"""
VIBStaking质押客户端模块

提供VIBStaking合约的交互接口，包括：
- 质押和取消质押
- 奖励领取
- 质押等级查询
- 质押信息查询
"""

from enum import IntEnum
from typing import Dict, Any, Optional
from web3 import Web3

from ..config import BlockchainConfig
from .base import BaseContractClient, TransactionError, ContractError


class StakeTier(IntEnum):
    """质押等级枚举"""
    BRONZE = 0
    SILVER = 1
    GOLD = 2
    PLATINUM = 3

    @classmethod
    def from_name(cls, name: str) -> "StakeTier":
        """从名称获取质押等级"""
        name_map = {
            "BRONZE": cls.BRONZE,
            "SILVER": cls.SILVER,
            "GOLD": cls.GOLD,
            "PLATINUM": cls.PLATINUM,
        }
        return name_map.get(name.upper(), cls.BRONZE)

    @property
    def min_amount(self) -> int:
        """获取该等级的最小质押量"""
        amounts = {
            StakeTier.BRONZE: 100 * 10**18,
            StakeTier.SILVER: 1000 * 10**18,
            StakeTier.GOLD: 5000 * 10**18,
            StakeTier.PLATINUM: 10000 * 10**18,
        }
        return amounts[self]

    @property
    def agent_limit(self) -> int:
        """获取该等级的Agent数量限制"""
        limits = {
            StakeTier.BRONZE: 1,
            StakeTier.SILVER: 3,
            StakeTier.GOLD: 10,
            StakeTier.PLATINUM: 50,
        }
        return limits[self]


class LockPeriod(IntEnum):
    """锁仓期枚举"""
    NONE = 0
    DAYS_30 = 1
    DAYS_90 = 2
    DAYS_180 = 3
    DAYS_365 = 4

    @classmethod
    def from_name(cls, name: str) -> "LockPeriod":
        """从名称获取锁仓期"""
        name_map = {
            "NONE": cls.NONE,
            "30D": cls.DAYS_30,
            "DAYS_30": cls.DAYS_30,
            "90D": cls.DAYS_90,
            "DAYS_90": cls.DAYS_90,
            "180D": cls.DAYS_180,
            "DAYS_180": cls.DAYS_180,
            "365D": cls.DAYS_365,
            "DAYS_365": cls.DAYS_365,
            "1Y": cls.DAYS_365,
            "1YEAR": cls.DAYS_365,
        }
        return name_map.get(name.upper(), cls.NONE)


class VIBStakingClient(BaseContractClient):
    """VIBE质押客户端

    提供VIBE代币质押的完整交互接口，支持多等级、多锁仓期的质押操作。
    """

    # 代币精度
    DECIMALS = 18

    # 质押等级最小质押量
    TIER_MIN_AMOUNTS = [100 * 10**18, 1000 * 10**18, 5000 * 10**18, 10000 * 10**18]

    def __init__(
        self,
        web3_client: Optional[Any] = None,
        config: Optional[BlockchainConfig] = None,
        contract_address: Optional[str] = None,
        abi: Optional[Any] = None,
    ):
        """
        初始化VIBStaking客户端

        Args:
            web3_client: Web3客户端实例
            config: 区块链配置
            contract_address: VIBStaking合约地址
            abi: 合约ABI
        """
        super().__init__(
            web3_client=web3_client,
            config=config,
            contract_address=contract_address,
            abi=abi,
        )

    @property
    def staking_address(self) -> str:
        """获取质押合约地址"""
        if not self.contract_address:
            raise ContractError("Contract address not set")
        return self.w3.to_checksum_address(self.contract_address)

    async def stake(
        self,
        amount: int,
        lock_period: LockPeriod,
        from_address: str,
        private_key: str,
        gas: Optional[int] = None,
    ) -> str:
        """
        质押VIBE（需先approve）

        Args:
            amount: 质押数量（wei单位）
            lock_period: 锁仓期类型
            from_address: 质押者地址
            private_key: 质押者私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = VIBStakingClient(...)
            >>> tx_hash = await client.stake(
            ...     amount=1000 * 10**18,  # 1000 VIBE
            ...     lock_period=LockPeriod.DAYS_90,
            ...     from_address="0x...",
            ...     private_key="..."
            ... )
            >>> print(f"Stake tx: {tx_hash}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        if amount < self.TIER_MIN_AMOUNTS[0]:
            raise TransactionError(
                f"Stake amount below minimum: {self.TIER_MIN_AMOUNTS[0]}"
            )

        checksum_from = self.w3.to_checksum_address(from_address)

        # 构建质押交易
        tx = self.build_contract_transaction(
            self.contract.functions.stake(amount, int(lock_period)),
            from_address=checksum_from,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, private_key)
        return tx_hash

    async def unstake(
        self,
        from_address: str,
        private_key: str,
        gas: Optional[int] = None,
    ) -> str:
        """
        取消质押

        Args:
            from_address: 质押者地址
            private_key: 质押者私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = VIBStakingClient(...)
            >>> tx_hash = await client.unstake(
            ...     from_address="0x...",
            ...     private_key="..."
            ... )
            >>> print(f"Unstake tx: {tx_hash}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_from = self.w3.to_checksum_address(from_address)

        # 构建取消质押交易
        tx = self.build_contract_transaction(
            self.contract.functions.unstake(),
            from_address=checksum_from,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, private_key)
        return tx_hash

    async def claim_reward(
        self,
        from_address: str,
        private_key: str,
        gas: Optional[int] = None,
    ) -> str:
        """
        领取奖励

        Args:
            from_address: 质押者地址
            private_key: 质押者私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = VIBStakingClient(...)
            >>> tx_hash = await client.claim_reward(
            ...     from_address="0x...",
            ...     private_key="..."
            ... )
            >>> print(f"Claim reward tx: {tx_hash}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_from = self.w3.to_checksum_address(from_address)

        # 构建领取奖励交易
        tx = self.build_contract_transaction(
            self.contract.functions.claimReward(),
            from_address=checksum_from,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, private_key)
        return tx_hash

    async def emergency_withdraw(
        self,
        from_address: str,
        private_key: str,
        gas: Optional[int] = None,
    ) -> str:
        """
        紧急提取（放弃所有奖励）

        Args:
            from_address: 质押者地址
            private_key: 质押者私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = VIBStakingClient(...)
            >>> tx_hash = await client.emergency_withdraw(
            ...     from_address="0x...",
            ...     private_key="..."
            ... )
            >>> print(f"Emergency withdraw tx: {tx_hash}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_from = self.w3.to_checksum_address(from_address)

        # 构建紧急提取交易
        tx = self.build_contract_transaction(
            self.contract.functions.emergencyWithdraw(),
            from_address=checksum_from,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, private_key)
        return tx_hash

    async def get_tier(self, address: str) -> StakeTier:
        """
        获取质押等级

        Args:
            address: 用户地址

        Returns:
            质押等级

        Example:
            >>> client = VIBStakingClient(...)
            >>> tier = await client.get_tier("0x...")
            >>> print(f"Tier: {tier.name}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_address = self.w3.to_checksum_address(address)
        try:
            tier = await self.call_contract_function(
                self.contract.functions.getUserTier(checksum_address)
            )
            return StakeTier(int(tier))
        except Exception:
            return StakeTier.BRONZE

    async def get_stake_info(self, address: str) -> Dict[str, Any]:
        """
        获取质押信息

        Args:
            address: 用户地址

        Returns:
            质押信息字典，包含：
            - amount: 质押数量
            - tier: 质押等级
            - lock_period: 锁仓期
            - stake_time: 质押时间
            - unlock_time: 解锁时间
            - pending_reward: 待领取奖励
            - is_active: 是否活跃

        Example:
            >>> client = VIBStakingClient(...)
            >>> info = await client.get_stake_info("0x...")
            >>> print(f"Staked: {info['amount']} VIBE")
            >>> print(f"Tier: {StakeTier(info['tier']).name}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_address = self.w3.to_checksum_address(address)
        stake_info = await self.call_contract_function(
            self.contract.functions.getStakeInfo(checksum_address)
        )

        pending_reward = await self.get_pending_reward(address)

        return {
            "amount": int(stake_info["amount"]),
            "tier": int(stake_info["tier"]),
            "lock_period": int(stake_info["lockPeriod"]),
            "stake_time": int(stake_info["stakeTime"]),
            "unlock_time": int(stake_info["unlockTime"]),
            "pending_reward": pending_reward,
            "is_active": bool(stake_info["isActive"]),
        }

    async def get_pending_reward(self, address: str) -> int:
        """
        获取待领取奖励

        Args:
            address: 用户地址

        Returns:
            待领取奖励数量（wei单位）

        Example:
            >>> client = VIBStakingClient(...)
            >>> reward = await client.get_pending_reward("0x...")
            >>> print(f"Pending reward: {reward} wei")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_address = self.w3.to_checksum_address(address)
        reward = await self.call_contract_function(
            self.contract.functions.getPendingReward(checksum_address)
        )
        return int(reward)

    async def total_staked(self) -> int:
        """
        获取总质押量

        Returns:
            总质押量（wei单位）

        Example:
            >>> client = VIBStakingClient(...)
            >>> total = await client.total_staked()
            >>> print(f"Total staked: {total} wei")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        total = await self.call_contract_function(
            self.contract.functions.totalStaked()
        )
        return int(total)

    async def get_staker_count(self) -> int:
        """
        获取质押者数量

        Returns:
            质押者数量

        Example:
            >>> client = VIBStakingClient(...)
            >>> count = await client.get_staker_count()
            >>> print(f"Stakers: {count}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        count = await self.call_contract_function(
            self.contract.functions.getStakerCount()
        )
        return int(count)

    async def get_stakers(
        self, offset: int = 0, limit: int = 100
    ) -> list:
        """
        获取质押者列表

        Args:
            offset: 偏移量
            limit: 数量限制

        Returns:
            质押者地址列表

        Example:
            >>> client = VIBStakingClient(...)
            >>> stakers = await client.get_stakers(offset=0, limit=10)
            >>> print(f"Stakers: {stakers}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        stakers = await self.call_contract_function(
            self.contract.functions.getStakers(offset, limit)
        )
        return [self.w3.to_checksum_address(addr) for addr in stakers]

    async def calculate_tier(self, amount: int) -> StakeTier:
        """
        计算质押等级

        Args:
            amount: 质押数量（wei单位）

        Returns:
            质押等级

        Example:
            >>> client = VIBStakingClient(...)
            >>> tier = await client.calculate_tier(5000 * 10**18)
            >>> print(f"Tier: {tier.name}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        tier = await self.call_contract_function(
            self.contract.functions.calculateTier(amount)
        )
        return StakeTier(int(tier))

    async def get_voting_power(self, address: str) -> int:
        """
        获取投票权（质押量 × 时长系数）

        Args:
            address: 用户地址

        Returns:
            投票权

        Example:
            >>> client = VIBStakingClient(...)
            >>> power = await client.get_voting_power("0x...")
            >>> print(f"Voting power: {power}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_address = self.w3.to_checksum_address(address)
        power = await self.call_contract_function(
            self.contract.functions.getVotingPower(checksum_address)
        )
        return int(power)

    async def get_staked_duration(self, address: str) -> int:
        """
        获取质押时长（秒）

        Args:
            address: 用户地址

        Returns:
            质押时长（秒）

        Example:
            >>> client = VIBStakingClient(...)
            >>> duration = await client.get_staked_duration("0x...")
            >>> print(f"Staked duration: {duration} seconds")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_address = self.w3.to_checksum_address(address)
        duration = await self.call_contract_function(
            self.contract.functions.getStakedDuration(checksum_address)
        )
        return int(duration)

    async def get_stake_details(
        self, address: str
    ) -> Dict[str, Any]:
        """
        获取质押详情（用于治理）

        Args:
            address: 用户地址

        Returns:
            质押详情字典，包含：
            - amount: 质押数量
            - tier: 质押等级
            - time_multiplier: 时长系数
            - voting_power: 投票权

        Example:
            >>> client = VIBStakingClient(...)
            >>> details = await client.get_stake_details("0x...")
            >>> print(f"Voting power: {details['voting_power']}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_address = self.w3.to_checksum_address(address)
        details = await self.call_contract_function(
            self.contract.functions.getStakeDetails(checksum_address)
        )

        return {
            "amount": int(details[0]),
            "tier": int(details[1]),
            "time_multiplier": int(details[2]),
            "voting_power": int(details[3]),
        }

    async def get_current_apy(self) -> int:
        """
        获取当前APY

        Returns:
            当前APY（百分比，例如3表示3%）

        Example:
            >>> client = VIBStakingClient(...)
            >>> apy = await client.get_current_apy()
            >>> print(f"Current APY: {apy}%")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        apy = await self.call_contract_function(
            self.contract.functions.currentAPY()
        )
        return int(apy)

    async def get_time_multiplier(self, address: str) -> int:
        """
        获取质押时长系数

        Args:
            address: 用户地址

        Returns:
            时长系数（x10000）

        Example:
            >>> client = VIBStakingClient(...)
            >>> multiplier = await client.get_time_multiplier("0x...")
            >>> print(f"Time multiplier: {multiplier / 10000}%")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_address = self.w3.to_checksum_address(address)
        multiplier = await self.call_contract_function(
            self.contract.functions.getTimeMultiplier(checksum_address)
        )
        return int(multiplier)


__all__ = [
    "StakeTier",
    "LockPeriod",
    "VIBStakingClient",
]
