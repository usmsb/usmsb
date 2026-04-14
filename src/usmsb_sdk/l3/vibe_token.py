"""
VIBE Token 管理模块

VIBE Token 是 USMSB 硅基文明的经济基础。
所有价值流转都通过 VIBE Token 进行结算。

核心功能：
- 铸造（Mint）：价值创造时铸造新 Token
- 转账（Transfer）：Agent 间 Token 转移
- 销毁（Burn）：手续费、系统扣款
- 余额查询：查询各 Agent 余额
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class VIBEBalance:
    """VIBE 余额记录"""
    agent_id: str
    balance: float = 0.0
    total_earned: float = 0.0
    total_spent: float = 0.0
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())


class VIBEToken:
    """
    VIBE Token 管理器
    
    VIBE Token 总量固定（1,000,000,000），通过挖矿机制释放。
    
    使用方式：
    ```python
    vibe = VIBEToken()
    
    # 铸造 Token 给 Agent
    vibe.mint(to_agent_id="agent_001", amount=100.0)
    
    # 转账
    vibe.transfer(from_agent_id="agent_001", to_agent_id="agent_002", amount=50.0)
    
    # 查询余额
    balance = vibe.get_balance("agent_001")
    ```
    """
    
    # VIBE Token 总供应量
    TOTAL_SUPPLY = 1_000_000_000.0  # 10 亿 VIBE
    
    # 系统保留比例（用于激励、储备等）
    SYSTEM_RESERVE_RATIO = 0.10  # 10% 归系统
    
    def __init__(self):
        # 余额记录：agent_id -> VIBEBalance
        self._balances: dict[str, VIBEBalance] = {}
        
        # 流通量
        self._circulating_supply = 0.0
        
        # 系统储备
        self._system_reserve = 0.0
        
        # 系统地址
        self._system_agent_id = "__SYSTEM__"
    
    def mint(self, to_agent_id: str, amount: float) -> bool:
        """
        铸造新 VIBE Token
        
        只有系统才能铸造 Token。
        铸造时按比例分配：to_agent 获得 90%，系统保留 10%。
        
        Args:
            to_agent_id: 接收者 Agent ID
            amount: 铸造数量
            
        Returns:
            bool: 是否成功
        """
        if amount <= 0:
            return False
        
        # 计算分配
        actual_amount = amount * (1 - self.SYSTEM_RESERVE_RATIO)
        system_amount = amount * self.SYSTEM_RESERVE_RATIO
        
        # 检查总供应量
        if self._circulating_supply + amount > self.TOTAL_SUPPLY:
            # 只铸造到最大供应量
            actual_amount = (self.TOTAL_SUPPLY - self._circulating_supply) * (1 - self.SYSTEM_RESERVE_RATIO)
            if actual_amount <= 0:
                return False
        
        # 更新接收者余额
        if to_agent_id not in self._balances:
            self._balances[to_agent_id] = VIBEBalance(agent_id=to_agent_id)
        
        self._balances[to_agent_id].balance += actual_amount
        self._balances[to_agent_id].total_earned += actual_amount
        self._balances[to_agent_id].updated_at = datetime.now().timestamp()
        
        # 更新系统储备
        self._system_reserve += system_amount
        
        # 更新流通量
        self._circulating_supply += actual_amount + system_amount
        
        return True
    
    def transfer(
        self,
        from_agent_id: str,
        to_agent_id: str,
        amount: float
    ) -> bool:
        """
        转账 VIBE Token
        
        Args:
            from_agent_id: 转出方
            to_agent_id: 转入方
            amount: 数量
            
        Returns:
            bool: 是否成功
        """
        if amount <= 0:
            return False
        
        if from_agent_id not in self._balances:
            return False
        
        if self._balances[from_agent_id].balance < amount:
            return False
        
        # 扣除转出方余额
        self._balances[from_agent_id].balance -= amount
        self._balances[from_agent_id].total_spent += amount
        self._balances[from_agent_id].updated_at = datetime.now().timestamp()
        
        # 增加转入方余额
        if to_agent_id not in self._balances:
            self._balances[to_agent_id] = VIBEBalance(agent_id=to_agent_id)
        
        self._balances[to_agent_id].balance += amount
        self._balances[to_agent_id].total_earned += amount
        self._balances[to_agent_id].updated_at = datetime.now().timestamp()
        
        return True
    
    def burn(self, from_agent_id: str, amount: float) -> bool:
        """
        销毁 VIBE Token
        
        Args:
            from_agent_id: 销毁方
            amount: 数量
            
        Returns:
            bool: 是否成功
        """
        if amount <= 0:
            return False
        
        if from_agent_id not in self._balances:
            return False
        
        if self._balances[from_agent_id].balance < amount:
            return False
        
        # 扣除余额
        self._balances[from_agent_id].balance -= amount
        self._balances[from_agent_id].total_spent += amount
        self._balances[from_agent_id].updated_at = datetime.now().timestamp()
        
        # 减少流通量
        self._circulating_supply -= amount
        
        return True
    
    def get_balance(self, agent_id: str) -> float:
        """
        获取 Agent 的 VIBE 余额
        
        Args:
            agent_id: Agent ID
            
        Returns:
            float: 余额
        """
        if agent_id not in self._balances:
            return 0.0
        return self._balances[agent_id].balance
    
    def get_total_earned(self, agent_id: str) -> float:
        """获取 Agent 的总收入"""
        if agent_id not in self._balances:
            return 0.0
        return self._balances[agent_id].total_earned
    
    def get_total_spent(self, agent_id: str) -> float:
        """获取 Agent 的总支出"""
        if agent_id not in self._balances:
            return 0.0
        return self._balances[agent_id].total_spent
    
    def get_circulating_supply(self) -> float:
        """获取流通量"""
        return self._circulating_supply
    
    def get_total_supply(self) -> float:
        """获取总供应量"""
        return self.TOTAL_SUPPLY
    
    def get_system_reserve(self) -> float:
        """获取系统储备"""
        return self._system_reserve
    
    def apply_transaction_fee(self, amount: float) -> tuple[float, float]:
        """
        计算交易手续费
        
        手续费 = 金额 × 5%
        实际到账 = 金额 - 手续费
        
        Args:
            amount: 交易金额
            
        Returns:
            tuple[float, float]: (手续费, 实际到账)
        """
        fee = amount * 0.05
        actual = amount - fee
        return fee, actual
    
    def get_all_balances(self) -> dict[str, VIBEBalance]:
        """获取所有余额记录"""
        return self._balances.copy()
    
    def get_statistics(self) -> dict[str, Any]:
        """获取 VIBE Token 统计信息"""
        return {
            "total_supply": self.TOTAL_SUPPLY,
            "circulating_supply": self._circulating_supply,
            "system_reserve": self._system_reserve,
            "total_agents": len(self._balances),
            "average_balance": (
                self._circulating_supply / len(self._balances)
                if self._balances else 0.0
            ),
        }
