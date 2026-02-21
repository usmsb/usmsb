"""
Tools 模块 - 所有工具注册
"""

import logging
from .registry import Tool, ToolRegistry

logger = logging.getLogger(__name__)


async def register_tools(registry):
    """注册所有工具"""
    from .platform import get_platform_tools
    from .monitor import get_monitor_tools
    from .blockchain import get_blockchain_tools
    from .ipfs import get_ipfs_tools
    from .database import get_database_tools
    from .ui import get_ui_tools
    from .governance import get_governance_tools
    from .system import get_system_tools
    from .web import get_web_tool_objects
    from .execution import get_execution_tools
    from .system_agents import get_system_agents_tools

    all_tools = []
    all_tools.extend(get_platform_tools())
    all_tools.extend(get_monitor_tools())
    all_tools.extend(get_blockchain_tools())
    all_tools.extend(get_ipfs_tools())
    all_tools.extend(get_database_tools())
    all_tools.extend(get_ui_tools())
    all_tools.extend(get_governance_tools())
    all_tools.extend(get_system_tools())
    all_tools.extend(get_web_tool_objects())
    all_tools.extend(get_execution_tools())
    all_tools.extend(get_system_agents_tools())

    for tool in all_tools:
        registry.register(tool)

    logger.info(f"Registered {len(all_tools)} tools")


def get_platform_tools():
    """平台管理工具"""
    return [
        Tool("start_node", "启动节点", lambda p: {"status": "success"}),
        Tool("stop_node", "停止节点", lambda p: {"status": "success"}),
        Tool("get_node_status", "获取节点状态", lambda p: {"status": "running"}),
        Tool("get_config", "获取配置", lambda p: {"config": {}}),
        Tool("update_config", "更新配置", lambda p: {"status": "success"}),
        Tool("bind_wallet", "绑定钱包", lambda p: {"status": "success"}),
        Tool("register_agent", "注册Agent", lambda p: {"status": "success"}),
    ]


__all__ = ["register_tools", "Tool", "ToolRegistry"]
