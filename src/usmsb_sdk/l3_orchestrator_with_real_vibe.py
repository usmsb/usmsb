# -*- coding: utf-8 -*-
"""
L3OrchestratorWithRealVIBE - 集成真实 VIBE Token 的 L3Orchestrator

继承 L3Orchestrator，集成真实 VIBE Token 经济：

功能：
- 使用 VIBETokenClient 连接 Base Sepolia 上的 VIBE Token
- Layer Settlement 费用支付
- Matching Fee 支付
- Agent 奖励发放

使用方式：
    orch = L3OrchestratorWithRealVIBE(agent_id="agent_001")
    
    # 发送 VIBE
    await orch.real_token_economy.transfer_vibe(to_address, amount)
    
    # 支付 Layer Fee
    await orch.real_token_economy.pay_layer_fee(layer=2, amount=10)
"""

import asyncio
import os
from typing import Any

from usmsb_sdk.l3_orchestrator import L3Orchestrator
from usmsb_sdk.economic.real_token_economy import RealVIBETokenEconomy


class L3OrchestratorWithRealVIBE(L3Orchestrator):
    """
    集成真实 VIBE Token 的 L3Orchestrator
    
    除了 L3Orchestrator 的所有功能外，还支持：
    - 真实 VIBE Token 转账
    - Layer Fee 支付
    - Matching Fee 支付
    - Agent 奖励
    """
    
    def __init__(
        self,
        agent_id: str,
        services: dict | None = None,
        llm_adapter=None,
        private_key: str | None = None,
        network: str = "base_sepolia",
    ):
        """
        初始化 L3OrchestratorWithRealVIBE
        
        Args:
            agent_id: Agent ID
            services: L4 服务
            llm_adapter: LLM 适配器
            private_key: 钱包私钥（从环境变量 VIBE_PRIVATE_KEY 读取）
            network: 网络 (base_sepolia, base, mainnet)
        """
        # 初始化父类
        super().__init__(
            agent_id=agent_id,
            services=services,
            llm_adapter=llm_adapter,
        )
        
        # VIBE Token 经济
        self.private_key = private_key or os.environ.get("VIBE_PRIVATE_KEY")
        self.network = network
        
        self.real_token_economy = RealVIBETokenEconomy(
            private_key=self.private_key,
        )
        
        print(f"[L3OrchestratorWithRealVIBE] Initialized on {network}")
        try:
            address = getattr(self.real_token_economy.web3_client, 'wallet_address', None)
            if address:
                balance = self.real_token_economy.get_balance(address)
                print(f"[L3OrchestratorWithRealVIBE] Connected, Balance: {balance}")
            else:
                print(f"[L3OrchestratorWithRealVIBE] Running in read-only mode")
        except Exception as e:
            print(f"[L3OrchestratorWithRealVIBE] Running in read-only mode: {e}")
    
    async def transfer_vibe(self, to_address: str, amount: float) -> bool:
        """
        转移 VIBE Token
        
        Args:
            to_address: 接收地址
            amount: 数量
            
        Returns:
            bool: 是否成功
        """
        return await self.real_token_economy.transfer_vibe(to_address, amount)
    
    async def pay_matching_fee(self, amount: float) -> bool:
        """
        支付 Matching Fee
        
        Args:
            amount: 数量
            
        Returns:
            bool: 是否成功
        """
        return await self.real_token_economy.calculate_and_pay_matching_fee(amount)
    
    async def pay_layer_fee(self, layer: int, amount: float) -> bool:
        """
        支付 Layer Fee
        
        Args:
            layer: Layer 编号
            amount: 数量
            
        Returns:
            bool: 是否成功
        """
        return await self.real_token_economy.pay_layer_fee(layer, amount)
    
    async def reward_agent(self, agent_id: str, amount: float) -> bool:
        """
        奖励 Agent
        
        Args:
            agent_id: Agent ID
            amount: 数量
            
        Returns:
            bool: 是否成功
        """
        # 获取 agent 的钱包地址（简化版，实际需要查询）
        # 这里只是示例，实际应该从 AgentRegistry 获取
        return await self.real_token_economy.reward_agent(agent_id, amount)
    
    def get_vibe_balance(self) -> float:
        """获取 VIBE 余额"""
        try:
            # 尝试从 web3_client 获取地址
            address = self.real_token_economy.web3_client.wallet_address if hasattr(self.real_token_economy.web3_client, 'wallet_address') else None
            if address:
                return self.real_token_economy.get_balance(address)
        except Exception:
            pass
        return 0.0
    
    def get_wallet_address(self) -> str:
        """获取钱包地址"""
        try:
            if hasattr(self.real_token_economy.web3_client, 'wallet_address'):
                return self.real_token_economy.web3_client.wallet_address
        except Exception:
            pass
        return "unknown"
    
    async def run_autonomous_with_economy(self) -> dict:
        """
        运行自主周期 + 经济操作
        
        Returns:
            dict: 运行结果
        """
        # 运行基础周期
        result = self.run_cycle()
        
        # 添加经济信息
        result["vibe_balance"] = self.get_vibe_balance()
        result["wallet_address"] = self.get_wallet_address()
        
        return result
