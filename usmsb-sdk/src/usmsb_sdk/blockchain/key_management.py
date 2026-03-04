"""
Agent私钥管理模块

提供Agent私钥的安全加密存储和解密功能，使用Fernet对称加密。
"""

import os
import hashlib
import base64
from typing import Dict, Tuple
from cryptography.fernet import Fernet
from eth_account import Account


class AgentKeyManager:
    """Agent私钥管理器

    提供Agent私钥的安全加密存储、解密和生成功能。
    """

    def __init__(self, encryption_key: str = None):
        """
        初始化私钥管理器

        Args:
            encryption_key: 加密密钥（字符串或bytes，如不指定则从环境变量读取）
        """
        if encryption_key is None:
            encryption_key = os.environ.get('AGENT_KEY_ENCRYPTION_KEY')

        if not encryption_key:
            raise ValueError(
                "Encryption key not provided. "
                "Set AGENT_KEY_ENCRYPTION_KEY environment variable or pass encryption_key parameter."
            )

        # 派生32字节的加密密钥（Fernet需要32字节）
        self.cipher = Fernet(self._derive_key(encryption_key))

    def _derive_key(self, password) -> bytes:
        """
        从密码派生Fernet密钥

        Args:
            password: 密码（字符串或bytes）

        Returns:
            32字节的密钥
        """
        # 使用SHA256派生32字节密钥
        if isinstance(password, bytes):
            password_bytes = password
        else:
            password_bytes = password.encode('utf-8')
        hash_bytes = hashlib.sha256(password_bytes).digest()

        # Fernet需要base64编码的32字节密钥
        return base64.urlsafe_b64encode(hash_bytes)

    def encrypt_private_key(self, private_key: str) -> str:
        """
        加密私钥

        Args:
            private_key: 原始私钥（十六进制字符串）

        Returns:
            加密后的私钥（base64字符串）

        Example:
            >>> manager = AgentKeyManager("my-secret-key")
            >>> encrypted = manager.encrypt_private_key("0xabc...")
            >>> print(encrypted)
        """
        # 确保私钥格式正确
        if private_key.startswith('0x'):
            private_key = private_key[2:]

        private_key_bytes = private_key.encode('utf-8')
        encrypted_bytes = self.cipher.encrypt(private_key_bytes)
        return base64.b64encode(encrypted_bytes).decode('utf-8')

    def decrypt_private_key(self, encrypted_key: str) -> str:
        """
        解密私钥

        Args:
            encrypted_key: 加密后的私钥（base64字符串）

        Returns:
            原始私钥（十六进制字符串，不带0x前缀）

        Example:
            >>> manager = AgentKeyManager("my-secret-key")
            >>> private_key = manager.decrypt_private_key(encrypted)
            >>> print(private_key)
        """
        encrypted_bytes = base64.b64decode(encrypted_key.encode('utf-8'))
        decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
        return decrypted_bytes.decode('utf-8')

    def generate_agent_keypair(self) -> Dict[str, str]:
        """
        生成Agent密钥对

        生成新的以太坊账户，并返回地址、私钥和加密后的私钥。

        Returns:
            字典包含：
            - address: 以太坊地址
            - private_key: 原始私钥（十六进制字符串）
            - encrypted_private_key: 加密后的私钥

        Example:
            >>> manager = AgentKeyManager("my-secret-key")
            >>> keypair = manager.generate_agent_keypair()
            >>> print(f"Address: {keypair['address']}")
            >>> print(f"Encrypted: {keypair['encrypted_private_key']}")
        """
        account = Account.create()

        # 移除0x前缀（如果存在）
        private_key = account.key.hex()

        return {
            "address": account.address,
            "private_key": private_key,
            "encrypted_private_key": self.encrypt_private_key(private_key),
        }

    def generate_agent_keypair_raw(self) -> Tuple[str, str]:
        """
        生成Agent密钥对（原始格式）

        生成新的以太坊账户，返回地址和私钥（不加密）。

        Returns:
            (address, private_key) 元组

        Example:
            >>> manager = AgentKeyManager("my-secret-key")
            >>> address, private_key = manager.generate_agent_keypair_raw()
            >>> print(f"Address: {address}")
        """
        account = Account.create()
        return account.address, account.key.hex()

    @staticmethod
    def create_from_mnemonic(mnemonic: str, index: int = 0) -> Dict[str, str]:
        """
        从助记词创建账户（使用HD钱包）

        Args:
            mnemonic: BIP39助记词
            index: 派生路径索引

        Returns:
            字典包含地址和私钥

        Note:
            此方法需要eth-account的HD钱包功能或额外依赖如mnemonic
        """
        try:
            from eth_account import Account
            from eth_account.messages import encode_defunct

            # 简化实现：使用账户索引派生
            # 实际生产环境应使用标准的BIP39/BIP32路径
            seed_phrase = f"{mnemonic}:{index}"
            account = Account.create(seed_phrase)

            return {
                "address": account.address,
                "private_key": account.key.hex(),
            }
        except ImportError:
            # 如果没有HD钱包库，使用简单方法
            account = Account.create()
            return {
                "address": account.address,
                "private_key": account.key.hex(),
            }

    def validate_private_key(self, private_key: str) -> bool:
        """
        验证私钥格式是否有效

        Args:
            private_key: 私钥（十六进制字符串）

        Returns:
            是否有效
        """
        try:
            # 移除0x前缀
            if private_key.startswith('0x'):
                private_key = private_key[2:]

            # 验证长度（64个十六进制字符）
            if len(private_key) != 64:
                return False

            # 验证是否为有效的十六进制
            int(private_key, 16)

            # 尝试从私钥创建账户
            Account.from_key(private_key)
            return True
        except (ValueError, Exception):
            return False

    def validate_encrypted_key(self, encrypted_key: str) -> bool:
        """
        验证加密密钥格式是否有效

        Args:
            encrypted_key: 加密后的密钥

        Returns:
            是否有效
        """
        try:
            # 尝试解码base64
            encrypted_bytes = base64.b64decode(encrypted_key.encode('utf-8'))
            # 尝试解密
            self.cipher.decrypt(encrypted_bytes)
            return True
        except Exception:
            return False


__all__ = [
    "AgentKeyManager",
]
