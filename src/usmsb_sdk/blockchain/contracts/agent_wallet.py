"""
AgentWallet合约客户端模块

提供AgentWallet智能合约的交互接口，包括：
- 钱包部署（通过工厂）
- 余额查询
- 充值操作
- Agent执行转账
- 大额转账审批流程
- 质押操作
- 限额管理
- 紧急功能
"""

from typing import Any

from eth_account import Account
from web3 import Web3

from ..config import BlockchainConfig
from .abi_loader import load_abi_and_bytecode
from .base import BaseContractClient, ContractError, TransactionError


class AgentWalletFactory:
    """AgentWallet合约工厂

    用于部署新的AgentWallet合约实例。
    """

    def __init__(
        self,
        web3: Web3,
        bytecode: str,
        abi: list,
        config: BlockchainConfig,
        contract_addresses: dict[str, str],
    ):
        """
        初始化AgentWallet工厂

        Args:
            web3: Web3实例
            bytecode: 合约字节码
            abi: 合约ABI
            config: 区块链配置
            contract_addresses: 已部署的合约地址字典
        """
        self.web3 = web3
        self.bytecode = bytecode
        self.abi = abi
        self.config = config
        self.contract_addresses = contract_addresses

        # 创建合约实例（用于构建交易）
        self.contract = web3.eth.contract(abi=abi, bytecode=bytecode)

    async def deploy_wallet(
        self,
        owner_address: str,
        agent_address: str,
        from_address: str,
        private_key: str,
        vibe_token_address: str | None = None,
        registry_address: str | None = None,
        staking_address: str | None = None,
        gas: int | None = None,
    ) -> tuple[str, str]:
        """
        部署新的AgentWallet合约

        Args:
            owner_address: Owner的EOA地址（所有者）
            agent_address: Agent的EOA地址（后端服务地址）
            from_address: 部署者地址（支付gas）
            private_key: 部署者私钥
            vibe_token_address: VIBEToken合约地址（如不指定则从配置获取）
            registry_address: AgentRegistry合约地址（如不指定则从配置获取）
            staking_address: VIBStaking合约地址（如不指定则从配置获取）
            gas: 可选的gas限制

        Returns:
            (wallet_address, tx_hash) 元组

        Raises:
            ContractError: 合约参数无效
            TransactionError: 交易失败

        Note:
            合约constructor参数：
            - _owner: Owner的EOA地址
            - _agent: Agent后端服务的EOA地址
            - _vibeToken: VIBEToken地址
            - _registry: AgentRegistry地址
            - _stakingContract: VIBStaking地址（可为零地址）
        """
        # 验证地址
        checksum_owner = self.web3.to_checksum_address(owner_address)
        checksum_agent = self.web3.to_checksum_address(agent_address)

        if checksum_owner == "0x0000000000000000000000000000000000000000":
            raise ContractError("Invalid owner address: zero address")
        if checksum_agent == "0x0000000000000000000000000000000000000000":
            raise ContractError("Invalid agent address: zero address")

        # 从配置或参数获取合约地址
        vibe_token = vibe_token_address or self.contract_addresses.get("VIBEToken")
        registry = registry_address or self.contract_addresses.get("AgentRegistry")
        staking = staking_address or self.contract_addresses.get(
            "VIBStaking", "0x0000000000000000000000000000000000000000"
        )

        if not vibe_token:
            raise ContractError("VIBEToken address not provided")

        # 构建部署交易
        checksum_from = self.web3.to_checksum_address(from_address)

        constructor = self.contract.constructor(
            _owner=checksum_owner,
            _agent=checksum_agent,
            _vibeToken=self.web3.to_checksum_address(vibe_token),
            _registry=(
                self.web3.to_checksum_address(registry)
                if registry else "0x0000000000000000000000000000000000000000"
            ),
            _stakingContract=(
                self.web3.to_checksum_address(staking)
                if staking else "0x0000000000000000000000000000000000000000"
            ),
        )

        # 估算gas
        if gas is None:
            gas = constructor.estimate_gas({"from": checksum_from})

        # 构建交易
        tx_data = constructor.build_transaction({
            "from": checksum_from,
            "gas": gas,
            "nonce": self.web3.eth.get_transaction_count(checksum_from),
            "chainId": self.config.chain_id,
        })

        # 签名交易
        account = Account.from_key(private_key)
        signed_tx = account.sign_transaction(tx_data)

        # 发送交易
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_hash_hex = self.web3.to_hex(tx_hash)

        # 等待交易确认并获取合约地址
        try:
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash_hex, timeout=120)
            if receipt.status == 1:
                contract_address = receipt.contractAddress
                return contract_address, tx_hash_hex
            else:
                raise TransactionError(f"Transaction failed: {tx_hash_hex}")
        except Exception as e:
            raise TransactionError(f"Transaction error: {e}")

    @classmethod
    def from_config(
        cls,
        config: BlockchainConfig,
        contract_addresses: dict[str, str] | None = None,
        bytecode: str | None = None,
        abi: list | None = None,
    ) -> "AgentWalletFactory":
        """
        从配置创建工厂实例

        Args:
            config: 区块链配置
            contract_addresses: 已部署的合约地址字典（如不指定则从配置获取）
            bytecode: 合约字节码（如不指定则自动加载）
            abi: 合约ABI（如不指定则自动加载）

        Returns:
            AgentWalletFactory实例
        """
        from ..web3_client import Web3Client

        web3_client = Web3Client(config=config)
        addresses = contract_addresses or config.contracts

        if bytecode is None or abi is None:
            abi, bytecode = load_abi_and_bytecode("AgentWallet")

        return cls(
            web3=web3_client.w3,
            bytecode=bytecode,
            abi=abi,
            config=config,
            contract_addresses=addresses,
        )


class AgentWalletClient(BaseContractClient):
    """AgentWallet合约客户端

    提供完整的AgentWallet交互功能，包括：
    - 余额查询
    - 充值操作
    - Agent转账（executeTransfer）
    - 大额转账审批流程（requestTransfer/approveTransfer/rejectTransfer）
    - 质押操作
    - 限额查询
    - 紧急功能（暂停、紧急提取）
    """

    # 质押等级枚举
    TIER_BRONZE = 0
    TIER_SILVER = 1
    TIER_GOLD = 2
    TIER_PLATINUM = 3

    # 质押等级名称
    TIER_NAMES = {
        0: "Bronze",
        1: "Silver",
        2: "Gold",
        3: "Platinum",
    }

    # 等级对应的折扣百分比
    TIER_DISCOUNTS = {
        0: 0,    # Bronze: 0%
        1: 5,    # Silver: 5%
        2: 10,   # Gold: 10%
        3: 20,   # Platinum: 20%
    }

    # 等级对应的Agent数量限制
    TIER_AGENT_LIMITS = {
        0: 1,    # Bronze: 1个Agent
        1: 3,    # Silver: 3个Agent
        2: 10,   # Gold: 10个Agent
        3: 50,   # Platinum: 50个Agent
    }

    def __init__(
        self,
        web3_client=None,
        config=None,
        contract_address: str | None = None,
        abi: Any | None = None,
    ):
        """
        初始化AgentWallet客户端

        Args:
            web3_client: Web3客户端实例
            config: 区块链配置
            contract_address: AgentWallet合约地址
            abi: 合约ABI（如不指定则自动加载）
        """
        super().__init__(
            web3_client=web3_client,
            config=config,
            contract_address=contract_address,
            abi=abi,
        )

    async def get_balance(self) -> int:
        """
        获取钱包VIBE余额（wei单位）

        Returns:
            余额（wei单位）

        Example:
            >>> client = AgentWalletClient(...)
            >>> balance = await client.get_balance()
            >>> print(f"Balance: {balance} wei")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        balance = await self.call_contract_function(
            self.contract.functions.getBalance()
        )
        return int(balance)

    async def get_balance_vibe(self) -> float:
        """
        获取钱包VIBE余额（VIBE单位）

        Returns:
            余额（VIBE单位）

        Example:
            >>> client = AgentWalletClient(...)
            >>> balance = await client.get_balance_vibe()
            >>> print(f"Balance: {balance:.2f} VIBE")
        """
        balance_wei = await self.get_balance()
        return float(self.w3.from_wei(balance_wei, "ether"))

    async def deposit(
        self,
        amount: int,
        from_address: str,
        private_key: str,
        gas: int | None = None,
    ) -> str:
        """
        充值VIBE到钱包

        注意：调用前需要先approve钱包地址。

        Args:
            amount: 充值金额（wei单位）
            from_address: 充值方地址
            private_key: 充值方私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> # 首先approve
            >>> token_client.approve(wallet_address, amount, from_address, private_key)
            >>> # 然后充值
            >>> client = AgentWalletClient(...)
            >>> tx_hash = await client.deposit(amount, from_address, private_key)
            >>> print(f"Deposit tx: {tx_hash}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_from = self.w3.to_checksum_address(from_address)

        # 构建充值交易
        tx = self.build_contract_transaction(
            self.contract.functions.deposit(amount),
            from_address=checksum_from,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, private_key)
        return tx_hash

    async def execute_transfer(
        self,
        to: str,
        amount: int,
        agent_address: str,
        agent_private_key: str,
        gas: int | None = None,
    ) -> str:
        """
        Agent执行转账

        只能由Agent地址调用（onlyAgent修饰符）。
        受单笔限额和每日限额限制。

        Args:
            to: 目标地址
            amount: 转账金额（wei单位）
            agent_address: Agent的EOA地址
            agent_private_key: Agent的私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = AgentWalletClient(...)
            >>> tx_hash = await client.execute_transfer(
            ...     to="0x...",
            ...     amount=100 * 10**18,
            ...     agent_address="0x...",
            ...     agent_private_key="..."
            ... )
            >>> print(f"Transfer tx: {tx_hash}")

        Raises:
            TransactionError: 转账失败（如超限额、地址不允许等）
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_to = self.w3.to_checksum_address(to)
        checksum_agent = self.w3.to_checksum_address(agent_address)

        # 构建转账交易
        tx = self.build_contract_transaction(
            self.contract.functions.executeTransfer(checksum_to, amount),
            from_address=checksum_agent,
            gas=gas,
        )

        # 签名并发送交易（使用Agent私钥）
        tx_hash = self.sign_and_send_transaction(tx, agent_private_key)
        return tx_hash

    async def request_transfer(
        self,
        to: str,
        amount: int,
        agent_address: str,
        agent_private_key: str,
        gas: int | None = None,
    ) -> str:
        """
        请求大额转账（需要Owner审批）

        超过限额的转账需要先创建请求，然后由Owner审批。
        只能由Agent地址调用。

        Args:
            to: 目标地址
            amount: 转账金额（wei单位）
            agent_address: Agent的EOA地址
            agent_private_key: Agent的私钥
            gas: 可选的gas限制

        Returns:
            请求ID（bytes32十六进制字符串）

        Example:
            >>> client = AgentWalletClient(...)
            >>> request_id = await client.request_transfer(
            ...     to="0x...",
            ...     amount=5000 * 10**18,
            ...     agent_address="0x...",
            ...     agent_private_key="..."
            ... )
            >>> print(f"Request ID: {request_id}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_to = self.w3.to_checksum_address(to)
        checksum_agent = self.w3.to_checksum_address(agent_address)

        # 构建请求交易
        tx = self.build_contract_transaction(
            self.contract.functions.requestTransfer(checksum_to, amount),
            from_address=checksum_agent,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, agent_private_key)

        # 从交易日志中提取requestId（简化处理，实际需要解析事件）
        # 这里返回交易哈希，实际应用中需要解析TransferRequested事件
        return tx_hash

    async def approve_transfer(
        self,
        request_id: str,
        owner_address: str,
        owner_private_key: str,
        gas: int | None = None,
    ) -> str:
        """
        Owner批准转账请求

        批准后会自动执行转账。

        Args:
            request_id: 转账请求ID（bytes32）
            owner_address: Owner的EOA地址
            owner_private_key: Owner的私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = AgentWalletClient(...)
            >>> tx_hash = await client.approve_transfer(
            ...     request_id="0x123...",
            ...     owner_address="0x...",
            ...     owner_private_key="..."
            ... )
            >>> print(f"Approve tx: {tx_hash}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_owner = self.w3.to_checksum_address(owner_address)

        # 确保request_id是bytes32格式
        if isinstance(request_id, str):
            request_id_bytes = self.w3.to_bytes(hexstr=request_id)
        else:
            request_id_bytes = request_id

        # 构建批准交易
        tx = self.build_contract_transaction(
            self.contract.functions.approveTransfer(request_id_bytes),
            from_address=checksum_owner,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, owner_private_key)
        return tx_hash

    async def reject_transfer(
        self,
        request_id: str,
        owner_address: str,
        owner_private_key: str,
        gas: int | None = None,
    ) -> str:
        """
        Owner拒绝转账请求

        Args:
            request_id: 转账请求ID（bytes32）
            owner_address: Owner的EOA地址
            owner_private_key: Owner的私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = AgentWalletClient(...)
            >>> tx_hash = await client.reject_transfer(
            ...     request_id="0x123...",
            ...     owner_address="0x...",
            ...     owner_private_key="..."
            ... )
            >>> print(f"Reject tx: {tx_hash}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_owner = self.w3.to_checksum_address(owner_address)

        # 确保request_id是bytes32格式
        if isinstance(request_id, str):
            request_id_bytes = self.w3.to_bytes(hexstr=request_id)
        else:
            request_id_bytes = request_id

        # 构建拒绝交易
        tx = self.build_contract_transaction(
            self.contract.functions.rejectTransfer(request_id_bytes),
            from_address=checksum_owner,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, owner_private_key)
        return tx_hash

    async def get_remaining_limit(self) -> int:
        """
        获取剩余每日限额（wei单位）

        Returns:
            剩余可用限额（wei单位）

        Example:
            >>> client = AgentWalletClient(...)
            >>> remaining = await client.get_remaining_limit()
            >>> print(f"Remaining: {remaining} wei")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        remaining = await self.call_contract_function(
            self.contract.functions.getRemainingDailyLimit()
        )
        return int(remaining)

    async def get_remaining_limit_vibe(self) -> float:
        """
        获取剩余每日限额（VIBE单位）

        Returns:
            剩余可用限额（VIBE单位）

        Example:
            >>> client = AgentWalletClient(...)
            >>> remaining = await client.get_remaining_limit_vibe()
            >>> print(f"Remaining: {remaining:.2f} VIBE")
        """
        remaining_wei = await self.get_remaining_limit()
        return float(self.w3.from_wei(remaining_wei, "ether"))

    async def get_staking_tier(self) -> int:
        """
        获取质押等级

        Returns:
            质押等级索引 (0=Bronze, 1=Silver, 2=Gold, 3=Platinum)

        Example:
            >>> client = AgentWalletClient(...)
            >>> tier = await client.get_staking_tier()
            >>> print(f"Tier: {AgentWalletClient.TIER_NAMES[tier]}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        tier = await self.call_contract_function(
            self.contract.functions.getStakingTier()
        )
        return int(tier)

    async def get_staking_tier_name(self) -> str:
        """
        获取质押等级名称

        Returns:
            质押等级名称（如 "Bronze", "Silver"）

        Example:
            >>> client = AgentWalletClient(...)
            >>> tier_name = await client.get_staking_tier_name()
            >>> print(f"Tier: {tier_name}")
        """
        tier = await self.get_staking_tier()
        return self.TIER_NAMES.get(tier, "Unknown")

    async def get_daily_limit(self) -> int:
        """
        获取每日限额（wei单位）

        Returns:
            每日限额（wei单位）

        Example:
            >>> client = AgentWalletClient(...)
            >>> limit = await client.get_daily_limit()
            >>> print(f"Daily limit: {limit} wei")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        limit = await self.call_contract_function(
            self.contract.functions.dailyLimit()
        )
        return int(limit)

    async def get_daily_limit_vibe(self) -> float:
        """
        获取每日限额（VIBE单位）

        Returns:
            每日限额（VIBE单位）

        Example:
            >>> client = AgentWalletClient(...)
            >>> limit = await client.get_daily_limit_vibe()
            >>> print(f"Daily limit: {limit:.2f} VIBE")
        """
        limit_wei = await self.get_daily_limit()
        return float(self.w3.from_wei(limit_wei, "ether"))

    async def get_max_per_tx(self) -> int:
        """
        获取单笔限额（wei单位）

        Returns:
            单笔最大限额（wei单位）

        Example:
            >>> client = AgentWalletClient(...)
            >>> max_per_tx = await client.get_max_per_tx()
            >>> print(f"Max per tx: {max_per_tx} wei")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        max_per_tx = await self.call_contract_function(
            self.contract.functions.maxPerTx()
        )
        return int(max_per_tx)

    async def get_max_per_tx_vibe(self) -> float:
        """
        获取单笔限额（VIBE单位）

        Returns:
            单笔最大限额（VIBE单位）

        Example:
            >>> client = AgentWalletClient(...)
            >>> max_per_tx = await client.get_max_per_tx_vibe()
            >>> print(f"Max per tx: {max_per_tx:.2f} VIBE")
        """
        max_wei = await self.get_max_per_tx()
        return float(self.w3.from_wei(max_wei, "ether"))

    async def get_daily_spent(self) -> int:
        """
        获取今日已转账金额（wei单位）

        Returns:
            今日已转账金额（wei单位）

        Example:
            >>> client = AgentWalletClient(...)
            >>> spent = await client.get_daily_spent()
            >>> print(f"Spent today: {spent} wei")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        spent = await self.call_contract_function(
            self.contract.functions.getDailySpent()
        )
        return int(spent)

    async def get_staked_amount(self) -> int:
        """
        获取质押金额（wei单位）

        Returns:
            质押金额（wei单位）

        Example:
            >>> client = AgentWalletClient(...)
            >>> staked = await client.get_staked_amount()
            >>> print(f"Staked: {staked} wei")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        staked = await self.call_contract_function(
            self.contract.functions.getStakedAmount()
        )
        return int(staked)

    async def get_staked_amount_vibe(self) -> float:
        """
        获取质押金额（VIBE单位）

        Returns:
            质押金额（VIBE单位）

        Example:
            >>> client = AgentWalletClient(...)
            >>> staked = await client.get_staked_amount_vibe()
            >>> print(f"Staked: {staked:.2f} VIBE")
        """
        staked_wei = await self.get_staked_amount()
        return float(self.w3.from_wei(staked_wei, "ether"))

    async def get_agent_limit(self) -> int:
        """
        获取当前质押等级对应的Agent数量限制

        Returns:
            Agent数量限制

        Example:
            >>> client = AgentWalletClient(...)
            >>> limit = await client.get_agent_limit()
            >>> print(f"Agent limit: {limit}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        limit = await self.call_contract_function(
            self.contract.functions.getAgentLimit()
        )
        return int(limit)

    async def get_discount(self) -> int:
        """
        获取当前质押等级对应的折扣百分比

        Returns:
            折扣百分比（如5表示5%）

        Example:
            >>> client = AgentWalletClient(...)
            >>> discount = await client.get_discount()
            >>> print(f"Discount: {discount}%")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        discount = await self.call_contract_function(
            self.contract.functions.getDiscount()
        )
        return int(discount)

    async def get_owner(self) -> str:
        """
        获取钱包Owner地址

        Returns:
            Owner地址

        Example:
            >>> client = AgentWalletClient(...)
            >>> owner = await client.get_owner()
            >>> print(f"Owner: {owner}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        owner = await self.call_contract_function(
            self.contract.functions.owner()
        )
        return self.w3.to_checksum_address(owner)

    async def get_agent(self) -> str:
        """
        获取Agent地址

        Returns:
            Agent地址

        Example:
            >>> client = AgentWalletClient(...)
            >>> agent = await client.get_agent()
            >>> print(f"Agent: {agent}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        agent = await self.call_contract_function(
            self.contract.functions.agent()
        )
        return self.w3.to_checksum_address(agent)

    async def pause(
        self,
        owner_address: str,
        owner_private_key: str,
        gas: int | None = None,
    ) -> str:
        """
        暂停钱包（Owner调用）

        暂停后所有转账操作都会失败，只有Owner可以恢复。

        Args:
            owner_address: Owner的EOA地址
            owner_private_key: Owner的私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = AgentWalletClient(...)
            >>> tx_hash = await client.pause(owner_address, owner_private_key)
            >>> print(f"Pause tx: {tx_hash}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_owner = self.w3.to_checksum_address(owner_address)

        # 构建暂停交易
        tx = self.build_contract_transaction(
            self.contract.functions.pause(),
            from_address=checksum_owner,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, owner_private_key)
        return tx_hash

    async def unpause(
        self,
        owner_address: str,
        owner_private_key: str,
        gas: int | None = None,
    ) -> str:
        """
        恢复钱包（Owner调用）

        Args:
            owner_address: Owner的EOA地址
            owner_private_key: Owner的私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = AgentWalletClient(...)
            >>> tx_hash = await client.unpause(owner_address, owner_private_key)
            >>> print(f"Unpause tx: {tx_hash}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_owner = self.w3.to_checksum_address(owner_address)

        # 构建恢复交易
        tx = self.build_contract_transaction(
            self.contract.functions.unpause(),
            from_address=checksum_owner,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, owner_private_key)
        return tx_hash

    async def update_limits(
        self,
        max_per_tx: int,
        daily_limit: int,
        owner_address: str,
        owner_private_key: str,
        gas: int | None = None,
    ) -> str:
        """
        更新限额（仅Owner）

        Args:
            max_per_tx: 新的单笔限额（wei单位）
            daily_limit: 新的每日限额（wei单位）
            owner_address: Owner的EOA地址
            owner_private_key: Owner的私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = AgentWalletClient(...)
            >>> tx_hash = await client.update_limits(
            ...     max_per_tx=1000 * 10**18,
            ...     daily_limit=5000 * 10**18,
            ...     owner_address="0x...",
            ...     owner_private_key="..."
            ... )
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_owner = self.w3.to_checksum_address(owner_address)

        # 构建更新限额交易
        tx = self.build_contract_transaction(
            self.contract.functions.updateLimits(max_per_tx, daily_limit),
            from_address=checksum_owner,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, owner_private_key)
        return tx_hash

    async def update_whitelist(
        self,
        addr: str,
        allowed: bool,
        owner_address: str,
        owner_private_key: str,
        gas: int | None = None,
    ) -> str:
        """
        更新白名单（仅Owner）

        Args:
            addr: 要更新的地址
            allowed: 是否允许
            owner_address: Owner的EOA地址
            owner_private_key: Owner的私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = AgentWalletClient(...)
            >>> tx_hash = await client.update_whitelist(
            ...     addr="0x...",
            ...     allowed=True,
            ...     owner_address="0x...",
            ...     owner_private_key="..."
            ... )
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_owner = self.w3.to_checksum_address(owner_address)
        checksum_addr = self.w3.to_checksum_address(addr)

        # 构建更新白名单交易
        tx = self.build_contract_transaction(
            self.contract.functions.updateWhitelist(checksum_addr, allowed),
            from_address=checksum_owner,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, owner_private_key)
        return tx_hash

    async def stake(
        self,
        amount: int,
        lock_period: int,
        caller_address: str,
        caller_private_key: str,
        gas: int | None = None,
    ) -> str:
        """
        质押VIBE代币

        锁仓期索引：0=无锁仓, 1=1月, 2=3月, 3=6月, 4=1年

        Args:
            amount: 质押金额（wei单位）
            lock_period: 锁仓期索引（0-4）
            caller_address: 调用者地址（Agent或Owner）
            caller_private_key: 调用者私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = AgentWalletClient(...)
            >>> tx_hash = await client.stake(
            ...     amount=1000 * 10**18,
            ...     lock_period=3,  # 6个月
            ...     caller_address="0x...",
            ...     caller_private_key="..."
            ... )
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_caller = self.w3.to_checksum_address(caller_address)

        # 构建质押交易
        tx = self.build_contract_transaction(
            self.contract.functions.stake(amount, lock_period),
            from_address=checksum_caller,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, caller_private_key)
        return tx_hash

    async def unstake(
        self,
        caller_address: str,
        caller_private_key: str,
        gas: int | None = None,
    ) -> str:
        """
        取消质押

        Args:
            caller_address: 调用者地址（Agent或Owner）
            caller_private_key: 调用者私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = AgentWalletClient(...)
            >>> tx_hash = await client.unstake(
            ...     caller_address="0x...",
            ...     caller_private_key="..."
            ... )
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_caller = self.w3.to_checksum_address(caller_address)

        # 构建取消质押交易
        tx = self.build_contract_transaction(
            self.contract.functions.unstake(),
            from_address=checksum_caller,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, caller_private_key)
        return tx_hash

    async def claim_staking_reward(
        self,
        caller_address: str,
        caller_private_key: str,
        gas: int | None = None,
    ) -> str:
        """
        领取质押奖励

        Args:
            caller_address: 调用者地址（Agent或Owner）
            caller_private_key: 调用者私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = AgentWalletClient(...)
            >>> tx_hash = await client.claim_staking_reward(
            ...     caller_address="0x...",
            ...     caller_private_key="..."
            ... )
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_caller = self.w3.to_checksum_address(caller_address)

        # 构建领取奖励交易
        tx = self.build_contract_transaction(
            self.contract.functions.claimStakingReward(),
            from_address=checksum_caller,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, caller_private_key)
        return tx_hash

    async def emergency_withdraw(
        self,
        token: str,
        to: str,
        amount: int,
        owner_address: str,
        owner_private_key: str,
        gas: int | None = None,
    ) -> str:
        """
        发起紧急提取（需要时间锁）

        需要2天后才能确认提取。

        Args:
            token: 代币地址（address(0)表示ETH）
            to: 接收地址
            amount: 提取金额（wei单位）
            owner_address: Owner的EOA地址
            owner_private_key: Owner的私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = AgentWalletClient(...)
            >>> tx_hash = await client.emergency_withdraw(
            ...     token="0x...",  # VIBE token address or zero address for ETH
            ...     to=owner_address,
            ...     amount=balance,
            ...     owner_address="0x...",
            ...     owner_private_key="..."
            ... )
            >>> # 等待2天后调用confirm_emergency_withdraw()
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_owner = self.w3.to_checksum_address(owner_address)
        checksum_token = self.w3.to_checksum_address(token)
        checksum_to = self.w3.to_checksum_address(to)

        # 构建紧急提取交易
        tx = self.build_contract_transaction(
            self.contract.functions.emergencyWithdraw(checksum_token, checksum_to, amount),
            from_address=checksum_owner,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, owner_private_key)
        return tx_hash

    async def confirm_emergency_withdraw(
        self,
        owner_address: str,
        owner_private_key: str,
        gas: int | None = None,
    ) -> str:
        """
        确认紧急提取（在时间锁到期后调用）

        Args:
            owner_address: Owner的EOA地址
            owner_private_key: Owner的私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = AgentWalletClient(...)
            >>> tx_hash = await client.confirm_emergency_withdraw(
            ...     owner_address="0x...",
            ...     owner_private_key="..."
            ... )
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_owner = self.w3.to_checksum_address(owner_address)

        # 构建确认提取交易
        tx = self.build_contract_transaction(
            self.contract.functions.confirmEmergencyWithdraw(),
            from_address=checksum_owner,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, owner_private_key)
        return tx_hash

    async def cancel_emergency_withdraw(
        self,
        owner_address: str,
        owner_private_key: str,
        gas: int | None = None,
    ) -> str:
        """
        取消待生效的紧急提取

        Args:
            owner_address: Owner的EOA地址
            owner_private_key: Owner的私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = AgentWalletClient(...)
            >>> tx_hash = await client.cancel_emergency_withdraw(
            ...     owner_address="0x...",
            ...     owner_private_key="..."
            ... )
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_owner = self.w3.to_checksum_address(owner_address)

        # 构建取消交易
        tx = self.build_contract_transaction(
            self.contract.functions.cancelEmergencyWithdraw(),
            from_address=checksum_owner,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, owner_private_key)
        return tx_hash

    @classmethod
    def from_config(
        cls,
        config=None,
        contract_address: str | None = None,
        abi: Any | None = None,
    ) -> "AgentWalletClient":
        """
        从配置创建客户端实例

        Args:
            config: 区块链配置（如不指定则使用默认配置）
            contract_address: AgentWallet合约地址
            abi: 合约ABI（如不指定则自动加载）

        Returns:
            AgentWalletClient实例

        Example:
            >>> from ..config import get_default_config
            >>> config = get_default_config()
            >>> client = AgentWalletClient.from_config(
            ...     config=config,
            ...     contract_address="0x..."
            ... )
        """
        if config is None:
            from ..config import get_default_config
            config = get_default_config()

        if abi is None:
            abi = load_abi_and_bytecode("AgentWallet")[0]

        return cls(
            config=config,
            contract_address=contract_address,
            abi=abi,
        )


__all__ = [
    "AgentWalletFactory",
    "AgentWalletClient",
]
