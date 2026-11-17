def destroy_priority(features):
    return 0.3559 * features['gap'] + -0.1160 * features['saving'] + -1.6182 * features['related'] + -0.9291 * features['density'] + -0.8859 * features['angle'] + -0.5215 * features['pos'] + -0.8370 * features['noise']
