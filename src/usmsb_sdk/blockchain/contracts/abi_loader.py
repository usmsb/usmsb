"""
合约ABI加载模块

提供从Hardhat编译输出加载合约ABI和字节码的功能。
"""

import json
import os
from typing import Dict, Optional, Tuple, Any
from pathlib import Path


class ABILoader:
    """合约ABI加载器

    从Hardhat编译输出中加载合约的ABI、字节码等信息。
    支持自动发现合约文件路径。
    """

    # 默认合约编译输出目录
    DEFAULT_ARTIFACTS_DIR = Path(__file__).parent.parent.parent.parent.parent / "contracts" / "artifacts" / "src"

    # 合约名称到文件名的映射（如果文件名与合约名不同）
    CONTRACT_FILE_MAP: Dict[str, str] = {
        # 添加需要特殊映射的合约
    }

    def __init__(self, artifacts_dir: Optional[Path] = None):
        """
        初始化ABI加载器

        Args:
            artifacts_dir: 合约编译输出目录，如不指定则使用默认路径
        """
        self.artifacts_dir = artifacts_dir or self.DEFAULT_ARTIFACTS_DIR
        if not self.artifacts_dir.exists():
            raise ValueError(f"Artifacts directory not found: {self.artifacts_dir}")

    def get_abi(self, contract_name: str) -> list:
        """
        加载合约ABI

        Args:
            contract_name: 合约名称，如 "AgentWallet", "VIBEToken"

        Returns:
            合约ABI列表

        Raises:
            FileNotFoundError: 合约文件未找到
        """
        file_path = self._get_contract_path(contract_name)
        with open(file_path, "r", encoding="utf-8") as f:
            artifact = json.load(f)
        return artifact.get("abi", [])

    def get_bytecode(self, contract_name: str) -> str:
        """
        加载合约字节码

        Args:
            contract_name: 合约名称

        Returns:
            合约字节码（deployment字节码）

        Raises:
            FileNotFoundError: 合约文件未找到
        """
        file_path = self._get_contract_path(contract_name)
        with open(file_path, "r", encoding="utf-8") as f:
            artifact = json.load(f)

        bytecode = artifact.get("bytecode", "")
        # 处理不同格式：有些是字符串，有些是 {"object": "...", "sourceMap": "..."}
        if isinstance(bytecode, dict):
            return bytecode.get("object", "")
        return bytecode

    def get_abi_and_bytecode(self, contract_name: str) -> Tuple[list, str]:
        """
        同时加载ABI和字节码

        Args:
            contract_name: 合约名称

        Returns:
            (ABI, 字节码) 元组
        """
        file_path = self._get_contract_path(contract_name)
        with open(file_path, "r", encoding="utf-8") as f:
            artifact = json.load(f)

        bytecode = artifact.get("bytecode", "")
        # 处理不同格式：有些是字符串，有些是 {"object": "...", "sourceMap": "..."}
        if isinstance(bytecode, dict):
            bytecode = bytecode.get("object", "")

        return artifact.get("abi", []), bytecode

    def get_full_artifact(self, contract_name: str) -> Dict[str, Any]:
        """
        加载完整的合约编译产物

        Args:
            contract_name: 合约名称

        Returns:
            完整的artifact字典
        """
        file_path = self._get_contract_path(contract_name)
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _get_contract_path(self, contract_name: str) -> Path:
        """
        获取合约文件路径

        Args:
            contract_name: 合约名称

        Returns:
            合约文件的完整路径

        Raises:
            FileNotFoundError: 合约文件未找到
        """
        # 检查是否有自定义文件映射
        file_name = self.CONTRACT_FILE_MAP.get(contract_name, contract_name)

        # 尝试几种可能的路径格式
        possible_paths = [
            self.artifacts_dir / f"{file_name}.sol" / f"{file_name}.json",
            self.artifacts_dir / file_name / f"{file_name}.json",
        ]

        for path in possible_paths:
            if path.exists():
                return path

        # 如果都找不到，抛出异常
        raise FileNotFoundError(
            f"Contract artifact not found for '{contract_name}'. "
            f"Checked: {[str(p) for p in possible_paths]}"
        )

    def list_available_contracts(self) -> list[str]:
        """
        列出所有可用的合约

        Returns:
            合约名称列表
        """
        contracts = []
        if not self.artifacts_dir.exists():
            return contracts

        for item in self.artifacts_dir.iterdir():
            if item.is_dir() and not item.name.startswith("@"):
                # 检查是否有对应的json文件
                json_file = item / f"{item.name}.json"
                if json_file.exists():
                    contracts.append(item.name)

        return sorted(contracts)


# 全局单例加载器
_default_loader: Optional[ABILoader] = None


def get_abi_loader() -> ABILoader:
    """
    获取默认的ABI加载器（单例）

    Returns:
        ABILoader实例
    """
    global _default_loader
    if _default_loader is None:
        _default_loader = ABILoader()
    return _default_loader


def load_abi(contract_name: str, artifacts_dir: Optional[Path] = None) -> list:
    """
    快捷函数：加载合约ABI

    Args:
        contract_name: 合约名称
        artifacts_dir: 可选的artifacts目录

    Returns:
        合约ABI列表
    """
    loader = ABILoader(artifacts_dir) if artifacts_dir else get_abi_loader()
    return loader.get_abi(contract_name)


def load_bytecode(contract_name: str, artifacts_dir: Optional[Path] = None) -> str:
    """
    快捷函数：加载合约字节码

    Args:
        contract_name: 合约名称
        artifacts_dir: 可选的artifacts目录

    Returns:
        合约字节码
    """
    loader = ABILoader(artifacts_dir) if artifacts_dir else get_abi_loader()
    return loader.get_bytecode(contract_name)


def load_abi_and_bytecode(
    contract_name: str,
    artifacts_dir: Optional[Path] = None,
) -> Tuple[list, str]:
    """
    快捷函数：同时加载ABI和字节码

    Args:
        contract_name: 合约名称
        artifacts_dir: 可选的artifacts目录

    Returns:
        (ABI, 字节码) 元组
    """
    loader = ABILoader(artifacts_dir) if artifacts_dir else get_abi_loader()
    return loader.get_abi_and_bytecode(contract_name)


__all__ = [
    "ABILoader",
    "get_abi_loader",
    "load_abi",
    "load_bytecode",
    "load_abi_and_bytecode",
]
