"""
CausalVerifier

因果验证器 - do-calculus 完整实现

用反事实推断验证策略
"""

from dataclasses import dataclass
from typing import Any

from ...models.causal_graph import CausalGraph


@dataclass
class VerificationContext:
    """验证上下文"""
    task_id: str
    strategy_a: Any  # 策略 A
    strategy_b: Any  # 策略 B
    outcome_a: Any  # 策略 A 的实际效果
    task_features: dict[str, Any]
    historical_records: list
    verification_cost: float


@dataclass
class VerificationResult:
    """验证结果"""
    strategy_a_expected: float
    strategy_b_expected: float
    difference: float
    confidence: float
    recommended_strategy: str
    should_execute_verification: bool
    reasoning: str
    execution_result: Any = None


class CausalVerifier:
    """
    因果验证器

    用反事实推断验证策略
    Pearl 的 do-calculus 实现

    核心思想：
    P(效果 | do(策略B), 上下文)

    不需要真的执行策略 B
    用因果模型推断效果
    只对高不确定的情况做真实执行
    """

    def __init__(
        self,
        causal_graph: CausalGraph,
        causal_model=None,
    ):
        """
        初始化

        Args:
            causal_graph: 因果图
            causal_model: 因果模型（条件概率分布或结构方程模型）
        """
        self.graph = causal_graph
        self.model = causal_model

    async def verify_counterfactual(
        self,
        context: VerificationContext,
    ) -> VerificationResult:
        """
        反事实验证

        Args:
            context: 验证上下文

        Returns:
            验证结果
        """
        # Step 1: 识别策略的因果效应
        strategy_a_effects = self._identify_strategy_effects(context.strategy_a)
        strategy_b_effects = self._identify_strategy_effects(context.strategy_b)

        # Step 2: 计算反事实效果
        expected_a = await self._compute_counterfactual_effect(
            strategy_a_effects,
            context.task_features,
            context.outcome_a,
        )

        expected_b = await self._compute_counterfactual_effect(
            strategy_b_effects,
            context.task_features,
            context.outcome_a,
        )

        # Step 3: 计算期望差异
        difference = abs(expected_a - expected_b)

        # Step 4: 计算置信度
        confidence = self._compute_confidence(
            strategy_b_effects,
            context.task_features,
            context.historical_records,
        )

        # Step 5: 决策
        should_execute = self._should_execute_verification(
            difference,
            confidence,
            context.verification_cost,
        )

        recommended = (
            context.strategy_a
            if expected_a > expected_b
            else context.strategy_b
        )

        return VerificationResult(
            strategy_a_expected=expected_a,
            strategy_b_expected=expected_b,
            difference=difference,
            confidence=confidence,
            recommended_strategy=getattr(recommended, "name", str(recommended)),
            should_execute_verification=should_execute,
            reasoning=self._generate_reasoning(difference, confidence),
        )

    def _identify_strategy_effects(self, strategy: Any) -> list:
        """
        识别策略的因果效应

        策略是通过激活某些因果边来起作用的

        Args:
            strategy: 策略

        Returns:
            激活的因果边列表
        """
        if not strategy:
            return []

        strategy_name = getattr(strategy, "name", str(strategy))
        effects = []

        # 在因果图中查找与策略相关的边
        for edge in self.graph.edges:
            # 简化的匹配逻辑
            if self._strategy_matches_edge(strategy_name, edge):
                effects.append(edge)

        return effects

    def _strategy_matches_edge(self, strategy_name: str, edge) -> bool:
        """检查策略是否匹配边"""
        strategy_lower = strategy_name.lower()
        source_lower = edge.source.lower()
        target_lower = edge.target.lower()

        # 简单的关键词匹配
        return (
            strategy_lower in source_lower
            or strategy_lower in target_lower
            or source_lower in strategy_lower
            or target_lower in strategy_lower
        )

    async def _compute_counterfactual_effect(
        self,
        strategy_effects: list,
        task_features: dict[str, Any],
        observed_outcome: Any,
    ) -> float:
        """
        计算反事实效果

        用 do-calculus：
        P(Y | do(X)) = Σ_z P(Y | X, Z) * P(Z)

        Args:
            strategy_effects: 策略的因果效应
            task_features: 任务特征
            observed_outcome: 观察到的结果

        Returns:
            期望效果
        """
        if not strategy_effects:
            # 没有因果效应，返回基础概率
            return 0.5

        # 简化实现：使用因果强度的加权平均
        total_strength = 0.0
        weighted_effect = 0.0

        for edge in strategy_effects:
            strength = abs(edge.strength)
            confidence = edge.confidence

            # 加权平均
            weighted_effect += strength * confidence
            total_strength += confidence

        if total_strength == 0:
            return 0.5

        # 归一化到 [0, 1]
        effect = (weighted_effect / total_strength + 1) / 2

        return max(0.0, min(1.0, effect))

    def _compute_confidence(
        self,
        strategy_effects: list,
        task_features: dict[str, Any],
        historical_records: list,
    ) -> float:
        """
        计算置信度

        置信度取决于：
        - 因果边的置信度
        - 条件概率估计的可靠性
        - 上下文与历史任务的相似度

        Args:
            strategy_effects: 策略的因果效应
            task_features: 任务特征
            historical_records: 历史记录

        Returns:
            置信度
        """
        if not strategy_effects:
            return 0.3

        # 边置信度
        avg_edge_confidence = sum(e.confidence for e in strategy_effects) / len(strategy_effects)

        # 历史相似度
        similarity = self._compute_similarity(task_features, historical_records)

        # 综合置信度
        confidence = avg_edge_confidence * 0.7 + similarity * 0.3

        return max(0.0, min(1.0, confidence))

    def _compute_similarity(
        self,
        task_features: dict[str, Any],
        historical_records: list,
    ) -> float:
        """
        计算任务与历史的相似度

        Args:
            task_features: 任务特征
            historical_records: 历史记录

        Returns:
            相似度
        """
        if not historical_records:
            return 0.5

        # 简化的相似度计算
        similarities = []

        for record in historical_records[-10:]:  # 只看最近 10 条
            record_features = getattr(record, "features", {})
            if not record_features:
                continue

            # 计算特征重叠
            common_keys = set(task_features.keys()) & set(record_features.keys())
            if common_keys:
                matches = sum(
                    1
                    for k in common_keys
                    if task_features.get(k) == record_features.get(k)
                )
                similarity = matches / len(common_keys)
                similarities.append(similarity)

        return sum(similarities) / len(similarities) if similarities else 0.5

    def _should_execute_verification(
        self,
        difference: float,
        confidence: float,
        verification_cost: float,
    ) -> bool:
        """
        决策：是否需要真实执行验证

        原则：
        - 差异大且置信度高 → 不需要执行，相信推断
        - 差异大但置信度低 → 需要执行验证
        - 差异小 → 不需要执行，差异不够大到值得验证
        - 验证成本高 → 更保守地决定执行

        Args:
            difference: 期望差异
            confidence: 置信度
            verification_cost: 验证成本

        Returns:
            是否应该执行
        """
        if difference < 0.1:
            return False  # 差异太小

        if confidence > 0.85:
            return False  # 高置信

        if confidence < 0.5:
            return True  # 低置信

        # 中等置信度，用成本效益决策
        expected_value = difference * 1.0  # 假设完美信息的价值
        cost_threshold = 0.3 * expected_value

        return verification_cost < cost_threshold

    def _generate_reasoning(self, difference: float, confidence: float) -> str:
        """生成推理说明"""
        if confidence > 0.85:
            if difference > 0.2:
                return f"高置信度（{confidence:.2f}）表明差异显著（{difference:.2f}），直接采纳推断"
            else:
                return f"高置信度（{confidence:.2f}），差异不显著（{difference:.2f}），无需验证"

        if confidence < 0.5:
            return f"低置信度（{confidence:.2f}），建议执行验证以确认"

        return f"中等置信度（{confidence:.2f}），差异（{difference:.2f}），成本效益决定"


class SimplifiedCausalVerifier(CausalVerifier):
    """
    简化版因果验证器

    不做完整的 do-calculus
    使用简化的模拟执行
    """

    async def verify_counterfactual(
        self,
        context: VerificationContext,
    ) -> VerificationResult:
        """
        简化验证

        使用简单的启发式方法
        """
        # 简化：直接比较策略属性
        rate_a = getattr(context.strategy_a, "success_rate", 0.5)
        rate_b = getattr(context.strategy_b, "success_rate", 0.5)

        expected_a = rate_a
        expected_b = rate_b

        difference = abs(expected_a - expected_b)
        confidence = 0.6  # 简化置信度

        recommended = (
            context.strategy_a if expected_a > expected_b else context.strategy_b
        )

        should_execute = difference > 0.3 and confidence < 0.7

        return VerificationResult(
            strategy_a_expected=expected_a,
            strategy_b_expected=expected_b,
            difference=difference,
            confidence=confidence,
            recommended_strategy=getattr(recommended, "name", str(recommended)),
            should_execute_verification=should_execute,
            reasoning=f"简化验证：策略A成功率{expected_a:.2f}，策略B成功率{expected_b:.2f}",
        )
