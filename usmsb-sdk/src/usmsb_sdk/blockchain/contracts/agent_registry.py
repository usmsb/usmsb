"""
Agent注册表客户端模块

提供Agent注册表合约的交互接口，包括：
- Agent注册和注销
- Agent有效性验证
- Agent拥有者查询
- Agent数量统计
"""

from typing import Dict, Any, Optional
from web3 import Web3

from ..config import BlockchainConfig
from .base import BaseContractClient, TransactionError, ContractError


class AgentRegistryClient(BaseContractClient):
    """Agent注册表客户端

    提供Agent注册表的完整交互接口，用于管理Agent钱包地址的注册和验证。
    """

    def __init__(
        self,
        web3_client: Optional[Any] = None,
        config: Optional[BlockchainConfig] = None,
        contract_address: Optional[str] = None,
        abi: Optional[Any] = None,
    ):
        """
        初始化Agent注册表客户端

        Args:
            web3_client: Web3客户端实例
            config: 区块链配置
            contract_address: AgentRegistry合约地址
            abi: 合约ABI
        """
        super().__init__(
            web3_client=web3_client,
            config=config,
            contract_address=contract_address,
            abi=abi,
        )

    @property
    def registry_address(self) -> str:
        """获取注册表合约地址"""
        if not self.contract_address:
            raise ContractError("Contract address not set")
        return self.w3.to_checksum_address(self.contract_address)

    async def register_agent(
        self,
        wallet_address: str,
        owner_address: str,
        owner_private_key: str,
        gas: Optional[int] = None,
    ) -> str:
        """
        注册Agent（msg.sender被记录为Owner）

        Args:
            wallet_address: Agent的合约钱包地址
            owner_address: Agent拥有者地址（调用者地址）
            owner_private_key: 拥有者私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = AgentRegistryClient(...)
            >>> tx_hash = await client.register_agent(
            ...     wallet_address="0x...",
            ...     owner_address="0x...",
            ...     owner_private_key="..."
            ... )
            >>> print(f"Register tx: {tx_hash}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_wallet = self.w3.to_checksum_address(wallet_address)
        checksum_owner = self.w3.to_checksum_address(owner_address)

        # 构建注册交易
        tx = self.build_contract_transaction(
            self.contract.functions.registerAgent(checksum_wallet),
            from_address=checksum_owner,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, owner_private_key)
        return tx_hash

    async def unregister_agent(
        self,
        wallet_address: str,
        admin_private_key: str,
        gas: Optional[int] = None,
    ) -> str:
        """
        注销Agent（仅Admin）

        Args:
            wallet_address: Agent的合约钱包地址
            admin_private_key: 管理员私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = AgentRegistryClient(...)
            >>> tx_hash = await client.unregister_agent(
            ...     wallet_address="0x...",
            ...     admin_private_key="..."
            ... )
            >>> print(f"Unregister tx: {tx_hash}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_wallet = self.w3.to_checksum_address(wallet_address)

        # 构建注销交易
        tx = self.build_contract_transaction(
            self.contract.functions.unregisterAgent(checksum_wallet),
            from_address=self.w3.to_checksum_address(
                self.w3.eth.account.from_key(admin_private_key).address
            ),
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, admin_private_key)
        return tx_hash

    async def is_valid_agent(self, address: str) -> bool:
        """
        验证Agent有效性

        Args:
            address: 要验证的地址

        Returns:
            是否为有效Agent

        Example:
            >>> client = AgentRegistryClient(...)
            >>> is_valid = await client.is_valid_agent("0x...")
            >>> print(f"Is valid: {is_valid}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_address = self.w3.to_checksum_address(address)
        is_valid = await self.call_contract_function(
            self.contract.functions.isValidAgent(checksum_address)
        )
        return bool(is_valid)

    async def get_agent_owner(self, wallet_address: str) -> str:
        """
        获取Agent的Owner

        Args:
            wallet_address: Agent钱包地址

        Returns:
            Agent拥有者地址

        Example:
            >>> client = AgentRegistryClient(...)
            >>> owner = await client.get_agent_owner("0x...")
            >>> print(f"Owner: {owner}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_wallet = self.w3.to_checksum_address(wallet_address)
        owner = await self.call_contract_function(
            self.contract.functions.getAgentOwner(checksum_wallet)
        )
        return self.w3.to_checksum_address(owner)

    async def get_owner_agent_count(self, owner: str) -> int:
        """
        获取Owner的Agent数量

        Args:
            owner: 拥有者地址

        Returns:
            拥有的Agent数量

        Example:
            >>> client = AgentRegistryClient(...)
            >>> count = await client.get_owner_agent_count("0x...")
            >>> print(f"Agent count: {count}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_owner = self.w3.to_checksum_address(owner)
        count = await self.call_contract_function(
            self.contract.functions.getOwnerAgentCount(checksum_owner)
        )
        return int(count)

    async def is_registered(self, wallet_address: str) -> bool:
        """
        检查Agent是否已注册

        Args:
            wallet_address: Agent钱包地址

        Returns:
            是否已注册

        Example:
            >>> client = AgentRegistryClient(...)
            >>> registered = await client.is_registered("0x...")
            >>> print(f"Registered: {registered}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_wallet = self.w3.to_checksum_address(wallet_address)
        is_reg = await self.call_contract_function(
            self.contract.functions.isRegistered(checksum_wallet)
        )
        return bool(is_reg)

    async def get_agent_count(self) -> int:
        """
        获取已注册的Agent总数

        Returns:
            Agent总数

        Example:
            >>> client = AgentRegistryClient(...)
            >>> count = await client.get_agent_count()
            >>> print(f"Total agents: {count}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        count = await self.call_contract_function(
            self.contract.functions.getAgentCount()
        )
        return int(count)

    async def get_agent_at(self, index: int) -> str:
        """
        根据索引获取Agent地址

        Args:
            index: Agent索引

        Returns:
            Agent地址

        Example:
            >>> client = AgentRegistryClient(...)
            >>> agent = await client.get_agent_at(0)
            >>> print(f"Agent at 0: {agent}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        agent = await self.call_contract_function(
            self.contract.functions.getAgentAt(index)
        )
        return self.w3.to_checksum_address(agent)

    async def get_all_agents(self, offset: int = 0, limit: int = 100) -> list:
        """
        获取Agent地址列表

        Args:
            offset: 偏移量
            limit: 数量限制

        Returns:
            Agent地址列表

        Example:
            >>> client = AgentRegistryClient(...)
            >>> agents = await client.get_all_agents(offset=0, limit=10)
            >>> print(f"Agents: {agents}")
        """
        count = await self.get_agent_count()
        if offset >= count:
            return []

        agents = []
        end = min(offset + limit, count)
        for i in range(offset, end):
            agent = await self.get_agent_at(i)
            agents.append(agent)
        return agents


__all__ = [
    "AgentRegistryClient",
]
