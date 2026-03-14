"""
Uncertainty Management Module

不确定性量化与管理
"""

import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProbabilityDistribution:
    """概率分布"""

    variable: str
    values: dict[Any, float]

    def __post_init__(self):
        total = sum(self.values.values())
        if total > 0:
            self.values = {k: v / total for k, v in self.values.items()}

    def get_probability(self, value: Any) -> float:
        return self.values.get(value, 0.0)

    def get_most_likely(self) -> tuple[Any, float]:
        if not self.values:
            return None, 0.0
        best = max(self.values.items(), key=lambda x: x[1])
        return best[0], best[1]

    def combine(
        self, other: "ProbabilityDistribution", method: str = "product"
    ) -> "ProbabilityDistribution":
        new_values = {}

        if method == "product":
            for v in set(self.values.keys()) | set(other.values.keys()):
                p1 = self.get_probability(v)
                p2 = other.get_probability(v)
                new_values[v] = p1 * p2

        elif method == "average":
            for v in set(self.values.keys()) | set(other.values.keys()):
                p1 = self.get_probability(v)
                p2 = other.get_probability(v)
                new_values[v] = (p1 + p2) / 2

        return ProbabilityDistribution(
            variable=f"combined_{self.variable}_{other.variable}",
            values=new_values,
        )

    def entropy(self) -> float:
        return -sum(p * math.log2(p) if p > 0 else 0 for p in self.values.values())


@dataclass
class FuzzySet:
    """模糊集合"""

    variable: str
    membership: dict[Any, float]

    def __post_init__(self):
        self.membership = {k: max(0.0, min(1.0, v)) for k, v in self.membership.items()}

    def get_membership(self, value: Any) -> float:
        return self.membership.get(value, 0.0)

    def alpha_cut(self, alpha: float) -> set[Any]:
        return {k for k, v in self.membership.items() if v >= alpha}

    def union(self, other: "FuzzySet") -> "FuzzySet":
        new_membership = {}
        for k in set(self.membership.keys()) | set(other.membership.keys()):
            new_membership[k] = max(self.get_membership(k), other.get_membership(k))
        return FuzzySet(
            variable=f"union_{self.variable}_{other.variable}",
            membership=new_membership,
        )

    def intersection(self, other: "FuzzySet") -> "FuzzySet":
        new_membership = {}
        for k in set(self.membership.keys()) | set(other.membership.keys()):
            new_membership[k] = min(self.get_membership(k), other.get_membership(k))
        return FuzzySet(
            variable=f"intersection_{self.variable}_{other.variable}",
            membership=new_membership,
        )

    def complement(self) -> "FuzzySet":
        return FuzzySet(
            variable=f"complement_{self.variable}",
            membership={k: 1.0 - v for k, v in self.membership.items()},
        )

    def centroid(self) -> float:
        if not self.membership:
            return 0.0

        total_membership = sum(self.membership.values())
        if total_membership == 0:
            return 0.0

        weighted_sum = sum(
            float(k) * v if isinstance(k, (int, float)) else v for k, v in self.membership.items()
        )
        return weighted_sum / total_membership


@dataclass
class DempsterShafer:
    """Dempster-Shafer证据理论"""

    frame: set[str]
    mass_functions: dict[frozenset, float] = field(default_factory=dict)

    def add_mass(self, subset: set[str], mass: float) -> None:
        key = frozenset(subset)
        self.mass_functions[key] = self.mass_functions.get(key, 0) + mass

    def belief(self, subset: set[str]) -> float:
        target = frozenset(subset)
        return sum(mass for key, mass in self.mass_functions.items() if key <= target)

    def plausibility(self, subset: set[str]) -> float:
        target = frozenset(subset)
        return sum(mass for key, mass in self.mass_functions.items() if key & target)

    def belief_interval(self, subset: set[str]) -> tuple[float, float]:
        return self.belief(subset), self.plausibility(subset)

    def combine(self, other: "DempsterShafer") -> "DempsterShafer":
        combined = DempsterShafer(frame=self.frame | other.frame)

        conflict = 0.0
        intermediate: dict[frozenset, float] = defaultdict(float)

        for key1, mass1 in self.mass_functions.items():
            for key2, mass2 in other.mass_functions.items():
                intersection = key1 & key2
                if not intersection:
                    conflict += mass1 * mass2
                else:
                    intermediate[intersection] += mass1 * mass2

        normalization = 1.0 - conflict

        if normalization > 0:
            for key, mass in intermediate.items():
                combined.mass_functions[key] = mass / normalization

        return combined

    def get_most_plausible(self) -> tuple[str, float]:
        if not self.frame:
            return "", 0.0

        best = max([(e, self.plausibility({e})) for e in self.frame], key=lambda x: x[1])
        return best


@dataclass
class BayesianNode:
    """贝叶斯网络节点"""

    name: str
    states: list[str]
    parents: list[str] = field(default_factory=list)
    cpt: dict[str, dict[str, float]] = field(default_factory=dict)


class BayesianNetwork:
    """贝叶斯网络"""

    def __init__(self):
        self.nodes: dict[str, BayesianNode] = {}
        self.evidence: dict[str, str] = {}

    def add_node(self, name: str, states: list[str], parents: list[str] | None = None) -> None:
        self.nodes[name] = BayesianNode(
            name=name,
            states=states,
            parents=parents or [],
        )

    def set_cpt(self, node_name: str, cpt: dict[str, dict[str, float]]) -> None:
        if node_name in self.nodes:
            self.nodes[node_name].cpt = cpt

    def set_evidence(self, node_name: str, state: str) -> None:
        if node_name in self.nodes:
            self.evidence[node_name] = state

    def query(self, query_node: str) -> dict[str, float]:
        if query_node not in self.nodes:
            return {}

        node = self.nodes[query_node]

        if query_node in self.evidence:
            return {self.evidence[query_node]: 1.0}

        if not node.parents:
            if node.cpt:
                return node.cpt.get("prior", {s: 1.0 / len(node.states) for s in node.states})
            return {s: 1.0 / len(node.states) for s in node.states}

        result = dict.fromkeys(node.states, 0.0)

        for parent_state_key, probs in node.cpt.items():
            parent_states = parent_state_key.split(",")
            valid = True

            for i, parent in enumerate(node.parents):
                if parent in self.evidence:
                    if parent_states[i] != self.evidence[parent]:
                        valid = False
                        break

            if valid:
                for state, prob in probs.items():
                    result[state] += prob

        total = sum(result.values())
        if total > 0:
            result = {k: v / total for k, v in result.items()}

        return result


class UncertaintyManager:
    """不确定性管理器"""

    def __init__(self):
        self._probability_dists: dict[str, ProbabilityDistribution] = {}
        self._fuzzy_sets: dict[str, FuzzySet] = {}
        self._dempster_shafer: dict[str, DempsterShafer] = {}
        self._bayesian_networks: dict[str, BayesianNetwork] = {}

    def create_probability_distribution(
        self, variable: str, values: dict[Any, float]
    ) -> ProbabilityDistribution:
        dist = ProbabilityDistribution(variable=variable, values=values)
        self._probability_dists[variable] = dist
        return dist

    def create_fuzzy_set(self, variable: str, membership: dict[Any, float]) -> FuzzySet:
        fs = FuzzySet(variable=variable, membership=membership)
        self._fuzzy_sets[variable] = fs
        return fs

    def create_dempster_shafer(self, name: str, frame: set[str]) -> DempsterShafer:
        ds = DempsterShafer(frame=frame)
        self._dempster_shafer[name] = ds
        return ds

    def create_bayesian_network(self, name: str) -> BayesianNetwork:
        bn = BayesianNetwork()
        self._bayesian_networks[name] = bn
        return bn

    def get_probability_distribution(self, variable: str) -> ProbabilityDistribution | None:
        return self._probability_dists.get(variable)

    def get_fuzzy_set(self, variable: str) -> FuzzySet | None:
        return self._fuzzy_sets.get(variable)

    def combine_evidence(
        self, sources: list[tuple[str, float, dict[Any, float]]], method: str = "weighted_average"
    ) -> dict[Any, float]:
        if not sources:
            return {}

        combined: dict[Any, float] = defaultdict(float)
        total_weight = 0.0

        for _source_name, confidence, values in sources:
            weight = confidence
            total_weight += weight

            for key, value in values.items():
                combined[key] += weight * value

        if method == "weighted_average" and total_weight > 0:
            combined = {k: v / total_weight for k, v in combined.items()}

        return dict(combined)

    def propagate_uncertainty(
        self, input_uncertainty: dict[str, Any], propagation_function: callable
    ) -> dict[str, Any]:
        return propagation_function(input_uncertainty)

    def measure_total_uncertainty(self, distribution: dict[Any, float]) -> float:
        if not distribution:
            return 1.0

        return -sum(p * math.log2(p) if p > 0 else 0 for p in distribution.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "probability_distributions": {
                k: {"variable": v.variable, "values": v.values}
                for k, v in self._probability_dists.items()
            },
            "fuzzy_sets": {
                k: {"variable": v.variable, "membership": v.membership}
                for k, v in self._fuzzy_sets.items()
            },
            "bayesian_networks": list(self._bayesian_networks.keys()),
        }
