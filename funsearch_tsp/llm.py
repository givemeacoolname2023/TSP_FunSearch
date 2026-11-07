"""LLM clients: a DeepSeek (OpenAI-compatible) client and an offline mock.

The real client talks to any OpenAI-compatible ``/chat/completions`` endpoint,
so switching provider only means changing ``DEEPSEEK_BASE_URL`` /
``DEEPSEEK_MODEL`` in ``.env``. The mock client needs no key and returns a
deterministic sequence of parameterised heuristics, which lets the whole
FunSearch loop (prompting, sandboxing, evaluation, islands, reporting) be
tested and demonstrated without spending money.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import List, Optional

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


class LLMError(RuntimeError):
    """A call to the LLM failed after all retries."""


def load_env_file(path=".env") -> None:
    """Minimal ``.env`` loader; never overrides variables already in the env."""
    if not path:
        return
    env_path = Path(path)
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


class ChatLLM(object):
    """OpenAI-compatible chat completion client with retries."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        api_key: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: int = 1600,
        timeout: float = 180.0,
        max_retries: int = 4,
        verbose: bool = True,
        extra_body: Optional[dict] = None,
    ) -> None:
        key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        if not key:
            raise LLMError(
                "no API key: set DEEPSEEK_API_KEY in .env (see .env.example) "
                "or run with --mock"
            )
        self.api_key = key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries
        self.verbose = verbose
        # Provider-specific request fields merged into the payload, e.g.
        # {"thinking": {"type": "disabled"}} to switch a reasoning model off.
        self.extra_body = dict(extra_body or {})
        self.total_calls = 0
        self.total_tokens = 0
        self.last_usage = {}

    # ------------------------------------------------------------------ #
    def _post(self, prompt: str) -> str:
        import requests  # imported lazily so --mock needs no dependency handling

        url = self.base_url + "/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        payload.update(self.extra_body)
        headers = {
            "Authorization": "Bearer " + self.api_key,
            "Content-Type": "application/json",
        }
        response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        if response.status_code != 200:
            raise LLMError(
                "HTTP %d from %s: %s"
                % (response.status_code, url, response.text[:500])
            )
        data = response.json()
        usage = data.get("usage") or {}
        if usage:
            self.last_usage = usage
            self.total_tokens += int(usage.get("total_tokens", 0) or 0)
        try:
            choice = data["choices"][0]
            message = choice["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("unexpected response shape: %s" % (exc,))

        content = message.get("content") or ""
        if not content.strip():
            reasoning = message.get("reasoning_content") or ""
            if reasoning:
                raise LLMError(
                    "the model spent its whole output budget on reasoning and returned no "
                    "answer (finish_reason=%r). Disable thinking (--thinking off) or raise "
                    "--max-tokens." % (choice.get("finish_reason"),)
                )
            raise LLMError(
                "empty completion (finish_reason=%r)" % (choice.get("finish_reason"),)
            )
        return content

    def generate(self, prompt: str) -> str:
        """Return one completion, retrying transient failures with backoff."""
        delay = 2.0
        last_error = ""
        for attempt in range(1, self.max_retries + 1):
            try:
                self.total_calls += 1
                text = self._post(prompt)
                if not text.strip():
                    raise LLMError("empty completion")
                return text
            except Exception as exc:  # noqa: BLE001 - network errors are broad
                last_error = "%s: %s" % (type(exc).__name__, exc)
                if attempt >= self.max_retries:
                    break
                if self.verbose:
                    print("  ! LLM call failed (%s), retry %d/%d in %.0fs"
                          % (last_error, attempt, self.max_retries - 1, delay))
                time.sleep(delay)
                delay = min(delay * 2, 30.0)
        raise LLMError("LLM call failed after %d attempts: %s" % (self.max_retries, last_error))


# --------------------------------------------------------------------------- #
# offline mock
# --------------------------------------------------------------------------- #
_LOOKAHEAD_TEMPLATE = '''def priority_v2(current, candidates, visited, dist, coords, step, n):
    """Nearest neighbour with a look-ahead on the cheapest way out of a city."""
    d = dist[current, candidates].astype(float)
    sub = dist[np.ix_(candidates, candidates)].astype(float)
    np.fill_diagonal(sub, np.inf)
    way_out = sub.min(axis=1)
    way_out = np.where(np.isfinite(way_out), way_out, 0.0)
    return -d - %s * way_out
'''

_ISOLATION_TEMPLATE = '''def priority_v2(current, candidates, visited, dist, coords, step, n):
    """Visit cities that are far from the remaining unvisited cities first."""
    d = dist[current, candidates].astype(float)
    sub = dist[np.ix_(candidates, candidates)].astype(float)
    np.fill_diagonal(sub, np.inf)
    isolation = sub.min(axis=1)
    isolation = np.where(np.isfinite(isolation), isolation, 0.0)
    return -d + %s * isolation
'''

_RADIAL_TEMPLATE = '''def priority_v2(current, candidates, visited, dist, coords, step, n):
    """Grow the tour from the outside in, using the distance to the visited centroid."""
    centre = coords[visited].mean(axis=0)
    radial = np.hypot(coords[candidates, 0] - centre[0], coords[candidates, 1] - centre[1])
    d = dist[current, candidates].astype(float)
    return -d + %s * radial * (1.0 - step / n)
'''

_PROGRESS_TEMPLATE = '''def priority_v2(current, candidates, visited, dist, coords, step, n):
    """Nearest neighbour early on, then reward cities close to another unvisited city."""
    d = dist[current, candidates].astype(float)
    sub = dist[np.ix_(candidates, candidates)].astype(float)
    np.fill_diagonal(sub, np.inf)
    nearest_other = sub.min(axis=1)
    nearest_other = np.where(np.isfinite(nearest_other), nearest_other, 0.0)
    return -d + (step / n) * %s * nearest_other
'''

_FARTHEST_TEMPLATE = '''def priority_v2(current, candidates, visited, dist, coords, step, n):
    """Deliberately poor baseline: prefer the farthest city (kept for testing)."""
    return dist[current, candidates].astype(float)
'''


class MockLLM(object):
    """Deterministic stand-in for the real LLM (no network, no cost).

    Emits a rotating sequence of parameterised heuristics, so successive calls
    return *different* programs and the islands/clusters actually fill up.
    """

    def __init__(self, verbose: bool = True) -> None:
        self.verbose = verbose
        self.calls = 0
        self.total_calls = 0
        self.total_tokens = 0
        self.last_usage = {}

    def _next_code(self) -> str:
        step = self.calls
        self.calls += 1
        family = step % 5
        # 45 distinct weights per family, so a mock run stays unique for a while
        weight = "%.2f" % (0.05 + 0.02 * ((step // 5) % 45),)
        if family == 0:
            return _LOOKAHEAD_TEMPLATE % (weight,)
        if family == 1:
            return _ISOLATION_TEMPLATE % (weight,)
        if family == 2:
            return _RADIAL_TEMPLATE % (weight,)
        if family == 3:
            return _PROGRESS_TEMPLATE % (weight,)
        return _FARTHEST_TEMPLATE

    def generate(self, prompt: str) -> str:
        self.total_calls += 1
        code = self._next_code()
        return "Here is my improved heuristic.\n\n```python\n%s```\n" % (code,)
