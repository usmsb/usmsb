"""
Intelligence Source Manager

Manages and orchestrates multiple intelligence sources (LLMs, knowledge bases,
agentic frameworks) providing unified access, load balancing, and failover.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from usmsb_sdk.intelligence_adapters.base import (
    IAgenticFrameworkAdapter,
    IIntelligenceSource,
    IKnowledgeBaseAdapter,
    ILLMAdapter,
    IntelligenceSourceStatus,
    IntelligenceSourceType,
)

logger = logging.getLogger(__name__)


class SelectionStrategy(StrEnum):
    """Strategy for selecting among multiple intelligence sources."""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    RANDOM = "random"
    PRIORITY = "priority"
    COST_OPTIMIZED = "cost_optimized"


@dataclass
class SourceRegistration:
    """Registration information for an intelligence source."""
    source: IIntelligenceSource
    name: str
    type: IntelligenceSourceType
    priority: int = 0
    is_primary: bool = False
    is_fallback: bool = False
    tags: list[str] = field(default_factory=list)


class IntelligenceSourceManager:
    """
    Intelligence Source Manager.

    Manages multiple intelligence sources and provides:
    - Unified access to different source types
    - Source selection based on strategy
    - Load balancing and failover
    - Health monitoring
    """

    def __init__(
        self,
        selection_strategy: SelectionStrategy = SelectionStrategy.PRIORITY,
        health_check_interval: float = 60.0,
    ):
        """
        Initialize the Intelligence Source Manager.

        Args:
            selection_strategy: Strategy for source selection
            health_check_interval: Interval for health checks in seconds
        """
        self.selection_strategy = selection_strategy
        self.health_check_interval = health_check_interval

        self._sources: dict[str, SourceRegistration] = {}
        self._llm_sources: list[str] = []
        self._knowledge_sources: list[str] = []
        self._agentic_sources: list[str] = []
        self._round_robin_index = 0

        self._on_source_failure: Callable[[str, Exception], None] | None = None
        self._on_source_recovery: Callable[[str], None] | None = None

    async def register_source(
        self,
        name: str,
        source: IIntelligenceSource,
        priority: int = 0,
        is_primary: bool = False,
        is_fallback: bool = False,
        tags: list[str] | None = None,
    ) -> bool:
        """
        Register an intelligence source.

        Args:
            name: Unique name for the source
            source: The intelligence source instance
            priority: Priority for selection (higher = more important)
            is_primary: Whether this is a primary source
            is_fallback: Whether this is a fallback source
            tags: Optional tags for filtering

        Returns:
            True if registration successful
        """
        if name in self._sources:
            logger.warning(f"Source '{name}' already registered, replacing")

        # Initialize the source if not already initialized
        if source.status == IntelligenceSourceStatus.UNINITIALIZED:
            success = await source.initialize()
            if not success:
                logger.error(f"Failed to initialize source '{name}'")
                return False

        registration = SourceRegistration(
            source=source,
            name=name,
            type=source.config.type,
            priority=priority,
            is_primary=is_primary,
            is_fallback=is_fallback,
            tags=tags or [],
        )

        self._sources[name] = registration

        # Categorize by type
        if isinstance(source, ILLMAdapter):
            self._llm_sources.append(name)
        if isinstance(source, IKnowledgeBaseAdapter):
            self._knowledge_sources.append(name)
        if isinstance(source, IAgenticFrameworkAdapter):
            self._agentic_sources.append(name)

        logger.info(f"Registered intelligence source: {name} (type: {source.config.type.value})")
        return True

    async def unregister_source(self, name: str) -> bool:
        """
        Unregister an intelligence source.

        Args:
            name: Name of the source to unregister

        Returns:
            True if unregistration successful
        """
        if name not in self._sources:
            return False

        registration = self._sources[name]

        # Shutdown the source
        await registration.source.shutdown()

        # Remove from registries
        del self._sources[name]
        if name in self._llm_sources:
            self._llm_sources.remove(name)
        if name in self._knowledge_sources:
            self._knowledge_sources.remove(name)
        if name in self._agentic_sources:
            self._agentic_sources.remove(name)

        logger.info(f"Unregistered intelligence source: {name}")
        return True

    def get_llm(self, name: str | None = None) -> ILLMAdapter | None:
        """
        Get an LLM adapter.

        Args:
            name: Specific source name, or None for auto-selection

        Returns:
            LLM adapter or None if not available
        """
        if name:
            if name in self._sources and isinstance(self._sources[name].source, ILLMAdapter):
                return self._sources[name].source
            return None

        # Auto-select based on strategy
        selected_name = self._select_source(self._llm_sources)
        if selected_name:
            return self._sources[selected_name].source
        return None

    def get_knowledge_base(self, name: str | None = None) -> IKnowledgeBaseAdapter | None:
        """
        Get a knowledge base adapter.

        Args:
            name: Specific source name, or None for auto-selection

        Returns:
            Knowledge base adapter or None if not available
        """
        if name:
            if name in self._sources and isinstance(self._sources[name].source, IKnowledgeBaseAdapter):
                return self._sources[name].source
            return None

        selected_name = self._select_source(self._knowledge_sources)
        if selected_name:
            return self._sources[selected_name].source
        return None

    def get_agentic_framework(self, name: str | None = None) -> IAgenticFrameworkAdapter | None:
        """
        Get an agentic framework adapter.

        Args:
            name: Specific source name, or None for auto-selection

        Returns:
            Agentic framework adapter or None if not available
        """
        if name:
            if name in self._sources and isinstance(self._sources[name].source, IAgenticFrameworkAdapter):
                return self._sources[name].source
            return None

        selected_name = self._select_source(self._agentic_sources)
        if selected_name:
            return self._sources[selected_name].source
        return None

    def _select_source(self, source_names: list[str]) -> str | None:
        """Select a source based on the configured strategy."""
        if not source_names:
            return None

        # Filter available sources
        available = [
            name for name in source_names
            if self._sources[name].source.status == IntelligenceSourceStatus.READY
        ]

        if not available:
            # Try fallback sources
            fallbacks = [
                name for name in source_names
                if self._sources[name].is_fallback
            ]
            if fallbacks:
                return fallbacks[0]
            return None

        if len(available) == 1:
            return available[0]

        if self.selection_strategy == SelectionStrategy.ROUND_ROBIN:
            self._round_robin_index = (self._round_robin_index + 1) % len(available)
            return available[self._round_robin_index]

        elif self.selection_strategy == SelectionStrategy.LEAST_LOADED:
            # Select source with lowest total requests
            return min(
                available,
                key=lambda n: self._sources[n].source.metrics.total_requests
            )

        elif self.selection_strategy == SelectionStrategy.PRIORITY:
            # Select highest priority source
            return max(available, key=lambda n: self._sources[n].priority)

        elif self.selection_strategy == SelectionStrategy.RANDOM:
            import random
            return random.choice(available)

        elif self.selection_strategy == SelectionStrategy.COST_OPTIMIZED:
            # Select source with lowest average cost
            return min(
                available,
                key=lambda n: self._sources[n].source.metrics.total_cost /
                              max(self._sources[n].source.metrics.total_requests, 1)
            )

        return available[0]

    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check on all sources.

        Returns:
            Health status for each source
        """
        results = {}
        for name, registration in self._sources.items():
            is_available = await registration.source.is_available()
            results[name] = {
                "status": registration.source.status.value,
                "available": is_available,
                "metrics": {
                    "total_requests": registration.source.metrics.total_requests,
                    "success_rate": (
                        registration.source.metrics.successful_requests /
                        max(registration.source.metrics.total_requests, 1)
                    ),
                    "average_latency": registration.source.metrics.average_latency,
                }
            }
        return results

    async def shutdown_all(self) -> None:
        """Shutdown all registered sources."""
        for name in list(self._sources.keys()):
            await self.unregister_source(name)
        logger.info("All intelligence sources shut down")

    def get_source_names(self, source_type: IntelligenceSourceType | None = None) -> list[str]:
        """
        Get names of registered sources.

        Args:
            source_type: Filter by type, or None for all

        Returns:
            List of source names
        """
        if source_type is None:
            return list(self._sources.keys())

        return [
            name for name, reg in self._sources.items()
            if reg.type == source_type
        ]

    def get_metrics(self) -> dict[str, Any]:
        """Get aggregated metrics for all sources."""
        total_requests = 0
        total_successful = 0
        total_failed = 0
        total_cost = 0.0
        total_tokens = 0

        for registration in self._sources.values():
            metrics = registration.source.metrics
            total_requests += metrics.total_requests
            total_successful += metrics.successful_requests
            total_failed += metrics.failed_requests
            total_cost += metrics.total_cost
            total_tokens += metrics.total_tokens_used

        return {
            "total_sources": len(self._sources),
            "llm_sources": len(self._llm_sources),
            "knowledge_sources": len(self._knowledge_sources),
            "agentic_sources": len(self._agentic_sources),
            "total_requests": total_requests,
            "successful_requests": total_successful,
            "failed_requests": total_failed,
            "success_rate": total_successful / max(total_requests, 1),
            "total_cost": total_cost,
            "total_tokens": total_tokens,
        }
