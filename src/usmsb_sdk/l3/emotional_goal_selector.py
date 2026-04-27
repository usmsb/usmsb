# -*- coding: utf-8 -*-
"""
EmotionalGoalSelector - 情绪注入的目标选择器

将情绪行为倾向（ActionTendency）注入目标生成和选择过程。

核心职责：
1. 注入情绪上下文到 LLM prompt
2. 根据 difficulty_multiplier 调整目标难度
3. 根据 reasoning_strategy 选择推理方式
4. 根据 collaboration_adjustment 倾向选择协作/独立目标

设计原则：
- 情绪通过"软约束"影响目标，不是硬替换
- LLM 仍然自由生成，但带着情绪背景
- 难度调整是后处理，不改变目标内容
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from usmsb_sdk.l4.emotional_architecture import (
        EmotionalArchitecture, ActionTendency
    )


# 难度等级定义
DIFFICULTY_LABELS = {
    (0.0, 0.2): "trivial",      # 微不足道
    (0.2, 0.4): "easy",          # 简单
    (0.4, 0.6): "medium",        # 中等
    (0.6, 0.8): "hard",          # 困难
    (0.8, 1.0): "exceptional",   # 极难
}


def difficulty_label(score: float) -> str:
    """将数值转换为难度标签"""
    for (low, high), label in DIFFICULTY_LABELS.items():
        if low <= score < high:
            return label
    return "medium"


# 情绪背景的目标前缀（注入到 prompt）
EMOTIONAL_GOAL_PREFIXES = {
    "ambitious": "一个具有挑战性的目标",
    "conservative": "一个稳妥可靠的目标",
    "exploring": "一个探索性的目标",
    "risk_averse": "一个保守安全的目标",
    "challenging": "一个竞争性的目标",
    "optimistic": "一个积极向上的目标",
    "recalibrating": "一个需要重新审视的目标",
    "vigilant": "一个需要谨慎评估的目标",
    "trusting": "一个协作性的目标",
    "withdrawn": "一个内省性的目标",
    "nurturing": "一个培育性的目标",
}


# 目标难度基准池（启发式生成时的素材）
DIFFICULTY_BASED_GOALS = {
    "trivial": [
        "整理一下今天的学习笔记",
        "检查一下工具箱的完整性",
        "更新一下个人待办清单",
        "回顾一下最近的对话记录",
    ],
    "easy": [
        "学习一个新技术概念",
        "练习一个工具使用方法",
        "优化一段现有代码",
        "总结一次协作经验",
    ],
    "medium": [
        "掌握一个新领域的核心原理",
        "构建一个中等规模的功能模块",
        "分析并解决一个复杂问题",
        "建立一个新的协作关系",
    ],
    "hard": [
        "攻克一个长期未解决的技术难题",
        "独立完成一个完整的产品设计",
        "发起并推动一个跨团队项目",
        "在未知领域建立第一个里程碑",
    ],
    "exceptional": [
        "实现一个前所未有的创新突破",
        "建立一个全新的能力体系",
        "推动一个改变规则的项目",
        "完成一个被认为不可能的任务",
    ],
}


@dataclass
class EmotionalContext:
    """情绪上下文（注入到目标生成）"""
    tendency: str                    # 行为倾向名称
    tendency_confidence: float       # 置信度
    difficulty_multiplier: float     # 难度系数
    reasoning_strategy: str          # 推理策略
    collaboration_adjustment: float  # 协作倾向调整
    time_allocation: str             # 时间分配
    dominant_emotion: str | None     # 主导情绪
    
    def inject_into_prompt(self, base_prompt: str) -> str:
        """将情绪上下文注入到 prompt"""
        prefix = EMOTIONAL_GOAL_PREFIXES.get(
            self.tendency, "一个目标"
        )
        
        emotional_note = f"""
[情绪背景]
当前行为倾向：{self.tendency}（置信度 {self.tendency_confidence:.2f}）
主导情绪：{self.dominant_emotion or '无'}
推理策略：{self.reasoning_strategy}
协作倾向：{'积极' if self.collaboration_adjustment >= 0 else '保守'}
时间策略：{self.time_allocation}

请生成{prefix}，符合上述情绪状态。"""
        
        return base_prompt + emotional_note
    
    def get_reasoning_style(self) -> str:
        """获取推理风格描述（供 LLM 参考）"""
        return f"[推理风格: {self.reasoning_strategy}]"
    
    def should_prefer_collaborative(self) -> bool:
        """是否倾向协作目标"""
        return self.collaboration_adjustment > 0.05


class EmotionalGoalSelector:
    """
    情绪目标选择器
    
    接收情绪引导 → 注入 prompt → 调整目标难度
    
    使用方式：
    ```python
    selector = EmotionalGoalSelector(emotional_arch)
    
    # 方式1：用情绪上下文生成 prompt
    enhanced_prompt = selector.enhance_prompt(base_prompt)
    
    # 方式2：用难度基准池生成目标（不用 LLM）
    goal = selector.generate_goal_from_pool(difficulty)
    
    # 方式3：后处理 LLM 生成的目标
    adjusted = selector.adjust_goal_difficulty(goal, emotional_context)
    ```
    """
    
    def __init__(
        self,
        emotional_architecture: EmotionalArchitecture | None = None,
    ):
        self.emotions = emotional_architecture
    
    def get_emotional_context(self) -> EmotionalContext | None:
        """从情感架构获取当前情绪上下文"""
        if not self.emotions:
            return None
        
        guidance = self.emotions.get_behavioral_guidance()
        dominant = self.emotions.mood.get_dominant_emotion()
        
        return EmotionalContext(
            tendency=guidance["tendency"],
            tendency_confidence=guidance["confidence"],
            difficulty_multiplier=guidance["difficulty_multiplier"],
            reasoning_strategy=guidance["reasoning_strategy"],
            collaboration_adjustment=guidance["collaboration_adjustment"],
            time_allocation=guidance["time_allocation"],
            dominant_emotion=dominant.value if dominant else None,
        )
    
    def enhance_prompt(self, base_prompt: str) -> str:
        """将情绪上下文注入 prompt"""
        ctx = self.get_emotional_context()
        if not ctx:
            return base_prompt
        return ctx.inject_into_prompt(base_prompt)
    
    def generate_goal_from_pool(
        self,
        base_difficulty: float = 0.5,
    ) -> dict:
        """
        从难度池生成目标（不需要 LLM）
        
        根据情绪调整后的难度，从池中选择或生成目标。
        
        Args:
            base_difficulty: 基础难度 (0.0-1.0)
        
        Returns:
            dict: 包含 name, description, difficulty, reasoning_style
        """
        ctx = self.get_emotional_context()
        multiplier = ctx.difficulty_multiplier if ctx else 1.0
        
        # 计算调整后难度
        adjusted = min(1.0, base_difficulty * multiplier)
        adjusted = max(0.0, adjusted)
        
        # 找难度等级
        label = difficulty_label(adjusted)
        
        # 选择池
        candidates = DIFFICULTY_BASED_GOALS.get(label, DIFFICULTY_BASED_GOALS["medium"])
        
        # 如果倾向协作，在目标中加协作元素
        if ctx and ctx.should_prefer_collaborative():
            collaborative_suffixes = [
                "，并与同伴分享经验",
                "，探索协作的可能性",
                "，寻求同伴的支持",
            ]
            chosen = random.choice(candidates)
            suffix = random.choice(collaborative_suffixes)
            name = chosen + suffix
        else:
            name = random.choice(candidates)
        
        # 推理风格
        reasoning = ctx.get_reasoning_style() if ctx else "[推理风格: normal]"
        
        return {
            "name": name,
            "description": name,
            "difficulty": adjusted,
            "difficulty_label": label,
            "reasoning_style": reasoning,
            "emotional_tendency": ctx.tendency if ctx else "neutral",
            "collaborative": ctx.should_prefer_collaborative() if ctx else False,
        }
    
    def adjust_goal_difficulty(
        self,
        goal: Any,
        base_difficulty: float = 0.5,
    ) -> Any:
        """
        后处理 LLM 生成的目标，调整其难度
        
        Args:
            goal: 目标对象（dict 或 Goal 对象）
            base_difficulty: LLM 生成时隐含的难度
        
        Returns:
            调整后的 goal（修改了 difficulty 相关的 metadata）
        """
        ctx = self.get_emotional_context()
        multiplier = ctx.difficulty_multiplier if ctx else 1.0
        
        adjusted = min(1.0, base_difficulty * multiplier)
        adjusted = max(0.0, adjusted)
        label = difficulty_label(adjusted)
        
        # 设置到 goal 的 metadata
        if hasattr(goal, 'metadata'):
            goal.metadata = goal.metadata or {}
            goal.metadata['difficulty'] = adjusted
            goal.metadata['difficulty_label'] = label
            goal.metadata['emotional_tendency'] = ctx.tendency if ctx else 'neutral'
            goal.metadata['reasoning_strategy'] = ctx.reasoning_strategy if ctx else 'normal'
            goal.metadata['collaboration_adjustment'] = ctx.collaboration_adjustment if ctx else 0.0
            goal.metadata['time_allocation'] = ctx.time_allocation if ctx else 'maintain'
        
        return goal
    
    def select_from_candidates(
        self,
        goals: list[Any],
        base_priority_key: str = "priority",
    ) -> Any | None:
        """
        从候选目标列表中选择最符合当前情绪的目标
        
        情绪影响选择：
        - AMBITIOUS → 选难度高的
        - CONSERVATIVE → 选难度低的
        - EXPLORING → 选新颖的（metadata 中 novelty 最高的）
        - RISK_AVERSE → 选难度低且有备份方案的
        
        Args:
            goals: 候选目标列表
            base_priority_key: 原始优先级字段名
        
        Returns:
            最符合情绪的目标，或 None
        """
        if not goals:
            return None
        
        ctx = self.get_emotional_context()
        if not ctx:
            return goals[0] if goals else None
        
        tendency = ctx.tendency
        
        # 预评分
        scored = []
        for g in goals:
            diff = 0.5
            if hasattr(g, 'metadata') and g.metadata:
                diff = g.metadata.get('difficulty', 0.5)
            
            score = self._score_goal(g, diff, tendency, ctx)
            scored.append((score, g))
        
        # 选最高分
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]
    
    def _score_goal(
        self,
        goal: Any,
        difficulty: float,
        tendency: str,
        ctx: EmotionalContext,
    ) -> float:
        """为单个目标打分"""
        base_score = 0.5
        
        if tendency == "ambitious":
            # 倾向高难度
            return base_score + (difficulty - 0.5) * 0.6
        
        elif tendency == "conservative":
            # 倾向低难度
            return base_score + (0.5 - difficulty) * 0.6
        
        elif tendency == "risk_averse":
            # 倾向低难度 + 有备份
            has_backup = goal.metadata.get('has_backup', False) if hasattr(goal, 'metadata') else False
            risk_score = 0.3 if difficulty < 0.4 else (-0.3 if difficulty > 0.6 else 0)
            backup_score = 0.2 if has_backup else 0
            return base_score + risk_score + backup_score
        
        elif tendency == "exploring":
            # 倾向新颖
            novelty = goal.metadata.get('novelty', 0.5) if hasattr(goal, 'metadata') else 0.5
            return base_score + (novelty - 0.5) * 0.5
        
        elif tendency == "trusting":
            # 倾向协作
            is_collab = goal.metadata.get('collaborative', False) if hasattr(goal, 'metadata') else False
            return base_score + (0.3 if is_collab else 0)
        
        elif tendency == "recalibrating":
            # 倾向需要审视的
            needs_review = goal.metadata.get('needs_review', True) if hasattr(goal, 'metadata') else False
            return base_score + (0.2 if needs_review else 0)
        
        elif tendency == "vigilant":
            # 倾向风险可控
            risk_controlled = goal.metadata.get('risk_level', 0.5) if hasattr(goal, 'metadata') else 0.5
            return base_score + (0.5 - risk_controlled) * 0.5
        
        else:
            return base_score
