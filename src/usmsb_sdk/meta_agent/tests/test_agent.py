"""
Meta Agent 测试
"""

import asyncio
import sys

sys.path.insert(0, "../../../../")

from usmsb_sdk.meta_agent import MetaAgent, MetaAgentConfig


async def test_meta_agent():
    """测试 Meta Agent"""
    print("=== 测试 Meta Agent ===")

    config = MetaAgentConfig(name="TestMetaAgent", description="测试用 Meta Agent")

    agent = MetaAgent(config)
    print(f"Agent ID: {agent.agent_id}")
    print(f"Config: {agent.config.name}")

    print("\n=== 测试工具注册 ===")
    tools = agent.get_available_tools()
    print(f"已注册工具数量: {len(tools)}")
    for tool in tools[:5]:
        print(f"  - {tool['name']}: {tool['description']}")

    print("\n=== 测试执行工具 ===")
    result = await agent.execute_tool("health_check", {"target": "system"})
    print(f"health_check 结果: {result}")

    result = await agent.execute_tool("get_node_status", {})
    print(f"get_node_status 结果: {result}")

    print("\n=== 测试创建钱包 ===")
    result = await agent.execute_tool("create_wallet", {"chain": "ethereum"})
    print(f"create_wallet 结果: {result}")

    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    asyncio.run(test_meta_agent())


# ─────────────────────────────────────────────────────────
# v2.0 功能测试
# ─────────────────────────────────────────────────────────

async def test_l1_rule_engine():
    """测试 L1 规则引擎"""
    print("\n=== 测试 L1 规则引擎 ===")
    from usmsb_sdk.l1.rule_engine import RuleEngine, Stimulus, Rule, Condition, ConditionType, ActionType

    engine = RuleEngine(name="test_l1")

    # 添加测试规则
    rule = Rule(
        name="test_ping",
        conditions=[Condition(ConditionType.KEYWORD, pattern="ping")],
        action_type=ActionType.RESPOND,
        action_payload={"response": "pong from L1"},
        priority=10,
    )
    engine.add_rule(rule)

    # 测试匹配
    response = await engine.react(Stimulus(text="ping"))
    print(f"  ping -> {response.action_result}")
    assert response.action_result == "pong from L1", f"Expected 'pong from L1', got '{response.action_result}'"

    # 测试未匹配（应返回默认）
    response2 = await engine.react(Stimulus(text="complex task with multiple steps"))
    print(f"  complex task -> (no match or fallback)")

    print("L1 规则引擎测试通过")


async def test_l3_adapter():
    """测试 L3Adapter（SDK PurposeGenerator → IL3 接口）"""
    print("\n=== 测试 L3Adapter ===")
    from usmsb_sdk.meta_agent.adapters.l3_adapter import L3Adapter, Goal

    adapter = L3Adapter(agent_id="test_meta_agent", llm_client=None)

    # 测试 generate_goal（会 fallback 到启发式）
    goal = await adapter.generate_goal({"task": "explore new domain"})
    print(f"  Generated goal: {goal.name}, strategy: {goal.metadata.get('strategy', 'unknown')}")
    assert isinstance(goal, Goal), "generate_goal should return Goal"
    assert goal.name, "Goal should have a name"

    # 测试 evaluate_outcome
    score = await adapter.evaluate_outcome(goal, {"success": True, "data": "result"})
    print(f"  evaluate_outcome score: {score}")
    assert 0.0 <= score <= 1.0

    # 测试 detect_intrinsic_motivation
    signal = await adapter.detect_intrinsic_motivation({})
    print(f"  Motivation: dominant={signal.dominant}, intensity={signal.intensity}")
    assert signal.dominant in ["curiosity", "growth", "social", "creation", "survival"]
    assert 0.0 <= signal.intensity <= 1.0

    print("L3Adapter 测试通过")


async def test_skill_registry():
    """测试 SkillRegistry"""
    print("\n=== 测试 SkillRegistry ===")
    import tempfile, os
    from usmsb_sdk.agent_skill.skill_platform.registry.skill_registry import SkillRegistry
    from usmsb_sdk.agent_skill.skill_platform.types import SkillMetadata, SkillTier

    with tempfile.TemporaryDirectory() as tmpdir:
        registry = SkillRegistry(registry_path=f"{tmpdir}/test_skill.db")

        # 创建 Skill metadata
        metadata = SkillMetadata(
            skill_id="test_skill_001",
            name="TestSkill",
            version="1.0.0",
            author_agent_id="test_agent",
            tier=SkillTier.L2,
            description="A test skill for unit testing",
        )

        # 测试安装
        instance = registry.install(metadata, config={"test": True})
        print(f"  Installed: {instance.metadata.name}, skill_id: {instance.metadata.skill_id}")
        assert instance.metadata.skill_id == "test_skill_001"

        # 测试查询已安装
        retrieved = registry.get_installed("test_skill_001")
        assert retrieved is not None
        assert retrieved.metadata.name == "TestSkill"

        # 测试列出已安装
        all_installed = registry.list_installed()
        assert len(all_installed) == 1
        print(f"  Total installed: {len(all_installed)}")

        # 测试卸载
        removed = registry.uninstall("test_skill_001")
        assert removed is True
        print("  Uninstalled: OK")

    print("SkillRegistry 测试通过")


async def test_strategy_router():
    """测试 StrategyRouter 经验库"""
    print("\n=== 测试 StrategyRouter 经验库 ===")
    import tempfile, os
    from usmsb_sdk.meta_agent.strategy_router import StrategyExperience, ScenarioTag

    with tempfile.TemporaryDirectory() as tmpdir:
        from usmsb_sdk.meta_agent.strategy_router import StrategyRouter

        # 创建一个 mock LLM manager
        class MockLLM:
            async def generate(self, prompt):
                return '{"strategy": "sdk", "reasoning": "test"}'

        router = StrategyRouter(llm_manager=MockLLM(), experience_db_path=f"{tmpdir}/test_exp.db")

        # 测试 scenario 分类（fallback）
        tag = await router._classify_scenario("测试ping")
        print(f"  Scenario: {tag.scenario}, complexity: {tag.complexity}")
        assert tag.scenario in ["INFO", "PLAN", "COG", "COLLAB"]

        print("StrategyRouter 经验库测试通过")


async def test_goal_engine_llm_driven():
    """测试 GoalEngine LLM 驱动版"""
    print("\n=== 测试 GoalEngine (LLM-driven) ===")
    from usmsb_sdk.meta_agent.goals.engine import GoalEngine

    engine = GoalEngine(agent_id="test_meta_agent", llm_client=None)

    # 测试添加目标
    await engine.add_goal({"id": "test_goal_1", "name": "测试目标", "status": "pending"})
    print(f"  Goals count: {len(engine.goals)}")
    assert len(engine.goals) == 1

    # 测试更新目标
    await engine.update_goal("test_goal_1", "completed")
    assert engine.goals[0]["status"] == "completed"
    print("  Update goal: OK")

    # 测试启动
    await engine.start()
    print("  Start: OK")

    print("GoalEngine LLM驱动版测试通过")


async def run_all_tests():
    """运行所有测试"""
    print("=" * 50)
    print("USMSB v2.0 功能测试")
    print("=" * 50)

    await test_l1_rule_engine()
    await test_l3_adapter()
    await test_skill_registry()
    await test_strategy_router()
    await test_goal_engine_llm_driven()

    print("\n" + "=" * 50)
    print("全部测试通过 ✅")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
