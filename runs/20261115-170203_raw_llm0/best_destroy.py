def destroy_priority(features):
    import numpy as np
    gap = features["gap"]
    saving = features["saving"]
    related = features["related"]
    density = features["density"]
    angle = features["angle"]
    pos = features["pos"]
    noise = features["noise"]

    # Rebias toward spatial clustering around the seed (related), which lets the
    # frozen cheapest-insertion repair rebuild a coherent region, while still
    # favoring costly detours (saving/gap) and sharp turns (angle near -1).
    # `saving` and `density` are in raw distance units, so they dominate by
    # magnitude; compress `saving` to keep the scales comparable.
    score = (
        1.4 * (gap - 1.0)
        + 0.9 * np.tanh(saving)
        - 0.8 * angle
        - 1.2 * related
        + 0.4 * np.tanh(1.0 - density)
        + 0.2 * np.abs(pos)
        + 0.05 * noise
    )
    return score
