def destroy_priority(features):
    gap = features["gap"]
    saving = features["saving"]
    related = features["related"]
    density = features["density"]
    angle = features["angle"]
    pos = features["pos"]
    noise = features["noise"]

    # Worst removal: cities contributing most extra length.
    worst = 0.7 * saving + 0.3 * (gap - 1.0)

    # Related removal: tear out a coherent spatial region around the seed.
    cluster = -1.1 * related

    # Break sharp U-turns (angle near -1) left over from construction / LS.
    turn = 0.5 * (1.0 - angle)

    # Sparse cities reinsert easily; dense ones are harder and less useful.
    sparse = 0.3 * density

    # Encourage spreading along the tour so repair can rebuild a region,
    # with mild locality so removals stay coherent.
    spread = 0.2 * pos

    # Tie-break jitter keeps removal sets from being deterministically stuck.
    tie = 0.1 * noise

    return worst + cluster + turn + sparse + spread + tie
