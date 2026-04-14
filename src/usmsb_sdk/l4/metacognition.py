# -*- coding: utf-8 -*-
"""
Metacognition - L4 元认知

元认知 = 思考自己在想什么。

核心能力：
- 推理追踪：记录每一步思考
- 质量评估：评估推理质量
- 策略优化：调整学习策略
- 困惑检测：发现思维卡住
- 自我纠正：发现错误后纠正
"""

import uuid
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
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class ReasoningTrace:
    """推理追踪"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""            # 推理目标
    steps: list[ReasoningStep] = field(default_factory=list)
    quality_score: float = 0.0
    quality_grade: ReasoningQuality = ReasoningQuality.ADEQUATE
    alternatives_considered: list[str] = field(default_factory=list)  # 全局替代方案
    start_time: float = field(default_factory=lambda: datetime.now().timestamp())
    end_time: float | None = None
    conclusion: str = ""
    is_complete: bool = False
    
    def add_step(self, thought: str, evidence: list[str] | None = None) -> ReasoningStep:
        """添加推理步骤"""
        step = ReasoningStep(
            step_number=len(self.steps) + 1,
            thought=thought,
            evidence=evidence or [],
        )
        self.steps.append(step)
        return step
    
    def revise_step(self, step_number: int, new_thought: str, reason: str) -> None:
        """修订之前的步骤"""
        if 0 <= step_number < len(self.steps):
            step = self.steps[step_number]
            step.thought = new_thought
            step.revised = True
            step.revision_reason = reason
    
    def calculate_quality(self) -> float:
        """计算推理质量"""
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
        
        # 质量等级
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


class LearningStrategyRegistry:
    """学习策略注册表"""
    
    def __init__(self):
        self.strategies: dict[str, LearningStrategy] = {}
        self._init_default_strategies()
    
    def _init_default_strategies(self) -> None:
        """初始化默认策略"""
        defaults = [
            LearningStrategy(
                name="divide_and_conquer",
                description="分而治之：将大问题分解为小问题",
                applicable_scenarios=["complex_problem", "multi_step"]
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
        ]
        
        for s in defaults:
            self.strategies[s.name] = s
    
    def get_for_scenario(self, scenario: str) -> LearningStrategy | None:
        """获取适合场景的策略"""
        candidates = [s for s in self.strategies.values() if scenario in s.applicable_scenarios]
        if not candidates:
            return None
        return max(candidates, key=lambda s: s.success_rate)
    
    def record_outcome(self, strategy_name: str, success: bool, quality: float) -> None:
        """记录策略使用结果"""
        if strategy_name not in self.strategies:
            return
        
        s = self.strategies[strategy_name]
        s.usage_count += 1
        
        # 指数加权移动平均
        s.avg_quality = s.avg_quality * 0.8 + quality * 0.2
        if success:
            s.success_rate = s.success_rate * 0.95 + 0.05
        else:
            s.success_rate = s.success_rate * 0.95 - 0.02
        
        s.success_rate = max(0.0, min(1.0, s.success_rate))


class Metacognition:
    """
    元认知引擎
    
    核心能力：
    1. 追踪自己的思考过程
    2. 评估推理质量
    3. 检测困惑
    4. 从学习中学习
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
        }
    
    def start_reasoning(self, goal: str) -> ReasoningTrace:
        """开始新的推理追踪"""
        trace = ReasoningTrace(goal=goal)
        self.current_trace = trace
        self.stats["total_reasonings"] += 1
        return trace
    
    def think(self, thought: str, evidence: list[str] | None = None) -> ReasoningStep:
        """
        添加思考步骤
        
        这是"我在想什么"的记录。
        """
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
        
        # 修正最后一步
        last_step = self.current_trace.steps[-1]
        self.current_trace.revise_step(last_step.step_number - 1, new_thought, reason)
        self.stats["self_corrections"] += 1
        
        print(f"[Metacognition] Self-corrected: {reason}")
    
    def finish_reasoning(self, conclusion: str) -> ReasoningTrace:
        """完成推理"""
        if not self.current_trace:
            return ReasoningTrace()
        
        self.current_trace.conclusion = conclusion
        self.current_trace.is_complete = True
        self.current_trace.end_time = datetime.now().timestamp()
        self.current_trace.calculate_quality()
        
        # 更新统计
        if self.current_trace.quality_grade == ReasoningQuality.EXCELLENT:
            self.stats["excellent_count"] += 1
        elif self.current_trace.quality_grade == ReasoningQuality.FAILED:
            self.stats["failed_count"] += 1
        
        # 存档
        self.reasoning_history.append(self.current_trace)
        
        # 保存策略结果
        if self.current_trace.alternatives_considered:
            strategy = self.learning_strategies.get_for_scenario("general")
            if strategy:
                self.learning_strategies.record_outcome(
                    strategy.name,
                    success=self.current_trace.quality_score > 0.5,
                    quality=self.current_trace.quality_score
                )
        
        result = self.current_trace
        self.current_trace = None
        
        return result
    
    def think_about_thinking(self) -> str:
        """
        元认知：思考自己在想什么
        
        这是"我知道我在想什么"的能力。
        """
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
        """
        检测困惑
        
        发现思维卡住的信号：
        1. 置信度持续下降
        2. 循环推理
        3. 缺乏证据
        """
        if not self.current_trace or len(self.current_trace.steps) < 3:
            return False
        
        recent = self.current_trace.steps[-3:]
        
        # 1. 置信度下降
        confidence_trend = [
            recent[i].confidence - recent[i+1].confidence 
            for i in range(len(recent)-1)
        ]
        if sum(confidence_trend) > 0.2:
            self.stats["confusion_detections"] += 1
            return True
        
        # 2. 循环推理（当前思考和之前相似）
        for i, step in enumerate(recent[:-1]):
            if step.thought[:50] == recent[-1].thought[:50]:
                self.stats["confusion_detections"] += 1
                return True
        
        # 3. 缺乏证据
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
        
        # 检测原因
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
    
    def suggest_strategy(self) -> LearningStrategy | None:
        """建议学习策略"""
        if self.detect_confusion():
            return self.learning_strategies.get_for_scenario("backtracking")
        
        if not self.current_trace or len(self.current_trace.steps) < 2:
            return self.learning_strategies.get_for_scenario("divide_and_conquer")
        
        # 根据历史选择最佳策略
        best = max(
            self.learning_strategies.strategies.values(),
            key=lambda s: s.success_rate * s.usage_count
        )
        return best
    
    def learn_from_outcome(self, outcome: dict) -> None:
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
        
        # 如果失败率高，更新策略
        if outcome["success"]:
            self.learning_strategies.record_outcome(
                "general",
                success=True,
                quality=outcome["quality"]
            )
        else:
            # 从失败中学习
            strategy = self.suggest_strategy()
            if strategy:
                self.learning_strategies.record_outcome(
                    strategy.name,
                    success=False,
                    quality=outcome["quality"]
                )
    
    def get_metacognitive_report(self) -> dict:
        """获取元认知报告"""
        return {
            "agent_id": self.agent_id,
            "stats": self.stats,
            "current_reasoning": {
                "active": self.current_trace is not None,
                "steps": len(self.current_trace.steps) if self.current_trace else 0,
                "quality": self.current_trace.quality_score if self.current_trace else 0.0,
            } if self.current_trace else None,
            "history_count": len(self.reasoning_history),
            "best_strategy": (
                max(self.learning_strategies.strategies.values(), 
                    key=lambda s: s.success_rate).name
                if self.learning_strategies.strategies else None
            ),
        }
    
    def to_dict(self) -> dict:
        return self.get_metacognitive_report()
