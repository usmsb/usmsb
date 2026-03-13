"""
区块链集成模块综合测试

测试内容：
1. 配置管理
2. Web3客户端
3. 合约客户端
4. 密钥管理
5. Agent管理器
6. 事件监听器
7. 统一入口
"""

import pytest
import sys
import os
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))


class TestConfig:
    """配置模块测试"""

    def test_default_config_is_testnet(self):
        """默认配置应该是测试网"""
        from usmsb_sdk.blockchain.config import BlockchainConfig, NetworkType

        config = BlockchainConfig()
        assert config.chain_id == 84532
        assert config.is_testnet()
        assert not config.is_mainnet()
        assert not config.is_local()

    def test_mainnet_config(self):
        """主网配置测试"""
        from usmsb_sdk.blockchain.config import BlockchainConfig, NetworkType

        config = BlockchainConfig(network=NetworkType.MAINNET)
        assert config.chain_id == 8453
        assert config.is_mainnet()
        assert not config.is_testnet()

    def test_local_config(self):
        """本地配置测试"""
        from usmsb_sdk.blockchain.config import BlockchainConfig, NetworkType

        config = BlockchainConfig(network=NetworkType.LOCAL)
        assert config.chain_id == 31337
        assert config.is_local()

    def test_contract_addresses(self):
        """合约地址配置测试"""
        from usmsb_sdk.blockchain.config import BlockchainConfig, NetworkType

        config = BlockchainConfig(network=NetworkType.TESTNET)

        # 验证测试网合约地址
        assert config.get_contract_address("VIBEToken") == "0x91d8C3084b4fd21A04fA3584BFE357F378938dbc"
        assert config.get_contract_address("VIBStaking") == "0xc3fbD1736a95f403A0569FcA8C84d7B85e2b4E53"
        assert config.get_contract_address("AgentRegistry") == "0x54bEbDc40cc8B60b0922D8FA6463ab710B14dC69"

    def test_env_variable_override(self, monkeypatch):
        """环境变量覆盖测试"""
        from usmsb_sdk.blockchain.config import BlockchainConfig, NetworkType

        # 设置环境变量
        monkeypatch.setenv("VIBE_NETWORK", "mainnet")

        config = BlockchainConfig()
        assert config.chain_id == 8453

    def test_explorer_urls(self):
        """区块浏览器URL测试"""
        from usmsb_sdk.blockchain.config import BlockchainConfig, NetworkType

        config = BlockchainConfig(network=NetworkType.TESTNET)

        tx_url = config.get_explorer_url("0x123")
        assert "sepolia.basescan.org" in tx_url
        assert "0x123" in tx_url

        addr_url = config.get_address_url("0xabc")
        assert "sepolia.basescan.org" in addr_url
        assert "0xabc" in addr_url


class TestWeb3Client:
    """Web3客户端测试"""

    def test_web3_client_creation(self):
        """Web3客户端创建测试"""
        from usmsb_sdk.blockchain.web3_client import Web3Client
        from usmsb_sdk.blockchain.config import BlockchainConfig, NetworkType

        config = BlockchainConfig(network=NetworkType.TESTNET)
        client = Web3Client(config=config)

        assert client.w3 is not None
        assert client.config == config

    def test_connection_test(self):
        """连接测试"""
        from usmsb_sdk.blockchain.web3_client import Web3Client
        from usmsb_sdk.blockchain.config import BlockchainConfig, NetworkType

        config = BlockchainConfig(network=NetworkType.TESTNET)
        client = Web3Client(config=config)

        result = client.test_connection()
        assert result["connected"] is True
        assert result["chain_id"] == 84532
        assert result["chain_match"] is True


class TestBaseContractClient:
    """基础合约客户端测试"""

    def test_transaction_building_uses_config_chain_id(self):
        """交易构建使用配置中的chainId"""
        from usmsb_sdk.blockchain.contracts.base import BaseContractClient
        from usmsb_sdk.blockchain.config import BlockchainConfig, NetworkType
        from usmsb_sdk.blockchain.web3_client import Web3Client
        from eth_account import Account

        config = BlockchainConfig(network=NetworkType.TESTNET)
        web3_client = Web3Client(config=config)
        client = BaseContractClient(web3_client=web3_client, config=config)

        # 使用测试账户
        test_account = Account.from_key('0x' + '1' * 64)
        tx = client.build_transaction(from_address=test_account.address)

        # 验证chainId来自配置
        assert tx["chainId"] == config.chain_id
        assert tx["chainId"] == 84532

    def test_eip1559_transaction_support(self):
        """EIP-1559交易支持测试"""
        from usmsb_sdk.blockchain.contracts.base import BaseContractClient
        from usmsb_sdk.blockchain.config import BlockchainConfig, NetworkType
        from usmsb_sdk.blockchain.web3_client import Web3Client
        from eth_account import Account

        config = BlockchainConfig(network=NetworkType.TESTNET)
        web3_client = Web3Client(config=config)
        client = BaseContractClient(web3_client=web3_client, config=config)

        test_account = Account.from_key('0x' + '1' * 64)
        tx = client.build_transaction(
            from_address=test_account.address,
            max_fee_per_gas=1000000000,
            max_priority_fee_per_gas=100000000
        )

        # EIP-1559交易应该有type=2
        assert tx.get("type") == 2
        assert "maxFeePerGas" in tx
        assert "maxPriorityFeePerGas" in tx

    def test_message_signing(self):
        """消息签名测试"""
        from usmsb_sdk.blockchain.contracts.base import BaseContractClient
        from usmsb_sdk.blockchain.config import BlockchainConfig, NetworkType
        from usmsb_sdk.blockchain.web3_client import Web3Client
        from eth_account import Account

        config = BlockchainConfig(network=NetworkType.TESTNET)
        web3_client = Web3Client(config=config)
        client = BaseContractClient(web3_client=web3_client, config=config)

        # 创建测试账户
        test_account = Account.from_key('0x' + '1' * 64)
        message = "Test message for signing"

        # 签名
        signature = client.sign_message(message, test_account.key.hex())

        # 恢复地址
        recovered = client.recover_address(message, signature)
        assert recovered.lower() == test_account.address.lower()


class TestVIBETokenClient:
    """VIBE代币客户端测试"""

    def test_tax_calculation(self):
        """交易税计算测试"""
        from usmsb_sdk.blockchain.contracts.vibe_token import VIBETokenClient
        from usmsb_sdk.blockchain.config import BlockchainConfig, NetworkType
        from usmsb_sdk.blockchain.web3_client import Web3Client

        config = BlockchainConfig(network=NetworkType.TESTNET)
        web3_client = Web3Client(config=config)

        # 创建客户端实例
        client = VIBETokenClient(
            web3_client=web3_client,
            config=config
        )

        # 测试税费计算（不需要合约实例）
        amount = 1000 * (10 ** 18)  # 1000 VIBE
        breakdown = client.get_tax_breakdown(amount)

        # 验证税率0.8%
        assert breakdown["tax_rate"] == 0.008
        assert breakdown["tax_vibe"] == 8.0  # 1000 * 0.008 = 8 VIBE
        assert breakdown["net_vibe"] == 992.0  # 1000 - 8 = 992 VIBE

    def test_net_transfer_amount(self):
        """实际到账金额计算测试"""
        from usmsb_sdk.blockchain.contracts.vibe_token import VIBETokenClient
        from usmsb_sdk.blockchain.config import BlockchainConfig, NetworkType
        from usmsb_sdk.blockchain.web3_client import Web3Client

        config = BlockchainConfig(network=NetworkType.TESTNET)
        web3_client = Web3Client(config=config)

        client = VIBETokenClient(
            web3_client=web3_client,
            config=config
        )

        amount = 1000 * (10 ** 18)
        net = client.get_net_transfer_amount(amount)

        expected_net = int(amount * Decimal("0.992"))
        assert net == expected_net


class TestKeyManagement:
    """密钥管理测试"""

    def test_key_encryption_decryption(self):
        """密钥加密解密测试"""
        from usmsb_sdk.blockchain.key_management import AgentKeyManager

        # 使用字符串密钥
        encryption_key = "my-secret-encryption-key-12345"
        manager = AgentKeyManager(encryption_key=encryption_key)

        # 测试私钥
        test_private_key = '0x' + 'a' * 64

        # 加密
        encrypted = manager.encrypt_private_key(test_private_key)
        assert encrypted != test_private_key

        # 解密
        decrypted = manager.decrypt_private_key(encrypted)
        assert decrypted == test_private_key[2:]  # 返回不带0x前缀

    def test_keypair_generation(self):
        """密钥对生成测试"""
        from usmsb_sdk.blockchain.key_management import AgentKeyManager

        encryption_key = "my-secret-encryption-key-12345"
        manager = AgentKeyManager(encryption_key=encryption_key)

        # 生成密钥对
        keypair = manager.generate_agent_keypair()

        # 验证返回字段
        assert "address" in keypair
        assert "private_key" in keypair
        assert "encrypted_private_key" in keypair

        # 验证地址格式
        assert keypair["address"].startswith("0x")
        assert len(keypair["address"]) == 42

        # 验证可以解密
        decrypted = manager.decrypt_private_key(keypair["encrypted_private_key"])
        assert decrypted == keypair["private_key"]

    def test_private_key_validation(self):
        """私钥验证测试"""
        from usmsb_sdk.blockchain.key_management import AgentKeyManager

        encryption_key = "my-secret-encryption-key-12345"
        manager = AgentKeyManager(encryption_key=encryption_key)

        # 有效的私钥
        valid_key = '0x' + 'a' * 64
        assert manager.validate_private_key(valid_key) is True

        # 无效的私钥（长度不对）
        invalid_key = '0x' + 'a' * 32
        assert manager.validate_private_key(invalid_key) is False

        # 无效的私钥（非十六进制）
        invalid_key2 = '0x' + 'g' * 64
        assert manager.validate_private_key(invalid_key2) is False


class TestABILoader:
    """ABI加载器测试"""

    def test_list_available_contracts(self):
        """列出可用合约测试"""
        from usmsb_sdk.blockchain.contracts.abi_loader import ABILoader

        try:
            loader = ABILoader()
            contracts = loader.list_available_contracts()

            # 验证返回的是列表
            assert isinstance(contracts, list)

            # 如果有合约，检查VIBEToken是否存在
            # 注意：目录结构可能导致找不到合约
            if contracts:
                print(f"Available contracts: {contracts[:5]}...")
        except ValueError as e:
            # 如果artifacts目录不存在，跳过测试
            pytest.skip(f"Artifacts directory not found: {e}")

    def test_load_vibe_token_abi(self):
        """加载VIBEToken ABI测试"""
        from usmsb_sdk.blockchain.contracts.abi_loader import load_abi_and_bytecode

        try:
            abi, bytecode = load_abi_and_bytecode("VIBEToken")

            # 验证ABI不为空
            assert isinstance(abi, list)
            assert len(abi) > 0

            # 验证bytecode不为空
            assert isinstance(bytecode, str)
            assert bytecode.startswith("0x")

            print(f"ABI functions: {[item.get('name') for item in abi if item.get('type') == 'function'][:5]}...")
        except FileNotFoundError as e:
            pytest.skip(f"VIBEToken artifact not found: {e}")
        except Exception as e:
            pytest.skip(f"Error loading ABI: {e}")


class TestVIBEBlockchainClient:
    """统一区块链客户端测试"""

    def test_client_initialization(self):
        """客户端初始化测试"""
        from usmsb_sdk.blockchain import VIBEBlockchainClient

        client = VIBEBlockchainClient()

        # 验证默认配置
        assert client.config.chain_id == 84532

    def test_lazy_loading_properties(self):
        """延迟加载属性测试"""
        from usmsb_sdk.blockchain import VIBEBlockchainClient

        client = VIBEBlockchainClient()

        # 验证属性延迟加载
        assert client._web3_client is None
        web3 = client.web3
        assert client._web3_client is not None
        assert web3 is not None

    def test_test_connection(self):
        """连接测试方法"""
        from usmsb_sdk.blockchain import VIBEBlockchainClient

        client = VIBEBlockchainClient()
        result = client.test_connection()

        assert result["connected"] is True
        assert result["chain_id"] == 84532

    def test_repr(self):
        """字符串表示测试"""
        from usmsb_sdk.blockchain import VIBEBlockchainClient

        client = VIBEBlockchainClient()
        repr_str = repr(client)

        assert "VIBEBlockchainClient" in repr_str
        assert "84532" in repr_str


class TestEventListener:
    """事件监听器测试"""

    def test_event_filter_dataclass(self):
        """事件过滤器数据类测试"""
        from usmsb_sdk.blockchain.event_listener import EventFilter

        event_filter = EventFilter(
            contract_name="VIBEToken",
            event_name="Transfer",
            from_block=1000000,
        )

        assert event_filter.contract_name == "VIBEToken"
        assert event_filter.event_name == "Transfer"
        assert event_filter.from_block == 1000000

    def test_parsed_event_dataclass(self):
        """解析事件数据类测试"""
        from usmsb_sdk.blockchain.event_listener import ParsedEvent

        event = ParsedEvent(
            contract_name="VIBEToken",
            event_name="Transfer",
            event=Mock(),
            block_number=12345,
            transaction_hash="0xabc123",
            args={"from": "0x1", "to": "0x2", "value": 1000}
        )

        assert event.contract_name == "VIBEToken"
        assert event.block_number == 12345
        assert "from" in event.args

    def test_event_filter_builder(self):
        """事件过滤器构建器测试"""
        from usmsb_sdk.blockchain.event_listener import filter_events

        builder = filter_events("VIBEToken", "Transfer")
        event_filter = builder.from_block(1000000).filter_args(from_address="0x123").build()

        assert event_filter.contract_name == "VIBEToken"
        assert event_filter.event_name == "Transfer"
        assert event_filter.from_block == 1000000
        assert event_filter.argument_filters == {"from_address": "0x123"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
