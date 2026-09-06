from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any


def to_jsonable(value: Any) -> Any:
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "__dataclass_fields__"):
        return to_jsonable(asdict(value))
    return value

