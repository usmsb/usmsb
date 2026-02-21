"""
SupplierAgent - 供给报价 Agent

提供商品报价，响应询价请求的智能代理。
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
class ProductInventory:
    """商品库存信息"""

    product_id: str
    product_name: str
    base_price: float
    available_quantity: float
    unit: str
    min_order_quantity: int = 1
    max_order_quantity: int = 10000
    lead_time_days: int = 7
    specifications: Dict[str, Any] = field(default_factory=dict)


class SupplierAgent(BaseAgent):
    """
    供给报价 Agent

    主要功能：
    - 管理商品目录和库存
    - 响应询价请求，提供报价
    - 支持批量报价和定制化报价
    - 报价有效期管理
    - 与其他 Agent 进行实际通信
    """

    def __init__(self, config_path: str = "config.yaml"):
        super().__init__(config_path)

        # 商品库存
        self.inventory: Dict[str, ProductInventory] = {}

        # 待处理报价
        self.pending_quotes: Dict[str, Dict[str, Any]] = {}

        # 报价历史
        self.quote_history: List[Dict[str, Any]] = []

        # 加载商品库存
        self._load_inventory()

        # 注册消息处理器
        self._register_handlers()

        logger.info(f"SupplierAgent initialized with {len(self.inventory)} products")

    def _load_inventory(self) -> None:
        """从配置加载商品库存"""
        products_config = self._demo_config.extra.get("products", [])

        for product in products_config:
            inventory_item = ProductInventory(
                product_id=product.get("id", ""),
                product_name=product.get("name", ""),
                base_price=product.get("base_price", 0.0),
                available_quantity=product.get("available_quantity", 1000),
                unit=product.get("unit", "件"),
                min_order_quantity=product.get("min_order_quantity", 1),
                max_order_quantity=product.get("max_order_quantity", 10000),
                lead_time_days=product.get("lead_time_days", 7),
                specifications=product.get("specifications", {}),
            )
            self.inventory[inventory_item.product_id] = inventory_item

        # 如果配置中没有商品，添加默认示例商品
        if not self.inventory:
            self._add_default_products()

    def _add_default_products(self) -> None:
        """添加默认示例商品"""
        default_products = [
            {
                "id": "steel_001",
                "name": "钢板 Q235",
                "base_price": 4500.00,
                "available_quantity": 5000,
                "unit": "吨",
                "min_order_quantity": 10,
                "max_order_quantity": 1000,
                "lead_time_days": 7,
            },
            {
                "id": "steel_002",
                "name": "螺纹钢 HRB400",
                "base_price": 4200.00,
                "available_quantity": 3000,
                "unit": "吨",
                "min_order_quantity": 5,
                "max_order_quantity": 500,
                "lead_time_days": 5,
            },
            {
                "id": "copper_001",
                "name": "铜板 T2",
                "base_price": 68000.00,
                "available_quantity": 200,
                "unit": "吨",
                "min_order_quantity": 1,
                "max_order_quantity": 50,
                "lead_time_days": 14,
            },
        ]

        for product in default_products:
            inventory_item = ProductInventory(**product)
            self.inventory[inventory_item.product_id] = inventory_item

    def _register_handlers(self) -> None:
        """注册消息处理器"""
        self.register_handler("quote_request", self.handle_quote_request)
        self.register_handler("quote_cancel", self.handle_quote_cancel)
        self.register_handler("match_confirm", self.handle_match_confirm)
        self.register_handler("match_reject", self.handle_match_reject)
        self.register_handler("product_inquiry", self.handle_product_inquiry)

    async def on_start(self) -> None:
        """启动时的初始化"""
        # 订阅报价相关主题
        self.subscribe("quote_requests")
        self.subscribe(f"supplier_{self.agent_id}")

        logger.info(f"SupplierAgent {self.name} ready for quotes")

    async def handle_quote_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理询价请求

        Args:
            message: 询价请求消息

        Returns:
            报价响应
        """
        request_id = message.get("message_id", "")
        product_id = message.get("payload", {}).get("product_id") or message.get("product_id")
        quantity = message.get("payload", {}).get("quantity") or message.get("quantity", 0)
        buyer_id = message.get("sender_id")

        logger.info(
            f"Received quote request {request_id} from {buyer_id}: "
            f"product={product_id}, quantity={quantity}"
        )

        # 验证商品是否存在
        if product_id not in self.inventory:
            error_response = self._create_error_response(
                message, f"Product {product_id} not available"
            )
            await self.send_message(
                "error", error_response, receiver_id=buyer_id, correlation_id=request_id
            )
            return error_response

        inventory = self.inventory[product_id]

        # 验证数量范围
        if quantity < inventory.min_order_quantity:
            error_response = self._create_error_response(
                message, f"Minimum order quantity is {inventory.min_order_quantity}"
            )
            await self.send_message(
                "error", error_response, receiver_id=buyer_id, correlation_id=request_id
            )
            return error_response

        max_available = min(inventory.max_order_quantity, inventory.available_quantity)
        if quantity > max_available:
            error_response = self._create_error_response(
                message, f"Maximum available quantity is {max_available}"
            )
            await self.send_message(
                "error", error_response, receiver_id=buyer_id, correlation_id=request_id
            )
            return error_response

        # 计算报价
        quote_response = await self._calculate_quote(message, inventory)

        # 保存待处理报价
        self.pending_quotes[quote_response["message_id"]] = {
            "request": message,
            "response": quote_response,
            "created_at": datetime.utcnow().isoformat(),
        }

        # 添加到历史记录
        self.quote_history.append(
            {
                "type": "quote_sent",
                "quote_id": quote_response["message_id"],
                "request_id": request_id,
                "buyer_id": buyer_id,
                "product_id": product_id,
                "quantity": quantity,
                "price": quote_response["unit_price"],
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # 发送报价响应
        await self.send_message(
            "quote_response", quote_response, receiver_id=buyer_id, correlation_id=request_id
        )

        logger.info(
            f"Quote {quote_response['message_id']} sent to {buyer_id}: "
            f"price={quote_response['unit_price']}, "
            f"total={quote_response['total_price']}"
        )

        return quote_response

    async def _calculate_quote(
        self, request: Dict[str, Any], inventory: ProductInventory
    ) -> Dict[str, Any]:
        """计算报价"""
        payload = request.get("payload", request)
        quantity = payload.get("quantity", 0)
        base_price = inventory.base_price

        # 数量折扣
        discount = self._calculate_quantity_discount(quantity)
        adjusted_price = base_price * (1 - discount)

        # 紧急订单加价
        delivery_date = payload.get("delivery_date")
        if delivery_date:
            urgency_factor = self._calculate_urgency_factor(delivery_date, inventory.lead_time_days)
            adjusted_price *= urgency_factor

        # 计算总价
        total_price = quantity * adjusted_price

        # 设置报价有效期（默认48小时）
        validity_hours = self._demo_config.extra.get("pricing_strategy", {}).get(
            "quote_validity_hours", 48
        )
        valid_until = (datetime.utcnow() + timedelta(hours=validity_hours)).isoformat() + "Z"

        quote_response = {
            "supplier_id": self.agent_id,
            "supplier_name": self.name,
            "request_id": request.get("message_id"),
            "product_id": inventory.product_id,
            "product_name": inventory.product_name,
            "quantity": quantity,
            "unit": inventory.unit,
            "unit_price": round(adjusted_price, 2),
            "currency": "CNY",
            "total_price": round(total_price, 2),
            "discount_applied": f"{discount * 100:.1f}%",
            "valid_until": valid_until,
            "delivery_lead_time": inventory.lead_time_days,
            "available_quantity": inventory.available_quantity,
            "terms": {
                "payment_method": "银行转账",
                "min_order_quantity": inventory.min_order_quantity,
                "warranty": "质保一年",
            },
            "specifications": inventory.specifications,
            "remarks": "感谢您的询价，期待与您合作！",
        }

        return quote_response

    def _calculate_quantity_discount(self, quantity: float) -> float:
        """计算数量折扣"""
        discounts = self._demo_config.extra.get("pricing_strategy", {}).get(
            "quantity_discounts", []
        )

        discount = 0.0
        for tier in discounts:
            if quantity >= tier.get("min_quantity", 0):
                discount = max(discount, tier.get("discount", 0))

        # 默认折扣规则
        if not discounts:
            if quantity >= 500:
                discount = 0.10
            elif quantity >= 200:
                discount = 0.05
            elif quantity >= 100:
                discount = 0.03
            elif quantity >= 50:
                discount = 0.02

        return discount

    def _calculate_urgency_factor(self, delivery_date: str, lead_time: int) -> float:
        """计算紧急订单加价因子"""
        try:
            target_date = datetime.fromisoformat(delivery_date.replace("Z", ""))
            days_until_delivery = (target_date - datetime.utcnow()).days

            if days_until_delivery < lead_time * 0.5:
                return 1.15
            elif days_until_delivery < lead_time * 0.75:
                return 1.10
            elif days_until_delivery < lead_time:
                return 1.05
        except Exception:
            pass

        return 1.0

    async def handle_quote_cancel(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理报价取消请求"""
        payload = message.get("payload", message)
        quote_id = payload.get("quote_id")

        if quote_id in self.pending_quotes:
            del self.pending_quotes[quote_id]
            logger.info(f"Quote {quote_id} cancelled")

            return {
                "message_type": "quote_cancel_ack",
                "status": "success",
                "quote_id": quote_id,
            }

        return {
            "message_type": "quote_cancel_ack",
            "status": "not_found",
            "quote_id": quote_id,
        }

    async def handle_match_confirm(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理撮合确认"""
        payload = message.get("payload", message)
        match_id = payload.get("match_id")
        product_id = payload.get("product_id")
        quantity = payload.get("matched_quantity", 0)

        logger.info(f"Match {match_id} confirmed for product {product_id}, quantity {quantity}")

        # 更新库存
        if product_id in self.inventory:
            self.inventory[product_id].available_quantity -= quantity
            logger.info(
                f"Inventory updated: {product_id} -{quantity}, "
                f"remaining: {self.inventory[product_id].available_quantity}"
            )

        # 添加到历史记录
        self.quote_history.append(
            {
                "type": "match_confirmed",
                "match_id": match_id,
                "product_id": product_id,
                "quantity": quantity,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        return {
            "message_type": "match_confirm_ack",
            "status": "accepted",
            "match_id": match_id,
        }

    async def handle_match_reject(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理撮合拒绝"""
        payload = message.get("payload", message)
        match_id = payload.get("match_id")

        logger.info(f"Match {match_id} rejected")

        return {
            "message_type": "match_reject_ack",
            "status": "acknowledged",
            "match_id": match_id,
        }

    async def handle_product_inquiry(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理商品查询"""
        catalog = self.get_product_catalog()

        return {
            "message_type": "product_catalog",
            "supplier_id": self.agent_id,
            "products": catalog,
            "total_products": len(catalog),
        }

    def get_product_catalog(self) -> List[Dict[str, Any]]:
        """获取商品目录"""
        return [
            {
                "product_id": inv.product_id,
                "product_name": inv.product_name,
                "base_price": inv.base_price,
                "unit": inv.unit,
                "available_quantity": inv.available_quantity,
                "min_order_quantity": inv.min_order_quantity,
                "max_order_quantity": inv.max_order_quantity,
                "lead_time_days": inv.lead_time_days,
                "specifications": inv.specifications,
            }
            for inv in self.inventory.values()
        ]

    def update_inventory(self, product_id: str, quantity_change: float) -> None:
        """更新库存"""
        if product_id in self.inventory:
            self.inventory[product_id].available_quantity += quantity_change
            logger.info(
                f"Inventory updated: {product_id}, change: {quantity_change}, "
                f"new quantity: {self.inventory[product_id].available_quantity}"
            )

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = super().get_stats()
        stats.update(
            {
                "products_count": len(self.inventory),
                "pending_quotes": len(self.pending_quotes),
                "quote_history_size": len(self.quote_history),
            }
        )
        return stats


async def main():
    """主函数"""
    # 设置日志
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # 获取配置路径
    config_path = os.environ.get("CONFIG_PATH", "config.yaml")

    # 创建并运行 Agent
    agent = SupplierAgent(config_path=config_path)

    # 获取端口配置
    http_port = int(os.environ.get("HTTP_PORT", "5101"))
    p2p_port = int(os.environ.get("P2P_PORT", "9101"))
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
        logging.info("Shutting down SupplierAgent...")


if __name__ == "__main__":
    asyncio.run(main())
