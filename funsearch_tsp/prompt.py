"""Prompt construction (best-shot prompting) and code extraction.

The prompt mirrors the structure of the program skeleton, as in Fig. 2a of the
FunSearch paper: the frozen skeleton, the interface of the evolved function,
then ``k = 2`` previously sampled programs renamed ``<name>_v0`` and
``<name>_v1`` in increasing order of score, and finally a request for
``<name>_v2``.

Two skeletons are supported (see ``funsearch_tsp/skeletons.py``): the frozen
greedy construction (``priority``) and the frozen ILS (``destroy_priority``).
"""
from __future__ import annotations

import ast
import re
from typing import List, Sequence

from . import skeleton
from .programs_database import Program

_FENCE_RE = re.compile(r"```(?:python|py)?\s*\n?(.*?)(?:```|$)", re.DOTALL)
_DEF_RE = re.compile(
    r"^[ \t]*def[ \t]+(?:destroy_)?priority(?:_v\d+)?[ \t]*\(", re.MULTILINE
)
_ANY_DEF_RE = re.compile(r"def[ \t]+(?:destroy_)?priority(?:_v\d+)?[ \t]*\(")
_DEF_NAME_RE = re.compile(r"def[ \t]+(?:destroy_)?priority(?:_v\d+)?[ \t]*\(")


def _rename_function(code: str, new_name: str = "priority") -> str:
    return _DEF_NAME_RE.sub("def %s(" % (new_name,), code, count=1)


def _slice_from_def(text: str) -> str:
    """Cut the reply down to the function definition (tolerating leading prose)."""
    match = _DEF_RE.search(text)
    if match is None:
        match = _ANY_DEF_RE.search(text)  # e.g. "Sure. def priority(...):" on one line
    if match is None:
        return ""
    return text[match.start():]


def _trim_to_compilable(code: str) -> str:
    """Drop trailing prose the LLM may have appended after the function body."""
    lines = code.rstrip().splitlines()
    while lines:
        candidate = "\n".join(lines).rstrip()
        if candidate.strip():
            try:
                ast.parse(candidate)
                return candidate + "\n"
            except SyntaxError:
                pass
        lines.pop()
        while lines and not lines[-1].strip():
            lines.pop()
    return ""


def extract_priority(response: str, skel=None) -> str:
    """Pull the evolved function out of an LLM reply.

    Prefers a fenced code block, falls back to the raw reply, renames
    ``<name>_v<k>`` to the frozen name and trims trailing prose. Raises
    ``ValueError`` when no compilable function is found.
    """
    skel = skel if skel is not None else skeleton
    wanted = skel.EVOLVED_NAME
    if not response or not response.strip():
        raise ValueError("empty LLM response")

    blocks = [b for b in _FENCE_RE.findall(response) if b.strip()]
    sources = blocks + [response] if blocks else [response]
    for text in sources:
        code = _slice_from_def(text)
        if not code:
            continue
        code = _rename_function(code, wanted)
        code = _trim_to_compilable(code)
        if not code:
            continue
        try:
            skel.check_signature(code)
        except ValueError:
            continue
        return code
    raise ValueError("no compilable `%s` function found in the LLM response" % (wanted,))


def _strip_docstring(code: str) -> str:
    """Render a sampled program in the prompt without its docstring."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code.strip()
    if not tree.body or not isinstance(tree.body[0], ast.FunctionDef):
        return code.strip()
    func = tree.body[0]
    if func.body and isinstance(func.body[0], ast.Expr) and isinstance(
        getattr(func.body[0], "value", None), ast.Constant
    ) and isinstance(func.body[0].value.value, str):
        lines = code.strip().splitlines()
        start = func.body[0].lineno - 1
        end = func.body[0].end_lineno
        return "\n".join(lines[:start] + lines[end:])
    return code.strip()


_IMPORT_RULES = [
    "- Only `numpy` (as np), `math`, `random`, `itertools`, `collections`, `functools`,",
    "  `operator` and `statistics` may be imported. No file, network or system access.",
]


def _greedy_prompt(programs: Sequence[Program], train_names: Sequence[str], skel) -> List[str]:
    return [
        "## Task",
        "The skeleton below builds a tour greedily: starting at city 0, it repeatedly appends",
        "the unvisited city with the highest score returned by `priority`. Your job is to write",
        "the body of `priority` so that the resulting tours are as short as possible.",
        "The skeleton is FIXED - it must not be modified, copied or redefined.",
        "",
        "## Frozen skeleton",
        "```python",
        skel.SKELETON_WITH_STUB.rstrip(),
        "```",
        "",
        "## How programs are scored",
        "Each program runs the skeleton on these training instances: %s."
        % (", ".join(train_names),),
        "For instance i, with L_i the length of the tour the program builds and L_nn_i the",
        "length built by the nearest-neighbour baseline (the seed program), the per-instance",
        "score is s_i = (L_nn_i - L_i) / L_nn_i. The program's score is the mean of the s_i:",
        "higher is better, 0.0 means 'exactly as good as nearest neighbour', and a perfect",
        "tour would give 1.0. Tour lengths use TSPLIB EUC_2D distances (rounded to integers)",
        "and the tour is closed, i.e. the last city is connected back to city 0.",
        "",
        "## Previously sampled implementations (best-shot)",
        "Below are %d implementations sampled from this island, ordered from the lowest to the"
        % (len(programs),),
        "highest score. Use them as inspiration: keep what works and fix what does not.",
        "",
    ]


def _ils_prompt(programs: Sequence[Program], train_names: Sequence[str], skel,
                features=None, scaled: bool = False) -> List[str]:
    stub = (skel.build_stub(features, scaled)
            if hasattr(skel, "build_stub") else skel.SKELETON_WITH_STUB)
    return [
        "## Task",
        "The skeleton below solves a TSP instance with an iterated local search (ILS):",
        "a nearest-neighbour tour is improved with 2-opt and Or-opt, then the following",
        "steps are repeated for a fixed number of rounds:",
        "  (a) destroy - remove a set of cities from the tour,",
        "  (b) repair  - reinsert each removed city at its cheapest position,",
        "  (c) improve - run 2-opt and Or-opt again,",
        "  (d) accept  - keep the new tour if it is not longer.",
        "",
        "Your job is to write the body of `destroy_priority`, which decides WHICH cities are",
        "removed in step (a). The number of removed cities and every other operator are fixed",
        "by the skeleton. Removing a well-chosen set of cities lets the repair rebuild a whole",
        "region of the tour; removing a poor set wastes the round.",
        "The skeleton is FIXED - it must not be modified, copied or redefined.",
        "",
        "## Frozen skeleton",
        "```python",
        stub.rstrip(),
        "```",
        "",
        "## How programs are scored",
        "Each program runs the skeleton on these training instances: %s."
        % (", ".join(train_names),),
        "For instance i, with L_i the tour length the program reaches and L_seed_i the length",
        "reached by the seed program (the same ILS driven by *random* destruction), the",
        "per-instance score is s_i = (L_seed_i - L_i) / L_seed_i. The program's score is the",
        "mean of the s_i: higher is better, 0.0 means 'exactly as good as random destruction',",
        "and a perfect tour would give 1.0. Tour lengths use TSPLIB EUC_2D distances (rounded",
        "to integers) and the tour is closed.",
        "",
        "## Previously sampled implementations (best-shot)",
        "Below are %d implementations sampled from this island, ordered from the lowest to the"
        % (len(programs),),
        "highest score. Use them as inspiration: keep what works and fix what does not.",
        "",
    ]


def build_prompt(
    programs: Sequence[Program],
    train_names: Sequence[str],
    baseline: dict,
    round_index: int = 0,
    skel=None,
    features=None,
    scaled: bool = False,
) -> str:
    """Best-shot prompt from ``programs`` (sorted internally by ascending score)."""
    skel = skel if skel is not None else skeleton
    wanted = skel.EVOLVED_NAME
    ordered = sorted(programs, key=lambda p: p.score)
    is_ils = getattr(skel, "NAME", "greedy") == "ils"

    header = [
        "You are an expert in combinatorial optimization and Python programming.",
        "We are using FunSearch to discover a heuristic for the Traveling Salesman Problem (TSP).",
        "",
    ]
    task = (
        _ils_prompt(ordered, train_names, skel, features, scaled)
        if is_ils
        else _greedy_prompt(ordered, train_names, skel)
    )

    body = []  # type: List[str]
    for version, program in enumerate(ordered):
        lengths = ", ".join(
            "%s=%s" % (name, program.lengths.get(name, "?")) for name in train_names
        )
        body.extend(
            [
                "### %s_v%d" % (wanted, version),
                "# score = %.6f" % (program.score,),
                "# tour lengths: %s" % (lengths,),
                "```python",
                _rename_function(_strip_docstring(program.code), "%s_v%d" % (wanted, version)),
                "```",
                "",
            ]
        )

    if is_ils:
        from . import skeleton_ils

        enabled = skeleton_ils.normalize_features(features)
        feature_lines = [
            "- `features` is a dict of %d arrays of shape (n,), all indexed by CITY ID:"
            % (len(enabled),),
        ]
        for name in enabled:
            feature_lines.append("  `%s` : %s" % (name, skeleton_ils.FEATURE_HELP[name]))
        if scaled:
            feature_lines.append(
                "  The distance-like features are in RAW distance units (not normalised).")
        else:
            feature_lines.append(
                "  The distance-like features are divided by the current average edge length,")
            feature_lines.append(
                "  so a program tuned on small instances behaves the same on large ones.")
            feature_lines.append("  The raw distance matrix is NOT available.")

        ideas = [
            "Ideas that help in large-neighbourhood search:",
        ]
        if "related" in enabled:
            ideas.append("- removing a spatially related cluster (`related`),")
        if "saving" in enabled:
            ideas.append("- removing the cities whose removal saves the most length (`saving`),")
        if "density" in enabled:
            ideas.append("- penalising cities in dense regions (`density`),")
        if "angle" in enabled:
            ideas.append("- preferring sharp turns (`angle`),")
        if "pos" in enabled:
            ideas.append("- spreading the removals along the tour instead of clustering them"
                         " (`pos`),")
        if "noise" in enabled:
            ideas.append("- breaking ties with `noise`,")
        ideas.append("and combining several of them with weights you choose.")

        footer = [
            "## Your task",
            "Write a NEW implementation called `%s_v%d` (a strictly better destroy operator)."
            % (wanted, len(ordered)),
            "Requirements:",
            "- Exactly the same signature: %s_v%d(features)" % (wanted, len(ordered)),
        ] + feature_lines + [
            "- Return a numpy array of exactly n finite scores; the k highest are removed.",
            "- Only the relative order of the scores matters.",
        ] + _IMPORT_RULES + [
            "- Prefer short, readable, deterministic code: shorter programs are sampled more often.",
            "",
        ] + ideas + [
            "",
            "Answer with ONE Python code block containing only the function definition of",
            "`%s_v%d`. No explanations, no tests, no example usage, no I/O."
            % (wanted, len(ordered)),
        ]
    else:
        footer = [
            "## Your task",
            "Write a NEW implementation called `priority_v%d` (a strictly better heuristic)."
            % (len(ordered),),
            "Requirements:",
            "- Exactly the same signature: priority_v%d(current, candidates, visited, dist, coords, step, n)"
            % (len(ordered),),
            "- Return a numpy array with exactly one finite score per entry of `candidates`,",
            "  in the same order (use `np.asarray(..., dtype=float)` results or plain numpy ops).",
        ] + _IMPORT_RULES + [
            "- Any finite score scale is fine; only the relative order of the scores matters.",
            "- Prefer short, readable, deterministic code: shorter programs are sampled more often.",
            "",
            "Ideas that have helped on greedy TSP constructions include: breaking distance ties",
            "with a secondary criterion, look-ahead (cost of the next hop after choosing a city),",
            "penalising cities that would become isolated, using the angle or direction of travel,",
            "and scaling the distance term by the fraction of the tour already built (step / n).",
            "",
            "Answer with ONE Python code block containing only the function definition of",
            "`priority_v%d`. No explanations, no tests, no example usage, no I/O."
            % (len(ordered),),
        ]

    return "\n".join(header + task + body + footer)
