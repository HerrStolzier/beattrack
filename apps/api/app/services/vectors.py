"""Decode PostgREST vectors at the boundary, without accepting corrupt numbers."""

import json
import math


def parse_vector(raw, dimensions: int | None = None) -> list[float] | None:
    """Return finite numbers or None for missing/malformed data.

    A JSON object, boolean, nested array or numeric string inside the vector is
    not a vector. Callers decide whether missing data is a fallback or an error.
    """
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            return None
    if not isinstance(raw, list) or not raw:
        return None
    if dimensions is not None and len(raw) != dimensions:
        return None
    try:
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in raw):
            return None
        return [float(value) for value in raw]
    except (OverflowError, ValueError):
        return None
