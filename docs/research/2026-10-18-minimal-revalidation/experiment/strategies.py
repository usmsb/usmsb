"""Five transparent heuristics; selectors never receive simulator/truth objects."""

from __future__ import annotations

from functools import lru_cache

from scenarios import PublicProblem

STRATEGIES = ("uniform", "full_identification", "decision_greedy", "hinted_coverage", "blind_reuse")
COVERAGE_PERIOD = 4
HINT_PERIOD = 4


class PublicScorer:
    def __init__(self, public: PublicProblem):
        self.public = public
        self.indices = {h: i for i, h in enumerate(public.hypothesis_ids)}
        self.probe_indices = {p: i for i, p in enumerate(public.probe_ids)}

    @lru_cache(maxsize=None)
    def scores(self, retained: tuple[str, ...], decision_only: bool) -> tuple[float, ...]:
        """Uniform retained-pair squared separation/cost, not entropy or HEC.

        Decision weights count symmetric action-set differences. They vanish
        for equal action sets, but not for merely pairwise-overlapping sets.
        """
        indices = [self.indices[h] for h in retained]
        pairs = []
        for pos, i in enumerate(indices):
            for j in indices[pos + 1:]:
                weight = (len(set(self.public.final_actions[i]) ^ set(self.public.final_actions[j]))
                          if decision_only else 1)
                if weight:
                    pairs.append((i, j, weight))
        return tuple(sum(weight * (self.public.kernels[i][column] -
                                   self.public.kernels[j][column]) ** 2
                         for i, j, weight in pairs) / self.public.costs[column]
                     for column in (self.probe_indices[p] for p in self.public.allowed_new))

    @lru_cache(maxsize=None)
    def indistinguishable(self, retained: tuple[str, ...]) -> bool:
        columns = [self.probe_indices[p] for p in self.public.allowed_new]
        return len({tuple(self.public.kernels[self.indices[h]][i] for i in columns)
                    for h in retained}) <= 1


class Policy:
    def __init__(self, name: str, scorer: PublicScorer):
        if name not in STRATEGIES:
            raise ValueError(name)
        self.name = name
        self.scorer = scorer
        self.round_robin_index = 0
        self.counts = dict.fromkeys(scorer.public.allowed_new, 0)
        self.selections = 0

    def _round_robin(self) -> str:
        allowed = self.scorer.public.allowed_new
        probe = allowed[self.round_robin_index % len(allowed)]
        self.round_robin_index += 1
        return probe

    def choose(self, retained: tuple[str, ...]) -> tuple[str, str]:
        """Inputs are only the public model, goal, allowlist, hint, and past evidence."""
        if self.name == "blind_reuse":
            raise ValueError("blind_reuse never probes")
        allowed = self.scorer.public.allowed_new
        if self.name == "uniform":
            probe, reason = self._round_robin(), "round_robin"
        elif self.name == "hinted_coverage":
            # Only complete groups of four spend one forced hint observation:
            # forced_hint_count <= floor(policy_observations / 4) at every prefix.
            if (self.selections + 1) % HINT_PERIOD == 0 and self.scorer.public.hint in allowed:
                probe, reason = self.scorer.public.hint, "hint_slot"
            else:
                probe, reason = self._round_robin(), "coverage"
        elif self.name == "decision_greedy" and (self.selections + 1) % COVERAGE_PERIOD == 0:
            probe, reason = self._round_robin(), "coverage"
        else:
            scores = self.scorer.scores(retained, self.name == "decision_greedy")
            if not scores or max(scores) == 0:
                probe, reason = self._round_robin(), "zero_score_coverage"
            else:
                # Ties use own past counts, then public declaration order.
                index = min(range(len(allowed)), key=lambda i: (-scores[i], self.counts[allowed[i]], i))
                probe, reason = allowed[index], "decision_separation" if self.name == "decision_greedy" else "all_hypotheses_separation"
        self.selections += 1
        self.counts[probe] += 1
        return probe, reason
