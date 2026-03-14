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
            "VIBEToken": "0x91d8C3084b4fd21A04fA3584BFE357F378938dbc",
            "VIBStaking": "0xc3fbD1736a95f403A0569FcA8C84d7B85e2b4E53",
            "AgentRegistry": "0x54bEbDc40cc8B60b0922D8FA6463ab710B14dC69",
            "VIBIdentity": "0x6b72711045b3a384E26eD9039CFF4cA12b856952",
            "VIBCollaboration": "0x7E61b51c49438696195142D06f46c12d90909059",
            "JointOrder": "0xc63d9DEb845138A2C5CFF41A4Cb519ccbDf00F3a",
            "VIBDividend": "0x324571F84C092a958eB46b3478742C58a7beaE7B",
            "VIBGovernance": "0xD866536154154a378544E9dc295D510a0fe29236",
            "ZKCredential": "0x4B8465Fe80Ec91876da78DB775a551dDdBBdB04a",
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
