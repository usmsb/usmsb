#!/usr/bin/env python3
"""
MetaAgent Chat 方法全流程测试

测试 chat 方法调用的所有核心模块
"""

import asyncio
import sys
sys.path.insert(0, '/Users/gujun/vibecode/usmsb')

from dataclasses import dataclass
from typing import Any, Optional


async def test_imports():
    """测试所有模块能否正常导入"""
    print("\n" + "="*60)
    print("1. 模块导入测试")
    print("="*60)

    modules = [
        ("MetaAgent", "usmsb_sdk.meta_agent.agent.MetaAgent"),
        ("L1 Engine", "usmsb_sdk.l1.rule_engine.RuleEngine"),
        ("ConversationManager", "usmsb_sdk.meta_agent.conversation.conversation_manager.ConversationManager"),
        ("MemoryManager", "usmsb_sdk.meta_agent.memory.memory_manager.MemoryManager"),
        ("ContextManager", "usmsb_sdk.meta_agent.context.context_manager.ContextManager"),
        ("ToolRegistry", "usmsb_sdk.meta_agent.tools.tool_registry.ToolRegistry"),
        ("SkillsManager", "usmsb_sdk.meta_agent.skills.skills_manager.SkillsManager"),
        ("StrategyRouter", "usmsb_sdk.meta_agent.strategy_router.StrategyRouter"),
        ("LLMManager", "usmsb_sdk.meta_agent.llm.manager.LLMManager"),
        ("SessionManager", "usmsb_sdk.meta_agent.session.session_manager.SessionManager"),
    ]

    results = {}
    for name, path in modules:
        try:
            parts = path.split(".")
            module = __import__(path, fromlist=[parts[-1]])
            results[name] = True
            print(f"  ✓ {name}")
        except Exception as e:
            results[name] = False
            print(f"  ✗ {name}: {e}")

    return all(results.values())


async def test_l1_rule_engine():
    """测试 L1 规则引擎"""
    print("\n" + "="*60)
    print("2. L1 规则引擎测试")
    print("="*60)

    try:
        from usmsb_sdk.l1.rule_engine import RuleEngine, Stimulus

        engine = RuleEngine()
        stimulus = Stimulus(text="你好")

        response = await engine.react(stimulus)
        print(f"  规则引擎响应: {response.action_result[:50] if response.action_result else 'None'}...")
        print(f"  匹配规则: {len(response.matched_rules)} 条")

        # 测试问候规则
        stimulus2 = Stimulus(text="hello")
        response2 = await engine.react(stimulus2)
        print(f"  Hello规则: {response2.action_result[:50] if response2.action_result else 'None'}...")

        return True
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_conversation_manager():
    """测试会话管理器"""
    print("\n" + "="*60)
    print("3. 会话管理器测试")
    print("="*60)

    try:
        from usmsb_sdk.meta_agent.conversation.conversation_manager import ConversationManager
        from usmsb_sdk.meta_agent.models.chat import MessageRole

        manager = ConversationManager()

        # 创建会话
        conversation = await manager.get_or_create_conversation(
            owner_id="test_user",
            owner_type="human"
        )
        print(f"  创建会话: {conversation.id}")

        # 添加消息
        await manager.add_message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="你好，测试消息"
        )
        print(f"  添加用户消息: OK")

        # 获取消息
        messages = await manager.get_messages_for_llm(
            conversation_id=conversation.id,
            accessor_id="test_user",
            max_tokens=4000
        )
        print(f"  获取消息: {len(messages)} 条")

        return True
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tool_registry():
    """测试工具注册表"""
    print("\n" + "="*60)
    print("4. 工具注册表测试")
    print("="*60)

    try:
        from usmsb_sdk.meta_agent.tools.tool_registry import ToolRegistry

        registry = ToolRegistry()

        # 注册测试工具
        @registry.register(name="test_tool")
        async def test_tool(param1: str) -> str:
            """测试工具"""
            return f"Result: {param1}"

        # 列出工具
        tools = registry.list_tools()
        print(f"  注册工具数: {len(tools)}")

        # 获取工具模式
        schema = registry.get_tools_schema(provider="openai")
        print(f"  OpenAI工具模式: {len(schema)} 个")

        # 执行工具
        result = await registry.execute("test_tool", param1="hello")
        print(f"  执行结果: {result}")

        return True
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_skills_manager():
    """测试技能管理器"""
    print("\n" + "="*60)
    print("5. 技能管理器测试")
    print("="*60)

    try:
        from usmsb_sdk.meta_agent.skills.skills_manager import SkillsManager

        manager = SkillsManager()

        # 获取技能目录
        catalog = manager.get_skills_catalog()
        print(f"  技能目录: {len(catalog)} 个技能")

        # 获取技能模式
        schema = manager.get_skills_schema(provider="openai")
        print(f"  OpenAI技能模式: {len(schema)} 个")

        return True
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_strategy_router():
    """测试策略路由器"""
    print("\n" + "="*60)
    print("6. 策略路由器测试")
    print("="*60)

    try:
        from usmsb_sdk.meta_agent.strategy_router import StrategyRouter

        router = StrategyRouter()

        # 测试场景分类
        scenario = await router._classify_scenario("帮我写一个排序算法")
        print(f"  分类结果: scenario={scenario.scenario}, complexity={scenario.complexity}")
        print(f"  建议层级: {scenario.suggested_layer}")

        # 测试路由
        async def test_fn():
            return "test_result"

        result = await router.route(
            message="test",
            suggested_layer="L1",
            internal_fn=test_fn,
            sdk_fn=None
        )
        print(f"  路由结果: winner={result.strategy_name}")

        return True
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_context_manager():
    """测试上下文管理器"""
    print("\n" + "="*60)
    print("7. 上下文管理器测试")
    print("="*60)

    try:
        from usmsb_sdk.meta_agent.context.context_manager import ContextManager

        manager = ContextManager()

        # 构建消息
        messages = await manager.build_messages(
            user_message="你好",
            conversation_history=[],
            user_info=None,
            available_tools=[],
            memory_context="",
            smart_recall_context="",
        )
        print(f"  构建消息数: {len(messages)}")

        return True
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_memory_manager():
    """测试记忆管理器"""
    print("\n" + "="*60)
    print("8. 记忆管理器测试")
    print("="*60)

    try:
        from usmsb_sdk.meta_agent.memory.memory_manager import MemoryManager

        manager = MemoryManager()

        # 获取上下文
        context = await manager.get_context(
            user_id="test_user",
            conversation_id="test_conv"
        )
        print(f"  上下文长度: {len(context)} 字符")

        return True
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_session_manager():
    """测试会话管理器"""
    print("\n" + "="*60)
    print("9. Session Manager 测试")
    print("="*60)

    try:
        from usmsb_sdk.meta_agent.session.session_manager import SessionManager

        manager = SessionManager()

        # 创建会话
        session = await manager.get_or_create_session(wallet_address="0x1234567890abcdef")
        print(f"  创建会话: {session.session_id}")

        # 更新活跃时间
        session.update_activity()
        print(f"  更新活跃时间: OK")

        return True
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_llm_manager():
    """测试 LLM 管理器"""
    print("\n" + "="*60)
    print("10. LLM 管理器测试")
    print("="*60)

    try:
        from usmsb_sdk.meta_agent.llm.manager import LLMManager

        # 创建管理器（不实际调用API）
        manager = LLMManager()

        # 检查配置
        print(f"  提供者: {manager.provider}")
        print(f"  最大令牌: {manager.max_tokens}")

        # 测试简单调用
        try:
            result = await manager.complete(
                prompt="Say 'test'",
                model="test",
                max_tokens=10
            )
            print(f"  调用结果: {result[:50] if result else 'None'}...")
        except Exception as llm_error:
            print(f"  LLM API 调用跳过 (预期): {type(llm_error).__name__}")

        return True
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_causal_learning_components():
    """测试因果学习组件"""
    print("\n" + "="*60)
    print("11. 因果学习组件测试")
    print("="*60)

    try:
        # 测试各组件导入
        from usmsb_sdk.meta_agent.evolution_v2.engine import SelfEvolutionEngine
        from usmsb_sdk.meta_agent.evolution_v2.causal_discovery.engine import CausalDiscoveryEngine
        from usmsb_sdk.meta_agent.evolution_v2.causal_meta_learner.meta_learner import CausalMetaLearner
        from usmsb_sdk.meta_agent.evolution_v2.causal_planner.planner import CausalPlanner
        from usmsb_sdk.meta_agent.evolution_v2.causal_verifier.verifier import CausalVerifier
        from usmsb_sdk.meta_agent.evolution_v2.reasoning_enhancer.enhancer import ReasoningEnhancer
        from usmsb_sdk.meta_agent.evolution_v2.auto_skill.auto_skill_engine import AutoSkillEngine

        print("  所有组件导入: OK")

        # 测试初始化
        discovery = CausalDiscoveryEngine()
        await discovery.initialize()
        print("  CausalDiscoveryEngine: ✓")

        meta = CausalMetaLearner()
        await meta.initialize()
        print("  CausalMetaLearner: ✓")

        return True
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_meta_agent_integration():
    """测试 MetaAgent 完整集成"""
    print("\n" + "="*60)
    print("12. MetaAgent 集成测试")
    print("="*60)

    try:
        from usmsb_sdk.meta_agent import MetaAgent

        # 创建实例
        agent = MetaAgent()

        # 检查所有组件
        components = [
            ("l1_engine", agent.l1_engine),
            ("conversation_manager", agent.conversation_manager),
            ("memory_manager", agent.memory_manager),
            ("context_manager", agent.context_manager),
            ("tool_registry", agent.tool_registry),
            ("skills_manager", agent.skills_manager),
            ("strategy_router", agent.strategy_router),
            ("llm_manager", agent.llm_manager),
        ]

        for name, component in components:
            status = "✓" if component is not None else "✗ (None)"
            print(f"  {name}: {status}")

        # 检查 task_executor
        has_executor = agent.task_executor is not None
        print(f"  task_executor: {'✓' if has_executor else '✗ (None)'}")

        return True
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("\n" + "#"*60)
    print("# MetaAgent Chat 方法全流程测试")
    print("#"*60)

    results = {}

    # 1. 模块导入
    results["模块导入"] = await test_imports()

    # 2. L1 规则引擎
    results["L1规则引擎"] = await test_l1_rule_engine()

    # 3. 会话管理器
    results["会话管理器"] = await test_conversation_manager()

    # 4. 工具注册表
    results["工具注册表"] = await test_tool_registry()

    # 5. 技能管理器
    results["技能管理器"] = await test_skills_manager()

    # 6. 策略路由器
    results["策略路由器"] = await test_strategy_router()

    # 7. 上下文管理器
    results["上下文管理器"] = await test_context_manager()

    # 8. 记忆管理器
    results["记忆管理器"] = await test_memory_manager()

    # 9. Session Manager
    results["SessionManager"] = await test_session_manager()

    # 10. LLM 管理器
    results["LLM管理器"] = await test_llm_manager()

    # 11. 因果学习组件
    results["因果学习组件"] = await test_causal_learning_components()

    # 12. MetaAgent 集成
    results["MetaAgent集成"] = await test_meta_agent_integration()

    # 总结
    print("\n" + "#"*60)
    print("# 测试总结")
    print("#"*60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✓" if result else "✗"
        print(f"  {status} {name}")

    print(f"\n通过: {passed}/{total}")

    if passed == total:
        print("\n🎉 所有模块测试通过!")
        return 0
    else:
        print(f"\n⚠ {total - passed} 项测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)