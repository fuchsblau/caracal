"""JSON envelope output formatter."""

import json
from datetime import UTC, datetime
from typing import Any

from caracal.output.precision import PRICE_DECIMALS

# JSON output uses uniform rounding for all floats. Currently all
# precision constants (price, indicator, percent) are 2, so PRICE_DECIMALS
# is representative. If asset-class-specific precision is needed later,
# this function would need field-name-aware rounding.
_JSON_DECIMALS = PRICE_DECIMALS


def _round_floats(obj: Any) -> Any:
    """Recursively round float values in nested data structures."""
    if isinstance(obj, float):
        return round(obj, _JSON_DECIMALS)
    if isinstance(obj, dict):
        return {k: _round_floats(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_round_floats(item) for item in obj]
    return obj


def format_success(
    data: Any,
    meta: dict[str, Any] | None = None,
) -> str:
    envelope = {
        "status": "success",
        "data": _round_floats(data),
        "meta": {
            **(meta or {}),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }
    return json.dumps(envelope, indent=2, default=str)


def format_error(
    code: str,
    message: str,
    meta: dict[str, Any] | None = None,
) -> str:
    envelope = {
        "status": "error",
        "error": {"code": code, "message": message},
        "meta": {
            **(meta or {}),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }
    return json.dumps(envelope, indent=2, default=str)
