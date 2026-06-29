# -*- coding: utf-8 -*-
"""
ButlerAgent - 超级个体大管家 Agent

.. deprecated:: v3.0
    本模块为早期 stub，且导入链已断裂（依赖 l3_orchestrator → 已不存在的 GoogleAgentCard）。
    请改用 `usmsb_sdk.products.super_individual.butler_pea.ButlerPea`
    （基于 v3.0 harness：一切皆 LLM + guard + 钱包）。本文件仅为向后兼容保留。

整合所有超级个体功能的主 Agent。

功能：
- 协调各专业 Agent
- 管理用户记忆
- 生成晨晚汇报
- 处理日常事务
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from usmsb_sdk.l3_orchestrator import L3Orchestrator
from usmsb_sdk.products.super_individual.user_memory import UserMemory, UserProfile, UserValue
from usmsb_sdk.products.super_individual.morning_briefing import MorningBriefing, MorningBriefingReport
from usmsb_sdk.products.super_individual.evening_summary import EveningSummary, EveningSummaryReport


@dataclass
class ButlerConfig:
    """Butler 配置"""
    user_id: str
    user_name: str = "User"
    personality: str = "helpful"  # helpful, formal, casual
    communication_style: str = "friendly"  # friendly, formal, brief


class ButlerAgent:
    """
    Butler Agent - 超级个体大管家
    
    协调所有功能，为用户提供全面的 AI 助手服务。
    
    使用方式：
    ```python
    butler = ButlerAgent(user_id="gujun")
    
    # 早晨
    briefing = await butler.morning_briefing()
    
    # 晚间
    summary = await butler.evening_summary(completed_tasks=[...])
    
    # 日常请求
    response = await butler.assist("帮我写一封邮件给客户")
    ```
    """
    
    def __init__(self, config: ButlerConfig):
        self.config = config
        self.user_id = config.user_id
        
        # 用户记忆
        self.user_memory = UserMemory(user_id=config.user_id)
        
        # 晨晚汇报
        self.morning_briefing = MorningBriefing(user_memory=self.user_memory)
        self.evening_summary = EveningSummary(user_memory=self.user_memory)
        
        # L3 Orchestrator（用于复杂任务）
        self.l3 = L3Orchestrator(agent_id=f"butler_{config.user_id}")
        
        # 专业 Agent（简化版）
        self.specialists: dict[str, Any] = {}
        
        # 状态
        self.is_initialized = False
        self.conversation_history: list[dict] = []
        
        print(f"[ButlerAgent] Initialized for {config.user_name}")
    
    async def initialize(self) -> None:
        """初始化 Butler"""
        if self.is_initialized:
            return
        
        # 加载用户画像（如果有）
        # 实际实现会从存储加载
        
        self.is_initialized = True
        print(f"[ButlerAgent] {self.config.user_name} is ready")
    
    # ========== 用户管理 ==========
    
    def load_user_profile(
        self,
        name: str,
        bio: str = "",
        values: list[dict] | None = None,
        goals: list[str] | None = None
    ) -> None:
        """加载用户画像"""
        profile = UserProfile(
            user_id=self.user_id,
            name=name,
            bio=bio,
            goals=goals or [],
        )
        
        # 添加价值观
        for v in (values or []):
            profile.values.append(UserValue(
                name=v.get("name", ""),
                description=v.get("description", ""),
                strength=v.get("strength", 0.5),
            ))
        
        self.user_memory.load_profile(profile)
    
    # ========== 晨晚汇报 ==========
    
    async def morning_briefing(
        self,
        date: str | None = None,
        pending_tasks: list[dict] | None = None
    ) -> MorningBriefingReport:
        """
        生成早晨汇报
        
        Args:
            date: 日期
            pending_tasks: 待处理任务
            
        Returns:
            MorningBriefingReport
        """
        briefing = await self.morning_briefing.generate(
            date=date,
            pending_tasks=pending_tasks,
        )
        
        # 记录
        self._add_to_history("system", "morning_briefing", {"date": briefing.date})
        
        return briefing
    
    async def evening_summary(
        self,
        date: str | None = None,
        completed_tasks: list[dict] | None = None,
        incomplete_tasks: list[str] | None = None
    ) -> EveningSummaryReport:
        """
        生成晚间总结
        
        Args:
            date: 日期
            completed_tasks: 完成的任务
            incomplete_tasks: 未完成的任务
            
        Returns:
            EveningSummaryReport
        """
        summary = await self.evening_summary.generate(
            date=date,
            completed_tasks=completed_tasks,
            incomplete_tasks=incomplete_tasks,
        )
        
        # 记录
        self._add_to_history("system", "evening_summary", {"date": summary.date})
        
        return summary
    
    # ========== 日常协助 ==========
    
    async def assist(self, request: str) -> str:
        """
        处理用户请求
        
        Args:
            request: 用户请求
            
        Returns:
            str: 响应
        """
        # 记录
        self._add_to_history("user", request)
        
        # 简单请求路由
        response = await self._route_request(request)
        
        # 记录响应
        self._add_to_history("assistant", response)
        
        return response
    
    async def _route_request(self, request: str) -> str:
        """路由请求到合适的处理函数"""
        request_lower = request.lower()
        
        # 早晨汇报
        if "早上" in request or "今日计划" in request or "morning" in request_lower:
            briefing = await self.morning_briefing()
            return self.morning_briefing.format_report(briefing)
        
        # 晚间总结
        if "晚上" in request or "总结" in request or "evening" in request_lower:
            summary = await self.evening_summary()
            return self.evening_summary.format_report(summary)
        
        # 查记忆
        if "记得" in request or "记忆" in request:
            return await self._search_memory(request)
        
        # 学习任务
        if "学习" in request or "学" in request:
            return await self._handle_learning(request)
        
        # 工作任务
        if "工作" in request or "任务" in request:
            return await self._handle_work(request)
        
        # 默认：使用 L3 处理
        return await self._handle_with_l3(request)
    
    async def _search_memory(self, request: str) -> str:
        """搜索记忆"""
        # 简化实现
        return f"我搜索了记忆，找到了以下相关内容..."
    
    async def _handle_learning(self, request: str) -> str:
        """处理学习请求"""
        # 添加到用户记忆
        self.user_memory.add_knowledge(
            content=request,
            importance=0.5,
            tags=["learning", "user_request"]
        )
        return f"好的，我已经记录了您的学习需求：{request}"
    
    async def _handle_work(self, request: str) -> str:
        """处理工作任务"""
        # 添加为待处理任务
        self.user_memory.add_episode(
            content={"type": "task", "description": request},
            importance=0.7,
            tags=["task", "work"]
        )
        return f"已记录工作任务：{request}"
    
    async def _handle_with_l3(self, request: str) -> str:
        """使用 L3 处理复杂请求"""
        # 生成目标
        goals = self.l3.generate_intrinsic_goals()
        
        # 执行目标
        result = self.l3.execute_goal_loop(goals[0] if goals else None)
        
        if result:
            return f"我已经分析了您的请求并生成了响应。"
        
        return "我理解您的请求，让我帮您处理。"
    
    # ========== 专业 Agent ==========
    
    def register_specialist(self, name: str, agent: Any) -> None:
        """注册专业 Agent"""
        self.specialists[name] = agent
        print(f"[ButlerAgent] Registered specialist: {name}")
    
    async def call_specialist(
        self,
        specialist_name: str,
        request: str
    ) -> str:
        """调用专业 Agent"""
        if specialist_name not in self.specialists:
            return f"专业 Agent 不存在: {specialist_name}"
        
        agent = self.specialists[specialist_name]
        
        try:
            result = await agent.assist(request)
            return result
        except Exception as e:
            return f"专业 Agent {specialist_name} 处理失败: {str(e)}"
    
    # ========== 历史记录 ==========
    
    def _add_to_history(self, role: str, content: str, metadata: dict | None = None) -> None:
        """添加到对话历史"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().timestamp(),
            "metadata": metadata or {},
        })
        
        # 限制历史长度
        if len(self.conversation_history) > 1000:
            self.conversation_history = self.conversation_history[-500:]
    
    def get_history(self, limit: int = 50) -> list[dict]:
        """获取对话历史"""
        return self.conversation_history[-limit:]
    
    # ========== 状态 ==========
    
    def get_status(self) -> dict:
        """获取状态"""
        return {
            "user_id": self.user_id,
            "user_name": self.config.user_name,
            "is_initialized": self.is_initialized,
            "specialists": list(self.specialists.keys()),
            "conversation_count": len(self.conversation_history),
            "user_profile": self.user_memory.to_dict(),
        }
    
    def __repr__(self) -> str:
        return f"ButlerAgent({self.config.user_name}, specialists={len(self.specialists)})"
