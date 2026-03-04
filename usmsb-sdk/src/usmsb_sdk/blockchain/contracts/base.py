"""
基础合约客户端模块

提供通用的合约交互接口，支持EIP-1559交易构建。
"""

from typing import Optional, Dict, Any, List, Union
from web3 import Web3
from web3.contract import Contract
from eth_account import Account
from eth_account.messages import encode_defunct

from ..config import BlockchainConfig
from ..web3_client import Web3Client


class TransactionError(Exception):
    """交易错误"""
    pass


class ContractError(Exception):
    """合约错误"""
    pass


class BaseContractClient:
    """基础合约客户端

    提供通用的合约交互功能，包括：
    - 合约实例创建
    - 交易构建
    - 交易签名和发送
    - EIP-1559支持
    """

    def __init__(
        self,
        web3_client: Optional[Web3Client] = None,
        config: Optional[BlockchainConfig] = None,
        contract_address: Optional[str] = None,
        abi: Optional[Union[List[Dict], str]] = None,
    ):
        """
        初始化基础合约客户端

        Args:
            web3_client: Web3客户端实例
            config: 区块链配置
            contract_address: 合约地址
            abi: 合约ABI（可以是列表或JSON字符串）
        """
        self.config = config or BlockchainConfig()
        self.web3_client = web3_client or Web3Client(config=self.config)
        self.contract_address = contract_address
        self.abi = abi
        self._contract: Optional[Contract] = None

    @property
    def w3(self) -> Web3:
        """获取Web3实例"""
        return self.web3_client.w3

    @property
    def contract(self) -> Optional[Contract]:
        """获取合约实例"""
        if self._contract is None and self.contract_address and self.abi:
            self._contract = self._create_contract()
        return self._contract

    def _create_contract(self) -> Contract:
        """创建合约实例"""
        if not self.contract_address:
            raise ContractError("Contract address not provided")
        if not self.abi:
            raise ContractError("Contract ABI not provided")

        checksum_address = self.w3.to_checksum_address(self.contract_address)
        return self.w3.eth.contract(address=checksum_address, abi=self.abi)

    def set_contract(self, address: str, abi: Union[List[Dict], str]) -> None:
        """
        设置合约

        Args:
            address: 合约地址
            abi: 合约ABI
        """
        self.contract_address = address
        self.abi = abi
        self._contract = self._create_contract()

    def build_transaction(
        self,
        from_address: str,
        value: int = 0,
        gas: Optional[int] = None,
        gas_price: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
        nonce: Optional[int] = None,
        data: Optional[str] = None,
        to: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        构建交易（支持EIP-1559）

        Args:
            from_address: 发送方地址
            value: 发送的ETH数量（wei），默认为0
            gas: gas限制，如不指定则自动估算
            gas_price: gas价格（用于Legacy交易），如不指定则自动获取
            max_fee_per_gas: EIP-1559最大基础gas费
            max_priority_fee_per_gas: EIP-1559优先费
            nonce: 交易nonce，如不指定则自动获取
            data: 交易数据
            to: 接收方地址
            **kwargs: 其他交易参数

        Returns:
            交易字典

        Note:
            如果提供了max_fee_per_gas或max_priority_fee_per_gas，将使用EIP-1559格式。
            否则使用Legacy交易格式。
        """
        from_address = self.w3.to_checksum_address(from_address)

        # 自动获取nonce
        if nonce is None:
            nonce = self.w3.eth.get_transaction_count(from_address)

        tx: Dict[str, Any] = {
            "from": from_address,
            "nonce": nonce,
            "value": value,
            "chainId": self.config.chain_id,  # 从配置获取，不硬编码
        }

        # EIP-1559 或 Legacy 交易
        use_eip1559 = (
            max_fee_per_gas is not None or
            max_priority_fee_per_gas is not None or
            self._supports_eip1559()
        )

        if use_eip1559:
            # EIP-1559 交易
            if max_fee_per_gas is None or max_priority_fee_per_gas is None:
                # 自动获取EIP-1559费用
                fee_data = self._get_eip1559_fees()
                if max_fee_per_gas is None:
                    max_fee_per_gas = fee_data["max_fee_per_gas"]
                if max_priority_fee_per_gas is None:
                    max_priority_fee_per_gas = fee_data["max_priority_fee_per_gas"]

            tx.update({
                "maxFeePerGas": max_fee_per_gas,
                "maxPriorityFeePerGas": max_priority_fee_per_gas,
                "type": 2,  # EIP-1559
            })
        else:
            # Legacy 交易
            if gas_price is None:
                gas_price = self.w3.eth.gas_price
            tx["gasPrice"] = gas_price
            tx["type"] = 0  # Legacy

        # 添加gas限制
        if gas is not None:
            tx["gas"] = gas

        # 添加其他字段
        if data is not None:
            tx["data"] = data
        if to is not None:
            tx["to"] = self.w3.to_checksum_address(to)

        # 添加额外的自定义字段
        tx.update(kwargs)

        return tx

    def _supports_eip1559(self) -> bool:
        """
        检查网络是否支持EIP-1559

        Returns:
            是否支持EIP-1559
        """
        # Base网络支持EIP-1559
        # 本地Anvil/Hardhat默认支持
        return self.config.chain_id in [8453, 84532, 31337]

    def _get_eip1559_fees(self) -> Dict[str, int]:
        """
        获取EIP-1559费用建议

        Returns:
            包含max_fee_per_gas和max_priority_fee_per_gas的字典
        """
        try:
            # 尝试从节点获取费用建议
            latest_block = self.w3.eth.get_block("latest")
            base_fee = latest_block.get("baseFeePerGas", 0)

            # 优先费通常为1-2 gwei
            priority_fee = self.w3.to_wei(1, "gwei")

            # 最大费用 = 基础费用 + 优先费
            max_fee = base_fee + priority_fee

            return {
                "max_fee_per_gas": max_fee,
                "max_priority_fee_per_gas": priority_fee,
            }
        except Exception:
            # 回退到简单计算
            priority_fee = self.w3.to_wei(1, "gwei")
            max_fee = self.w3.eth.gas_price + priority_fee
            return {
                "max_fee_per_gas": max_fee,
                "max_priority_fee_per_gas": priority_fee,
            }

    def sign_transaction(
        self,
        transaction: Dict[str, Any],
        private_key: str,
    ) -> bytes:
        """
        签名交易

        Args:
            transaction: 交易字典
            private_key: 私钥

        Returns:
            签名后的交易（raw transaction）
        """
        account = Account.from_key(private_key)
        signed = account.sign_transaction(transaction)
        return signed.rawTransaction

    def send_raw_transaction(self, raw_transaction: bytes) -> str:
        """
        发送原始交易

        Args:
            raw_transaction: 原始交易数据

        Returns:
            交易哈希
        """
        tx_hash = self.w3.eth.send_raw_transaction(raw_transaction)
        return self.w3.to_hex(tx_hash)

    def sign_and_send_transaction(
        self,
        transaction: Dict[str, Any],
        private_key: str,
    ) -> str:
        """
        签名并发送交易

        Args:
            transaction: 交易字典
            private_key: 私钥

        Returns:
            交易哈希
        """
        raw_tx = self.sign_transaction(transaction, private_key)
        return self.send_raw_transaction(raw_tx)

    def build_contract_transaction(
        self,
        contract_function,
        from_address: str,
        value: int = 0,
        gas: Optional[int] = None,
        gas_price: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        构建合约调用交易

        Args:
            contract_function: 合约函数对象
            from_address: 发送方地址
            value: 发送的ETH数量（wei）
            gas: gas限制
            gas_price: gas价格（Legacy）
            max_fee_per_gas: 最大基础gas费（EIP-1559）
            max_priority_fee_per_gas: 优先费（EIP-1559）
            **kwargs: 其他交易参数

        Returns:
            交易字典
        """
        # 构建基础交易
        tx = self.build_transaction(
            from_address=from_address,
            value=value,
            gas=gas,
            gas_price=gas_price,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

        # 使用合约函数构建交易
        contract_tx = contract_function.build_transaction(tx)
        return contract_tx

    def call_contract_function(
        self,
        contract_function,
        block_identifier: Optional[Any] = None,
    ) -> Any:
        """
        调用合约只读函数

        Args:
            contract_function: 合约函数对象
            block_identifier: 区块标识

        Returns:
            函数返回值
        """
        return contract_function.call(block_identifier=block_identifier)

    def estimate_contract_gas(
        self,
        contract_function,
        from_address: str,
        value: int = 0,
    ) -> int:
        """
        估算合约调用gas

        Args:
            contract_function: 合约函数对象
            from_address: 发送方地址
            value: 发送的ETH数量（wei）

        Returns:
            估算的gas数量
        """
        tx = self.build_transaction(
            from_address=from_address,
            value=value,
        )
        return contract_function.estimate_gas(tx)

    def sign_message(self, message: str, private_key: str) -> str:
        """
        签名消息

        Args:
            message: 要签名的消息
            private_key: 私钥

        Returns:
            签名（十六进制字符串）
        """
        account = Account.from_key(private_key)
        message_encoded = encode_defunct(text=message)
        signed = account.sign_message(message_encoded)
        return signed.signature.hex()

    def recover_address(self, message: str, signature: str) -> str:
        """
        从签名恢复地址

        Args:
            message: 原始消息
            signature: 签名（十六进制字符串）

        Returns:
            签名者地址
        """
        message_encoded = encode_defunct(text=message)
        address = self.w3.eth.account.recover_message(
            message_encoded,
            signature=signature
        )
        return address

    def get_transaction_receipt(self, tx_hash: str) -> Dict[str, Any]:
        """
        获取交易收据

        Args:
            tx_hash: 交易哈希

        Returns:
            交易收据字典
        """
        receipt = self.w3.eth.get_transaction_receipt(tx_hash)

        # 添加成功状态判断
        if receipt is None:
            raise TransactionError(f"Transaction receipt not found: {tx_hash}")

        return receipt

    def wait_for_transaction(
        self,
        tx_hash: str,
        timeout: int = 120,
        poll_latency: float = 0.1,
        raise_on_failure: bool = True,
    ) -> Dict[str, Any]:
        """
        等待交易完成

        Args:
            tx_hash: 交易哈希
            timeout: 超时时间（秒）
            poll_latency: 轮询间隔（秒）
            raise_on_failure: 交易失败时是否抛出异常

        Returns:
            交易收据字典

        Raises:
            TransactionError: 交易失败或超时
        """
        receipt = self.w3.eth.wait_for_transaction_receipt(
            tx_hash,
            timeout=timeout,
            poll_latency=poll_latency,
        )

        if raise_on_failure and receipt["status"] != 1:
            raise TransactionError(
                f"Transaction failed: {tx_hash}. "
                f"Receipt: {receipt}"
            )

        return receipt

    def get_explorer_url(self, tx_hash: str) -> str:
        """
        获取交易的区块浏览器URL

        Args:
            tx_hash: 交易哈希

        Returns:
            区块浏览器URL
        """
        return self.config.get_explorer_url(tx_hash)


__all__ = [
    "BaseContractClient",
    "TransactionError",
    "ContractError",
]
