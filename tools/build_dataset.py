#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build a frozen TSPLIB working set for the FunSearch project.

``ALL_tsp.tar.gz`` is a *library*, not a dataset. It mixes several distance
conventions, sizes from 14 to 85,900 cities, and a few problem types that are
not TSP at all. ``funsearch_tsp.tsp`` accepts only ``EDGE_WEIGHT_TYPE : EUC_2D``
with a ``NODE_COORD_SECTION``, so the library must be filtered and frozen
before any search runs.

Four sub-commands, in this order::

    # 0. the archive holds *.tsp.gz members: decompress them first
    python tools/build_dataset.py unpack --src all_tsp_files

    # 1. inventory the library (reads the headers, shows what is usable)
    python tools/build_dataset.py scan --src all_tsp_files

    # 2. propose a frozen search / validation / final split, then edit it
    python tools/build_dataset.py split --manifest tsp_files/data/manifest.csv

    # 3. copy the chosen instances into tsp_files/ (dry run first)
    python tools/build_dataset.py select --split tsp_files/data/split.json --dry-run
    python tools/build_dataset.py select --split tsp_files/data/split.json

    # 4. exact verification: every published .opt.tour must reproduce its optimum
    python tools/build_dataset.py verify --lib all_tsp_files

Only the Python standard library and numpy (already a project dependency) are
used, so none of this needs network access or an extra install. The published
optima are embedded below (source: TSPLIB95/tsp/TSP-BEST.html, Reinelt 1991).
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# published optimal tour lengths for the symmetric TSPLIB instances
# source: https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/TSP-BEST.html
# ``dsj1000`` has two published values; the EUC_2D one is kept here.
# --------------------------------------------------------------------------- #
OPT_TEXT = """
a280 2579
ali535 202339
att48 10628
att532 27686
bayg29 1610
bays29 2020
berlin52 7542
bier127 118282
brazil58 25395
brd14051 469385
brg180 1950
burma14 3323
ch130 6110
ch150 6528
d198 15780
d493 35002
d657 48912
d1291 50801
d1655 62128
d2103 80450
d15112 1573084
d18512 645238
dantzig42 699
dsj1000 18659688
eil51 426
eil76 538
eil101 629
fl417 11861
fl1400 20127
fl1577 22249
fl3795 28772
fnl4461 182566
fri26 937
gil262 2378
gr17 2085
gr21 2707
gr24 1272
gr48 5046
gr96 55209
gr120 6942
gr137 69853
gr202 40160
gr229 134602
gr431 171414
gr666 294358
hk48 11461
kroA100 21282
kroB100 22141
kroC100 20749
kroD100 21294
kroE100 22068
kroA150 26524
kroB150 26130
kroA200 29368
kroB200 29437
lin105 14379
lin318 42029
linhp318 41345
nrw1379 56638
p654 34643
pa561 2763
pcb442 50778
pcb1173 56892
pcb3038 137694
pla7397 23260728
pla33810 66048945
pla85900 142382641
pr76 108159
pr107 44303
pr124 59030
pr136 96772
pr144 58537
pr152 73682
pr226 80369
pr264 49135
pr299 48191
pr439 107217
pr1002 259045
pr2392 378032
rat99 1211
rat195 2323
rat575 6773
rat783 8806
rd100 7910
rd400 15281
rl1304 252948
rl1323 270199
rl1889 316536
rl5915 565530
rl5934 556045
rl11849 923288
si175 21407
si535 48450
si1032 92650
st70 675
swiss42 1273
ts225 126643
tsp225 3916
u159 42080
u574 36905
u724 41910
u1060 224094
u1432 152970
u1817 57201
u2152 64253
u2319 234256
ulysses16 6859
ulysses22 7013
usa13509 19982859
vm1084 239297
vm1748 336556
"""

SUPPORTED_EDGE_WEIGHT_TYPE = "EUC_2D"


def opt_table() -> Dict[str, int]:
    table = {}
    for line in OPT_TEXT.strip().splitlines():
        name, value = line.split()
        table[name] = int(value)
    return table


OPT = opt_table()


# --------------------------------------------------------------------------- #
# TSPLIB reading (tolerant: header layouts are not uniform across the library)
# --------------------------------------------------------------------------- #
def parse_header(path: Path) -> Dict[str, object]:
    """Read the header of a TSPLIB ``.tsp`` file without loading the body."""
    info = {
        "name": path.stem,
        "dimension": None,           # type: Optional[int]
        "edge_weight_type": None,    # type: Optional[str]
        "edge_weight_format": None,  # type: Optional[str]
        "has_coords": False,
        "has_weights": False,
    }
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for index, raw in enumerate(handle):
            line = raw.strip()
            if not line:
                continue
            upper = line.upper()
            if upper.startswith("NODE_COORD_SECTION"):
                info["has_coords"] = True
                break
            if upper.startswith("EDGE_WEIGHT_SECTION"):
                info["has_weights"] = True
                break
            if upper.startswith("EOF"):
                break
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip().upper()
                value = value.strip()
                if key == "NAME":
                    info["name"] = value
                elif key == "DIMENSION":
                    try:
                        info["dimension"] = int(float(value))
                    except ValueError:
                        pass
                elif key == "EDGE_WEIGHT_TYPE":
                    info["edge_weight_type"] = value.upper()
                elif key == "EDGE_WEIGHT_FORMAT":
                    info["edge_weight_format"] = value.upper()
            if index > 80:
                break
    return info


def read_instance(path: Path) -> Tuple[List[int], List[Tuple[float, float]]]:
    """Return ``(labels, coords)`` from a ``NODE_COORD_SECTION`` instance.

    The label column is kept because a tour file refers to *labels*, not to
    0-based positions. Stock TSPLIB instances use 1..n, but reading them keeps
    the verification honest instead of assuming.
    """
    labels = []  # type: List[int]
    coords = []  # type: List[Tuple[float, float]]
    inside = False
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            upper = line.upper()
            if not inside:
                if upper.startswith("NODE_COORD_SECTION"):
                    inside = True
                elif upper.startswith("EOF"):
                    break
                continue
            if upper.startswith("EOF") or upper.startswith("DISPLAY_DATA_SECTION"):
                break
            parts = line.split()
            if len(parts) < 3:
                break
            try:
                labels.append(int(float(parts[0])))
                coords.append((float(parts[1]), float(parts[2])))
            except ValueError:
                break
    if not coords:
        raise ValueError("%s: no NODE_COORD_SECTION entries" % path.name)
    return labels, coords


def read_tour(path: Path) -> List[int]:
    """Return the label sequence of a ``.opt.tour`` / ``.tour`` file.

    The layout is not uniform: ``berlin52.opt.tour`` puts one label per line
    while ``rd100.opt.tour`` and ``pr1002.opt.tour`` pack many per line, so
    every integer on a line is consumed until the ``-1`` terminator.
    """
    labels = []  # type: List[int]
    inside = False
    done = False
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            upper = line.upper()
            if not inside:
                if upper.startswith("TOUR_SECTION"):
                    inside = True
                elif upper.startswith("EOF"):
                    break
                continue
            for part in line.split():
                if part in ("-1", "-1.0", "EOF"):
                    done = True
                    break
                try:
                    labels.append(int(float(part)))
                except ValueError:
                    continue
            if done:
                break
    return labels


def size_bucket(n: Optional[int], edges: Tuple[int, int, int]) -> str:
    if n is None:
        return "unknown"
    small, medium, large = edges
    if n <= small:
        return "n<=%d" % small
    if n <= medium:
        return "%d<n<=%d" % (small, medium)
    if n <= large:
        return "%d<n<=%d" % (medium, large)
    return "n>%d" % large


def _opt_for(name: str) -> str:
    value = OPT.get(name)
    return "" if value is None else str(value)


def find_tour(instance: Path, name: str) -> Optional[Path]:
    """Locate the published optimal tour for an instance, if it exists."""
    for candidate in (instance.with_name(name + ".opt.tour"),
                      instance.parent / (instance.stem + ".opt.tour"),
                      instance.with_suffix(".opt.tour")):
        if candidate.exists():
            return candidate
    return None


def clean_name(raw: str) -> str:
    """Normalise a declared NAME.

    A few library files carry the extension in the header (``pa561`` declares
    ``NAME : pa561.tsp``), which would otherwise produce ``pa561.tsp.tsp``.
    """
    name = raw.strip()
    if name.lower().endswith(".tsp"):
        name = name[:-4]
    if name.lower().endswith(".opt"):
        name = name[:-4]
    return name.strip()


def group_of(n: Optional[int], edges: Tuple[int, int, int, int]) -> Optional[str]:
    """Map a size to its frozen group, or None when it exceeds the budget."""
    if n is None:
        return None
    search_max, validation_max, final_max, transfer_max = edges
    if n <= search_max:
        return "search"
    if n <= validation_max:
        return "validation"
    if n <= final_max:
        return "final"
    if n <= transfer_max:
        return "transfer"
    return None


# --------------------------------------------------------------------------- #
# sub-command: unpack
# --------------------------------------------------------------------------- #
def cmd_unpack(args: argparse.Namespace) -> int:
    src = Path(args.src)
    if not src.is_dir():
        sys.stderr.write("unpack: --src %s is not a directory\n" % src)
        return 2
    dest = Path(args.dest) if args.dest else None

    archives = sorted(src.rglob("*.gz"))
    # the archive itself is not a member to expand
    archives = [p for p in archives if p.suffixes[-2:] != [".tar", ".gz"]]
    if not archives:
        print("no *.gz members under %s -- already decompressed, skip this step" % src)
        return 0

    written = 0
    skipped = 0
    for path in archives:
        target = path.with_suffix("")            # a280.tsp.gz -> a280.tsp
        if dest is not None:
            target = dest / target.relative_to(src)
        if target.exists() and not args.force:
            skipped += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(str(path), "rb") as source, open(str(target), "wb") as sink:
            shutil.copyfileobj(source, sink)
        written += 1

    print("decompressed %d files (%d already present, use --force to redo)"
          % (written, skipped))
    if dest is not None:
        print("output -> %s" % dest)
    print("next: python tools/build_dataset.py scan --src %s"
          % (dest if dest is not None else src))
    return 0


# --------------------------------------------------------------------------- #
# sub-command: scan
# --------------------------------------------------------------------------- #
def cmd_scan(args: argparse.Namespace) -> int:
    src = Path(args.src)
    if not src.is_dir():
        sys.stderr.write("scan: --src %s is not a directory\n" % src)
        return 2

    edges = (args.search_max, args.validation_max, args.final_max,
             args.transfer_max)

    # Group the files by declared NAME first: the library contains files whose
    # NAME collides (linhp318 declares NAME : lin318) or carries the extension.
    candidates = []  # type: List[Tuple[str, Path, Dict[str, object]]]
    for path in sorted(src.rglob("*.tsp")):
        info = parse_header(path)
        name = clean_name(str(info["name"])) or path.stem
        candidates.append((name, path, info))

    by_name = {}  # type: Dict[str, List[Path]]
    for name, path, _info in candidates:
        by_name.setdefault(name, []).append(path)
    keep = {}  # type: Dict[str, Path]
    for name, paths in by_name.items():
        exact = [p for p in paths if p.stem == name]
        keep[name] = (exact or paths)[0]

    rows = []
    for name, path, info in candidates:
        dimension = info["dimension"]  # type: Optional[int]
        ewt = info["edge_weight_type"]
        tour = find_tour(path, name)

        reasons = []
        if keep.get(name) != path:
            reasons.append("duplicate NAME (using %s)" % keep[name].name)
        if ewt != SUPPORTED_EDGE_WEIGHT_TYPE:
            reasons.append("EDGE_WEIGHT_TYPE=%s" % (ewt or "missing"))
        if not info["has_coords"]:
            reasons.append("no NODE_COORD_SECTION")
        if name not in OPT:
            reasons.append("no published optimum")
        band = group_of(dimension, edges)
        if band is None and not reasons:
            reasons.append("n>%d, beyond the phase-1 budget" % args.transfer_max)

        rows.append({
            "name": name,
            "file": path.relative_to(src).as_posix(),
            "n": "" if dimension is None else dimension,
            "edge_weight_type": ewt or "",
            "edge_weight_format": info["edge_weight_format"] or "",
            "has_coords": int(bool(info["has_coords"])),
            "opt": _opt_for(name),
            "has_opt_tour": int(bool(tour)),
            "usable": int(not reasons),
            "verifiable": int(bool(tour) and not reasons),
            "group": band or "",
            "size_bucket": size_bucket(dimension, edges[:3]),
            "excluded_because": "; ".join(reasons),
        })

    out = Path(args.manifest)
    out.parent.mkdir(parents=True, exist_ok=True)
    columns = ["name", "file", "n", "edge_weight_type", "edge_weight_format",
               "has_coords", "opt", "has_opt_tour", "usable", "verifiable",
               "group", "size_bucket", "excluded_because"]
    with open(out, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    usable = [row for row in rows if row["usable"] == 1]
    print("scanned %d .tsp files under %s" % (len(rows), src))
    print("  usable (EUC_2D + coords + published optimum) : %d" % len(usable))
    seen = sorted({str(row["edge_weight_type"]) or "missing" for row in rows})
    print("  EDGE_WEIGHT_TYPE values                     : %s" % ", ".join(seen))
    counts = {}  # type: Dict[str, int]
    for row in usable:
        counts[str(row["group"])] = counts.get(str(row["group"]), 0) + 1
    for group in ("search", "validation", "final", "transfer"):
        members = [str(r["name"]) for r in usable if r["group"] == group]
        print("  %-10s %2d : %s" % (group, len(members), " ".join(members)))
    extra = [str(r["name"]) for r in rows if r["excluded_because"].startswith("n>")]
    if extra:
        print("  beyond budget (%d) : %s" % (len(extra), " ".join(extra)))
    print("  verifiable via .opt.tour : %d"
          % sum(1 for row in rows if row["verifiable"] == 1))
    print("manifest -> %s" % out)
    print("next     : python tools/build_dataset.py split --manifest %s" % out)
    return 0


# --------------------------------------------------------------------------- #
# sub-command: split
# --------------------------------------------------------------------------- #
def cmd_split(args: argparse.Namespace) -> int:
    manifest = Path(args.manifest)
    if not manifest.exists():
        sys.stderr.write("split: %s not found -- run `scan` first\n" % manifest)
        return 2
    with open(manifest, "r", encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["usable"] == "1"]

    edges = (args.search_max, args.validation_max, args.final_max,
             args.transfer_max)
    groups = {"search": [], "validation": [], "final": [],
              "transfer": []}  # type: Dict[str, List[str]]
    for row in sorted(rows, key=lambda r: int(r["n"] or 10 ** 9)):
        band = group_of(int(row["n"]) if row["n"] else None, edges)
        if band is not None:
            groups[band].append(row["name"])

    split = {
        "_note": ("Frozen split written by tools/build_dataset.py. `search` drives "
                  "selection, `validation` is reported while developing, `final` is "
                  "reported once, `transfer` is never trained on and only measures "
                  "scale transfer. No instance may appear in two groups."),
        "_criteria": {
            "edge_weight_type": SUPPORTED_EDGE_WEIGHT_TYPE,
            "search_max": args.search_max,
            "validation_max": args.validation_max,
            "final_max": args.final_max,
            "transfer_max": args.transfer_max,
        },
        "search": groups["search"],
        "validation": groups["validation"],
        "final": groups["final"],
        "transfer": groups["transfer"],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(split, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    print("split -> %s" % out)
    for key in ("search", "validation", "final", "transfer"):
        print("  %-10s %2d : %s" % (key, len(groups[key]), " ".join(groups[key])))
    print("edit %s to change the panel, then run `select`" % out)
    return 0


# --------------------------------------------------------------------------- #
# sub-command: select
# --------------------------------------------------------------------------- #
def cmd_select(args: argparse.Namespace) -> int:
    src = Path(args.src)
    dest = Path(args.dest)
    manifest = Path(args.manifest)

    if not src.is_dir():
        sys.stderr.write("select: --src %s is not a directory\n" % src)
        return 2
    if not manifest.exists():
        sys.stderr.write("select: %s not found -- run `scan` first\n" % manifest)
        return 2

    files = {}  # type: Dict[str, str]
    with open(manifest, "r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            files[row["name"]] = row["file"]

    split = json.loads(Path(args.split).read_text(encoding="utf-8"))
    chosen = []  # type: List[Tuple[str, str]]
    seen = {}    # type: Dict[str, str]
    for group in ("search", "validation", "final", "transfer"):
        for name in split.get(group, []):
            if name in seen:
                sys.stderr.write(
                    "select: %s is in both %s and %s -- a frozen split cannot "
                    "share instances\n" % (name, seen[name], group))
                return 2
            seen[name] = group
            chosen.append((group, name))

    missing = [name for _, name in chosen if name not in files]
    if missing:
        sys.stderr.write("select: not in the manifest: %s\n" % ", ".join(missing))
        return 2

    plan = []  # type: List[Tuple[str, str, Path, Path]]
    for group, name in chosen:
        plan.append((group, name, src / files[name], dest / (name + ".tsp")))

    if args.dry_run:
        for group, name, source, target in plan:
            flag = "would overwrite" if target.exists() else "would copy"
            print("%-10s %-12s %s -> %s" % (group, name, flag, target))
        print("dry run: %d files, nothing written" % len(plan))
        return 0

    dest.mkdir(parents=True, exist_ok=True)
    for _group, _name, source, target in plan:
        shutil.copy2(str(source), str(target))
    print("copied %d instances into %s" % (len(plan), dest))

    opt_out = Path(args.opt_out)
    opt_out.parent.mkdir(parents=True, exist_ok=True)
    with open(opt_out, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["name", "group", "n", "opt"])
        for group, name in chosen:
            dimension = parse_header(src / files[name])["dimension"]
            writer.writerow([name, group, "" if dimension is None else dimension,
                             _opt_for(name)])
    print("optimal values -> %s" % opt_out)

    extra = sorted(p.stem for p in dest.glob("*.tsp") if p.stem not in seen)
    if args.prune:
        for stem in extra:
            (dest / (stem + ".tsp")).unlink()
        print("pruned %d instances not in the split: %s"
              % (len(extra), " ".join(extra) if extra else "-"))
    elif extra:
        print("note: %d instances in %s are not in the split: %s"
              % (len(extra), dest, " ".join(extra)))
        print("      pass --prune to remove them")
    return 0


# --------------------------------------------------------------------------- #
# sub-command: table
# --------------------------------------------------------------------------- #
def cmd_table(args: argparse.Namespace) -> int:
    """Write a human-readable table of the frozen split (for the report)."""
    manifest = Path(args.manifest)
    split_file = Path(args.split)
    for path in (manifest, split_file):
        if not path.exists():
            sys.stderr.write("table: %s not found\n" % path)
            return 2

    with open(manifest, "r", encoding="utf-8", newline="") as handle:
        rows = {row["name"]: row for row in csv.DictReader(handle)
                if row["usable"] == "1"}
    split = json.loads(split_file.read_text(encoding="utf-8"))

    titles = {"search": "search (drives selection)",
              "validation": "validation (reported while developing)",
              "final": "final (reported once)",
              "transfer": "transfer (never trained on)"}
    lines = ["# Frozen instance split", ""]
    lines.append("Generated by `tools/build_dataset.py table` from "
                 "`tsp_files/data/manifest.csv` and `tsp_files/data/split.json`.")
    lines.append("")
    total = 0
    for group in ("search", "validation", "final", "transfer"):
        names = split.get(group, [])
        total += len(names)
        lines.append("%s: %d instances" % (titles[group], len(names)))
    lines.append("")
    for group in ("search", "validation", "final", "transfer"):
        names = sorted(split.get(group, []),
                       key=lambda name: int(rows[name]["n"]) if name in rows else 0)
        lines.append("## %s" % titles[group])
        lines.append("")
        lines.append("| instance | n | published opt | .opt.tour |")
        lines.append("|---|---|---|---|")
        for name in names:
            row = rows.get(name)
            if row is None:
                lines.append("| %s | ? | ? | ? |" % name)
                continue
            lines.append("| %s | %s | %s | %s |"
                         % (name, row["n"], row["opt"] or "-",
                            "yes" if row["has_opt_tour"] == "1" else "no"))
        lines.append("")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print("table -> %s (%d instances)" % (out, total))
    return 0


# --------------------------------------------------------------------------- #
# sub-command: verify
# --------------------------------------------------------------------------- #
def cmd_verify(args: argparse.Namespace) -> int:
    import numpy as np

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from funsearch_tsp.tsp import pairwise_dist

    lib = Path(args.lib)
    work = Path(args.src)
    if not work.is_dir():
        sys.stderr.write("verify: --src %s is not a directory\n" % work)
        return 2

    rows = []  # type: List[Tuple[str, object, object, object, str]]
    passed = failed = skipped = 0
    for path in sorted(work.glob("*.tsp")):
        name = path.stem
        tour_file = lib / (name + ".opt.tour")
        if not tour_file.exists():
            skipped += 1
            rows.append((name, "-", "-", "-", "no .opt.tour"))
            continue
        labels, coords = read_instance(path)
        n = len(labels)
        tour = read_tour(tour_file)
        if len(tour) != n or len(set(tour)) != n:
            failed += 1
            rows.append((name, n, len(tour), _opt_for(name) or "-", "FAIL (tour length)"))
            continue
        dist = pairwise_dist(np.asarray(coords, dtype=np.float64))
        position = {label: index for index, label in enumerate(labels)}
        total = 0
        broken = False
        for step in range(n):
            a = position.get(tour[step])
            b = position.get(tour[(step + 1) % n])
            if a is None or b is None:
                broken = True
                break
            total += int(dist[a, b])
        if broken:
            failed += 1
            rows.append((name, n, total, _opt_for(name) or "-", "FAIL (label)"))
            continue
        expected = OPT.get(name)
        if expected is None:
            rows.append((name, n, total, "?", "unknown optimum"))
        elif total == expected:
            passed += 1
            rows.append((name, n, total, expected, "ok"))
        else:
            failed += 1
            rows.append((name, n, total, expected, "FAIL"))

    print("%-12s %8s %10s %10s  %s" % ("instance", "n", "tour len", "opt", "verdict"))
    for row in rows:
        print("%-12s %8s %10s %10s  %s" % row)
    print("\nverified ok %d, failed %d, no tour file %d"
          % (passed, failed, skipped))
    if failed:
        print("a mismatch means the distance matrix is wrong: check the nint "
              "rounding, the coordinate order, and that the tour is closed")
        return 1
    print("the distance function reproduces every published optimum it was given")
    return 0


# --------------------------------------------------------------------------- #
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the TSPLIB working set for the FunSearch project.")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("unpack", help="decompress the *.tsp.gz / *.opt.tour.gz members")
    p.add_argument("--src", required=True)
    p.add_argument("--dest", default="")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_unpack)

    p = sub.add_parser("scan", help="inventory a library into the manifest CSV")
    p.add_argument("--src", required=True, help="directory holding the *.tsp library")
    p.add_argument("--manifest", default="tsp_files/data/manifest.csv")
    p.add_argument("--search-max", type=int, default=100)
    p.add_argument("--validation-max", type=int, default=200)
    p.add_argument("--final-max", type=int, default=500)
    p.add_argument("--transfer-max", type=int, default=2000)
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("split", help="propose a frozen search/validation/final split")
    p.add_argument("--manifest", default="tsp_files/data/manifest.csv")
    p.add_argument("--out", default="tsp_files/data/split.json")
    p.add_argument("--search-max", type=int, default=100)
    p.add_argument("--validation-max", type=int, default=200)
    p.add_argument("--final-max", type=int, default=500)
    p.add_argument("--transfer-max", type=int, default=2000)
    p.set_defaults(func=cmd_split)

    p = sub.add_parser("select", help="copy the split's instances into tsp_files/")
    p.add_argument("--src", default=os.environ.get("TSPLIB_TSP_DIR", ""))
    p.add_argument("--manifest", default="tsp_files/data/manifest.csv")
    p.add_argument("--split", default="tsp_files/data/split.json")
    p.add_argument("--dest", default="tsp_files")
    p.add_argument("--opt-out", default="tsp_files/data/optimal_values.csv")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--prune", action="store_true",
                   help="delete .tsp files in --dest that are not in the split")
    p.set_defaults(func=cmd_select)

    p = sub.add_parser("table", help="write a markdown table of the frozen split")
    p.add_argument("--manifest", default="tsp_files/data/manifest.csv")
    p.add_argument("--split", default="tsp_files/data/split.json")
    p.add_argument("--out", default="tsp_files/data/split.md")
    p.set_defaults(func=cmd_table)

    p = sub.add_parser("verify", help="check .opt.tour files against the optima")
    p.add_argument("--lib", default=os.environ.get("TSPLIB_TSP_DIR", ""))
    p.add_argument("--src", default="tsp_files")
    p.set_defaults(func=cmd_verify)

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 2

    if args.command in ("scan", "unpack", "select"):
        if not args.src:
            sys.stderr.write("%s: pass --src (or set TSPLIB_TSP_DIR)\n" % args.command)
            return 2
    if args.command == "select" and args.dest:
        pass
    if args.command == "verify" and not args.lib:
        sys.stderr.write("verify: pass --lib (or set TSPLIB_TSP_DIR)\n")
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
