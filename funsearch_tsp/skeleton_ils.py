"""The frozen ILS skeleton for FunSearch on TSP.

Structure (fixed, the LLM may not change any of it):

    greedy_construct  -> nearest-neighbour tour
    local_search      -> 2-opt, then Or-opt, until neither improves
    ils               -> T rounds of  destroy -> repair -> local_search -> accept

The single evolvable piece is ``destroy_priority(features)``: it scores every
city and the ``k`` highest scores are ripped out of the tour.

Everything the evolved function can see is a *scale-free* feature, i.e. a
quantity divided by the current average edge length ``d_bar = L / n`` or a
ratio/cosine.  This is what makes a program evolved on 50-city instances
transfer to 200-city instances.
"""
from __future__ import annotations

import ast

#: Name + argument list of the frozen evolved function.
NAME = "ils"
EVOLVED_NAME = "destroy_priority"
SIGNATURE_ARGS = ["features"]
SIGNATURE = "destroy_priority(features)"

#: Fixed ILS constants (identical for every matched-skeleton method).
DEFAULT_ITERATIONS = 100
DEFAULT_K = 10
LOCAL_SEARCH_SEGMENTS = 3  # Or-opt segment lengths 1..3

#: The frozen feature set.  Every feature is either dimensionless by
#: construction (gap, angle, pos, noise) or divided by the current average edge
#: length d_bar = L/n (saving, related, density), which is what makes a program
#: evolved on 50-city instances behave the same on 300-city ones.
FEATURES = ("gap", "saving", "related", "density", "angle", "pos", "noise")

#: Features that are part of the *scaling* argument (the other four are
#: dimensionless anyway, so the "raw" variant only changes these three).
SCALED_FEATURES = ("saving", "related", "density")

#: The trivial seed program reads this one, so it can never be ablated away.
ALWAYS_ON = ("noise",)

#: One-line description per feature, used by the prompt and the docs.
FEATURE_HELP = {
    "gap": "(d(prev,i) + d(i,next)) / d(prev,next), always >= 1",
    "saving": "(d(prev,i) + d(i,next) - d(prev,next)) / d_bar",
    "related": "d(seed, i) / d_bar, distance to a random seed city",
    "density": "mean distance to the 5 nearest cities / d_bar",
    "angle": "cos(prev->i, i->next), in [-1, 1]",
    "pos": "(position(i) - position(seed)) / n, in [-1, 1]",
    "noise": "U[0, 1), freshly drawn every ILS round",
}

SKELETON_SOURCE = '''"""Frozen ILS skeleton -- only `destroy_priority` is evolved."""
import numpy as np

# ---- feature configuration (build_source overrides these two lines) ----
ENABLED_FEATURES = ("gap", "saving", "related", "density", "angle", "pos", "noise")
SCALE_FREE = True


def tour_length(tour, dist):
    """Closed-tour length under TSPLIB EUC_2D integer distances."""
    return int(dist[tour, np.roll(tour, -1)].sum())


def evaluate_tour(tour, problem):
    """Same as tour_length, kept for compatibility with the greedy skeleton."""
    return tour_length(np.asarray(tour, dtype=np.int64).ravel(), problem["dist"])


def greedy_construct(problem):
    """Nearest-neighbour construction (frozen starting point)."""
    dist = problem["dist"]
    n = problem["n"]
    visited = np.zeros(n, dtype=bool)
    tour = np.empty(n, dtype=np.int64)
    tour[0] = 0
    visited[0] = True
    cur = 0
    for step in range(1, n):
        cand = np.flatnonzero(~visited)
        d = dist[cur, cand]
        cur = int(cand[int(np.argmin(d))])
        tour[step] = cur
        visited[cur] = True
    return tour


def _local_density(dist, k=5):
    """Mean distance from each city to its k nearest neighbours (static)."""
    n = dist.shape[0]
    k = min(k, n - 1)
    order = np.argsort(dist, axis=1)[:, 1:k + 1]
    return dist[np.arange(n)[:, None], order].mean(axis=1).astype(float)


def two_opt(tour, dist, max_moves=400):
    """Best-improvement 2-opt over all edge pairs, until no move helps."""
    tour = np.asarray(tour, dtype=np.int64).copy()
    n = tour.size
    if n < 5:
        return tour
    valid = np.triu(np.ones((n, n), dtype=bool), k=2)
    valid[0, n - 1] = False
    for _ in range(max_moves):
        a = tour
        b = np.roll(tour, -1)
        d_ab = dist[a, b]
        delta = (dist[np.ix_(a, a)] + dist[np.ix_(b, b)]
                 - d_ab[:, None] - d_ab[None, :])
        delta = np.where(valid, delta, 0)
        flat = int(np.argmin(delta))
        i, j = divmod(flat, n)
        if delta[i, j] >= 0:
            break
        tour[i + 1:j + 1] = tour[i + 1:j + 1][::-1]
    return tour


def or_opt(tour, dist, max_moves=80, max_seg=3):
    """Or-opt: relocate a segment of 1..max_seg cities, either orientation."""
    tour = np.asarray(tour, dtype=np.int64).copy()
    n = tour.size
    if n < 6:
        return tour
    idx = np.arange(n)
    dif = (idx[:, None] - idx[None, :]) % n     # dif[j, i] = (j - i) mod n
    for _ in range(max_moves):
        best = None          # (delta, i, length, j, reversed)
        for length in range(1, max_seg + 1):
            if n - length < 3:
                break
            start = tour
            end = tour[(idx + length - 1) % n]
            prev = tour[(idx - 1) % n]
            nxt = tour[(idx + length) % n]
            gain = (dist[prev, start] + dist[end, nxt] - dist[prev, nxt]).astype(float)
            u = tour                                   # gap j is (u[j], v[j])
            v = np.roll(tour, -1)
            base = dist[u, v].astype(float)
            fwd = dist[np.ix_(u, start)] + dist[np.ix_(end, v)].T - base[:, None]
            bwd = dist[np.ix_(u, end)] + dist[np.ix_(start, v)].T - base[:, None]
            delta_f = fwd - gain[None, :]
            delta_b = bwd - gain[None, :]
            bad = (dif <= (length - 1)) | (dif == (n - 1))   # own gap / inside
            delta_f = np.where(bad, 0.0, delta_f)
            delta_b = np.where(bad, 0.0, delta_b)
            for delta, rev in ((delta_f, False), (delta_b, True)):
                flat = int(np.argmin(delta))
                j, i = divmod(flat, n)
                if delta[j, i] < -1e-9 and (best is None or delta[j, i] < best[0]):
                    best = (float(delta[j, i]), i, length, j, rev)
        if best is None:
            break
        _, i, length, j, rev = best
        seg = tour[(i + idx[:length]) % n]
        if rev:
            seg = seg[::-1]
        keep = np.ones(n, dtype=bool)
        keep[(i + idx[:length]) % n] = False
        rest = tour[keep]
        # insertion gap j is (tour[j], tour[j+1]); convert to a position in `rest`
        anchor = tour[j]
        insert_at = int(np.flatnonzero(rest == anchor)[0]) + 1
        tour = np.concatenate([rest[:insert_at], seg, rest[insert_at:]])
    return tour


def local_search(tour, problem, max_rounds=4):
    """2-opt then Or-opt, repeated until neither improves."""
    dist = problem["dist"]
    tour = np.asarray(tour, dtype=np.int64).copy()
    best = tour_length(tour, dist)
    for _ in range(max_rounds):
        tour = two_opt(tour, dist)
        tour = or_opt(tour, dist)
        length = tour_length(tour, dist)
        if length >= best:
            break
        best = length
    return tour


def remove_cities(tour, removed):
    """Drop `removed` from `tour`, keeping the visiting order."""
    drop = np.zeros(int(tour.max()) + 1, dtype=bool)
    drop[np.asarray(removed, dtype=np.int64)] = True
    return tour[~drop[tour]]


def cheapest_insertion(partial, removed, dist):
    """Reinsert every removed city at its cheapest gap (frozen repair)."""
    tour = np.asarray(partial, dtype=np.int64).copy()
    for city in np.asarray(removed, dtype=np.int64):
        u = tour
        v = np.roll(tour, -1)
        cost = dist[u, city] + dist[city, v] - dist[u, v]
        pos = int(np.argmin(cost))
        tour = np.insert(tour, pos + 1, city)
    return tour


def _by_city(tour, values):
    """Scatter per-tour-position values into a per-city array."""
    out = np.empty(tour.size, dtype=float)
    out[tour] = values
    return out


def features_of(tour, problem, rng):
    """The frozen, scale-free feature set shown to `destroy_priority`."""
    dist = problem["dist"]
    coords = problem["coords"]
    n = problem["n"]
    prev = np.roll(tour, 1)
    nxt = np.roll(tour, -1)
    d_prev = dist[prev, tour].astype(float)
    d_next = dist[tour, nxt].astype(float)
    d_close = dist[prev, nxt].astype(float)
    d_bar = max(d_prev.sum() / float(n), 1e-9)

    vec_in = coords[tour] - coords[prev]
    vec_out = coords[nxt] - coords[tour]
    norm = (np.linalg.norm(vec_in, axis=1) * np.linalg.norm(vec_out, axis=1)) + 1e-9
    cosang = (vec_in * vec_out).sum(axis=1) / norm

    position = np.empty(n, dtype=float)
    position[tour] = np.arange(n, dtype=float)
    seed_city = int(rng.integers(n))

    scale = d_bar if SCALE_FREE else 1.0
    every = {
        "gap": _by_city(tour, (d_prev + d_next) / np.maximum(d_close, 1e-9)),
        "saving": _by_city(tour, (d_prev + d_next - d_close) / scale),
        "related": dist[seed_city, :].astype(float) / scale,
        "density": problem["density"] / scale,
        "angle": _by_city(tour, cosang),
        "pos": (position - position[seed_city]) / float(n),
        "noise": rng.random(n),
    }
    return {name: every[name] for name in ENABLED_FEATURES}


def ils(problem, destroy_priority, iterations=100, k=10, seed=0):
    """Destroy -> repair -> local search -> accept, repeated `iterations` times."""
    dist = problem["dist"]
    n = problem["n"]
    if "density" not in problem:
        problem["density"] = _local_density(dist)
    k = max(1, min(int(k), n - 2))
    rng = np.random.default_rng(int(seed))

    tour = local_search(greedy_construct(problem), problem)
    best = tour.copy()
    best_len = tour_length(best, dist)

    for _ in range(int(iterations)):
        scores = np.asarray(destroy_priority(features_of(tour, problem, rng)),
                            dtype=float).ravel()
        if scores.shape[0] != n:
            raise ValueError("destroy_priority returned %d scores for %d cities"
                             % (scores.shape[0], n))
        if not np.all(np.isfinite(scores)):
            raise ValueError("destroy_priority returned non-finite scores")
        removed = np.argsort(-scores, kind="stable")[:k]
        partial = remove_cities(tour, removed)
        candidate = cheapest_insertion(partial, removed, dist)
        candidate = local_search(candidate, problem)
        length = tour_length(candidate, dist)
        if length < best_len:
            best = candidate.copy()
            best_len = length
        if length <= tour_length(tour, dist):
            tour = candidate
    return best
'''

#: The trivial seed program: pure random destruction.
SEED_DESTROY = '''def destroy_priority(features):
    """Random destruction (the trivial seed program)."""
    return features["noise"]
'''

#: Alias used by ``evaluate``/``run`` through the uniform skeleton interface.
SEED = SEED_DESTROY

#: The human-designed baseline the evolved operator has to beat.
WORST_REMOVAL = '''def destroy_priority(features):
    """Worst removal: rip out the cities whose removal saves the most length."""
    return features["saving"]
'''

#: Related removal, a second human baseline (a classical LNS operator).
RELATED_REMOVAL = '''def destroy_priority(features):
    """Related removal: rip out the cities closest to a random seed city."""
    return -features["related"]
'''

BASELINES = {
    "random": SEED_DESTROY,
    "worst": WORST_REMOVAL,
    "related": RELATED_REMOVAL,
}

PRIORITY_DOCSTRING = '''"""Score every city; the k highest scores are removed from the tour.

Arguments
---------
features : dict[str, np.ndarray]
    Seven arrays of shape (n,), each indexed by *city id* (not tour order).
    All of them are scale-free: distances are divided by the current average
    edge length d_bar = tour_length / n, so the same program behaves the same
    way on 20-city and 200-city instances.

    gap      : (d(prev,i) + d(i,next)) / d(prev,next)      in [1, ...]
    saving   : (d(prev,i) + d(i,next) - d(prev,next)) / d_bar
    related  : d(seed, i) / d_bar        distance to a random seed city
    density  : mean_k d(i, .) / d_bar    local sparsity around city i
    angle    : cos(prev->i, i->next)     in [-1, 1]
    pos      : (position(i) - position(seed)) / n   in [-1, 1]
    noise    : U[0, 1)                   fixed random values for this round

Returns
-------
np.ndarray, shape (n,)
    One finite score per city; larger means "remove this city earlier".
    Only the relative order matters.
"""'''

SKELETON_WITH_STUB = (
    SKELETON_SOURCE.rstrip()
    + "\n\n\n# ---- Function to be evolved by FunSearch ----\n"
    + "def destroy_priority(features):\n"
    + "    "
    + PRIORITY_DOCSTRING.replace("\n", "\n    ")
    + "\n"
)


def stub_docstring(features=None, scaled: bool = False) -> str:
    """Docstring for the stub, describing only the features actually exposed.

    An ablation run must not advertise a feature it has removed, otherwise the
    model writes `features["saving"]` in a run where that key does not exist and
    every candidate is rejected.
    """
    enabled = normalize_features(features)
    if scaled:
        scale_line = (
            "    The distance-like arrays are in RAW distance units (not divided by\n"
            "    d_bar), so their magnitudes grow with the instance's coordinate scale."
        )
    else:
        scale_line = (
            "    All of them are scale-free: distances are divided by the current average\n"
            "    edge length d_bar = tour_length / n, so the same program behaves the same\n"
            "    way on 20-city and 200-city instances."
        )
    rows = {
        "gap": "    gap      : (d(prev,i) + d(i,next)) / d(prev,next)      in [1, ...]",
        "saving": "    saving   : (d(prev,i) + d(i,next) - d(prev,next)) / d_bar",
        "related": "    related  : d(seed, i) / d_bar        distance to a random seed city",
        "density": "    density  : mean_k d(i, .) / d_bar    local sparsity around city i",
        "angle": "    angle    : cos(prev->i, i->next)     in [-1, 1]",
        "pos": "    pos      : (position(i) - position(seed)) / n   in [-1, 1]",
        "noise": "    noise    : U[0, 1)                   fixed random values for this round",
    }
    lines = [
        '"""Score every city; the k highest scores are removed from the tour.',
        "",
        "Arguments",
        "---------",
        "features : dict[str, np.ndarray]",
        "    %d arrays of shape (n,), each indexed by *city id* (not tour order)."
        % (len(enabled),),
        scale_line,
        "",
    ]
    lines.extend(rows[name] for name in enabled if name in rows)
    lines.extend([
        "",
        "Returns",
        "-------",
        "np.ndarray, shape (n,)",
        '    One finite score per city; larger means "remove this city earlier".',
        "    Only the relative order matters.",
        '"""',
    ])
    return "\n".join(lines)


def build_stub(features=None, scaled: bool = False) -> str:
    """Skeleton source plus a stub whose docstring matches the feature set."""
    enabled = normalize_features(features)
    body = stub_docstring(enabled, scaled)
    block = ""
    if enabled != tuple(FEATURES) or scaled:
        block = (
            "# ---- feature configuration ----\n"
            "ENABLED_FEATURES = %r\n"
            "SCALE_FREE = %r\n\n" % (tuple(enabled), not scaled)
        )
    return (SKELETON_SOURCE.rstrip() + "\n\n\n" + block
            + "# ---- Function to be evolved by FunSearch ----\n"
            + "def destroy_priority(features):\n"
            + "    "
            + body.replace("\n", "\n    ")
            + "\n")


def normalize_features(features=None) -> tuple:
    """Validate a feature subset and return it in canonical order.

    ``None`` (or an empty sequence) means "all of them".  ``noise`` is always
    kept because the trivial seed program reads it.
    """
    if not features:
        return tuple(FEATURES)
    wanted = set()
    for name in features:
        key = str(name).strip().lower()
        if key not in FEATURES:
            raise ValueError("unknown feature %r (choose from %s)"
                             % (name, ", ".join(FEATURES)))
        wanted.add(key)
    wanted.update(ALWAYS_ON)
    return tuple(name for name in FEATURES if name in wanted)


def features_key(features=None, scaled: bool = False) -> str:
    """Stable string used to scope caches and to record a run's configuration."""
    return "features=%s;scale=%s" % (",".join(normalize_features(features)),
                                     "raw" if scaled else "free")


def build_source(destroy_code: str, features=None, scaled: bool = False) -> str:
    """Full executable module: frozen ILS skeleton + candidate destroy function.

    ``features`` (a subset of :data:`FEATURES`) and ``scaled`` (use raw distance
    units instead of dividing by d_bar) are baked into the module as
    ``ENABLED_FEATURES`` / ``SCALE_FREE``, so the very same candidate code is
    measured against the feature configuration it was evolved for.
    """
    code = (destroy_code or "").strip()
    if not code:
        raise ValueError("empty destroy_priority code")
    enabled = normalize_features(features)
    block = ""
    if enabled != tuple(FEATURES) or scaled:
        block = (
            "# ---- feature configuration ----\n"
            "ENABLED_FEATURES = %r\n"
            "SCALE_FREE = %r\n\n" % (tuple(enabled), not scaled)
        )
    source = (SKELETON_SOURCE.rstrip() + "\n\n\n" + block
              + "# ---- evolved by FunSearch ----\n" + code + "\n")
    compile(source, "<FunSearch candidate (ils)>", "exec")
    return source


#: Ablation "A2": nearest neighbour + 2-opt/Or-opt only, *no* ILS loop.
#: It exposes ``solve`` (which the sandbox prefers over ``ils``) so the same
#: evaluation path measures the skeleton's local search on its own. The dummy
#: ``destroy_priority`` is never called and only satisfies the loader.
LOCAL_SEARCH_ONLY = (
    SKELETON_SOURCE.rstrip()
    + '''


# ---- A2 ablation: no ILS loop, only the local search ----
def destroy_priority(features):
    """Never called: this variant stops after the local search."""
    return features["noise"]


def solve(problem, priority):
    """Nearest-neighbour construction followed by 2-opt + Or-opt."""
    return local_search(greedy_construct(problem), problem)
'''
)

#: Extra ablation names accepted by ``solve --baseline`` besides BASELINES.
EXTRA_BASELINES = ("lsonly",)


def local_search_only_source() -> str:
    """Module source of the A2 ablation (NN + local search, no destruction)."""
    source = LOCAL_SEARCH_ONLY
    compile(source, "<local search only>", "exec")
    return source


def check_signature(destroy_code: str) -> None:
    """Reject candidates that do not define ``destroy_priority(features)``."""
    tree = ast.parse(destroy_code)
    found = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == EVOLVED_NAME
    ]
    if not found:
        raise ValueError("no top-level `def destroy_priority(features)` found")
    args = [a.arg for a in found[0].args.args]
    if args != SIGNATURE_ARGS:
        raise ValueError(
            "destroy_priority signature must be (%s), got (%s)"
            % (", ".join(SIGNATURE_ARGS), ", ".join(args))
        )
