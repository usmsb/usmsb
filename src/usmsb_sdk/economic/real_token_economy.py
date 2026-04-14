# -*- coding: utf-8 -*-
"""
RealVIBETokenEconomy - 真实 VIBE Token 经济系统

使用 Base Sepolia 测试网上的真实 VIBE Token 合约。

配置：
- 网络: Base Sepolia (chain_id: 84532)
- RPC: https://sepolia.base.org
- VIBEToken: 0x93C52dF000317e12F891474B46d8B05652430bDC

使用方式：
    economy = RealVIBETokenEconomy()
    
    # 查询余额
    balance = economy.get_balance("0x...")
    
    # 转账
    economy.transfer(from_address="0x...", to_address="0x...", amount=100.0)
    
    # 授权
    economy.approve(spender="0x...", amount=100.0)
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from usmsb_sdk.blockchain.config import BlockchainConfig, NetworkType
from usmsb_sdk.blockchain.web3_client import Web3Client
from usmsb_sdk.blockchain.contracts.vibe_token import VIBETokenClient


@dataclass
class TransactionRecord:
    """交易记录"""
    tx_hash: str
    from_address: str
    to_address: str
    amount: float  # VIBE 单位
    timestamp: float
    status: str  # pending, confirmed, failed
    gas_used: int | None = None


class RealVIBETokenEconomy:
    """
    真实 VIBE Token 经济系统
    
    使用 Base Sepolia 测试网上的真实合约。
    
    功能：
    - 余额查询（真实链上数据）
    - 转账（真实交易）
    - 授权（ERC20 approve）
    - 质押（调用 Staking 合约）
    - 批量操作
    
    注意：
    - 需要设置私钥环境变量或提供签名者
    - 默认使用读取引能（不需要私钥）
    """
    
    # 合约地址
    VIBE_TOKEN_ADDRESS = "0x93C52dF000317e12F891474B46d8B05652430bDC"
    
    def __init__(
        self,
        private_key: str | None = None,
        rpc_url: str | None = None,
        config: BlockchainConfig | None = None,
    ):
        """
        初始化真实 VIBE Token 经济系统
        
        Args:
            private_key: 钱包私钥（用于签名交易）
            rpc_url: 自定义 RPC URL
            config: 区块链配置
        """
        # 优先使用环境变量
        self.private_key = private_key or os.environ.get("VIBE_PRIVATE_KEY")
        self.rpc_url = rpc_url or os.environ.get("VIBE_RPC_URL")
        
        # 创建配置
        if config is None:
            if self.rpc_url:
                self.config = BlockchainConfig(
                    network=NetworkType.TESTNET,
                    rpc_url=self.rpc_url
                )
            else:
                self.config = BlockchainConfig(network=NetworkType.TESTNET)
        
        # Web3 客户端
        self.web3_client = Web3Client(config=self.config)
        
        # VIBE Token 客户端
        self.token_client = VIBETokenClient(
            web3_client=self.web3_client,
            config=self.config,
            contract_address=self.VIBE_TOKEN_ADDRESS,
        )
        
        # 交易历史
        self._transactions: list[TransactionRecord] = []
        
        # 缓存
        self._balance_cache: dict[str, tuple[float, float]] = {}  # address -> (balance, timestamp)
    
    # =========================================================================
    # 余额操作
    # =========================================================================
    
    def get_balance(self, address: str, use_cache: bool = True) -> float:
        """
        获取 VIBE 余额
        
        Args:
            address: 以太坊地址
            use_cache: 是否使用缓存（5分钟）
            
        Returns:
            float: VIBE 余额
        """
        # 检查缓存
        if use_cache and address in self._balance_cache:
            balance, timestamp = self._balance_cache[address]
            if datetime.now().timestamp() - timestamp < 300:  # 5 分钟
                return balance
        
        # 查询链上余额
        try:
            balance_wei = self.token_client.balance_of(address)
            balance_vibe = self.token_client.balance_of_vibe(address)
            
            # 更新缓存
            self._balance_cache[address] = (balance_vibe, datetime.now().timestamp())
            
            return balance_vibe
        except Exception as e:
            print(f"[RealVIBETokenEconomy] Failed to get balance: {e}")
            return 0.0
    
    def get_total_supply(self) -> float:
        """获取总供应量"""
        try:
            return self.token_client.total_supply_vibe()
        except Exception as e:
            print(f"[RealVIBETokenEconomy] Failed to get total supply: {e}")
            return 0.0
    
    # =========================================================================
    # 转账操作
    # =========================================================================
    
    def transfer(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        wait_for_confirmation: bool = True,
        timeout: float = 60.0,
    ) -> TransactionRecord | None:
        """
        转账 VIBE Token
        
        Args:
            from_address: 发送方地址
            to_address: 接收方地址
            amount: VIBE 数量
            wait_for_confirmation: 是否等待确认
            timeout: 超时时间（秒）
            
        Returns:
            TransactionRecord 或 None
        """
        if not self.private_key:
            print("[RealVIBETokenEconomy] No private key configured, cannot transfer")
            return None
        
        try:
            # 转换 VIBE to wei
            amount_wei = int(amount * (10 ** self.token_client.DECIMALS))
            
            # 获取 nonce
            w3 = self.web3_client.w3
            nonce = w3.eth.get_transaction_count(from_address)
            
            # 构建交易
            contract = self.token_client.contract
            txn = contract.functions.transfer(
                to_address,
                amount_wei
            ).build_transaction({
                'from': from_address,
                'nonce': nonce,
                'gas': 100000,
                'gasPrice': w3.eth.gas_price,
                'chainId': self.config.chain_id,
            })
            
            # 签名
            signed_txn = w3.eth.account.sign_transaction(
                txn,
                private_key=self.private_key
            )
            
            # 发送
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            tx_hash_hex = tx_hash.hex()
            
            record = TransactionRecord(
                tx_hash=tx_hash_hex,
                from_address=from_address,
                to_address=to_address,
                amount=amount,
                timestamp=datetime.now().timestamp(),
                status="pending",
            )
            
            self._transactions.append(record)
            
            # 等待确认
            if wait_for_confirmation:
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
                
                if receipt.status == 1:
                    record.status = "confirmed"
                    record.gas_used = receipt.gas_used
                else:
                    record.status = "failed"
            
            return record
            
        except Exception as e:
            print(f"[RealVIBETokenEconomy] Transfer failed: {e}")
            return None
    
    def approve(
        self,
        owner_address: str,
        spender_address: str,
        amount: float,
    ) -> TransactionRecord | None:
        """
        授权 Token
        
        Args:
            owner_address: 所有者地址
            spender_address: 获授权者地址
            amount: VIBE 数量
            
        Returns:
            TransactionRecord 或 None
        """
        if not self.private_key:
            print("[RealVIBETokenEconomy] No private key configured, cannot approve")
            return None
        
        try:
            amount_wei = int(amount * (10 ** self.token_client.DECIMALS))
            
            w3 = self.web3_client.w3
            nonce = w3.eth.get_transaction_count(owner_address)
            
            contract = self.token_client.contract
            txn = contract.functions.approve(
                spender_address,
                amount_wei
            ).build_transaction({
                'from': owner_address,
                'nonce': nonce,
                'gas': 100000,
                'gasPrice': w3.eth.gas_price,
                'chainId': self.config.chain_id,
            })
            
            signed_txn = w3.eth.account.sign_transaction(
                txn,
                private_key=self.private_key
            )
            
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            return TransactionRecord(
                tx_hash=tx_hash.hex(),
                from_address=owner_address,
                to_address=spender_address,
                amount=amount,
                timestamp=datetime.now().timestamp(),
                status="pending",
            )
            
        except Exception as e:
            print(f"[RealVIBETokenEconomy] Approve failed: {e}")
            return None
    
    def get_allowance(self, owner: str, spender: str) -> float:
        """查询授权额度"""
        try:
            allowance_wei = self.token_client.allowance(owner, spender)
            return allowance_wei / (10 ** self.token_client.DECIMALS)
        except Exception as e:
            print(f"[RealVIBETokenEconomy] Failed to get allowance: {e}")
            return 0.0
    
    # =========================================================================
    # 经济计算
    # =========================================================================
    
    def calculate_matching_fee(self, order_value: float) -> float:
        """计算匹配费（1%）"""
        return order_value * 0.01
    
    def calculate_layer2_fee(self, order_value: float) -> float:
        """计算二层费（2%）"""
        return order_value * 0.02
    
    def calculate_layer3_fee(self, order_value: float) -> float:
        """计算三层费（3%）"""
        return order_value * 0.03
    
    # =========================================================================
    # 批量操作
    # =========================================================================
    
    def get_balances(self, addresses: list[str]) -> dict[str, float]:
        """批量查询余额"""
        return {addr: self.get_balance(addr) for addr in addresses}
    
    def get_transaction_history(self, address: str, limit: int = 50) -> list[TransactionRecord]:
        """获取交易历史"""
        return [
            tx for tx in self._transactions
            if tx.from_address == address or tx.to_address == address
        ][:limit]
    
    # =========================================================================
    # 网络信息
    # =========================================================================
    
    def get_network_info(self) -> dict:
        """获取网络信息"""
        return {
            "network": self.config.network_name,
            "chain_id": self.config.chain_id,
            "rpc_url": self.config.rpc_url,
            "explorer_url": self.config.explorer_url,
            "contract_address": self.VIBE_TOKEN_ADDRESS,
            "is_connected": self.web3_client.is_connected(),
        }
    
    def __repr__(self) -> str:
        return f"RealVIBETokenEconomy(network={self.config.network_name})"
