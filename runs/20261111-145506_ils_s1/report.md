# FunSearch run: 20261111-145506_ils_s1

- skeleton: `ils` (evolves `destroy_priority`)
- ILS constants: 100 rounds, 10 cities removed per round, 2-opt + Or-opt local search, cheapest-insertion repair
- wall time: 361.8s
- training instances: eil51 (n=51), berlin52 (n=52), st70 (n=70), eil76 (n=76), pr76 (n=76), rat99 (n=99), kroA100 (n=100), kroB100 (n=100), kroC100 (n=100), kroD100 (n=100), kroE100 (n=100), rd100 (n=100)
- islands: 4, k = 2, programs collected: 40, LLM calls: 40
- tokens used: 179566
- billed generation calls: 40, tokens logged per call: 179566, retries: 0
- of those, 0 call(s) produced code that was already evaluated and cost 0 tokens: the code cache saves the *evaluation*, never the generation
- baseline (random-destruction ILS) tour lengths: eil51=427, berlin52=7741, st70=692, eil76=544, pr76=110356, rat99=1246, kroA100=21727, kroB100=22269, kroC100=21890, kroD100=21810, kroE100=22830, rd100=7988

## Result

| instance | random-destruction ILS | FunSearch best | improvement |
|---|---|---|---|
| eil51 | 427 | 427 | +0.00% |
| berlin52 | 7741 | 7542 | +2.57% |
| st70 | 692 | 680 | +1.73% |
| eil76 | 544 | 544 | +0.00% |
| pr76 | 110356 | 109186 | +1.06% |
| rat99 | 1246 | 1211 | +2.81% |
| kroA100 | 21727 | 21282 | +2.05% |
| kroB100 | 22269 | 22199 | +0.31% |
| kroC100 | 21890 | 20983 | +4.14% |
| kroD100 | 21810 | 21810 | +0.00% |
| kroE100 | 22830 | 22174 | +2.87% |
| rd100 | 7988 | 7910 | +0.98% |

- best score (mean relative improvement): +0.015442
- best program id: 30 (island 1, 975 chars)

## Validation (held-out, not used for selection)

| instance | n | random-destruction ILS | FunSearch best | improvement |
|---|---|---|---|---|
| eil101 | 101 | 630 | 629 | +0.16% |
| lin105 | 105 | 14580 | 14379 | +1.38% |
| pr107 | 107 | 44438 | 44303 | +0.30% |
| pr124 | 124 | 59764 | 59030 | +1.23% |
| bier127 | 127 | 119519 | 118967 | +0.46% |
| ch130 | 130 | 6259 | 6248 | +0.18% |
| pr136 | 136 | 102992 | 101211 | +1.73% |
| pr144 | 144 | 59286 | 58763 | +0.88% |
| ch150 | 150 | 6574 | 6568 | +0.09% |
| kroA150 | 150 | 27820 | 27200 | +2.23% |
| kroB150 | 150 | 27107 | 26382 | +2.67% |
| pr152 | 152 | 75074 | 73818 | +1.67% |
| u159 | 159 | 42721 | 42721 | +0.00% |
| rat195 | 195 | 2376 | 2339 | +1.56% |
| d198 | 198 | 15932 | 15854 | +0.49% |
| kroA200 | 200 | 29586 | 29523 | +0.21% |
| kroB200 | 200 | 30177 | 30038 | +0.46% |

- mean improvement over the random-destruction ILS on held-out instances: +0.92%

## Validation trajectory (held-out, logged only)

The held-out set was scored each time the *search* score reached a new global best. These numbers were written to this file and never fed back into sampling, island resets or the stopping rule.

| programs collected | attempt | search score | held-out mean |
|---|---|---|---|
| 2 | 2 | +0.0004 | -0.11% |
| 3 | 3 | +0.0064 | +0.08% |
| 6 | 6 | +0.0091 | +0.47% |
| 7 | 7 | +0.0095 | +0.43% |
| 10 | 10 | +0.0136 | +0.84% |
| 30 | 30 | +0.0154 | +0.92% |

- held-out mean moved from -0.11% to +0.92% across the run (+1.03 points)
- meanwhile the search score moved from +0.0004 to +0.0154 (+1.51 points)

## Convergence

| attempt | island | score | signature | chars |
|---|---|---|---|---|
| 1 | 1 | -0.002761 | (-0.005, -0.001, 0.007, -0.006, -0.004, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 721 |
| 2 | 2 | +0.000382 | (-0.002, -0.001, 0.01, -0.006, -0.004, -0.002, 0.0, 0.0, 0.0, -0.009, 0.009, 0.01) | 442 |
| 3 | 3 | +0.006383 | (0.0, 0.0, 0.017, 0.0, 0.011, 0.0, 0.0, 0.0, 0.016, 0.0, 0.023, 0.01) | 1405 |
| 4 | 3 | +0.001604 | (0.0, 0.0, 0.009, 0.0, 0.011, -0.014, 0.0, 0.0, 0.0, -0.002, 0.016, 0.0) | 1278 |
| 5 | 0 | -0.002899 | (-0.005, -0.001, 0.0, 0.0, -0.011, -0.014, 0.0, 0.0, 0.0, -0.004, 0.0, 0.0) | 1250 |
| 6 | 1 | +0.009116 | (0.0, -0.001, 0.01, 0.0, 0.011, 0.019, 0.019, 0.0, 0.016, 0.0, 0.025, 0.01) | 946 |
| 7 | 1 | +0.009482 | (0.0, 0.003, 0.01, 0.0, 0.011, 0.019, 0.019, 0.0, 0.016, 0.0, 0.025, 0.01) | 931 |
| 8 | 1 | -0.003452 | (-0.005, -0.001, 0.0, 0.0, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 820 |
| 9 | 3 | +0.002287 | (0.0, 0.0, 0.017, 0.0, 0.011, -0.014, 0.0, 0.0, 0.0, -0.003, 0.016, 0.0) | 1255 |
| 10 | 1 | +0.013579 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.02, 0.003, 0.041, 0.0, 0.029, 0.01) | 1046 |
| 11 | 1 | +0.010403 | (0.0, 0.0, 0.01, 0.0, 0.011, 0.027, 0.019, 0.003, 0.016, 0.0, 0.029, 0.01) | 1122 |
| 12 | 1 | +0.012812 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.011, 0.003, 0.041, 0.0, 0.029, 0.01) | 947 |
| 13 | 1 | +0.013579 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.02, 0.003, 0.041, 0.0, 0.029, 0.01) | 851 |
| 14 | 2 | +0.011140 | (0.0, 0.003, 0.01, 0.0, 0.011, 0.027, 0.019, 0.003, 0.029, -0.003, 0.023, 0.01) | 1160 |
| 15 | 1 | +0.012419 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.027, 0.019, 0.003, 0.029, 0.0, 0.029, 0.01) | 969 |
| 16 | 2 | +0.012934 | (0.0, 0.0, 0.017, 0.0, 0.011, 0.028, 0.02, 0.003, 0.041, 0.0, 0.024, 0.01) | 942 |
| 17 | 1 | +0.012019 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.019, 0.003, 0.029, 0.0, 0.023, 0.01) | 897 |
| 18 | 2 | +0.013265 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.02, 0.003, 0.041, 0.0, 0.025, 0.01) | 946 |
| 19 | 2 | +0.011081 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.019, 0.003, 0.016, 0.0, 0.025, 0.01) | 950 |
| 20 | 2 | +0.013579 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.02, 0.003, 0.041, 0.0, 0.029, 0.01) | 838 |
| 21 | 0 | +0.012019 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.019, 0.003, 0.029, 0.0, 0.023, 0.01) | 879 |
| 22 | 2 | +0.013579 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.02, 0.003, 0.041, 0.0, 0.029, 0.01) | 799 |
| 23 | 3 | +0.000086 | (0.0, -0.001, 0.009, 0.0, -0.004, -0.014, 0.0, 0.0, 0.0, -0.004, 0.016, 0.0) | 971 |
| 24 | 3 | +0.006383 | (0.0, 0.0, 0.017, 0.0, 0.011, 0.0, 0.0, 0.0, 0.016, 0.0, 0.023, 0.01) | 604 |
| 25 | 3 | +0.002888 | (0.0, 0.0, 0.01, 0.0, 0.011, 0.0, 0.0, 0.0, 0.0, -0.003, 0.016, 0.0) | 876 |
| 26 | 0 | +0.013265 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.02, 0.003, 0.041, 0.0, 0.025, 0.01) | 858 |
| 27 | 2 | +0.013579 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.02, 0.003, 0.041, 0.0, 0.029, 0.01) | 952 |
| 28 | 1 | +0.012419 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.027, 0.019, 0.003, 0.029, 0.0, 0.029, 0.01) | 853 |
| 29 | 1 | +0.013265 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.02, 0.003, 0.041, 0.0, 0.025, 0.01) | 888 |
| 30 | 2 | +0.015442 | (0.0, 0.026, 0.017, 0.0, 0.011, 0.028, 0.02, 0.003, 0.041, 0.0, 0.029, 0.01) | 976 |
| 31 | 3 | +0.010673 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.011, 0.003, 0.016, 0.0, 0.029, 0.01) | 745 |
| 32 | 0 | +0.013214 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.02, 0.003, 0.041, 0.0, 0.024, 0.01) | 978 |
| 33 | 3 | +0.011350 | (0.0, 0.003, 0.01, 0.0, 0.011, 0.027, 0.019, 0.003, 0.029, 0.0, 0.023, 0.01) | 932 |
| 34 | 1 | +0.013579 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.02, 0.003, 0.041, 0.0, 0.029, 0.01) | 922 |
| 35 | 3 | +0.010537 | (0.0, 0.0, 0.017, 0.0, 0.011, 0.027, 0.019, 0.003, 0.016, 0.0, 0.023, 0.01) | 944 |
| 36 | 3 | -0.003911 | (-0.005, -0.001, 0.0, -0.006, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 975 |
| 37 | 3 | +0.013302 | (0.0, 0.026, 0.017, 0.0, 0.011, 0.028, 0.02, 0.003, 0.016, 0.0, 0.029, 0.01) | 895 |
| 38 | 0 | +0.012149 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.027, 0.019, 0.003, 0.029, 0.0, 0.025, 0.01) | 921 |
| 39 | 0 | +0.013579 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.02, 0.003, 0.041, 0.0, 0.029, 0.01) | 872 |
| 40 | 0 | +0.011952 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.027, 0.019, 0.003, 0.029, 0.0, 0.023, 0.01) | 954 |

## Islands

- island 0: 7 programs, 6 clusters, best +0.013579
- island 1: 1 programs, 1 clusters, best +0.015442
- island 2: 3 programs, 2 clusters, best +0.015442
- island 3: 1 programs, 1 clusters, best +0.013579

## Island resets

- island 2 re-seeded from island 1 program 10 (score +0.013579)
- island 0 re-seeded from island 1 program 10 (score +0.013579)
- island 2 re-seeded from island 0 program 10 (score +0.013579)
- island 3 re-seeded from island 0 program 10 (score +0.013579)
- island 1 re-seeded from island 2 program 30 (score +0.015442)
- island 3 re-seeded from island 0 program 10 (score +0.013579)

## Failure statistics

- attempts: 40, new programs stored: 40, duplicates: 0, rejected/failed: 0

## Best program

```python
def destroy_priority(features):
    gap = features["gap"]
    saving = features["saving"]
    related = features["related"]
    density = features["density"]
    angle = features["angle"]
    pos = features["pos"]
    noise = features["noise"]

    # Worst removal: cities contributing most extra length.
    worst = 0.7 * saving + 0.3 * (gap - 1.0)

    # Related removal: tear out a coherent spatial region around the seed.
    cluster = -1.1 * related

    # Break sharp U-turns (angle near -1) left over from construction / LS.
    turn = 0.5 * (1.0 - angle)

    # Sparse cities reinsert easily; dense ones are harder and less useful.
    sparse = 0.3 * density

    # Encourage spreading along the tour so repair can rebuild a region,
    # with mild locality so removals stay coherent.
    spread = 0.2 * pos

    # Tie-break jitter keeps removal sets from being deterministically stuck.
    tie = 0.1 * noise

    return worst + cluster + turn + sparse + spread + tie
```

