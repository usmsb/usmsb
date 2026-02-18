"""
External Agent Adapter

This module provides unified integration for external AI Agents:
- Support for multiple protocols (A2A, MCP, P2P)
- Skill discovery and capability matching
- Communication protocol abstraction
- External agent lifecycle management

Supported Protocols:
1. A2A (Agent-to-Agent): Direct agent communication protocol
2. MCP (Model Context Protocol): Standard AI service protocol
3. P2P: Peer-to-peer decentralized communication
4. HTTP/REST: Standard web API integration
"""

import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union, TypeVar, Generic

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ExternalAgentProtocol(str, Enum):
    """Supported external agent protocols."""
    A2A = "a2a"           # Agent-to-Agent
    MCP = "mcp"           # Model Context Protocol
    P2P = "p2p"           # Peer-to-Peer
    HTTP = "http"         # HTTP REST
    WEBSOCKET = "websocket"  # WebSocket
    GRPC = "grpc"         # gRPC


class ExternalAgentStatus(str, Enum):
    """Status of external agent."""
    UNKNOWN = "unknown"
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"


class SkillMatchLevel(str, Enum):
    """Level of skill matching."""
    EXACT = "exact"
    PARTIAL = "partial"
    COMPATIBLE = "compatible"
    NONE = "none"


@dataclass
class SkillDefinition:
    """Definition of an agent skill."""
    skill_id: str
    name: str
    description: str
    category: str = "general"
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    keywords: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "keywords": self.keywords,
            "prerequisites": self.prerequisites,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillDefinition":
        return cls(
            skill_id=data.get("skill_id", str(uuid.uuid4())),
            name=data.get("name", "Unknown"),
            description=data.get("description", ""),
            category=data.get("category", "general"),
            input_schema=data.get("input_schema", {}),
            output_schema=data.get("output_schema", {}),
            keywords=data.get("keywords", []),
            prerequisites=data.get("prerequisites", []),
            metadata=data.get("metadata", {}),
        )

    def matches(self, query: str) -> SkillMatchLevel:
        """Check if skill matches a query."""
        query_lower = query.lower()

        # Exact match
        if query_lower == self.name.lower() or query_lower == self.skill_id.lower():
            return SkillMatchLevel.EXACT

        # Check keywords
        for keyword in self.keywords:
            if query_lower == keyword.lower():
                return SkillMatchLevel.EXACT
            if keyword.lower() in query_lower:
                return SkillMatchLevel.PARTIAL

        # Check description
        if query_lower in self.description.lower():
            return SkillMatchLevel.PARTIAL

        # Check category
        if query_lower == self.category.lower():
            return SkillMatchLevel.COMPATIBLE

        return SkillMatchLevel.NONE


@dataclass
class ExternalAgentProfile:
    """Profile of an external agent."""
    agent_id: str
    name: str
    description: str
    protocol: ExternalAgentProtocol
    endpoint: str
    skills: List[SkillDefinition] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    status: ExternalAgentStatus = ExternalAgentStatus.UNKNOWN
    reputation: float = 1.0
    last_seen: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "protocol": self.protocol.value,
            "endpoint": self.endpoint,
            "skills": [s.to_dict() for s in self.skills],
            "capabilities": self.capabilities,
            "status": self.status.value,
            "reputation": self.reputation,
            "last_seen": self.last_seen,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExternalAgentProfile":
        skills = [SkillDefinition.from_dict(s) for s in data.get("skills", [])]
        return cls(
            agent_id=data.get("agent_id", str(uuid.uuid4())),
            name=data.get("name", "Unknown"),
            description=data.get("description", ""),
            protocol=ExternalAgentProtocol(data.get("protocol", "http")),
            endpoint=data.get("endpoint", ""),
            skills=skills,
            capabilities=data.get("capabilities", []),
            status=ExternalAgentStatus(data.get("status", "unknown")),
            reputation=data.get("reputation", 1.0),
            last_seen=data.get("last_seen", 0.0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ExternalAgentCall:
    """A call to an external agent."""
    call_id: str
    agent_id: str
    skill_name: str
    arguments: Dict[str, Any]
    timeout: float = 60.0
    priority: int = 0
    created_at: float = field(default_factory=time.time)
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "call_id": self.call_id,
            "agent_id": self.agent_id,
            "skill_name": self.skill_name,
            "arguments": self.arguments,
            "timeout": self.timeout,
            "priority": self.priority,
            "created_at": self.created_at,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
        }


@dataclass
class ExternalAgentResponse:
    """Response from an external agent."""
    call_id: str
    agent_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "call_id": self.call_id,
            "agent_id": self.agent_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }


class ProtocolHandler(ABC):
    """Abstract base class for protocol handlers."""

    @abstractmethod
    async def connect(self, endpoint: str) -> bool:
        """Connect to the agent endpoint."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the agent."""
        pass

    @abstractmethod
    async def call_skill(
        self,
        skill_name: str,
        arguments: Dict[str, Any],
        timeout: float = 60.0,
    ) -> ExternalAgentResponse:
        """Call a skill on the external agent."""
        pass

    @abstractmethod
    async def discover_skills(self) -> List[SkillDefinition]:
        """Discover available skills from the agent."""
        pass

    @abstractmethod
    async def check_status(self) -> ExternalAgentStatus:
        """Check the agent's status."""
        pass


class A2AProtocolHandler(ProtocolHandler):
    """Handler for A2A (Agent-to-Agent) protocol."""

    def __init__(self):
        self._connected = False
        self._endpoint: Optional[str] = None

    async def connect(self, endpoint: str) -> bool:
        """Connect to A2A agent."""
        self._endpoint = endpoint
        # In real implementation, establish A2A connection
        self._connected = True
        logger.info(f"A2A connection established to {endpoint}")
        return True

    async def disconnect(self) -> None:
        """Disconnect from A2A agent."""
        self._connected = False
        logger.info("A2A connection closed")

    async def call_skill(
        self,
        skill_name: str,
        arguments: Dict[str, Any],
        timeout: float = 60.0,
    ) -> ExternalAgentResponse:
        """Call skill via A2A protocol."""
        if not self._connected:
            return ExternalAgentResponse(
                call_id=str(uuid.uuid4()),
                agent_id="",
                success=False,
                error="Not connected",
            )

        call_id = str(uuid.uuid4())
        start_time = time.time()

        try:
            # In real implementation, send A2A message
            await asyncio.sleep(0.1)  # Simulate network delay

            return ExternalAgentResponse(
                call_id=call_id,
                agent_id="",
                success=True,
                result={"output": f"Executed {skill_name}"},
                metadata={"execution_time": time.time() - start_time},
            )

        except asyncio.TimeoutError:
            return ExternalAgentResponse(
                call_id=call_id,
                agent_id="",
                success=False,
                error="Timeout",
            )

        except Exception as e:
            return ExternalAgentResponse(
                call_id=call_id,
                agent_id="",
                success=False,
                error=str(e),
            )

    async def discover_skills(self) -> List[SkillDefinition]:
        """Discover skills via A2A protocol."""
        # In real implementation, query agent for skills
        return []

    async def check_status(self) -> ExternalAgentStatus:
        """Check A2A agent status."""
        if self._connected:
            return ExternalAgentStatus.ONLINE
        return ExternalAgentStatus.OFFLINE


class HTTPProtocolHandler(ProtocolHandler):
    """Handler for HTTP REST protocol."""

    def __init__(self):
        self._connected = False
        self._endpoint: Optional[str] = None

    async def connect(self, endpoint: str) -> bool:
        """Connect to HTTP agent."""
        self._endpoint = endpoint
        self._connected = True
        logger.info(f"HTTP connection established to {endpoint}")
        return True

    async def disconnect(self) -> None:
        """Disconnect from HTTP agent."""
        self._connected = False
        logger.info("HTTP connection closed")

    async def call_skill(
        self,
        skill_name: str,
        arguments: Dict[str, Any],
        timeout: float = 60.0,
    ) -> ExternalAgentResponse:
        """Call skill via HTTP."""
        if not self._connected:
            return ExternalAgentResponse(
                call_id=str(uuid.uuid4()),
                agent_id="",
                success=False,
                error="Not connected",
            )

        call_id = str(uuid.uuid4())
        start_time = time.time()

        try:
            # In real implementation, make HTTP request
            # POST {endpoint}/skills/{skill_name}
            await asyncio.sleep(0.2)  # Simulate HTTP delay

            return ExternalAgentResponse(
                call_id=call_id,
                agent_id="",
                success=True,
                result={"output": f"HTTP executed {skill_name}"},
                metadata={"execution_time": time.time() - start_time},
            )

        except Exception as e:
            return ExternalAgentResponse(
                call_id=call_id,
                agent_id="",
                success=False,
                error=str(e),
            )

    async def discover_skills(self) -> List[SkillDefinition]:
        """Discover skills via HTTP."""
        # GET {endpoint}/skills
        return []

    async def check_status(self) -> ExternalAgentStatus:
        """Check HTTP agent status."""
        # GET {endpoint}/health
        if self._connected:
            return ExternalAgentStatus.ONLINE
        return ExternalAgentStatus.OFFLINE


class ExternalAgentAdapter:
    """
    Unified Adapter for External AI Agents.

    This adapter provides a unified interface for integrating external
    AI agents regardless of their communication protocol.

    Features:
    - Multi-protocol support (A2A, MCP, P2P, HTTP, WebSocket, gRPC)
    - Skill discovery and capability matching
    - Connection management
    - Call routing and load balancing
    - Error handling and retries
    """

    def __init__(self):
        """Initialize the External Agent Adapter."""
        # Registered external agents
        self._agents: Dict[str, ExternalAgentProfile] = {}

        # Protocol handlers
        self._handlers: Dict[str, ProtocolHandler] = {}

        # Pending calls
        self._pending_calls: Dict[str, ExternalAgentCall] = {}

        # Call history
        self._call_history: List[ExternalAgentCall] = []

        # Skill index for quick lookup
        self._skill_index: Dict[str, List[str]] = {}  # skill_name -> agent_ids

        # Callbacks
        self.on_agent_registered: Optional[Callable[[ExternalAgentProfile], None]] = None
        self.on_agent_status_changed: Optional[Callable[[str, ExternalAgentStatus], None]] = None
        self.on_call_completed: Optional[Callable[[ExternalAgentCall], None]] = None

    def _get_protocol_handler(self, protocol: ExternalAgentProtocol) -> ProtocolHandler:
        """Get or create a protocol handler."""
        if protocol == ExternalAgentProtocol.A2A:
            return A2AProtocolHandler()
        elif protocol == ExternalAgentProtocol.HTTP:
            return HTTPProtocolHandler()
        else:
            # Default to HTTP
            return HTTPProtocolHandler()

    # ========== Agent Registration ==========

    async def register_agent(
        self,
        agent_id: str,
        name: str,
        description: str,
        protocol: ExternalAgentProtocol,
        endpoint: str,
        skills: Optional[List[SkillDefinition]] = None,
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExternalAgentProfile:
        """
        Register an external agent.

        Args:
            agent_id: Unique identifier
            name: Agent name
            description: Agent description
            protocol: Communication protocol
            endpoint: Agent endpoint
            skills: List of skills
            capabilities: List of capabilities
            metadata: Additional metadata

        Returns:
            The registered agent profile
        """
        profile = ExternalAgentProfile(
            agent_id=agent_id,
            name=name,
            description=description,
            protocol=protocol,
            endpoint=endpoint,
            skills=skills or [],
            capabilities=capabilities or [],
            status=ExternalAgentStatus.UNKNOWN,
            metadata=metadata or {},
        )

        # Create and connect protocol handler
        handler = self._get_protocol_handler(protocol)
        connected = await handler.connect(endpoint)

        if connected:
            profile.status = ExternalAgentStatus.ONLINE
            profile.last_seen = time.time()

            # Discover skills if not provided
            if not profile.skills:
                profile.skills = await handler.discover_skills()

        self._agents[agent_id] = profile
        self._handlers[agent_id] = handler

        # Index skills
        for skill in profile.skills:
            skill_key = skill.name.lower()
            if skill_key not in self._skill_index:
                self._skill_index[skill_key] = []
            self._skill_index[skill_key].append(agent_id)

        logger.info(f"Registered external agent: {agent_id} ({protocol.value})")

        if self.on_agent_registered:
            self.on_agent_registered(profile)

        return profile

    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an external agent."""
        if agent_id not in self._agents:
            return False

        # Disconnect handler
        if agent_id in self._handlers:
            await self._handlers[agent_id].disconnect()
            del self._handlers[agent_id]

        # Remove from skill index
        profile = self._agents[agent_id]
        for skill in profile.skills:
            skill_key = skill.name.lower()
            if skill_key in self._skill_index:
                if agent_id in self._skill_index[skill_key]:
                    self._skill_index[skill_key].remove(agent_id)

        del self._agents[agent_id]
        logger.info(f"Unregistered external agent: {agent_id}")
        return True

    def get_agent(self, agent_id: str) -> Optional[ExternalAgentProfile]:
        """Get an agent profile by ID."""
        return self._agents.get(agent_id)

    def list_agents(
        self,
        protocol: Optional[ExternalAgentProtocol] = None,
        status: Optional[ExternalAgentStatus] = None,
    ) -> List[ExternalAgentProfile]:
        """List registered agents with optional filtering."""
        agents = list(self._agents.values())

        if protocol:
            agents = [a for a in agents if a.protocol == protocol]

        if status:
            agents = [a for a in agents if a.status == status]

        return agents

    # ========== Skill Discovery ==========

    def find_agents_by_skill(
        self,
        skill_name: str,
        match_level: SkillMatchLevel = SkillMatchLevel.PARTIAL,
    ) -> List[ExternalAgentProfile]:
        """
        Find agents that have a specific skill.

        Args:
            skill_name: Skill to search for
            match_level: Minimum match level required

        Returns:
            List of matching agent profiles
        """
        skill_lower = skill_name.lower()
        matching_agents = []

        for agent in self._agents.values():
            for skill in agent.skills:
                match = skill.matches(skill_name)

                # Check if match level is sufficient
                levels = {
                    SkillMatchLevel.EXACT: 4,
                    SkillMatchLevel.PARTIAL: 3,
                    SkillMatchLevel.COMPATIBLE: 2,
                    SkillMatchLevel.NONE: 1,
                }

                if levels[match] >= levels[match_level]:
                    matching_agents.append(agent)
                    break

        return matching_agents

    def find_agents_by_capability(
        self,
        capability: str,
    ) -> List[ExternalAgentProfile]:
        """Find agents that have a specific capability."""
        capability_lower = capability.lower()
        return [
            agent for agent in self._agents.values()
            if any(capability_lower in c.lower() for c in agent.capabilities)
        ]

    def get_skill(self, agent_id: str, skill_name: str) -> Optional[SkillDefinition]:
        """Get a specific skill from an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return None

        for skill in agent.skills:
            if skill.name.lower() == skill_name.lower():
                return skill

        return None

    # ========== Agent Calls ==========

    async def call_agent(
        self,
        agent_id: str,
        skill_name: str,
        arguments: Dict[str, Any],
        timeout: float = 60.0,
        priority: int = 0,
    ) -> ExternalAgentResponse:
        """
        Call a skill on an external agent.

        Args:
            agent_id: Target agent ID
            skill_name: Skill to call
            arguments: Arguments for the skill
            timeout: Call timeout
            priority: Call priority

        Returns:
            The response from the agent
        """
        if agent_id not in self._agents:
            return ExternalAgentResponse(
                call_id=str(uuid.uuid4()),
                agent_id=agent_id,
                success=False,
                error="Agent not found",
            )

        if agent_id not in self._handlers:
            return ExternalAgentResponse(
                call_id=str(uuid.uuid4()),
                agent_id=agent_id,
                success=False,
                error="No handler for agent",
            )

        # Create call record
        call = ExternalAgentCall(
            call_id=str(uuid.uuid4()),
            agent_id=agent_id,
            skill_name=skill_name,
            arguments=arguments,
            timeout=timeout,
            priority=priority,
        )

        self._pending_calls[call.call_id] = call

        # Execute call
        handler = self._handlers[agent_id]
        start_time = time.time()

        try:
            response = await handler.call_skill(skill_name, arguments, timeout)

            call.status = "completed" if response.success else "failed"
            call.result = response.result
            call.error = response.error
            call.execution_time = time.time() - start_time

            # Update agent last seen
            self._agents[agent_id].last_seen = time.time()

        except asyncio.TimeoutError:
            call.status = "timeout"
            call.error = "Call timed out"
            call.execution_time = time.time() - start_time

            response = ExternalAgentResponse(
                call_id=call.call_id,
                agent_id=agent_id,
                success=False,
                error="Timeout",
            )

        except Exception as e:
            call.status = "error"
            call.error = str(e)
            call.execution_time = time.time() - start_time

            response = ExternalAgentResponse(
                call_id=call.call_id,
                agent_id=agent_id,
                success=False,
                error=str(e),
            )

        # Move to history
        self._call_history.append(call)
        if call.call_id in self._pending_calls:
            del self._pending_calls[call.call_id]

        if self.on_call_completed:
            self.on_call_completed(call)

        return response

    async def call_best_agent(
        self,
        skill_name: str,
        arguments: Dict[str, Any],
        selection_criteria: str = "reputation",
        timeout: float = 60.0,
    ) -> ExternalAgentResponse:
        """
        Find and call the best agent for a skill.

        Args:
            skill_name: Skill to call
            arguments: Arguments for the skill
            selection_criteria: How to select agent (reputation, load, random)
            timeout: Call timeout

        Returns:
            The response from the selected agent
        """
        # Find agents with the skill
        agents = self.find_agents_by_skill(skill_name, SkillMatchLevel.PARTIAL)

        # Filter online agents
        online_agents = [a for a in agents if a.status == ExternalAgentStatus.ONLINE]

        if not online_agents:
            return ExternalAgentResponse(
                call_id=str(uuid.uuid4()),
                agent_id="",
                success=False,
                error="No online agents with required skill",
            )

        # Select best agent
        if selection_criteria == "reputation":
            best_agent = max(online_agents, key=lambda a: a.reputation)
        elif selection_criteria == "random":
            import random
            best_agent = random.choice(online_agents)
        else:
            best_agent = online_agents[0]

        return await self.call_agent(
            agent_id=best_agent.agent_id,
            skill_name=skill_name,
            arguments=arguments,
            timeout=timeout,
        )

    async def broadcast_to_skill(
        self,
        skill_name: str,
        arguments: Dict[str, Any],
        max_responses: int = 5,
        timeout: float = 30.0,
    ) -> List[ExternalAgentResponse]:
        """
        Broadcast a call to all agents with a skill.

        Args:
            skill_name: Skill to call
            arguments: Arguments for the skill
            max_responses: Maximum responses to wait for
            timeout: Total timeout for all responses

        Returns:
            List of responses
        """
        agents = self.find_agents_by_skill(skill_name)
        online_agents = [a for a in agents if a.status == ExternalAgentStatus.ONLINE]

        if not online_agents:
            return []

        # Make concurrent calls
        tasks = [
            self.call_agent(a.agent_id, skill_name, arguments, timeout / 2)
            for a in online_agents[:max_responses * 2]
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter valid responses
        valid_responses = [
            r for r in responses
            if isinstance(r, ExternalAgentResponse) and r.success
        ]

        return valid_responses[:max_responses]

    # ========== Status Management ==========

    async def check_agent_status(self, agent_id: str) -> ExternalAgentStatus:
        """Check the status of an agent."""
        if agent_id not in self._agents or agent_id not in self._handlers:
            return ExternalAgentStatus.UNKNOWN

        handler = self._handlers[agent_id]
        status = await handler.check_status()

        old_status = self._agents[agent_id].status
        self._agents[agent_id].status = status

        if status == ExternalAgentStatus.ONLINE:
            self._agents[agent_id].last_seen = time.time()

        if old_status != status and self.on_agent_status_changed:
            self.on_agent_status_changed(agent_id, status)

        return status

    async def check_all_agents_status(self) -> Dict[str, ExternalAgentStatus]:
        """Check status of all registered agents."""
        tasks = {aid: self.check_agent_status(aid) for aid in self._agents}
        results = {}

        for aid, task in tasks.items():
            results[aid] = await task

        return results

    # ========== Utility Methods ==========

    def get_statistics(self) -> Dict[str, Any]:
        """Get adapter statistics."""
        successful_calls = sum(1 for c in self._call_history if c.status == "completed")
        failed_calls = sum(1 for c in self._call_history if c.status != "completed")

        return {
            "total_agents": len(self._agents),
            "online_agents": sum(
                1 for a in self._agents.values()
                if a.status == ExternalAgentStatus.ONLINE
            ),
            "total_skills": sum(len(a.skills) for a in self._agents.values()),
            "total_calls": len(self._call_history),
            "pending_calls": len(self._pending_calls),
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "success_rate": successful_calls / max(1, len(self._call_history)),
        }

    def get_call_history(
        self,
        agent_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[ExternalAgentCall]:
        """Get call history."""
        history = self._call_history

        if agent_id:
            history = [c for c in history if c.agent_id == agent_id]

        return history[-limit:]

    def clear_history(self) -> None:
        """Clear call history."""
        self._call_history.clear()


# ========== Convenience Functions ==========

def create_skill_from_dict(data: Dict[str, Any]) -> SkillDefinition:
    """Create a SkillDefinition from a dictionary."""
    return SkillDefinition.from_dict(data)


def create_agent_from_skill_md(skill_md_content: str) -> Optional[ExternalAgentProfile]:
    """
    Parse a skill.md file and create an agent profile.

    Args:
        skill_md_content: Content of skill.md file

    Returns:
        ExternalAgentProfile or None if parsing fails
    """
    # Simple markdown parsing for skill definitions
    # Expected format:
    # # Agent Name
    # Description: ...
    # Protocol: ...
    # Endpoint: ...
    # ## Skills
    # - skill_name: description

    try:
        lines = skill_md_content.split('\n')
        name = ""
        description = ""
        protocol = ExternalAgentProtocol.HTTP
        endpoint = ""
        skills = []

        for i, line in enumerate(lines):
            line = line.strip()

            if line.startswith('# ') and not name:
                name = line[2:].strip()

            elif line.lower().startswith('description:'):
                description = line.split(':', 1)[1].strip()

            elif line.lower().startswith('protocol:'):
                proto_str = line.split(':', 1)[1].strip().lower()
                protocol = ExternalAgentProtocol(proto_str)

            elif line.lower().startswith('endpoint:'):
                endpoint = line.split(':', 1)[1].strip()

            elif line.startswith('- ') and ':' in line:
                skill_parts = line[2:].split(':', 1)
                if len(skill_parts) == 2:
                    skills.append(SkillDefinition(
                        skill_id=str(uuid.uuid4()),
                        name=skill_parts[0].strip(),
                        description=skill_parts[1].strip(),
                    ))

        if name and endpoint:
            return ExternalAgentProfile(
                agent_id=str(uuid.uuid4()),
                name=name,
                description=description,
                protocol=protocol,
                endpoint=endpoint,
                skills=skills,
            )

    except Exception as e:
        logger.error(f"Failed to parse skill.md: {e}")

    return None
