"""Multi-season crop rotation sequence evaluation."""

from typing import Any, Dict, Iterable, List
from .compatibility import get_rotation_compatibility


def evaluate_rotation_sequence(crops: Iterable[str]) -> Dict[str, Any]:
    sequence = [str(c).lower() for c in crops]
    transitions = [get_rotation_compatibility(a, b) for a, b in zip(sequence, sequence[1:])]
    scores = [float(t.get("compatibility_score", 5.0)) for t in transitions]
    return {
        "sequence": sequence,
        "transitions": transitions,
        "mean_compatibility_score": round(sum(scores) / len(scores), 2) if scores else None,
        "minimum_compatibility_score": min(scores) if scores else None,
        "rotation_class": ("strong" if scores and min(scores) >= 7 else
                           "acceptable" if scores and min(scores) >= 4 else
                           "insufficient_data" if not scores else "weak"),
    }
