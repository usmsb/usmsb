"""
区块链集成模块

提供USMSB SDK的区块链集成功能，包括：
- 多网络配置管理
- Web3客户端封装
- 智能合约交互
- Agent管理
- 事件监听
- 统一区块链客户端入口
"""

import logging

logger = logging.getLogger(__name__)

import asyncio
from typing import Any, Dict, Optional

from .agent_manager import (
    AgentCreationError,
    AgentManager,
)
from .config import (
    BlockchainConfig,
    NetworkConfig,
    NetworkType,
    get_default_config,
)
from .contracts import (
    AgentRegistryClient,
    AgentWalletClient,
    AgentWalletFactory,
    BaseContractClient,
    ContractError,
    IdentityType,
    JointOrderClient,
    LockPeriod,
    PoolStatus,
    ProposalState,
    ProposalType,
    # 枚举和类型
    StakeTier,
    TransactionError,
    VetoType,
    VIBCollaborationClient,
    VIBDividendClient,
    # 合约客户端
    VIBETokenClient,
    VIBGovernanceClient,
    VIBIdentityClient,
    VIBStakingClient,
)
from .event_listener import (
    AsyncEventCallback,
    BlockchainEventListener,
    EventCallback,
    EventFilter,
    EventFilterBuilder,
    ParsedEvent,
    TypedEventListener,
    create_event_listener,
    filter_events,
)
from .key_management import (
    AgentKeyManager,
)
from .web3_client import (
    Web3Client,
)


class VIBEBlockchainClient:
    """统一区块链客户端入口

    提供一站式访问所有VIBE区块链功能的接口。
    整合了所有合约客户端、Web3客户端和Agent管理器。

    主要功能：
    - 统一的配置和网络管理
    - 所有合约客户端的集中访问
    - Agent创建和管理
    - Agent状态查询
    - 便捷的检查方法

    Example:
        >>> from usmsb_sdk.blockchain import VIBEBlockchainClient
        >>>
        >>> # 使用默认配置（测试网）
        >>> client = VIBEBlockchainClient()
        >>>
        >>> # 检查是否可以创建Agent
        >>> result = await client.check_can_create_agent("0x...")
        >>> print(f"Can create: {result['can_create']}")
        >>>
        >>> # 获取代币余额
        >>> balance = await client.token.balance_of_vibe("0x...")
        >>> print(f"Balance: {balance} VIBE")
    """

    def __init__(self, config: BlockchainConfig | None = None):
        """
        初始化统一区块链客户端

        Args:
            config: 区块链配置（如不指定则使用默认配置）
        """
        self.config = config or BlockchainConfig()
        self._web3_client: Web3Client | None = None
        self._token_client: VIBETokenClient | None = None
        self._registry_client: AgentRegistryClient | None = None
        self._identity_client: VIBIdentityClient | None = None
        self._staking_client: VIBStakingClient | None = None
        self._wallet_factory: AgentWalletFactory | None = None
        self._dividend_client: VIBDividendClient | None = None
        self._governance_client: VIBGovernanceClient | None = None
        self._collaboration_client: VIBCollaborationClient | None = None
        self._joint_order_client: JointOrderClient | None = None
        self._agent_manager: AgentManager | None = None
        self._key_manager: AgentKeyManager | None = None

    @property
    def web3(self) -> Web3Client:
        """获取Web3客户端"""
        if self._web3_client is None:
            self._web3_client = Web3Client(config=self.config)
        return self._web3_client

    @property
    def token(self) -> VIBETokenClient:
        """获取VIBE代币客户端"""
        if self._token_client is None:
            from .contracts.abi_loader import load_abi_and_bytecode
            from .contracts.vibe_token import VIBETokenClient

            self._token_client = VIBETokenClient(
                web3_client=self.web3,
                config=self.config,
                contract_address=self.config.get_contract_address("VIBEToken"),
                abi=load_abi_and_bytecode("VIBEToken")[0],
            )
        return self._token_client

    @property
    def registry(self) -> AgentRegistryClient:
        """获取Agent注册表客户端"""
        if self._registry_client is None:
            from .contracts.abi_loader import load_abi_and_bytecode
            from .contracts.agent_registry import AgentRegistryClient

            self._registry_client = AgentRegistryClient(
                web3_client=self.web3,
                config=self.config,
                contract_address=self.config.get_contract_address("AgentRegistry"),
                abi=load_abi_and_bytecode("AgentRegistry")[0],
            )
        return self._registry_client

    @property
    def identity(self) -> VIBIdentityClient:
        """获取VIB身份客户端"""
        if self._identity_client is None:
            from .contracts.abi_loader import load_abi_and_bytecode
            from .contracts.vib_identity import VIBIdentityClient

            self._identity_client = VIBIdentityClient(
                web3_client=self.web3,
                config=self.config,
                contract_address=self.config.get_contract_address("VIBIdentity"),
                abi=load_abi_and_bytecode("VIBIdentity")[0],
            )
        return self._identity_client

    @property
    def staking(self) -> VIBStakingClient:
        """获取质押客户端"""
        if self._staking_client is None:
            from .contracts.abi_loader import load_abi_and_bytecode
            from .contracts.vib_staking import VIBStakingClient

            self._staking_client = VIBStakingClient(
                web3_client=self.web3,
                config=self.config,
                contract_address=self.config.get_contract_address("VIBStaking"),
                abi=load_abi_and_bytecode("VIBStaking")[0],
            )
        return self._staking_client

    @property
    def wallet_factory(self) -> AgentWalletFactory:
        """获取钱包工厂"""
        if self._wallet_factory is None:
            from .contracts.abi_loader import load_abi_and_bytecode
            from .contracts.agent_wallet import AgentWalletFactory

            abi, bytecode = load_abi_and_bytecode("AgentWallet")
            self._wallet_factory = AgentWalletFactory(
                web3=self.web3.w3,
                bytecode=bytecode,
                abi=abi,
                config=self.config,
                contract_addresses=self.config.contracts,
            )
        return self._wallet_factory

    @property
    def dividend(self) -> VIBDividendClient:
        """获取分红客户端"""
        if self._dividend_client is None:
            from .contracts.abi_loader import load_abi_and_bytecode
            from .contracts.vib_dividend import VIBDividendClient

            self._dividend_client = VIBDividendClient(
                web3_client=self.web3,
                config=self.config,
                contract_address=self.config.get_contract_address("VIBDividend"),
                abi=load_abi_and_bytecode("VIBDividend")[0],
            )
        return self._dividend_client

    @property
    def governance(self) -> VIBGovernanceClient:
        """获取治理客户端"""
        if self._governance_client is None:
            from .contracts.abi_loader import load_abi_and_bytecode
            from .contracts.vib_governance import VIBGovernanceClient

            self._governance_client = VIBGovernanceClient(
                web3_client=self.web3,
                config=self.config,
                contract_address=self.config.get_contract_address("VIBGovernance"),
                abi=load_abi_and_bytecode("VIBGovernance")[0],
            )
        return self._governance_client

    @property
    def collaboration(self) -> VIBCollaborationClient:
        """获取协作客户端"""
        if self._collaboration_client is None:
            from .contracts.abi_loader import load_abi_and_bytecode
            from .contracts.vib_collaboration import VIBCollaborationClient

            self._collaboration_client = VIBCollaborationClient(
                web3_client=self.web3,
                config=self.config,
                contract_address=self.config.get_contract_address("VIBCollaboration"),
                abi=load_abi_and_bytecode("VIBCollaboration")[0],
            )
        return self._collaboration_client

    @property
    def joint_order(self) -> JointOrderClient:
        """获取联合订单客户端"""
        if self._joint_order_client is None:
            from .contracts.abi_loader import load_abi_and_bytecode
            from .contracts.joint_order import JointOrderClient

            self._joint_order_client = JointOrderClient(
                web3_client=self.web3,
                config=self.config,
                contract_address=self.config.get_contract_address("JointOrder"),
                abi=load_abi_and_bytecode("JointOrder")[0],
            )
        return self._joint_order_client

    @property
    def agent_manager(self) -> AgentManager:
        """获取Agent管理器"""
        if self._agent_manager is None:
            self._agent_manager = AgentManager(config=self.config)
        return self._agent_manager

    @property
    def key_manager(self) -> AgentKeyManager:
        """获取密钥管理器"""
        if self._key_manager is None:
            self._key_manager = AgentKeyManager()
        return self._key_manager

    @property
    def event_listener(self) -> BlockchainEventListener:
        """获取事件监听器"""
        from web3 import Web3

        from .contracts.abi_loader import load_abi_and_bytecode
        from .event_listener import BlockchainEventListener

        if not hasattr(self, '_event_listener') or self._event_listener is None:
            web3 = Web3(Web3.HTTPProvider(self.config.rpc_url))
            contracts = {}

            # 加载所有合约
            for contract_name in [
                "VIBEToken", "AgentRegistry", "VIBStaking",
                "VIBDividend", "VIBGovernance", "VIBCollaboration",
                "JointOrder"
            ]:
                try:
                    address = self.config.get_contract_address(contract_name)
                    abi = load_abi_and_bytecode(contract_name)[0]
                    if address and abi:
                        contracts[contract_name] = web3.eth.contract(
                            address=Web3.to_checksum_address(address),
                            abi=abi
                        )
                except Exception as e:
                    logger.warning(f"Failed to load contract {contract_name}: {e}")

            self._event_listener = BlockchainEventListener(self.config, contracts)

        return self._event_listener

    def get_wallet_client(self, wallet_address: str) -> AgentWalletClient:
        """
        获取指定钱包的客户端

        Args:
            wallet_address: AgentWallet合约地址

        Returns:
            AgentWalletClient实例
        """
        from .contracts.abi_loader import load_abi_and_bytecode
        from .contracts.agent_wallet import AgentWalletClient

        return AgentWalletClient(
            web3_client=self.web3,
            config=self.config,
            contract_address=wallet_address,
            abi=load_abi_and_bytecode("AgentWallet")[0],
        )

    async def check_can_create_agent(self, owner: str) -> dict[str, Any]:
        """
        检查Owner是否可以创建新Agent

        Args:
            owner: Owner地址

        Returns:
            字典包含：
            - can_create: 是否可以创建
            - current: 当前Agent数量
            - limit: Agent数量限制
            - remaining: 剩余可创建数量
            - reason: 不能创建的原因（如适用）

        Example:
            >>> client = VIBEBlockchainClient()
            >>> result = await client.check_can_create_agent("0x...")
            >>> if result['can_create']:
            ...     print(f"Can create {result['remaining']} more agents")
        """
        return await self.agent_manager.check_can_create_agent(owner)

    async def get_agent_full_status(
        self,
        agent_address: str,
        wallet_address: str,
    ) -> dict[str, Any]:
        """
        获取Agent完整状态

        Args:
            agent_address: Agent的EOA地址
            wallet_address: AgentWallet合约地址

        Returns:
            字典包含Agent的完整状态信息

        Example:
            >>> client = VIBEBlockchainClient()
            >>> status = await client.get_agent_full_status(
            ...     agent_address="0x...",
            ...     wallet_address="0x...",
            ... )
            >>> print(f"Balance: {status['wallet_balance']} VIBE")
        """
        return await self.agent_manager.get_agent_full_status(agent_address, wallet_address)

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
    ) -> dict[str, Any]:
        """
        创建新Agent

        Args:
            owner_address: Owner的EOA地址
            owner_private_key: Owner的私钥
            agent_name: Agent名称
            agent_metadata: Agent元数据（JSON字符串）
            initial_deposit: 初始充值金额（wei单位）
            register_identity: 是否注册身份
            agent_address: Agent地址（如不指定则自动生成）
            agent_private_key: Agent私钥（如不指定则自动生成）
            encryption_key: 加密密钥（用于加密私钥）

        Returns:
            创建结果字典

        Example:
            >>> client = VIBEBlockchainClient()
            >>> result = await client.create_agent(
            ...     owner_address="0x...",
            ...     owner_private_key="...",
            ...     agent_name="MyAgent",
            ...     initial_deposit=100 * 10**18,
            ... )
            >>> print(f"Wallet: {result['wallet_address']}")
        """
        return await self.agent_manager.create_agent(
            owner_address=owner_address,
            owner_private_key=owner_private_key,
            agent_name=agent_name,
            agent_metadata=agent_metadata,
            initial_deposit=initial_deposit,
            register_identity=register_identity,
            agent_address=agent_address,
            agent_private_key=agent_private_key,
            encryption_key=encryption_key,
        )

    def test_connection(self) -> dict[str, Any]:
        """
        测试区块链连接

        Returns:
            连接测试结果

        Example:
            >>> client = VIBEBlockchainClient()
            >>> result = client.test_connection()
            >>> print(f"Connected: {result['connected']}")
            >>> print(f"Chain ID: {result['chain_id']}")
        """
        return self.web3.test_connection()

    def get_explorer_url(self, tx_hash: str) -> str:
        """
        获取交易的区块浏览器URL

        Args:
            tx_hash: 交易哈希

        Returns:
            区块浏览器URL
        """
        return self.config.get_explorer_url(tx_hash)

    def get_address_url(self, address: str) -> str:
        """
        获取地址的区块浏览器URL

        Args:
            address: 以太坊地址

        Returns:
            区块浏览器URL
        """
        return self.config.get_address_url(address)

    def __repr__(self) -> str:
        return (
            f"VIBEBlockchainClient("
            f"network={self.config.network_name!r}, "
            f"chain_id={self.config.chain_id}"
            f")"
        )


__all__ = [
    # 配置
    "NetworkType",
    "NetworkConfig",
    "BlockchainConfig",
    "get_default_config",
    # Web3客户端
    "Web3Client",
    # 基础类
    "BaseContractClient",
    "TransactionError",
    "ContractError",
    # 代币客户端
    "VIBETokenClient",
    # 钱包
    "AgentWalletFactory",
    "AgentWalletClient",
    # 注册表
    "AgentRegistryClient",
    # 身份
    "VIBIdentityClient",
    "IdentityType",
    # 质押
    "VIBStakingClient",
    "StakeTier",
    "LockPeriod",
    # 分红
    "VIBDividendClient",
    # 治理
    "VIBGovernanceClient",
    "ProposalType",
    "ProposalState",
    "VetoType",
    # 协作
    "VIBCollaborationClient",
    # 联合订单
    "JointOrderClient",
    "PoolStatus",
    # 密钥管理
    "AgentKeyManager",
    # Agent管理
    "AgentManager",
    "AgentCreationError",
    # 事件监听
    "BlockchainEventListener",
    "ParsedEvent",
    "EventFilter",
    "EventFilterBuilder",
    "TypedEventListener",
    "create_event_listener",
    "filter_events",
    "EventCallback",
    "AsyncEventCallback",
    # 统一入口
    "VIBEBlockchainClient",
]
