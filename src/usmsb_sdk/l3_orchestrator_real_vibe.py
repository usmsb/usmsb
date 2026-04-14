# -*- coding: utf-8 -*-
"""
L3OrchestratorWithRealVIBE - 带真实 VIBE Token 的 L3 编排器

集成了 Base Sepolia 测试网上的真实 VIBE Token 合约。

使用方式：
    # 设置私钥
    os.environ["VIBE_PRIVATE_KEY"] = "0x..."
    
    # 创建编排器
    orch = L3OrchestratorWithRealVIBE(
        agent_id="agent_001",
        wallet_address="0x...",  # 钱包地址
    )
    
    # 查询余额
    balance = orch.get_vibe_balance()
    
    # 转账
    orch.transfer_vibe(to="0x...", amount=100.0)
"""

import os
from typing import Any

from usmsb_sdk.l3_orchestrator import L3Orchestrator
from usmsb_sdk.economic.real_token_economy import RealVIBETokenEconomy


class L3OrchestratorWithRealVIBE(L3Orchestrator):
    """
    带真实 VIBE Token 的 L3 编排器
    
    在原有 L3Orchestrator 基础上增加：
    - 真实区块链 VIBE Token 操作
    - 链上余额查询
    - 链上转账
    - 质押和奖励
    
    使用真实合约：
    - VIBEToken: 0x93C52dF000317e12F891474B46d8B05652430bDC
    - 网络: Base Sepolia
    """
    
    def __init__(
        self,
        agent_id: str,
        wallet_address: str,
        services: dict | None = None,
        llm_adapter=None,
    ):
        """
        初始化
        
        Args:
            agent_id: Agent ID
            wallet_address: 钱包地址（用于查询余额和转账）
            services: L4 服务
            llm_adapter: LLM 适配器
        """
        # 初始化父类
        super().__init__(agent_id, services, llm_adapter)
        
        # 钱包地址
        self.wallet_address = wallet_address
        
        # 初始化真实 VIBE 经济系统
        self.vibe_economy = RealVIBETokenEconomy()
        
        # 更新 Agent 状态中的资源
        self._update_resources_from_chain()
    
    def _update_resources_from_chain(self) -> None:
        """从链上更新资源"""
        try:
            balance = self.vibe_economy.get_balance(self.wallet_address)
            self._resources = balance
            self.agent_state.resources = balance
        except Exception as e:
            print(f"[L3OrchestratorWithRealVIBE] Failed to update resources: {e}")
    
    # =========================================================================
    # VIBE Token 操作
    # =========================================================================
    
    def get_vibe_balance(self) -> float:
        """
        获取 VIBE 余额（从链上）
        
        Returns:
            float: VIBE 余额
        """
        balance = self.vibe_economy.get_balance(self.wallet_address)
        self._resources = balance
        return balance
    
    def transfer_vibe(
        self,
        to_address: str,
        amount: float,
    ) -> dict:
        """
        转账 VIBE Token（链上）
        
        Args:
            to_address: 接收方地址
            amount: VIBE 数量
            
        Returns:
            dict: 交易结果
        """
        result = self.vibe_economy.transfer(
            from_address=self.wallet_address,
            to_address=to_address,
            amount=amount,
        )
        
        if result:
            # 更新本地余额
            self._update_resources_from_chain()
            
            return {
                "success": True,
                "tx_hash": result.tx_hash,
                "amount": amount,
                "to": to_address,
                "status": result.status,
            }
        
        return {
            "success": False,
            "error": "Transfer failed",
        }
    
    def approve_vibe(self, spender: str, amount: float) -> dict:
        """
        授权 VIBE Token
        
        Args:
            spender: 获授权者地址
            amount: 授权数量
            
        Returns:
            dict: 授权结果
        """
        result = self.vibe_economy.approve(
            owner_address=self.wallet_address,
            spender_address=spender,
            amount=amount,
        )
        
        if result:
            return {
                "success": True,
                "tx_hash": result.tx_hash,
                "amount": amount,
                "spender": spender,
            }
        
        return {
            "success": False,
            "error": "Approve failed",
        }
    
    def get_allowance(self, spender: str) -> float:
        """查询授权额度"""
        return self.vibe_economy.get_allowance(self.wallet_address, spender)
    
    # =========================================================================
    # 经济操作
    # =========================================================================
    
    def calculate_and_pay_matching_fee(self, order_value: float) -> float:
        """
        计算并支付匹配费（1%）
        
        Args:
            order_value: 订单价值
            
        Returns:
            float: 实际支付的 VIBE 数量
        """
        fee = self.vibe_economy.calculate_matching_fee(order_value)
        
        if fee > 0:
            # 支付给系统地址（模拟）
            system_address = "0x0000000000000000000000000000000000000001"
            self.transfer_vibe(system_address, fee)
        
        return fee
    
    def pay_layer_fee(self, order_value: float, layer: int) -> float:
        """
        支付分层费
        
        Args:
            order_value: 订单价值
            layer: 层数 (1, 2, 3)
            
        Returns:
            float: 实际支付的 VIBE 数量
        """
        if layer == 1:
            fee = self.vibe_economy.calculate_matching_fee(order_value)
        elif layer == 2:
            fee = self.vibe_economy.calculate_layer2_fee(order_value)
        elif layer == 3:
            fee = self.vibe_economy.calculate_layer3_fee(order_value)
        else:
            fee = 0.0
        
        if fee > 0:
            system_address = "0x0000000000000000000000000000000000000001"
            self.transfer_vibe(system_address, fee)
        
        return fee
    
    # =========================================================================
    # 价值创造和分配
    # =========================================================================
    
    def receive_payment(self, from_address: str, amount: float) -> dict:
        """
        接收支付（用于价值创造）
        
        Args:
            from_address: 付款方地址
            amount: VIBE 数量
            
        Returns:
            dict: 接收结果
        """
        # 实际应该在链上确认，这里简化处理
        self._update_resources_from_chain()
        
        return {
            "success": True,
            "amount": amount,
            "from": from_address,
            "new_balance": self._resources,
        }
    
    def reward_agent(self, agent_address: str, amount: float) -> dict:
        """
        奖励 Agent（用于激励机制）
        
        Args:
            agent_address: Agent 地址
            amount: 奖励数量
            
        Returns:
            dict: 奖励结果
        """
        return self.transfer_vibe(agent_address, amount)
    
    # =========================================================================
    # 状态查询
    # =========================================================================
    
    def get_agent_status(self) -> dict:
        """
        获取完整 Agent 状态（增强版）
        
        包含链上 VIBE 信息
        """
        status = super().get_agent_status()
        
        # 添加链上信息
        try:
            status["blockchain"] = {
                "wallet_address": self.wallet_address,
                "vibe_balance": self.get_vibe_balance(),
                "network": self.vibe_economy.get_network_info()["network"],
            }
        except Exception as e:
            status["blockchain"] = {
                "error": str(e),
            }
        
        return status
    
    def get_network_info(self) -> dict:
        """获取网络信息"""
        return self.vibe_economy.get_network_info()
    
    def __repr__(self) -> str:
        return f"L3OrchestratorWithRealVIBE(agent={self.agent_id}, wallet={self.wallet_address[:10]}...)"
