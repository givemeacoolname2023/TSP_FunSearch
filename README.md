# FunSearch for the Travelling Salesman Problem

Applying FunSearch to TSP. A standard iterated-local-search (ILS) skeleton is **frozen** — nearest-neighbour construction, 2-opt/Or-opt local search, cheapest-insertion repair, 100 destroy/repair rounds with k = 10 — and only the function that decides **which cities the destroy step removes** (`destroy_priority(features)`) is evolved by an LLM.

The project compares 14 methods on three disjoint TSPLIB splits: three insertion constructors (with and without local search), nearest neighbour + local search, three hand-written destroy operators, the LLM-evolved operator (3 seeds), a same-budget random-weight control (3 seeds), and the raw-distance variants of the last two.

**Headline result (final split, 13 instances of 225–493 cities, mean gap to the published optimum):**

| method                                 | mean gap          |
| -------------------------------------- | ----------------- |
| constructors + local search            | 5.3–5.8 %         |
| nearest neighbour + local search       | 3.54 %            |
| ILS, random destruction (seed program) | 3.36 %            |
| ILS, worst removal                     | 2.86 %            |
| ILS, related removal                   | 2.27 %            |
| **ILS, evolved operator (3 seeds)**    | **2.31 % ± 0.17** |
| ILS, random-weight control (3 seeds)   | 2.12 % ± 0.24     |

The evolved operator beats random destruction by about one gap point, but is statistically indistinguishable from the strongest hand-written operator and from a random search over the same features at the same budget.

## Environment

```
Python 3.9+         (tested on 3.9.13)
numpy 1.26.4, requests 2.25+, matplotlib 3.5+
```

```powershell
pip install -r requirements.txt
```

Only the LLM search calls a paid API. Everything else (baselines, evaluation,tables, figures) runs offline.

## Quick start (no API key needed)

```powershell
python -m funsearch_tsp.run --skeleton ils --mock --n-programs 5 --train eil51
```

`--mock` replaces the LLM with a deterministic stand-in, so this verifies the
installation in a few seconds and costs nothing. It writes a run directory under
`runs/`.

## Reproducing every result in the report

Set the key first (only steps 2 and 4 need it):

```powershell
copy .env.example .env      # then put your DEEPSEEK_API_KEY into .env
```

| #    | What                           | Command                                                      | Output                               | Time / cost                    |
| ---- | ------------------------------ | ------------------------------------------------------------ | ------------------------------------ | ------------------------------ |
| 1    | 10 baselines × 3 splits        | `python tools\eval_baselines.py --group search validation final --work-dir runs\baselines` | `runs\baselines\<split>\*.csv`       | ~15 min, free                  |
| 2    | LLM operator, 3 seeds          | `python -m funsearch_tsp.run --skeleton ils --n-programs 40 --seed 0 --tag ils_s0` (repeat for seeds 1, 2) | `runs\<ts>_ils_s<k>\best_destroy.py` | 397 s and 174k tokens per seed |
| 3    | Random-weight control, 3 seeds | same, plus `--sampler random-linear`                         | same layout                          | ~2.5 min per seed, **free**    |
| 4    | Raw-distance variants          | steps 2–3 plus `--features-scale raw`                        | same layout                          | as above                       |
| 5    | Score a program on one split   | `python -m funsearch_tsp.solve --program runs\<ts>_ils_s0\best_destroy.py --group final --csv runs\<ts>_ils_s0\final.csv` | `<split>.csv`                        | 10–70 s                        |
| 6    | **The three summary tables**   | `python tools\make_tables.py`                                | `runs\summary_<split>.md`            | seconds                        |
| 7    | **The figures**                | `python tools\plot_figures.py`                               | `runs\figures\*.png`                 | seconds                        |
| 8    | Work / budget table            | `python tools\measure_work.py`                               | `runs\table_work.md`                 | ~1 min                         |

Reproducing the full study costs about **1.1M tokens** (six LLM runs) and roughly **45 minutes** of CPU time; everything except steps 2 and 4 is free.

`runs/` is not committed (it holds run artefacts). Regenerate it with the commands above — steps 6–8 only read the CSVs, so they always agree with whatever is in `runs/`.

## Repository layout

```
funsearch_tsp/
  run.py                 search loop: islands, Boltzmann sampling, candidate loop
  skeleton_ils.py        frozen ILS skeleton, the 7 features, 3 built-in operators
  skeleton.py            stage-1 greedy skeleton (kept for the ablation history)
  construct.py           3 insertion constructors, with and without local search
  skeletons.py           skeleton registry
  evaluate.py            scoring (improvement over the seed program)
  sandbox.py             subprocess sandbox + code-hash result cache
  prompt.py              prompt construction
  llm.py                 DeepSeek client / random-weight sampler / mock sampler
  programs_database.py   islands and signature clusters
  tsp.py                 TSPLIB parser (EUC_2D only)
  solve.py               evaluate one program or one baseline on a split
tools/
  build_dataset.py       select TSPLIB instances and freeze the splits
  eval_baselines.py      run the 10 baselines over one or more splits
  make_tables.py         summary_<split>.md from the CSVs
  plot_figures.py        convergence / improvement ladder / paired scatter
  measure_work.py        per-method work accounting (budget matching)
tsp_files/               63 TSPLIB instances (EUC_2D) + data/split.json
```

## Data

63 symmetric TSPLIB instances, **0.8 MB total**, committed directly — no download script is needed. Only instances declaring `EDGE_WEIGHT_TYPE : EUC_2D` are accepted; any other convention raises an error instead of being mis-evaluated.

The splits in `tsp_files/data/split.json` are frozen before any search:

| split      | instances | cities  | used for                                    |
| ---------- | --------- | ------- | ------------------------------------------- |
| search     | 12        | 51–100  | selecting the program inside the search     |
| validation | 17        | 101–200 | never used for selection                    |
| final      | 13        | 225–493 | evaluated once, after all searches finished |

## Things that are easy to misread

* **Two different `k`.** `--k 2` is how many parent programs each island samples per generation; the ILS constant `k = 10` is how many cities the destroy step removes. `report.md` prints the former (`islands: 4, k = 2`).
* **Three kinds of "seed".** `--seed` controls the search trajectory (three seeds mean three independent searches producing three different programs); the evaluation itself uses a fixed internal seed, so a given program always produces the same tours; and the *seed program* is the trivial `return features["noise"]` operator that FunSearch starts from and that defines score 0.
* **Caching.** The code-hash cache removes repeated *execution*, never a repeated *generation* — a duplicate program still costs one API call, which is logged.

