"""
测试工具执行 - 验证工具调用的修复

运行方式:
    cd usmsb-sdk
    python -m pytest tests/test_tool_execution.py -v
"""

import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestToolRegistry:
    """测试工具注册和执行"""

    @pytest.fixture
    def registry(self):
        """创建工具注册表"""
        from usmsb_sdk.platform.external.meta_agent.tools.registry import ToolRegistry
        return ToolRegistry()

    @pytest.fixture
    def Tool(self):
        """导入 Tool 类"""
        from usmsb_sdk.platform.external.meta_agent.tools.registry import Tool as ToolClass
        return ToolClass

    @pytest.fixture
    def mock_session(self):
        """创建模拟的用户会话"""
        session = MagicMock()
        session.wallet_address = "0xtest123456789"
        session._initialized = True

        # 模拟 workspace
        workspace = MagicMock()
        workspace.read_file = AsyncMock(return_value="test content")
        workspace.write_file = AsyncMock(return_value=True)
        workspace.list_files = AsyncMock(return_value=[])
        session.workspace = workspace

        # 模拟 sandbox
        sandbox = MagicMock()
        sandbox.execute = AsyncMock(return_value={"status": "success", "output": "test"})
        session.sandbox = sandbox

        return session

    @pytest.mark.asyncio
    async def test_register_tool(self, registry):
        """测试工具注册"""
        async def test_handler(params):
            return {"result": "ok"}

        tool = Tool(
            name="test_tool",
            description="测试工具",
            handler=test_handler,
        )
        registry.register(tool)

        assert "test_tool" in [t["name"] for t in registry.list_tools()]

    @pytest.mark.asyncio
    async def test_execute_tool_without_session(self, registry):
        """测试执行不需要 session 的工具"""
        async def test_handler(params):
            return {"result": "ok", "params": params}

        tool = Tool(
            name="test_tool",
            description="测试工具",
            handler=test_handler,
            requires_session=False,
        )
        registry.register(tool)

        result = await registry.execute("test_tool", command="echo hello")
        assert result["result"] == "ok"
        assert result["params"]["command"] == "echo hello"

    @pytest.mark.asyncio
    async def test_execute_tool_with_session(self, registry, mock_session):
        """测试执行需要 session 的工具"""
        async def session_handler(session, params):
            return {
                "result": "ok",
                "wallet": session.wallet_address,
                "params": params
            }

        tool = Tool(
            name="session_tool",
            description="需要 session 的工具",
            handler=session_handler,
            requires_session=True,
        )
        registry.register(tool)

        result = await registry.execute("session_tool", session=mock_session, data="test")
        assert result["result"] == "ok"
        assert result["wallet"] == "0xtest123456789"
        assert result["params"]["data"] == "test"

    @pytest.mark.asyncio
    async def test_tool_requires_session_error(self, registry):
        """测试需要 session 但未提供的情况"""
        async def session_handler(session, params):
            return {"result": "ok"}

        tool = Tool(
            name="requires_session_tool",
            description="需要 session 的工具",
            handler=session_handler,
            requires_session=True,
        )
        registry.register(tool)

        with pytest.raises(RuntimeError) as exc_info:
            await registry.execute("requires_session_tool", data="test")

        assert "requires a UserSession" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_tool_schema_anthropic_format(self, registry):
        """测试 Anthropic 格式的工具 schema"""
        async def test_handler(params):
            return {}

        tool = Tool(
            name="test_tool",
            description="测试工具",
            handler=test_handler,
        )
        registry.register(tool)

        schemas = registry.get_tools_schema(provider="anthropic")
        assert len(schemas) == 1
        assert schemas[0]["name"] == "test_tool"
        assert "input_schema" in schemas[0]

    @pytest.mark.asyncio
    async def test_tool_schema_openai_format(self, registry):
        """测试 OpenAI 格式的工具 schema"""
        async def test_handler(params):
            return {}

        tool = Tool(
            name="test_tool",
            description="测试工具",
            handler=test_handler,
        )
        registry.register(tool)

        schemas = registry.get_tools_schema(provider="openai")
        assert len(schemas) == 1
        assert schemas[0]["type"] == "function"
        assert schemas[0]["function"]["name"] == "test_tool"


class TestToolModules:
    """测试各个工具模块"""

    @pytest.mark.asyncio
    async def test_platform_tools(self):
        """测试平台工具"""
        from usmsb_sdk.platform.external.meta_agent.tools.platform import (
            get_platform_tools,
            start_node,
            get_node_status,
        )

        tools = get_platform_tools()
        assert len(tools) > 0

        result = await start_node({})
        assert result["status"] == "success"

        result = await get_node_status({})
        assert result["status"] == "running"

    @pytest.mark.asyncio
    async def test_web_tools(self):
        """测试网页工具"""
        from usmsb_sdk.platform.external.meta_agent.tools.web import (
            get_web_tool_objects,
        )

        tools = get_web_tool_objects()
        assert len(tools) > 0

        # 检查工具是否有正确的 schema
        for tool in tools:
            schema = tool.to_function_schema(provider="anthropic")
            assert "name" in schema
            assert "input_schema" in schema

    @pytest.mark.asyncio
    async def test_system_tools_schema(self):
        """测试系统工具的 schema"""
        from usmsb_sdk.platform.external.meta_agent.tools.system import (
            get_system_tools,
        )

        tools = get_system_tools()
        assert len(tools) > 0

        # 检查需要 session 的工具
        session_required_tools = [t for t in tools if t.requires_session]
        assert len(session_required_tools) > 0

        # 检查不需要 session 的工具
        no_session_tools = [t for t in tools if not t.requires_session]
        assert len(no_session_tools) > 0


class TestToolExecutionIntegration:
    """测试工具执行集成"""

    @pytest.fixture
    def mock_session_manager(self):
        """创建模拟的 session manager"""
        manager = MagicMock()

        async def get_or_create_session(wallet_address):
            session = MagicMock()
            session.wallet_address = wallet_address
            session._initialized = True

            # 模拟 workspace
            workspace = MagicMock()
            workspace.read_file = AsyncMock(return_value="test content")
            workspace.write_file = AsyncMock(return_value=True)
            workspace.list_files = AsyncMock(return_value=[])
            workspace.exists = AsyncMock(return_value=False)
            workspace.create_directory = AsyncMock(return_value=True)
            workspace.delete_file = AsyncMock(return_value=True)
            workspace.get_file_info = AsyncMock(return_value=None)
            workspace.copy_file = AsyncMock(return_value=True)
            workspace.move_file = AsyncMock(return_value=True)
            session.workspace = workspace

            # 模拟 sandbox
            sandbox = MagicMock()
            sandbox.execute = AsyncMock(return_value={"status": "success", "output": "test"})
            session.sandbox = sandbox

            # 模拟 browser_context
            browser_context = MagicMock()
            browser_context.open = AsyncMock(return_value={"status": "success"})
            browser_context.click = AsyncMock(return_value={"status": "success"})
            browser_context.fill = AsyncMock(return_value={"status": "success"})
            browser_context.get_content = AsyncMock(return_value={"content": "test"})
            browser_context.screenshot = AsyncMock(return_value={"status": "success"})
            browser_context.close = AsyncMock(return_value=None)
            session.browser_context = browser_context

            session.update_browser_activity = MagicMock()

            return session

        manager.get_or_create_session = get_or_create_session
        return manager

    @pytest.mark.asyncio
    async def test_execute_tool_calls_with_wallet(self, mock_session_manager):
        """测试带 wallet_address 的工具调用"""
        from usmsb_sdk.platform.external.meta_agent.tools.registry import ToolRegistry, Tool

        registry = ToolRegistry()

        # 注册一个需要 session 的工具
        async def read_file_handler(session, params):
            content = await session.workspace.read_file(params.get("path", ""))
            return {"status": "success", "content": content}

        tool = Tool(
            name="read_file",
            description="读取文件",
            handler=read_file_handler,
            requires_session=True,
        )
        registry.register(tool)

        # 注册一个不需要 session 的工具
        async def health_check_handler(params):
            return {"status": "healthy", "target": params.get("target", "system")}

        tool2 = Tool(
            name="health_check",
            description="健康检查",
            handler=health_check_handler,
            requires_session=False,
        )
        registry.register(tool2)

        # 模拟 _execute_tool_calls 的逻辑
        wallet_address = "0xtest123"
        user_session = await mock_session_manager.get_or_create_session(wallet_address)

        # 执行不需要 session 的工具
        tool_obj = registry.get_tool("health_check")
        if tool_obj.requires_session:
            result = await registry.execute("health_check", session=user_session, target="test")
        else:
            result = await registry.execute("health_check", target="test")

        assert result["status"] == "healthy"

        # 执行需要 session 的工具
        tool_obj = registry.get_tool("read_file")
        if tool_obj.requires_session:
            if user_session is None:
                result = {"error": "需要用户会话"}
            else:
                result = await registry.execute("read_file", session=user_session, path="test.txt")
        else:
            result = await registry.execute("read_file", path="test.txt")

        assert result["status"] == "success"
        assert result["content"] == "test content"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
