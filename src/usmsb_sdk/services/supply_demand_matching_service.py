"""
Supply-Demand Matching Integration Service

This module provides an integrated service that combines:
- Active Matching Service (proactive search)
- Environment Broadcast Service (announcements)
- External Agent Adapter (external integration)
- Negotiation and deal closing

It serves as the main entry point for supply-demand matching in the platform.
"""

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from usmsb_sdk.core.elements import Agent, Goal, Resource
from usmsb_sdk.platform.environment.broadcast_service import (
    BroadcastScope,
    BroadcastType,
    EnvironmentBroadcastService,
)
from usmsb_sdk.platform.external.external_agent_adapter import (
    ExternalAgentAdapter,
    ExternalAgentProfile,
    ExternalAgentProtocol,
)
from usmsb_sdk.services.active_matching_service import (
    ActiveMatchingService,
    NegotiationStrategy,
    SearchStrategy,
)

logger = logging.getLogger(__name__)


class MatchingMode(StrEnum):
    """Mode for supply-demand matching."""
    PROACTIVE = "proactive"       # Actively search and reach out
    PASSIVE = "passive"           # Wait for incoming requests
    HYBRID = "hybrid"             # Both proactive and passive
    AUCTION = "auction"           # Auction-based matching


class MatchStatus(StrEnum):
    """Status of a match."""
    SEARCHING = "searching"
    NEGOTIATING = "negotiating"
    MATCHED = "matched"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SupplyListing:
    """A supply listing in the marketplace."""
    listing_id: str
    agent_id: str
    agent_name: str
    resource: dict[str, Any]
    price_range: dict[str, float]
    availability: str = "now"
    capabilities: list[str] = field(default_factory=list)
    reputation: float = 1.0
    created_at: float = field(default_factory=time.time)
    expires_at: float | None = None
    status: str = "active"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "listing_id": self.listing_id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "resource": self.resource,
            "price_range": self.price_range,
            "availability": self.availability,
            "capabilities": self.capabilities,
            "reputation": self.reputation,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status,
            "metadata": self.metadata,
        }


@dataclass
class DemandListing:
    """A demand listing in the marketplace."""
    listing_id: str
    agent_id: str
    agent_name: str
    requirement: dict[str, Any]
    budget: dict[str, float]
    deadline: str | None = None
    required_capabilities: list[str] = field(default_factory=list)
    priority: int = 0
    created_at: float = field(default_factory=time.time)
    expires_at: float | None = None
    status: str = "active"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "listing_id": self.listing_id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "requirement": self.requirement,
            "budget": self.budget,
            "deadline": self.deadline,
            "required_capabilities": self.required_capabilities,
            "priority": self.priority,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status,
            "metadata": self.metadata,
        }


@dataclass
class Match:
    """A matched supply-demand pair."""
    match_id: str
    supply_listing: SupplyListing
    demand_listing: DemandListing
    match_score: float
    negotiated_terms: dict[str, Any] | None = None
    status: MatchStatus = MatchStatus.SEARCHING
    negotiation_session_id: str | None = None
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "supply_listing": self.supply_listing.to_dict(),
            "demand_listing": self.demand_listing.to_dict(),
            "match_score": self.match_score,
            "negotiated_terms": self.negotiated_terms,
            "status": self.status.value,
            "negotiation_session_id": self.negotiation_session_id,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
        }


@dataclass
class MatchingStats:
    """Statistics for the matching service."""
    total_supply_listings: int = 0
    total_demand_listings: int = 0
    active_searches: int = 0
    total_matches: int = 0
    successful_matches: int = 0
    failed_matches: int = 0
    total_negotiations: int = 0
    successful_negotiations: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_supply_listings": self.total_supply_listings,
            "total_demand_listings": self.total_demand_listings,
            "active_searches": self.active_searches,
            "total_matches": self.total_matches,
            "successful_matches": self.successful_matches,
            "failed_matches": self.failed_matches,
            "total_negotiations": self.total_negotiations,
            "successful_negotiations": self.successful_negotiations,
            "success_rate": self.successful_matches / max(1, self.total_matches),
        }


class SupplyDemandMatchingService:
    """
    Integrated Supply-Demand Matching Service.

    This service provides a unified interface for:
    - Publishing supply listings
    - Publishing demand listings
    - Proactive matching (both sides can initiate)
    - Automated negotiation
    - Deal closing

    It integrates:
    - ActiveMatchingService for proactive search
    - EnvironmentBroadcastService for announcements
    - ExternalAgentAdapter for external agent integration
    """

    def __init__(
        self,
        active_matching_service: ActiveMatchingService,
        broadcast_service: EnvironmentBroadcastService,
        external_agent_adapter: ExternalAgentAdapter,
    ):
        """
        Initialize the Supply-Demand Matching Service.

        Args:
            active_matching_service: Service for proactive matching
            broadcast_service: Service for environment broadcasts
            external_agent_adapter: Adapter for external agents
        """
        self.active_matching = active_matching_service
        self.broadcast = broadcast_service
        self.external_adapter = external_agent_adapter

        # Listings
        self._supply_listings: dict[str, SupplyListing] = {}
        self._demand_listings: dict[str, DemandListing] = {}

        # Matches
        self._matches: dict[str, Match] = {}

        # Agent listings index
        self._agent_supply_listings: dict[str, list[str]] = {}
        self._agent_demand_listings: dict[str, list[str]] = {}

        # Statistics
        self._stats = MatchingStats()

        # Running searches
        self._running_searches: dict[str, asyncio.Task] = {}

        # Callbacks
        self.on_match_created: Callable[[Match], None] | None = None
        self.on_match_completed: Callable[[Match], None] | None = None
        self.on_listing_added: Callable[[dict[str, Any]], None] | None = None

        # Setup broadcast handlers
        self._setup_broadcast_handlers()

    def _setup_broadcast_handlers(self) -> None:
        """Setup handlers for broadcast messages."""
        # These will be called when broadcasts are received
        pass

    # ========== Supply Listing Management ==========

    async def publish_supply(
        self,
        agent: Agent,
        resource: Resource,
        price_range: dict[str, float] | None = None,
        availability: str = "now",
        expires_in: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SupplyListing:
        """
        Publish a supply listing.

        Args:
            agent: The supplier agent
            resource: The resource being offered
            price_range: Price range for the resource
            availability: Availability status
            expires_in: Time until listing expires (seconds)
            metadata: Additional metadata

        Returns:
            The created supply listing
        """
        listing_id = str(uuid.uuid4())

        listing = SupplyListing(
            listing_id=listing_id,
            agent_id=agent.id,
            agent_name=agent.name,
            resource=resource.to_dict(),
            price_range=price_range or {"min": 0, "max": 1000},
            availability=availability,
            capabilities=agent.capabilities,
            reputation=agent.metadata.get("reputation", 1.0),
            expires_at=time.time() + expires_in if expires_in else None,
            metadata=metadata or {},
        )

        self._supply_listings[listing_id] = listing

        # Index by agent
        if agent.id not in self._agent_supply_listings:
            self._agent_supply_listings[agent.id] = []
        self._agent_supply_listings[agent.id].append(listing_id)

        self._stats.total_supply_listings += 1

        # Broadcast supply availability
        await self.broadcast.broadcast_supply_available(
            agent_id=agent.id,
            agent_name=agent.name,
            resource=resource.to_dict(),
            price_range=price_range,
            availability=availability,
        )

        if self.on_listing_added:
            self.on_listing_added({"type": "supply", "listing": listing.to_dict()})

        logger.info(f"Published supply listing {listing_id} from agent {agent.id}")
        return listing

    def get_supply_listing(self, listing_id: str) -> SupplyListing | None:
        """Get a supply listing by ID."""
        return self._supply_listings.get(listing_id)

    def get_agent_supply_listings(self, agent_id: str) -> list[SupplyListing]:
        """Get all supply listings for an agent."""
        listing_ids = self._agent_supply_listings.get(agent_id, [])
        return [
            self._supply_listings[lid]
            for lid in listing_ids
            if lid in self._supply_listings
        ]

    def search_supply_listings(
        self,
        capabilities: list[str] | None = None,
        price_max: float | None = None,
        keywords: list[str] | None = None,
        limit: int = 20,
    ) -> list[SupplyListing]:
        """Search supply listings."""
        results = []

        for listing in self._supply_listings.values():
            if listing.status != "active":
                continue

            if listing.expires_at and time.time() > listing.expires_at:
                continue

            # Filter by capabilities
            if capabilities:
                if not any(c in listing.capabilities for c in capabilities):
                    continue

            # Filter by price
            if price_max is not None:
                if listing.price_range.get("min", 0) > price_max:
                    continue

            # Filter by keywords
            if keywords:
                resource_desc = listing.resource.get("description", "").lower()
                if not any(kw.lower() in resource_desc for kw in keywords):
                    continue

            results.append(listing)

        # Sort by reputation
        results.sort(key=lambda x: x.reputation, reverse=True)
        return results[:limit]

    # ========== Demand Listing Management ==========

    async def publish_demand(
        self,
        agent: Agent,
        goal: Goal,
        budget: dict[str, float] | None = None,
        deadline: str | None = None,
        expires_in: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DemandListing:
        """
        Publish a demand listing.

        Args:
            agent: The demander agent
            goal: The goal/requirement
            budget: Budget range
            deadline: Deadline for fulfillment
            expires_in: Time until listing expires (seconds)
            metadata: Additional metadata

        Returns:
            The created demand listing
        """
        listing_id = str(uuid.uuid4())

        listing = DemandListing(
            listing_id=listing_id,
            agent_id=agent.id,
            agent_name=agent.name,
            requirement=goal.to_dict(),
            budget=budget or goal.metadata.get("budget", {"min": 0, "max": 10000}),
            deadline=deadline or goal.metadata.get("deadline"),
            required_capabilities=goal.metadata.get("required_skills", []),
            priority=goal.priority,
            expires_at=time.time() + expires_in if expires_in else None,
            metadata=metadata or {},
        )

        self._demand_listings[listing_id] = listing

        # Index by agent
        if agent.id not in self._agent_demand_listings:
            self._agent_demand_listings[agent.id] = []
        self._agent_demand_listings[agent.id].append(listing_id)

        self._stats.total_demand_listings += 1

        # Broadcast demand seeking
        await self.broadcast.broadcast_demand_seeking(
            agent_id=agent.id,
            agent_name=agent.name,
            requirement=goal.to_dict(),
            budget=budget,
            deadline=deadline,
        )

        if self.on_listing_added:
            self.on_listing_added({"type": "demand", "listing": listing.to_dict()})

        logger.info(f"Published demand listing {listing_id} from agent {agent.id}")
        return listing

    def get_demand_listing(self, listing_id: str) -> DemandListing | None:
        """Get a demand listing by ID."""
        return self._demand_listings.get(listing_id)

    def get_agent_demand_listings(self, agent_id: str) -> list[DemandListing]:
        """Get all demand listings for an agent."""
        listing_ids = self._agent_demand_listings.get(agent_id, [])
        return [
            self._demand_listings[lid]
            for lid in listing_ids
            if lid in self._demand_listings
        ]

    def search_demand_listings(
        self,
        capabilities: list[str] | None = None,
        budget_min: float | None = None,
        keywords: list[str] | None = None,
        limit: int = 20,
    ) -> list[DemandListing]:
        """Search demand listings."""
        results = []

        for listing in self._demand_listings.values():
            if listing.status != "active":
                continue

            if listing.expires_at and time.time() > listing.expires_at:
                continue

            # Filter by capabilities
            if capabilities:
                if not any(c in listing.required_capabilities for c in capabilities):
                    continue

            # Filter by budget
            if budget_min is not None:
                if listing.budget.get("max", 0) < budget_min:
                    continue

            # Filter by keywords
            if keywords:
                req_desc = listing.requirement.get("description", "").lower()
                if not any(kw.lower() in req_desc for kw in keywords):
                    continue

            results.append(listing)

        # Sort by priority
        results.sort(key=lambda x: x.priority, reverse=True)
        return results[:limit]

    # ========== Proactive Matching ==========

    async def supplier_proactive_search(
        self,
        supplier_agent: Agent,
        resource: Resource,
        mode: MatchingMode = MatchingMode.HYBRID,
        max_results: int = 10,
        auto_negotiate: bool = False,
        negotiation_strategy: NegotiationStrategy = NegotiationStrategy.BALANCED,
    ) -> list[Match]:
        """
        Supplier proactively searches for demands.

        Args:
            supplier_agent: The supplier agent
            resource: The resource being offered
            mode: Matching mode
            max_results: Maximum results
            auto_negotiate: Whether to auto-negotiate
            negotiation_strategy: Strategy for negotiation

        Returns:
            List of potential matches
        """
        str(uuid.uuid4())
        self._stats.active_searches += 1

        try:
            # Use active matching service to search
            opportunities = await self.active_matching.supplier_search_demands(
                supplier_agent=supplier_agent,
                resource=resource,
                search_strategy=SearchStrategy.PROACTIVE_OUTREACH,
                max_results=max_results,
            )

            matches = []

            for opp in opportunities:
                # Find or create demand listing
                demand_listing = DemandListing(
                    listing_id=str(uuid.uuid4()),
                    agent_id=opp.counterpart_agent_id,
                    agent_name=opp.counterpart_name,
                    requirement=opp.details,
                    budget=opp.details.get("budget_range", {}),
                    required_capabilities=opp.details.get("required_skills", []),
                )

                # Create supply listing
                supply_listing = SupplyListing(
                    listing_id=str(uuid.uuid4()),
                    agent_id=supplier_agent.id,
                    agent_name=supplier_agent.name,
                    resource=resource.to_dict(),
                    price_range=resource.metadata.get("price_range", {}),
                    capabilities=supplier_agent.capabilities,
                )

                # Create match
                match = Match(
                    match_id=str(uuid.uuid4()),
                    supply_listing=supply_listing,
                    demand_listing=demand_listing,
                    match_score=opp.match_score.overall,
                    status=MatchStatus.SEARCHING,
                )

                self._matches[match.match_id] = match
                self._stats.total_matches += 1

                if self.on_match_created:
                    self.on_match_created(match)

                # Start negotiation if auto-negotiate
                if auto_negotiate:
                    match = await self._start_negotiation(
                        match=match,
                        supplier_agent=supplier_agent,
                        negotiation_strategy=negotiation_strategy,
                    )

                matches.append(match)

            return matches

        finally:
            self._stats.active_searches -= 1

    async def demander_proactive_search(
        self,
        demander_agent: Agent,
        goal: Goal,
        mode: MatchingMode = MatchingMode.HYBRID,
        max_results: int = 10,
        auto_negotiate: bool = False,
        negotiation_strategy: NegotiationStrategy = NegotiationStrategy.BALANCED,
    ) -> list[Match]:
        """
        Demander proactively searches for suppliers.

        Args:
            demander_agent: The demander agent
            goal: The goal/requirement
            mode: Matching mode
            max_results: Maximum results
            auto_negotiate: Whether to auto-negotiate
            negotiation_strategy: Strategy for negotiation

        Returns:
            List of potential matches
        """
        str(uuid.uuid4())
        self._stats.active_searches += 1

        try:
            # Use active matching service to search
            opportunities = await self.active_matching.demander_search_suppliers(
                demander_agent=demander_agent,
                goal=goal,
                search_strategy=SearchStrategy.PROACTIVE_OUTREACH,
                max_results=max_results,
            )

            matches = []

            for opp in opportunities:
                # Create supply listing
                supply_listing = SupplyListing(
                    listing_id=str(uuid.uuid4()),
                    agent_id=opp.counterpart_agent_id,
                    agent_name=opp.counterpart_name,
                    resource=opp.details,
                    price_range={"min": opp.details.get("price_per_request", 0), "max": 10000},
                    capabilities=opp.details.get("capabilities", []),
                    reputation=opp.details.get("reputation", 1.0),
                )

                # Create demand listing
                demand_listing = DemandListing(
                    listing_id=str(uuid.uuid4()),
                    agent_id=demander_agent.id,
                    agent_name=demander_agent.name,
                    requirement=goal.to_dict(),
                    budget=goal.metadata.get("budget", {}),
                    required_capabilities=goal.metadata.get("required_skills", []),
                )

                # Create match
                match = Match(
                    match_id=str(uuid.uuid4()),
                    supply_listing=supply_listing,
                    demand_listing=demand_listing,
                    match_score=opp.match_score.overall,
                    status=MatchStatus.SEARCHING,
                )

                self._matches[match.match_id] = match
                self._stats.total_matches += 1

                if self.on_match_created:
                    self.on_match_created(match)

                # Start negotiation if auto-negotiate
                if auto_negotiate:
                    match = await self._start_negotiation(
                        match=match,
                        demander_agent=demander_agent,
                        negotiation_strategy=negotiation_strategy,
                    )

                matches.append(match)

            return matches

        finally:
            self._stats.active_searches -= 1

    async def _start_negotiation(
        self,
        match: Match,
        supplier_agent: Agent | None = None,
        demander_agent: Agent | None = None,
        negotiation_strategy: NegotiationStrategy = NegotiationStrategy.BALANCED,
    ) -> Match:
        """Start negotiation for a match."""
        match.status = MatchStatus.NEGOTIATING
        self._stats.total_negotiations += 1

        # Determine initiator
        initiator = supplier_agent or demander_agent
        counterpart_id = (
            match.demand_listing.agent_id
            if supplier_agent
            else match.supply_listing.agent_id
        )

        # Create negotiation context
        context = {
            "supply": match.supply_listing.to_dict(),
            "demand": match.demand_listing.to_dict(),
            "match_score": match.match_score,
        }

        # Initiate negotiation
        session = await self.active_matching.initiate_negotiation(
            initiator=initiator,
            counterpart_id=counterpart_id,
            context=context,
        )

        match.negotiation_session_id = session.session_id

        # Auto-negotiate
        if initiator:
            result = await self.active_matching.auto_negotiate(
                agent=initiator,
                session_id=session.session_id,
                strategy=negotiation_strategy,
            )

            if result.success:
                match.status = MatchStatus.MATCHED
                match.negotiated_terms = result.final_terms
                self._stats.successful_negotiations += 1
            else:
                match.status = MatchStatus.FAILED
                self._stats.failed_matches += 1

        return match

    # ========== Match Management ==========

    def get_match(self, match_id: str) -> Match | None:
        """Get a match by ID."""
        return self._matches.get(match_id)

    def get_agent_matches(
        self,
        agent_id: str,
        status: MatchStatus | None = None,
    ) -> list[Match]:
        """Get all matches involving an agent."""
        matches = []

        for match in self._matches.values():
            if match.supply_listing.agent_id == agent_id or match.demand_listing.agent_id == agent_id:
                if status is None or match.status == status:
                    matches.append(match)

        return matches

    async def complete_match(self, match_id: str, terms: dict[str, Any]) -> Match | None:
        """Complete a match with final terms."""
        if match_id not in self._matches:
            return None

        match = self._matches[match_id]
        match.status = MatchStatus.COMPLETED
        match.negotiated_terms = terms
        match.completed_at = time.time()

        self._stats.successful_matches += 1

        # Broadcast transaction complete
        await self.broadcast.broadcast(
            broadcast_type=BroadcastType.TRANSACTION_COMPLETE,
            sender_id="matching_service",
            sender_name="Matching Service",
            content={
                "match_id": match_id,
                "supply_agent": match.supply_listing.agent_id,
                "demand_agent": match.demand_listing.agent_id,
                "terms": terms,
            },
            scope=BroadcastScope.DIRECT,
            target_agents=[match.supply_listing.agent_id, match.demand_listing.agent_id],
        )

        if self.on_match_completed:
            self.on_match_completed(match)

        logger.info(f"Match {match_id} completed")
        return match

    async def cancel_match(self, match_id: str, reason: str = "") -> bool:
        """Cancel a match."""
        if match_id not in self._matches:
            return False

        match = self._matches[match_id]
        match.status = MatchStatus.CANCELLED
        match.metadata["cancel_reason"] = reason

        self._stats.failed_matches += 1

        logger.info(f"Match {match_id} cancelled: {reason}")
        return True

    # ========== External Agent Integration ==========

    async def search_external_agents(
        self,
        capability: str,
        protocol: ExternalAgentProtocol | None = None,
    ) -> list[ExternalAgentProfile]:
        """Search for external agents with a capability."""
        agents = self.external_adapter.find_agents_by_capability(capability)

        if protocol:
            agents = [a for a in agents if a.protocol == protocol]

        return agents

    async def call_external_agent(
        self,
        agent_id: str,
        skill_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Call a skill on an external agent."""
        response = await self.external_adapter.call_agent(
            agent_id=agent_id,
            skill_name=skill_name,
            arguments=arguments,
        )

        return response.to_dict()

    # ========== Utility Methods ==========

    def get_statistics(self) -> dict[str, Any]:
        """Get service statistics."""
        return {
            **self._stats.to_dict(),
            "active_supply_listings": sum(
                1 for l in self._supply_listings.values()
                if l.status == "active"
            ),
            "active_demand_listings": sum(
                1 for l in self._demand_listings.values()
                if l.status == "active"
            ),
            "active_matches": sum(
                1 for m in self._matches.values()
                if m.status in [MatchStatus.SEARCHING, MatchStatus.NEGOTIATING]
            ),
        }

    def cleanup_expired_listings(self) -> int:
        """Remove expired listings."""
        now = time.time()
        expired_count = 0

        # Clean supply listings
        for _listing_id, listing in list(self._supply_listings.items()):
            if listing.expires_at and now > listing.expires_at:
                listing.status = "expired"
                expired_count += 1

        # Clean demand listings
        for _listing_id, listing in list(self._demand_listings.items()):
            if listing.expires_at and now > listing.expires_at:
                listing.status = "expired"
                expired_count += 1

        return expired_count

    async def start_background_matching(
        self,
        agent: Agent,
        listing_type: str,  # "supply" or "demand"
        listing_id: str,
        interval: float = 60.0,
    ) -> str:
        """Start background matching for a listing."""
        task_id = str(uuid.uuid4())

        async def matching_loop():
            while True:
                try:
                    await asyncio.sleep(interval)

                    if listing_type == "supply":
                        listing = self._supply_listings.get(listing_id)
                        if listing and listing.status == "active":
                            # Continue searching for matching demands
                            pass

                    elif listing_type == "demand":
                        listing = self._demand_listings.get(listing_id)
                        if listing and listing.status == "active":
                            # Continue searching for matching supplies
                            pass

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Background matching error: {e}")

        task = asyncio.create_task(matching_loop())
        self._running_searches[task_id] = task

        return task_id

    def stop_background_matching(self, task_id: str) -> bool:
        """Stop a background matching task."""
        if task_id in self._running_searches:
            self._running_searches[task_id].cancel()
            del self._running_searches[task_id]
            return True
        return False
