"""Bounded strict JSON decoding for model-selected actions."""

from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from usmsb_sdk.growth_economic_harness.models import ModelDecision


class StructuredOutputError(ValueError):
    """A model result cannot safely become an action."""


StrictOutput = TypeVar("StrictOutput", bound=BaseModel)


def _reject_constant(value: str) -> None:
    raise StructuredOutputError(f"non-finite JSON number is not allowed: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise StructuredOutputError(f"duplicate JSON key is not allowed: {key}")
        value[key] = item
    return value


def decode_model_decision(raw_output: str, *, max_bytes: int = 256_000) -> ModelDecision:
    """Decode exactly one UTF-8 JSON object and validate the action schema."""

    return decode_strict_model(raw_output, ModelDecision, max_bytes=max_bytes)


def decode_strict_model(
    raw_output: str,
    model_type: type[StrictOutput],
    *,
    max_bytes: int = 256_000,
) -> StrictOutput:
    """Decode one JSON object into a strict Pydantic boundary model."""

    try:
        encoded = raw_output.encode("utf-8", errors="strict")
    except UnicodeError as error:
        raise StructuredOutputError(f"model output is not valid UTF-8: {error}") from error
    if not encoded:
        raise StructuredOutputError("model output is empty")
    if len(encoded) > max_bytes:
        raise StructuredOutputError(
            f"model output exceeds {max_bytes} bytes: received {len(encoded)}"
        )
    if raw_output.startswith("\ufeff"):
        raise StructuredOutputError("UTF-8 BOM is not allowed")

    try:
        decoded = json.loads(
            raw_output,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except StructuredOutputError:
        raise
    except json.JSONDecodeError as error:
        raise StructuredOutputError(
            f"invalid or multiple JSON documents at line {error.lineno} column {error.colno}: "
            f"{error.msg}"
        ) from error

    if not isinstance(decoded, dict):
        raise StructuredOutputError("top-level model output must be a JSON object")
    try:
        return model_type.model_validate(decoded)
    except ValidationError as error:
        raise StructuredOutputError(
            f"{model_type.__name__} schema validation failed: {error}"
        ) from error
