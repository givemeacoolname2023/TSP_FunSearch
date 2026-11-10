"""Registry of the interchangeable FunSearch skeletons.

Both skeletons expose the same small interface so that ``sandbox``,
``evaluate``, ``prompt`` and ``run`` do not care which one is in use:

    NAME            short name used on the command line ("greedy" / "ils")
    EVOLVED_NAME    name of the one function FunSearch may rewrite
    SIGNATURE_ARGS  its argument list
    SEED            the trivial seed program
    SKELETON_WITH_STUB  prompt view of the frozen skeleton
    build_source(code) -> str
    check_signature(code) -> None
    DEFAULT_BASELINE  "nn" (greedy) or "random" (ils): what score 0 means
"""
from __future__ import annotations

from . import skeleton, skeleton_ils

_REGISTRY = {
    skeleton.NAME: skeleton,
    skeleton_ils.NAME: skeleton_ils,
}

#: The skeleton a program belongs to, guessed from the function it defines.
_BY_EVOLVED = {
    skeleton.EVOLVED_NAME: skeleton,
    skeleton_ils.EVOLVED_NAME: skeleton_ils,
}

DEFAULT = skeleton_ils.NAME


def get(name=None):
    """Return the skeleton module for ``name`` (default: the main ILS one)."""
    if name is None:
        return _REGISTRY[DEFAULT]
    key = str(name).strip().lower()
    if key not in _REGISTRY:
        raise KeyError(
            "unknown skeleton %r (choose from %s)"
            % (name, ", ".join(sorted(_REGISTRY)))
        )
    return _REGISTRY[key]


def names():
    return sorted(_REGISTRY)


def detect(code: str):
    """Guess the skeleton from the source: ``destroy_priority`` means ILS."""
    if "def destroy_priority" in (code or ""):
        return skeleton_ils
    if "def priority" in (code or ""):
        return skeleton
    return None
