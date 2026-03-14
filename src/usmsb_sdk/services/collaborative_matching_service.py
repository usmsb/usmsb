"""
Collaborative Matching Service

This module implements collaborative matching for complex tasks:
- Analyze if a goal requires multiple agents
- Organize collaboration sessions
- Coordinate multi-agent task execution
- Integrate results from multiple agents

Key Features:
1. Collaboration Analysis: Determine if collaboration is needed
2. Role Assignment: Assign roles to different agents
3. Coordination: Coordinate execution across agents
4. Result Integration: Combine outputs from multiple agents
"""

import asyncio
import json
import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from usmsb_sdk.core.communication.agent_communication import (
    AgentAddress,
    AgentCommunicationManager,
    MessageType,
)
from usmsb_sdk.core.elements import Agent, Goal
from usmsb_sdk.intelligence_adapters.base import ILLMAdapter
from usmsb_sdk.node.decentralized_node import DistributedServiceRegistry
from usmsb_sdk.services.active_matching_service import (
    ActiveMatchingService,
)

logger = logging.getLogger(__name__)


class CollaborationMode(StrEnum):
    """Mode of collaboration."""
    PARALLEL = "parallel"       # Agents work simultaneously
    SEQUENTIAL = "sequential"    # Agents work in sequence
    HYBRID = "hybrid"           # Mix of parallel and sequential


class CollaborationStatus(StrEnum):
    """Status of collaboration session."""
    ANALYZING = "analyzing"
    ORGANIZING = "organizing"
    EXECUTING = "executing"
    INTEGRATING = "integrating"
    COMPLETED = "completed"
    FAILED = "failed"


class RoleType(StrEnum):
    """Type of role in collaboration."""
    COORDINATOR = "coordinator"
    PRIMARY = "primary"
    SPECIALIST = "specialist"
    SUPPORT = "support"
    VALIDATOR = "validator"


@dataclass
class CollaborationRole:
    """A role in a collaboration session."""
    role_id: str
    role_type: RoleType
    required_skills: list[str]
    assigned_agent_id: str | None = None
    assigned_agent_name: str | None = None
    status: str = "pending"  # pending, assigned, executing, completed
    contribution: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "role_id": self.role_id,
            "role_type": self.role_type.value,
            "required_skills": self.required_skills,
            "assigned_agent_id": self.assigned_agent_id,
            "assigned_agent_name": self.assigned_agent_name,
            "status": self.status,
            "contribution": self.contribution,
        }


@dataclass
class CollaborationPlan:
    """Plan for a collaboration session."""
    plan_id: str
    goal_id: str
    goal_description: str
    mode: CollaborationMode
    roles: list[CollaborationRole]
    dependencies: dict[str, list[str]] = field(default_factory=dict)  # role_id -> dependent role_ids
    estimated_duration: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal_id": self.goal_id,
            "goal_description": self.goal_description,
            "mode": self.mode.value,
            "roles": [r.to_dict() for r in self.roles],
            "dependencies": self.dependencies,
            "estimated_duration": self.estimated_duration,
            "created_at": self.created_at,
        }


@dataclass
class CollaborationSession:
    """A collaboration session between multiple agents."""
    session_id: str
    goal: Goal
    plan: CollaborationPlan
    status: CollaborationStatus
    participants: list[str] = field(default_factory=list)
    coordinator_id: str | None = None
    started_at: float | None = None
    completed_at: float | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "goal": {"id": self.goal.id, "name": self.goal.name, "description": self.goal.description},
            "plan": self.plan.to_dict(),
            "status": self.status.value,
            "participants": self.participants,
            "coordinator_id": self.coordinator_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error,
        }


@dataclass
class ParticipantInvite:
    """Invitation to join a collaboration session."""
    invite_id: str
    session_id: str
    role: CollaborationRole
    status: str = "pending"  # pending, accepted, rejected
    response_message: str | None = None


class CollaborativeMatchingService:
    """
    Collaborative Matching Service

    Enables multiple agents to collaborate on complex tasks
    that cannot be completed by a single agent.
    """

    def __init__(
        self,
        active_matching: ActiveMatchingService,
        communication_manager: AgentCommunicationManager,
        llm_adapter: ILLMAdapter,
        registry: DistributedServiceRegistry,
    ):
        """
        Initialize the Collaborative Matching Service.

        Args:
            active_matching: For finding and matching agents
            communication_manager: For agent communication
            llm_adapter: For intelligent planning
            registry: For service discovery
        """
        self.active_matching = active_matching
        self.comm = communication_manager
        self.llm = llm_adapter
        self.registry = registry

        # Active collaboration sessions
        self._sessions: dict[str, CollaborationSession] = {}

        # Pending invitations
        self._invitations: dict[str, ParticipantInvite] = {}

        # Callbacks
        self.on_session_started: Callable[[CollaborationSession], None] | None = None
        self.on_session_completed: Callable[[CollaborationSession], None] | None = None
        self.on_participant_joined: Callable[[str, str], None] | None = None

    async def analyze_collaboration_need(
        self,
        goal: Goal,
    ) -> CollaborationPlan:
        """
        Analyze if a goal requires collaboration.

        Args:
            goal: The goal to analyze

        Returns:
            Collaboration plan if needed, None otherwise
        """
        required_skills = goal.metadata.get("required_skills", [])
        complexity = goal.metadata.get("complexity", "medium")

        # Use LLM to analyze collaboration need
        analysis_prompt = f"""
        分析以下需求是否需要多个Agent协作完成：

        需求：{goal.description}
        所需技能：{required_skills}
        复杂度：{complexity}

        请判断：
        1. 是否需要多Agent协作 (是/否)
        2. 如果需要，建议的Agent角色分工
        3. 协作模式（并行/串行/混合）
        4. 每个角色需要的技能

        以JSON格式返回，格式：
        {{
            "need_collaboration": true/false,
            "mode": "parallel/sequential/hybrid",
            "roles": [
                {{
                    "role_type": "coordinator/primary/specialist/support/validator",
                    "required_skills": ["skill1", "skill2"]
                }}
            ],
            "estimated_duration": 3600,
            "reasoning": "分析理由"
        }}
        """

        try:
            response = await self.llm_adapter.generate_text(analysis_prompt)
            result = json.loads(response)

            if not result.get("need_collaboration", False):
                return None

            # Create collaboration plan
            plan_id = str(uuid.uuid4())
            roles = []
            for role_data in result.get("roles", []):
                role = CollaborationRole(
                    role_id=str(uuid.uuid4()),
                    role_type=RoleType(role_data.get("role_type", "specialist")),
                    required_skills=role_data.get("required_skills", []),
                )
                roles.append(role)

            plan = CollaborationPlan(
                plan_id=plan_id,
                goal_id=goal.id,
                goal_description=goal.description,
                mode=CollaborationMode(result.get("mode", "hybrid")),
                roles=roles,
                estimated_duration=result.get("estimated_duration", 3600),
            )

            return plan

        except Exception as e:
            logger.error(f"Collaboration analysis error: {e}")
            # Fallback: simple analysis based on skills
            if len(required_skills) > 3:
                return self._create_simple_plan(goal, required_skills)
            return None

    def _create_simple_plan(self, goal: Goal, skills: list[str]) -> CollaborationPlan:
        """Create a simple collaboration plan based on skills count."""
        plan_id = str(uuid.uuid4())

        # Split skills among roles
        primary_skills = skills[:len(skills)//2 + 1] if skills else []
        support_skills = skills[len(skills)//2 + 1:] if len(skills) > 1 else []

        roles = [
            CollaborationRole(
                role_id=str(uuid.uuid4()),
                role_type=RoleType.PRIMARY,
                required_skills=primary_skills,
            ),
        ]

        if support_skills:
            roles.append(CollaborationRole(
                role_id=str(uuid.uuid4()),
                role_type=RoleType.SUPPORT,
                required_skills=support_skills,
            ))

        return CollaborationPlan(
            plan_id=plan_id,
            goal_id=goal.id,
            goal_description=goal.description,
            mode=CollaborationMode.HYBRID,
            roles=roles,
            estimated_duration=3600,
        )

    async def organize_collaboration(
        self,
        goal: Goal,
        plan: CollaborationPlan,
        coordinator_agent: Agent,
    ) -> CollaborationSession:
        """
        Organize a collaboration session.

        Args:
            goal: The goal to achieve
            plan: Collaboration plan
            coordinator_agent: The agent coordinating the collaboration

        Returns:
            Collaboration session
        """
        session = CollaborationSession(
            session_id=str(uuid.uuid4()),
            goal=goal,
            plan=plan,
            status=CollaborationStatus.ORGANIZING,
            coordinator_id=coordinator_agent.id,
        )

        self._sessions[session.session_id] = session

        # Find agents for each role
        for role in plan.roles:
            # Search for agents with matching skills
            candidates = await self.active_matching.demander_search_suppliers(
                demander_agent=coordinator_agent,
                goal=Goal(
                    name=f"Find {role.role_type.value}",
                    description=f"Need agent with skills: {', '.join(role.required_skills)}",
                    metadata={"required_skills": role.required_skills},
                ),
            )

            if candidates:
                best_candidate = candidates[0]
                role.assigned_agent_id = best_candidate.counterpart_agent_id
                role.assigned_agent_name = best_candidate.counterpart_name

                # Send invitation
                await self._send_invitation(
                    session_id=session.session_id,
                    role=role,
                    target_agent_id=best_candidate.counterpart_agent_id,
                )

        # Update session participants
        session.participants = [
            r.assigned_agent_id for r in plan.roles
            if r.assigned_agent_id
        ]

        if self.on_session_started:
            self.on_session_started(session)

        return session

    async def _send_invitation(
        self,
        session_id: str,
        role: CollaborationRole,
        target_agent_id: str,
    ) -> None:
        """Send invitation to join collaboration."""
        invite = ParticipantInvite(
            invite_id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
        )
        self._invitations[invite.invite_id] = invite

        # Send invitation message
        await self.comm.send(
            recipient=AgentAddress(agent_id=target_agent_id, node_id=""),
            subject=f"Collaboration Invitation: {role.role_type.value}",
            content={
                "type": "collaboration_invitation",
                "invite_id": invite.invite_id,
                "session_id": session_id,
                "role": role.to_dict(),
                "message": f"You are invited to join as a {role.role_type.value}",
            },
            message_type=MessageType.REQUEST,
        )

    async def handle_invitation_response(
        self,
        invite_id: str,
        accepted: bool,
        response_message: str = "",
    ) -> bool:
        """Handle response to collaboration invitation."""
        if invite_id not in self._invitations:
            return False

        invite = self._invitations[invite_id]
        invite.status = "accepted" if accepted else "rejected"
        invite.response_message = response_message

        if accepted:
            invite.role.status = "assigned"

            # Update session
            session = self._sessions.get(invite.session_id)
            if session:
                session.participants.append(invite.role.assigned_agent_id)

                if self.on_participant_joined:
                    self.on_participant_joined(
                        session.session_id,
                        invite.role.assigned_agent_id,
                    )

        return accepted

    async def execute_collaboration(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        """
        Execute a collaboration session.

        Args:
            session_id: The session to execute

        Returns:
            Execution results
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.status = CollaborationStatus.EXECUTING
        session.started_at = time.time()

        try:
            if session.plan.mode == CollaborationMode.PARALLEL:
                result = await self._execute_parallel(session)
            elif session.plan.mode == CollaborationMode.SEQUENTIAL:
                result = await self._execute_sequential(session)
            else:  # HYBRID
                result = await self._execute_hybrid(session)

            session.status = CollaborationStatus.COMPLETED
            session.result = result
            session.completed_at = time.time()

        except Exception as e:
            logger.error(f"Collaboration execution error: {e}")
            session.status = CollaborationStatus.FAILED
            session.error = str(e)

        if self.on_session_completed:
            self.on_session_completed(session)

        return session.to_dict()

    async def _execute_parallel(
        self,
        session: CollaborationSession,
    ) -> dict[str, Any]:
        """Execute collaboration in parallel mode."""
        tasks = []

        for role in session.plan.roles:
            if role.assigned_agent_id:
                task = self._execute_role(role, session)
                tasks.append(task)

        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results
        combined = {
            "mode": "parallel",
            "contributions": {},
            "final_output": None,
        }

        for i, role in enumerate(session.plan.roles):
            if role.assigned_agent_id:
                if isinstance(results[i], Exception):
                    combined["contributions"][role.role_id] = {"error": str(results[i])}
                else:
                    combined["contributions"][role.role_id] = results[i]

        # Integrate results
        combined["final_output"] = await self._integrate_results(combined["contributions"])

        return combined

    async def _execute_sequential(
        self,
        session: CollaborationSession,
    ) -> dict[str, Any]:
        """Execute collaboration in sequential mode."""
        contributions = {}
        previous_output = None

        for role in session.plan.roles:
            if not role.assigned_agent_id:
                continue

            role.status = "executing"

            # Execute role with previous output as input
            result = await self._execute_role(
                role,
                session,
                input_data=previous_output,
            )

            contributions[role.role_id] = result
            previous_output = result
            role.status = "completed"

        return {
            "mode": "sequential",
            "contributions": contributions,
            "final_output": previous_output,
        }

    async def _execute_hybrid(
        self,
        session: CollaborationSession,
    ) -> dict[str, Any]:
        """Execute collaboration in hybrid mode (mix of parallel and sequential)."""
        # Group roles by dependency level
        contributions = {}

        # Execute independent roles in parallel first
        independent_roles = [
            r for r in session.plan.roles
            if not session.plan.dependencies.get(r.role_id)
        ]

        if independent_roles:
            tasks = [
                self._execute_role(role, session)
                for role in independent_roles
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for role, result in zip(independent_roles, results, strict=False):
                if isinstance(result, Exception):
                    contributions[role.role_id] = {"error": str(result)}
                else:
                    contributions[role.role_id] = result

        # Execute dependent roles sequentially
        for role in session.plan.roles:
            if session.plan.dependencies.get(role.role_id) and role.assigned_agent_id:
                role.status = "executing"
                result = await self._execute_role(
                    role,
                    session,
                    input_data=contributions,
                )
                contributions[role.role_id] = result
                role.status = "completed"

        return {
            "mode": "hybrid",
            "contributions": contributions,
            "final_output": await self._integrate_results(contributions),
        }

    async def _execute_role(
        self,
        role: CollaborationRole,
        session: CollaborationSession,
        input_data: Any = None,
    ) -> dict[str, Any]:
        """Execute a single role in collaboration."""
        if not role.assigned_agent_id:
            return {"error": "No agent assigned"}

        # Send task request to agent
        request_content = {
            "type": "collaboration_task",
            "session_id": session.session_id,
            "role": role.to_dict(),
            "goal_description": session.goal.description,
            "input_data": input_data,
        }

        try:
            response = await self.comm.request(
                recipient=AgentAddress(agent_id=role.assigned_agent_id, node_id=""),
                subject=f"Task: {role.role_type.value}",
                content=request_content,
                timeout=300.0,  # 5 minutes
            )

            if response and response.content:
                role.contribution = response.content
                role.status = "completed"
                return response.content

        except Exception as e:
            logger.error(f"Role execution error: {e}")
            role.status = "failed"
            return {"error": str(e)}

        return {"error": "No response"}

    async def _integrate_results(
        self,
        contributions: dict[str, Any],
    ) -> dict[str, Any]:
        """Integrate results from multiple agents."""
        # Use LLM to integrate results
        integration_prompt = f"""
        整合以下多个Agent的输出，形成最终结果：

        {json.dumps(contributions, indent=2, ensure_ascii=False)}

        请分析并整合这些输出，形成一个统一的结果。
        以JSON格式返回整合后的结果。
        """

        try:
            response = await self.llm_adapter.generate_text(integration_prompt)
            return json.loads(response)
        except Exception as e:
            logger.error(f"Result integration error: {e}")
            # Fallback: just combine all outputs
            return {
                "integrated": True,
                "outputs": list(contributions.values()),
            }

    def get_session(self, session_id: str) -> CollaborationSession | None:
        """Get a collaboration session by ID."""
        return self._sessions.get(session_id)

    def get_active_sessions(self) -> list[CollaborationSession]:
        """Get all active collaboration sessions."""
        return [
            s for s in self._sessions.values()
            if s.status in [CollaborationStatus.ORGANIZING, CollaborationStatus.EXECUTING]
        ]

    def get_session_stats(self) -> dict[str, Any]:
        """Get collaboration statistics."""
        total = len(self._sessions)
        completed = sum(1 for s in self._sessions.values() if s.status == CollaborationStatus.COMPLETED)
        failed = sum(1 for s in self._sessions.values() if s.status == CollaborationStatus.FAILED)

        return {
            "total_sessions": total,
            "active_sessions": total - completed - failed,
            "completed_sessions": completed,
            "failed_sessions": failed,
            "success_rate": completed / total if total > 0 else 0,
        }
