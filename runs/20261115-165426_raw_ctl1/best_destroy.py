def destroy_priority(features):
    return 0.3566 * features['gap'] + 0.7986 * features['saving'] + -1.0241 * features['related'] + -1.2418 * features['density'] + 0.0323 * features['angle'] + -0.3038 * features['pos'] + -1.4559 * features['noise']
