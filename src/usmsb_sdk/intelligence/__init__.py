# -*- coding: utf-8 -*-
"""
Phase 3: Intelligent Optimization Layer

USMSB 智能优化模块。

功能：
- 历史数据分析
- 定价策略优化
- 需求预测
- 市场反馈闭环
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class StrategyAnalysis:
    """策略分析结果"""
    id: str
    agent_id: str
    analysis_type: str  # pricing, timing, demand
    data_points: int
    insights: list[str]
    recommendations: list[str]
    confidence: float  # 0.0-1.0
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class PriceSuggestion:
    """价格建议"""
    agent_id: str
    suggested_price: float
    currency: str
    confidence: float
    based_on: list[str]  # 分析方法
    market_avg: float
    agent_reputation: float


class MarketFeedbackLoop:
    """
    市场反馈闭环
    
    收集市场数据，分析反馈，调整策略。
    """
    
    def __init__(self):
        self._feedback_data: list[dict] = []
        self._analyses: list[StrategyAnalysis] = []
    
    def record_feedback(
        self,
        agent_id: str,
        order_id: str,
        price: float,
        success: bool,
        response_time: float
    ) -> None:
        """记录市场反馈"""
        self._feedback_data.append({
            "agent_id": agent_id,
            "order_id": order_id,
            "price": price,
            "success": success,
            "response_time": response_time,
            "timestamp": datetime.now().timestamp()
        })
    
    def analyze_trends(self, agent_id: str) -> StrategyAnalysis:
        """分析趋势"""
        agent_data = [f for f in self._feedback_data if f["agent_id"] == agent_id]
        
        if not agent_data:
            return None
        
        insights = []
        recommendations = []
        
        # 计算平均成功率
        success_rate = sum(1 for f in agent_data if f["success"]) / len(agent_data)
        
        if success_rate < 0.5:
            insights.append(f"成功率偏低: {success_rate:.1%}")
            recommendations.append("建议降低价格或提高响应速度")
        
        # 计算平均价格
        avg_price = sum(f["price"] for f in agent_data) / len(agent_data)
        insights.append(f"平均成交价格: {avg_price:.2f}")
        
        return StrategyAnalysis(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            analysis_type="trend",
            data_points=len(agent_data),
            insights=insights,
            recommendations=recommendations,
            confidence=min(1.0, len(agent_data) / 100)
        )


class DemandPredictor:
    """需求预测"""
    
    def predict(self, capability: str, days: int = 7) -> dict:
        """预测需求"""
        # 简化预测
        return {
            "capability": capability,
            "predicted_demand": 0.5 + (datetime.now().timestamp() % 100) / 200,
            "confidence": 0.6,
            "timeframe_days": days
        }


class PriceSuggestionEngine:
    """报价建议引擎"""
    
    def suggest_price(
        self,
        agent_id: str,
        base_cost: float,
        market_avg: float,
        agent_reputation: float
    ) -> PriceSuggestion:
        """建议价格"""
        # 基于声誉和市场均价计算
        reputation_factor = 0.5 + agent_reputation * 0.5
        suggested = base_cost * (1 + reputation_factor) * 0.8 + market_avg * 0.2
        
        return PriceSuggestion(
            agent_id=agent_id,
            suggested_price=suggested,
            currency="VIBE",
            confidence=0.7,
            based_on=["cost", "reputation", "market_avg"],
            market_avg=market_avg,
            agent_reputation=agent_reputation
        )


class IntelligentOptimizer:
    """
    智能优化器
    
    整合所有智能优化功能。
    """
    
    def __init__(self):
        self.feedback_loop = MarketFeedbackLoop()
        self.demand_predictor = DemandPredictor()
        self.price_engine = PriceSuggestionEngine()
    
    def get_price_suggestion(
        self,
        agent_id: str,
        base_cost: float,
        market_avg: float,
        agent_reputation: float
    ) -> PriceSuggestion:
        """获取价格建议"""
        return self.price_engine.suggest_price(
            agent_id, base_cost, market_avg, agent_reputation
        )
    
    def predict_demand(self, capability: str) -> dict:
        """预测需求"""
        return self.demand_predictor.predict(capability)
    
    def run_analysis(self, agent_id: str) -> StrategyAnalysis | None:
        """运行分析"""
        return self.feedback_loop.analyze_trends(agent_id)
