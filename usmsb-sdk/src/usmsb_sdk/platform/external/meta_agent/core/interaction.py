"""
交互服务 (Interaction)
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class InteractionService:
    """交互服务 - 与 Agent/真人对话"""

    def __init__(self, llm_manager):
        self.llm = llm_manager

    async def chat_with_agent(
        self, agent_id: str, message: str, context: Optional[Dict] = None
    ) -> str:
        """与 Agent 对话"""
        # 调用平台 API 与 Agent 对话
        return f"与 {agent_id} 对话: {message}"

    async def chat_with_human(
        self, wallet_address: str, message: str, context: Optional[Dict] = None
    ) -> str:
        """与真人对话"""
        return f"与 {wallet_address} 对话: {message}"

    async def broadcast(self, message: str, targets: list, context: Optional[Dict] = None) -> int:
        """广播消息"""
        return len(targets)
