"""Dynamic Group Loop; the model selects roles, this code only runs them safely."""

from __future__ import annotations

import asyncio
from typing import Protocol

from usmsb_sdk.growth_economic_harness.models import TeamRole
from usmsb_sdk.growth_economic_harness.ports import (
    GroupContribution,
    GroupReasoner,
    GroupRequest,
    GroupResult,
)


class RoleReasoner(Protocol):
    async def reason(self, role: TeamRole, request: GroupRequest) -> GroupContribution: ...


class GroupSynthesizer(Protocol):
    async def synthesize(
        self,
        request: GroupRequest,
        contributions: list[GroupContribution],
    ) -> GroupResult: ...


class DynamicGroupLoop(GroupReasoner):
    """Run exactly the roles chosen in ``TeamPlan`` and preserve disagreement."""

    def __init__(
        self,
        role_reasoner: RoleReasoner,
        synthesizer: GroupSynthesizer,
        *,
        max_parallel_roles: int = 12,
    ) -> None:
        self.role_reasoner = role_reasoner
        self.synthesizer = synthesizer
        self.max_parallel_roles = max(1, max_parallel_roles)

    async def deliberate(self, request: GroupRequest) -> GroupResult:
        roles = request.team_plan.roles
        if len(roles) > self.max_parallel_roles:
            raise ValueError(
                f"model selected {len(roles)} roles; limit is {self.max_parallel_roles}"
            )
        contributions = await asyncio.gather(
            *(self.role_reasoner.reason(role, request) for role in roles)
        )
        result = await self.synthesizer.synthesize(request, list(contributions))
        returned_roles = {item.role for item in result.contributions}
        expected_roles = {role.name for role in roles}
        if returned_roles != expected_roles:
            raise ValueError(
                "group result lost or invented roles: "
                f"expected={sorted(expected_roles)}, returned={sorted(returned_roles)}"
            )
        return result
