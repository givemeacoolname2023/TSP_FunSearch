"""Draw the three report figures from what is already in ``runs/``.

    python tools/plot_figures.py
    python tools/plot_figures.py --groups final --out-dir runs/figures

F1  convergence:  score of every candidate vs. the number of candidates tried,
                   one curve per seed, for the LLM and for the random-weight
                   control.
F2  improvement ladder: mean gap of the 14 methods on a split group, so the
                   contribution of each design layer is readable at a glance.
F3  paired scatter: per-instance gap of the evolved operator vs. the control
                   (and their raw-feature variants); points near the diagonal
                   mean "no systematic difference".

Nothing is recomputed here: the numbers come from the same CSVs that
``tools/summarize.py`` reads and from the ``programs.jsonl`` logs.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")           # headless: only PNG files are produced
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np               # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TOOLS = Path(__file__).resolve().parent
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import make_tables  # noqa: E402
import summarize    # noqa: E402

#: How the 14 methods are grouped, and the colour each group gets.
GROUPS_OF = [
    ("constructive", ["nearest-ins", "cheapest-ins", "farthest-ins"], "#c44e52"),
    ("constructive+LS", ["nearest-ins-ls", "cheapest-ins-ls", "farthest-ins-ls"], "#dd8452"),
    ("NN+LS", ["lsonly"], "#937860"),
    ("same skeleton (destroy ops)", ["random", "worst", "related"], "#55a868"),
    ("evolved (LLM)", ["llm", "llm-raw"], "#4c72b0"),
    ("random-weight control", ["control", "control-raw"], "#8172b3"),
]

#: Display labels (kept short so they fit on the y axis).
LABELS = {
    "nearest-ins": "nearest insertion",
    "cheapest-ins": "cheapest insertion",
    "farthest-ins": "farthest insertion",
    "nearest-ins-ls": "nearest ins. + LS",
    "cheapest-ins-ls": "cheapest ins. + LS",
    "farthest-ins-ls": "farthest ins. + LS",
    "lsonly": "NN + LS (no ILS loop)",
    "random": "ILS, random removal (seed)",
    "worst": "ILS, worst removal",
    "related": "ILS, related removal",
    "llm": "ILS, LLM operator (free)",
    "llm-raw": "ILS, LLM operator (raw)",
    "control": "ILS, random weights (free)",
    "control-raw": "ILS, random weights (raw)",
}

SEED_PATTERN = {"llm": "*_ils_s{}", "control": "*_ctl{}"}


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python tools/plot_figures.py",
        description="Render the report figures from runs/ (no evaluation is performed).",
    )
    parser.add_argument("--runs-dir", default=str(ROOT / "runs"))
    parser.add_argument("--out-dir", default=str(ROOT / "runs" / "figures"))
    parser.add_argument("--groups", nargs="+", default=None,
                        help="split groups used by F2/F3 (default: search + final)")
    parser.add_argument("--dpi", type=int, default=150)
    return parser.parse_args(argv)


def load_programs(path: Path):
    """[(attempt, ok, score)] from one run's programs.jsonl."""
    rows = []
    if not path.is_file():
        return rows
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            rows.append((int(record.get("attempt", len(rows) + 1)),
                         bool(record.get("ok")),
                         float(record.get("score") or 0.0)))
    return rows


def find_run(runs_dir: Path, pattern: str):
    """Newest directory matching a seed pattern (e.g. *_ctl2)."""
    hits = sorted(p for p in runs_dir.glob(pattern) if p.is_dir())
    return hits[-1] if hits else None


# ----------------------------------------------------------------- F1
def figure_convergence(runs_dir: Path, out_path: Path, dpi: int) -> bool:
    data = {}
    for name, template in SEED_PATTERN.items():
        series = []
        for seed in (0, 1, 2):
            run = find_run(runs_dir, template.format(seed))
            if run is None:
                continue
            rows = load_programs(run / "programs.jsonl")
            if rows:
                series.append((seed, run.name, rows))
        if series:
            data[name] = series
    if not data:
        print("  ! F1: no programs.jsonl found, skipped")
        return False

    fig, axes = plt.subplots(1, len(data), figsize=(6.2 * len(data), 4.2), squeeze=False)
    for axis, (name, series) in zip(axes[0], data.items()):
        colour = "#4c72b0" if name == "llm" else "#8172b3"
        for seed, _run_name, rows in series:
            attempts = [a for a, _ok, _s in rows]
            scores = [s for _a, ok, s in rows if ok]
            attempts_ok = [a for a, ok, _s in rows if ok]
            axis.scatter(attempts_ok, scores, s=14, alpha=0.30, color=colour,
                         edgecolors="none", label=None)
            best, curve = -np.inf, []
            for _a, ok, score in rows:
                if ok:
                    best = max(best, score)
                curve.append(best if best > -np.inf else np.nan)
            axis.plot(attempts, curve, color=colour, lw=1.8, alpha=0.9,
                      label="seed %d" % seed)
        axis.axhline(0.0, color="black", lw=1.0, ls="--")
        axis.text(0.015, 0.03, "seed program (random removal)", transform=axis.transAxes,
                  fontsize=7.5, color="black", alpha=0.75)
        axis.set_xlabel("candidate program index (API attempts)")
        axis.set_ylabel("score vs. the seed program")
        title = "LLM-evolved operator" if name == "llm" else "random-weight control"
        axis.set_title("%s (thin line = best so far)" % (title,), fontsize=10)
        axis.grid(alpha=0.25, lw=0.6)
        axis.legend(fontsize=7.5, loc="lower right")
    fig.suptitle("F1 - convergence on the search group (40 candidates per seed)", fontsize=11)
    fig.tight_layout(rect=(0.01, 0, 1, 0.94))
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
    print("  F1 -> %s" % (out_path,))
    return True


# ----------------------------------------------------------------- F2
def figure_ladder(found, groups, out_path: Path, dpi: int) -> bool:
    panels = []
    for group in groups:
        means = {}
        base = found["baselines"][group]
        for method, path in base.items():
            means[method] = summarize.per_instance_mean(
                summarize.load_method([str(path)], "gap"))
        for column, paths in found["stochastic"][group].items():
            means[column] = summarize.per_instance_mean(
                summarize.load_method([str(p) for p in paths], "gap"))
        if means:
            panels.append((group, means))
    if not panels:
        print("  ! F2: nothing to plot, skipped")
        return False

    fig, axes = plt.subplots(1, len(panels), figsize=(7.2 * len(panels), 5.6), squeeze=False)
    for axis, (group, means) in zip(axes[0], panels):
        rows = []          # (value, label, colour)
        for group_name, methods, colour in GROUPS_OF:
            for method in methods:
                if method in means and means[method]:
                    value = float(np.mean(list(means[method].values())))
                    rows.append((value, LABELS.get(method, method), colour))
        rows.sort(key=lambda r: r[0])
        values = [r[0] for r in rows]
        labels = [r[1] for r in rows]
        colours = [r[2] for r in rows]
        positions = np.arange(len(rows))
        axis.barh(positions, values, color=colours, height=0.72)
        for pos, value in zip(positions, values):
            axis.text(value + max(values) * 0.012, pos, "%.2f%%" % (value,),
                      va="center", fontsize=7.5)
        axis.set_yticks(positions)
        axis.set_yticklabels(labels, fontsize=8)
        axis.set_xlabel("mean gap to the published optimum (%)  -- lower is better")
        axis.set_title("%s group (%d instances)" % (group, _count_instances(means)), fontsize=10)
        axis.grid(axis="x", alpha=0.25, lw=0.6)
        axis.set_xlim(0, max(values) * 1.16)

        # The interesting differences (0.6% vs 3.5%) are invisible on a linear
        # axis dominated by the 20% construction bars, so the ILS family gets a
        # zoomed inset instead of a second figure.
        low = [r for r in rows if r[0] <= 4.0]
        if 2 < len(low) < len(rows):
            inset = axis.inset_axes([0.47, 0.06, 0.50, 0.40])
            low_pos = np.arange(len(low))
            inset.barh(low_pos, [r[0] for r in low], color=[r[2] for r in low], height=0.7)
            inset.set_yticks(low_pos)
            inset.set_yticklabels([r[1] for r in low], fontsize=6)
            inset.set_xlim(0, max(r[0] for r in low) * 1.25)
            inset.tick_params(axis="x", labelsize=6)
            inset.grid(axis="x", alpha=0.2, lw=0.5)
            inset.set_title("zoom: the ILS family", fontsize=7)
            for pos, row in zip(low_pos, low):
                inset.text(row[0] + max(r[0] for r in low) * 0.03, pos,
                           "%.2f" % (row[0],), va="center", fontsize=5.5)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _n, _m, c in GROUPS_OF]
    fig.legend(handles, [g for g, _m, _c in GROUPS_OF], loc="lower center", ncol=3,
               fontsize=8, frameon=False)
    fig.suptitle("F2 - improvement ladder: what each design layer is worth", fontsize=11)
    fig.tight_layout(rect=(0, 0.06, 1, 0.94))
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
    print("  F2 -> %s" % (out_path,))
    return True


def _count_instances(means):
    for values in means.values():
        return len(values)
    return 0


# ----------------------------------------------------------------- F3
def figure_paired(found, group, out_path: Path, dpi: int) -> bool:
    seeds = found["stochastic"][group]
    pairs = [("control", "llm", "scale-free features"),
             ("control-raw", "llm-raw", "raw distance features")]
    usable = [(x, y, title) for x, y, title in pairs if x in seeds and y in seeds]
    if not usable:
        print("  ! F3: need both a control and an llm column in %s, skipped" % (group,))
        return False

    fig, axes = plt.subplots(1, len(usable), figsize=(5.6 * len(usable), 5.2), squeeze=False)
    for axis, (left, right, title) in zip(axes[0], usable):
        a = summarize.per_instance_mean(summarize.load_method(
            [str(p) for p in seeds[left]], "gap"))
        b = summarize.per_instance_mean(summarize.load_method(
            [str(p) for p in seeds[right]], "gap"))
        common = sorted(set(a) & set(b))
        xs = np.array([a[n] for n in common])
        ys = np.array([b[n] for n in common])
        stats = summarize.paired(b, a)      # difference = llm - control
        limit = max(xs.max(), ys.max()) * 1.15
        axis.plot([0, limit], [0, limit], color="black", lw=1.0, ls="--", alpha=0.7)
        axis.scatter(xs, ys, s=38, color="#4c72b0", edgecolors="white", linewidths=0.6, zorder=3)
        spread = max(xs.max(), ys.max())
        for name, x, y in zip(common, xs, ys):
            if abs(x - y) > 0.18 * spread:
                axis.annotate(name, (x, y), fontsize=6.5, alpha=0.75,
                              xytext=(3, 3), textcoords="offset points")
        axis.set_xlim(0, limit)
        axis.set_ylim(0, limit)
        axis.set_aspect("equal")
        axis.set_xlabel("random-weight control gap (%)")
        axis.set_ylabel("LLM operator gap (%)")
        axis.set_title("%s\nLLM - control = %+.2f%% (95%% CI +/-%.2f%%), n=%d, %dW/%dL/%dT"
                       % (title, stats["mean"], stats["ci"], stats["n"],
                          stats["wins"], stats["losses"], stats["ties"]),
                       fontsize=8.5)
        axis.grid(alpha=0.25, lw=0.6)
        axis.text(0.04, 0.93, "below the diagonal = LLM better",
                  transform=axis.transAxes, fontsize=7.5, style="italic", alpha=0.8)
    fig.suptitle("F3 - per-instance paired comparison on the %s group" % (group,), fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
    print("  F3 -> %s" % (out_path,))
    return True


def _collect_means(found, group):
    means = {}
    base = found["baselines"][group]
    for method, path in base.items():
        means[method] = summarize.per_instance_mean(
            summarize.load_method([str(path)], "gap"))
    for column, paths in found["stochastic"][group].items():
        means[column] = summarize.per_instance_mean(
            summarize.load_method([str(p) for p in paths], "gap"))
    return means


def figure_ladder_paper(found, group, out_path: Path, dpi: int = 300) -> bool:
    """Single-panel version of F2 sized for a 16 cm column in the report.

    The two-panel PNG is meant for the screen; at report width its axis labels
    would be ~3 pt, so the paper copy uses one panel and larger type.
    """
    means = _collect_means(found, group)
    rows = []
    for _group_name, methods, colour in GROUPS_OF:
        for method in methods:
            if method in means and means[method]:
                rows.append((float(np.mean(list(means[method].values()))),
                             LABELS.get(method, method), colour))
    if not rows:
        print("  ! F2-paper: nothing to plot, skipped")
        return False
    rows.sort(key=lambda r: r[0])
    values = [r[0] for r in rows]
    labels = [r[1] for r in rows]
    colours = [r[2] for r in rows]

    fig, axis = plt.subplots(figsize=(7.2, 3.1))
    positions = np.arange(len(rows))
    axis.barh(positions, values, color=colours, height=0.76)
    for pos, value in zip(positions, values):
        axis.text(value + max(values) * 0.015, pos, "%.2f" % (value,),
                  va="center", fontsize=6.0)
    axis.set_yticks(positions)
    axis.set_yticklabels(labels, fontsize=6.2)
    axis.set_xlabel("mean gap to the published optimum (%)", fontsize=7)
    axis.set_title("%s group (%d instances)" % (group, _count_instances(means)), fontsize=7.5)
    axis.grid(axis="x", alpha=0.25, lw=0.5)
    axis.set_xlim(0, max(values) * 1.22)
    axis.tick_params(axis="x", labelsize=6)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _n, _m, c in GROUPS_OF]
    short = ["constructive", "constructive+LS", "NN+LS", "destroy ops", "evolved", "control"]
    axis.legend(handles, short, fontsize=5.4, ncol=2, frameon=False,
                loc="lower right", handlelength=1.1, columnspacing=0.8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
    print("  F2 (paper) -> %s" % (out_path,))
    return True


def main(argv=None) -> int:
    args = parse_args(argv)
    runs_dir = Path(args.runs_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    groups = args.groups or ["search", "final"]

    found = make_tables.discover(runs_dir)
    print("rendering figures into %s" % (out_dir,))
    done = [
        figure_convergence(runs_dir, out_dir / "F1_convergence.png", args.dpi),
        figure_ladder(found, groups, out_dir / "F2_improvement_ladder.png", args.dpi),
        figure_ladder_paper(found, "final", out_dir / "F2_ladder_paper.png"),
        figure_paired(found, "final", out_dir / "F3_paired_final.png", args.dpi),
    ]
    print("done: %d/%d figures" % (sum(1 for d in done if d), len(done)))
    return 0 if any(done) else 1


if __name__ == "__main__":
    sys.exit(main())
