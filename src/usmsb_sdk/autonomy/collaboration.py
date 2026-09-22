"""Participant-owned reference collaboration policy over open protocol records.

The owner chooses allowed partners, capabilities and acceptance criteria, not
the environment. Discovery selects among currently available offers. This is a
bounded engineering policy with replaceable choices, NOT autonomous model work
or an empirical USMSB law. No operation/domain/scenario names are built in.
"""
import json

from .contracts import _check, _text
from .evolution import ReferenceDecisionPolicy, clone, fingerprint


EFFECTS = {"join_goal", "request_execution", "accept_execution", "set_goal_contract", "request_goal_review",
           "review_goal_result", "adopt_execution", "record_learning", "record_goal_gap", "resolve_goal_gap", "set_concern"}
TERMINAL = {"completed", "failed", "declined", "cancelled", "closed_uncertain"}


def content(obj):
    try:
        result = json.loads(obj.get("content", ""))
    except (ValueError, TypeError):
        return {}
    return result if isinstance(result, dict) else {}


class CollaborationPolicy(ReferenceDecisionPolicy):
    """An explicit per-subject grant; configuring a policy never grants peers access.

    Work profiles apply only to this subject's already-assessed concern. Each
    subject independently accepts/refuses requests, runs its installed programs,
    verifies frozen candidates or actually consumes them. No goal is completed
    by this policy and no effect is permitted without the embedding host.
    """
    allowed_effects = EFFECTS

    def __init__(self, config):
        self.config = clone(config)
        _check(config.get("execution_scope") == "owner_authorized_local_programs", "Explicit local program authorization required")
        _check(type(config.get("max_requests")) is int and 1 <= config["max_requests"] <= 100, "Persistent request budget required")
        _check(type(config.get("max_accepts")) is int and 0 <= config["max_accepts"] <= 100, "Persistent acceptance budget required")
        for key in ("provider_ids", "requester_ids", "accept_operations", "work", "verify", "discover_conditions"):
            _check(isinstance(config.get(key, []), list) and len(config.get(key, [])) <= 30, "Bounded " + key + " required")
        _check(config.get("provider_ids") or not config.get("work"), "Owner must authorize a partner set, not arbitrary remote side effects")
        for item in config.get("work", []):
            for key in ("concern_id", "produce_operation", "candidate_format", "verify_operation", "consume_operation", "criterion"):
                _text(item.get(key), 180)
            _check(isinstance(item.get("input_object_ids", []), list) and len(item.get("input_object_ids", [])) <= 12, "Bounded input objects required")
            _check(type(item.get("allow_read_only_recovery", False)) is bool, "Explicit recovery scope required")
        for item in config.get("verify", []):
            for key in ("operation", "candidate_format", "result_format", "pass_field", "criterion"):
                _text(item.get(key), 180)
        for item in config.get("discover_conditions", []):
            for key in ("id", "source_id", "external_id", "title", "reason_for_caring", "unit"):
                _text(item.get(key), 180)
            _check(isinstance(item.get("path"), str) and item["path"].startswith("/") and len(item["path"]) <= 500, "Explicit source field required")
            _check(type(item.get("desired")) in {str, bool, int, float} and item["desired"] != "", "Desired source condition required")
            _check(type(item.get("max_age_seconds")) is int and 30 <= item["max_age_seconds"] <= 86400, "Bounded observation freshness required")
        self.version = "usmsb.local-collaboration.v1:" + fingerprint(config)

    @staticmethod
    def actions(context):
        return {a["action_key"]: a for a in context["memory"].get("actions", []) if a.get("action_key")}

    def propose(self, context, key, operation, parameters, reason):
        _check(operation in self.allowed_effects, "Effect is not owner-authorized")
        prior = self.actions(context)
        if key in prior:
            return None
        applied = context["memory"].get("actions", [])
        if operation in {"request_execution", "accept_execution"}:
            limit = self.config["max_requests" if operation == "request_execution" else "max_accepts"]
            if sum((a.get("intent") or {}).get("operation") == operation for a in applied) >= limit:
                return {"decision": "wait", "reason": "persistent_" + operation + "_budget"}
        return {"decision": "propose_action", "action_key": key, "intent": {"operation": operation, "parameters": parameters}, "reason": reason}

    def choose(self, context, operation, *, excluded=(), own=False):
        aid = context["subject"]["subject_id"]
        allowed = {aid} if own else set(self.config.get("provider_ids", []))
        choices = [c for c in context["environment"].get("capabilities", []) if c.get("operation") == operation
            and c.get("owner_id") in allowed and c.get("id") not in excluded and c.get("runtime_online") is True
            and c.get("available_slots", 0) > 0 and c.get("remaining_today", 0) > 0 and not c.get("curation")]
        # A deterministic tie-break, not a universal value function. Owners can
        # replace the whole policy instead of accepting this engineering choice.
        return min(choices, key=lambda c: c["id"], default=None)

    def decide(self, context):
        base = super().decide(context)
        if base["decision"] != "wait" or base["reason"] == "reconcile_original_execution":
            return base
        aid, env = context["subject"]["subject_id"], context["environment"]
        runs = {r["id"]: r for r in env.get("executions", [])}
        objects = {o["id"]: o for o in env.get("objects", [])}
        goals = {g["id"]: g for g in env.get("goals", [])}
        prior = self.actions(context)
        affected = env.get("evidence_impacts", {}).get("objects", {})
        # Standing attention rules can discover a previously absent condition
        # from a NEW real source record. They do not pre-create a task list.
        # The ordinary concern assessment forms a goal on the next cycle.
        for rule in self.config.get("discover_conditions", []):
            key = "discover-condition:" + rule["id"]
            if key in prior:
                continue
            for observed in sorted(context["observations"], key=lambda o: o.get("observed_at", 0), reverse=True):
                meta = env.get("observation_metadata", {}).get(observed["id"], {})
                if (observed.get("source_id") != rule["source_id"] or observed.get("effective_validity") != "valid"
                        or meta.get("external_id") != rule["external_id"] or meta.get("superseded")):
                    continue
                try:
                    actual = observed["payload"]["raw_record"]
                    for part in rule["path"].split("/")[1:]:
                        actual = actual[part.replace("~1", "/").replace("~0", "~")]
                except (KeyError, TypeError, IndexError):
                    continue
                if type(actual) != type(rule["desired"]) or actual == rule["desired"]:
                    continue  # Unknown/absent/type-mismatched data is not a gap.
                return self.propose(context, key, "set_concern", {"title": rule["title"], "reason_for_caring": rule["reason_for_caring"],
                    "basis_observation_id": observed["id"], "selector": {"source_id": rule["source_id"], "external_id": rule["external_id"],
                        "root": "raw_record", "path": rule["path"], "match": []}, "comparison": "eq", "desired": rule["desired"],
                    "unit": rule["unit"], "max_age_seconds": rule["max_age_seconds"]}, "new_observed_condition_enters_own_attention") or base
        # Requests are commitments only after this provider's own choice.
        for run in sorted(runs.values(), key=lambda r: r["id"]):
            if (run.get("provider_id") == aid and run["status"] == "requested"
                and run.get("requester_id") in self.config.get("requester_ids", [])
                and run.get("operation") in self.config.get("accept_operations", [])):
                cap = self.choose(context, run["operation"], own=True)
                if cap and cap["id"] == run["capability_id"] and not any(oid in affected for oid in run.get("input_object_ids", [])):
                    proposal = self.propose(context, "accept:" + run["id"], "accept_execution", {"execution_id": run["id"]}, "provider_independently_accepts_within_owner_scope")
                    if proposal:
                        return proposal
        # A reviewer responds to assigned, current criteria and its own method.
        for review in env.get("reviews", []):
            if review.get("status") != "awaiting_review" or aid not in review.get("verifier_ids", []):
                continue
            goal, candidate = goals.get(review["goal_id"]), objects.get(review["candidate_id"])
            if candidate and candidate["id"] in affected:
                continue
            if not goal or not candidate or goal.get("acceptance_contract_id") != review["contract_id"] or candidate.get("owner_id") == aid:
                continue
            rule = next((r for r in self.config.get("verify", []) if r["candidate_format"] == content(candidate).get("format")), None)
            if not rule:
                continue
            key = "verify:" + review["id"]
            if aid not in goal["member_ids"]:
                return self.propose(context, key + ":join", "join_goal", {"goal_id": goal["id"]}, "reviewer_voluntarily_joins_relevant_goal") or base
            issued = prior.get(key)
            if not issued:
                cap = self.choose(context, rule["operation"], own=True)
                if cap:
                    return self.propose(context, key, "request_execution", {"capability_id": cap["id"], "goal_id": goal["id"],
                        "input_object_ids": [candidate["id"]], "arguments": rule.get("arguments", {}), "purpose": "Independently check the frozen candidate using my owner-installed method"}, "verify_frozen_candidate") or base
                continue
            run = runs.get(issued["receipt"]["id"])
            if not run or run["status"] not in TERMINAL:
                continue
            result = content(objects.get(run.get("output_id"), {}))
            contract = next((c for c in env.get("goal_contracts", []) if c["id"] == review["contract_id"]), {})
            criteria = contract.get("criteria", [])
            # This reference reviewer understands one execution-based criterion;
            # new/expanded criteria never silently get a blanket approval.
            if (len(criteria) != 1 or criteria[0].get("evidence_kind") != "execution"
                    or criteria[0].get("description") != rule["criterion"]):
                continue
            passed = (run["status"] == "completed" and result.get("format") == rule["result_format"]
                      and result.get(rule["pass_field"]) is True
                      and result.get("candidate_id") == candidate["id"]
                      and result.get("candidate_hash") == fingerprint_text(candidate["content"]))
            return self.propose(context, key + ":verdict", "review_goal_result", {"goal_id": goal["id"], "review_id": review["id"],
                "checks": [{"criterion_id": criteria[0]["id"], "status": "pass" if passed else "fail", "evidence_ids": [run["id"]],
                            "reason": "Actual independent execution and frozen-candidate binding checked; no clinical or causal certification"}]}, "independent_execution_result_changes_acceptance") or base
        for spec in self.config.get("work", []):
            state = context["memory"]["concerns"].get(spec["concern_id"], {})
            goal = goals.get(state.get("goal_id"))
            assessment = next((a for a in env.get("assessments", []) if a.get("concern_id") == spec["concern_id"] and a.get("actor_id") == aid), {})
            if not goal or goal["status"] != "active" or goal.get("owner_id") != aid:
                continue
            key = "work:" + goal["id"]
            blocked_inputs = [oid for oid in spec.get("input_object_ids", []) if oid in affected]
            if blocked_inputs:
                issue = fingerprint({oid: affected[oid] for oid in blocked_inputs})
                return self.propose(context, key + ":evidence:" + issue, "record_goal_gap", {"goal_id": goal["id"], "kind": "evidence",
                    "description": "Input use was withdrawn or disputed; review source authority and obtain a new authorized version before proceeding"}, "source_notice_changes_next_action") or base
            # A consumption that already happened still needs its real adoption
            # record if its effect made the measured condition align first.
            # Do not start new work just because an old episode once had a gap.
            if assessment.get("status") != "gap" and key + ":consume" not in prior:
                continue
            started = [v for k, v in prior.items() if k.startswith(key + ":produce:")]
            latest = started[-1] if started else None
            run = runs.get(latest["receipt"]["id"]) if latest else None
            if latest and (not run or run["status"] not in TERMINAL):
                continue  # Missing, leased and uncertain are not retry permission.
            if not run or run["status"] in {"declined", "cancelled"} or (run["status"] == "failed" and spec.get("allow_read_only_recovery") is True):
                if any(objects.get(oid) is None for oid in spec.get("input_object_ids", [])):
                    continue
                # A new relevant source version may justify another bounded
                # read-only attempt, never a paid/unknown replay. With unchanged
                # evidence only an alternative authorized provider is considered.
                excluded = [v["intent"]["parameters"]["capability_id"] for v in started
                            if v["intent"]["parameters"].get("observation_ids") == [assessment["observation_id"]]]
                cap = self.choose(context, spec["produce_operation"], excluded=excluded)
                if not cap:
                    gap = self.propose(context, key + ":gap:" + str(len(started)), "record_goal_gap", {"goal_id": goal["id"], "kind": "capability",
                        "description": "No currently available owner-authorized provider for " + spec["produce_operation"]}, "wait_for_authorized_capability_or_alternative")
                    if gap:
                        return gap
                    continue
                return self.propose(context, key + ":produce:" + str(len(started)), "request_execution", {
                    "goal_id": goal["id"], "capability_id": cap["id"], "input_object_ids": spec.get("input_object_ids", []),
                    "observation_ids": [assessment["observation_id"]], "arguments": spec.get("arguments", {}),
                    "purpose": "Respond to my observed condition using an available authorized capability"}, "discover_available_capability_for_own_goal") or base
            if run["status"] != "completed":
                continue
            candidate = objects.get(run.get("output_id"))
            if not candidate or content(candidate).get("format") != spec["candidate_format"]:
                continue
            if candidate["id"] in affected:
                return self.propose(context, key + ":evidence:" + fingerprint(affected[candidate["id"]]), "record_goal_gap", {
                    "goal_id": goal["id"], "kind": "evidence", "description": "The candidate or its source has a withdrawal or counterevidence notice; previous acceptance is not current authorization"},
                    "candidate_notice_prevents_further_consumption") or base
            for gap_key, gap_action in prior.items():
                if gap_key.startswith(key + ":gap:") and gap_action["intent"]["operation"] == "record_goal_gap":
                    resolved = self.propose(context, gap_key + ":resolved", "resolve_goal_gap", {"goal_id": goal["id"],
                        "gap_id": gap_action["receipt"]["id"], "evidence_ids": [candidate["id"]],
                        "resolution": "An authorized provider actually produced the linked artifact; execution, validation and impact remain distinct"}, "actual_result_resolves_previous_capability_gap")
                    if resolved:
                        return resolved
            contracts = [c for c in env.get("goal_contracts", []) if c["goal_id"] == goal["id"]]
            if not contracts:
                cap = self.choose(context, spec["verify_operation"])
                if cap and cap["owner_id"] not in {aid, candidate["owner_id"]}:
                    return self.propose(context, key + ":contract", "set_goal_contract", {"goal_id": goal["id"], "expected_version": None,
                        "criteria": [{"id": "actual", "description": spec.get("criterion", "Independently reproduce the candidate's declared method"), "evidence_kind": "execution"}],
                        "verifier_ids": [cap["owner_id"]]}, "select_available_independent_verifier") or base
                continue
            own_contract = prior.get(key + ":contract")
            if not own_contract or goal.get("acceptance_contract_id") != own_contract["receipt"]["id"]:
                continue  # Changed criteria require renewed owner deliberation.
            review_action = prior.get(key + ":review")
            if not review_action:
                return self.propose(context, key + ":review", "request_goal_review", {"goal_id": goal["id"], "candidate_id": candidate["id"],
                    "contract_id": goal["acceptance_contract_id"]}, "request_independent_current_version_review") or base
            review = next((r for r in env.get("reviews", []) if r["id"] == review_action["receipt"]["id"]), None)
            if not review or review["status"] != "accepted":
                continue
            use = prior.get(key + ":consume")
            if not use:
                cap = self.choose(context, spec["consume_operation"])
                if cap:
                    return self.propose(context, key + ":consume", "request_execution", {"goal_id": goal["id"], "capability_id": cap["id"],
                        "input_object_ids": [candidate["id"]], "arguments": {**spec.get("consume_arguments", {}), "goal_review_id": review["id"]},
                        "purpose": "Actually consume the independently reviewed artifact; execution is not social impact"}, "consume_only_currently_accepted_candidate") or base
                continue
            consumed = runs.get(use["receipt"]["id"])
            if consumed and consumed["status"] == "completed":
                adoption = self.propose(context, key + ":adopt", "adopt_execution", {"execution_id": consumed["id"], "object_id": candidate["id"]}, "record_actual_protocol_bound_consumption")
                if adoption:
                    return adoption
                feedback = self.propose(context, key + ":learn", "record_learning", {"lesson": "An independently checked artifact was actually used; continue observing the original condition.",
                    "previous_strategy": "Wait for trustworthy execution and independent review", "next_strategy": "Retain the used result and assess subsequent source changes; causal effect remains unproven",
                    "execution_ids": [run["id"], consumed["id"]], "goal_ids": [goal["id"]], "observation_ids": [assessment["observation_id"]],
                    "confidence": "tentative"}, "consumption_updates_next_strategy_not_goal_success")
                if feedback:
                    return feedback
        return {"decision": "wait", "reason": "no_new_authorized_collaboration_or_waiting_original_result"}


def fingerprint_text(value):
    import hashlib
    return hashlib.sha256(value.encode()).hexdigest()
