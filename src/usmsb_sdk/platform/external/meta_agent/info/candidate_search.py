import json
import logging

from .types import CandidateMessage, RetrievalIntent

logger = logging.getLogger(__name__)


class CandidateSearch:
    def __init__(self, conversation_manager, llm_manager):
        self.conversation_manager = conversation_manager
        self.llm = llm_manager

    async def search(
        self, user_id: str, intent: RetrievalIntent, limit: int = 100
    ) -> list[CandidateMessage]:
        try:
            keywords = self._extract_keywords(intent)
            logger.info(f"[INFO_EXTRACT] Candidate search keywords: {keywords}")

            all_results = []
            seen_ids = set()

            for keyword in keywords:
                if not keyword or len(keyword) < 2:
                    continue

                logger.info(f"[INFO_EXTRACT] Searching for keyword: {keyword}")
                results = await self.conversation_manager.search_all_conversations(
                    owner_id=user_id, query=keyword, limit=limit
                )
                logger.info(
                    f"[INFO_EXTRACT] Search for '{keyword}' returned {len(results)} results"
                )

                for r in results:
                    if r["id"] not in seen_ids:
                        seen_ids.add(r["id"])
                        all_results.append(r)

            logger.info(f"[INFO_EXTRACT] Total unique results: {len(all_results)}")

            candidates = [
                CandidateMessage(
                    message_id=r["id"],
                    content=r["content"],
                    role=r["role"],
                    timestamp=r["timestamp"],
                    conversation_title=r.get("conversation_title", ""),
                )
                for r in all_results
            ]

            if not candidates:
                return []

            ranked = await self._rank_by_relevance(candidates, intent)
            return ranked

        except Exception as e:
            logger.warning(f"Candidate search failed: {e}")
            return []

    def _extract_keywords(self, intent: RetrievalIntent) -> list[str]:
        keywords = set()

        desc = intent.description.lower()
        format_hint = intent.format_hint.lower() if intent.format_hint else ""
        info_type_val = intent.info_type
        if hasattr(info_type_val, "value"):
            info_type_str = info_type_val.value
        else:
            info_type_str = str(info_type_val)

        import sys

        print(
            f"[INFO_EXTRACT] _extract_keywords: desc={desc}, format_hint={format_hint}, info_type={info_type_str}",
            file=sys.stderr,
        )


        for text in [desc, format_hint]:
            for word in [
                "虾聊",
                "xialiao",
                "api",
                "key",
                "key",
                "token",
                "账号",
                "账户",
                "密码",
                "github",
                "url",
                "链接",
                "地址",
                "邮箱",
                "phone",
                "手机",
            ]:
                if word in text:
                    if word == "key" and "api" in text:
                        keywords.add("api_key")
                    elif word == "key":
                        keywords.add(word)
                    else:
                        keywords.add(word)

            import re

            matches = re.findall(r"xialiao_\w+", text)
            keywords.update(matches)

            if "credential" in info_type_str:
                if "虾聊" in text or "xialiao" in text:
                    keywords.add("虾聊")
                    keywords.add("xialiao")
                keywords.add("api")
                keywords.add("key")
                keywords.add("token")

        if not keywords and intent.description:
            keywords.add(intent.description)

        logger.info(f"[INFO_EXTRACT] Final keywords: {list(keywords)}")

        return list(keywords)

    async def _rank_by_relevance(
        self, candidates: list[CandidateMessage], intent: RetrievalIntent, limit: int = 20
    ) -> list[CandidateMessage]:
        try:
            logger.info(f"[INFO_EXTRACT] Starting ranking with {len(candidates)} candidates")

            candidates_text = "\n".join(
                [
                    f"[{i}] 角色:{c.role} 内容:{c.content[:200]}"
                    for i, c in enumerate(candidates[:30])
                ]
            )
            logger.info(f"[INFO_EXTRACT] Candidates text length: {len(candidates_text)}")

            prompt = f"""给定用户检索意图，对候选消息按与意图的相关度排序。

用户想要找: {intent.description}
信息类型: {intent.info_type}
格式要求: {intent.format_hint}

候选消息:
{candidates_text}

请返回按相关度排序的候选索引（最相关的在前，最多{limit}个）:
{{
    "ranked_indices": [索引列表],
    "reasoning": "简要说明"
}}

注意：
- 只返回真正可能包含目标信息的候选
- 排除明显不相关的消息
"""
            logger.info("[INFO_EXTRACT] Calling LLM for ranking...")
            response = await self.llm.chat(prompt)
            logger.info(f"[INFO_EXTRACT] Ranking LLM response: {response[:500]}...")
            data = self._parse_json(response)

            if not data:
                return candidates[:limit]

            ranked_indices = data.get("ranked_indices", [])[:limit]
            return [candidates[i] for i in ranked_indices if i < len(candidates)]

        except Exception as e:
            logger.warning(f"Ranking failed: {e}")
            return candidates[:limit]

    def _parse_json(self, response: str) -> dict | None:
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            return json.loads(response.strip())
        except Exception:
            import re

            match = re.search(r"\[[\s\S]*\]|\{[\s\S]*\}", response)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
        return None
