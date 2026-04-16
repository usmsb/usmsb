import logging
from typing import Any
from uuid import uuid4

from .types import InfoNeed, InfoNeedType

logger = logging.getLogger(__name__)


class InfoExtractorTool:
    name = "retrieve_user_info"
    description = "从用户的历史对话记录中提取需要的信息，如 API Key、密码、账号、网址等"

    parameters = {
        "type": "object",
        "properties": {
            "info_type": {
                "type": "string",
                "description": "需要的信息类型：credential（凭证/API Key）、account（账号）、url（网址）、other（其他）",
                "enum": ["credential", "account", "url", "other"],
            },
            "desc": {
                "type": "string",
                "description": "对需要信息的详细描述，如'虾聊社区的API Key'、'GitHub仓库链接'。必须填写这个参数！",
            },
            "format_hint": {
                "type": "string",
                "description": "格式提示，帮助更精确地提取，如'xialiao_开头'、'github.com/用户名/仓库名'",
            },
            "validation_hint": {
                "type": "string",
                "description": "验证提示，如'调用API验证Key是否有效'",
            },
        },
        "required": ["desc"],
    }

    async def execute(self, params: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        logger.info(f"Tool execute called with params: {params}")
        logger.info(f"Tool execute called with context user_id: {context.get('user_id')}")
        logger.info(f"info_extractor in context: {type(context.get('info_extractor'))}")

        info_extractor = context.get("info_extractor")
        user_id = context.get("user_id")

        logger.info(f"info_extractor is None: {info_extractor is None}")

        if not info_extractor or not user_id:
            logger.error(
                f"ERROR: Missing info_extractor or user_id: extractor={bool(info_extractor)}, user_id={user_id}"
            )
            return {"success": False, "message": "Missing info_extractor or user_id in context"}

        info_type = params.get("info_type", "other")
        description = params.get("desc", "")
        if not description:
            description = params.get("description", "")
        if not description:
            description = params.get("properties", "")
        format_hint = params.get("format_hint", "")

        if not description:
            description = self._infer_description(info_type, format_hint)
            logger.info(f"[INFO_EXTRACT] Inferred description from info_type: {description}")

        need = InfoNeed(
            need_id=f"tool_{uuid4().hex[:8]}",
            name=description,
            info_type=InfoNeedType(info_type),
            description=description,
            format_hint=format_hint,
            validation_hint=params.get("validation_hint", ""),
            need_tool_validation=False,
            tool_name="",
        )

        try:
            logger.info(
                f"[INFO_EXTRACT] Starting extraction for need: {description}, user_id: {user_id}"
            )
            results = await info_extractor.extract([need], user_id)
            logger.info(f"[INFO_EXTRACT] Extraction results: {results}")

            if results and need.need_id in results:
                value = results[need.need_id]
                logger.info(f"FOUND VALUE: {value}")
                return {
                    "success": True,
                    "found": True,
                    "value": value,
                    "message": f"找到信息: {value[:50]}...",
                }
            else:
                logger.info(f"No results found for need: {description}")
                return {"success": True, "found": False, "message": "未在历史对话中找到需要的信息"}
        except Exception as e:
            logger.error(f"InfoExtractorTool execute failed: {e}")
            return {"success": False, "message": str(e)}

    def _infer_description(self, info_type: str, format_hint: str) -> str:
        """从 info_type 和 format_hint 推断需要查找的信息描述"""
        format_hint_lower = format_hint.lower() if format_hint else ""

        if (
            info_type == "credential"
            or "key" in format_hint_lower
            or "token" in format_hint_lower
            or "api" in format_hint_lower
        ):
            if "xialiao" in format_hint_lower or "虾聊" in format_hint_lower:
                return "虾聊API Key"
            if "github" in format_hint_lower:
                return "GitHub API Key"
            return "API Key 或 Token"

        if info_type == "account" or "账号" in format_hint_lower:
            if "xialiao" in format_hint_lower or "虾聊" in format_hint_lower:
                return "虾聊账号"
            return "用户账号"

        if info_type == "url" or "链接" in format_hint_lower or "地址" in format_hint_lower:
            return "网址链接"

        return "用户信息"
