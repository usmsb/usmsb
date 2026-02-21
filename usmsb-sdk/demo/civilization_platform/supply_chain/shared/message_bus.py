"""
Supply Chain Demo - Message Bus

提供 Agent 之间的消息通信功能，基于内存队列实现简单高效的消息传递。
支持 Redis 作为可选的后端存储。
"""

import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
import uuid

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """消息数据结构"""
    message_type: str
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    sender_id: str = ""
    receiver_id: Optional[str] = None  # None 表示广播
    correlation_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5  # 1-10, 越高越优先
    ttl: int = 3600  # 消息有效期（秒）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_type": self.message_type,
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "correlation_id": self.correlation_id,
            "payload": self.payload,
            "priority": self.priority,
            "ttl": self.ttl,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(
            message_type=data.get("message_type", ""),
            message_id=data.get("message_id", str(uuid.uuid4())),
            timestamp=data.get("timestamp", datetime.utcnow().isoformat() + "Z"),
            sender_id=data.get("sender_id", ""),
            receiver_id=data.get("receiver_id"),
            correlation_id=data.get("correlation_id"),
            payload=data.get("payload", {}),
            priority=data.get("priority", 5),
            ttl=data.get("ttl", 3600),
        )


class MessageBus:
    """
    消息总线

    提供 Agent 之间的消息传递功能：
    - 点对点消息
    - 广播消息
    - 主题订阅
    - 消息持久化（可选）
    """

    _instance: Optional["MessageBus"] = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, redis_url: Optional[str] = None):
        if MessageBus._initialized:
            return

        self._redis_url = redis_url
        self._redis_client = None

        # 消息队列：每个 Agent 一个队列
        self._agent_queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)

        # 主题订阅
        self._topic_subscribers: Dict[str, Set[str]] = defaultdict(set)

        # Agent 消息处理器
        self._message_handlers: Dict[str, Callable] = {}

        # 消息历史（用于调试）
        self._message_history: List[Dict[str, Any]] = []
        self._max_history = 1000

        # 运行状态
        self._running = False
        self._consumer_tasks: Dict[str, asyncio.Task] = {}

        MessageBus._initialized = True
        logger.info("MessageBus initialized")

    async def connect(self) -> bool:
        """连接消息总线"""
        self._running = True

        # 如果配置了 Redis，尝试连接
        if self._redis_url:
            try:
                import redis.asyncio as aioredis
                self._redis_client = await aioredis.from_url(self._redis_url)
                logger.info(f"MessageBus connected to Redis: {self._redis_url}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}, using in-memory queue")
                self._redis_client = None

        logger.info("MessageBus started")
        return True

    async def disconnect(self) -> None:
        """断开消息总线"""
        self._running = False

        # 取消所有消费者任务
        for task in self._consumer_tasks.values():
            task.cancel()

        self._consumer_tasks.clear()

        # 关闭 Redis 连接
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None

        logger.info("MessageBus stopped")

    def register_agent(self, agent_id: str, message_handler: Callable) -> None:
        """
        注册 Agent

        Args:
            agent_id: Agent ID
            message_handler: 消息处理回调函数
        """
        if agent_id not in self._agent_queues:
            self._agent_queues[agent_id] = asyncio.Queue()

        self._message_handlers[agent_id] = message_handler

        # 启动消费者任务
        if agent_id not in self._consumer_tasks or self._consumer_tasks[agent_id].done():
            self._consumer_tasks[agent_id] = asyncio.create_task(
                self._consume_messages(agent_id)
            )

        logger.info(f"Agent registered: {agent_id}")

    def unregister_agent(self, agent_id: str) -> None:
        """
        注销 Agent

        Args:
            agent_id: Agent ID
        """
        # 取消消费者任务
        if agent_id in self._consumer_tasks:
            self._consumer_tasks[agent_id].cancel()
            del self._consumer_tasks[agent_id]

        # 清理队列和处理器
        if agent_id in self._agent_queues:
            del self._agent_queues[agent_id]

        if agent_id in self._message_handlers:
            del self._message_handlers[agent_id]

        # 从所有主题中取消订阅
        for topic in self._topic_subscribers:
            self._topic_subscribers[topic].discard(agent_id)

        logger.info(f"Agent unregistered: {agent_id}")

    async def _consume_messages(self, agent_id: str) -> None:
        """消费 Agent 消息的后台任务"""
        queue = self._agent_queues[agent_id]
        handler = self._message_handlers.get(agent_id)

        if not handler:
            logger.warning(f"No handler for agent: {agent_id}")
            return

        while self._running:
            try:
                # 等待消息
                message = await asyncio.wait_for(queue.get(), timeout=1.0)

                # 调用处理器
                try:
                    await handler(message.to_dict())
                except Exception as e:
                    logger.error(f"Error handling message for {agent_id}: {e}")

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in consumer for {agent_id}: {e}")
                await asyncio.sleep(0.1)

    async def send_message(
        self,
        message: Message,
        receiver_id: Optional[str] = None
    ) -> bool:
        """
        发送点对点消息

        Args:
            message: 消息对象
            receiver_id: 接收者 ID（可选，默认使用 message.receiver_id）

        Returns:
            是否发送成功
        """
        target = receiver_id or message.receiver_id

        if not target:
            logger.warning("No receiver specified for point-to-point message")
            return False

        if target not in self._agent_queues:
            logger.warning(f"Receiver not found: {target}")
            return False

        # 添加到接收者的队列
        await self._agent_queues[target].put(message)

        # 记录历史
        self._record_message(message)

        logger.debug(f"Message sent from {message.sender_id} to {target}")
        return True

    async def broadcast(
        self,
        message: Message,
        exclude_sender: bool = True
    ) -> int:
        """
        广播消息给所有 Agent

        Args:
            message: 消息对象
            exclude_sender: 是否排除发送者

        Returns:
            接收消息的 Agent 数量
        """
        count = 0

        for agent_id in self._agent_queues:
            if exclude_sender and agent_id == message.sender_id:
                continue

            await self._agent_queues[agent_id].put(message)
            count += 1

        # 记录历史
        self._record_message(message)

        logger.debug(f"Broadcast from {message.sender_id} to {count} agents")
        return count

    async def publish(
        self,
        topic: str,
        message: Message
    ) -> int:
        """
        发布消息到主题

        Args:
            topic: 主题名称
            message: 消息对象

        Returns:
            接收消息的订阅者数量
        """
        subscribers = self._topic_subscribers.get(topic, set())
        count = 0

        for agent_id in subscribers:
            if agent_id in self._agent_queues:
                await self._agent_queues[agent_id].put(message)
                count += 1

        # 记录历史
        self._record_message(message)

        logger.debug(f"Published to topic '{topic}': {count} subscribers")
        return count

    def subscribe(self, agent_id: str, topic: str) -> None:
        """
        订阅主题

        Args:
            agent_id: Agent ID
            topic: 主题名称
        """
        self._topic_subscribers[topic].add(agent_id)
        logger.info(f"Agent {agent_id} subscribed to topic '{topic}'")

    def unsubscribe(self, agent_id: str, topic: str) -> None:
        """
        取消订阅主题

        Args:
            agent_id: Agent ID
            topic: 主题名称
        """
        self._topic_subscribers[topic].discard(agent_id)
        logger.info(f"Agent {agent_id} unsubscribed from topic '{topic}'")

    def _record_message(self, message: Message) -> None:
        """记录消息历史"""
        self._message_history.append({
            "message_id": message.message_id,
            "message_type": message.message_type,
            "sender_id": message.sender_id,
            "receiver_id": message.receiver_id,
            "timestamp": message.timestamp,
        })

        # 限制历史大小
        if len(self._message_history) > self._max_history:
            self._message_history = self._message_history[-self._max_history:]

    def get_message_history(
        self,
        agent_id: Optional[str] = None,
        message_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取消息历史

        Args:
            agent_id: 过滤特定 Agent 的消息
            message_type: 过滤特定类型的消息
            limit: 返回数量限制

        Returns:
            消息历史列表
        """
        history = self._message_history

        if agent_id:
            history = [
                m for m in history
                if m["sender_id"] == agent_id or m["receiver_id"] == agent_id
            ]

        if message_type:
            history = [m for m in history if m["message_type"] == message_type]

        return history[-limit:]

    def get_queue_size(self, agent_id: str) -> int:
        """获取 Agent 队列大小"""
        if agent_id in self._agent_queues:
            return self._agent_queues[agent_id].qsize()
        return 0

    def get_stats(self) -> Dict[str, Any]:
        """获取消息总线统计信息"""
        return {
            "running": self._running,
            "registered_agents": len(self._message_handlers),
            "topics": list(self._topic_subscribers.keys()),
            "total_subscriptions": sum(len(s) for s in self._topic_subscribers.values()),
            "message_history_size": len(self._message_history),
            "redis_connected": self._redis_client is not None,
        }


# 全局消息总线实例
_message_bus: Optional[MessageBus] = None


async def get_message_bus(redis_url: Optional[str] = None) -> MessageBus:
    """获取全局消息总线实例"""
    global _message_bus

    if _message_bus is None:
        _message_bus = MessageBus(redis_url=redis_url)
        await _message_bus.connect()

    return _message_bus


async def shutdown_message_bus() -> None:
    """关闭全局消息总线"""
    global _message_bus

    if _message_bus:
        await _message_bus.disconnect()
        _message_bus = None
