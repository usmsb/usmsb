"""
USMSB Manager

The main entry point for the USMSB SDK.
Provides unified access to all SDK components and services.
"""

import logging
import os
from typing import Any

from usmsb_sdk.config.settings import Settings, get_settings
from usmsb_sdk.core.elements import Agent, Environment
from usmsb_sdk.intelligence_adapters.base import (
    IAgenticFrameworkAdapter,
    IIntelligenceSource,
    IKnowledgeBaseAdapter,
    ILLMAdapter,
    IntelligenceSourceConfig,
    IntelligenceSourceType,
)
from usmsb_sdk.intelligence_adapters.llm.openai_adapter import OpenAIAdapter
from usmsb_sdk.intelligence_adapters.manager import (
    IntelligenceSourceManager,
    SelectionStrategy,
)
from usmsb_sdk.services.agentic_workflow_service import AgenticWorkflowService
from usmsb_sdk.services.behavior_prediction_service import BehaviorPredictionService

logger = logging.getLogger(__name__)


class USMSBManager:
    """
    USMSB SDK Manager.

    The primary entry point for using the USMSB SDK.
    Handles initialization, configuration, and provides access to services.

    Example:
        ```python
        from usmsb_sdk import USMSBManager, AgentBuilder

        async def main():
            # Initialize SDK
            sdk = USMSBManager(config_path="./config.yaml")
            await sdk.initialize()

            # Create an agent
            agent = (AgentBuilder()
                .with_name("MyAgent")
                .with_type("ai_agent")
                .with_capabilities(["reasoning", "planning"])
                .build())

            # Get prediction service
            prediction_service = sdk.get_service("behavior_prediction")
            prediction = await prediction_service.predict_agent_behavior(agent, environment)

            # Cleanup
            await sdk.shutdown()
        ```
    """

    def __init__(
        self,
        config_path: str | None = None,
        settings: Settings | None = None,
        **kwargs,
    ):
        """
        Initialize the USMSB Manager.

        Args:
            config_path: Path to configuration file (YAML or JSON)
            settings: Pre-configured Settings instance
            **kwargs: Additional configuration overrides
        """
        self._settings = settings or get_settings()
        self._config_path = config_path
        self._config_overrides = kwargs

        self._initialized = False
        self._source_manager: IntelligenceSourceManager | None = None
        self._services: dict[str, Any] = {}

        # Registries
        self._agents: dict[str, Agent] = {}
        self._environments: dict[str, Environment] = {}

    async def initialize(self) -> bool:
        """
        Initialize the SDK.

        Loads configuration, initializes intelligence sources, and sets up services.

        Returns:
            True if initialization successful
        """
        if self._initialized:
            logger.warning("USMSBManager already initialized")
            return True

        try:
            logger.info("Initializing USMSB SDK...")

            # Initialize intelligence source manager
            self._source_manager = IntelligenceSourceManager(
                selection_strategy=SelectionStrategy.PRIORITY,
            )

            # Register default LLM adapter
            await self._register_default_llm()

            # Initialize services
            await self._initialize_services()

            self._initialized = True
            logger.info("USMSB SDK initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize USMSB SDK: {e}")
            return False

    async def _register_default_llm(self) -> None:
        """Register the default LLM adapter based on configuration."""
        llm_config = self._settings.llm

        if not llm_config.api_key:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("No LLM API key configured. Some features will be unavailable.")
                return
            llm_config.api_key = api_key

        config = IntelligenceSourceConfig(
            name="openai",
            type=IntelligenceSourceType.LLM,
            api_key=llm_config.api_key,
            model=llm_config.model,
            extra_params={
                "temperature": llm_config.temperature,
                "max_tokens": llm_config.max_tokens,
                "timeout": llm_config.timeout,
            },
        )

        adapter = OpenAIAdapter(config)
        await self._source_manager.register_source(
            name="openai",
            source=adapter,
            priority=1,
            is_primary=True,
        )
        logger.info(f"Registered LLM adapter: {config.model}")

    async def _initialize_services(self) -> None:
        """Initialize application services."""
        llm = self._source_manager.get_llm()

        if llm:
            self._services["behavior_prediction"] = BehaviorPredictionService(llm)
            self._services["agentic_workflow"] = AgenticWorkflowService(llm)
            logger.info("Initialized application services")

    def get_service(self, name: str) -> Any | None:
        """
        Get a service by name.

        Args:
            name: Service name

        Returns:
            Service instance or None if not found
        """
        return self._services.get(name)

    def get_llm(self, name: str | None = None) -> ILLMAdapter | None:
        """
        Get an LLM adapter.

        Args:
            name: Specific adapter name, or None for default

        Returns:
            LLM adapter or None
        """
        if not self._source_manager:
            return None
        return self._source_manager.get_llm(name)

    def get_knowledge_base(self, name: str | None = None) -> IKnowledgeBaseAdapter | None:
        """Get a knowledge base adapter."""
        if not self._source_manager:
            return None
        return self._source_manager.get_knowledge_base(name)

    def get_agentic_framework(self, name: str | None = None) -> IAgenticFrameworkAdapter | None:
        """Get an agentic framework adapter."""
        if not self._source_manager:
            return None
        return self._source_manager.get_agentic_framework(name)

    async def register_intelligence_source(
        self,
        name: str,
        source: IIntelligenceSource,
        priority: int = 0,
        is_primary: bool = False,
        is_fallback: bool = False,
    ) -> bool:
        """
        Register an intelligence source.

        Args:
            name: Unique name for the source
            source: The intelligence source instance
            priority: Priority for selection
            is_primary: Whether this is a primary source
            is_fallback: Whether this is a fallback source

        Returns:
            True if registration successful
        """
        if not self._source_manager:
            logger.error("Source manager not initialized")
            return False

        return await self._source_manager.register_source(
            name=name,
            source=source,
            priority=priority,
            is_primary=is_primary,
            is_fallback=is_fallback,
        )

    def register_agent(self, agent: Agent) -> None:
        """Register an agent with the manager."""
        self._agents[agent.id] = agent

    def get_agent(self, agent_id: str) -> Agent | None:
        """Get a registered agent by ID."""
        return self._agents.get(agent_id)

    def list_agents(self) -> list[Agent]:
        """List all registered agents."""
        return list(self._agents.values())

    def register_environment(self, environment: Environment) -> None:
        """Register an environment with the manager."""
        self._environments[environment.id] = environment

    def get_environment(self, env_id: str) -> Environment | None:
        """Get a registered environment by ID."""
        return self._environments.get(env_id)

    def list_environments(self) -> list[Environment]:
        """List all registered environments."""
        return list(self._environments.values())

    @property
    def settings(self) -> Settings:
        """Get the current settings."""
        return self._settings

    @property
    def is_initialized(self) -> bool:
        """Check if the SDK is initialized."""
        return self._initialized

    async def health_check(self) -> dict[str, Any]:
        """
        Perform a health check.

        Returns:
            Health status information
        """
        status = {
            "initialized": self._initialized,
            "agents_count": len(self._agents),
            "environments_count": len(self._environments),
            "services": list(self._services.keys()),
        }

        if self._source_manager:
            status["intelligence_sources"] = await self._source_manager.health_check()
            status["metrics"] = self._source_manager.get_metrics()

        return status

    async def shutdown(self) -> None:
        """Shutdown the SDK and cleanup resources."""
        if not self._initialized:
            return

        logger.info("Shutting down USMSB SDK...")

        # Clear registries
        self._agents.clear()
        self._environments.clear()

        # Shutdown services
        self._services.clear()

        # Shutdown intelligence sources
        if self._source_manager:
            await self._source_manager.shutdown_all()

        self._initialized = False
        logger.info("USMSB SDK shutdown complete")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()
        return False
