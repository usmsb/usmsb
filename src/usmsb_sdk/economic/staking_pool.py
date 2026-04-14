"""
StakingPool - 质押池

Phase 2: 经济激励层。

功能：
- 保证金机制
- 锁定期
- 收益分配
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class StakingPosition:
    """质押头寸"""
    id: str
    agent_id: str
    amount: float
    start_time: float
    lock_until: float  # 锁定截止时间
    reward_weight: float = 1.0  # 奖励权重
    claimed_rewards: float = 0.0


class StakingPool:
    """
    质押池
    
    使用方式：
    ```python
    pool = StakingPool()
    
    # 质押
    position_id = pool.stake(agent_id="agent_001", amount=1000, lock_days=30)
    
    # 获取收益
    rewards = pool.calculate_rewards(position_id)
    
    # 领取收益
    pool.claim_rewards(position_id)
    ```
    """
    
    ANNUAL_REWARD_RATE = 0.12  # 12% 年化收益率
    
    def __init__(self):
        self._positions: dict[str, StakingPosition] = {}
        self._total_staked: float = 0.0
        self._reward_pool: float = 0.0
        self._agent_positions: dict[str, list[str]] = {}  # agent_id -> [position_ids]
    
    def stake(
        self,
        agent_id: str,
        amount: float,
        lock_days: int = 30
    ) -> str | None:
        """质押"""
        if amount <= 0:
            return None
        
        position_id = str(uuid.uuid4())
        
        position = StakingPosition(
            id=position_id,
            agent_id=agent_id,
            amount=amount,
            start_time=datetime.now().timestamp(),
            lock_until=datetime.now().timestamp() + lock_days * 86400,
            reward_weight=1.0 + (lock_days / 365) * 0.5  # 锁得越久，权重越高
        )
        
        self._positions[position_id] = position
        self._total_staked += amount
        
        if agent_id not in self._agent_positions:
            self._agent_positions[agent_id] = []
        self._agent_positions[agent_id].append(position_id)
        
        return position_id
    
    def unstake(self, position_id: str) -> float | None:
        """解除质押"""
        position = self._positions.get(position_id)
        if not position:
            return None
        
        # 检查是否已解锁
        if datetime.now().timestamp() < position.lock_until:
            return None
        
        # 计算应得奖励
        rewards = self._calculate_rewards_internal(position)
        
        # 更新状态
        self._total_staked -= position.amount
        del self._positions[position_id]
        
        if position_id in self._agent_positions.get(position.agent_id, []):
            self._agent_positions[position.agent_id].remove(position_id)
        
        return rewards
    
    def calculate_rewards(self, position_id: str) -> float:
        """计算奖励"""
        position = self._positions.get(position_id)
        if not position:
            return 0.0
        return self._calculate_rewards_internal(position)
    
    def _calculate_rewards_internal(self, position: StakingPosition) -> float:
        """内部计算奖励"""
        days_staked = (datetime.now().timestamp() - position.start_time) / 86400
        annual_rewards = position.amount * self.ANNUAL_REWARD_RATE * position.reward_weight
        daily_rewards = annual_rewards / 365
        total_rewards = daily_rewards * days_staked
        
        # 减去已领取的
        return total_rewards - position.claimed_rewards
    
    def claim_rewards(self, position_id: str) -> float:
        """领取奖励"""
        position = self._positions.get(position_id)
        if not position:
            return 0.0
        
        rewards = self._calculate_rewards_internal(position)
        
        if rewards > 0:
            position.claimed_rewards += rewards
            self._reward_pool -= rewards
        
        return rewards
    
    def get_position(self, position_id: str) -> StakingPosition | None:
        return self._positions.get(position_id)
    
    def get_agent_positions(self, agent_id: str) -> list[StakingPosition]:
        position_ids = self._agent_positions.get(agent_id, [])
        return [self._positions[pid] for pid in position_ids if pid in self._positions]
    
    def add_to_reward_pool(self, amount: float) -> None:
        self._reward_pool += amount
    
    def get_statistics(self) -> dict[str, Any]:
        return {
            "total_staked": self._total_staked,
            "reward_pool": self._reward_pool,
            "total_positions": len(self._positions),
            "annual_reward_rate": self.ANNUAL_REWARD_RATE,
        }
