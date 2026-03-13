"""
Comprehensive tool test plan for meta agent

Run: python -m pytest tests/test_all_tools.py -v --tb=short
"""

import asyncio
import pytest
import sys
import os
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from usmsb_sdk.platform.external.meta_agent.tools.execution import get_execution_tools
from usmsb_sdk.platform.external.meta_agent.tools.system import get_system_tools
from usmsb_sdk.platform.external.meta_agent.tools.web import get_web_tools
from usmsb_sdk.platform.external.meta_agent.tools.platform import get_platform_tools
from usmsb_sdk.platform.external.meta_agent.tools.monitor import get_monitor_tools
from usmsb_sdk.platform.external.meta_agent.tools.blockchain import get_blockchain_tools
from usmsb_sdk.platform.external.meta_agent.tools.ipfs import get_ipfs_tools
from usmsb_sdk.platform.external.meta_agent.tools.database import get_database_tools
from usmsb_sdk.platform.external.meta_agent.tools.ui import get_ui_tools
from usmsb_sdk.platform.external.meta_agent.tools.governance import get_governance_tools
from usmsb_sdk.platform.external.meta_agent.tools.system_agents import get_system_agents_tools
from usmsb_sdk.platform.external.meta_agent.tools.precise_matching import get_precise_matching_tools
import inspect


def create_mock_session():
    """Create a mock user session"""
    session = MagicMock()
    session.wallet_address = "0xtest123456789abcdef"
    session.session_id = "test_session_001"
    session._initialized = True

    workspace = MagicMock()
    workspace.read_file = AsyncMock(return_value="test content")
    workspace.write_file = AsyncMock(return_value=True)
    workspace.list_files = AsyncMock(return_value=["file1.txt", "file2.txt"])
    workspace.create_directory = AsyncMock(return_value=True)
    workspace.delete_file = AsyncMock(return_value=True)
    workspace.copy_file = AsyncMock(return_value=True)
    workspace.move_file = AsyncMock(return_value=True)
    workspace.get_file_info = AsyncMock(return_value={"size": 100, "modified": "2024-01-01"})
    workspace.search_files = AsyncMock(return_value=["file1.txt"])
    workspace.download_file = AsyncMock(return_value=True)
    workspace.get_storage_usage = AsyncMock(return_value={"used": 1000, "limit": 10000000})
    session.workspace = workspace

    sandbox = MagicMock()
    sandbox.execute = AsyncMock(
        return_value=MagicMock(
            success=True,
            stdout="test output",
            stderr="",
            result="test result",
            error=None,
            execution_time=0.1,
        )
    )
    sandbox.run_command = AsyncMock(
        return_value=MagicMock(
            success=True, stdout="command output", stderr="", error=None, execution_time=0.1
        )
    )
    sandbox.workspace_dir = Path("/data/users/test/workspace")
    sandbox.sandbox_dir = Path("/data/users/test/sandbox")
    session.sandbox = sandbox

    browser = MagicMock()
    browser.open = AsyncMock(return_value={"status": "success", "url": "http://example.com"})
    browser.click = AsyncMock(return_value={"status": "success"})
    browser.fill = AsyncMock(return_value={"status": "success"})
    browser.get_content = AsyncMock(
        return_value={"status": "success", "content": "<html>test</html>"}
    )
    browser.screenshot = AsyncMock(
        return_value={"status": "success", "path": "/tmp/screenshot.png"}
    )
    browser.close = AsyncMock(return_value={"status": "success"})
    session.browser = browser

    return session


async def call_tool_handler(tool, session, params):
    """Call tool handler with correct signature"""
    handler = tool.handler
    sig = inspect.signature(handler)
    param_names = list(sig.parameters.keys())

    # Check if first param is 'session' or 'self'
    if param_names and param_names[0] in ("session", "self"):
        if param_names[0] == "session":
            return await handler(session, params)
        else:
            return await handler(params)
    else:
        return await handler(params)


class TestExecutionTools:
    """Test execution tools"""

    @pytest.fixture
    def session(self):
        return create_mock_session()

    @pytest.mark.asyncio
    async def test_execute_python(self, session):
        tools = get_execution_tools()
        tool = next((t for t in tools if hasattr(t, "name") and t.name == "execute_python"), None)
        if tool:
            result = await call_tool_handler(tool, session, {"code": "print('hello')"})
            assert result is not None

    @pytest.mark.asyncio
    async def test_run_command(self, session):
        tools = get_execution_tools()
        tool = next((t for t in tools if hasattr(t, "name") and t.name == "run_command"), None)
        if tool:
            result = await call_tool_handler(tool, session, {"command": "echo hello"})
            assert result is not None

    @pytest.mark.asyncio
    async def test_browser_open(self, session):
        tools = get_execution_tools()
        tool = next((t for t in tools if hasattr(t, "name") and t.name == "browser_open"), None)
        if tool:
            result = await call_tool_handler(tool, session, {"url": "http://example.com"})
            assert result is not None

    @pytest.mark.asyncio
    async def test_start_jupyter(self, session):
        tools = get_execution_tools()
        tool = next((t for t in tools if hasattr(t, "name") and t.name == "start_jupyter"), None)
        if tool:
            result = await call_tool_handler(tool, session, {"port": 8888})
            assert result is not None


class TestSystemTools:
    """Test system tools"""

    @pytest.fixture
    def session(self):
        return create_mock_session()

    @pytest.mark.asyncio
    async def test_read_file(self, session):
        tools = get_system_tools()
        tool = next((t for t in tools if hasattr(t, "name") and t.name == "read_file"), None)
        if tool:
            result = await call_tool_handler(tool, session, {"path": "/test/file.txt"})
            assert result is not None

    @pytest.mark.asyncio
    async def test_write_file(self, session):
        tools = get_system_tools()
        tool = next((t for t in tools if hasattr(t, "name") and t.name == "write_file"), None)
        if tool:
            result = await call_tool_handler(
                tool, session, {"path": "/test/file.txt", "content": "hello"}
            )
            assert result is not None

    @pytest.mark.asyncio
    async def test_list_directory(self, session):
        tools = get_system_tools()
        tool = next((t for t in tools if hasattr(t, "name") and t.name == "list_directory"), None)
        if tool:
            result = await call_tool_handler(tool, session, {"path": "/test"})
            assert result is not None

    @pytest.mark.asyncio
    async def test_create_directory(self, session):
        tools = get_system_tools()
        tool = next((t for t in tools if hasattr(t, "name") and t.name == "create_directory"), None)
        if tool:
            result = await call_tool_handler(tool, session, {"path": "/test/newdir"})
            assert result is not None


class TestWebTools:
    """Test web tools"""

    @pytest.fixture
    def session(self):
        return create_mock_session()

    @pytest.mark.asyncio
    async def test_search_web(self, session):
        tools = get_web_tools()
        tool = next((t for t in tools if hasattr(t, "name") and t.name == "search_web"), None)
        if tool:
            result = await call_tool_handler(tool, session, {"query": "test query"})
            assert result is not None

    @pytest.mark.asyncio
    async def test_fetch_url(self, session):
        tools = get_web_tools()
        tool = next((t for t in tools if hasattr(t, "name") and t.name == "fetch_url"), None)
        if tool:
            result = await call_tool_handler(tool, session, {"url": "http://example.com"})
            assert result is not None

    @pytest.mark.asyncio
    async def test_parse_html(self, session):
        tools = get_web_tools()
        tool = next((t for t in tools if hasattr(t, "name") and t.name == "parse_html"), None)
        if tool:
            result = await call_tool_handler(
                tool, session, {"html": "<html></html>", "selector": "body"}
            )
            assert result is not None


class TestPlatformTools:
    """Test platform tools"""

    @pytest.fixture
    def session(self):
        return create_mock_session()

    @pytest.mark.asyncio
    async def test_get_user_info(self, session):
        tools = get_platform_tools()
        tool = next((t for t in tools if hasattr(t, "name") and t.name == "get_user_info"), None)
        if tool:
            result = await call_tool_handler(tool, session, {"user_id": "123"})
            assert result is not None

    @pytest.mark.asyncio
    async def test_bind_wallet(self, session):
        tools = get_platform_tools()
        tool = next((t for t in tools if hasattr(t, "name") and t.name == "bind_wallet"), None)
        if tool:
            result = await call_tool_handler(tool, session, {"wallet_address": "0x123"})
            assert result is not None


class TestMonitorTools:
    """Test monitor tools"""

    @pytest.fixture
    def session(self):
        return create_mock_session()

    @pytest.mark.asyncio
    async def test_health_check(self, session):
        tools = get_monitor_tools()
        tool = next((t for t in tools if hasattr(t, "name") and t.name == "health_check"), None)
        if tool:
            result = await call_tool_handler(tool, session, {})
            assert result is not None

    @pytest.mark.asyncio
    async def test_get_system_metrics(self, session):
        tools = get_monitor_tools()
        tool = next(
            (t for t in tools if hasattr(t, "name") and t.name == "get_system_metrics"), None
        )
        if tool:
            result = await call_tool_handler(tool, session, {})
            assert result is not None


class TestBlockchainTools:
    """Test blockchain tools"""

    @pytest.fixture
    def session(self):
        return create_mock_session()

    @pytest.mark.asyncio
    async def test_get_balance(self, session):
        tools = get_blockchain_tools()
        tool = next((t for t in tools if hasattr(t, "name") and t.name == "get_balance"), None)
        if tool:
            result = await call_tool_handler(tool, session, {"address": "0x123"})
            assert result is not None

    @pytest.mark.asyncio
    async def test_get_chain_info(self, session):
        tools = get_blockchain_tools()
        tool = next((t for t in tools if hasattr(t, "name") and t.name == "get_chain_info"), None)
        if tool:
            result = await call_tool_handler(tool, session, {})
            assert result is not None


class TestDatabaseTools:
    """Test database tools"""

    @pytest.fixture
    def session(self):
        return create_mock_session()

    @pytest.mark.asyncio
    async def test_query_db(self, session):
        tools = get_database_tools()
        tool = next((t for t in tools if hasattr(t, "name") and t.name == "query_db"), None)
        if tool:
            result = await call_tool_handler(tool, session, {"query": "SELECT * FROM test"})
            assert result is not None

    @pytest.mark.asyncio
    async def test_insert_db(self, session):
        tools = get_database_tools()
        tool = next((t for t in tools if hasattr(t, "name") and t.name == "insert_db"), None)
        if tool:
            result = await call_tool_handler(
                tool, session, {"table": "test", "data": {"key": "value"}}
            )
            assert result is not None


class TestGovernanceTools:
    """Test governance tools"""

    @pytest.fixture
    def session(self):
        return create_mock_session()

    @pytest.mark.asyncio
    async def test_list_proposals(self, session):
        tools = get_governance_tools()
        tool = next((t for t in tools if hasattr(t, "name") and t.name == "list_proposals"), None)
        if tool:
            result = await call_tool_handler(tool, session, {})
            assert result is not None

    @pytest.mark.asyncio
    async def test_vote(self, session):
        tools = get_governance_tools()
        tool = next((t for t in tools if hasattr(t, "name") and t.name == "vote"), None)
        if tool:
            result = await call_tool_handler(tool, session, {"proposal_id": "1", "vote": "yes"})
            assert result is not None


class TestIPFSTools:
    """Test IPFS tools"""

    @pytest.fixture
    def session(self):
        return create_mock_session()

    @pytest.mark.asyncio
    async def test_upload_to_ipfs(self, session):
        tools = get_ipfs_tools()
        tool = next((t for t in tools if hasattr(t, "name") and t.name == "upload_to_ipfs"), None)
        if tool:
            result = await call_tool_handler(tool, session, {"content": "test content"})
            assert result is not None

    @pytest.mark.asyncio
    async def test_download_from_ipfs(self, session):
        tools = get_ipfs_tools()
        tool = next(
            (t for t in tools if hasattr(t, "name") and t.name == "download_from_ipfs"), None
        )
        if tool:
            result = await call_tool_handler(tool, session, {"cid": "QmTest"})
            assert result is not None


class TestToolsCount:
    """Test tool count"""

    def test_tool_count(self):
        """Verify tool count"""
        all_tools = []
        all_tools.extend(get_execution_tools())
        all_tools.extend(get_system_tools())
        all_tools.extend(get_web_tools())
        all_tools.extend(get_platform_tools())
        all_tools.extend(get_monitor_tools())
        all_tools.extend(get_blockchain_tools())
        all_tools.extend(get_ipfs_tools())
        all_tools.extend(get_database_tools())
        all_tools.extend(get_ui_tools())
        all_tools.extend(get_governance_tools())
        all_tools.extend(get_system_agents_tools())
        all_tools.extend(get_precise_matching_tools())

        tool_names = [t.name if hasattr(t, "name") else t.get("name") for t in all_tools]
        unique_tools = set(tool_names)

        print(f"\nTotal tools: {len(all_tools)}")
        print(f"Unique tools: {len(unique_tools)}")

        # Should have 90+ tools
        assert len(all_tools) >= 90, f"Expected 90+ tools, got {len(all_tools)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
