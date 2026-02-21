"""
Context Manager - 上下文管理
"""

import logging

logger = logging.getLogger(__name__)


class ContextManager:
    """上下文管理器"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conversations = {}

    async def init(self):
        logger.info("Context Manager initialized")

    async def add_message(self, conversation_id: str, role: str, content: str):
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        self.conversations[conversation_id].append({"role": role, "content": content})

    async def get_context(self, conversation_id: str, limit: int = 10) -> list:
        return self.conversations.get(conversation_id, [])[-limit:]

    async def save(self):
        logger.info("Context saved")
