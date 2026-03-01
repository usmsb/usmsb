import logging
from typing import List, Dict, Optional

from .types import InfoNeed, InfoNeedType
from .intent_analyzer import IntentAnalyzer
from .candidate_search import CandidateSearch
from .llm_extractor import LLMExtractor
from .validator import Validator

logger = logging.getLogger(__name__)


class InfoExtractor:
    def __init__(self, llm_manager, conversation_manager, tool_registry, memory_manager):
        self.llm = llm_manager
        self.conversation_manager = conversation_manager
        self.tool_registry = tool_registry
        self.memory_manager = memory_manager

        self.intent_analyzer = IntentAnalyzer(llm_manager)
        self.candidate_search = CandidateSearch(conversation_manager, llm_manager)
        self.llm_extractor = LLMExtractor(llm_manager)
        self.validator = Validator(tool_registry, llm_manager)

    async def extract(self, info_needs: List[InfoNeed], user_id: str) -> Dict[str, str]:
        logger.info(
            f"[INFO_EXTRACT] extract called, needs count={len(info_needs)}, user_id={user_id}"
        )
        results = {}

        for need in info_needs:
            logger.info(f"[INFO_EXTRACT] processing need: {need.name}, info_type={need.info_type}")
            intent = await self.intent_analyzer.analyze_from_need(need)
            logger.info(
                f"[INFO_EXTRACT] intent: info_type={intent.info_type}, description={intent.description}"
            )

            candidates = await self.candidate_search.search(user_id, intent)
            logger.info(f"[INFO_EXTRACT] candidates found: {len(candidates)}")

            if not candidates:
                logger.warning(f"[INFO_EXTRACT] No candidates found for need: {need.name}")
                continue

            for candidate in candidates:
                logger.info(f"[INFO_EXTRACT] Processing candidate {candidate.message_id}")
                extracted = await self.llm_extractor.extract(candidate, intent)
                logger.info(
                    f"[INFO_EXTRACT] extracted from candidate {candidate.message_id}: {extracted}"
                )

                if extracted is None:
                    continue

                validation = await self.validator.validate(extracted, intent)
                logger.info(f"[INFO_EXTRACT] validation result: is_valid={validation.is_valid}")

                if validation.is_valid:
                    results[need.need_id] = validation.validated_value
                    need.fulfilled = True
                    need.value = validation.validated_value

                    await self._update_memory(user_id, need, validation.validated_value)
                    logger.info(
                        f"[INFO_EXTRACT] Successfully extracted: {validation.validated_value[:50]}..."
                    )

                    logger.info(
                        f"Extracted info for {need.need_id}: {validation.validated_value[:30]}..."
                    )
                    break

        return results

    async def _update_memory(self, user_id: str, need: InfoNeed, value: str):
        if not self.memory_manager:
            return

        try:
            await self.memory_manager.store_important_entity(
                user_id=user_id, content=value, entity_type=need.info_type.value, name=need.name
            )
        except Exception as e:
            logger.warning(f"Failed to update memory: {e}")
