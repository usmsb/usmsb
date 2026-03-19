"""
USMSB Platform - Direct Service Tests

Phase 6: Internal Testing

Tests the new USMSB services directly without legacy service dependencies.
"""

import time
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))


def test_agent_soul_models():
    """Test Agent Soul models."""
    print("Testing Agent Soul models...")

    from usmsb_sdk.services.agent_soul.models import (
        DeclaredSoul, InferredSoul, AgentSoul
    )
    from usmsb_sdk.core.elements import Goal, Value

    # Test DeclaredSoul
    soul = DeclaredSoul(
        goals=[Goal(id="g1", name="Test Goal", description="Test", priority=1)],
        value_seeking=[Value(id="v1", name="VIBE", type="economic", metric=10.0)],
        capabilities=["coding", "testing"],
        risk_tolerance=0.7,
        collaboration_style="aggressive",
    )

    d = soul.to_dict()
    assert d["capabilities"] == ["coding", "testing"]
    assert d["risk_tolerance"] == 0.7
    assert d["collaboration_style"] == "aggressive"

    # Test InferredSoul
    inferred = InferredSoul(
        actual_success_rate=0.85,
        avg_response_time_minutes=30.0,
        collaboration_count=10,
        value_alignment_score=0.9,
    )

    assert inferred.actual_success_rate == 0.85
    assert inferred.collaboration_count == 10

    # Test AgentSoul update
    agent_soul = AgentSoul(
        agent_id="test-agent",
        declared=DeclaredSoul(capabilities=["coding"]),
    )

    agent_soul.update_from_behavior({
        "contract_id": "c1",
        "success": True,
        "response_time_minutes": 60,
        "quality_score": 0.9,
        "value_match_score": 0.85,
        "timestamp": time.time(),
    })

    assert agent_soul.inferred.collaboration_count == 1
    assert agent_soul.soul_version == 2

    print("✓ Agent Soul models: PASS")


def test_value_contract_models():
    """Test Value Contract models."""
    print("Testing Value Contract models...")

    from usmsb_sdk.services.value_contract.models import (
        ValueFlow, ContractRisk, TaskValueContract, ProjectValueContract
    )
    from usmsb_sdk.core.elements import Resource, Value

    # Test ValueFlow
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
    assert d["value"]["metric"] == 5.0
    assert d["trigger"] == "on_delivery"

    # Test ContractRisk
    risk = ContractRisk(
        risk_id="risk-1",
        risk_type="quality",
        probability=0.2,
        impact=0.5,
        mitigation="Quality review before delivery",
    )

    assert risk.probability == 0.2
    assert risk.mitigation == "Quality review before delivery"

    # Test TaskValueContract
    task = TaskValueContract(
        contract_id="tc-1",
        contract_type="task",
        parties=["demand", "supply"],
        transformation_path="Task completion",
        status="draft",
        price_vibe=10.0,
        deadline=time.time() + 86400,
    )

    assert task.contract_type == "task"
    assert task.price_vibe == 10.0
    assert task.status == "draft"

    # Test ProjectValueContract
    project = ProjectValueContract(
        contract_id="pc-1",
        contract_type="project",
        parties=["owner", "agent-1"],
        transformation_path="Multi-agent project",
        total_budget_vibe=100.0,
    )

    assert project.contract_type == "project"
    assert project.total_budget_vibe == 100.0

    print("✓ Value Contract models: PASS")


def test_contract_templates():
    """Test Contract templates."""
    print("Testing Contract templates...")

    from usmsb_sdk.services.value_contract.templates import (
        get_template, list_templates, TEMPLATES
    )

    # Test simple_task template
    simple = get_template("simple_task")
    assert simple is not None
    assert simple.template_id == "simple_task"
    assert "price_vibe" in simple.variable_terms
    assert simple.fixed_terms["risk_allocation"] == "supply_bears_risk"

    # Test complex_task template
    complex_t = get_template("complex_task")
    assert complex_t is not None
    assert "milestones" in complex_t.variable_terms
    assert complex_t.fixed_terms["risk_allocation"] == "shared"

    # Test project template
    project = get_template("project")
    assert project is not None
    assert project.contract_type == "project"
    assert "total_budget_vibe" in project.variable_terms

    # Test list_templates
    all_templates = list_templates()
    assert len(all_templates) == 3
    template_ids = [t.template_id for t in all_templates]
    assert "simple_task" in template_ids
    assert "complex_task" in template_ids
    assert "project" in template_ids

    print("✓ Contract templates: PASS")


def test_matching_engine():
    """Test USMSB Matching Engine."""
    print("Testing USMSB Matching Engine...")

    from usmsb_sdk.services.agent_soul.models import AgentSoul, DeclaredSoul, InferredSoul
    from usmsb_sdk.services.matching.usmsb_matching_engine import USMSBMatchingEngine
    from usmsb_sdk.core.elements import Goal

    engine = USMSBMatchingEngine()

    # Test value alignment calculation
    soul_a = AgentSoul(
        agent_id="agent-a",
        declared=DeclaredSoul(
            capabilities=["coding"],
            risk_tolerance=0.5,
            collaboration_style="balanced",
            pricing_strategy="negotiable",
        ),
    )

    soul_b = AgentSoul(
        agent_id="agent-b",
        declared=DeclaredSoul(
            capabilities=["testing"],
            risk_tolerance=0.5,
            collaboration_style="balanced",
            pricing_strategy="negotiable",
        ),
        inferred=InferredSoul(actual_success_rate=0.9),
    )

    alignment = engine._calculate_value_alignment(soul_a, soul_b)

    # Same risk tolerance, style, pricing = high alignment
    assert alignment > 0.9

    # Test collaboration score
    soul_c = AgentSoul(
        agent_id="agent-c",
        declared=DeclaredSoul(
            capabilities=["coding", "design"],
            goals=[Goal(id="g1", name="Build Platform", description="Build", priority=1)],
            collaboration_style="balanced",
        ),
    )

    soul_d = AgentSoul(
        agent_id="agent-d",
        declared=DeclaredSoul(
            capabilities=["testing", "design"],
            goals=[Goal(id="g2", name="Build Platform", description="Build together", priority=1)],
            collaboration_style="balanced",
        ),
    )

    shared = engine._find_shared_goals(soul_c, soul_d)
    assert "Build Platform" in shared

    score = engine._calculate_collaboration_score(soul_c, soul_d, shared)
    assert score > 0.3

    print("✓ USMSB Matching Engine: PASS")


def test_emergence_discovery():
    """Test Emergence Discovery."""
    print("Testing Emergence Discovery...")

    from usmsb_sdk.services.matching.emergence_discovery import EmergenceDiscovery

    discovery = EmergenceDiscovery()

    # Test threshold configuration
    threshold = discovery.get_emergence_threshold()

    assert threshold["min_active_agents"] == 100
    assert threshold["min_collaboration_rate"] == 0.30
    assert threshold["min_soul_completeness"] == 0.70

    # Test threshold update
    original = discovery.get_emergence_threshold()
    discovery.set_emergence_threshold(min_active_agents=50)

    updated = discovery.get_emergence_threshold()
    assert updated["min_active_agents"] == 50

    # Restore
    discovery.set_emergence_threshold(min_active_agents=original["min_active_agents"])

    print("✓ Emergence Discovery: PASS")


def test_feedback_loop():
    """Test Feedback Loop."""
    print("Testing Feedback Loop...")

    from usmsb_sdk.services.feedback.collaboration_feedback_loop import (
        ValueDeliveryEvaluation
    )

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
    assert d["on_time_score"] == 1.0
    assert d["value_match_score"] == 0.85
    assert d["overall_score"] > 0.8

    # Test failed evaluation
    failed = ValueDeliveryEvaluation(
        contract_id="c2",
        success=False,
        quality_score=0.0,
        on_time_score=0.0,
        value_match_score=0.0,
        issues=["Quality below standard"],
    )

    assert failed.success is False
    assert failed.overall_score == 0.0
    assert len(failed.issues) == 1

    print("✓ Feedback Loop: PASS")


def test_negotiation():
    """Test Negotiation service."""
    print("Testing Negotiation...")

    from usmsb_sdk.services.value_contract.negotiation import (
        ValueNegotiationSession, NegotiationRound
    )

    # Test session creation
    session = ValueNegotiationSession(
        session_id="neg-1",
        participants=["agent-a", "agent-b"],
        template_id="simple_task",
        status="active",
    )

    assert len(session.participants) == 2
    assert session.status == "active"
    assert session.template_id == "simple_task"

    # Test negotiation round
    round = NegotiationRound(
        round=1,
        proposer_id="agent-a",
        proposed_changes={"price_vibe": 5.0, "deadline": 86400},
        status="pending",
    )

    assert round.round == 1
    assert round.proposed_changes["price_vibe"] == 5.0

    # Test session serialization
    d = session.to_dict()
    assert d["session_id"] == "neg-1"
    assert d["status"] == "active"

    # Test session deserialization
    session2 = ValueNegotiationSession.from_dict(d)
    assert session2.session_id == "neg-1"
    assert session2.status == "active"

    print("✓ Negotiation: PASS")


def test_soul_contract_integration():
    """Test Soul and Contract integration."""
    print("Testing Soul-Contract integration...")

    from usmsb_sdk.services.agent_soul.models import AgentSoul, DeclaredSoul
    from usmsb_sdk.services.value_contract.models import TaskValueContract

    # Create agents with Soul
    demand = AgentSoul(
        agent_id="demand-agent",
        declared=DeclaredSoul(
            capabilities=["project_management"],
            base_price_vibe=20.0,
        ),
    )

    supply = AgentSoul(
        agent_id="supply-agent",
        declared=DeclaredSoul(
            capabilities=["coding", "testing"],
            base_price_vibe=10.0,
        ),
    )

    # Create contract between them
    contract = TaskValueContract(
        contract_id="contract-1",
        contract_type="task",
        parties=[demand.agent_id, supply.agent_id],
        transformation_path="Development task",
        price_vibe=15.0,
        status="active",
    )

    # Verify integration
    assert demand.agent_id in contract.parties
    assert supply.agent_id in contract.parties
    assert contract.price_vibe == 15.0

    # Verify Soul data is preserved
    assert demand.declared.base_price_vibe == 20.0
    assert supply.declared.base_price_vibe == 10.0

    print("✓ Soul-Contract integration: PASS")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("USMSB Platform - Phase 6 Internal Tests")
    print("=" * 60)
    print()

    tests = [
        test_agent_soul_models,
        test_value_contract_models,
        test_contract_templates,
        test_matching_engine,
        test_emergence_discovery,
        test_feedback_loop,
        test_negotiation,
        test_soul_contract_integration,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: FAIL - {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
