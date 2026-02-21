"""
Supply Chain Demo - Shared Module
供应链报价Demo - 共享模块

更新说明:
---------
BaseAgent 现在支持 SDK HTTP Server 和 P2P Server。

启动方式:
    # 方式1: 使用 HTTP + P2P Server (生产推荐)
    from shared.base_agent import run_agent_with_both
    await run_agent_with_both(
        agent,
        http_port=5101,
        p2p_port=9101,
        platform_url="http://localhost:8000",
        bootstrap_peers=[("127.0.0.1", 9101)],
    )

    # 方式2: 使用 HTTP Server (简单模式)
    from shared.base_agent import run_agent_with_http_sdk
    await run_agent_with_http_sdk(agent, http_port=5101)

    # 方式3: 使用 P2P Server (去中心化)
    from shared.base_agent import BaseAgent
    agent = MyAgent("config.yaml")
    await agent.start_with_p2p(port=9101)

    # 方式4: 同时启动 HTTP 和 P2P (实例方法)
    await agent.start_with_both(http_port=5101, p2p_port=9101)

    # 方式5: 传统消息总线
    from shared.base_agent import run_agent
    await run_agent(agent)

环境变量:
    HTTP_PORT - HTTP 服务端口 (默认: 5101)
    P2P_PORT - P2P 服务端口 (默认: 9101)
    ENABLE_P2P - 是否启用 P2P (默认: true)
    PLATFORM_URL - 平台注册 URL (默认: http://localhost:8000)
    BOOTSTRAP_PEERS - P2P 引导节点，逗号分隔 (格式: host:port,host:port)
"""

from .protocols import (
    MessageType,
    MessagePriority,
    BaseMessage,
    QuoteRequest,
    QuoteResponse,
    PricePredictionItem,
    PricePrediction,
    MatchResult,
    create_message,
)

from .base_agent import (
    BaseAgent,
    AgentConfig,
    run_agent,
    run_agent_with_http_sdk,
    run_agent_with_both,
)

# HTTP Server 支持 (来自 SDK)
# 注意: 需要确保 SDK 模块可用
try:
    from usmsb_sdk.agent_sdk.http_server import HTTPServer, run_agent_with_http
    from usmsb_sdk.agent_sdk.p2p_server import P2PServer, run_agent_with_p2p

    _HTTP_AVAILABLE = True
    _P2P_AVAILABLE = True
except ImportError:
    _HTTP_AVAILABLE = False
    _P2P_AVAILABLE = False
    HTTPServer = None
    run_agent_with_http = None
    P2PServer = None
    run_agent_with_p2p = None

__all__ = [
    # 协议相关
    "MessageType",
    "MessagePriority",
    "BaseMessage",
    "QuoteRequest",
    "QuoteResponse",
    "PricePredictionItem",
    "PricePrediction",
    "MatchResult",
    "create_message",
    # Agent 相关
    "BaseAgent",
    "AgentConfig",
    "run_agent",
    "run_agent_with_http_sdk",
    "run_agent_with_both",
    # SDK HTTP Server
    "HTTPServer",
    "run_agent_with_http",
    # SDK P2P Server
    "P2PServer",
    "run_agent_with_p2p",
]
