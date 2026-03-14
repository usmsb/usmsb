"""
自我优化器 - Self Optimizer

策略调整和参数优化
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from .models import (
    SelfReflection,
)

logger = logging.getLogger(__name__)


@dataclass
class OptimizationParameter:
    """优化参数"""

    name: str
    current_value: float
    min_value: float
    max_value: float
    step_size: float
    history: list[float] = field(default_factory=list)
    performance_history: list[float] = field(default_factory=list)


@dataclass
class OptimizationResult:
    """优化结果"""

    parameter_name: str
    old_value: float
    new_value: float
    improvement: float
    confidence: float


@dataclass
class StrategyAdjustment:
    """策略调整"""

    strategy_name: str
    adjustment_type: str
    old_value: Any
    new_value: Any
    reason: str
    expected_improvement: float


class SelfOptimizer:
    """
    自我优化器

    核心职责：
    1. 参数优化 - 自动调整系统参数
    2. 策略优化 - 优化决策和学习策略
    3. 资源分配 - 优化计算资源分配
    4. 性能调优 - 持续改进系统性能
    5. 自适应调整 - 根据环境变化调整
    """

    def __init__(self, llm_manager=None, capability_assessor=None, meta_learner=None):
        self.llm = llm_manager
        self.capability_assessor = capability_assessor
        self.meta_learner = meta_learner

        self._parameters: dict[str, OptimizationParameter] = {}
        self._optimization_history: list[OptimizationResult] = []
        self._strategy_adjustments: list[StrategyAdjustment] = []

        self._learning_rate: float = 0.1
        self._exploration_rate: float = 0.2
        self._adaptation_speed: float = 0.5

        self._performance_baseline: dict[str, float] = {}
        self._optimization_candidates: list[str] = []

        self._initialized = False

    async def initialize(self):
        """初始化自我优化器"""
        if self._initialized:
            return

        self._initialize_parameters()

        self._initialized = True
        logger.info("SelfOptimizer initialized")

    def _initialize_parameters(self):
        """初始化优化参数"""
        self._parameters = {
            "learning_rate": OptimizationParameter(
                name="learning_rate",
                current_value=0.1,
                min_value=0.01,
                max_value=0.5,
                step_size=0.01,
            ),
            "exploration_rate": OptimizationParameter(
                name="exploration_rate",
                current_value=0.2,
                min_value=0.05,
                max_value=0.5,
                step_size=0.01,
            ),
            "confidence_threshold": OptimizationParameter(
                name="confidence_threshold",
                current_value=0.6,
                min_value=0.3,
                max_value=0.9,
                step_size=0.05,
            ),
            "evolution_interval": OptimizationParameter(
                name="evolution_interval",
                current_value=300,
                min_value=60,
                max_value=600,
                step_size=30,
            ),
            "knowledge_consolidation_threshold": OptimizationParameter(
                name="knowledge_consolidation_threshold",
                current_value=0.7,
                min_value=0.5,
                max_value=0.95,
                step_size=0.05,
            ),
            "curiosity_drive": OptimizationParameter(
                name="curiosity_drive",
                current_value=0.7,
                min_value=0.3,
                max_value=1.0,
                step_size=0.05,
            ),
            "reflection_frequency": OptimizationParameter(
                name="reflection_frequency",
                current_value=0.2,
                min_value=0.1,
                max_value=0.5,
                step_size=0.02,
            ),
            "goal_timeout_multiplier": OptimizationParameter(
                name="goal_timeout_multiplier",
                current_value=1.5,
                min_value=1.0,
                max_value=3.0,
                step_size=0.1,
            ),
        }

    async def optimize(self) -> dict[str, Any]:
        """
        执行优化

        分析当前性能，调整参数和策略
        """
        await self._ensure_initialized()

        results = {
            "parameters_optimized": 0,
            "strategies_adjusted": 0,
            "improvements": [],
        }

        param_results = await self._optimize_parameters()
        results["parameters_optimized"] = len(param_results)
        results["improvements"].extend(param_results)

        strategy_results = await self._optimize_strategies()
        results["strategies_adjusted"] = len(strategy_results)
        results["improvements"].extend(strategy_results)

        resource_results = await self._optimize_resources()
        results["improvements"].extend(resource_results)

        return results

    async def _optimize_parameters(self) -> list[dict[str, Any]]:
        """优化参数"""
        improvements = []

        for param_name, param in self._parameters.items():
            old_value = param.current_value

            new_value, confidence = await self._find_optimal_value(param)

            if confidence > 0.6 and new_value != old_value:
                param.current_value = new_value
                param.history.append(new_value)

                result = OptimizationResult(
                    parameter_name=param_name,
                    old_value=old_value,
                    new_value=new_value,
                    improvement=abs(new_value - old_value) / param.max_value,
                    confidence=confidence,
                )

                self._optimization_history.append(result)

                improvements.append(
                    {
                        "type": "parameter",
                        "name": param_name,
                        "old": old_value,
                        "new": new_value,
                        "confidence": confidence,
                    }
                )

                await self._apply_parameter(param_name, new_value)

        return improvements

    async def _find_optimal_value(
        self,
        param: OptimizationParameter,
    ) -> tuple[float, float]:
        """寻找最优参数值"""
        current = param.current_value

        gradient = self._estimate_gradient(param)

        if len(param.history) >= 3:
            historical_best = self._find_historical_best(param)
            gradient = gradient * 0.7 + (historical_best - current) * 0.3

        if abs(gradient) < 0.001:
            return current, 0.5

        step = gradient * param.step_size * 2

        if self._exploration_rate > random.random():
            step = random.uniform(-param.step_size, param.step_size)

        new_value = current + step

        new_value = max(param.min_value, min(param.max_value, new_value))

        confidence = 1.0 - abs(gradient) / (param.max_value - param.min_value)

        return new_value, confidence

    def _estimate_gradient(self, param: OptimizationParameter) -> float:
        """估计梯度"""
        if len(param.performance_history) < 2:
            return 0.0

        recent_performance = param.performance_history[-3:]
        gradient = sum(
            (recent_performance[i + 1] - recent_performance[i])
            for i in range(len(recent_performance) - 1)
        ) / len(recent_performance)

        if len(param.history) >= 2:
            value_diff = param.history[-1] - param.history[-2]
            if abs(value_diff) > 0.0001:
                gradient = gradient / value_diff

        return gradient

    def _find_historical_best(self, param: OptimizationParameter) -> float:
        """找到历史最佳值"""
        if not param.performance_history or not param.history:
            return param.current_value

        best_idx = param.performance_history.index(max(param.performance_history))
        if best_idx < len(param.history):
            return param.history[best_idx]

        return param.current_value

    async def _apply_parameter(self, name: str, value: float):
        """应用参数值"""
        if name == "learning_rate":
            self._learning_rate = value
        elif name == "exploration_rate":
            self._exploration_rate = value
        elif name == "adaptation_speed":
            self._adaptation_speed = value

    async def _optimize_strategies(self) -> list[dict[str, Any]]:
        """优化策略"""
        improvements = []

        if self.meta_learner:
            strategy_performance = self.meta_learner.get_meta_learning_stats()

            for strategy_name, perf in strategy_performance.get("strategy_performance", {}).items():
                if perf.get("success_rate", 0.5) < 0.4:
                    adjustment = StrategyAdjustment(
                        strategy_name=strategy_name,
                        adjustment_type="deprecate",
                        old_value=perf,
                        new_value={"weight": 0.5},
                        reason="Low success rate",
                        expected_improvement=0.1,
                    )
                    self._strategy_adjustments.append(adjustment)
                    improvements.append(
                        {
                            "type": "strategy",
                            "name": strategy_name,
                            "action": "weight_reduced",
                            "reason": "low_success_rate",
                        }
                    )

        if self.capability_assessor:
            weaknesses = await self.capability_assessor.identify_weaknesses()

            for weakness in weaknesses[:3]:
                adjustment = StrategyAdjustment(
                    strategy_name=f"focus_{weakness.capability_id}",
                    adjustment_type="prioritize",
                    old_value=None,
                    new_value={"priority": weakness.priority},
                    reason=f"Weakness identified: {weakness.capability_name}",
                    expected_improvement=weakness.gap * 0.5,
                )
                self._strategy_adjustments.append(adjustment)
                improvements.append(
                    {
                        "type": "strategy",
                        "name": f"focus_{weakness.capability_id}",
                        "action": "prioritized",
                        "reason": "weakness_identified",
                    }
                )

        return improvements

    async def _optimize_resources(self) -> list[dict[str, Any]]:
        """优化资源分配"""
        improvements = []

        total_importance = 0.0
        resource_needs = {}

        if self.capability_assessor:
            for cap_id, cap in self.capability_assessor.get_all_capabilities().items():
                need = 1.0 - cap.score
                resource_needs[cap_id] = need
                total_importance += need

        if total_importance > 0:
            for cap_id, need in resource_needs.items():
                allocation = need / total_importance
                if allocation > 0.3:
                    improvements.append(
                        {
                            "type": "resource",
                            "capability": cap_id,
                            "allocation": allocation,
                            "note": "High resource allocation recommended",
                        }
                    )

        return improvements

    async def adaptive_adjust(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        自适应调整

        根据当前上下文动态调整参数
        """
        await self._ensure_initialized()

        adjustments = {}

        difficulty = context.get("difficulty", 0.5)
        if difficulty > 0.7:
            adjustments["learning_rate"] = min(
                self._parameters["learning_rate"].max_value,
                self._parameters["learning_rate"].current_value * 1.2,
            )
            adjustments["confidence_threshold"] = max(
                self._parameters["confidence_threshold"].min_value,
                self._parameters["confidence_threshold"].current_value * 0.9,
            )

        time_pressure = context.get("time_pressure", 0.0)
        if time_pressure > 0.7:
            adjustments["exploration_rate"] = max(
                self._parameters["exploration_rate"].min_value,
                self._parameters["exploration_rate"].current_value * 0.7,
            )

        performance = context.get("recent_performance", 0.5)
        if performance < 0.5:
            adjustments["curiosity_drive"] = min(
                self._parameters["curiosity_drive"].max_value,
                self._parameters["curiosity_drive"].current_value * 1.1,
            )

        for param_name, new_value in adjustments.items():
            if param_name in self._parameters:
                param = self._parameters[param_name]
                new_value = max(param.min_value, min(param.max_value, new_value))
                param.current_value = new_value

        return adjustments

    async def update_performance(
        self,
        performance_score: float,
        context: dict[str, Any] | None = None,
    ):
        """
        更新性能记录

        用于参数优化学习
        """
        for param in self._parameters.values():
            param.performance_history.append(performance_score)
            if len(param.performance_history) > 100:
                param.performance_history = param.performance_history[-100:]

    async def generate_optimization_report(self) -> dict[str, Any]:
        """生成优化报告"""
        await self._ensure_initialized()

        report = {
            "current_parameters": {
                name: {
                    "value": p.current_value,
                    "range": [p.min_value, p.max_value],
                    "history_length": len(p.history),
                }
                for name, p in self._parameters.items()
            },
            "optimization_history": [
                {
                    "parameter": r.parameter_name,
                    "change": r.new_value - r.old_value,
                    "improvement": r.improvement,
                    "confidence": r.confidence,
                }
                for r in self._optimization_history[-10:]
            ],
            "strategy_adjustments": [
                {
                    "strategy": a.strategy_name,
                    "type": a.adjustment_type,
                    "reason": a.reason,
                }
                for a in self._strategy_adjustments[-10:]
            ],
            "statistics": {
                "total_optimizations": len(self._optimization_history),
                "total_adjustments": len(self._strategy_adjustments),
                "average_improvement": (
                    sum(r.improvement for r in self._optimization_history)
                    / len(self._optimization_history)
                )
                if self._optimization_history
                else 0.0,
            },
        }

        return report

    async def suggest_improvements(
        self,
        reflection: SelfReflection,
    ) -> list[dict[str, Any]]:
        """
        根据自我反思建议改进

        Args:
            reflection: 自我反思结果

        Returns:
            改进建议列表
        """
        suggestions = []

        for weakness in reflection.weaknesses:
            if "推理" in weakness or "reasoning" in weakness.lower():
                suggestions.append(
                    {
                        "area": "reasoning",
                        "suggestion": "增加推理练习",
                        "parameter_adjustment": {
                            "learning_rate": self._parameters["learning_rate"].current_value * 1.1,
                        },
                    }
                )

            if "学习" in weakness or "learning" in weakness.lower():
                suggestions.append(
                    {
                        "area": "learning",
                        "suggestion": "优化学习策略",
                        "parameter_adjustment": {
                            "curiosity_drive": min(
                                1.0, self._parameters["curiosity_drive"].current_value * 1.2
                            ),
                        },
                    }
                )

        for action in reflection.action_items[:3]:
            suggestions.append(
                {
                    "area": "action",
                    "suggestion": action.get("action", ""),
                    "priority": action.get("priority", "medium"),
                }
            )

        return suggestions

    def get_parameter(self, name: str) -> float | None:
        """获取参数值"""
        if name in self._parameters:
            return self._parameters[name].current_value
        return None

    def set_parameter(self, name: str, value: float) -> bool:
        """设置参数值"""
        if name in self._parameters:
            param = self._parameters[name]
            param.current_value = max(param.min_value, min(param.max_value, value))
            param.history.append(param.current_value)
            return True
        return False

    async def _ensure_initialized(self):
        """确保已初始化"""
        if not self._initialized:
            await self.initialize()


import random
