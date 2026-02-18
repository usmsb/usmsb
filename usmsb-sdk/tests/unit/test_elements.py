"""
Unit Tests for USMSB Core Elements

Tests for the 9 core elements: Agent, Object, Goal, Resource, Rule,
Information, Value, Risk, Environment.
"""

import pytest
from datetime import datetime

from usmsb_sdk.core.elements import (
    Agent,
    AgentType,
    Environment,
    EnvironmentType,
    Goal,
    GoalStatus,
    Information,
    InformationType,
    Object,
    Resource,
    ResourceType,
    Risk,
    RiskType,
    Rule,
    RuleType,
    Value,
    ValueType,
)


class TestGoal:
    """Tests for Goal element."""

    def test_goal_creation(self):
        """Test basic goal creation."""
        goal = Goal(name="Test Goal", description="A test goal")
        assert goal.name == "Test Goal"
        assert goal.description == "A test goal"
        assert goal.status == GoalStatus.PENDING
        assert goal.id is not None
        assert goal.created_at > 0

    def test_goal_status_update(self):
        """Test goal status updates."""
        goal = Goal(name="Test")
        assert goal.status == GoalStatus.PENDING

        goal.update_status(GoalStatus.IN_PROGRESS)
        assert goal.status == GoalStatus.IN_PROGRESS

        goal.update_status(GoalStatus.COMPLETED)
        assert goal.status == GoalStatus.COMPLETED
        assert goal.is_achieved()

    def test_goal_priority(self):
        """Test goal priority."""
        goal1 = Goal(name="Low", priority=1)
        goal2 = Goal(name="High", priority=10)

        assert goal2.priority > goal1.priority


class TestResource:
    """Tests for Resource element."""

    def test_resource_creation(self):
        """Test basic resource creation."""
        resource = Resource(
            name="Gold",
            type=ResourceType.TANGIBLE,
            quantity=100.0,
            unit="grams",
        )
        assert resource.name == "Gold"
        assert resource.type == ResourceType.TANGIBLE
        assert resource.quantity == 100.0
        assert resource.unit == "grams"

    def test_resource_consumption(self):
        """Test resource consumption."""
        resource = Resource(name="Money", quantity=1000.0)

        # Successful consumption
        result = resource.consume(500.0)
        assert result is True
        assert resource.quantity == 500.0

        # Failed consumption (insufficient)
        result = resource.consume(600.0)
        assert result is False
        assert resource.quantity == 500.0

    def test_resource_replenishment(self):
        """Test resource replenishment."""
        resource = Resource(name="Energy", quantity=50.0)
        resource.replenish(25.0)
        assert resource.quantity == 75.0


class TestRule:
    """Tests for Rule element."""

    def test_rule_creation(self):
        """Test basic rule creation."""
        rule = Rule(
            name="No Smoking",
            description="Smoking is prohibited",
            type=RuleType.SOCIAL,
        )
        assert rule.name == "No Smoking"
        assert rule.type == RuleType.SOCIAL
        assert rule.is_active is True

    def test_rule_applies_to(self):
        """Test rule application check."""
        rule = Rule(
            name="Speed Limit",
            type=RuleType.LEGAL,
            scope=["driving", "highway"],
        )

        # Should apply
        assert rule.applies_to({"type": "driving"}) is True
        assert rule.applies_to({"type": "highway"}) is True

        # Should not apply
        assert rule.applies_to({"type": "walking"}) is False

        # Inactive rule should not apply
        rule.is_active = False
        assert rule.applies_to({"type": "driving"}) is False


class TestInformation:
    """Tests for Information element."""

    def test_information_creation(self):
        """Test basic information creation."""
        info = Information(
            content="The stock market is up 2%",
            type=InformationType.TEXT,
            source="market_feed",
            quality=0.95,
        )
        assert info.content == "The stock market is up 2%"
        assert info.type == InformationType.TEXT
        assert info.quality == 0.95

    def test_information_quality_check(self):
        """Test information quality threshold."""
        high_quality = Information(content="Good data", quality=0.9)
        low_quality = Information(content="Bad data", quality=0.5)

        assert high_quality.is_high_quality(0.7) is True
        assert low_quality.is_high_quality(0.7) is False


class TestValue:
    """Tests for Value element."""

    def test_value_creation(self):
        """Test basic value creation."""
        value = Value(
            name="Revenue",
            type=ValueType.ECONOMIC,
            metric=10000.0,
            unit="USD",
        )
        assert value.name == "Revenue"
        assert value.type == ValueType.ECONOMIC
        assert value.metric == 10000.0

    def test_value_positivity(self):
        """Test value positivity check."""
        positive = Value(metric=100.0)
        negative = Value(metric=-50.0)
        none_value = Value()

        assert positive.is_positive() is True
        assert negative.is_positive() is False
        assert none_value.is_positive() is False


class TestRisk:
    """Tests for Risk element."""

    def test_risk_creation(self):
        """Test basic risk creation."""
        risk = Risk(
            name="Market Crash",
            type=RiskType.MARKET,
            probability=0.3,
            impact=0.8,
        )
        assert risk.name == "Market Crash"
        assert risk.probability == 0.3
        assert risk.impact == 0.8
        assert risk.severity == pytest.approx(0.24)

    def test_risk_severity_calculation(self):
        """Test risk severity calculation."""
        risk = Risk(probability=0.5, impact=0.6)
        severity = risk.calculate_severity()
        assert severity == pytest.approx(0.3)

    def test_risk_threshold(self):
        """Test high risk threshold."""
        high_risk = Risk(probability=0.8, impact=0.8)
        low_risk = Risk(probability=0.2, impact=0.3)

        assert high_risk.is_high_risk(0.5) is True
        assert low_risk.is_high_risk(0.5) is False


class TestEnvironment:
    """Tests for Environment element."""

    def test_environment_creation(self):
        """Test basic environment creation."""
        env = Environment(
            name="Stock Market",
            type=EnvironmentType.ECONOMIC,
            state={"trend": "bullish", "volatility": 0.25},
        )
        assert env.name == "Stock Market"
        assert env.type == EnvironmentType.ECONOMIC
        assert env.state["trend"] == "bullish"

    def test_environment_state_update(self):
        """Test environment state updates."""
        env = Environment(name="Test")
        env.update_state("temperature", 25)
        env.update_state("humidity", 60)

        assert env.get_state("temperature") == 25
        assert env.get_state("humidity") == 60
        assert env.get_state("nonexistent", "default") == "default"


class TestObject:
    """Tests for Object element."""

    def test_object_creation(self):
        """Test basic object creation."""
        obj = Object(
            name="Product",
            type="goods",
            properties={"price": 100, "weight": 2.5},
        )
        assert obj.name == "Product"
        assert obj.properties["price"] == 100

    def test_object_state_update(self):
        """Test object state updates."""
        obj = Object(name="Widget")
        obj.update_property("color", "blue")
        obj.update_state("status", "available")

        assert obj.properties["color"] == "blue"
        assert obj.current_state["status"] == "available"


class TestAgent:
    """Tests for Agent element."""

    def test_agent_creation(self):
        """Test basic agent creation."""
        agent = Agent(
            name="TestBot",
            type=AgentType.AI_AGENT,
            capabilities=["reasoning", "planning"],
        )
        assert agent.name == "TestBot"
        assert agent.type == AgentType.AI_AGENT
        assert "reasoning" in agent.capabilities
        assert len(agent.goals) == 0

    def test_agent_goal_management(self):
        """Test agent goal management."""
        agent = Agent(name="TestAgent")
        goal1 = Goal(name="Goal 1", priority=5)
        goal2 = Goal(name="Goal 2", priority=10)

        agent.add_goal(goal1)
        agent.add_goal(goal2)

        assert len(agent.goals) == 2

        # Get highest priority
        highest = agent.get_highest_priority_goal()
        assert highest.name == "Goal 2"

        # Remove goal
        result = agent.remove_goal(goal1.id)
        assert result is True
        assert len(agent.goals) == 1

    def test_agent_resource_management(self):
        """Test agent resource management."""
        agent = Agent(name="TestAgent")
        resource = Resource(name="Credits", type=ResourceType.FINANCIAL, quantity=1000.0)

        agent.add_resource(resource)

        assert len(agent.resources) == 1
        assert resource.owner_agent_id == agent.id

        # Get by type
        financial = agent.get_resource_by_type(ResourceType.FINANCIAL)
        assert len(financial) == 1

    def test_agent_information_buffer(self):
        """Test agent information buffer."""
        agent = Agent(name="TestAgent")

        info1 = Information(content="Info 1")
        info2 = Information(content="Info 2")

        agent.add_information(info1)
        agent.add_information(info2)

        assert len(agent.information_buffer) == 2

        agent.clear_information_buffer()
        assert len(agent.information_buffer) == 0

    def test_agent_capability_check(self):
        """Test agent capability checking."""
        agent = Agent(
            name="TestAgent",
            capabilities=["reasoning", "planning"],
        )

        assert agent.has_capability("reasoning") is True
        assert agent.has_capability("coding") is False

        agent.add_capability("coding")
        assert agent.has_capability("coding") is True

    def test_agent_state_management(self):
        """Test agent state management."""
        agent = Agent(name="TestAgent")

        agent.update_state("mood", "happy")
        agent.update_state("energy", 80)

        assert agent.get_state("mood") == "happy"
        assert agent.get_state("energy") == 80
        assert agent.get_state("nonexistent", "default") == "default"

    def test_agent_to_dict(self):
        """Test agent serialization."""
        agent = Agent(
            name="TestAgent",
            type=AgentType.AI_AGENT,
            capabilities=["reasoning"],
        )
        agent.add_goal(Goal(name="Test Goal"))

        result = agent.to_dict()

        assert result["name"] == "TestAgent"
        assert result["type"] == "ai_agent"
        assert "reasoning" in result["capabilities"]
        assert result["goals_count"] == 1
