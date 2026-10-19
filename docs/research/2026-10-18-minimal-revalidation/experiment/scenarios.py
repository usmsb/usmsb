"""Prespecified finite synthetic cases. Truth stays in the simulator specification.

No claim of AI behavior, a new algorithm, or external validity is made here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product


@dataclass(frozen=True)
class PublicProblem:
    case_id: str
    description: str
    hypothesis_ids: tuple[str, ...]
    probe_ids: tuple[str, ...]
    scopes: tuple[str, ...]
    costs: tuple[float, ...]
    kernels: tuple[tuple[float, ...], ...]
    allowed_new: tuple[str, ...]
    initial_actions: tuple[tuple[str, ...], ...]
    final_actions: tuple[tuple[str, ...], ...]
    old_action: str
    hint: str
    # A fixed, policy-independent current-scope prefix precedes a goal revision.
    revision_prefix: tuple[str, ...] = ()

    def goal(self, *, final: bool = True) -> dict[str, set[str]]:
        actions = self.final_actions if final else self.initial_actions
        return {h: set(a) for h, a in zip(self.hypothesis_ids, actions, strict=True)}

    def model_dict(self) -> dict:
        return {
            "family_id": f"offline-revalidation-v1/{self.case_id}",
            "probes": [dict(id=p, scope=s, cost=c) for p, s, c in
                       zip(self.probe_ids, self.scopes, self.costs, strict=True)],
            "hypotheses": [dict(id=h, probabilities=dict(zip(self.probe_ids, k, strict=True)))
                           for h, k in zip(self.hypothesis_ids, self.kernels, strict=True)],
        }


@dataclass(frozen=True)
class SimulatorSpec:
    public: PublicProblem
    guarantee_applies: bool = True
    outside_probabilities: tuple[float, ...] | None = None
    outside_actions: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


def _case(case_id: str, description: str, kernels: tuple[tuple[float, ...], ...],
          actions: tuple[tuple[str, ...], ...], *, old_action: str = "a0",
          allowed: tuple[int, ...] | None = None, hint: int = 0,
          new_costs: tuple[float, ...] | None = None,
          initial: tuple[tuple[str, ...], ...] | None = None,
          prefix: tuple[int, ...] = ()) -> PublicProblem:
    width = len(kernels[0])
    ids = tuple(f"new_{i}" for i in range(width))
    return PublicProblem(
        case_id, description, tuple(f"h{i:02d}" for i in range(len(kernels))),
        ("old_success",) + ids, ("old",) + ("new",) * width,
        (2.0,) + (new_costs or (1.0,) * width),
        tuple((0.9,) + row for row in kernels),
        tuple(ids[i] for i in (range(width) if allowed is None else allowed)),
        initial or actions, actions, old_action, ids[hint], tuple(ids[i] for i in prefix),
    )


def _bits(width: int) -> tuple[tuple[int, ...], ...]:
    return tuple(product((0, 1), repeat=width))


def _kernels(bits: tuple[tuple[int, ...], ...]) -> tuple[tuple[float, ...], ...]:
    return tuple(tuple(0.9 if bit else 0.1 for bit in row) for row in bits)


def cases() -> tuple[SimulatorSpec, ...]:
    result = []
    bits = _bits(5)
    result.append(SimulatorSpec(_case(
        "irrelevant_nuisance", "One decision bit, four irrelevant nuisance bits; H has 32 members.",
        _kernels(bits), tuple((f"a{row[0]}",) for row in bits),
        new_costs=(1.0, 1.5, 1.5, 1.5, 1.5))))

    # Neither the policy nor its hint receives the true changed location.
    faults = tuple(tuple(int(location == i) for i in range(4)) for location in range(-1, 4))
    result.append(SimulatorSpec(_case(
        "unknown_changed_location", "No fault or exactly one of four changed locations, hidden from policies.",
        _kernels(faults), (("maintain",),) + tuple((f"repair_{i}",) for i in range(4)),
        old_action="maintain")))

    result.append(SimulatorSpec(_case(
        "unidentifiable_conflict", "Identical kernels, disjoint acceptable actions: evidence cannot decide.",
        ((0.5,), (0.5,)), (("a0",), ("a1",)))))

    bits = _bits(3)
    result.append(SimulatorSpec(_case(
        "goal_revision", "After a common 24-observation new_0 prefix, goal changes from bit 0 to bit 1; H and kernels stay fixed.",
        _kernels(bits), tuple((f"a{row[1]}",) for row in bits),
        initial=tuple((f"a{row[0]}",) for row in bits), prefix=(0,) * 24)))

    bits = _bits(4)
    result.append(SimulatorSpec(_case(
        "misleading_hint", "Hint always names irrelevant new_0; only bit 3 affects the action.",
        _kernels(bits), tuple((f"a{row[3]}",) for row in bits), hint=0)))

    bits = _bits(2)
    result.append(SimulatorSpec(_case(
        "restricted_probes", "Decision bit 1 cannot be observed: only nuisance probe new_0 is authorized.",
        _kernels(bits), tuple((f"a{row[1]}",) for row in bits), allowed=(0,))))

    outside = _case(
        "outside_family", "True new probability is 0.85, outside {0.1,0.9}, but only a0 is correct; confident wrong a1 is possible.",
        ((0.1,), (0.9,)), (("a0",), ("a1",)))
    result.append(SimulatorSpec(outside, False, (0.9, 0.85), ("a0",)))

    result.append(SimulatorSpec(_case(
        "multiple_correct_actions", "Three pairwise-overlapping action sets have no global intersection; eliminating one member can suffice.",
        ((0.9, 0.1, 0.1), (0.1, 0.9, 0.1), (0.1, 0.1, 0.9)),
        (("a", "b"), ("a", "c"), ("b", "c")), old_action="a")))

    result.append(SimulatorSpec(_case(
        "scope_shift", "All joint hypotheses predict the same old successes; history provides no evidence about current change.",
        ((0.1,), (0.9,)), (("reuse",), ("switch",)), old_action="reuse")))

    result.append(SimulatorSpec(_case(
        "weak_signal_budget", "Small known separation, p=0.48 versus 0.52; unresolved runs at 800 remain failures to conclude.",
        ((0.48,), (0.52,)), (("a0",), ("a1",)))))
    return tuple(result)
