## Method comparison (validation group)

| method | seeds | mean gap | std across seeds | worst instance |
|---|---|---|---|---|
| lsonly | 1 | +2.18% | 0.00% | +6.43% |
| random | 1 | +1.97% | 0.00% | +6.43% |
| worst | 1 | +2.16% | 0.00% | +6.43% |
| related | 1 | +0.96% | 0.00% | +4.59% |
| nearest-ins | 1 | +20.35% | 0.00% | +31.91% |
| nearest-ins-ls | 1 | +3.74% | 0.00% | +6.96% |
| cheapest-ins | 1 | +17.90% | 0.00% | +24.76% |
| cheapest-ins-ls | 1 | +3.79% | 0.00% | +7.40% |
| farthest-ins | 1 | +7.26% | 0.00% | +11.80% |
| farthest-ins-ls | 1 | +3.30% | 0.00% | +6.11% |
| llm | 3 | +1.04% | 0.04% | +4.40% |
| control | 3 | +1.13% | 0.03% | +4.62% |
| llm-raw | 3 | +1.04% | 0.04% | +4.59% |
| control-raw | 3 | +1.13% | 0.04% | +5.38% |

| instance | lsonly | random | worst | related | nearest-ins | nearest-ins-ls | cheapest-ins | cheapest-ins-ls | farthest-ins | farthest-ins-ls | llm | control | llm-raw | control-raw |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| eil101 | +0.32% | +0.16% | +0.16% | +0.00% | +13.04% | +3.34% | +11.61% | +4.29% | +7.31% | +3.50% | +0.11% | +0.00% | +0.00% | +0.00% |
| lin105 | +1.40% | +1.40% | +1.40% | +0.33% | +31.91% | +3.19% | +17.57% | +1.22% | +6.11% | +2.60% | +0.19% | +0.19% | +0.26% | +0.11% |
| pr107 | +0.62% | +0.30% | +0.62% | +0.30% | +20.11% | +1.34% | +18.70% | +5.18% | +2.98% | +0.59% | +0.00% | +0.10% | +0.30% | +0.30% |
| pr124 | +1.24% | +1.24% | +1.24% | +0.00% | +15.50% | +2.60% | +10.65% | +1.57% | +10.11% | +2.64% | +0.00% | +0.00% | +0.00% | +0.00% |
| bier127 | +1.05% | +1.05% | +1.05% | +0.37% | +23.21% | +4.09% | +18.91% | +4.80% | +9.29% | +3.13% | +0.58% | +0.84% | +0.37% | +0.64% |
| ch130 | +5.04% | +2.44% | +5.04% | +1.46% | +21.87% | +4.57% | +19.49% | +6.55% | +4.93% | +2.34% | +2.26% | +2.13% | +2.21% | +2.21% |
| pr136 | +6.43% | +6.43% | +6.43% | +4.59% | +10.20% | +3.39% | +13.24% | +1.99% | +8.59% | +5.49% | +4.40% | +4.62% | +4.59% | +5.38% |
| pr144 | +1.28% | +1.28% | +1.28% | +0.00% | +25.75% | +0.69% | +24.76% | +0.69% | +8.10% | +4.67% | +0.39% | +0.00% | +0.00% | +0.00% |
| ch150 | +0.70% | +0.70% | +0.70% | +0.61% | +22.06% | +3.95% | +22.52% | +1.70% | +8.84% | +6.11% | +0.61% | +0.61% | +0.61% | +0.61% |
| kroA150 | +4.89% | +4.89% | +4.89% | +2.55% | +17.30% | +3.39% | +12.97% | +4.69% | +8.61% | +4.39% | +2.55% | +2.55% | +2.55% | +3.34% |
| kroB150 | +3.74% | +3.74% | +3.74% | +0.18% | +21.00% | +3.80% | +20.89% | +3.68% | +4.02% | +0.58% | +1.16% | +2.22% | +0.98% | +0.66% |
| pr152 | +1.89% | +1.89% | +1.89% | +0.18% | +17.96% | +4.33% | +20.15% | +4.33% | +2.33% | +0.82% | +0.18% | +0.46% | +0.18% | +0.34% |
| u159 | +1.52% | +1.52% | +1.52% | +1.46% | +23.60% | +6.96% | +18.79% | +2.90% | +11.80% | +5.07% | +1.52% | +1.50% | +1.46% | +1.50% |
| rat195 | +2.28% | +2.28% | +2.07% | +1.46% | +22.26% | +4.00% | +22.00% | +5.98% | +9.99% | +4.48% | +0.98% | +1.19% | +1.35% | +1.35% |
| d198 | +1.03% | +0.96% | +1.03% | +0.43% | +13.15% | +3.63% | +11.41% | +3.17% | +3.63% | +1.30% | +0.37% | +0.37% | +0.43% | +0.46% |
| kroA200 | +0.79% | +0.74% | +0.79% | +0.38% | +22.70% | +6.40% | +20.34% | +7.40% | +9.45% | +5.03% | +0.49% | +0.43% | +0.38% | +0.40% |
| kroB200 | +2.87% | +2.51% | +2.87% | +1.96% | +24.44% | +3.85% | +20.27% | +4.34% | +7.29% | +3.39% | +1.85% | +1.94% | +1.96% | +1.96% |

### Paired: llm vs control  (difference = llm - control; negative means llm better)

- instances compared: **17**
- mean difference: **-0.09%**
- 95% CI of the mean difference: ±0.14%
- standard deviation of the differences: 0.30%
- llm better on **7**, control better on **6**, ties **4**
- verdict: **inconclusive**

### Paired: llm vs related  (difference = llm - related; negative means llm better)

- instances compared: **17**
- mean difference: **+0.08%**
- 95% CI of the mean difference: ±0.17%
- standard deviation of the differences: 0.36%
- llm better on **6**, related better on **7**, ties **4**
- verdict: **inconclusive**

### Paired: llm vs llm-raw  (difference = llm - llm-raw; negative means llm better)

- instances compared: **17**
- mean difference: **+0.00%**
- 95% CI of the mean difference: ±0.09%
- standard deviation of the differences: 0.18%
- llm better on **6**, llm-raw better on **7**, ties **4**
- verdict: **inconclusive**

### Paired: control vs control-raw  (difference = control - control-raw; negative means control better)

- instances compared: **17**
- mean difference: **-0.01%**
- 95% CI of the mean difference: ±0.23%
- standard deviation of the differences: 0.49%
- control better on **7**, control-raw better on **5**, ties **5**
- verdict: **inconclusive**
