"""Classical constructive heuristics (the insertion family) as extra baselines.

The proposal promises a first comparison family of *constructive heuristics* —
nearest / cheapest / farthest insertion — each of them also in a version that
runs 2-opt + Or-opt afterwards ("+ LS").  None of these use the destroy
operator, so they are baselines, not FunSearch targets: they exist to show how
much of the final tour length is explained by the construction and the local
search alone.

They are evaluated through the same sandbox as everything else: ``build_source``
returns a module whose ``solve(problem, priority)`` builds and (optionally)
improves a tour, so ``solve.py`` and ``tools/eval_baselines.py`` can measure
them without any special case in the evaluator.
"""
from __future__ import annotations

from . import skeleton_ils

#: The three insertion variants.  They differ only in *which* city is inserted
#: next; the insertion position is always the cheapest one.
KINDS = ("nearest-insertion", "cheapest-insertion", "farthest-insertion")

CONSTRUCTOR_SOURCE = '''

# ---- constructive baselines: the insertion family ----
def _start_pair(dist):
    """Seed the subtour with city 0 and its nearest neighbour."""
    n = dist.shape[0]
    row = dist[0].astype(np.int64).copy()
    row[0] = np.iinfo(np.int64).max
    first = int(np.argmin(row))
    return np.array([0, first], dtype=np.int64)


def _insertion_position(tour, dist, city):
    """Index of the edge in `tour` where `city` is cheapest to insert."""
    u = tour
    v = np.roll(tour, -1)
    cost = dist[u, city] + dist[city, v] - dist[u, v]
    return int(np.argmin(cost))


def _nearest_or_farthest(problem, farthest):
    dist = problem["dist"]
    n = problem["n"]
    tour = _start_pair(dist)
    in_tour = np.zeros(n, dtype=bool)
    in_tour[tour] = True
    # dmin[c] = distance from c to the current subtour (kept for every city;
    # visited cities are masked out below instead of being given a sentinel,
    # because "nearest" and "farthest" need opposite sentinels).
    dmin = np.minimum(dist[0], dist[tour[-1]]).astype(np.float64)
    while tour.size < n:
        if farthest:
            score = np.where(in_tour, -np.inf, dmin)
            city = int(np.argmax(score))
        else:
            score = np.where(in_tour, np.inf, dmin)
            city = int(np.argmin(score))
        pos = _insertion_position(tour, dist, city)
        tour = np.insert(tour, pos + 1, city)
        in_tour[city] = True
        dmin = np.minimum(dmin, dist[city].astype(np.float64))
    return tour


def nearest_insertion(problem):
    """Always insert the unvisited city closest to the current subtour."""
    return _nearest_or_farthest(problem, farthest=False)


def farthest_insertion(problem):
    """Always insert the unvisited city farthest from the current subtour."""
    return _nearest_or_farthest(problem, farthest=True)


def cheapest_insertion(problem):
    """Insert the (city, edge) pair with the smallest insertion cost overall."""
    dist = problem["dist"]
    n = problem["n"]
    tour = _start_pair(dist)
    in_tour = np.zeros(n, dtype=bool)
    in_tour[tour] = True
    while tour.size < n:
        remaining = np.flatnonzero(~in_tour)
        u = tour
        v = np.roll(tour, -1)
        delta = (dist[np.ix_(remaining, u)]
                 + dist[np.ix_(v, remaining)].T
                 - dist[u, v][None, :])
        flat = int(np.argmin(delta))
        which, pos = divmod(flat, tour.size)
        city = int(remaining[which])
        tour = np.insert(tour, pos + 1, city)
        in_tour[city] = True
    return tour
'''

#: Short label -> (constructor name, run local search afterwards)
_LABELS = {
    "nearest-ins": ("nearest_insertion", False),
    "nearest-ins-ls": ("nearest_insertion", True),
    "cheapest-ins": ("cheapest_insertion", False),
    "cheapest-ins-ls": ("cheapest_insertion", True),
    "farthest-ins": ("farthest_insertion", False),
    "farthest-ins-ls": ("farthest_insertion", True),
}

#: All baseline labels this module can evaluate (bare and with local search).
LABELS = tuple(_LABELS)

DESCRIPTIONS = {
    "nearest-ins": "nearest insertion, no local search",
    "nearest-ins-ls": "nearest insertion + 2-opt/Or-opt",
    "cheapest-ins": "cheapest insertion, no local search",
    "cheapest-ins-ls": "cheapest insertion + 2-opt/Or-opt",
    "farthest-ins": "farthest insertion, no local search",
    "farthest-ins-ls": "farthest insertion + 2-opt/Or-opt",
}


def build_source(label: str) -> str:
    """Module source for one constructive baseline (runs inside the sandbox)."""
    if label not in _LABELS:
        raise KeyError("unknown constructive baseline %r (choose from %s)"
                       % (label, ", ".join(LABELS)))
    func, with_ls = _LABELS[label]
    finish = "return local_search(tour, problem)" if with_ls else "return tour"
    source = skeleton_ils.SKELETON_SOURCE.rstrip() + CONSTRUCTOR_SOURCE + '''


# ---- placeholder: this baseline never calls the evolved function ----
def destroy_priority(features):
    """Never called."""
    return features["noise"]


def solve(problem, priority):
    """Build a tour with the chosen insertion rule%s."""
    tour = %s(problem)
    %s
''' % (" and polish it with 2-opt/Or-opt" if with_ls else "", func, finish)
    compile(source, "<constructive baseline>", "exec")
    return source
