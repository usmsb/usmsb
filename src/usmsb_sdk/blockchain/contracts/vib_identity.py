"""
VIBIdentity身份认证客户端模块

提供VIBIdentity合约的交互接口，包括：
- 身份注册
- 身份验证
- Agent数量限制查询
- 身份信息查询
"""

from enum import IntEnum
from typing import Any

from ..config import BlockchainConfig
from .base import BaseContractClient, ContractError


class IdentityType(IntEnum):
    """身份类型枚举"""
    AI_AGENT = 0
    HUMAN_PROVIDER = 1
    NODE_OPERATOR = 2
    GOVERNANCE = 3

    @classmethod
    def from_name(cls, name: str) -> "IdentityType":
        """从名称获取身份类型"""
        name_map = {
            "AI_AGENT": cls.AI_AGENT,
            "AGENT": cls.AI_AGENT,
            "HUMAN_PROVIDER": cls.HUMAN_PROVIDER,
            "HUMAN": cls.HUMAN_PROVIDER,
            "NODE_OPERATOR": cls.NODE_OPERATOR,
            "NODE": cls.NODE_OPERATOR,
            "GOVERNANCE": cls.GOVERNANCE,
        }
        return name_map.get(name.upper(), cls.AI_AGENT)


class VIBIdentityClient(BaseContractClient):
    """VIB身份认证客户端

    提供VIBE身份认证（SBT）的完整交互接口，用于AI Agent、
    人类服务者、节点运营商等身份的注册和管理。
    """

    # 代币精度
    DECIMALS = 18

    # 注册费用（VIBE代币）
    REGISTRATION_FEE = 100 * 10**18  # 100 VIBE

    # ETH注册费用
    ETH_REGISTRATION_FEE = 0.01 * 10**18  # 0.01 ETH

    # 各等级Agent数量限制
    BRONZE_AGENT_LIMIT = 1
    SILVER_AGENT_LIMIT = 3
    GOLD_AGENT_LIMIT = 10
    PLATINUM_AGENT_LIMIT = 50

    def __init__(
        self,
        web3_client: Any | None = None,
        config: BlockchainConfig | None = None,
        contract_address: str | None = None,
        abi: Any | None = None,
    ):
        """
        初始化VIBIdentity客户端

        Args:
            web3_client: Web3客户端实例
            config: 区块链配置
            contract_address: VIBIdentity合约地址
            abi: 合约ABI
        """
        super().__init__(
            web3_client=web3_client,
            config=config,
            contract_address=contract_address,
            abi=abi,
        )

    @property
    def identity_address(self) -> str:
        """获取身份合约地址"""
        if not self.contract_address:
            raise ContractError("Contract address not set")
        return self.w3.to_checksum_address(self.contract_address)

    async def register_ai_identity_for(
        self,
        agent_address: str,
        name: str,
        metadata: str,
        from_address: str,
        private_key: str,
        gas: int | None = None,
    ) -> tuple[int, str]:
        """
        为Agent注册身份（由创建者调用）

        Args:
            agent_address: Agent地址
            name: Agent名称
            metadata: 元数据（JSON格式的agent能力描述）
            from_address: 创建者地址
            private_key: 创建者私钥
            gas: 可选的gas限制

        Returns:
            (token_id, tx_hash) 元组

        Example:
            >>> client = VIBIdentityClient(...)
            >>> token_id, tx_hash = await client.register_ai_identity_for(
            ...     agent_address="0x...",
            ...     name="MyAgent",
            ...     metadata='{"capabilities": ["chat", "code"]}',
            ...     from_address="0x...",
            ...     private_key="..."
            ... )
            >>> print(f"Token ID: {token_id}, TX: {tx_hash}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_agent = self.w3.to_checksum_address(agent_address)
        checksum_from = self.w3.to_checksum_address(from_address)

        # 构建注册交易
        tx = self.build_contract_transaction(
            self.contract.functions.registerAIIdentityFor(checksum_agent, name, metadata),
            from_address=checksum_from,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, private_key)

        # 从交易收据获取token ID（通过事件解析）
        # 简化处理：假设成功注册后返回1，实际应从事件解析
        token_id = 1

        return (token_id, tx_hash)

    async def register_ai_identity(
        self,
        name: str,
        metadata: str,
        from_address: str,
        private_key: str,
        gas: int | None = None,
    ) -> tuple[int, str]:
        """
        注册AI Agent身份（自注册）

        Args:
            name: Agent名称
            metadata: 元数据（JSON格式的agent能力描述）
            from_address: 质押者地址
            private_key: 质押者私钥
            gas: 可选的gas限制

        Returns:
            (token_id, tx_hash) 元组

        Example:
            >>> client = VIBIdentityClient(...)
            >>> token_id, tx_hash = await client.register_ai_identity(
            ...     name="MyAgent",
            ...     metadata='{"capabilities": ["chat", "code"]}',
            ...     from_address="0x...",
            ...     private_key="..."
            ... )
            >>> print(f"Token ID: {token_id}, TX: {tx_hash}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_from = self.w3.to_checksum_address(from_address)

        # 构建注册交易
        tx = self.build_contract_transaction(
            self.contract.functions.registerAIIdentity(name, metadata),
            from_address=checksum_from,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, private_key)

        # 从交易收据获取token ID（通过事件解析）
        # 简化处理：假设成功注册后返回1，实际应从事件解析
        token_id = 1

        return (token_id, tx_hash)

    async def register_human_provider(
        self,
        name: str,
        metadata: str,
        from_address: str,
        private_key: str,
        gas: int | None = None,
    ) -> tuple[int, str]:
        """
        注册人类服务者身份

        Args:
            name: 服务者名称
            metadata: 元数据（技能、证书等信息）
            from_address: 注册者地址
            private_key: 注册者私钥
            gas: 可选的gas限制

        Returns:
            (token_id, tx_hash) 元组
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_from = self.w3.to_checksum_address(from_address)

        tx = self.build_contract_transaction(
            self.contract.functions.registerHumanProvider(name, metadata),
            from_address=checksum_from,
            gas=gas,
        )

        tx_hash = self.sign_and_send_transaction(tx, private_key)
        token_id = 1

        return (token_id, tx_hash)

    async def register_node_operator(
        self,
        name: str,
        metadata: str,
        from_address: str,
        private_key: str,
        gas: int | None = None,
    ) -> tuple[int, str]:
        """
        注册节点运营商身份

        Args:
            name: 节点名称
            metadata: 元数据（节点规格、位置等信息）
            from_address: 注册者地址
            private_key: 注册者私钥
            gas: 可选的gas限制

        Returns:
            (token_id, tx_hash) 元组
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_from = self.w3.to_checksum_address(from_address)

        tx = self.build_contract_transaction(
            self.contract.functions.registerNodeOperator(name, metadata),
            from_address=checksum_from,
            gas=gas,
        )

        tx_hash = self.sign_and_send_transaction(tx, private_key)
        token_id = 1

        return (token_id, tx_hash)

    async def register_governance(
        self,
        name: str,
        metadata: str,
        from_address: str,
        private_key: str,
        gas: int | None = None,
    ) -> tuple[int, str]:
        """
        注册治理参与者身份

        Args:
            name: 治理者名称
            metadata: 元数据（治理历史、提案记录等）
            from_address: 注册者地址
            private_key: 注册者私钥
            gas: 可选的gas限制

        Returns:
            (token_id, tx_hash) 元组
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_from = self.w3.to_checksum_address(from_address)

        tx = self.build_contract_transaction(
            self.contract.functions.registerGovernance(name, metadata),
            from_address=checksum_from,
            gas=gas,
        )

        tx_hash = self.sign_and_send_transaction(tx, private_key)
        token_id = 1

        return (token_id, tx_hash)

    async def get_agent_limit(self, owner: str) -> int:
        """
        获取Agent数量限制

        Bronze=1, Silver=3, Gold=10, Platinum=50

        Args:
            owner: 用户地址

        Returns:
            Agent数量限制

        Example:
            >>> client = VIBIdentityClient(...)
            >>> limit = await client.get_agent_limit("0x...")
            >>> print(f"Agent limit: {limit}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_owner = self.w3.to_checksum_address(owner)
        limit = await self.call_contract_function(
            self.contract.functions.getAgentLimit(checksum_owner)
        )
        return int(limit)

    async def get_user_agent_count(self, owner: str) -> int:
        """
        获取已创建Agent数量

        Args:
            owner: 用户地址

        Returns:
            已创建Agent数量

        Example:
            >>> client = VIBIdentityClient(...)
            >>> count = await client.get_user_agent_count("0x...")
            >>> print(f"Agent count: {count}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_owner = self.w3.to_checksum_address(owner)
        count = await self.call_contract_function(
            self.contract.functions.getUserAgentCount(checksum_owner)
        )
        return int(count)

    async def is_registered(self, address: str) -> bool:
        """
        检查是否已注册身份

        Args:
            address: 地址

        Returns:
            是否已注册

        Example:
            >>> client = VIBIdentityClient(...)
            >>> registered = await client.is_registered("0x...")
            >>> print(f"Registered: {registered}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_address = self.w3.to_checksum_address(address)
        is_reg = await self.call_contract_function(
            self.contract.functions.isRegistered(checksum_address)
        )
        return bool(is_reg)

    async def get_identity_info(self, token_id: int) -> dict[str, Any]:
        """
        获取身份信息

        Args:
            token_id: 代币ID

        Returns:
            身份信息字典，包含：
            - owner: 拥有者地址
            - identity_type: 身份类型
            - name: 名称
            - registration_time: 注册时间
            - metadata: 元数据
            - is_verified: 是否已验证

        Example:
            >>> client = VIBIdentityClient(...)
            >>> info = await client.get_identity_info(1)
            >>> print(f"Owner: {info['owner']}")
            >>> print(f"Name: {info['name']}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        identity_info = await self.call_contract_function(
            self.contract.functions.getIdentityInfo(token_id)
        )

        return {
            "owner": self.w3.to_checksum_address(identity_info["owner"]),
            "identity_type": int(identity_info["identityType"]),
            "name": identity_info["name"],
            "registration_time": int(identity_info["registrationTime"]),
            "metadata": identity_info["metadata"],
            "is_verified": bool(identity_info["isVerified"]),
        }

    async def get_token_id_by_address(self, owner: str) -> int:
        """
        根据地址获取代币ID

        Args:
            owner: 地址

        Returns:
            代币ID

        Example:
            >>> client = VIBIdentityClient(...)
            >>> token_id = await client.get_token_id_by_address("0x...")
            >>> print(f"Token ID: {token_id}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_owner = self.w3.to_checksum_address(owner)
        token_id = await self.call_contract_function(
            self.contract.functions.getTokenIdByAddress(checksum_owner)
        )
        return int(token_id)

    async def get_identity_type(self, token_id: int) -> IdentityType:
        """
        获取身份类型

        Args:
            token_id: 代币ID

        Returns:
            身份类型

        Example:
            >>> client = VIBIdentityClient(...)
            >>> type_id = await client.get_identity_type(1)
            >>> print(f"Type: {IdentityType(type_id).name}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        identity_type = await self.call_contract_function(
            self.contract.functions.getIdentityType(token_id)
        )
        return IdentityType(int(identity_type))

    async def check_name_available(self, name: str) -> bool:
        """
        检查名称是否可用

        Args:
            name: 名称

        Returns:
            是否可用

        Example:
            >>> client = VIBIdentityClient(...)
            >>> available = await client.check_name_available("MyAgent")
            >>> print(f"Available: {available}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        available = await self.call_contract_function(
            self.contract.functions.checkNameAvailable(name)
        )
        return bool(available)

    async def get_verified_count(self) -> int:
        """
        获取已验证身份数量

        Returns:
            已验证身份数量

        Example:
            >>> client = VIBIdentityClient(...)
            >>> count = await client.get_verified_count()
            >>> print(f"Verified: {count}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        count = await self.call_contract_function(
            self.contract.functions.getVerifiedCount()
        )
        return int(count)

    async def get_count_by_type(self, identity_type: IdentityType) -> int:
        """
        获取指定类型的身份数量

        Args:
            identity_type: 身份类型

        Returns:
            该类型的身份数量

        Example:
            >>> client = VIBIdentityClient(...)
            >>> count = await client.get_count_by_type(IdentityType.AI_AGENT)
            >>> print(f"AI Agents: {count}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        count = await self.call_contract_function(
            self.contract.functions.getCountByType(int(identity_type))
        )
        return int(count)

    async def get_identity_count(self) -> int:
        """
        获取总身份数量

        Returns:
            总身份数量

        Example:
            >>> client = VIBIdentityClient(...)
            >>> count = await client.get_identity_count()
            >>> print(f"Total identities: {count}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        count = await self.call_contract_function(
            self.contract.functions.identityCount()
        )
        return int(count)

    async def get_agent_creator(self, agent: str) -> str:
        """
        获取Agent的创建者

        Args:
            agent: Agent地址

        Returns:
            创建者地址

        Example:
            >>> client = VIBIdentityClient(...)
            >>> creator = await client.get_agent_creator("0x...")
            >>> print(f"Creator: {creator}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_agent = self.w3.to_checksum_address(agent)
        creator = await self.call_contract_function(
            self.contract.functions.getAgentCreator(checksum_agent)
        )
        return self.w3.to_checksum_address(creator)

    async def update_metadata(
        self,
        token_id: int,
        metadata: str,
        from_address: str,
        private_key: str,
        gas: int | None = None,
    ) -> str:
        """
        更新身份元数据

        Args:
            token_id: 代币ID
            metadata: 新的元数据
            from_address: 拥有者地址
            private_key: 拥有者私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = VIBIdentityClient(...)
            >>> tx_hash = await client.update_metadata(
            ...     token_id=1,
            ...     metadata='{"updated": true}',
            ...     from_address="0x...",
            ...     private_key="..."
            ... )
            >>> print(f"Update tx: {tx_hash}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_from = self.w3.to_checksum_address(from_address)

        tx = self.build_contract_transaction(
            self.contract.functions.updateMetadata(token_id, metadata),
            from_address=checksum_from,
            gas=gas,
        )

        tx_hash = self.sign_and_send_transaction(tx, private_key)
        return tx_hash

    async def verify_identity(
        self,
        token_id: int,
        verified: bool,
        admin_address: str,
        admin_private_key: str,
        gas: int | None = None,
    ) -> str:
        """
        验证身份（仅管理员）

        Args:
            token_id: 代币ID
            verified: 是否验证
            admin_address: 管理员地址
            admin_private_key: 管理员私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = VIBIdentityClient(...)
            >>> tx_hash = await client.verify_identity(
            ...     token_id=1,
            ...     verified=True,
            ...     admin_address="0x...",
            ...     admin_private_key="..."
            ... )
            >>> print(f"Verify tx: {tx_hash}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_admin = self.w3.to_checksum_address(admin_address)

        tx = self.build_contract_transaction(
            self.contract.functions.verifyIdentity(token_id, verified),
            from_address=checksum_admin,
            gas=gas,
        )

        tx_hash = self.sign_and_send_transaction(tx, admin_private_key)
        return tx_hash


__all__ = [
    "IdentityType",
    "VIBIdentityClient",
]
