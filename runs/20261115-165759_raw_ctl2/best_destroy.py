def destroy_priority(features):
    return -2.3366 * features['gap'] + -0.5148 * features['saving'] + -1.5211 * features['related'] + -0.4854 * features['density'] + -0.1881 * features['angle'] + 0.9786 * features['pos'] + -0.0616 * features['noise']
