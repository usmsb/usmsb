"""
Marketplace Module

Manages services, demands, and matching operations.
Enables agents to publish services, post demands, and find matches.
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from usmsb_sdk.agent_sdk.platform_client import PlatformClient

logger = logging.getLogger(__name__)


class PriceType(Enum):
    """Service pricing types"""
    HOURLY = "hourly"
    FIXED = "fixed"
    PER_REQUEST = "per_request"
    MILESTONE = "milestone"


class ServiceStatus(Enum):
    """Service status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    ARCHIVED = "archived"


class DemandStatus(Enum):
    """Demand status"""
    ACTIVE = "active"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class OpportunityType(Enum):
    """Opportunity type"""
    DEMAND = "demand"
    SUPPLY = "supply"


@dataclass
class PriceRange:
    """Price range for budget or suggestions"""
    min: float
    max: float
    recommended: float | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {"min": self.min, "max": self.max}
        if self.recommended is not None:
            result["recommended"] = self.recommended
        return result


@dataclass
class MatchScore:
    """Matching score breakdown"""
    overall: float
    capability_match: float
    price_match: float
    reputation_match: float
    time_match: float
    semantic_match: float = 0.0
    suggested_price_range: PriceRange | None = None
    reasoning: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MatchScore":
        price_range = None
        if data.get("suggested_price_range"):
            pr = data["suggested_price_range"]
            price_range = PriceRange(
                min=pr.get("min", 0),
                max=pr.get("max", 0),
                recommended=pr.get("recommended"),
            )
        return cls(
            overall=data.get("overall", 0),
            capability_match=data.get("capability_match", 0),
            price_match=data.get("price_match", 0),
            reputation_match=data.get("reputation_match", 0),
            time_match=data.get("time_match", 0),
            semantic_match=data.get("semantic_match", 0),
            suggested_price_range=price_range,
            reasoning=data.get("reasoning", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        result = {
            "overall": round(self.overall, 3),
            "capability_match": round(self.capability_match, 3),
            "price_match": round(self.price_match, 3),
            "reputation_match": round(self.reputation_match, 3),
            "time_match": round(self.time_match, 3),
            "semantic_match": round(self.semantic_match, 3),
            "reasoning": self.reasoning,
        }
        if self.suggested_price_range:
            result["suggested_price_range"] = self.suggested_price_range.to_dict()
        return result


@dataclass
class ServiceDefinition:
    """Definition of a service to be published"""
    service_name: str
    description: str
    category: str
    skills: list[str]
    price: float
    price_type: str = "hourly"
    availability: str = "24/7"
    max_concurrent: int = 10
    quality_guarantees: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "service_name": self.service_name,
            "description": self.description,
            "category": self.category,
            "skills": self.skills,
            "price": self.price,
            "price_type": self.price_type,
            "availability": self.availability,
            "max_concurrent": self.max_concurrent,
            "quality_guarantees": self.quality_guarantees,
            "metadata": self.metadata,
        }


@dataclass
class Service:
    """Published service"""
    id: str
    agent_id: str
    service_name: str
    description: str
    category: str
    skills: list[str]
    price: float
    price_type: str
    availability: str
    status: str
    created_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Service":
        return cls(
            id=data.get("id", ""),
            agent_id=data.get("agent_id", ""),
            service_name=data.get("service_name", ""),
            description=data.get("description", ""),
            category=data.get("category", ""),
            skills=data.get("skills", []),
            price=data.get("price", 0),
            price_type=data.get("price_type", "hourly"),
            availability=data.get("availability", "24/7"),
            status=data.get("status", "active"),
            created_at=datetime.fromtimestamp(data["created_at"]) if data.get("created_at") else None,
        )


@dataclass
class DemandDefinition:
    """Definition of a demand/requirement to be published"""
    title: str
    description: str
    required_skills: list[str]
    budget_min: float
    budget_max: float
    category: str = ""
    deadline: datetime | None = None
    priority: str = "medium"
    quality_requirements: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "required_skills": self.required_skills,
            "budget_min": self.budget_min,
            "budget_max": self.budget_max,
            "priority": self.priority,
            "quality_requirements": self.quality_requirements,
        }
        if self.deadline:
            result["deadline"] = self.deadline.isoformat()
        return result


@dataclass
class Demand:
    """Published demand"""
    id: str
    agent_id: str
    title: str
    description: str
    category: str
    required_skills: list[str]
    budget_min: float
    budget_max: float
    priority: str
    status: str
    deadline: datetime | None = None
    created_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Demand":
        return cls(
            id=data.get("id", ""),
            agent_id=data.get("agent_id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            category=data.get("category", ""),
            required_skills=data.get("required_skills", []),
            budget_min=data.get("budget_min", 0),
            budget_max=data.get("budget_max", 0),
            priority=data.get("priority", "medium"),
            status=data.get("status", "active"),
            deadline=datetime.fromisoformat(data["deadline"]) if data.get("deadline") else None,
            created_at=datetime.fromtimestamp(data["created_at"]) if data.get("created_at") else None,
        )


@dataclass
class Opportunity:
    """A matching business opportunity"""
    opportunity_id: str
    type: str  # demand or supply
    counterpart_id: str
    counterpart_name: str
    details: dict[str, Any]
    match_score: MatchScore
    status: str
    created_at: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Opportunity":
        score_data = data.get("match_score", {})
        return cls(
            opportunity_id=data.get("opportunity_id", ""),
            type=data.get("opportunity_type", "demand"),
            counterpart_id=data.get("counterpart_agent_id", ""),
            counterpart_name=data.get("counterpart_name", "Unknown"),
            details=data.get("details", {}),
            match_score=MatchScore.from_dict(score_data),
            status=data.get("status", "discovered"),
            created_at=data.get("created_at"),
        )


class MarketplaceManager:
    """
    Manages marketplace operations for an agent.

    Features:
    - Service publishing and management
    - Demand posting and management
    - Opportunity discovery and matching
    - Price suggestions and negotiations
    """

    def __init__(
        self,
        platform_client: PlatformClient,
        logger: logging.Logger | None = None,
    ):
        self._platform = platform_client
        self.logger = logger or logging.getLogger(__name__)

        # Local caches
        self._my_services: dict[str, Service] = {}
        self._my_demands: dict[str, Demand] = {}
        self._opportunity_watchers: list[Callable] = []

    # ==================== Service Management ====================

    async def publish_service(
        self,
        service_def: ServiceDefinition,
    ) -> Service | None:
        """
        Publish a service to the marketplace.

        Args:
            service_def: Service definition

        Returns:
            Published Service object or None on failure
        """
        response = await self._platform.publish_service(
            service_name=service_def.service_name,
            service_type=service_def.category,
            capabilities=service_def.skills,
            price=service_def.price,
            description=service_def.description,
            price_type=service_def.price_type,
            availability=service_def.availability,
        )

        if response.success and response.data:
            service = Service.from_dict(response.data.get("service", response.data))
            self._my_services[service.id] = service
            self.logger.info(f"Service published: {service.service_name} (ID: {service.id})")
            return service

        self.logger.error(f"Failed to publish service: {response.error}")
        return None

    async def list_services(
        self,
        category: str | None = None,
        agent_id: str | None = None,
        limit: int = 100,
    ) -> list[Service]:
        """
        List services on the marketplace.

        Args:
            category: Filter by category
            agent_id: Filter by agent
            limit: Maximum results

        Returns:
            List of Service objects
        """
        response = await self._platform.list_services(
            agent_id=agent_id,
            category=category,
            limit=limit,
        )

        if response.success and response.data:
            return [Service.from_dict(s) for s in response.data]
        return []

    async def list_my_services(self) -> list[Service]:
        """List all services published by this agent"""
        return list(self._my_services.values())

    async def update_service(
        self,
        service_id: str,
        **updates,
    ) -> bool:
        """
        Update a service.

        Args:
            service_id: Service ID
            **updates: Fields to update (price, availability, etc.)
        """
        # TODO: Implement when platform API supports it
        self.logger.warning("Service update not yet implemented in platform API")
        return False

    async def unpublish_service(self, service_id: str) -> bool:
        """Remove a service from the marketplace"""
        # TODO: Implement when platform API supports it
        if service_id in self._my_services:
            del self._my_services[service_id]
            return True
        return False

    # ==================== Demand Management ====================

    async def publish_demand(
        self,
        demand_def: DemandDefinition,
    ) -> Demand | None:
        """
        Publish a demand to the marketplace.

        Args:
            demand_def: Demand definition

        Returns:
            Published Demand object or None on failure
        """
        response = await self._platform.publish_demand(
            title=demand_def.title,
            description=demand_def.description,
            required_skills=demand_def.required_skills,
            budget_min=demand_def.budget_min,
            budget_max=demand_def.budget_max,
            category=demand_def.category,
            deadline=demand_def.deadline.isoformat() if demand_def.deadline else None,
            priority=demand_def.priority,
            quality_requirements=demand_def.quality_requirements,
        )

        if response.success and response.data:
            demand = Demand.from_dict(response.data)
            self._my_demands[demand.id] = demand
            self.logger.info(f"Demand published: {demand.title} (ID: {demand.id})")
            return demand

        self.logger.error(f"Failed to publish demand: {response.error}")
        return None

    async def list_demands(
        self,
        category: str | None = None,
        agent_id: str | None = None,
        limit: int = 100,
    ) -> list[Demand]:
        """
        List demands on the marketplace.

        Args:
            category: Filter by category
            agent_id: Filter by agent
            limit: Maximum results

        Returns:
            List of Demand objects
        """
        response = await self._platform.list_demands(
            agent_id=agent_id,
            category=category,
            limit=limit,
        )

        if response.success and response.data:
            return [Demand.from_dict(d) for d in response.data]
        return []

    async def list_my_demands(self) -> list[Demand]:
        """List all demands published by this agent"""
        return list(self._my_demands.values())

    async def cancel_demand(self, demand_id: str) -> bool:
        """Cancel a demand"""
        response = await self._platform.cancel_demand(demand_id)

        if response.success:
            if demand_id in self._my_demands:
                self._my_demands[demand_id].status = "cancelled"
            self.logger.info(f"Demand cancelled: {demand_id}")
            return True
        return False

    # ==================== Matching ====================

    async def find_opportunities(
        self,
        as_supplier: bool = True,
        capabilities: list[str] | None = None,
        budget_range: tuple | None = None,
    ) -> list[Opportunity]:
        """
        Find matching opportunities.

        Args:
            as_supplier: True to find demands (as supplier), False to find suppliers
            capabilities: Filter by capabilities
            budget_range: (min, max) budget filter

        Returns:
            List of matching opportunities
        """
        if as_supplier:
            response = await self._platform.search_demands(
                capabilities=capabilities,
                budget_min=budget_range[0] if budget_range else None,
                budget_max=budget_range[1] if budget_range else None,
            )
        else:
            response = await self._platform.search_suppliers(
                required_skills=capabilities or [],
                budget_min=budget_range[0] if budget_range else None,
                budget_max=budget_range[1] if budget_range else None,
            )

        if response.success and response.data:
            return [Opportunity.from_dict(o) for o in response.data]
        return []

    async def get_opportunity(self, opportunity_id: str) -> Opportunity | None:
        """Get a specific opportunity by ID"""
        opportunities = await self.get_all_opportunities()
        for opp in opportunities:
            if opp.opportunity_id == opportunity_id:
                return opp
        return None

    async def get_all_opportunities(self) -> list[Opportunity]:
        """Get all opportunities for this agent"""
        response = await self._platform.get_opportunities()

        if response.success and response.data:
            return [Opportunity.from_dict(o) for o in response.data]
        return []

    async def get_matching_stats(self) -> dict[str, Any]:
        """Get matching statistics"""
        response = await self._platform.get_matching_stats()

        if response.success and response.data:
            return response.data
        return {}

    # ==================== Opportunity Watching ====================

    async def watch_opportunities(
        self,
        callback: Callable[[list[Opportunity]], None],
        interval: float = 60.0,
        as_supplier: bool = True,
    ) -> asyncio.Task:
        """
        Watch for new opportunities and call callback when found.

        Args:
            callback: Function to call with new opportunities
            interval: Check interval in seconds
            as_supplier: True to watch demands, False to watch suppliers

        Returns:
            asyncio.Task that can be cancelled to stop watching
        """
        seen_ids = set()

        async def watch_loop():
            while True:
                try:
                    opportunities = await self.find_opportunities(as_supplier=as_supplier)
                    new_opps = [o for o in opportunities if o.opportunity_id not in seen_ids]

                    if new_opps:
                        for opp in new_opps:
                            seen_ids.add(opp.opportunity_id)
                        await callback(new_opps)

                    await asyncio.sleep(interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in opportunity watch: {e}")
                    await asyncio.sleep(interval)

        return asyncio.create_task(watch_loop())

    # ==================== Price Suggestions ====================

    def suggest_price(
        self,
        match_score: MatchScore,
    ) -> PriceRange:
        """
        Get suggested price range from a match score.

        Args:
            match_score: Match score with suggested price

        Returns:
            PriceRange with suggestions
        """
        if match_score.suggested_price_range:
            return match_score.suggested_price_range

        # Fallback: estimate from match score
        if match_score.overall >= 0.8:
            # High match - can charge premium
            return PriceRange(min=80, max=150, recommended=100)
        elif match_score.overall >= 0.5:
            # Medium match - competitive pricing
            return PriceRange(min=50, max=100, recommended=75)
        else:
            # Low match - budget pricing
            return PriceRange(min=30, max=60, recommended=45)

    # ==================== Convenience Methods ====================

    async def find_work(self, capabilities: list[str] | None = None) -> list[Opportunity]:
        """
        Find work opportunities matching agent's capabilities.
        Shorthand for find_opportunities(as_supplier=True)
        """
        return await self.find_opportunities(as_supplier=True, capabilities=capabilities)

    async def find_workers(
        self,
        required_skills: list[str],
        budget_range: tuple | None = None,
    ) -> list[Opportunity]:
        """
        Find workers/suppliers for a task.
        Shorthand for find_opportunities(as_supplier=False)
        """
        return await self.find_opportunities(
            as_supplier=False,
            capabilities=required_skills,
            budget_range=budget_range,
        )
