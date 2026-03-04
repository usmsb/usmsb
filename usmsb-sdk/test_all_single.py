"""
逐一测试所有工具
"""

import sys
import asyncio

sys.path.insert(0, "usmsb-sdk/src")

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

from unittest.mock import MagicMock, AsyncMock
from pathlib import Path
import inspect


def create_mock_session():
    session = MagicMock()
    session.wallet_address = "0xtest123456789abcdef"
    session.session_id = "test_session_001"
    session._initialized = True
    session.workspace = MagicMock()
    session.workspace.read_file = AsyncMock(return_value="test content")
    session.workspace.write_file = AsyncMock(return_value=True)
    session.workspace.list_files = AsyncMock(return_value=["file1.txt"])
    session.workspace.create_directory = AsyncMock(return_value=True)
    session.workspace.delete_file = AsyncMock(return_value=True)
    session.workspace.copy_file = AsyncMock(return_value=True)
    session.workspace.move_file = AsyncMock(return_value=True)
    session.workspace.get_file_info = AsyncMock(return_value={"size": 100})
    session.workspace.search_files = AsyncMock(return_value=["file1.txt"])
    session.workspace.download_file = AsyncMock(return_value=True)
    session.workspace.get_storage_usage = AsyncMock(return_value={"used": 1000, "limit": 10000000})
    session.sandbox = MagicMock()
    session.sandbox.execute = AsyncMock(
        return_value=MagicMock(success=True, stdout="test", result="test")
    )
    session.sandbox.run_command = AsyncMock(return_value=MagicMock(success=True, stdout="test"))
    session.sandbox.workspace_dir = Path("/test")
    session.browser = MagicMock()
    session.browser.open = AsyncMock(return_value={"status": "success"})
    session.browser.click = AsyncMock(return_value={"status": "success"})
    session.browser.fill = AsyncMock(return_value={"status": "success"})
    session.browser.get_content = AsyncMock(
        return_value={"status": "success", "content": "<html>test</html>"}
    )
    session.browser.screenshot = AsyncMock(return_value={"status": "success"})
    session.browser.close = AsyncMock(return_value={"status": "success"})
    return session


async def call_tool(tool, session):
    """调用工具处理器"""
    try:
        handler = tool.handler
        sig = inspect.signature(handler)
        params = list(sig.parameters.keys())

        # 确定调用方式
        if not params:
            result = await handler()
        elif params[0] in ("session", "self"):
            if len(params) == 1:
                result = await handler(session)
            else:
                result = await handler(session, {})
        else:
            result = await handler({})
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def test_all_tools():
    session = create_mock_session()

    # 收集所有工具
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

    # 过滤掉 dict 类型的工具
    tool_objs = [t for t in all_tools if hasattr(t, "name")]

    print(f"Total tools to test: {len(tool_objs)}\n")

    passed = 0
    failed = 0
    results = []

    for tool in tool_objs:
        try:
            result = await call_tool(tool, session)
            if result and isinstance(result, dict):
                status = result.get("status", "unknown")
                if status in ("success", "healthy", "running") or "error" not in str(result):
                    passed += 1
                    results.append(f"✓ {tool.name}")
                else:
                    failed += 1
                    results.append(f"✗ {tool.name}: {result.get('message', result)[:50]}")
            else:
                passed += 1
                results.append(f"✓ {tool.name}")
        except Exception as e:
            failed += 1
            results.append(f"✗ {tool.name}: {str(e)[:50]}")

    print("=== Test Results ===")
    for r in results:
        print(r)

    print(f"\n=== Summary ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")


if __name__ == "__main__":
    asyncio.run(test_all_tools())
