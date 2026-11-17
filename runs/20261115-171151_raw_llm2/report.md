# FunSearch run: 20261115-171151_raw_llm2

- skeleton: `ils` (evolves `destroy_priority`)
- ILS constants: 100 rounds, 10 cities removed per round, 2-opt + Or-opt local search, cheapest-insertion repair
- wall time: 247.4s
- training instances: eil51 (n=51), berlin52 (n=52), st70 (n=70), eil76 (n=76), pr76 (n=76), rat99 (n=99), kroA100 (n=100), kroB100 (n=100), kroC100 (n=100), kroD100 (n=100), kroE100 (n=100), rd100 (n=100)
- islands: 4, k = 2, programs collected: 40, LLM calls: 40
- tokens used: 178850
- billed generation calls: 40, tokens logged per call: 178850, retries: 0
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
| rat99 | 1246 | 1212 | +2.73% |
| kroA100 | 21727 | 21282 | +2.05% |
| kroB100 | 22269 | 22199 | +0.31% |
| kroC100 | 21890 | 20983 | +4.14% |
| kroD100 | 21810 | 21810 | +0.00% |
| kroE100 | 22830 | 22160 | +2.93% |
| rd100 | 7988 | 7910 | +0.98% |

- best score (mean relative improvement): +0.015426
- best program id: 19 (island 0, 1023 chars)

## Validation (held-out, not used for selection)

| instance | n | random-destruction ILS | FunSearch best | improvement |
|---|---|---|---|---|
| eil101 | 101 | 630 | 629 | +0.16% |
| lin105 | 105 | 14580 | 14416 | +1.12% |
| pr107 | 107 | 44438 | 44438 | +0.00% |
| pr124 | 124 | 59764 | 59030 | +1.23% |
| bier127 | 127 | 119519 | 118715 | +0.67% |
| ch130 | 130 | 6259 | 6245 | +0.22% |
| pr136 | 136 | 102992 | 101211 | +1.73% |
| pr144 | 144 | 59286 | 58537 | +1.26% |
| ch150 | 150 | 6574 | 6568 | +0.09% |
| kroA150 | 150 | 27820 | 27200 | +2.23% |
| kroB150 | 150 | 27107 | 26491 | +2.27% |
| pr152 | 152 | 75074 | 73818 | +1.67% |
| u159 | 159 | 42721 | 42693 | +0.07% |
| rat195 | 195 | 2376 | 2342 | +1.43% |
| d198 | 198 | 15932 | 15848 | +0.53% |
| kroA200 | 200 | 29586 | 29481 | +0.35% |
| kroB200 | 200 | 30177 | 30014 | +0.54% |

- mean improvement over the random-destruction ILS on held-out instances: +0.92%

## Validation trajectory (held-out, logged only)

The held-out set was scored each time the *search* score reached a new global best. These numbers were written to this file and never fed back into sampling, island resets or the stopping rule.

| programs collected | attempt | search score | held-out mean |
|---|---|---|---|
| 14 | 14 | +0.0130 | +0.84% |
| 19 | 19 | +0.0154 | +0.92% |

- held-out mean moved from +0.84% to +0.92% across the run (+0.07 points)
- meanwhile the search score moved from +0.0130 to +0.0154 (+0.24 points)

## Convergence

| attempt | island | score | signature | chars |
|---|---|---|---|---|
| 1 | 3 | -0.003911 | (-0.005, -0.001, 0.0, -0.006, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 822 |
| 2 | 1 | -0.003911 | (-0.005, -0.001, 0.0, -0.006, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 1049 |
| 3 | 0 | -0.000609 | (-0.002, -0.001, 0.01, 0.0, 0.0, -0.014, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0) | 799 |
| 4 | 1 | -0.003911 | (-0.005, -0.001, 0.0, -0.006, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 814 |
| 5 | 1 | -0.003911 | (-0.005, -0.001, 0.0, -0.006, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 988 |
| 6 | 2 | -0.000418 | (-0.002, 0.0, 0.0, 0.0, 0.0, -0.014, 0.0, 0.0, 0.0, -0.004, 0.016, 0.0) | 675 |
| 7 | 3 | -0.003911 | (-0.005, -0.001, 0.0, -0.006, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 397 |
| 8 | 0 | -0.001896 | (-0.005, -0.001, 0.0, 0.0, -0.011, -0.014, 0.0, 0.0, 0.0, -0.002, 0.0, 0.01) | 482 |
| 9 | 2 | -0.003452 | (-0.005, -0.001, 0.0, 0.0, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 1012 |
| 10 | 1 | -0.003911 | (-0.005, -0.001, 0.0, -0.006, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 988 |
| 11 | 3 | -0.003911 | (-0.005, -0.001, 0.0, -0.006, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 620 |
| 12 | 2 | -0.003452 | (-0.005, -0.001, 0.0, 0.0, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 885 |
| 13 | 2 | -0.003911 | (-0.005, -0.001, 0.0, -0.006, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 1045 |
| 14 | 3 | +0.013038 | (0.0, 0.003, 0.01, 0.0, 0.012, 0.027, 0.02, 0.003, 0.041, 0.0, 0.029, 0.01) | 518 |
| 15 | 0 | -0.002641 | (-0.005, -0.001, 0.009, -0.006, -0.004, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 1109 |
| 16 | 1 | -0.003911 | (-0.005, -0.001, 0.0, -0.006, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 610 |
| 17 | 1 | -0.003911 | (-0.005, -0.001, 0.0, -0.006, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 1201 |
| 18 | 3 | -0.003363 | (-0.005, -0.001, 0.0, -0.006, -0.004, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 816 |
| 19 | 2 | +0.015426 | (0.0, 0.026, 0.017, 0.0, 0.011, 0.027, 0.02, 0.003, 0.041, 0.0, 0.029, 0.01) | 1024 |
| 20 | 2 | -0.003911 | (-0.005, -0.001, 0.0, -0.006, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 881 |
| 21 | 0 | -0.003911 | (-0.005, -0.001, 0.0, -0.006, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 1013 |
| 22 | 1 | -0.003911 | (-0.005, -0.001, 0.0, -0.006, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 1273 |
| 23 | 0 | -0.003911 | (-0.005, -0.001, 0.0, -0.006, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 691 |
| 24 | 2 | -0.003452 | (-0.005, -0.001, 0.0, 0.0, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 1054 |
| 25 | 2 | +0.015426 | (0.0, 0.026, 0.017, 0.0, 0.011, 0.027, 0.02, 0.003, 0.041, 0.0, 0.029, 0.01) | 882 |
| 26 | 0 | -0.000819 | (-0.002, -0.001, 0.01, 0.0, 0.0, -0.014, 0.0, 0.0, 0.0, -0.003, 0.0, 0.0) | 634 |
| 27 | 2 | +0.015426 | (0.0, 0.026, 0.017, 0.0, 0.011, 0.027, 0.02, 0.003, 0.041, 0.0, 0.029, 0.01) | 740 |
| 28 | 3 | +0.000218 | (-0.002, -0.001, 0.009, 0.0, 0.0, -0.014, 0.0, 0.0, 0.0, -0.004, 0.016, 0.0) | 1064 |
| 29 | 3 | +0.012961 | (0.0, 0.003, 0.01, 0.0, 0.011, 0.027, 0.02, 0.003, 0.041, 0.0, 0.029, 0.01) | 533 |
| 30 | 2 | -0.003452 | (-0.005, -0.001, 0.0, 0.0, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 698 |
| 31 | 2 | -0.003410 | (-0.002, -0.001, 0.0, -0.002, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 707 |
| 32 | 2 | +0.000422 | (-0.002, -0.001, 0.01, -0.006, -0.004, -0.014, 0.0, 0.0, 0.0, 0.003, 0.009, 0.01) | 746 |
| 33 | 0 | +0.015426 | (0.0, 0.026, 0.017, 0.0, 0.011, 0.027, 0.02, 0.003, 0.041, 0.0, 0.029, 0.01) | 695 |
| 34 | 2 | -0.003410 | (-0.002, -0.001, 0.0, -0.002, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 651 |
| 35 | 1 | -0.003911 | (-0.005, -0.001, 0.0, -0.006, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 885 |
| 36 | 3 | -0.001414 | (0.0, 0.0, 0.0, 0.0, 0.0, -0.014, 0.0, 0.0, 0.0, -0.003, 0.0, 0.0) | 985 |
| 37 | 1 | -0.003452 | (-0.005, -0.001, 0.0, 0.0, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 828 |
| 38 | 0 | -0.003452 | (-0.005, -0.001, 0.0, 0.0, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 783 |
| 39 | 1 | -0.003911 | (-0.005, -0.001, 0.0, -0.006, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 1151 |
| 40 | 1 | -0.003452 | (-0.005, -0.001, 0.0, 0.0, -0.011, -0.014, 0.0, 0.0, 0.0, -0.011, 0.0, 0.0) | 983 |

## Islands

- island 0: 3 programs, 2 clusters, best +0.015426
- island 1: 5 programs, 3 clusters, best +0.015426
- island 2: 1 programs, 1 clusters, best +0.015426
- island 3: 1 programs, 1 clusters, best +0.015426

## Island resets

- island 2 re-seeded from island 1 program 0 (score +0.000000)
- island 3 re-seeded from island 1 program 0 (score +0.000000)
- island 0 re-seeded from island 2 program 19 (score +0.015426)
- island 1 re-seeded from island 2 program 19 (score +0.015426)
- island 2 re-seeded from island 0 program 19 (score +0.015426)
- island 3 re-seeded from island 1 program 19 (score +0.015426)

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

    # Normalise the raw-distance features to a comparable scale.
    def z(x):
        m = np.mean(x)
        s = np.std(x) + 1e-9
        return (x - m) / s

    # High saving = removing this city shortens the tour a lot.
    # High gap = city is far from its neighbours relative to the shortcut.
    # Sharp turns (angle near -1) often signal poor local structure.
    score = (
        1.0 * z(saving)
        + 0.8 * z(gap)
        - 0.6 * z(density)
        - 0.4 * z(angle)          # angle near -1 -> positive -> prefer removal
        - 0.5 * related           # related is already ~scaled; cluster removals
        + 0.15 * z(np.abs(pos))   # spread removals across the tour
        + 0.05 * noise            # tie-breaking
    )
    return score
```

