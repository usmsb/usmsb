"""Harness checks only. SDK mathematical/unit tests are maintained separately."""

from __future__ import annotations

import gzip
import inspect
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
import run_experiments as runner
from scenarios import PublicProblem, cases
from strategies import Policy, PublicScorer, STRATEGIES

RESULTS = runner.HERE / "results" / "first-run"


class HarnessTests(unittest.TestCase):
    def test_prespecified_parameters_and_case_contract(self):
        self.assertEqual((runner.SEED, runner.REPEATS, runner.MAX_NEW, runner.DELTA),
                         (20261018, 80, 800, 0.05))
        self.assertEqual(len(cases()), 10)
        for spec in cases():
            public = spec.public
            model = runner.sdk.FiniteModel.from_dict(public.model_dict())
            self.assertEqual(len(model.hypotheses), len(public.final_actions))
            self.assertEqual({row[0] for row in public.kernels}, {0.9})
            self.assertTrue(set(public.revision_prefix) <= set(public.allowed_new))
            self.assertTrue(set(public.allowed_new) < set(public.probe_ids))

    def test_policy_surface_excludes_private_environment(self):
        self.assertEqual(list(inspect.signature(Policy.choose).parameters), ["self", "retained"])
        self.assertEqual(list(inspect.signature(PublicScorer).parameters), ["public"])
        self.assertFalse({"truth", "true_id", "probabilities", "environment", "changed_location",
                          "outside_actions", "outside_probabilities"} & set(PublicProblem.__dataclass_fields__))

    def test_pairing_is_per_probe_not_adaptive_order(self):
        spec = cases()[0]
        left, right = runner.Environment(spec, 7), runner.Environment(spec, 7)
        self.assertEqual(left.true_id, right.true_id)
        a = [left.draw("new_1") for _ in range(5)]
        for _ in range(17):
            right.draw("new_0")
        b = [right.draw("new_1") for _ in range(5)]
        self.assertEqual(a, b)
        self.assertNotEqual(runner.stream_seed("case", 1, "new_0"),
                            runner.stream_seed("case", 2, "new_0"))

    def test_greedy_scores_ignore_nuisance_only_for_decision_policy(self):
        public = cases()[0].public
        scorer = PublicScorer(public)
        # Condition on a fixed decision bit. All remaining differences are nuisance.
        same_action = tuple(h for h, actions in zip(public.hypothesis_ids, public.final_actions)
                            if actions == ("a0",))
        self.assertTrue(all(score == 0 for score in scorer.scores(same_action, True)))
        self.assertTrue(any(score > 0 for score in scorer.scores(same_action, False)))
        policy = Policy("decision_greedy", scorer)
        self.assertEqual(policy.choose(public.hypothesis_ids)[0], "new_0")

    def test_every_prefix_respects_hint_cap_and_coverage(self):
        public = next(c.public for c in cases() if c.public.case_id == "misleading_hint")
        for name in ("uniform", "decision_greedy", "hinted_coverage"):
            policy = Policy(name, PublicScorer(public))
            forced_hints = 0
            for t in range(1, 161):
                _, reason = policy.choose(public.hypothesis_ids)
                forced_hints += reason == "hint_slot"
                self.assertLessEqual(forced_hints, t // 4)
            self.assertTrue(all(count >= 10 for count in policy.counts.values()))
        restricted = next(c.public for c in cases() if c.public.case_id == "restricted_probes")
        for name in STRATEGIES[:-1]:
            policy = Policy(name, PublicScorer(restricted))
            self.assertEqual({policy.choose(restricted.hypothesis_ids)[0] for _ in range(20)}, {"new_0"})

    def test_overlapping_actions_are_not_treated_as_a_global_certificate(self):
        public = next(c.public for c in cases() if c.public.case_id == "multiple_correct_actions")
        scorer = PublicScorer(public)
        self.assertFalse(set.intersection(*(set(a) for a in public.final_actions)))
        self.assertTrue(all(score > 0 for score in scorer.scores(public.hypothesis_ids, True)))

    def test_byte_comparison_detects_missing_extra_and_changed_files_without_writes(self):
        # Test fixtures stay inside the authorized experiment subtree.
        with tempfile.TemporaryDirectory(prefix="check-fixture-", dir=runner.HERE) as tmp:
            root = Path(tmp)
            (root / "a").write_bytes(b"original")
            expected = {"a": b"different", "b": b"missing"}
            self.assertEqual(runner.compare_artifacts(root, expected), ["missing:b", "bytes_differ:a"])
            self.assertEqual((root / "a").read_bytes(), b"original")
            self.assertEqual(runner.compare_artifacts(root, {}), ["unexpected:a"])


@unittest.skipUnless((RESULTS / "manifest.json").exists(), "first full run has not occurred")
class RecordedEvidenceTests(unittest.TestCase):
    def test_all_logged_trials_account_for_costs_coverage_and_outcomes(self):
        total = 0
        for spec in cases():
            public = spec.public
            price = dict(zip(public.probe_ids, public.costs))
            seen = set()
            truths = {}
            with gzip.open(RESULTS / "trials" / f"{public.case_id}.jsonl.gz", "rt", encoding="utf-8") as stream:
                for line in stream:
                    row = json.loads(line)
                    total += 1
                    key = (row["strategy"], row["repeat"])
                    self.assertNotIn(key, seen)
                    seen.add(key)
                    truth = row["truth_evaluator_only"]
                    previous = truths.setdefault(row["repeat"], truth)
                    self.assertEqual(previous, truth)
                    receipts = [event for event in row["trace"] if event["event"] == "observation"]
                    self.assertEqual(len(receipts), row["final_evaluation"]["receipt_count"])
                    self.assertEqual(sum(price[e["receipt"]["probe_id"]] for e in receipts), row["total_cost"])
                    self.assertEqual(row["total_cost"], row["new_cost"] + runner.OLD_COUNT * 2)
                    new_receipts = [e for e in receipts if e["stage"] != "old"]
                    self.assertEqual(len(new_receipts), row["new_observations"])
                    self.assertLessEqual(len(new_receipts), runner.MAX_NEW)
                    self.assertTrue({e["receipt"]["probe_id"] for e in new_receipts} <= set(public.allowed_new))
                    self.assertEqual(row["stage_counts"]["revision_prefix"], len(public.revision_prefix))
                    self.assertEqual(row["after_old_evaluation"]["retained_hypotheses"], list(public.hypothesis_ids))
                    self.assertEqual(row["correct_selection"], row["chosen_action"] in truth["acceptable_actions"])
                    if row["certified_selection"]:
                        self.assertIn(row["chosen_action"], row["final_evaluation"]["common_actions"])
                    if row["strategy"] == "blind_reuse":
                        self.assertEqual(row["stage_counts"]["policy_new"], 0)
                        self.assertFalse(row["certified_selection"])
                    if row["strategy"] == "hinted_coverage":
                        forced = 0
                        for t, event in enumerate((e for e in receipts if e["stage"] == "policy_new"), 1):
                            forced += event["selection"] == "hint_slot"
                            self.assertLessEqual(forced, t // 4)
                    if row["strategy"] == "full_identification" and row["action_selected"]:
                        self.assertTrue(PublicScorer(public).indistinguishable(tuple(row["final_evaluation"]["retained_hypotheses"])))
                    # Replay the first and last repeat per strategy/case (100 trials).
                    if row["repeat"] in (0, runner.REPEATS - 1):
                        session = runner.sdk.RevalidationSession(
                            runner.sdk.FiniteModel.from_dict(public.model_dict()), delta=runner.DELTA,
                            allowed_probes={"old_success", *public.allowed_new}, max_cost=row["max_cost"])
                        for event in receipts:
                            prior = session.retained_ids
                            session.observe(runner.sdk.Observation(**event["receipt"]))
                            self.assertEqual(event["eliminated"], sorted(set(prior) - set(session.retained_ids)))
                        goal_id = "goal_revised" if public.revision_prefix else "goal_final"
                        self.assertEqual(session.evaluate(goal_id, public.goal()), row["final_evaluation"])
                        self.assertEqual(session.log_likelihoods, row["final_log_likelihoods"])
            self.assertEqual(len(seen), runner.REPEATS * len(STRATEGIES))
        self.assertEqual(total, 4000)

    def test_artifact_hashes_and_summary_counts(self):
        manifest = json.loads((RESULTS / "manifest.json").read_bytes())
        self.assertEqual(manifest["source_sha256"], runner.source_hashes())
        for filename, digest in manifest["artifact_sha256"].items():
            self.assertEqual(runner.sha256((RESULTS / filename).read_bytes()), digest)
        summary = json.loads((RESULTS / "summary.json").read_bytes())
        self.assertEqual(len(summary), 50)
        for row in summary:
            self.assertEqual(row["correct_selected"] + row["wrong_selected"] + row["undecided"], runner.REPEATS)
            self.assertEqual(sum(row["stop_reasons"].values()), runner.REPEATS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
