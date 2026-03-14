import json
import logging

from .types import InfoNeed, RetrievalIntent

logger = logging.getLogger(__name__)


class IntentAnalyzer:
    def __init__(self, llm_manager):
        self.llm = llm_manager

    async def analyze_from_need(self, need: InfoNeed) -> RetrievalIntent:
        return RetrievalIntent(
            info_type=need.info_type.value,
            description=need.description,
            format_hint=need.format_hint,
            validation_hint=need.validation_hint,
            need_tool_validation=need.need_tool_validation,
            tool_name=need.tool_name,
        )

    async def analyze_from_question(self, question: str) -> RetrievalIntent | None:
        prompt = f"""分析用户问题，判断用户想要从历史对话中检索什么信息。

用户问题: {question}

请返回JSON:
{{
    "need_retrieval": true/false,
    "info_type": "credential/account/url/reference/context/param/other/未知",
    "description": "用户想要查找的具体信息",
    "format_hint": "正确的格式应该是什么样的",
    "validation_hint": "如何验证找到的信息是否正确",
    "need_tool_validation": true/false,
    "tool_name": "工具名称（如有）"
}}

注意：
- 如果用户问题表明需要查找之前提供的信息，设置 need_retrieval: true
- info_type 要具体描述
- format_hint 描述正确格式
"""
        try:
            response = await self.llm.chat(prompt)
            data = self._parse_json(response)
            if not data:
                return None

            if not data.get("need_retrieval"):
                return None

            return RetrievalIntent(
                info_type=data.get("info_type", "other"),
                description=data.get("description", ""),
                format_hint=data.get("format_hint", ""),
                validation_hint=data.get("validation_hint", ""),
                need_tool_validation=data.get("need_tool_validation", False),
                tool_name=data.get("tool_name", ""),
            )
        except Exception as e:
            logger.warning(f"Intent analysis failed: {e}")
            return None

    def _parse_json(self, response: str) -> dict | None:
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            return json.loads(response.strip())
        except Exception:
            import re

            match = re.search(r"\{[\s\S]*\}", response)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
        return None
