"""
Hybrid Matching Service - 混合智能匹配服务

结合向量召回和LLM重排序的智能匹配：
1. 向量召回（Recall）：使用向量嵌入快速召回候选
2. LLM重排序（Rerank）：使用LLM智能排序和生成解释

流程：
- 用户查询 → 向量化 → 向量召回Top-K候选 → LLM重排序 → 返回结果
"""

import hashlib
import json
import logging
import math
from dataclasses import dataclass, field
from typing import Any

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv(verbose=False)
except ImportError:
    pass  # dotenv not installed, use system env vars

logger = logging.getLogger(__name__)


@dataclass
class MatchCandidate:
    """匹配候选"""
    id: str
    name: str
    agent_id: str
    capabilities: list[str]
    description: str
    price: float = 0.0
    reputation: float = 0.5
    availability: str = "available"
    vector_score: float = 0.0
    llm_score: float = 0.0
    final_score: float = 0.0
    match_reasons: list[str] = field(default_factory=list)
    embedding: list[float] | None = None


@dataclass
class MatchResult:
    """匹配结果"""
    candidate: MatchCandidate
    score: float
    explanation: str
    match_reasons: list[str]


class HybridEmbeddingService:
    """
    混合嵌入服务

    支持多种嵌入方式：
    1. MiniMax Embedding API（推荐）
    2. 本地 hash 向量（降级方案）
    """

    def __init__(self, llm_adapter=None, vector_dim: int = 384):
        self.llm_adapter = llm_adapter
        self.vector_dim = vector_dim
        self._use_api = llm_adapter is not None and hasattr(llm_adapter, "embed")

    async def embed(self, text: str) -> list[float]:
        """生成文本向量"""
        if self._use_api:
            try:
                return await self.llm_adapter.embed(text)
            except Exception as e:
                logger.warning(f"API embedding failed, fallback to local: {e}")

        return self._embed_local(text)

    def _embed_local(self, text: str) -> list[float]:
        """
        本地生成简单向量（降级方案）
        基于 hash 和文本特征
        """
        vector = [0.0] * self.vector_dim

        text_lower = text.lower()
        text_hash = hashlib.md5(text.encode()).hexdigest()

        for i, char in enumerate(text_hash[: self.vector_dim // 4]):
            idx = int(char, 16) * 4
            if idx < self.vector_dim:
                vector[idx] = (ord(text_lower[i % len(text_lower)]) % 100) / 100.0

        for i, word in enumerate(text_lower.split()[:50]):
            word_hash = sum(ord(c) for c in word)
            idx = word_hash % self.vector_dim
            vector[idx] = min(1.0, vector[idx] + 0.1)

        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量生成向量"""
        if self._use_api and hasattr(self.llm_adapter, 'embed_batch'):
            try:
                return await self.llm_adapter.embed_batch(texts)
            except Exception as e:
                logger.warning(f"Batch API embedding failed, fallback to individual: {e}")

        return [await self.embed(text) for text in texts]


class HybridMatchingService:
    """
    混合匹配服务

    结合向量召回和LLM重排序：
    1. 向量召回（Recall）：快速召回Top-K候选
    2. LLM重排序（Rerank）：智能排序和生成解释
    """

    def __init__(
        self,
        llm_adapter=None,
        vector_dim: int = 384,
        recall_top_k: int = 20,
        final_top_k: int = 10,
    ):
        self.llm_adapter = llm_adapter
        self.embedding_service = HybridEmbeddingService(llm_adapter, vector_dim)
        self.recall_top_k = recall_top_k
        self.final_top_k = final_top_k

        # 缓存
        self._embedding_cache: dict[str, list[float]] = {}

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """计算余弦相似度"""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def _get_embedding(self, text: str) -> list[float]:
        """获取嵌入向量（带缓存）"""
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        embedding = await self.embedding_service.embed(text)
        self._embedding_cache[cache_key] = embedding
        return embedding

    async def match_supply_to_demands(
        self,
        supply: dict[str, Any],
        demands: list[dict[str, Any]],
        min_score: float = 0.3,
        max_results: int = 10,
    ) -> list[MatchResult]:
        """
        匹配供给到需求

        Args:
            supply: 供给方信息（能力、技能等）
            demands: 需求列表
            min_score: 最低匹配分数
            max_results: 最大返回数量

        Returns:
            匹配结果列表
        """
        if not demands:
            return []

        # Step 1: 生成供给方向量
        supply_text = self._build_supply_text(supply)
        supply_embedding = await self._get_embedding(supply_text)

        # Step 2: 向量召回
        candidates = []
        for demand in demands:
            demand_text = self._build_demand_text(demand)
            demand_embedding = await self._get_embedding(demand_text)

            vector_score = self._cosine_similarity(supply_embedding, demand_embedding)

            if vector_score >= min_score:
                candidate = MatchCandidate(
                    id=demand.get('id', ''),
                    name=demand.get('title', 'Untitled'),
                    agent_id=demand.get('agent_id', ''),
                    capabilities=demand.get('required_skills', []),
                    description=demand.get('description', ''),
                    vector_score=vector_score,
                )
                candidate.embedding = demand_embedding
                candidates.append(candidate)

        # 按向量分数排序，取Top-K
        candidates.sort(key=lambda x: x.vector_score, reverse=True)
        candidates = candidates[:self.recall_top_k]

        if not candidates:
            return []

        # Step 3: LLM重排序
        results = await self._llm_rerank_supply_to_demands(supply, candidates, max_results)

        return results

    async def match_demand_to_supplies(
        self,
        demand: dict[str, Any],
        supplies: list[dict[str, Any]],
        min_score: float = 0.3,
        max_results: int = 10,
    ) -> list[MatchResult]:
        """
        匹配需求到供给

        Args:
            demand: 需求信息
            supplies: 供给列表
            min_score: 最低匹配分数
            max_results: 最大返回数量

        Returns:
            匹配结果列表
        """
        if not supplies:
            return []

        # Step 1: 生成需求向量
        demand_text = self._build_demand_text(demand)
        demand_embedding = await self._get_embedding(demand_text)

        # Step 2: 向量召回
        candidates = []
        for supply in supplies:
            supply_text = self._build_supply_text(supply)
            supply_embedding = await self._get_embedding(supply_text)

            vector_score = self._cosine_similarity(demand_embedding, supply_embedding)

            if vector_score >= min_score:
                candidate = MatchCandidate(
                    id=supply.get('id', ''),
                    name=supply.get('name', 'Unknown'),
                    agent_id=supply.get('agent_id', ''),
                    capabilities=supply.get('capabilities', []),
                    description=supply.get('description', ''),
                    price=supply.get('price', 0),
                    reputation=supply.get('reputation', 0.5),
                    availability=supply.get('availability', 'available'),
                    vector_score=vector_score,
                )
                candidate.embedding = supply_embedding
                candidates.append(candidate)

        # 按向量分数排序，取Top-K
        candidates.sort(key=lambda x: x.vector_score, reverse=True)
        candidates = candidates[:self.recall_top_k]

        if not candidates:
            return []

        # Step 3: LLM重排序
        results = await self._llm_rerank_demand_to_supplies(demand, candidates, max_results)

        return results

    def _build_supply_text(self, supply: dict[str, Any]) -> str:
        """构建供给方文本"""
        parts = []

        capabilities = supply.get('capabilities', [])
        if capabilities:
            parts.append(f"技能: {', '.join(capabilities)}")

        description = supply.get('description', '')
        if description:
            parts.append(f"描述: {description}")

        if not parts:
            parts.append("通用服务提供者")

        return " | ".join(parts)

    def _build_demand_text(self, demand: dict[str, Any]) -> str:
        """构建需求文本"""
        parts = []

        title = demand.get('title', '')
        if title:
            parts.append(f"标题: {title}")

        required_skills = demand.get('required_skills', [])
        if required_skills:
            parts.append(f"所需技能: {', '.join(required_skills)}")

        description = demand.get('description', '')
        if description:
            parts.append(f"描述: {description}")

        if not parts:
            parts.append("通用需求")

        return " | ".join(parts)

    async def _llm_rerank_supply_to_demands(
        self,
        supply: dict[str, Any],
        candidates: list[MatchCandidate],
        max_results: int,
    ) -> list[MatchResult]:
        """LLM重排序：供给方匹配需求"""

        if not self.llm_adapter:
            # 无LLM，直接使用向量分数
            results = []
            for c in candidates[:max_results]:
                results.append(MatchResult(
                    candidate=c,
                    score=c.vector_score,
                    explanation=f"向量相似度匹配 (分数: {c.vector_score:.2f})",
                    match_reasons=["语义相似"],
                ))
            return results

        # 构建LLM提示
        supply_caps = supply.get('capabilities', [])
        candidates_text = "\n".join([
            f"{i+1}. [{c.id}] {c.name}\n   技能: {', '.join(c.capabilities)}\n   描述: {c.description[:100]}...\n   向量分数: {c.vector_score:.2f}"
            for i, c in enumerate(candidates[:15])
        ])

        prompt = f"""作为一个智能匹配助手，请评估以下需求与供给方的匹配程度。

供给方能力:
- 技能: {', '.join(supply_caps)}
- 描述: {supply.get('description', '无')}

候选需求列表:
{candidates_text}

请为每个需求评估匹配程度，返回JSON格式:
{{
    "rankings": [
        {{
            "id": "需求ID",
            "score": 0.85,
            "reasons": ["匹配原因1", "匹配原因2"],
            "explanation": "简短解释为什么匹配"
        }}
    ]
}}

评分标准:
1. 技能匹配度 (40%): 供给方技能是否覆盖需求所需技能
2. 语义相关性 (30%): 描述是否相关
3. 综合适配性 (30%): 整体匹配程度

只返回JSON，不要其他内容。"""

        try:
            response = await self.llm_adapter.generate_text(prompt)

            # 解析JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            data = json.loads(response.strip())
            rankings = data.get("rankings", [])

            # 构建结果
            id_to_candidate = {c.id: c for c in candidates}
            results = []

            for r in rankings:
                cid = r.get("id", "")
                if cid in id_to_candidate:
                    candidate = id_to_candidate[cid]
                    llm_score = r.get("score", 0.5)

                    # 混合分数：70% LLM + 30% 向量
                    final_score = llm_score * 0.7 + candidate.vector_score * 0.3

                    results.append(MatchResult(
                        candidate=candidate,
                        score=final_score,
                        explanation=r.get("explanation", ""),
                        match_reasons=r.get("reasons", []),
                    ))

            # 按最终分数排序
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:max_results]

        except Exception as e:
            logger.warning(f"LLM reranking failed: {e}, using vector scores")
            # 降级：使用向量分数
            results = []
            for c in candidates[:max_results]:
                results.append(MatchResult(
                    candidate=c,
                    score=c.vector_score,
                    explanation=f"语义相似匹配 (分数: {c.vector_score:.2f})",
                    match_reasons=["语义相似"],
                ))
            return results

    async def _llm_rerank_demand_to_supplies(
        self,
        demand: dict[str, Any],
        candidates: list[MatchCandidate],
        max_results: int,
    ) -> list[MatchResult]:
        """LLM重排序：需求方匹配供给"""

        if not self.llm_adapter:
            # 无LLM，直接使用向量分数
            results = []
            for c in candidates[:max_results]:
                results.append(MatchResult(
                    candidate=c,
                    score=c.vector_score,
                    explanation=f"向量相似度匹配 (分数: {c.vector_score:.2f})",
                    match_reasons=["语义相似"],
                ))
            return results

        # 构建LLM提示
        demand_skills = demand.get('required_skills', [])
        candidates_text = "\n".join([
            f"{i+1}. [{c.id}] {c.name}\n   技能: {', '.join(c.capabilities)}\n   价格: {c.price}\n   声誉: {c.reputation}\n   向量分数: {c.vector_score:.2f}"
            for i, c in enumerate(candidates[:15])
        ])

        prompt = f"""作为一个智能匹配助手，请评估以下供给方与需求的匹配程度。

需求信息:
- 所需技能: {', '.join(demand_skills)}
- 描述: {demand.get('description', '无')}

候选供给方列表:
{candidates_text}

请为每个供给方评估匹配程度，返回JSON格式:
{{
    "rankings": [
        {{
            "id": "供给方ID",
            "score": 0.85,
            "reasons": ["匹配原因1", "匹配原因2"],
            "explanation": "简短解释为什么推荐这个供给方"
        }}
    ]
}}

评分标准:
1. 技能匹配度 (40%): 供给方技能是否覆盖所需技能
2. 价格合理性 (20%): 价格是否在预算范围内
3. 声誉评分 (20%): 历史声誉如何
4. 综合适配性 (20%): 整体匹配程度

只返回JSON，不要其他内容。"""

        try:
            response = await self.llm_adapter.generate_text(prompt)

            # 解析JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            data = json.loads(response.strip())
            rankings = data.get("rankings", [])

            # 构建结果
            id_to_candidate = {c.id: c for c in candidates}
            results = []

            for r in rankings:
                cid = r.get("id", "")
                if cid in id_to_candidate:
                    candidate = id_to_candidate[cid]
                    llm_score = r.get("score", 0.5)

                    # 混合分数：70% LLM + 30% 向量
                    final_score = llm_score * 0.7 + candidate.vector_score * 0.3

                    results.append(MatchResult(
                        candidate=candidate,
                        score=final_score,
                        explanation=r.get("explanation", ""),
                        match_reasons=r.get("reasons", []),
                    ))

            # 按最终分数排序
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:max_results]

        except Exception as e:
            logger.warning(f"LLM reranking failed: {e}, using vector scores")
            # 降级：使用向量分数
            results = []
            for c in candidates[:max_results]:
                results.append(MatchResult(
                    candidate=c,
                    score=c.vector_score,
                    explanation=f"语义相似匹配 (分数: {c.vector_score:.2f})",
                    match_reasons=["语义相似"],
                ))
            return results


# 全局实例
_hybrid_matching_service: HybridMatchingService | None = None


def get_hybrid_matching_service() -> HybridMatchingService:
    """获取混合匹配服务实例"""
    global _hybrid_matching_service
    if _hybrid_matching_service is None:
        # 延迟初始化，尝试获取LLM适配器
        llm_adapter = None
        try:
            import os

            from usmsb_sdk.intelligence_adapters.base import (
                IntelligenceSourceConfig,
                IntelligenceSourceType,
            )
            from usmsb_sdk.intelligence_adapters.llm.minimax_adapter import MiniMaxAdapter

            api_key = os.getenv("MINIMAX_API_KEY")
            if api_key:
                config = IntelligenceSourceConfig(
                    name="minimax",
                    type=IntelligenceSourceType.LLM,
                    api_key=api_key,
                    model=os.getenv("MINIMAX_MODEL", "abab6.5s-chat"),
                    extra_params={
                        "base_url": os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/v1"),
                    },
                )
                llm_adapter = MiniMaxAdapter(config)
                # 初始化是异步的，我们在这里创建但不等待
                # 实际使用时会自动初始化
        except Exception as e:
            logger.warning(f"Failed to initialize LLM adapter for hybrid matching: {e}")

        _hybrid_matching_service = HybridMatchingService(llm_adapter=llm_adapter)

    return _hybrid_matching_service


async def init_hybrid_matching_service():
    """初始化混合匹配服务（异步）"""
    global _hybrid_matching_service

    llm_adapter = None
    try:
        import os

        from usmsb_sdk.intelligence_adapters.base import (
            IntelligenceSourceConfig,
            IntelligenceSourceType,
        )
        from usmsb_sdk.intelligence_adapters.llm.minimax_adapter import MiniMaxAdapter

        api_key = os.getenv("MINIMAX_API_KEY")
        if api_key:
            # Mask API key for logging (show first 10 and last 4 chars)
            masked_key = f"{api_key[:10]}...{api_key[-4:]}" if len(api_key) > 14 else "***"
            logger.info(f"MINIMAX_API_KEY found: {masked_key}")

            config = IntelligenceSourceConfig(
                name="minimax",
                type=IntelligenceSourceType.LLM,
                api_key=api_key,
                model=os.getenv("MINIMAX_MODEL", "abab6.5s-chat"),
                extra_params={
                    "base_url": os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/v1"),
                },
            )
            llm_adapter = MiniMaxAdapter(config)
            await llm_adapter.initialize()
            logger.info("Hybrid matching service initialized with MiniMax LLM adapter")
        else:
            logger.warning("MINIMAX_API_KEY not found in environment, using local vector embeddings only")
    except Exception as e:
        logger.warning(f"Failed to initialize LLM adapter: {e}, using vector-only mode")

    _hybrid_matching_service = HybridMatchingService(llm_adapter=llm_adapter)
    return _hybrid_matching_service
