import json
import logging
from typing import Optional

from .types import RetrievalIntent, CandidateMessage, ExtractedInfo

logger = logging.getLogger(__name__)


class LLMExtractor:
    def __init__(self, llm_manager):
        self.llm = llm_manager

    async def extract(
        self, candidate: CandidateMessage, intent: RetrievalIntent
    ) -> Optional[ExtractedInfo]:
        prompt = f"""从给定消息中提取用户需要的信息。

用户想要找: {intent.description}
信息类型: {intent.info_type}
正确格式应该是: {intent.format_hint}

候选消息:
---
角色: {candidate.role}
内容:
{candidate.content}
---

请判断这条消息是否包含用户需要的信息。

返回JSON:
{{
    "contains_target_info": true/false,
    "extracted_value": "提取到的具体信息",
    "confidence": 0.0-1.0,
    "reasoning": "判断理由"
}}

注意：
- 严格按 format_hint 判断格式是否正确
- 如果格式完全符合，设置高置信度
- 如果格式不完全符合但可能是有效信息，设置中置信度
- 如果完全不包含目标信息，设置 contains_target_info: false
"""
        try:
            logger.info(f"[LLM_EXTRACT] Calling LLM for candidate {candidate.message_id}")
            response = await self.llm.chat(prompt)
            logger.info(
                f"[LLM_EXTRACT] LLM response for {candidate.message_id}: {response[:200]}..."
            )
            data = self._parse_json(response)

            if not data:
                return None

            if data.get("contains_target_info") and data.get("extracted_value"):
                return ExtractedInfo(
                    value=data["extracted_value"],
                    confidence=data.get("confidence", 0.5),
                    source_message_id=candidate.message_id,
                    reasoning=data.get("reasoning", ""),
                )

            return None

        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")
            return None

    def _parse_json(self, response: str) -> Optional[dict]:
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
