"""
System Agents Module

This module provides built-in system agents for the USMSB SDK platform.
System agents are platform-level agents that provide essential services
such as monitoring, routing, logging, and recommendations.

Available System Agents:
    - MonitorAgent: System and node health monitoring
    - RecommenderAgent: Agent recommendation service
    - RouterAgent: Message routing and load balancing
    - LoggerAgent: Centralized logging service

Usage:
    from usmsb_sdk.platform.external.system_agents import (
        MonitorAgent,
        RecommenderAgent,
        RouterAgent,
        LoggerAgent,
        BaseSystemAgent,
    )

    # Create a monitor agent
    monitor = MonitorAgent(config)
    await monitor.start()
"""

from usmsb_sdk.platform.external.system_agents.base_system_agent import (
    BaseSystemAgent,
    SystemAgentConfig,
    SystemAgentPermission,
)
from usmsb_sdk.platform.external.system_agents.logger_agent import LoggerAgent
from usmsb_sdk.platform.external.system_agents.monitor_agent import MonitorAgent
from usmsb_sdk.platform.external.system_agents.recommender_agent import RecommenderAgent
from usmsb_sdk.platform.external.system_agents.router_agent import RouterAgent

__all__ = [
    # Base classes
    "BaseSystemAgent",
    "SystemAgentPermission",
    "SystemAgentConfig",
    # System agents
    "MonitorAgent",
    "RecommenderAgent",
    "RouterAgent",
    "LoggerAgent",
]

__version__ = "1.0.0"
