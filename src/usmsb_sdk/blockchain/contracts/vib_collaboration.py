"""
VIBCollaboration 协作分成合约客户端

实现 VIBE 协作分成合约的 Python 客户端，支持：
- 创建协作项目
- 添加贡献者
- 分发收入（70%产出者/20%贡献者/10%协调者）
- 获取项目信息
- 获取用户总收入
"""

from typing import List, Optional, Dict, Any, Union

from .base import BaseContractClient, TransactionError, ContractError
from ..config import BlockchainConfig
from ..web3_client import Web3Client


class VIBCollaborationClient(BaseContractClient):
    """协作分成客户端

    实现白皮书承诺的协作分成机制：
    - 最终产出者: 70%
    - 协作贡献者: 20%（按贡献度分配）
    - 协作协调者: 10%

    完全去中心化：分成由合约自动执行，不需要人工干预
    """

    # 合约常量
    PRECISION = 10000  # 精度
    PRODUCER_RATIO = 7000  # 70%
    CONTRIBUTORS_RATIO = 2000  # 20%
    COORDINATOR_RATIO = 1000  # 10%

    def __init__(
        self,
        web3_client: Optional[Web3Client] = None,
        config: Optional[BlockchainConfig] = None,
        contract_address: Optional[str] = None,
        abi: Optional[Union[List[Dict], str]] = None,
    ):
        """
        初始化 VIBCollaboration 客户端

        Args:
            web3_client: Web3 客户端实例
            config: 区块链配置
            contract_address: 合约地址（如不指定则从配置中获取）
            abi: 合约 ABI（如不指定则使用内置 ABI）
        """
        super().__init__(web3_client, config)

        # 获取合约地址
        if contract_address is None:
            contract_address = self.config.get_contract_address("VIBCollaboration")
            if contract_address is None or contract_address == "待部署":
                raise ContractError("VIBCollaboration contract not deployed or configured")

        # 使用内置 ABI（简化版本）
        if abi is None:
            abi = self._get_default_abi()

        self.set_contract(contract_address, abi)

    def _get_default_abi(self) -> List[Dict]:
        """获取默认 ABI"""
        return [
            # 只读函数
            {
                "inputs": [{"internalType": "bytes32", "name": "projectId", "type": "bytes32"}],
                "name": "getProjectInfo",
                "outputs": [
                    {
                        "components": [
                            {"internalType": "bytes32", "name": "projectId", "type": "bytes32"},
                            {"internalType": "address", "name": "finalProducer", "type": "address"},
                            {"internalType": "address", "name": "coordinator", "type": "address"},
                            {"internalType": "uint256", "name": "totalRevenue", "type": "uint256"},
                            {"internalType": "uint256", "name": "producerShare", "type": "uint256"},
                            {"internalType": "uint256", "name": "contributorsShare", "type": "uint256"},
                            {"internalType": "uint256", "name": "coordinatorShare", "type": "uint256"},
                            {"internalType": "uint256", "name": "createdAt", "type": "uint256"},
                            {"internalType": "uint256", "name": "distributedAt", "type": "uint256"},
                            {"internalType": "bool", "name": "distributed", "type": "bool"},
                            {"internalType": "bool", "name": "finalized", "type": "bool"},
                        ],
                        "internalType": "struct VIBCollaboration.CollaborationProject",
                        "name": "",
                        "type": "tuple",
                    }
                ],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [{"internalType": "bytes32", "name": "projectId", "type": "bytes32"}],
                "name": "getContributors",
                "outputs": [{"internalType": "address[]", "name": "", "type": "address[]"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [{"internalType": "bytes32", "name": "projectId", "type": "bytes32"}],
                "name": "getContributorCount",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
                "name": "getUserTotalIncome",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [],
                "name": "projectCount",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [
                    {"internalType": "bytes32", "name": "projectId", "type": "bytes32"},
                    {"internalType": "address", "name": "contributor", "type": "address"},
                ],
                "name": "contributorWeights",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            },
            # 写入函数
            {
                "inputs": [
                    {"internalType": "address", "name": "finalProducer", "type": "address"},
                    {"internalType": "address", "name": "coordinator", "type": "address"},
                ],
                "name": "createProject",
                "outputs": [{"internalType": "bytes32", "name": "projectId", "type": "bytes32"}],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [
                    {"internalType": "bytes32", "name": "projectId", "type": "bytes32"},
                    {"internalType": "address[]", "name": "contributors", "type": "address[]"},
                    {"internalType": "uint256[]", "name": "weights", "type": "uint256[]"},
                ],
                "name": "addContributors",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [
                    {"internalType": "bytes32", "name": "projectId", "type": "bytes32"},
                    {"internalType": "uint256", "name": "amount", "type": "uint256"},
                ],
                "name": "receiveAndDistribute",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
        ]

    async def create_project(
        self,
        producer: str,
        coordinator: str,
        from_address: str,
        private_key: str,
        gas_limit: Optional[int] = None,
    ) -> str:
        """创建协作项目

        Args:
            producer: 最终产出者地址
            coordinator: 协调者地址
            from_address: 创建者地址
            private_key: 私钥
            gas_limit: 可选的 gas 限制

        Returns:
            项目ID（bytes32的十六进制字符串）

        Raises:
            TransactionError: 交易失败
            ContractError: 合约调用失败
            ValueError: 无效的地址
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            from_address = self.w3.to_checksum_address(from_address)
            producer = self.w3.to_checksum_address(producer)
            coordinator = self.w3.to_checksum_address(coordinator)

            if producer == "0x0000000000000000000000000000000000000000":
                raise ValueError("Invalid producer address")
            if coordinator == "0x0000000000000000000000000000000000000000":
                raise ValueError("Invalid coordinator address")

            # 构建交易
            tx = self.build_contract_transaction(
                self.contract.functions.createProject(producer, coordinator),
                from_address=from_address,
                gas=gas_limit,
            )

            # 签名并发送
            tx_hash = self.sign_and_send_transaction(tx, private_key)

            # 等待交易并获取项目ID
            receipt = self.wait_for_transaction(tx_hash, timeout=120)

            # 从事件日志中获取项目ID
            if receipt.get("logs"):
                for log in receipt["logs"]:
                    if len(log.get("topics", [])) > 1:
                        # ProjectCreated 事件的第一个 indexed 参数是 projectId
                        project_id = "0x" + log["topics"][1].hex()[26:]
                        return project_id

            # 如果没有找到事件日志，回退到估计
            raise TransactionError("Could not extract projectId from transaction logs")
        except ValueError:
            raise
        except Exception as e:
            raise TransactionError(f"Failed to create project: {e}")

    async def add_contributors(
        self,
        project_id: str,
        contributors: List[str],
        weights: List[int],
        from_address: str,
        private_key: str,
        gas_limit: Optional[int] = None,
    ) -> str:
        """添加贡献者

        权重总和应 <= 10000（100%）

        Args:
            project_id: 项目ID（bytes32的十六进制字符串）
            contributors: 贡献者地址列表
            weights: 贡献权重列表（精度10000）
            from_address: 调用者地址（产出者、协调者或owner）
            private_key: 私钥
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

            if len(contributors) != len(weights):
                raise ValueError("Contributors and weights arrays must have the same length")
            if not contributors:
                raise ValueError("Contributors array cannot be empty")

            from_address = self.w3.to_checksum_address(from_address)
            contributors_checksummed = [
                self.w3.to_checksum_address(addr) for addr in contributors
            ]

            # 验证权重总和
            total_weight = sum(weights)
            if total_weight > self.PRECISION:
                raise ValueError(
                    f"Total weights ({total_weight}) exceed 100% ({self.PRECISION})"
                )

            # 检查项目是否存在
            project = await self.get_project_info(project_id)
            if not project["final_producer"]:
                raise ValueError(f"Project {project_id} not found")

            # 检查是否已分发
            if project["distributed"]:
                raise ValueError(f"Project {project_id} already distributed")

            # 验证权限
            is_authorized = (
                from_address == project["final_producer"] or
                from_address == project["coordinator"]
            )
            if not is_authorized:
                # 尝试检查是否为 owner（需要额外调用）
                raise ValueError(
                    f"Unauthorized: {from_address} is not producer, coordinator, or owner"
                )

            # 构建交易
            tx = self.build_contract_transaction(
                self.contract.functions.addContributors(
                    project_id,
                    contributors_checksummed,
                    weights,
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
            raise TransactionError(f"Failed to add contributors: {e}")

    async def distribute(
        self,
        project_id: str,
        amount: int,
        from_address: str,
        private_key: str,
        gas_limit: Optional[int] = None,
    ) -> str:
        """分发收入

        需要先 approve VIBEToken 给本合约
        分发比例：70%产出者/20%贡献者/10%协调者

        Args:
            project_id: 项目ID（bytes32的十六进制字符串）
            amount: 分发金额（wei）
            from_address: 调用者地址
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

            if amount <= 0:
                raise ValueError("Amount must be greater than 0")

            from_address = self.w3.to_checksum_address(from_address)

            # 构建交易
            tx = self.build_contract_transaction(
                self.contract.functions.receiveAndDistribute(project_id, amount),
                from_address=from_address,
                gas=gas_limit,
            )

            # 签名并发送
            tx_hash = self.sign_and_send_transaction(tx, private_key)
            return tx_hash
        except ValueError:
            raise
        except Exception as e:
            raise TransactionError(f"Failed to distribute revenue: {e}")

    async def get_project_info(self, project_id: str) -> Dict[str, Any]:
        """获取项目信息

        Args:
            project_id: 项目ID（bytes32的十六进制字符串）

        Returns:
            项目信息字典：
            - project_id: 项目ID
            - final_producer: 最终产出者地址
            - coordinator: 协调者地址
            - total_revenue: 总收入
            - producer_share: 产出者份额
            - contributors_share: 贡献者总份额
            - coordinator_share: 协调者份额
            - created_at: 创建时间
            - distributed_at: 分发时间
            - distributed: 是否已分发
            - finalized: 是否已结算

        Raises:
            ContractError: 合约调用失败
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            # 确保 project_id 是正确的格式
            if isinstance(project_id, str):
                if project_id.startswith("0x"):
                    project_id_bytes = self.w3.to_bytes(hexstr=project_id)
                else:
                    project_id_bytes = bytes.fromhex(project_id)
            else:
                project_id_bytes = project_id

            result = self.call_contract_function(
                self.contract.functions.getProjectInfo(project_id_bytes)
            )

            # 解析结构体返回值
            return {
                "project_id": "0x" + result[0].hex(),
                "final_producer": result[1],
                "coordinator": result[2],
                "total_revenue": int(result[3]),
                "producer_share": int(result[4]),
                "contributors_share": int(result[5]),
                "coordinator_share": int(result[6]),
                "created_at": int(result[7]),
                "distributed_at": int(result[8]),
                "distributed": bool(result[9]),
                "finalized": bool(result[10]),
            }
        except Exception as e:
            raise ContractError(f"Failed to get project info: {e}")

    async def get_contributors(
        self,
        project_id: str,
    ) -> List[str]:
        """获取项目的贡献者列表

        Args:
            project_id: 项目ID（bytes32的十六进制字符串）

        Returns:
            贡献者地址列表

        Raises:
            ContractError: 合约调用失败
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            # 确保 project_id 是正确的格式
            if isinstance(project_id, str):
                if project_id.startswith("0x"):
                    project_id_bytes = self.w3.to_bytes(hexstr=project_id)
                else:
                    project_id_bytes = bytes.fromhex(project_id)
            else:
                project_id_bytes = project_id

            result = self.call_contract_function(
                self.contract.functions.getContributors(project_id_bytes)
            )
            return list(result) if result else []
        except Exception as e:
            raise ContractError(f"Failed to get contributors: {e}")

    async def get_contributor_count(self, project_id: str) -> int:
        """获取项目的贡献者数量

        Args:
            project_id: 项目ID（bytes32的十六进制字符串）

        Returns:
            贡献者数量

        Raises:
            ContractError: 合约调用失败
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            # 确保 project_id 是正确的格式
            if isinstance(project_id, str):
                if project_id.startswith("0x"):
                    project_id_bytes = self.w3.to_bytes(hexstr=project_id)
                else:
                    project_id_bytes = bytes.fromhex(project_id)
            else:
                project_id_bytes = project_id

            result = self.call_contract_function(
                self.contract.functions.getContributorCount(project_id_bytes)
            )
            return int(result) if result else 0
        except Exception as e:
            raise ContractError(f"Failed to get contributor count: {e}")

    async def get_contributor_weight(
        self,
        project_id: str,
        contributor: str,
    ) -> int:
        """获取贡献者在项目中的权重

        Args:
            project_id: 项目ID（bytes32的十六进制字符串）
            contributor: 贡献者地址

        Returns:
            贡献者权重

        Raises:
            ContractError: 合约调用失败
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            # 确保 project_id 是正确的格式
            if isinstance(project_id, str):
                if project_id.startswith("0x"):
                    project_id_bytes = self.w3.to_bytes(hexstr=project_id)
                else:
                    project_id_bytes = bytes.fromhex(project_id)
            else:
                project_id_bytes = project_id

            contributor = self.w3.to_checksum_address(contributor)

            result = self.call_contract_function(
                self.contract.functions.contributorWeights(project_id_bytes, contributor)
            )
            return int(result) if result else 0
        except Exception as e:
            raise ContractError(f"Failed to get contributor weight: {e}")

    async def get_user_total_income(self, user: str) -> int:
        """获取用户总收入

        Args:
            user: 用户地址

        Returns:
            用户总收入（wei）

        Raises:
            ContractError: 合约调用失败
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            result = self.call_contract_function(
                self.contract.functions.getUserTotalIncome(self.w3.to_checksum_address(user))
            )
            return int(result) if result else 0
        except Exception as e:
            raise ContractError(f"Failed to get user total income: {e}")

    async def estimate_distribution(self, amount: int) -> Dict[str, int]:
        """预估分成金额

        Args:
            amount: 总金额（wei）

        Returns:
            分成预估：
            - producer_amount: 产出者金额（70%）
            - contributors_amount: 贡献者金额（20%）
            - coordinator_amount: 协调者金额（10%）
        """
        producer_amount = (amount * self.PRODUCER_RATIO) // self.PRECISION
        coordinator_amount = (amount * self.COORDINATOR_RATIO) // self.PRECISION
        contributors_amount = amount - producer_amount - coordinator_amount

        return {
            "producer_amount": producer_amount,
            "contributors_amount": contributors_amount,
            "coordinator_amount": coordinator_amount,
            "total": amount,
        }

    async def get_project_count(self) -> int:
        """获取项目总数

        Returns:
            项目总数

        Raises:
            ContractError: 合约调用失败
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            result = self.call_contract_function(
                self.contract.functions.projectCount()
            )
            return int(result) if result else 0
        except Exception as e:
            raise ContractError(f"Failed to get project count: {e}")


__all__ = [
    "VIBCollaborationClient",
]
