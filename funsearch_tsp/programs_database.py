"""Islands, signature clusters and the sampling rules of FunSearch.

This follows Romera-Paredes et al., Nature 625, 468-475 (2024), Methods
"Programs database": islands evolve independently, programs inside an island
are clustered by their signature (the tuple of per-instance scores), a cluster
is sampled with Boltzmann selection favouring high scores, and a program inside
that cluster is sampled favouring short code. Periodically the programs of the
worst half of the islands are discarded and re-seeded from the best program of
a surviving island.

One deliberate deviation: the paper feeds raw scores into the Boltzmann
exponent, but our scores are relative improvements in the 0-0.1 range, which
would make the exponential nearly uniform. We therefore min-max normalise the
scores inside an island before applying the temperature.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np


@dataclass
class Program:
    """One evaluated candidate (or the seed) stored in the database."""

    program_id: int
    code: str
    score: float
    signature: Tuple[float, ...] = ()
    lengths: Dict[str, int] = field(default_factory=dict)
    rel: Dict[str, float] = field(default_factory=dict)
    island_id: int = -1
    parents: Tuple[int, ...] = ()
    created_at: float = field(default_factory=time.time)
    origin: str = "llm"  # "seed" | "llm" | "clone"

    @property
    def char_len(self) -> int:
        return len(self.code)

    def to_dict(self) -> dict:
        return {
            "program_id": self.program_id,
            "island_id": self.island_id,
            "score": self.score,
            "signature": list(self.signature),
            "lengths": self.lengths,
            "rel": self.rel,
            "char_len": self.char_len,
            "parents": list(self.parents),
            "origin": self.origin,
            "created_at": self.created_at,
            "code": self.code,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Program":
        return cls(
            program_id=int(data["program_id"]),
            code=data["code"],
            score=float(data["score"]),
            signature=tuple(float(x) for x in data.get("signature", ())),
            lengths={k: int(v) for k, v in data.get("lengths", {}).items()},
            rel={k: float(v) for k, v in data.get("rel", {}).items()},
            island_id=int(data.get("island_id", -1)),
            parents=tuple(int(x) for x in data.get("parents", ())),
            created_at=float(data.get("created_at", 0.0)),
            origin=str(data.get("origin", "llm")),
        )

    def clone(self) -> "Program":
        return Program(
            program_id=self.program_id,
            code=self.code,
            score=self.score,
            signature=self.signature,
            lengths=dict(self.lengths),
            rel=dict(self.rel),
            island_id=-1,
            parents=self.parents,
            created_at=self.created_at,
            origin="clone",
        )


class Island(object):
    """A subpopulation of programs, clustered by signature."""

    def __init__(self, island_id: int) -> None:
        self.island_id = island_id
        self.clusters = {}  # type: Dict[Tuple[float, ...], List[Program]]

    # -- population ------------------------------------------------------- #
    def add(self, program: Program) -> None:
        program.island_id = self.island_id
        self.clusters.setdefault(program.signature, []).append(program)

    def clear(self) -> None:
        self.clusters = {}

    @property
    def programs(self) -> List[Program]:
        out = []  # type: List[Program]
        for members in self.clusters.values():
            out.extend(members)
        return out

    @property
    def size(self) -> int:
        return sum(len(m) for m in self.clusters.values())

    @property
    def best(self) -> Optional[Program]:
        programs = self.programs
        if not programs:
            return None
        return max(programs, key=lambda p: (p.score, -p.program_id))

    @property
    def best_score(self) -> float:
        best = self.best
        return best.score if best is not None else -math.inf

    # -- sampling (paper eq. 1 and the program-length rule) ---------------- #
    def cluster_scores(self) -> List[float]:
        return [float(np.mean([p.score for p in members])) for members in self.clusters.values()]

    def sample_cluster(self, rng: np.random.Generator, t0: float, cycle: int) -> Tuple[float, ...]:
        signatures = list(self.clusters.keys())
        if len(signatures) == 1:
            return signatures[0]
        scores = np.asarray(self.cluster_scores(), dtype=float)
        spread = float(scores.max() - scores.min())
        if spread <= 0:
            normalised = np.zeros_like(scores)
        else:
            normalised = (scores - scores.min()) / spread
        n = max(self.size, 1)
        temperature = t0 * (1.0 - (n % cycle) / float(cycle))
        temperature = max(temperature, 1e-6)
        # Subtract the max before exponentiating: same distribution, but immune
        # to overflow when the temperature gets small at the end of a cycle.
        shifted = normalised - float(normalised.max())
        weights = np.exp(shifted / temperature)
        total = weights.sum()
        if not np.isfinite(total) or total <= 0:
            weights = np.ones_like(scores)
            total = weights.sum()
        probabilities = weights / total
        index = int(rng.choice(len(signatures), p=probabilities))
        return signatures[index]

    def sample_program(
        self,
        rng: np.random.Generator,
        t0: float = 0.1,
        cycle: int = 50,
        t_program: float = 0.1,
    ) -> Optional[Program]:
        if not self.clusters:
            return None
        signature = self.sample_cluster(rng, t0, cycle)
        members = self.clusters[signature]
        if len(members) == 1:
            return members[0]
        lengths = np.asarray([-p.char_len for p in members], dtype=float)
        lo, hi = lengths.min(), lengths.max()
        if hi <= lo:  # every program has the same length: sample uniformly
            normalised = np.ones_like(lengths)
        else:
            normalised = (lengths - lo) / (hi - lo) + 1e-6
        weights = np.exp(normalised / max(t_program, 1e-6))
        probabilities = weights / weights.sum()
        index = int(rng.choice(len(members), p=probabilities))
        return members[index]


class ProgramsDatabase(object):
    """The islands model, with periodic resets of the worst half."""

    def __init__(
        self,
        num_islands: int,
        seed_program: Program,
        rng: Optional[np.random.Generator] = None,
        t_cluster: float = 0.1,
        t_program: float = 0.1,
        cycle: int = 50,
        num_sampled: int = 2,
    ) -> None:
        if num_islands < 2:
            raise ValueError("FunSearch needs at least two islands for resets to work")
        self.num_islands = int(num_islands)
        self.rng = rng if rng is not None else np.random.default_rng(0)
        self.t_cluster = float(t_cluster)
        self.t_program = float(t_program)
        self.cycle = int(cycle)
        self.num_sampled = int(num_sampled)
        self._next_id = 0
        self.islands = [Island(i) for i in range(self.num_islands)]
        self.events = []  # type: List[dict]
        self._seed_code = seed_program.code
        self._seed_score = seed_program.score
        self._seed_signature = seed_program.signature
        self._seed_lengths = dict(seed_program.lengths)
        self._seed_rel = dict(seed_program.rel)
        seed = self._new_program(
            seed_program.code,
            seed_program.score,
            seed_program.signature,
            seed_program.lengths,
            seed_program.rel,
            origin="seed",
        )
        for island in self.islands:
            island.add(seed.clone())

    # -- bookkeeping ------------------------------------------------------- #
    def _new_program(self, code, score, signature, lengths, rel, parents=(), origin="llm") -> Program:
        program = Program(
            program_id=self._next_id,
            code=code,
            score=float(score),
            signature=tuple(signature),
            lengths=dict(lengths),
            rel=dict(rel),
            parents=tuple(parents),
            origin=origin,
        )
        self._next_id += 1
        return program

    def add(self, program: Program, island_id: int) -> Program:
        program.program_id = self._next_id
        self._next_id += 1
        self.islands[island_id].add(program)
        return program

    def all_programs(self) -> List[Program]:
        out = []  # type: List[Program]
        for island in self.islands:
            out.extend(island.programs)
        return out

    def best_program(self) -> Optional[Program]:
        programs = self.all_programs()
        if not programs:
            return None
        return max(programs, key=lambda p: (p.score, -p.program_id))

    def stats(self) -> dict:
        return {
            "num_islands": self.num_islands,
            "num_programs": len(self.all_programs()),
            "island_best_scores": [round(i.best_score, 6) for i in self.islands],
            "island_sizes": [i.size for i in self.islands],
            "island_clusters": [len(i.clusters) for i in self.islands],
        }

    # -- sampling ---------------------------------------------------------- #
    def sample(self) -> Tuple[int, List[Program]]:
        """Uniformly pick an island, then sample ``num_sampled`` programs in it."""
        island_id = int(self.rng.integers(self.num_islands))
        island = self.islands[island_id]
        picked = []  # type: List[Program]
        for _ in range(self.num_sampled):
            program = island.sample_program(
                self.rng, t0=self.t_cluster, cycle=self.cycle, t_program=self.t_program
            )
            if program is not None:
                picked.append(program)
        return island_id, picked

    # -- island reset ------------------------------------------------------ #
    def reset_worst_half(self) -> List[dict]:
        """Wipe the programs of the worst half and re-seed them from survivors."""
        ranked = sorted(self.islands, key=lambda i: (-i.best_score, i.island_id))
        keep = max(1, self.num_islands // 2)
        survivors, losers = ranked[:keep], ranked[keep:]
        resets = []  # type: List[dict]
        for island in losers:
            donor = survivors[int(self.rng.integers(len(survivors)))]
            best = donor.best
            if best is None:  # pragma: no cover - survivors always hold a program
                continue
            island.clear()
            island.add(best.clone())
            event = {
                "event": "island_reset",
                "island_id": island.island_id,
                "donor_island": donor.island_id,
                "donor_program": best.program_id,
                "score": round(best.score, 6),
                "time": time.time(),
            }
            resets.append(event)
            self.events.append(event)
        return resets
