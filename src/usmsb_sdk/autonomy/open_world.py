"""Portable references and feedback decisions for an open common world.

No networking, identity provider, model, scheduler or fabricated reward. A host
owns identity, evidence freshness, permissions, persistence and actual effects.
"""
import re
from .contracts import _check, _text


def world_reference(node, ledger, kind, record_id):
    _check(isinstance(node, str) and re.fullmatch(r"wishbud:ed25519:[A-Za-z0-9_-]{43}", node), "Invalid node identity")
    _check(isinstance(ledger, str) and re.fullmatch(r"storage_[a-f0-9]{20}", ledger), "Invalid ledger identity")
    for value in (kind, record_id):
        _check(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,120}", value), "Invalid record reference")
    return f"{node}/{ledger}/{kind}/{record_id}"


def feedback_decision(assessment, memory, *, enabled=True, max_episodes=12):
    """A reference participant policy; NOT the mandatory policy of the world.

    Fresh gap -> investigate; changed evidence -> reconsider; alignment ->
    assess effects; unknown -> wait. The host records outcomes/learning before
    advancing its memory. Alignment never certifies its actions caused a change.
    Any AI host may use these signals with its own policy instead.
    """
    _check(type(enabled) is bool and type(max_episodes) is int and 1 <= max_episodes <= 1000, "Invalid response policy")
    _check(isinstance(assessment, dict) and isinstance(memory, dict), "Invalid feedback state")
    state = assessment.get("status", "unknown")
    _check(state in {"gap", "aligned", "unknown", "disabled"}, "Unknown assessment state")
    evidence = assessment.get("observation_id")
    if not enabled or state in {"unknown", "disabled"} or not evidence:
        return {"decision": "wait", "reason": "unavailable_or_paused", "creates_goal": False}
    _text(assessment.get("id"), 160)
    _text(evidence, 160)
    if memory.get("assessment_id") == assessment["id"]:
        return {"decision": "wait", "reason": "already_considered", "creates_goal": False}
    episodes = memory.get("episodes", 0)
    _check(type(episodes) is int and episodes >= 0, "Invalid episode counter")
    active = bool(memory.get("goal_id")) and memory.get("phase") != "aligned"
    if state == "gap" and not active and episodes >= max_episodes:
        return {"decision": "wait", "reason": "episode_budget", "creates_goal": False}
    decision = ("reconsider" if active else "investigate") if state == "gap" else ("assess_effect" if active else "observe")
    return {"decision": decision, "reason": "evidence_changed", "creates_goal": decision == "investigate",
            "evidence_id": evidence, "assessment_id": assessment["id"], "phase": state,
            "previous_strategy": memory.get("strategy"), "causal_claim": False}
