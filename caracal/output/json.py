"""JSON envelope output formatter."""

import json
from datetime import UTC, datetime
from typing import Any


def format_success(
    data: Any,
    meta: dict[str, Any] | None = None,
) -> str:
    envelope = {
        "status": "success",
        "data": data,
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
