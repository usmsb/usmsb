"""
Supply Chain Demo - Data Models

定义供应链系统中的数据模型。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class MatchStatus(Enum):
    """撮合状态枚举"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProductCategory(Enum):
    """商品类别"""
    RAW_MATERIAL = "raw_material"
    SEMI_FINISHED = "semi_finished"
    FINISHED = "finished"
    EQUIPMENT = "equipment"
    CONSUMABLE = "consumable"


@dataclass
class Product:
    """
    商品模型

    表示供应链中的商品信息。
    """
    id: str = field(default_factory=lambda: f"prod_{uuid.uuid4().hex[:8]}")
    name: str = ""
    category: str = ProductCategory.RAW_MATERIAL.value
    description: str = ""
    specifications: Dict[str, Any] = field(default_factory=dict)
    unit: str = "件"
    base_price: float = 0.0
    currency: str = "CNY"
    min_order_quantity: int = 1
    max_order_quantity: int = 10000
    lead_time_days: int = 7
    quality_standard: str = ""
    tags: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "specifications": self.specifications,
            "unit": self.unit,
            "base_price": self.base_price,
            "currency": self.currency,
            "min_order_quantity": self.min_order_quantity,
            "max_order_quantity": self.max_order_quantity,
            "lead_time_days": self.lead_time_days,
            "quality_standard": self.quality_standard,
            "tags": self.tags,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Product":
        """从字典创建"""
        return cls(**data)


@dataclass
class Supplier:
    """
    供应商模型

    表示供应链中的供应商信息。
    """
    id: str = field(default_factory=lambda: f"sup_{uuid.uuid4().hex[:8]}")
    name: str = ""
    code: str = ""
    contact_person: str = ""
    contact_phone: str = ""
    contact_email: str = ""
    address: str = ""
    location: str = ""
    credit_rating: float = 0.0  # 信用评级 0-5
    products: List[str] = field(default_factory=list)  # 产品 ID 列表
    capabilities: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    payment_terms: List[str] = field(default_factory=list)
    delivery_regions: List[str] = field(default_factory=list)
    is_verified: bool = False
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "contact_person": self.contact_person,
            "contact_phone": self.contact_phone,
            "contact_email": self.contact_email,
            "address": self.address,
            "location": self.location,
            "credit_rating": self.credit_rating,
            "products": self.products,
            "capabilities": self.capabilities,
            "certifications": self.certifications,
            "payment_terms": self.payment_terms,
            "delivery_regions": self.delivery_regions,
            "is_verified": self.is_verified,
            "is_active": self.is_active,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class Buyer:
    """
    采购商模型

    表示供应链中的采购商信息。
    """
    id: str = field(default_factory=lambda: f"buy_{uuid.uuid4().hex[:8]}")
    name: str = ""
    code: str = ""
    contact_person: str = ""
    contact_phone: str = ""
    contact_email: str = ""
    address: str = ""
    location: str = ""
    credit_limit: float = 0.0
    credit_used: float = 0.0
    credit_rating: float = 0.0
    preferred_suppliers: List[str] = field(default_factory=list)
    frequently_purchased: List[str] = field(default_factory=list)  # 常购产品
    payment_methods: List[str] = field(default_factory=list)
    is_verified: bool = False
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def available_credit(self) -> float:
        """可用信用额度"""
        return self.credit_limit - self.credit_used

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "contact_person": self.contact_person,
            "contact_phone": self.contact_phone,
            "contact_email": self.contact_email,
            "address": self.address,
            "location": self.location,
            "credit_limit": self.credit_limit,
            "credit_used": self.credit_used,
            "credit_rating": self.credit_rating,
            "preferred_suppliers": self.preferred_suppliers,
            "frequently_purchased": self.frequently_purchased,
            "payment_methods": self.payment_methods,
            "is_verified": self.is_verified,
            "is_active": self.is_active,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class PriceHistory:
    """
    价格历史记录

    用于价格预测和市场分析。
    """
    id: str = field(default_factory=lambda: f"ph_{uuid.uuid4().hex[:8]}")
    product_id: str = ""
    supplier_id: Optional[str] = None
    price: float = 0.0
    currency: str = "CNY"
    quantity: float = 0.0
    unit: str = ""
    transaction_type: str = "quote"  # quote, transaction, market
    source: str = ""  # 数据来源
    region: str = ""
    recorded_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "product_id": self.product_id,
            "supplier_id": self.supplier_id,
            "price": self.price,
            "currency": self.currency,
            "quantity": self.quantity,
            "unit": self.unit,
            "transaction_type": self.transaction_type,
            "source": self.source,
            "region": self.region,
            "recorded_at": self.recorded_at,
            "metadata": self.metadata,
        }


@dataclass
class Transaction:
    """
    交易记录

    表示已完成的交易。
    """
    id: str = field(default_factory=lambda: f"tx_{uuid.uuid4().hex[:8]}")
    match_id: str = ""
    buyer_id: str = ""
    supplier_id: str = ""
    product_id: str = ""
    product_name: str = ""
    quantity: float = 0.0
    unit: str = ""
    unit_price: float = 0.0
    total_amount: float = 0.0
    currency: str = "CNY"
    status: str = MatchStatus.PENDING.value
    delivery_address: str = ""
    delivery_date: Optional[str] = None
    actual_delivery_date: Optional[str] = None
    payment_status: str = "pending"  # pending, partial, completed
    payment_method: str = ""
    payment_date: Optional[str] = None
    remarks: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def calculate_total(self) -> float:
        """计算总金额"""
        self.total_amount = self.quantity * self.unit_price
        return self.total_amount

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "match_id": self.match_id,
            "buyer_id": self.buyer_id,
            "supplier_id": self.supplier_id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "unit": self.unit,
            "unit_price": self.unit_price,
            "total_amount": self.total_amount,
            "currency": self.currency,
            "status": self.status,
            "delivery_address": self.delivery_address,
            "delivery_date": self.delivery_date,
            "actual_delivery_date": self.actual_delivery_date,
            "payment_status": self.payment_status,
            "payment_method": self.payment_method,
            "payment_date": self.payment_date,
            "remarks": self.remarks,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class AgentRegistry:
    """
    Agent 注册信息

    用于平台管理已注册的 Agent。
    """
    agent_id: str = ""
    agent_type: str = ""  # supplier, buyer, predictor, match
    agent_name: str = ""
    endpoint: str = ""
    capabilities: List[str] = field(default_factory=list)
    status: str = "offline"  # online, offline, busy
    last_heartbeat: Optional[str] = None
    registered_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "agent_name": self.agent_name,
            "endpoint": self.endpoint,
            "capabilities": self.capabilities,
            "status": self.status,
            "last_heartbeat": self.last_heartbeat,
            "registered_at": self.registered_at,
            "metadata": self.metadata,
        }
