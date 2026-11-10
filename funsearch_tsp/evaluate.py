"""The FunSearch evaluation function for TSP.

For every training instance we build a tour with the frozen skeleton and
measure its length ``L``. With ``L_nn`` the length produced by the seed
program (nearest neighbour, computed once per run) the per-instance score is

    s_i = (L_nn_i - L_i) / L_nn_i        (1.0 would be a perfect tour)

so ``s_i = 0`` means "no better than nearest neighbour", and positive values
mean an improvement. The aggregate score is the mean over instances, and the
*unrounded* tuple of per-instance scores is the program's signature, used for
clustering. Relative scores keep instances of different size on the same
scale, which matters because a 20-city and a 50-city tour differ by ~2.5x in
absolute length.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from . import sandbox, skeleton
from .tsp import TSPInstance

#: Fallback training set, used only when ``tsp_files/data/split.json`` is absent.
#: Five instances spanning 51-100 cities, mixing clustered (eil*/berlin*/kro*)
#: and uniform (rd100) geometry, all ``EUC_2D`` with a published optimum.
TRAIN_DEFAULT = ("eil51", "berlin52", "st70", "kroA100", "rd100")


@dataclass
class Evaluation:
    """Result of evaluating one candidate program."""

    ok: bool
    score: float = -math.inf
    signature: Tuple[float, ...] = ()
    lengths: Dict[str, int] = field(default_factory=dict)
    rel: Dict[str, float] = field(default_factory=dict)
    error: str = ""
    elapsed: float = 0.0
    cached: bool = False

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "score": self.score,
            "signature": list(self.signature),
            "lengths": self.lengths,
            "rel": self.rel,
            "error": self.error,
            "elapsed": self.elapsed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Evaluation":
        return cls(
            ok=bool(data["ok"]),
            score=float(data["score"]),
            signature=tuple(float(x) for x in data.get("signature", ())),
            lengths={k: int(v) for k, v in data.get("lengths", {}).items()},
            rel={k: float(v) for k, v in data.get("rel", {}).items()},
            error=str(data.get("error", "")),
            elapsed=float(data.get("elapsed", 0.0)),
            cached=True,
        )


def instances_payload(instances: Sequence[TSPInstance]) -> Dict[str, dict]:
    """Plain, picklable description of the instances handed to the subprocess."""
    payload = {}
    for inst in instances:
        payload[inst.name] = {
            "dist": inst.dist,
            "coords": inst.coords,
            "n": inst.n,
        }
    return payload


def score_from_lengths(
    lengths: Dict[str, int], baseline: Dict[str, float]
) -> Tuple[Dict[str, float], float, Tuple[float, ...]]:
    """Relative per-instance improvements, their mean, and the signature."""
    rel = {}  # type: Dict[str, float]
    for name, length in lengths.items():
        base = float(baseline[name])
        rel[name] = (base - float(length)) / base if base else 0.0
    ordered = tuple(rel[name] for name in lengths)
    score = sum(ordered) / len(ordered) if ordered else -math.inf
    signature = tuple(round(x, 3) for x in ordered)
    return rel, score, signature


def compute_baseline(
    payload: Dict[str, dict], timeout: float = 60.0, skel=None
) -> Dict[str, float]:
    """Tour lengths of the skeleton's seed program, one per instance.

    For the greedy skeleton that is nearest neighbour; for the ILS skeleton it
    is the ILS driven by the trivial *random-destruction* seed, so score 0 means
    "no better than random destruction" — the baseline the evolved operator has
    to beat.
    """
    skel = skel if skel is not None else skeleton
    source = skel.build_source(skel.SEED)
    ok, result, _ = sandbox.run_source(source, payload, timeout=timeout)
    if not ok:
        raise RuntimeError("the seed program failed to run: %s" % (result,))
    return {name: float(v) for name, v in result["lengths"].items()}


def evaluate_program(
    priority_code: str,
    payload: Dict[str, dict],
    baseline: Dict[str, float],
    timeout: float = 30.0,
    cache: Optional[sandbox.ResultCache] = None,
    use_cache: bool = True,
    skel=None,
) -> Evaluation:
    """Static-check, execute and score one candidate program."""
    skel = skel if skel is not None else skeleton
    if cache is not None and use_cache:
        hit = cache.get(priority_code)
        if hit is not None:
            return Evaluation.from_dict(hit)

    try:
        sandbox.validate_candidate(priority_code, skel=skel)
    except sandbox.ProgramRejected as exc:
        return Evaluation(ok=False, error="rejected: %s" % (exc,))

    try:
        source = skel.build_source(priority_code)
    except SyntaxError as exc:  # pragma: no cover - validate_candidate catches it
        return Evaluation(ok=False, error="SyntaxError: %s" % (exc,))

    ok, result, elapsed = sandbox.run_source(source, payload, timeout=timeout)
    if not ok:
        return Evaluation(ok=False, error=str(result), elapsed=elapsed)

    lengths = {name: int(v) for name, v in result["lengths"].items()}
    missing = [name for name in payload if name not in lengths]
    if missing:
        return Evaluation(
            ok=False, error="missing results for %s" % (", ".join(missing)), elapsed=elapsed
        )

    rel, score, signature = score_from_lengths(lengths, baseline)
    evaluation = Evaluation(
        ok=True,
        score=score,
        signature=signature,
        lengths=lengths,
        rel=rel,
        elapsed=elapsed,
    )
    if cache is not None:
        cache.put(priority_code, evaluation.to_dict())
    return evaluation
