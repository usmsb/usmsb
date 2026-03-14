"""
Agent管理器模块

整合Agent创建流程，提供完整的Agent生命周期管理。
"""

import json

from eth_account import Account

from .config import BlockchainConfig
from .contracts.abi_loader import load_abi_and_bytecode
from .contracts.agent_registry import AgentRegistryClient
from .contracts.agent_wallet import AgentWalletClient, AgentWalletFactory
from .contracts.vib_identity import VIBIdentityClient
from .contracts.vib_staking import VIBStakingClient
from .contracts.vibe_token import VIBETokenClient
from .key_management import AgentKeyManager
from .web3_client import Web3Client


class AgentCreationError(Exception):
    """Agent创建错误"""
    pass


class AgentManager:
    """Agent管理器

    整合Agent创建流程，提供一站式Agent创建和管理功能。

    主要功能：
    - 检查Owner的Agent数量限制
    - 生成Agent密钥对
    - 部署AgentWallet合约
    - 注册到AgentRegistry
    - 注册VIBIdentity
    - 初始充值
    """

    def __init__(
        self,
        config: BlockchainConfig | None = None,
        key_manager: AgentKeyManager | None = None,
    ):
        """
        初始化Agent管理器

        Args:
            config: 区块链配置
            key_manager: 密钥管理器（如不指定则自动创建）
        """
        self.config = config or BlockchainConfig()
        self.web3_client = Web3Client(config=self.config)
        self.key_manager = key_manager

        # 延迟初始化合约客户端
        self._token_client: VIBETokenClient | None = None
        self._registry_client: AgentRegistryClient | None = None
        self._identity_client: VIBIdentityClient | None = None
        self._staking_client: VIBStakingClient | None = None
        self._wallet_factory: AgentWalletFactory | None = None

    @property
    def token_client(self) -> VIBETokenClient:
        """获取VIBE代币客户端"""
        if self._token_client is None:
            self._token_client = VIBETokenClient(
                web3_client=self.web3_client,
                config=self.config,
                contract_address=self.config.get_contract_address("VIBEToken"),
                abi=load_abi_and_bytecode("VIBEToken")[0],
            )
        return self._token_client

    @property
    def registry_client(self) -> AgentRegistryClient:
        """获取Agent注册表客户端"""
        if self._registry_client is None:
            self._registry_client = AgentRegistryClient(
                web3_client=self.web3_client,
                config=self.config,
                contract_address=self.config.get_contract_address("AgentRegistry"),
                abi=load_abi_and_bytecode("AgentRegistry")[0],
            )
        return self._registry_client

    @property
    def identity_client(self) -> VIBIdentityClient:
        """获取VIB身份客户端"""
        if self._identity_client is None:
            self._identity_client = VIBIdentityClient(
                web3_client=self.web3_client,
                config=self.config,
                contract_address=self.config.get_contract_address("VIBIdentity"),
                abi=load_abi_and_bytecode("VIBIdentity")[0],
            )
        return self._identity_client

    @property
    def staking_client(self) -> VIBStakingClient:
        """获取质押客户端"""
        if self._staking_client is None:
            self._staking_client = VIBStakingClient(
                web3_client=self.web3_client,
                config=self.config,
                contract_address=self.config.get_contract_address("VIBStaking"),
                abi=load_abi_and_bytecode("VIBStaking")[0],
            )
        return self._staking_client

    @property
    def wallet_factory(self) -> AgentWalletFactory:
        """获取钱包工厂"""
        if self._wallet_factory is None:
            abi, bytecode = load_abi_and_bytecode("AgentWallet")
            self._wallet_factory = AgentWalletFactory(
                web3=self.web3_client.w3,
                bytecode=bytecode,
                abi=abi,
                config=self.config,
                contract_addresses=self.config.contracts,
            )
        return self._wallet_factory

    async def check_can_create_agent(self, owner_address: str) -> dict[str, any]:
        """
        检查Owner是否可以创建新Agent

        Args:
            owner_address: Owner地址

        Returns:
            字典包含：
            - can_create: 是否可以创建
            - current: 当前Agent数量
            - limit: Agent数量限制
            - remaining: 剩余可创建数量
            - reason: 不能创建的原因（如适用）

        Example:
            >>> manager = AgentManager()
            >>> result = await manager.check_can_create_agent("0x...")
            >>> if result['can_create']:
            ...     print(f"Can create {result['remaining']} more agents")
        """
        checksum_owner = self.web3_client.w3.to_checksum_address(owner_address)

        # 获取当前Agent数量
        current_count = await self.registry_client.get_owner_agent_count(checksum_owner)

        # 获取Agent数量限制
        limit = await self.identity_client.get_agent_limit(checksum_owner)

        remaining = limit - current_count
        can_create = remaining > 0
        reason = None if can_create else "Agent limit reached"

        return {
            "can_create": can_create,
            "current": current_count,
            "limit": limit,
            "remaining": max(0, remaining),
            "reason": reason,
        }

    async def generate_agent_keypair(self) -> tuple[str, str]:
        """
        生成Agent密钥对

        Returns:
            (address, private_key) 元组

        Example:
            >>> manager = AgentManager()
            >>> address, private_key = await manager.generate_agent_keypair()
            >>> print(f"Agent address: {address}")
        """
        account = Account.create()
        return account.address, account.key.hex()

    async def generate_agent_keypair_encrypted(
        self,
        encryption_key: str = None,
    ) -> dict[str, str]:
        """
        生成Agent密钥对（加密）

        Args:
            encryption_key: 加密密钥（如不指定则从环境变量读取）

        Returns:
            字典包含地址、私钥和加密后的私钥
        """
        if self.key_manager is None:
            self.key_manager = AgentKeyManager(encryption_key)

        return self.key_manager.generate_agent_keypair()

    async def create_agent(
        self,
        owner_address: str,
        owner_private_key: str,
        agent_name: str = "",
        agent_metadata: str = "{}",
        initial_deposit: int = 0,
        register_identity: bool = True,
        agent_address: str = None,
        agent_private_key: str = None,
        encryption_key: str = None,
    ) -> dict[str, any]:
        """
        完整的Agent创建流程

        流程：
        1. 检查Owner的Agent数量限制
        2. 生成Agent密钥对（如未提供）
        3. 部署AgentWallet合约
        4. 注册到AgentRegistry
        5. 注册VIBIdentity（可选）
        6. 初始充值（可选）

        Args:
            owner_address: Owner的EOA地址
            owner_private_key: Owner的私钥
            agent_name: Agent名称（用于身份注册）
            agent_metadata: Agent元数据（JSON字符串）
            initial_deposit: 初始充值金额（wei单位）
            register_identity: 是否注册身份
            agent_address: Agent地址（如不指定则自动生成）
            agent_private_key: Agent私钥（如不指定则自动生成）
            encryption_key: 加密密钥（用于加密私钥）

        Returns:
            字典包含：
            - agent_address: Agent的EOA地址
            - agent_private_key: Agent的私钥（加密后）
            - wallet_address: AgentWallet合约地址
            - tx_hash: 部署交易哈希
            - identity_token_id: 身份代币ID（如注册）

        Raises:
            AgentCreationError: 创建失败

        Example:
            >>> manager = AgentManager()
            >>> result = await manager.create_agent(
            ...     owner_address="0x...",
            ...     owner_private_key="...",
            ...     agent_name="MyAgent",
            ...     agent_metadata='{"type": "chat"}',
            ...     initial_deposit=100 * 10**18,
            ... )
            >>> print(f"Wallet address: {result['wallet_address']}")
        """
        checksum_owner = self.web3_client.w3.to_checksum_address(owner_address)

        # 1. 检查Agent数量限制
        check_result = await self.check_can_create_agent(checksum_owner)
        if not check_result["can_create"]:
            raise AgentCreationError(
                f"Cannot create agent: {check_result['reason']}. "
                f"Current: {check_result['current']}, Limit: {check_result['limit']}"
            )

        # 2. 生成Agent密钥对（如未提供）
        if agent_address is None or agent_private_key is None:
            if encryption_key and self.key_manager is None:
                self.key_manager = AgentKeyManager(encryption_key)

            if self.key_manager:
                keypair = await self.generate_agent_keypair_encrypted(encryption_key)
                agent_address = keypair["address"]
                agent_private_key = keypair["encrypted_private_key"]
            else:
                agent_address, agent_private_key = await self.generate_agent_keypair()

        checksum_agent = self.web3_client.w3.to_checksum_address(agent_address)

        # 3. 部署AgentWallet合约
        try:
            wallet_address, tx_hash = await self.wallet_factory.deploy_wallet(
                owner_address=checksum_owner,
                agent_address=checksum_agent,
                from_address=checksum_owner,
                private_key=owner_private_key,
            )
        except Exception as e:
            raise AgentCreationError(f"Failed to deploy AgentWallet: {e}")

        # 4. 注册到AgentRegistry
        try:
            registry_tx_hash = await self.registry_client.register_agent(
                wallet_address=wallet_address,
                owner_address=checksum_owner,
                owner_private_key=owner_private_key,
            )
        except Exception as e:
            raise AgentCreationError(f"Failed to register agent: {e}")

        # 5. 注册VIBIdentity（可选）
        identity_token_id = None
        if register_identity:
            try:
                # 使用Agent的元数据
                if isinstance(agent_metadata, dict):
                    agent_metadata = json.dumps(agent_metadata)

                identity_token_id, identity_tx_hash = await self.identity_client.register_ai_identity_for(
                    agent_address=checksum_agent,
                    name=agent_name or f"Agent_{checksum_agent[:8]}",
                    metadata=agent_metadata,
                    from_address=checksum_owner,
                    private_key=owner_private_key,
                )
            except Exception as e:
                # 身份注册失败不影响Agent创建
                import warnings
                warnings.warn(f"Failed to register identity: {e}", stacklevel=2)

        # 6. 初始充值（可选）
        if initial_deposit > 0:
            try:
                # 首先授权钱包
                await self.token_client.approve(
                    spender=wallet_address,
                    amount=initial_deposit,
                    from_address=checksum_owner,
                    private_key=owner_private_key,
                )

                # 然后充值
                await AgentWalletClient(
                    web3_client=self.web3_client,
                    config=self.config,
                    contract_address=wallet_address,
                    abi=load_abi_and_bytecode("AgentWallet")[0],
                ).deposit(
                    amount=initial_deposit,
                    from_address=checksum_owner,
                    private_key=owner_private_key,
                )
            except Exception as e:
                raise AgentCreationError(f"Failed to deposit initial amount: {e}")

        return {
            "agent_address": checksum_agent,
            "agent_private_key": agent_private_key,
            "wallet_address": wallet_address,
            "tx_hash": tx_hash,
            "registry_tx_hash": registry_tx_hash,
            "identity_token_id": identity_token_id,
        }

    async def get_agent_full_status(
        self,
        agent_address: str,
        wallet_address: str,
    ) -> dict[str, any]:
        """
        获取Agent完整状态

        Args:
            agent_address: Agent的EOA地址
            wallet_address: AgentWallet合约地址

        Returns:
            字典包含Agent的完整状态信息

        Example:
            >>> manager = AgentManager()
            >>> status = await manager.get_agent_full_status(
            ...     agent_address="0x...",
            ...     wallet_address="0x...",
            ... )
            >>> print(f"Balance: {status['wallet_balance']} VIBE")
        """
        checksum_agent = self.web3_client.w3.to_checksum_address(agent_address)
        checksum_wallet = self.web3_client.w3.to_checksum_address(wallet_address)

        # 获取钱包客户端
        wallet_client = AgentWalletClient(
            web3_client=self.web3_client,
            config=self.config,
            contract_address=checksum_wallet,
            abi=load_abi_and_bytecode("AgentWallet")[0],
        )

        # 并行获取各种状态
        (
            is_valid,
            owner,
            wallet_balance,
            staking_tier,
            daily_limit,
            remaining_limit,
            max_per_tx,
            staked_amount,
            is_registered_identity,
        ) = await asyncio.gather(
            self.registry_client.is_valid_agent(checksum_wallet),
            self.registry_client.get_agent_owner(checksum_wallet),
            wallet_client.get_balance_vibe(),
            wallet_client.get_staking_tier(),
            wallet_client.get_daily_limit_vibe(),
            wallet_client.get_remaining_limit_vibe(),
            wallet_client.get_max_per_tx_vibe(),
            wallet_client.get_staked_amount_vibe(),
            self.identity_client.is_registered(checksum_agent),
        )

        return {
            "agent_address": checksum_agent,
            "wallet_address": checksum_wallet,
            "owner": owner,
            "is_valid": is_valid,
            "wallet_balance": wallet_balance,
            "staking_tier": staking_tier,
            "staking_tier_name": AgentWalletClient.TIER_NAMES.get(staking_tier, "Unknown"),
            "daily_limit": daily_limit,
            "remaining_limit": remaining_limit,
            "max_per_tx": max_per_tx,
            "staked_amount": staked_amount,
            "is_registered_identity": is_registered_identity,
        }

    async def list_owner_agents(self, owner_address: str) -> list[dict[str, str]]:
        """
        列出Owner的所有Agent

        Args:
            owner_address: Owner地址

        Returns:
            Agent列表，每个Agent包含地址、钱包地址等信息

        Example:
            >>> manager = AgentManager()
            >>> agents = await manager.list_owner_agents("0x...")
            >>> for agent in agents:
            ...     print(f"Agent: {agent['agent_address']}")
        """
        checksum_owner = self.web3_client.w3.to_checksum_address(owner_address)

        # 获取所有注册的Agent
        all_agents = await self.registry_client.get_all_agents()

        # 过滤出属于该Owner的Agent
        owner_agents = []
        for wallet_address in all_agents:
            try:
                agent_owner = await self.registry_client.get_agent_owner(wallet_address)
                if agent_owner.lower() == checksum_owner.lower():
                    # 获取Agent地址（从钱包合约）
                    wallet_client = AgentWalletClient(
                        web3_client=self.web3_client,
                        config=self.config,
                        contract_address=wallet_address,
                        abi=load_abi_and_bytecode("AgentWallet")[0],
                    )
                    agent_address = await wallet_client.get_agent()

                    owner_agents.append({
                        "agent_address": agent_address,
                        "wallet_address": wallet_address,
                        "owner": agent_owner,
                    })
            except Exception:
                # 跳过无法访问的Agent
                continue

        return owner_agents

    async def get_wallet_client(self, wallet_address: str) -> AgentWalletClient:
        """
        获取指定钱包的客户端

        Args:
            wallet_address: AgentWallet合约地址

        Returns:
            AgentWalletClient实例
        """
        return AgentWalletClient(
            web3_client=self.web3_client,
            config=self.config,
            contract_address=wallet_address,
            abi=load_abi_and_bytecode("AgentWallet")[0],
        )


# 导入asyncio用于gather操作
import asyncio

__all__ = [
    "AgentManager",
    "AgentCreationError",
]
