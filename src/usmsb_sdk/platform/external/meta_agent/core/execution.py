"""
执行服务 (Execution)
基于 USMSB Core - IExecutionService
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ExecutionService:
    """
    执行服务

    提供执行能力:
    - 工具调用
    - 动作执行
    - 结果整合
    """

    def __init__(self, tool_registry):
        self.tool_registry = tool_registry

    async def execute(
        self, actions: list[dict[str, Any]], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        执行行动

        Args:
            actions: 行动列表
            context: 上下文

        Returns:
            执行结果
        """
        results = []

        for action in actions:
            tool_name = action.get("tool")
            params = action.get("params", {})

            try:
                result = await self.tool_registry.execute(tool_name, **params)
                results.append({"tool": tool_name, "status": "success", "result": result})
            except Exception as e:
                logger.error(f"Tool {tool_name} execution failed: {e}")
                results.append({"tool": tool_name, "status": "error", "error": str(e)})

        return {
            "status": "success"
            if all(r.get("status") == "success" for r in results)
            else "partial",
            "results": results,
        }

    async def execute_tool(self, tool_name: str, params: dict[str, Any]) -> Any:
        """执行单个工具"""
        return await self.tool_registry.execute(tool_name, **params)
