from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StringSchema:
    description: str
    min_length: int = 1

    def to_json_schema(self) -> dict[str, Any]:
        return {
            "type": "string",
            "description": self.description,
            "minLength": self.min_length,
        }

    def validate(self, name: str, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError(f"{name} must be a string")
        if len(value.strip()) < self.min_length:
            raise ValueError(f"{name} must not be empty")
        return value


@dataclass(frozen=True)
class IntegerSchema:
    description: str
    minimum: int | None = None
    maximum: int | None = None

    def to_json_schema(self) -> dict[str, Any]:
        schema: dict[str, Any] = {
            "type": "integer",
            "description": self.description,
        }
        if self.minimum is not None:
            schema["minimum"] = self.minimum
        if self.maximum is not None:
            schema["maximum"] = self.maximum
        return schema

    def validate(self, name: str, value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
        if self.minimum is not None and value < self.minimum:
            raise ValueError(f"{name} must be at least {self.minimum}")
        if self.maximum is not None and value > self.maximum:
            raise ValueError(f"{name} must be at most {self.maximum}")
        return value


@dataclass(frozen=True)
class ArraySchema:
    description: str
    items: StringSchema
    min_items: int = 1

    def to_json_schema(self) -> dict[str, Any]:
        return {
            "type": "array",
            "description": self.description,
            "items": self.items.to_json_schema(),
            "minItems": self.min_items,
        }

    def validate(self, name: str, value: Any) -> list[str]:
        if not isinstance(value, list):
            raise ValueError(f"{name} must be an array")
        if len(value) < self.min_items:
            raise ValueError(f"{name} must contain at least {self.min_items} item")
        return [self.items.validate(f"{name}[{index}]", item) for index, item in enumerate(value)]


InputSchema = StringSchema | IntegerSchema | ArraySchema

