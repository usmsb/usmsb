"""
区块链配置管理模块

提供多网络配置管理，支持测试网、主网和本地开发环境。
通过环境变量 VIBE_NETWORK 和 VIBE_RPC_URL 进行配置。
"""

import os
from enum import Enum

from pydantic import BaseModel


class NetworkType(Enum):
    """网络类型枚举"""
    TESTNET = "testnet"   # Base Sepolia
    MAINNET = "mainnet"   # Base Mainnet
    LOCAL = "local"       # 本地开发


class NetworkConfig(BaseModel):
    """单个网络的配置模型"""
    name: str
    chain_id: int
    rpc_url: str
    explorer_url: str
    contracts: dict[str, str]

    model_config = {"frozen": True}


# 预定义网络配置
_NETWORKS: dict[NetworkType, NetworkConfig] = {
    NetworkType.TESTNET: NetworkConfig(
        name="Base Sepolia",
        chain_id=84532,
        rpc_url="https://sepolia.base.org",
        explorer_url="https://sepolia.basescan.org",
        contracts={
            "VIBEToken": "0x211BEAfF36775089Fa2e2Ad31aF797b5482cC189",
            "VIBStaking": "0x3108D8F72d4Ea0e64738D2275f513D01b1E33083",
            "VIBVesting": "0x452AE65f597A6e9c1ECAC2CB3AeBc3A6FCa272c2",
            "VIBReserve": "0xE99189ABe26306E25760CB3228BC0FEA3f0B8252",
            "VIBProtocolFund": "0x84a101C9d3E553251648Fe216FAfE1e933E4eA7a",
            "VIBInfrastructurePool": "0xd2172EB2D32F07a73D103Aa1F803A18f83aB4B26",
            "VIBBuilderReward": "0xFc60B29664c723cb8970690A4CE08f079b8F922D",
            "VIBDevReward": "0xD2710F80C34b477EadE275F2e642d1F6051e3f1C",
            "VIBIdentity": "0x1E65FB872b997Dce30b8fb3b106b2FBdFD0cFf2E",
            "VIBNodeReward": "0xBa33dFf94627463a3344fEd3DF4BBC634b693dFD",
            "VIBCollaboration": "0xfe7e9831bb88Fefbbb43d7525239458F8388bFa6",
            "VIBDividend": "0x0e4372c3e8e2E8f2eC7518Ebde0671Aa567Ef1CE",
            "AgentRegistry": "0xd27972E461Bf49e5eAC0Ee558248bC86a3b0836E",
            "ZKCredential": "0xD23a416d02B9963eB69df59db1A21218e11b03CE",
            "JointOrder": "0xa80A9A7bda3E9aEff55A2d4E1da1362B1E901EeD",
            "VIBGovernance": "0x4624732022De6a3A53E25D10F726687Cb33Ca337",
            "VIBOutputReward": "0xE949976295A2Af52a7A8017FbBf2F2b7dcD80dE6",
            "AirdropDistributor": "0x8967Dff66E79BD1548bCEB34307ef8EF37eBf30c",
            "VIBGovernanceDelegation": "0x8003c7e4459186F4bce9669e7b9BA7ED651C3a71",
            "VIBContributionPoints": "0x2cbB07431aac73bDa29A65c755a0C9DAc25bBF1E",
            "VIBVEPoints": "0x6803A33fccE80CC590904e8Bd478F152ef688e0C",
            "VIBDispute": "0x3a61228c22C3360D39866e7a288f185e838b6779",
            "AgentWallet": "0x27E8a52c53a2ab16e78B8FF99aaEDB59c19F9409",
            "EmissionController": "0xE56Af4725865329C155Cf0941BeD48C8094Fd033",
        }
    ),
    NetworkType.MAINNET: NetworkConfig(
        name="Base",
        chain_id=8453,
        rpc_url="https://mainnet.base.org",
        explorer_url="https://basescan.org",
        contracts={
            "VIBEToken": "待部署",
            "VIBStaking": "待部署",
            "AgentRegistry": "待部署",
            "VIBIdentity": "待部署",
            "VIBCollaboration": "待部署",
            "JointOrder": "待部署",
            "VIBDividend": "待部署",
            "VIBGovernance": "待部署",
            "ZKCredential": "待部署",
        }
    ),
    NetworkType.LOCAL: NetworkConfig(
        name="Local",
        chain_id=31337,
        rpc_url="http://localhost:8545",
        explorer_url="",
        contracts={}
    )
}


class BlockchainConfig:
    """区块链配置管理器

    提供统一的区块链配置接口，支持多网络切换和RPC URL覆盖。
    """

    def __init__(self, network: NetworkType | None = None, rpc_url: str | None = None):
        """
        初始化配置

        Args:
            network: 网络类型，如不指定则从环境变量 VIBE_NETWORK 读取，默认为 TESTNET
            rpc_url: RPC URL，如不指定则使用配置中的默认值或环境变量 VIBE_RPC_URL
        """
        # 优先使用环境变量
        env_network = os.environ.get("VIBE_NETWORK", "").lower()
        if env_network:
            try:
                network = NetworkType(env_network)
            except ValueError:
                raise ValueError(f"Invalid VIBE_NETWORK value: {env_network}. "
                               f"Must be one of: {[n.value for n in NetworkType]}")
        elif network is None:
            network = NetworkType.TESTNET  # 默认测试网

        self.network_type = network
        self.config = _NETWORKS[network]

        # 允许通过参数或环境变量覆盖RPC
        if rpc_url:
            self._rpc_url = rpc_url
        else:
            env_rpc = os.environ.get("VIBE_RPC_URL")
            self._rpc_url = env_rpc if env_rpc else self.config.rpc_url

    @property
    def chain_id(self) -> int:
        """获取当前网络的链ID"""
        return self.config.chain_id

    @property
    def rpc_url(self) -> str:
        """获取RPC URL"""
        return self._rpc_url

    @property
    def network_name(self) -> str:
        """获取网络名称"""
        return self.config.name

    @property
    def explorer_url(self) -> str:
        """获取区块浏览器基础URL"""
        return self.config.explorer_url

    @property
    def contracts(self) -> dict[str, str]:
        """获取合约地址字典"""
        return self.config.contracts

    def get_contract_address(self, name: str) -> str | None:
        """
        获取指定合约的地址

        Args:
            name: 合约名称，如 "VIBEToken", "VIBStaking" 等

        Returns:
            合约地址，如不存在则返回 None
        """
        return self.config.contracts.get(name)

    def get_explorer_url(self, tx_hash: str) -> str:
        """
        获取交易的区块浏览器URL

        Args:
            tx_hash: 交易哈希

        Returns:
            完整的区块浏览器URL
        """
        return f"{self.config.explorer_url}/tx/{tx_hash}"

    def get_address_url(self, address: str) -> str:
        """
        获取地址的区块浏览器URL

        Args:
            address: 以太坊地址

        Returns:
            完整的区块浏览器URL
        """
        return f"{self.config.explorer_url}/address/{address}"

    def is_mainnet(self) -> bool:
        """判断是否为主网"""
        return self.network_type == NetworkType.MAINNET

    def is_testnet(self) -> bool:
        """判断是否为测试网"""
        return self.network_type == NetworkType.TESTNET

    def is_local(self) -> bool:
        """判断是否为本地环境"""
        return self.network_type == NetworkType.LOCAL


def get_default_config() -> BlockchainConfig:
    """获取默认配置（基于环境变量或测试网）"""
    return BlockchainConfig()


__all__ = [
    "NetworkType",
    "NetworkConfig",
    "BlockchainConfig",
    "get_default_config",
]
