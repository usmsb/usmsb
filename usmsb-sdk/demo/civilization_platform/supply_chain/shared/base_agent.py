"""
Supply Chain Demo - Base Agent

提供所有 Agent 的基类实现，集成 SDK BaseAgent 和消息总线。

迁移说明:
---------
此 BaseAgent 现在继承自 SDK 的 usmsb_sdk.agent_sdk.BaseAgent，
同时保留了 Demo 特有的功能（如 Redis 消息总线）。

启动方式更新:
    # 方式1: 使用 SDK HTTP Server (推荐)
    from usmsb_sdk.agent_sdk.http_server import run_agent_with_http
    await run_agent_with_http(agent, http_port=5101)

    # 方式2: 使用传统消息总线
    from shared.base_agent import run_agent
    await run_agent(agent)
"""

import asyncio
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import yaml

# 添加 SDK 路径
sdk_path = str(Path(__file__).parent.parent.parent.parent.parent / "src")
if sdk_path not in sys.path:
    sys.path.insert(0, sdk_path)

# 导入 SDK BaseAgent 和相关组件
from usmsb_sdk.agent_sdk import BaseAgent as SDKBaseAgent
from usmsb_sdk.agent_sdk import AgentConfig as SDKAgentConfig
from usmsb_sdk.agent_sdk import (
    SkillDefinition,
    CapabilityDefinition,
    ProtocolType,
)
from usmsb_sdk.agent_sdk.http_server import HTTPServer, run_agent_with_http
from usmsb_sdk.agent_sdk.p2p_server import (
    P2PServer as SDKP2PServer,
    run_agent_with_p2p as sdk_run_agent_with_p2p,
)
from usmsb_sdk.agent_sdk.communication import Message as SDKMessage, MessageType, Session

# 保留 Demo 特有的消息总线（用于 Agent 间通信）
from shared.message_bus import Message, MessageBus, get_message_bus, shutdown_message_bus

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Agent 配置 (Demo 特有配置，兼容旧格式)"""

    agent_id: str
    agent_name: str
    agent_type: str
    description: str = ""
    version: str = "1.0.0"

    # 平台配置
    platform_url: str = "http://localhost:8080"
    auto_register: bool = True
    heartbeat_interval: int = 30

    # Redis 配置
    redis_url: str = "redis://localhost:6379"

    # 服务配置
    server_host: str = "0.0.0.0"
    server_port: int = 8000

    # 超时配置
    request_timeout: int = 30
    response_timeout: int = 10

    # 日志级别
    log_level: str = "INFO"

    # 额外配置
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, config_path: str) -> "AgentConfig":
        """从 YAML 文件加载配置"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            data = {}

        # 解析环境变量
        data = cls._resolve_env_vars(data)

        agent_config = data.get("agent", {})
        platform_config = data.get("platform", {})
        redis_config = data.get("redis", {})
        server_config = data.get("server", {})
        timeout_config = data.get("timeouts", {})
        logging_config = data.get("logging", {})

        return cls(
            agent_id=agent_config.get("id", "agent_001"),
            agent_name=agent_config.get("name", "Agent"),
            agent_type=agent_config.get("type", "unknown"),
            description=agent_config.get("description", ""),
            version=agent_config.get("version", "1.0.0"),
            platform_url=platform_config.get("url", "http://localhost:8080"),
            auto_register=platform_config.get("auto_register", True),
            heartbeat_interval=platform_config.get("heartbeat_interval", 30),
            redis_url=redis_config.get("url", "redis://localhost:6379"),
            server_host=server_config.get("host", "0.0.0.0"),
            server_port=server_config.get("port", 8000),
            request_timeout=timeout_config.get("request_timeout", 30),
            response_timeout=timeout_config.get("response_timeout", 10),
            log_level=logging_config.get("level", "INFO"),
            extra=data,
        )

    @staticmethod
    def _resolve_env_vars(data: Any) -> Any:
        """递归解析环境变量"""
        if isinstance(data, dict):
            return {k: AgentConfig._resolve_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [AgentConfig._resolve_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
            # 解析 ${VAR_NAME:default} 格式
            content = data[2:-1]
            if ":" in content:
                var_name, default = content.split(":", 1)
            else:
                var_name, default = content, ""
            return os.environ.get(var_name, default)
        return data

    def to_sdk_config(self) -> SDKAgentConfig:
        """转换为 SDK AgentConfig"""
        # 根据 agent_type 确定 category
        category_map = {
            "supplier": "supply_chain",
            "buyer": "supply_chain",
            "predictor": "analytics",
            "match": "matching",
        }
        category = category_map.get(self.agent_type.lower(), "general")

        # 创建 SDK 配置
        sdk_config = SDKAgentConfig(
            name=self.agent_name,
            description=self.description or f"{self.agent_name} - {self.agent_type}",
            agent_id=self.agent_id,
            version=self.version,
            protocols={},  # 使用空字典，让 SDK 自动初始化默认协议
            skills=[],
            capabilities=[
                CapabilityDefinition(
                    name=self.agent_type,
                    description=f"Agent type: {self.agent_type}",
                    category=category,
                )
            ],
            auto_register=False,  # 我们自己控制注册
            heartbeat_interval=self.heartbeat_interval,
            log_level=self.log_level,
        )

        # 禁用所有协议的自动启动 (我们手动控制服务器启动)
        for protocol_type in sdk_config.protocols:
            sdk_config.protocols[protocol_type].enabled = False

        return sdk_config


class BaseAgent(SDKBaseAgent):
    """
    Demo Agent 基类 - 继承 SDK BaseAgent

    此类继承自 SDK BaseAgent，同时提供 Demo 特有的功能。

    主要功能:
    - 继承 SDK BaseAgent 的所有能力
    - 配置管理（从 YAML 加载）
    - 消息通信（基于 Redis 消息总线）
    - 生命周期管理
    - 错误处理和重试
    - 支持 SDK HTTP Server

    使用方式:
        # 方式1: 传统消息总线模式
        class MyAgent(BaseAgent):
            async def on_start(self):
                self.subscribe("my_topic")

        agent = MyAgent("config.yaml")
        await run_agent(agent)

        # 方式2: HTTP Server 模式 (推荐)
        agent = MyAgent("config.yaml")
        await run_agent_with_http_sdk(agent, http_port=5101)
    """

    def __init__(self, config_path: str = "config.yaml"):
        # 加载 Demo 配置
        self._demo_config = AgentConfig.from_yaml(config_path)

        # 转换为 SDK AgentConfig
        sdk_config = self._demo_config.to_sdk_config()

        # 调用 SDK BaseAgent 初始化
        super().__init__(sdk_config)

        # Demo 特有属性
        self.agent_type = self._demo_config.agent_type
        self._demo_message_handlers: Dict[str, Callable] = {}
        self._message_bus: Optional[MessageBus] = None
        self._http_server: Optional[HTTPServer] = None
        self._p2p_server: Optional[SDKP2PServer] = None
        self._background_tasks: List[asyncio.Task] = []

        # 设置日志
        self._setup_logging()

        # 注册默认消息处理器
        self._register_default_handlers()

        logger.info(f"{self.__class__.__name__} initialized: {self.agent_id}")

    # ========== SDK BaseAgent 抽象方法实现 ==========

    async def initialize(self) -> None:
        """SDK BaseAgent 初始化方法"""
        # Demo 的初始化逻辑在 on_start 中
        pass

    async def handle_message(
        self, message: SDKMessage, session: Optional[Session] = None
    ) -> Optional[SDKMessage]:
        """
        SDK BaseAgent 消息处理方法

        Args:
            message: SDK Message 对象
            session: 可选的会话对象

        Returns:
            响应消息（可选）
        """
        # 转换 SDK Message 为 Demo 消息格式
        demo_message = {
            "message_type": getattr(message.type, "value", str(message.type))
            if hasattr(message, "type")
            else "unknown",
            "message_id": getattr(message, "message_id", ""),
            "sender_id": message.sender_id if hasattr(message, "sender_id") else "unknown",
            "receiver_id": message.receiver_id
            if hasattr(message, "receiver_id")
            else self.agent_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payload": message.content if hasattr(message, "content") else {},
        }

        # 调用 Demo 消息处理器
        response = await self._handle_demo_message(demo_message)

        if response:
            # 转换响应为 SDK Message
            return SDKMessage(
                type=MessageType.RESPONSE,
                sender_id=self.agent_id,
                receiver_id=response.get("receiver_id"),
                content=response.get("payload", {}),
            )
        return None

    async def execute_skill(self, skill_name: str, params: Dict[str, Any]) -> Any:
        """
        SDK BaseAgent 技能执行方法

        Args:
            skill_name: 技能名称
            params: 技能参数

        Returns:
            执行结果
        """
        # Demo 默认技能处理
        handler = self._demo_message_handlers.get(skill_name)
        if handler:
            return await handler(params)
        raise ValueError(f"Unknown skill: {skill_name}")

    async def shutdown(self) -> None:
        """SDK BaseAgent 关闭方法"""
        await self.stop()

    # ========== Demo 消息处理 ==========

    async def _handle_demo_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        处理 Demo 格式的消息

        Args:
            message: 消息字典

        Returns:
            响应消息（可选）
        """
        message_type = message.get("message_type", "unknown")
        message_id = message.get("message_id", "")

        logger.debug(f"{self.name} received message: {message_type} [{message_id}]")

        handler = self._demo_message_handlers.get(message_type)

        if handler:
            try:
                return await handler(message)
            except Exception as e:
                logger.error(f"{self.name} error handling {message_type}: {e}", exc_info=True)
                return self._create_error_response(message, str(e))
        else:
            logger.warning(f"{self.name} no handler for: {message_type}")
            return None

    def _setup_logging(self) -> None:
        """设置日志"""
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)

        # 配置根日志
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # 设置当前模块的日志级别
        logging.getLogger(self.__class__.__module__).setLevel(log_level)

    def _register_default_handlers(self) -> None:
        """注册默认消息处理器"""
        self._demo_message_handlers["heartbeat"] = self._handle_heartbeat
        self._demo_message_handlers["ping"] = self._handle_ping
        self._demo_message_handlers["error"] = self._handle_error

    def register_handler(self, message_type: str, handler: Callable) -> None:
        """
        注册消息处理器

        Args:
            message_type: 消息类型
            handler: 异步处理函数
        """
        self._demo_message_handlers[message_type] = handler
        logger.debug(f"{self.name} registered handler for: {message_type}")

    def unregister_handler(self, message_type: str) -> None:
        """注销消息处理器"""
        if message_type in self._demo_message_handlers:
            del self._demo_message_handlers[message_type]

    async def _handle_heartbeat(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理心跳消息"""
        return {
            "message_type": "heartbeat_ack",
            "sender_id": self.agent_id,
            "receiver_id": message.get("sender_id"),
            "correlation_id": message.get("message_id"),
            "status": self._state.value if hasattr(self, "_state") else "running",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    async def _handle_ping(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理 Ping 消息"""
        return {
            "message_type": "pong",
            "sender_id": self.agent_id,
            "receiver_id": message.get("sender_id"),
            "correlation_id": message.get("message_id"),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    async def _handle_error(self, message: Dict[str, Any]) -> None:
        """处理错误消息"""
        error = message.get("payload", {}).get("error", "Unknown error")
        logger.error(f"{self.name} received error: {error}")

    def _create_error_response(self, request: Dict[str, Any], error_message: str) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "message_type": "error",
            "message_id": f"error_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "sender_id": self.agent_id,
            "receiver_id": request.get("sender_id"),
            "correlation_id": request.get("message_id"),
            "payload": {"error": error_message},
        }

    # ========== 消息发送 (Demo 消息总线) ==========

    async def send_message(
        self,
        message_type: str,
        payload: Dict[str, Any],
        receiver_id: str,
        correlation_id: Optional[str] = None,
        priority: int = 5,
    ) -> bool:
        """
        发送点对点消息

        Args:
            message_type: 消息类型
            payload: 消息内容
            receiver_id: 接收者 ID
            correlation_id: 关联 ID
            priority: 优先级

        Returns:
            是否发送成功
        """
        if not self._message_bus:
            logger.warning(f"{self.name} message bus not initialized")
            return False

        message = Message(
            message_type=message_type,
            sender_id=self.agent_id,
            receiver_id=receiver_id,
            correlation_id=correlation_id,
            payload=payload,
            priority=priority,
        )

        return await self._message_bus.send_message(message, receiver_id)

    async def broadcast(
        self,
        message_type: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        exclude_self: bool = True,
    ) -> int:
        """
        广播消息

        Args:
            message_type: 消息类型
            payload: 消息内容
            correlation_id: 关联 ID
            exclude_self: 是否排除自己

        Returns:
            接收消息的 Agent 数量
        """
        if not self._message_bus:
            logger.warning(f"{self.name} message bus not initialized")
            return 0

        message = Message(
            message_type=message_type,
            sender_id=self.agent_id,
            correlation_id=correlation_id,
            payload=payload,
        )

        return await self._message_bus.broadcast(message, exclude_self)

    async def publish(
        self,
        topic: str,
        message_type: str,
        payload: Dict[str, Any],
    ) -> int:
        """
        发布消息到主题

        Args:
            topic: 主题名称
            message_type: 消息类型
            payload: 消息内容

        Returns:
            接收消息的订阅者数量
        """
        if not self._message_bus:
            logger.warning(f"{self.name} message bus not initialized")
            return 0

        message = Message(
            message_type=message_type,
            sender_id=self.agent_id,
            payload=payload,
        )

        return await self._message_bus.publish(topic, message)

    def subscribe(self, topic: str) -> None:
        """订阅主题"""
        if self._message_bus:
            self._message_bus.subscribe(self.agent_id, topic)

    def unsubscribe(self, topic: str) -> None:
        """取消订阅主题"""
        if self._message_bus:
            self._message_bus.unsubscribe(self.agent_id, topic)

    # ========== 生命周期 ==========

    async def start(self) -> bool:
        """
        启动 Agent

        Returns:
            是否启动成功
        """
        if self._running:
            logger.warning(f"{self.name} already running")
            return True

        logger.info(f"{self.name} starting...")

        # 注意: 不调用 SDK 的 super().start() 以避免自动启动服务器
        # SDK 的 initialize() 和 shutdown() 会在需要时被调用

        # 设置 SDK 内部状态
        try:
            from usmsb_sdk.agent_sdk.base_agent import AgentState

            if hasattr(self, "_state"):
                await self._set_state(AgentState.INITIALIZING)
        except Exception:
            pass

        # 连接消息总线 (Demo 特有)
        self._message_bus = await get_message_bus(self._demo_config.redis_url)

        # 注册到消息总线
        self._message_bus.register_agent(self.agent_id, self._handle_demo_message)

        # 启动心跳任务
        if self._demo_config.heartbeat_interval > 0:
            task = asyncio.create_task(self._heartbeat_loop())
            self._background_tasks.append(task)

        # 执行子类初始化
        try:
            await self.on_start()
        except Exception as e:
            logger.error(f"{self.name} on_start error: {e}")
            return False

        self._running = True

        # 设置 SDK 状态为 RUNNING
        try:
            from usmsb_sdk.agent_sdk.base_agent import AgentState

            if hasattr(self, "_state"):
                await self._set_state(AgentState.RUNNING)
        except Exception:
            pass

        logger.info(f"{self.name} started successfully")
        return True

    async def stop(self) -> None:
        """停止 Agent"""
        if not self._running:
            return

        logger.info(f"{self.name} stopping...")

        self._running = False

        # 停止 HTTP Server
        if self._http_server:
            await self._http_server.stop()
            self._http_server = None

        # 停止 P2P Server
        if self._p2p_server:
            await self._p2p_server.stop()
            self._p2p_server = None

        # 取消后台任务
        for task in self._background_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._background_tasks.clear()

        # 执行子类清理
        try:
            await self.on_stop()
        except Exception as e:
            logger.error(f"{self.name} on_stop error: {e}")

        # 从消息总线注销
        if self._message_bus:
            self._message_bus.unregister_agent(self.agent_id)

        # 调用 SDK BaseAgent 的停止逻辑
        try:
            await super().stop()
        except Exception as e:
            logger.warning(f"SDK stop error: {e}")

        logger.info(f"{self.name} stopped")

    async def on_start(self) -> None:
        """子类可重写的启动钩子"""
        pass

    async def on_stop(self) -> None:
        """子类可重写的停止钩子"""
        pass

    async def _heartbeat_loop(self) -> None:
        """心跳循环"""
        while self._running:
            try:
                await asyncio.sleep(self._demo_config.heartbeat_interval)

                if self._running:
                    # 发送心跳广播
                    await self.broadcast(
                        "heartbeat",
                        {
                            "status": self._state.value if hasattr(self, "_state") else "running",
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"{self.name} heartbeat error: {e}")

    # ========== HTTP Server 支持 ==========

    async def start_with_http(
        self,
        host: str = "0.0.0.0",
        port: int = 5001,
        platform_url: str = None,
    ) -> HTTPServer:
        """
        使用 SDK HTTP Server 启动 Agent

        Args:
            host: 监听地址
            port: HTTP 端口
            platform_url: 平台 URL

        Returns:
            HTTPServer 实例
        """
        # 先启动 Agent (如果尚未启动)
        if not self._running:
            await self.start()

        # 创建 SDK HTTP Server
        self._http_server = HTTPServer(
            agent=self,
            host=host,
            port=port,
            platform_url=platform_url or self._demo_config.platform_url,
        )
        await self._http_server.start()

        logger.info(f"{self.name} HTTP Server started on port {port}")
        logger.info(f"   Health: http://{host}:{port}/health")
        logger.info(f"   Invoke: http://{host}:{port}/invoke")

        return self._http_server

    # ========== P2P Server 支持 ==========

    async def start_with_p2p(
        self,
        host: str = "0.0.0.0",
        port: int = 9001,
        bootstrap_peers: List = None,
    ) -> SDKP2PServer:
        """
        使用 SDK P2P Server 启动 Agent (去中心化模式)

        Args:
            host: 监听地址
            port: P2P 端口
            bootstrap_peers: 引导节点列表 [(address, port), ...]

        Returns:
            P2PServer 实例
        """
        # 先启动 Agent (如果尚未启动)
        if not self._running:
            await self.start()

        # 创建 SDK P2P Server
        self._p2p_server = SDKP2PServer(
            agent=self,
            host=host,
            port=port,
            bootstrap_peers=bootstrap_peers or [],
        )
        await self._p2p_server.start()

        logger.info(f"{self.name} P2P Server started on port {port}")
        logger.info(f"   Peer ID: {self._p2p_server.peer_id[:16]}...")

        return self._p2p_server

    async def start_with_both(
        self,
        http_port: int = 5001,
        p2p_port: int = 9001,
        platform_url: str = None,
        bootstrap_peers: List = None,
    ) -> tuple:
        """
        同时启动 HTTP Server 和 P2P Server

        Args:
            http_port: HTTP 端口
            p2p_port: P2P 端口
            platform_url: 平台 URL
            bootstrap_peers: 引导节点列表

        Returns:
            (HTTPServer, P2PServer) 元组
        """
        # 先启动 Agent
        await self.start()

        # 启动 HTTP Server
        http_server = await self.start_with_http(
            port=http_port,
            platform_url=platform_url or self._demo_config.platform_url,
        )

        # 启动 P2P Server
        p2p_server = await self.start_with_p2p(
            port=p2p_port,
            bootstrap_peers=bootstrap_peers,
        )

        logger.info(f"{self.name} running with HTTP:{http_port} and P2P:{p2p_port}")

        return http_server, p2p_server

    # ========== 重试机制 ==========

    async def execute_with_retry(
        self,
        operation: Callable,
        max_retries: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
    ) -> Any:
        """
        带重试的操作执行

        Args:
            operation: 异步操作函数
            max_retries: 最大重试次数
            delay: 初始延迟
            backoff: 退避因子

        Returns:
            操作结果
        """
        last_error = None
        current_delay = delay

        for attempt in range(max_retries + 1):
            try:
                return await operation()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    logger.warning(
                        f"{self.name} operation failed, retrying ({attempt + 1}/{max_retries}): {e}"
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

        raise last_error

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running

    def get_stats(self) -> Dict[str, Any]:
        """获取 Agent 统计信息"""
        stats = {
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "agent_type": self.agent_type,
            "status": self._state.value if hasattr(self, "_state") else "unknown",
            "running": self._running,
            "message_handlers": list(self._demo_message_handlers.keys()),
        }

        if self._message_bus:
            stats["queue_size"] = self._message_bus.get_queue_size(self.agent_id)

        return stats


async def run_agent(agent: BaseAgent) -> None:
    """
    运行 Agent 直到收到停止信号 (使用消息总线)

    Args:
        agent: Agent 实例
    """
    try:
        await agent.start()

        # 等待停止信号
        while agent.is_running:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info(f"Received interrupt signal for {agent.name}")
    finally:
        await agent.stop()
        await shutdown_message_bus()


async def run_agent_with_http_sdk(
    agent: BaseAgent,
    http_port: int = 5001,
    platform_url: str = "http://localhost:8000",
) -> None:
    """
    使用 SDK HTTP Server 运行 Agent (推荐方式)

    Args:
        agent: Agent 实例
        http_port: HTTP 端口
        platform_url: 平台 API 地址
    """
    try:
        # 使用 HTTP Server 启动
        await agent.start_with_http(
            port=http_port,
            platform_url=platform_url,
        )

        logger.info(f"{agent.name} running with HTTP on port {http_port}")
        logger.info(f"   Health: http://localhost:{http_port}/health")
        logger.info(f"   Invoke: http://localhost:{http_port}/invoke")

        # 等待停止信号
        while agent.is_running:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info(f"Received interrupt signal for {agent.name}")
    finally:
        await agent.stop()
        await shutdown_message_bus()


async def run_agent_with_both(
    agent: BaseAgent,
    http_port: int = 5001,
    p2p_port: int = 9001,
    platform_url: str = "http://localhost:8000",
    bootstrap_peers: List = None,
) -> None:
    """
    使用 SDK HTTP Server 和 P2P Server 运行 Agent (推荐生产方式)

    Args:
        agent: Agent 实例
        http_port: HTTP 端口
        p2p_port: P2P 端口
        platform_url: 平台 API 地址
        bootstrap_peers: P2P 引导节点列表 [(address, port), ...]
    """
    try:
        # 同时启动 HTTP 和 P2P Server
        await agent.start_with_both(
            http_port=http_port,
            p2p_port=p2p_port,
            platform_url=platform_url,
            bootstrap_peers=bootstrap_peers,
        )

        logger.info(f"{agent.name} running with HTTP:{http_port} and P2P:{p2p_port}")
        logger.info(f"   Health: http://localhost:{http_port}/health")
        logger.info(f"   Invoke: http://localhost:{http_port}/invoke")
        logger.info(f"   P2P: port {p2p_port}")

        # 等待停止信号
        while agent.is_running:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info(f"Received interrupt signal for {agent.name}")
    finally:
        await agent.stop()
        await shutdown_message_bus()


# 导出供外部使用
__all__ = [
    "BaseAgent",
    "AgentConfig",
    "run_agent",
    "run_agent_with_http_sdk",
    "run_agent_with_both",
    "HTTPServer",
    "run_agent_with_http",
    "SDKP2PServer",
    "sdk_run_agent_with_p2p",
]
