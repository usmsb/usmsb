"""Offline research calculator, NOT an authorization or semantic decision engine.

Implements Proposition C in ../03-mathematical-results.md.
Missing-outcome bracketing follows existing partial-identification/OPSE ideas.
The caller must justify comparability, bounded outcomes, and drift assumptions.
"""

from dataclasses import dataclass
from math import isfinite, log, sqrt
from typing import Iterable, Sequence


def _integer(value: int, name: str, minimum: int = 0) -> None:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")


def _finite(value: float, name: str) -> None:
    if not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be finite")


@dataclass(frozen=True)
class Evidence:
    """All enrollments count; None means unknown, never zero reward."""

    n: int
    sums: tuple[float, ...]
    observed: tuple[int, ...]

    def __post_init__(self) -> None:
        _integer(self.n, "n")
        if not self.sums or len(self.sums) != len(self.observed):
            raise ValueError("nonempty equal dimensions required")
        for total, count in zip(self.sums, self.observed):
            _integer(count, "observed")
            _finite(total, "sum")
            if count > self.n or not 0 <= total <= count:
                raise ValueError("invalid bounded-outcome sufficient statistics")

    @classmethod
    def from_rows(
        cls, rows: Iterable[Sequence[float | None]], dimensions: int
    ) -> "Evidence":
        _integer(dimensions, "dimensions", 1)
        totals = [0.0] * dimensions
        counts = [0] * dimensions
        n = 0
        for row in rows:
            if len(row) != dimensions:
                raise ValueError("row dimension mismatch")
            for j, value in enumerate(row):
                if value is not None:
                    _finite(value, "outcome")
                    if not 0 <= value <= 1:
                        raise ValueError("outcome must be in [0,1]")
                    totals[j] += value
                    counts[j] += 1
            n += 1
        return cls(n, tuple(totals), tuple(counts))

    def completion_box(self) -> tuple[tuple[float, float], ...]:
        if not self.n:
            return tuple((0.0, 1.0) for _ in self.sums)
        return tuple(
            (s / self.n, (s + self.n - observed) / self.n)
            for s, observed in zip(self.sums, self.observed)
        )

    def completed_means(self) -> tuple[float | None, ...]:
        """Deliberately naive comparator; not a generally unbiased estimate."""
        return tuple(
            s / count if count else None for s, count in zip(self.sums, self.observed)
        )


def radius(n: int, candidates: int, dimensions: int, delta: float) -> float:
    _integer(n, "n", 1)
    _integer(candidates, "candidates", 1)
    _integer(dimensions, "dimensions", 1)
    _finite(delta, "delta")
    if not 0 < delta < 1:
        raise ValueError("delta must be in (0,1)")
    # Sum logs rather than multiplying large integers into a floating value.
    log_budget = (
        log(2) + log(candidates) + log(dimensions) + log(n) + log(n + 1) - log(delta)
    )
    return sqrt(log_budget / (2 * n))


def confidence_box(
    evidence: Evidence,
    candidates: int,
    delta: float,
    drift: Sequence[float],
) -> tuple[tuple[float, float], ...]:
    dimensions = len(evidence.sums)
    # Validate the family and budget even when there are no enrollments.
    r = radius(max(1, evidence.n), candidates, dimensions, delta)
    if len(drift) != dimensions:
        raise ValueError("drift dimension mismatch")
    for amount in drift:
        _finite(amount, "drift")
        if not 0 <= amount <= 1:
            raise ValueError("normalized drift must be in [0,1]")
    if not evidence.n:
        return evidence.completion_box()
    return tuple(
        (max(0.0, lo - r - amount), min(1.0, hi + r + amount))
        for (lo, hi), amount in zip(evidence.completion_box(), drift)
    )


def linear_bounds(
    box: Sequence[tuple[float, float]], weights: Sequence[float], cost: float = 0.0
) -> tuple[float, float]:
    if not box or len(box) != len(weights):
        raise ValueError("weight dimension mismatch")
    _finite(cost, "cost")
    lower = upper = -cost
    for (lo, hi), weight in zip(box, weights):
        _finite(lo, "lower")
        _finite(hi, "upper")
        _finite(weight, "weight")
        if lo > hi:
            raise ValueError("empty interval")
        lower += weight * (lo if weight >= 0 else hi)
        upper += weight * (hi if weight >= 0 else lo)
    return lower, upper


def gain_bounds(
    candidate: Sequence[tuple[float, float]],
    baseline: Sequence[tuple[float, float]],
    weights: Sequence[float],
    candidate_cost: float = 0.0,
    baseline_cost: float = 0.0,
) -> tuple[float, float]:
    lo_k, hi_k = linear_bounds(candidate, weights, candidate_cost)
    lo_0, hi_0 = linear_bounds(baseline, weights, baseline_cost)
    return lo_k - hi_0, hi_k - lo_0


def wilson_interval(successes: int, trials: int) -> tuple[float, float]:
    """95% interval for Monte Carlo event frequency, not a system guarantee."""
    _integer(successes, "successes")
    _integer(trials, "trials", 1)
    if successes > trials:
        raise ValueError("successes exceeds trials")
    z = 1.959963984540054
    p = successes / trials
    scale = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / scale
    half = z * sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / scale
    return max(0.0, center - half), min(1.0, center + half)
