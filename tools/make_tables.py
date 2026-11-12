"""Regenerate every comparison table from what is already in ``runs/``.

    python tools/make_tables.py
    python tools/make_tables.py --groups search final
    python tools/make_tables.py --runs-dir runs --out-dir runs

It discovers, by directory naming only:

    runs/baselines_<group>/<method>_*.csv     the four built-in operators
    runs/*_ils_s<k>/<group>.csv               one directory per LLM seed
    runs/*_ctl<k>/<group>.csv                 one directory per control seed

and then calls ``tools/summarize.py`` once per group, so the statistics are
identical to running it by hand. Everything is printed first (what was found,
and what is missing) so a stale directory cannot silently be counted as an
extra "seed".
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = Path(__file__).resolve().parent
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import summarize  # noqa: E402  (same directory)

BASELINE_METHODS = ("lsonly", "random", "worst", "related")
GROUPS = ("search", "validation", "final")

LLM_PATTERN = re.compile(r"_ils_s(\d+)$")
CTL_PATTERN = re.compile(r"_ctl(\d+)$")


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
                        help="skip the llm-vs-control / llm-vs-related paired tests")
    return parser.parse_args(argv)


def newest(paths):
    return sorted(paths, key=lambda p: p.name)[-1]


def discover(runs_dir):
    """{baselines: {group: {method: path}}, llm: {group: [paths]}, ctl: {...}}."""
    runs_dir = Path(runs_dir)
    out = {"baselines": {}, "llm": {}, "ctl": {}}

    for group in GROUPS:
        base = runs_dir / ("baselines_%s" % (group,))
        found = {}
        if base.is_dir():
            for method in BASELINE_METHODS:
                hits = list(base.glob("%s_*.csv" % (method,)))
                if hits:
                    found[method] = newest(hits)
        out["baselines"][group] = found

    for key, pattern in (("llm", LLM_PATTERN), ("ctl", CTL_PATTERN)):
        for group in GROUPS:
            entries = []
            for directory in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
                match = pattern.search(directory.name)
                if not match:
                    continue
                csv_path = directory / ("%s.csv" % (group,))
                if csv_path.is_file():
                    entries.append((int(match.group(1)), directory.name, csv_path))
            out[key][group] = [path for _, _, path in sorted(entries)]
    return out


def report(found, runs_dir):
    print("runs dir : %s" % (runs_dir,))
    for group in GROUPS:
        base = found["baselines"][group]
        print("  %-10s baselines: %-40s llm seeds: %d   control seeds: %d"
              % (group,
                 ", ".join(sorted(base)) or "(missing)",
                 len(found["llm"][group]),
                 len(found["ctl"][group])))
    missing = []
    for group in GROUPS:
        for method in BASELINE_METHODS:
            if method not in found["baselines"][group]:
                missing.append("baselines %s/%s" % (group, method))
        if not found["llm"][group]:
            missing.append("llm/%s" % (group,))
        if not found["ctl"][group]:
            missing.append("control/%s" % (group,))
    if missing:
        print("  ! missing: %s" % (", ".join(missing),))


def build_argv(found, group, out_path, args):
    argv = ["--group", group, "--metric", args.metric]

    base = found["baselines"][group]
    for method in BASELINE_METHODS:
        if method in base:
            argv += ["--method", method, str(base[method])]
    llm = found["llm"][group]
    ctl = found["ctl"][group]
    if llm:
        argv += ["--method", "llm"] + [str(p) for p in llm]
    if ctl:
        argv += ["--method", "control"] + [str(p) for p in ctl]
    if not args.no_pairs and llm and ctl:
        argv += ["--pair", "llm", "control"]
    if not args.no_pairs and llm and "related" in base:
        argv += ["--pair", "llm", "related"]
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
        if not found["llm"][group] and not found["ctl"][group] and not methods:
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
