"""Input validation helpers shared by every module (Phase 4: robust validation)."""
from typing import Any, Iterable, List


class ValidationError(ValueError):
    """Raised when user supplied or file supplied input is invalid."""


def require_int(value: Any, name: str, minimum: int = None, maximum: int = None) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str, float)):
        raise ValidationError(f"{name} must be an integer, got {value!r}")
    try:
        f = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{name} must be an integer, got {value!r}")
    if f != int(f):
        raise ValidationError(f"{name} must be a whole number, got {value!r}")
    n = int(f)
    if minimum is not None and n < minimum:
        raise ValidationError(f"{name} must be >= {minimum}, got {n}")
    if maximum is not None and n > maximum:
        raise ValidationError(f"{name} must be <= {maximum}, got {n}")
    return n


def require_int_list(values: Any, name: str, minimum: int = None, maximum: int = None,
                     allow_empty: bool = False) -> List[int]:
    if isinstance(values, str):
        values = values.replace(",", " ").split()
    if not isinstance(values, Iterable):
        raise ValidationError(f"{name} must be a list of integers")
    out = [require_int(v, f"{name}[{i}]", minimum, maximum) for i, v in enumerate(values)]
    if not out and not allow_empty:
        raise ValidationError(f"{name} must not be empty")
    return out


def require_matrix(m: Any, name: str, rows: int = None, cols: int = None) -> List[List[int]]:
    if not isinstance(m, (list, tuple)) or not m:
        raise ValidationError(f"{name} must be a non-empty matrix")
    out = [require_int_list(r, f"{name}[{i}]", minimum=0) for i, r in enumerate(m)]
    width = len(out[0])
    if any(len(r) != width for r in out):
        raise ValidationError(f"{name} rows must all have the same length")
    if rows is not None and len(out) != rows:
        raise ValidationError(f"{name} must have {rows} rows, got {len(out)}")
    if cols is not None and width != cols:
        raise ValidationError(f"{name} must have {cols} columns, got {width}")
    return out
