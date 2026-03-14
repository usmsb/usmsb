"""
System Agents Tools - 将 system_agents 包装为 meta_agent 的工具
"""

import logging
from typing import Any

from .registry import Tool

logger = logging.getLogger(__name__)

# 全局 system agent 实例
_recommender_agent = None
_router_agent = None
_monitor_agent = None
_logger_agent = None


def _get_recommender_agent():
    """获取或创建推荐系统 agent"""
    global _recommender_agent
    if _recommender_agent is None:
        from usmsb_sdk.agent_sdk.agent_config import AgentConfig
        from usmsb_sdk.platform.external.system_agents.recommender_agent import RecommenderAgent

        config = AgentConfig(
            agent_id="meta-agent-recommender",
            name="MetaAgentRecommender",
            description="Recommendation service for meta-agent",
        )
        _recommender_agent = RecommenderAgent(config)
    return _recommender_agent


def _get_router_agent():
    """获取或创建路由 agent"""
    global _router_agent
    if _router_agent is None:
        from usmsb_sdk.agent_sdk.agent_config import AgentConfig
        from usmsb_sdk.platform.external.system_agents.router_agent import RouterAgent

        config = AgentConfig(
            agent_id="meta-agent-router",
            name="MetaAgentRouter",
            description="Routing service for meta-agent",
        )
        _router_agent = RouterAgent(config)
    return _router_agent


def _get_monitor_agent():
    """获取或创建监控 agent"""
    global _monitor_agent
    if _monitor_agent is None:
        from usmsb_sdk.agent_sdk.agent_config import AgentConfig
        from usmsb_sdk.platform.external.system_agents.monitor_agent import MonitorAgent

        config = AgentConfig(
            agent_id="meta-agent-monitor",
            name="MetaAgentMonitor",
            description="Monitoring service for meta-agent",
        )
        _monitor_agent = MonitorAgent(config)
    return _monitor_agent


def _get_logger_agent():
    """获取或创建日志 agent"""
    global _logger_agent
    if _logger_agent is None:
        from usmsb_sdk.agent_sdk.agent_config import AgentConfig
        from usmsb_sdk.platform.external.system_agents.logger_agent import LoggerAgent

        config = AgentConfig(
            agent_id="meta-agent-logger",
            name="MetaAgentLogger",
            description="Logging service for meta-agent",
        )
        _logger_agent = LoggerAgent(config)
    return _logger_agent


# ==================== 工具函数 ====================


async def recommend_agents(params: dict[str, Any]) -> dict[str, Any]:
    """根据任务描述推荐合适的 agent"""
    agent = _get_recommender_agent()
    return await agent.execute_skill("recommend", params)


async def search_agents(params: dict[str, Any]) -> dict[str, Any]:
    """按条件搜索 agent"""
    agent = _get_recommender_agent()
    return await agent.execute_skill("search", params)


async def rate_agent(params: dict[str, Any]) -> dict[str, Any]:
    """给 agent 评分"""
    agent = _get_recommender_agent()
    return await agent.execute_skill("rate", params)


async def get_recommendation_history(params: dict[str, Any]) -> dict[str, Any]:
    """获取推荐历史"""
    agent = _get_recommender_agent()
    return await agent.execute_skill("get_history", params)


async def route_message(params: dict[str, Any]) -> dict[str, Any]:
    """路由消息到目标"""
    agent = _get_router_agent()
    return await agent.execute_skill("route", params)


async def get_load_balance_status(params: dict[str, Any]) -> dict[str, Any]:
    """获取负载均衡状态"""
    agent = _get_router_agent()
    return await agent.execute_skill("balance", params)


async def get_route_info(params: dict[str, Any]) -> dict[str, Any]:
    """获取路由信息"""
    agent = _get_router_agent()
    return await agent.execute_skill("get_routes", params)


async def get_system_health(params: dict[str, Any]) -> dict[str, Any]:
    """获取系统健康状态"""
    agent = _get_monitor_agent()
    return await agent.execute_skill("health_check", params)


async def get_system_metrics(params: dict[str, Any]) -> dict[str, Any]:
    """获取系统指标"""
    agent = _get_monitor_agent()
    return await agent.execute_skill("get_metrics", params)


async def get_alerts(params: dict[str, Any]) -> dict[str, Any]:
    """获取告警列表"""
    agent = _get_monitor_agent()
    return await agent.execute_skill("get_alerts", params)


async def query_logs(params: dict[str, Any]) -> dict[str, Any]:
    """查询日志"""
    agent = _get_logger_agent()
    return await agent.execute_skill("query", params)


# ==================== 工具定义 ====================


def get_system_agents_tools():
    """获取 system agents 工具列表"""

    # 注意：handler 需要是 async 函数，或者使用 async wrapper
    async def recommend_agents_wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return await recommend_agents(params)

    async def search_agents_wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return await search_agents(params)

    async def rate_agent_wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return await rate_agent(params)

    async def get_recommendation_history_wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return await get_recommendation_history(params)

    async def route_message_wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return await route_message(params)

    async def get_load_balance_status_wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return await get_load_balance_status(params)

    async def get_route_info_wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return await get_route_info(params)

    async def get_system_health_wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return await get_system_health(params)

    async def get_system_metrics_wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return await get_system_metrics(params)

    async def get_alerts_wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return await get_alerts(params)

    async def query_logs_wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return await query_logs(params)

    return [
        # 推荐系统工具
        Tool(
            "recommend_agents",
            "根据任务描述推荐合适的Agent",
            recommend_agents_wrapper,
        ),
        Tool(
            "search_agents",
            "按条件搜索Agent",
            search_agents_wrapper,
        ),
        Tool(
            "rate_agent",
            "给Agent评分",
            rate_agent_wrapper,
        ),
        Tool(
            "get_recommendation_history",
            "获取推荐历史",
            get_recommendation_history_wrapper,
        ),
        # 路由工具
        Tool(
            "route_message",
            "路由消息到目标",
            route_message_wrapper,
        ),
        Tool(
            "get_load_balance_status",
            "获取负载均衡状态",
            get_load_balance_status_wrapper,
        ),
        Tool(
            "get_route_info",
            "获取路由信息",
            get_route_info_wrapper,
        ),
        # 监控工具
        Tool(
            "get_system_health",
            "获取系统健康状态",
            get_system_health_wrapper,
        ),
        Tool(
            "get_system_metrics",
            "获取系统指标",
            get_system_metrics_wrapper,
        ),
        Tool(
            "get_alerts",
            "获取告警列表",
            get_alerts_wrapper,
        ),
        # 日志工具
        Tool(
            "query_logs",
            "查询系统日志",
            query_logs_wrapper,
        ),
    ]


async def register_tools(registry):
    """注册 system agents 工具"""
    tools = get_system_agents_tools()
    for tool in tools:
        registry.register(tool)
    logger.info(f"Registered {len(tools)} system agent tools")
