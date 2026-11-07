"""The frozen FunSearch skeleton for TSP, plus the seed `priority` program.

FunSearch only ever rewrites the body of ``priority``; everything below is
fixed and is shown verbatim to the LLM in every prompt.
"""
from __future__ import annotations

SKELETON_SOURCE = '''"""Frozen skeleton -- the priority function is the only evolvable part."""
import numpy as np


def solve(problem, priority):
    """Build one tour greedily and return it as a list/array of city indices.

    The tour starts at city 0 and at each step appends the unvisited city with
    the highest `priority` score. The last city is connected back to city 0 by
    `evaluate_tour`, so the returned sequence must be a permutation of
    range(problem["n"]).
    """
    dist = problem["dist"]        # (n, n) int64, TSPLIB EUC_2D distances
    coords = problem["coords"]    # (n, 2) float64 city coordinates
    n = problem["n"]              # number of cities

    visited = np.zeros(n, dtype=bool)
    tour = np.empty(n, dtype=np.int64)
    tour[0] = 0
    visited[0] = True
    cur = 0
    for step in range(1, n):
        candidates = np.flatnonzero(~visited)            # unvisited cities
        scores = priority(cur, candidates, visited, dist, coords, step, n)
        scores = np.asarray(scores, dtype=float).ravel()
        if scores.shape[0] != candidates.shape[0]:
            raise ValueError("priority returned %d scores for %d candidates"
                             % (scores.shape[0], candidates.shape[0]))
        if not np.all(np.isfinite(scores)):
            raise ValueError("priority returned non-finite scores")
        nxt = int(candidates[int(np.argmax(scores))])    # ties -> smallest index
        tour[step] = nxt
        visited[nxt] = True
        cur = nxt
    return tour


def evaluate_tour(tour, problem):
    """Closed-tour length under TSPLIB EUC_2D distances (minimisation)."""
    dist = problem["dist"]
    tour = np.asarray(tour, dtype=np.int64).ravel()
    return int(dist[tour, np.roll(tour, -1)].sum())
'''

#: The signature every evolved program must use. It is frozen: the prompt
#: repeats it, the static checker enforces it.
PRIORITY_SIGNATURE = "priority(current, candidates, visited, dist, coords, step, n)"

PRIORITY_DOCSTRING = '''"""Score the candidate next cities of a greedy TSP construction.

Arguments
---------
current : int
    Index of the city the tour currently stands on.
candidates : np.ndarray, shape (m,)
    Indices of the still-unvisited cities, in increasing order. Exactly these
    cities must be scored, one score each, in this order.
visited : np.ndarray of bool, shape (n,)
    True for cities already in the tour.
dist : np.ndarray, shape (n, n), int64
    Symmetric TSPLIB EUC_2D distance matrix.
coords : np.ndarray, shape (n, 2), float64
    City coordinates.
step : int
    Number of cities already placed (1 <= step <= n-1). step / n is the
    fraction of the tour that has been built.
n : int
    Total number of cities.

Returns
-------
np.ndarray, shape (m,)
    One score per entry of `candidates`; higher scores are visited earlier.
    Any finite real value is allowed. Returned scores are ranked, so only the
    relative order matters.
"""'''

SEED_PRIORITY = '''def priority(current, candidates, visited, dist, coords, step, n):
    """Nearest neighbour: prefer the closest unvisited city."""
    return -dist[current, candidates]
'''

#: Prompt-friendly view of the skeleton: skeleton + the empty function to evolve.
SKELETON_WITH_STUB = (
    SKELETON_SOURCE.rstrip()
    + "\n\n\n# ---- Function to be evolved by FunSearch ----\n"
    + "def priority(current, candidates, visited, dist, coords, step, n):\n"
    + "    "
    + PRIORITY_DOCSTRING.replace("\n", "\n    ")
    + "\n"
)


def build_source(priority_code: str) -> str:
    """Full, executable module source: frozen skeleton + candidate ``priority``."""
    code = (priority_code or "").strip()
    if not code:
        raise ValueError("empty priority code")
    source = SKELETON_SOURCE.rstrip() + "\n\n\n# ---- evolved by FunSearch ----\n" + code + "\n"
    compile(source, "<FunSearch candidate>", "exec")  # raises SyntaxError if broken
    return source


def check_signature(priority_code: str) -> None:
    """Reject candidates that do not define ``priority`` with the frozen signature."""
    import ast

    tree = ast.parse(priority_code)
    found = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "priority":
            found.append(node)
    if not found:
        raise ValueError("no top-level `def priority(...)` found")
    func = found[0]
    args = [a.arg for a in func.args.args]
    expected = ["current", "candidates", "visited", "dist", "coords", "step", "n"]
    if args != expected:
        raise ValueError(
            "priority signature must be (%s), got (%s)"
            % (", ".join(expected), ", ".join(args))
        )
