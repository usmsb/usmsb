"""
MultiWallet - 多币种钱包

支持多种加密货币和 Token 的钱包管理。

功能：
- USDC 余额查询
- VIBE 余额查询
- ETH 余额查询
- 多币种地址管理
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WalletAddress:
    """钱包地址"""
    address: str
    currency: str  # USDC, VIBE, ETH
    label: str = ""  # 地址标签


@dataclass
class WalletBalance:
    """钱包余额"""
    address: str
    currency: str
    balance: float
    last_updated: float = 0.0


class MultiWallet:
    """
    多币种钱包
    
    使用方式：
    ```python
    wallet = MultiWallet()
    
    # 添加地址
    wallet.add_address("0x123...", "USDC", "Main Wallet")
    wallet.add_address("vibe_456...", "VIBE", "VIBE Rewards")
    
    # 查询余额
    balance = wallet.get_balance("0x123...", "USDC")
    
    # 获取总资产
    total = wallet.get_total_value_usd()
    ```
    """
    
    def __init__(self, agent_id: str | None = None):
        self.agent_id = agent_id or "default"
        
        # 地址存储
        self._addresses: dict[str, WalletAddress] = {}
        
        # 余额缓存
        self._balances: dict[str, dict[str, float]] = {}  # address -> (currency -> balance)
        
        # 默认 VIBE 汇率（USD）
        self._vibe_usd_rate = 0.01
    
    def add_address(self, address: str, currency: str, label: str = "") -> bool:
        """
        添加钱包地址
        
        Args:
            address: 钱包地址
            currency: 币种 (USDC, VIBE, ETH)
            label: 地址标签
            
        Returns:
            bool: 是否成功
        """
        if currency not in ["USDC", "VIBE", "ETH", "BTC"]:
            return False
        
        wallet_address = WalletAddress(
            address=address,
            currency=currency,
            label=label
        )
        
        self._addresses[f"{address}_{currency}"] = wallet_address
        
        if address not in self._balances:
            self._balances[address] = {}
        
        return True
    
    def remove_address(self, address: str, currency: str) -> bool:
        """移除地址"""
        key = f"{address}_{currency}"
        if key in self._addresses:
            del self._addresses[key]
            return True
        return False
    
    def get_addresses(self, currency: str | None = None) -> list[WalletAddress]:
        """获取地址列表"""
        if currency:
            return [
                addr for addr in self._addresses.values()
                if addr.currency == currency
            ]
        return list(self._addresses.values())
    
    def update_balance(self, address: str, currency: str, balance: float) -> bool:
        """
        更新余额（模拟，真实场景需要调用区块链）
        
        Args:
            address: 钱包地址
            currency: 币种
            balance: 新余额
            
        Returns:
            bool: 是否成功
        """
        if address not in self._balances:
            self._balances[address] = {}
        
        self._balances[address][currency] = balance
        return True
    
    def get_balance(self, address: str, currency: str) -> float:
        """
        获取余额
        
        Args:
            address: 钱包地址
            currency: 币种
            
        Returns:
            float: 余额
        """
        if address not in self._balances:
            return 0.0
        return self._balances[address].get(currency, 0.0)
    
    def get_all_balances(self, address: str) -> dict[str, float]:
        """获取某地址的所有余额"""
        return self._balances.get(address, {}).copy()
    
    def set_vibe_usd_rate(self, rate: float) -> None:
        """设置 VIBE/USD 汇率"""
        self._vibe_usd_rate = rate
    
    def get_vibe_usd_rate(self) -> float:
        """获取 VIBE/USD 汇率"""
        return self._vibe_usd_rate
    
    def get_total_value_usd(self, address: str | None = None) -> float:
        """
        获取总资产（USD）
        
        Args:
            address: 钱包地址（None = 所有地址）
            
        Returns:
            float: 总资产 USD
        """
        total = 0.0
        
        # USD 汇率（简化版）
        eth_usd_rate = 3500.0
        btc_usd_rate = 65000.0
        
        addresses_to_check = []
        if address:
            addresses_to_check = [address]
        else:
            addresses_to_check = list(self._balances.keys())
        
        for addr in addresses_to_check:
            balances = self._balances.get(addr, {})
            
            # 加上各币种价值
            total += balances.get("USDC", 0.0) * 1.0  # USDC = 1 USD
            total += balances.get("VIBE", 0.0) * self._vibe_usd_rate
            total += balances.get("ETH", 0.0) * eth_usd_rate
            total += balances.get("BTC", 0.0) * btc_usd_rate
        
        return total
    
    def can_pay(self, amount: float, currency: str) -> bool:
        """
        检查是否可以支付
        
        Args:
            amount: 支付金额
            currency: 币种
            
        Returns:
            bool: 是否可以支付
        """
        for addr, balances in self._balances.items():
            if balances.get(currency, 0.0) >= amount:
                return True
        return False
    
    def pay(self, from_address: str, to_address: str, amount: float, currency: str) -> bool:
        """
        发起支付（模拟）
        
        Args:
            from_address: 发送方地址
            to_address: 接收方地址
            amount: 金额
            currency: 币种
            
        Returns:
            bool: 是否成功
        """
        # 检查余额
        balance = self.get_balance(from_address, currency)
        if balance < amount:
            return False
        
        # 扣除余额（简化版，真实场景需要区块链确认）
        self._balances[from_address][currency] -= amount
        
        # 接收方余额增加（模拟）
        if to_address not in self._balances:
            self._balances[to_address] = {}
        self._balances[to_address][currency] = self._balances[to_address].get(currency, 0.0) + amount
        
        return True
    
    def get_wallet_info(self) -> dict[str, Any]:
        """获取钱包信息"""
        total_usd = self.get_total_value_usd()
        
        return {
            "agent_id": self.agent_id,
            "total_addresses": len(self._addresses),
            "total_balance_usd": total_usd,
            "currencies": list(set(addr.currency for addr in self._addresses.values())),
            "vibe_usd_rate": self._vibe_usd_rate,
        }
