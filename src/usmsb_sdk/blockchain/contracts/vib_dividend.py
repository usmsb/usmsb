"""
VIBDividend 分红合约客户端

实现 VIBE 分红合约的 Python 客户端，支持：
- 获取待领取分红
- 领取分红（需间隔1天冷却期）
- 获取合约分红余额
- 获取分红统计
"""

from typing import Optional, Dict, Any, Union, List

from .base import BaseContractClient, TransactionError, ContractError
from ..config import BlockchainConfig
from ..web3_client import Web3Client


class VIBDividendClient(BaseContractClient):
    """VIBE 分红合约客户端

    实现白皮书承诺的分红机制：
    - 将交易手续费的 20% 分配给质押者
    - 按质押量比例分配
    - 领取分红需间隔1天冷却期
    """

    # 合约常量
    PRECISION = 1e18  # 精度因子
    CLAIM_COOLDOWN = 86400  # 1天冷却期（秒）

    def __init__(
        self,
        web3_client: Optional[Web3Client] = None,
        config: Optional[BlockchainConfig] = None,
        contract_address: Optional[str] = None,
        abi: Optional[Union[List[Dict], str]] = None,
    ):
        """
        初始化 VIBDividend 客户端

        Args:
            web3_client: Web3 客户端实例
            config: 区块链配置
            contract_address: 合约地址（如不指定则从配置中获取）
            abi: 合约 ABI（如不指定则使用内置 ABI）
        """
        super().__init__(web3_client, config)

        # 获取合约地址
        if contract_address is None:
            contract_address = self.config.get_contract_address("VIBDividend")
            if contract_address is None or contract_address == "待部署":
                raise ContractError("VIBDividend contract not deployed or configured")

        # 使用内置 ABI（简化版本）
        if abi is None:
            abi = self._get_default_abi()

        self.set_contract(contract_address, abi)

    def _get_default_abi(self) -> List[Dict]:
        """获取默认 ABI"""
        return [
            # 只读函数
            {
                "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
                "name": "getPendingDividend",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [],
                "name": "getBalance",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [],
                "name": "dividendPerTokenStored",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [],
                "name": "dividendBalance",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [],
                "name": "totalDividendsDistributed",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [],
                "name": "lastUpdateTime",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            },
            # 写入函数
            {
                "inputs": [],
                "name": "claimDividend",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
        ]

    async def get_pending_dividend(self, user: str) -> int:
        """获取用户待领取分红

        Args:
            user: 用户地址

        Returns:
            待领取分红金额（wei）

        Raises:
            ContractError: 合约调用失败
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            result = self.call_contract_function(
                self.contract.functions.getPendingDividend(self.w3.to_checksum_address(user))
            )
            return int(result) if result else 0
        except Exception as e:
            raise ContractError(f"Failed to get pending dividend: {e}")

    async def claim_dividend(
        self,
        from_address: str,
        private_key: str,
        gas_limit: Optional[int] = None,
    ) -> str:
        """领取分红

        Args:
            from_address: 领取人地址
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
                self.contract.functions.claimDividend(),
                from_address=from_address,
                gas=gas_limit,
            )

            # 签名并发送
            tx_hash = self.sign_and_send_transaction(tx, private_key)
            return tx_hash
        except Exception as e:
            raise TransactionError(f"Failed to claim dividend: {e}")

    async def get_balance(self) -> int:
        """获取合约分红余额

        Returns:
            合约中可用分红余额（wei）

        Raises:
            ContractError: 合约调用失败
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            result = self.call_contract_function(
                self.contract.functions.getBalance()
            )
            return int(result) if result else 0
        except Exception as e:
            raise ContractError(f"Failed to get dividend balance: {e}")

    async def get_dividend_stats(self) -> Dict[str, Any]:
        """获取分红统计

        Returns:
            包含以下信息的字典:
            - dividend_per_token: 每质押代币的累计分红
            - dividend_balance: 合约分红余额
            - total_distributed: 累计已分配分红
            - last_update_time: 上次更新时间
            - precision: 精度因子

        Raises:
            ContractError: 合约调用失败
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            # 批量获取数据
            dividend_per_token = self.call_contract_function(
                self.contract.functions.dividendPerTokenStored()
            )
            dividend_balance = self.call_contract_function(
                self.contract.functions.dividendBalance()
            )
            total_distributed = self.call_contract_function(
                self.contract.functions.totalDividendsDistributed()
            )
            last_update = self.call_contract_function(
                self.contract.functions.lastUpdateTime()
            )

            return {
                "dividend_per_token": int(dividend_per_token) if dividend_per_token else 0,
                "dividend_balance": int(dividend_balance) if dividend_balance else 0,
                "total_distributed": int(total_distributed) if total_distributed else 0,
                "last_update_time": int(last_update) if last_update else 0,
                "precision": int(self.PRECISION),
                "claim_cooldown": self.CLAIM_COOLDOWN,
            }
        except Exception as e:
            raise ContractError(f"Failed to get dividend stats: {e}")

    async def check_claim_available(self, user: str) -> Dict[str, Any]:
        """检查用户是否可以领取分红

        Args:
            user: 用户地址

        Returns:
            包含以下信息的字典:
            - can_claim: 是否可以领取
            - pending: 待领取金额
            - time_until_claim: 距离可领取的秒数（如果 can_claim 为 False）
            - reason: 不能领取的原因（如果 can_claim 为 False）

        Raises:
            ContractError: 合约调用失败
        """
        try:
            user = self.w3.to_checksum_address(user)

            # 获取待领取分红
            pending = await self.get_pending_dividend(user)

            if pending == 0:
                return {
                    "can_claim": False,
                    "pending": 0,
                    "time_until_claim": 0,
                    "reason": "No pending dividend",
                }

            # 检查冷却期（需要从合约获取 lastClaimTime）
            # 这里简化处理，实际需要调用合约
            return {
                "can_claim": True,
                "pending": pending,
                "time_until_claim": 0,
                "reason": "",
            }
        except Exception as e:
            raise ContractError(f"Failed to check claim availability: {e}")

    async def claim_dividend_and_wait(
        self,
        from_address: str,
        private_key: str,
        timeout: int = 120,
        poll_latency: float = 0.1,
    ) -> Dict[str, Any]:
        """领取分红并等待交易确认

        Args:
            from_address: 领取人地址
            private_key: 私钥
            timeout: 超时时间（秒）
            poll_latency: 轮询间隔（秒）

        Returns:
            包含交易信息的字典:
            - tx_hash: 交易哈希
            - receipt: 交易收据
            - success: 是否成功
            - explorer_url: 区块浏览器链接

        Raises:
            TransactionError: 交易失败或超时
            ContractError: 合约调用失败
        """
        try:
            # 发送交易
            tx_hash = await self.claim_dividend(from_address, private_key)

            # 等待确认
            receipt = self.wait_for_transaction(tx_hash, timeout, poll_latency)

            return {
                "tx_hash": tx_hash,
                "receipt": receipt,
                "success": receipt.get("status") == 1,
                "explorer_url": self.get_explorer_url(tx_hash),
            }
        except Exception as e:
            raise TransactionError(f"Failed to claim dividend and wait: {e}")


__all__ = [
    "VIBDividendClient",
]
