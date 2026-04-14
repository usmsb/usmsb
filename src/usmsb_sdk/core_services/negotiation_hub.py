"""
NegotiationHub - 谈判中心

USMSB 核心服务之一。
管理任务谈判和合约生成。

功能：
- 谈判发起和管理
- 多轮谈判
- 合约生成
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class NegotiationStatus(Enum):
    """谈判状态"""
    PROPOSED = "proposed"       # 已提议
    COUNTERED = "countered"     # 已还价
    ACCEPTED = "accepted"        # 已接受
    REJECTED = "rejected"       # 已拒绝
    EXPIRED = "expired"         # 已过期
    CANCELLED = "cancelled"     # 已取消


@dataclass
class NegotiationTerm:
    """谈判条款"""
    type: str  # price, timeline, scope, quality, payment
    value: Any
    description: str = ""


@dataclass
class Negotiation:
    """谈判"""
    id: str
    task_id: str
    buyer_id: str
    seller_id: str
    status: NegotiationStatus
    terms: list[NegotiationTerm] = field(default_factory=list)
    current_round: int = 1
    max_rounds: int = 5
    history: list[dict] = field(default_factory=list)  # 谈判历史
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())
    expires_at: float | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Contract:
    """合约"""
    id: str
    negotiation_id: str
    task_id: str
    buyer_id: str
    seller_id: str
    terms: dict  # 合约条款
    total_price: float
    currency: str = "VIBE"
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    status: str = "active"  # active, completed, disputed, cancelled
    metadata: dict = field(default_factory=dict)


class NegotiationHub:
    """
    谈判中心
    
    使用方式：
    ```python
    hub = NegotiationHub()
    
    # 发起谈判
    neg_id = hub.start_negotiation(
        task_id="task_001",
        buyer_id="agent_buyer",
        seller_id="agent_seller",
        initial_terms=[NegotiationTerm(type="price", value=100)]
    )
    
    # 还价
    hub.counter(neg_id, [NegotiationTerm(type="price", value=90)])
    
    # 接受
    contract = hub.accept(neg_id)
    ```
    """
    
    def __init__(self):
        self._negotiations: dict[str, Negotiation] = {}
        self._contracts: dict[str, Contract] = {}
    
    def start_negotiation(
        self,
        task_id: str,
        buyer_id: str,
        seller_id: str,
        initial_terms: list[NegotiationTerm],
        expires_in: float = 3600.0  # 1 hour
    ) -> str:
        """
        发起谈判
        
        Args:
            task_id: 任务 ID
            buyer_id: 买方
            seller_id: 卖方
            initial_terms: 初始条款
            expires_in: 过期时间（秒）
            
        Returns:
            str: 谈判 ID
        """
        neg = Negotiation(
            id=str(uuid.uuid4()),
            task_id=task_id,
            buyer_id=buyer_id,
            seller_id=seller_id,
            status=NegotiationStatus.PROPOSED,
            terms=initial_terms,
            expires_at=datetime.now().timestamp() + expires_in
        )
        
        # 记录历史
        neg.history.append({
            "round": 0,
            "action": "proposed",
            "agent_id": buyer_id,
            "terms": [{"type": t.type, "value": t.value} for t in initial_terms]
        })
        
        self._negotiations[neg.id] = neg
        
        return neg.id
    
    def counter(
        self,
        negotiation_id: str,
        counter_terms: list[NegotiationTerm],
        counterer_id: str
    ) -> bool:
        """
        还价
        
        Args:
            negotiation_id: 谈判 ID
            counter_terms: 还价条款
            counterer_id: 还价方
            
        Returns:
            bool: 是否成功
        """
        neg = self._negotiations.get(negotiation_id)
        if not neg:
            return False
        
        if neg.status not in [NegotiationStatus.PROPOSED, NegotiationStatus.COUNTERED]:
            return False
        
        if neg.current_round >= neg.max_rounds:
            neg.status = NegotiationStatus.EXPIRED
            return False
        
        # 更新条款
        neg.terms = counter_terms
        neg.current_round += 1
        neg.status = NegotiationStatus.COUNTERED
        neg.updated_at = datetime.now().timestamp()
        
        # 记录历史
        neg.history.append({
            "round": neg.current_round,
            "action": "countered",
            "agent_id": counterer_id,
            "terms": [{"type": t.type, "value": t.value} for t in counter_terms]
        })
        
        return True
    
    def accept(self, negotiation_id: str, acceptor_id: str) -> Contract | None:
        """
        接受谈判
        
        Args:
            negotiation_id: 谈判 ID
            acceptor_id: 接受方
            
        Returns:
            Contract 或 None
        """
        neg = self._negotiations.get(negotiation_id)
        if not neg:
            return None
        
        if neg.status not in [NegotiationStatus.PROPOSED, NegotiationStatus.COUNTERED]:
            return None
        
        # 检查过期
        if neg.expires_at and datetime.now().timestamp() > neg.expires_at:
            neg.status = NegotiationStatus.EXPIRED
            return None
        
        # 更新状态
        neg.status = NegotiationStatus.ACCEPTED
        neg.updated_at = datetime.now().timestamp()
        
        # 生成合约
        contract = self._generate_contract(neg)
        self._contracts[contract.id] = contract
        
        # 记录历史
        neg.history.append({
            "round": neg.current_round,
            "action": "accepted",
            "agent_id": acceptor_id
        })
        
        return contract
    
    def reject(self, negotiation_id: str, rejector_id: str, reason: str = "") -> bool:
        """
        拒绝谈判
        
        Args:
            negotiation_id: 谈判 ID
            rejector_id: 拒绝方
            reason: 原因
            
        Returns:
            bool: 是否成功
        """
        neg = self._negotiations.get(negotiation_id)
        if not neg:
            return False
        
        neg.status = NegotiationStatus.REJECTED
        neg.updated_at = datetime.now().timestamp()
        
        # 记录历史
        neg.history.append({
            "round": neg.current_round,
            "action": "rejected",
            "agent_id": rejector_id,
            "reason": reason
        })
        
        return True
    
    def cancel(self, negotiation_id: str, canceller_id: str) -> bool:
        """取消谈判"""
        neg = self._negotiations.get(negotiation_id)
        if not neg:
            return False
        
        # 只有发起方可以取消
        if neg.buyer_id != canceller_id:
            return False
        
        neg.status = NegotiationStatus.CANCELLED
        neg.updated_at = datetime.now().timestamp()
        
        return True
    
    def _generate_contract(self, neg: Negotiation) -> Contract:
        """生成合约"""
        # 提取价格
        total_price = 0.0
        for term in neg.terms:
            if term.type == "price":
                total_price = term.value
                break
        
        # 提取其他条款
        terms_dict = {}
        for term in neg.terms:
            terms_dict[term.type] = {
                "value": term.value,
                "description": term.description
            }
        
        contract = Contract(
            id=str(uuid.uuid4()),
            negotiation_id=neg.id,
            task_id=neg.task_id,
            buyer_id=neg.buyer_id,
            seller_id=neg.seller_id,
            terms=terms_dict,
            total_price=total_price
        )
        
        return contract
    
    def get_negotiation(self, negotiation_id: str) -> Negotiation | None:
        """获取谈判"""
        return self._negotiations.get(negotiation_id)
    
    def get_contract(self, contract_id: str) -> Contract | None:
        """获取合约"""
        return self._contracts.get(contract_id)
    
    def get_active_negotiations(self, agent_id: str) -> list[Negotiation]:
        """获取 Agent 的活跃谈判"""
        result = []
        for neg in self._negotiations.values():
            if neg.status in [NegotiationStatus.PROPOSED, NegotiationStatus.COUNTERED]:
                if agent_id in [neg.buyer_id, neg.seller_id]:
                    result.append(neg)
        return result
    
    def get_statistics(self) -> dict[str, Any]:
        """获取统计"""
        total_negs = len(self._negotiations)
        total_contracts = len(self._contracts)
        
        neg_by_status = {}
        for neg in self._negotiations.values():
            status = neg.status.value
            neg_by_status[status] = neg_by_status.get(status, 0) + 1
        
        total_volume = sum(c.total_price for c in self._contracts.values())
        
        return {
            "total_negotiations": total_negs,
            "total_contracts": total_contracts,
            "negotiations_by_status": neg_by_status,
            "total_contract_volume": total_volume,
        }
