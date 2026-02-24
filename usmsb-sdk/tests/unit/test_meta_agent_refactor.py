"""
Meta Agent Refactor 单元测试

测试新创建的模块：
1. 敏感信息处理器注册表
2. 意图识别器
3. Chat 配置类
"""

import pytest
from unittest.mock import Mock
import os


class TestSensitiveInfoRegistry:
    """敏感信息注册表测试"""

    def test_import_registry(self):
        """测试导入注册表"""
        from usmsb_sdk.platform.external.meta_agent.sensitive.registry import (
            SensitiveInfoRegistry,
            SensitiveInfoHandler,
            get_sensitive_info_registry,
            clear_sensitive_info_registry,
        )
        assert SensitiveInfoRegistry is not None
        assert SensitiveInfoHandler is not None

    def test_get_all_keywords(self):
        """测试获取所有关键词"""
        from usmsb_sdk.platform.external.meta_agent.sensitive.registry import (
            get_sensitive_info_registry,
            clear_sensitive_info_registry,
        )

        clear_sensitive_info_registry()
        registry = get_sensitive_info_registry()
        keywords = registry.get_all_keywords()

        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert "password" in keywords
        assert "token" in keywords

    def test_get_all_patterns(self):
        """测试获取所有正则模式"""
        from usmsb_sdk.platform.external.meta_agent.sensitive.registry import (
            get_sensitive_info_registry,
            clear_sensitive_info_registry,
        )

        clear_sensitive_info_registry()
        registry = get_sensitive_info_registry()
        patterns = registry.get_all_patterns()

        assert isinstance(patterns, dict)
        assert len(patterns) > 0


class TestIntentRecognizer:
    """意图识别器测试"""

    def test_import_recognizer(self):
        """测试导入意图识别器"""
        from usmsb_sdk.platform.external.meta_agent.intent.recognizer import (
            IntentRecognizer,
            Intent,
            IntentType,
        )
        assert IntentRecognizer is not None
        assert Intent is not None
        assert IntentType is not None

    def test_intent_type_enum(self):
        """测试意图类型枚举"""
        from usmsb_sdk.platform.external.meta_agent.intent.recognizer import IntentType

        assert hasattr(IntentType, "SIMPLE_CHAT")
        assert hasattr(IntentType, "TOOL_CALL")
        assert hasattr(IntentType, "INFO_RETRIEVAL")

    def test_intent_dataclass(self):
        """测试意图数据类"""
        from usmsb_sdk.platform.external.meta_agent.intent.recognizer import Intent, IntentType

        intent = Intent(
            type=IntentType.SIMPLE_CHAT,
            confidence=0.9,
            parameters={},
            reasoning="Test",
        )

        assert intent.type == IntentType.SIMPLE_CHAT
        assert intent.confidence == 0.9
        assert intent.is_simple() == True
        assert intent.is_tool_call() == False

    def test_rule_based_recognition(self):
        """测试基于规则的意图识别（降级模式）"""
        from usmsb_sdk.platform.external.meta_agent.intent.recognizer import (
            IntentRecognizer,
            IntentType,
        )
        import asyncio

        recognizer = IntentRecognizer(llm_manager=None)

        # Test simple greeting
        async def test_greeting():
            intent = await recognizer.recognize("你好")
            assert intent.is_simple() == True

        # Test tool call
        async def test_tool():
            intent = await recognizer.recognize("帮我查询一下数据")
            assert intent.type in [IntentType.TOOL_CALL, IntentType.INFO_RETRIEVAL]

        asyncio.run(test_greeting())
        asyncio.run(test_tool())


class TestChatConfig:
    """Chat 配置类测试"""

    def test_import_chat_config(self):
        """测试导入 ChatConfig"""
        from usmsb_sdk.platform.external.meta_agent.config.chat_config import ChatConfig
        assert ChatConfig is not None

    def test_default_values(self):
        """测试默认值"""
        from usmsb_sdk.platform.external.meta_agent.config.chat_config import ChatConfig

        config = ChatConfig()
        assert config.max_history_tokens == 2000
        assert config.max_context_tokens == 4000
        assert config.max_tool_iterations == 20
        assert config.simple_message_threshold == 20

    def test_from_env(self):
        """测试从环境变量加载"""
        from usmsb_sdk.platform.external.meta_agent.config.chat_config import ChatConfig

        config = ChatConfig.from_env()
        assert config.max_history_tokens == 2000

    def test_message_templates(self):
        """测试消息模板"""
        from usmsb_sdk.platform.external.meta_agent.config.chat_config import ChatConfig

        config = ChatConfig()
        assert "后台任务" in config.background_task_start_message
        assert "完成" in config.background_task_complete_template
        assert "失败" in config.background_task_fail_template

    def test_to_dict(self):
        """测试转换为字典"""
        from usmsb_sdk.platform.external.meta_agent.config.chat_config import ChatConfig

        config = ChatConfig()
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert "max_history_tokens" in config_dict
        assert config_dict["max_history_tokens"] == 2000


class TestIntegration:
    """集成测试"""

    def test_meta_agent_import(self):
        """测试导入 MetaAgent"""
        from usmsb_sdk.platform.external.meta_agent import MetaAgent
        assert MetaAgent is not None

    def test_meta_agent_config(self):
        """测试导入 MetaAgentConfig"""
        from usmsb_sdk.platform.external.meta_agent import MetaAgentConfig
        assert MetaAgentConfig is not None

    def test_sensitive_registry_in_config(self):
        """测试敏感信息注册表在配置中的使用"""
        from usmsb_sdk.platform.external.meta_agent.sensitive.registry import (
            get_sensitive_info_registry,
        )

        registry = get_sensitive_info_registry()
        keywords = registry.get_all_keywords()

        assert isinstance(keywords, list)
        assert len(keywords) > 0
