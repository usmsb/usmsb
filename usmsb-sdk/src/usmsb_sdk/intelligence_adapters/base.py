"""
Intelligence Source Base Interfaces

This module defines the abstract interfaces for intelligence sources:
- IIntelligenceSource: Base interface for all intelligence sources
- ILLMAdapter: Large Language Model adapter interface
- IKnowledgeBaseAdapter: Knowledge base adapter interface
- IAgenticFrameworkAdapter: Agentic framework adapter interface
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class IntelligenceSourceType(str, Enum):
    """Types of intelligence sources."""
    LLM = "llm"
    KNOWLEDGE_BASE = "knowledge_base"
    AGENTIC_FRAMEWORK = "agentic_framework"
    HUMAN = "human"


class IntelligenceSourceStatus(str, Enum):
    """Status of an intelligence source."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class IntelligenceSourceConfig:
    """Configuration for an intelligence source."""
    name: str
    type: IntelligenceSourceType
    api_key: Optional[str] = None
    model: Optional[str] = None
    endpoint: Optional[str] = None
    max_retries: int = 3
    timeout: float = 30.0
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntelligenceSourceMetrics:
    """Metrics for an intelligence source."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens_used: int = 0
    total_cost: float = 0.0
    average_latency: float = 0.0
    last_request_time: Optional[float] = None


class IIntelligenceSource(ABC):
    """
    Base interface for all intelligence sources.

    All intelligence sources (LLMs, knowledge bases, agentic frameworks)
    must implement this interface.
    """

    def __init__(self, config: IntelligenceSourceConfig):
        """Initialize the intelligence source with configuration."""
        self.config = config
        self.status = IntelligenceSourceStatus.UNINITIALIZED
        self.metrics = IntelligenceSourceMetrics()

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the intelligence source.

        Returns:
            True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the intelligence source and cleanup resources."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if the intelligence source is available.

        Returns:
            True if available, False otherwise
        """
        pass

    def get_status(self) -> IntelligenceSourceStatus:
        """Get current status of the intelligence source."""
        return self.status

    def get_metrics(self) -> IntelligenceSourceMetrics:
        """Get usage metrics for the intelligence source."""
        return self.metrics

    def _record_request(
        self,
        success: bool,
        tokens: int = 0,
        cost: float = 0.0,
        latency: float = 0.0,
    ) -> None:
        """Record a request in metrics."""
        self.metrics.total_requests += 1
        if success:
            self.metrics.successful_requests += 1
        else:
            self.metrics.failed_requests += 1
        self.metrics.total_tokens_used += tokens
        self.metrics.total_cost += cost

        # Update average latency
        if self.metrics.total_requests > 1:
            self.metrics.average_latency = (
                (self.metrics.average_latency * (self.metrics.total_requests - 1) + latency)
                / self.metrics.total_requests
            )
        else:
            self.metrics.average_latency = latency


class ILLMAdapter(IIntelligenceSource):
    """
    Large Language Model Adapter Interface.

    Provides text generation, understanding, reasoning, and evaluation
    capabilities from LLM services.
    """

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: Input prompt
            context: Additional context
            **kwargs: Additional generation parameters

        Returns:
            Generated text
        """
        pass

    @abstractmethod
    async def generate_with_system(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Generate text with separate system and user prompts.

        Args:
            system_prompt: System-level instructions
            user_prompt: User input
            context: Additional context
            **kwargs: Additional generation parameters

        Returns:
            Generated text
        """
        pass

    @abstractmethod
    async def understand_intent(
        self,
        text: str,
        schema: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Understand the intent from text.

        Args:
            text: Input text to analyze
            schema: Optional schema for structured output
            context: Additional context
            **kwargs: Additional parameters

        Returns:
            Dictionary containing extracted intent and entities
        """
        pass

    @abstractmethod
    async def reason(
        self,
        facts: List[str],
        query: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Perform reasoning over facts.

        Args:
            facts: List of facts to reason over
            query: Query to answer
            context: Additional context
            **kwargs: Additional parameters

        Returns:
            Reasoning result
        """
        pass

    @abstractmethod
    async def evaluate(
        self,
        item: Any,
        criteria: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Evaluate an item against criteria.

        Args:
            item: Item to evaluate
            criteria: Evaluation criteria
            context: Additional context
            **kwargs: Additional parameters

        Returns:
            Evaluation result
        """
        pass

    @abstractmethod
    async def embed(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[float]:
        """
        Generate embeddings for text.

        Args:
            text: Text to embed
            context: Additional context
            **kwargs: Additional parameters

        Returns:
            Embedding vector
        """
        pass


class IKnowledgeBaseAdapter(IIntelligenceSource):
    """
    Knowledge Base Adapter Interface.

    Provides knowledge retrieval, fact lookup, and semantic search
    capabilities from knowledge storage systems.
    """

    @abstractmethod
    async def query_knowledge(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Query the knowledge base.

        Args:
            query: Query string
            context: Additional context
            **kwargs: Additional parameters (e.g., limit, filters)

        Returns:
            List of matching knowledge items
        """
        pass

    @abstractmethod
    async def retrieve_facts(
        self,
        entity: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[str]:
        """
        Retrieve facts about an entity.

        Args:
            entity: Entity to retrieve facts about
            context: Additional context
            **kwargs: Additional parameters

        Returns:
            List of facts about the entity
        """
        pass

    @abstractmethod
    async def semantic_search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search using embeddings.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filters: Optional filters
            context: Additional context

        Returns:
            List of matching items with similarity scores
        """
        pass

    @abstractmethod
    async def add_knowledge(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add knowledge to the knowledge base.

        Args:
            content: Content to add
            metadata: Optional metadata
            embedding: Optional pre-computed embedding
            context: Additional context

        Returns:
            ID of the added knowledge item
        """
        pass


class IAgenticFrameworkAdapter(IIntelligenceSource):
    """
    Agentic Framework Adapter Interface.

    Provides action planning, tool execution, and multi-agent coordination
    capabilities from agentic frameworks like LangChain, AutoGen.
    """

    @abstractmethod
    async def plan_action_sequence(
        self,
        goal: str,
        current_state: Dict[str, Any],
        available_tools: List[str],
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Plan a sequence of actions to achieve a goal.

        Args:
            goal: Goal to achieve
            current_state: Current state
            available_tools: List of available tools
            context: Additional context
            **kwargs: Additional parameters

        Returns:
            List of planned actions
        """
        pass

    @abstractmethod
    async def execute_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a tool.

        Args:
            tool_name: Name of the tool to execute
            params: Tool parameters
            context: Additional context
            **kwargs: Additional parameters

        Returns:
            Tool execution result
        """
        pass

    @abstractmethod
    async def coordinate_agents(
        self,
        task: str,
        agents: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Coordinate multiple agents for a task.

        Args:
            task: Task to coordinate
            agents: List of agent specifications
            context: Additional context
            **kwargs: Additional parameters

        Returns:
            Coordination result
        """
        pass

    @abstractmethod
    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: callable,
    ) -> None:
        """
        Register a tool with the framework.

        Args:
            name: Tool name
            description: Tool description
            parameters: Parameter schema
            handler: Function to handle tool execution
        """
        pass
