"""
Human Agent Adapter

Adapter for integrating human agents into the USMSB platform.
Supports human-in-the-loop workflows, task assignment, and collaboration.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from usmsb_sdk.core.elements import Agent, AgentType, Goal, Resource

logger = logging.getLogger(__name__)


class HumanAgentStatus(str, Enum):
    """Status of a human agent."""
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    AWAY = "away"


class TaskStatus(str, Enum):
    """Status of an assigned task."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


@dataclass
class Skill:
    """A skill possessed by a human agent."""
    name: str
    level: int = 1  # 1-5 scale
    certifications: List[str] = field(default_factory=list)
    experience_years: float = 0.0
    last_used: Optional[float] = None


@dataclass
class HumanAgentProfile:
    """Profile for a human agent."""
    agent_id: str
    user_id: str
    name: str
    email: Optional[str] = None
    status: HumanAgentStatus = HumanAgentStatus.OFFLINE
    skills: List[Skill] = field(default_factory=list)
    specializations: List[str] = field(default_factory=list)
    rating: float = 5.0
    completed_tasks: int = 0
    availability_hours: Dict[str, str] = field(default_factory=dict)  # day -> hours
    hourly_rate: float = 0.0
    timezone: str = "UTC"
    languages: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: time.time())
    last_active: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def has_skill(self, skill_name: str, min_level: int = 1) -> bool:
        """Check if agent has a skill at minimum level."""
        for skill in self.skills:
            if skill.name.lower() == skill_name.lower():
                return skill.level >= min_level
        return False

    def get_skill_level(self, skill_name: str) -> int:
        """Get skill level for a skill."""
        for skill in self.skills:
            if skill.name.lower() == skill_name.lower():
                return skill.level
        return 0


@dataclass
class AssignedTask:
    """A task assigned to a human agent."""
    id: str
    title: str
    description: str
    assigned_to: str  # agent_id
    assigned_by: str  # agent_id or system
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0
    required_skills: List[str] = field(default_factory=list)
    deadline: Optional[float] = None
    estimated_duration_minutes: int = 60
    actual_duration_minutes: Optional[int] = None
    reward: float = 0.0
    created_at: float = field(default_factory=lambda: time.time())
    accepted_at: Optional[float] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Any] = None
    feedback: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class HumanAgentAdapter:
    """
    Human Agent Adapter.

    Provides integration between human agents and the USMSB platform:
    - Profile management
    - Task assignment
    - Status tracking
    - Communication
    - Feedback collection
    """

    def __init__(self):
        """Initialize the Human Agent Adapter."""
        self._profiles: Dict[str, HumanAgentProfile] = {}
        self._tasks: Dict[str, AssignedTask] = {}
        self._pending_tasks: Dict[str, List[str]] = {}  # agent_id -> task_ids
        self._callbacks: Dict[str, Callable] = {}

    def register_human_agent(
        self,
        user_id: str,
        name: str,
        email: Optional[str] = None,
        skills: Optional[List[Skill]] = None,
        specializations: Optional[List[str]] = None,
        hourly_rate: float = 0.0,
        timezone: str = "UTC",
        languages: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HumanAgentProfile:
        """
        Register a new human agent.

        Args:
            user_id: External user ID
            name: Agent name
            email: Email address
            skills: List of skills
            specializations: List of specializations
            hourly_rate: Hourly rate
            timezone: Timezone
            languages: List of languages
            metadata: Additional metadata

        Returns:
            Created profile
        """
        import uuid

        agent_id = f"human_{uuid.uuid4().hex[:8]}"

        profile = HumanAgentProfile(
            agent_id=agent_id,
            user_id=user_id,
            name=name,
            email=email,
            skills=skills or [],
            specializations=specializations or [],
            hourly_rate=hourly_rate,
            timezone=timezone,
            languages=languages or [],
            metadata=metadata or {},
        )

        self._profiles[agent_id] = profile
        self._pending_tasks[agent_id] = []

        logger.info(f"Human agent registered: {name} (ID: {agent_id})")
        return profile

    def get_profile(self, agent_id: str) -> Optional[HumanAgentProfile]:
        """Get human agent profile."""
        return self._profiles.get(agent_id)

    def get_profile_by_user(self, user_id: str) -> Optional[HumanAgentProfile]:
        """Get profile by external user ID."""
        for profile in self._profiles.values():
            if profile.user_id == user_id:
                return profile
        return None

    def update_status(
        self,
        agent_id: str,
        status: HumanAgentStatus,
    ) -> bool:
        """
        Update human agent status.

        Args:
            agent_id: Agent ID
            status: New status

        Returns:
            True if successful
        """
        profile = self._profiles.get(agent_id)
        if not profile:
            return False

        profile.status = status
        profile.last_active = time.time()

        logger.info(f"Human agent {agent_id} status updated to {status.value}")
        return True

    def add_skill(
        self,
        agent_id: str,
        skill: Skill,
    ) -> bool:
        """Add a skill to a human agent."""
        profile = self._profiles.get(agent_id)
        if not profile:
            return False

        # Check if skill exists
        for i, s in enumerate(profile.skills):
            if s.name.lower() == skill.name.lower():
                profile.skills[i] = skill
                return True

        profile.skills.append(skill)
        return True

    def assign_task(
        self,
        agent_id: str,
        title: str,
        description: str,
        assigned_by: str,
        required_skills: Optional[List[str]] = None,
        priority: int = 0,
        deadline: Optional[float] = None,
        estimated_duration_minutes: int = 60,
        reward: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AssignedTask:
        """
        Assign a task to a human agent.

        Args:
            agent_id: Target agent ID
            title: Task title
            description: Task description
            assigned_by: Assigner ID
            required_skills: Required skills
            priority: Task priority
            deadline: Deadline timestamp
            estimated_duration_minutes: Estimated duration
            reward: Reward amount
            metadata: Additional metadata

        Returns:
            Assigned task
        """
        import uuid

        if agent_id not in self._profiles:
            raise ValueError(f"Agent {agent_id} not found")

        task = AssignedTask(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            assigned_to=agent_id,
            assigned_by=assigned_by,
            required_skills=required_skills or [],
            priority=priority,
            deadline=deadline,
            estimated_duration_minutes=estimated_duration_minutes,
            reward=reward,
            metadata=metadata or {},
        )

        self._tasks[task.id] = task
        self._pending_tasks[agent_id].append(task.id)

        # Notify callback if registered
        if agent_id in self._callbacks:
            asyncio.create_task(self._callbacks[agent_id]("task_assigned", task))

        logger.info(f"Task {task.id} assigned to human agent {agent_id}")
        return task

    def accept_task(self, task_id: str) -> bool:
        """Accept a pending task."""
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.PENDING:
            return False

        task.status = TaskStatus.ACCEPTED
        task.accepted_at = time.time()

        logger.info(f"Task {task_id} accepted")
        return True

    def reject_task(self, task_id: str, reason: Optional[str] = None) -> bool:
        """Reject a pending task."""
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.PENDING:
            return False

        task.status = TaskStatus.REJECTED
        task.feedback = reason

        # Remove from pending
        if task.assigned_to in self._pending_tasks:
            if task_id in self._pending_tasks[task.assigned_to]:
                self._pending_tasks[task.assigned_to].remove(task_id)

        logger.info(f"Task {task_id} rejected")
        return True

    def start_task(self, task_id: str) -> bool:
        """Start working on an accepted task."""
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.ACCEPTED:
            return False

        task.status = TaskStatus.IN_PROGRESS
        task.started_at = time.time()

        # Update agent status
        profile = self._profiles.get(task.assigned_to)
        if profile:
            profile.status = HumanAgentStatus.BUSY

        logger.info(f"Task {task_id} started")
        return True

    def complete_task(
        self,
        task_id: str,
        result: Any,
        feedback: Optional[str] = None,
    ) -> bool:
        """Complete a task with result."""
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.IN_PROGRESS:
            return False

        task.status = TaskStatus.COMPLETED
        task.result = result
        task.feedback = feedback
        task.completed_at = time.time()

        if task.started_at:
            task.actual_duration_minutes = int((task.completed_at - task.started_at) / 60)

        # Update profile
        profile = self._profiles.get(task.assigned_to)
        if profile:
            profile.completed_tasks += 1
            profile.status = HumanAgentStatus.AVAILABLE

        # Remove from pending
        if task.assigned_to in self._pending_tasks:
            if task_id in self._pending_tasks[task.assigned_to]:
                self._pending_tasks[task.assigned_to].remove(task_id)

        logger.info(f"Task {task_id} completed")
        return True

    def get_task(self, task_id: str) -> Optional[AssignedTask]:
        """Get task by ID."""
        return self._tasks.get(task_id)

    def get_pending_tasks(self, agent_id: str) -> List[AssignedTask]:
        """Get pending tasks for an agent."""
        task_ids = self._pending_tasks.get(agent_id, [])
        return [self._tasks[tid] for tid in task_ids if tid in self._tasks]

    def get_tasks_by_status(
        self,
        agent_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
    ) -> List[AssignedTask]:
        """Get tasks filtered by status."""
        tasks = list(self._tasks.values())

        if agent_id:
            tasks = [t for t in tasks if t.assigned_to == agent_id]

        if status:
            tasks = [t for t in tasks if t.status == status]

        return tasks

    def rate_task(
        self,
        task_id: str,
        rating: float,
        feedback: Optional[str] = None,
    ) -> bool:
        """
        Rate a completed task.

        Args:
            task_id: Task ID
            rating: Rating (1-5)
            feedback: Optional feedback

        Returns:
            True if successful
        """
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.COMPLETED:
            return False

        # Update agent rating
        profile = self._profiles.get(task.assigned_to)
        if profile:
            # Weighted average
            old_count = profile.completed_tasks
            profile.rating = (profile.rating * old_count + rating) / (old_count + 1)

        task.metadata["rating"] = rating
        if feedback:
            task.metadata["rating_feedback"] = feedback

        return True

    def register_callback(
        self,
        agent_id: str,
        callback: Callable[[str, Any], None],
    ) -> None:
        """Register a callback for agent notifications."""
        self._callbacks[agent_id] = callback

    def unregister_callback(self, agent_id: str) -> None:
        """Unregister callback."""
        if agent_id in self._callbacks:
            del self._callbacks[agent_id]

    def search_agents(
        self,
        skills: Optional[List[str]] = None,
        status: Optional[HumanAgentStatus] = None,
        min_rating: Optional[float] = None,
        specialization: Optional[str] = None,
    ) -> List[HumanAgentProfile]:
        """
        Search for human agents.

        Args:
            skills: Required skills
            status: Status filter
            min_rating: Minimum rating
            specialization: Specialization filter

        Returns:
            Matching agents
        """
        results = list(self._profiles.values())

        if skills:
            for skill in skills:
                results = [r for r in results if r.has_skill(skill)]

        if status:
            results = [r for r in results if r.status == status]

        if min_rating:
            results = [r for r in results if r.rating >= min_rating]

        if specialization:
            results = [r for r in results if specialization in r.specializations]

        return results

    def get_adapter_stats(self) -> Dict[str, Any]:
        """Get adapter statistics."""
        total_agents = len(self._profiles)
        available_agents = sum(
            1 for p in self._profiles.values()
            if p.status == HumanAgentStatus.AVAILABLE
        )
        total_tasks = len(self._tasks)
        completed_tasks = sum(
            1 for t in self._tasks.values()
            if t.status == TaskStatus.COMPLETED
        )

        return {
            "total_human_agents": total_agents,
            "available_agents": available_agents,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "average_rating": sum(p.rating for p in self._profiles.values()) / max(total_agents, 1),
        }
