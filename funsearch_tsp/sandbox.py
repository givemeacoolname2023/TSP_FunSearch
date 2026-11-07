"""Static validation and isolated execution of LLM-generated programs.

Every candidate runs in a fresh ``spawn`` subprocess with a wall-clock
timeout, so an infinite loop, a crash or a `sys.exit()` cannot take the
FunSearch loop down. The static checks are a cheap first filter (a denylist,
not a real sandbox): they stop the obvious accidents before paying for a
subprocess, and README documents this limitation honestly.
"""
from __future__ import annotations

import ast
import hashlib
import json
import multiprocessing as mp
import os
import pickle
import shutil
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import skeleton

#: Modules a heuristic has any business importing.
ALLOWED_IMPORTS = {
    "math",
    "random",
    "itertools",
    "collections",
    "functools",
    "operator",
    "statistics",
    "numpy",
}

#: Names a candidate must not call.
FORBIDDEN_CALLS = {
    "eval",
    "exec",
    "compile",
    "open",
    "input",
    "breakpoint",
    "globals",
    "locals",
    "vars",
    "dir",
    "getattr",
    "setattr",
    "delattr",
    "__import__",
    "memoryview",
}

#: Functions of the skeleton a candidate must not shadow.
RESERVED_DEFS = {"solve", "evaluate_tour"}


class ProgramRejected(ValueError):
    """The candidate failed the static checks and was never executed."""


def validate_candidate(priority_code: str) -> None:
    """Raise :class:`ProgramRejected` unless the code is safe to try.

    Checks, in order: it defines ``priority`` with the frozen signature, it
    only imports allowed modules, it does not call dangerous builtins, it does
    not touch dunder attributes, and it does not redefine the skeleton.
    """
    code = (priority_code or "").strip()
    if not code:
        raise ProgramRejected("empty program")
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise ProgramRejected("SyntaxError: %s" % (exc,))

    try:
        skeleton.check_signature(code)
    except ValueError as exc:
        raise ProgramRejected(str(exc))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in ALLOWED_IMPORTS:
                    raise ProgramRejected("import of %r is not allowed" % (alias.name,))
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                raise ProgramRejected("relative imports are not allowed")
            root = (node.module or "").split(".")[0]
            if root not in ALLOWED_IMPORTS:
                raise ProgramRejected("import from %r is not allowed" % (node.module,))
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in FORBIDDEN_CALLS:
                raise ProgramRejected("call to %r is not allowed" % (func.id,))
            if isinstance(func, ast.Attribute) and func.attr.startswith("__"):
                raise ProgramRejected("dunder call %r is not allowed" % (func.attr,))
        elif isinstance(node, ast.Name):
            if node.id.startswith("__"):
                raise ProgramRejected("dunder name %r is not allowed" % (node.id,))
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                raise ProgramRejected("dunder attribute %r is not allowed" % (node.attr,))
        elif isinstance(node, ast.FunctionDef):
            if node.name in RESERVED_DEFS:
                raise ProgramRejected("redefining %r is not allowed" % (node.name,))

    # Building the full module compiles the candidate together with the skeleton.
    try:
        skeleton.build_source(code)
    except SyntaxError as exc:
        raise ProgramRejected("SyntaxError: %s" % (exc,))


# --------------------------------------------------------------------------- #
# child process
# --------------------------------------------------------------------------- #
def _write_result(path: str, payload: Tuple[str, object]) -> None:
    """Hand a result back to the parent through a file, never through a pipe."""
    if not path:
        return
    try:
        with open(path, "wb") as handle:
            pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception:
        pass


def _child_entry(args_path: str) -> None:
    """Entry point of the evaluation subprocess (must stay module level).

    The job is read from, and the result written to, ordinary files. A
    ``multiprocessing.Queue`` cannot be used here: when the payload is larger
    than the OS pipe buffer, the child's feeder thread blocks while the parent
    sits in ``join()``, so a worker that has already finished looks like a
    timeout. Tours are only requested by ``solve.py``, which is exactly the
    case where that payload grows past the buffer.
    """
    result_path = ""
    try:
        with open(args_path, "rb") as handle:
            job = pickle.load(handle)
        source = job["source"]
        instances = job["instances"]
        want_tours = job["want_tours"]
        result_path = job["result_path"]
        np.random.seed(0)  # deterministic heuristics even if they sample
        namespace = {"np": np, "__name__": "funsearch_candidate", "__builtins__": __builtins__}
        exec(compile(source, "<FunSearch candidate>", "exec"), namespace)

        solve = namespace.get("solve")
        evaluate_tour = namespace.get("evaluate_tour")
        priority = namespace.get("priority")
        if not (callable(solve) and callable(evaluate_tour) and callable(priority)):
            raise RuntimeError("skeleton functions missing after exec")

        lengths = {}  # type: Dict[str, int]
        tours = {}  # type: Dict[str, List[int]]
        for name, blob in instances.items():
            problem = {
                "dist": np.asarray(blob["dist"], dtype=np.int64),
                "coords": np.asarray(blob["coords"], dtype=np.float64),
                "n": int(blob["n"]),
            }
            tour = np.asarray(solve(problem, priority)).ravel()
            n = problem["n"]
            if tour.shape[0] != n:
                raise ValueError("tour has %d cities, expected %d" % (tour.shape[0], n))
            if tour.min() < 0 or tour.max() >= n or len(set(tour.tolist())) != n:
                raise ValueError("tour is not a permutation of range(n)")
            lengths[name] = int(evaluate_tour(tour.astype(np.int64), problem))
            if want_tours:
                tours[name] = [int(c) for c in tour]

        _write_result(result_path, ("ok", {"lengths": lengths, "tours": tours}))
    except BaseException as exc:  # noqa: BLE001 - report everything to the parent
        _write_result(result_path, ("error", "%s: %s" % (type(exc).__name__, exc)))


def run_source(
    source: str,
    instances: Dict[str, dict],
    timeout: float = 30.0,
    want_tours: bool = False,
) -> Tuple[bool, object, float]:
    """Execute ``source`` on ``instances`` in a subprocess.

    Returns ``(ok, payload, elapsed)``. When ``ok``, ``payload`` is
    ``{"lengths": {name: length}, "tours": {name: [cities]}}`` (``tours`` is
    empty unless ``want_tours``); otherwise ``payload`` is an error string.
    """
    ctx = mp.get_context("spawn")
    workdir = tempfile.mkdtemp(prefix="funsearch_eval_")
    args_path = os.path.join(workdir, "job.pkl")
    result_path = os.path.join(workdir, "result.pkl")
    try:
        with open(args_path, "wb") as handle:
            pickle.dump({"source": source, "instances": instances,
                         "want_tours": want_tours, "result_path": result_path},
                        handle, protocol=pickle.HIGHEST_PROTOCOL)

        proc = ctx.Process(target=_child_entry, args=(args_path,))
        proc.daemon = True
        started = time.time()
        proc.start()
        proc.join(timeout)
        elapsed = time.time() - started

        if proc.is_alive():
            proc.terminate()
            proc.join(5.0)
            if proc.is_alive() and hasattr(proc, "kill"):
                proc.kill()
                proc.join(5.0)
            return False, "Timeout after %.1fs" % (timeout,), elapsed

        if not os.path.exists(result_path):
            return False, ("worker died without a result (exitcode=%r)"
                           % (proc.exitcode,)), elapsed
        try:
            with open(result_path, "rb") as handle:
                payload = pickle.load(handle)
        except Exception as exc:
            return False, "unreadable worker result (%s)" % (exc,), elapsed

        kind, value = payload
        if kind == "ok":
            return True, value, elapsed
        return False, str(value), elapsed
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# --------------------------------------------------------------------------- #
# result cache (never pay for the same program twice)
# --------------------------------------------------------------------------- #
def code_key(priority_code: str) -> str:
    """Stable hash of a program: insensitive to leading/trailing whitespace."""
    normalized = "\n".join(
        line.rstrip() for line in (priority_code or "").strip().splitlines() if line.strip()
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class ResultCache(object):
    """JSON-backed ``code_hash -> evaluation record`` cache."""

    def __init__(self, path) -> None:
        self.path = Path(path)
        self.data = {}  # type: Dict[str, dict]
        if self.path.is_file():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                self.data = {}

    def get(self, priority_code: str) -> Optional[dict]:
        return self.data.get(code_key(priority_code))

    def put(self, priority_code: str, record: dict) -> None:
        self.data[code_key(priority_code)] = record

    def __len__(self) -> int:
        return len(self.data)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
