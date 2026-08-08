"""Fail-closed JSON Schema validation for host-provided capability arguments.

The growth harness validates model-selected arguments before producing an
``ActionIntent``. It intentionally supports the portable JSON Schema subset
used by MCP/A2A tool descriptors and rejects unknown validation keywords rather
than pretending an unchecked payload is safe.
"""

from __future__ import annotations

import json
import math
import re
from typing import Any


class JsonSchemaValidationError(ValueError):
    pass


_ANNOTATION_KEYWORDS = {
    "$schema",
    "$id",
    "$anchor",
    "title",
    "description",
    "default",
    "examples",
    "deprecated",
    "readOnly",
    "writeOnly",
}
_SUPPORTED_KEYWORDS = {
    "$ref",
    "$defs",
    "definitions",
    "type",
    "enum",
    "const",
    "allOf",
    "anyOf",
    "oneOf",
    "not",
    "required",
    "properties",
    "patternProperties",
    "additionalProperties",
    "dependentRequired",
    "propertyNames",
    "minProperties",
    "maxProperties",
    "items",
    "prefixItems",
    "contains",
    "minContains",
    "maxContains",
    "minItems",
    "maxItems",
    "uniqueItems",
    "minLength",
    "maxLength",
    "pattern",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
}


def validate_json_schema(value: Any, schema: dict[str, Any]) -> None:
    if not isinstance(schema, dict):
        raise JsonSchemaValidationError("tool input_schema must be a JSON object")
    if not schema:
        return
    _validate_schema_node(schema, root=schema, path="$schema", active=set())
    _validate(value, schema, root=schema, path="$")


def _validate_schema_node(
    schema: Any,
    *,
    root: dict[str, Any],
    path: str,
    active: set[int],
) -> None:
    """Validate the supported schema itself before it can guard any value."""

    if isinstance(schema, bool):
        return
    if not isinstance(schema, dict):
        raise JsonSchemaValidationError(f"{path}: schema node must be an object or boolean")
    identity = id(schema)
    if identity in active:
        raise JsonSchemaValidationError(f"{path}: cyclic in-memory schema objects are forbidden")
    active.add(identity)
    try:
        unsupported = set(schema) - _ANNOTATION_KEYWORDS - _SUPPORTED_KEYWORDS
        if unsupported:
            raise JsonSchemaValidationError(
                f"{path}: unsupported input_schema keywords: {sorted(unsupported)}"
            )

        for key in ("$schema", "$id", "$anchor", "title", "description"):
            if key in schema and not isinstance(schema[key], str):
                raise JsonSchemaValidationError(f"{path}: {key} must be a string")
        for key in ("deprecated", "readOnly", "writeOnly"):
            if key in schema and not isinstance(schema[key], bool):
                raise JsonSchemaValidationError(f"{path}: {key} must be a boolean")
        if "examples" in schema and not isinstance(schema["examples"], list):
            raise JsonSchemaValidationError(f"{path}: examples must be an array")

        if "$ref" in schema:
            _resolve_local_ref(schema["$ref"], root=root, path=path)
        for keyword in ("$defs", "definitions", "properties", "patternProperties"):
            if keyword not in schema:
                continue
            mapping = schema[keyword]
            if not isinstance(mapping, dict):
                raise JsonSchemaValidationError(f"{path}: {keyword} must be an object")
            for name, child in mapping.items():
                if keyword == "patternProperties":
                    try:
                        re.compile(name)
                    except re.error as error:
                        raise JsonSchemaValidationError(
                            f"{path}: invalid patternProperties regex: {error}"
                        ) from error
                _validate_schema_node(
                    child,
                    root=root,
                    path=f"{path}.{keyword}.{name}",
                    active=active,
                )

        if "type" in schema:
            declared = schema["type"]
            types = [declared] if isinstance(declared, str) else declared
            allowed = {"null", "boolean", "object", "array", "number", "integer", "string"}
            if (
                not isinstance(types, list)
                or not types
                or not all(isinstance(item, str) and item in allowed for item in types)
                or len(types) != len(set(types))
            ):
                raise JsonSchemaValidationError(
                    f"{path}: type must be a supported string or unique non-empty string list"
                )
        if "enum" in schema and not isinstance(schema["enum"], list):
            raise JsonSchemaValidationError(f"{path}: enum must be an array")

        for keyword in ("allOf", "anyOf", "oneOf"):
            if keyword not in schema:
                continue
            options = schema[keyword]
            if not isinstance(options, list) or not options:
                raise JsonSchemaValidationError(f"{path}: {keyword} must be a non-empty array")
            for index, child in enumerate(options):
                _validate_schema_node(
                    child,
                    root=root,
                    path=f"{path}.{keyword}[{index}]",
                    active=active,
                )
        for keyword in ("not", "propertyNames", "contains", "items", "additionalProperties"):
            if keyword in schema:
                _validate_schema_node(
                    schema[keyword],
                    root=root,
                    path=f"{path}.{keyword}",
                    active=active,
                )
        if "prefixItems" in schema:
            prefix = schema["prefixItems"]
            if not isinstance(prefix, list):
                raise JsonSchemaValidationError(f"{path}: prefixItems must be an array")
            for index, child in enumerate(prefix):
                _validate_schema_node(
                    child,
                    root=root,
                    path=f"{path}.prefixItems[{index}]",
                    active=active,
                )

        required = schema.get("required", [])
        if (
            not isinstance(required, list)
            or not all(isinstance(item, str) for item in required)
            or len(required) != len(set(required))
        ):
            raise JsonSchemaValidationError(f"{path}: required must be a unique string array")
        dependencies = schema.get("dependentRequired", {})
        if not isinstance(dependencies, dict):
            raise JsonSchemaValidationError(f"{path}: dependentRequired must be an object")
        for name, values in dependencies.items():
            if (
                not isinstance(values, list)
                or not all(isinstance(item, str) for item in values)
                or len(values) != len(set(values))
            ):
                raise JsonSchemaValidationError(
                    f"{path}: dependentRequired[{name!r}] must be a unique string array"
                )

        for minimum, maximum in (
            ("minProperties", "maxProperties"),
            ("minItems", "maxItems"),
            ("minLength", "maxLength"),
            ("minContains", "maxContains"),
        ):
            for keyword in (minimum, maximum):
                if keyword in schema and (
                    isinstance(schema[keyword], bool)
                    or not isinstance(schema[keyword], int)
                    or schema[keyword] < 0
                ):
                    raise JsonSchemaValidationError(
                        f"{path}: {keyword} must be a non-negative integer"
                    )
            if (
                minimum in schema
                and maximum in schema
                and schema[minimum] > schema[maximum]
            ):
                raise JsonSchemaValidationError(f"{path}: {minimum} exceeds {maximum}")
        if ("minContains" in schema or "maxContains" in schema) and "contains" not in schema:
            raise JsonSchemaValidationError(
                f"{path}: minContains/maxContains require contains"
            )
        if "uniqueItems" in schema and not isinstance(schema["uniqueItems"], bool):
            raise JsonSchemaValidationError(f"{path}: uniqueItems must be a boolean")
        if "pattern" in schema:
            if not isinstance(schema["pattern"], str):
                raise JsonSchemaValidationError(f"{path}: pattern must be a string")
            try:
                re.compile(schema["pattern"])
            except re.error as error:
                raise JsonSchemaValidationError(f"{path}: invalid pattern: {error}") from error
        for keyword in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum"):
            if keyword in schema and (
                not _is_number(schema[keyword])
                or not math.isfinite(float(schema[keyword]))
            ):
                raise JsonSchemaValidationError(f"{path}: {keyword} must be a finite number")
        if "multipleOf" in schema and (
            not _is_number(schema["multipleOf"])
            or not math.isfinite(float(schema["multipleOf"]))
            or schema["multipleOf"] <= 0
        ):
            raise JsonSchemaValidationError(f"{path}: multipleOf must be a positive finite number")
    finally:
        active.remove(identity)


def _validate(value: Any, schema: Any, *, root: dict[str, Any], path: str) -> None:
    if isinstance(schema, bool):
        if not schema:
            raise JsonSchemaValidationError(f"{path}: value is forbidden by schema")
        return
    if not isinstance(schema, dict):
        raise JsonSchemaValidationError(f"{path}: schema node must be an object or boolean")
    unsupported = set(schema) - _ANNOTATION_KEYWORDS - _SUPPORTED_KEYWORDS
    if unsupported:
        raise JsonSchemaValidationError(
            f"{path}: unsupported input_schema keywords: {sorted(unsupported)}"
        )

    if "$ref" in schema:
        resolved = _resolve_local_ref(schema["$ref"], root=root, path=path)
        siblings = {key: item for key, item in schema.items() if key != "$ref"}
        _validate(value, resolved, root=root, path=path)
        if siblings:
            _validate(value, siblings, root=root, path=path)
        return

    if "const" in schema and value != schema["const"]:
        raise JsonSchemaValidationError(f"{path}: value does not equal const")
    if "enum" in schema:
        enum = schema["enum"]
        if not isinstance(enum, list) or not any(_json_equal(value, item) for item in enum):
            raise JsonSchemaValidationError(f"{path}: value is not in enum")

    _validate_combinators(value, schema, root=root, path=path)
    expected_types = schema.get("type")
    if expected_types is not None:
        types = [expected_types] if isinstance(expected_types, str) else expected_types
        if not isinstance(types, list) or not types or not all(isinstance(item, str) for item in types):
            raise JsonSchemaValidationError(f"{path}: schema type must be a string or string list")
        if not any(_is_json_type(value, item) for item in types):
            raise JsonSchemaValidationError(
                f"{path}: expected JSON type {types}, received {_json_type(value)}"
            )

    if isinstance(value, dict):
        _validate_object(value, schema, root=root, path=path)
    elif isinstance(value, list):
        _validate_array(value, schema, root=root, path=path)
    elif isinstance(value, str):
        _validate_string(value, schema, path=path)
    elif _is_number(value):
        _validate_number(value, schema, path=path)


def _validate_combinators(
    value: Any,
    schema: dict[str, Any],
    *,
    root: dict[str, Any],
    path: str,
) -> None:
    for item in schema.get("allOf", []):
        _validate(value, item, root=root, path=path)
    for keyword, expected_matches in (("anyOf", "at_least_one"), ("oneOf", "exactly_one")):
        if keyword not in schema:
            continue
        options = schema[keyword]
        if not isinstance(options, list) or not options:
            raise JsonSchemaValidationError(f"{path}: {keyword} must be a non-empty list")
        matches = 0
        for option in options:
            try:
                _validate(value, option, root=root, path=path)
            except JsonSchemaValidationError:
                continue
            matches += 1
        if expected_matches == "at_least_one" and matches == 0:
            raise JsonSchemaValidationError(f"{path}: no anyOf branch matched")
        if expected_matches == "exactly_one" and matches != 1:
            raise JsonSchemaValidationError(f"{path}: expected exactly one oneOf match, got {matches}")
    if "not" in schema:
        try:
            _validate(value, schema["not"], root=root, path=path)
        except JsonSchemaValidationError:
            pass
        else:
            raise JsonSchemaValidationError(f"{path}: value matched forbidden not schema")


def _validate_object(
    value: dict[str, Any],
    schema: dict[str, Any],
    *,
    root: dict[str, Any],
    path: str,
) -> None:
    required = schema.get("required", [])
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        raise JsonSchemaValidationError(f"{path}: required must be a string list")
    missing = [name for name in required if name not in value]
    if missing:
        raise JsonSchemaValidationError(f"{path}: missing required properties {missing}")
    _check_length(len(value), schema, "minProperties", "maxProperties", path)

    properties = schema.get("properties", {})
    patterns = schema.get("patternProperties", {})
    if not isinstance(properties, dict) or not isinstance(patterns, dict):
        raise JsonSchemaValidationError(f"{path}: properties must be objects")
    matched: set[str] = set()
    for name, child_schema in properties.items():
        if name in value:
            matched.add(name)
            _validate(value[name], child_schema, root=root, path=f"{path}.{name}")
    for pattern, child_schema in patterns.items():
        try:
            matcher = re.compile(pattern)
        except re.error as error:
            raise JsonSchemaValidationError(f"{path}: invalid patternProperties regex: {error}") from error
        for name, item in value.items():
            if matcher.search(name):
                matched.add(name)
                _validate(item, child_schema, root=root, path=f"{path}.{name}")

    additional = schema.get("additionalProperties", True)
    for name, item in value.items():
        if name in matched:
            continue
        if additional is False:
            raise JsonSchemaValidationError(f"{path}: additional property {name!r} is forbidden")
        if isinstance(additional, dict):
            _validate(item, additional, root=root, path=f"{path}.{name}")

    dependencies = schema.get("dependentRequired", {})
    if not isinstance(dependencies, dict):
        raise JsonSchemaValidationError(f"{path}: dependentRequired must be an object")
    for name, dependent_names in dependencies.items():
        if name not in value:
            continue
        if not isinstance(dependent_names, list) or not all(
            isinstance(item, str) for item in dependent_names
        ):
            raise JsonSchemaValidationError(f"{path}: dependentRequired values must be lists")
        missing_dependent = [item for item in dependent_names if item not in value]
        if missing_dependent:
            raise JsonSchemaValidationError(
                f"{path}: property {name!r} requires {missing_dependent}"
            )
    if "propertyNames" in schema:
        for name in value:
            _validate(name, schema["propertyNames"], root=root, path=f"{path}.<property>")


def _validate_array(
    value: list[Any],
    schema: dict[str, Any],
    *,
    root: dict[str, Any],
    path: str,
) -> None:
    _check_length(len(value), schema, "minItems", "maxItems", path)
    if schema.get("uniqueItems"):
        encoded = [json.dumps(item, ensure_ascii=False, sort_keys=True) for item in value]
        if len(encoded) != len(set(encoded)):
            raise JsonSchemaValidationError(f"{path}: array items must be unique")
    prefix = schema.get("prefixItems", [])
    if not isinstance(prefix, list):
        raise JsonSchemaValidationError(f"{path}: prefixItems must be a list")
    for index, child_schema in enumerate(prefix):
        if index < len(value):
            _validate(value[index], child_schema, root=root, path=f"{path}[{index}]")
    items = schema.get("items")
    if items is not None:
        for index in range(len(prefix), len(value)):
            _validate(value[index], items, root=root, path=f"{path}[{index}]")
    if "contains" in schema:
        matches = 0
        for index, item in enumerate(value):
            try:
                _validate(item, schema["contains"], root=root, path=f"{path}[{index}]")
            except JsonSchemaValidationError:
                continue
            matches += 1
        minimum = schema.get("minContains", 1)
        maximum = schema.get("maxContains")
        if matches < minimum or (maximum is not None and matches > maximum):
            raise JsonSchemaValidationError(f"{path}: contains matched {matches} items")


def _validate_string(value: str, schema: dict[str, Any], *, path: str) -> None:
    _check_length(len(value), schema, "minLength", "maxLength", path)
    if "pattern" in schema:
        try:
            if re.search(schema["pattern"], value) is None:
                raise JsonSchemaValidationError(f"{path}: string does not match pattern")
        except re.error as error:
            raise JsonSchemaValidationError(f"{path}: invalid schema pattern: {error}") from error


def _validate_number(value: int | float, schema: dict[str, Any], *, path: str) -> None:
    if not math.isfinite(float(value)):
        raise JsonSchemaValidationError(f"{path}: non-finite number is forbidden")
    checks = (
        ("minimum", lambda actual, bound: actual >= bound),
        ("maximum", lambda actual, bound: actual <= bound),
        ("exclusiveMinimum", lambda actual, bound: actual > bound),
        ("exclusiveMaximum", lambda actual, bound: actual < bound),
    )
    for keyword, predicate in checks:
        if keyword in schema and not predicate(value, schema[keyword]):
            raise JsonSchemaValidationError(f"{path}: number violates {keyword}")
    if "multipleOf" in schema:
        divisor = schema["multipleOf"]
        if not _is_number(divisor) or divisor <= 0:
            raise JsonSchemaValidationError(f"{path}: multipleOf must be positive")
        quotient = float(value) / float(divisor)
        if not math.isclose(quotient, round(quotient), rel_tol=1e-9, abs_tol=1e-9):
            raise JsonSchemaValidationError(f"{path}: number is not a multipleOf {divisor}")


def _check_length(
    length: int,
    schema: dict[str, Any],
    minimum_key: str,
    maximum_key: str,
    path: str,
) -> None:
    minimum = schema.get(minimum_key)
    maximum = schema.get(maximum_key)
    if minimum is not None and length < minimum:
        raise JsonSchemaValidationError(f"{path}: length is below {minimum_key}={minimum}")
    if maximum is not None and length > maximum:
        raise JsonSchemaValidationError(f"{path}: length exceeds {maximum_key}={maximum}")


def _resolve_local_ref(reference: Any, *, root: dict[str, Any], path: str) -> Any:
    if not isinstance(reference, str) or not reference.startswith("#/"):
        raise JsonSchemaValidationError(f"{path}: only local JSON Pointer $ref is supported")
    node: Any = root
    for raw_part in reference[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or part not in node:
            raise JsonSchemaValidationError(f"{path}: unresolved schema reference {reference!r}")
        node = node[part]
    return node


def _json_equal(left: Any, right: Any) -> bool:
    return type(left) is type(right) and left == right


def _is_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float))


def _is_json_type(value: Any, expected: str) -> bool:
    checks = {
        "null": lambda item: item is None,
        "boolean": lambda item: isinstance(item, bool),
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "number": _is_number,
        "integer": lambda item: not isinstance(item, bool) and isinstance(item, int),
        "string": lambda item: isinstance(item, str),
    }
    if expected not in checks:
        raise JsonSchemaValidationError(f"unsupported JSON Schema type {expected!r}")
    return checks[expected](value)


def _json_type(value: Any) -> str:
    for expected in ("null", "boolean", "object", "array", "integer", "number", "string"):
        if _is_json_type(value, expected):
            return expected
    return type(value).__name__
