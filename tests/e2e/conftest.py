"""
E2E test fixtures. Copies of integration test fixtures for e2e scope.
"""
import pytest
import sqlite3
import time
from unittest.mock import patch

VALID_TX = "0x" + "a" * 64

MOCK_USER = {
    "user_id": "test_user",
    "wallet_address": "0xBOUNDWALLET",
    "agent_id": "agent_bound",
    "name": "BoundAgent",
    "status": "bound",
    "binding_status": "bound",
    "owner_wallet": "0xBOUNDWALLET",
    "capabilities": "[]",
    "description": "Test agent",
    "level": 1,
    "key_id": "bound_key1",
}


def create_test_db():
    """Create in-memory SQLite with production schema."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    from usmsb_sdk.api.database import init_db
    init_db(conn)
    return conn


@pytest.fixture(scope="function")
def integration_db():
    """Fresh in-memory DB per test."""
    conn = create_test_db()
    import usmsb_sdk.api.database as db_mod
    original = db_mod.get_db
    db_mod.get_db = lambda: conn
    yield conn
    db_mod.get_db = original
    conn.close()


@pytest.fixture(scope="function")
def sample_bound_agent(integration_db):
    now = time.time()
    integration_db.execute(
        """INSERT INTO agents
           (agent_id, name, status, owner_wallet, binding_status,
            created_at, updated_at, stake, reputation)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("agent_bound", "BoundAgent", "active", "0xBOUNDWALLET", "bound",
         now, now, 1000.0, 5.0)
    )
    integration_db.execute(
        """INSERT INTO api_keys (key_id, agent_id, key_hash, key_prefix, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        ("bound_key1", "agent_bound", "hash1", "test_", now)
    )
    integration_db.commit()
    return "agent_bound"


@pytest.fixture(scope="function")
def sample_pending_binding(integration_db):
    now = time.time()
    integration_db.execute(
        """INSERT INTO agents
           (agent_id, name, status, binding_status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("agent_pending", "PendingAgent", "active", "pending", now, now)
    )
    integration_db.commit()
    return "agent_pending"


@pytest.fixture(scope="function")
def sample_proposal(integration_db):
    now = time.time()
    integration_db.execute(
        """INSERT INTO proposals
           (id, title, proposer_id, status, votes_for, votes_against, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("prop1", "Test Proposal", "0xPROPOSER", "active", 0, 0, now, now)
    )
    integration_db.commit()
    return "prop1"


@pytest.fixture(scope="module")
def _app():
    import usmsb_sdk.api.database as db_mod
    from usmsb_sdk.api.rest.main import app as main_app
    return main_app, db_mod


@pytest.fixture(scope="function")
def client(_app):
    app, db_mod = _app
    from fastapi.testclient import TestClient
    from usmsb_sdk.api.rest.unified_auth import get_current_user_unified
    from usmsb_sdk.api.rest.auth import get_current_user

    app.dependency_overrides[get_current_user_unified] = lambda: MOCK_USER
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER

    with TestClient(app, raise_server_exceptions=False) as tc:
        yield tc

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Web3 mocks
# ---------------------------------------------------------------------------

class _W3Ctx:
    def __init__(self, mock_w3, original_from_env, patcher):
        self.mock_w3 = mock_w3
        self.original_from_env = original_from_env
        self.patcher = patcher

    def __enter__(self):
        return self.mock_w3

    def __exit__(self, *args):
        self.patcher.stop()
        if self.original_from_env:
            from usmsb_sdk.blockchain.config import BlockchainConfig
            BlockchainConfig.from_env = self.original_from_env


def _make_w3(status=1, from_addr=None):
    class FakeReceipt:
        status = status
        blockNumber = 1000
        confirmations = 1

    eth = FakeReceipt()
    eth.get_transaction_receipt = lambda tx: FakeReceipt()
    eth.chain_id = 84532

    class FakeW3:
        eth = eth
        to_checksum_address = lambda self, x: x

    return FakeW3()


def mock_web3(status=1, from_addr=None):
    from usmsb_sdk.blockchain.config import BlockchainConfig
    original = getattr(BlockchainConfig, 'from_env', None)
    mock_w3 = _make_w3(status=status, from_addr=from_addr)
    patcher = patch("web3.Web3", return_value=mock_w3)
    patcher.start()

    class _Cfg:
        rpc_url = "http://localhost:8545"
        chain_id = 84532

        def get_contract_address(self, name):
            return "0x" + "a" * 40

    BlockchainConfig.from_env = classmethod(lambda cls: _Cfg())
    return _W3Ctx(mock_w3, original, patcher)


def mock_web3_not_found():
    return mock_web3()


def mock_web3_failed():
    return mock_web3(status=0)


class mock_vib_governance_client:
    def __init__(self, proposal_data=None, voting_power=None):
        from unittest.mock import MagicMock, AsyncMock
        if proposal_data is None:
            proposal_data = {
                "id": 1, "proposer": "0xVOTERADDR",
                "proposal_type": MagicMock(), "state": MagicMock(),
                "title": "Test", "description": "Test proposal",
                "target": "0x" + "b" * 40, "data": "", "start_time": 0,
                "end_time": 0, "execute_time": 0, "for_votes": 100,
                "against_votes": 50, "abstain_votes": 10,
                "total_voters": 5, "executed": False,
            }
        self.proposal_data = proposal_data
        self.voting_power = voting_power if voting_power is not None else 1000 * (10**18)
        self._mock = MagicMock()
        self._mock.get_proposal = AsyncMock(return_value=self.proposal_data)
        self._mock.get_voting_power = AsyncMock(return_value=self.voting_power)

    def __enter__(self):
        import usmsb_sdk.blockchain.contracts.vib_governance as vg_mod
        self._orig = vg_mod.VIBGovernanceClient
        vg_mod.VIBGovernanceClient = lambda *a, **kw: self._mock
        return self._mock

    def __exit__(self, *args):
        import usmsb_sdk.blockchain.contracts.vib_governance as vg_mod
        vg_mod.VIBGovernanceClient = self._orig
