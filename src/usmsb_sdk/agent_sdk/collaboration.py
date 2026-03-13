"""
Collaboration Module

Manages multi-agent collaboration sessions.
Supports coordinated task execution among multiple agents.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from usmsb_sdk.agent_sdk.platform_client import PlatformClient, APIResponse


logger = logging.getLogger(__name__)


class CollaborationMode(Enum):
    """Collaboration execution mode"""
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    HIERARCHICAL = "hierarchical"
    SWARM = "swarm"


class CollaborationStatus(Enum):
    """Collaboration session status"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    ORGANIZING = "organizing"
    EXECUTING = "executing"
    INTEGRATING = "integrating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RoleType(Enum):
    """Types of collaboration roles"""
    COORDINATOR = "coordinator"
    PRIMARY = "primary"
    SPECIALIST = "specialist"
    SUPPORT = "support"
    REVIEWER = "reviewer"


@dataclass
class CollaborationRole:
    """A role in a collaboration"""
    role_id: str
    role_type: str
    required_skills: List[str]
    responsibilities: List[str]
    status: str  # pending, filled, completed
    assigned_agent: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "role_type": self.role_type,
            "required_skills": self.required_skills,
            "responsibilities": self.responsibilities,
            "status": self.status,
            "assigned_agent": self.assigned_agent,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollaborationRole":
        return cls(
            role_id=data.get("role_id", ""),
            role_type=data.get("role_type", "support"),
            required_skills=data.get("required_skills", []),
            responsibilities=data.get("responsibilities", []),
            status=data.get("status", "pending"),
            assigned_agent=data.get("assigned_agent"),
        )


@dataclass
class CollaborationParticipant:
    """A participant in a collaboration"""
    agent_id: str
    agent_name: str
    role: str
    status: str
    contribution: Optional[Dict[str, Any]] = None
    joined_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollaborationParticipant":
        return cls(
            agent_id=data.get("agent_id", ""),
            agent_name=data.get("agent_name", "Unknown"),
            role=data.get("role", "support"),
            status=data.get("status", "pending"),
            contribution=data.get("contribution"),
            joined_at=datetime.fromisoformat(data["joined_at"]) if data.get("joined_at") else None,
        )


@dataclass
class CollaborationPlan:
    """Plan for collaboration execution"""
    plan_id: str
    mode: str
    phases: List[Dict[str, Any]]
    dependencies: Dict[str, List[str]]
    estimated_duration: int  # seconds

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollaborationPlan":
        return cls(
            plan_id=data.get("plan_id", ""),
            mode=data.get("mode", "parallel"),
            phases=data.get("phases", []),
            dependencies=data.get("dependencies", {}),
            estimated_duration=data.get("estimated_duration", 0),
        )


@dataclass
class Contribution:
    """Agent's contribution to a collaboration"""
    agent_id: str
    role: str
    output: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    submitted_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "output": self.output,
            "metadata": self.metadata,
            "submitted_at": self.submitted_at.isoformat(),
        }


@dataclass
class CollaborationResult:
    """Final result of a collaboration"""
    session_id: str
    success: bool
    outputs: Dict[str, Any]
    metrics: Dict[str, Any]
    completed_at: datetime

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollaborationResult":
        return cls(
            session_id=data.get("session_id", ""),
            success=data.get("success", False),
            outputs=data.get("outputs", {}),
            metrics=data.get("metrics", {}),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else datetime.now(),
        )


@dataclass
class CollaborationSession:
    """A collaboration session between multiple agents"""
    session_id: str
    goal: str
    collaboration_mode: str
    coordinator_id: str
    participants: List[CollaborationParticipant]
    roles: List[CollaborationRole]
    plan: Optional[CollaborationPlan]
    status: str
    result: Optional[CollaborationResult]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    @property
    def is_active(self) -> bool:
        return self.status in ["analyzing", "organizing", "executing", "integrating"]

    @property
    def is_completed(self) -> bool:
        return self.status in ["completed", "failed", "cancelled"]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollaborationSession":
        # Parse goal
        goal = data.get("goal", "")
        if isinstance(goal, str):
            try:
                goal_data = json.loads(goal)
                goal = goal_data.get("description", goal_data.get("name", goal))
            except (json.JSONDecodeError, TypeError):
                pass

        # Parse participants
        participants = []
        p_data = data.get("participants", [])
        if isinstance(p_data, str):
            try:
                p_data = json.loads(p_data)
            except (json.JSONDecodeError, TypeError):
                p_data = []
        for p in p_data:
            participants.append(CollaborationParticipant.from_dict(p))

        # Parse roles
        roles = []
        plan_data = data.get("plan", {})
        if isinstance(plan_data, str):
            try:
                plan_data = json.loads(plan_data)
            except (json.JSONDecodeError, TypeError):
                plan_data = {}
        for r in plan_data.get("roles", []):
            roles.append(CollaborationRole.from_dict(r))

        # Parse plan
        plan = None
        if plan_data:
            plan = CollaborationPlan.from_dict(plan_data)

        # Parse result
        result = None
        if data.get("result"):
            result = CollaborationResult.from_dict(data["result"])

        return cls(
            session_id=data.get("session_id", ""),
            goal=goal,
            collaboration_mode=plan_data.get("mode", "parallel") if plan_data else "parallel",
            coordinator_id=data.get("coordinator_id", ""),
            participants=participants,
            roles=roles,
            plan=plan,
            status=data.get("status", "pending"),
            result=result,
            created_at=datetime.fromtimestamp(data["created_at"]) if isinstance(data.get("created_at"), (int, float)) else None,
            updated_at=datetime.fromtimestamp(data["updated_at"]) if isinstance(data.get("updated_at"), (int, float)) else None,
        )


class CollaborationManager:
    """
    Manages multi-agent collaboration.

    Features:
    - Create and join collaboration sessions
    - Role assignment and management
    - Contribution submission
    - Result integration
    """

    def __init__(
        self,
        platform_client: PlatformClient,
        agent_id: str,
        logger: Optional[logging.Logger] = None,
    ):
        self._platform = platform_client
        self.agent_id = agent_id
        self.logger = logger or logging.getLogger(__name__)

        # Session cache
        self._sessions: Dict[str, CollaborationSession] = {}

    # ==================== Session Creation ====================

    async def create(
        self,
        goal: str,
        required_skills: List[str],
        mode: str = "parallel",
        coordinator_agent_id: Optional[str] = None,
    ) -> Optional[CollaborationSession]:
        """
        Create a new collaboration session.

        Args:
            goal: Goal description
            required_skills: Skills needed for the collaboration
            mode: Collaboration mode (parallel, sequential, hierarchical)
            coordinator_agent_id: Coordinator agent (defaults to self)

        Returns:
            CollaborationSession or None on failure
        """
        response = await self._platform.create_collaboration(
            goal_description=goal,
            required_skills=required_skills,
            collaboration_mode=mode,
            coordinator_agent_id=coordinator_agent_id or self.agent_id,
        )

        if response.success and response.data:
            session = CollaborationSession.from_dict(response.data)
            self._sessions[session.session_id] = session
            self.logger.info(f"Collaboration created: {session.session_id}")
            return session

        self.logger.error(f"Failed to create collaboration: {response.error}")
        return None

    async def join(
        self,
        session_id: str,
        role: str = "support",
    ) -> bool:
        """
        Join an existing collaboration.

        Args:
            session_id: Session to join
            role: Role to take

        Returns:
            True if joined successfully
        """
        # TODO: Implement when platform API supports joining
        self.logger.warning("Direct join not yet supported - waiting for invitation")
        return False

    async def leave(self, session_id: str) -> bool:
        """Leave a collaboration"""
        # TODO: Implement when platform API supports leaving
        return False

    # ==================== Session Queries ====================

    async def get(self, session_id: str) -> Optional[CollaborationSession]:
        """Get a collaboration session by ID"""
        if session_id in self._sessions:
            return self._sessions[session_id]

        response = await self._platform.get_collaboration(session_id)

        if response.success and response.data:
            session = CollaborationSession.from_dict(response.data)
            self._sessions[session_id] = session
            return session

        return None

    async def list_all(self, status: Optional[str] = None) -> List[CollaborationSession]:
        """List all collaborations"""
        response = await self._platform.get_collaborations(status=status)

        if response.success and response.data:
            sessions = [CollaborationSession.from_dict(s) for s in response.data]
            for s in sessions:
                self._sessions[s.session_id] = s
            return sessions

        return []

    async def list_active(self) -> List[CollaborationSession]:
        """List active collaborations"""
        sessions = await self.list_all()
        return [s for s in sessions if s.is_active]

    async def get_stats(self) -> Dict[str, Any]:
        """Get collaboration statistics"""
        response = await self._platform.get_collaboration_stats()

        if response.success and response.data:
            return response.data
        return {}

    # ==================== Execution ====================

    async def execute(self, session_id: str) -> Optional[CollaborationSession]:
        """
        Execute a collaboration session.

        Args:
            session_id: Session to execute

        Returns:
            Updated session
        """
        response = await self._platform.execute_collaboration(session_id)

        if response.success and response.data:
            session = CollaborationSession.from_dict(response.data)
            self._sessions[session_id] = session
            self.logger.info(f"Collaboration executing: {session_id}")
            return session

        self.logger.error(f"Failed to execute collaboration: {response.error}")
        return None

    # ==================== Contributions ====================

    async def submit_contribution(
        self,
        session_id: str,
        contribution: Contribution,
    ) -> bool:
        """
        Submit contribution to a collaboration.

        Args:
            session_id: Target session
            contribution: Contribution to submit

        Returns:
            True if successful
        """
        # TODO: Implement when platform API supports contribution submission
        self.logger.info(f"Contribution submitted to {session_id}: {contribution.role}")
        return True

    async def request_help(
        self,
        session_id: str,
        task: str,
        required_skills: List[str],
    ) -> bool:
        """
        Request help from other participants.

        Args:
            session_id: Target session
            task: Task needing help
            required_skills: Skills needed

        Returns:
            True if request sent
        """
        # TODO: Implement help request mechanism
        self.logger.info(f"Help requested in {session_id} for: {task}")
        return True

    async def sync_progress(
        self,
        session_id: str,
        progress: Dict[str, Any],
    ) -> bool:
        """
        Sync progress with other participants.

        Args:
            session_id: Target session
            progress: Progress update

        Returns:
            True if synced
        """
        # TODO: Implement progress sync
        return True

    # ==================== Results ====================

    async def integrate_results(
        self,
        session_id: str,
    ) -> Optional[CollaborationResult]:
        """
        Integrate results from all participants.

        Args:
            session_id: Target session

        Returns:
            Integrated result
        """
        session = await self.get(session_id)
        if session and session.result:
            return session.result
        return None

    async def vote_on_result(
        self,
        session_id: str,
        result_id: str,
        approve: bool,
        comment: str = "",
    ) -> bool:
        """
        Vote on a proposed result.

        Args:
            session_id: Target session
            result_id: Result to vote on
            approve: True to approve
            comment: Optional comment

        Returns:
            True if vote recorded
        """
        # TODO: Implement voting mechanism
        return True

    # ==================== Role Management ====================

    async def assign_role(
        self,
        session_id: str,
        agent_id: str,
        role: str,
    ) -> bool:
        """
        Assign a role to an agent.

        Args:
            session_id: Target session
            agent_id: Agent to assign
            role: Role to assign

        Returns:
            True if assigned
        """
        # TODO: Implement role assignment
        return True

    async def request_role_change(
        self,
        session_id: str,
        new_role: str,
    ) -> bool:
        """
        Request to change own role.

        Args:
            session_id: Target session
            new_role: Desired role

        Returns:
            True if request sent
        """
        # TODO: Implement role change request
        return True

    # ==================== Convenience Methods ====================

    async def start_collaboration(
        self,
        goal: str,
        required_skills: List[str],
        mode: str = "parallel",
    ) -> Optional[CollaborationSession]:
        """
        Convenience method to create and start a collaboration.
        """
        session = await self.create(
            goal=goal,
            required_skills=required_skills,
            mode=mode,
        )

        if session:
            return await self.execute(session.session_id)

        return None

    async def contribute(
        self,
        session_id: str,
        output: Any,
        role: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """
        Convenience method to submit a contribution.
        """
        contribution = Contribution(
            agent_id=self.agent_id,
            role=role or "support",
            output=output,
            metadata=metadata or {},
        )

        return await self.submit_contribution(session_id, contribution)
