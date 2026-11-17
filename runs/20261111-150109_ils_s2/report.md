# FunSearch run: 20261111-150109_ils_s2

- skeleton: `ils` (evolves `destroy_priority`)
- ILS constants: 100 rounds, 10 cities removed per round, 2-opt + Or-opt local search, cheapest-insertion repair
- wall time: 338.2s
- training instances: eil51 (n=51), berlin52 (n=52), st70 (n=70), eil76 (n=76), pr76 (n=76), rat99 (n=99), kroA100 (n=100), kroB100 (n=100), kroC100 (n=100), kroD100 (n=100), kroE100 (n=100), rd100 (n=100)
- islands: 4, k = 2, programs collected: 40, LLM calls: 40
- tokens used: 177836
- billed generation calls: 40, tokens logged per call: 177836, retries: 0
- of those, 0 call(s) produced code that was already evaluated and cost 0 tokens: the code cache saves the *evaluation*, never the generation
- baseline (random-destruction ILS) tour lengths: eil51=427, berlin52=7741, st70=692, eil76=544, pr76=110356, rat99=1246, kroA100=21727, kroB100=22269, kroC100=21890, kroD100=21810, kroE100=22830, rd100=7988

## Result

| instance | random-destruction ILS | FunSearch best | improvement |
|---|---|---|---|
| eil51 | 427 | 427 | +0.00% |
| berlin52 | 7741 | 7715 | +0.34% |
| st70 | 692 | 680 | +1.73% |
| eil76 | 544 | 544 | +0.00% |
| pr76 | 110356 | 109186 | +1.06% |
| rat99 | 1246 | 1211 | +2.81% |
| kroA100 | 21727 | 21282 | +2.05% |
| kroB100 | 22269 | 22199 | +0.31% |
| kroC100 | 21890 | 20880 | +4.61% |
| kroD100 | 21810 | 21810 | +0.00% |
| kroE100 | 22830 | 22160 | +2.93% |
| rd100 | 7988 | 7910 | +0.98% |

- best score (mean relative improvement): +0.014022
- best program id: 16 (island 0, 1143 chars)

## Validation (held-out, not used for selection)

| instance | n | random-destruction ILS | FunSearch best | improvement |
|---|---|---|---|---|
| eil101 | 101 | 630 | 630 | +0.00% |
| lin105 | 105 | 14580 | 14426 | +1.06% |
| pr107 | 107 | 44438 | 44303 | +0.30% |
| pr124 | 124 | 59764 | 59030 | +1.23% |
| bier127 | 127 | 119519 | 118967 | +0.46% |
| ch130 | 130 | 6259 | 6248 | +0.18% |
| pr136 | 136 | 102992 | 101211 | +1.73% |
| pr144 | 144 | 59286 | 58763 | +0.88% |
| ch150 | 150 | 6574 | 6568 | +0.09% |
| kroA150 | 150 | 27820 | 27200 | +2.23% |
| kroB150 | 150 | 27107 | 26176 | +3.43% |
| pr152 | 152 | 75074 | 73818 | +1.67% |
| u159 | 159 | 42721 | 42721 | +0.00% |
| rat195 | 195 | 2376 | 2349 | +1.14% |
| d198 | 198 | 15932 | 15858 | +0.46% |
| kroA200 | 200 | 29586 | 29507 | +0.27% |
| kroB200 | 200 | 30177 | 29973 | +0.68% |

- mean improvement over the random-destruction ILS on held-out instances: +0.93%

## Validation trajectory (held-out, logged only)

The held-out set was scored each time the *search* score reached a new global best. These numbers were written to this file and never fed back into sampling, island resets or the stopping rule.

| programs collected | attempt | search score | held-out mean |
|---|---|---|---|
| 3 | 3 | +0.0070 | +0.15% |
| 6 | 6 | +0.0105 | +0.46% |
| 11 | 11 | +0.0120 | +0.83% |
| 13 | 13 | +0.0129 | +0.96% |
| 16 | 16 | +0.0140 | +0.93% |

- held-out mean moved from +0.15% to +0.93% across the run (+0.78 points)
- meanwhile the search score moved from +0.0070 to +0.0140 (+0.70 points)

## Convergence

| attempt | island | score | signature | chars |
|---|---|---|---|---|
| 1 | 3 | -0.000227 | (-0.002, -0.001, 0.009, 0.0, 0.011, -0.014, 0.0, 0.0, 0.0, -0.004, 0.0, 0.0) | 1087 |
| 2 | 1 | -0.003314 | (-0.005, -0.001, 0.0, 0.0, -0.011, -0.014, 0.0, 0.0, 0.0, -0.009, 0.0, 0.0) | 1314 |
| 3 | 0 | +0.006974 | (0.0, 0.003, 0.017, 0.0, -0.004, 0.0, 0.016, 0.0, 0.016, 0.0, 0.025, 0.01) | 991 |
| 4 | 1 | -0.002463 | (-0.005, -0.001, 0.0, -0.006, -0.004, -0.014, 0.0, 0.0, 0.0, -0.009, 0.009, 0.0) | 845 |
| 5 | 1 | -0.003226 | (-0.005, -0.001, 0.0, -0.006, -0.004, -0.014, 0.0, 0.0, 0.0, -0.009, 0.0, 0.0) | 437 |
| 6 | 2 | +0.010457 | (0.0, 0.0, 0.01, 0.0, 0.011, 0.012, 0.02, 0.0, 0.046, 0.0, 0.016, 0.01) | 697 |
| 7 | 3 | +0.009450 | (0.0, 0.0, 0.01, 0.0, 0.011, 0.012, 0.016, 0.0, 0.029, 0.0, 0.025, 0.01) | 799 |
| 8 | 0 | +0.006679 | (-0.002, 0.0, 0.016, 0.0, 0.011, -0.014, 0.019, 0.0, 0.016, 0.0, 0.025, 0.01) | 1245 |
| 9 | 2 | +0.000831 | (-0.002, -0.001, 0.009, 0.0, -0.011, -0.014, 0.0, 0.0, 0.016, -0.003, 0.016, 0.0) | 959 |
| 10 | 1 | -0.002015 | (0.0, 0.003, 0.0, 0.0, -0.011, -0.014, 0.0, 0.0, 0.0, -0.003, 0.0, 0.0) | 1202 |
| 11 | 3 | +0.012019 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.019, 0.003, 0.029, 0.0, 0.023, 0.01) | 1141 |
| 12 | 2 | +0.011585 | (0.0, 0.0, 0.017, 0.0, 0.011, 0.027, 0.016, 0.003, 0.029, 0.0, 0.025, 0.01) | 977 |
| 13 | 2 | +0.012924 | (0.0, 0.0, 0.017, 0.0, 0.011, 0.028, 0.011, 0.003, 0.046, 0.0, 0.029, 0.01) | 1067 |
| 14 | 3 | +0.005256 | (-0.002, 0.003, 0.01, 0.0, -0.004, -0.014, 0.019, 0.0, 0.016, 0.0, 0.025, 0.01) | 1321 |
| 15 | 2 | +0.010721 | (0.0, 0.0, 0.01, 0.0, 0.011, 0.027, 0.016, 0.0, 0.029, 0.0, 0.025, 0.01) | 1003 |
| 16 | 0 | +0.014022 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.02, 0.003, 0.046, 0.0, 0.029, 0.01) | 1144 |
| 17 | 1 | +0.013204 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.011, 0.003, 0.046, 0.0, 0.029, 0.01) | 1012 |
| 18 | 3 | +0.011388 | (0.0, 0.0, 0.017, 0.0, 0.011, 0.027, 0.016, 0.003, 0.029, 0.0, 0.023, 0.01) | 865 |
| 19 | 2 | +0.011585 | (0.0, 0.0, 0.017, 0.0, 0.011, 0.027, 0.016, 0.003, 0.029, 0.0, 0.025, 0.01) | 875 |
| 20 | 2 | -0.002586 | (-0.005, -0.001, 0.0, -0.002, 0.0, -0.014, 0.0, 0.0, 0.0, -0.009, 0.0, 0.0) | 919 |
| 21 | 0 | +0.013028 | (0.0, 0.003, 0.01, 0.0, 0.011, 0.028, 0.02, 0.003, 0.041, 0.0, 0.029, 0.01) | 939 |
| 22 | 1 | +0.013038 | (0.0, 0.003, 0.01, 0.0, 0.012, 0.027, 0.02, 0.003, 0.041, 0.0, 0.029, 0.01) | 886 |
| 23 | 0 | +0.014022 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.02, 0.003, 0.046, 0.0, 0.029, 0.01) | 846 |
| 24 | 2 | +0.009450 | (0.0, 0.0, 0.01, 0.0, 0.011, 0.012, 0.016, 0.0, 0.029, 0.0, 0.025, 0.01) | 936 |
| 25 | 2 | -0.003911 | (-0.005, -0.001, 0.0, -0.006, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 1113 |
| 26 | 2 | +0.011952 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.027, 0.019, 0.003, 0.029, 0.0, 0.023, 0.01) | 938 |
| 27 | 3 | +0.013204 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.011, 0.003, 0.046, 0.0, 0.029, 0.01) | 1006 |
| 28 | 2 | +0.014022 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.02, 0.003, 0.046, 0.0, 0.029, 0.01) | 934 |
| 29 | 0 | -0.003381 | (-0.005, 0.0, 0.0, -0.002, -0.011, -0.014, 0.0, 0.0, 0.0, -0.009, 0.0, 0.0) | 968 |
| 30 | 3 | +0.014022 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.02, 0.003, 0.046, 0.0, 0.029, 0.01) | 888 |
| 31 | 0 | -0.002586 | (-0.005, -0.001, 0.0, -0.002, 0.0, -0.014, 0.0, 0.0, 0.0, -0.009, 0.0, 0.0) | 893 |
| 32 | 0 | +0.011672 | (0.0, 0.0, 0.017, 0.0, 0.011, 0.027, 0.019, 0.003, 0.029, 0.0, 0.023, 0.01) | 1000 |
| 33 | 1 | +0.012019 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.019, 0.003, 0.029, 0.0, 0.023, 0.01) | 1023 |
| 34 | 3 | +0.014022 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.02, 0.003, 0.046, 0.0, 0.029, 0.01) | 1025 |
| 35 | 2 | +0.013028 | (0.0, 0.003, 0.01, 0.0, 0.011, 0.028, 0.02, 0.003, 0.041, 0.0, 0.029, 0.01) | 969 |
| 36 | 3 | +0.013657 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.02, 0.003, 0.046, 0.0, 0.025, 0.01) | 933 |
| 37 | 1 | +0.013518 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.019, 0.003, 0.046, 0.0, 0.024, 0.01) | 950 |
| 38 | 3 | +0.012873 | (0.0, 0.003, 0.017, 0.0, 0.012, 0.027, 0.011, 0.003, 0.041, 0.0, 0.029, 0.01) | 840 |
| 39 | 2 | +0.013630 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.02, 0.003, 0.041, 0.0, 0.029, 0.01) | 858 |
| 40 | 0 | +0.013204 | (0.0, 0.003, 0.017, 0.0, 0.011, 0.028, 0.011, 0.003, 0.046, 0.0, 0.029, 0.01) | 1023 |

## Islands

- island 0: 8 programs, 7 clusters, best +0.014022
- island 1: 1 programs, 1 clusters, best +0.014022
- island 2: 4 programs, 4 clusters, best +0.014022
- island 3: 1 programs, 1 clusters, best +0.014022

## Island resets

- island 0 re-seeded from island 3 program 11 (score +0.012019)
- island 1 re-seeded from island 3 program 11 (score +0.012019)
- island 2 re-seeded from island 1 program 17 (score +0.013204)
- island 3 re-seeded from island 1 program 17 (score +0.013204)
- island 3 re-seeded from island 2 program 28 (score +0.014022)
- island 1 re-seeded from island 0 program 16 (score +0.014022)

## Failure statistics

- attempts: 40, new programs stored: 40, duplicates: 0, rejected/failed: 0

## Best program

```python
def destroy_priority(features):
    import numpy as np
    gap = features["gap"]
    saving = features["saving"]
    related = features["related"]
    density = features["density"]
    angle = features["angle"]
    pos = features["pos"]
    noise = features["noise"]

    # Worst-removal: high saving means a big detour that repair can shortcut.
    # Related removal: small `related` (close to seed) is the target region;
    # `1 - related` rewards proximity so a coherent cluster is destroyed.
    score = 1.0 * saving + 0.8 * (1.0 - related)

    # Awkward nodes in the tour: high gap (long detour vs shortcut).
    score = score + 0.30 * (gap - 1.0)

    # Sharp turns (low cos) are strong candidates for reordering.
    score = score - 0.15 * angle

    # Cities in sparse regions have more freedom when reinserted.
    score = score - 0.12 * density

    # Spread removals along the tour rather than dumping them into one gap:
    # use |pos| around the seed to reach both sides of the cycle.
    score = score + 0.20 * np.abs(pos)

    # Deterministic tie-break, small so it never overrides real signal.
    return score + 1e-3 * noise
```

