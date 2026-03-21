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
            "VIBEToken": "0x93C52dF000317e12F891474B46d8B05652430bDC",
            "VIBStaking": "0x1901Ab56eA38cBeFc7a3F0Ed188B7108d27f4c05",
            "VIBVesting": "0x4d3008550fc164ccf0e1C0C4f666E77FC14dE924",
            "VIBReserve": "0x56AbAf5fc5d58c92C0A51F79251BF3A3002f4263",
            "VIBProtocolFund": "0x0F39011e7E542D939C1dce40754a86b01BB3fA5a",
            "VIBInfrastructurePool": "0xFc2943d6D426D4D6433944e1ADa4D475F3552500",
            "VIBBuilderReward": "0x397Faf7D727db190fB677362B15c091f1d94F7b3",
            "VIBDevReward": "0x1a5E99b52e87E718906e8516fDD9c8775Ee0351E",
            "VIBIdentity": "0x978eddDf11728B4e6A6C461D8806eD5f4339D466",
            "VIBNodeReward": "0xc417b180F3b743A51e86c16A8319Eac353fDC29b",
            "VIBCollaboration": "0xe568c56f467E27Cb38d4B132B02318C81EC29D78",
            "VIBDividend": "0x0e4372c3e8e2E8f2eC7518Ebde0671Aa567Ef1CE",
            "AgentRegistry": "0xC5AbAE9f580C48D645bDE9904712891AE8FcDec6",
            "ZKCredential": "0x59EE17f1E914ba2de89F080CF44FC46Ee46DF874",
            "JointOrder": "0x55f4b49c9C269Fccf6d90e16304654b7F69138d0",
            "VIBGovernance": "0x27475aea1eEba485005B1717a35a7D411d144a1d",
            "VIBOutputReward": "0x7b3CEB40CFb093e66EcD5b49F835586Ba7Ef428b",
            "AirdropDistributor": "0x01cdC2C7C3Deb071e6C7B42ED66884DDd3CADDf6",
            "VIBGovernanceDelegation": "0x47428bAB428966B32F246a3e9456f10dc70141A5",
            "VIBContributionPoints": "0x60D9244bF262bF85Fd3057C95Ca00fEa1622f3E5",
            "VIBVEPoints": "0xB2b56dce955ab200E0c1888C22Ac711803e607F1",
            "VIBDispute": "0xE32d99daDBd4443423EfDc590af7591f84FAFE7e",
            "AgentWallet": "0xeAd5FCC931493F702208B737528578718D681243",
            "EmissionController": "0xaeD496480c9668dc90Dc309fCD8Fd9aE4268dF39",
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

    @classmethod
    def from_env(cls) -> "BlockchainConfig":
        """
        从环境变量创建配置实例。

        读取以下环境变量:
        - VIBE_NETWORK: 网络类型 (mainnet/testnet/base_sepolia)
        - VIBE_RPC_URL: 自定义RPC URL

        Returns:
            BlockchainConfig 实例
        """
        return cls()

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
