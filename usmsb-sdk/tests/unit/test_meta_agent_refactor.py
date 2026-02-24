"""
Meta Agent Refactor 单元测试

测试新创建的模块：
1. 敏感信息处理器注册表
2. 意图识别器
3. Chat 配置类
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch


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

    def test_detect_info_type(self):
        """测试检测敏感信息类型"""
        from usmsb_sdk.platform.external.meta_agent.sensitive.registry import (
            get_sensitive_info_registry,
            clear_sensitive_info_registry,
        )

        clear_sensitive_info_registry()
        registry = get_sensitive_info_registry()

        # 测试 Bearer token
        info_type = registry.detect_info_type("Bearer abc123xyz")
        assert info_type in ["token", "api_key"]


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

        assert IntentType.SIMPLE_CHAT.value == "simple_chat"
        assert IntentType.TOOL_CALL.value == "tool_call"
        assert IntentType.INFO_RETRIEVAL.value == "info_retrieval"

    def test_intent_dataclass(self):
        """测试意图数据类"""
        from usmsb_sdk.platform.external.meta_agent.intent.recognizer import (
            Intent,
            IntentType,
        )

        intent = Intent(
            type=IntentType.SIMPLE_CHAT,
            confidence=0.9,
            reasoning="Test intent",
        )

        assert intent.type == IntentType.SIMPLE_CHAT
        assert intent.confidence == 0.9
        assert intent.is_simple() is True
        assert intent.is_tool_call() is False

    def test_rule_based_recognition_greeting(self):
        """测试规则识别 - 问候"""
        from usmsb_sdk.platform.external.meta_agent.intent.recognizer import (
            IntentRecognizer,
            IntentType,
        )

        recognizer = IntentRecognizer(llm_manager=None)
        intent = recognizer._rule_based_recognition("你好")

        assert intent.type == IntentType.SIMPLE_CHAT
        assert intent.confidence > 0.5

    def test_rule_based_recognition_tool(self):
        """测试规则识别 - 工具调用"""
        from usmsb_sdk.platform.external.meta_agent.intent.recognizer import (
            IntentRecognizer,
            IntentType,
        )

        recognizer = IntentRecognizer(llm_manager=None)
        intent = recognizer._rule_based_recognition("搜索一下最新的新闻")

        assert intent.type == IntentType.TOOL_CALL

    def test_rule_based_recognition_retrieval(self):
        """测试规则识别 - 信息检索"""
        from usmsb_sdk.platform.external.meta_agent.intent.recognizer import (
            IntentRecognizer,
            IntentType,
        )

        recognizer = IntentRecognizer(llm_manager=None)
        intent = recognizer._rule_based_recognition("我的密码是什么")

        assert intent.type == IntentType.INFO_RETRIEVAL


class TestChatConfig:
    """Chat 配置类测试"""

    def test_import_chat_config(self):
        """测试导入配置类"""
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
        assert config.search_candidates_limit == 30

    def test_from_env(self):
        """测试从环境变量加载"""
        from usmsb_sdk.platform.external.meta_agent.config.chat_config import ChatConfig

        config = ChatConfig.from_env()

        assert config.max_history_tokens == 2000
        assert isinstance(config.simple_keywords, list)
        assert isinstance(config.tool_keywords, list)

    def test_message_templates(self):
        """测试消息模板"""
        from usmsb_sdk.platform.external.meta_agent.config.chat_config import ChatConfig

        config = ChatConfig()

        assert "后台任务开始" in config.background_task_start_message
        assert "{result}" in config.background_task_complete_template
        assert "{error}" in config.background_task_error_template

    def test_to_dict(self):
        """测试转换为字典"""
        from usmsb_sdk.platform.external.meta_agent.config.chat_config import ChatConfig

        config = ChatConfig()
        d = config.to_dict()

        assert isinstance(d, dict)
        assert "max_history_tokens" in d
        assert "max_context_tokens" in d


class TestIntegration:
    """集成测试"""

    def test_meta_agent_import(self):
        """测试 MetaAgent 导入"""
        from usmsb_sdk.platform.external.meta_agent import MetaAgent, MetaAgentConfig

        assert MetaAgent is not None
        assert MetaAgentConfig is not None

    def test_meta_agent_config(self):
        """测试 MetaAgentConfig"""
        from usmsb_sdk.platform.external.meta_agent.meta_agent_config import MetaAgentConfig

        config = MetaAgentConfig()

        assert config.name == "MetaAgent"
        assert config.version == "1.0.0"

    def test_sensitive_registry_in_config(self):
        """测试敏感信息注册表在配置中可用"""
        from usmsb_sdk.platform.external.meta_agent.meta_agent_config import MetaAgentConfig

        config = MetaAgentConfig()

        # 验证配置有必要的字段
        assert hasattr(config, "smart_recall_enabled")
        assert hasattr(config, "guardian_enabled")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
