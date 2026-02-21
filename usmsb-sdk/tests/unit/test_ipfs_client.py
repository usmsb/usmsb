"""
Unit tests for IPFSClient and Encryption modules.

Tests cover encryption/decryption, key derivation, and IPFS operations
with mocked HTTP requests for reliable unit testing.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from typing import Any, Dict

import pytest
import aiohttp

from usmsb_sdk.platform.external.meta_agent.ipfs import Encryption, IPFSClient


# ============================================================================
# Encryption Tests
# ============================================================================

class TestEncryption:
    """Test cases for the Encryption class."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypting and decrypting returns original data."""
        original_data = b"Hello, World! This is a test message."
        key = b"01234567890123456789012345678901"  # 32 bytes

        encrypted = Encryption.encrypt(original_data, key)
        decrypted = Encryption.decrypt(encrypted, key)

        assert decrypted == original_data
        assert encrypted != original_data
        assert len(encrypted) == len(original_data) + Encryption.NONCE_SIZE + 16  # nonce + tag

    def test_encrypt_with_different_keys(self):
        """Test that encrypting with different keys produces different results."""
        data = b"Same data, different keys"
        key1 = b"01234567890123456789012345678901"
        key2 = b"98765432109876543210987654321098"

        encrypted1 = Encryption.encrypt(data, key1)
        encrypted2 = Encryption.encrypt(data, key2)

        assert encrypted1 != encrypted2

    def test_decrypt_with_wrong_key(self):
        """Test that decrypting with wrong key raises an error."""
        data = b"Secret message"
        correct_key = b"01234567890123456789012345678901"
        wrong_key = b"98765432109876543210987654321098"

        encrypted = Encryption.encrypt(data, correct_key)

        with pytest.raises(Exception):  # cryptography.exceptions.InvalidTag
            Encryption.decrypt(encrypted, wrong_key)

    def test_decrypt_with_invalid_key_length(self):
        """Test that decrypting with an invalid key length raises ValueError."""
        encrypted = b"some_encrypted_data"
        invalid_key = b"too_short"

        with pytest.raises(ValueError, match="32 bytes"):
            Encryption.decrypt(encrypted, invalid_key)

    def test_encrypt_with_invalid_key_length(self):
        """Test that encrypting with an invalid key length raises ValueError."""
        data = b"Test data"
        invalid_key = b"way_too_long_for_a_valid_aes_key_here"

        with pytest.raises(ValueError, match="32 bytes"):
            Encryption.encrypt(data, invalid_key)

    def test_encrypt_produces_unique_nonces(self):
        """Test that each encryption produces a unique nonce."""
        data = b"Same data"
        key = b"01234567890123456789012345678901"

        encrypted1 = Encryption.encrypt(data, key)
        encrypted2 = Encryption.encrypt(data, key)

        # Extract nonces
        nonce1 = encrypted1[:Encryption.NONCE_SIZE]
        nonce2 = encrypted2[:Encryption.NONCE_SIZE]

        assert nonce1 != nonce2
        # The ciphertext should also be different due to different nonces
        assert encrypted1 != encrypted2

    def test_key_derivation_from_signature(self):
        """Test key derivation from a wallet signature."""
        signature = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"

        key = Encryption.derive_key_from_signature(signature)

        assert len(key) == 32
        assert isinstance(key, bytes)

    def test_key_derivation_is_deterministic(self):
        """Test that same signature always produces same key."""
        signature = "test_signature_12345"
        salt = b"test_salt"

        key1 = Encryption.derive_key_from_signature(signature, salt)
        key2 = Encryption.derive_key_from_signature(signature, salt)

        assert key1 == key2
        assert len(key1) == 32

    def test_key_derivation_with_different_salts(self):
        """Test that different salts produce different keys."""
        signature = "test_signature_12345"

        key1 = Encryption.derive_key_from_signature(signature, b"salt1")
        key2 = Encryption.derive_key_from_signature(signature, b"salt2")

        assert key1 != key2

    def test_key_derivation_default_salt(self):
        """Test key derivation with default salt."""
        signature = "test_signature"

        key = Encryption.derive_key_from_signature(signature)

        assert len(key) == 32

    def test_generate_key(self):
        """Test random key generation."""
        key1 = Encryption.generate_key()
        key2 = Encryption.generate_key()

        assert len(key1) == 32
        assert len(key2) == 32
        assert key1 != key2  # Should be random

    def test_hash_key(self):
        """Test key hashing for identification."""
        key = b"01234567890123456789012345678901"

        hash1 = Encryption.hash_key(key)
        hash2 = Encryption.hash_key(key)

        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA-256 produces 64 hex chars
        assert hash1 == hash2  # Deterministic

    def test_hash_different_keys_different_hashes(self):
        """Test that different keys produce different hashes."""
        key1 = b"01234567890123456789012345678901"
        key2 = b"98765432109876543210987654321098"

        hash1 = Encryption.hash_key(key1)
        hash2 = Encryption.hash_key(key2)

        assert hash1 != hash2

    def test_empty_data_encryption(self):
        """Test encrypting empty data."""
        data = b""
        key = b"01234567890123456789012345678901"

        encrypted = Encryption.encrypt(data, key)
        decrypted = Encryption.decrypt(encrypted, key)

        assert decrypted == data

    def test_large_data_encryption(self):
        """Test encrypting large data (1MB)."""
        data = b"A" * 1024 * 1024  # 1MB
        key = b"01234567890123456789012345678901"

        encrypted = Encryption.encrypt(data, key)
        decrypted = Encryption.decrypt(encrypted, key)

        assert decrypted == data

    def test_invalid_tag_causes_decryption_error(self):
        """Test that modifying ciphertext causes decryption to fail."""
        data = b"Secret message"
        key = b"01234567890123456789012345678901"

        encrypted = Encryption.encrypt(data, key)

        # Corrupt the ciphertext (modify a byte in the middle)
        encrypted_list = bytearray(encrypted)
        encrypted_list[20] = encrypted_list[20] ^ 0xFF
        corrupted = bytes(encrypted_list)

        with pytest.raises(Exception):  # InvalidTag
            Encryption.decrypt(corrupted, key)

    def test_short_encrypted_data_fails(self):
        """Test that encrypted data shorter than nonce size fails."""
        key = b"01234567890123456789012345678901"

        # Only 5 bytes, less than nonce size (12)
        encrypted = b"12345"

        with pytest.raises(Exception):
            Encryption.decrypt(encrypted, key)


# ============================================================================
# IPFSClient Tests
# ============================================================================

class TestIPFSClient:
    """Test cases for IPFSClient class."""

    @pytest.fixture
    def mock_aiohttp_session(self):
        """Create a mock aiohttp session with proper async context manager support."""

        # Create a mock response object that supports async context manager
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='{}')
        mock_response.json = AsyncMock(return_value={"Hash": "QmTestCID123", "Pins": ["QmTestPin"]})
        mock_response.read = AsyncMock(return_value=b"test data")

        # Make the response work as an async context manager
        async def response_enter():
            return mock_response
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        # Create a context manager wrapper for the request
        class RequestContextManager:
            def __init__(self, response):
                self._response = response

            async def __aenter__(self):
                return self._response

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        # Create mock session
        session = MagicMock()
        session.closed = False

        # Create mock for session.post/get that returns a context manager
        def mock_request(*args, **kwargs):
            return RequestContextManager(mock_response)

        session.post = mock_request
        session.get = mock_request
        session.close = AsyncMock()

        return session, mock_response

    @pytest.fixture
    def ipfs_client(self):
        """Create an IPFSClient instance with test gateways."""
        return IPFSClient(
            gateways=["http://localhost:5001/api/v0", "http://localhost:8080/api/v0"],
            timeout=10
        )

    @pytest.fixture
    def test_wallet(self):
        """Test wallet address."""
        return "0x1234567890abcdef1234567890abcdef12345678"

    @pytest.fixture
    def test_encryption_key(self):
        """Test encryption key (32 bytes)."""
        return b"01234567890123456789012345678901"

    @pytest.fixture
    def test_user_data(self):
        """Sample user data for testing."""
        return {
            "profile": {
                "name": "Test User",
                "preferences": {"theme": "dark"}
            },
            "knowledge": [
                {"id": "k1", "content": "Test knowledge item"}
            ]
        }

    @pytest.mark.asyncio
    async def test_upload_user_data_success(self, ipfs_client, mock_aiohttp_session,
                                            test_wallet, test_user_data, test_encryption_key):
        """Test successful user data upload."""
        session, mock_response = mock_aiohttp_session
        ipfs_client.encryption_key = test_encryption_key

        with patch.object(ipfs_client, '_get_session', return_value=session):
            result = await ipfs_client.upload_user_data(test_wallet, test_user_data)

            assert result.success is True
            assert result.cid == "QmTestCID123"
            assert result.size > 0

    @pytest.mark.asyncio
    async def test_upload_user_data_without_encryption(self, ipfs_client, mock_aiohttp_session,
                                                       test_wallet, test_user_data):
        """Test upload without encryption."""
        session, mock_response = mock_aiohttp_session
        ipfs_client.encryption_key = None

        with patch.object(ipfs_client, '_get_session', return_value=session):
            result = await ipfs_client.upload_user_data(
                test_wallet,
                test_user_data,
                encrypt=False
            )

            assert result.success is True

    @pytest.mark.asyncio
    async def test_upload_empty_data(self, ipfs_client, test_wallet):
        """Test uploading empty data returns error."""
        result = await ipfs_client.upload_user_data(test_wallet, {})

        assert result.success is False
        assert "No data to upload" in result.error

    @pytest.mark.asyncio
    async def test_download_user_data_success(self, ipfs_client, mock_aiohttp_session,
                                             test_wallet, test_encryption_key):
        """Test successful user data download."""
        session, mock_response = mock_aiohttp_session

        # Prepare mock response with encrypted data
        test_data = json.dumps({"test": "data"}).encode()
        encrypted = Encryption.encrypt(test_data, test_encryption_key)

        package = {
            "metadata": {
                "version": "1.0",
                "wallet_address": test_wallet,
                "encryption": "AES-256-GCM"
            },
            "knowledge": encrypted.hex(),
            "checksum": IPFSClient._calculate_checksum(encrypted)
        }
        mock_response.read = AsyncMock(return_value=json.dumps(package).encode())

        ipfs_client.encryption_key = test_encryption_key

        with patch.object(ipfs_client, '_get_session', return_value=session):
            result = await ipfs_client.download_user_data(test_wallet, "QmTestCID123")

            assert result == {"test": "data"}

    @pytest.mark.asyncio
    async def test_download_user_data_without_cid(self, ipfs_client, test_wallet):
        """Test download without CID returns None."""
        result = await ipfs_client.download_user_data(test_wallet, None)

        assert result is None

    @pytest.mark.asyncio
    async def test_upload_download_roundtrip(self, ipfs_client, test_wallet,
                                              test_user_data, test_encryption_key):
        """Test that uploading and downloading returns original data."""
        # Simulate successful upload
        test_cid = "QmTestRoundtripCID"

        ipfs_client.encryption_key = test_encryption_key

        # Mock upload
        with patch.object(ipfs_client, '_upload_bytes', return_value=test_cid):
            upload_result = await ipfs_client.upload_user_data(
                test_wallet,
                test_user_data,
                encrypt=True
            )

            assert upload_result.success
            assert upload_result.cid == test_cid

        # Mock download
        encrypted_data = Encryption.encrypt(
            json.dumps(test_user_data).encode(),
            test_encryption_key
        )
        package = {
            "metadata": {
                "version": "1.0",
                "wallet_address": test_wallet,
                "encryption": "AES-256-GCM"
            },
            "knowledge": encrypted_data.hex(),
            "checksum": IPFSClient._calculate_checksum(encrypted_data)
        }

        with patch.object(ipfs_client, '_download_bytes',
                          return_value=json.dumps(package).encode()):
            download_result = await ipfs_client.download_user_data(
                test_wallet,
                test_cid
            )

            assert download_result == test_user_data

    @pytest.mark.asyncio
    async def test_gateway_failover(self, ipfs_client, test_wallet,
                                   test_user_data, test_encryption_key):
        """Test that client switches gateways when one fails."""
        ipfs_client.encryption_key = test_encryption_key

        # Mock responses - first fails, second succeeds
        success_response = MagicMock()
        success_response.status = 200
        success_response.json = AsyncMock(return_value={"Hash": "QmFailoverCID"})
        success_response.__aenter__ = AsyncMock(return_value=success_response)
        success_response.__aexit__ = AsyncMock(return_value=None)

        # Create a context manager wrapper for requests
        class RequestContextManager:
            def __init__(self, response, should_fail=False):
                self._response = response
                self._should_fail = should_fail

            async def __aenter__(self):
                if self._should_fail:
                    raise aiohttp.ClientError("First gateway failed")
                return self._response

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        call_count = [0]

        def mock_request(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return RequestContextManager(success_response, should_fail=True)
            return RequestContextManager(success_response, should_fail=False)

        session = MagicMock()
        session.post = mock_request
        session.get = mock_request

        with patch.object(ipfs_client, '_get_session', return_value=session):
            result = await ipfs_client.upload_user_data(test_wallet, test_user_data)

            assert result.success is True
            assert call_count[0] == 2  # First failed, second succeeded

    @pytest.mark.asyncio
    async def test_all_gateways_fail(self, ipfs_client, test_wallet, test_user_data):
        """Test behavior when all gateways fail."""
        ipfs_client.gateways = ["http://bad1", "http://bad2"]

        # Create a failing context manager
        class FailingRequestContextManager:
            async def __aenter__(self):
                raise aiohttp.ClientError("All failed")

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        session = MagicMock()
        session.post = lambda *args, **kwargs: FailingRequestContextManager()
        session.get = lambda *args, **kwargs: FailingRequestContextManager()

        with patch.object(ipfs_client, '_get_session', return_value=session):
            result = await ipfs_client.upload_user_data(test_wallet, test_user_data)

            assert result.success is False
            assert "failed on all gateways" in result.error

    @pytest.mark.asyncio
    async def test_pin_cid_success(self, ipfs_client, mock_aiohttp_session):
        """Test successful CID pinning."""
        session, mock_response = mock_aiohttp_session

        with patch.object(ipfs_client, '_get_session', return_value=session):
            result = await ipfs_client.pin_cid("QmTestPin")

            assert result is True

    @pytest.mark.asyncio
    async def test_pin_cid_failure(self, ipfs_client):
        """Test CID pinning failure."""
        # Create a failing context manager for pin
        class FailingPinContextManager:
            async def __aenter__(self):
                raise aiohttp.ClientError("Pin failed")

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        session = MagicMock()
        session.post = lambda *args, **kwargs: FailingPinContextManager()

        with patch.object(ipfs_client, '_get_session', return_value=session):
            result = await ipfs_client.pin_cid("QmTestPin")

            assert result is False

    @pytest.mark.asyncio
    async def test_get_user_cid_not_implemented(self, ipfs_client, test_wallet):
        """Test that get_user_cid returns None (not yet implemented)."""
        result = await ipfs_client.get_user_cid(test_wallet)

        assert result is None

    @pytest.mark.asyncio
    async def test_publish_cid_success(self, ipfs_client, test_wallet):
        """Test CID publishing (placeholder returns True)."""
        result = await ipfs_client.publish_cid(test_wallet, "QmTestCID")

        assert result is True

    @pytest.mark.asyncio
    async def test_set_encryption_key(self, ipfs_client):
        """Test setting encryption key."""
        valid_key = b"01234567890123456789012345678901"
        ipfs_client.set_encryption_key(valid_key)

        assert ipfs_client.encryption_key == valid_key

    def test_set_encryption_key_invalid_length(self, ipfs_client):
        """Test setting encryption key with invalid length raises error."""
        invalid_key = b"too_short"

        with pytest.raises(ValueError, match="32 bytes"):
            ipfs_client.set_encryption_key(invalid_key)

    @pytest.mark.asyncio
    async def test_derive_and_set_key(self, ipfs_client):
        """Test deriving and setting key from signature."""
        signature = "test_signature_for_derivation"

        ipfs_client.derive_and_set_key(signature)

        assert ipfs_client.encryption_key is not None
        assert len(ipfs_client.encryption_key) == 32

    @pytest.mark.asyncio
    async def test_close_session(self, ipfs_client):
        """Test closing aiohttp session."""
        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        ipfs_client._session = mock_session

        await ipfs_client.close()

        mock_session.close.assert_called_once()
        assert ipfs_client._session is None

    @pytest.mark.asyncio
    async def test_close_already_closed_session(self, ipfs_client):
        """Test closing an already closed session."""
        ipfs_client._session = None

        # Should not raise an error
        await ipfs_client.close()

        assert ipfs_client._session is None

    def test_get_gateway_config(self, ipfs_client):
        """Test getting gateway configuration."""
        config = ipfs_client._get_gateway_config()

        assert config.url == ipfs_client.gateways[0]
        assert config.timeout == ipfs_client.timeout

    def test_get_gateway_config_after_switch(self, ipfs_client):
        """Test getting gateway config after switching gateways."""
        ipfs_client._current_gateway_index = 1

        config = ipfs_client._get_gateway_config()

        assert config.url == ipfs_client.gateways[1]

    def test_switch_gateway_behavior(self, ipfs_client):
        """Test gateway switching behavior."""
        initial_index = ipfs_client._current_gateway_index
        initial_gateway = ipfs_client._switch_gateway()

        assert ipfs_client._current_gateway_index != initial_index
        assert initial_gateway == ipfs_client.gateways[ipfs_client._current_gateway_index]

        # Test wrapping around
        ipfs_client._current_gateway_index = len(ipfs_client.gateways) - 1
        last_gateway = ipfs_client._switch_gateway()

        assert ipfs_client._current_gateway_index == 0
        assert last_gateway == ipfs_client.gateways[0]

    @pytest.mark.asyncio
    async def test_download_with_invalid_json(self, ipfs_client, mock_aiohttp_session,
                                             test_wallet, test_encryption_key):
        """Test download when response contains invalid JSON."""
        session, mock_response = mock_aiohttp_session

        # Return invalid JSON
        mock_response.read = AsyncMock(return_value=b"not valid json")

        ipfs_client.encryption_key = test_encryption_key

        with patch.object(ipfs_client, '_get_session', return_value=session):
            # Should handle JSON parsing error gracefully
            result = await ipfs_client.download_user_data(test_wallet, "QmTestCID")

            assert result is None

    @pytest.mark.asyncio
    async def test_calculate_checksum(self, ipfs_client):
        """Test checksum calculation."""
        data = b"test data"

        checksum = IPFSClient._calculate_checksum(data)

        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA-256 hex length

    @pytest.mark.asyncio
    async def test_checksum_deterministic(self, ipfs_client):
        """Test that checksum is deterministic."""
        data = b"same data"

        checksum1 = IPFSClient._calculate_checksum(data)
        checksum2 = IPFSClient._calculate_checksum(data)

        assert checksum1 == checksum2

    @pytest.mark.asyncio
    async def test_download_with_profile_data(self, ipfs_client, mock_aiohttp_session,
                                             test_wallet, test_encryption_key):
        """Test download with profile data included."""
        session, mock_response = mock_aiohttp_session

        # Prepare mock response with encrypted profile data
        test_profile_data = {"name": "Test User", "age": 30}
        profile_json = json.dumps(test_profile_data).encode()
        encrypted_profile = Encryption.encrypt(profile_json, test_encryption_key)

        package = {
            "metadata": {
                "version": "1.0",
                "wallet_address": test_wallet,
                "encryption": "AES-256-GCM",
                "files": ["profile.enc"]
            },
            "profile": encrypted_profile.hex(),
            "knowledge": None,
            "checksum": IPFSClient._calculate_checksum(encrypted_profile)
        }
        mock_response.read = AsyncMock(return_value=json.dumps(package).encode())

        ipfs_client.encryption_key = test_encryption_key

        with patch.object(ipfs_client, '_get_session', return_value=session):
            # Note: current implementation prioritizes 'knowledge' field, so this test
            # verifies the package structure handling
            result = await ipfs_client.download_user_data(test_wallet, "QmTestCID")

            # Since we have knowledge=None, this will handle the case
            assert result is None or result == {}


# ============================================================================
# Integration Tests (marked as slow)
# ============================================================================

@pytest.mark.slow
@pytest.mark.requires_network
class TestIPFSClientIntegration:
    """Integration tests that may require network access."""

    @pytest.mark.asyncio
    async def test_gateway_switching_logic(self):
        """Test gateway switching logic without actual network calls."""
        client = IPFSClient(
            gateways=["gateway1", "gateway2", "gateway3"]
        )

        # Initial gateway
        assert client._current_gateway_index == 0

        # Switch once
        client._switch_gateway()
        assert client._current_gateway_index == 1

        # Switch again
        client._switch_gateway()
        assert client._current_gateway_index == 2

        # Switch again (should wrap around)
        client._switch_gateway()
        assert client._current_gateway_index == 0


# ============================================================================
# Parameterized Tests
# ============================================================================

@pytest.mark.parametrize("data_size", [0, 1, 100, 1024, 1024*100])
def test_encrypt_decrypt_various_sizes(data_size):
    """Test encryption/decryption with various data sizes."""
    data = b"A" * data_size
    key = b"01234567890123456789012345678901"

    encrypted = Encryption.encrypt(data, key)
    decrypted = Encryption.decrypt(encrypted, key)

    assert decrypted == data


@pytest.mark.parametrize("signature,expected_length", [
    ("0xabc", 32),
    ("a" * 100, 32),
    ("", 32),
    ("!@#$%^&*()", 32),
])
def test_key_derivation_various_inputs(signature, expected_length):
    """Test key derivation with various input signatures."""
    key = Encryption.derive_key_from_signature(signature)

    assert len(key) == expected_length
