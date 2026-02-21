"""
Supply Chain Demo - Communication Protocols

定义 Agent 之间通信的消息协议。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
import json


class MessageType(Enum):
    """消息类型枚举"""
    # 询价相关
    QUOTE_REQUEST = "quote_request"
    QUOTE_RESPONSE = "quote_response"
    QUOTE_CANCEL = "quote_cancel"

    # 预测相关
    PRICE_PREDICTION = "price_prediction"
    PRICE_QUERY = "price_query"

    # 撮合相关
    MATCH_REQUEST = "match_request"
    MATCH_RESULT = "match_result"
    MATCH_CONFIRM = "match_confirm"
    MATCH_REJECT = "match_reject"

    # 交易相关
    TRANSACTION_CREATE = "transaction_create"
    TRANSACTION_UPDATE = "transaction_update"
    TRANSACTION_COMPLETE = "transaction_complete"

    # 系统相关
    HEARTBEAT = "heartbeat"
    REGISTER = "register"
    DEREGISTER = "deregister"
    ERROR = "error"


class MessagePriority(Enum):
    """消息优先级"""
    LOW = 1
    NORMAL = 5
    HIGH = 8
    URGENT = 10


@dataclass
class BaseMessage:
    """
    基础消息类

    所有 Agent 间通信消息的基类。
    """
    message_type: str
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    priority: int = MessagePriority.NORMAL.value
    sender_id: str = ""
    receiver_id: Optional[str] = None
    correlation_id: Optional[str] = None  # 用于请求-响应关联
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "message_type": self.message_type,
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "priority": self.priority,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseMessage":
        """从字典创建消息"""
        return cls(**data)


@dataclass
class QuoteRequest(BaseMessage):
    """
    询价请求消息

    BuyerAgent 发送给 SupplierAgent 的询价请求。
    """
    message_type: str = MessageType.QUOTE_REQUEST.value
    buyer_id: str = ""
    product_id: str = ""
    product_name: str = ""
    quantity: float = 0.0
    unit: str = "件"
    delivery_date: Optional[str] = None
    delivery_location: str = ""
    requirements: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "buyer_id": self.buyer_id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "unit": self.unit,
            "delivery_date": self.delivery_date,
            "delivery_location": self.delivery_location,
            "requirements": self.requirements,
        })
        return data


@dataclass
class QuoteResponse(BaseMessage):
    """
    报价响应消息

    SupplierAgent 返回给 BuyerAgent 的报价。
    """
    message_type: str = MessageType.QUOTE_RESPONSE.value
    supplier_id: str = ""
    request_id: str = ""  # 对应的 QuoteRequest.message_id
    product_id: str = ""
    product_name: str = ""
    quantity: float = 0.0
    unit_price: float = 0.0
    currency: str = "CNY"
    total_price: float = 0.0
    valid_until: Optional[str] = None
    delivery_lead_time: int = 0  # 交货周期（天）
    terms: Dict[str, Any] = field(default_factory=dict)
    remarks: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "supplier_id": self.supplier_id,
            "request_id": self.request_id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "currency": self.currency,
            "total_price": self.total_price,
            "valid_until": self.valid_until,
            "delivery_lead_time": self.delivery_lead_time,
            "terms": self.terms,
            "remarks": self.remarks,
        })
        return data

    def calculate_total(self) -> float:
        """计算总价"""
        self.total_price = self.quantity * self.unit_price
        return self.total_price


@dataclass
class PricePredictionItem:
    """单个价格预测项"""
    date: str
    price: float
    confidence: float  # 置信度 0-1


@dataclass
class PricePrediction(BaseMessage):
    """
    价格预测消息

    PredictorAgent 提供的价格预测结果。
    """
    message_type: str = MessageType.PRICE_PREDICTION.value
    predictor_id: str = ""
    product_id: str = ""
    product_name: str = ""
    current_price: float = 0.0
    currency: str = "CNY"
    predicted_prices: List[Dict[str, Any]] = field(default_factory=list)
    trend: str = "stable"  # up, down, stable
    trend_strength: float = 0.0  # 趋势强度 -1 到 1
    recommendation: str = ""
    analysis_factors: List[str] = field(default_factory=list)
    prediction_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "predictor_id": self.predictor_id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "current_price": self.current_price,
            "currency": self.currency,
            "predicted_prices": self.predicted_prices,
            "trend": self.trend,
            "trend_strength": self.trend_strength,
            "recommendation": self.recommendation,
            "analysis_factors": self.analysis_factors,
            "prediction_confidence": self.prediction_confidence,
        })
        return data


@dataclass
class MatchResult(BaseMessage):
    """
    撮合结果消息

    MatchAgent 产生的买卖撮合结果。
    """
    message_type: str = MessageType.MATCH_RESULT.value
    match_id: str = field(default_factory=lambda: f"match_{uuid.uuid4().hex[:8]}")
    buyer_id: str = ""
    supplier_id: str = ""
    product_id: str = ""
    product_name: str = ""
    requested_quantity: float = 0.0
    matched_quantity: float = 0.0
    original_price: float = 0.0
    matched_price: float = 0.0  # 撮合后的价格
    total_amount: float = 0.0
    status: str = "pending"  # pending, confirmed, rejected, completed, cancelled
    valid_until: Optional[str] = None
    match_score: float = 0.0  # 撮合匹配度 0-1
    match_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "match_id": self.match_id,
            "buyer_id": self.buyer_id,
            "supplier_id": self.supplier_id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "requested_quantity": self.requested_quantity,
            "matched_quantity": self.matched_quantity,
            "original_price": self.original_price,
            "matched_price": self.matched_price,
            "total_amount": self.total_amount,
            "status": self.status,
            "valid_until": self.valid_until,
            "match_score": self.match_score,
            "match_reasons": self.match_reasons,
        })
        return data

    def calculate_total(self) -> float:
        """计算总金额"""
        self.total_amount = self.matched_quantity * self.matched_price
        return self.total_amount


# 消息工厂函数
def create_message(message_type: MessageType, **kwargs) -> BaseMessage:
    """
    根据消息类型创建消息实例

    Args:
        message_type: 消息类型枚举
        **kwargs: 消息属性

    Returns:
        消息实例
    """
    message_classes = {
        MessageType.QUOTE_REQUEST: QuoteRequest,
        MessageType.QUOTE_RESPONSE: QuoteResponse,
        MessageType.PRICE_PREDICTION: PricePrediction,
        MessageType.MATCH_RESULT: MatchResult,
    }

    cls = message_classes.get(message_type, BaseMessage)
    return cls(**kwargs)


def parse_message(data: Dict[str, Any]) -> BaseMessage:
    """
    解析消息字典为对应的消息对象

    Args:
        data: 消息字典

    Returns:
        消息对象
    """
    message_type = data.get("message_type", "")

    type_to_class = {
        MessageType.QUOTE_REQUEST.value: QuoteRequest,
        MessageType.QUOTE_RESPONSE.value: QuoteResponse,
        MessageType.PRICE_PREDICTION.value: PricePrediction,
        MessageType.MATCH_RESULT.value: MatchResult,
    }

    cls = type_to_class.get(message_type, BaseMessage)
    return cls(**data)
