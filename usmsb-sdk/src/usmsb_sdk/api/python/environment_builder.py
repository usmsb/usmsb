"""
Environment Builder

Fluent API for creating and configuring Environment instances.
"""

from typing import Any, Dict, List, Optional

from usmsb_sdk.core.elements import Environment, EnvironmentType


class EnvironmentBuilder:
    """
    Fluent builder for creating Environment instances.

    Provides a convenient chainable API for configuring environments.

    Example:
        ```python
        environment = (EnvironmentBuilder()
            .with_id("env_001")
            .with_name("Stock Market")
            .with_type("economic")
            .with_state("market_trend", "bullish")
            .with_state("volatility", 0.25)
            .build())
        ```
    """

    def __init__(self):
        """Initialize the builder with default values."""
        self._id: Optional[str] = None
        self._name: str = "Environment"
        self._type: EnvironmentType = EnvironmentType.SOCIAL
        self._state: Dict[str, Any] = {}
        self._influencing_factors: List[str] = []
        self._constraints: Dict[str, Any] = {}
        self._metadata: Dict[str, Any] = {}

    def with_id(self, env_id: str) -> "EnvironmentBuilder":
        """
        Set the environment ID.

        Args:
            env_id: Unique identifier for the environment

        Returns:
            Self for chaining
        """
        self._id = env_id
        return self

    def with_name(self, name: str) -> "EnvironmentBuilder":
        """
        Set the environment name.

        Args:
            name: Display name for the environment

        Returns:
            Self for chaining
        """
        self._name = name
        return self

    def with_type(self, env_type: str) -> "EnvironmentBuilder":
        """
        Set the environment type.

        Args:
            env_type: Type of environment
                ("natural", "social", "technological", "economic", "virtual")

        Returns:
            Self for chaining
        """
        if isinstance(env_type, str):
            env_type = EnvironmentType(env_type)
        self._type = env_type
        return self

    def with_state(self, state: Dict[str, Any]) -> "EnvironmentBuilder":
        """
        Set the environment state.

        Args:
            state: Dictionary of state values

        Returns:
            Self for chaining
        """
        self._state = state.copy()
        return self

    def add_state(self, key: str, value: Any) -> "EnvironmentBuilder":
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

    def with_influencing_factors(self, factors: List[str]) -> "EnvironmentBuilder":
        """
        Set the influencing factors.

        Args:
            factors: List of factors that influence the environment

        Returns:
            Self for chaining
        """
        self._influencing_factors = factors.copy()
        return self

    def add_influencing_factor(self, factor: str) -> "EnvironmentBuilder":
        """
        Add an influencing factor.

        Args:
            factor: Factor to add

        Returns:
            Self for chaining
        """
        if factor not in self._influencing_factors:
            self._influencing_factors.append(factor)
        return self

    def with_constraints(self, constraints: Dict[str, Any]) -> "EnvironmentBuilder":
        """
        Set the environment constraints.

        Args:
            constraints: Dictionary of constraints

        Returns:
            Self for chaining
        """
        self._constraints = constraints.copy()
        return self

    def add_constraint(self, key: str, value: Any) -> "EnvironmentBuilder":
        """
        Add a constraint.

        Args:
            key: Constraint key
            value: Constraint value

        Returns:
            Self for chaining
        """
        self._constraints[key] = value
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> "EnvironmentBuilder":
        """
        Set the environment metadata.

        Args:
            metadata: Dictionary of metadata

        Returns:
            Self for chaining
        """
        self._metadata = metadata.copy()
        return self

    def add_metadata(self, key: str, value: Any) -> "EnvironmentBuilder":
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

    def build(self) -> Environment:
        """
        Build the Environment instance.

        Returns:
            Configured Environment instance
        """
        environment = Environment(
            id=self._id,
            name=self._name,
            type=self._type,
            state=self._state,
            influencing_factors=self._influencing_factors,
            constraints=self._constraints,
            metadata=self._metadata,
        )
        return environment

    @classmethod
    def from_environment(cls, environment: Environment) -> "EnvironmentBuilder":
        """
        Create a builder from an existing environment.

        Args:
            environment: Existing environment to copy

        Returns:
            Builder configured with the environment's values
        """
        builder = cls()
        builder._id = environment.id
        builder._name = environment.name
        builder._type = environment.type
        builder._state = environment.state.copy()
        builder._influencing_factors = environment.influencing_factors.copy()
        builder._constraints = environment.constraints.copy()
        builder._metadata = environment.metadata.copy()
        return builder
