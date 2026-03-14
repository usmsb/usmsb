"""
Web3客户端封装模块

提供统一的Web3连接和交互接口，支持异步操作。
"""

import asyncio
from typing import Any

from web3 import Web3

from .config import BlockchainConfig


class Web3Client:
    """Web3客户端封装类

    提供统一的Web3连接、交易查询和连接测试功能。
    """

    def __init__(
        self,
        config: BlockchainConfig | None = None,
        rpc_url: str | None = None,
    ):
        """
        初始化Web3客户端

        Args:
            config: 区块链配置，如不指定则使用默认配置
            rpc_url: RPC URL，如指定则覆盖配置中的RPC URL
        """
        self.config = config or BlockchainConfig()
        self._rpc_url = rpc_url or self.config.rpc_url
        self._w3: Web3 | None = None
        self._w3_async = None  # 异步Web3实例（待实现）

    @property
    def w3(self) -> Web3:
        """获取Web3实例，延迟连接"""
        if self._w3 is None:
            self.connect()
        return self._w3

    def connect(self) -> None:
        """连接到区块链节点"""
        self._w3 = Web3(Web3.HTTPProvider(self._rpc_url))

    def reconnect(self, new_rpc_url: str | None = None) -> None:
        """重新连接到区块链节点

        Args:
            new_rpc_url: 新的RPC URL，如不指定则使用当前RPC URL
        """
        if new_rpc_url:
            self._rpc_url = new_rpc_url
        self._w3 = Web3(Web3.HTTPProvider(self._rpc_url))

    def is_connected(self) -> bool:
        """检查连接状态"""
        if self._w3 is None:
            return False
        return self._w3.is_connected()

    def test_connection(self) -> dict:
        """测试连接并返回网络信息

        Returns:
            包含网络信息的字典
        """
        try:
            chain_id = self.w3.eth.chain_id
            block_number = self.w3.eth.block_number
            latest_block = self.w3.eth.get_block("latest")

            return {
                "connected": True,
                "rpc_url": self._rpc_url,
                "chain_id": chain_id,
                "expected_chain_id": self.config.chain_id,
                "chain_match": chain_id == self.config.chain_id,
                "network_name": self.config.network_name,
                "block_number": block_number,
                "latest_block_hash": latest_block["hash"].hex() if latest_block else None,
            }
        except Exception as e:
            return {
                "connected": False,
                "rpc_url": self._rpc_url,
                "error": str(e),
            }

    def get_chain_id(self) -> int:
        """获取当前链ID"""
        return self.w3.eth.chain_id

    def get_block_number(self) -> int:
        """获取当前区块号"""
        return self.w3.eth.block_number

    def get_balance(self, address: str) -> int:
        """
        获取地址的ETH余额

        Args:
            address: 以太坊地址

        Returns:
            余额（以wei为单位）
        """
        return self.w3.eth.get_balance(address)

    def get_transaction(self, tx_hash: str) -> dict:
        """
        获取交易详情

        Args:
            tx_hash: 交易哈希

        Returns:
            交易详情字典
        """
        return self.w3.eth.get_transaction(tx_hash)

    def get_transaction_receipt(self, tx_hash: str) -> dict:
        """
        获取交易收据

        Args:
            tx_hash: 交易哈希

        Returns:
            交易收据字典
        """
        return self.w3.eth.get_transaction_receipt(tx_hash)

    def wait_for_transaction_receipt(
        self,
        tx_hash: str,
        timeout: int = 120,
        poll_latency: float = 0.1,
    ) -> dict:
        """
        等待交易收据

        Args:
            tx_hash: 交易哈希
            timeout: 超时时间（秒）
            poll_latency: 轮询间隔（秒）

        Returns:
            交易收据字典

        Raises:
            TimeExhausted: 超时未收到交易收据
        """
        return self.w3.eth.wait_for_transaction_receipt(
            tx_hash,
            timeout=timeout,
            poll_latency=poll_latency,
        )

    def estimate_gas(
        self,
        transaction: dict,
        block_identifier: Any | None = None,
    ) -> int:
        """
        估算交易gas

        Args:
            transaction: 交易字典
            block_identifier: 区块标识

        Returns:
            估算的gas数量
        """
        return self.w3.eth.estimate_gas(transaction, block_identifier)

    def get_gas_price(self) -> int:
        """获取当前gas价格"""
        return self.w3.eth.gas_price

    def get_block(self, block_identifier: Any, full_transactions: bool = False) -> dict:
        """
        获取区块信息

        Args:
            block_identifier: 区块标识（区块号或"latest"等）
            full_transactions: 是否包含完整交易信息

        Returns:
            区块信息字典
        """
        return self.w3.eth.get_block(block_identifier, full_transactions=full_transactions)

    def get_code(self, address: str, block_identifier: Any | None = None) -> bytes:
        """
        获取合约代码

        Args:
            address: 合约地址
            block_identifier: 区块标识

        Returns:
            合约字节码
        """
        return self.w3.eth.get_code(address, block_identifier)

    def to_checksum_address(self, address: str) -> str:
        """
        转换为校验和地址

        Args:
            address: 以太坊地址

        Returns:
            校验和地址
        """
        return self.w3.to_checksum_address(address)

    def to_hex(self, value: Any) -> str:
        """
        转换为十六进制字符串

        Args:
            value: 要转换的值

        Returns:
            十六进制字符串
        """
        return self.w3.to_hex(value)

    def from_wei(self, value: int, unit: str = "ether") -> float:
        """
        从wei转换

        Args:
            value: wei值
            unit: 目标单位

        Returns:
            转换后的值
        """
        return self.w3.from_wei(value, unit)

    def to_wei(self, value: float, unit: str = "ether") -> int:
        """
        转换为wei

        Args:
            value: 原始值
            unit: 原始单位

        Returns:
            wei值
        """
        return self.w3.to_wei(value, unit)

    # 异步方法占位（需要使用web3.py的异步支持或eth-lib等库）

    async def test_connection_async(self) -> dict:
        """
        异步测试连接

        Returns:
            包含网络信息的字典
        """
        # 在单独的线程中运行同步方法
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.test_connection)

    async def get_balance_async(self, address: str) -> int:
        """
        异步获取地址余额

        Args:
            address: 以太坊地址

        Returns:
            余额（以wei为单位）
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_balance, address)

    async def get_transaction_receipt_async(self, tx_hash: str) -> dict:
        """
        异步获取交易收据

        Args:
            tx_hash: 交易哈希

        Returns:
            交易收据字典
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_transaction_receipt, tx_hash)

    async def wait_for_transaction_receipt_async(
        self,
        tx_hash: str,
        timeout: int = 120,
        poll_latency: float = 0.1,
    ) -> dict:
        """
        异步等待交易收据

        Args:
            tx_hash: 交易哈希
            timeout: 超时时间（秒）
            poll_latency: 轮询间隔（秒）

        Returns:
            交易收据字典

        Raises:
            TimeExhausted: 超时未收到交易收据
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.wait_for_transaction_receipt(tx_hash, timeout, poll_latency)
        )

    def __repr__(self) -> str:
        return f"Web3Client(rpc_url={self._rpc_url!r}, network={self.config.network_name!r})"


__all__ = [
    "Web3Client",
]
