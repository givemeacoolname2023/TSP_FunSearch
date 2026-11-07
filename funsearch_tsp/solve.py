"""Apply a FunSearch-generated `priority` function to TSP instances.

    python -m funsearch_tsp.solve --program runs/<ts>/best_priority.py \
           --instances berlin52 eil51 eil101 rand100 rand200

The generated program is a *policy*, not a tour: it is spliced into the frozen
greedy skeleton, which then builds one tour per instance. Both the program and
the nearest-neighbour baseline run in an isolated subprocess, so a bad program
can only cost you a timeout.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List, Optional

from . import evaluate, sandbox, skeleton, tsp
from .prompt import extract_priority

#: Published TSPLIB optima (used only to report the gap; never used for search).
KNOWN_OPTIMA = {
    "berlin52": 7542,
    "eil51": 426,
    "eil76": 538,
    "eil101": 629,
    "st70": 675,
    "pr76": 108159,
    "kroA100": 21282,
    "rd100": 7910,
}


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m funsearch_tsp.solve",
        description="Solve TSP instances with a FunSearch-generated priority function.",
    )
    parser.add_argument("--program", required=True, help="path to the generated .py file")
    parser.add_argument("--instances", nargs="+", default=None,
                        help="instance names or paths (default: every .tsp in --data-dir)")
    parser.add_argument("--data-dir", default=None, help="directory holding the .tsp files")
    parser.add_argument("--timeout", type=float, default=60.0, help="per-instance timeout (s)")
    parser.add_argument("--csv", default="results.csv", help="where to write the results table")
    parser.add_argument("--show-tour", action="store_true", help="print the full visiting order")
    return parser.parse_args(argv)


def load_priority_code(path) -> str:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    try:
        return extract_priority(text)
    except ValueError as exc:
        raise SystemExit("cannot find a `priority` function in %s: %s" % (path, exc))


def discover_instances(data_dir=None) -> List[str]:
    root = Path(data_dir) if data_dir else tsp.DEFAULT_DATA_DIR
    names = sorted(p.stem for p in root.glob("*.tsp"))
    if not names:
        raise SystemExit("no .tsp files found in %s" % (root,))
    return names


def main(argv=None) -> int:
    args = parse_args(argv)
    code = load_priority_code(args.program)
    try:
        sandbox.validate_candidate(code)
    except sandbox.ProgramRejected as exc:
        raise SystemExit("the program in %s failed the static checks: %s" % (args.program, exc))

    names = args.instances or discover_instances(args.data_dir)
    instances = tsp.load_instances(names, args.data_dir)
    payload = evaluate.instances_payload(instances)
    source = skeleton.build_source(code)

    baseline = evaluate.compute_baseline(payload, timeout=max(60.0, args.timeout))
    ok, result, elapsed = sandbox.run_source(source, payload, timeout=args.timeout, want_tours=True)
    if not ok:
        raise SystemExit("the program failed on the instances: %s" % (result,))

    rows = []  # type: List[dict]
    print("%-10s %5s %9s %9s %10s %9s %9s" %
          ("instance", "n", "NN", "FunSearch", "improve", "optimum", "gap"))
    print("-" * 68)
    gaps = []  # type: List[float]
    for inst in instances:
        nn = int(baseline[inst.name])
        ours = int(result["lengths"][inst.name])
        improve = 100.0 * (nn - ours) / nn if nn else 0.0
        optimum = KNOWN_OPTIMA.get(inst.name)
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
            "tour": " ".join(str(c) for c in result["tours"][inst.name]),
        })
    print("-" * 68)
    if gaps:
        print("mean gap to the published optima over %d TSPLIB instances: %.2f%%"
              % (len(gaps), sum(gaps) / len(gaps)))
    print("evaluated in %.2fs (program + baseline)" % (elapsed,))

    if args.csv:
        csv_path = Path(args.csv)
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
