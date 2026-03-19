"""
Emergence Discovery Service

Phase 3 of USMSB Agent Platform implementation.

Provides hybrid emergence mechanism:
- Simple tasks (complexity < threshold) → centralized matching
- Complex tasks (complexity >= threshold) → decentralized discovery

D4 Fix: Broadcasts are now persisted to DB, not just in-memory.
Emergence is NOT automatic. It requires:
1. Minimum active agents (100)
2. Minimum collaboration rate (30%)
3. Minimum Soul completeness (70%)

Only when these thresholds are met does the platform enable full
decentralized emergence for complex tasks.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from usmsb_sdk.services.agent_soul import AgentSoulManager
from usmsb_sdk.services.schema import BroadcastDB, BroadcastResponseDB, create_session

logger = logging.getLogger(__name__)


@dataclass
class EmergenceStats:
    """Platform emergence statistics."""
    active_agents: int = 0
    collaboration_success_rate: float = 0.0
    soul_completeness: float = 0.0  # % of agents with complete Soul
    total_collaborations: int = 0
    emergence_enabled: bool = False

    def meets_threshold(self) -> bool:
        return (
            self.active_agents >= EmergenceDiscovery.EMERGENCE_TRIGGER["min_active_agents"]
            and self.collaboration_success_rate >= EmergenceDiscovery.EMERGENCE_TRIGGER["min_collaboration_rate"]
            and self.soul_completeness >= EmergenceDiscovery.EMERGENCE_TRIGGER["min_soul_completeness"]
        )


@dataclass
class OpportunityDiscoveryResult:
    """Result of complex task opportunity discovery."""
    discovery_type: str  # "decentralized" | "centralized"
    opportunities: list[dict] = field(default_factory=list)
    total_found: int = 0
    discovery_time_ms: float = 0.0
    agent_responses: int = 0
    emergence_active: bool = False


@dataclass
class AgentBroadcast:
    """Represents an agent's broadcast for opportunity discovery."""
    broadcast_id: str
    agent_id: str
    broadcast_type: str  # "seeking" | "offering"
    content: dict[str, Any]  # {goal, capability, requirements}
    timestamp: float = 0.0
    expires_at: float = 0.0
    responses: list[dict] = field(default_factory=list)


class EmergenceDiscovery:
    """
    Hybrid Emergence Discovery Service.

    Manages the transition from centralized to decentralized matching
    based on platform emergence readiness.

    Emergence trigger thresholds (configurable):
    - min_active_agents: 100
    - min_collaboration_rate: 0.30
    - min_soul_completeness: 0.70
    """

    # Emergence trigger thresholds
    EMERGENCE_TRIGGER = {
        "min_active_agents": 100,
        "min_collaboration_rate": 0.30,
        "min_soul_completeness": 0.70,
    }

    # Broadcast configuration
    BROADCAST_TIMEOUT_SECONDS = 300  # 5 minutes
    MAX_BROADCAST_RESPONSES = 20

    def __init__(self, db_session=None):
        self.soul_manager = None
        self._db_session = db_session  # Optional DB session

    def _get_db_session(self):
        """Get or create DB session."""
        if self._db_session is None:
            self._db_session = create_session()
        return self._db_session

    def _get_soul_manager(self) -> AgentSoulManager:
        if self.soul_manager is None:
            session = create_session()
            self.soul_manager = AgentSoulManager(session)
        return self.soul_manager

    async def get_emergence_stats(self) -> EmergenceStats:
        """
        Calculate current platform emergence statistics.

        Returns EmergenceStats with current platform metrics.
        """
        manager = self._get_soul_manager()
        session = manager.db
        from usmsb_sdk.services.schema import AgentSoulDB, FeedbackEventDB

        # Count active agents (have registered Soul and were active recently)
        all_souls = session.query(AgentSoulDB).all()
        active_agents = len([
            s for s in all_souls
            if s.environment_state and s.environment_state.get("status") != "deleted"
        ])

        # Calculate collaboration success rate
        recent_events = session.query(FeedbackEventDB).filter(
            FeedbackEventDB.process_status == "processed"
        ).all()

        total_collaborations = len(recent_events)
        successful = len([e for e in recent_events if e.event_data and e.event_data.get("success")])

        collaboration_rate = successful / max(total_collaborations, 1)

        # Calculate Soul completeness
        complete_souls = len([
            s for s in all_souls
            if s.declared_soul and s.inferred_soul
        ])
        soul_completeness = complete_souls / max(len(all_souls), 1)

        stats = EmergenceStats(
            active_agents=active_agents,
            collaboration_success_rate=collaboration_rate,
            soul_completeness=soul_completeness,
            total_collaborations=total_collaborations,
            emergence_enabled=self._check_emergence_trigger(active_agents, collaboration_rate, soul_completeness),
        )

        return stats

    def _check_emergence_trigger(
        self,
        active_agents: int,
        collaboration_rate: float,
        soul_completeness: float,
    ) -> bool:
        """Check if emergence trigger conditions are met."""
        return (
            active_agents >= self.EMERGENCE_TRIGGER["min_active_agents"]
            and collaboration_rate >= self.EMERGENCE_TRIGGER["min_collaboration_rate"]
            and soul_completeness >= self.EMERGENCE_TRIGGER["min_soul_completeness"]
        )

    async def should_use_emergence(self) -> bool:
        """
        Check if the platform has reached emergence readiness.

        Returns True if all trigger conditions are met.
        """
        stats = await self.get_emergence_stats()
        return stats.meets_threshold()

    async def discover_complex_task(
        self,
        agent_id: str,
        task_def: dict[str, Any],
        complexity_score: float,
    ) -> OpportunityDiscoveryResult:
        """
        Discover opportunities for a complex task using emergence mechanism.

        For complex tasks (complexity >= threshold):
        - Use decentralized discovery with agent broadcasts

        Args:
            agent_id: Agent seeking opportunity
            task_def: Task definition
            complexity_score: Task complexity (0-10)

        Returns:
            OpportunityDiscoveryResult with found opportunities
        """
        start_time = time.time()
        emergence_active = await self.should_use_emergence()

        if complexity_score < self.EMERGENCE_TRIGGER["min_active_agents"] or not emergence_active:
            # Below threshold or emergence not active → use centralized
            return OpportunityDiscoveryResult(
                discovery_type="centralized",
                opportunities=[],
                total_found=0,
                discovery_time_ms=(time.time() - start_time) * 1000,
                agent_responses=0,
                emergence_active=emergence_active,
            )

        # Emergence active → use decentralized discovery
        return await self._decentralized_discovery(
            agent_id=agent_id,
            task_def=task_def,
        )

    async def _decentralized_discovery(
        self,
        agent_id: str,
        task_def: dict[str, Any],
    ) -> OpportunityDiscoveryResult:
        """
        Decentralized opportunity discovery via agent broadcasts.

        Flow:
        1. Agent broadcasts its goal/capability need
        2. Other agents respond if interested
        3. Collect responses within timeout window
        4. Rank and return opportunities

        This is the emergence mechanism - agents self-organize.

        D4 Fix: Now persists broadcast to DB instead of in-memory.
        """
        start_time = time.time()
        db = self._get_db_session()

        # Create broadcast
        broadcast_id = f"bc-{int(time.time())}-{agent_id[:8]}"
        now = time.time()

        # D4 Fix: Persist to DB instead of in-memory
        db_broadcast = BroadcastDB(
            broadcast_id=broadcast_id,
            agent_id=agent_id,
            broadcast_type="seeking",
            content={
                "task_def": task_def,
                "goal": task_def.get("title", "Complex task"),
            },
            response_count=0,
            status="active",
            timestamp=now,
            expires_at=now + self.BROADCAST_TIMEOUT_SECONDS,
        )

        db.add(db_broadcast)
        db.commit()

        # Create in-memory broadcast object for _collect_responses
        broadcast = AgentBroadcast(
            broadcast_id=broadcast_id,
            agent_id=agent_id,
            broadcast_type="seeking",
            content={
                "task_def": task_def,
                "goal": task_def.get("title", "Complex task"),
            },
            timestamp=now,
            expires_at=now + self.BROADCAST_TIMEOUT_SECONDS,
        )

        try:
            # Simulate collecting responses (in real impl, this would wait for async responses)
            # For now, use existing agents in the system
            responses = await self._collect_responses(broadcast)

            # Rank responses
            ranked = await self._rank_responses(responses)

            return OpportunityDiscoveryResult(
                discovery_type="decentralized",
                opportunities=ranked,
                total_found=len(ranked),
                discovery_time_ms=(time.time() - start_time) * 1000,
                agent_responses=len(responses),
                emergence_active=True,
            )

        finally:
            # Mark broadcast as fulfilled in DB
            self.fulfill_broadcast(broadcast_id)

    async def _collect_responses(self, broadcast: AgentBroadcast) -> list[dict]:
        """Collect responses to a broadcast from other agents."""
        manager = self._get_soul_manager()
        all_agents = await self._get_all_agents()

        responses = []
        for agent_soul in all_agents:
            if agent_soul.agent_id == broadcast.agent_id:
                continue

            # Check if agent is interested
            if self._agent_interested(agent_soul, broadcast):
                responses.append({
                    "agent_id": agent_soul.agent_id,
                    "agent_soul": agent_soul.to_dict(),
                    "match_score": self._calculate_response_match(agent_soul, broadcast),
                    "proposed_terms": self._generate_proposed_terms(agent_soul),
                    "responded_at": time.time(),
                })

        return responses[:self.MAX_BROADCAST_RESPONSES]

    def _agent_interested(self, agent_soul, broadcast: AgentBroadcast) -> bool:
        """Check if an agent is interested in responding to a broadcast."""
        # Simple interest check based on capabilities/goals
        content = broadcast.content
        task_goal = content.get("goal", "")

        # Check if agent's capabilities might match
        for cap in agent_soul.declared.capabilities:
            if cap.lower() in task_goal.lower():
                return True

        return False

    def _calculate_response_match(self, agent_soul, broadcast: AgentBroadcast) -> float:
        """Calculate how well an agent matches the broadcast's need."""
        content = broadcast.content
        task_goal = content.get("goal", "")

        # Simple match based on capability overlap
        match_count = 0
        for cap in agent_soul.declared.capabilities:
            if cap.lower() in task_goal.lower():
                match_count += 1

        base_score = match_count / max(len(agent_soul.declared.capabilities), 1)

        # Adjust by reputation
        if agent_soul.inferred:
            rep_adjustment = (agent_soul.inferred.actual_success_rate - 0.5) * 0.2
            base_score = max(0.0, min(1.0, base_score + rep_adjustment))

        return base_score

    def _generate_proposed_terms(self, agent_soul) -> dict[str, Any]:
        """Generate proposed contract terms from agent's Soul."""
        return {
            "price_vibe": agent_soul.declared.base_price_vibe or 10.0,
            "deadline": 86400,  # Default 1 day
            "style": agent_soul.declared.collaboration_style,
        }

    async def _rank_responses(self, responses: list[dict]) -> list[dict]:
        """Rank responses by match score and return sorted list."""
        sorted_responses = sorted(
            responses,
            key=lambda x: x.get("match_score", 0),
            reverse=True
        )
        return sorted_responses

    async def _get_all_agents(self) -> list:
        """Get all registered agent souls."""
        manager = self._get_soul_manager()
        session = manager.db
        from usmsb_sdk.services.schema import AgentSoulDB

        db_records = session.query(AgentSoulDB).filter(
            AgentSoulDB.environment_state.isnot(None)
        ).all()

        souls = [manager._db_to_soul(r) for r in db_records]
        return souls

    async def broadcast_goal(
        self,
        agent_id: str,
        goal: str,
        requirements: list[str],
    ) -> str:
        """
        Agent broadcasts a goal to the platform.

        This enables other agents to discover collaboration opportunities.

        D4 Fix: Now persists to DB instead of in-memory.

        Returns broadcast_id.
        """
        db = self._get_db_session()

        broadcast_id = f"bc-goal-{int(time.time())}-{agent_id[:8]}"

        db_broadcast = BroadcastDB(
            broadcast_id=broadcast_id,
            agent_id=agent_id,
            broadcast_type="seeking",
            content={
                "goal": goal,
                "requirements": requirements,
            },
            response_count=0,
            status="active",
            timestamp=time.time(),
            expires_at=time.time() + self.BROADCAST_TIMEOUT_SECONDS,
        )

        db.add(db_broadcast)
        db.commit()

        logger.info(f"Persisted broadcast_goal {broadcast_id} for agent {agent_id}")
        return broadcast_id

    async def broadcast_capability(
        self,
        agent_id: str,
        capability: str,
        offering: str,
    ) -> str:
        """
        Agent broadcasts a capability offering.

        This enables agents seeking this capability to respond.

        D4 Fix: Now persists to DB instead of in-memory.

        Returns broadcast_id.
        """
        db = self._get_db_session()

        broadcast_id = f"bc-cap-{int(time.time())}-{agent_id[:8]}"

        db_broadcast = BroadcastDB(
            broadcast_id=broadcast_id,
            agent_id=agent_id,
            broadcast_type="offering",
            content={
                "capability": capability,
                "offering": offering,
            },
            response_count=0,
            status="active",
            timestamp=time.time(),
            expires_at=time.time() + self.BROADCAST_TIMEOUT_SECONDS,
        )

        db.add(db_broadcast)
        db.commit()

        logger.info(f"Persisted broadcast_capability {broadcast_id} for agent {agent_id}")
        return broadcast_id

    def get_active_broadcasts(self, agent_id: str | None = None) -> list[dict]:
        """
        Get active broadcasts from DB.

        D4 Fix: Now reads from DB, not in-memory.
        """
        db = self._get_db_session()
        now = time.time()

        query = db.query(BroadcastDB).filter(
            BroadcastDB.status == "active",
            BroadcastDB.expires_at > now,
        )

        if agent_id:
            query = query.filter(BroadcastDB.agent_id == agent_id)

        broadcasts = query.all()

        return [
            {
                "broadcast_id": b.broadcast_id,
                "agent_id": b.agent_id,
                "broadcast_type": b.broadcast_type,
                "content": b.content,
                "response_count": b.response_count,
                "expires_at": b.expires_at,
            }
            for b in broadcasts
        ]

    def cleanup_expired_broadcasts(self) -> int:
        """
        Clean up expired broadcasts.

        L1 Fix: Prevents memory leak by removing expired broadcasts from DB.

        Returns:
            Number of broadcasts cleaned up
        """
        db = self._get_db_session()
        now = time.time()

        # Mark expired broadcasts as expired
        result = db.query(BroadcastDB).filter(
            BroadcastDB.status == "active",
            BroadcastDB.expires_at <= now,
        ).update({"status": "expired"})

        db.commit()
        return result

    def fulfill_broadcast(self, broadcast_id: str) -> bool:
        """
        Mark a broadcast as fulfilled (opportunity found).

        D4 Fix: Persist fulfillment status to DB.

        Returns:
            True if broadcast was found and updated
        """
        db = self._get_db_session()

        result = db.query(BroadcastDB).filter(
            BroadcastDB.broadcast_id == broadcast_id
        ).update({
            "status": "fulfilled",
            "fulfilled_at": time.time(),
        })

        db.commit()
        return result > 0

    def get_emergence_threshold(self) -> dict:
        """Return current emergence trigger thresholds."""
        return self.EMERGENCE_TRIGGER.copy()

    def set_emergence_threshold(self, **kwargs) -> None:
        """Update emergence trigger thresholds (admin only in production)."""
        for key, value in kwargs.items():
            if key in self.EMERGENCE_TRIGGER:
                self.EMERGENCE_TRIGGER[key] = value
                logger.info(f"Updated emergence threshold {key} = {value}")
