# -*- coding: utf-8 -*-
"""
TeamMemory - 团队共享记忆

团队上下文、历史决策、共享知识。

功能：
- 团队上下文存储
- 决策历史
- 共享知识库
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TeamContext:
    """团队上下文"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    team_id: str = ""
    content: Any = None
    category: str = ""  # decision, project, meeting, culture
    importance: float = 0.5
    contributor: str = ""  # member_id
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    tags: list[str] = field(default_factory=list)


@dataclass
class Decision:
    """团队决策"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    decision_type: str = ""  # strategic, tactical, operational
    made_by: str = ""  # member_id
    made_at: float = field(default_factory=lambda: datetime.now().timestamp())
    rationale: str = ""
    status: str = "active"  # active, superseded, cancelled
    votes: dict[str, str] = field(default_factory=dict)  # member_id -> vote


class TeamMemory:
    """
    团队共享记忆
    
    存储团队的共享上下文和历史。
    
    使用方式：
    ```python
    memory = TeamMemory(team_id="team_001")
    
    # 添加上下文
    memory.add_context("Q2目标", category="project")
    
    # 添加决策
    memory.add_decision("采用微服务架构", rationale="...")
    
    # 查询
    results = memory.search("架构")
    ```
    """
    
    def __init__(self, team_id: str):
        self.team_id = team_id
        
        # 上下文存储
        self.contexts: list[TeamContext] = []
        
        # 决策存储
        self.decisions: list[Decision] = []
        
        # 索引
        self.category_index: dict[str, list[str]] = {}  # category -> [context_ids]
        self.tag_index: dict[str, list[str]] = {}  # tag -> [context_ids]
        
        print(f"[TeamMemory] Initialized for team: {team_id}")
    
    # ========== 上下文管理 ==========
    
    def add_context(
        self,
        content: Any,
        category: str = "",
        importance: float = 0.5,
        contributor: str = "",
        tags: list[str] | None = None
    ) -> str:
        """
        添加团队上下文
        
        Args:
            content: 内容
            category: 类别
            importance: 重要性
            contributor: 贡献者
            tags: 标签
            
        Returns:
            str: 上下文 ID
        """
        context = TeamContext(
            team_id=self.team_id,
            content=content,
            category=category,
            importance=importance,
            contributor=contributor,
            tags=tags or [],
        )
        
        self.contexts.append(context)
        
        # 更新索引
        if category:
            if category not in self.category_index:
                self.category_index[category] = []
            self.category_index[category].append(context.id)
        
        for tag in context.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = []
            self.tag_index[tag].append(context.id)
        
        return context.id
    
    def get_context(self, context_id: str) -> TeamContext | None:
        """获取上下文"""
        for ctx in self.contexts:
            if ctx.id == context_id:
                return ctx
        return None
    
    def get_by_category(self, category: str) -> list[TeamContext]:
        """按类别获取"""
        context_ids = self.category_index.get(category, [])
        return [self.get_context(cid) for cid in context_ids if self.get_context(cid)]
    
    def get_by_tag(self, tag: str) -> list[TeamContext]:
        """按标签获取"""
        context_ids = self.tag_index.get(tag, [])
        return [self.get_context(cid) for cid in context_ids if self.get_context(cid)]
    
    def search(self, query: str) -> list[TeamContext]:
        """搜索"""
        results = []
        query_lower = query.lower()
        
        for ctx in self.contexts:
            content_str = str(ctx.content).lower()
            if query_lower in content_str:
                results.append(ctx)
            elif any(query_lower in tag.lower() for tag in ctx.tags):
                results.append(ctx)
        
        return results
    
    # ========== 决策管理 ==========
    
    def add_decision(
        self,
        title: str,
        description: str = "",
        decision_type: str = "",
        made_by: str = "",
        rationale: str = ""
    ) -> str:
        """
        添加团队决策
        
        Args:
            title: 决策标题
            description: 描述
            decision_type: 类型
            made_by: 决策者
            rationale: 理由
            
        Returns:
            str: 决策 ID
        """
        decision = Decision(
            title=title,
            description=description,
            decision_type=decision_type,
            made_by=made_by,
            rationale=rationale,
        )
        
        self.decisions.append(decision)
        
        # 同时添加到上下文
        self.add_context(
            content={
                "type": "decision",
                "title": title,
                "decision_id": decision.id,
            },
            category="decision",
            importance=0.8,
            contributor=made_by,
        )
        
        return decision.id
    
    def vote_decision(self, decision_id: str, member_id: str, vote: str) -> bool:
        """
        投票决策
        
        Args:
            decision_id: 决策 ID
            member_id: 成员 ID
            vote: 投票 (yes, no, abstain)
        """
        for decision in self.decisions:
            if decision.id == decision_id:
                decision.votes[member_id] = vote
                return True
        return False
    
    def get_decision(self, decision_id: str) -> Decision | None:
        """获取决策"""
        for decision in self.decisions:
            if decision.id == decision_id:
                return decision
        return None
    
    def get_active_decisions(self) -> list[Decision]:
        """获取活跃决策"""
        return [d for d in self.decisions if d.status == "active"]
    
    # ========== 周会记录 ==========
    
    def add_meeting_notes(
        self,
        meeting_type: str,
        content: str,
        attendees: list[str],
        outcomes: list[str]
    ) -> str:
        """
        添加会议记录
        
        Args:
            meeting_type: 会议类型 (weekly, planning, retrospective)
            content: 内容
            attendees: 参会人
            outcomes: 决议
            
        Returns:
            str: 记录 ID
        """
        context = self.add_context(
            content={
                "type": "meeting",
                "meeting_type": meeting_type,
                "content": content,
                "attendees": attendees,
                "outcomes": outcomes,
            },
            category="meeting",
            importance=0.6,
        )
        
        return context
    
    # ========== 统计 ==========
    
    def get_statistics(self) -> dict:
        """获取统计"""
        return {
            "team_id": self.team_id,
            "total_contexts": len(self.contexts),
            "total_decisions": len(self.decisions),
            "active_decisions": len(self.get_active_decisions()),
            "categories": list(self.category_index.keys()),
            "tags": list(self.tag_index.keys()),
        }
    
    def __repr__(self) -> str:
        return f"TeamMemory({self.team_id}, contexts={len(self.contexts)})"
