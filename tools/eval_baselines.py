"""Compare the built-in destroy operators (and optional extra methods) on split groups.

    python tools/eval_baselines.py --group final
    python tools/eval_baselines.py --group search validation            # both in one go
    python tools/eval_baselines.py --group final --include llm=runs/<ts>_ils01/final.csv
    python tools/eval_baselines.py --group search --baselines lsonly related

Each method is evaluated by ``funsearch_tsp.solve`` itself (same skeleton, same
T/k, same baseline), so the numbers in the resulting table are directly
comparable: every column is "tour length reached by that destroy operator" and
the gap column is relative to the published optimum.

With several ``--group`` values the groups are evaluated one after another, each
with its own table and its own CSV sub-directory, because the groups have
different roles (search = used for selection, validation/final = held out).
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from funsearch_tsp import construct, solve, skeleton_ils  # noqa: E402

RUNS_DIR = ROOT / "runs"

#: Every method this tool can measure, in the order they should appear in a table.
ALL_METHODS = (["lsonly", "random", "worst", "related"] + list(construct.LABELS))


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python tools/eval_baselines.py",
        description="Measure the built-in destroy operators on one or more split groups.",
    )
    parser.add_argument("--group", nargs="+", default=["final"],
                        help="one or more split groups to evaluate in a single command: "
                             "search validation final transfer")
    parser.add_argument("--baselines", nargs="+", default=list(ALL_METHODS),
                        choices=list(ALL_METHODS),
                        help="methods to measure (default: all of them); 'lsonly' is the A2 "
                             "ablation, '*-ins' are the constructive insertion baselines and "
                             "'*-ins-ls' the same followed by 2-opt/Or-opt")
    parser.add_argument("--include", nargs="+", default=None, metavar="LABEL=CSV",
                        help="add an existing results.csv to the same table (single --group "
                             "only), e.g. llm=runs/20261111-001309_ils01/final.csv")
    parser.add_argument("--split", default=None, help="path to split.json")
    parser.add_argument("--work-dir", default=None,
                        help="where the per-method CSVs are written (default "
                             "runs/baselines_<group>; with several groups, <work-dir>/<group>)")
    parser.add_argument("--out", default=None,
                        help="write the markdown table here as well (with several groups a "
                             "_<group> suffix is added)")
    parser.add_argument("--chunk", type=int, default=1,
                        help="instances per evaluation subprocess (default 1)")
    parser.add_argument("--timeout", type=float, default=900.0,
                        help="wall-clock budget per batch (s)")
    args = parser.parse_args(argv)
    if args.include and len(args.group) > 1:
        parser.error("--include only works with a single --group (tables are per group)")
    return args


def read_results(path):
    """{instance: {n, length, gap, opt}} from a solve CSV."""
    rows = {}
    with open(path, "r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            name = (row.get("instance") or "").strip()
            if not name:
                continue
            length = (row.get("funsearch") or "").strip()
            gap = (row.get("gap_pct") or "").strip()
            opt = (row.get("optimum") or "").strip()
            rows[name] = {
                "n": int(float(row.get("n") or 0)),
                "length": int(float(length)) if length else None,
                "gap": float(gap) if gap else None,
                "opt": int(float(opt)) if opt else None,
            }
    return rows


def run_method(name, group, args, csv_path):
    """Delegate the actual evaluation to ``solve`` so the protocol is identical."""
    argv = ["--baseline", name, "--group", group, "--csv", str(csv_path),
            "--chunk", str(args.chunk), "--timeout", str(args.timeout)]
    if args.split:
        argv += ["--split", args.split]
    print("\n=== %s (%s) ===" % (name, group))
    try:
        solve.main(argv)
    except SystemExit as exc:
        print("  ! %s failed: %s" % (name, exc))
        return None
    return csv_path if Path(csv_path).exists() else None


def markdown_table(columns, order):
    """columns: {label: {instance: {...}}}, order: list of instance names."""
    head = ["instance", "n", "opt"] + list(columns)
    lines = ["| " + " | ".join(head) + " |",
             "|" + "|".join(["---"] * len(head)) + "|"]
    for inst in order:
        n = opt = ""
        cells = []
        for label in columns:
            cell = columns[label].get(inst)
            if not cell:
                cells.append("-")
                continue
            n = cell["n"] or n
            opt = cell["opt"] or opt
            if cell["length"] is None:
                cells.append("failed")
            elif cell["gap"] is None:
                cells.append("%d" % (cell["length"],))
            else:
                cells.append("%d (%.2f%%)" % (cell["length"], cell["gap"]))
        lines.append("| %s | %s | %s | %s |" % (inst, n, opt or "-", " | ".join(cells)))

    def summary(label):
        gaps = [c["gap"] for c in columns[label].values() if c["gap"] is not None]
        if not gaps:
            return "-", "-"
        return "%.2f%%" % (sum(gaps) / len(gaps)), "%.2f%%" % (max(gaps))

    lines.append("| **mean gap** | | | "
                 + " | ".join(summary(l)[0] for l in columns) + " |")
    lines.append("| **worst gap** | | | "
                 + " | ".join(summary(l)[1] for l in columns) + " |")
    return "\n".join(lines)


def work_dir_for(group, args):
    if args.work_dir:
        base = Path(args.work_dir)
        return base / group if len(args.group) > 1 else base
    return RUNS_DIR / ("baselines_%s" % (group,))


def evaluate_one(group, args, stamp):
    """Run every requested method on one group; return {label: rows}."""
    work = work_dir_for(group, args)
    work.mkdir(parents=True, exist_ok=True)
    print("\n" + "=" * 70)
    print("group %s  ->  %s" % (group, work))
    print("=" * 70)

    columns = {}
    for name in args.baselines:
        csv_path = work / ("%s_%s.csv" % (name, stamp))
        produced = run_method(name, group, args, csv_path)
        if produced:
            columns[name] = read_results(produced)
    for spec in (args.include or []):
        if "=" not in spec:
            raise SystemExit("--include needs LABEL=CSV, got %r" % (spec,))
        label, path = spec.split("=", 1)
        if not Path(path).exists():
            raise SystemExit("--include %s: %s does not exist" % (label, path))
        columns[label.strip()] = read_results(path)
    return columns


def main(argv=None) -> int:
    args = parse_args(argv)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    produced_any = False
    for group in args.group:
        columns = evaluate_one(group, args, stamp)
        if not columns:
            print("! no method produced results for group %s" % (group,))
            continue
        produced_any = True
        order = list(next(iter(columns.values())).keys())
        table = markdown_table(columns, order)
        print("\n" + table + "\n")
        if args.out:
            out = Path(args.out)
            if len(args.group) > 1:
                out = out.with_name("%s_%s%s" % (out.stem, group, out.suffix))
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(table + "\n", encoding="utf-8")
            print("table written to %s" % (out,))
    if not produced_any:
        raise SystemExit("no group produced results")
    return 0


if __name__ == "__main__":
    sys.exit(main())
