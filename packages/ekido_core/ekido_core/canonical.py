"""Canonical JSON (RFC 8785 / JCS) and document hashing.

Everyone who signs or checks a manifest must produce identical bytes, so this is the only
serializer allowed for hashing. Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

MAX_SAFE_INTEGER = 2**53 - 1


def _number(value: int | float) -> str:
    """Format a number as ECMAScript does, which is what RFC 8785 requires."""
    if isinstance(value, int):
        if abs(value) > MAX_SAFE_INTEGER:
            raise ValueError(f"integer outside the safe range, send it as a string: {value}")
        return str(value)
    if not math.isfinite(value):
        raise ValueError("NaN and Infinity are not valid JSON")
    if value == 0:
        return "0"  # Covers -0.0 as well.
    if value == int(value) and abs(value) < 1e21:
        return str(int(value))

    mantissa, _, exponent = repr(abs(value)).partition("e")
    sign = "-" if value < 0 else ""
    if not exponent:
        return sign + mantissa

    # Python and ECMAScript switch to exponent form at different magnitudes, so rebuild from digits.
    exp = int(exponent)
    whole, _, fraction = mantissa.partition(".")
    fraction = "" if fraction == "0" else fraction
    digits = whole + fraction
    point = len(whole) + exp  # Position of the decimal point relative to the start of digits.
    if 0 < point <= 21:
        if point >= len(digits):
            return sign + digits + "0" * (point - len(digits))
        return sign + digits[:point] + "." + digits[point:]
    if -6 < point <= 0:
        return sign + "0." + "0" * (-point) + digits
    head = digits[0] + ("." + digits[1:] if len(digits) > 1 else "")
    e = point - 1
    return f"{sign}{head}e{'+' if e > 0 else '-'}{abs(e)}"


def _encode(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return _number(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_encode(item) for item in value) + "]"
    if isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise TypeError(f"object keys must be strings, got {type(key).__name__}")
        # RFC 8785 sorts by UTF-16 code units, which differs from Python's default for some characters.
        keys = sorted(value, key=lambda k: k.encode("utf-16-be"))
        return "{" + ",".join(_encode(k) + ":" + _encode(value[k]) for k in keys) + "}"
    raise TypeError(f"not JSON-serializable: {type(value).__name__}")


def canonical_bytes(document: Any) -> bytes:
    return _encode(document).encode("utf-8")


def document_hash(document: dict, *, exclude: tuple[str, ...] = ("signature", "sig")) -> str:
    """SHA-256 of the canonical form with signature fields removed, as lowercase hex."""
    body = {k: v for k, v in document.items() if k not in exclude}
    return hashlib.sha256(canonical_bytes(body)).hexdigest()
