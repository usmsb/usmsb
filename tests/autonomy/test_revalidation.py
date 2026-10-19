"""Focused stdlib tests; no provider, LLM or SDK optional dependency needed."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "_revalidation_test_core", ROOT / "src/usmsb_sdk/autonomy/revalidation.py")
rv = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = rv
spec.loader.exec_module(rv)


def make_model():
    return rv.FiniteModel.from_dict({"family_id": "joint-v1", "probes": [
        {"id": "old", "cost": 1, "scope": "old-epoch"},
        {"id": "current", "cost": 2, "scope": "new-epoch"}], "hypotheses": [
        {"id": "stable", "probabilities": {"old": 0.8, "current": 0.8}},
        {"id": "changed", "probabilities": {"old": 0.8, "current": 0.2}}]})


class RevalidationTests(unittest.TestCase):
    def setUp(self):
        self.model = make_model()
        self.session = rv.RevalidationSession(self.model)
        self.goal = {"stable": {"continue"}, "changed": {"replace"}}

    def receipt(self, i, probe="current", value=0):
        return rv.Observation(str(i), probe, "new-epoch" if probe == "current"
                              else "old-epoch", value, f"receipt:{i}")

    def test_cold_start_not_zero_or_success(self):
        result = self.session.evaluate("g1", self.goal)
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["receipt_count"], 0)

    def test_goal_change_does_not_recollect_or_rewrite_evidence(self):
        for i in range(8):
            self.session.observe(self.receipt(i))
        first = self.session.evaluate("g1", self.goal)
        second = self.session.evaluate("g2", {"stable": {"keep"}, "changed": {"keep"}})
        self.assertEqual(first["common_actions"], ["replace"])
        self.assertEqual(second["common_actions"], ["keep"])
        self.assertEqual(first["registered_probe_cost"], second["registered_probe_cost"])
        self.assertEqual(first["receipt_count"], second["receipt_count"])

    def test_old_success_does_not_identify_unknown_current_change(self):
        for i in range(100):
            self.session.observe(self.receipt(i, "old", 1))
        self.assertEqual(self.session.retained_ids, ("stable", "changed"))
        self.assertEqual(self.session.evaluate("g1", self.goal)["status"], "inconclusive")

    def test_likelihoods_match_hand_computation(self):
        import math
        self.session.observe(self.receipt(1))
        scores = self.session.log_likelihoods
        self.assertAlmostEqual(scores["stable"], math.log(0.2))
        self.assertAlmostEqual(scores["changed"], math.log(0.8))

    def test_confidence_set_empty_is_not_a_certificate(self):
        for i in range(4):
            self.session.observe(self.receipt(i, value=0))
        for i in range(4, 20):
            self.session.observe(self.receipt(i, value=1))
        self.assertEqual(self.session.retained_ids, ())
        result = self.session.evaluate("g1", self.goal)
        self.assertEqual(result["status"], "model_conflict")
        self.assertEqual(result["common_actions"], [])

    def test_pairwise_overlap_is_insufficient(self):
        model = rv.FiniteModel("overlap", (rv.Probe("q", 1, "s"),), tuple(
            rv.Hypothesis(h, (0.5,)) for h in ("h1", "h2", "h3")))
        session = rv.RevalidationSession(model)
        result = session.evaluate("g", {"h1": {"a", "b"}, "h2": {"b", "c"}, "h3": {"a", "c"}})
        self.assertEqual(result["status"], "inconclusive")

    def test_common_action_avoids_unnecessary_full_identification(self):
        result = self.session.evaluate("g1", {"stable": {"x", "y"}, "changed": {"y", "z"}})
        self.assertEqual(result["common_actions"], ["y"])
        self.assertEqual(len(result["retained_hypotheses"]), 2)

    def test_duplicate_receipt_is_idempotent(self):
        receipt = self.receipt(1)
        self.assertTrue(self.session.observe(receipt))
        self.assertFalse(self.session.observe(receipt))
        self.assertEqual(self.session.cost, 2)

    def test_reused_id_with_changed_contents_rejected(self):
        self.session.observe(self.receipt(1))
        with self.assertRaises(rv.EvidenceError):
            self.session.observe(self.receipt(1, value=1))

    def test_source_cannot_be_recounted_with_new_id(self):
        self.session.observe(self.receipt(1))
        with self.assertRaises(rv.EvidenceError):
            self.session.observe(rv.Observation("newid", "current", "new-epoch", 0, "receipt:1"))

    def test_source_cannot_be_recounted_across_probes(self):
        self.session.observe(self.receipt(1))
        with self.assertRaises(rv.EvidenceError):
            self.session.observe(rv.Observation("newid", "old", "old-epoch", 0, "receipt:1"))
        self.assertEqual(self.session.cost, 2)

    def test_old_scope_cannot_be_relabelled_by_probe(self):
        with self.assertRaises(rv.EvidenceError):
            self.session.observe(rv.Observation("x", "current", "old-epoch", 1, "receipt:x"))
        self.assertEqual(self.session.cost, 0)

    def test_permissions_are_host_defined(self):
        session = rv.RevalidationSession(self.model, allowed_probes={"old"})
        with self.assertRaises(rv.EvidenceError):
            session.observe(self.receipt(1))

    def test_empty_permission_set_denies_all(self):
        session = rv.RevalidationSession(self.model, allowed_probes=set())
        with self.assertRaises(rv.EvidenceError):
            session.observe(self.receipt(1))

    def test_budget_enforced_before_mutation(self):
        session = rv.RevalidationSession(self.model, max_cost=1)
        with self.assertRaises(rv.EvidenceError):
            session.observe(self.receipt(1))
        self.assertEqual(session.snapshot()["observations"], [])

    def test_invalid_outcome_not_coerced(self):
        for value in [None, True, 0.0, "1", -1, 2]:
            with self.subTest(value=value), self.assertRaises(rv.EvidenceError):
                self.session.observe(self.receipt(1, value=value))

    def test_source_required(self):
        with self.assertRaises(rv.EvidenceError):
            self.session.observe(rv.Observation("1", "current", "new-epoch", 0, ""))

    def test_model_is_detached_from_input(self):
        data = self.model.to_dict()
        model = rv.FiniteModel.from_dict(data)
        data["hypotheses"][0]["probabilities"]["current"] = 0.01
        self.assertEqual(model, self.model)

    def test_model_rejects_unknown_or_missing_probe_predictions(self):
        data = self.model.to_dict()
        del data["hypotheses"][0]["probabilities"]["current"]
        with self.assertRaises(rv.EvidenceError):
            rv.FiniteModel.from_dict(data)

    def test_model_invalid_values(self):
        for value in [0, 1, -0.2, float("nan"), float("inf"), True]:
            data = self.model.to_dict()
            data["hypotheses"][0]["probabilities"]["current"] = value
            with self.subTest(value=value), self.assertRaises(rv.EvidenceError):
                rv.FiniteModel.from_dict(data)

    def test_duplicate_model_identifiers(self):
        data = self.model.to_dict()
        data["hypotheses"][1]["id"] = "stable"
        with self.assertRaises(rv.EvidenceError):
            rv.FiniteModel.from_dict(data)

    def test_no_silent_missing_goal_mapping(self):
        with self.assertRaises(rv.EvidenceError):
            self.session.evaluate("g", {"stable": {"continue"}})

    def test_snapshot_roundtrip(self):
        for i in range(5):
            self.session.observe(self.receipt(i))
        restored = rv.RevalidationSession.restore(self.session.snapshot(),
            expected_model_digest=self.model.digest, allowed_probes={"old", "current"},
            max_cost=1000, delta=0.05)
        self.assertEqual(restored.snapshot(), self.session.snapshot())
        self.assertEqual(restored.evaluate("g1", self.goal), self.session.evaluate("g1", self.goal))

    def test_snapshot_cannot_increase_error_allowance(self):
        data = self.session.snapshot()
        data["delta"] = 0.99
        with self.assertRaises(rv.EvidenceError):
            rv.RevalidationSession.restore(data, expected_model_digest=self.model.digest,
                allowed_probes={"old", "current"}, max_cost=1000, delta=0.05)

    def test_snapshot_cannot_expand_authority(self):
        self.session.observe(self.receipt(1))
        with self.assertRaises(rv.EvidenceError):
            rv.RevalidationSession.restore(self.session.snapshot(), expected_model_digest=self.model.digest,
                allowed_probes={"old"}, max_cost=1000, delta=0.05)

    def test_snapshot_cannot_change_model(self):
        data = copy.deepcopy(self.session.snapshot())
        data["model"]["family_id"] = "different"
        with self.assertRaises(rv.EvidenceError):
            rv.RevalidationSession.restore(data, expected_model_digest=self.model.digest,
                allowed_probes={"old", "current"}, max_cost=1000, delta=0.05)

    def test_output_explicitly_disclaims_semantic_validation(self):
        result = self.session.evaluate("g", self.goal)
        self.assertEqual(result["semantic_validation"], "not_provided")
        self.assertEqual(result["authorization"], "not_provided")
        self.assertEqual(result["model_coverage"], "assumed_not_verified")


if __name__ == "__main__":
    unittest.main()
