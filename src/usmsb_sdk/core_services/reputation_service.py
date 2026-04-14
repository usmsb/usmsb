"""
ReputationService - 声誉服务

USMSB 核心服务之一。
计算和管理 Agent 声誉。

功能：
- 声誉计算
- 信任评估
- 评价管理
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ReviewRating(Enum):
    """评价等级"""
    EXCELLENT = 5  # 优秀
    GOOD = 4       # 良好
    AVERAGE = 3   # 一般
    POOR = 2      # 较差
    BAD = 1       # 很差


@dataclass
class Review:
    """评价"""
    id: str
    order_id: str
    reviewer_id: str  # 评价方
    reviewee_id: str  # 被评价方
    rating: ReviewRating
    comment: str = ""
    tags: list[str] = field(default_factory=list)  # 标签
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: dict = field(default_factory=dict)


class ReputationService:
    """
    声誉服务
    
    使用方式：
    ```python
    service = ReputationService()
    
    # 提交评价
    review_id = service.submit_review(
        order_id="order_001",
        reviewer_id="agent_001",
        reviewee_id="agent_002",
        rating=ReviewRating.GOOD,
        comment="Great work!"
    )
    
    # 计算声誉
    reputation = service.calculate_reputation("agent_002")
    
    # 获取评价
    reviews = service.get_reviews("agent_002")
    ```
    """
    
    # 声誉计算参数
    BASE_REPUTATION = 0.5  # 基础声誉
    EXCELLENT_BONUS = 0.1  # 优秀加成
    BAD_PENALTY = 0.15      # 很差惩罚
    DECAY_RATE = 0.01       # 衰减率（每天）
    MAX_REPUTATION = 1.0
    MIN_REPUTATION = 0.0
    
    def __init__(self):
        # 评价存储
        self._reviews: dict[str, Review] = {}
        
        # Agent 声誉缓存
        self._reputation_cache: dict[str, tuple[float, float]] = {}  # agent_id -> (reputation, updated_at)
        
        # Agent 评价索引
        self._review_index: dict[str, list[str]] = {}  # agent_id -> [review_id]
    
    def submit_review(
        self,
        order_id: str,
        reviewer_id: str,
        reviewee_id: str,
        rating: ReviewRating,
        comment: str = "",
        tags: list[str] | None = None
    ) -> str:
        """
        提交评价
        
        Args:
            order_id: 订单 ID
            reviewer_id: 评价方
            reviewee_id: 被评价方
            rating: 评价等级
            comment: 评价内容
            tags: 标签
            
        Returns:
            str: 评价 ID
        """
        review = Review(
            id=str(uuid.uuid4()),
            order_id=order_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            rating=rating,
            comment=comment,
            tags=tags or []
        )
        
        self._reviews[review.id] = review
        
        # 更新索引
        if reviewee_id not in self._review_index:
            self._review_index[reviewee_id] = []
        self._review_index[reviewee_id].append(review.id)
        
        # 清除声誉缓存
        if reviewee_id in self._reputation_cache:
            del self._reputation_cache[reviewee_id]
        
        return review.id
    
    def get_review(self, review_id: str) -> Review | None:
        """获取评价"""
        return self._reviews.get(review_id)
    
    def get_reviews(
        self,
        agent_id: str,
        limit: int = 100
    ) -> list[Review]:
        """
        获取 Agent 的所有评价
        
        Args:
            agent_id: Agent ID
            limit: 返回数量
            
        Returns:
            list[Review]: 评价列表
        """
        review_ids = self._review_index.get(agent_id, [])
        reviews = [self._reviews[rid] for rid in review_ids if rid in self._reviews]
        
        # 按时间排序
        reviews.sort(key=lambda r: r.created_at, reverse=True)
        
        return reviews[:limit]
    
    def calculate_reputation(
        self,
        agent_id: str,
        use_cache: bool = True
    ) -> float:
        """
        计算 Agent 声誉
        
        声誉 = 基础声誉 + 加权平均评价 + 奖励/惩罚
        
        Args:
            agent_id: Agent ID
            use_cache: 是否使用缓存
            
        Returns:
            float: 声誉值 (0.0-1.0)
        """
        # 检查缓存
        if use_cache and agent_id in self._reputation_cache:
            reputation, updated_at = self._reputation_cache[agent_id]
            # 缓存有效期：1 小时
            if datetime.now().timestamp() - updated_at < 3600:
                return reputation
        
        # 获取所有评价
        reviews = self.get_reviews(agent_id, limit=1000)
        
        if not reviews:
            return self.BASE_REPUTATION
        
        # 计算加权平均
        total_weight = 0.0
        weighted_sum = 0.0
        
        for review in reviews:
            # 权重：越新的评价权重越高
            age_days = (datetime.now().timestamp() - review.created_at) / 86400
            weight = 1.0 / (1.0 + age_days * 0.1)  # 指数衰减
            
            rating_value = review.rating.value
            
            weighted_sum += rating_value * weight
            total_weight += weight
        
        if total_weight == 0:
            return self.BASE_REPUTATION
        
        # 归一化到 0-1
        normalized_rating = weighted_sum / (total_weight * 5.0)  # 假设 5 分制
        
        # 计算声誉
        reputation = normalized_rating
        
        # 应用奖励/惩罚
        excellent_count = sum(1 for r in reviews if r.rating == ReviewRating.EXCELLENT)
        bad_count = sum(1 for r in reviews if r.rating == ReviewRating.BAD)
        
        if excellent_count > 5:
            reputation = min(self.MAX_REPUTATION, reputation + self.EXCELLENT_BONUS)
        if bad_count > 3:
            reputation = max(self.MIN_REPUTATION, reputation - self.BAD_PENALTY)
        
        # 应用时间衰减
        oldest_review = min(reviews, key=lambda r: r.created_at)
        age_days = (datetime.now().timestamp() - oldest_review.created_at) / 86400
        decay = age_days * self.DECAY_RATE
        reputation = max(self.MIN_REPUTATION, reputation - decay)
        
        # 限制范围
        reputation = max(self.MIN_REPUTATION, min(self.MAX_REPUTATION, reputation))
        
        # 更新缓存
        self._reputation_cache[agent_id] = (reputation, datetime.now().timestamp())
        
        return reputation
    
    def get_trust_score(self, agent_id: str) -> float:
        """
        获取信任分数
        
        信任分数基于声誉和历史行为。
        
        Args:
            agent_id: Agent ID
            
        Returns:
            float: 信任分数 (0.0-1.0)
        """
        reviews = self.get_reviews(agent_id, limit=100)
        
        if not reviews:
            return 0.5
        
        # 信任分数 = 声誉 × 一致性因子
        reputation = self.calculate_reputation(agent_id)
        
        # 一致性因子：评价的离散程度
        ratings = [r.rating.value for r in reviews]
        if len(ratings) > 1:
            import statistics
            std_dev = statistics.stdev(ratings) if len(ratings) > 1 else 0
            consistency = 1.0 - (std_dev / 2.0)  # 标准差越小，一致性越高
        else:
            consistency = 1.0
        
        trust_score = reputation * consistency
        
        return max(0.0, min(1.0, trust_score))
    
    def get_rating_distribution(self, agent_id: str) -> dict[str, int]:
        """获取评价分布"""
        reviews = self.get_reviews(agent_id)
        
        distribution = {
            "excellent": 0,
            "good": 0,
            "average": 0,
            "poor": 0,
            "bad": 0,
        }
        
        for review in reviews:
            if review.rating == ReviewRating.EXCELLENT:
                distribution["excellent"] += 1
            elif review.rating == ReviewRating.GOOD:
                distribution["good"] += 1
            elif review.rating == ReviewRating.AVERAGE:
                distribution["average"] += 1
            elif review.rating == ReviewRating.POOR:
                distribution["poor"] += 1
            elif review.rating == ReviewRating.BAD:
                distribution["bad"] += 1
        
        return distribution
    
    def get_statistics(self, agent_id: str) -> dict[str, Any]:
        """获取 Agent 的声誉统计"""
        reviews = self.get_reviews(agent_id)
        
        return {
            "total_reviews": len(reviews),
            "reputation": self.calculate_reputation(agent_id),
            "trust_score": self.get_trust_score(agent_id),
            "rating_distribution": self.get_rating_distribution(agent_id),
        }
