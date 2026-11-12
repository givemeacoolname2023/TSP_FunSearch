"""Aggregate several runs into one table and run paired statistics.

    python tools/summarize.py --group final ^
        --method random runs\baselines_final\random_*.csv ^
        --method llm runs\20261111-001309_ils01\final.csv ^
        --method control runs\ctl_rw0\final.csv runs\ctl_rw1\final.csv runs\ctl_rw2\final.csv ^
        --pair llm control

Every ``--method`` may take several CSVs: they are treated as independent seeds
of the same method. The paired comparison uses the per-instance mean gap of each
method, so "paired" means "the same instance is compared with itself across the
two methods" — which is far more sensitive than comparing two independent means.
"""
from __future__ import annotations

import argparse
import glob
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval_baselines import read_results  # noqa: E402  (same directory)


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python tools/summarize.py",
        description="Aggregate method results (one or more seeds) and pair them.",
    )
    parser.add_argument("--method", action="append", nargs="+", metavar="LABEL CSV...",
                        required=True,
                        help="label followed by one or more results.csv files (seeds)")
    parser.add_argument("--pair", action="append", nargs=2, metavar=("A", "B"), default=None,
                        help="paired comparison of two labels (A - B; negative means A better)")
    parser.add_argument("--metric", choices=["gap", "length"], default="gap",
                        help="gap (percent, needs published optima) or raw tour length")
    parser.add_argument("--group", default=None, help="only annotate which split group this is")
    parser.add_argument("--out", default=None, help="also write the markdown here")
    args = parser.parse_args(argv)
    if any(len(m) < 2 for m in args.method):
        parser.error("--method needs a label and at least one CSV")
    return args


def expand_paths(paths):
    """Resolve shell wildcards ourselves.

    PowerShell passes ``*.csv`` to a native program verbatim, so a command like
    ``--method llm runs\\*_ils_s0\\final.csv`` would otherwise arrive as a
    literal filename. Globbing here keeps the command short in any shell.
    """
    out = []
    for pattern in paths:
        hits = sorted(glob.glob(str(pattern)))
        out.extend(hits if hits else [pattern])
    return out


def load_method(csvs, metric):
    """[{instance: value}] — one dict per seed."""
    seeds = []
    for path in expand_paths(csvs):
        rows = read_results(path)
        values = {}
        for name, cell in rows.items():
            if cell["length"] is None:
                continue
            if metric == "gap":
                if cell["gap"] is None:      # no published optimum for this instance
                    continue
                values[name] = cell["gap"]
            else:
                values[name] = float(cell["length"])
        seeds.append(values)
    return seeds


def per_instance_mean(seeds):
    """{instance: mean over seeds}, skipping instances a seed did not produce."""
    out = {}
    for values in seeds:
        for name, value in values.items():
            if value is None:
                continue
            out.setdefault(name, []).append(value)
    return {name: sum(v) / len(v) for name, v in out.items() if v}


def seed_means(seeds):
    means = []
    for values in seeds:
        clean = [v for v in values.values() if v is not None]
        if clean:
            means.append(sum(clean) / len(clean))
    return means


def stdev(values):
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / (len(values) - 1))


def fmt(value, unit="%"):
    if value is None:
        return "-"
    if unit == "%":
        return "%+.2f%%" % (value,)
    return "%.0f" % (value,)


def fmt_mag(value, unit="%"):
    """Magnitude without a sign (standard deviations, confidence intervals)."""
    if value is None:
        return "-"
    if unit == "%":
        return "%.2f%%" % (abs(value),)
    return "%.0f" % (abs(value),)


def paired(a, b):
    """Paired statistics on the per-instance means of two methods."""
    common = [name for name in a if name in b and a[name] is not None and b[name] is not None]
    diffs = [a[name] - b[name] for name in common]
    n = len(diffs)
    mean = sum(diffs) / n if n else None
    sd = stdev(diffs)
    se = sd / math.sqrt(n) if n else None
    wins = sum(1 for d in diffs if d < 0)   # A smaller gap/length -> A better
    losses = sum(1 for d in diffs if d > 0)
    ties = n - wins - losses
    return {
        "n": n, "mean": mean, "sd": sd, "se": se,
        "ci": 1.96 * se if se is not None else None,
        "wins": wins, "losses": losses, "ties": ties,
        "diffs": diffs, "instances": common,
    }


def main(argv=None) -> int:
    args = parse_args(argv)
    unit = "%" if args.metric == "gap" else ""

    methods = {}
    for spec in args.method:
        label, csvs = spec[0], spec[1:]
        seeds = load_method(csvs, args.metric)
        methods[label] = {"seeds": seeds, "mean": per_instance_mean(seeds),
                          "seed_means": seed_means(seeds)}

    lines = []
    title = "Method comparison" + (" (%s group)" % args.group if args.group else "")
    lines.append("## " + title)
    lines.append("")
    lines.append("| method | seeds | mean %s | std across seeds | worst instance |"
                 % ("gap" if unit == "%" else "length",))
    lines.append("|---|---|---|---|---|")
    for label, info in methods.items():
        sm = info["seed_means"]
        worst = max((v for v in info["mean"].values() if v is not None), default=None)
        lines.append("| %s | %d | %s | %s | %s |"
                     % (label, len(info["seeds"]),
                        fmt(sum(sm) / len(sm) if sm else None, unit),
                        fmt_mag(stdev(sm), unit), fmt(worst, unit)))
    lines.append("")

    order = list(methods[list(methods)[0]]["mean"].keys())
    head = ["instance"] + list(methods)
    lines.append("| " + " | ".join(head) + " |")
    lines.append("|" + "|".join(["---"] * len(head)) + "|")
    for name in order:
        cells = [fmt(methods[label]["mean"].get(name), unit) for label in methods]
        lines.append("| %s | %s |" % (name, " | ".join(cells)))
    lines.append("")

    for a_label, b_label in (args.pair or []):
        for label in (a_label, b_label):
            if label not in methods:
                raise SystemExit("--pair %s: unknown label (have %s)"
                                 % (label, ", ".join(methods)))
        stat = paired(methods[a_label]["mean"], methods[b_label]["mean"])
        lines.append("### Paired: %s vs %s  (difference = %s - %s; negative means %s better)"
                     % (a_label, b_label, a_label, b_label, a_label))
        lines.append("")
        lines.append("- instances compared: **%d**" % stat["n"])
        lines.append("- mean difference: **%s**" % fmt(stat["mean"], unit))
        lines.append("- 95%% CI of the mean difference: ±%s" % fmt_mag(stat["ci"], unit))
        lines.append("- standard deviation of the differences: %s" % fmt_mag(stat["sd"], unit))
        lines.append("- %s better on **%d**, %s better on **%d**, ties **%d**"
                     % (a_label, stat["wins"], b_label, stat["losses"], stat["ties"]))
        verdict = "inconclusive"
        if stat["mean"] is not None and stat["ci"] is not None:
            if stat["mean"] + stat["ci"] < 0:
                verdict = "%s is better with 95%% confidence" % a_label
            elif stat["mean"] - stat["ci"] > 0:
                verdict = "%s is better with 95%% confidence" % b_label
        lines.append("- verdict: **%s**" % verdict)
        lines.append("")

    table = "\n".join(lines).rstrip()
    print(table)
    if args.out:
        Path(args.out).write_text(table + "\n", encoding="utf-8")
        print("\nwritten to %s" % (args.out,))
    return 0


if __name__ == "__main__":
    sys.exit(main())
