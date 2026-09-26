"""Portable common-model contracts, without a registry, scheduler or authority.

Definitions extend one USMSB element; composition is expressed by references and
attributed relations. Definitions never grant execution or access permissions.
"""
from copy import deepcopy
import hashlib
import json
import math
import re

from .contracts import ContractError, _check, _text

ELEMENTS = ("Agent", "Object", "Goal", "Resource", "Rule", "Information", "Value", "Risk", "Environment")
FIELD_TYPES = {"string", "number", "integer", "boolean", "object", "array"}


def model_definition(name, element, parents, fields):
    _check(element in ELEMENTS, "Unknown USMSB element")
    _check(isinstance(parents, list) and len(parents) <= 8, "Invalid parents")
    _check(isinstance(fields, dict) and len(fields) <= 32, "Invalid extension fields")
    inherited = {}
    for parent in parents:
        _check(parent.get("element") == element, "Parent element differs; use composition")
        for key, spec in parent.get("fields", {}).items():
            _check(key not in inherited or inherited[key] == spec, "Conflicting inherited field")
            inherited[key] = deepcopy(spec)
    for key, spec in fields.items():
        _check(isinstance(key, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", key), "Invalid field name")
        _check(isinstance(spec, dict) and set(spec) <= {"type", "required", "unit", "description"}, "Invalid field contract")
        _check(isinstance(spec.get("type"), str) and spec["type"] in FIELD_TYPES, "Invalid field type")
        _check(type(spec.get("required", False)) is bool, "Invalid required flag")
        normalized = {"type": spec["type"], "required": spec.get("required", False)}
        for attr in ("unit", "description"):
            if attr in spec:
                normalized[attr] = _text(spec[attr], 1000)
        _check(key not in inherited or inherited[key] == normalized, "Cannot redefine inherited semantics")
        inherited[key] = normalized
    _check(len(inherited) <= 128, "Too many inherited fields")
    return {"schema": "usmsb.model-definition.v1", "name": _text(name, 160),
            "element": element, "fields": inherited, "unknown_fields": "preserve"}


def model_properties(definition, properties):
    _check(isinstance(properties, dict), "Properties must be an object")
    try:
        raw = json.dumps(properties, allow_nan=False, ensure_ascii=False)
    except (TypeError, ValueError, RecursionError):
        raise ContractError("Properties must be finite JSON") from None
    _check(len(raw.encode()) <= 16000, "Properties exceed 16KB")
    for name, spec in definition.get("fields", {}).items():
        if name not in properties:
            _check(not spec["required"], "Missing required property: " + name)
            continue
        value = properties[name]
        valid = {"string": isinstance(value, str), "boolean": type(value) is bool,
                 "integer": type(value) is int,
                 "number": type(value) is int or type(value) is float and math.isfinite(value),
                 "object": isinstance(value, dict), "array": isinstance(value, list)}
        _check(valid[spec["type"]], "Property type mismatch: " + name)
    return deepcopy(properties)  # preserve extensions that this reader does not interpret


def object_reference(record):
    """The legacy object ID already identifies its content, not a mutable URL."""
    _text(record.get("content"), 32000)
    content = record["content"]
    return {"schema": "usmsb.object-reference.v1", "object_id": record.get("logical_id", record["id"]),
            "version_id": record["id"], "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
            "model_id": record.get("model_id", "usmsb:Object")}


def attributed_relation(actor_id, source, target, relationship, reason):
    """A statement about a relationship cannot create consent, rights or revenue."""
    _check(isinstance(relationship, str) and relationship in {"supports", "depends_on", "references", "motivated_by", "questions"}, "Unsupported statement relation")
    _check(isinstance(source, dict) and isinstance(target, dict), "Invalid relation endpoints")
    for ref in (source, target):
        _text(ref.get("id"), 180)
        _text(ref.get("kind"), 80)
    _check(source["id"] != target["id"], "A relation needs distinct endpoints")
    return {"schema": "usmsb.attributed-relation.v1", "actor_id": _text(actor_id, 180),
            "source": deepcopy(source), "target": deepcopy(target), "relationship": relationship,
            "reason": _text(reason), "effect": "statement_only"}
