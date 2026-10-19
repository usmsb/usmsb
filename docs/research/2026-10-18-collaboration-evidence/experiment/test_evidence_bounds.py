"""Deterministic checks; these do not prove the concentration theorem."""

import itertools
import math
import random
import unittest

from evidence_bounds import (
    Evidence,
    confidence_box,
    gain_bounds,
    linear_bounds,
    radius,
    wilson_interval,
)


class EvidenceTests(unittest.TestCase):
    def test_missing_is_not_zero_or_dropped(self):
        e = Evidence.from_rows([(1,), (None,), (0,)], 1)
        self.assertEqual(e.n, 3)
        self.assertEqual(e.observed, (2,))
        self.assertEqual(e.completion_box(), ((1 / 3, 2 / 3),))
        self.assertEqual(e.completed_means(), (0.5,))

    def test_empty_and_unmeasured_are_unknown(self):
        e = Evidence.from_rows([], 2)
        self.assertEqual(confidence_box(e, 3, 0.05, (0, 0)), ((0, 1), (0, 1)))
        e = Evidence.from_rows([(0.5, None)] * 128, 2)
        self.assertEqual(confidence_box(e, 2, 0.05, (0, 0))[1], (0, 1))

    def test_completion_box_exhaustive_masks(self):
        # All binary completions and all masks, not just random examples.
        for values in itertools.product((0, 1), repeat=4):
            true_mean = sum(values) / 4
            for mask in itertools.product((False, True), repeat=4):
                rows = [(value if seen else None,) for value, seen in zip(values, mask)]
                lo, hi = Evidence.from_rows(rows, 1).completion_box()[0]
                self.assertLessEqual(lo, true_mean)
                self.assertGreaterEqual(hi, true_mean)

    def test_complete_data_matches_formula(self):
        e = Evidence(100, (60,), (100,))
        r = radius(100, 2, 1, 0.05)
        self.assertEqual(confidence_box(e, 2, 0.05, (0,)), ((0.6 - r, 0.6 + r),))

    def test_drift_only_widens(self):
        e = Evidence(1000, (700,), (1000,))
        a = confidence_box(e, 2, 0.05, (0,))
        b = confidence_box(e, 2, 0.05, (0.2,))
        self.assertLessEqual(b[0][0], a[0][0])
        self.assertGreaterEqual(b[0][1], a[0][1])
        self.assertEqual(confidence_box(e, 2, 0.05, (1,)), ((0, 1),))

    def test_signed_weights_and_cost(self):
        box = ((0.2, 0.8), (0.1, 0.6))
        lo, hi = linear_bounds(box, (0.7, -0.3), 0.05)
        vertices = [
            0.7 * x - 0.3 * y - 0.05
            for x, y in itertools.product(box[0], box[1])
        ]
        self.assertAlmostEqual(lo, min(vertices))
        self.assertAlmostEqual(hi, max(vertices))

    def test_gain_box_contains_all_corners(self):
        rng = random.Random(20261018)
        for _ in range(100):
            candidate = tuple(tuple(sorted((rng.random(), rng.random()))) for _ in range(2))
            baseline = tuple(tuple(sorted((rng.random(), rng.random()))) for _ in range(2))
            weights = (rng.uniform(-1, 1), rng.uniform(-1, 1))
            lo, hi = gain_bounds(candidate, baseline, weights, 0.1, 0.02)
            for x in itertools.product(*candidate):
                for y in itertools.product(*baseline):
                    value = sum(w * (a - b) for w, a, b in zip(weights, x, y)) - 0.08
                    self.assertLessEqual(lo - 1e-12, value)
                    self.assertGreaterEqual(hi + 1e-12, value)

    def test_identical_observations_opposite_revised_goals(self):
        # A=[1,0]; mu+ and mu- share A mu, but w=[0,1] separates them.
        minus, plus = (0.8, 0.1), (0.8, 0.9)
        self.assertEqual(minus[0], plus[0])
        self.assertLess(minus[1] - 0.5, 0)
        self.assertGreater(plus[1] - 0.5, 0)

    def test_observation_width_reduction(self):
        before = Evidence.from_rows([(None, None), (0.2, None)], 2)
        after = Evidence.from_rows([(0.7, None), (0.2, None)], 2)
        weights = (0.8, -0.2)
        a = linear_bounds(before.completion_box(), weights)
        b = linear_bounds(after.completion_box(), weights)
        self.assertAlmostEqual((a[1] - a[0]) - (b[1] - b[0]), abs(weights[0]) / 2)

    def test_pending_successes_not_unbiased_completed_sample(self):
        e = Evidence(1000, (350,), (350,))
        self.assertEqual(e.completed_means(), (1,))
        self.assertEqual(e.completion_box(), ((0.35, 1),))

    def test_family_error_budget(self):
        delta, k, d, limit = 0.05, 3, 2, 1000
        total = sum(
            k * d * 2 * math.exp(-2 * n * radius(n, k, d, delta) ** 2)
            for n in range(1, limit + 1)
        )
        self.assertAlmostEqual(total, delta * limit / (limit + 1))
        self.assertLess(total, delta)

    def test_invalid_evidence(self):
        for args in [
            (-1, (0,), (0,)), (1, (), ()), (1, (2,), (1,)),
            (1, (0,), (2,)), (1, (math.nan,), (1,)), (1, (0,), ()),
        ]:
            with self.assertRaises(ValueError):
                Evidence(*args)
        for row in [[1.1], [-0.1], [math.inf], [math.nan], [0, 1]]:
            with self.assertRaises(ValueError):
                Evidence.from_rows([row], 1)

    def test_invalid_budgets_and_drift(self):
        for args in [(0, 2, 1, 0.05), (1, 0, 1, 0.05), (1, 2, 1, 0), (1, 2, 1, 1)]:
            with self.assertRaises(ValueError):
                radius(*args)
        e = Evidence(0, (0,), (0,))
        for drift in [(), (-0.1,), (1.1,), (math.nan,)]:
            with self.assertRaises(ValueError):
                confidence_box(e, 2, 0.05, drift)
        with self.assertRaises(ValueError):
            confidence_box(e, 2, math.nan, (0,))

    def test_dimension_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            linear_bounds(((0, 1),), (0.5, 0.5))
        with self.assertRaises(ValueError):
            gain_bounds(((0, 1),), ((0, 1), (0, 1)), (1,))
        with self.assertRaises(ValueError):
            linear_bounds(((1, 0),), (1,))
        with self.assertRaises(ValueError):
            linear_bounds(((0, 1),), (math.nan,))

    def test_wilson_zero_events_is_not_zero_risk(self):
        lo, hi = wilson_interval(0, 400)
        self.assertAlmostEqual(lo, 0)
        self.assertGreater(hi, 0)
        self.assertLess(hi, 0.01)
        with self.assertRaises(ValueError):
            wilson_interval(401, 400)


if __name__ == "__main__":
    unittest.main()
