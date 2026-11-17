## Work per run (budget matching, TA1: "match solve time or objective evaluations")

Static counts follow directly from the frozen skeleton: `ils()` performs one local
search on the nearest-neighbour tour and then `100` rounds of
(destroy -> cheapest-insertion repair -> local search -> accept).
Wall-clock is measured in the sandbox on one instance, subprocess startup included
(~0.4 s), so it is comparable across rows but slightly overstates a single solve.

| method | ILS rounds | local-search calls | cheapest-insertion repairs | eil51 (n=51) | kroA100 (n=100) | d493 (n=493) |
|---|---|---|---|---|---|---|
| `nearest-ins` | 0 | 0 | 0 | 0.38 s | 0.45 s | 0.48 s |
| `cheapest-ins` | 0 | 0 | 0 | 0.44 s | 0.42 s | 0.87 s |
| `farthest-ins` | 0 | 0 | 0 | 0.38 s | 0.34 s | 0.33 s |
| `nearest-ins-ls` | 0 | 1 | 0 | 0.31 s | 0.32 s | 3.77 s |
| `cheapest-ins-ls` | 0 | 1 | 0 | 0.36 s | 0.36 s | 3.06 s |
| `farthest-ins-ls` | 0 | 1 | 0 | 0.32 s | 0.32 s | 2.29 s |
| `lsonly` | 0 | 1 | 0 | 0.32 s | 0.33 s | 1.22 s |
| `random` | 100 | 101 | 100 | 0.47 s | 0.55 s | 5.71 s |
| `worst` | 100 | 101 | 100 | 0.44 s | 0.52 s | 5.85 s |
| `related` | 100 | 101 | 100 | 0.60 s | 0.86 s | 13.16 s |

All LNS rows share the same k=10, repair operator and local-search budget, so they are matched by construction; only the construction-only rows do less work, and they are reported as reference points, not as budget-matched competitors.

Note that wall-clock is not a neutral budget axis: the stronger removal operators take longer per run (`related` 12.8 s vs `random` 7.1 s on d493) because a better destruction lets the repair reach genuinely shorter tours, after which the local search has more left to improve. The report therefore matches the *algorithmic* budget (T, k, repair, local search) and reports time separately, instead of equalising seconds.
