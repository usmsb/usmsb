"""
Encryption Module

Provides AES-256-GCM encryption/decryption utilities and wallet signature-based key derivation.
"""

import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class Encryption:
    """
    AES-256-GCM encryption utility.

    Provides secure encryption and decryption for user data stored on IPFS.
    """

    # Nonce size for AES-GCM (96 bits = 12 bytes)
    NONCE_SIZE = 12

    # Key derivation salt and info constants
    DEFAULT_SALT = b"USMSB_META_AGENT_v1"
    KEY_INFO = b"encryption_key"

    @staticmethod
    def encrypt(data: bytes, key: bytes) -> bytes:
        """
        Encrypt data using AES-256-GCM.

        Args:
            data: Raw data to encrypt
            key: 32-byte encryption key (AES-256)

        Returns:
            Encrypted data with nonce prepended: nonce + ciphertext

        Raises:
            ValueError: If key is not 32 bytes
        """
        if len(key) != 32:
            raise ValueError(f"Encryption key must be 32 bytes (AES-256), got {len(key)} bytes")

        # Generate random nonce
        nonce = os.urandom(Encryption.NONCE_SIZE)

        # Encrypt using AES-GCM
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, data, None)

        # Return nonce + ciphertext
        return nonce + ciphertext

    @staticmethod
    def decrypt(encrypted: bytes, key: bytes) -> bytes:
        """
        Decrypt AES-256-GCM encrypted data.

        Args:
            encrypted: Encrypted data with nonce prepended
            key: 32-byte encryption key (AES-256)

        Returns:
            Decrypted data

        Raises:
            ValueError: If key is not 32 bytes
            cryptography.exceptions.InvalidTag: If decryption fails (wrong key or corrupted data)
        """
        if len(key) != 32:
            raise ValueError(f"Decryption key must be 32 bytes (AES-256), got {len(key)} bytes")

        # Extract nonce and ciphertext
        nonce = encrypted[:Encryption.NONCE_SIZE]
        ciphertext = encrypted[Encryption.NONCE_SIZE:]

        # Decrypt using AES-GCM
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)

        return plaintext

    @staticmethod
    def derive_key_from_signature(signature: str, salt: bytes | None = None) -> bytes:
        """
        Derive AES-256 encryption key from a wallet signature.

        Uses HKDF (HMAC-based Extract-and-Expand Key Derivation Function)
        with SHA-256 to derive a secure key from the signature.

        Args:
            signature: Wallet signature string
            salt: Optional salt for key derivation (defaults to DEFAULT_SALT)

        Returns:
            32-byte encryption key suitable for AES-256
        """
        if salt is None:
            salt = Encryption.DEFAULT_SALT

        # Convert signature to bytes
        signature_bytes = signature.encode('utf-8')

        # Use HKDF to derive a 32-byte key
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,  # AES-256 requires 32 bytes
            salt=salt,
            info=Encryption.KEY_INFO,
            backend=default_backend()
        )

        key = hkdf.derive(signature_bytes)

        return key

    @staticmethod
    def generate_key() -> bytes:
        """
        Generate a random 32-byte encryption key.

        Returns:
            32-byte random key
        """
        return os.urandom(32)

    @staticmethod
    def hash_key(key: bytes) -> str:
        """
        Hash a key for identification purposes (e.g., logging).

        Args:
            key: Encryption key

        Returns:
            Hexadecimal hash of the key
        """
        import hashlib
        return hashlib.sha256(key).hexdigest()


class KeyDerivation:
    """
    Encryption key derivation strategy using EIP-191 personal signature.

    Users sign a fixed message to generate their encryption key.
    The key is derived from the signature using HKDF and exists only in memory.
    """

    # Signing message (fixed) - EIP-191 compatible
    SIGN_MESSAGE = """
    Sign this message to generate your encryption key.

    This signature will be used to encrypt your private data
    before storing it on IPFS.

    Only sign this message on trusted platforms!
    """

    # Key derivation constants
    _DEFAULT_SALT = b"USMSB_META_AGENT_v1"
    _KEY_INFO = b"encryption_key"
    _KEY_LENGTH = 32  # AES-256

    @staticmethod
    def derive_key_from_signature(signature: str) -> bytes:
        """
        Derive AES-256 encryption key from wallet signature.

        Process:
        1. User signs the fixed message in their wallet
        2. Frontend sends the signature to backend
        3. Backend uses HKDF to derive key from signature
        4. Key exists only in memory, not persisted

        Args:
            signature: Wallet signature string (hex-encoded)

        Returns:
            32-byte encryption key suitable for AES-256

        Raises:
            ValueError: If signature is empty or invalid
        """
        if not signature:
            raise ValueError("Signature cannot be empty")

        # Clean signature (remove 0x prefix if present)
        signature_clean = signature.strip()
        if signature_clean.startswith("0x"):
            signature_clean = signature_clean[2:]

        try:
            # Convert hex signature to bytes for key derivation
            signature_bytes = bytes.fromhex(signature_clean)
        except ValueError:
            # If not hex, use the string directly
            signature_bytes = signature.encode('utf-8')

        # Use HKDF to derive a 32-byte key
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=KeyDerivation._KEY_LENGTH,  # AES-256
            salt=KeyDerivation._DEFAULT_SALT,
            info=KeyDerivation._KEY_INFO,
            backend=default_backend()
        )

        key = hkdf.derive(signature_bytes)

        return key

    @staticmethod
    def verify_signature(
        message: str,
        signature: str,
        expected_address: str
    ) -> bool:
        """
        Verify signature is from expected wallet address.

        Uses EIP-191/ecrecover to verify the signature.

        Args:
            message: The message that was signed
            signature: The signature (hex-encoded)
            expected_address: The expected wallet address (hex)

        Returns:
            True if signature is valid and from expected address, False otherwise

        Raises:
            ImportError: If eth-account or web3 is not available
            ValueError: If signature or address format is invalid
        """
        try:
            from eth_account import Account
            from eth_account.messages import encode_defunct
        except ImportError:
            try:
                from web3 import Web3
            except ImportError:
                raise ImportError(
                    "Either 'eth-account' or 'web3' package is required for signature verification. "
                    "Install with: pip install eth-account"
                )
            # Fallback to web3 approach
            return KeyDerivation._verify_with_web3(message, signature, expected_address)

        # Normalize the message (EIP-191 personal sign)
        message_text = message.strip()
        message_encoded = encode_defunct(text=message_text)

        # Clean signature
        signature_clean = signature.strip()
        if signature_clean.startswith("0x"):
            signature_clean = signature_clean[2:]

        try:
            # Recover address from signature
            signature_bytes = bytes.fromhex(signature_clean)
            recovered_address = Account.recover_message(message_encoded, signature=signature_bytes)
        except Exception as e:
            raise ValueError(f"Invalid signature format: {e}")

        # Normalize addresses for comparison
        expected_normalized = expected_address.lower().strip()
        if expected_normalized.startswith("0x"):
            expected_normalized = expected_normalized[2:]

        recovered_normalized = recovered_address.lower().strip()
        if recovered_normalized.startswith("0x"):
            recovered_normalized = recovered_normalized[2:]

        return recovered_normalized == expected_normalized

    @staticmethod
    def _verify_with_web3(
        message: str,
        signature: str,
        expected_address: str
    ) -> bool:
        """
        Verify signature using Web3 library.

        Args:
            message: The message that was signed
            signature: The signature (hex-encoded)
            expected_address: The expected wallet address (hex)

        Returns:
            True if signature is valid and from expected address
        """
        from web3 import Web3

        # Clean signature
        signature_clean = signature.strip()
        if signature_clean.startswith("0x"):
            signature_clean = signature_clean[2:]

        # Recover address from signature
        recovered_address = Web3.eth.account.recover_message(
            text=message.strip(),
            signature=signature_clean
        )

        # Normalize addresses for comparison
        expected_normalized = expected_address.lower().strip()
        if expected_normalized.startswith("0x"):
            expected_normalized = expected_normalized[2:]

        recovered_normalized = recovered_address.lower().strip()
        if recovered_normalized.startswith("0x"):
            recovered_normalized = recovered_normalized[2:]

        return recovered_normalized == expected_normalized

    @staticmethod
    def get_sign_message() -> str:
        """
        Get the fixed signing message for encryption key derivation.

        Returns:
            The message that users should sign
        """
        return KeyDerivation.SIGN_MESSAGE.strip()

    @staticmethod
    def generate_test_signature(
        private_key: str,
        message: str | None = None
    ) -> tuple[str, str]:
        """
        Generate a test signature (for testing purposes only).

        Args:
            private_key: Private key to sign with (hex)
            message: Message to sign (defaults to SIGN_MESSAGE)

        Returns:
            Tuple of (signature, address)
        """
        from eth_account import Account

        if message is None:
            message = KeyDerivation.SIGN_MESSAGE.strip()

        # Clean private key
        private_key_clean = private_key.strip()
        if private_key_clean.startswith("0x"):
            private_key_clean = private_key_clean[2:]

        # Create account from private key
        account = Account.from_key(private_key_clean)

        # Sign message
        from eth_account.messages import encode_defunct
        message_encoded = encode_defunct(text=message)
        signed_message = Account.sign_message(message_encoded, private_key_clean)

        return (signed_message.signature.hex(), account.address)
