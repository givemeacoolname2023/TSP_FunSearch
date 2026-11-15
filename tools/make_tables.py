"""Regenerate every comparison table from what is already in ``runs/``.

    python tools/make_tables.py
    python tools/make_tables.py --groups search final
    python tools/make_tables.py --runs-dir runs --out-dir runs

It discovers, by directory naming only:

    runs/baselines_<group>/<method>_*.csv     the built-in operators
    runs/baselines/<group>/<method>_*.csv     (same, multi-group layout)
    runs/*_ils_s<k>/<group>.csv               one directory per LLM seed
    runs/*_ctl<k>/<group>.csv                 one directory per control seed
    runs/*_raw_llm<k>/<group>.csv             ... the same in raw distance units
    runs/*_raw_ctl<k>/<group>.csv

and then calls ``tools/summarize.py`` once per group, so the statistics are
identical to running it by hand. Everything is printed first (what was found,
and what is missing) so a stale directory cannot silently be counted as an
extra "seed".

Free-space and raw-space runs are kept in separate rows (``llm`` vs ``llm-raw``)
because mixing them into one mean would answer no question at all.  The feature
scale is read from each run's ``config.json`` and only falls back to the
directory tag when that file is missing.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = Path(__file__).resolve().parent
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import summarize  # noqa: E402  (same directory)
from funsearch_tsp import construct  # noqa: E402

BASELINE_METHODS = tuple(["lsonly", "random", "worst", "related"] + list(construct.LABELS))
GROUPS = ("search", "validation", "final")

#: ``_ils_s0`` (free) and ``_raw_llm0`` (raw distance units) name the same thing.
LLM_PATTERN = re.compile(r"(?:^|_)(raw_)?(?:ils_s|llm)(\d+)$")
CTL_PATTERN = re.compile(r"(?:^|_)(raw_)?ctl(\d+)$")

#: label -> (backend, requires raw?) used to name the columns in the table.
STOCHASTIC = (("llm", "llm", LLM_PATTERN), ("control", "ctl", CTL_PATTERN))


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python tools/make_tables.py",
        description="Rebuild runs/summary_<group>.md from the CSVs already in runs/.",
    )
    parser.add_argument("--runs-dir", default=str(ROOT / "runs"))
    parser.add_argument("--out-dir", default=None,
                        help="where summary_<group>.md is written (default: --runs-dir)")
    parser.add_argument("--groups", nargs="+", default=list(GROUPS), choices=GROUPS)
    parser.add_argument("--metric", choices=["gap", "length"], default="gap")
    parser.add_argument("--no-pairs", action="store_true",
                        help="skip the paired tests")
    return parser.parse_args(argv)


def scale_of(directory: Path, match) -> str:
    """'raw' or 'free' for one run directory (config.json wins over the tag)."""
    config = directory / "config.json"
    try:
        data = json.loads(config.read_text(encoding="utf-8"))
        return "raw" if str(data.get("features_scale", "free")).lower() == "raw" else "free"
    except (OSError, ValueError):
        return "raw" if match.group(1) else "free"


def discover(runs_dir):
    """{baselines: {group: {method: path}}, stochastic: {group: {label: [paths]}}}."""
    runs_dir = Path(runs_dir)
    out = {"baselines": {}, "stochastic": {group: {} for group in GROUPS}}

    for group in GROUPS:
        # Two layouts are accepted, because tools/eval_baselines.py uses
        # <work-dir>/<group> for a multi-group run and <work-dir> for a single
        # one:   runs/baselines_<group>/   and   runs/baselines/<group>/
        candidates = [runs_dir / ("baselines_%s" % (group,)), runs_dir / "baselines" / group]
        found = {}
        for base in candidates:
            if not base.is_dir():
                continue
            for method in BASELINE_METHODS:
                for hit in base.glob("%s_*.csv" % (method,)):
                    previous = found.get(method)
                    if previous is None or hit.name > previous.name:
                        found[method] = hit
        out["baselines"][group] = found

    directories = sorted(p for p in runs_dir.iterdir() if p.is_dir()) \
        if runs_dir.is_dir() else []
    for group in GROUPS:
        buckets = {}
        for label, _key, pattern in STOCHASTIC:
            for directory in directories:
                match = pattern.search(directory.name)
                if not match:
                    continue
                csv_path = directory / ("%s.csv" % (group,))
                if not csv_path.is_file():
                    continue
                column = label if scale_of(directory, match) == "free" else label + "-raw"
                buckets.setdefault(column, []).append((int(match.group(2)), csv_path))
        out["stochastic"][group] = {
            column: [path for _, path in sorted(items)]
            for column, items in buckets.items()
        }
    return out


def report(found, runs_dir):
    print("runs dir : %s" % (runs_dir,))
    for group in GROUPS:
        base = found["baselines"][group]
        seeds = found["stochastic"][group]
        detail = ", ".join("%s=%d" % (name, len(paths)) for name, paths in sorted(seeds.items()))
        print("  %-10s baselines: %-52s seeds: %s"
              % (group, ", ".join(sorted(base)) or "(missing)", detail or "(none)"))
    missing = []
    for group in GROUPS:
        for method in BASELINE_METHODS:
            if method not in found["baselines"][group]:
                missing.append("baselines %s/%s" % (group, method))
        for column in ("llm", "control"):
            if column not in found["stochastic"][group]:
                missing.append("%s/%s" % (column, group))
    if missing:
        print("  ! missing: %s" % (", ".join(missing),))


def build_argv(found, group, out_path, args):
    argv = ["--group", group, "--metric", args.metric]

    base = found["baselines"][group]
    for method in BASELINE_METHODS:
        if method in base:
            argv += ["--method", method, str(base[method])]
    seeds = found["stochastic"][group]
    for column in ("llm", "control", "llm-raw", "control-raw"):
        if column in seeds:
            argv += ["--method", column] + [str(p) for p in seeds[column]]

    if not args.no_pairs:
        wanted = [
            ("llm", "control"),        # does the LLM beat random search?
            ("llm", "related"),        # does it beat the strongest hand-made operator?
            ("llm", "llm-raw"),        # scale-free ablation, main method
            ("control", "control-raw"),  # scale-free ablation, control
        ]
        available = set(seeds)
        for left, right in wanted:
            if left in available and right in available:
                argv += ["--pair", left, right]
            elif left in available and right in base:
                argv += ["--pair", left, right]
    argv += ["--out", str(out_path)]
    return argv


def main(argv=None) -> int:
    args = parse_args(argv)
    runs_dir = Path(args.runs_dir)
    if not runs_dir.is_dir():
        raise SystemExit("no such directory: %s" % (runs_dir,))
    out_dir = Path(args.out_dir) if args.out_dir else runs_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    found = discover(runs_dir)
    report(found, runs_dir)

    written = []
    for group in args.groups:
        methods = list(found["baselines"][group])
        if not found["stochastic"][group] and not methods:
            print("\n! %s: nothing to summarise, skipped" % (group,))
            continue
        out_path = out_dir / ("summary_%s.md" % (group,))
        print("\n" + "=" * 70)
        print("summary for %s -> %s" % (group, out_path))
        print("=" * 70)
        try:
            summarize.main(build_argv(found, group, out_path, args))
        except SystemExit as exc:
            print("! summarize failed for %s: %s" % (group, exc))
            continue
        written.append(out_path)

    print("")
    for path in written:
        print("written: %s" % (path,))
    return 0 if written else 1


if __name__ == "__main__":
    sys.exit(main())
