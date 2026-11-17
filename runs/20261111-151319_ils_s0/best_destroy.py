def destroy_priority(features):
    gap = features["gap"]
    saving = features["saving"]
    related = features["related"]
    density = features["density"]
    angle = features["angle"]
    pos = features["pos"]
    noise = features["noise"]

    # Worst removal: high saving (removing the city shortens the tour a lot).
    # Related removal: focus around the seed (small related = close to seed).
    # Avoid dense regions (hard to reconnect) and sharp turns (bad reinsert).
    # Spread removals: strongly favour cities near the seed in tour position
    # (|pos| small) so the cluster is spatially+positionally coherent.
    score = (
        1.10 * saving
        - 0.90 * related
        - 0.35 * density
        - 0.30 * (angle + 1.0)
        + 0.20 * gap
        - 0.50 * np.abs(pos)
        + 0.05 * noise
    )
    return score
