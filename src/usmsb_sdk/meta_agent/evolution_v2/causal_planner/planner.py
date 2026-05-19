"""
CausalPlanner

因果规划器 - 完整实现

在抽象因果空间中规划任务执行策略
策略可跨任务迁移
"""

import uuid
from dataclasses import dataclass

from ...models.causal_graph import CausalGraph
from ...models.task_record import TaskRecord
from .task_abstraction import TaskAbstractionEngine, TaskFeatureExtractor
from .backward_search import BackwardSearch, CostAwareBackwardSearch
from .strategy_selector import StrategySelector, StrategySelectionResult, StrategyProfile, PlanningConstraints
from .plan_instantiator import PlanInstantiator, ExecutionPlan


@dataclass
class CausalPlannerConfig:
    """因果规划器配置"""
    max_plan_depth: int = 10
    max_strategies_per_step: int = 5
    min_coverage_ratio: float = 0.8
    planning_timeout: int = 30
    use_llm_abstraction: bool = True
    use_cost_aware: bool = True


class CausalPlanner:
    """
    因果规划器

    在抽象因果空间中规划任务执行策略

    流程：
    1. 任务抽象：用 LLM 提取关键实体和因果关系
    2. 目标识别：识别任务目标对应的因果末端
    3. 逆向搜索：从目标出发，逆向搜索需要的因果边
    4. 策略选择：贪心选择能覆盖最多因果边的策略
    5. 策略实例化：将抽象策略映射到具体行动
    """

    def __init__(
        self,
        causal_graph: CausalGraph,
        llm_manager=None,
        config: CausalPlannerConfig | None = None,
    ):
        """
        初始化

        Args:
            causal_graph: 因果图
            llm_manager: LLM 管理器
            config: 配置
        """
        self.graph = causal_graph
        self.llm = llm_manager
        self.config = config or CausalPlannerConfig()

        # 组件
        self.abstraction_engine = TaskAbstractionEngine(llm_manager)
        self.feature_extractor = TaskFeatureExtractor()
        self.backward_search = (
            CostAwareBackwardSearch(causal_graph)
            if self.config.use_cost_aware
            else BackwardSearch(causal_graph)
        )
        self.strategy_selector = StrategySelector()
        self.plan_instantiator = PlanInstantiator(llm_manager)

    async def plan(
        self,
        task: TaskRecord | Any,
        constraints: PlanningConstraints | None = None,
    ) -> ExecutionPlan:
        """
        规划主流程

        Args:
            task: 任务
            constraints: 约束条件

        Returns:
            ExecutionPlan: 可执行的计划
        """
        if constraints is None:
            constraints = PlanningConstraints(
                max_duration=60.0,
                max_cost=100.0,
            )

        # Step 1: 任务抽象
        abstraction = await self._abstract_task(task)

        # Step 2: 目标因果识别
        target_nodes = self._identify_target_nodes(abstraction)

        # Step 3: 因果逆向搜索
        required_edges = self.backward_search.get_required_causes(target_nodes)

        if not required_edges:
            # 没有找到因果边，使用默认策略
            return await self._default_plan(task, constraints)

        # Step 4: 策略选择
        selection = self.strategy_selector.select(
            required_edges, constraints
        )

        # Step 5: 策略实例化
        plan = self.plan_instantiator.instantiate(
            selection.selected_strategies, task
        )

        # 添加覆盖信息
        plan.coverage_ratio = selection.coverage_ratio

        return plan

    async def _abstract_task(self, task: Any) -> TaskAbstraction:
        """任务抽象"""
        if self.config.use_llm_abstraction and self.llm:
            return await self.abstraction_engine.abstract(task)

        # 回退到特征提取
        features = self.feature_extractor.extract(task)
        return TaskAbstraction(
            entities=[str(task)],
            relations=[],
            goal=str(task),
            causal_subgraph=None,
        )

    def _identify_target_nodes(self, abstraction: TaskAbstraction) -> list[str]:
        """
        目标因果识别

        识别任务目标对应的因果末端

        Args:
            abstraction: 任务抽象

        Returns:
            目标节点列表
        """
        # 在因果图中查找匹配的节点
        target_nodes = []

        for node in self.graph.nodes:
            # 检查节点是否与目标相关
            if self._node_matches_goal(node, abstraction.goal):
                target_nodes.append(node)

        # 如果没有匹配，使用所有末端节点
        if not target_nodes:
            target_nodes = self._get_terminal_nodes()

        return target_nodes

    def _node_matches_goal(self, node: str, goal: str) -> bool:
        """检查节点是否匹配目标"""
        node_lower = node.lower()
        goal_lower = goal.lower()

        # 简单的关键词匹配
        goal_keywords = set(goal_lower.split())
        node_words = set(node_lower.replace("_", " ").split())

        return bool(goal_keywords & node_words)

    def _get_terminal_nodes(self) -> list[str]:
        """获取所有末端节点（没有子节点的节点）"""
        terminal = []

        for node in self.graph.nodes:
            children = self.graph.get_children(node)
            if not children:
                terminal.append(node)

        return terminal

    async def _default_plan(
        self,
        task: Any,
        constraints: PlanningConstraints,
    ) -> ExecutionPlan:
        """生成默认计划"""
        # 使用基本的策略
        default_strategy = StrategyProfile(
            strategy_id="default",
            name="default_execution",
            activates_edges=[],
            produces_nodes=[],
            cost=10.0,
            success_rate=0.5,
            applicable_conditions=[],
        )

        plan = self.plan_instantiator.instantiate(
            [default_strategy], task
        )

        return plan

    def register_strategy(self, strategy: StrategyProfile) -> None:
        """注册策略"""
        self.strategy_selector.register_strategy(strategy)

    def set_edge_costs(self, edge_costs: dict[str, float]) -> None:
        """设置边的成本"""
        if isinstance(self.backward_search, CostAwareBackwardSearch):
            self.backward_search.edge_costs = edge_costs


class HierarchicalCausalPlanner(CausalPlanner):
    """
    分层因果规划器

    支持分层规划：
    1. 高层：抽象任务 → 子目标
    2. 低层：子目标 → 具体策略
    """

    def __init__(
        self,
        causal_graph: CausalGraph,
        llm_manager=None,
        config: CausalPlannerConfig | None = None,
    ):
        super().__init__(causal_graph, llm_manager, config)

        # 子规划器
        self.sub_planners: dict[str, CausalPlanner] = {}

    async def plan_hierarchical(
        self,
        task: Any,
        constraints: PlanningConstraints | None = None,
        depth: int = 0,
    ) -> ExecutionPlan:
        """
        分层规划

        Args:
            task: 任务
            constraints: 约束
            depth: 当前层深度

        Returns:
            执行计划
        """
        if depth >= 2:  # 最多两层
            return await self.plan(task, constraints)

        # 检查是否有子规划器
        task_type = getattr(task, "task_type", "general")
        if task_type in self.sub_planners:
            return await self.sub_planners[task_type].plan(task, constraints)

        # 默认规划
        return await self.plan(task, constraints)

    def register_sub_planner(
        self,
        task_type: str,
        planner: CausalPlanner,
    ) -> None:
        """注册子规划器"""
        self.sub_planners[task_type] = planner
