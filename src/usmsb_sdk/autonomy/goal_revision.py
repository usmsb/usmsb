"""Goal -> action -> outcome -> feedback -> revised goal, without a planner.

Revisions are attributed proposals, not evidence of improvement. The embedding
world decides authority and consent; existing obligations are never rewritten.
"""
from .contracts import _check, _text

REVISION_FIELDS = {"title": 160, "description": 4000, "domain": 60, "success_criteria": 2000}


def revision_patch(changes):
    _check(isinstance(changes, dict) and bool(changes), "Require a non-empty goal revision")
    _check(set(changes) <= set(REVISION_FIELDS), "Revision cannot change identity, ownership or obligations")
    return {key: _text(value, REVISION_FIELDS[key]) for key, value in changes.items()}


def revision_basis(version):
    _check(type(version) is int and version >= 1, "Require a positive goal revision")
    return version


def goal_version(record):
    """Legacy goals have revision 1. Snapshot intent, not transient membership."""
    return {"schema": "usmsb.goal-revision.v1", "goal_id": record["id"],
            "revision": revision_basis(record.get("revision", 1)),
            "intent": {key: record[key] for key in REVISION_FIELDS},
            "semantics": "feedback_driven_intent_not_retroactive_contract_change"}
