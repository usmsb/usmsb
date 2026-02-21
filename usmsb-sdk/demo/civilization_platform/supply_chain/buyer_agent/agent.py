"""
BuyerAgent - 需求询价 Agent

发起询价请求，接收并比较报价的智能代理。
集成真实的协议处理器和消息总线。
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
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
class QuoteRequestRecord:
    """询价请求记录"""

    request_id: str
    product_id: str
    product_name: str
    quantity: float
    unit: str
    delivery_date: Optional[str]
    delivery_location: str
    requirements: Dict[str, Any]
    status: str = "pending"
    responses: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class BuyerAgent(BaseAgent):
    """
    需求询价 Agent

    主要功能：
    - 发起询价请求
    - 接收和比较多个供应商报价
    - 根据价格预测决定采购时机
    - 确认撮合结果
    """

    def __init__(self, config_path: str = "config.yaml"):
        super().__init__(config_path)

        # 询价记录
        self.quote_requests: Dict[str, QuoteRequestRecord] = {}

        # 采购历史
        self.purchase_history: List[Dict[str, Any]] = []

        # 价格预测缓存
        self.price_predictions: Dict[str, Dict[str, Any]] = {}

        # 已知供应商
        self.known_suppliers: List[str] = []

        # 注册消息处理器
        self._register_handlers()

        logger.info("BuyerAgent initialized")

    def _register_handlers(self) -> None:
        """注册消息处理器"""
        self.register_handler("quote_response", self.handle_quote_response)
        self.register_handler("price_prediction", self.handle_price_prediction)
        self.register_handler("match_result", self.handle_match_result)
        self.register_handler("match_confirm_ack", self.handle_match_confirm_ack)

    async def on_start(self) -> None:
        """启动时的初始化"""
        # 订阅相关主题
        self.subscribe("quotes")
        self.subscribe("predictions")
        self.subscribe(f"buyer_{self.agent_id}")

        logger.info(f"BuyerAgent {self.name} ready for purchasing")

    # ========== 询价功能 ==========

    def create_quote_request(
        self,
        product_id: str,
        product_name: str,
        quantity: float,
        unit: str = "件",
        delivery_date: Optional[str] = None,
        delivery_location: str = "",
        requirements: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        创建询价请求

        Args:
            product_id: 商品 ID
            product_name: 商品名称
            quantity: 需求数量
            unit: 单位
            delivery_date: 期望交货日期
            delivery_location: 交货地点
            requirements: 其他要求

        Returns:
            询价请求消息
        """
        request_id = f"req_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        request = {
            "request_id": request_id,
            "product_id": product_id,
            "product_name": product_name,
            "quantity": quantity,
            "unit": unit,
            "delivery_date": delivery_date,
            "delivery_location": delivery_location,
            "requirements": requirements or {},
        }

        # 保存记录
        record = QuoteRequestRecord(
            request_id=request_id,
            product_id=product_id,
            product_name=product_name,
            quantity=quantity,
            unit=unit,
            delivery_date=delivery_date,
            delivery_location=delivery_location,
            requirements=requirements or {},
        )
        self.quote_requests[request_id] = record

        logger.info(f"Created quote request: {request_id} for {product_name}")

        return request

    async def send_quote_request(
        self, request: Dict[str, Any], target_suppliers: Optional[List[str]] = None
    ) -> bool:
        """
        发送询价请求

        Args:
            request: 询价请求数据
            target_suppliers: 目标供应商列表（None 表示广播给所有）

        Returns:
            是否发送成功
        """
        request_id = request.get("request_id")
        logger.info(f"Sending quote request: {request_id}")

        payload = {
            **request,
            "buyer_id": self.agent_id,
            "buyer_name": self.name,
        }

        if target_suppliers:
            # 发送给指定供应商
            for supplier_id in target_suppliers:
                await self.send_message("quote_request", payload, receiver_id=supplier_id)
        else:
            # 广播给所有供应商
            count = await self.broadcast("quote_request", payload)
            logger.info(f"Broadcast quote request to {count} agents")

        return True

    async def handle_quote_response(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理报价响应

        接收供应商的报价，保存并评估。
        """
        payload = message.get("payload", message)
        supplier_id = payload.get("supplier_id") or message.get("sender_id")
        request_id = payload.get("request_id")

        logger.info(
            f"Received quote response from {supplier_id}: "
            f"price={payload.get('unit_price')}, "
            f"total={payload.get('total_price')}"
        )

        # 查找对应的询价记录
        if request_id not in self.quote_requests:
            logger.warning(f"Unknown quote request: {request_id}")
            return {"status": "error", "message": "Unknown request"}

        # 保存报价响应
        record = self.quote_requests[request_id]
        quote_data = {
            **payload,
            "supplier_id": supplier_id,
            "received_at": datetime.utcnow().isoformat(),
        }
        record.responses.append(quote_data)
        record.status = "quoted"
        record.updated_at = datetime.utcnow().isoformat()

        # 评估报价
        evaluation = self._evaluate_quote(quote_data, record)

        logger.info(
            f"Quote evaluated: score={evaluation['total_score']:.1f}, "
            f"recommendation={evaluation['recommendation']}"
        )

        return {
            "status": "received",
            "request_id": request_id,
            "evaluation": evaluation,
        }

    def _evaluate_quote(self, quote: Dict[str, Any], request: QuoteRequestRecord) -> Dict[str, Any]:
        """评估报价"""
        score = 0.0
        factors = {}

        # 获取配置的权重
        weights = self._get_evaluation_weights()

        # 价格评估
        price = quote.get("unit_price", 0)
        target_price = request.requirements.get("target_price", price * 1.1)

        if target_price > 0:
            price_ratio = price / target_price
            if price_ratio <= 0.9:
                factors["price"] = {"score": 100, "note": "价格低于目标"}
            elif price_ratio <= 1.0:
                factors["price"] = {"score": 80, "note": "价格接近目标"}
            elif price_ratio <= 1.1:
                factors["price"] = {"score": 60, "note": "价格略高于目标"}
            else:
                factors["price"] = {"score": 40, "note": "价格较高"}
        else:
            factors["price"] = {"score": 70, "note": "无目标参考"}

        score += factors["price"]["score"] * weights.get("price", 0.4)

        # 交货时间评估
        lead_time = quote.get("delivery_lead_time", 7)
        if request.delivery_date:
            days_until_delivery = self._calculate_days_until(request.delivery_date)
            if lead_time <= days_until_delivery * 0.5:
                factors["delivery"] = {"score": 100, "note": "交货时间充裕"}
            elif lead_time <= days_until_delivery * 0.8:
                factors["delivery"] = {"score": 80, "note": "交货时间合适"}
            elif lead_time <= days_until_delivery:
                factors["delivery"] = {"score": 60, "note": "交货时间紧张"}
            else:
                factors["delivery"] = {"score": 30, "note": "可能无法按时交货"}
        else:
            factors["delivery"] = {"score": 70, "note": "无特定交货要求"}

        score += factors["delivery"]["score"] * weights.get("delivery", 0.3)

        # 供应商评估
        supplier_rating = quote.get("supplier_rating", 3.5)
        rating_score = min(supplier_rating / 5.0 * 100, 100)
        factors["supplier"] = {"score": rating_score, "note": f"供应商评级: {supplier_rating}"}
        score += rating_score * weights.get("supplier", 0.2)

        # 条款评估
        terms = quote.get("terms", {})
        terms_score = 70
        if quote.get("discount_applied"):
            terms_score += 10
        if terms.get("warranty"):
            terms_score += 10
        factors["terms"] = {"score": terms_score, "note": "附加条款"}
        score += terms_score * weights.get("terms", 0.1)

        return {
            "total_score": round(score, 2),
            "factors": factors,
            "recommendation": self._get_recommendation(score),
        }

    def _get_evaluation_weights(self) -> Dict[str, float]:
        """获取评估权重配置"""
        preferences = self._demo_config.extra.get("purchasing_preferences", {})
        priority_factors = preferences.get("priority_factors", [])

        weights = {"price": 0.4, "delivery": 0.3, "supplier": 0.2, "terms": 0.1}

        for factor in priority_factors:
            name = factor.get("name")
            weight = factor.get("weight")
            if name and weight is not None:
                weights[name] = weight

        return weights

    def _calculate_days_until(self, date_str: str) -> int:
        """计算距离目标日期的天数"""
        try:
            target_date = datetime.fromisoformat(date_str.replace("Z", ""))
            return max((target_date - datetime.utcnow()).days, 1)
        except Exception:
            return 30

    def _get_recommendation(self, score: float) -> str:
        """根据评分给出建议"""
        if score >= 80:
            return "强烈推荐接受此报价"
        elif score >= 70:
            return "推荐接受此报价"
        elif score >= 60:
            return "可以考虑此报价"
        elif score >= 50:
            return "建议继续询价"
        else:
            return "不推荐此报价"

    # ========== 价格预测 ==========

    async def handle_price_prediction(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理价格预测"""
        payload = message.get("payload", message)
        product_id = payload.get("product_id")

        self.price_predictions[product_id] = {
            **payload,
            "received_at": datetime.utcnow().isoformat(),
        }

        logger.info(
            f"Price prediction received for {product_id}: "
            f"trend={payload.get('trend')}, "
            f"recommendation={payload.get('recommendation')}"
        )

        return {"status": "received", "product_id": product_id}

    async def request_price_prediction(self, product_id: str, days_ahead: int = 7) -> bool:
        """请求价格预测"""
        await self.broadcast(
            "price_query",
            {
                "product_id": product_id,
                "days_ahead": days_ahead,
                "requester_id": self.agent_id,
            },
        )
        return True

    # ========== 撮合处理 ==========

    async def handle_match_result(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理撮合结果"""
        payload = message.get("payload", message)
        match_id = payload.get("match_id")
        match_score = payload.get("match_score", 0)

        logger.info(f"Match result received: {match_id}, score: {match_score}")

        # 根据匹配分数决定是否接受
        auto_decision = self._demo_config.extra.get("auto_decision", {})
        auto_enabled = auto_decision.get("enabled", True)
        auto_accept_threshold = auto_decision.get("auto_accept_threshold", 80)

        if auto_enabled and match_score * 100 >= auto_accept_threshold:
            # 自动接受
            return await self._accept_match(payload)
        elif match_score >= 0.5:
            # 需要评估
            return await self._evaluate_match(payload)
        else:
            # 自动拒绝
            return await self._reject_match(payload, "Match score too low")

    async def _accept_match(self, match: Dict[str, Any]) -> Dict[str, Any]:
        """接受撮合"""
        match_id = match.get("match_id")

        # 记录采购历史
        self.purchase_history.append(
            {
                "match_id": match_id,
                "product_id": match.get("product_id"),
                "product_name": match.get("product_name"),
                "quantity": match.get("matched_quantity"),
                "price": match.get("matched_price"),
                "total_amount": match.get("total_amount"),
                "supplier_id": match.get("supplier_id"),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # 发送确认给 MatchAgent
        await self.broadcast(
            "match_confirm",
            {
                "match_id": match_id,
                "buyer_id": self.agent_id,
                "confirmed_at": datetime.utcnow().isoformat(),
            },
        )

        logger.info(f"Match {match_id} accepted")

        return {
            "status": "accepted",
            "match_id": match_id,
        }

    async def _evaluate_match(self, match: Dict[str, Any]) -> Dict[str, Any]:
        """评估撮合（简化处理，实际中可能需要人工确认）"""
        # 检查价格预测
        product_id = match.get("product_id")
        if product_id in self.price_predictions:
            prediction = self.price_predictions[product_id]
            trend = prediction.get("trend", "stable")

            if trend == "down":
                logger.info(f"Price trending down, considering rejection")
                # 可以选择等待或接受
                return await self._accept_match(match)

        return await self._accept_match(match)

    async def _reject_match(self, match: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """拒绝撮合"""
        match_id = match.get("match_id")

        await self.broadcast(
            "match_reject",
            {
                "match_id": match_id,
                "buyer_id": self.agent_id,
                "reason": reason,
                "rejected_at": datetime.utcnow().isoformat(),
            },
        )

        logger.info(f"Match {match_id} rejected: {reason}")

        return {
            "status": "rejected",
            "match_id": match_id,
            "reason": reason,
        }

    async def handle_match_confirm_ack(self, message: Dict[str, Any]) -> None:
        """处理撮合确认回执"""
        payload = message.get("payload", message)
        match_id = payload.get("match_id")
        status = payload.get("status")

        logger.info(f"Match {match_id} confirmation acknowledged: {status}")

    # ========== 辅助方法 ==========

    def compare_quotes(self, request_id: str) -> List[Dict[str, Any]]:
        """比较某个询价的所有报价"""
        if request_id not in self.quote_requests:
            return []

        record = self.quote_requests[request_id]

        comparisons = []
        for response in record.responses:
            evaluation = self._evaluate_quote(response, record)
            comparisons.append(
                {
                    "supplier_id": response.get("supplier_id"),
                    "unit_price": response.get("unit_price"),
                    "total_price": response.get("total_price"),
                    "delivery_lead_time": response.get("delivery_lead_time"),
                    "valid_until": response.get("valid_until"),
                    "score": evaluation["total_score"],
                    "recommendation": evaluation["recommendation"],
                }
            )

        # 按评分排序
        comparisons.sort(key=lambda x: x["score"], reverse=True)

        return comparisons

    def get_best_quote(self, request_id: str) -> Optional[Dict[str, Any]]:
        """获取最佳报价"""
        comparisons = self.compare_quotes(request_id)
        if comparisons:
            return comparisons[0]
        return None

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = super().get_stats()
        stats.update(
            {
                "quote_requests_count": len(self.quote_requests),
                "purchase_history_size": len(self.purchase_history),
                "price_predictions_count": len(self.price_predictions),
            }
        )
        return stats


async def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    config_path = os.environ.get("CONFIG_PATH", "config.yaml")
    agent = BuyerAgent(config_path=config_path)

    # 获取端口配置
    http_port = int(os.environ.get("HTTP_PORT", "5102"))
    p2p_port = int(os.environ.get("P2P_PORT", "9102"))
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
        logging.info("Shutting down BuyerAgent...")


if __name__ == "__main__":
    asyncio.run(main())
