"""
CustomA2AHandler - Custom A2A 协议处理器

USMSB 私有协议处理器，支持：
- 任务委托与报酬机制
- 钱包签名认证
- Agent Card 发现与声誉系统
- 消息广播
- 协商流程
"""

import asyncio
import logging
import time
import uuid
from typing import Any, Callable

from usmsb_sdk.protocol.types.custom_a2a import (
    CustomTaskStatus,
    CustomMessageType,
    CustomMessage,
    CustomTask,
    CustomAgentCard,
)
from usmsb_sdk.protocol.types.envelope import A2AEnvelope


logger = logging.getLogger(__name__)


class CustomA2AHandler:
    """
    Custom A2A 协议处理器

    核心方法：
    - on_task_request()    → 处理任务请求
    - on_query()           → 处理查询
    - on_discovery()       → 处理发现请求
    - on_heartbeat()       → 处理心跳
    - on_negotiation()     → 处理协商
    - on_broadcast()       → 处理广播

    Task 状态机：
    pending → accepted → in_progress → completed
                                      → failed
                                      → canceled
    """

    def __init__(
        self,
        agent_id: str,
        agent_card: CustomAgentCard,
        skill_handlers: dict[str, Callable] | None = None,
        message_queue: asyncio.Queue | None = None,
        http_client: Any = None,
        peer_registry: dict[str, str] | None = None,
        task_store: Any = None,
    ):
        self._agent_id = agent_id
        self._agent_card = agent_card
        self._skill_handlers = skill_handlers or {}
        self._message_queue = message_queue or asyncio.Queue()

        # 任务存储
        if task_store:
            self._task_store = task_store
        else:
            from .persistence import InMemoryCustomTaskStore
            self._task_store = InMemoryCustomTaskStore()

        # 消息监听器
        self._listeners: dict[str, list[Callable]] = {}

        # 传输层
        self._transport: Any = None
        if http_client:
            from .transport import CustomA2ATransport
            self._transport = CustomA2ATransport(
                agent_id=agent_id,
                http_client=http_client,
                peer_registry=peer_registry,
            )

    @property
    def agent_id(self) -> str:
        """获取 Agent ID"""
        return self._agent_id

    @property
    def agent_card(self) -> CustomAgentCard:
        """获取 AgentCard"""
        return self._agent_card

    # === 消息处理 ===

    async def handle_envelope(self, envelope: A2AEnvelope) -> A2AEnvelope | None:
        """
        处理 A2AEnvelope 消息

        根据消息类型分发到对应处理器。
        """
        msg_type = envelope.message_type
        payload = envelope.payload

        if msg_type == "task":
            return await self.on_task_request(envelope)
        elif msg_type == "query":
            return await self.on_query(envelope)
        elif msg_type == "response":
            return await self.on_response(envelope)
        elif msg_type == "error":
            return await self.on_error(envelope)
        elif msg_type == "heartbeat":
            return await self.on_heartbeat(envelope)
        elif msg_type == "discovery":
            return await self.on_discovery(envelope)
        elif msg_type == "negotiation":
            return await self.on_negotiation(envelope)
        elif msg_type == "broadcast":
            return await self.on_broadcast(envelope)
        else:
            logger.warning(f"Unknown message type: {msg_type}")
            return None

    async def on_task_request(self, envelope: A2AEnvelope) -> A2AEnvelope:
        """处理任务请求"""
        payload = envelope.payload

        task = CustomTask(
            id=str(uuid.uuid4()),
            task_id=payload.get("task_id", ""),
            delegator=envelope.sender_id,
            delegatee=self._agent_id,
            description=payload.get("description", ""),
            status=CustomTaskStatus.PENDING,
            input_data=payload.get("input_data", {}),
            deadline=payload.get("deadline"),
            reward=payload.get("reward", 0.0),
            currency=payload.get("currency", "USDC"),
        )

        await self._task_store.save(task)

        # 调用技能处理器
        skill_id = payload.get("skill_id")
        if skill_id and skill_id in self._skill_handlers:
            handler = self._skill_handlers[skill_id]
            try:
                result = await handler(task.input_data)
                await self.complete_task(task.id, result)
            except Exception as e:
                await self.fail_task(task.id, str(e))
        else:
            # 默认处理：接受任务
            await self.accept_task(task.id)

        # 构建响应
        return A2AEnvelope(
            sender_id=self._agent_id,
            receiver_id=envelope.sender_id,
            message_type="response",
            correlation_id=envelope.correlation_id,
            payload={
                "task_id": task.id,
                "status": task.status.value,
                "result": task.output_data,
            },
        )

    async def on_query(self, envelope: A2AEnvelope) -> A2AEnvelope:
        """处理查询消息"""
        payload = envelope.payload
        query_type = payload.get("type", "")

        result = {"query_type": query_type}

        if query_type == "task_status":
            task_id = payload.get("task_id")
            task = await self.get_task(task_id)
            result["task"] = task.model_dump() if task else None
        elif query_type == "agent_info":
            result["agent"] = self._agent_card.model_dump()
        elif query_type == "capabilities":
            result["capabilities"] = self._agent_card.capabilities
            result["skills"] = [s.model_dump() for s in self._agent_card.skills]

        return A2AEnvelope(
            sender_id=self._agent_id,
            receiver_id=envelope.sender_id,
            message_type="response",
            correlation_id=envelope.correlation_id,
            payload=result,
        )

    async def on_response(self, envelope: A2AEnvelope) -> A2AEnvelope | None:
        """处理响应消息"""
        payload = envelope.payload
        task_id = payload.get("task_id")

        if task_id:
            task = await self.get_task(task_id)
            if task:
                if payload.get("status") == "completed":
                    await self.complete_task(task_id, payload.get("result"))
                elif payload.get("status") == "failed":
                    await self.fail_task(task_id, payload.get("error"))

        # 触发监听器
        await self._notify_listeners("response", envelope)
        return None

    async def on_error(self, envelope: A2AEnvelope) -> A2AEnvelope | None:
        """处理错误消息"""
        payload = envelope.payload
        task_id = payload.get("task_id")

        if task_id:
            await self.fail_task(task_id, payload.get("error", "Unknown error"))

        await self._notify_listeners("error", envelope)
        return None

    async def on_heartbeat(self, envelope: A2AEnvelope) -> A2AEnvelope:
        """处理心跳"""
        active_tasks = await self.get_active_tasks()
        return A2AEnvelope(
            sender_id=self._agent_id,
            receiver_id=envelope.sender_id,
            message_type="response",
            correlation_id=envelope.correlation_id,
            payload={
                "status": "alive",
                "timestamp": time.time(),
                "current_tasks": len(active_tasks),
            },
        )

    async def on_discovery(self, envelope: A2AEnvelope) -> A2AEnvelope:
        """处理发现请求"""
        return A2AEnvelope(
            sender_id=self._agent_id,
            receiver_id=envelope.sender_id,
            message_type="response",
            correlation_id=envelope.correlation_id,
            payload={
                "agent_card": self._agent_card.model_dump(),
            },
        )

    async def on_negotiation(self, envelope: A2AEnvelope) -> A2AEnvelope:
        """处理协商消息"""
        payload = envelope.payload
        negotiation_type = payload.get("negotiation_type", "")
        proposed_terms = payload.get("terms", {})

        # 处理协商
        accepted_terms = proposed_terms.copy()
        accepted_terms["status"] = "proposed"

        # TODO: 实现完整的协商逻辑
        return A2AEnvelope(
            sender_id=self._agent_id,
            receiver_id=envelope.sender_id,
            message_type="response",
            correlation_id=envelope.correlation_id,
            payload={
                "negotiation_type": negotiation_type,
                "terms": accepted_terms,
            },
        )

    async def on_broadcast(self, envelope: A2AEnvelope) -> A2AEnvelope | None:
        """处理广播消息"""
        await self._notify_listeners("broadcast", envelope)
        return None

    # === 任务管理 ===

    async def accept_task(self, task_id: str) -> bool:
        """接受任务"""
        task = await self._task_store.get(task_id)
        if not task or task.delegatee != self._agent_id:
            return False

        task.status = CustomTaskStatus.ACCEPTED
        task.accepted_at = time.time()
        await self._task_store.update(task_id, task)

        # 发送接受消息
        await self._send_to_agent(
            to_agent=task.delegator,
            message_type=CustomMessageType.RESPONSE,
            payload={
                "task_id": task_id,
                "status": "accepted",
            },
            correlation_id=task.id,
        )
        return True

    async def complete_task(self, task_id: str, output_data: Any) -> bool:
        """完成任务"""
        task = await self._task_store.get(task_id)
        if not task:
            return False

        task.status = CustomTaskStatus.COMPLETED
        task.output_data = output_data
        task.completed_at = time.time()
        await self._task_store.update(task_id, task)

        # 发送完成消息
        await self._send_to_agent(
            to_agent=task.delegator,
            message_type=CustomMessageType.RESPONSE,
            payload={
                "task_id": task_id,
                "status": "completed",
                "output_data": output_data,
            },
            correlation_id=task.id,
        )
        return True

    async def fail_task(self, task_id: str, error: str) -> bool:
        """标记任务失败"""
        task = await self._task_store.get(task_id)
        if not task:
            return False

        task.status = CustomTaskStatus.FAILED
        task.error = error
        task.completed_at = time.time()
        await self._task_store.update(task_id, task)

        # 发送失败消息
        await self._send_to_agent(
            to_agent=task.delegator,
            message_type=CustomMessageType.ERROR,
            payload={
                "task_id": task_id,
                "status": "failed",
                "error": error,
            },
            correlation_id=task.id,
        )
        return True

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = await self._task_store.get(task_id)
        if not task or task.delegator != self._agent_id:
            return False

        task.status = CustomTaskStatus.CANCELLED
        task.completed_at = time.time()
        await self._task_store.update(task_id, task)

        # 发送取消消息
        await self._send_to_agent(
            to_agent=task.delegatee,
            message_type=CustomMessageType.ERROR,
            payload={
                "task_id": task_id,
                "status": "canceled",
            },
            correlation_id=task.id,
        )
        return True

    async def get_task(self, task_id: str) -> CustomTask | None:
        """获取任务"""
        return await self._task_store.get(task_id)

    async def get_pending_tasks(self) -> list[CustomTask]:
        """获取待处理任务"""
        tasks, _ = await self._task_store.list(page_size=1000)
        return [t for t in tasks if t.is_pending()]

    async def get_active_tasks(self) -> list[CustomTask]:
        """获取进行中的任务"""
        tasks, _ = await self._task_store.list(page_size=1000)
        return [t for t in tasks if not t.is_terminal()]

    # === 消息发送 ===

    async def _send_to_agent(
        self,
        to_agent: str,
        message_type: str,
        payload: dict,
        correlation_id: str = "",
    ) -> None:
        """发送消息到指定 Agent（内部方法）"""
        envelope = A2AEnvelope(
            sender_id=self._agent_id,
            receiver_id=to_agent,
            message_type=message_type,
            payload=payload,
            correlation_id=correlation_id,
        )
        if self._transport:
            await self._transport.send(envelope)
        else:
            await self._message_queue.put(envelope)

    async def send_task_request(
        self,
        to_agent: str,
        description: str,
        input_data: dict,
        skill_id: str = "",
        reward: float = 0.0,
        currency: str = "USDC",
        deadline: float | None = None,
    ) -> str:
        """发送任务请求"""
        task_id = str(uuid.uuid4())
        envelope = A2AEnvelope(
            sender_id=self._agent_id,
            receiver_id=to_agent,
            message_type="task",
            payload={
                "task_id": task_id,
                "description": description,
                "input_data": input_data,
                "skill_id": skill_id,
                "reward": reward,
                "currency": currency,
                "deadline": deadline,
            },
        )
        await self._message_queue.put(envelope)
        return task_id

    async def send_query(
        self,
        to_agent: str,
        query_type: str,
        query_data: dict | None = None,
    ) -> None:
        """发送查询"""
        envelope = A2AEnvelope(
            sender_id=self._agent_id,
            receiver_id=to_agent,
            message_type="query",
            payload={
                "type": query_type,
                **(query_data or {}),
            },
        )
        await self._message_queue.put(envelope)

    async def broadcast(
        self,
        message_type: str,
        payload: dict,
    ) -> None:
        """广播消息"""
        envelope = A2AEnvelope(
            sender_id=self._agent_id,
            receiver_id="",  # 广播
            message_type=message_type,
            payload=payload,
        )
        await self._message_queue.put(envelope)

    # === 监听器 ===

    def register_listener(self, event_type: str, handler: Callable) -> None:
        """注册消息监听器"""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(handler)

    async def _notify_listeners(self, event_type: str, envelope: A2AEnvelope) -> None:
        """通知监听器"""
        handlers = self._listeners.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(envelope)
                else:
                    handler(envelope)
            except Exception as e:
                logger.error(f"Listener error: {e}")

    def __repr__(self) -> str:
        return f"CustomA2AHandler(agent={self._agent_id})"
