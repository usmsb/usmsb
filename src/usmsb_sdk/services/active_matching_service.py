"""
Active Matching Service

This module implements proactive matching capabilities for AI Agents:
- Suppliers actively search for demands
- Demanders actively search for suppliers
- Bidirectional negotiation
- Intelligent matching scoring

Key Features:
1. Proactive Discovery: Agents can actively broadcast and search
2. Negotiation Support: Multi-round negotiation with LLM assistance
3. Smart Scoring: Multi-dimensional match evaluation
4. Both-side Initiative: Both supply and demand sides can initiate
"""

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
    Message,
    MessageType,
)
from usmsb_sdk.core.elements import Agent, Goal, Resource
from usmsb_sdk.intelligence_adapters.base import ILLMAdapter
from usmsb_sdk.node.decentralized_node import DistributedServiceRegistry, ServiceType

logger = logging.getLogger(__name__)


class SearchStrategy(StrEnum):
    """Strategy for proactive search."""
    ACTIVE_BROADCAST = "active_broadcast"       # Broadcast to network
    TARGETED_SEARCH = "targeted_search"         # Search specific targets
    PROACTIVE_OUTREACH = "proactive_outreach"   # Direct outreach
    NETWORK_EXPLORATION = "network_exploration" # Explore network


class NegotiationStrategy(StrEnum):
    """Strategy for negotiation."""
    AGGRESSIVE = "aggressive"     # Maximize own benefit
    BALANCED = "balanced"         # Win-win approach
    CONSERVATIVE = "conservative" # Prioritize deal closure


class NegotiationStatus(StrEnum):
    """Status of negotiation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AGREED = "agreed"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class OpportunityStatus(StrEnum):
    """Status of an opportunity."""
    DISCOVERED = "discovered"
    CONTACTED = "contacted"
    NEGOTIATING = "negotiating"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class MatchScore:
    """Score for a supply-demand match."""
    overall: float
    capability_match: float
    price_match: float
    reputation_match: float
    time_match: float
    suggested_price_range: dict[str, float] = field(default_factory=dict)
    reasoning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall,
            "capability_match": self.capability_match,
            "price_match": self.price_match,
            "reputation_match": self.reputation_match,
            "time_match": self.time_match,
            "suggested_price_range": self.suggested_price_range,
            "reasoning": self.reasoning,
        }


@dataclass
class Opportunity:
    """A discovered business opportunity."""
    opportunity_id: str
    counterpart_agent_id: str
    counterpart_name: str
    opportunity_type: str  # "supply" or "demand"
    details: dict[str, Any]
    match_score: MatchScore
    status: OpportunityStatus = OpportunityStatus.DISCOVERED
    created_at: float = field(default_factory=time.time)
    negotiation_session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "counterpart_agent_id": self.counterpart_agent_id,
            "counterpart_name": self.counterpart_name,
            "opportunity_type": self.opportunity_type,
            "details": self.details,
            "match_score": self.match_score.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at,
            "negotiation_session_id": self.negotiation_session_id,
        }


@dataclass
class NegotiationProposal:
    """A proposal during negotiation."""
    price: float
    delivery_time: str
    payment_terms: str
    quality_guarantee: str = ""
    additional_terms: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "price": self.price,
            "delivery_time": self.delivery_time,
            "payment_terms": self.payment_terms,
            "quality_guarantee": self.quality_guarantee,
            "additional_terms": self.additional_terms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NegotiationProposal":
        return cls(
            price=data.get("price", 0.0),
            delivery_time=data.get("delivery_time", ""),
            payment_terms=data.get("payment_terms", ""),
            quality_guarantee=data.get("quality_guarantee", ""),
            additional_terms=data.get("additional_terms", {}),
        )


@dataclass
class NegotiationRound:
    """A single round of negotiation."""
    round_number: int
    proposer_id: str
    proposal: NegotiationProposal
    response: str  # "accepted", "rejected", "counter"
    counter_proposal: NegotiationProposal | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_number": self.round_number,
            "proposer_id": self.proposer_id,
            "proposal": self.proposal.to_dict(),
            "response": self.response,
            "counter_proposal": self.counter_proposal.to_dict() if self.counter_proposal else None,
            "timestamp": self.timestamp,
        }


@dataclass
class NegotiationSession:
    """A negotiation session between two agents."""
    session_id: str
    initiator_id: str
    counterpart_id: str
    context: dict[str, Any]
    status: NegotiationStatus = NegotiationStatus.PENDING
    rounds: list[NegotiationRound] = field(default_factory=list)
    final_terms: dict[str, Any] | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "initiator_id": self.initiator_id,
            "counterpart_id": self.counterpart_id,
            "context": self.context,
            "status": self.status.value,
            "rounds": [r.to_dict() for r in self.rounds],
            "final_terms": self.final_terms,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class NegotiationResult:
    """Result of a negotiation."""
    success: bool
    session_id: str
    final_terms: dict[str, Any] | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "session_id": self.session_id,
            "final_terms": self.final_terms,
            "reason": self.reason,
        }


class ActiveMatchingService:
    """
    Active Matching Service for Proactive Agent Matching.

    This service enables AI Agents to actively:
    1. Broadcast their capabilities or requirements
    2. Search for potential partners
    3. Initiate negotiations
    4. Auto-negotiate using LLM

    Both supply and demand sides can take initiative.
    """

    def __init__(
        self,
        communication_manager: AgentCommunicationManager,
        llm_adapter: ILLMAdapter,
        platform_registry: DistributedServiceRegistry,
    ):
        """
        Initialize the Active Matching Service.

        Args:
            communication_manager: For agent communication
            llm_adapter: For intelligent matching and negotiation
            platform_registry: For service discovery
        """
        self.comm = communication_manager
        self.llm = llm_adapter
        self.registry = platform_registry

        # Active searches tracking
        self._active_searches: dict[str, dict[str, Any]] = {}

        # Negotiations tracking
        self._negotiations: dict[str, NegotiationSession] = {}

        # Opportunities discovered
        self._opportunities: dict[str, Opportunity] = {}

        # Match history for learning
        self._match_history: list[dict[str, Any]] = []

        # Callbacks
        self.on_opportunity_discovered: Callable[[Opportunity], None] | None = None
        self.on_negotiation_update: Callable[[NegotiationSession], None] | None = None
        self.on_match_completed: Callable[[dict[str, Any]], None] | None = None

        # Start message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Setup handlers for incoming messages."""
        # These will be called by the communication manager
        pass

    # ========== Supplier Proactive Search ==========

    async def supplier_search_demands(
        self,
        supplier_agent: Agent,
        resource: Resource,
        search_strategy: SearchStrategy = SearchStrategy.ACTIVE_BROADCAST,
        max_results: int = 10,
    ) -> list[Opportunity]:
        """
        Supplier actively searches for matching demands.

        This allows a supplier to proactively find potential customers.

        Args:
            supplier_agent: The supplier agent
            resource: The resource/service being offered
            search_strategy: How to search
            max_results: Maximum opportunities to return

        Returns:
            List of discovered opportunities
        """
        search_id = str(uuid.uuid4())
        self._active_searches[search_id] = {
            "agent_id": supplier_agent.id,
            "type": "supply",
            "resource": resource.to_dict(),
            "started_at": time.time(),
            "status": "active",
        }

        opportunities = []

        try:
            # Step 1: Broadcast supply availability
            await self._broadcast_supply(supplier_agent, resource)

            # Step 2: Search demand pool in registry
            demand_services = await self._search_demand_services(supplier_agent, resource)

            # Step 3: Analyze and score each potential match
            for demand_info in demand_services[:max_results * 2]:
                match_score = await self._calculate_match_score(
                    supply=resource,
                    demand=demand_info,
                    supplier=supplier_agent,
                )

                if match_score.overall >= 0.5:  # Minimum threshold
                    opportunity = Opportunity(
                        opportunity_id=str(uuid.uuid4()),
                        counterpart_agent_id=demand_info.get("agent_id", "unknown"),
                        counterpart_name=demand_info.get("agent_name", "Unknown"),
                        opportunity_type="demand",
                        details=demand_info,
                        match_score=match_score,
                    )
                    opportunities.append(opportunity)
                    self._opportunities[opportunity.opportunity_id] = opportunity

                    if self.on_opportunity_discovered:
                        self.on_opportunity_discovered(opportunity)

            # Sort by match score
            opportunities.sort(key=lambda o: o.match_score.overall, reverse=True)

            # Step 4: Proactively contact top matches
            if search_strategy == SearchStrategy.PROACTIVE_OUTREACH:
                for opp in opportunities[:max_results]:
                    await self._send_supply_proposal(supplier_agent, opp)

            return opportunities[:max_results]

        finally:
            self._active_searches[search_id]["status"] = "completed"

    async def _broadcast_supply(self, supplier: Agent, resource: Resource) -> None:
        """Broadcast supply availability to the network."""
        message_content = {
            "type": "supply_available",
            "agent_id": supplier.id,
            "agent_name": supplier.name,
            "capabilities": supplier.capabilities,
            "resource": resource.to_dict(),
            "price_range": resource.metadata.get("price_range", {"min": 0, "max": 1000}),
            "availability": resource.metadata.get("availability", "now"),
            "reputation": supplier.metadata.get("reputation", 1.0),
            "timestamp": time.time(),
        }

        await self.comm.broadcast(
            subject="Supply Available",
            content=message_content,
            topic="supply.available",
        )
        logger.info(f"Supplier {supplier.id} broadcast supply availability")

    async def _search_demand_services(
        self,
        supplier: Agent,
        resource: Resource,
    ) -> list[dict[str, Any]]:
        """Search for demand services in the registry."""
        demands = []

        # Get services that might indicate demand
        services = await self.registry.discover_services(
            service_type=ServiceType.SKILL_PROVIDER,
            capabilities=supplier.capabilities,
        )

        for service in services:
            demand_info = {
                "agent_id": service.provider_node,
                "agent_name": service.metadata.get("name", "Unknown"),
                "service_type": service.service_type.value,
                "required_skills": service.capabilities,
                "budget_range": service.metadata.get("budget_range"),
                "deadline": service.metadata.get("deadline"),
                "priority": service.metadata.get("priority", 0),
            }
            demands.append(demand_info)

        return demands

    async def _send_supply_proposal(
        self,
        supplier: Agent,
        opportunity: Opportunity,
    ) -> None:
        """Send a proposal to a potential customer."""
        proposal_content = {
            "type": "supply_proposal",
            "supplier_id": supplier.id,
            "supplier_name": supplier.name,
            "service_description": supplier.capabilities,
            "proposed_price": opportunity.match_score.suggested_price_range,
            "availability": "immediate",
            "portfolio": supplier.metadata.get("portfolio", []),
            "reputation_score": supplier.metadata.get("reputation", 1.0),
            "match_reasoning": opportunity.match_score.reasoning,
            "opportunity_id": opportunity.opportunity_id,
        }

        await self.comm.send(
            recipient=AgentAddress(
                agent_id=opportunity.counterpart_agent_id,
                node_id="",
            ),
            subject="Service Proposal from " + supplier.name,
            content=proposal_content,
            message_type=MessageType.REQUEST,
        )

        opportunity.status = OpportunityStatus.CONTACTED
        logger.info(f"Sent supply proposal from {supplier.id} to {opportunity.counterpart_agent_id}")

    # ========== Demander Proactive Search ==========

    async def demander_search_suppliers(
        self,
        demander_agent: Agent,
        goal: Goal,
        search_strategy: SearchStrategy = SearchStrategy.ACTIVE_BROADCAST,
        max_results: int = 10,
    ) -> list[Opportunity]:
        """
        Demander actively searches for matching suppliers.

        This allows a demander to proactively find potential service providers.

        Args:
            demander_agent: The demander agent
            goal: The goal/requirement
            search_strategy: How to search
            max_results: Maximum opportunities to return

        Returns:
            List of discovered opportunities
        """
        search_id = str(uuid.uuid4())
        self._active_searches[search_id] = {
            "agent_id": demander_agent.id,
            "type": "demand",
            "goal": goal.to_dict(),
            "started_at": time.time(),
            "status": "active",
        }

        opportunities = []

        try:
            # Step 1: Broadcast demand seeking
            await self._broadcast_demand(demander_agent, goal)

            # Step 2: Search supplier services in registry
            supplier_services = await self._search_supplier_services(demander_agent, goal)

            # Step 3: Analyze and score each potential match
            for supplier_info in supplier_services[:max_results * 2]:
                match_score = await self._calculate_demand_match_score(
                    goal=goal,
                    supplier=supplier_info,
                    demander=demander_agent,
                )

                if match_score.overall >= 0.5:
                    opportunity = Opportunity(
                        opportunity_id=str(uuid.uuid4()),
                        counterpart_agent_id=supplier_info.get("agent_id", "unknown"),
                        counterpart_name=supplier_info.get("agent_name", "Unknown"),
                        opportunity_type="supply",
                        details=supplier_info,
                        match_score=match_score,
                    )
                    opportunities.append(opportunity)
                    self._opportunities[opportunity.opportunity_id] = opportunity

                    if self.on_opportunity_discovered:
                        self.on_opportunity_discovered(opportunity)

            opportunities.sort(key=lambda o: o.match_score.overall, reverse=True)

            # Step 4: Send inquiries to top matches
            for opp in opportunities[:max_results]:
                await self._send_demand_inquiry(demander_agent, opp, goal)

            return opportunities[:max_results]

        finally:
            self._active_searches[search_id]["status"] = "completed"

    async def _broadcast_demand(self, demander: Agent, goal: Goal) -> None:
        """Broadcast demand seeking to the network."""
        message_content = {
            "type": "demand_seeking",
            "agent_id": demander.id,
            "agent_name": demander.name,
            "goal": goal.to_dict(),
            "required_capabilities": goal.metadata.get("required_skills", []),
            "budget_range": goal.metadata.get("budget", {"min": 0, "max": 10000}),
            "deadline": goal.metadata.get("deadline"),
            "priority": goal.priority,
            "timestamp": time.time(),
        }

        await self.comm.broadcast(
            subject="Demand Seeking",
            content=message_content,
            topic="demand.seeking",
        )
        logger.info(f"Demander {demander.id} broadcast demand seeking")

    async def _search_supplier_services(
        self,
        demander: Agent,
        goal: Goal,
    ) -> list[dict[str, Any]]:
        """Search for supplier services in the registry."""
        suppliers = []

        required_skills = goal.metadata.get("required_skills", [])

        services = await self.registry.discover_services(
            service_type=ServiceType.SKILL_PROVIDER,
            capabilities=required_skills,
        )

        for service in services:
            supplier_info = {
                "agent_id": service.provider_node,
                "agent_name": service.metadata.get("name", "Unknown"),
                "capabilities": service.capabilities,
                "price_per_request": service.cost_per_request,
                "reputation": service.metadata.get("reputation", 1.0),
                "availability": service.load < service.max_capacity * 0.8,
                "avg_latency": service.avg_latency,
            }
            suppliers.append(supplier_info)

        return suppliers

    async def _send_demand_inquiry(
        self,
        demander: Agent,
        opportunity: Opportunity,
        goal: Goal,
    ) -> None:
        """Send an inquiry to a potential supplier."""
        inquiry_content = {
            "type": "demand_inquiry",
            "demander_id": demander.id,
            "demander_name": demander.name,
            "goal_description": goal.description,
            "required_capabilities": goal.metadata.get("required_skills", []),
            "budget_range": goal.metadata.get("budget"),
            "deadline": goal.metadata.get("deadline"),
            "questions": [
                "Can you provide this service?",
                "What is your best price?",
                "What is your availability?",
                "Can you share relevant experience?",
            ],
            "opportunity_id": opportunity.opportunity_id,
        }

        await self.comm.send(
            recipient=AgentAddress(
                agent_id=opportunity.counterpart_agent_id,
                node_id="",
            ),
            subject="Service Inquiry from " + demander.name,
            content=inquiry_content,
            message_type=MessageType.REQUEST,
        )

        opportunity.status = OpportunityStatus.CONTACTED
        logger.info(f"Sent demand inquiry from {demander.id} to {opportunity.counterpart_agent_id}")

    # ========== Negotiation ==========

    async def initiate_negotiation(
        self,
        initiator: Agent,
        counterpart_id: str,
        context: dict[str, Any],
    ) -> NegotiationSession:
        """
        Initiate a negotiation session.

        Args:
            initiator: The agent initiating negotiation
            counterpart_id: The counterpart agent ID
            context: Negotiation context (resource, goal, etc.)

        Returns:
            The negotiation session
        """
        session = NegotiationSession(
            session_id=str(uuid.uuid4()),
            initiator_id=initiator.id,
            counterpart_id=counterpart_id,
            context=context,
            status=NegotiationStatus.PENDING,
        )

        self._negotiations[session.session_id] = session

        # Send negotiation invitation
        invitation_content = {
            "type": "negotiation_invitation",
            "session_id": session.session_id,
            "initiator_id": initiator.id,
            "initiator_name": initiator.name,
            "context": context,
            "initial_terms": context.get("initial_terms", {}),
        }

        await self.comm.send(
            recipient=AgentAddress(agent_id=counterpart_id, node_id=""),
            subject="Negotiation Invitation",
            content=invitation_content,
            message_type=MessageType.REQUEST,
        )

        session.status = NegotiationStatus.IN_PROGRESS
        logger.info(f"Negotiation {session.session_id} initiated by {initiator.id}")

        if self.on_negotiation_update:
            self.on_negotiation_update(session)

        return session

    async def submit_proposal(
        self,
        session_id: str,
        proposal: NegotiationProposal,
    ) -> NegotiationRound:
        """
        Submit a proposal in a negotiation.

        Args:
            session_id: The negotiation session ID
            proposal: The proposal to submit

        Returns:
            The negotiation round record
        """
        if session_id not in self._negotiations:
            raise ValueError(f"Negotiation session {session_id} not found")

        session = self._negotiations[session_id]

        round_record = NegotiationRound(
            round_number=len(session.rounds) + 1,
            proposer_id=session.initiator_id,
            proposal=proposal,
            response="pending",
        )

        # Send proposal to counterpart
        proposal_content = {
            "type": "negotiation_proposal",
            "session_id": session_id,
            "round_number": round_record.round_number,
            "proposal": proposal.to_dict(),
        }

        response = await self.comm.request(
            recipient=AgentAddress(agent_id=session.counterpart_id, node_id=""),
            subject=f"Negotiation Round {round_record.round_number}",
            content=proposal_content,
            timeout=60.0,
        )

        if response:
            response_data = response.content if hasattr(response, 'content') else {}
            round_record.response = response_data.get("response", "rejected")

            if response_data.get("counter_proposal"):
                round_record.counter_proposal = NegotiationProposal.from_dict(
                    response_data["counter_proposal"]
                )

            # Update session based on response
            if round_record.response == "accepted":
                session.status = NegotiationStatus.AGREED
                session.final_terms = proposal.to_dict()
            elif round_record.response == "rejected":
                if len(session.rounds) >= 5:  # Max rounds
                    session.status = NegotiationStatus.REJECTED

        else:
            round_record.response = "timeout"
            if len(session.rounds) >= 3:
                session.status = NegotiationStatus.TIMEOUT

        session.rounds.append(round_record)
        session.updated_at = time.time()

        if self.on_negotiation_update:
            self.on_negotiation_update(session)

        return round_record

    async def auto_negotiate(
        self,
        agent: Agent,
        session_id: str,
        strategy: NegotiationStrategy = NegotiationStrategy.BALANCED,
        max_rounds: int = 5,
    ) -> NegotiationResult:
        """
        Auto-negotiate using LLM.

        The LLM will generate proposals based on:
        - Negotiation context
        - History of rounds
        - Agent's goals and constraints
        - Negotiation strategy

        Args:
            agent: The agent negotiating
            session_id: Negotiation session ID
            strategy: Negotiation strategy
            max_rounds: Maximum negotiation rounds

        Returns:
            The negotiation result
        """
        if session_id not in self._negotiations:
            return NegotiationResult(
                success=False,
                session_id=session_id,
                reason="Session not found",
            )

        session = self._negotiations[session_id]

        # Build negotiation prompt for LLM
        prompt = self._build_negotiation_prompt(agent, session, strategy)

        try:
            # Get LLM's proposal
            response = await self.llm.generate_text(prompt, temperature=0.7)
            proposal_data = json.loads(response)

            proposal = NegotiationProposal(
                price=proposal_data.get("price", 0),
                delivery_time=proposal_data.get("delivery_time", ""),
                payment_terms=proposal_data.get("payment_terms", ""),
                quality_guarantee=proposal_data.get("quality_guarantee", ""),
                additional_terms=proposal_data.get("additional_terms", {}),
            )

            # Submit proposal
            round_record = await self.submit_proposal(session_id, proposal)

            # Check result
            if round_record.response == "accepted":
                return NegotiationResult(
                    success=True,
                    session_id=session_id,
                    final_terms=proposal.to_dict(),
                )
            elif round_record.response == "counter" and len(session.rounds) < max_rounds:
                # Continue negotiation with counter proposal
                return await self.auto_negotiate(agent, session_id, strategy, max_rounds)
            else:
                return NegotiationResult(
                    success=False,
                    session_id=session_id,
                    reason=f"Negotiation {round_record.response}",
                )

        except Exception as e:
            logger.error(f"Auto-negotiation failed: {e}")
            return NegotiationResult(
                success=False,
                session_id=session_id,
                reason=str(e),
            )

    def _build_negotiation_prompt(
        self,
        agent: Agent,
        session: NegotiationSession,
        strategy: NegotiationStrategy,
    ) -> str:
        """Build the negotiation prompt for LLM."""
        return f"""
You are a professional negotiation agent.

## Negotiation Context:
{json.dumps(session.context, indent=2, ensure_ascii=False)}

## Negotiation History:
{json.dumps([r.to_dict() for r in session.rounds], indent=2, ensure_ascii=False)}

## Your Role:
- Agent: {agent.name}
- Strategy: {strategy.value}

## Your Goals:
{json.dumps([g.to_dict() for g in agent.goals[:3]], indent=2, ensure_ascii=False) if agent.goals else "Complete the negotiation successfully"}

## Your Constraints:
- Budget limit: {agent.metadata.get('budget_limit', 'negotiable')}
- Time limit: {agent.metadata.get('time_limit', 'flexible')}
- Quality requirements: {agent.metadata.get('quality_requirements', 'standard')}

## Task:
Generate your next negotiation proposal. Consider:
1. Previous offers and responses
2. Your strategy ({strategy.value})
3. Acceptable compromise range

## Response Format (JSON only):
{{
    "price": <number>,
    "delivery_time": "<string>",
    "payment_terms": "<string>",
    "quality_guarantee": "<string>",
    "additional_terms": {{}},
    "reasoning": "<brief explanation>"
}}
"""

    # ========== Match Scoring ==========

    async def _calculate_match_score(
        self,
        supply: Resource,
        demand: dict[str, Any],
        supplier: Agent,
    ) -> MatchScore:
        """Calculate match score between supply and demand."""
        prompt = f"""
Evaluate the match between this supply and demand:

## Supply (Service Provider):
- Agent: {supplier.name}
- Capabilities: {supplier.capabilities}
- Resource: {json.dumps(supply.to_dict(), ensure_ascii=False)}
- Reputation: {supplier.metadata.get('reputation', 1.0)}

## Demand (Customer Need):
{json.dumps(demand, indent=2, ensure_ascii=False)}

## Evaluate:
1. capability_match (0-1): How well do capabilities match?
2. price_match (0-1): Is price reasonable?
3. reputation_match (0-1): Is reputation acceptable?
4. time_match (0-1): Is timing suitable?
5. overall (0-1): Weighted average
6. suggested_price_range: {{"min": <number>, "max": <number>}}
7. reasoning: Brief explanation

## Response Format (JSON only):
{{
    "capability_match": <number>,
    "price_match": <number>,
    "reputation_match": <number>,
    "time_match": <number>,
    "overall": <number>,
    "suggested_price_range": {{"min": <number>, "max": <number>}},
    "reasoning": "<string>"
}}
"""
        try:
            response = await self.llm.generate_text(prompt, temperature=0.3)
            result = json.loads(response)

            return MatchScore(
                overall=result.get("overall", 0.5),
                capability_match=result.get("capability_match", 0.5),
                price_match=result.get("price_match", 0.5),
                reputation_match=result.get("reputation_match", 0.5),
                time_match=result.get("time_match", 0.5),
                suggested_price_range=result.get("suggested_price_range", {}),
                reasoning=result.get("reasoning", ""),
            )
        except Exception as e:
            logger.error(f"Match scoring failed: {e}")
            return MatchScore(
                overall=0.5,
                capability_match=0.5,
                price_match=0.5,
                reputation_match=0.5,
                time_match=0.5,
            )

    async def _calculate_demand_match_score(
        self,
        goal: Goal,
        supplier: dict[str, Any],
        demander: Agent,
    ) -> MatchScore:
        """Calculate match score between demand and supplier."""
        prompt = f"""
Evaluate the match between this demand and supplier:

## Demand (Customer Need):
- Goal: {goal.name}
- Description: {goal.description}
- Required Skills: {goal.metadata.get('required_skills', [])}
- Budget: {goal.metadata.get('budget', {})}
- Deadline: {goal.metadata.get('deadline')}

## Supplier (Service Provider):
{json.dumps(supplier, indent=2, ensure_ascii=False)}

## Evaluate:
1. capability_match (0-1): Can supplier meet requirements?
2. price_match (0-1): Is price within budget?
3. reputation_match (0-1): Is reputation acceptable?
4. time_match (0-1): Can supplier meet deadline?
5. overall (0-1): Weighted average
6. suggested_price_range: {{"min": <number>, "max": <number>}}
7. reasoning: Brief explanation

## Response Format (JSON only):
{{
    "capability_match": <number>,
    "price_match": <number>,
    "reputation_match": <number>,
    "time_match": <number>,
    "overall": <number>,
    "suggested_price_range": {{"min": <number>, "max": <number>}},
    "reasoning": "<string>"
}}
"""
        try:
            response = await self.llm.generate_text(prompt, temperature=0.3)
            result = json.loads(response)

            return MatchScore(
                overall=result.get("overall", 0.5),
                capability_match=result.get("capability_match", 0.5),
                price_match=result.get("price_match", 0.5),
                reputation_match=result.get("reputation_match", 0.5),
                time_match=result.get("time_match", 0.5),
                suggested_price_range=result.get("suggested_price_range", {}),
                reasoning=result.get("reasoning", ""),
            )
        except Exception as e:
            logger.error(f"Demand match scoring failed: {e}")
            return MatchScore(
                overall=0.5,
                capability_match=0.5,
                price_match=0.5,
                reputation_match=0.5,
                time_match=0.5,
            )

    # ========== Message Handlers ==========

    async def handle_supply_available(self, message: Message) -> dict[str, Any] | None:
        """Handle incoming supply available broadcast."""
        # This could be used by demanders to discover suppliers
        logger.debug(f"Received supply available from {message.content.get('agent_id')}")
        return None

    async def handle_demand_seeking(self, message: Message) -> dict[str, Any] | None:
        """Handle incoming demand seeking broadcast."""
        # This could be used by suppliers to discover demanders
        logger.debug(f"Received demand seeking from {message.content.get('agent_id')}")
        return None

    async def handle_negotiation_invitation(
        self,
        message: Message,
        agent: Agent,
    ) -> dict[str, Any]:
        """Handle incoming negotiation invitation."""
        content = message.content
        session_id = content.get("session_id")

        # Create local negotiation session
        session = NegotiationSession(
            session_id=session_id,
            initiator_id=content.get("initiator_id"),
            counterpart_id=agent.id,
            context=content.get("context", {}),
            status=NegotiationStatus.IN_PROGRESS,
        )
        self._negotiations[session_id] = session

        return {
            "type": "negotiation_accepted",
            "session_id": session_id,
            "status": "accepted",
        }

    async def handle_negotiation_proposal(
        self,
        message: Message,
        agent: Agent,
        auto_respond: bool = True,
    ) -> dict[str, Any]:
        """Handle incoming negotiation proposal."""
        content = message.content
        session_id = content.get("session_id")
        proposal_data = content.get("proposal", {})

        if session_id not in self._negotiations:
            return {"response": "rejected", "reason": "Unknown session"}

        session = self._negotiations[session_id]
        proposal = NegotiationProposal.from_dict(proposal_data)

        if auto_respond:
            # Use LLM to evaluate and respond
            response = await self._evaluate_proposal_with_llm(agent, session, proposal)
            return response
        else:
            # Return for manual review
            return {
                "response": "pending",
                "proposal": proposal.to_dict(),
            }

    async def _evaluate_proposal_with_llm(
        self,
        agent: Agent,
        session: NegotiationSession,
        proposal: NegotiationProposal,
    ) -> dict[str, Any]:
        """Use LLM to evaluate a proposal and generate response."""
        prompt = f"""
Evaluate this negotiation proposal and decide your response:

## Your Role:
- Agent: {agent.name}
- Your Goals: {[g.name for g in agent.goals[:3]] if agent.goals else "Complete negotiation"}
- Your Constraints: {agent.metadata}

## Negotiation Context:
{json.dumps(session.context, indent=2, ensure_ascii=False)}

## Previous Rounds:
{json.dumps([r.to_dict() for r in session.rounds[-3:]], indent=2, ensure_ascii=False)}

## Current Proposal:
{json.dumps(proposal.to_dict(), indent=2, ensure_ascii=False)}

## Decision Options:
1. "accepted" - Accept the proposal as-is
2. "rejected" - Reject the proposal
3. "counter" - Make a counter proposal

## Response Format (JSON only):
{{
    "response": "<accepted|rejected|counter>",
    "reasoning": "<brief explanation>",
    "counter_proposal": {{
        "price": <number or null>,
        "delivery_time": "<string or null>",
        "payment_terms": "<string or null>",
        "quality_guarantee": "<string or null>",
        "additional_terms": {{}}
    }}
}}
"""
        try:
            response = await self.llm.generate_text(prompt, temperature=0.5)
            result = json.loads(response)

            response_data = {
                "response": result.get("response", "rejected"),
                "reasoning": result.get("reasoning", ""),
            }

            if result.get("response") == "counter" and result.get("counter_proposal"):
                counter = result["counter_proposal"]
                if counter.get("price") is not None:
                    response_data["counter_proposal"] = counter

            return response_data

        except Exception as e:
            logger.error(f"Proposal evaluation failed: {e}")
            return {"response": "rejected", "reason": "Evaluation error"}

    # ========== Utility Methods ==========

    def get_opportunity(self, opportunity_id: str) -> Opportunity | None:
        """Get an opportunity by ID."""
        return self._opportunities.get(opportunity_id)

    def get_negotiation(self, session_id: str) -> NegotiationSession | None:
        """Get a negotiation session by ID."""
        return self._negotiations.get(session_id)

    def get_active_searches(self) -> list[dict[str, Any]]:
        """Get all active searches."""
        return [
            {**s, "search_id": sid}
            for sid, s in self._active_searches.items()
            if s["status"] == "active"
        ]

    def get_statistics(self) -> dict[str, Any]:
        """Get service statistics."""
        return {
            "total_searches": len(self._active_searches),
            "active_searches": sum(
                1 for s in self._active_searches.values()
                if s["status"] == "active"
            ),
            "total_opportunities": len(self._opportunities),
            "total_negotiations": len(self._negotiations),
            "successful_negotiations": sum(
                1 for n in self._negotiations.values()
                if n.status == NegotiationStatus.AGREED
            ),
        }
