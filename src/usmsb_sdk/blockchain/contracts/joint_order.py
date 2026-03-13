"""
JointOrder 联合订单合约客户端

实现 VIBE 联合订单合约的 Python 客户端，支持：
- 创建需求池
- 提交报价
- 接受报价
- 取消需求池
- 获取需求池信息
- 获取所有报价
"""

from enum import IntEnum
from typing import List, Optional, Dict, Any, Union

from .base import BaseContractClient, TransactionError, ContractError
from ..config import BlockchainConfig
from ..web3_client import Web3Client


class PoolStatus(IntEnum):
    """需求池状态枚举"""
    CREATED = 0  # 已创建
    FUNDED = 1  # 已托管资金
    BIDDING = 2  # 竞价中
    AWARDED = 3  # 已授标
    IN_PROGRESS = 4  # 执行中
    DELIVERED = 5  # 已交付
    COMPLETED = 6  # 已完成
    DISPUTED = 7  # 争议中
    CANCELLED = 8  # 已取消
    EXPIRED = 9  # 已过期


class JointOrderClient(BaseContractClient):
    """联合订单客户端

    实现白皮书承诺的联合订单机制：
    - 多方需求聚合
    - 服务商反向竞价
    - 智能合约托管资金
    - 分批结算
    - 争议处理
    """

    # 合约常量
    MIN_POOL_BUDGET = 100 * 10**18  # 最低池预算 100 VIBE
    MAX_PARTICIPANTS = 50  # 最大参与者数量
    MAX_BIDS = 20  # 最大报价数量
    PLATFORM_FEE_RATE = 300  # 平台费率 3% (基点)
    MIN_BIDDING_DURATION = 3600  # 最短竞价时间 1小时
    MAX_BIDDING_DURATION = 604800  # 最长竞价时间 7天

    def __init__(
        self,
        web3_client: Optional[Web3Client] = None,
        config: Optional[BlockchainConfig] = None,
        contract_address: Optional[str] = None,
        abi: Optional[Union[List[Dict], str]] = None,
    ):
        """
        初始化 JointOrder 客户端

        Args:
            web3_client: Web3 客户端实例
            config: 区块链配置
            contract_address: 合约地址（如不指定则从配置中获取）
            abi: 合约 ABI（如不指定则使用内置 ABI）
        """
        super().__init__(web3_client, config)

        # 获取合约地址
        if contract_address is None:
            contract_address = self.config.get_contract_address("JointOrder")
            if contract_address is None or contract_address == "待部署":
                raise ContractError("JointOrder contract not deployed or configured")

        # 使用内置 ABI（简化版本）
        if abi is None:
            abi = self._get_default_abi()

        self.set_contract(contract_address, abi)

    def _get_default_abi(self) -> List[Dict]:
        """获取默认 ABI"""
        return [
            # 只读函数
            {
                "inputs": [{"internalType": "bytes32", "name": "poolId", "type": "bytes32"}],
                "name": "getPool",
                "outputs": [
                    {
                        "components": [
                            {"internalType": "bytes32", "name": "poolId", "type": "bytes32"},
                            {"internalType": "address", "name": "creator", "type": "address"},
                            {"internalType": "string", "name": "serviceType", "type": "string"},
                            {"internalType": "uint256", "name": "totalBudget", "type": "uint256"},
                            {"internalType": "uint256", "name": "minBudget", "type": "uint256"},
                            {"internalType": "uint256", "name": "participantCount", "type": "uint256"},
                            {"internalType": "uint256", "name": "bidCount", "type": "uint256"},
                            {"internalType": "uint256", "name": "createdAt", "type": "uint256"},
                            {"internalType": "uint256", "name": "fundingDeadline", "type": "uint256"},
                            {"internalType": "uint256", "name": "biddingEndsAt", "type": "uint256"},
                            {"internalType": "uint256", "name": "deliveryDeadline", "type": "uint256"},
                            {"internalType": "enum JointOrder.PoolStatus", "name": "status", "type": "uint8"},
                            {"internalType": "address", "name": "winningProvider", "type": "address"},
                            {"internalType": "uint256", "name": "winningBid", "type": "uint256"},
                            {"internalType": "uint256", "name": "platformFee", "type": "uint256"},
                            {"internalType": "bytes32", "name": "metadataHash", "type": "bytes32"},
                        ],
                        "internalType": "struct JointOrder.OrderPool",
                        "name": "",
                        "type": "tuple",
                    }
                ],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [{"internalType": "bytes32", "name": "poolId", "type": "bytes32"}],
                "name": "getPoolBids",
                "outputs": [{"internalType": "bytes32[]", "name": "", "type": "bytes32[]"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [
                    {"internalType": "bytes32", "name": "poolId", "type": "bytes32"},
                    {"internalType": "bytes32", "name": "bidId", "type": "bytes32"},
                ],
                "name": "getBid",
                "outputs": [
                    {
                        "components": [
                            {"internalType": "bytes32", "name": "bidId", "type": "bytes32"},
                            {"internalType": "bytes32", "name": "poolId", "type": "bytes32"},
                            {"internalType": "address", "name": "provider", "type": "address"},
                            {"internalType": "uint256", "name": "price", "type": "uint256"},
                            {"internalType": "uint256", "name": "deliveryTime", "type": "uint256"},
                            {"internalType": "uint256", "name": "reputationScore", "type": "uint256"},
                            {"internalType": "uint256", "name": "computedScore", "type": "uint256"},
                            {"internalType": "bool", "name": "isWinner", "type": "bool"},
                            {"internalType": "string", "name": "proposal", "type": "string"},
                        ],
                        "internalType": "struct JointOrder.Bid",
                        "name": "",
                        "type": "tuple",
                    }
                ],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [],
                "name": "getStats",
                "outputs": [
                    {"internalType": "uint256", "name": "_totalPoolsCreated", "type": "uint256"},
                    {"internalType": "uint256", "name": "_totalPoolsCompleted", "type": "uint256"},
                    {"internalType": "uint256", "name": "_totalVolume", "type": "uint256"},
                ],
                "stateMutability": "view",
                "type": "function",
            },
            # 写入函数
            {
                "inputs": [
                    {"internalType": "string", "name": "serviceType", "type": "string"},
                    {"internalType": "uint256", "name": "minBudget", "type": "uint256"},
                    {"internalType": "uint256", "name": "fundingDuration", "type": "uint256"},
                    {"internalType": "uint256", "name": "biddingDuration", "type": "uint256"},
                    {"internalType": "uint256", "name": "deliveryDeadline", "type": "uint256"},
                    {"internalType": "bytes32", "name": "metadataHash", "type": "bytes32"},
                ],
                "name": "createPool",
                "outputs": [{"internalType": "bytes32", "name": "poolId", "type": "bytes32"}],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [
                    {"internalType": "bytes32", "name": "poolId", "type": "bytes32"},
                    {"internalType": "uint256", "name": "price", "type": "uint256"},
                    {"internalType": "uint256", "name": "deliveryTime", "type": "uint256"},
                    {"internalType": "uint256", "name": "reputationScore", "type": "uint256"},
                    {"internalType": "string", "name": "proposal", "type": "string"},
                    {"internalType": "bytes", "name": "reputationSignature", "type": "bytes"},
                ],
                "name": "submitBid",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [
                    {"internalType": "bytes32", "name": "poolId", "type": "bytes32"},
                    {"internalType": "bytes32", "name": "bidId", "type": "bytes32"},
                ],
                "name": "awardPool",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [
                    {"internalType": "bytes32", "name": "poolId", "type": "bytes32"},
                    {"internalType": "string", "name": "reason", "type": "string"},
                ],
                "name": "cancelPool",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [
                    {"internalType": "bytes32", "name": "poolId", "type": "bytes32"},
                    {"internalType": "uint8", "name": "rating", "type": "uint8"},
                ],
                "name": "confirmDelivery",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [{"internalType": "bytes32", "name": "poolId", "type": "bytes32"}],
                "name": "withdrawEarnings",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [{"internalType": "bytes32", "name": "poolId", "type": "bytes32"}],
                "name": "claimRefund",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
        ]

    async def create_pool(
        self,
        service_type: str,
        min_budget: int,
        bidding_duration: int,
        from_address: str,
        private_key: str,
        funding_duration: Optional[int] = None,
        delivery_deadline: Optional[int] = None,
        metadata_hash: Optional[bytes] = None,
        gas_limit: Optional[int] = None,
    ) -> str:
        """创建需求池

        Args:
            service_type: 服务类型
            min_budget: 最低预算（wei）
            bidding_duration: 竞价期限（秒）
            from_address: 创建者地址
            private_key: 私钥
            funding_duration: 托管期限（秒，默认7天）
            delivery_deadline: 交付截止时间（时间戳，默认竞价后30天）
            metadata_hash: 元数据哈希
            gas_limit: 可选的 gas 限制

        Returns:
            需求池ID（bytes32的十六进制字符串）

        Raises:
            TransactionError: 交易失败
            ContractError: 合约调用失败
            ValueError: 无效的参数
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            if not service_type:
                raise ValueError("Service type cannot be empty")
            if min_budget < self.MIN_POOL_BUDGET:
                raise ValueError(
                    f"Min budget ({min_budget}) is below minimum ({self.MIN_POOL_BUDGET})"
                )
            if bidding_duration < self.MIN_BIDDING_DURATION:
                raise ValueError(
                    f"Bidding duration ({bidding_duration}) is below minimum ({self.MIN_BIDDING_DURATION})"
                )
            if bidding_duration > self.MAX_BIDDING_DURATION:
                raise ValueError(
                    f"Bidding duration ({bidding_duration}) exceeds maximum ({self.MAX_BIDDING_DURATION})"
                )

            from_address = self.w3.to_checksum_address(from_address)

            # 设置默认值
            if funding_duration is None:
                funding_duration = 7 * 86400  # 7天
            if delivery_deadline is None:
                current_time = int(self.w3.eth.get_block("latest")["timestamp"])
                delivery_deadline = current_time + funding_duration + bidding_duration + 30 * 86400
            if metadata_hash is None:
                metadata_hash = b"\x00" * 32

            # 构建交易
            tx = self.build_contract_transaction(
                self.contract.functions.createPool(
                    service_type,
                    min_budget,
                    funding_duration,
                    bidding_duration,
                    delivery_deadline,
                    metadata_hash,
                ),
                from_address=from_address,
                gas=gas_limit,
            )

            # 签名并发送
            tx_hash = self.sign_and_send_transaction(tx, private_key)

            # 等待交易并获取池ID
            receipt = self.wait_for_transaction(tx_hash, timeout=120)

            # 从事件日志中获取池ID
            if receipt.get("logs"):
                for log in receipt["logs"]:
                    if len(log.get("topics", [])) > 1:
                        # PoolCreated 事件的第一个 indexed 参数是 poolId
                        pool_id = "0x" + log["topics"][1].hex()[26:]
                        return pool_id

            raise TransactionError("Could not extract poolId from transaction logs")
        except ValueError:
            raise
        except Exception as e:
            raise TransactionError(f"Failed to create pool: {e}")

    async def submit_bid(
        self,
        pool_id: str,
        price: int,
        delivery_time: int,
        reputation: int,
        from_address: str,
        private_key: str,
        proposal: str = "",
        reputation_signature: Optional[bytes] = None,
        gas_limit: Optional[int] = None,
    ) -> str:
        """提交报价

        Args:
            pool_id: 需求池ID（bytes32的十六进制字符串）
            price: 报价（wei）
            delivery_time: 承诺交付时间（小时）
            reputation: 信誉分（0-100）
            from_address: 服务商地址
            private_key: 私钥
            proposal: 方案描述
            reputation_signature: 信誉签名
            gas_limit: 可选的 gas 限制

        Returns:
            交易哈希

        Raises:
            TransactionError: 交易失败
            ContractError: 合约调用失败
            ValueError: 无效的参数
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            if price <= 0:
                raise ValueError("Price must be greater than 0")
            if reputation > 100:
                raise ValueError("Reputation score must be <= 100")

            from_address = self.w3.to_checksum_address(from_address)

            # 检查需求池状态和预算
            pool = await self.get_pool_info(pool_id)
            if price > pool["total_budget"]:
                raise ValueError(f"Price ({price}) exceeds pool budget ({pool['total_budget']})")

            # 设置默认值
            if reputation_signature is None:
                reputation_signature = b""

            # 构建交易
            tx = self.build_contract_transaction(
                self.contract.functions.submitBid(
                    pool_id,
                    price,
                    delivery_time,
                    reputation,
                    proposal,
                    reputation_signature,
                ),
                from_address=from_address,
                gas=gas_limit,
            )

            # 签名并发送
            tx_hash = self.sign_and_send_transaction(tx, private_key)
            return tx_hash
        except ValueError:
            raise
        except Exception as e:
            raise TransactionError(f"Failed to submit bid: {e}")

    async def accept_bid(
        self,
        pool_id: str,
        bid_id: str,
        from_address: str,
        private_key: str,
        gas_limit: Optional[int] = None,
    ) -> str:
        """接受报价（授标）

        Args:
            pool_id: 需求池ID（bytes32的十六进制字符串）
            bid_id: 报价ID（bytes32的十六进制字符串）
            from_address: 调用者地址（必须是池创建者）
            private_key: 私钥
            gas_limit: 可选的 gas 限制

        Returns:
            交易哈希

        Raises:
            TransactionError: 交易失败
            ContractError: 合约调用失败
            ValueError: 无权限或状态不正确
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            from_address = self.w3.to_checksum_address(from_address)

            # 检查权限
            pool = await self.get_pool_info(pool_id)
            if from_address != pool["creator"]:
                raise ValueError("Only pool creator can award bids")

            # 检查状态
            if pool["status"] != PoolStatus.FUNDED:
                raise ValueError(f"Pool is not in FUNDED state, current state: {pool['status'].name}")

            # 确保bid_id是正确的格式
            if isinstance(bid_id, str):
                if bid_id.startswith("0x"):
                    bid_id_bytes = self.w3.to_bytes(hexstr=bid_id)
                else:
                    bid_id_bytes = bytes.fromhex(bid_id)
            else:
                bid_id_bytes = bid_id

            # 构建交易
            tx = self.build_contract_transaction(
                self.contract.functions.awardPool(pool_id, bid_id_bytes),
                from_address=from_address,
                gas=gas_limit,
            )

            # 签名并发送
            tx_hash = self.sign_and_send_transaction(tx, private_key)
            return tx_hash
        except ValueError:
            raise
        except Exception as e:
            raise TransactionError(f"Failed to accept bid: {e}")

    async def cancel_pool(
        self,
        pool_id: str,
        from_address: str,
        private_key: str,
        reason: str = "",
        gas_limit: Optional[int] = None,
    ) -> str:
        """取消需求池

        Args:
            pool_id: 需求池ID（bytes32的十六进制字符串）
            from_address: 调用者地址（池创建者或owner）
            private_key: 私钥
            reason: 取消原因
            gas_limit: 可选的 gas 限制

        Returns:
            交易哈希

        Raises:
            TransactionError: 交易失败
            ContractError: 合约调用失败
            ValueError: 无权限或状态不正确
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            from_address = self.w3.to_checksum_address(from_address)

            # 检查权限和状态
            pool = await self.get_pool_info(pool_id)
            is_creator = from_address == pool["creator"]
            is_owner = False  # 需要额外检查，这里简化处理

            if not (is_creator or is_owner):
                raise ValueError("Only pool creator or owner can cancel pool")

            if pool["status"] not in [PoolStatus.CREATED, PoolStatus.FUNDED]:
                raise ValueError(f"Pool cannot be cancelled in state: {pool['status'].name}")

            # 构建交易
            tx = self.build_contract_transaction(
                self.contract.functions.cancelPool(pool_id, reason),
                from_address=from_address,
                gas=gas_limit,
            )

            # 签名并发送
            tx_hash = self.sign_and_send_transaction(tx, private_key)
            return tx_hash
        except ValueError:
            raise
        except Exception as e:
            raise TransactionError(f"Failed to cancel pool: {e}")

    async def get_pool_info(self, pool_id: str) -> Dict[str, Any]:
        """获取需求池信息

        Args:
            pool_id: 需求池ID（bytes32的十六进制字符串）

        Returns:
            需求池信息字典：
            - pool_id: 需求池ID
            - creator: 创建者地址
            - service_type: 服务类型
            - total_budget: 总预算
            - min_budget: 最低预算
            - participant_count: 参与者数量
            - bid_count: 报价数量
            - created_at: 创建时间
            - funding_deadline: 托管截止时间
            - bidding_ends_at: 竞价截止时间
            - delivery_deadline: 交付截止时间
            - status: 状态
            - winning_provider: 中标服务商
            - winning_bid: 中标价格
            - platform_fee: 平台费用
            - metadata_hash: 元数据哈希

        Raises:
            ContractError: 合约调用失败
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            # 确保 pool_id 是正确的格式
            if isinstance(pool_id, str):
                if pool_id.startswith("0x"):
                    pool_id_bytes = self.w3.to_bytes(hexstr=pool_id)
                else:
                    pool_id_bytes = bytes.fromhex(pool_id)
            else:
                pool_id_bytes = pool_id

            result = self.call_contract_function(
                self.contract.functions.getPool(pool_id_bytes)
            )

            # 解析结构体返回值
            return {
                "pool_id": "0x" + result[0].hex(),
                "creator": result[1],
                "service_type": result[2],
                "total_budget": int(result[3]),
                "min_budget": int(result[4]),
                "participant_count": int(result[5]),
                "bid_count": int(result[6]),
                "created_at": int(result[7]),
                "funding_deadline": int(result[8]),
                "bidding_ends_at": int(result[9]),
                "delivery_deadline": int(result[10]),
                "status": PoolStatus(int(result[11])),
                "winning_provider": result[12],
                "winning_bid": int(result[13]),
                "platform_fee": int(result[14]),
                "metadata_hash": "0x" + result[15].hex(),
                "status_name": PoolStatus(int(result[11])).name,
            }
        except Exception as e:
            raise ContractError(f"Failed to get pool info: {e}")

    async def get_bids(self, pool_id: str) -> List[Dict[str, Any]]:
        """获取需求池的所有报价

        Args:
            pool_id: 需求池ID（bytes32的十六进制字符串）

        Returns:
            报价列表，每个报价包含：
            - bid_id: 报价ID
            - pool_id: 需求池ID
            - provider: 服务商地址
            - price: 报价
            - delivery_time: 承诺交付时间
            - reputation_score: 信誉分
            - computed_score: 综合评分
            - is_winner: 是否中标
            - proposal: 方案描述

        Raises:
            ContractError: 合约调用失败
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            # 确保 pool_id 是正确的格式
            if isinstance(pool_id, str):
                if pool_id.startswith("0x"):
                    pool_id_bytes = self.w3.to_bytes(hexstr=pool_id)
                else:
                    pool_id_bytes = bytes.fromhex(pool_id)
            else:
                pool_id_bytes = pool_id

            # 获取报价ID列表
            bid_ids = self.call_contract_function(
                self.contract.functions.getPoolBids(pool_id_bytes)
            )

            if not bid_ids:
                return []

            # 获取每个报价的详细信息
            bids = []
            for bid_id in bid_ids:
                bid = self.call_contract_function(
                    self.contract.functions.getBid(pool_id_bytes, bid_id)
                )
                bids.append({
                    "bid_id": "0x" + bid[0].hex(),
                    "pool_id": "0x" + bid[1].hex(),
                    "provider": bid[2],
                    "price": int(bid[3]),
                    "delivery_time": int(bid[4]),
                    "reputation_score": int(bid[5]),
                    "computed_score": int(bid[6]),
                    "is_winner": bool(bid[7]),
                    "proposal": bid[8],
                })

            return bids
        except Exception as e:
            raise ContractError(f"Failed to get bids: {e}")

    async def confirm_delivery(
        self,
        pool_id: str,
        rating: int,
        from_address: str,
        private_key: str,
        gas_limit: Optional[int] = None,
    ) -> str:
        """确认交付

        Args:
            pool_id: 需求池ID（bytes32的十六进制字符串）
            rating: 评分（1-5）
            from_address: 参与者地址
            private_key: 私钥
            gas_limit: 可选的 gas 限制

        Returns:
            交易哈希

        Raises:
            TransactionError: 交易失败
            ContractError: 合约调用失败
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            if not (1 <= rating <= 5):
                raise ValueError("Rating must be between 1 and 5")

            from_address = self.w3.to_checksum_address(from_address)

            # 构建交易
            tx = self.build_contract_transaction(
                self.contract.functions.confirmDelivery(pool_id, rating),
                from_address=from_address,
                gas=gas_limit,
            )

            # 签名并发送
            tx_hash = self.sign_and_send_transaction(tx, private_key)
            return tx_hash
        except ValueError:
            raise
        except Exception as e:
            raise TransactionError(f"Failed to confirm delivery: {e}")

    async def withdraw_earnings(
        self,
        pool_id: str,
        from_address: str,
        private_key: str,
        gas_limit: Optional[int] = None,
    ) -> str:
        """提取收益

        Args:
            pool_id: 需求池ID（bytes32的十六进制字符串）
            from_address: 服务商地址（中标者）
            private_key: 私钥
            gas_limit: 可选的 gas 限制

        Returns:
            交易哈希

        Raises:
            TransactionError: 交易失败
            ContractError: 合约调用失败
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            from_address = self.w3.to_checksum_address(from_address)

            # 构建交易
            tx = self.build_contract_transaction(
                self.contract.functions.withdrawEarnings(pool_id),
                from_address=from_address,
                gas=gas_limit,
            )

            # 签名并发送
            tx_hash = self.sign_and_send_transaction(tx, private_key)
            return tx_hash
        except Exception as e:
            raise TransactionError(f"Failed to withdraw earnings: {e}")

    async def claim_refund(
        self,
        pool_id: str,
        from_address: str,
        private_key: str,
        gas_limit: Optional[int] = None,
    ) -> str:
        """领取退款

        在池被取消后，参与者可以领取资金退款

        Args:
            pool_id: 需求池ID（bytes32的十六进制字符串）
            from_address: 参与者地址
            private_key: 私钥
            gas_limit: 可选的 gas 限制

        Returns:
            交易哈希

        Raises:
            TransactionError: 交易失败
            ContractError: 合约调用失败
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            from_address = self.w3.to_checksum_address(from_address)

            # 构建交易
            tx = self.build_contract_transaction(
                self.contract.functions.claimRefund(pool_id),
                from_address=from_address,
                gas=gas_limit,
            )

            # 签名并发送
            tx_hash = self.sign_and_send_transaction(tx, private_key)
            return tx_hash
        except Exception as e:
            raise TransactionError(f"Failed to claim refund: {e}")

    async def get_stats(self) -> Dict[str, Any]:
        """获取联合订单统计信息

        Returns:
            统计信息字典：
            - total_pools_created: 总创建池数
            - total_pools_completed: 总完成池数
            - total_volume: 总交易量

        Raises:
            ContractError: 合约调用失败
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            result = self.call_contract_function(
                self.contract.functions.getStats()
            )

            return {
                "total_pools_created": int(result[0]) if result[0] else 0,
                "total_pools_completed": int(result[1]) if result[1] else 0,
                "total_volume": int(result[2]) if result[2] else 0,
            }
        except Exception as e:
            raise ContractError(f"Failed to get stats: {e}")


__all__ = [
    "JointOrderClient",
    "PoolStatus",
]
