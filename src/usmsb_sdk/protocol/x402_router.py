"""
x402 Router - 机器间微支付路由

x402 = HTTP 402 Payment Header
用于 Agent 之间的价值流转。

功能：
- 支付请求构建
- 支付处理
- 支付验证
- 退款处理
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class PaymentStatus(Enum):
    """支付状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class Currency(Enum):
    """支持的货币"""
    USDC = "USDC"
    VIBE = "VIBE"
    ETH = "ETH"
    BTC = "BTC"


@dataclass
class PaymentRequest:
    """支付请求"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_address: str = ""
    to_address: str = ""
    amount: float = 0.0
    currency: Currency = Currency.USDC
    memo: str = ""
    max_fee: float = 0.01  # 最大手续费
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: dict = field(default_factory=dict)


@dataclass
class PaymentResult:
    """支付结果"""
    success: bool
    payment_id: str
    transaction_hash: str | None = None
    fee_paid: float = 0.0
    amount_paid: float = 0.0
    error: str | None = None
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class PaymentRecord:
    """支付记录"""
    id: str
    request: PaymentRequest
    result: PaymentResult | None
    status: PaymentStatus
    retry_count: int = 0
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())


class x402Router:
    """
    x402 支付路由
    
    使用方式：
    ```python
    router = x402Router()
    
    # 创建支付请求
    request = router.create_payment(
        from_address="0x123...",
        to_address="0x456...",
        amount=10.0,
        currency=Currency.USDC,
        memo="Service payment"
    )
    
    # 处理支付
    result = router.process_payment(request)
    
    # 验证支付
    verified = router.verify_payment(result.transaction_hash)
    ```
    """
    
    def __init__(self):
        # 支付记录
        self._payments: dict[str, PaymentRecord] = {}
        
        # 手续费率
        self._fee_rates = {
            Currency.USDC: 0.001,   # 0.1%
            Currency.VIBE: 0.001,   # 0.1%
            Currency.ETH: 0.002,    # 0.2%
            Currency.BTC: 0.002,    # 0.2%
        }
        
        # 最小支付金额
        self._min_amounts = {
            Currency.USDC: 0.01,
            Currency.VIBE: 1.0,
            Currency.ETH: 0.001,
            Currency.BTC: 0.0001,
        }
    
    def create_payment(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        currency: Currency,
        memo: str = "",
        max_fee: float | None = None
    ) -> PaymentRequest:
        """
        创建支付请求
        
        Args:
            from_address: 发送方地址
            to_address: 接收方地址
            amount: 金额
            currency: 币种
            memo: 备注
            max_fee: 最大手续费
            
        Returns:
            PaymentRequest: 支付请求
        """
        if max_fee is None:
            max_fee = amount * self._fee_rates.get(currency, 0.001)
        
        request = PaymentRequest(
            from_address=from_address,
            to_address=to_address,
            amount=amount,
            currency=currency,
            memo=memo,
            max_fee=max_fee
        )
        
        return request
    
    def process_payment(self, request: PaymentRequest) -> PaymentResult:
        """
        处理支付
        
        Args:
            request: 支付请求
            
        Returns:
            PaymentResult: 支付结果
        """
        # 验证金额
        min_amount = self._min_amounts.get(request.currency, 0.0)
        if request.amount < min_amount:
            return PaymentResult(
                success=False,
                payment_id=request.id,
                error=f"Amount {request.amount} below minimum {min_amount}"
            )
        
        # 计算手续费
        fee = request.amount * self._fee_rates.get(request.currency, 0.001)
        if fee > request.max_fee:
            return PaymentResult(
                success=False,
                payment_id=request.id,
                error=f"Fee {fee} exceeds max_fee {request.max_fee}"
            )
        
        # 模拟支付处理
        try:
            # 生成交易哈希
            tx_hash = f"0x{uuid.uuid4().hex[:64]}"
            
            result = PaymentResult(
                success=True,
                payment_id=request.id,
                transaction_hash=tx_hash,
                fee_paid=fee,
                amount_paid=request.amount - fee
            )
            
            # 记录支付
            record = PaymentRecord(
                id=request.id,
                request=request,
                result=result,
                status=PaymentStatus.COMPLETED
            )
            self._payments[request.id] = record
            
            return result
            
        except Exception as e:
            return PaymentResult(
                success=False,
                payment_id=request.id,
                error=str(e)
            )
    
    def verify_payment(self, transaction_hash: str) -> bool:
        """
        验证支付
        
        Args:
            transaction_hash: 交易哈希
            
        Returns:
            bool: 是否验证成功
        """
        # 在真实场景中，需要查询区块链确认交易
        # 这里简化处理
        if transaction_hash and transaction_hash.startswith("0x"):
            return True
        return False
    
    def get_payment(self, payment_id: str) -> PaymentRecord | None:
        """获取支付记录"""
        return self._payments.get(payment_id)
    
    def get_payment_by_tx(self, tx_hash: str) -> PaymentRecord | None:
        """通过交易哈希获取支付记录"""
        for record in self._payments.values():
            if record.result and record.result.transaction_hash == tx_hash:
                return record
        return None
    
    def refund_payment(self, payment_id: str) -> PaymentResult:
        """
        退款
        
        Args:
            payment_id: 支付 ID
            
        Returns:
            PaymentResult: 退款结果
        """
        record = self._payments.get(payment_id)
        if not record:
            return PaymentResult(
                success=False,
                payment_id=payment_id,
                error="Payment not found"
            )
        
        if record.status == PaymentStatus.REFUNDED:
            return PaymentResult(
                success=False,
                payment_id=payment_id,
                error="Already refunded"
            )
        
        # 模拟退款
        refund_tx = f"0x{uuid.uuid4().hex[:64]}"
        
        record.status = PaymentStatus.REFUNDED
        record.updated_at = datetime.now().timestamp()
        
        return PaymentResult(
            success=True,
            payment_id=payment_id,
            transaction_hash=refund_tx,
            amount_paid=record.request.amount,
            fee_paid=0.0
        )
    
    def get_fee_rate(self, currency: Currency) -> float:
        """获取手续费率"""
        return self._fee_rates.get(currency, 0.001)
    
    def get_min_amount(self, currency: Currency) -> float:
        """获取最小支付金额"""
        return self._min_amounts.get(currency, 0.0)
    
    def estimate_fee(self, amount: float, currency: Currency) -> float:
        """
        估算手续费
        
        Args:
            amount: 金额
            currency: 币种
            
        Returns:
            float: 预估手续费
        """
        return amount * self._fee_rates.get(currency, 0.001)
    
    def get_payment_stats(self) -> dict[str, Any]:
        """获取支付统计"""
        total = len(self._payments)
        completed = sum(1 for r in self._payments.values() if r.status == PaymentStatus.COMPLETED)
        failed = sum(1 for r in self._payments.values() if r.status == PaymentStatus.FAILED)
        refunded = sum(1 for r in self._payments.values() if r.status == PaymentStatus.REFUNDED)
        
        total_volume = sum(
            r.request.amount for r in self._payments.values()
            if r.status == PaymentStatus.COMPLETED
        )
        
        return {
            "total_payments": total,
            "completed": completed,
            "failed": failed,
            "refunded": refunded,
            "total_volume": total_volume,
        }
