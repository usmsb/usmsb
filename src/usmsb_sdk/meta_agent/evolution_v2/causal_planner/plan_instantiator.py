"""
策略实例化

CausalPlanner 的组件

将抽象策略映射到具体行动
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ExecutionPlanStep:
    """执行计划步骤"""
    step_id: int
    strategy: str
    action: str
    params: dict[str, Any]
    expected_effect: float
    confidence: float
    preconditions: list[str]
    postconditions: list[str]


@dataclass
class ExecutionPlan:
    """可执行的计划"""
    plan_id: str
    task_id: str
    steps: list[ExecutionPlanStep]
    total_cost: float
    expected_quality: float
    confidence: float
    coverage_ratio: float
    reasoning: str


class PlanInstantiator:
    """
    计划实例化器

    将抽象的策略选择转换为可执行的动作序列
    """

    def __init__(self, llm_manager=None):
        self.llm = llm_manager

    def instantiate(
        self,
        strategies: list,
        task: Any,
        context: dict[str, Any] | None = None,
    ) -> ExecutionPlan:
        """
        实例化计划

        Args:
            strategies: 选中的策略
            task: 任务
            context: 上下文

        Returns:
            可执行的计划
        """
        steps = []
        step_id = 1
        total_cost = 0.0
        total_expected_quality = 0.0

        for strategy in strategies:
            step = self._strategy_to_step(strategy, step_id, task, context)
            steps.append(step)
            total_cost += step.expected_effect * 100  # 简化的成本计算
            total_expected_quality += step.confidence
            step_id += 1

        expected_quality = (
            total_expected_quality / len(steps) if steps else 0.0
        )

        return ExecutionPlan(
            plan_id=f"plan_{id(task)}",
            task_id=getattr(task, "task_id", str(id(task))),
            steps=steps,
            total_cost=total_cost,
            expected_quality=expected_quality,
            confidence=expected_quality,
            coverage_ratio=1.0,  # 已在选择阶段计算
            reasoning=self._generate_reasoning(steps),
        )

    def _strategy_to_step(
        self,
        strategy: Any,
        step_id: int,
        task: Any,
        context: dict[str, Any] | None,
    ) -> ExecutionPlanStep:
        """
        将策略转换为执行步骤

        Args:
            strategy: 策略
            step_id: 步骤 ID
            task: 任务
            context: 上下文

        Returns:
            执行步骤
        """
        # 提取策略信息
        strategy_name = getattr(strategy, "name", str(strategy))
        strategy_id = getattr(strategy, "strategy_id", strategy_name)

        # 根据策略名称确定动作
        action, params = self._get_action_for_strategy(strategy_name, task, context)

        return ExecutionPlanStep(
            step_id=step_id,
            strategy=strategy_name,
            action=action,
            params=params,
            expected_effect=getattr(strategy, "success_rate", 0.7),
            confidence=getattr(strategy, "success_rate", 0.7),
            preconditions=self._get_preconditions(strategy_name),
            postconditions=self._get_postconditions(strategy_name),
        )

    def _get_action_for_strategy(
        self,
        strategy_name: str,
        task: Any,
        context: dict[str, Any] | None,
    ) -> tuple[str, dict[str, Any]]:
        """
        获取策略对应的动作

        Args:
            strategy_name: 策略名称
            task: 任务
            context: 上下文

        Returns:
            (action, params)
        """
        strategy_lower = strategy_name.lower()

        if "search" in strategy_lower or "查询" in strategy_lower:
            return "search", {"query": getattr(task, "description", "")}

        elif "analyze" in strategy_lower or "分析" in strategy_lower:
            return "analyze", {"input": getattr(task, "description", "")}

        elif "code" in strategy_lower or "代码" in strategy_lower:
            return "write_code", {"spec": getattr(task, "description", "")}

        elif "api" in strategy_lower or "调用" in strategy_lower:
            return "call_api", {"endpoint": getattr(task, "description", "")}

        elif "verify" in strategy_lower or "验证" in strategy_lower:
            return "verify", {"target": getattr(task, "description", "")}

        else:
            return "execute", {"task": getattr(task, "description", "")}

    def _get_preconditions(self, strategy_name: str) -> list[str]:
        """获取前置条件"""
        strategy_lower = strategy_name.lower()

        if "search" in strategy_lower or "查询" in strategy_lower:
            return ["需要有效的查询条件"]

        elif "analyze" in strategy_lower or "分析" in strategy_lower:
            return ["需要有输入数据"]

        elif "code" in strategy_lower or "代码" in strategy_lower:
            return ["需要代码规范文档", "需要测试用例"]

        elif "api" in strategy_lower or "调用" in strategy_lower:
            return ["API 端点可用", "认证信息有效"]

        elif "verify" in strategy_lower or "验证" in strategy_lower:
            return ["有待验证的目标"]

        return []

    def _get_postconditions(self, strategy_name: str) -> list[str]:
        """获取后置条件"""
        strategy_lower = strategy_name.lower()

        if "search" in strategy_lower or "查询" in strategy_lower:
            return ["返回搜索结果"]

        elif "analyze" in strategy_lower or "分析" in strategy_lower:
            return ["返回分析报告"]

        elif "code" in strategy_lower or "代码" in strategy_lower:
            return ["生成可执行代码"]

        elif "api" in strategy_lower or "调用" in strategy_lower:
            return ["返回 API 响应"]

        elif "verify" in strategy_lower or "验证" in strategy_lower:
            return ["返回验证结果"]

        return []


class LLMPlanInstantiator(PlanInstantiator):
    """
    LLM 辅助的计划实例化器

    使用 LLM 生成更精确的动作和参数
    """

    async def instantiate(
        self,
        strategies: list,
        task: Any,
        context: dict[str, Any] | None = None,
    ) -> ExecutionPlan:
        """
        实例化计划（使用 LLM）

        Args:
            strategies: 选中的策略
            task: 任务
            context: 上下文
        """
        if not self.llm:
            return super().instantiate(strategies, task, context)

        steps = []
        step_id = 1
        total_cost = 0.0

        for strategy in strategies:
            # 使用 LLM 生成精确的动作
            action, params = await self._llm_generate_action(
                strategy, task, context
            )

            step = ExecutionPlanStep(
                step_id=step_id,
                strategy=getattr(strategy, "name", str(strategy)),
                action=action,
                params=params,
                expected_effect=getattr(strategy, "success_rate", 0.7),
                confidence=getattr(strategy, "success_rate", 0.7),
                preconditions=self._get_preconditions(getattr(strategy, "name", "")),
                postconditions=self._get_postconditions(getattr(strategy, "name", "")),
            )

            steps.append(step)
            total_cost += step.expected_effect * 100
            step_id += 1

        expected_quality = (
            sum(s.confidence for s in steps) / len(steps) if steps else 0.0
        )

        return ExecutionPlan(
            plan_id=f"plan_{id(task)}",
            task_id=getattr(task, "task_id", str(id(task))),
            steps=steps,
            total_cost=total_cost,
            expected_quality=expected_quality,
            confidence=expected_quality,
            coverage_ratio=1.0,
            reasoning=self._generate_reasoning(steps),
        )

    async def _llm_generate_action(
        self,
        strategy: Any,
        task: Any,
        context: dict[str, Any] | None,
    ) -> tuple[str, dict[str, Any]]:
        """使用 LLM 生成动作"""
        strategy_name = getattr(strategy, "name", str(strategy))
        task_desc = getattr(task, "description", str(task))

        prompt = f"""
        策略：{strategy_name}
        任务：{task_desc}
        上下文：{context}

        请生成具体的动作和参数，格式如下（JSON）：
        {{
            "action": "动作名称",
            "params": {{"参数名": "参数值"}}
        }}
        """

        try:
            response = await self.llm.analyze(prompt)
            import json
            data = json.loads(response)
            return data["action"], data.get("params", {})
        except Exception:
            return super()._get_action_for_strategy(strategy_name, task, context)
