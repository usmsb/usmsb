"""
VIBE代币客户端模块

提供VIBE代币合约的交互接口，包括：
- 余额查询
- 授权操作
- 转账功能（支持交易税计算）
- 税费明细查询
"""

from typing import Dict, Optional, Any
from web3 import Web3
from decimal import Decimal

from ..config import BlockchainConfig
from .base import BaseContractClient, TransactionError, ContractError


class VIBETokenClient(BaseContractClient):
    """VIBE代币客户端

    提供完整的VIBE代币操作接口，包括余额查询、授权、转账等功能。
    支持交易税（0.8%）的自动计算和显示。
    """

    # 代币精度（18位小数）
    DECIMALS = 18

    # 交易税率（0.8% = 8/1000）
    TAX_RATE = Decimal("0.008")

    def __init__(
        self,
        web3_client: Optional[Any] = None,
        config: Optional[BlockchainConfig] = None,
        contract_address: Optional[str] = None,
        abi: Optional[Any] = None,
    ):
        """
        初始化VIBE代币客户端

        Args:
            web3_client: Web3客户端实例
            config: 区块链配置
            contract_address: VIBE代币合约地址
            abi: 合约ABI
        """
        super().__init__(
            web3_client=web3_client,
            config=config,
            contract_address=contract_address,
            abi=abi,
        )

    @property
    def token_address(self) -> str:
        """获取代币合约地址"""
        if not self.contract_address:
            raise ContractError("Contract address not set")
        return self.w3.to_checksum_address(self.contract_address)

    def balance_of(self, address: str) -> int:
        """
        查询余额（wei单位）

        Args:
            address: 要查询的地址

        Returns:
            余额（wei单位）

        Example:
            >>> client = VIBETokenClient(...)
            >>> balance = client.balance_of("0x...")
            >>> print(f"Balance: {balance} wei")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_address = self.w3.to_checksum_address(address)
        balance = self.call_contract_function(
            self.contract.functions.balanceOf(checksum_address)
        )
        return int(balance)

    def balance_of_vibe(self, address: str) -> float:
        """
        查询余额（VIBE单位）

        将wei单位的余额转换为VIBE单位（除以10^18）。

        Args:
            address: 要查询的地址

        Returns:
            余额（VIBE单位，浮点数）

        Example:
            >>> client = VIBETokenClient(...)
            >>> balance = client.balance_of_vibe("0x...")
            >>> print(f"Balance: {balance:.2f} VIBE")
        """
        balance_wei = self.balance_of(address)
        return float(self.w3.from_wei(balance_wei, "ether"))

    def approve(
        self,
        spender: str,
        amount: int,
        from_address: str,
        private_key: str,
        gas: Optional[int] = None,
    ) -> str:
        """
        授权消费

        授权指定地址使用当前账户的代币。

        Args:
            spender: 被授权的地址
            amount: 授权金额（wei单位），使用2**256-1表示无限授权
            from_address: 授权方地址
            private_key: 授权方私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = VIBETokenClient(...)
            >>> tx_hash = client.approve(
            ...     spender="0x...",
            ...     amount=2**256-1,  # 无限授权
            ...     from_address="0x...",
            ...     private_key="..."
            ... )
            >>> print(f"Approve tx: {tx_hash}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_spender = self.w3.to_checksum_address(spender)
        checksum_from = self.w3.to_checksum_address(from_address)

        # 构建授权交易
        tx = self.build_contract_transaction(
            self.contract.functions.approve(checksum_spender, amount),
            from_address=checksum_from,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, private_key)
        return tx_hash

    def allowance(self, owner: str, spender: str) -> int:
        """
        查询授权额度

        查询owner授权给spender的代币数量。

        Args:
            owner: 代币所有者地址
            spender: 被授权地址

        Returns:
            授权额度（wei单位）

        Example:
            >>> client = VIBETokenClient(...)
            >>> allowance = client.allowance("0x...", "0x...")
            >>> print(f"Allowance: {allowance} wei")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_owner = self.w3.to_checksum_address(owner)
        checksum_spender = self.w3.to_checksum_address(spender)

        allowance_value = self.call_contract_function(
            self.contract.functions.allowance(checksum_owner, checksum_spender)
        )
        return int(allowance_value)

    def get_tax_breakdown(self, amount: int) -> Dict[str, Any]:
        """
        计算交易税明细

        VIBE代币交易会收取0.8%的交易税。

        Args:
            amount: 转账金额（wei单位）

        Returns:
            税费明细字典，包含：
            - amount: 原始金额（wei）
            - amount_vibe: 原始金额（VIBE）
            - tax_rate: 税率
            - tax_amount: 税费金额（wei）
            - tax_vibe: 税费金额（VIBE）
            - net_amount: 实际到账金额（wei）
            - net_vibe: 实际到账金额（VIBE）

        Example:
            >>> client = VIBETokenClient(...)
            >>> breakdown = client.get_tax_breakdown(1000 * 10**18)
            >>> print(f"Tax: {breakdown['tax_vibe']} VIBE")
            >>> print(f"Net: {breakdown['net_vibe']} VIBE")
        """
        tax_amount = int(amount * self.TAX_RATE)
        net_amount = amount - tax_amount

        return {
            "amount": amount,
            "amount_vibe": float(self.w3.from_wei(amount, "ether")),
            "tax_rate": float(self.TAX_RATE),
            "tax_amount": tax_amount,
            "tax_vibe": float(self.w3.from_wei(tax_amount, "ether")),
            "net_amount": net_amount,
            "net_vibe": float(self.w3.from_wei(net_amount, "ether")),
        }

    def get_net_transfer_amount(self, amount: int) -> int:
        """
        计算实际到账金额（扣除税费）

        快速计算扣除交易税后的实际到账金额。

        Args:
            amount: 转账金额（wei单位）

        Returns:
            实际到账金额（wei单位）

        Example:
            >>> client = VIBETokenClient(...)
            >>> net = client.get_net_transfer_amount(1000 * 10**18)
            >>> print(f"Net amount: {net} wei")
        """
        tax_amount = int(amount * self.TAX_RATE)
        return amount - tax_amount

    def transfer(
        self,
        to: str,
        amount: int,
        from_address: str,
        private_key: str,
        gas: Optional[int] = None,
    ) -> str:
        """
        转账（有交易税）

        向指定地址转账VIBE代币，转账会自动扣除0.8%的交易税。

        Args:
            to: 接收方地址
            amount: 转账金额（wei单位）
            from_address: 发送方地址
            private_key: 发送方私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = VIBETokenClient(...)
            >>> tx_hash = client.transfer(
            ...     to="0x...",
            ...     amount=1000 * 10**18,  # 1000 VIBE
            ...     from_address="0x...",
            ...     private_key="..."
            ... )
            >>> print(f"Transfer tx: {tx_hash}")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_to = self.w3.to_checksum_address(to)
        checksum_from = self.w3.to_checksum_address(from_address)

        # 构建转账交易
        tx = self.build_contract_transaction(
            self.contract.functions.transfer(checksum_to, amount),
            from_address=checksum_from,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, private_key)
        return tx_hash

    def transfer_from(
        self,
        from_address: str,
        to: str,
        amount: int,
        sender_address: str,
        private_key: str,
        gas: Optional[int] = None,
    ) -> str:
        """
        代理转账（从授权额度中转账）

        使用授权的额度进行转账，常用于DeFi协议操作。

        Args:
            from_address: 代币所有者地址
            to: 接收方地址
            amount: 转账金额（wei单位）
            sender_address: 转账发起者地址
            private_key: 转账发起者私钥
            gas: 可选的gas限制

        Returns:
            交易哈希

        Example:
            >>> client = VIBETokenClient(...)
            >>> tx_hash = client.transfer_from(
            ...     from_address="0x...",  # 代币所有者
            ...     to="0x...",
            ...     amount=1000 * 10**18,
            ...     sender_address="0x...",  # 代理地址
            ...     private_key="..."
            ... )
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        checksum_from = self.w3.to_checksum_address(from_address)
        checksum_to = self.w3.to_checksum_address(to)
        checksum_sender = self.w3.to_checksum_address(sender_address)

        # 构建代理转账交易
        tx = self.build_contract_transaction(
            self.contract.functions.transferFrom(checksum_from, checksum_to, amount),
            from_address=checksum_sender,
            gas=gas,
        )

        # 签名并发送交易
        tx_hash = self.sign_and_send_transaction(tx, private_key)
        return tx_hash

    def total_supply(self) -> int:
        """
        查询代币总供应量

        Returns:
            总供应量（wei单位）

        Example:
            >>> client = VIBETokenClient(...)
            >>> supply = client.total_supply()
            >>> print(f"Total supply: {supply} wei")
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        supply = self.call_contract_function(
            self.contract.functions.totalSupply()
        )
        return int(supply)

    def total_supply_vibe(self) -> float:
        """
        查询代币总供应量（VIBE单位）

        Returns:
            总供应量（VIBE单位）

        Example:
            >>> client = VIBETokenClient(...)
            >>> supply = client.total_supply_vibe()
            >>> print(f"Total supply: {supply:.2f} VIBE")
        """
        supply = self.total_supply()
        return float(self.w3.from_wei(supply, "ether"))

    def name(self) -> str:
        """
        查询代币名称

        Returns:
            代币名称
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        return self.call_contract_function(
            self.contract.functions.name()
        )

    def symbol(self) -> str:
        """
        查询代币符号

        Returns:
            代币符号
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        return self.call_contract_function(
            self.contract.functions.symbol()
        )

    def decimals(self) -> int:
        """
        查询代币精度

        Returns:
            代币精度（小数位数）
        """
        if not self.contract:
            raise ContractError("Contract not initialized")

        return self.call_contract_function(
            self.contract.functions.decimals()
        )


__all__ = [
    "VIBETokenClient",
]
