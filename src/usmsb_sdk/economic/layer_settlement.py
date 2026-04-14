"""
LayerSettlement - 分层结算

Phase 2: 经济激励层。

功能：
- VIBE 作为匹配费支付
- 任意 Token 支付
- 分层结算
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SettlementLayer(Enum):
    """结算层级"""
    LAYER_1 = "layer_1"  # 即时结算
    LAYER_2 = "layer_2"  # 标准结算
    LAYER_3 = "layer_3"  # 延迟结算


class SettlementStatus(Enum):
    """结算状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Settlement:
    """结算记录"""
    id: str
    order_id: str
    from_agent: str
    to_agent: str
    amount: float
    currency: str  # VIBE, USDC, ETH, etc.
    layer: SettlementLayer
    status: SettlementStatus
    fee: float = 0.0
    net_amount: float = 0.0
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    completed_at: float | None = None
    metadata: dict = field(default_factory=dict)


class LayerSettlement:
    """
    分层结算
    
    使用方式：
    ```python
    settlement = LayerSettlement()
    
    # 创建结算
    settlement.create_settlement(
        order_id="order_001",
        from_agent="buyer",
        to_agent="seller",
        amount=100.0,
        currency="VIBE",
        layer=SettlementLayer.LAYER_2
    )
    
    # 处理结算
    settlement.process("settlement_001")
    ```
    """
    
    # 各层配置
    LAYER_CONFIG = {
        SettlementLayer.LAYER_1: {
            "fee_rate": 0.02,  # 2%
            "processing_time": 1,  # 1 秒
        },
        SettlementLayer.LAYER_2: {
            "fee_rate": 0.01,  # 1%
            "processing_time": 60,  # 1 分钟
        },
        SettlementLayer.LAYER_3: {
            "fee_rate": 0.005,  # 0.5%
            "processing_time": 3600,  # 1 小时
        },
    }
    
    def __init__(self, token_economy=None):
        self.token_economy = token_economy
        self._settlements: dict[str, Settlement] = {}
        self._order_settlements: dict[str, list[str]] = {}
    
    def create_settlement(
        self,
        order_id: str,
        from_agent: str,
        to_agent: str,
        amount: float,
        currency: str = "VIBE",
        layer: SettlementLayer = SettlementLayer.LAYER_2
    ) -> str:
        """创建结算"""
        config = self.LAYER_CONFIG[layer]
        
        fee = amount * config["fee_rate"]
        net_amount = amount - fee
        
        settlement = Settlement(
            id=str(uuid.uuid4()),
            order_id=order_id,
            from_agent=from_agent,
            to_agent=to_agent,
            amount=amount,
            currency=currency,
            layer=layer,
            status=SettlementStatus.PENDING,
            fee=fee,
            net_amount=net_amount
        )
        
        self._settlements[settlement.id] = settlement
        
        if order_id not in self._order_settlements:
            self._order_settlements[order_id] = []
        self._order_settlements[order_id].append(settlement.id)
        
        return settlement.id
    
    def process(self, settlement_id: str) -> bool:
        """处理结算"""
        settlement = self._settlements.get(settlement_id)
        if not settlement:
            return False
        
        if settlement.status != SettlementStatus.PENDING:
            return False
        
        settlement.status = SettlementStatus.PROCESSING
        
        # 模拟处理
        settlement.status = SettlementStatus.COMPLETED
        settlement.completed_at = datetime.now().timestamp()
        
        return True
    
    def get_settlement(self, settlement_id: str) -> Settlement | None:
        return self._settlements.get(settlement_id)
    
    def get_order_settlements(self, order_id: str) -> list[Settlement]:
        settlement_ids = self._order_settlements.get(order_id, [])
        return [self._settlements[sid] for sid in settlement_ids if sid in self._settlements]
    
    def get_statistics(self) -> dict[str, Any]:
        total = len(self._settlements)
        by_layer = {}
        by_status = {}
        total_volume = 0.0
        
        for s in self._settlements.values():
            by_layer[s.layer.value] = by_layer.get(s.layer.value, 0) + 1
            by_status[s.status.value] = by_status.get(s.status.value, 0) + 1
            total_volume += s.amount
        
        return {
            "total_settlements": total,
            "by_layer": by_layer,
            "by_status": by_status,
            "total_volume": total_volume,
        }
