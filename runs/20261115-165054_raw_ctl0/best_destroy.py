def destroy_priority(features):
    return -0.4561 * features['gap'] + 0.6277 * features['saving'] + -0.8813 * features['related'] + -1.0025 * features['density'] + -2.5054 * features['angle'] + 0.7862 * features['pos'] + -0.2332 * features['noise']
