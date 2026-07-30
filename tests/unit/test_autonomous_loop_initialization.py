"""Regression tests for the MetaAgent autonomous-loop dependency wiring."""

from types import SimpleNamespace

import pytest

from usmsb_sdk.meta_agent.agent import MetaAgent


@pytest.mark.asyncio
async def test_autonomous_loop_passes_llm_manager_to_goal_prioritizer(monkeypatch):
    captured: dict[str, object] = {}

    class DummyMotivationEngine:
        pass

    class DummyPurposeGenerator:
        def __init__(self, **kwargs):
            captured["purpose_kwargs"] = kwargs

    class DummyPrioritizer:
        def __init__(self, **kwargs):
            captured["prioritizer_kwargs"] = kwargs

    class DummyValueSeedEngine:
        def __init__(self, **kwargs):
            captured["value_seed_kwargs"] = kwargs

        def create_value_seed(self, agent_id):
            captured["value_seed_agent_id"] = agent_id

    class DummyNegotiationEngine:
        def __init__(self, **kwargs):
            captured["negotiation_kwargs"] = kwargs

    class DummyLoopConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class DummyAutonomousLoop:
        def __init__(self, **kwargs):
            captured["loop_kwargs"] = kwargs

    monkeypatch.setattr(
        "usmsb_sdk.l3.intrinsic_motivation.IntrinsicMotivationEngine",
        DummyMotivationEngine,
    )
    monkeypatch.setattr(
        "usmsb_sdk.l3.purpose_generator.PurposeGenerator",
        DummyPurposeGenerator,
    )
    monkeypatch.setattr(
        "usmsb_sdk.l3.llm_goal_prioritizer.LLMGoalPrioritizer",
        DummyPrioritizer,
    )
    monkeypatch.setattr(
        "usmsb_sdk.l3.value_seed_engine.ValueSeedEngine",
        DummyValueSeedEngine,
    )
    monkeypatch.setattr(
        "usmsb_sdk.l3.dynamic_negotiation.NegotiationEngine",
        DummyNegotiationEngine,
    )
    monkeypatch.setattr(
        "usmsb_sdk.l3.autonomous_loop.LoopConfig",
        DummyLoopConfig,
    )
    monkeypatch.setattr(
        "usmsb_sdk.l3.autonomous_loop.AutonomousLoop",
        DummyAutonomousLoop,
    )

    manager = SimpleNamespace(_adapter=object())
    agent = object.__new__(MetaAgent)
    agent.agent_id = "agent-test"
    agent.llm_manager = manager
    agent.l4_agent = None
    agent.gene_capsule_adapter = None

    await agent._init_autonomous_loop()

    assert captured["prioritizer_kwargs"] == {"llm_manager": manager}
    assert captured["purpose_kwargs"]["llm_client"] is manager._adapter
    assert captured["loop_kwargs"]["llm_goal_prioritizer"].__class__ is DummyPrioritizer
    assert isinstance(agent.autonomous_loop, DummyAutonomousLoop)
