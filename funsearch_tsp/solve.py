"""Apply a FunSearch-generated program to TSP instances.

    python -m funsearch_tsp.solve --program runs/<ts>/best_destroy.py --group search
    python -m funsearch_tsp.solve --program runs/<ts>/best_priority.py --group search

The generated program is a *policy*, not a tour. Which frozen skeleton it plugs
into is detected from the file itself (``destroy_priority`` -> the ILS
skeleton, ``priority`` -> the greedy construction skeleton), and both the
program and the baseline run in an isolated subprocess, so a bad program can
only cost you a timeout.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from . import construct, evaluate, sandbox, skeleton, skeleton_ils, skeletons, tsp
from .prompt import extract_priority

#: Published TSPLIB optima (used only to report the gap; never used for search).
#: Deliberately empty: ``tsp_files/data/optimal_values.csv`` -- written by
#: ``tools/build_dataset.py select`` -- is the single source of truth and covers
#: every instance in ``tsp_files/``.
KNOWN_OPTIMA: Dict[str, int] = {}

#: Optima tables written by the dataset builder. The first one that exists wins;
#: the second entry keeps the layout used before ``data/`` was moved.
_ROOT = Path(__file__).resolve().parent.parent
OPTIMA_CSVS = (
    _ROOT / "tsp_files" / "data" / "optimal_values.csv",
    _ROOT / "data" / "optimal_values.csv",
)


def load_known_optima(path=None) -> Dict[str, int]:
    """Return the published optima read from the generated CSV.

    A missing table is announced rather than swallowed: without it the gap
    column silently degrades to ``-`` for every instance, which is easy to miss
    when the results table is copied into a report.
    """
    table = dict(KNOWN_OPTIMA)
    candidates = [Path(path)] if path is not None else list(OPTIMA_CSVS)
    chosen = None
    for candidate in candidates:
        if candidate.exists():
            chosen = candidate
            break
    if chosen is None:
        sys.stderr.write(
            "warning: no optima table found (looked for "
            "tsp_files/data/optimal_values.csv and data/optimal_values.csv); "
            "the gap column will be empty\n")
        return table
    with open(chosen, "r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            value = (row.get("opt") or "").strip()
            name = (row.get("name") or "").strip()
            if not name or not value:
                continue
            try:
                table[name] = int(float(value))
            except ValueError:
                continue
    return table


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m funsearch_tsp.solve",
        description="Solve TSP instances with a FunSearch-generated priority function.",
    )
    parser.add_argument("--program", default=None,
                        help="path to the generated .py file (or use --baseline)")
    parser.add_argument("--baseline",
                        choices=(sorted(skeleton_ils.BASELINES)
                                 + list(skeleton_ils.EXTRA_BASELINES)
                                 + list(construct.LABELS)),
                        default=None,
                        help="evaluate a built-in method instead of a generated program: the "
                             "destroy operators (random | worst | related), the A2 ablation "
                             "'lsonly' (nearest neighbour + 2-opt/Or-opt, no ILS loop), or a "
                             "constructive baseline (nearest-/cheapest-/farthest-ins, with an "
                             "optional -ls suffix that runs 2-opt/Or-opt afterwards)")
    parser.add_argument("--instances", nargs="+", default=None,
                        help="instance names or paths (default: every .tsp in --data-dir)")
    parser.add_argument("--group", default=None,
                        help="take the instance list from a named group of the frozen "
                             "split instead of typing it out: "
                             "search | validation | final | transfer")
    parser.add_argument("--split", default=None,
                        help="path to split.json (default: tsp_files/data/split.json)")
    parser.add_argument("--data-dir", default=None, help="directory holding the .tsp files")
    parser.add_argument("--timeout", type=float, default=60.0,
                        help="wall-clock budget per batch, not per instance (s)")
    parser.add_argument("--chunk", type=int, default=0,
                        help="instances evaluated per subprocess (0 = one batch, and on "
                             "timeout solve retries instance by instance so that only the "
                             "genuinely slow instances are lost)")
    parser.add_argument("--csv", default="results.csv", help="where to write the results table")
    parser.add_argument("--show-tour", action="store_true", help="print the full visiting order")
    parser.add_argument("--skeleton", choices=["auto"] + skeletons.names(), default="auto",
                        help="which frozen skeleton to plug the program into; 'auto' (default) "
                             "reads it off the file: destroy_priority -> ils, priority -> greedy")
    args = parser.parse_args(argv)

    if args.group is not None and args.instances is not None:
        parser.error("--group and --instances are alternatives; pass only one")
    if (args.program is None) == (args.baseline is None):
        parser.error("pass exactly one of --program or --baseline")
    return args


#: Frozen splits written by ``tools/build_dataset.py``; the first existing one wins.
SPLIT_JSONS = (
    _ROOT / "tsp_files" / "data" / "split.json",
    _ROOT / "data" / "split.json",
)


def instances_for_group(group, path=None) -> List[str]:
    """Return the instance names of one group of the frozen split."""
    candidates = [Path(path)] if path is not None else list(SPLIT_JSONS)
    chosen = None
    for candidate in candidates:
        if candidate.exists():
            chosen = candidate
            break
    if chosen is None:
        raise SystemExit("--group %s: no split.json found (looked for %s); pass --split"
                         % (group, ", ".join(str(c) for c in candidates)))
    with open(chosen, "r", encoding="utf-8") as handle:
        split = json.load(handle)
    if group not in split:
        raise SystemExit("--group %s: %s has no such group (available: %s)"
                         % (group, chosen, ", ".join(
                             g for g in split if not g.startswith("_"))))
    names = [name for name in split[group] if name]
    if not names:
        raise SystemExit("--group %s: the group is empty in %s" % (group, chosen))
    return names


def load_priority_code(path, skel=None) -> str:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    try:
        return extract_priority(text, skel=skel)
    except ValueError as exc:
        raise SystemExit("cannot find the evolved function in %s: %s" % (path, exc))


def _chunks(items, size):
    """Split ``items`` into lists of at most ``size`` elements (``size<=0`` keeps all)."""
    if not size or size <= 0:
        yield list(items)
        return
    for start in range(0, len(items), size):
        yield list(items[start:start + size])


def _evaluate_chunks(instances, source, timeout, chunk_size):
    """Run ``source`` over ``instances`` in batches; return lengths/tours/failures."""
    lengths = {}  # type: Dict[str, int]
    tours = {}    # type: Dict[str, List[int]]
    failed = {}   # type: Dict[str, str]
    elapsed = 0.0
    for chunk in _chunks(instances, chunk_size):
        chunk_payload = evaluate.instances_payload(chunk)
        ok, result, spent = sandbox.run_source(
            source, chunk_payload, timeout=timeout, want_tours=True)
        elapsed += spent
        if ok:
            lengths.update(result["lengths"])
            tours.update(result.get("tours") or {})
        else:
            for inst in chunk:
                failed[inst.name] = str(result)
    return lengths, tours, failed, elapsed


def discover_instances(data_dir=None) -> List[str]:
    root = Path(data_dir) if data_dir else tsp.DEFAULT_DATA_DIR
    names = sorted(p.stem for p in root.glob("*.tsp"))
    if not names:
        raise SystemExit("no .tsp files found in %s" % (root,))
    return names


def main(argv=None) -> int:
    args = parse_args(argv)
    source_override = None
    if args.baseline == "lsonly":
        skel = skeleton_ils
        code = None
        source_override = skeleton_ils.local_search_only_source()
        method_label = "ls-only"
        origin = "A2 ablation: nearest neighbour + 2-opt/Or-opt, no ILS loop"
    elif args.baseline in construct.LABELS:
        skel = skeleton_ils
        code = None
        source_override = construct.build_source(args.baseline)
        method_label = args.baseline
        origin = "constructive baseline: %s" % (construct.DESCRIPTIONS[args.baseline],)
    elif args.baseline is not None:
        skel = skeleton_ils
        code = skeleton_ils.BASELINES[args.baseline].strip()
        method_label = args.baseline
        origin = "built-in baseline operator '%s'" % (args.baseline,)
    else:
        raw = Path(args.program).read_text(encoding="utf-8", errors="replace")
        if args.skeleton == "auto":
            skel = skeletons.detect(raw)
            if skel is None:
                raise SystemExit("cannot tell which skeleton %s belongs to; pass --skeleton "
                                 "greedy|ils" % (args.program,))
        else:
            skel = skeletons.get(args.skeleton)
        code = load_priority_code(args.program, skel=skel)
        method_label = "FunSearch"
        origin = str(args.program)
    if code is not None:
        try:
            sandbox.validate_candidate(code, skel=skel)
        except sandbox.ProgramRejected as exc:
            raise SystemExit("%s failed the static checks: %s" % (origin, exc))

    if args.group is not None:
        names = instances_for_group(args.group, args.split)
    else:
        names = args.instances or discover_instances(args.data_dir)
    instances = tsp.load_instances(names, args.data_dir)
    payload = evaluate.instances_payload(instances)
    source = source_override if source_override is not None else skel.build_source(code)

    baseline = evaluate.compute_baseline(
        payload, timeout=max(60.0, args.timeout), skel=skel)
    base_label = "random-destruction ILS" if getattr(skel, "NAME", "") == "ils" else "NN"
    print("skeleton: %s (evolves %s); baseline: %s" % (skel.NAME, skel.EVOLVED_NAME, base_label))
    print("program : %s" % (origin,))

    # Evaluate in one batch first (fast path). A generated priority function can
    # be super-quadratic in n, so a single 1800-city instance may need more wall
    # clock than the other 62 together; if the batch times out we retry instance
    # by instance so that one slow instance cannot sink the whole run.
    lengths, tours, failed, elapsed = _evaluate_chunks(
        instances, source, args.timeout, args.chunk)
    if failed and len(failed) == len(instances) and len(instances) > 1:
        print("note: the batch exceeded --timeout %.0fs; retrying instance by instance "
              "(this can take several minutes)" % (args.timeout,))
        lengths, tours, failed, elapsed2 = _evaluate_chunks(
            instances, source, args.timeout, 1)
        elapsed += elapsed2

    if failed and len(failed) == len(instances):
        raise SystemExit("the program failed on every instance: %s"
                         % (next(iter(failed.values())),))
    if failed:
        print("warning: %d instance(s) did not finish (%s); they are marked as failed"
              % (len(failed), next(iter(failed.values()))))

    rows = []  # type: List[dict]
    known_optima = load_known_optima()
    print("%-10s %5s %9s %9s %10s %9s %9s" %
          ("instance", "n", base_label, method_label, "improve", "optimum", "gap"))
    print("-" * 68)
    gaps = []  # type: List[float]
    for inst in instances:
        nn = int(baseline[inst.name])
        if inst.name in failed:
            print("%-10s %5d %9d %9s %10s %9s %9s"
                  % (inst.name, inst.n, nn, "FAILED", "-", "-", "-"))
            rows.append({
                "instance": inst.name, "n": inst.n, "nearest_neighbour": nn,
                "funsearch": "", "improvement_pct": "", "optimum": "",
                "gap_pct": "", "tour": "", "note": failed[inst.name],
            })
            continue
        ours = int(lengths[inst.name])
        improve = 100.0 * (nn - ours) / nn if nn else 0.0
        optimum = known_optima.get(inst.name)
        gap = 100.0 * (ours - optimum) / optimum if optimum else None
        if gap is not None:
            gaps.append(gap)
        print("%-10s %5d %9d %9d %9.2f%% %9s %9s"
              % (inst.name, inst.n, nn, ours, improve,
                 optimum if optimum else "-",
                 ("%.2f%%" % (gap,)) if gap is not None else "-"))
        rows.append({
            "instance": inst.name,
            "n": inst.n,
            "nearest_neighbour": nn,
            "funsearch": ours,
            "improvement_pct": round(improve, 4),
            "optimum": optimum if optimum else "",
            "gap_pct": round(gap, 4) if gap is not None else "",
            "tour": " ".join(str(c) for c in tours.get(inst.name, [])),
            "note": "",
        })
    print("-" * 68)
    if gaps:
        print("mean gap to the published optima over %d TSPLIB instances: %.2f%%"
              % (len(gaps), sum(gaps) / len(gaps)))
    print("evaluated in %.2fs (program + baseline)" % (elapsed,))

    if args.csv:
        csv_path = Path(args.csv)
        # create the parent directory instead of dying with FileNotFoundError
        # after the whole table has already been printed
        try:
            csv_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise SystemExit("cannot create %s: %s" % (csv_path.parent, exc))
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print("results written to %s" % (csv_path,))

    if args.show_tour:
        for row in rows:
            print("\n%s (length %d):\n  %s"
                  % (row["instance"], row["funsearch"], row["tour"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
