"""
DynamicNegotiationProtocol - 动态协商协议

Agent 之间动态协商的协议。

核心功能：
- 协商提议
- 多轮谈判
- 资源分配
- 协议达成
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class NegotiationState(Enum):
    """协商状态"""
    PROPOSED = "proposed"           # 已提议
    COUNTERED = "countered"         # 已还价
    ACCEPTED = "accepted"           # 已接受
    REJECTED = "rejected"           # 已拒绝
    EXPIRED = "expired"             # 已过期
    CANCELLED = "cancelled"         # 已取消


class NegotiationRole(Enum):
    """协商角色"""
    INITIATOR = "initiator"       # 发起方
    RESPONDENT = "respondent"      # 响应方


@dataclass
class NegotiationOffer:
    """协商提议"""
    id: str
    initiator_id: str
    respondent_id: str
    offer_type: str  # resource_exchange, capability_sharing, collaboration, etc.
    terms: dict  # 条款内容
    proposed_value: float  # 提议的价值
    state: NegotiationState
    round: int = 1
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    expires_at: float = field(default_factory=lambda: datetime.now().timestamp() + 3600)
    history: list[dict] = field(default_factory=list)  # 协商历史


@dataclass
class NegotiationResult:
    """协商结果"""
    success: bool
    offer_id: str
    final_terms: dict | None
    value_exchanged: float
    created_at: float


class NegotiationEngine:
    """
    协商引擎
    
    使用方式：
    ```python
    engine = NegotiationEngine()
    
    # 发起协商
    offer_id = engine.propose(
        initiator_id="agent_001",
        respondent_id="agent_002",
        offer_type="resource_exchange",
        terms={"resource_a": 50, "resource_b": 30}
    )
    
    # 响应方还价
    engine.counter(offer_id, respondent_id, {"resource_a": 45, "resource_b": 35})
    
    # 发起方接受
    result = engine.accept(offer_id, initiator_id)
    ```
    """
    
    def __init__(self, max_rounds: int = 5):
        self.max_rounds = max_rounds
        
        # 协商存储
        self._offers: dict[str, NegotiationOffer] = {}
        
        # Agent 协商记录
        self._agent_offers: dict[str, list[str]] = {}
    
    def propose(
        self,
        initiator_id: str,
        respondent_id: str,
        offer_type: str,
        terms: dict,
        proposed_value: float = 0.0,
        expires_in: float = 3600.0
    ) -> str:
        """
        发起协商提议
        
        Args:
            initiator_id: 发起方 ID
            respondent_id: 响应方 ID
            offer_type: 提议类型
            terms: 条款
            proposed_value: 提议价值
            expires_in: 过期时间（秒）
            
        Returns:
            str: 提议 ID
        """
        offer_id = str(uuid.uuid4())
        
        offer = NegotiationOffer(
            id=offer_id,
            initiator_id=initiator_id,
            respondent_id=respondent_id,
            offer_type=offer_type,
            terms=terms,
            proposed_value=proposed_value,
            state=NegotiationState.PROPOSED,
            history=[{
                "round": 0,
                "action": "proposed",
                "agent_id": initiator_id,
                "terms": terms,
                "timestamp": datetime.now().timestamp()
            }]
        )
        offer.expires_at = datetime.now().timestamp() + expires_in
        
        self._offers[offer_id] = offer
        
        if initiator_id not in self._agent_offers:
            self._agent_offers[initiator_id] = []
        self._agent_offers[initiator_id].append(offer_id)
        
        return offer_id
    
    def counter(
        self,
        offer_id: str,
        counterer_id: str,
        counter_terms: dict,
        counter_value: float | None = None
    ) -> bool:
        """
        还价
        
        Args:
            offer_id: 提议 ID
            counterer_id: 还价方 ID
            counter_terms: 还价条款
            counter_value: 还价价值（可选）
            
        Returns:
            bool: 是否成功
        """
        if offer_id not in self._offers:
            return False
        
        offer = self._offers[offer_id]
        
        # 检查状态
        if offer.state not in [NegotiationState.PROPOSED, NegotiationState.COUNTERED]:
            return False
        
        # 检查轮次
        if offer.round >= self.max_rounds:
            offer.state = NegotiationState.EXPIRED
            return False
        
        # 确定还价方角色
        if counterer_id == offer.initiator_id:
            # 发起方还价（接受对方还价）
            pass
        elif counterer_id == offer.respondent_id:
            # 响应方还价
            pass
        else:
            return False
        
        # 记录还价
        offer.terms = counter_terms
        if counter_value is not None:
            offer.proposed_value = counter_value
        offer.state = NegotiationState.COUNTERED
        offer.round += 1
        offer.history.append({
            "round": offer.round,
            "action": "countered",
            "agent_id": counterer_id,
            "terms": counter_terms,
            "value": counter_value,
            "timestamp": datetime.now().timestamp()
        })
        
        return True
    
    def accept(self, offer_id: str, accepter_id: str) -> NegotiationResult:
        """
        接受提议
        
        Args:
            offer_id: 提议 ID
            accepter_id: 接受方 ID
            
        Returns:
            NegotiationResult: 协商结果
        """
        if offer_id not in self._offers:
            return NegotiationResult(
                success=False,
                offer_id=offer_id,
                final_terms=None,
                value_exchanged=0.0
            )
        
        offer = self._offers[offer_id]
        
        # 检查是否是参与方
        if accepter_id not in [offer.initiator_id, offer.respondent_id]:
            return NegotiationResult(
                success=False,
                offer_id=offer_id,
                final_terms=None,
                value_exchanged=0.0
            )
        
        # 检查状态
        if offer.state not in [NegotiationState.PROPOSED, NegotiationState.COUNTERED]:
            return NegotiationResult(
                success=False,
                offer_id=offer_id,
                final_terms=None,
                value_exchanged=0.0
            )
        
        # 检查过期
        if datetime.now().timestamp() > offer.expires_at:
            offer.state = NegotiationState.EXPIRED
            return NegotiationResult(
                success=False,
                offer_id=offer_id,
                final_terms=None,
                value_exchanged=0.0
            )
        
        # 接受
        offer.state = NegotiationState.ACCEPTED
        offer.history.append({
            "round": offer.round,
            "action": "accepted",
            "agent_id": accepter_id,
            "timestamp": datetime.now().timestamp()
        })
        
        return NegotiationResult(
            success=True,
            offer_id=offer_id,
            final_terms=offer.terms.copy(),
            value_exchanged=offer.proposed_value,
            created_at=datetime.now().timestamp()
        )
    
    def reject(self, offer_id: str, rejecter_id: str, reason: str = "") -> bool:
        """
        拒绝提议
        
        Args:
            offer_id: 提议 ID
            rejecter_id: 拒绝方 ID
            reason: 拒绝原因
            
        Returns:
            bool: 是否成功
        """
        if offer_id not in self._offers:
            return False
        
        offer = self._offers[offer_id]
        
        if rejecter_id not in [offer.initiator_id, offer.respondent_id]:
            return False
        
        offer.state = NegotiationState.REJECTED
        offer.history.append({
            "round": offer.round,
            "action": "rejected",
            "agent_id": rejecter_id,
            "reason": reason,
            "timestamp": datetime.now().timestamp()
        })
        
        return True
    
    def cancel(self, offer_id: str, canceller_id: str) -> bool:
        """取消提议"""
        if offer_id not in self._offers:
            return False
        
        offer = self._offers[offer_id]
        
        if canceller_id != offer.initiator_id:
            return False  # 只有发起方可以取消
        
        offer.state = NegotiationState.CANCELLED
        return True
    
    def get_offer(self, offer_id: str) -> NegotiationOffer | None:
        """获取提议"""
        return self._offers.get(offer_id)
    
    def get_active_offers(self, agent_id: str) -> list[NegotiationOffer]:
        """获取 Agent 的活跃提议"""
        active = []
        for offer in self._offers.values():
            if offer.state in [NegotiationState.PROPOSED, NegotiationState.COUNTERED]:
                if agent_id in [offer.initiator_id, offer.respondent_id]:
                    if datetime.now().timestamp() < offer.expires_at:
                        active.append(offer)
        return active
    
    def get_negotiation_history(self, agent_id: str) -> list[dict]:
        """获取 Agent 的协商历史"""
        history = []
        for offer in self._agent_offers.get(agent_id, []):
            offer_obj = self._offers.get(offer)
            if offer_obj:
                history.append({
                    "offer_id": offer,
                    "type": offer_obj.offer_type,
                    "state": offer_obj.state.value,
                    "final_terms": offer_obj.terms if offer_obj.state == NegotiationState.ACCEPTED else None,
                    "history": offer_obj.history
                })
        return history


class DynamicNegotiationProtocol:
    """
    动态协商协议
    
    整合协商引擎，提供高级协商功能。
    
    使用方式：
    ```python
    protocol = DynamicNegotiationProtocol()
    
    # 发起资源交换协商
    result = protocol.negotiate_resource_exchange(
        initiator="a1",
        respondent="a2",
        resources_a={"compute": 50},
        resources_b={"storage": 100}
    )
    ```
    """
    
    def __init__(self):
        self.engine = NegotiationEngine()
    
    def negotiate_resource_exchange(
        self,
        initiator_id: str,
        respondent_id: str,
        resources_offered: dict[str, float],
        resources_requested: dict[str, float]
    ) -> NegotiationResult:
        """
        资源交换协商
        
        Args:
            initiator_id: 发起方
            respondent_id: 响应方
            resources_offered: 提供的资源
            resources_requested: 请求的资源
            
        Returns:
            NegotiationResult: 协商结果
        """
        terms = {
            "type": "resource_exchange",
            "offered": resources_offered,
            "requested": resources_requested
        }
        
        # 计算总价值
        total_value = sum(resources_offered.values()) + sum(resources_requested.values())
        
        offer_id = self.engine.propose(
            initiator_id=initiator_id,
            respondent_id=respondent_id,
            offer_type="resource_exchange",
            terms=terms,
            proposed_value=total_value / 2
        )
        
        # 自动接受（简化版本）
        return self.engine.accept(offer_id, respondent_id)
    
    def negotiate_capability_sharing(
        self,
        initiator_id: str,
        respondent_id: str,
        capabilities_to_share: list[str],
        duration: float = 3600.0
    ) -> NegotiationResult:
        """
        能力共享协商
        """
        terms = {
            "type": "capability_sharing",
            "capabilities": capabilities_to_share,
            "duration": duration
        }
        
        offer_id = self.engine.propose(
            initiator_id=initiator_id,
            respondent_id=respondent_id,
            offer_type="capability_sharing",
            terms=terms,
            proposed_value=len(capabilities_to_share) * 10.0
        )
        
        return self.engine.accept(offer_id, respondent_id)
    
    def negotiate_collaboration(
        self,
        initiator_id: str,
        respondent_id: str,
        task_description: str,
        effort_split: dict[str, float],
        reward_split: dict[str, float]
    ) -> NegotiationResult:
        """
        协作协商
        """
        terms = {
            "type": "collaboration",
            "task": task_description,
            "effort_split": effort_split,
            "reward_split": reward_split
        }
        
        total_reward = sum(reward_split.values())
        
        offer_id = self.engine.propose(
            initiator_id=initiator_id,
            respondent_id=respondent_id,
            offer_type="collaboration",
            terms=terms,
            proposed_value=total_reward
        )
        
        return self.engine.accept(offer_id, respondent_id)
    
    def get_pending_negotiations(self, agent_id: str) -> list[NegotiationOffer]:
        """获取待处理的协商"""
        return self.engine.get_active_offers(agent_id)
    
    def get_negotiation_history(self, agent_id: str) -> list[dict]:
        """获取协商历史"""
        return self.engine.get_negotiation_history(agent_id)
