"""
VIBE Token 真实区块链集成
基于 Base Sepolia 测试网
"""

import logging
from dataclasses import dataclass
from typing import Any

from web3 import Web3

logger = logging.getLogger(__name__)

# Base Sepolia 配置
BASE_SEPOLIA_RPC = "https://sepolia.base.org"
BASE_SEPOLIA_CHAIN_ID = 84532
BASE_SEPOLIA_EXPLORER = "https://sepolia.basescan.org"

# VIBE Token 合约地址
VIBE_TOKEN_ADDRESS = "0x895BeA0E70F61C093E7Ef05b45Fe744ef45c2600"

# ERC-20 标准 ABI（完整）
ERC20_ABI = [
    {
        "inputs": [],
        "name": "name",
        "outputs": [{"type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "recipient", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "from", "type": "address"},
            {"name": "to", "type": "address"},
            {"name": "value", "type": "uint256"}
        ],
        "name": "transferFrom",
        "outputs": [{"type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"name": "from", "type": "address", "indexed": True},
            {"name": "to", "type": "address", "indexed": True},
            {"name": "value", "type": "uint256", "indexed": False}
        ],
        "name": "Transfer",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"name": "owner", "type": "address", "indexed": True},
            {"name": "spender", "type": "address", "indexed": True},
            {"name": "value", "type": "uint256", "indexed": False}
        ],
        "name": "Approval",
        "type": "event"
    },
]

# 最小精度（VIBE Token 假设 18 位小数）
VIBE_DECIMALS = 18


@dataclass
class VIBEBalance:
    """VIBE 余额"""
    address: str
    balance_wei: int
    balance_vibe: float
    chain: str = "base_sepolia"


class VIBEToken:
    """VIBE Token 合约封装"""

    def __init__(
        self,
        rpc_url: str = BASE_SEPOLIA_RPC,
        contract_address: str = VIBE_TOKEN_ADDRESS,
        private_key: str | None = None,
    ):
        self.rpc_url = rpc_url
        self.contract_address = contract_address
        self.private_key = private_key

        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=ERC20_ABI
        )

        logger.info(f"VIBEToken initialized: chain={rpc_url[:30]}, contract={contract_address}")

    @property
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.w3.is_connected()

    def create_wallet(self) -> dict[str, Any]:
        """创建新钱包"""
        account = self.w3.eth.account.create()
        return {
            "address": account.address,
            "private_key": account.key.hex(),
            "public_key": account.key.hex()[2:66],
        }

    def address_to_checksum(self, address: str) -> str:
        """转换为 checksum 地址"""
        return Web3.to_checksum_address(address)

    def from_wei(self, amount_wei: int) -> float:
        """Wei 转 VIBE"""
        return amount_wei / (10 ** VIBE_DECIMALS)

    def to_wei(self, amount_vibe: float) -> int:
        """VIBE 转 Wei"""
        return int(amount_vibe * (10 ** VIBE_DECIMALS))

    def get_balance(self, address: str) -> VIBEBalance:
        """查询 VIBE 余额"""
        checksum_address = self.address_to_checksum(address)
        balance_wei = self.contract.functions.balanceOf(checksum_address).call()
        return VIBEBalance(
            address=checksum_address,
            balance_wei=balance_wei,
            balance_vibe=self.from_wei(balance_wei),
            chain="base_sepolia"
        )

    def get_total_supply(self) -> float:
        """查询总供应量"""
        total_wei = self.contract.functions.totalSupply().call()
        return self.from_wei(total_wei)

    def get_decimals(self) -> int:
        """查询精度"""
        return self.contract.functions.decimals().call()

    def transfer(
        self,
        from_private_key: str,
        to_address: str,
        amount_vibe: float,
    ) -> dict[str, Any]:
        """转账 VIBE"""
        if not self.private_key and not from_private_key:
            raise ValueError("需要提供私钥进行转账")

        pk = from_private_key or self.private_key
        account = self.w3.eth.account.from_key(pk)
        nonce = self.w3.eth.get_transaction_count(account.address)
        to_checksum = self.address_to_checksum(to_address)

        amount_wei = self.to_wei(amount_vibe)

        tx = self.contract.functions.transfer(
            to_checksum,
            amount_wei
        ).build_transaction({
            "from": account.address,
            "nonce": nonce,
            "gas": 100000,
            "maxFeePerGas": self.w3.eth.gas_price * 2,
            "maxPriorityFeePerGas": self.w3.eth.max_priority_fee,
            "chainId": BASE_SEPOLIA_CHAIN_ID,
        })

        signed_tx = self.w3.eth.account.sign_transaction(tx, pk)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            "success": receipt.status == 1,
            "tx_hash": tx_hash.hex(),
            "block_number": receipt.blockNumber,
            "explorer_url": f"{BASE_SEPOLIA_EXPLORER}/tx/{tx_hash.hex()}",
        }

    def approve(
        self,
        private_key: str,
        spender_address: str,
        amount_vibe: float,
    ) -> dict[str, Any]:
        """授权代币"""
        account = self.w3.eth.account.from_key(private_key)
        nonce = self.w3.eth.get_transaction_count(account.address)
        spender_checksum = self.address_to_checksum(spender_address)
        amount_wei = self.to_wei(amount_vibe)

        tx = self.contract.functions.approve(
            spender_checksum,
            amount_wei
        ).build_transaction({
            "from": account.address,
            "nonce": nonce,
            "gas": 100000,
            "maxFeePerGas": self.w3.eth.gas_price * 2,
            "maxPriorityFeePerGas": self.w3.eth.max_priority_fee,
            "chainId": BASE_SEPOLIA_CHAIN_ID,
        })

        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            "success": receipt.status == 1,
            "tx_hash": tx_hash.hex(),
            "explorer_url": f"{BASE_SEPOLIA_EXPLORER}/tx/{tx_hash.hex()}",
        }

    def get_transfer_history(
        self,
        address: str,
        from_block: int = 0,
        to_block: int = "latest"
    ) -> list[dict]:
        """获取转账历史（仅 Transfer 事件）"""
        checksum_address = self.address_to_checksum(address)
        if to_block == "latest":
            to_block = self.w3.eth.block_number

        events = self.contract.events.Transfer.get_logs(
            argument_filters={"from": checksum_address},
            from_block=from_block,
            to_block=to_block
        )

        history = []
        for e in events:
            history.append({
                "from": e.args["from"],
                "to": e.args["to"],
                "value_vibe": self.from_wei(e.args["value"]),
                "tx_hash": e.transactionHash.hex(),
                "block_number": e.blockNumber,
            })

        return history


# 全局单例（延迟初始化）
_vibe_token: VIBEToken | None = None


def get_vibe_token(private_key: str | None = None) -> VIBEToken:
    """获取全局 VIBE Token 实例"""
    global _vibe_token
    if _vibe_token is None:
        _vibe_token = VIBEToken(private_key=private_key)
    return _vibe_token
