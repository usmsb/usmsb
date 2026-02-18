"""Test configuration for pytest."""
import pytest


@pytest.fixture
def sample_agent():
    """Create a sample agent for testing."""
    from usmsb_sdk.core.elements import Agent, AgentType
    return Agent(
        name="TestAgent",
        type=AgentType.AI_AGENT,
        capabilities=["reasoning", "planning"],
    )


@pytest.fixture
def sample_environment():
    """Create a sample environment for testing."""
    from usmsb_sdk.core.elements import Environment, EnvironmentType
    return Environment(
        name="TestEnvironment",
        type=EnvironmentType.SOCIAL,
        state={"test": True},
    )


@pytest.fixture
def sample_goal():
    """Create a sample goal for testing."""
    from usmsb_sdk.core.elements import Goal
    return Goal(
        name="TestGoal",
        description="A test goal",
        priority=1,
    )
