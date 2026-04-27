# -*- coding: utf-8 -*-
"""
LLMGoalPrioritizer - LLM 驱动的目标优先级引擎

使用 LLM 动态评估目标优先级，替代硬编码公式。

核心职责：
1. 收集 Agent 完整状态上下文（能力、情绪、历史、资源）
2. 将状态 + 候选目标输入 LLM
3. LLM 输出优先级排序 + 理由 + 风险评估

与硬编码公式的区别：
- 硬编码：difficulty × emotion_weight = priority
- LLM：综合理解"这个目标在当前状态下做成的可能性"

设计原则：
- LLM 是"顾问"，最终决定仍可被外部覆盖
- 无 LLM 时回退到规则评分
- 输出结构化，便于日志和调试
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from usmsb_sdk.meta_agent.llm.manager import LLMManager


# ─────────────────────────────────────────────────────────────────────────────
# 数据结构
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GoalCandidate:
    """候选目标"""
    id: str | None
    name: str
    description: str
    difficulty: float = 0.5           # 0.0-1.0
    difficulty_label: str = "medium"
    collaborative: bool = False
    reasoning_style: str = "normal"
    emotional_tendency: str = "neutral"
    metadata: dict = field(default_factory=dict)
    
    def to_prompt_dict(self) -> dict:
        return {
            "name": self.name,
            "difficulty": f"{self.difficulty_label} ({self.difficulty:.2f})",
            "collaborative": "是" if self.collaborative else "否",
            "reasoning_style": self.reasoning_style,
        }


@dataclass
class AgentState:
    """Agent 状态上下文"""
    agent_id: str
    capabilities: dict[str, float] = field(default_factory=dict)  # skill -> level
    confidence: float = 0.5       # 全局信心 0.0-1.0
    motivation: str = "curiosity"  # 当前主导动机
    motivation_intensity: float = 0.5
    resources: dict[str, float] = field(default_factory=dict)  # resource -> amount
    recent_success_rate: float = 0.5  # 最近5个目标的成功率
    
    # 情绪状态
    emotional_tendency: str = "neutral"
    difficulty_multiplier: float = 1.0
    collaboration_adjustment: float = 0.0
    time_allocation: str = "maintain"
    
    # 历史（最近3个目标）
    recent_goals: list[dict] = field(default_factory=dict)
    
    def to_prompt_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "capabilities": self.capabilities or {"general": 0.6},
            "confidence": f"{self.confidence:.0%}",
            "dominant_motivation": f"{self.motivation} ({self.motivation_intensity:.0%})",
            "recent_success_rate": f"{self.recent_success_rate:.0%}",
            "emotional_state": self.emotional_tendency,
            "difficulty_adjustment": f"×{self.difficulty_multiplier:.2f}",
            "collaboration_tendency": f"{'+' if self.collaboration_adjustment >= 0 else ''}{self.collaboration_adjustment:.2f}",
        }


@dataclass
class PriorityResult:
    """优先级评估结果"""
    goal_id: str | None
    goal_name: str
    priority_score: float          # 0.0-1.0
    rank: int                     # 排名（1=最高）
    reasoning: str               # LLM 理由
    risk_level: str              # low/medium/high
    recommended_strategy: str    # 建议执行策略
    estimated_success_chance: float  # 估计成功概率
    warnings: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=lambda: time.time())
    
    def to_dict(self) -> dict:
        return {
            "goal": self.goal_name,
            "rank": self.rank,
            "priority_score": round(self.priority_score, 3),
            "reasoning": self.reasoning,
            "risk": self.risk_level,
            "strategy": self.recommended_strategy,
            "success_chance": f"{self.estimated_success_chance:.0%}",
            "warnings": self.warnings,
        }


# ─────────────────────────────────────────────────────────────────────────────
# System Prompt
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a strategic goal prioritization AI for a silicon-based Agent.

Given the Agent's current state and candidate goals, you must:
1. Evaluate which goal has the highest probability of success RIGHT NOW
2. Consider alignment with the Agent's emotional state and motivation
3. Identify risks and suggest mitigation strategies

Output format (JSON only, no other text):
{
  "rankings": [
    {
      "goal_index": 0,
      "priority_score": 0.85,
      "reasoning": "why this goal is best suited for current state",
      "risk_level": "low|medium|high",
      "recommended_strategy": "specific execution approach",
      "estimated_success_chance": 0.8,
      "warnings": ["risk1", "risk2"]
    }
  ],
  "analysis": "overall assessment of goal feasibility"
}"""

# ─────────────────────────────────────────────────────────────────────────────
# Fallback 规则评分（无 LLM 时使用）
# ─────────────────────────────────────────────────────────────────────────────

def _get_goal_difficulty(goal: Any) -> float:
    """从任意 goal 对象提取难度值"""
    # 优先用属性
    if hasattr(goal, 'difficulty'):
        return getattr(goal, 'difficulty', 0.5)
    # 再用 metadata
    if hasattr(goal, 'metadata') and isinstance(goal.metadata, dict):
        return goal.metadata.get('difficulty', 0.5)
    # 最后尝试 dict
    if isinstance(goal, dict):
        return goal.get('difficulty', 0.5)
    return 0.5


def _get_goal_difficulty_label(goal: Any) -> str:
    """从任意 goal 对象提取难度标签"""
    if hasattr(goal, 'difficulty_label'):
        return getattr(goal, 'difficulty_label', 'medium')
    if hasattr(goal, 'metadata') and isinstance(goal.metadata, dict):
        return goal.metadata.get('difficulty_label', 'medium')
    if isinstance(goal, dict):
        return goal.get('difficulty_label', 'medium')
    return 'medium'


def _is_goal_collaborative(goal: Any) -> bool:
    """从任意 goal 对象提取协作性"""
    if hasattr(goal, 'collaborative'):
        return getattr(goal, 'collaborative', False)
    if hasattr(goal, 'metadata') and isinstance(goal.metadata, dict):
        return goal.metadata.get('collaborative', False)
    if isinstance(goal, dict):
        return goal.get('collaborative', False)
    return False


def fallback_score(goal: Any, state: AgentState) -> float:
    """
    回退评分（无 LLM 时使用规则）
    
    支持任意 goal 对象类型（GoalCandidate, PoolGoal, dict）
    """
    base = 0.5
    
    difficulty = _get_goal_difficulty(goal)
    difficulty_label = _get_goal_difficulty_label(goal)
    collaborative = _is_goal_collaborative(goal)
    
    # 难度匹配：Agent 信心高 → 可以接受更高难度
    confidence_diff = abs(difficulty - state.confidence)
    difficulty_match = 0.15 * (1.0 - confidence_diff)
    
    # 协作匹配：情绪协作调整
    collab_bonus = 0.1 * state.collaboration_adjustment if collaborative else 0.0
    
    # 情绪匹配
    emotional_match = {
        "ambitious": {"hard": 0.15, "medium": 0.05, "easy": -0.05},
        "conservative": {"easy": 0.15, "medium": 0.05, "hard": -0.1},
        "exploring": {"collaborative": 0.1, "novel": 0.1},
        "risk_averse": {"easy": 0.15, "hard": -0.15},
        "trusting": {"collaborative": 0.15, "independent": -0.05},
    }.get(state.emotional_tendency, {})
    
    emotion_bonus = 0.0
    if difficulty_label in emotional_match:
        emotion_bonus += emotional_match[difficulty_label]
    if collaborative and "collaborative" in emotional_match:
        emotion_bonus += emotional_match["collaborative"]
    
    # 成功率加成
    success_bonus = 0.1 * (state.recent_success_rate - 0.5)
    
    score = base + difficulty_match + collab_bonus + emotion_bonus + success_bonus
    return max(0.0, min(1.0, score))


# ─────────────────────────────────────────────────────────────────────────────
# LLMGoalPrioritizer
# ─────────────────────────────────────────────────────────────────────────────

class LLMGoalPrioritizer:
    """
    LLM 驱动的目标优先级引擎
    
    使用 LLM 综合评估目标优先级，替代硬编码公式。
    
    使用方式：
    ```python
    prioritizer = LLMGoalPrioritizer(llm_manager)
    
    # 构建 Agent 状态
    state = AgentState(
        agent_id="agent_001",
        capabilities={"coding": 0.7, "research": 0.5},
        confidence=0.6,
        emotional_tendency="exploring",
        recent_success_rate=0.7,
    )
    
    # 评估候选目标
    candidates = [
        GoalCandidate(id="g1", name="学习新技术", difficulty=0.6),
        GoalCandidate(id="g2", name="优化代码", difficulty=0.4),
    ]
    
    results = await prioritizer.prioritize(state, candidates)
    best = results[0]  # 排名最高的目标
    ```
    
    无 LLM 时回退到规则评分，保证系统始终可用。
    """
    
    def __init__(
        self,
        llm_manager: LLMManager | None = None,
        use_fallback: bool = True,
        timeout: float = 30.0,
    ):
        self.llm = llm_manager
        self.use_fallback = use_fallback
        self.timeout = timeout
        self._stats = {
            "llm_calls": 0,
            "fallback_calls": 0,
            "llm_errors": 0,
        }
    
    async def prioritize(
        self,
        state: AgentState,
        candidates: list[GoalCandidate],
    ) -> list[PriorityResult]:
        """
        对候选目标进行优先级排序
        
        Args:
            state: Agent 当前状态
            candidates: 候选目标列表
        
        Returns:
            按优先级排序的结果列表（rank 1 = 最高优先级）
        """
        if not candidates:
            return []
        
        if len(candidates) == 1:
            # 只有一个目标，直接返回（但仍尝试 LLM 评估）
            single = candidates[0]
            if self.llm:
                try:
                    result = await self._llm_evaluate_single(state, single)
                    return [result]
                except Exception:
                    pass
            score = fallback_score(single, state)
            return [PriorityResult(
                goal_id=single.id,
                goal_name=single.name,
                priority_score=score,
                rank=1,
                reasoning="唯一候选目标",
                risk_level="medium",
                recommended_strategy="normal",
                estimated_success_chance=score,
            )]
        
        # 多个候选目标 → LLM 评估
        if self.llm:
            try:
                return await self._llm_prioritize(state, candidates)
            except Exception as e:
                self._stats["llm_errors"] += 1
                if not self.use_fallback:
                    raise
        
        # 回退到规则评分
        return self._fallback_prioritize(state, candidates)
    
    async def _llm_prioritize(
        self,
        state: AgentState,
        candidates: list[GoalCandidate],
    ) -> list[PriorityResult]:
        """使用 LLM 进行优先级排序"""
        self._stats["llm_calls"] += 1
        
        # 构建 prompt
        prompt = self._build_prompt(state, candidates)
        
        # 调用 LLM
        import asyncio
        response = await asyncio.wait_for(
            self.llm.generate_with_system(SYSTEM_PROMPT, prompt),
            timeout=self.timeout
        )
        
        # 解析 JSON 输出
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            # LLM 输出非 JSON，回退
            return self._fallback_prioritize(state, candidates)
        
        # 构建结果
        rankings = data.get("rankings", [])
        goal_map = {i: c for i, c in enumerate(candidates)}
        
        results = []
        for r in rankings:
            idx = r.get("goal_index", 0)
            if idx not in goal_map:
                continue
            
            goal = goal_map[idx]
            results.append(PriorityResult(
                goal_id=goal.id,
                goal_name=goal.name,
                priority_score=r.get("priority_score", 0.5),
                rank=len(results) + 1,
                reasoning=r.get("reasoning", ""),
                risk_level=r.get("risk_level", "medium"),
                recommended_strategy=r.get("recommended_strategy", "normal"),
                estimated_success_chance=r.get("estimated_success_chance", 0.5),
                warnings=r.get("warnings", []),
            ))
        
        # 确保所有候选都有结果
        ranked_ids = {r.goal_id for r in results}
        for i, goal in enumerate(candidates):
            if goal.id not in ranked_ids and goal.name not in {r.goal_name for r in results}:
                # 未被 LLM 评级的目标，用回退
                score = fallback_score(goal, state)
                results.append(PriorityResult(
                    goal_id=goal.id,
                    goal_name=goal.name,
                    priority_score=score,
                    rank=len(results) + 1,
                    reasoning="未被 LLM 评级（回退评分）",
                    risk_level="medium",
                    recommended_strategy="normal",
                    estimated_success_chance=score,
                ))
        
        # 按 priority_score 排序
        results.sort(key=lambda x: x.priority_score, reverse=True)
        for i, r in enumerate(results):
            r.rank = i + 1
        
        return results
    
    async def _llm_evaluate_single(
        self,
        state: AgentState,
        goal: GoalCandidate,
    ) -> PriorityResult:
        """LLM 评估单个目标（不排序）"""
        self._stats["llm_calls"] += 1
        
        prompt = self._build_prompt(state, [goal])
        
        import asyncio
        response = await asyncio.wait_for(
            self.llm.generate_with_system(SYSTEM_PROMPT, prompt),
            timeout=self.timeout
        )
        
        try:
            data = json.loads(response)
            r = data.get("rankings", [{}])[0]
            return PriorityResult(
                goal_id=goal.id,
                goal_name=goal.name,
                priority_score=r.get("priority_score", 0.5),
                rank=1,
                reasoning=r.get("reasoning", ""),
                risk_level=r.get("risk_level", "medium"),
                recommended_strategy=r.get("recommended_strategy", "normal"),
                estimated_success_chance=r.get("estimated_success_chance", 0.5),
                warnings=r.get("warnings", []),
            )
        except (json.JSONDecodeError, IndexError, KeyError):
            score = fallback_score(goal, state)
            return PriorityResult(
                goal_id=goal.id,
                goal_name=goal.name,
                priority_score=score,
                rank=1,
                reasoning="LLM 解析失败，使用回退评分",
                risk_level="medium",
                recommended_strategy="normal",
                estimated_success_chance=score,
            )
    
    def _build_prompt(self, state: AgentState, candidates: list[GoalCandidate]) -> str:
        """构建 LLM prompt"""
        state_dict = state.to_prompt_dict()
        
        candidates_text = []
        for i, g in enumerate(candidates):
            candidates_text.append(f"[目标 {i}] {g.name}")
            candidates_text.append(f"  难度: {g.difficulty_label} ({g.difficulty:.2f})")
            candidates_text.append(f"  协作: {'是' if g.collaborative else '否'}")
            candidates_text.append(f"  推理风格: {g.reasoning_style}")
            candidates_text.append("")
        
        prompt = f"""Agent 状态：
- 能力：{json.dumps(state_dict['capabilities'], ensure_ascii=False)}
- 信心：{state_dict['confidence']}
- 主导动机：{state_dict['dominant_motivation']}
- 最近成功率：{state_dict['recent_success_rate']}
- 情绪状态：{state_dict['emotional_state']}
- 难度调整：{state_dict['difficulty_adjustment']}
- 协作倾向：{state_dict['collaboration_tendency']}

候选目标：
{chr(10).join(candidates_text)}
请评估每个目标的优先级，给出排序和理由。"""
        
        return prompt
    
    def _fallback_prioritize(
        self,
        state: AgentState,
        candidates: list[GoalCandidate],
    ) -> list[PriorityResult]:
        """回退：规则评分"""
        self._stats["fallback_calls"] += 1
        
        scored = []
        for g in candidates:
            score = fallback_score(g, state)
            
            difficulty = _get_goal_difficulty(g)
            difficulty_label = _get_goal_difficulty_label(g)
            
            # 估算成功概率
            difficulty_gap = abs(difficulty - state.confidence)
            success_chance = max(0.1, min(0.95, state.recent_success_rate * (1.0 - difficulty_gap * 0.5)))
            
            # 风险等级
            if difficulty > state.confidence + 0.3:
                risk = "high"
            elif difficulty > state.confidence + 0.15:
                risk = "medium"
            else:
                risk = "low"
            
            scored.append(PriorityResult(
                goal_id=getattr(g, 'id', None),
                goal_name=getattr(g, 'name', str(g)),
                priority_score=score,
                rank=0,
                reasoning=f"规则评分：{score:.2f}（信心{state.confidence:.0%}×难度{difficulty_label}）",
                risk_level=risk,
                recommended_strategy=self._suggest_strategy(g, state),
                estimated_success_chance=success_chance,
            ))
        
        # 排序
        scored.sort(key=lambda x: x.priority_score, reverse=True)
        for i, r in enumerate(scored):
            r.rank = i + 1
        
        return scored
    
    def _suggest_strategy(self, goal: Any, state: AgentState) -> str:
        """建议执行策略"""
        difficulty = _get_goal_difficulty(goal)
        collaborative = _is_goal_collaborative(goal)
        
        if difficulty > state.confidence + 0.2:
            return "分阶段执行，先做子目标"
        elif state.emotional_tendency == "conservative":
            return "保守执行，充分验证"
        elif state.emotional_tendency == "ambitious":
            return "大胆推进，快速迭代"
        elif collaborative:
            return "协作优先，寻求支持"
        else:
            return "独立执行，专注推进"
    
    def get_stats(self) -> dict:
        """获取统计"""
        return {
            **self._stats,
            "fallback_rate": (
                self._stats["fallback_calls"] /
                max(1, self._stats["llm_calls"] + self._stats["fallback_calls"])
            ),
        }
