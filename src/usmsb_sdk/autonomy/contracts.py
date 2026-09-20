"""Portable USMSB Goal/Action/Outcome contracts.

These validate attributed proposals and evidence, not their truth. Persistence,
identity, permission, consent and effects belong to the embedding environment.
No goal is selected, assigned or certified by this module.
"""
from copy import deepcopy
from ..core.elements import Goal, GoalStatus


class ContractError(ValueError):
    pass


def _check(ok, message):
    if not ok:
        raise ContractError(message)


def _text(value, limit=2000):
    _check(isinstance(value, str) and 0 < len(value.strip()) <= limit, "Expected bounded, non-empty text")
    return value.strip()


def _ids(value, maximum=32):
    _check(isinstance(value, list) and len(value) <= maximum, "Expected bounded reference list")
    result = [_text(v, 180) for v in value]
    _check(len(set(result)) == len(result), "Duplicate reference")
    return result


def goal_element(record):
    """Map a persisted World-compatible record to the existing USMSB Goal."""
    statuses = {"active": GoalStatus.IN_PROGRESS, "achieved": GoalStatus.COMPLETED,
                "abandoned": GoalStatus.CANCELLED, "paused": GoalStatus.PENDING}
    _check(record.get("status") in statuses, "Unknown goal status")
    return Goal(id=record["id"], name=record["title"], description=record["description"],
                status=statuses[record["status"]], associated_agent_id=record["owner_id"],
                parent_goal_id=record.get("parent_goal_id"),
                metadata={"source_status": record["status"], "domain": record.get("domain"),
                          "success_criteria": record.get("success_criteria"), "origin": record.get("origin")})


def goal_contract(criteria, verifier_ids):
    _check(isinstance(criteria, list) and 1 <= len(criteria) <= 16, "Require 1–16 acceptance criteria")
    verifiers = _ids(verifier_ids, 12)
    _check(bool(verifiers), "Require explicitly chosen verifiers")
    normalized = []
    for item in criteria:
        _check(isinstance(item, dict), "Invalid criterion")
        mode = item.get("evidence_kind", "artifact")
        _check(mode in {"artifact", "execution", "observation"}, "Unknown evidence kind")
        normalized.append({"id": _text(item.get("id"), 80), "description": _text(item.get("description")),
                           "evidence_kind": mode})
    _check(len({c["id"] for c in normalized}) == len(normalized), "Duplicate criterion")
    return {"schema": "usmsb.goal-contract.v1", "criteria": normalized, "verifier_ids": verifiers,
            "independent_review": True}


def plan_steps(steps):
    _check(isinstance(steps, list) and 1 <= len(steps) <= 32, "Require 1–32 plan steps")
    normalized = []
    for step in steps:
        _check(isinstance(step, dict), "Invalid step")
        normalized.append({"id": _text(step.get("id"), 80), "title": _text(step.get("title"), 300),
                           "depends_on": _ids(step.get("depends_on", [])),
                           "capability": _text(step.get("capability", "open"), 180),
                           "goal_id": step.get("goal_id"), "execution_id": step.get("execution_id")})
    by_id = {s["id"]: s for s in normalized}
    _check(len(by_id) == len(normalized), "Duplicate plan step")
    done, pending = set(), set(by_id)
    for step in normalized:
        _check(set(step["depends_on"]) <= set(by_id), "Unknown dependency")
        for key in ("goal_id", "execution_id"):
            if step[key] is not None:
                _text(step[key], 180)
    while pending:
        ready = {key for key in pending if set(by_id[key]["depends_on"]) <= done}
        _check(bool(ready), "Cyclic dependency")
        pending -= ready
        done |= ready
    return normalized


def review_checks(contract, checks):
    _check(isinstance(checks, list) and len(checks) == len(contract["criteria"]), "Assess every agreed criterion")
    expected = {c["id"] for c in contract["criteria"]}
    normalized = []
    for item in checks:
        _check(isinstance(item, dict) and item.get("criterion_id") in expected, "Unknown criterion")
        status = item.get("status")
        _check(status in {"pass", "fail", "unknown"}, "Unknown assessment")
        refs = _ids(item.get("evidence_ids", []), 12)
        _check(status != "pass" or bool(refs), "Passing assessment requires evidence")
        normalized.append({"criterion_id": item["criterion_id"], "status": status,
                           "evidence_ids": refs, "reason": _text(item.get("reason"))})
    _check({c["criterion_id"] for c in normalized} == expected, "Missing or repeated criterion")
    return normalized


def remote_status(value):
    """Accepted is NOT completed; an opaque run ref permits read-only polling.

    A transport error after creation is unknown. The caller must never recreate
    the operation to obtain its status. Provider credentials stay host-private.
    """
    _check(isinstance(value, dict), "Invalid remote result")
    state = value.get("state")
    _check(state in {"accepted", "running", "completed", "failed", "unknown"}, "Unknown remote state")
    result = {"state": state, "run_ref": _text(value.get("run_ref"), 500)}
    if state == "completed":
        output = value.get("output")
        _check(isinstance(output, dict), "Completed run requires full output")
        _text(output.get("title"), 160)
        _text(output.get("content"), 32000)
        _check(output.get("content_type") in {"application/json", "text/markdown"}, "Invalid media type")
        result["output"] = deepcopy(output)
    if state in {"failed", "unknown"}:
        result["error"] = _text(value.get("error", state), 2000)
    return result
