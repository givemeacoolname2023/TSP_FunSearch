def destroy_priority(features):
    import numpy as np
    gap = features["gap"]
    saving = features["saving"]
    related = features["related"]
    density = features["density"]
    angle = features["angle"]
    pos = features["pos"]
    noise = features["noise"]

    # Worst-removal: high saving means a big detour that repair can shortcut.
    # Related removal: small `related` (close to seed) is the target region;
    # `1 - related` rewards proximity so a coherent cluster is destroyed.
    score = 1.0 * saving + 0.8 * (1.0 - related)

    # Awkward nodes in the tour: high gap (long detour vs shortcut).
    score = score + 0.30 * (gap - 1.0)

    # Sharp turns (low cos) are strong candidates for reordering.
    score = score - 0.15 * angle

    # Cities in sparse regions have more freedom when reinserted.
    score = score - 0.12 * density

    # Spread removals along the tour rather than dumping them into one gap:
    # use |pos| around the seed to reach both sides of the cycle.
    score = score + 0.20 * np.abs(pos)

    # Deterministic tie-break, small so it never overrides real signal.
    return score + 1e-3 * noise
