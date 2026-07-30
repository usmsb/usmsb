# SPDX-License-Identifier: MIT
# Copyright (c) 2026 HKUDS/OpenHarness Integration for USMSB
# MetaAgentAdapter - OpenHarness Agent Spawning Integration

"""
OpenHarness MetaAgentAdapter for USMSB.

This adapter wraps OpenHarness agent spawning capabilities to provide:
- Dynamic agent creation
- Agent lifecycle management
- Multi-agent orchestration
- Agent communication
- Resource allocation

The adapter integrates USMSB's L5 (Collective Intelligence) with OH's
agent spawning system for emergent multi-agent behavior.

Usage:
    >>> adapter = MetaAgentAdapter()
    >>> agent = await adapter.spawn_agent("researcher", model="minimax-m1")
    >>> result = await adapter.delegate_task(agent.id, "Research AI trends")
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
        sanitize_name,
        sanitize_agent_name,
    )
    OPENHARNESS_AVAILABLE = True
except ImportError:
    OPENHARNESS_AVAILABLE = False
    TeamLifecycleManager = None

from usmsb_sdk.adapters.openharness.config import SwarmConfig, SwarmBackend
from usmsb_sdk.adapters.openharness.exceptions import (
    AgentSpawnError,
    OpenHarnessNotAvailableError,
)

log = logging.getLogger(__name__)


class AgentState(str, Enum):
    """Agent lifecycle state."""
    SPAWNING = "spawning"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    IDLE = "idle"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class AgentSpec:
    """
    Specification for spawning an agent.
    
    Attributes:
        agent_type: Type/category of agent (e.g., researcher, coder)
        name: Display name for the agent
        model: LLM model to use
        prompt: System prompt
        capabilities: List of agent capabilities
        backend: Execution backend (tmux, subprocess, worktree)
        config: Agent-specific configuration
    """
    agent_type: str
    name: str | None = None
    model: str | None = None
    prompt: str | None = None
    capabilities: list[str] = field(default_factory=list)
    backend: SwarmBackend = SwarmBackend.SUBPROCESS
    color: str | None = None
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class SpawnedAgent:
    """
    A spawned agent instance.
    
    Attributes:
        agent_id: Unique agent identifier
        name: Display name
        spec: Original specification
        state: Current state
        team_id: Team this agent belongs to
        session_id: OH session ID
        created_at: Creation timestamp
        started_at: When agent started running
        backend_info: Backend-specific info (tmux pane, etc.)
    """
    agent_id: str
    name: str
    spec: AgentSpec
    state: AgentState = AgentState.SPAWNING
    team_id: str | None = None
    session_id: str | None = None
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    stopped_at: float | None = None
    backend_info: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "agent_type": self.spec.agent_type,
            "state": self.state.value,
            "team_id": self.team_id,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "error": self.error,
            "backend_info": self.backend_info,
        }


@dataclass
class TaskResult:
    """
    Result of a delegated task.
    
    Attributes:
        task_id: Task identifier
        agent_id: Agent that executed
        success: Whether task succeeded
        output: Task output
        error: Error message if failed
        duration_seconds: Task duration
    """
    task_id: str
    agent_id: str
    success: bool
    output: str = ""
    error: str | None = None
    duration_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DelegatedTask:
    """
    A task delegated to an agent.
    
    Attributes:
        task_id: Task identifier
        description: Task description
        agent_id: Assigned agent
        priority: Priority (1-5)
        status: Current status
        created_at: Creation time
        started_at: Execution start time
        completed_at: Completion time
    """
    task_id: str
    description: str
    agent_id: str
    priority: int = 3
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None


class MetaAgentAdapter:
    """
    OpenHarness MetaAgent Adapter.
    
    This adapter wraps OH's agent spawning to provide:
    - Dynamic agent creation based on specs
    - Agent lifecycle management
    - Task delegation and tracking
    - Resource monitoring
    - Collective decision support
    
    The adapter implements USMSB's L5 capabilities for
    emergent multi-agent behavior.
    
    Example:
        >>> adapter = MetaAgentAdapter()
        >>> 
        >>> # Spawn a researcher agent
        >>> researcher = await adapter.spawn_agent(
        ...     AgentSpec(
        ...         agent_type="researcher",
        ...         name="Research Agent 1",
        ...         capabilities=["web_search", "data_analysis"]
        ...     )
        ... )
        >>> 
        >>> # Delegate a task
        >>> task = await adapter.delegate_task(
        ...     agent_id=researcher.agent_id,
        ...     description="Research latest AI trends",
        ...     priority=5
        ... )
        >>> 
        >>> # Get result
        >>> result = await adapter.get_task_result(task.task_id)
        >>> print(result.output)
    """

    def __init__(
        self,
        config: SwarmConfig | None = None,
        teams_dir: str | Path | None = None,
    ):
        """
        Initialize MetaAgentAdapter.
        
        Args:
            config: Swarm configuration
            teams_dir: Directory for team data
        """
        if not OPENHARNESS_AVAILABLE:
            raise OpenHarnessNotAvailableError()
        
        self._config = config or SwarmConfig()
        self._teams_dir = Path(teams_dir or self._config.teams_dir).expanduser().resolve()
        
        # Create OH lifecycle manager
        self._lifecycle_manager = TeamLifecycleManager()
        
        # Agent registry
        self._agents: dict[str, SpawnedAgent] = {}
        self._tasks: dict[str, DelegatedTask] = {}
        self._task_results: dict[str, TaskResult] = {}
        
        # Event queues for async communication
        self._agent_events: dict[str, asyncio.Queue] = {}
        
        log.info("MetaAgentAdapter initialized")

    @property
    def agent_count(self) -> int:
        """Return number of active agents."""
        return len([a for a in self._agents.values() 
                    if a.state not in (AgentState.STOPPED, AgentState.FAILED)])

    async def spawn_agent(
        self,
        spec: AgentSpec,
        team_id: str | None = None,
    ) -> SpawnedAgent:
        """
        Spawn a new agent based on specification.
        
        Args:
            spec: Agent specification
            team_id: Optional team to join
            
        Returns:
            SpawnedAgent instance
            
        Raises:
            AgentSpawnError: If spawning fails
        """
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"
        
        try:
            # Create agent info
            agent = SpawnedAgent(
                agent_id=agent_id,
                name=spec.name or f"{spec.agent_type}_{agent_id[-8:]}",
                spec=spec,
                state=AgentState.SPAWNING,
                team_id=team_id,
            )
            
            # Map backend
            oh_backend = "tmux" if spec.backend == SwarmBackend.TMUX else "subprocess"
            
            # Create event queue
            self._agent_events[agent_id] = asyncio.Queue()
            
            # Spawn via OH lifecycle manager
            normalized_team = sanitize_name(team_id or "default")
            if self._lifecycle_manager.get_team(normalized_team) is None:
                self._lifecycle_manager.create_team(normalized_team, description="USMSB dynamic team")
            member = OHTeamMember(
                agent_id=sanitize_agent_name(agent_id),
                name=agent.name,
                backend_type=oh_backend,
                joined_at=time.time(),
                agent_type=spec.agent_type,
                model=spec.model,
                prompt=spec.prompt,
                color=spec.color,
            )
            self._lifecycle_manager.add_member(normalized_team, member)
            
            # Update state
            agent.state = AgentState.INITIALIZING
            agent.session_id = f"session_{agent_id}"
            self._agents[agent_id] = agent
            
            log.info("Spawned agent: %s (%s)", agent_id, spec.agent_type)
            
            # Start initialization task
            asyncio.create_task(self._initialize_agent(agent))
            
            return agent
            
        except Exception as e:
            log.error("Failed to spawn agent %s: %s", agent_id, e)
            raise AgentSpawnError(
                agent_type=spec.agent_type,
                message=str(e),
            )

    async def _initialize_agent(self, agent: SpawnedAgent) -> None:
        """Initialize agent (run after spawn)."""
        try:
            await asyncio.sleep(0.1)  # Brief initialization
            agent.state = AgentState.READY
            agent.started_at = time.time()
            
            # Signal ready
            await self._agent_events[agent.agent_id].put({
                "type": "state_change",
                "state": AgentState.READY,
            })
            
            log.info("Agent initialized: %s", agent.agent_id)
            
        except Exception as e:
            agent.state = AgentState.FAILED
            agent.error = str(e)
            log.error("Agent initialization failed: %s", e)

    async def stop_agent(self, agent_id: str) -> bool:
        """
        Stop a running agent.
        
        Args:
            agent_id: Agent to stop
            
        Returns:
            True if stopped successfully
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        
        try:
            agent.state = AgentState.STOPPING
            
            # Remove from team if in one
            if agent.team_id:
                self._lifecycle_manager.remove_member(
                    sanitize_name(agent.team_id),
                    sanitize_agent_name(agent_id),
                )
            
            agent.state = AgentState.STOPPED
            agent.stopped_at = time.time()
            
            # Close event queue
            if agent_id in self._agent_events:
                await self._agent_events[agent_id].put(None)  # Signal close
                del self._agent_events[agent_id]
            
            log.info("Agent stopped: %s", agent_id)
            return True
            
        except Exception as e:
            agent.state = AgentState.FAILED
            agent.error = str(e)
            log.error("Failed to stop agent %s: %s", agent_id, e)
            return False

    def get_agent(self, agent_id: str) -> SpawnedAgent | None:
        """Get agent by ID."""
        return self._agents.get(agent_id)

    def list_agents(
        self,
        team_id: str | None = None,
        state: AgentState | None = None,
    ) -> list[SpawnedAgent]:
        """
        List agents with optional filters.
        
        Args:
            team_id: Filter by team
            state: Filter by state
            
        Returns:
            List of SpawnedAgent objects
        """
        agents = list(self._agents.values())
        
        if team_id:
            agents = [a for a in agents if a.team_id == team_id]
        if state:
            agents = [a for a in agents if a.state == state]
        
        return sorted(agents, key=lambda a: a.created_at)

    async def delegate_task(
        self,
        agent_id: str,
        description: str,
        priority: int = 3,
        timeout_seconds: float | None = None,
    ) -> DelegatedTask | None:
        """
        Delegate a task to an agent.
        
        Args:
            agent_id: Agent to delegate to
            description: Task description
            priority: Task priority (1-5)
            timeout_seconds: Optional timeout
            
        Returns:
            DelegatedTask or None if agent not found
        """
        agent = self._agents.get(agent_id)
        if not agent:
            log.warning("Cannot delegate to unknown agent: %s", agent_id)
            return None
        
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        task = DelegatedTask(
            task_id=task_id,
            description=description,
            agent_id=agent_id,
            priority=priority,
        )
        
        self._tasks[task_id] = task
        
        # Send task to agent
        if agent_id in self._agent_events:
            await self._agent_events[agent_id].put({
                "type": "task",
                "task_id": task_id,
                "description": description,
                "priority": priority,
            })
        
        log.info("Delegated task %s to agent %s", task_id, agent_id)
        
        return task

    async def get_agent_events(
        self,
        agent_id: str,
        timeout_seconds: float = 30.0,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Get events from an agent's event queue.
        
        Args:
            agent_id: Agent to get events from
            timeout_seconds: Queue timeout
            
        Yields:
            Event dictionaries
        """
        if agent_id not in self._agent_events:
            return
        
        queue = self._agent_events[agent_id]
        
        while True:
            try:
                event = await asyncio.wait_for(
                    queue.get(),
                    timeout=timeout_seconds,
                )
                
                if event is None:  # Signal to stop
                    break
                
                yield event
                
            except asyncio.TimeoutError:
                break

    async def wait_for_state(
        self,
        agent_id: str,
        target_state: AgentState,
        timeout_seconds: float = 30.0,
    ) -> bool:
        """
        Wait for an agent to reach a target state.
        
        Args:
            agent_id: Agent to monitor
            target_state: State to wait for
            timeout_seconds: Max wait time
            
        Returns:
            True if target state reached, False if timeout
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        
        if agent.state == target_state:
            return True
        
        async for event in self.get_agent_events(agent_id, timeout_seconds):
            if event.get("type") == "state_change":
                if event.get("state") == target_state:
                    return True
        
        return False

    def complete_task(
        self,
        task_id: str,
        success: bool,
        output: str = "",
        error: str | None = None,
    ) -> TaskResult | None:
        """
        Mark a task as complete.
        
        This is typically called by the agent to report completion.
        
        Args:
            task_id: Task to complete
            success: Whether task succeeded
            output: Task output
            error: Error message if failed
            
        Returns:
            TaskResult or None if task not found
        """
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        task.status = "completed" if success else "failed"
        
        result = TaskResult(
            task_id=task_id,
            agent_id=task.agent_id,
            success=success,
            output=output,
            error=error,
        )
        
        self._task_results[task_id] = result
        
        return result

    def get_task(self, task_id: str) -> DelegatedTask | None:
        """Get task by ID."""
        return self._tasks.get(task_id)

    def get_task_result(self, task_id: str) -> TaskResult | None:
        """Get task result by ID."""
        return self._task_results.get(task_id)

    def list_tasks(
        self,
        agent_id: str | None = None,
        status: str | None = None,
    ) -> list[DelegatedTask]:
        """
        List tasks with optional filters.
        
        Args:
            agent_id: Filter by agent
            status: Filter by status
            
        Returns:
            List of DelegatedTask objects
        """
        tasks = list(self._tasks.values())
        
        if agent_id:
            tasks = [t for t in tasks if t.agent_id == agent_id]
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        return sorted(tasks, key=lambda t: (-t.priority, t.created_at))

    async def create_team(
        self,
        team_id: str,
        name: str | None = None,
        description: str = "",
    ) -> str:
        """
        Create a team for agents.
        
        Args:
            team_id: Unique team identifier
            name: Display name
            description: Team description
            
        Returns:
            Team ID
        """
        try:
            self._lifecycle_manager.create_team(
                sanitize_name(team_id),
                description=description,
            )
            
            log.info("Created team: %s", team_id)
            return team_id
            
        except Exception as e:
            log.error("Failed to create team %s: %s", team_id, e)
            raise

    async def add_agent_to_team(
        self,
        agent_id: str,
        team_id: str,
    ) -> bool:
        """
        Add an agent to a team.
        
        Args:
            agent_id: Agent to add
            team_id: Team to join
            
        Returns:
            True if added successfully
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        
        try:
            member = OHTeamMember(
                agent_id=sanitize_agent_name(agent_id),
                name=agent.name,
                backend_type=("tmux" if agent.spec.backend == SwarmBackend.TMUX else "subprocess"),
                joined_at=time.time(),
                agent_type=agent.spec.agent_type,
                model=agent.spec.model,
                prompt=agent.spec.prompt,
            )
            self._lifecycle_manager.add_member(sanitize_name(team_id), member)
            
            agent.team_id = team_id
            return True
            
        except Exception as e:
            log.error("Failed to add agent %s to team %s: %s", agent_id, team_id, e)
            return False

    async def broadcast_to_team(
        self,
        team_id: str,
        message: dict[str, Any],
    ) -> int:
        """
        Broadcast a message to all agents in a team.
        
        Args:
            team_id: Team to broadcast to
            message: Message dictionary
            
        Returns:
            Number of agents message was sent to
        """
        team_agents = self.list_agents(team_id=team_id)
        count = 0
        
        for agent in team_agents:
            if agent.agent_id in self._agent_events:
                await self._agent_events[agent.agent_id].put({
                    "type": "broadcast",
                    "team_id": team_id,
                    **message,
                })
                count += 1
        
        return count

    def get_statistics(self) -> dict[str, Any]:
        """Get meta-agent statistics."""
        agents = list(self._agents.values())
        
        return {
            "total_agents": len(agents),
            "agents_by_state": {
                state.value: len([a for a in agents if a.state == state])
                for state in AgentState
            },
            "total_tasks": len(self._tasks),
            "completed_tasks": len([t for t in self._tasks.values() if t.status == "completed"]),
            "failed_tasks": len([t for t in self._tasks.values() if t.status == "failed"]),
            "pending_tasks": len([t for t in self._tasks.values() if t.status == "pending"]),
        }
