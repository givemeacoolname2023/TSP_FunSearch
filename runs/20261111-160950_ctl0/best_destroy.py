def destroy_priority(features):
    return 0.3739 * features['gap'] + 0.7552 * features['saving'] + -0.8861 * features['related'] + -0.3958 * features['density'] + -0.3040 * features['angle'] + -1.0536 * features['pos'] + -0.2701 * features['noise']
