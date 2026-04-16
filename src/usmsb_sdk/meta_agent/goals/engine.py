"""
Goal Engine - 目标引擎（LLM 驱动版）

策略模式：
- SDK: 使用 L3Adapter（→ PurposeGenerator → L3 SDK）
- Internal: 使用内建启发式逻辑
"""

import logging

logger = logging.getLogger(__name__)


class GoalEngine:
    """
    目标引擎 - LLM 驱动版。

    委托给 L3Adapter，同时保留 internal 策略。
    """

    def __init__(self, llm_client=None, agent_id: str = "meta_agent"):
        self.agent_id = agent_id
        self.llm = llm_client

        # 内部策略：简单列表（原有逻辑）
        self.goals = []
        self.eternal_goals = [
            {"id": "platform_health", "name": "平台健康运营", "status": "in_progress"},
            {"id": "user_satisfaction", "name": "用户满意度", "status": "in_progress"},
            {"id": "system_optimization", "name": "系统优化", "status": "in_progress"},
            {"id": "learning_evolution", "name": "自主学习进化", "status": "in_progress"},
        ]

        # SDK 策略：L3Adapter
        self._l3_adapter = None

    def _get_l3_adapter(self):
        """延迟初始化 L3Adapter（避免循环导入）"""
        if self._l3_adapter is None:
            try:
                from ..adapters.l3_adapter import L3Adapter
                self._l3_adapter = L3Adapter(
                    agent_id=self.agent_id,
                    llm_client=self.llm,
                    internal_goals_engine=self,
                )
            except ImportError:
                logger.warning("[GoalEngine] L3Adapter not available")
                return None
        return self._l3_adapter

    async def start(self):
        """启动目标引擎"""
        self._get_l3_adapter()
        logger.info("Goal Engine (LLM-driven) started")

    async def stop(self):
        """停止目标引擎"""
        logger.info("Goal Engine stopped")

    async def check_goals(self):
        """
        检查目标状态。

        SDK 策略：使用 L3 检测内在动机，强度高时生成新目标。
        """
        adapter = self._get_l3_adapter()
        if not adapter:
            return

        try:
            # 使用 SDK 检测内在动机
            state = self._get_current_state()
            signal = await adapter.detect_intrinsic_motivation(state)

            if signal.intensity > 0.65:
                # 动机强烈，生成新目标
                goal = await adapter.generate_goal(state)
                await self.add_goal(goal)
                logger.info(f"[GoalEngine] Generated new goal: {goal.name} (motivation={signal.dominant}, intensity={signal.intensity:.2f})")
        except Exception as e:
            logger.warning(f"[GoalEngine] check_goals failed: {e}")

    def _get_current_state(self) -> dict:
        """获取当前 Agent 状态"""
        return {
            "active_goals": len(self.goals),
            "eternal_goals": len(self.eternal_goals),
            "agent_id": self.agent_id,
        }

    async def add_goal(self, goal):
        """添加目标"""
        if isinstance(goal, dict):
            self.goals.append(goal)
        else:
            # Goal dataclass
            self.goals.append({
                "id": goal.id,
                "name": goal.name,
                "description": getattr(goal, 'description', goal.name),
                "status": getattr(goal, 'status', 'pending'),
                "metadata": getattr(goal, 'metadata', {}),
            })

    async def update_goal(self, goal_id: str, status: str):
        """更新目标状态"""
        for goal in self.goals + self.eternal_goals:
            if goal.get("id") == goal_id:
                goal["status"] = status
