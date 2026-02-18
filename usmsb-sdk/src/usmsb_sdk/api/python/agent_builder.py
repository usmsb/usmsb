"""
Agent Builder

Fluent API for creating and configuring Agent instances.
"""

from typing import Any, Dict, List, Optional

from usmsb_sdk.core.elements import Agent, AgentType, Goal, Resource, Rule


class AgentBuilder:
    """
    Fluent builder for creating Agent instances.

    Provides a convenient chainable API for configuring agents.

    Example:
        ```python
        agent = (AgentBuilder()
            .with_id("agent_001")
            .with_name("TradingBot")
            .with_type("ai_agent")
            .with_capabilities(["market_analysis", "trade_execution"])
            .with_goal("Maximize profit")
            .with_resource("capital", 10000.0, "financial")
            .build())
        ```
    """

    def __init__(self):
        """Initialize the builder with default values."""
        self._id: Optional[str] = None
        self._name: str = "Agent"
        self._type: AgentType = AgentType.AI_AGENT
        self._capabilities: List[str] = []
        self._state: Dict[str, Any] = {}
        self._goals: List[Goal] = []
        self._resources: List[Resource] = []
        self._rules: List[Rule] = []
        self._metadata: Dict[str, Any] = {}

    def with_id(self, agent_id: str) -> "AgentBuilder":
        """
        Set the agent ID.

        Args:
            agent_id: Unique identifier for the agent

        Returns:
            Self for chaining
        """
        self._id = agent_id
        return self

    def with_name(self, name: str) -> "AgentBuilder":
        """
        Set the agent name.

        Args:
            name: Display name for the agent

        Returns:
            Self for chaining
        """
        self._name = name
        return self

    def with_type(self, agent_type: str) -> "AgentBuilder":
        """
        Set the agent type.

        Args:
            agent_type: Type of agent ("human", "ai_agent", "organization", "system")

        Returns:
            Self for chaining
        """
        if isinstance(agent_type, str):
            agent_type = AgentType(agent_type)
        self._type = agent_type
        return self

    def with_capabilities(self, capabilities: List[str]) -> "AgentBuilder":
        """
        Set the agent capabilities.

        Args:
            capabilities: List of capability names

        Returns:
            Self for chaining
        """
        self._capabilities = capabilities.copy()
        return self

    def add_capability(self, capability: str) -> "AgentBuilder":
        """
        Add a single capability.

        Args:
            capability: Capability name to add

        Returns:
            Self for chaining
        """
        if capability not in self._capabilities:
            self._capabilities.append(capability)
        return self

    def with_state(self, state: Dict[str, Any]) -> "AgentBuilder":
        """
        Set the agent state.

        Args:
            state: Dictionary of state values

        Returns:
            Self for chaining
        """
        self._state = state.copy()
        return self

    def add_state(self, key: str, value: Any) -> "AgentBuilder":
        """
        Add a state value.

        Args:
            key: State key
            value: State value

        Returns:
            Self for chaining
        """
        self._state[key] = value
        return self

    def with_goal(self, goal: Goal) -> "AgentBuilder":
        """
        Add a goal object.

        Args:
            goal: Goal instance to add

        Returns:
            Self for chaining
        """
        self._goals.append(goal)
        return self

    def add_goal(
        self,
        name: str,
        description: str = "",
        priority: int = 0,
    ) -> "AgentBuilder":
        """
        Add a goal by specifying its attributes.

        Args:
            name: Goal name
            description: Goal description
            priority: Goal priority

        Returns:
            Self for chaining
        """
        goal = Goal(
            name=name,
            description=description,
            priority=priority,
        )
        self._goals.append(goal)
        return self

    def with_resource(self, resource: Resource) -> "AgentBuilder":
        """
        Add a resource object.

        Args:
            resource: Resource instance to add

        Returns:
            Self for chaining
        """
        self._resources.append(resource)
        return self

    def add_resource(
        self,
        name: str,
        quantity: float,
        resource_type: str = "tangible",
        unit: Optional[str] = None,
    ) -> "AgentBuilder":
        """
        Add a resource by specifying its attributes.

        Args:
            name: Resource name
            quantity: Resource quantity
            resource_type: Type of resource
            unit: Unit of measurement

        Returns:
            Self for chaining
        """
        from usmsb_sdk.core.elements import ResourceType
        try:
            rtype = ResourceType(resource_type)
        except ValueError:
            rtype = ResourceType.TANGIBLE

        resource = Resource(
            name=name,
            quantity=quantity,
            type=rtype,
            unit=unit,
        )
        self._resources.append(resource)
        return self

    def with_rule(self, rule: Rule) -> "AgentBuilder":
        """
        Add a rule object.

        Args:
            rule: Rule instance to add

        Returns:
            Self for chaining
        """
        self._rules.append(rule)
        return self

    def add_rule(
        self,
        name: str,
        description: str,
        rule_type: str = "social",
    ) -> "AgentBuilder":
        """
        Add a rule by specifying its attributes.

        Args:
            name: Rule name
            description: Rule description
            rule_type: Type of rule

        Returns:
            Self for chaining
        """
        from usmsb_sdk.core.elements import RuleType
        try:
            rtype = RuleType(rule_type)
        except ValueError:
            rtype = RuleType.SOCIAL

        rule = Rule(
            name=name,
            description=description,
            type=rtype,
        )
        self._rules.append(rule)
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> "AgentBuilder":
        """
        Set the agent metadata.

        Args:
            metadata: Dictionary of metadata

        Returns:
            Self for chaining
        """
        self._metadata = metadata.copy()
        return self

    def add_metadata(self, key: str, value: Any) -> "AgentBuilder":
        """
        Add a metadata value.

        Args:
            key: Metadata key
            value: Metadata value

        Returns:
            Self for chaining
        """
        self._metadata[key] = value
        return self

    def build(self) -> Agent:
        """
        Build the Agent instance.

        Returns:
            Configured Agent instance
        """
        agent = Agent(
            id=self._id,
            name=self._name,
            type=self._type,
            capabilities=self._capabilities,
            state=self._state,
            goals=self._goals,
            resources=self._resources,
            rules=self._rules,
            metadata=self._metadata,
        )
        return agent

    @classmethod
    def from_agent(cls, agent: Agent) -> "AgentBuilder":
        """
        Create a builder from an existing agent.

        Args:
            agent: Existing agent to copy

        Returns:
            Builder configured with the agent's values
        """
        builder = cls()
        builder._id = agent.id
        builder._name = agent.name
        builder._type = agent.type
        builder._capabilities = agent.capabilities.copy()
        builder._state = agent.state.copy()
        builder._goals = agent.goals.copy()
        builder._resources = agent.resources.copy()
        builder._rules = agent.rules.copy()
        builder._metadata = agent.metadata.copy()
        return builder
