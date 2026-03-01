"""
Demo Agent 基类

为所有 Demo 场景提供统一的 Agent 基类，
包含日志、可视化、消息处理等通用功能。
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field

# 添加项目路径
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from usmsb_sdk.agent_sdk import (
    BaseAgent,
    AgentConfig,
    SkillDefinition,
    CapabilityDefinition,
)


@dataclass
class DemoMessage:
    """Demo 消息结构"""
    sender: str
    receiver: str
    content: Any
    message_type: str = "text"
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "message_type": self.message_type,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class DemoAgent(BaseAgent):
    """
    Demo Agent 基类

    提供以下功能：
    - 统一的日志记录
    - 消息可视化
    - 性能统计
    - 场景集成
    """

    def __init__(
        self,
        config: AgentConfig,
        scenario_name: str = "default",
        visualizer: Optional[Any] = None,
    ):
        super().__init__(config)
        self.scenario_name = scenario_name
        self.visualizer = visualizer
        self.message_history: List[DemoMessage] = []
        self.action_history: List[Dict] = []
        self._message_handlers: Dict[str, Callable] = {}

        # 注册默认消息处理器
        self._register_default_handlers()

    def _register_default_handlers(self):
        """注册默认消息处理器"""
        self._message_handlers = {
            "text": self._handle_text_message,
            "task": self._handle_task_message,
            "result": self._handle_result_message,
            "negotiation": self._handle_negotiation_message,
            "collaboration": self._handle_collaboration_message,
        }

    async def initialize(self):
        """初始化 Agent"""
        self.logger.info(f"[{self.scenario_name}] {self.name} 初始化中...")
        await self._setup_skills()
        await self._setup_capabilities()
        self.logger.info(f"[{self.scenario_name}] {self.name} 初始化完成")

    async def _setup_skills(self):
        """设置技能 - 子类重写"""
        pass

    async def _setup_capabilities(self):
        """设置能力 - 子类重写"""
        pass

    def register_skill(
        self,
        name: str,
        description: str,
        handler: Optional[Callable] = None,
        parameters: Optional[Dict] = None,
    ):
        """注册技能"""
        skill = SkillDefinition(
            name=name,
            description=description,
        )
        # 保存 handler 供内部使用（不在 SkillDefinition 中）
        if handler:
            self._skill_handlers = getattr(self, '_skill_handlers', {})
            self._skill_handlers[name] = handler
        self._skills[name] = skill
        self.logger.debug(f"注册技能: {name}")

    def register_capability(
        self,
        name: str,
        description: str,
        level: str = "advanced",
    ):
        """注册能力"""
        capability = CapabilityDefinition(
            name=name,
            description=description,
            category="development",
            level=level,
        )
        self.capabilities.append(capability)
        self.logger.debug(f"注册能力: {name} (等级: {level})")

    async def handle_message(self, message: Any, session: Any = None) -> Any:
        """处理消息"""
        # 记录消息
        demo_msg = self._wrap_message(message)
        self.message_history.append(demo_msg)

        # 可视化
        if self.visualizer:
            await self.visualizer.log_message(demo_msg)

        # 获取消息类型
        msg_type = getattr(message, 'message_type', 'text')
        if isinstance(message, dict):
            msg_type = message.get('message_type', 'text')

        # 调用对应处理器
        handler = self._message_handlers.get(msg_type, self._handle_text_message)
        result = await handler(message)

        # 记录动作
        self._log_action("handle_message", {
            "type": msg_type,
            "sender": demo_msg.sender,
        })

        return result

    async def _handle_text_message(self, message: Any) -> Any:
        """处理文本消息 - 子类重写"""
        content = self._extract_content(message)
        content_str = str(content)
        self.logger.info(f"收到消息: {content_str[:100] if len(content_str) > 100 else content_str}")
        return {"status": "received", "agent": self.name}

    async def _handle_task_message(self, message: Any) -> Any:
        """处理任务消息 - 子类重写"""
        return {"status": "task_accepted", "agent": self.name}

    async def _handle_result_message(self, message: Any) -> Any:
        """处理结果消息 - 子类重写"""
        return {"status": "result_received", "agent": self.name}

    async def _handle_negotiation_message(self, message: Any) -> Any:
        """处理协商消息 - 子类重写"""
        return {"status": "negotiation_received", "agent": self.name}

    async def _handle_collaboration_message(self, message: Any) -> Any:
        """处理协作消息 - 子类重写"""
        return {"status": "collaboration_received", "agent": self.name}

    async def execute_skill(self, skill_name: str, params: Dict) -> Any:
        """执行技能"""
        self._log_action("execute_skill", {"skill": skill_name, "params": params})

        if skill_name not in self.skills:
            self.logger.warning(f"未知技能: {skill_name}")
            return {"error": f"Unknown skill: {skill_name}"}

        skill = self.skills[skill_name]
        if skill.handler:
            result = await skill.handler(params)
            return result
        return {"status": "executed", "skill": skill_name}

    async def send_message(
        self,
        receiver: str,
        content: Any,
        message_type: str = "text",
        metadata: Optional[Dict] = None,
    ) -> DemoMessage:
        """发送消息"""
        msg = DemoMessage(
            sender=self.name,
            receiver=receiver,
            content=content,
            message_type=message_type,
            metadata=metadata or {},
        )
        self.message_history.append(msg)

        if self.visualizer:
            await self.visualizer.log_message(msg)

        self._log_action("send_message", {
            "receiver": receiver,
            "type": message_type,
        })

        return msg

    async def broadcast(self, content: Any, message_type: str = "text") -> List[DemoMessage]:
        """广播消息给所有已知的 Agent"""
        messages = []
        for agent_name in self.known_agents:
            msg = await self.send_message(agent_name, content, message_type)
            messages.append(msg)
        return messages

    def _wrap_message(self, message: Any) -> DemoMessage:
        """包装消息为 DemoMessage"""
        if isinstance(message, DemoMessage):
            return message

        if isinstance(message, dict):
            return DemoMessage(
                sender=message.get('sender', 'unknown'),
                receiver=message.get('receiver', self.name),
                content=message.get('content', message),
                message_type=message.get('message_type', 'text'),
                metadata=message.get('metadata', {}),
            )

        # Handle Message object from communication.py
        if hasattr(message, 'sender_id'):
            sender = getattr(message, 'sender_id', 'unknown')
            receiver = getattr(message, 'receiver_id', self.name)
            content = getattr(message, 'content', str(message))
            # Get message type from MessageType enum
            msg_type = getattr(message, 'type', None)
            if msg_type and hasattr(msg_type, 'value'):
                message_type = msg_type.value
            else:
                message_type = 'text'
            return DemoMessage(
                sender=sender,
                receiver=receiver,
                content=content,
                message_type=message_type,
                metadata=getattr(message, 'metadata', {}),
            )

        return DemoMessage(
            sender='unknown',
            receiver=self.name,
            content=str(message),
        )

    def _extract_content(self, message: Any) -> Any:
        """提取消息内容"""
        if isinstance(message, DemoMessage):
            return message.content
        if isinstance(message, dict):
            return message.get('content', message)
        # Handle Message object from communication.py
        if hasattr(message, 'content'):
            return message.content
        return message

    def _log_action(self, action: str, details: Dict):
        """记录动作"""
        self.action_history.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
        })

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "agent_name": self.name,
            "scenario": self.scenario_name,
            "messages_sent": len([m for m in self.message_history if m.sender == self.name]),
            "messages_received": len([m for m in self.message_history if m.receiver == self.name]),
            "actions_count": len(self.action_history),
            "skills_count": len(self.skills),
            "capabilities_count": len(self.capabilities),
        }

    async def shutdown(self):
        """关闭 Agent"""
        self.logger.info(f"[{self.scenario_name}] {self.name} 关闭中...")
        stats = self.get_stats()
        self.logger.info(f"[{self.scenario_name}] {self.name} 统计: {stats}")


class TeamCoordinator:
    """
    团队协调器

    管理 Agent 团队的通信和协作
    """

    def __init__(self, scenario_name: str):
        self.scenario_name = scenario_name
        self.agents: Dict[str, DemoAgent] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        self.logger = logging.getLogger(f"Coordinator.{scenario_name}")

    def add_agent(self, agent: DemoAgent):
        """添加 Agent 到团队"""
        self.agents[agent.name] = agent
        self.logger.info(f"添加 Agent: {agent.name}")

    async def start(self):
        """启动协调器"""
        self.running = True
        self.logger.info(f"[{self.scenario_name}] 协调器启动")

        # 初始化所有 Agent
        for agent in self.agents.values():
            await agent.initialize()

        # 启动消息处理循环
        asyncio.create_task(self._message_loop())

    async def stop(self):
        """停止协调器"""
        self.running = False
        self.logger.info(f"[{self.scenario_name}] 协调器停止")

        # 关闭所有 Agent
        for agent in self.agents.values():
            await agent.shutdown()

    async def _message_loop(self):
        """消息处理循环"""
        while self.running:
            try:
                msg = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=1.0
                )
                await self._deliver_message(msg)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"消息处理错误: {e}")

    async def _deliver_message(self, msg: DemoMessage):
        """投递消息"""
        receiver = msg.receiver
        if receiver in self.agents:
            await self.agents[receiver].handle_message(msg)
        else:
            self.logger.warning(f"未知的接收者: {receiver}")

    async def broadcast(self, sender: str, content: Any, message_type: str = "text"):
        """广播消息"""
        for agent_name in self.agents:
            if agent_name != sender:
                msg = DemoMessage(
                    sender=sender,
                    receiver=agent_name,
                    content=content,
                    message_type=message_type,
                )
                await self.message_queue.put(msg)

    async def send_to(self, sender: str, receiver: str, content: Any, message_type: str = "text"):
        """发送消息给指定 Agent"""
        msg = DemoMessage(
            sender=sender,
            receiver=receiver,
            content=content,
            message_type=message_type,
        )
        await self.message_queue.put(msg)

    def get_team_stats(self) -> Dict:
        """获取团队统计"""
        return {
            "scenario": self.scenario_name,
            "agents_count": len(self.agents),
            "agents": {name: agent.get_stats() for name, agent in self.agents.items()},
        }
