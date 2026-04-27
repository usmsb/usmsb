# -*- coding: utf-8 -*-
"""
Metacognition - L4 元认知 v2

元认知 = 思考自己在想什么。

v2 升级（闭环）：
- 推理追踪：记录每一步思考
- 质量评估：评估推理质量
- 策略优化：根据任务场景选择策略
- 困惑检测：发现思维卡住
- 自我纠正：发现错误后纠正
- 场景闭环：记录"场景+策略→结果"，下次类似任务复用成功策略
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ReasoningQuality(Enum):
    """推理质量等级"""
    EXCELLENT = "excellent"    # 0.9+
    GOOD = "good"              # 0.7-0.9
    ADEQUATE = "adequate"      # 0.5-0.7
    POOR = "poor"              # 0.3-0.5
    FAILED = "failed"          # < 0.3


# ─────────────────────────────────────────────────────────────────────────────
# 任务场景类型
# ─────────────────────────────────────────────────────────────────────────────

class TaskScenario(Enum):
    """任务场景类型（用于策略匹配）"""
    COMPLEX_PROBLEM = "complex_problem"      # 复杂多步骤问题
    NOVEL_PROBLEM = "novel_problem"          # 全新/未知问题
    PATTERN_RECOGNITION = "pattern_recognition"  # 模式识别/类比
    SOCIAL = "social"                        # 社交/协作类问题
    KNOWLEDGE_GAP = "knowledge_gap"          # 知识缺口类
    SEARCH = "search"                        # 搜索/查找类
    TRIAL_AND_ERROR = "trial_and_error"      # 试错类
    GENERALIZATION = "generalization"          # 泛化/抽象类
    DECISION = "decision"                    # 决策类（有明确选项）
    PLANNING = "planning"                    # 规划类（多阶段）


# 场景描述（用于 LLM 判断）
# 策略 applicable_scenarios 别名映射（模块级别，供 _matches_scenario 使用）
SCENARIO_ALIASES = {
    "social": ["social", "social_problem"],
    "social_problem": ["social", "social_problem"],
    "complex_problem": ["complex_problem", "multi_step"],
    "novel_problem": ["novel_problem"],
    "planning": ["planning", "complex_problem"],
}

SCENARIO_DESCRIPTIONS = {
    TaskScenario.COMPLEX_PROBLEM: "复杂多步骤问题，需要分解为子问题",
    TaskScenario.NOVEL_PROBLEM: "全新的、从未遇到过的问题",
    TaskScenario.PATTERN_RECOGNITION: "识别模式、找相似问题的解法",
    TaskScenario.SOCIAL: "涉及他人意图、协作或社交交互",
    TaskScenario.KNOWLEDGE_GAP: "需要获取外部知识填补认知空白",
    TaskScenario.SEARCH: "搜索、查找、探索未知空间",
    TaskScenario.TRIAL_AND_ERROR: "通过尝试和错误逐步逼近解法",
    TaskScenario.GENERALIZATION: "从具体实例提取普遍规律",
    TaskScenario.DECISION: "在多个选项中选择最优",
    TaskScenario.PLANNING: "制定多阶段行动计划",
}


@dataclass
class ReasoningStep:
    """推理步骤"""
    step_number: int
    thought: str              # 思考内容
    evidence: list[str] = field(default_factory=list)  # 证据
    confidence: float = 0.5   # 该步骤置信度
    revised: bool = False     # 是否被修订过
    revision_reason: str = "" # 修订原因
    alternatives_considered: list[str] = field(default_factory=list)  # 考虑过的替代方案
    timestamp: float = field(default_factory=lambda: time.time())


@dataclass
class ReasoningTrace:
    """推理追踪"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""            # 推理目标
    scenario: str = "general"  # 任务场景
    steps: list[ReasoningStep] = field(default_factory=list)
    strategy_used: str = ""    # 使用的策略名称
    quality_score: float = 0.0
    quality_grade: ReasoningQuality = ReasoningQuality.ADEQUATE
    alternatives_considered: list[str] = field(default_factory=list)  # 全局替代方案
    start_time: float = field(default_factory=lambda: time.time())
    end_time: float | None = None
    conclusion: str = ""
    is_complete: bool = False
    task_context: dict = field(default_factory=dict)  # 任务上下文（难度/类型等）
    
    def add_step(self, thought: str, evidence: list[str] | None = None) -> ReasoningStep:
        step = ReasoningStep(
            step_number=len(self.steps) + 1,
            thought=thought,
            evidence=evidence or [],
        )
        self.steps.append(step)
        return step
    
    def revise_step(self, step_number: int, new_thought: str, reason: str) -> None:
        if 0 <= step_number < len(self.steps):
            step = self.steps[step_number]
            step.thought = new_thought
            step.revised = True
            step.revision_reason = reason
    
    def calculate_quality(self) -> float:
        if not self.steps:
            return 0.0
        
        score = 0.0
        
        # 1. 有证据的步骤比例 (30%)
        steps_with_evidence = sum(1 for s in self.steps if s.evidence)
        score += (steps_with_evidence / len(self.steps)) * 0.3
        
        # 2. 考虑替代方案 (20%)
        total_alternatives = sum(len(s.alternatives_considered) for s in self.steps)
        score += min(1.0, total_alternatives / 3) * 0.2
        
        # 3. 自我修订次数 (20%)
        revised_count = sum(1 for s in self.steps if s.revised)
        score += min(1.0, revised_count / 2) * 0.2
        
        # 4. 平均置信度 (20%)
        avg_confidence = sum(s.confidence for s in self.steps) / len(self.steps)
        score += avg_confidence * 0.2
        
        # 5. 完成度 (10%)
        if self.is_complete:
            score += 0.1
        
        self.quality_score = min(1.0, score)
        
        if self.quality_score >= 0.9:
            self.quality_grade = ReasoningQuality.EXCELLENT
        elif self.quality_score >= 0.7:
            self.quality_grade = ReasoningQuality.GOOD
        elif self.quality_score >= 0.5:
            self.quality_grade = ReasoningQuality.ADEQUATE
        elif self.quality_score >= 0.3:
            self.quality_grade = ReasoningQuality.POOR
        else:
            self.quality_grade = ReasoningQuality.FAILED
        
        return self.quality_score


@dataclass
class LearningStrategy:
    """学习策略"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    applicable_scenarios: list[str] = field(default_factory=list)
    success_rate: float = 0.5
    usage_count: int = 0
    avg_quality: float = 0.0
    
    # v2: 场景维度的成功率（scenario → (successes, total)）
    # 这才是闭环的核心：同类任务+同类策略→效果
    scenario_history: dict[str, dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: {"success": 0, "total": 0}))
    
    def get_scenario_success_rate(self, scenario: str) -> float:
        """获取某个场景下的成功率"""
        history = self.scenario_history.get(scenario, {"success": 0, "total": 0})
        total = history["total"]
        if total == 0:
            return self.success_rate  # 无历史，用全局
        return history["success"] / total
    
    def record_scenario_outcome(self, scenario: str, success: bool) -> None:
        """记录某个场景的结果"""
        self.scenario_history[scenario]["total"] += 1
        if success:
            self.scenario_history[scenario]["success"] += 1


class LearningStrategyRegistry:
    """学习策略注册表"""
    
    def __init__(self):
        self.strategies: dict[str, LearningStrategy] = {}
        self._init_default_strategies()
    
    def _init_default_strategies(self) -> None:
        defaults = [
            LearningStrategy(
                name="divide_and_conquer",
                description="分而治之：将大问题分解为小问题",
                applicable_scenarios=["complex_problem", "multi_step", "planning"]
            ),
            LearningStrategy(
                name="analogy",
                description="类比推理：找相似问题的解法",
                applicable_scenarios=["novel_problem", "pattern_recognition"]
            ),
            LearningStrategy(
                name="backtracking",
                description="回溯法：从错误中学习并修正",
                applicable_scenarios=["trial_and_error", "search"]
            ),
            LearningStrategy(
                name="abstraction",
                description="抽象化：提取本质特征",
                applicable_scenarios=["generalization", "concept_formation"]
            ),
            LearningStrategy(
                name="collaboration",
                description="协作求解：借助他人知识",
                applicable_scenarios=["social_problem", "knowledge_gap"]
            ),
            LearningStrategy(
                name="decision_tree",
                description="决策树：穷举选项后比较",
                applicable_scenarios=["decision", "planning"]
            ),
        ]
        
        for s in defaults:
            self.strategies[s.name] = s
    
    def _matches_scenario(self, strategy: LearningStrategy, scenario: str) -> bool:
        """判断策略是否适用于给定场景（含别名）"""
        if scenario in strategy.applicable_scenarios:
            return True
        aliases = SCENARIO_ALIASES.get(scenario, [])
        return any(a in strategy.applicable_scenarios for a in aliases)
    
    def get_for_scenario(self, scenario: str) -> LearningStrategy | None:
        """获取适合场景的策略（基于历史成功率）"""
        candidates = [
            s for s in self.strategies.values()
            if self._matches_scenario(s, scenario)
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda s: s.get_scenario_success_rate(scenario))
    
    def get_best_for_context(
        self,
        scenario: str,
        task_metadata: dict | None = None,
    ) -> tuple[LearningStrategy | None, str]:
        """
        根据完整上下文获取最佳策略
        
        Returns:
            (最佳策略, 选择理由)
        """
        # 只选择适用该场景的策略
        candidates = [
            s for s in self.strategies.values()
            if self._matches_scenario(s, scenario)
        ]
        if not candidates:
            return None, "no_strategies"
        
        # 计算综合分数
        scored = []
        for s in candidates:
            # 场景匹配权重（已过滤，只选匹配的）
            scenario_match = 1.0
            
            # 场景历史成功率
            scenario_history = s.scenario_history.get(scenario, {"success": 0, "total": 0})
            scenario_total = scenario_history["total"]
            scenario_rate = s.get_scenario_success_rate(scenario)
            
            # 全局成功率（兜底）
            global_rate = s.success_rate
            
            # 置信度：样本数决定，越多样本越可靠
            if scenario_total == 0:
                # 无该场景历史 → 用全局，全局样本也少时降权
                confidence = min(0.5, s.usage_count / 10)
                rate = global_rate * (0.5 + confidence)
            else:
                # 有该场景历史 → 样本越多，场景权重越高
                confidence = min(0.9, scenario_total / 5)
                # 场景历史占主导，全局做平滑
                rate = scenario_rate * confidence + global_rate * (1 - confidence)
            
            # 综合分 = 场景匹配加分 + 成功率加权
            score = scenario_match * 0.2 + rate * 0.8
            
            scored.append((score, s))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        best = scored[0][1]
        
        reason = f"场景匹配{'✓' if self._matches_scenario(best, scenario) else '✗'}, "
        reason += f"场景成功率 {best.get_scenario_success_rate(scenario):.0%}, "
        reason += f"全局成功率 {best.success_rate:.0%}, "
        reason += f"使用次数 {best.usage_count}"
        
        return best, reason
    
    def record_outcome(
        self,
        strategy_name: str,
        success: bool,
        quality: float,
        scenario: str | None = None,
    ) -> None:
        """记录策略使用结果（含场景）"""
        if strategy_name not in self.strategies:
            return
        
        s = self.strategies[strategy_name]
        s.usage_count += 1
        
        # 指数加权移动平均更新全局质量
        s.avg_quality = s.avg_quality * 0.8 + quality * 0.2
        
        # 更新全局成功率
        if success:
            s.success_rate = s.success_rate * 0.95 + 0.05
        else:
            s.success_rate = s.success_rate * 0.95 - 0.02
        s.success_rate = max(0.0, min(1.0, s.success_rate))
        
        # v2: 如果有场景，记录到场景历史
        if scenario:
            s.record_scenario_outcome(scenario, success)


class Metacognition:
    """
    元认知引擎 v2
    
    核心能力：
    1. 追踪自己的思考过程
    2. 评估推理质量
    3. 检测困惑
    4. 从学习中学习（v2: 场景闭环）
    5. 基于历史的任务-策略匹配
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        
        # 当前推理追踪
        self.current_trace: ReasoningTrace | None = None
        
        # 历史推理追踪
        self.reasoning_history: list[ReasoningTrace] = []
        
        # 学习策略
        self.learning_strategies = LearningStrategyRegistry()
        
        # 元认知统计
        self.stats = {
            "total_reasonings": 0,
            "excellent_count": 0,
            "failed_count": 0,
            "confusion_detections": 0,
            "self_corrections": 0,
            "scenario_history_hits": 0,
        }
    
    def start_reasoning(
        self,
        goal: str,
        scenario: str | None = None,
        task_metadata: dict | None = None,
    ) -> tuple[ReasoningTrace, str]:
        """
        开始新的推理追踪
        
        Returns:
            (推理追踪, 建议的策略名称)
        """
        # 获取推荐策略
        scenario = scenario or "general"
        best_strategy, strategy_reason = self.learning_strategies.get_best_for_context(
            scenario, task_metadata
        )
        strategy_name = best_strategy.name if best_strategy else "none"
        
        trace = ReasoningTrace(
            goal=goal,
            scenario=scenario,
            strategy_used=strategy_name,
            task_context=task_metadata or {},
        )
        self.current_trace = trace
        self.stats["total_reasonings"] += 1
        
        return trace, strategy_reason
    
    def think(
        self,
        thought: str,
        evidence: list[str] | None = None,
    ) -> ReasoningStep:
        """添加思考步骤"""
        if not self.current_trace:
            self.start_reasoning("unknown")
        
        step = self.current_trace.add_step(thought, evidence)
        return step
    
    def consider_alternative(self, alternative: str) -> None:
        """记录考虑过的替代方案"""
        if self.current_trace:
            if self.current_trace.steps:
                self.current_trace.steps[-1].alternatives_considered.append(alternative)
            self.current_trace.alternatives_considered.append(alternative)
    
    def revise(self, reason: str, new_thought: str) -> None:
        """自我纠正"""
        if not self.current_trace or not self.current_trace.steps:
            return
        
        last_step = self.current_trace.steps[-1]
        self.current_trace.revise_step(last_step.step_number - 1, new_thought, reason)
        self.stats["self_corrections"] += 1
    
    def finish_reasoning(
        self,
        conclusion: str,
        task_outcome: dict | None = None,
    ) -> ReasoningTrace:
        """
        完成推理
        
        Args:
            conclusion: 推理结论
            task_outcome: 可选，任务执行结果 {
                "success": bool,
                "quality": float,
            }
        """
        if not self.current_trace:
            return ReasoningTrace()
        
        self.current_trace.conclusion = conclusion
        self.current_trace.is_complete = True
        self.current_trace.end_time = time.time()
        self.current_trace.calculate_quality()
        
        # 更新统计
        if self.current_trace.quality_grade == ReasoningQuality.EXCELLENT:
            self.stats["excellent_count"] += 1
        elif self.current_trace.quality_grade == ReasoningQuality.FAILED:
            self.stats["failed_count"] += 1
        
        # 记录策略结果（含场景）
        strategy = self.current_trace.strategy_used
        scenario = self.current_trace.scenario
        
        # 任务结果优先，否则用推理质量
        if task_outcome:
            success = task_outcome.get("success", self.current_trace.quality_score > 0.5)
            quality = task_outcome.get("quality", self.current_trace.quality_score)
        else:
            success = self.current_trace.quality_score > 0.5
            quality = self.current_trace.quality_score
        
        self.learning_strategies.record_outcome(
            strategy_name=strategy,
            success=success,
            quality=quality,
            scenario=scenario,
        )
        
        # 存档
        self.reasoning_history.append(self.current_trace)
        
        result = self.current_trace
        self.current_trace = None
        
        return result
    
    def think_about_thinking(self) -> str:
        """元认知：思考自己在想什么"""
        if not self.current_trace or not self.current_trace.steps:
            return "我没有在思考任何事情。"
        
        current_step = self.current_trace.steps[-1]
        quality = self.current_trace.calculate_quality()
        
        response = f"我在想：{current_step.thought[:100]}..."
        
        if quality < 0.5:
            response += f"\n⚠️ 推理质量较低（{quality:.2f}），建议换一种思考方式。"
            response += f"\n💡 可以考虑：{', '.join(current_step.alternatives_considered[:2]) if current_step.alternatives_considered else '尝试分解问题'}"
        else:
            response += f"\n✅ 推理质量正常（{quality:.2f}），继续。"
        
        return response
    
    def detect_confusion(self) -> bool:
        """检测困惑"""
        if not self.current_trace or len(self.current_trace.steps) < 3:
            return False
        
        recent = self.current_trace.steps[-3:]
        
        confidence_trend = [
            recent[i].confidence - recent[i+1].confidence
            for i in range(len(recent)-1)
        ]
        if sum(confidence_trend) > 0.2:
            self.stats["confusion_detections"] += 1
            return True
        
        for i, step in enumerate(recent[:-1]):
            if step.thought[:50] == recent[-1].thought[:50]:
                self.stats["confusion_detections"] += 1
                return True
        
        if all(not s.evidence for s in recent):
            self.stats["confusion_detections"] += 1
            return True
        
        return False
    
    def get_confusion_reason(self) -> str:
        """获取困惑原因"""
        if not self.current_trace:
            return "无推理进行中"
        
        recent = self.current_trace.steps[-3:] if self.current_trace.steps else []
        
        if len(recent) < 3:
            return "推理步骤不足"
        
        confidence_trend = [
            recent[i].confidence - recent[i+1].confidence
            for i in range(len(recent)-1)
        ]
        if sum(confidence_trend) > 0.2:
            return "置信度持续下降，可能走错了方向"
        
        if all(not s.evidence for s in recent):
            return "缺乏证据支持，需要更多信息"
        
        for i, step in enumerate(recent[:-1]):
            if step.thought[:50] == recent[-1].thought[:50]:
                return "检测到循环推理，可能陷入局部最优"
        
        return "未知原因"
    
    def suggest_strategy(self) -> tuple[LearningStrategy | None, str]:
        """
        建议学习策略（基于场景历史）
        
        Returns:
            (策略, 选择理由)
        """
        if self.detect_confusion():
            return (
                self.learning_strategies.strategies.get("backtracking"),
                "检测到困惑，建议回溯"
            )
        
        if not self.current_trace:
            return None, "无推理进行中"
        
        scenario = self.current_trace.scenario
        metadata = self.current_trace.task_context
        
        return self.learning_strategies.get_best_for_context(scenario, metadata)
    
    def classify_scenario(
        self,
        goal_description: str,
        task_metadata: dict | None = None,
    ) -> str:
        """
        根据目标描述和上下文分类任务场景
        
        规则化分类（不用 LLM）：
        - 包含"分解"/"多步"/"阶段" → complex_problem
        - 包含"类似"/"相似"/"模式" → pattern_recognition
        - 包含"协作"/"他人"/"社交" → social
        - 包含"搜索"/"查找"/"探索" → search
        - 包含"决策"/"选择"/"选项" → decision
        - 包含"规划"/"计划"/"安排" → planning
        - 包含"新"/"未知"/"从未" → novel_problem
        - 否则 → general
        """
        desc = goal_description.lower()
        
        # 场景关键字（包含别名映射）
        scenario_keywords = {
            "complex_problem": ["分解", "多步", "阶段", "复杂", "多个", "逐步"],
            "novel_problem": ["新", "未知", "从未", "创新", "突破"],
            "pattern_recognition": ["类似", "相似", "模式", "类比", "规律"],
            "social": ["协作", "合作", "他人", "社交", "团队", "沟通", "social"],
            "search": ["搜索", "查找", "探索", "寻找", "发现"],
            "decision": ["决策", "选择", "比较", "权衡", "最优"],
            "planning": ["规划", "计划", "安排", "设计", "策划"],
            "trial_and_error": ["尝试", "试错", "实验", "验证"],
            "knowledge_gap": ["学习", "了解", "研究", "理解", "掌握"],
            "generalization": ["抽象", "概括", "总结", "归纳", "泛化"],
        }
        
        for scenario, keywords in scenario_keywords.items():
            if any(kw in desc for kw in keywords):
                return scenario
        
        # 从 metadata 推断
        if task_metadata:
            if task_metadata.get("is_collaborative"):
                return "social"
            if task_metadata.get("is_multi_step"):
                return "complex_problem"
            if task_metadata.get("is_novel"):
                return "novel_problem"
        
        return "general"
    
    def learn_from_outcome(
        self,
        outcome: dict,
        scenario: str | None = None,
    ) -> None:
        """
        从结果中学习
        
        outcome = {
            "success": bool,
            "quality": float,
            "lessons": [str, ...]
        }
        """
        if not self.reasoning_history:
            return
        
        trace = self.reasoning_history[-1]
        scenario = scenario or trace.scenario
        
        self.learning_strategies.record_outcome(
            strategy_name=trace.strategy_used,
            success=outcome["success"],
            quality=outcome["quality"],
            scenario=scenario,
        )
    
    def get_metacognitive_report(self) -> dict:
        """获取元认知报告"""
        best = self.learning_strategies.strategies.get(
            max(
                self.learning_strategies.strategies.values(),
                key=lambda s: s.success_rate
            ).name
        ) if self.learning_strategies.strategies else None
        
        return {
            "agent_id": self.agent_id,
            "stats": self.stats,
            "current_reasoning": {
                "active": self.current_trace is not None,
                "scenario": self.current_trace.scenario if self.current_trace else None,
                "strategy": self.current_trace.strategy_used if self.current_trace else None,
                "steps": len(self.current_trace.steps) if self.current_trace else 0,
                "quality": self.current_trace.quality_score if self.current_trace else 0.0,
            } if self.current_trace else None,
            "history_count": len(self.reasoning_history),
            "best_strategy": best.name if best else None,
            "best_strategy_global_rate": best.success_rate if best else 0.0,
            "strategy_scenario_rates": {
                name: s.get_scenario_success_rate(self.current_trace.scenario if self.current_trace else "general")
                for name, s in self.learning_strategies.strategies.items()
            },
        }
    
    def get_scenario_summary(self, scenario: str) -> dict:
        """获取某个场景的历史总结"""
        result = {
            "scenario": scenario,
            "total_traces": 0,
            "successful_traces": 0,
            "strategies_used": {},
            "avg_quality": 0.0,
        }
        
        traces = [t for t in self.reasoning_history if t.scenario == scenario]
        if not traces:
            return result
        
        result["total_traces"] = len(traces)
        result["successful_traces"] = sum(1 for t in traces if t.quality_score >= 0.5)
        
        strategy_counts = defaultdict(lambda: {"count": 0, "quality_sum": 0.0})
        for t in traces:
            strategy_counts[t.strategy_used]["count"] += 1
            strategy_counts[t.strategy_used]["quality_sum"] += t.quality_score
        
        result["strategies_used"] = {
            s: {
                "count": d["count"],
                "avg_quality": d["quality_sum"] / d["count"] if d["count"] > 0 else 0.0
            }
            for s, d in strategy_counts.items()
        }
        
        result["avg_quality"] = sum(t.quality_score for t in traces) / len(traces)
        
        return result
    
    def to_dict(self) -> dict:
        return self.get_metacognitive_report()
