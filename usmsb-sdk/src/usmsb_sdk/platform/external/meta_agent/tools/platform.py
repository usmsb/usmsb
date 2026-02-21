"""
Platform Tools - 平台管理工具
"""

from .registry import Tool


def get_platform_tools():
    """获取平台管理工具"""
    return [
        Tool("start_node", "启动节点", start_node),
        Tool("stop_node", "停止节点", stop_node),
        Tool("get_node_status", "获取节点状态", get_node_status),
        Tool("get_config", "获取配置", get_config),
        Tool("update_config", "更新配置", update_config),
        Tool("bind_wallet", "绑定钱包", bind_wallet),
        Tool("register_agent", "注册Agent", register_agent),
        Tool("unregister_agent", "注销Agent", unregister_agent),
        Tool("general_response", "通用响应", general_response),
    ]


async def register_tools(registry):
    """注册平台工具"""
    for tool in get_platform_tools():
        registry.register(tool)


async def start_node(params):
    return {"status": "success", "message": "Node started"}


async def stop_node(params):
    return {"status": "success", "message": "Node stopped"}


async def get_node_status(params):
    return {"status": "running", "cpu": 50, "memory": 60}


async def get_config(params):
    return {"config": {}}


async def update_config(params):
    return {"status": "success"}


async def bind_wallet(params):
    wallet = params.get("wallet_address")
    return {"status": "success", "wallet": wallet}


async def register_agent(params):
    agent_id = params.get("agent_id")
    return {"status": "success", "agent_id": agent_id}


async def unregister_agent(params):
    agent_id = params.get("agent_id")
    return {"status": "success", "agent_id": agent_id}


async def general_response(params):
    message = params.get("message", "好的，我明白了")
    return {"response": message}
