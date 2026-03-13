"""
决策服务 (Decision)
基于 USMSB Core - IDecisionService
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DecisionService:
    """
    决策服务

    提供决策能力:
    - 意图理解后的行动规划
    - 策略选择
    - 任务分解
    """

    def __init__(self, llm_manager):
        self.llm = llm_manager

    async def decide(
        self, agent_id: str, goal: Any, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        为 Agent 做出决策

        Args:
            agent_id: Agent ID
            goal: 决策目标
            context: 上下文

        Returns:
            决策结果，包含行动方案
        """
        if isinstance(goal, dict):
            return await self._decide_from_dict(goal, context)
        return await self._decide_from_text(str(goal), context)

    async def _decide_from_dict(self, goal: Dict, context: Optional[Dict]) -> Dict[str, Any]:
        """从字典目标决策"""
        intent = goal.get("intent", "unknown")
        original = goal.get("original", "")

        # 根据意图选择行动
        if intent in ["command", "命令", "执行"]:
            return await self._plan_command(goal, context)
        elif intent in ["query", "查询", "搜索"]:
            return await self._plan_query(goal, context)
        elif intent in ["question", "问题", "问答", "自我介绍", "了解AI助手信息"]:
            return await self._plan_answer(goal, context)
        else:
            return await self._plan_general(goal, context)

    async def _decide_from_text(self, goal_text: str, context: Optional[Dict]) -> Dict[str, Any]:
        """从文本目标决策"""
        prompt = f"""分析用户请求，制定执行计划。

用户请求: {goal_text}

请制定执行计划，包括:
1. 需要调用的工具
2. 工具调用顺序
3. 参数

以 JSON 格式返回:"""

        llm_result = await self.llm.chat(prompt)

        return {
            "actions": [{"tool": "general_response", "params": {"message": llm_result}}],
            "plan": llm_result,
        }

    async def _plan_command(self, goal: Dict, context: Optional[Dict]) -> Dict[str, Any]:
        """规划命令执行"""
        return {"actions": [{"tool": "execute_command", "params": goal}], "plan": "execute"}

    async def _plan_query(self, goal: Dict, context: Optional[Dict]) -> Dict[str, Any]:
        """规划查询"""
        return {"actions": [{"tool": "query_data", "params": goal}], "plan": "query"}

    async def _plan_answer(self, goal: Dict, context: Optional[Dict]) -> Dict[str, Any]:
        """规划问答"""
        original = goal.get("original", "你好")

        # 使用 LLM 生成回答
        response = await self.llm.chat(
            message=original, system_prompt="你是一个友好的AI助手。请用中文回答用户的问题。"
        )

        return {
            "actions": [{"tool": "general_response", "params": {"message": response}}],
            "plan": "answer",
        }

    async def _plan_general(self, goal: Dict, context: Optional[Dict]) -> Dict[str, Any]:
        """通用规划"""
        original = goal.get("original", "")

        # 使用 LLM 生成回答
        response = await self.llm.chat(
            message=original, system_prompt="你是一个友好的AI助手。请用中文简洁地回答用户的问题。"
        )

        return {
            "actions": [{"tool": "general_response", "params": {"message": response}}],
            "plan": "general",
        }

    async def plan_actions(
        self,
        goal: Any,
        constraints: Optional[Dict[str, Any]] = None,
        available_actions: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """规划行动序列"""
        return {"actions": [], "plan": []}

    async def select_strategy(
        self,
        situation: Dict[str, Any],
        strategies: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """选择最优策略"""
        if not strategies:
            return {"selected": None, "reason": "no strategies"}
        return {"selected": strategies[0], "reason": "first strategy"}
