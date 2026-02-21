"""
MatchAgent - 交易撮合 Agent

匹配买卖双方，撮合交易的智能代理。
集成真实的协议处理器和消息总线。
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
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
class PendingMatch:
    """待处理撮合"""

    match_id: str
    buyer_id: str
    supplier_id: str
    product_id: str
    request_data: Dict[str, Any]
    quote_data: Dict[str, Any]
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: Optional[str] = None


@dataclass
class MatchScore:
    """撮合评分"""

    total_score: float
    price_score: float
    quantity_score: float
    delivery_score: float
    supplier_score: float
    details: Dict[str, Any] = field(default_factory=dict)


class MatchAgent(BaseAgent):
    """
    交易撮合 Agent

    主要功能：
    - 匹配买卖双方需求
    - 价格协商与优化
    - 交易确认与跟踪
    - 争议处理
    """

    def __init__(self, config_path: str = "config.yaml"):
        super().__init__(config_path)

        # 待处理撮合
        self.pending_matches: Dict[str, PendingMatch] = {}

        # 已完成撮合
        self.completed_matches: List[Dict[str, Any]] = []

        # 询价请求缓存
        self.quote_requests: Dict[str, Dict[str, Any]] = {}

        # 报价响应缓存
        self.quote_responses: Dict[str, List[Dict[str, Any]]] = {}

        # 注册消息处理器
        self._register_handlers()

        logger.info("MatchAgent initialized")

    def _register_handlers(self) -> None:
        """注册消息处理器"""
        self.register_handler("quote_request", self.handle_quote_request)
        self.register_handler("quote_response", self.handle_quote_response)
        self.register_handler("match_request", self.handle_match_request)
        self.register_handler("match_confirm", self.handle_match_confirm)
        self.register_handler("match_reject", self.handle_match_reject)

    async def on_start(self) -> None:
        """启动时的初始化"""
        self.subscribe("matching")
        self.subscribe(f"match_{self.agent_id}")

        # 启动过期检查任务
        validity_config = self._demo_config.extra.get("validity", {})
        interval = validity_config.get("expiry_check_interval", 60)
        task = asyncio.create_task(self._check_expired_matches_loop(interval))
        self._background_tasks.append(task)

        logger.info(f"MatchAgent {self.name} ready for matching")

    async def handle_quote_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理询价请求"""
        payload = message.get("payload", message)
        request_id = payload.get("request_id") or message.get("message_id")
        buyer_id = message.get("sender_id")

        # 保存询价请求
        self.quote_requests[request_id] = {
            **payload,
            "buyer_id": buyer_id,
            "received_at": datetime.utcnow().isoformat(),
        }
        self.quote_responses[request_id] = []

        logger.info(f"Quote request received: {request_id} from {buyer_id}")

        return {
            "status": "received",
            "request_id": request_id,
            "message": "Waiting for quotes",
        }

    async def handle_quote_response(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理报价响应"""
        payload = message.get("payload", message)
        request_id = payload.get("request_id")
        supplier_id = payload.get("supplier_id") or message.get("sender_id")

        if request_id not in self.quote_requests:
            logger.warning(f"Unknown request ID: {request_id}")
            return {"status": "error", "message": "Unknown request"}

        # 保存报价
        quote_data = {
            **payload,
            "supplier_id": supplier_id,
            "received_at": datetime.utcnow().isoformat(),
        }
        self.quote_responses[request_id].append(quote_data)

        logger.info(
            f"Quote response received for {request_id} from {supplier_id}: "
            f"price={payload.get('unit_price')}"
        )

        # 检查是否需要自动撮合
        matching_config = self._demo_config.extra.get("matching", {})
        min_quotes = matching_config.get("min_quotes_to_match", 1)
        auto_match = matching_config.get("auto_match", {})
        auto_enabled = auto_match.get("enabled", True)

        responses = self.quote_responses[request_id]

        if auto_enabled and len(responses) >= min_quotes:
            # 等待一小段时间以收集更多报价
            wait_time = min(matching_config.get("quote_wait_timeout", 30), 5)
            await asyncio.sleep(wait_time)

            # 触发自动撮合
            return await self.auto_match(request_id)

        return {
            "status": "received",
            "request_id": request_id,
            "quotes_received": len(responses),
        }

    async def handle_match_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理手动撮合请求"""
        payload = message.get("payload", message)
        request_id = payload.get("request_id")

        if request_id not in self.quote_requests:
            return {"status": "error", "message": "Request not found"}

        return await self.auto_match(request_id)

    async def auto_match(self, request_id: str) -> Dict[str, Any]:
        """自动撮合"""
        request = self.quote_requests.get(request_id)
        responses = self.quote_responses.get(request_id, [])

        if not request:
            return {"status": "error", "message": "Request not found"}

        if not responses:
            return {"status": "error", "message": "No quotes available"}

        logger.info(f"Starting auto match for request: {request_id}")

        # 评估所有报价
        scored_quotes = []
        for response in responses:
            score = self._evaluate_match(request, response)
            scored_quotes.append((response, score))

        # 按评分排序
        scored_quotes.sort(key=lambda x: x[1].total_score, reverse=True)

        # 选择最佳匹配
        best_quote, best_score = scored_quotes[0]

        # 检查是否达到最低匹配阈值
        matching_config = self._demo_config.extra.get("matching", {})
        min_score = matching_config.get("min_match_score", 0.5)

        if best_score.total_score < min_score:
            return {
                "status": "no_match",
                "message": "No quote meets minimum match criteria",
                "best_score": best_score.total_score,
            }

        # 创建撮合结果
        match_result = await self._create_match_result(request, best_quote, best_score)

        # 保存待处理撮合
        match_id = match_result["match_id"]
        validity_config = self._demo_config.extra.get("validity", {})
        validity_hours = validity_config.get("default_hours", 24)
        expires_at = (datetime.utcnow() + timedelta(hours=validity_hours)).isoformat()

        pending_match = PendingMatch(
            match_id=match_id,
            buyer_id=request.get("buyer_id"),
            supplier_id=best_quote.get("supplier_id"),
            product_id=request.get("product_id"),
            request_data=request,
            quote_data=best_quote,
            status="pending",
            expires_at=expires_at,
        )
        self.pending_matches[match_id] = pending_match

        # 发送撮合结果给买卖双方
        buyer_id = request.get("buyer_id")
        supplier_id = best_quote.get("supplier_id")

        await self.send_message("match_result", match_result, receiver_id=buyer_id)

        await self.send_message("match_result", match_result, receiver_id=supplier_id)

        # 广播撮合结果
        await self.broadcast("match_result", match_result)

        logger.info(
            f"Match created: {match_id}, buyer={buyer_id}, "
            f"supplier={supplier_id}, score={best_score.total_score:.2f}"
        )

        return match_result

    def _evaluate_match(self, request: Dict[str, Any], quote: Dict[str, Any]) -> MatchScore:
        """评估撮合匹配度"""
        matching_config = self._demo_config.extra.get("matching", {})
        weights = matching_config.get(
            "score_weights",
            {
                "price": 0.4,
                "quantity": 0.2,
                "delivery": 0.25,
                "supplier": 0.15,
            },
        )

        # 价格评分
        price_score = self._calculate_price_score(request, quote)

        # 数量评分
        quantity_score = self._calculate_quantity_score(request, quote)

        # 交货时间评分
        delivery_score = self._calculate_delivery_score(request, quote)

        # 供应商评分
        supplier_score = self._calculate_supplier_score(quote)

        # 计算总分
        total_score = (
            price_score * weights.get("price", 0.4)
            + quantity_score * weights.get("quantity", 0.2)
            + delivery_score * weights.get("delivery", 0.25)
            + supplier_score * weights.get("supplier", 0.15)
        )

        return MatchScore(
            total_score=total_score,
            price_score=price_score,
            quantity_score=quantity_score,
            delivery_score=delivery_score,
            supplier_score=supplier_score,
            details={
                "weights": weights,
                "price_diff_percent": self._calculate_price_diff(request, quote),
            },
        )

    def _calculate_price_score(self, request: Dict[str, Any], quote: Dict[str, Any]) -> float:
        """计算价格评分"""
        quoted_price = quote.get("unit_price", 0)
        target_price = request.get("requirements", {}).get("target_price", quoted_price * 1.1)

        if target_price <= 0:
            return 0.5

        price_ratio = quoted_price / target_price

        if price_ratio <= 0.8:
            return 1.0
        elif price_ratio <= 0.9:
            return 0.9
        elif price_ratio <= 1.0:
            return 0.8
        elif price_ratio <= 1.1:
            return 0.6
        elif price_ratio <= 1.2:
            return 0.4
        else:
            return 0.2

    def _calculate_quantity_score(self, request: Dict[str, Any], quote: Dict[str, Any]) -> float:
        """计算数量评分"""
        requested_qty = request.get("quantity", 0)
        quoted_qty = quote.get("quantity", requested_qty)

        if quoted_qty >= requested_qty:
            return 1.0
        elif quoted_qty >= requested_qty * 0.9:
            return 0.8
        elif quoted_qty >= requested_qty * 0.7:
            return 0.6
        elif quoted_qty >= requested_qty * 0.5:
            return 0.4
        else:
            return 0.2

    def _calculate_delivery_score(self, request: Dict[str, Any], quote: Dict[str, Any]) -> float:
        """计算交货时间评分"""
        delivery_date = request.get("delivery_date")
        lead_time = quote.get("delivery_lead_time", 7)

        if not delivery_date:
            return 0.7

        try:
            target_date = datetime.fromisoformat(delivery_date.replace("Z", ""))
            days_until = max((target_date - datetime.utcnow()).days, 1)

            if lead_time <= days_until * 0.5:
                return 1.0
            elif lead_time <= days_until * 0.75:
                return 0.9
            elif lead_time <= days_until:
                return 0.7
            else:
                return 0.3
        except Exception:
            return 0.5

    def _calculate_supplier_score(self, quote: Dict[str, Any]) -> float:
        """计算供应商评分"""
        supplier_rating = quote.get("supplier_rating", 3.5)
        is_verified = quote.get("supplier_verified", False)

        rating_score = min(supplier_rating / 5.0, 1.0)

        if is_verified:
            rating_score = min(rating_score + 0.1, 1.0)

        return rating_score

    def _calculate_price_diff(self, request: Dict[str, Any], quote: Dict[str, Any]) -> float:
        """计算价格差异百分比"""
        quoted_price = quote.get("unit_price", 0)
        target_price = request.get("requirements", {}).get("target_price", quoted_price)

        if target_price <= 0:
            return 0.0

        return round((quoted_price - target_price) / target_price * 100, 2)

    async def _create_match_result(
        self, request: Dict[str, Any], quote: Dict[str, Any], score: MatchScore
    ) -> Dict[str, Any]:
        """创建撮合结果"""
        match_id = f"match_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        # 计算撮合价格
        original_price = quote.get("unit_price", 0)
        matched_price = self._calculate_matched_price(request, quote, score)

        # 计算总金额
        quantity = min(request.get("quantity", 0), quote.get("quantity", 0))
        total_amount = quantity * matched_price

        # 设置有效期
        validity_config = self._demo_config.extra.get("validity", {})
        validity_hours = validity_config.get("default_hours", 24)
        valid_until = (datetime.utcnow() + timedelta(hours=validity_hours)).isoformat() + "Z"

        # 撮合理由
        match_reasons = self._generate_match_reasons(score)

        match_result = {
            "match_id": match_id,
            "buyer_id": request.get("buyer_id"),
            "supplier_id": quote.get("supplier_id"),
            "product_id": request.get("product_id"),
            "product_name": request.get("product_name", quote.get("product_name", "")),
            "requested_quantity": request.get("quantity"),
            "matched_quantity": quantity,
            "original_price": original_price,
            "matched_price": round(matched_price, 2),
            "total_amount": round(total_amount, 2),
            "currency": quote.get("currency", "CNY"),
            "status": "pending",
            "valid_until": valid_until,
            "match_score": round(score.total_score, 2),
            "match_reasons": match_reasons,
            "score_details": {
                "price_score": round(score.price_score, 2),
                "quantity_score": round(score.quantity_score, 2),
                "delivery_score": round(score.delivery_score, 2),
                "supplier_score": round(score.supplier_score, 2),
            },
            "delivery_lead_time": quote.get("delivery_lead_time"),
            "delivery_date": request.get("delivery_date"),
            "delivery_location": request.get("delivery_location"),
            "created_at": datetime.utcnow().isoformat(),
        }

        return match_result

    def _calculate_matched_price(
        self, request: Dict[str, Any], quote: Dict[str, Any], score: MatchScore
    ) -> float:
        """计算撮合价格"""
        original_price = quote.get("unit_price", 0)

        negotiation_config = self._demo_config.extra.get("negotiation", {})
        bonus = negotiation_config.get("bonus_discount", {})

        # 高匹配度可能有额外折扣
        if score.total_score >= 0.9:
            discount = bonus.get("excellent", 0.02)
        elif score.total_score >= 0.8:
            discount = bonus.get("good", 0.01)
        else:
            discount = 0

        return original_price * (1 - discount)

    def _generate_match_reasons(self, score: MatchScore) -> List[str]:
        """生成撮合理由"""
        reasons = []

        if score.price_score >= 0.8:
            reasons.append("价格具有竞争力")
        if score.quantity_score >= 0.9:
            reasons.append("可满足全部需求量")
        if score.delivery_score >= 0.8:
            reasons.append("交货时间合适")
        if score.supplier_score >= 0.8:
            reasons.append("供应商信用良好")

        if not reasons:
            reasons.append("综合条件最优")

        return reasons

    async def handle_match_confirm(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理撮合确认"""
        payload = message.get("payload", message)
        match_id = payload.get("match_id")
        confirmer_id = message.get("sender_id")

        if match_id not in self.pending_matches:
            return {"status": "error", "message": "Match not found"}

        pending_match = self.pending_matches[match_id]

        logger.info(f"Match {match_id} confirmed by {confirmer_id}")

        # 更新状态
        pending_match.status = "confirmed"

        # 移动到已完成列表
        completed_match = {
            "match_id": match_id,
            "buyer_id": pending_match.buyer_id,
            "supplier_id": pending_match.supplier_id,
            "product_id": pending_match.product_id,
            "request_data": pending_match.request_data,
            "quote_data": pending_match.quote_data,
            "status": "confirmed",
            "confirmed_at": datetime.utcnow().isoformat(),
        }
        self.completed_matches.append(completed_match)

        # 从待处理中移除
        del self.pending_matches[match_id]

        # 广播确认通知
        confirm_notification = {
            "match_id": match_id,
            "status": "confirmed",
            "confirmed_at": datetime.utcnow().isoformat(),
        }

        # 发送给买卖双方
        await self.send_message(
            "match_confirmed", confirm_notification, receiver_id=pending_match.buyer_id
        )
        await self.send_message(
            "match_confirm", confirm_notification, receiver_id=pending_match.supplier_id
        )

        await self.broadcast("match_confirmed", confirm_notification)

        return confirm_notification

    async def handle_match_reject(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理撮合拒绝"""
        payload = message.get("payload", message)
        match_id = payload.get("match_id")
        reason = payload.get("reason", "No reason provided")

        if match_id not in self.pending_matches:
            return {"status": "error", "message": "Match not found"}

        pending_match = self.pending_matches[match_id]
        pending_match.status = "rejected"

        logger.info(f"Match {match_id} rejected: {reason}")

        # 从待处理中移除
        del self.pending_matches[match_id]

        # 广播拒绝通知
        reject_notification = {
            "match_id": match_id,
            "status": "rejected",
            "reason": reason,
            "rejected_at": datetime.utcnow().isoformat(),
        }

        await self.broadcast("match_rejected", reject_notification)

        return reject_notification

    async def _check_expired_matches_loop(self, interval: int) -> None:
        """定期检查过期的撮合"""
        while self._running:
            try:
                await asyncio.sleep(interval)

                if not self._running:
                    break

                now = datetime.utcnow()
                expired_matches = []

                for match_id, match in self.pending_matches.items():
                    if match.expires_at:
                        try:
                            expiry_time = datetime.fromisoformat(match.expires_at.replace("Z", ""))
                            if now > expiry_time:
                                expired_matches.append(match_id)
                        except Exception:
                            pass

                # 处理过期撮合
                for match_id in expired_matches:
                    logger.info(f"Match {match_id} expired")

                    match = self.pending_matches[match_id]
                    match.status = "expired"

                    # 发送过期通知
                    expiry_notification = {
                        "match_id": match_id,
                        "status": "expired",
                        "expired_at": datetime.utcnow().isoformat(),
                    }

                    await self.send_message(
                        "match_expired", expiry_notification, receiver_id=match.buyer_id
                    )
                    await self.send_message(
                        "match_expired", expiry_notification, receiver_id=match.supplier_id
                    )

                    await self.broadcast("match_expired", expiry_notification)

                    del self.pending_matches[match_id]

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error checking expired matches: {e}")
                await asyncio.sleep(60)

    def get_match_status(self, match_id: str) -> Optional[Dict[str, Any]]:
        """获取撮合状态"""
        if match_id in self.pending_matches:
            match = self.pending_matches[match_id]
            return {
                "match_id": match_id,
                "status": match.status,
                "buyer_id": match.buyer_id,
                "supplier_id": match.supplier_id,
                "created_at": match.created_at,
                "expires_at": match.expires_at,
            }

        for completed in self.completed_matches:
            if completed["match_id"] == match_id:
                return {
                    "match_id": match_id,
                    "status": completed["status"],
                    "confirmed_at": completed["confirmed_at"],
                }

        return None

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = super().get_stats()
        stats.update(
            {
                "pending_matches": len(self.pending_matches),
                "completed_matches": len(self.completed_matches),
                "total_requests": len(self.quote_requests),
                "total_responses": sum(len(r) for r in self.quote_responses.values()),
            }
        )
        return stats


async def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    config_path = os.environ.get("CONFIG_PATH", "config.yaml")
    agent = MatchAgent(config_path=config_path)

    # 获取端口配置
    http_port = int(os.environ.get("HTTP_PORT", "5104"))
    p2p_port = int(os.environ.get("P2P_PORT", "9104"))
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
        logging.info("Shutting down MatchAgent...")


if __name__ == "__main__":
    asyncio.run(main())
