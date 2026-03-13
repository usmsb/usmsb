"""
区块链配置测试脚本

验证多网络配置和Web3客户端功能。
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from usmsb_sdk.blockchain.config import (
    NetworkType,
    BlockchainConfig,
    get_default_config,
)
from usmsb_sdk.blockchain.web3_client import Web3Client
from usmsb_sdk.blockchain.contracts.base import BaseContractClient


def test_config():
    """测试配置模块"""
    print("=== 测试配置模块 ===")

    # 测试默认配置
    config = BlockchainConfig()
    print(f"默认网络: {config.network_name}")
    print(f"Chain ID: {config.chain_id}")
    print(f"RPC URL: {config.rpc_url}")

    # 测试测试网配置
    testnet_config = BlockchainConfig(network=NetworkType.TESTNET)
    print(f"\n测试网网络: {testnet_config.network_name}")
    print(f"测试网Chain ID: {testnet_config.chain_id}")
    assert testnet_config.chain_id == 84532, "测试网chain_id不正确"
    print("测试网chain_id验证通过!")

    # 测试主网配置
    mainnet_config = BlockchainConfig(network=NetworkType.MAINNET)
    print(f"\n主网网络: {mainnet_config.network_name}")
    print(f"主网Chain ID: {mainnet_config.chain_id}")
    assert mainnet_config.chain_id == 8453, "主网chain_id不正确"
    print("主网chain_id验证通过!")

    # 测试本地配置
    local_config = BlockchainConfig(network=NetworkType.LOCAL)
    print(f"\n本地网络: {local_config.network_name}")
    print(f"本地Chain ID: {local_config.chain_id}")
    assert local_config.chain_id == 31337, "本地chain_id不正确"
    print("本地chain_id验证通过!")

    # 测试合约地址获取
    print(f"\nVIBEToken地址: {testnet_config.get_contract_address('VIBEToken')}")
    print(f"VIBStaking地址: {testnet_config.get_contract_address('VIBStaking')}")
    print(f"AgentRegistry地址: {testnet_config.get_contract_address('AgentRegistry')}")

    # 验证合约地址
    assert testnet_config.get_contract_address("VIBEToken") == "0x91d8C3084b4fd21A04fA3584BFE357F378938dbc"
    assert testnet_config.get_contract_address("VIBStaking") == "0xc3fbD1736a95f403A0569FcA8C84d7B85e2b4E53"
    assert testnet_config.get_contract_address("AgentRegistry") == "0x54bEbDc40cc8B60b0922D8FA6463ab710B14dC69"
    print("合约地址验证通过!")

    # 测试网络类型判断
    assert testnet_config.is_testnet()
    assert not testnet_config.is_mainnet()
    assert not testnet_config.is_local()
    print("网络类型判断验证通过!")

    print("\n配置模块测试通过!")


def test_web3_client():
    """测试Web3客户端"""
    print("\n=== 测试Web3客户端 ===")

    config = BlockchainConfig(network=NetworkType.TESTNET)
    client = Web3Client(config=config)

    # 测试连接
    result = client.test_connection()
    print(f"连接状态: {'成功' if result['connected'] else '失败'}")
    if result["connected"]:
        print(f"链ID: {result['chain_id']}")
        print(f"区块高度: {result['block_number']}")
        print(f"网络名称: {result['network_name']}")
        print(f"Chain匹配: {result['chain_match']}")

    print("Web3客户端测试通过!")


def test_base_contract_client():
    """测试基础合约客户端"""
    print("\n=== 测试基础合约客户端 ===")

    config = BlockchainConfig(network=NetworkType.TESTNET)
    web3_client = Web3Client(config=config)
    contract_client = BaseContractClient(
        web3_client=web3_client,
        config=config,
    )

    # 测试交易构建（使用有效的私钥生成的地址）
    from eth_account import Account
    test_addr = Account.from_key('0x' + '1' * 64).address
    tx = contract_client.build_transaction(
        from_address=test_addr,
        value=contract_client.w3.to_wei(0.1, "ether"),
    )

    print(f"交易from: {tx['from']}")
    print(f"交易chainId: {tx['chainId']}")
    print(f"交易value: {tx['value']}")
    print(f"交易nonce: {tx['nonce']}")

    # 验证chainId不是硬编码的
    assert tx['chainId'] == config.chain_id, "chainId应从配置获取"
    print("交易chainId验证通过!")

    print("基础合约客户端测试通过!")


if __name__ == "__main__":
    try:
        test_config()
        test_web3_client()
        test_base_contract_client()
        print("\n" + "=" * 40)
        print("所有测试通过!")
        print("=" * 40)
    except AssertionError as e:
        print(f"\n测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
