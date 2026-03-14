"""
Agent Network Explorer Service

This module implements AI Agent network exploration capabilities:
- Proactive network exploration to discover new agents
- Multi-hop recommendation mechanism
- Agent capability information management
- Trust scoring and relationship management
- Contact initiation and relationship building

Key Features:
1. Network Discovery: Agents can explore the network to find new partners
2. Multi-hop Recommendations: Get recommendations through trusted agents
3. Capability Matching: Match with agents that have required capabilities
4. Trust Management: Maintain trust scores for relationship decisions
"""

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
)
from usmsb_sdk.core.elements import Agent
from usmsb_sdk.intelligence_adapters.base import ILLMAdapter
from usmsb_sdk.node.decentralized_node import DistributedServiceRegistry

logger = logging.getLogger(__name__)


class ExplorationStrategy(StrEnum):
    """Strategy for network exploration."""
    BFS = "breadth_first"      # Explore broadly
    DFS = "depth_first"        # Explore deeply
    RANDOM = "random"          # Random exploration
    TARGETED = "targeted"      # Target specific capabilities


class TrustLevel(StrEnum):
    """Trust level for agent relationships."""
    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    TRUSTED = "trusted"


@dataclass
class AgentCapabilityInfo:
    """Information about an agent's capabilities."""
    agent_id: str
    agent_name: str
    capabilities: list[str]
    skills: list[str]
    reputation: float
    status: str
    last_seen: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "capabilities": self.capabilities,
            "skills": self.skills,
            "reputation": self.reputation,
            "status": self.status,
            "last_seen": self.last_seen,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentCapabilityInfo":
        return cls(
            agent_id=data.get("agent_id", ""),
            agent_name=data.get("agent_name", "Unknown"),
            capabilities=data.get("capabilities", []),
            skills=data.get("skills", []),
            reputation=data.get("reputation", 1.0),
            status=data.get("status", "unknown"),
            last_seen=data.get("last_seen", time.time()),
            metadata=data.get("metadata", {}),
        )


@dataclass
class AgentRecommendation:
    """Recommendation from another agent."""
    recommended_agent_id: str
    recommended_agent_name: str
    recommended_by: str
    capability_match: float
    trust_score: float
    reason: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommended_agent_id": self.recommended_agent_id,
            "recommended_agent_name": self.recommended_agent_name,
            "recommended_by": self.recommended_by,
            "capability_match": self.capability_match,
            "trust_score": self.trust_score,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class ContactRequest:
    """Request to contact another agent."""
    request_id: str
    requester_id: str
    requester_name: str
    target_id: str
    contact_reason: str
    proposal: dict[str, Any] | None = None
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    response_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "requester_id": self.requester_id,
            "requester_name": self.requester_name,
            "target_id": self.target_id,
            "contact_reason": self.contact_reason,
            "proposal": self.proposal,
            "status": self.status,
            "created_at": self.created_at,
            "response_message": self.response_message,
        }


@dataclass
class ContactResult:
    """Result of a contact attempt."""
    target_agent_id: str
    accepted: bool
    response_message: str
    suggested_action: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_agent_id": self.target_agent_id,
            "accepted": self.accepted,
            "response_message": self.response_message,
            "suggested_action": self.suggested_action,
        }


@dataclass
class ExplorationRecord:
    """Record of a network exploration."""
    explorer_id: str
    discovered_agents: list[str]
    exploration_depth: int
    strategy: str
    started_at: float
    completed_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "explorer_id": self.explorer_id,
            "discovered_agents": self.discovered_agents,
            "exploration_depth": self.exploration_depth,
            "strategy": self.strategy,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class AgentRelationship:
    """Relationship between two agents."""
    agent_id: str
    related_agent_id: str
    trust_level: TrustLevel
    trust_score: float
    interaction_count: int
    last_interaction: float
    shared_capabilities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "related_agent_id": self.related_agent_id,
            "trust_level": self.trust_level.value,
            "trust_score": self.trust_score,
            "interaction_count": self.interaction_count,
            "last_interaction": self.last_interaction,
            "shared_capabilities": self.shared_capabilities,
            "metadata": self.metadata,
        }


class AgentNetworkExplorer:
    """
    Agent Network Explorer Service

    Enables AI Agents to proactively explore the network,
    discover new agents, and build relationships.
    """

    def __init__(
        self,
        communication_manager: AgentCommunicationManager,
        registry: DistributedServiceRegistry,
        llm_adapter: ILLMAdapter | None = None,
    ):
        """
        Initialize the Agent Network Explorer.

        Args:
            communication_manager: For agent communication
            registry: For service discovery
            llm_adapter: For intelligent matching (optional)
        """
        self.comm = communication_manager
        self.registry = registry
        self.llm = llm_adapter

        # Network graph: agent_id -> set of known agent_ids
        self._network_graph: dict[str, set[str]] = {}

        # Agent capabilities cache
        self._agent_capabilities: dict[str, AgentCapabilityInfo] = {}

        # Trust scores: agent_id -> {related_agent_id -> trust_score}
        self._trust_scores: dict[str, dict[str, float]] = {}

        # Relationships: agent_id -> list of relationships
        self._relationships: dict[str, list[AgentRelationship]] = {}

        # Exploration history
        self._exploration_history: list[ExplorationRecord] = []

        # Contact requests
        self._contact_requests: dict[str, ContactRequest] = {}

        # Callbacks
        self.on_agent_discovered: Callable[[AgentCapabilityInfo], None] | None = None
        self.on_relationship_established: Callable[[AgentRelationship], None] | None = None

    async def explore_network(
        self,
        agent: Agent,
        exploration_depth: int = 2,
        max_agents_per_hop: int = 5,
        target_capabilities: list[str] | None = None,
        strategy: ExplorationStrategy = ExplorationStrategy.BFS,
    ) -> list[AgentCapabilityInfo]:
        """
        Proactively explore the network to discover new agents.

        Args:
            agent: The agent performing exploration
            exploration_depth: How many hops to explore
            max_agents_per_hop: Maximum agents to discover per hop
            target_capabilities: Filter by specific capabilities
            strategy: Exploration strategy to use

        Returns:
            List of discovered agent capabilities
        """
        discovered_agents: list[AgentCapabilityInfo] = []
        visited: set[str] = {agent.id}
        current_hop: list[str] = [agent.id]

        exploration_record = ExplorationRecord(
            explorer_id=agent.id,
            discovered_agents=[],
            exploration_depth=exploration_depth,
            strategy=strategy.value,
            started_at=time.time(),
        )

        try:
            for _depth in range(exploration_depth):
                next_hop: list[str] = []

                for current_agent_id in current_hop:
                    # Get known agents from network graph or registry
                    known_agents = await self._get_known_agents(current_agent_id)

                    for known_agent_id in known_agents:
                        if known_agent_id in visited:
                            continue
                        if len(discovered_agents) >= max_agents_per_hop * exploration_depth:
                            break

                        # Get agent capabilities
                        capability_info = await self._get_agent_capabilities(known_agent_id)

                        if capability_info:
                            # Check if matches target capabilities
                            if target_capabilities:
                                match_score = self._calculate_capability_match(
                                    capability_info.capabilities + capability_info.skills,
                                    target_capabilities
                                )
                                if match_score < 0.3:
                                    continue

                            discovered_agents.append(capability_info)
                            visited.add(known_agent_id)
                            next_hop.append(known_agent_id)

                            # Update network graph
                            if agent.id not in self._network_graph:
                                self._network_graph[agent.id] = set()
                            self._network_graph[agent.id].add(known_agent_id)

                            # Trigger callback
                            if self.on_agent_discovered:
                                self.on_agent_discovered(capability_info)

                        if len(discovered_agents) >= max_agents_per_hop * exploration_depth:
                            break

                current_hop = next_hop

                if not current_hop:
                    break

            # Update exploration record
            exploration_record.discovered_agents = [a.agent_id for a in discovered_agents]
            exploration_record.completed_at = time.time()
            self._exploration_history.append(exploration_record)

            return discovered_agents

        except Exception as e:
            logger.error(f"Network exploration error: {e}")
            return discovered_agents

    async def _get_known_agents(self, agent_id: str) -> list[str]:
        """Get agents known by a specific agent."""
        # From local network graph
        if agent_id in self._network_graph:
            return list(self._network_graph[agent_id])

        # From registry
        try:
            services = await self.registry.discover_services(
                service_type=None,
                capabilities=None,
            )
            return [s.provider_node for s in services]
        except Exception:
            return []

    async def _get_agent_capabilities(self, agent_id: str) -> AgentCapabilityInfo | None:
        """Get capabilities of an agent."""
        # Check cache first
        if agent_id in self._agent_capabilities:
            return self._agent_capabilities[agent_id]

        # Query the agent directly
        try:
            response = await self.comm.request(
                recipient=AgentAddress(agent_id=agent_id, node_id=""),
                subject="Query Capabilities",
                content={"type": "query_capabilities"},
                timeout=10.0,
            )

            if response and response.content:
                info = AgentCapabilityInfo(
                    agent_id=agent_id,
                    agent_name=response.content.get("name", "Unknown"),
                    capabilities=response.content.get("capabilities", []),
                    skills=response.content.get("skills", []),
                    reputation=response.content.get("reputation", 1.0),
                    status=response.content.get("status", "active"),
                )
                self._agent_capabilities[agent_id] = info
                return info
        except Exception as e:
            logger.debug(f"Failed to query agent {agent_id}: {e}")

        # Try to get from registry
        try:
            services = await self.registry.discover_services(
                service_type=None,
                capabilities=None,
            )
            for service in services:
                if service.provider_node == agent_id:
                    info = AgentCapabilityInfo(
                        agent_id=agent_id,
                        agent_name=service.provider_node,
                        capabilities=service.capabilities,
                        skills=[],
                        reputation=1.0,
                        status="active",
                    )
                    self._agent_capabilities[agent_id] = info
                    return info
        except Exception:
            pass

        return None

    def _calculate_capability_match(
        self,
        agent_capabilities: list[str],
        target_capabilities: list[str],
    ) -> float:
        """Calculate how well agent capabilities match targets."""
        if not target_capabilities:
            return 1.0

        agent_caps_set = {c.lower() for c in agent_capabilities}
        target_caps_set = {c.lower() for c in target_capabilities}

        matches = len(agent_caps_set & target_caps_set)
        return matches / len(target_caps_set) if target_caps_set else 0.0

    async def request_recommendations(
        self,
        agent: Agent,
        target_capability: str,
        max_recommendations: int = 5,
    ) -> list[AgentRecommendation]:
        """
        Request recommendations from known agents.

        Args:
            agent: The agent requesting recommendations
            target_capability: The capability being sought
            max_recommendations: Maximum number of recommendations

        Returns:
            List of agent recommendations
        """
        recommendations: list[AgentRecommendation] = []

        # Get known agents from network
        known_agents = self._network_graph.get(agent.id, set())

        for known_agent_id in known_agents:
            # Send recommendation request
            try:
                response = await self.comm.request(
                    recipient=AgentAddress(agent_id=known_agent_id, node_id=""),
                    subject="Request Recommendation",
                    content={
                        "type": "request_recommendation",
                        "target_capability": target_capability,
                        "requester_id": agent.id,
                    },
                    timeout=15.0,
                )

                if response and response.content:
                    recommended_agents = response.content.get("recommendations", [])

                    for rec in recommended_agents:
                        recommendation = AgentRecommendation(
                            recommended_agent_id=rec.get("agent_id", ""),
                            recommended_agent_name=rec.get("agent_name", "Unknown"),
                            recommended_by=known_agent_id,
                            capability_match=rec.get("capability_match", 0.5),
                            trust_score=self._get_trust_score(agent.id, known_agent_id),
                            reason=rec.get("reason", ""),
                        )
                        recommendations.append(recommendation)
            except Exception as e:
                logger.debug(f"Failed to get recommendation from {known_agent_id}: {e}")

        # Sort by trust_score * capability_match
        recommendations.sort(
            key=lambda r: r.trust_score * r.capability_match,
            reverse=True
        )

        return recommendations[:max_recommendations]

    def _get_trust_score(self, agent_id: str, other_agent_id: str) -> float:
        """Get trust score between two agents."""
        if agent_id not in self._trust_scores:
            return 0.5  # Default medium trust
        return self._trust_scores[agent_id].get(other_agent_id, 0.5)

    async def initiate_contact(
        self,
        agent: Agent,
        target_agent_id: str,
        contact_reason: str,
        proposal: dict[str, Any] | None = None,
    ) -> ContactResult:
        """
        Initiate contact with another agent.

        Args:
            agent: The agent initiating contact
            target_agent_id: The target agent to contact
            contact_reason: Reason for contact
            proposal: Optional proposal for collaboration

        Returns:
            Result of the contact attempt
        """
        # Create contact request
        request = ContactRequest(
            request_id=str(uuid.uuid4()),
            requester_id=agent.id,
            requester_name=agent.name,
            target_id=target_agent_id,
            contact_reason=contact_reason,
            proposal=proposal,
        )
        self._contact_requests[request.request_id] = request

        # Send contact message
        try:
            response = await self.comm.request(
                recipient=AgentAddress(agent_id=target_agent_id, node_id=""),
                subject=f"Contact Request from {agent.name}",
                content={
                    "type": "contact_request",
                    "request_id": request.request_id,
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "contact_reason": contact_reason,
                    "proposal": proposal,
                    "capabilities": agent.capabilities,
                },
                timeout=30.0,
            )

            if response:
                accepted = response.content.get("accepted", False)
                result = ContactResult(
                    target_agent_id=target_agent_id,
                    accepted=accepted,
                    response_message=response.content.get("message", ""),
                    suggested_action=response.content.get("suggested_action"),
                )

                # Update relationship if accepted
                if accepted:
                    await self._establish_relationship(agent.id, target_agent_id)

                return result

        except Exception as e:
            logger.debug(f"Contact request failed: {e}")

        return ContactResult(
            target_agent_id=target_agent_id,
            accepted=False,
            response_message="No response",
        )

    async def _establish_relationship(
        self,
        agent_id: str,
        related_agent_id: str,
    ) -> None:
        """Establish a relationship between two agents."""
        # Get shared capabilities
        agent_caps = await self._get_agent_capabilities(agent_id)
        related_caps = await self._get_agent_capabilities(related_agent_id)

        shared = []
        if agent_caps and related_caps:
            agent_caps_set = set(agent_caps.capabilities + agent_caps.skills)
            related_caps_set = set(related_caps.capabilities + related_caps.skills)
            shared = list(agent_caps_set & related_caps_set)

        # Create relationship
        relationship = AgentRelationship(
            agent_id=agent_id,
            related_agent_id=related_agent_id,
            trust_level=TrustLevel.MEDIUM,
            trust_score=0.6,
            interaction_count=1,
            last_interaction=time.time(),
            shared_capabilities=shared,
        )

        if agent_id not in self._relationships:
            self._relationships[agent_id] = []
        self._relationships[agent_id].append(relationship)

        # Update network graph
        if agent_id not in self._network_graph:
            self._network_graph[agent_id] = set()
        self._network_graph[agent_id].add(related_agent_id)

        # Update trust scores
        if agent_id not in self._trust_scores:
            self._trust_scores[agent_id] = {}
        self._trust_scores[agent_id][related_agent_id] = 0.6

        # Trigger callback
        if self.on_relationship_established:
            self.on_relationship_established(relationship)

    async def broadcast_interest(
        self,
        agent: Agent,
        interest_type: str,  # "seeking" or "offering"
        capability: str,
        details: dict[str, Any],
    ) -> int:
        """
        Broadcast interest to the network.

        Args:
            agent: The agent broadcasting
            interest_type: Type of interest
            capability: The capability involved
            details: Additional details

        Returns:
            Number of agents expected to receive
        """
        broadcast_content = {
            "type": "interest_broadcast",
            "agent_id": agent.id,
            "agent_name": agent.name,
            "interest_type": interest_type,
            "capability": capability,
            "details": details,
            "timestamp": time.time(),
        }

        await self.comm.broadcast(
            subject=f"Interest: {interest_type} {capability}",
            content=broadcast_content,
            topic=f"interest.{interest_type}.{capability}",
        )

        # Return expected reach
        return len(self._network_graph.get(agent.id, set()))

    async def get_agent_network(
        self,
        agent_id: str,
        depth: int = 1,
    ) -> list[AgentCapabilityInfo]:
        """
        Get an agent's network (agents they know).

        Args:
            agent_id: The agent to get network for
            depth: How many hops to traverse

        Returns:
            List of agents in the network
        """
        network: list[AgentCapabilityInfo] = []
        visited: set[str] = {agent_id}
        current: list[str] = list(self._network_graph.get(agent_id, set()))

        for _ in range(depth):
            next_level: list[str] = []
            for agent_id in current:
                if agent_id in visited:
                    continue
                visited.add(agent_id)

                capability_info = await self._get_agent_capabilities(agent_id)
                if capability_info:
                    network.append(capability_info)

                next_level.extend(self._network_graph.get(agent_id, []))
            current = next_level

        return network

    def get_trusted_agents(
        self,
        agent_id: str,
        min_trust: float = 0.7,
    ) -> list[str]:
        """
        Get agents trusted by a specific agent.

        Args:
            agent_id: The agent to get trusted agents for
            min_trust: Minimum trust threshold

        Returns:
            List of trusted agent IDs
        """
        trust_scores = self._trust_scores.get(agent_id, {})
        return [
            aid for aid, score in trust_scores.items()
            if score >= min_trust
        ]

    async def update_trust_score(
        self,
        agent_id: str,
        related_agent_id: str,
        new_score: float,
    ) -> None:
        """
        Update trust score between two agents.

        Args:
            agent_id: First agent
            related_agent_id: Second agent
            new_score: New trust score (0-1)
        """
        if agent_id not in self._trust_scores:
            self._trust_scores[agent_id] = {}

        self._trust_scores[agent_id][related_agent_id] = max(0.0, min(1.0, new_score))

        # Update trust level
        if agent_id in self._relationships:
            for rel in self._relationships[agent_id]:
                if rel.related_agent_id == related_agent_id:
                    rel.trust_score = new_score
                    if new_score >= 0.8:
                        rel.trust_level = TrustLevel.TRUSTED
                    elif new_score >= 0.6:
                        rel.trust_level = TrustLevel.HIGH
                    elif new_score >= 0.4:
                        rel.trust_level = TrustLevel.MEDIUM
                    else:
                        rel.trust_level = TrustLevel.LOW
                    break

    def get_exploration_stats(self, agent_id: str) -> dict[str, Any]:
        """Get exploration statistics for an agent."""
        agent_explorations = [
            e for e in self._exploration_history
            if e.explorer_id == agent_id
        ]

        return {
            "total_explorations": len(agent_explorations),
            "total_discovered": sum(
                len(e.discovered_agents) for e in agent_explorations
            ),
            "network_size": len(self._network_graph.get(agent_id, set())),
            "trusted_agents": len(self.get_trusted_agents(agent_id)),
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize explorer state."""
        return {
            "network_graph": {
                aid: list(agents) for aid, agents in self._network_graph.items()
            },
            "trust_scores": self._trust_scores,
            "relationships": {
                aid: [r.to_dict() for r in rels]
                for aid, rels in self._relationships.items()
            },
            "exploration_history": [e.to_dict() for e in self._exploration_history[-50:]],
        }
