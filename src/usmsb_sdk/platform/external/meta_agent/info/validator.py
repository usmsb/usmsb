import json
import logging

from .types import ExtractedInfo, RetrievalIntent, ValidationResult

logger = logging.getLogger(__name__)


class Validator:
    def __init__(self, tool_registry=None, llm_manager=None):
        self.tool_registry = tool_registry
        self.llm = llm_manager

    async def validate(
        self, extracted_info: ExtractedInfo, intent: RetrievalIntent
    ) -> ValidationResult:
        if intent.need_tool_validation and self.tool_registry:
            return await self._tool_validate(extracted_info, intent)

        return await self._llm_validate(extracted_info, intent)

    async def _tool_validate(
        self, extracted_info: ExtractedInfo, intent: RetrievalIntent
    ) -> ValidationResult:
        if not self.tool_registry or not intent.tool_name:
            return await self._llm_validate(extracted_info, intent)

        try:
            result = await self.tool_registry.execute(
                intent.tool_name, api_key=extracted_info.value
            )

            if result.get("success") or result.get("status") == 200:
                return ValidationResult(
                    is_valid=True, validated_value=extracted_info.value, method="tool_call"
                )
            else:
                return ValidationResult(
                    is_valid=False,
                    method="tool_call",
                    error=f"验证失败: {result.get('error', 'unknown')}",
                )
        except Exception as e:
            return ValidationResult(is_valid=False, method="tool_call", error=str(e))

    async def _llm_validate(
        self, extracted_info: ExtractedInfo, intent: RetrievalIntent
    ) -> ValidationResult:
        prompt = f"""判断找到的信息是否符合用户需求。

用户想要找: {intent.description}
正确格式应该是: {intent.format_hint}
验证方法是: {intent.validation_hint}

找到的信息: {extracted_info.value}
置信度: {extracted_info.confidence}

请判断这个信息是否正确有效。

返回JSON:
{{
    "is_valid": true/false,
    "reasoning": "判断理由"
}}
"""
        try:
            response = await self.llm.chat(prompt)
            data = self._parse_json(response)

            if not data:
                return ValidationResult(
                    is_valid=False, method="llm", error="Failed to parse LLM response"
                )

            return ValidationResult(
                is_valid=data.get("is_valid", False),
                validated_value=extracted_info.value if data.get("is_valid") else None,
                method="llm",
                reasoning=data.get("reasoning", ""),
            )

        except Exception as e:
            return ValidationResult(is_valid=False, method="llm", error=str(e))

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
