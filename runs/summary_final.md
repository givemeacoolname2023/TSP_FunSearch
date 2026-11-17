## Method comparison (final group)

| method | seeds | mean gap | std across seeds | worst instance |
|---|---|---|---|---|
| lsonly | 1 | +3.54% | 0.00% | +8.56% |
| random | 1 | +3.36% | 0.00% | +8.56% |
| worst | 1 | +2.86% | 0.00% | +5.31% |
| related | 1 | +2.27% | 0.00% | +4.77% |
| nearest-ins | 1 | +23.15% | 0.00% | +34.15% |
| nearest-ins-ls | 1 | +5.80% | 0.00% | +9.12% |
| cheapest-ins | 1 | +18.66% | 0.00% | +26.35% |
| cheapest-ins-ls | 1 | +5.27% | 0.00% | +9.84% |
| farthest-ins | 1 | +9.72% | 0.00% | +17.06% |
| farthest-ins-ls | 1 | +5.39% | 0.00% | +8.14% |
| llm | 3 | +2.31% | 0.17% | +4.73% |
| control | 3 | +2.12% | 0.24% | +4.89% |
| llm-raw | 3 | +2.25% | 0.00% | +4.72% |
| control-raw | 3 | +2.32% | 0.06% | +4.73% |

| instance | lsonly | random | worst | related | nearest-ins | nearest-ins-ls | cheapest-ins | cheapest-ins-ls | farthest-ins | farthest-ins-ls | llm | control | llm-raw | control-raw |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ts225 | +0.00% | +0.00% | +0.00% | +0.00% | +19.93% | +8.48% | +26.35% | +2.15% | +9.31% | +4.12% | +0.00% | +0.00% | +0.00% | +0.00% |
| tsp225 | +2.27% | +2.27% | +2.27% | +1.58% | +21.48% | +5.01% | +16.32% | +2.71% | +9.14% | +7.41% | +1.61% | +1.63% | +1.64% | +1.66% |
| pr226 | +1.19% | +0.84% | +0.89% | +0.74% | +28.01% | +6.09% | +13.26% | +6.48% | +2.81% | +1.36% | +0.48% | +0.46% | +0.58% | +0.23% |
| gil262 | +4.71% | +3.62% | +4.71% | +1.47% | +22.50% | +5.17% | +17.33% | +7.40% | +7.40% | +4.58% | +1.08% | +0.98% | +0.97% | +1.11% |
| pr264 | +8.56% | +8.56% | +0.00% | +3.92% | +34.15% | +9.12% | +18.51% | +9.84% | +10.16% | +6.34% | +3.71% | +2.54% | +3.92% | +3.82% |
| a280 | +5.31% | +5.31% | +5.31% | +4.77% | +19.97% | +7.87% | +15.63% | +5.04% | +17.06% | +8.14% | +4.73% | +4.89% | +4.72% | +4.73% |
| pr299 | +4.03% | +4.03% | +4.03% | +1.65% | +21.91% | +4.90% | +20.35% | +6.77% | +7.54% | +4.81% | +2.34% | +1.55% | +1.87% | +2.64% |
| lin318 | +3.74% | +3.74% | +3.74% | +3.09% | +24.51% | +2.84% | +17.70% | +4.75% | +7.44% | +4.09% | +3.15% | +3.04% | +3.08% | +3.03% |
| rd400 | +2.77% | +2.77% | +2.77% | +2.04% | +23.57% | +4.78% | +21.15% | +4.39% | +11.05% | +5.15% | +2.33% | +1.79% | +2.04% | +2.08% |
| fl417 | +3.10% | +2.50% | +3.10% | +2.38% | +22.28% | +2.87% | +20.55% | +2.38% | +7.82% | +3.29% | +2.47% | +2.29% | +2.40% | +2.31% |
| pr439 | +3.84% | +3.84% | +3.84% | +3.07% | +23.84% | +8.35% | +21.42% | +8.66% | +12.41% | +7.68% | +2.71% | +2.73% | +2.91% | +3.14% |
| pcb442 | +2.98% | +2.66% | +2.98% | +2.49% | +20.37% | +4.80% | +19.80% | +2.92% | +14.58% | +7.40% | +2.63% | +2.64% | +2.72% | +2.57% |
| d493 | +3.53% | +3.52% | +3.53% | +2.36% | +18.46% | +5.19% | +14.19% | +5.07% | +9.68% | +5.63% | +2.84% | +3.06% | +2.37% | +2.90% |

### Paired: llm vs control  (difference = llm - control; negative means llm better)

- instances compared: **13**
- mean difference: **+0.19%**
- 95% CI of the mean difference: ±0.22%
- standard deviation of the differences: 0.40%
- llm better on **5**, control better on **7**, ties **1**
- verdict: **inconclusive**

### Paired: llm vs related  (difference = llm - related; negative means llm better)

- instances compared: **13**
- mean difference: **+0.04%**
- 95% CI of the mean difference: ±0.17%
- standard deviation of the differences: 0.31%
- llm better on **5**, related better on **7**, ties **1**
- verdict: **inconclusive**

### Paired: llm vs llm-raw  (difference = llm - llm-raw; negative means llm better)

- instances compared: **13**
- mean difference: **+0.07%**
- 95% CI of the mean difference: ±0.12%
- standard deviation of the differences: 0.22%
- llm better on **5**, llm-raw better on **7**, ties **1**
- verdict: **inconclusive**

### Paired: control vs control-raw  (difference = control - control-raw; negative means control better)

- instances compared: **13**
- mean difference: **-0.20%**
- 95% CI of the mean difference: ±0.26%
- standard deviation of the differences: 0.47%
- control better on **7**, control-raw better on **5**, ties **1**
- verdict: **inconclusive**
