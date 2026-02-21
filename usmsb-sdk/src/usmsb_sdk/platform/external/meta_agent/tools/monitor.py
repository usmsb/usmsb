"""
Monitor Tools - 监控工具
"""

from .registry import Tool


def get_monitor_tools():
    return [
        Tool("health_check", "检查系统或Agent健康状态", health_check),
        Tool("get_metrics", "获取系统指标", get_metrics),
        Tool("set_threshold", "设置告警阈值", set_threshold),
        Tool("get_alerts", "获取告警列表", get_alerts),
    ]


async def register_tools(registry):
    for tool in get_monitor_tools():
        registry.register(tool)


async def health_check(params):
    return {"status": "healthy", "target": params.get("target", "system")}


async def get_metrics(params):
    return {"cpu": 45.5, "memory": 62.3, "disk": 38.1}


async def set_threshold(params):
    return {"status": "success", "metric": params.get("metric")}


async def get_alerts(params):
    return {"alerts": [], "count": 0}
