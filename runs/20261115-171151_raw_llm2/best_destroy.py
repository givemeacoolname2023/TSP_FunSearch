def destroy_priority(features):
    import numpy as np
    gap = features["gap"]
    saving = features["saving"]
    related = features["related"]
    density = features["density"]
    angle = features["angle"]
    pos = features["pos"]
    noise = features["noise"]

    # Normalise the raw-distance features to a comparable scale.
    def z(x):
        m = np.mean(x)
        s = np.std(x) + 1e-9
        return (x - m) / s

    # High saving = removing this city shortens the tour a lot.
    # High gap = city is far from its neighbours relative to the shortcut.
    # Sharp turns (angle near -1) often signal poor local structure.
    score = (
        1.0 * z(saving)
        + 0.8 * z(gap)
        - 0.6 * z(density)
        - 0.4 * z(angle)          # angle near -1 -> positive -> prefer removal
        - 0.5 * related           # related is already ~scaled; cluster removals
        + 0.15 * z(np.abs(pos))   # spread removals across the tour
        + 0.05 * noise            # tie-breaking
    )
    return score
