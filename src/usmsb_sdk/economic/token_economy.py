"""
TokenEconomy - VIBE Token 经济系统

Phase 2: 经济激励层核心模块。

功能：
- VIBE Token 发行与销毁
- VIBE 作为匹配费
- 生态系统激励
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TokenEventType(Enum):
    """Token 事件类型"""
    MINTED = "minted"         # 铸造
    BURNED = "burned"         # 销毁
    TRANSFERRED = "transferred" # 转账
    STAKED = "staked"         # 质押
    UNSTAKED = "unstaked"     # 解质押
    REWARDED = "rewarded"     # 奖励


@dataclass
class TokenEvent:
    """Token 事件"""
    id: str
    event_type: TokenEventType
    agent_id: str
    amount: float
    balance_after: float
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: dict = field(default_factory=dict)


class TokenEconomy:
    """
    VIBE Token 经济系统
    
    使用方式：
    ```python
    economy = TokenEconomy()
    
    # 铸造 Token
    economy.mint(to="agent_001", amount=100)
    
    # 转账
    economy.transfer(from_="agent_001", to="agent_002", amount=50)
    
    # 销毁
    economy.burn(from_="agent_001", amount=10)
    
    # 余额查询
    balance = economy.get_balance("agent_001")
    ```
    """
    
    # VIBE Token 配置
    TOTAL_SUPPLY = 1_000_000_000  # 10 亿
    INITIAL_SUPPLY = 100_000_000  # 1 亿初始发行
    ANNUAL_INFLATION = 0.05  # 5% 年通胀
    
    # 匹配费比例
    MATCHING_FEE_RATE = 0.01  # 1%
    
    def __init__(self):
        # 余额
        self._balances: dict[str, float] = {}
        
        # 发行总量
        self._total_supply = 0.0
        
        # 事件日志
        self._events: list[TokenEvent] = []
        
        # 质押池
        self._staking_pool: dict[str, tuple[float, float]] = {}  # agent_id -> (amount, unlock_time)
        
        # 激励池
        self._incentive_pool: float = 0.0
    
    def initialize(self, initial_holders: dict[str, float]) -> None:
        """
        初始化经济系统
        
        Args:
            initial_holders: 初始持有者 {agent_id: amount}
        """
        for agent_id, amount in initial_holders.items():
            self.mint(to=agent_id, amount=amount)
        
        self._total_supply = self.INITIAL_SUPPLY
    
    def mint(self, to: str, amount: float) -> bool:
        """
        铸造 Token
        
        Args:
            to: 接收方
            amount: 数量
            
        Returns:
            bool: 是否成功
        """
        if amount <= 0:
            return False
        
        if self._total_supply + amount > self.TOTAL_SUPPLY:
            # 不能超过总量
            amount = self.TOTAL_SUPPLY - self._total_supply
            if amount <= 0:
                return False
        
        # 更新余额
        self._balances[to] = self._balances.get(to, 0) + amount
        self._total_supply += amount
        
        # 记录事件
        self._log_event(
            event_type=TokenEventType.MINTED,
            agent_id=to,
            amount=amount,
            balance_after=self._balances[to]
        )
        
        return True
    
    def burn(self, from_: str, amount: float) -> bool:
        """
        销毁 Token
        
        Args:
            from_: 销毁方
            amount: 数量
            
        Returns:
            bool: 是否成功
        """
        if amount <= 0:
            return False
        
        balance = self._balances.get(from_, 0)
        if balance < amount:
            return False
        
        self._balances[from_] = balance - amount
        self._total_supply -= amount
        
        # 记录事件
        self._log_event(
            event_type=TokenEventType.BURNED,
            agent_id=from_,
            amount=amount,
            balance_after=self._balances[from_]
        )
        
        return True
    
    def transfer(self, from_: str, to: str, amount: float) -> bool:
        """
        转账
        
        Args:
            from_: 转出方
            to: 转入方
            amount: 数量
            
        Returns:
            bool: 是否成功
        """
        if amount <= 0:
            return False
        
        from_balance = self._balances.get(from_, 0)
        if from_balance < amount:
            return False
        
        self._balances[from_] = from_balance - amount
        self._balances[to] = self._balances.get(to, 0) + amount
        
        # 记录事件
        self._log_event(
            event_type=TokenEventType.TRANSFERRED,
            agent_id=from_,
            amount=amount,
            balance_after=self._balances[from_]
        )
        
        return True
    
    def get_balance(self, agent_id: str) -> float:
        """获取余额"""
        return self._balances.get(agent_id, 0.0)
    
    def get_total_supply(self) -> float:
        """获取发行总量"""
        return self._total_supply
    
    def get_circulating_supply(self) -> float:
        """获取流通量（去除质押）"""
        staked = sum(amount for amount, _ in self._staking_pool.values())
        return self._total_supply - staked
    
    def stake(self, agent_id: str, amount: float, lock_days: int = 30) -> bool:
        """
        质押
        
        Args:
            agent_id: 质押方
            amount: 数量
            lock_days: 锁定期（天）
            
        Returns:
            bool: 是否成功
        """
        if amount <= 0:
            return False
        
        balance = self._balances.get(agent_id, 0)
        if balance < amount:
            return False
        
        # 扣除余额
        self._balances[agent_id] = balance - amount
        
        # 加入质押池
        unlock_time = datetime.now().timestamp() + lock_days * 86400
        current_staked, _ = self._staking_pool.get(agent_id, (0, 0))
        self._staking_pool[agent_id] = (current_staked + amount, max(unlock_time, self._staking_pool.get(agent_id, (0, 0))[1]))
        
        # 记录事件
        self._log_event(
            event_type=TokenEventType.STAKED,
            agent_id=agent_id,
            amount=amount,
            balance_after=self._balances.get(agent_id, 0)
        )
        
        return True
    
    def unstake(self, agent_id: str, amount: float | None = None) -> bool:
        """
        解质押
        
        Args:
            agent_id: 解质押方
            amount: 数量（None = 全部）
            
        Returns:
            bool: 是否成功
        """
        if agent_id not in self._staking_pool:
            return False
        
        staked, unlock_time = self._staking_pool[agent_id]
        
        # 检查是否已解锁
        if datetime.now().timestamp() < unlock_time:
            return False
        
        # 解质押数量
        unstake_amount = amount if amount else staked
        unstake_amount = min(unstake_amount, staked)
        
        if unstake_amount <= 0:
            return False
        
        # 更新质押池
        new_staked = staked - unstake_amount
        if new_staked > 0:
            self._staking_pool[agent_id] = (new_staked, unlock_time)
        else:
            del self._staking_pool[agent_id]
        
        # 返还余额
        self._balances[agent_id] = self._balances.get(agent_id, 0) + unstake_amount
        
        # 记录事件
        self._log_event(
            event_type=TokenEventType.UNSTAKED,
            agent_id=agent_id,
            amount=unstake_amount,
            balance_after=self._balances.get(agent_id, 0)
        )
        
        return True
    
    def get_staked_amount(self, agent_id: str) -> float:
        """获取质押数量"""
        if agent_id not in self._staking_pool:
            return 0.0
        return self._staking_pool[agent_id][0]
    
    def calculate_matching_fee(self, order_value: float) -> float:
        """
        计算匹配费
        
        匹配费 = 订单价值 × 1% (VIBE 支付)
        
        Args:
            order_value: 订单价值
            
        Returns:
            float: 匹配费
        """
        return order_value * self.MATCHING_FEE_RATE
    
    def add_to_incentive_pool(self, amount: float) -> None:
        """向激励池添加资金"""
        self._incentive_pool += amount
    
    def distribute_incentive(self, to: str, amount: float) -> bool:
        """分发激励"""
        if self._incentive_pool < amount:
            return False
        
        self._incentive_pool -= amount
        self._balances[to] = self._balances.get(to, 0) + amount
        
        self._log_event(
            event_type=TokenEventType.REWARDED,
            agent_id=to,
            amount=amount,
            balance_after=self._balances.get(to, 0)
        )
        
        return True
    
    def get_incentive_pool(self) -> float:
        """获取激励池余额"""
        return self._incentive_pool
    
    def _log_event(
        self,
        event_type: TokenEventType,
        agent_id: str,
        amount: float,
        balance_after: float
    ) -> None:
        """记录事件"""
        event = TokenEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            agent_id=agent_id,
            amount=amount,
            balance_after=balance_after
        )
        self._events.append(event)
    
    def get_events(
        self,
        agent_id: str | None = None,
        limit: int = 100
    ) -> list[TokenEvent]:
        """获取事件"""
        events = self._events
        if agent_id:
            events = [e for e in events if e.agent_id == agent_id]
        return events[-limit:]
    
    def get_statistics(self) -> dict[str, Any]:
        """获取统计"""
        total_staked = sum(amount for amount, _ in self._staking_pool.values())
        
        return {
            "total_supply": self._total_supply,
            "circulating_supply": self.get_circulating_supply(),
            "total_staked": total_staked,
            "incentive_pool": self._incentive_pool,
            "token_holders": len(self._balances),
            "matching_fee_rate": self.MATCHING_FEE_RATE,
        }
