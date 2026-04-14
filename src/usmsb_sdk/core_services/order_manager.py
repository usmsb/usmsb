"""
OrderManager - 订单管理

USMSB 核心服务之一。
管理任务的订单生命周期。

功能：
- 订单创建/更新
- 订单状态机
- 履约追踪
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class OrderStatus(Enum):
    """订单状态"""
    CREATED = "created"           # 已创建
    ACCEPTED = "accepted"         # 已接受
    IN_PROGRESS = "in_progress"   # 进行中
    SUBMITTED = "submitted"       # 已提交（待验收）
    COMPLETED = "completed"       # 已完成
    DISPUTED = "disputed"       # 争议中
    CANCELLED = "cancelled"     # 已取消
    EXPIRED = "expired"         # 已过期


class OrderPriority(Enum):
    """订单优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Order:
    """订单"""
    id: str
    task_id: str
    buyer_id: str  # 买方
    seller_id: str  # 卖方
    title: str
    description: str
    price: float
    currency: str = "VIBE"
    status: OrderStatus = OrderStatus.CREATED
    priority: OrderPriority = OrderPriority.NORMAL
    input_data: dict = field(default_factory=dict)
    output_data: dict | None = None
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    accepted_at: float | None = None
    started_at: float | None = None
    submitted_at: float | None = None
    completed_at: float | None = None
    deadline: float | None = None
    metadata: dict = field(default_factory=dict)


class OrderManager:
    """
    订单管理器
    
    使用方式：
    ```python
    manager = OrderManager()
    
    # 创建订单
    order = manager.create_order(
        task_id="task_001",
        buyer_id="agent_buyer",
        seller_id="agent_seller",
        title="数据分析",
        price=100.0
    )
    
    # 更新状态
    manager.accept_order(order.id)
    manager.start_order(order.id)
    manager.complete_order(order.id)
    
    # 获取订单
    order = manager.get_order(order.id)
    ```
    """
    
    def __init__(self):
        # 订单存储
        self._orders: dict[str, Order] = {}
        
        # 订单索引
        self._buyer_index: dict[str, list[str]] = {}  # buyer_id -> [order_id]
        self._seller_index: dict[str, list[str]] = {}  # seller_id -> [order_id]
        self._status_index: dict[OrderStatus, list[str]] = {}
    
    def create_order(
        self,
        task_id: str,
        buyer_id: str,
        seller_id: str,
        title: str,
        description: str = "",
        price: float = 0.0,
        currency: str = "VIBE",
        priority: OrderPriority = OrderPriority.NORMAL,
        input_data: dict | None = None,
        deadline: float | None = None
    ) -> Order:
        """
        创建订单
        
        Args:
            task_id: 任务 ID
            buyer_id: 买方
            seller_id: 卖方
            title: 标题
            description: 描述
            price: 价格
            currency: 货币
            priority: 优先级
            input_data: 输入数据
            deadline: 截止时间
            
        Returns:
            Order: 创建的订单
        """
        order = Order(
            id=str(uuid.uuid4()),
            task_id=task_id,
            buyer_id=buyer_id,
            seller_id=seller_id,
            title=title,
            description=description,
            price=price,
            currency=currency,
            priority=priority,
            input_data=input_data or {},
            deadline=deadline
        )
        
        self._orders[order.id] = order
        
        # 更新索引
        if buyer_id not in self._buyer_index:
            self._buyer_index[buyer_id] = []
        self._buyer_index[buyer_id].append(order.id)
        
        if seller_id not in self._seller_index:
            self._seller_index[seller_id] = []
        self._seller_index[seller_id].append(order.id)
        
        if order.status not in self._status_index:
            self._status_index[order.status] = []
        self._status_index[order.status].append(order.id)
        
        return order
    
    def get_order(self, order_id: str) -> Order | None:
        """获取订单"""
        return self._orders.get(order_id)
    
    def _update_status_index(self, order: Order, old_status: OrderStatus) -> None:
        """更新状态索引"""
        # 移除旧状态
        if old_status in self._status_index:
            if order.id in self._status_index[old_status]:
                self._status_index[old_status].remove(order.id)
        
        # 添加新状态
        if order.status not in self._status_index:
            self._status_index[order.status] = []
        self._status_index[order.status].append(order.id)
    
    def accept_order(self, order_id: str) -> bool:
        """接受订单"""
        order = self._orders.get(order_id)
        if not order or order.status != OrderStatus.CREATED:
            return False
        
        old_status = order.status
        order.status = OrderStatus.ACCEPTED
        order.accepted_at = datetime.now().timestamp()
        
        self._update_status_index(order, old_status)
        return True
    
    def start_order(self, order_id: str) -> bool:
        """开始订单"""
        order = self._orders.get(order_id)
        if not order or order.status != OrderStatus.ACCEPTED:
            return False
        
        old_status = order.status
        order.status = OrderStatus.IN_PROGRESS
        order.started_at = datetime.now().timestamp()
        
        self._update_status_index(order, old_status)
        return True
    
    def submit_order(self, order_id: str, output_data: dict) -> bool:
        """提交订单"""
        order = self._orders.get(order_id)
        if not order or order.status != OrderStatus.IN_PROGRESS:
            return False
        
        old_status = order.status
        order.status = OrderStatus.SUBMITTED
        order.output_data = output_data
        order.submitted_at = datetime.now().timestamp()
        
        self._update_status_index(order, old_status)
        return True
    
    def complete_order(self, order_id: str) -> bool:
        """完成订单"""
        order = self._orders.get(order_id)
        if not order or order.status != OrderStatus.SUBMITTED:
            return False
        
        old_status = order.status
        order.status = OrderStatus.COMPLETED
        order.completed_at = datetime.now().timestamp()
        
        self._update_status_index(order, old_status)
        return True
    
    def dispute_order(self, order_id: str) -> bool:
        """争议订单"""
        order = self._orders.get(order_id)
        if not order or order.status not in [
            OrderStatus.IN_PROGRESS,
            OrderStatus.SUBMITTED
        ]:
            return False
        
        old_status = order.status
        order.status = OrderStatus.DISPUTED
        
        self._update_status_index(order, old_status)
        return True
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        order = self._orders.get(order_id)
        if not order or order.status in [
            OrderStatus.COMPLETED,
            OrderStatus.DISPUTED,
            OrderStatus.CANCELLED
        ]:
            return False
        
        old_status = order.status
        order.status = OrderStatus.CANCELLED
        
        self._update_status_index(order, old_status)
        return True
    
    def get_orders_by_buyer(self, buyer_id: str) -> list[Order]:
        """获取买方的订单"""
        order_ids = self._buyer_index.get(buyer_id, [])
        return [self._orders[oid] for oid in order_ids if oid in self._orders]
    
    def get_orders_by_seller(self, seller_id: str) -> list[Order]:
        """获取卖方的订单"""
        order_ids = self._seller_index.get(seller_id, [])
        return [self._orders[oid] for oid in order_ids if oid in self._orders]
    
    def get_orders_by_status(self, status: OrderStatus) -> list[Order]:
        """按状态获取订单"""
        order_ids = self._status_index.get(status, [])
        return [self._orders[oid] for oid in order_ids if oid in self._orders]
    
    def get_active_orders(self) -> list[Order]:
        """获取活跃订单"""
        active_statuses = [
            OrderStatus.ACCEPTED,
            OrderStatus.IN_PROGRESS,
            OrderStatus.SUBMITTED
        ]
        
        orders = []
        for status in active_statuses:
            orders.extend(self.get_orders_by_status(status))
        
        return orders
    
    def get_statistics(self) -> dict[str, Any]:
        """获取统计"""
        total = len(self._orders)
        
        by_status = {
            status.value: len(order_ids)
            for status, order_ids in self._status_index.items()
        }
        
        total_volume = sum(
            order.price for order in self._orders.values()
            if order.status == OrderStatus.COMPLETED
        )
        
        return {
            "total_orders": total,
            "by_status": by_status,
            "completed_volume": total_volume,
            "currency": "VIBE",
        }
