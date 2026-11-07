"""TSPLIB parsing and the symmetric Euclidean distance matrix.

TSPLIB's official EUC_2D distance is

    d_ij = nint( sqrt((x_i - x_j)^2 + (y_i - y_j)^2) ),   nint(x) = floor(x + 0.5)

We keep the round-to-nearest integer distances so that reported tour
lengths can be compared directly with the published TSPLIB optima.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "tsp_files"


class TSPInstance(object):
    """A parsed symmetric TSP instance."""

    def __init__(
        self,
        name: str,
        coords,
        comment: str = "",
        path: Optional[str] = None,
    ) -> None:
        self.name = name
        self.comment = comment
        self.path = str(path) if path is not None else ""
        self.coords = np.asarray(coords, dtype=np.float64)
        if self.coords.ndim != 2 or self.coords.shape[1] != 2:
            raise ValueError(
                "coords must be an (n, 2) array, got shape %r" % (self.coords.shape,)
            )
        if self.coords.shape[0] < 2:
            raise ValueError("an instance needs at least two cities")
        self._dist = None  # type: Optional[np.ndarray]

    @property
    def n(self) -> int:
        return int(self.coords.shape[0])

    @property
    def dist(self) -> np.ndarray:
        """(n, n) int64 matrix of TSPLIB EUC_2D distances (cached)."""
        if self._dist is None:
            self._dist = pairwise_dist(self.coords)
        return self._dist

    def as_problem(self) -> Dict[str, object]:
        """Plain dict handed to the solver skeleton / evaluated programs."""
        return {"dist": self.dist, "coords": self.coords, "n": self.n}

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "TSPInstance(name=%r, n=%d)" % (self.name, self.n)


def pairwise_dist(coords: np.ndarray) -> np.ndarray:
    """TSPLIB EUC_2D distance matrix: nint of the Euclidean distance."""
    coords = np.asarray(coords, dtype=np.float64)
    diff = coords[:, None, :] - coords[None, :, :]
    euclid = np.sqrt((diff ** 2).sum(axis=-1))
    return np.floor(euclid + 0.5).astype(np.int64)


def parse_tsplib(path) -> TSPInstance:
    """Parse a TSPLIB ``.tsp`` file with ``EDGE_WEIGHT_TYPE : EUC_2D``."""
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")

    name = path.stem
    comment = ""
    dimension = None
    edge_weight_type = None
    coords = []  # type: List[tuple]
    in_coords = False

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        upper = line.upper()

        if not in_coords:
            if upper.startswith("EOF"):
                break
            if upper.startswith("NODE_COORD_SECTION"):
                in_coords = True
            elif upper.startswith("NAME"):
                name = _value_after_colon(line) or name
            elif upper.startswith("COMMENT"):
                comment = _value_after_colon(line)
            elif upper.startswith("DIMENSION"):
                value = _value_after_colon(line)
                if value:
                    dimension = int(float(value))
            elif upper.startswith("EDGE_WEIGHT_TYPE"):
                edge_weight_type = _value_after_colon(line).upper()
            # every other header line / section is ignored on purpose
            continue

        # inside NODE_COORD_SECTION
        parts = line.split()
        if len(parts) < 3:
            in_coords = False  # a new section started; keep scanning headers
            if upper.startswith("NODE_COORD_SECTION"):
                in_coords = True
            continue
        try:
            x = float(parts[1])
            y = float(parts[2])
        except ValueError:
            in_coords = False  # e.g. DISPLAY_DATA_SECTION or EOF marker
            continue
        coords.append((x, y))

    if edge_weight_type is not None and edge_weight_type != "EUC_2D":
        raise ValueError(
            "%s: unsupported EDGE_WEIGHT_TYPE %r (only EUC_2D is supported)"
            % (path.name, edge_weight_type)
        )
    if not coords:
        raise ValueError("%s: no NODE_COORD_SECTION entries found" % path.name)
    if dimension is not None and dimension != len(coords):
        raise ValueError(
            "%s: DIMENSION %d but %d coordinates" % (path.name, dimension, len(coords))
        )

    return TSPInstance(name=name, coords=coords, comment=comment, path=str(path))


def _value_after_colon(line: str) -> str:
    if ":" not in line:
        return ""
    return line.split(":", 1)[1].strip()


def resolve_instance_path(name_or_path, data_dir=None) -> Path:
    """Accept ``eil51``, ``eil51.tsp`` or a path to an existing file."""
    candidate = Path(str(name_or_path))
    if candidate.suffix.lower() == ".tsp" and candidate.is_file():
        return candidate
    root = Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR
    for option in (
        root / str(name_or_path),
        root / (str(name_or_path) + ".tsp"),
        candidate,
        candidate.with_suffix(".tsp"),
    ):
        if option.is_file():
            return option
    raise FileNotFoundError(
        "cannot find instance %r (looked in %s)" % (name_or_path, root)
    )


def load_instance(name_or_path, data_dir=None) -> TSPInstance:
    return parse_tsplib(resolve_instance_path(name_or_path, data_dir))


def load_instances(names, data_dir=None) -> List[TSPInstance]:
    return [load_instance(n, data_dir) for n in names]
