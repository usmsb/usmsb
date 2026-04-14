# -*- coding: utf-8 -*-
"""
Google A2A Protocol Handler

实现 Google A2A (Agent-to-Agent) 协议规范：
https://github.com/google/a2a-python

A2A 协议要点：
1. AgentCard at /.well-known/agent.json
2. Task State Machine: submitted → working → completed/failed/input-required
3. JSON-RPC 2.0 消息格式
4. SSE (Server-Sent Events) for push updates
"""

import uuid
import json
import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Google A2A Task Status"""
    SUBMITTED = "submitted"           # 任务已提交
    WORKING = "working"              # 任务执行中
    COMPLETED = "completed"          # 任务已完成
    FAILED = "failed"                # 任务失败
    INPUT_REQUIRED = "input-required" # 需要更多输入
    CANCELLED = "cancelled"          # 任务已取消


class MessageType(Enum):
    """Google A2A Message Types"""
    TASK = "task"
    TASK_RESPONSE = "task_response"
    TASK_STATUS_UPDATE = "task_status_update"
    AGENT_CARD = "agent_card"
    ERROR = "error"
    CANCEL = "cancel"


@dataclass
class A2ATask:
    """A2A 任务"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.SUBMITTED
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())
    input_data: dict = field(default_factory=dict)
    output_data: Any = None
    error: str | None = None
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status.value,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "input": self.input_data,
            "output": self.output_data,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class GoogleAgentCard:
    """
    Google A2A Agent Card
    
    遵循 Google A2A 协议规范：
    {
        "name": "Agent Name",
        "description": "...",
        "version": "1.0",
        "capabilities": {...},
        "skills": [...],
        "authentication": {...}
    }
    """
    name: str
    description: str
    version: str = "1.0"
    provider: dict = field(default_factory=dict)
    capabilities: dict = field(default_factory=dict)
    skills: list[dict] = field(default_factory=list)
    authentication: dict = field(default_factory=dict)
    url: str = ""
    endpoint: str = ""
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "provider": self.provider,
            "capabilities": self.capabilities,
            "skills": self.skills,
            "authentication": self.authentication,
            "url": self.url,
            "endpoint": self.endpoint,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "GoogleAgentCard":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            provider=data.get("provider", {}),
            capabilities=data.get("capabilities", {}),
            skills=data.get("skills", []),
            authentication=data.get("authentication", {}),
            url=data.get("url", ""),
            endpoint=data.get("endpoint", ""),
            metadata=data.get("metadata", {}),
        )


class GoogleA2AHandler:
    """
    Google A2A Protocol Handler
    
    遵循 Google A2A 协议规范：
    - AgentCard 发现
    - Task State Machine
    - JSON-RPC 2.0
    """
    
    WELL_KNOWN_PATH = "/.well-known/agent.json"
    
    def __init__(
        self,
        agent_id: str,
        agent_card: GoogleAgentCard | None = None,
    ):
        self.agent_id = agent_id
        self.agent_card = agent_card or self._create_default_agent_card()
        
        # 任务存储
        self._tasks: dict[str, A2ATask] = {}
        
        # 任务回调
        self._task_handlers: dict[str, Callable] = {}
        
        # SSE 订阅者
        self._sse_subscribers: dict[str, asyncio.Queue] = {}
    
    def _create_default_agent_card(self) -> GoogleAgentCard:
        """创建默认 AgentCard"""
        return GoogleAgentCard(
            name=f"USMSB Agent {self.agent_id}",
            description="USMSB Silicon-based Life Agent",
            version="2.0",
            provider={"organization": "USMSB", "url": ""},
            capabilities={
                "streaming": True,
                "pushNotifications": True,
                "stateTransitionHistory": True,
            },
            skills=[
                {"id": "reasoning", "name": "Reasoning", "description": "Logical reasoning"},
                {"id": "coding", "name": "Coding", "description": "Code generation"},
                {"id": "analysis", "name": "Analysis", "description": "Data analysis"},
            ],
            authentication={"type": "none"},
        )
    
    def get_agent_card_json(self) -> str:
        """获取 AgentCard JSON (用于 /.well-known/agent.json)"""
        return json.dumps(self.agent_card.to_dict(), indent=2)
    
    def register_task_handler(
        self,
        skill_name: str,
        handler: Callable[[dict], Any]
    ) -> None:
        """注册任务处理器"""
        self._task_handlers[skill_name] = handler
        logger.info(f"Registered task handler for skill: {skill_name}")
    
    async def submit_task(
        self,
        skill_name: str,
        input_data: dict,
        metadata: dict | None = None
    ) -> str:
        """
        提交任务 (遵循 Google A2A Task State Machine)
        
        Args:
            skill_name: 技能名称
            input_data: 输入数据
            metadata: 元数据
            
        Returns:
            str: 任务 ID
        """
        task_id = str(uuid.uuid4())
        
        task = A2ATask(
            id=task_id,
            status=TaskStatus.SUBMITTED,
            input_data={"skill": skill_name, **input_data},
            metadata=metadata or {},
        )
        
        self._tasks[task_id] = task
        
        # 异步执行任务
        asyncio.create_task(self._execute_task(task_id))
        
        return task_id
    
    async def _execute_task(self, task_id: str) -> None:
        """执行任务"""
        task = self._tasks.get(task_id)
        if not task:
            return
        
        try:
            # 更新状态为 working
            task.status = TaskStatus.WORKING
            task.updated_at = datetime.now().timestamp()
            await self._notify_status_update(task)
            
            # 获取技能名称
            skill_name = task.input_data.get("skill")
            handler = self._task_handlers.get(skill_name)
            
            if not handler:
                # 尝试通用处理器
                handler = self._task_handlers.get("*")
            
            if handler:
                # 执行处理器
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(task.input_data)
                else:
                    result = handler(task.input_data)
                
                task.output_data = result
                task.status = TaskStatus.COMPLETED
            else:
                task.error = f"No handler for skill: {skill_name}"
                task.status = TaskStatus.FAILED
            
        except Exception as e:
            logger.error(f"Task execution error: {e}")
            task.error = str(e)
            task.status = TaskStatus.FAILED
        
        task.updated_at = datetime.now().timestamp()
        await self._notify_status_update(task)
    
    async def _notify_status_update(self, task: A2ATask) -> None:
        """通知任务状态更新 (SSE)"""
        for queue in self._sse_subscribers.values():
            await queue.put(task.to_dict())
    
    async def get_task_status(self, task_id: str) -> dict | None:
        """获取任务状态"""
        task = self._tasks.get(task_id)
        return task.to_dict() if task else None
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        task.status = TaskStatus.CANCELLED
        task.updated_at = datetime.now().timestamp()
        await self._notify_status_update(task)
        return True
    
    async def subscribe_updates(self, subscription_id: str) -> asyncio.Queue:
        """订阅任务更新 (SSE)"""
        queue = asyncio.Queue()
        self._sse_subscribers[subscription_id] = queue
        return queue
    
    async def unsubscribe_updates(self, subscription_id: str) -> None:
        """取消订阅"""
        if subscription_id in self._sse_subscribers:
            del self._sse_subscribers[subscription_id]
    
    def handle_json_rpc_request(self, request: dict) -> dict:
        """
        处理 JSON-RPC 2.0 请求
        
        Google A2A 使用 JSON-RPC 2.0 格式：
        {
            "jsonrpc": "2.0",
            "id": "...",
            "method": "tasks/submit|tasks/get|cancel",
            "params": {...}
        }
        """
        jsonrpc = request.get("jsonrpc")
        if jsonrpc != "2.0":
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Invalid JSON-RPC"},
                "id": request.get("id"),
            }
        
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")
        
        try:
            if method == "tasks/submit":
                task_id = asyncio.run(self.submit_task(
                    skill_name=params.get("skillName", ""),
                    input_data=params.get("input", {}),
                    metadata=params.get("metadata"),
                ))
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"taskId": task_id},
                }
            
            elif method == "tasks/get":
                task = asyncio.run(self.get_task_status(params.get("taskId", "")))
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": task,
                }
            
            elif method == "tasks/cancel":
                cancelled = asyncio.run(self.cancel_task(params.get("taskId", "")))
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"cancelled": cancelled},
                }
            
            elif method == "agents/card":
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": self.agent_card.to_dict(),
                }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                    "id": req_id,
                }
        
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Internal error: {e}"},
                "id": req_id,
            }
    
    def __repr__(self) -> str:
        return f"GoogleA2AHandler(agent={self.agent_id}, tasks={len(self._tasks)})"
