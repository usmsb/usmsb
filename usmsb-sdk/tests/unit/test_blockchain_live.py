"""
区块链集成测试 - 真实链上测试

测试与Base Sepolia测试网的真实交互
"""

import pytest
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))


class TestLiveBlockchainConnection:
    """真实区块链连接测试"""

    def test_vibe_blockchain_client_connection(self):
        """测试统一客户端连接"""
        from usmsb_sdk.blockchain import VIBEBlockchainClient

        client = VIBEBlockchainClient()
        result = client.test_connection()

        assert result["connected"] is True
        assert result["chain_id"] == 84532
        assert result["chain_match"] is True
        print(f"✅ Connected to {result['network_name']} at block {result['block_number']}")

    def test_token_client_initialization(self):
        """测试代币客户端初始化"""
        from usmsb_sdk.blockchain import VIBEBlockchainClient

        client = VIBEBlockchainClient()

        # 获取代币客户端（延迟加载）
        token_client = client.token
        assert token_client is not None
        print(f"✅ Token client initialized for {client.config.get_contract_address('VIBEToken')}")

    def test_query_token_info(self):
        """测试查询代币信息"""
        from usmsb_sdk.blockchain import VIBEBlockchainClient

        client = VIBEBlockchainClient()

        # 查询代币名称和符号
        name = client.token.name()
        symbol = client.token.symbol()
        decimals = client.token.decimals()

        assert "VIBE" in name  # 名称包含VIBE
        assert symbol == "VIBE"
        assert decimals == 18
        print(f"✅ Token: {name} ({symbol}), Decimals: {decimals}")

    def test_query_token_balance(self):
        """测试查询代币余额"""
        from usmsb_sdk.blockchain import VIBEBlockchainClient

        client = VIBEBlockchainClient()

        # 使用一个已知的地址查询余额
        test_address = "0x91d8C3084b4fd21A04fA3584BFE357F378938dbc"  # Token合约地址
        balance = client.token.balance_of_vibe(test_address)

        assert balance >= 0
        print(f"✅ Balance of {test_address[:10]}...: {balance:.2f} VIBE")

    def test_query_total_supply(self):
        """测试查询总供应量"""
        from usmsb_sdk.blockchain import VIBEBlockchainClient

        client = VIBEBlockchainClient()

        supply = client.token.total_supply_vibe()
        # 总供应量可能为0（如果尚未mint）或正值
        assert supply >= 0
        print(f"✅ Total supply: {supply:,.0f} VIBE")

    def test_registry_client_initialization(self):
        """测试注册表客户端初始化"""
        from usmsb_sdk.blockchain import VIBEBlockchainClient

        client = VIBEBlockchainClient()
        registry = client.registry
        assert registry is not None
        print(f"✅ Registry client initialized")

    def test_staking_client_initialization(self):
        """测试质押客户端初始化"""
        from usmsb_sdk.blockchain import VIBEBlockchainClient

        client = VIBEBlockchainClient()
        staking = client.staking
        assert staking is not None
        print(f"✅ Staking client initialized")

    def test_get_explorer_url(self):
        """测试区块浏览器URL生成"""
        from usmsb_sdk.blockchain import VIBEBlockchainClient

        client = VIBEBlockchainClient()

        tx_url = client.get_explorer_url("0x1234567890abcdef")
        assert "sepolia.basescan.org" in tx_url
        assert "0x1234567890abcdef" in tx_url
        print(f"✅ Explorer URL: {tx_url}")


class TestTaxCalculation:
    """交易税计算测试"""

    def test_tax_rate(self):
        """测试税率计算"""
        from usmsb_sdk.blockchain.contracts.vibe_token import VIBETokenClient
        from usmsb_sdk.blockchain import VIBEBlockchainClient

        client = VIBEBlockchainClient()

        # 测试不同金额的税费计算
        amounts = [100, 1000, 10000, 1000000]

        for amount in amounts:
            amount_wei = amount * (10 ** 18)
            breakdown = client.token.get_tax_breakdown(amount_wei)

            # 验证税率是0.8%
            assert breakdown["tax_rate"] == 0.008

            # 验证税费计算正确
            expected_tax = amount * 0.008
            assert abs(breakdown["tax_vibe"] - expected_tax) < 0.0001

            # 验证实际到账金额
            expected_net = amount - expected_tax
            assert abs(breakdown["net_vibe"] - expected_net) < 0.0001

            print(f"✅ Tax for {amount} VIBE: {breakdown['tax_vibe']:.4f} VIBE (net: {breakdown['net_vibe']:.4f})")


class TestNetworkSwitching:
    """网络切换测试"""

    def test_testnet_config(self):
        """测试网配置"""
        from usmsb_sdk.blockchain import VIBEBlockchainClient
        from usmsb_sdk.blockchain.config import BlockchainConfig, NetworkType

        config = BlockchainConfig(network=NetworkType.TESTNET)
        client = VIBEBlockchainClient(config=config)

        assert client.config.chain_id == 84532
        assert client.config.is_testnet()
        print(f"✅ Testnet config: chain_id={client.config.chain_id}")

    def test_mainnet_config(self):
        """主网配置（不连接）"""
        from usmsb_sdk.blockchain.config import BlockchainConfig, NetworkType

        config = BlockchainConfig(network=NetworkType.MAINNET)

        assert config.chain_id == 8453
        assert config.is_mainnet()
        print(f"✅ Mainnet config: chain_id={config.chain_id}")

    def test_local_config(self):
        """本地配置（不连接）"""
        from usmsb_sdk.blockchain.config import BlockchainConfig, NetworkType

        config = BlockchainConfig(network=NetworkType.LOCAL)

        assert config.chain_id == 31337
        assert config.is_local()
        print(f"✅ Local config: chain_id={config.chain_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
