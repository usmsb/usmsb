"""
MarketFeedbackLoop - 市场反馈闭环

Phase 3: 智能优化层 - 核心模块

完整实现：
- 历史数据分析
- 趋势检测
- 价格优化
- 需求预测
- A/B 测试框架
"""

import uuid
import json
import sqlite3
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable


@dataclass
class FeedbackRecord:
    """市场反馈记录"""
    id: str
    agent_id: str
    order_id: str
    capability: str
    price: float
    market_price: float  # 当时市场价
    success: bool
    response_time: float  # 响应时间（秒）
    completion_time: float  # 完成时间（秒）
    quality_score: float  # 质量评分 0-1
    customer_satisfaction: float  # 客户满意度 0-1
    timestamp: float
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "order_id": self.order_id,
            "capability": self.capability,
            "price": self.price,
            "market_price": self.market_price,
            "success": self.success,
            "response_time": self.response_time,
            "completion_time": self.completion_time,
            "quality_score": self.quality_score,
            "customer_satisfaction": self.customer_satisfaction,
            "timestamp": self.timestamp
        }


@dataclass
class TrendAnalysis:
    """趋势分析结果"""
    capability: str
    direction: str  # "up", "down", "stable"
    change_rate: float  # 变化率
    confidence: float  # 置信度 0-1
    prediction: float  # 预测值
    sample_size: int


@dataclass
class PriceRecommendation:
    """价格建议"""
    agent_id: str
    capability: str
    optimal_price: float
    min_price: float
    max_price: float
    confidence: float
    based_on: dict  # 分析依据
    expected_success_rate: float
    expected_volume: int


@dataclass
class DemandForecast:
    """需求预测"""
    capability: str
    current_demand: float  # 当前需求指数 0-1
    predicted_demand_7d: float  # 7天预测
    predicted_demand_30d: float  # 30天预测
    confidence: float
    seasonality: dict  # 季节性因素
    trends: list[str]  # 趋势描述


@dataclass
class ABTestResult:
    """A/B 测试结果"""
    test_id: str
    hypothesis: str
    variant_a_results: dict
    variant_b_results: dict
    winner: str  # "a", "b", "none"
    statistical_significance: float  # 统计显著性
    p_value: float
    recommended_action: str


class MarketFeedbackDB:
    """市场反馈数据库"""
    
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = "/Users/gujun/vibecode/usmsb/data/market_feedback.db"
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                order_id TEXT NOT NULL,
                capability TEXT NOT NULL,
                price REAL NOT NULL,
                market_price REAL NOT NULL,
                success INTEGER NOT NULL,
                response_time REAL NOT NULL,
                completion_time REAL NOT NULL,
                quality_score REAL NOT NULL,
                customer_satisfaction REAL NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent ON feedback(agent_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_capability ON feedback(capability)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON feedback(timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def save(self, record: FeedbackRecord) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO feedback 
            (id, agent_id, order_id, capability, price, market_price, success,
             response_time, completion_time, quality_score, customer_satisfaction, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.id, record.agent_id, record.order_id, record.capability,
            record.price, record.market_price, int(record.success),
            record.response_time, record.completion_time,
            record.quality_score, record.customer_satisfaction, record.timestamp
        ))
        
        conn.commit()
        conn.close()
        return True
    
    def load_recent(self, agent_id: str | None = None, days: int = 30) -> list[FeedbackRecord]:
        cutoff = datetime.now().timestamp() - days * 86400
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if agent_id:
            cursor.execute("""
                SELECT * FROM feedback
                WHERE timestamp > ? AND agent_id = ?
                ORDER BY timestamp DESC
            """, (cutoff, agent_id))
        else:
            cursor.execute("""
                SELECT * FROM feedback
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            """, (cutoff,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [FeedbackRecord(
            id=row[0], agent_id=row[1], order_id=row[2],
            capability=row[3], price=row[4], market_price=row[5],
            success=bool(row[6]), response_time=row[7],
            completion_time=row[8], quality_score=row[9],
            customer_satisfaction=row[10], timestamp=row[11]
        ) for row in rows]
    
    def get_capability_stats(self, capability: str, days: int = 30) -> dict:
        cutoff = datetime.now().timestamp() - days * 86400
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                AVG(price) as avg_price,
                AVG(success) as avg_success,
                AVG(quality_score) as avg_quality,
                AVG(customer_satisfaction) as avg_satisfaction,
                COUNT(*) as count
            FROM feedback
            WHERE capability = ? AND timestamp > ?
        """, (capability, cutoff))
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            "capability": capability,
            "avg_price": row[0] or 0,
            "avg_success_rate": row[1] or 0,
            "avg_quality": row[2] or 0,
            "avg_satisfaction": row[3] or 0,
            "sample_size": row[4] or 0
        }


class TrendDetector:
    """趋势检测器 - 使用真实统计方法"""
    
    def __init__(self, min_samples: int = 10):
        self.min_samples = min_samples
    
    def detect_trend(self, prices: list[float], timestamps: list[float]) -> TrendAnalysis:
        """
        使用线性回归检测趋势
        
        Args:
            prices: 价格序列
            timestamps: 时间戳序列
            
        Returns:
            TrendAnalysis: 趋势分析结果
        """
        if len(prices) < self.min_samples:
            return TrendAnalysis(
                capability="",
                direction="stable",
                change_rate=0,
                confidence=0,
                prediction=statistics.mean(prices) if prices else 0,
                sample_size=len(prices)
            )
        
        # 线性回归
        n = len(prices)
        x_mean = statistics.mean(timestamps)
        y_mean = statistics.mean(prices)
        
        numerator = sum((t - x_mean) * (p - y_mean) for t, p in zip(timestamps, prices))
        denominator = sum((t - x_mean) ** 2 for t in timestamps)
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # 计算趋势方向
        price_range = max(prices) - min(prices)
        if abs(slope) < price_range * 0.001:
            direction = "stable"
            change_rate = 0
        elif slope > 0:
            direction = "up"
            change_rate = slope * (timestamps[-1] - timestamps[0]) / price_range if price_range > 0 else 0
        else:
            direction = "down"
            change_rate = slope * (timestamps[-1] - timestamps[0]) / price_range if price_range > 0 else 0
        
        # 预测下一个值
        last_timestamp = timestamps[-1]
        interval = (timestamps[-1] - timestamps[0]) / (n - 1) if n > 1 else 86400
        prediction = prices[-1] + slope * interval
        
        # 计算置信度（基于样本量和标准差）
        if len(prices) > 1:
            stdev = statistics.stdev(prices)
            cv = stdev / statistics.mean(prices) if statistics.mean(prices) > 0 else 0
            confidence = min(1.0, n / 100) * (1 - min(1.0, cv))
        else:
            confidence = 0
        
        return TrendAnalysis(
            capability="",
            direction=direction,
            change_rate=change_rate,
            confidence=confidence,
            prediction=prediction,
            sample_size=n
        )


class PriceOptimizer:
    """价格优化器 - 使用弹性模型"""
    
    # 价格弹性系数（简化模型）
    DEFAULT_ELASTICITY = -0.8  # 价格每涨 1%，需求降 0.8%
    
    def __init__(self):
        self.elasticity_cache: dict[str, float] = {}
    
    def calculate_optimal_price(
        self,
        base_cost: float,
        avg_success_rate: float,
        market_avg_price: float,
        elasticity: float | None = None
    ) -> PriceRecommendation:
        """
        基于供需弹性模型计算最优价格
        
        Args:
            base_cost: 基础成本
            avg_success_rate: 平均成功率
            market_avg_price: 市场均价
            elasticity: 价格弹性（可选）
            
        Returns:
            PriceRecommendation: 价格建议
        """
        if elasticity is None:
            elasticity = self.DEFAULT_ELASTICITY
        
        # 成功率高可以溢价
        success_premium = (avg_success_rate - 0.5) * 0.3  # ±15%
        
        # 基于弹性的价格范围
        # 最优价格 = 成本 / (1 - |弹性| * (1 - success_rate))
        denominator = 1 - abs(elasticity) * (1 - avg_success_rate)
        if denominator <= 0:
            denominator = 0.1
        
        optimal = base_cost / denominator * (1 + success_premium)
        
        # 市场校准
        optimal = (optimal * 0.6 + market_avg_price * 0.4)
        
        # 价格范围
        min_price = optimal * 0.7
        max_price = optimal * 1.3
        
        # 预期成功率
        expected_success = avg_success_rate * (1 + (optimal - market_avg_price) / market_avg_price * elasticity)
        expected_success = max(0.1, min(0.99, expected_success))
        
        return PriceRecommendation(
            agent_id="",
            capability="",
            optimal_price=optimal,
            min_price=min_price,
            max_price=max_price,
            confidence=0.8 if avg_success_rate > 0.7 else 0.6,
            based_on={
                "base_cost": base_cost,
                "market_avg": market_avg_price,
                "success_rate": avg_success_rate,
                "elasticity": elasticity
            },
            expected_success_rate=expected_success,
            expected_volume=int(100 * expected_success)
        )
    
    def estimate_elasticity(
        self,
        price_data: list[tuple[float, float]]  # (price, demand) pairs
    ) -> float:
        """
        从数据中估计价格弹性
        
        使用对数回归: ln(demand) = a + b * ln(price)
        弹性 = b
        
        Args:
            price_data: (价格, 需求量) 对列表
            
        Returns:
            float: 估计的弹性系数
        """
        if len(price_data) < 5:
            return self.DEFAULT_ELASTICITY
        
        # 过滤掉零值
        valid_data = [(p, d) for p, d in price_data if p > 0 and d > 0]
        
        if len(valid_data) < 5:
            return self.DEFAULT_ELASTICITY
        
        # 对数转换
        ln_prices = [math.log(p) for p, d in valid_data]
        ln_demands = [math.log(d) for p, d in valid_data]
        
        # 简单线性回归
        n = len(ln_prices)
        x_mean = sum(ln_prices) / n
        y_mean = sum(ln_demands) / n
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(ln_prices, ln_demands))
        denominator = sum((x - x_mean) ** 2 for x in ln_prices)
        
        if denominator == 0:
            return self.DEFAULT_ELASTICITY
        
        elasticity = numerator / denominator
        
        # 限制在合理范围内
        return max(-2.0, min(-0.1, elasticity))


class DemandForecaster:
    """需求预测器 - 使用时间序列分析"""
    
    def __init__(self):
        self.seasonality_period = 7 * 86400  # 7天周期
    
    def forecast(
        self,
        capability: str,
        historical_data: list[FeedbackRecord],
        forecast_days: int = 30
    ) -> DemandForecast:
        """
        使用分解法进行需求预测
        
        分解为：趋势 + 季节性 + 残差
        
        Args:
            capability: 能力类型
            historical_data: 历史数据
            forecast_days: 预测天数
            
        Returns:
            DemandForecast: 需求预测
        """
        if len(historical_data) < 10:
            return DemandForecast(
                capability=capability,
                current_demand=0.5,
                predicted_demand_7d=0.5,
                predicted_demand_30d=0.5,
                confidence=0.3,
                seasonality={},
                trends=["数据不足"]
            )
        
        # 计算每日需求
        daily_demand = self._aggregate_daily_demand(historical_data)
        
        # 趋势检测
        trend = self._detect_trend(daily_demand)
        
        # 季节性分析
        seasonality = self._analyze_seasonality(daily_demand)
        
        # 当前需求
        current = self._calculate_current_demand(daily_demand)
        
        # 预测
        predicted_7d = self._extrapolate(daily_demand, trend, seasonality, 7)
        predicted_30d = self._extrapolate(daily_demand, trend, seasonality, 30)
        
        trends = []
        if trend > 0.1:
            trends.append("需求上升")
        elif trend < -0.1:
            trends.append("需求下降")
        else:
            trends.append("需求稳定")
        
        return DemandForecast(
            capability=capability,
            current_demand=current,
            predicted_demand_7d=predicted_7d,
            predicted_demand_30d=predicted_30d,
            confidence=min(0.9, len(historical_data) / 100),
            seasonality=seasonality,
            trends=trends
        )
    
    def _aggregate_daily_demand(self, data: list[FeedbackRecord]) -> dict[str, int]:
        """按天聚合需求"""
        daily = defaultdict(int)
        for record in data:
            day = datetime.fromtimestamp(record.timestamp).strftime("%Y-%m-%d")
            if record.success:
                daily[day] += 1
        return dict(daily)
    
    def _detect_trend(self, daily: dict[str, int]) -> float:
        """检测趋势（每日变化率）"""
        if len(daily) < 2:
            return 0
        
        values = list(daily.values())
        n = len(values)
        
        # 简单线性回归
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, values))
        denominator = sum((xi - x_mean) ** 2 for xi in x)
        
        if denominator == 0:
            return 0
        
        slope = numerator / denominator
        avg = y_mean if y_mean > 0 else 1
        
        return slope / avg  # 相对变化率
    
    def _analyze_seasonality(self, daily: dict[str, int]) -> dict:
        """分析季节性（周模式）"""
        weekday_pattern = defaultdict(list)
        
        for day_str, count in daily.items():
            dt = datetime.strptime(day_str, "%Y-%m-%d")
            weekday = dt.weekday()  # 0=周一, 6=周日
            weekday_pattern[weekday].append(count)
        
        pattern = {}
        for weekday, counts in weekday_pattern.items():
            pattern[weekday] = statistics.mean(counts)
        
        # 归一化
        if pattern:
            max_val = max(pattern.values())
            if max_val > 0:
                pattern = {k: v / max_val for k, v in pattern.items()}
        
        return pattern
    
    def _calculate_current_demand(self, daily: dict[str, int]) -> float:
        """计算当前需求指数（最近7天平均）"""
        if not daily:
            return 0.5
        
        sorted_days = sorted(daily.keys())
        recent_days = sorted_days[-7:] if len(sorted_days) >= 7 else sorted_days
        
        recent_avg = statistics.mean(daily[d] for d in recent_days)
        
        # 归一化到 0-1
        all_avg = statistics.mean(daily.values()) if daily else 1
        if all_avg > 0:
            return min(1.0, recent_avg / (all_avg * 2))
        return 0.5
    
    def _extrapolate(
        self,
        daily: dict[str, int],
        trend: float,
        seasonality: dict,
        days: int
    ) -> float:
        """外推预测"""
        current = self._calculate_current_demand(daily)
        
        # 趋势外推
        extrapolated = current * (1 + trend * days / 7)
        
        # 季节性调整
        weekday = datetime.now().weekday()
        if weekday in seasonality:
            extrapolated *= seasonality[weekday]
        
        return max(0.1, min(1.0, extrapolated))


class ABTestEngine:
    """A/B 测试引擎 - 完整的统计显著性检验"""
    
    def __init__(self, min_sample_size: int = 30):
        self.min_sample_size = min_sample_size
        self._tests: dict[str, dict] = defaultdict(dict)
    
    def create_test(
        self,
        test_id: str,
        hypothesis: str,
        variant_a: Callable,
        variant_b: Callable,
        metric_fn: Callable[[list], float]
    ) -> None:
        """
        创建 A/B 测试
        
        Args:
            test_id: 测试 ID
            hypothesis: 假设描述
            variant_a: A 变体函数
            variant_b: B 变体函数
            metric_fn: 评估指标函数
        """
        self._tests[test_id] = {
            "hypothesis": hypothesis,
            "variant_a": variant_a,
            "variant_b": variant_b,
            "metric_fn": metric_fn,
            "results_a": [],
            "results_b": [],
            "created_at": datetime.now().timestamp()
        }
    
    def record_result(self, test_id: str, variant: str, result: float) -> None:
        """记录测试结果"""
        if test_id not in self._tests:
            return
        
        if variant == "a":
            self._tests[test_id]["results_a"].append(result)
        elif variant == "b":
            self._tests[test_id]["results_b"].append(result)
    
    def analyze(self, test_id: str) -> ABTestResult | None:
        """
        分析测试结果（使用双样本 t 检验）
        
        Returns:
            ABTestResult: 分析结果
        """
        if test_id not in self._tests:
            return None
        
        test = self._tests[test_id]
        results_a = test["results_a"]
        results_b = test["results_b"]
        
        if len(results_a) < self.min_sample_size or len(results_b) < self.min_sample_size:
            return ABTestResult(
                test_id=test_id,
                hypothesis=test["hypothesis"],
                variant_a_results={"mean": statistics.mean(results_a) if results_a else 0},
                variant_b_results={"mean": statistics.mean(results_b) if results_b else 0},
                winner="none",
                statistical_significance=0,
                p_value=1.0,
                recommended_action="数据不足"
            )
        
        # 计算统计量
        mean_a = statistics.mean(results_a)
        mean_b = statistics.mean(results_b)
        std_a = statistics.stdev(results_a) if len(results_a) > 1 else 0
        std_b = statistics.stdev(results_b) if len(results_b) > 1 else 0
        n_a = len(results_a)
        n_b = len(results_b)
        
        # 合并标准误差
        pooled_se = ((std_a ** 2 / n_a) + (std_b ** 2 / n_b)) ** 0.5
        
        # t 统计量
        if pooled_se > 0:
            t_stat = (mean_b - mean_a) / pooled_se
        else:
            t_stat = 0
        
        # 简化 p 值（使用正态近似）
        from math import sqrt, erf
        p_value = 2 * (1 - 0.5 * (1 + erf(abs(t_stat) / sqrt(2))))
        
        # 统计显著性
        significance = 1 - p_value
        
        # 判断赢家
        if p_value < 0.05:
            if mean_b > mean_a:
                winner = "b"
            else:
                winner = "a"
        else:
            winner = "none"
        
        return ABTestResult(
            test_id=test_id,
            hypothesis=test["hypothesis"],
            variant_a_results={
                "mean": mean_a,
                "std": std_a,
                "n": n_a
            },
            variant_b_results={
                "mean": mean_b,
                "std": std_b,
                "n": n_b
            },
            winner=winner,
            statistical_significance=significance,
            p_value=p_value,
            recommended_action=f"{winner.upper()} 变体" if winner != "none" else "继续收集数据"
        )


class MarketFeedbackLoop:
    """
    市场反馈闭环 - 完整实现
    
    整合所有市场分析功能，形成闭环优化。
    """
    
    def __init__(self):
        self.db = MarketFeedbackDB()
        self.trend_detector = TrendDetector()
        self.price_optimizer = PriceOptimizer()
        self.demand_forecaster = DemandForecaster()
        self.ab_engine = ABTestEngine()
    
    def record_feedback(
        self,
        agent_id: str,
        order_id: str,
        capability: str,
        price: float,
        market_price: float,
        success: bool,
        response_time: float,
        completion_time: float,
        quality_score: float,
        customer_satisfaction: float
    ) -> None:
        """记录市场反馈"""
        record = FeedbackRecord(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            order_id=order_id,
            capability=capability,
            price=price,
            market_price=market_price,
            success=success,
            response_time=response_time,
            completion_time=completion_time,
            quality_score=quality_score,
            customer_satisfaction=customer_satisfaction,
            timestamp=datetime.now().timestamp()
        )
        self.db.save(record)
    
    def analyze_agent_trends(self, agent_id: str, days: int = 30) -> list[TrendAnalysis]:
        """分析 Agent 的趋势"""
        records = self.db.load_recent(agent_id, days)
        
        # 按能力分组
        by_capability = defaultdict(list)
        for record in records:
            by_capability[record.capability].append(record)
        
        results = []
        for capability, cap_records in by_capability.items():
            if len(cap_records) < 5:
                continue
            
            prices = [r.price for r in cap_records]
            timestamps = [r.timestamp for r in cap_records]
            
            trend = self.trend_detector.detect_trend(prices, timestamps)
            trend.capability = capability
            results.append(trend)
        
        return results
    
    def get_price_recommendation(
        self,
        agent_id: str,
        capability: str,
        base_cost: float
    ) -> PriceRecommendation:
        """获取价格建议"""
        # 获取该能力的市场统计
        stats = self.db.get_capability_stats(capability)
        
        # 获取需求预测
        records = self.db.load_recent(days=30)
        forecast = self.demand_forecaster.forecast(capability, records)
        
        # 考虑需求调整价格
        demand_factor = 1 + (forecast.current_demand - 0.5) * 0.2
        adjusted_cost = base_cost * demand_factor
        
        recommendation = self.price_optimizer.calculate_optimal_price(
            base_cost=adjusted_cost,
            avg_success_rate=stats["avg_success_rate"],
            market_avg_price=stats["avg_price"]
        )
        recommendation.agent_id = agent_id
        recommendation.capability = capability
        
        return recommendation
    
    def get_demand_forecast(self, capability: str) -> DemandForecast:
        """获取需求预测"""
        records = self.db.load_recent(days=90)
        return self.demand_forecaster.forecast(capability, records)
    
    def create_ab_test(
        self,
        test_id: str,
        hypothesis: str,
        agent_id: str
    ) -> None:
        """创建 A/B 测试"""
        def variant_a_fn():
            # 当前策略
            return self.get_price_recommendation(agent_id, "test", 50.0).optimal_price
        
        def variant_b_fn():
            # 新策略（简化版）
            stats = self.db.get_capability_stats("test")
            return stats["avg_price"] * 0.9
        
        def metric_fn(results: list) -> float:
            return statistics.mean(results)
        
        self.ab_engine.create_test(test_id, hypothesis, variant_a_fn, variant_b_fn, metric_fn)
    
    def get_market_statistics(self, capability: str | None = None) -> dict:
        """获取市场统计"""
        if capability:
            return self.db.get_capability_stats(capability)
        else:
            records = self.db.load_recent(days=30)
            capabilities = set(r.capability for r in records)
            stats = {}
            for cap in capabilities:
                stats[cap] = self.db.get_capability_stats(cap)
            return stats


import math
