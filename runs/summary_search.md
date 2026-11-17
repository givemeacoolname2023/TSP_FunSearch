## Method comparison (search group)

| method | seeds | mean gap | std across seeds | worst instance |
|---|---|---|---|---|
| lsonly | 1 | +2.60% | 0.00% | +5.50% |
| random | 1 | +2.20% | 0.00% | +5.50% |
| worst | 1 | +2.60% | 0.00% | +5.50% |
| related | 1 | +0.74% | 0.00% | +2.42% |
| nearest-ins | 1 | +20.38% | 0.00% | +26.42% |
| nearest-ins-ls | 1 | +4.73% | 0.00% | +7.69% |
| cheapest-ins | 1 | +16.83% | 0.00% | +21.76% |
| cheapest-ins-ls | 1 | +5.72% | 0.00% | +10.19% |
| farthest-ins | 1 | +7.61% | 0.00% | +12.96% |
| farthest-ins-ls | 1 | +3.58% | 0.00% | +10.29% |
| llm | 3 | +0.65% | 0.10% | +2.42% |
| control | 3 | +0.62% | 0.01% | +2.42% |
| llm-raw | 3 | +0.65% | 0.03% | +2.42% |
| control-raw | 3 | +0.65% | 0.03% | +2.42% |

| instance | lsonly | random | worst | related | nearest-ins | nearest-ins-ls | cheapest-ins | cheapest-ins-ls | farthest-ins | farthest-ins-ls | llm | control | llm-raw | control-raw |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| eil51 | +0.70% | +0.23% | +0.70% | +0.23% | +15.96% | +5.40% | +15.96% | +6.10% | +4.93% | +3.29% | +0.23% | +0.23% | +0.23% | +0.23% |
| berlin52 | +2.74% | +2.64% | +2.74% | +0.00% | +19.21% | +7.69% | +19.38% | +6.06% | +9.72% | +8.01% | +0.76% | +0.00% | +0.00% | +0.00% |
| st70 | +2.52% | +2.52% | +2.52% | +1.48% | +21.63% | +5.04% | +15.70% | +5.93% | +6.52% | +1.33% | +0.74% | +0.99% | +0.99% | +1.23% |
| eil76 | +1.67% | +1.12% | +1.67% | +1.12% | +15.24% | +4.09% | +12.27% | +4.09% | +9.29% | +2.04% | +1.12% | +1.12% | +1.12% | +1.12% |
| pr76 | +3.11% | +2.03% | +3.11% | +0.95% | +19.26% | +6.00% | +16.44% | +3.68% | +5.53% | +3.66% | +0.95% | +0.95% | +0.95% | +0.95% |
| rat99 | +4.38% | +2.89% | +4.38% | +0.83% | +19.98% | +4.71% | +18.41% | +5.86% | +8.75% | +4.29% | +0.03% | +0.03% | +0.30% | +0.08% |
| kroA100 | +2.09% | +2.09% | +2.09% | +0.00% | +21.55% | +3.52% | +17.20% | +5.75% | +11.72% | +2.33% | +0.00% | +0.11% | +0.00% | +0.00% |
| kroB100 | +0.58% | +0.58% | +0.58% | +0.26% | +21.38% | +0.00% | +15.54% | +4.11% | +5.48% | +2.89% | +0.26% | +0.26% | +0.26% | +0.26% |
| kroC100 | +5.50% | +5.50% | +5.50% | +1.13% | +26.42% | +6.74% | +21.76% | +10.19% | +4.58% | +0.80% | +0.80% | +0.92% | +1.13% | +0.96% |
| kroD100 | +3.52% | +2.42% | +3.52% | +2.42% | +18.43% | +6.45% | +18.36% | +6.45% | +4.72% | +1.44% | +2.42% | +2.42% | +2.42% | +2.42% |
| kroE100 | +3.45% | +3.45% | +3.45% | +0.42% | +25.52% | +0.68% | +17.36% | +0.68% | +7.18% | +2.57% | +0.44% | +0.44% | +0.42% | +0.57% |
| rd100 | +0.99% | +0.99% | +0.99% | +0.00% | +19.91% | +6.40% | +13.53% | +9.79% | +12.96% | +10.29% | +0.00% | +0.00% | +0.00% | +0.00% |

### Paired: llm vs control  (difference = llm - control; negative means llm better)

- instances compared: **12**
- mean difference: **+0.02%**
- 95% CI of the mean difference: ±0.14%
- standard deviation of the differences: 0.25%
- llm better on **3**, control better on **1**, ties **8**
- verdict: **inconclusive**

### Paired: llm vs related  (difference = llm - related; negative means llm better)

- instances compared: **12**
- mean difference: **-0.09%**
- 95% CI of the mean difference: ±0.23%
- standard deviation of the differences: 0.40%
- llm better on **3**, related better on **2**, ties **7**
- verdict: **inconclusive**

### Paired: llm vs llm-raw  (difference = llm - llm-raw; negative means llm better)

- instances compared: **12**
- mean difference: **-0.01%**
- 95% CI of the mean difference: ±0.16%
- standard deviation of the differences: 0.27%
- llm better on **3**, llm-raw better on **2**, ties **7**
- verdict: **inconclusive**

### Paired: control vs control-raw  (difference = control - control-raw; negative means control better)

- instances compared: **12**
- mean difference: **-0.03%**
- 95% CI of the mean difference: ±0.05%
- standard deviation of the differences: 0.09%
- control better on **4**, control-raw better on **1**, ties **7**
- verdict: **inconclusive**
