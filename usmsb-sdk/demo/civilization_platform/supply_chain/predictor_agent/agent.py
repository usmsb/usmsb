"""
PredictorAgent - 价格预测 Agent

基于历史数据预测价格趋势的智能代理。
集成真实的协议处理器和消息总线。
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import random
import sys
from pathlib import Path

# 添加共享模块路径
shared_path = str(Path(__file__).parent.parent)
if shared_path not in sys.path:
    sys.path.insert(0, shared_path)

from shared.base_agent import BaseAgent, AgentConfig, run_agent
from shared.message_bus import Message

logger = logging.getLogger(__name__)


@dataclass
class PriceDataPoint:
    """价格数据点"""

    timestamp: str
    price: float
    volume: Optional[float] = None
    source: str = "market"


@dataclass
class PredictionModel:
    """预测模型配置"""

    name: str
    version: str
    accuracy: float
    last_trained: str


class PredictorAgent(BaseAgent):
    """
    价格预测 Agent

    主要功能：
    - 收集历史价格数据
    - 基于算法预测价格趋势
    - 提供采购时机建议
    - 市场风险分析
    """

    def __init__(self, config_path: str = "config.yaml"):
        super().__init__(config_path)

        # 价格历史数据
        self.price_history: Dict[str, List[PriceDataPoint]] = {}

        # 预测缓存
        self.predictions_cache: Dict[str, Dict[str, Any]] = {}

        # 模型信息
        self.model_info: Optional[PredictionModel] = None

        # 加载模型配置
        self._load_model()

        # 注册消息处理器
        self._register_handlers()

        # 初始化模拟历史数据
        self._initialize_sample_data()

        logger.info("PredictorAgent initialized")

    def _load_model(self) -> None:
        """加载预测模型配置"""
        model_config = self._demo_config.extra.get("model", {})
        self.model_info = PredictionModel(
            name=model_config.get("name", "LinearRegression"),
            version=model_config.get("version", "1.0.0"),
            accuracy=model_config.get("accuracy", 0.85),
            last_trained=model_config.get("last_trained", datetime.utcnow().isoformat()),
        )

    def _initialize_sample_data(self) -> None:
        """初始化示例历史数据"""
        tracked = self._demo_config.extra.get("tracked_products", [])

        if not tracked:
            # 默认跟踪的商品
            sample_products = [
                ("steel_001", 4500.0, 100),
                ("steel_002", 4200.0, 80),
                ("copper_001", 68000.0, 50),
                ("aluminum_001", 22000.0, 60),
            ]
        else:
            sample_products = [
                (p.get("product_id"), 4500.0, 100)
                for p in tracked
                if p.get("collection_enabled", True)
            ]

        for product_id, base_price, days in sample_products:
            self._generate_sample_history(product_id, base_price, days)

    def _generate_sample_history(self, product_id: str, base_price: float, days: int) -> None:
        """生成模拟历史数据"""
        history = []
        current_price = base_price

        for i in range(days):
            # 模拟价格波动
            change_percent = random.gauss(0, 0.02)
            current_price *= 1 + change_percent

            # 添加趋势
            trend_factor = 1 + (0.001 * (i / days))
            adjusted_price = current_price * trend_factor

            data_point = PriceDataPoint(
                timestamp=(datetime.utcnow() - timedelta(days=days - i)).isoformat(),
                price=round(adjusted_price, 2),
                volume=random.uniform(100, 1000),
                source="market",
            )
            history.append(data_point)

        self.price_history[product_id] = history

    def _register_handlers(self) -> None:
        """注册消息处理器"""
        self.register_handler("price_query", self.handle_price_query)
        self.register_handler("quote_response", self.handle_quote_response)

    async def on_start(self) -> None:
        """启动时的初始化"""
        self.subscribe("predictions")
        self.subscribe(f"predictor_{self.agent_id}")

        # 启动定期预测任务
        scheduled = self._demo_config.extra.get("scheduled_tasks", {})
        periodic = scheduled.get("periodic_prediction", {})
        if periodic.get("enabled", True):
            interval = periodic.get("interval_seconds", 3600)
            task = asyncio.create_task(self._periodic_prediction_loop(interval))
            self._background_tasks.append(task)

        logger.info(f"PredictorAgent {self.name} ready for predictions")

    async def handle_price_query(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理价格查询请求"""
        payload = message.get("payload", message)
        product_id = payload.get("product_id")
        days_ahead = payload.get("days_ahead", 7)
        requester_id = message.get("sender_id")

        logger.info(f"Price query for {product_id}, {days_ahead} days ahead from {requester_id}")

        prediction = await self.predict_price(product_id, days_ahead)

        # 发送给请求者
        if requester_id:
            await self.send_message(
                "price_prediction",
                prediction,
                receiver_id=requester_id,
                correlation_id=message.get("message_id"),
            )

        return prediction

    async def handle_quote_response(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理报价响应，记录价格数据"""
        payload = message.get("payload", message)
        product_id = payload.get("product_id")
        price = payload.get("unit_price")

        if product_id and price:
            data_point = PriceDataPoint(
                timestamp=datetime.utcnow().isoformat(),
                price=price,
                volume=payload.get("quantity"),
                source="quote",
            )

            if product_id not in self.price_history:
                self.price_history[product_id] = []

            self.price_history[product_id].append(data_point)

            logger.info(f"Recorded price data for {product_id}: {price}")

        return {"status": "recorded"}

    async def predict_price(self, product_id: str, days_ahead: int = 7) -> Dict[str, Any]:
        """预测商品价格"""
        # 检查缓存
        cache_key = f"{product_id}_{days_ahead}"
        cache_config = self._demo_config.extra.get("prediction", {}).get("cache", {})
        cache_enabled = cache_config.get("enabled", True)
        cache_ttl = cache_config.get("ttl_seconds", 300)

        if cache_enabled and cache_key in self.predictions_cache:
            cached = self.predictions_cache[cache_key]
            cache_time = datetime.fromisoformat(cached.get("cached_at", "2000-01-01"))
            if (datetime.utcnow() - cache_time).seconds < cache_ttl:
                logger.debug(f"Returning cached prediction for {product_id}")
                return cached

        # 获取历史数据
        history = self.price_history.get(product_id, [])

        if not history:
            return self._create_empty_prediction(product_id, days_ahead)

        # 计算当前价格
        current_price = history[-1].price if history else 0

        # 生成预测
        predicted_prices = self._generate_predictions(history, current_price, days_ahead)

        # 计算趋势
        trend, trend_strength = self._calculate_trend(history, predicted_prices)

        # 生成建议
        recommendation = self._generate_recommendation(trend, trend_strength, days_ahead)

        # 分析因素
        analysis_factors = self._analyze_factors(history, trend)

        # 计算整体置信度
        prediction_confidence = self._calculate_confidence(history, days_ahead)

        prediction = {
            "predictor_id": self.agent_id,
            "predictor_name": self.name,
            "product_id": product_id,
            "current_price": current_price,
            "currency": "CNY",
            "predicted_prices": predicted_prices,
            "trend": trend,
            "trend_strength": round(trend_strength, 3),
            "recommendation": recommendation,
            "analysis_factors": analysis_factors,
            "prediction_confidence": prediction_confidence,
            "model_info": {
                "name": self.model_info.name if self.model_info else "unknown",
                "version": self.model_info.version if self.model_info else "unknown",
                "accuracy": self.model_info.accuracy if self.model_info else 0,
            },
            "prediction_horizon": days_ahead,
            "cached_at": datetime.utcnow().isoformat(),
        }

        # 缓存预测结果
        if cache_enabled:
            self.predictions_cache[cache_key] = prediction

        # 广播预测结果
        await self.broadcast("price_prediction", prediction)

        logger.info(
            f"Prediction for {product_id}: trend={trend}, confidence={prediction_confidence:.2f}"
        )

        return prediction

    def _generate_predictions(
        self, history: List[PriceDataPoint], current_price: float, days_ahead: int
    ) -> List[Dict[str, Any]]:
        """生成价格预测序列"""
        predictions = []

        # 计算历史波动率
        prices = [p.price for p in history[-30:]]
        if len(prices) < 2:
            volatility = 0.02
        else:
            returns = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))]
            volatility = (sum(r**2 for r in returns) / len(returns)) ** 0.5

        # 计算趋势
        if len(prices) >= 7:
            recent_avg = sum(prices[-7:]) / 7
            older_avg = sum(prices[-14:-7]) / 7 if len(prices) >= 14 else recent_avg
            trend_rate = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0
        else:
            trend_rate = 0

        predicted_price = current_price

        for i in range(1, days_ahead + 1):
            # 添加趋势和随机波动
            trend_component = trend_rate * (i / days_ahead)
            random_component = random.gauss(0, volatility * 0.5)
            change = trend_component + random_component

            predicted_price *= 1 + change
            predicted_price = max(predicted_price, 0)

            # 置信度随预测天数递减
            confidence = max(0.9 - (i * 0.05), 0.5)

            predictions.append(
                {
                    "date": (datetime.utcnow() + timedelta(days=i)).strftime("%Y-%m-%d"),
                    "price": round(predicted_price, 2),
                    "confidence": round(confidence, 2),
                    "change_from_current": round(
                        (predicted_price - current_price) / current_price * 100, 2
                    ),
                }
            )

        return predictions

    def _calculate_trend(
        self, history: List[PriceDataPoint], predictions: List[Dict[str, Any]]
    ) -> Tuple[str, float]:
        """计算价格趋势"""
        if not predictions:
            return "stable", 0.0

        current_price = history[-1].price if history else 0
        final_predicted_price = predictions[-1]["price"]

        if current_price == 0:
            return "stable", 0.0

        change_percent = (final_predicted_price - current_price) / current_price

        thresholds = self._demo_config.extra.get("prediction", {}).get("trend_thresholds", {})
        strong_up = thresholds.get("strong_up", 0.05)
        strong_down = thresholds.get("strong_down", -0.05)

        if change_percent > strong_up:
            return "up", min(change_percent, 1.0)
        elif change_percent < strong_down:
            return "down", max(change_percent, -1.0)
        else:
            return "stable", change_percent

    def _generate_recommendation(self, trend: str, trend_strength: float, days_ahead: int) -> str:
        """生成采购建议"""
        if trend == "up":
            if trend_strength > 0.1:
                return "价格预计显著上涨，建议尽快采购"
            else:
                return "价格预计小幅上涨，建议适当提前采购"
        elif trend == "down":
            if trend_strength < -0.1:
                return "价格预计显著下跌，建议观望"
            else:
                return "价格预计小幅下跌，可适当延后采购"
        else:
            return "价格预计保持稳定，可按需采购"

    def _analyze_factors(self, history: List[PriceDataPoint], trend: str) -> List[str]:
        """分析影响价格的因素"""
        factors = []

        # 市场供需
        if trend == "up":
            factors.append("市场需求增加")
        elif trend == "down":
            factors.append("市场供应充足")

        # 波动性
        prices = [p.price for p in history[-30:]]
        if len(prices) >= 2:
            returns = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))]
            volatility = (sum(r**2 for r in returns) / len(returns)) ** 0.5

            if volatility > 0.03:
                factors.append("市场波动较大，注意风险")
            elif volatility < 0.01:
                factors.append("市场相对稳定")

        # 季节性因素
        current_month = datetime.utcnow().month
        seasonal = self._demo_config.extra.get("seasonal_factors", {})

        spring = seasonal.get("spring_peak", {})
        if current_month in spring.get("months", [3, 4, 5]):
            factors.append("春季开工旺季，需求可能增加")

        autumn = seasonal.get("autumn_peak", {})
        if current_month in autumn.get("months", [9, 10, 11]):
            factors.append("秋季施工旺季，需求可能增加")

        factors.append("原材料成本变化")

        return factors

    def _calculate_confidence(self, history: List[PriceDataPoint], days_ahead: int) -> float:
        """计算预测置信度"""
        conf_config = self._demo_config.extra.get("prediction", {}).get("confidence", {})
        base_confidence = conf_config.get("base_value", 0.85)

        # 数据量因素
        data_points = len(history)
        min_points = (
            self._demo_config.extra.get("model", {}).get("parameters", {}).get("min_data_points", 7)
        )

        if data_points < min_points:
            base_confidence *= 0.5
        elif data_points < 30:
            base_confidence *= 0.75
        elif data_points < 90:
            base_confidence *= 0.9

        # 预测时间因素
        max_horizon = self._demo_config.extra.get("prediction", {}).get("max_horizon", 30)
        if days_ahead > max_horizon * 0.5:
            base_confidence *= 0.7
        elif days_ahead > 14:
            base_confidence *= 0.85

        return round(base_confidence, 2)

    def _create_empty_prediction(self, product_id: str, days_ahead: int) -> Dict[str, Any]:
        """创建空预测响应"""
        return {
            "predictor_id": self.agent_id,
            "product_id": product_id,
            "current_price": 0,
            "currency": "CNY",
            "predicted_prices": [],
            "trend": "unknown",
            "trend_strength": 0,
            "recommendation": "数据不足，无法提供预测",
            "analysis_factors": ["缺乏历史数据"],
            "prediction_confidence": 0,
            "error": "No historical data available",
        }

    def get_price_history(self, product_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """获取价格历史数据"""
        history = self.price_history.get(product_id, [])
        recent = history[-days:] if len(history) > days else history

        return [
            {
                "timestamp": p.timestamp,
                "price": p.price,
                "volume": p.volume,
                "source": p.source,
            }
            for p in recent
        ]

    async def _periodic_prediction_loop(self, interval: int) -> None:
        """定期生成预测"""
        while self._running:
            try:
                await asyncio.sleep(interval)

                if not self._running:
                    break

                # 为所有跟踪的商品生成预测
                for product_id in self.price_history.keys():
                    await self.predict_price(product_id, days_ahead=7)
                    logger.debug(f"Generated periodic prediction for {product_id}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic prediction: {e}")
                await asyncio.sleep(60)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = super().get_stats()
        stats.update(
            {
                "tracked_products": len(self.price_history),
                "cached_predictions": len(self.predictions_cache),
                "model_name": self.model_info.name if self.model_info else None,
                "model_accuracy": self.model_info.accuracy if self.model_info else None,
            }
        )
        return stats


async def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    config_path = os.environ.get("CONFIG_PATH", "config.yaml")
    agent = PredictorAgent(config_path=config_path)

    # 获取端口配置
    http_port = int(os.environ.get("HTTP_PORT", "5103"))
    p2p_port = int(os.environ.get("P2P_PORT", "9103"))
    enable_p2p = os.environ.get("ENABLE_P2P", "true").lower() == "true"
    platform_url = os.environ.get("PLATFORM_URL", agent.config.platform_url)

    # 获取引导节点
    bootstrap_peers_str = os.environ.get("BOOTSTRAP_PEERS", "")
    bootstrap_peers = []
    if bootstrap_peers_str:
        for peer in bootstrap_peers_str.split(","):
            if ":" in peer:
                addr, port = peer.strip().split(":")
                bootstrap_peers.append((addr, int(port)))

    try:
        if enable_p2p:
            # 使用 HTTP + P2P 模式启动 (生产推荐)
            from shared.base_agent import run_agent_with_both

            await run_agent_with_both(
                agent,
                http_port=http_port,
                p2p_port=p2p_port,
                platform_url=platform_url,
                bootstrap_peers=bootstrap_peers if bootstrap_peers else None,
            )
        else:
            # 仅使用 HTTP Server 启动
            from shared.base_agent import run_agent_with_http_sdk

            await run_agent_with_http_sdk(
                agent,
                http_port=http_port,
                platform_url=platform_url,
            )
    except KeyboardInterrupt:
        logging.info("Shutting down PredictorAgent...")


if __name__ == "__main__":
    asyncio.run(main())
