"""FunSearch main loop for TSP.

    python -m funsearch_tsp.run --mock --n-programs 20          # offline demo
    python -m funsearch_tsp.run --n-programs 40                 # real DeepSeek calls

Each iteration samples an island, samples k programs from it, builds a
best-shot prompt, asks the LLM for a new `priority`, validates it statically,
executes it in a subprocess, scores it on the training instances, and stores it
in the island it came from. The worst half of the islands is periodically
wiped and re-seeded from the best surviving island.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from . import evaluate, llm, sandbox, skeleton, skeleton_ils, skeletons, tsp
from .prompt import build_prompt, extract_priority
from .programs_database import Program, ProgramsDatabase

RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"

#: The frozen split written by ``tools/build_dataset.py``. When it exists it
#: decides which instances train and which are held out, so a run cannot
#: accidentally overlap the two groups.
SPLIT_JSON = Path(__file__).resolve().parent.parent / "tsp_files" / "data" / "split.json"


def split_defaults():
    """Return ``(train, validation)`` from the frozen split, or ``(None, None)``."""
    if not SPLIT_JSON.exists():
        return None, None
    try:
        data = json.loads(SPLIT_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, None
    train = [n for n in data.get("search", []) if n]
    validation = [n for n in data.get("validation", []) if n]
    return (train or None), (validation or None)


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m funsearch_tsp.run",
        description="FunSearch for TSP: evolve a greedy priority function with an LLM.",
    )
    parser.add_argument("--skeleton", choices=skeletons.names(), default=skeletons.DEFAULT,
                        help="which frozen skeleton to search on: 'ils' (default, the main "
                             "experiment: evolve destroy_priority inside iterated local search) "
                             "or 'greedy' (the preliminary construction baseline: evolve priority)")
    parser.add_argument("--features", nargs="+", default=None,
                        help="subset of the frozen feature set to expose to the evolved "
                             "program (default: all of gap saving related density angle pos "
                             "noise). Used for feature ablation; 'noise' is always kept")
    parser.add_argument("--features-scale", choices=["free", "raw"], default="free",
                        help="'free' (default) divides the distance-like features by the "
                             "average edge length d_bar, making them scale-free; 'raw' keeps "
                             "raw distance units, which is the ablation that tests whether "
                             "scale-free features help cross-scale transfer")
    parser.add_argument("--train", nargs="+", default=None,
                        help="training instances (names in tsp_files/ or paths); "
                             "default: the `search` group of tsp_files/data/split.json")
    parser.add_argument("--validation", nargs="+", default=None,
                        help="held-out instances scored once for the best program "
                             "(never used for selection); default: the `validation` group")
    parser.add_argument("--validation-trace", dest="validation_trace",
                        action="store_true", default=True,
                        help="also score the held-out set whenever a new global best "
                             "appears (logged only; the scores never feed back into "
                             "sampling, resetting or stopping)")
    parser.add_argument("--no-validation-trace", dest="validation_trace",
                        action="store_false",
                        help="disable the held-out trace; the final held-out table is "
                             "still produced")
    parser.add_argument("--data-dir", default=None, help="directory holding the .tsp files")
    parser.add_argument("--islands", type=int, default=4, help="number of islands (m)")
    parser.add_argument("--n-programs", type=int, default=40,
                        help="number of successfully evaluated programs to collect")
    parser.add_argument("--max-attempts", type=int, default=None,
                        help="hard cap on LLM calls (default 3 * n-programs + 10)")
    parser.add_argument("--k", type=int, default=2, help="programs per prompt (k in the paper)")
    parser.add_argument("--time-budget", type=float, default=1800.0, help="wall-clock seconds")
    parser.add_argument("--eval-timeout", type=float, default=30.0,
                        help="per-program evaluation timeout in seconds")
    parser.add_argument("--seed", type=int, default=0, help="RNG seed")
    parser.add_argument("--reset-every", type=int, default=None,
                        help="reset the worst half every N new programs (default n_programs // 3)")
    parser.add_argument("--t-cluster", type=float, default=0.1, help="cluster temperature T0")
    parser.add_argument("--t-program", type=float, default=0.1, help="program-length temperature")
    parser.add_argument("--temperature", type=float, default=1.0, help="LLM sampling temperature")
    parser.add_argument("--max-tokens", type=int, default=1600)
    parser.add_argument("--sampler", choices=["llm", "random-linear"], default="llm",
                        help="'llm' (default) asks the model for the next program; "
                             "'random-linear' is the control group: same budget, same feature "
                             "space, but the weights of the linear combination are drawn at "
                             "random, so any gain of the LLM run over it is attributable to the "
                             "search direction rather than to trying N candidates")
    parser.add_argument("--thinking", choices=["off", "on"], default="off",
                        help="'off' (default) sends thinking={'type': 'disabled'}; required for "
                             "reasoning models such as deepseek-flash, which otherwise spend the "
                             "whole output budget on reasoning and return no code")
    parser.add_argument("--model", default=None, help="model name (default $DEEPSEEK_MODEL)")
    parser.add_argument("--base-url", default=None, help="OpenAI-compatible base URL")
    parser.add_argument("--mock", action="store_true", help="offline mock LLM (no API key needed)")
    parser.add_argument("--env-file", default=".env", help="path to the .env file with the API key")
    parser.add_argument("--run-dir", default=None, help="output directory (default runs/<timestamp>)")
    parser.add_argument("--tag", default=None, help="short label used in the run directory name")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    if args.train is None or args.validation is None:
        train_default, validation_default = split_defaults()
        if args.train is None:
            args.train = train_default or list(evaluate.TRAIN_DEFAULT)
        if args.validation is None:
            args.validation = validation_default
    return args


def make_llm(args: argparse.Namespace):
    if args.mock:
        return llm.MockLLM(verbose=not args.quiet, skeleton=args.skeleton,
                           features=args.features)
    if args.sampler == "random-linear":
        return llm.RandomLinearSampler(
            skeleton=args.skeleton, seed=args.seed, verbose=not args.quiet,
            features=args.features)
    llm.load_env_file(args.env_file)
    model = args.model or os.environ.get("DEEPSEEK_MODEL") or llm.DEFAULT_MODEL
    base_url = args.base_url or os.environ.get("DEEPSEEK_BASE_URL") or llm.DEFAULT_BASE_URL
    extra_body = {} if args.thinking == "on" else {"thinking": {"type": "disabled"}}
    return llm.ChatLLM(
        model=model,
        base_url=base_url,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        verbose=not args.quiet,
        extra_body=extra_body,
    )


def usage_fields(client) -> dict:
    """Billing/retry fields for one generation call (TA: log every billed token)."""
    usage = getattr(client, "last_usage", None) or {}
    return {
        "tokens": int(usage.get("total_tokens", 0) or 0),
        "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
        "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
        "retries": int(getattr(client, "last_retries", 0) or 0),
    }


def prepare_run_dir(args: argparse.Namespace) -> Path:
    if args.run_dir:
        run_dir = Path(args.run_dir)
    else:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        tag = args.tag or ("mock" if args.mock else "llm")
        run_dir = RUNS_DIR / ("%s_%s" % (stamp, tag))
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_report(
    path: Path,
    args: argparse.Namespace,
    run_dir: Path,
    instances,
    baseline: dict,
    seed_eval,
    best: Optional[Program],
    attempts: List[dict],
    db: ProgramsDatabase,
    started: float,
    llm_client,
    validation_rows: Optional[List[dict]] = None,
    validation_trace: Optional[List[dict]] = None,
    skel=None,
) -> None:
    """Render ``report.md``. ``skel`` decides how the baseline is labelled."""
    skel = skel if skel is not None else skeleton
    is_ils = getattr(skel, "NAME", "greedy") == "ils"
    base_label = "random-destruction ILS" if is_ils else "nearest neighbour"
    wall = time.time() - started
    ok_attempts = [a for a in attempts if a["ok"] and not a.get("duplicate")]
    duplicates = [a for a in attempts if a.get("duplicate")]
    lines = []  # type: List[str]
    lines.append("# FunSearch run: %s" % (run_dir.name,))
    lines.append("")
    lines.append("- skeleton: `%s` (evolves `%s`)" % (skel.NAME, skel.EVOLVED_NAME))
    if is_ils:
        lines.append("- ILS constants: %d rounds, %d cities removed per round, "
                     "2-opt + Or-opt local search, cheapest-insertion repair"
                     % (skeleton_ils.DEFAULT_ITERATIONS, skeleton_ils.DEFAULT_K))
    lines.append("- wall time: %.1fs" % (wall,))
    lines.append("- training instances: %s" % (", ".join("%s (n=%d)" % (i.name, i.n) for i in instances),))
    lines.append("- islands: %d, k = %d, programs collected: %d, LLM calls: %d"
                 % (db.num_islands, db.num_sampled, len(ok_attempts), getattr(llm_client, "total_calls", 0)))
    if getattr(llm_client, "total_tokens", 0):
        lines.append("- tokens used: %d" % (llm_client.total_tokens,))
    billed = sum(int(a.get("tokens", 0) or 0) for a in attempts)
    retries = sum(int(a.get("retries", 0) or 0) for a in attempts)
    duplicates_billed = [a for a in attempts if a.get("duplicate")]
    dup_tokens = sum(int(a.get("tokens", 0) or 0) for a in duplicates_billed)
    lines.append("- billed generation calls: %d, tokens logged per call: %d, retries: %d"
                 % (len(attempts), billed, retries))
    lines.append("- of those, %d call(s) produced code that was already evaluated and cost "
                 "%d tokens: the code cache saves the *evaluation*, never the generation"
                 % (len(duplicates_billed), dup_tokens))
    lines.append("- baseline (%s) tour lengths: %s"
                 % (base_label, ", ".join("%s=%d" % (k, int(v)) for k, v in baseline.items()),))
    lines.append("")

    lines.append("## Result")
    if best is None:
        lines.append("No valid program was found.")
    else:
        lines.append("")
        lines.append("| instance | %s | FunSearch best | improvement |" % (base_label,))
        lines.append("|---|---|---|---|")
        for name, nn in baseline.items():
            length = best.lengths.get(name)
            rel = best.rel.get(name, 0.0)
            lines.append("| %s | %d | %s | %+.2f%% |" % (name, int(nn), length, 100.0 * rel))
        lines.append("")
        lines.append("- best score (mean relative improvement): %+.6f" % (best.score,))
        lines.append("- best program id: %d (island %d, %d chars)"
                     % (best.program_id, best.island_id, len(best.code)))
    lines.append("")

    if best is not None and validation_rows:
        lines.append("## Validation (held-out, not used for selection)")
        lines.append("")
        lines.append("| instance | n | %s | FunSearch best | improvement |" % (base_label,))
        lines.append("|---|---|---|---|---|")
        for row in validation_rows:
            lines.append("| %s | %d | %d | %d | %+.2f%% |"
                         % (row["instance"], row["n"], row["nn"], row["ours"], row["improvement"]))
        lines.append("")
        mean = sum(r["improvement"] for r in validation_rows) / len(validation_rows)
        lines.append("- mean improvement over the %s on held-out instances: %+.2f%%"
                     % (base_label, mean))
        lines.append("")

    if validation_trace:
        lines.append("## Validation trajectory (held-out, logged only)")
        lines.append("")
        lines.append("The held-out set was scored each time the *search* score reached a new "
                     "global best. These numbers were written to this file and never fed back "
                     "into sampling, island resets or the stopping rule.")
        lines.append("")
        lines.append("| programs collected | attempt | search score | held-out mean |")
        lines.append("|---|---|---|---|")
        for row in validation_trace:
            lines.append("| %d | %d | %+.4f | %+.2f%% |"
                         % (row["collected"], row["attempt"],
                            row["search_score"], row["validation_mean"]))
        lines.append("")
        if len(validation_trace) >= 2:
            first = validation_trace[0]["validation_mean"]
            last = validation_trace[-1]["validation_mean"]
            lines.append("- held-out mean moved from %+.2f%% to %+.2f%% across the run (%+.2f points)"
                         % (first, last, last - first))
            lines.append("- meanwhile the search score moved from %+.4f to %+.4f (%+.2f points)"
                         % (validation_trace[0]["search_score"],
                            validation_trace[-1]["search_score"],
                            100.0 * (validation_trace[-1]["search_score"]
                                     - validation_trace[0]["search_score"])))
            lines.append("")

    if ok_attempts:
        lines.append("## Convergence")
        lines.append("")
        lines.append("| attempt | island | score | signature | chars |")
        lines.append("|---|---|---|---|---|")
        for a in ok_attempts:
            lines.append("| %d | %d | %+.6f | %s | %d |"
                         % (a["attempt"], a["island"], a["score"],
                            tuple(a["signature"]), len(a["code"])))
        lines.append("")

    lines.append("## Islands")
    lines.append("")
    stats = db.stats()
    for i, island in enumerate(db.islands):
        lines.append("- island %d: %d programs, %d clusters, best %+.6f"
                     % (i, island.size, len(island.clusters), island.best_score))
    if db.events:
        lines.append("")
        lines.append("## Island resets")
        lines.append("")
        for event in db.events:
            lines.append("- island %d re-seeded from island %d program %d (score %+.6f)"
                         % (event["island_id"], event["donor_island"],
                            event["donor_program"], event["score"]))
    lines.append("")

    lines.append("## Failure statistics")
    lines.append("")
    rejected = [a for a in attempts if not a["ok"]]
    lines.append("- attempts: %d, new programs stored: %d, duplicates: %d, rejected/failed: %d"
                 % (len(attempts), len(ok_attempts), len(duplicates), len(rejected)))
    if rejected:
        counts = {}
        for a in rejected[:200]:
            key = a["error"].split(":")[0][:60]
            counts[key] = counts.get(key, 0) + 1
        for key, value in sorted(counts.items(), key=lambda kv: -kv[1]):
            lines.append("  - %s: %d" % (key, value))
    lines.append("")

    if best is not None:
        lines.append("## Best program")
        lines.append("")
        lines.append("```python")
        lines.append(best.code.strip())
        lines.append("```")
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    args = parse_args(argv)
    run_dir = prepare_run_dir(args)
    rng = np.random.default_rng(args.seed)
    skel = skeletons.get(args.skeleton)
    features = None
    if getattr(skel, "NAME", "") == "ils" and args.features:
        features = skeleton_ils.normalize_features(args.features)
    scaled = getattr(skel, "NAME", "") == "ils" and args.features_scale == "raw"

    instances = tsp.load_instances(args.train, args.data_dir)
    payload = evaluate.instances_payload(instances)
    train_names = [i.name for i in instances]
    validation_instances = (
        tsp.load_instances(args.validation, args.data_dir) if args.validation else []
    )
    # Serialise the held-out set once: neither its payload nor its
    # nearest-neighbour baseline changes during a run.
    validation_payload = (
        evaluate.instances_payload(validation_instances) if validation_instances else None
    )
    validation_baseline = {}  # type: Dict[str, int]
    validation_trace = []  # type: List[dict]

    def probe_validation(code):
        """Score the held-out set. Logged only; never feeds back into the search."""
        if validation_payload is None:
            return None
        if not validation_baseline:
            validation_baseline.update(
                evaluate.compute_baseline(
                    validation_payload, timeout=max(60.0, args.eval_timeout * 2),
                    skel=skel, features=features, scaled=scaled))
        ok, result, _ = sandbox.run_source(
            evaluate.build_for(skel, code, features, scaled), validation_payload,
            timeout=args.eval_timeout)
        if not ok:
            if not args.quiet:
                print("  ! held-out probe failed: %s" % (result,))
            return None
        scores = []
        for inst in validation_instances:
            nn = int(validation_baseline[inst.name])
            ours = int(result["lengths"][inst.name])
            scores.append(100.0 * (nn - ours) / nn if nn else 0.0)
        return sum(scores) / len(scores)

    client = make_llm(args)
    cache = sandbox.ResultCache(
        run_dir / "cache.json", namespace=evaluate.feature_scope(skel, features, scaled))

    config = {
        "argv": sys.argv[1:] if argv is None else list(argv),
        "run_dir": str(run_dir),
        "skeleton": skel.NAME,
        "evolved_function": skel.EVOLVED_NAME,
        "features": list(features) if features else list(getattr(skel, "FEATURES", ())),
        "features_scale": "raw" if scaled else "free",
        "train": train_names,
        "validation": [i.name for i in validation_instances],
        "islands": args.islands,
        "n_programs": args.n_programs,
        "k": args.k,
        "time_budget": args.time_budget,
        "eval_timeout": args.eval_timeout,
        "seed": args.seed,
        "t_cluster": args.t_cluster,
        "t_program": args.t_program,
        "llm_temperature": args.temperature,
        "sampler": "mock" if args.mock else args.sampler,
        "thinking": args.thinking,
        "model": ("random-linear" if args.sampler == "random-linear"
                  else getattr(client, "model", "mock")),
        "base_url": getattr(client, "base_url", ""),
        "mock": bool(args.mock),
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "started_at": datetime.now().isoformat(timespec="seconds"),
    }
    if skel.NAME == "ils":
        config["ils_iterations"] = skeleton_ils.DEFAULT_ITERATIONS
        config["ils_k"] = skeleton_ils.DEFAULT_K
    (run_dir / "config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    if not args.quiet:
        print("FunSearch for TSP")
        print("  run dir   : %s" % (run_dir,))
        print("  skeleton  : %s (evolves %s)" % (skel.NAME, skel.EVOLVED_NAME))
        if skel.NAME == "ils":
            print("  ils       : T=%d rounds, k=%d cities removed per round"
                  % (skeleton_ils.DEFAULT_ITERATIONS, skeleton_ils.DEFAULT_K))
        print("  sampler   : %s" % (config["sampler"],))
        if args.mock:
            llm_label = "mock (offline)"
        elif args.sampler == "random-linear":
            llm_label = "none (control: random weights)"
        else:
            llm_label = config["model"]
        print("  llm       : %s" % (llm_label,))
        print("  train     : %s" % (", ".join("%s n=%d" % (i.name, i.n) for i in instances),))
        print("  islands   : %d, k=%d, programs=%d, budget=%.0fs"
              % (args.islands, args.k, args.n_programs, args.time_budget))

    started = time.time()
    baseline = evaluate.compute_baseline(
        payload, timeout=max(60.0, args.eval_timeout * 2), skel=skel,
        features=features, scaled=scaled)
    seed_eval = evaluate.evaluate_program(
        skel.SEED, payload, baseline, timeout=args.eval_timeout, skel=skel,
        features=features, scaled=scaled
    )
    if not seed_eval.ok:  # pragma: no cover - the seed is our own code
        raise RuntimeError("seed program failed: %s" % (seed_eval.error,))
    if not args.quiet:
        print("  baseline  : %s" % (", ".join("%s=%d" % (k, int(v)) for k, v in baseline.items()),))

    seed_program = Program(
        program_id=0,
        code=skel.SEED.strip(),
        score=seed_eval.score,
        signature=seed_eval.signature,
        lengths=seed_eval.lengths,
        rel=seed_eval.rel,
        origin="seed",
    )
    db = ProgramsDatabase(
        num_islands=args.islands,
        seed_program=seed_program,
        rng=rng,
        t_cluster=args.t_cluster,
        t_program=args.t_program,
        num_sampled=args.k,
    )
    seed_name = "seed_priority.py" if skel.NAME == "greedy" else "seed_destroy.py"
    (run_dir / seed_name).write_text(skel.SEED, encoding="utf-8")

    max_attempts = args.max_attempts or (3 * args.n_programs + 10)
    reset_every = args.reset_every or max(1, args.n_programs // 3)
    programs_path = run_dir / "programs.jsonl"
    attempts = []  # type: List[dict]
    collected = 0
    attempt = 0
    consecutive_llm_errors = 0
    consecutive_duplicates = 0
    seen = set([sandbox.code_key(skel.SEED, skel.NAME)])
    best_seen = seed_program.score

    try:
        with programs_path.open("w", encoding="utf-8") as log:
            while collected < args.n_programs and attempt < max_attempts:
                if time.time() - started > args.time_budget:
                    if not args.quiet:
                        print("  ! time budget exhausted after %d programs" % (collected,))
                    break

                attempt += 1
                island_id, parents = db.sample()
                prompt_text = build_prompt(parents, train_names, baseline, attempt, skel=skel,
                                          features=features, scaled=scaled)
                try:
                    reply = client.generate(prompt_text)
                    code = extract_priority(reply, skel=skel)
                except llm.LLMError as exc:
                    consecutive_llm_errors += 1
                    record = {
                        "attempt": attempt, "island": island_id, "ok": False,
                        "error": "llm: %s" % (exc,), "code": "", "score": None,
                        "signature": [], "lengths": {}, "duplicate": False,
                        "cached": False, "elapsed": 0.0, "parents": [p.program_id for p in parents],
                        "time": time.time() - started,
                    }
                    record.update(usage_fields(client))
                    attempts.append(record)
                    log.write(json.dumps(record, ensure_ascii=False) + "\n")
                    log.flush()
                    if consecutive_llm_errors >= 5:
                        raise
                    continue
                except ValueError as exc:  # unparsable reply: not the LLM's fault, retry
                    consecutive_llm_errors = 0
                    record = {
                        "attempt": attempt, "island": island_id, "ok": False,
                        "error": "parse: %s" % (exc,), "code": reply[:2000],
                        "score": None, "signature": [], "lengths": {},
                        "duplicate": False, "cached": False, "elapsed": 0.0,
                        "parents": [p.program_id for p in parents],
                        "time": time.time() - started,
                    }
                    record.update(usage_fields(client))
                    attempts.append(record)
                    log.write(json.dumps(record, ensure_ascii=False) + "\n")
                    log.flush()
                    continue
                consecutive_llm_errors = 0
                usage = usage_fields(client)

                key = sandbox.code_key(code, skel.NAME)
                duplicate = key in seen
                evaluation = evaluate.evaluate_program(
                    code, payload, baseline, timeout=args.eval_timeout, cache=cache,
                    skel=skel, features=features, scaled=scaled
                )
                seen.add(key)
                consecutive_duplicates = consecutive_duplicates + 1 if duplicate else 0

                if evaluation.ok and not duplicate:
                    program = Program(
                        program_id=-1,
                        code=code.strip(),
                        score=evaluation.score,
                        signature=evaluation.signature,
                        lengths=evaluation.lengths,
                        rel=evaluation.rel,
                        parents=tuple(p.program_id for p in parents),
                    )
                    db.add(program, island_id)
                    collected += 1
                    improved = evaluation.score > best_seen
                    if improved:
                        best_seen = evaluation.score
                        if args.validation_trace:
                            heldout = probe_validation(code)
                            if heldout is not None:
                                validation_trace.append({
                                    "collected": collected,
                                    "attempt": attempt,
                                    "search_score": evaluation.score,
                                    "validation_mean": heldout,
                                })
                                if not args.quiet:
                                    print("            ^ held-out (logged, not used): %+.2f%%"
                                          % (heldout,))
                    if collected % reset_every == 0:
                        db.reset_worst_half()

                record = {
                    "attempt": attempt,
                    "island": island_id,
                    "ok": bool(evaluation.ok),
                    "error": evaluation.error,
                    "score": evaluation.score if evaluation.ok else None,
                    "signature": list(evaluation.signature),
                    "lengths": evaluation.lengths,
                    "duplicate": bool(duplicate),
                    "cached": bool(evaluation.cached),
                    "elapsed": round(evaluation.elapsed, 3),
                    "parents": [p.program_id for p in parents],
                    "time": round(time.time() - started, 2),
                    "code": code,
                }
                record.update(usage)
                attempts.append(record)
                log.write(json.dumps(record, ensure_ascii=False) + "\n")
                log.flush()

                if not args.quiet:
                    if evaluation.ok and not duplicate:
                        print("  [%3d/%d] island=%d score=%+.4f sig=%s %.2fs%s"
                              % (collected, args.n_programs, island_id, evaluation.score,
                                 tuple(evaluation.signature), evaluation.elapsed,
                                 " *best*" if improved else ""))
                    elif duplicate:
                        print("  [%3d] attempt %d: duplicate program, skipped" % (collected, attempt))
                    else:
                        print("  [%3d] attempt %d: rejected (%s)"
                              % (collected, attempt, evaluation.error or "invalid"))

                if consecutive_duplicates >= 20:
                    if not args.quiet:
                        print("  ! the sampler returned 20 already-evaluated programs in a row;"
                              " stopping early")
                    break
    except KeyboardInterrupt:
        print("\n  ! interrupted by the user, saving what we have")
    finally:
        cache.save()

    best = db.best_program()
    best_name = "best_priority.py" if skel.NAME == "greedy" else "best_destroy.py"
    if best is not None:
        (run_dir / best_name).write_text(best.code.strip() + "\n", encoding="utf-8")

    validation_rows = []  # type: List[dict]
    if best is not None and validation_payload is not None:
        if not validation_baseline:
            validation_baseline.update(
                evaluate.compute_baseline(
                    validation_payload, timeout=max(60.0, args.eval_timeout * 2),
                    skel=skel, features=features, scaled=scaled))
        ok, result, _ = sandbox.run_source(
            evaluate.build_for(skel, best.code, features, scaled), validation_payload,
            timeout=args.eval_timeout
        )
        if ok:
            for inst in validation_instances:
                nn = int(validation_baseline[inst.name])
                ours = int(result["lengths"][inst.name])
                validation_rows.append({
                    "instance": inst.name,
                    "n": inst.n,
                    "nn": nn,
                    "ours": ours,
                    "improvement": 100.0 * (nn - ours) / nn if nn else 0.0,
                })
        elif not args.quiet:
            print("  ! validation run failed: %s" % (result,))

    write_report(run_dir / "report.md", args, run_dir, instances, baseline, seed_eval, best,
                 attempts, db, started, client, validation_rows, validation_trace, skel=skel)

    if not args.quiet:
        base_label = "random-destruction ILS" if skel.NAME == "ils" else "nearest neighbour"
        print("")
        if best is None:
            print("No valid program found.")
        else:
            print("search      (train, %d instances)      : mean %+.2f%% vs %s"
                  % (len(instances), 100.0 * best.score, base_label))
            for name, nn in baseline.items():
                print("  %-8s base=%6d  best=%6s  %+6.2f%%"
                      % (name, int(nn), best.lengths.get(name), 100.0 * best.rel.get(name, 0.0)))
            if validation_rows:
                mean = sum(r["improvement"] for r in validation_rows) / len(validation_rows)
                print("validation  (held-out, %d instances)   : mean %+.2f%% vs %s"
                      % (len(validation_rows), mean, base_label))
                for row in validation_rows:
                    print("  %-8s base=%6d  best=%6d  %+6.2f%%"
                          % (row["instance"], row["nn"], row["ours"], row["improvement"]))
                print("            (never used for selection; only reported)")
            if validation_trace:
                print("held-out trace: %d points, %+.2f%% -> %+.2f%% while search went %+.4f -> %+.4f"
                      % (len(validation_trace),
                         validation_trace[0]["validation_mean"],
                         validation_trace[-1]["validation_mean"],
                         validation_trace[0]["search_score"],
                         validation_trace[-1]["search_score"]))
            print("Best code  : %s" % (run_dir / best_name,))
        print("Report     : %s" % (run_dir / "report.md",))
        print('Solve with : python -m funsearch_tsp.solve --program "%s" --group search'
              % (run_dir / best_name,))
    return 0


if __name__ == "__main__":
    sys.exit(main())
