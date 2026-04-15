# SPDX-License-Identifier: MIT
# Copyright (c) 2026 HKUDS/OpenHarness Integration for USMSB
# SwarmAdapter - OpenHarness Swarm Coordination Integration

"""
OpenHarness SwarmAdapter for USMSB.

This adapter wraps the OpenHarness Swarm system to provide:
- Multi-agent team management
- Agent registration and lifecycle
- Task assignment and tracking
- Swarm coordination (tmux/subprocess/worktree)
- Mailbox-based inter-agent communication

The adapter integrates USMSB's L4 (Team Intelligence) with OH's
swarm infrastructure.

Usage:
    >>> adapter = SwarmAdapter()
    >>> team = await adapter.create_team("team_001", leader_id="agent_leader")
    >>> await adapter.register_agent("agent_001", team_id="team_001", capabilities=["research"])
    >>> task = await adapter.assign_task("team_001", {"description": "Research AI trends"})
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator

try:
    from openharness.swarm.team_lifecycle import (
        TeamLifecycleManager,
        TeamMember as OHTeamMember,
        TeamFile as OHTeamFile,
        AllowedPath as OHAllowedPath,
        sanitize_name,
        sanitize_agent_name,
    )
    from openharness.swarm.registry import TeamRegistry
    from openharness.swarm.types import BackendType
    from openharness.swarm.mailbox import MailboxMessage
    OPENHARNESS_AVAILABLE = True
except ImportError:
    OPENHARNESS_AVAILABLE = False
    TeamLifecycleManager = None
    TeamRegistry = None
    BackendType = None

from usmsb_sdk.adapters.openharness.config import SwarmConfig, SwarmBackend
from usmsb_sdk.adapters.openharness.exceptions import (
    SwarmError,
    TeamCreationError,
    AgentRegistrationError,
    TaskAssignmentError,
    OpenHarnessNotAvailableError,
)

log = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Agent status in a team."""
    ACTIVE = "active"
    IDLE = "idle"
    STOPPED = "stopped"


class TaskStatus(str, Enum):
    """Task status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentInfo:
    """
    Information about a team agent.
    
    Attributes:
        agent_id: Unique agent identifier
        name: Agent display name
        team_id: Team this agent belongs to
        backend_type: Execution backend (tmux, subprocess, worktree)
        agent_type: Agent role/type (e.g., researcher, coder)
        model: LLM model used by this agent
        status: Current status
        is_active: Whether agent is active
        capabilities: List of agent capabilities
        joined_at: Timestamp when agent joined
        session_id: OH session ID for this agent
    """
    agent_id: str
    name: str
    team_id: str
    backend_type: str = "subprocess"
    agent_type: str | None = None
    model: str | None = None
    status: AgentStatus = AgentStatus.ACTIVE
    is_active: bool = True
    capabilities: list[str] = field(default_factory=list)
    joined_at: float = field(default_factory=time.time)
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "team_id": self.team_id,
            "backend_type": self.backend_type,
            "agent_type": self.agent_type,
            "model": self.model,
            "status": self.status.value,
            "is_active": self.is_active,
            "capabilities": self.capabilities,
            "joined_at": self.joined_at,
            "session_id": self.session_id,
            "metadata": self.metadata,
        }


@dataclass
class Task:
    """
    A task assigned to a team member.
    
    Attributes:
        task_id: Unique task identifier
        description: Task description
        assignee_id: Agent ID assigned to this task
        team_id: Team this task belongs to
        status: Current task status
        priority: Task priority (1-5, 5 is highest)
        created_at: Creation timestamp
        started_at: When task started execution
        completed_at: When task completed
        result: Task execution result
        error: Error message if failed
    """
    task_id: str
    description: str
    assignee_id: str | None
    team_id: str
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 3
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    result: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "assignee_id": self.assignee_id,
            "team_id": self.team_id,
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class TeamInfo:
    """
    Information about a swarm team.
    
    Attributes:
        team_id: Unique team identifier
        name: Team display name
        description: Team description
        leader_id: Agent ID of the team leader
        member_ids: List of member agent IDs
        created_at: Team creation timestamp
        backend_type: Coordination backend
        allowed_paths: Paths that all members can access
    """
    team_id: str
    name: str
    description: str = ""
    leader_id: str = ""
    member_ids: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    backend_type: SwarmBackend = SwarmBackend.SUBPROCESS
    allowed_paths: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "team_id": self.team_id,
            "name": self.name,
            "description": self.description,
            "leader_id": self.leader_id,
            "member_ids": self.member_ids,
            "created_at": self.created_at,
            "backend_type": self.backend_type.value,
            "allowed_paths": self.allowed_paths,
            "metadata": self.metadata,
        }


@dataclass
class MailboxMessage:
    """
    An inter-agent message.
    
    Attributes:
        message_id: Unique message identifier
        from_agent: Sender agent ID
        to_agent: Recipient agent ID
        content: Message content
        message_type: Type of message
        timestamp: Send timestamp
        read: Whether message has been read
    """
    message_id: str
    from_agent: str
    to_agent: str
    content: str
    message_type: str = "text"
    timestamp: float = field(default_factory=time.time)
    read: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class SwarmAdapter:
    """
    OpenHarness Swarm Coordination Adapter.
    
    This adapter wraps OH's TeamLifecycle and TeamRegistry to provide:
    - Team creation and management
    - Agent registration and lifecycle
    - Task assignment and tracking
    - Inter-agent communication (mailbox)
    - Allowed path management
    
    The adapter integrates USMSB's L4 (Team Intelligence) with OH's
    swarm infrastructure for multi-agent coordination.
    
    Example:
        >>> adapter = SwarmAdapter()
        >>> 
        >>> # Create a team
        >>> team = await adapter.create_team(
        ...     team_id="research_team",
        ...     name="Research Team",
        ...     leader_id="agent_leader"
        ... )
        >>> 
        >>> # Register agents
        >>> await adapter.register_agent(
        ...     agent_id="agent_researcher",
        ...     team_id="research_team",
        ...     capabilities=["web_search", "data_analysis"]
        ... )
        >>> 
        >>> # Assign task
        >>> task = await adapter.assign_task(
        ...     team_id="research_team",
        ...     description="Research AI trends",
        ...     assignee_id="agent_researcher"
        ... )
    """

    def __init__(
        self,
        config: SwarmConfig | None = None,
        teams_dir: str | Path | None = None,
    ):
        """
        Initialize SwarmAdapter.
        
        Args:
            config: Swarm configuration
            teams_dir: Directory for team data (overrides config)
        """
        if not OPENHARNESS_AVAILABLE:
            raise OpenHarnessNotAvailableError()
        
        self._config = config or SwarmConfig()
        self._teams_dir = Path(teams_dir or self._config.teams_dir).expanduser().resolve()
        
        # Create teams directory
        self._teams_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize OH TeamLifecycleManager
        self._lifecycle_manager = TeamLifecycleManager(
            teams_dir=str(self._teams_dir),
        )
        
        # In-memory cache of team/agent info
        self._teams: dict[str, TeamInfo] = {}
        self._agents: dict[str, AgentInfo] = {}
        self._tasks: dict[str, Task] = {}
        
        # Load existing teams
        self._load_existing_teams()
        
        log.info(
            "SwarmAdapter initialized at %s with %d teams",
            self._teams_dir,
            len(self._teams),
        )

    def _load_existing_teams(self) -> None:
        """Load existing teams from disk."""
        try:
            for team_file in self._teams_dir.glob("*/team.json"):
                try:
                    team_data = team_file.read_text(encoding="utf-8")
                    import json
                    data = json.loads(team_data)
                    
                    team_info = TeamInfo(
                        team_id=data.get("name", team_file.parent.name),
                        name=data.get("name", ""),
                        description=data.get("description", ""),
                        leader_id=data.get("lead_agent_id", ""),
                        created_at=data.get("created_at", time.time()),
                    )
                    self._teams[team_info.team_id] = team_info
                    
                except Exception as e:
                    log.warning("Failed to load team from %s: %s", team_file, e)
        except Exception as e:
            log.warning("Failed to load existing teams: %s", e)

    async def create_team(
        self,
        team_id: str,
        name: str | None = None,
        leader_id: str = "",
        description: str = "",
        member_ids: list[str] | None = None,
        backend_type: SwarmBackend | None = None,
        allowed_paths: list[str] | None = None,
    ) -> TeamInfo:
        """
        Create a new team.
        
        Args:
            team_id: Unique team identifier
            name: Display name for the team
            leader_id: Agent ID of the team leader
            description: Team description
            member_ids: Initial member agent IDs
            backend_type: Coordination backend
            allowed_paths: Paths all members can access
            
        Returns:
            TeamInfo for the created team
            
        Raises:
            TeamCreationError: If team creation fails
        """
        try:
            backend = backend_type or self._config.backend
            
            # Map to OH BackendType
            oh_backend_map = {
                SwarmBackend.TMUX: BackendType.TMUX,
                SwarmBackend.SUBPROCESS: BackendType.SUBPROCESS,
                SwarmBackend.WORKTREE: BackendType.WORKTREE,
            }
            oh_backend = oh_backend_map.get(backend, BackendType.SUBPROCESS)
            
            # Create team via OH lifecycle manager
            team = await self._lifecycle_manager.create_team(
                team_name=sanitize_name(team_id),
                lead_agent_id=leader_id,
                description=description,
                member_ids=[sanitize_agent_name(m) for m in (member_ids or [])],
                backend_type=oh_backend,
            )
            
            # Create team info
            team_info = TeamInfo(
                team_id=team_id,
                name=name or team_id,
                description=description,
                leader_id=leader_id,
                member_ids=member_ids or [],
                backend_type=backend or self._config.backend,
                allowed_paths=allowed_paths or [],
            )
            
            self._teams[team_id] = team_info
            
            log.info("Created team: %s (%s)", team_id, name)
            
            return team_info
            
        except Exception as e:
            raise TeamCreationError(
                team_name=team_id,
                message=str(e),
            )

    async def delete_team(self, team_id: str) -> bool:
        """
        Delete a team.
        
        Args:
            team_id: Team to delete
            
        Returns:
            True if deleted, False if not found
        """
        try:
            await self._lifecycle_manager.delete_team(sanitize_name(team_id))
            
            if team_id in self._teams:
                del self._teams[team_id]
            
            # Remove all agents in this team
            for agent_id in list(self._agents.keys()):
                if self._agents[agent_id].team_id == team_id:
                    del self._agents[agent_id]
            
            log.info("Deleted team: %s", team_id)
            return True
            
        except Exception as e:
            log.error("Failed to delete team %s: %s", team_id, e)
            return False

    def get_team(self, team_id: str) -> TeamInfo | None:
        """Get team info by ID."""
        return self._teams.get(team_id)

    def list_teams(self) -> list[TeamInfo]:
        """List all teams."""
        return list(self._teams.values())

    async def register_agent(
        self,
        agent_id: str,
        team_id: str,
        name: str | None = None,
        agent_type: str | None = None,
        capabilities: list[str] | None = None,
        model: str | None = None,
        prompt: str | None = None,
        color: str | None = None,
    ) -> AgentInfo:
        """
        Register an agent with a team.
        
        Args:
            agent_id: Unique agent identifier
            team_id: Team to register with
            name: Display name
            agent_type: Agent role/type
            capabilities: List of agent capabilities
            model: LLM model to use
            prompt: Initial system prompt
            color: Display color
            
        Returns:
            AgentInfo for the registered agent
            
        Raises:
            AgentRegistrationError: If registration fails
        """
        try:
            if team_id not in self._teams:
                raise AgentRegistrationError(
                    agent_id=agent_id,
                    message=f"Team '{team_id}' does not exist",
                )
            
            # Register with OH lifecycle manager
            await self._lifecycle_manager.add_member(
                team_name=sanitize_name(team_id),
                agent_id=sanitize_agent_name(agent_id),
                agent_type=agent_type,
                model=model,
                prompt=prompt,
                color=color,
            )
            
            # Create agent info
            agent_info = AgentInfo(
                agent_id=agent_id,
                name=name or agent_id,
                team_id=team_id,
                agent_type=agent_type,
                capabilities=capabilities or [],
                model=model,
            )
            
            self._agents[agent_id] = agent_info
            
            # Update team member list
            if agent_id not in self._teams[team_id].member_ids:
                self._teams[team_id].member_ids.append(agent_id)
            
            log.info("Registered agent %s in team %s", agent_id, team_id)
            
            return agent_info
            
        except AgentRegistrationError:
            raise
        except Exception as e:
            raise AgentRegistrationError(
                agent_id=agent_id,
                message=str(e),
                team_name=team_id,
            )

    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from its team.
        
        Args:
            agent_id: Agent to unregister
            
        Returns:
            True if unregistered, False if not found
        """
        try:
            agent = self._agents.get(agent_id)
            if not agent:
                return False
            
            await self._lifecycle_manager.remove_member(
                team_name=sanitize_name(agent.team_id),
                agent_id=sanitize_agent_name(agent_id),
            )
            
            # Remove from team
            if agent.team_id in self._teams:
                team = self._teams[agent.team_id]
                if agent_id in team.member_ids:
                    team.member_ids.remove(agent_id)
            
            del self._agents[agent_id]
            
            log.info("Unregistered agent: %s", agent_id)
            return True
            
        except Exception as e:
            log.error("Failed to unregister agent %s: %s", agent_id, e)
            return False

    def get_agent(self, agent_id: str) -> AgentInfo | None:
        """Get agent info by ID."""
        return self._agents.get(agent_id)

    def list_agents(self, team_id: str | None = None) -> list[AgentInfo]:
        """
        List agents, optionally filtered by team.
        
        Args:
            team_id: Optional team filter
            
        Returns:
            List of AgentInfo objects
        """
        if team_id:
            return [a for a in self._agents.values() if a.team_id == team_id]
        return list(self._agents.values())

    async def assign_task(
        self,
        team_id: str,
        description: str,
        assignee_id: str | None = None,
        priority: int = 3,
        metadata: dict[str, Any] | None = None,
    ) -> Task:
        """
        Assign a task to a team member.
        
        Args:
            team_id: Team to assign task to
            description: Task description
            assignee_id: Optional specific agent to assign to
            priority: Task priority (1-5)
            metadata: Additional task metadata
            
        Returns:
            Task object for the assigned task
            
        Raises:
            TaskAssignmentError: If assignment fails
        """
        try:
            if team_id not in self._teams:
                raise TaskAssignmentError(
                    task_id="",
                    message=f"Team '{team_id}' does not exist",
                    team_name=team_id,
                )
            
            task_id = f"task_{uuid.uuid4().hex[:8]}"
            
            # Auto-assign if assignee not specified
            if assignee_id is None:
                assignee_id = await self._auto_assign(team_id, priority)
            
            task = Task(
                task_id=task_id,
                description=description,
                assignee_id=assignee_id,
                team_id=team_id,
                priority=priority,
                metadata=metadata or {},
            )
            
            self._tasks[task_id] = task
            
            # If auto-assigned, notify the agent
            if assignee_id:
                await self.send_message(
                    from_agent="system",
                    to_agent=assignee_id,
                    content=f"New task assigned: {description}",
                    message_type="task_notification",
                )
            
            log.info("Assigned task %s to %s in team %s", task_id, assignee_id, team_id)
            
            return task
            
        except TaskAssignmentError:
            raise
        except Exception as e:
            raise TaskAssignmentError(
                task_id="",
                message=str(e),
                team_name=team_id,
                assignee_id=assignee_id,
            )

    async def _auto_assign(self, team_id: str, priority: int) -> str | None:
        """
        Auto-assign task to an available agent.
        
        Selection criteria:
        1. Agent with matching capabilities
        2. Currently has lowest task load
        3. Is active
        """
        team_agents = self.list_agents(team_id)
        active_agents = [a for a in team_agents if a.status == AgentStatus.ACTIVE]
        
        if not active_agents:
            return None
        
        # Count current tasks per agent
        task_counts = {}
        for task in self._tasks.values():
            if task.team_id == team_id and task.assignee_id:
                task_counts[task.assignee_id] = task_counts.get(task.assignee_id, 0) + 1
        
        # Select agent with lowest load
        def agent_load(agent: AgentInfo) -> tuple[int, int]:
            count = task_counts.get(agent.agent_id, 0)
            # Prefer higher priority-capable agents for high priority tasks
            cap_score = len(agent.capabilities) if priority >= 4 else 0
            return (count, -cap_score)
        
        selected = min(active_agents, key=agent_load)
        return selected.agent_id

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: Any = None,
        error: str | None = None,
    ) -> Task | None:
        """
        Update task status.
        
        Args:
            task_id: Task to update
            status: New status
            result: Task result (if completed)
            error: Error message (if failed)
            
        Returns:
            Updated Task or None if not found
        """
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        task.status = status
        
        if status == TaskStatus.IN_PROGRESS and task.started_at is None:
            task.started_at = time.time()
        elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            task.completed_at = time.time()
        
        if result is not None:
            task.result = result
        if error is not None:
            task.error = error
        
        log.info("Updated task %s status to %s", task_id, status)
        
        return task

    def get_task(self, task_id: str) -> Task | None:
        """Get task by ID."""
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        team_id: str | None = None,
        assignee_id: str | None = None,
        status: TaskStatus | None = None,
    ) -> list[Task]:
        """
        List tasks with optional filters.
        
        Args:
            team_id: Filter by team
            assignee_id: Filter by assignee
            status: Filter by status
            
        Returns:
            List of matching tasks
        """
        tasks = list(self._tasks.values())
        
        if team_id:
            tasks = [t for t in tasks if t.team_id == team_id]
        if assignee_id:
            tasks = [t for t in tasks if t.assignee_id == assignee_id]
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        # Sort by priority and creation time
        tasks.sort(key=lambda t: (-t.priority, t.created_at))
        
        return tasks

    async def send_message(
        self,
        from_agent: str,
        to_agent: str,
        content: str,
        message_type: str = "text",
        metadata: dict[str, Any] | None = None,
    ) -> MailboxMessage:
        """
        Send a message to an agent.
        
        Args:
            from_agent: Sender agent ID
            to_agent: Recipient agent ID
            content: Message content
            message_type: Type of message
            metadata: Additional metadata
            
        Returns:
            MailboxMessage that was sent
        """
        message = MailboxMessage(
            message_id=f"msg_{uuid.uuid4().hex[:8]}",
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            message_type=message_type,
            metadata=metadata or {},
        )
        
        # Store message in agent's mailbox
        agent = self._agents.get(to_agent)
        if agent:
            agent.metadata.setdefault("mailbox", []).append(message)
        
        log.debug("Sent message from %s to %s", from_agent, to_agent)
        
        return message

    def get_messages(
        self,
        agent_id: str,
        unread_only: bool = False,
    ) -> list[MailboxMessage]:
        """
        Get messages for an agent.
        
        Args:
            agent_id: Agent to get messages for
            unread_only: Only return unread messages
            
        Returns:
            List of messages
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return []
        
        messages = agent.metadata.get("mailbox", [])
        
        if unread_only:
            messages = [m for m in messages if not m.read]
        
        return messages

    def mark_message_read(self, agent_id: str, message_id: str) -> bool:
        """Mark a message as read."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        
        for msg in agent.metadata.get("mailbox", []):
            if msg.message_id == message_id:
                msg.read = True
                return True
        
        return False

    async def add_allowed_path(
        self,
        team_id: str,
        path: str,
        tool_name: str = "file_edit",
        added_by: str = "system",
    ) -> bool:
        """
        Add an allowed path for a team.
        
        Args:
            team_id: Team to add path for
            path: Path to allow
            tool_name: Tool this applies to
            added_by: Agent who added this
            
        Returns:
            True if added successfully
        """
        team = self._teams.get(team_id)
        if not team:
            return False
        
        try:
            await self._lifecycle_manager.add_allowed_path(
                team_name=sanitize_name(team_id),
                path=path,
                tool_name=tool_name,
                added_by=added_by,
            )
            
            team.allowed_paths.append(path)
            return True
            
        except Exception as e:
            log.error("Failed to add allowed path: %s", e)
            return False

    def get_statistics(self) -> dict[str, Any]:
        """Get swarm statistics."""
        return {
            "total_teams": len(self._teams),
            "total_agents": len(self._agents),
            "total_tasks": len(self._tasks),
            "tasks_by_status": {
                status.value: len([t for t in self._tasks.values() if t.status == status])
                for status in TaskStatus
            },
            "teams_dir": str(self._teams_dir),
        }
