def destroy_priority(features):
    saving = features["saving"]
    related = features["related"]
    gap = features["gap"]
    angle = features["angle"]
    density = features["density"]
    pos = features["pos"]
    noise = features["noise"]

    # Normalise the raw, scale-dependent signals so they are comparable.
    save_signal = np.tanh(saving)
    turn_signal = -angle
    gap_signal = 1.0 - 1.0 / np.maximum(gap, 1e-9)
    related_signal = -related
    density_signal = -np.tanh(density)
    pos_signal = np.abs(pos)

    # Combine: expensive + structurally awkward cities get removed.
    base = (2.2 * save_signal
            + 1.3 * turn_signal
            + 0.8 * gap_signal
            + 0.7 * related_signal
            + 0.3 * density_signal
            + 0.2 * pos_signal)

    # Small deterministic jitter to break ties.
    return base + 0.05 * noise
