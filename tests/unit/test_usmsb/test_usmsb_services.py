"""
USMSB Platform - Test Suite for New Services

Phase 6: Internal Testing and Optimization

Tests cover:
- AgentSoul models and manager
- ValueContract models and service
- ValueContract negotiation
- USMSB Matching Engine
- Emergence Discovery
- Feedback Loop
"""

import time
import uuid

import pytest


# ============== Test: Agent Soul Models ==============


def test_declared_soul_to_dict():
    """Test DeclaredSoul serialization."""
    from usmsb_sdk.services.agent_soul.models import DeclaredSoul
    from usmsb_sdk.core.elements import Goal, Value

    soul = DeclaredSoul(
        goals=[
            Goal(id="g1", name="Learn coding", description="Master Python", priority=1)
        ],
        value_seeking=[
            Value(id="v1", name="VIBE tokens", type="economic", metric=10.0)
        ],
        capabilities=["coding", "writing"],
        risk_tolerance=0.7,
        collaboration_style="aggressive",
        preferred_contract_type="task",
        pricing_strategy="negotiable",
        base_price_vibe=5.0,
    )

    d = soul.to_dict()

    assert d["capabilities"] == ["coding", "writing"]
    assert d["risk_tolerance"] == 0.7
    assert d["collaboration_style"] == "aggressive"
    assert len(d["goals"]) == 1
    assert d["goals"][0]["name"] == "Learn coding"


def test_declared_soul_from_dict():
    """Test DeclaredSoul deserialization."""
    from usmsb_sdk.services.agent_soul.models import DeclaredSoul

    data = {
        "capabilities": ["analysis", "writing"],
        "risk_tolerance": 0.5,
        "collaboration_style": "balanced",
        "preferred_contract_type": "project",
        "pricing_strategy": "market",
        "base_price_vibe": 20.0,
        "goals": [],
        "value_seeking": [],
    }

    soul = DeclaredSoul.from_dict(data)

    assert soul.capabilities == ["analysis", "writing"]
    assert soul.risk_tolerance == 0.5
    assert soul.base_price_vibe == 20.0


def test_inferred_soul_update():
    """Test InferredSoul update_from_behavior."""
    from usmsb_sdk.services.agent_soul.models import AgentSoul, DeclaredSoul

    agent_id = f"test-{uuid.uuid4().hex[:8]}"
    soul = AgentSoul(
        agent_id=agent_id,
        declared=DeclaredSoul(capabilities=["coding"]),
        inferred=None,
    )

    # First event - successful
    soul.update_from_behavior({
        "contract_id": "c1",
        "success": True,
        "response_time_minutes": 60,
        "quality_score": 0.9,
        "value_match_score": 0.85,
        "timestamp": time.time(),
    })

    assert soul.inferred.collaboration_count == 1
    assert soul.inferred.actual_success_rate > 0.5
    assert soul.soul_version == 2


def test_agent_soul_export():
    """Test Agent Soul data export for portability."""
    from usmsb_sdk.services.agent_soul.models import AgentSoul, DeclaredSoul, InferredSoul

    agent_id = f"test-{uuid.uuid4().hex[:8]}"
    soul = AgentSoul(
        agent_id=agent_id,
        declared=DeclaredSoul(capabilities=["test"]),
        inferred=InferredSoul(actual_success_rate=0.8),
        soul_version=3,
        soul_declared_at=time.time(),
    )

    exported = soul.to_dict()

    assert exported["agent_id"] == agent_id
    assert exported["declared"]["capabilities"] == ["test"]
    assert exported["inferred"]["actual_success_rate"] == 0.8
    assert exported["soul_version"] == 3


# ============== Test: Value Contract Models ==============


def test_value_flow_creation():
    """Test ValueFlow creation."""
    from usmsb_sdk.services.value_contract.models import ValueFlow
    from usmsb_sdk.core.elements import Resource, Value

    flow = ValueFlow(
        flow_id="vf-1",
        from_agent_id="agent-a",
        to_agent_id="agent-b",
        resource=Resource(id="r1", name="Compute", type="computational", quantity=100),
        value=Value(id="v1", name="Payment", type="economic", metric=5.0),
        trigger="on_delivery",
    )

    d = flow.to_dict()

    assert d["flow_id"] == "vf-1"
    assert d["from_agent_id"] == "agent-a"
    assert d["value"]["metric"] == 5.0
    assert d["trigger"] == "on_delivery"


def test_task_contract_creation():
    """Test TaskValueContract creation."""
    from usmsb_sdk.services.value_contract.models import TaskValueContract, ValueFlow

    contract = TaskValueContract(
        contract_id="tc-1",
        contract_type="task",
        parties=["demand-agent", "supply-agent"],
        transformation_path="Task completion for payment",
        status="draft",
        task_definition={
            "title": "Write report",
            "description": "Write a market analysis report",
        },
        price_vibe=10.0,
        deadline=time.time() + 86400,
    )

    assert contract.contract_type == "task"
    assert contract.status == "draft"
    assert contract.price_vibe == 10.0
    assert len(contract.parties) == 2


def test_project_contract_creation():
    """Test ProjectValueContract creation."""
    from usmsb_sdk.services.value_contract.models import ProjectValueContract

    contract = ProjectValueContract(
        contract_id="pc-1",
        contract_type="project",
        parties=["owner", "agent-1", "agent-2"],
        transformation_path="Multi-agent collaboration",
        project_definition={
            "title": "Research Platform",
            "goal_description": "Build a research platform",
        },
        total_budget_vibe=100.0,
    )

    assert contract.contract_type == "project"
    assert contract.total_budget_vibe == 100.0
    assert len(contract.parties) == 3


# ============== Test: Contract Templates ==============


def test_simple_task_template():
    """Test simple task template structure."""
    from usmsb_sdk.services.value_contract.templates import get_template, TEMPLATES

    template = get_template("simple_task")
    assert template is not None
    assert template.template_id == "simple_task"
    assert "price_vibe" in template.variable_terms
    assert "deadline" in template.variable_terms
    assert template.fixed_terms["risk_allocation"] == "supply_bears_risk"


def test_complex_task_template():
    """Test complex task template."""
    from usmsb_sdk.services.value_contract.templates import get_template

    template = get_template("complex_task")
    assert template is not None
    assert "milestones" in template.variable_terms
    assert template.fixed_terms["risk_allocation"] == "shared"


def test_all_templates():
    """Test all templates are available."""
    from usmsb_sdk.services.value_contract.templates import list_templates

    templates = list_templates()
    template_ids = [t.template_id for t in templates]

    assert "simple_task" in template_ids
    assert "complex_task" in template_ids
    assert "project" in template_ids


# ============== Test: USMSB Matching Engine ==============


def test_match_score_calculation():
    """Test match score calculation."""
    from usmsb_sdk.services.agent_soul.models import AgentSoul, DeclaredSoul, InferredSoul

    # Create two agents
    soul_a = AgentSoul(
        agent_id="agent-a",
        declared=DeclaredSoul(
            capabilities=["coding", "testing"],
            goals=[],
            risk_tolerance=0.5,
        ),
    )

    soul_b = AgentSoul(
        agent_id="agent-b",
        declared=DeclaredSoul(
            capabilities=["writing", "testing"],
            goals=[],
            risk_tolerance=0.5,
        ),
        inferred=InferredSoul(actual_success_rate=0.9),
    )

    # Test value alignment
    from usmsb_sdk.services.matching.usmsb_matching_engine import USMSBMatchingEngine

    engine = USMSBMatchingEngine()

    alignment = engine._calculate_value_alignment(soul_a, soul_b)

    # Same risk tolerance = 1.0 alignment on that dimension
    assert alignment > 0.7  # Should be high since both have same risk tolerance


def test_collaboration_score():
    """Test collaboration score calculation."""
    from usmsb_sdk.services.agent_soul.models import AgentSoul, DeclaredSoul
    from usmsb_sdk.services.matching.usmsb_matching_engine import USMSBMatchingEngine
    from usmsb_sdk.core.elements import Goal

    soul_a = AgentSoul(
        agent_id="agent-a",
        declared=DeclaredSoul(
            capabilities=["coding"],
            goals=[Goal(id="g1", name="Build platform", description="Build a platform", priority=1)],
            collaboration_style="balanced",
        ),
    )

    soul_b = AgentSoul(
        agent_id="agent-b",
        declared=DeclaredSoul(
            capabilities=["design"],
            goals=[Goal(id="g2", name="Build platform", description="Build platform together", priority=1)],
            collaboration_style="balanced",
        ),
    )

    engine = USMSBMatchingEngine()

    shared_goals = engine._find_shared_goals(soul_a, soul_b)
    assert "Build platform" in shared_goals

    score = engine._calculate_collaboration_score(soul_a, soul_b, shared_goals)
    assert score > 0.3


# ============== Test: Emergence Discovery ==============


def test_emergence_threshold():
    """Test emergence threshold configuration."""
    from usmsb_sdk.services.matching.emergence_discovery import EmergenceDiscovery

    discovery = EmergenceDiscovery()
    threshold = discovery.get_emergence_threshold()

    assert threshold["min_active_agents"] == 100
    assert threshold["min_collaboration_rate"] == 0.30
    assert threshold["min_soul_completeness"] == 0.70


def test_emergence_threshold_update():
    """Test threshold can be updated."""
    from usmsb_sdk.services.matching.emergence_discovery import EmergenceDiscovery

    discovery = EmergenceDiscovery()

    original = discovery.get_emergence_threshold()
    discovery.set_emergence_threshold(min_active_agents=50)

    updated = discovery.get_emergence_threshold()
    assert updated["min_active_agents"] == 50

    # Restore
    discovery.set_emergence_threshold(min_active_agents=original["min_active_agents"])


# ============== Test: Feedback Loop ==============


def test_value_delivery_evaluation():
    """Test value delivery evaluation structure."""
    from usmsb_sdk.services.feedback.collaboration_feedback_loop import ValueDeliveryEvaluation

    evaluation = ValueDeliveryEvaluation(
        contract_id="c1",
        success=True,
        quality_score=0.9,
        on_time_score=1.0,
        value_match_score=0.85,
    )

    d = evaluation.to_dict()

    assert d["contract_id"] == "c1"
    assert d["success"] is True
    assert d["quality_score"] == 0.9


# ============== Test: Negotiation ==============


def test_negotiation_session_creation():
    """Test negotiation session creation."""
    from usmsb_sdk.services.value_contract.negotiation import ValueNegotiationSession

    session = ValueNegotiationSession(
        session_id="neg-1",
        participants=["agent-a", "agent-b"],
        template_id="simple_task",
        status="active",
    )

    assert len(session.participants) == 2
    assert session.status == "active"
    assert session.to_dict()["session_id"] == "neg-1"


def test_negotiation_round():
    """Test negotiation round tracking."""
    from usmsb_sdk.services.value_contract.negotiation import NegotiationRound

    round = NegotiationRound(
        round=1,
        proposer_id="agent-a",
        proposed_changes={"price_vibe": 5.0, "deadline": 86400},
        status="pending",
    )

    assert round.round == 1
    assert round.proposed_changes["price_vibe"] == 5.0


# ============== Test: Integration Patterns ==============


def test_soul_contract_integration():
    """Test Soul and Contract integration flow."""
    from usmsb_sdk.services.agent_soul.models import AgentSoul, DeclaredSoul
    from usmsb_sdk.services.value_contract.models import TaskValueContract

    # Create agents with Soul
    demand = AgentSoul(
        agent_id="demand-agent",
        declared=DeclaredSoul(
            capabilities=["project_management"],
            goals=[],
            base_price_vibe=20.0,
        ),
    )

    supply = AgentSoul(
        agent_id="supply-agent",
        declared=DeclaredSoul(
            capabilities=["coding", "testing"],
            goals=[],
            base_price_vibe=10.0,
        ),
    )

    # Create contract
    contract = TaskValueContract(
        contract_id="contract-1",
        contract_type="task",
        parties=[demand.agent_id, supply.agent_id],
        transformation_path="Development task",
        price_vibe=15.0,  # Negotiated price
        status="active",
    )

    # Verify integration
    assert demand.agent_id in contract.parties
    assert supply.agent_id in contract.parties
    assert contract.price_vibe == 15.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
