"""
Integration test fixtures — production-matched schema, mocked Web3.
"""
import pytest
import sys
import os
import time
import sqlite3
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


# ---------------------------------------------------------------------------
# Production-matched schema
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Mock Web3 helpers
# ---------------------------------------------------------------------------

VALID_TX = "0x" + "a" * 64


def _mock_cfg():
    cfg = MagicMock()
    cfg.chain_id = 84532
    cfg.network_name = "Base Sepolia"
    cfg.rpc_url = "https://sepolia.base.org"
    return cfg


def _make_w3(status=1, from_addr=None):
    r = MagicMock()
    r.status = status
    r.blockNumber = 1000
    r.confirmations = 1
    r.from_addr = from_addr or "0xVOTERADDR"
    eth = MagicMock()
    eth.get_transaction_receipt.return_value = r
    eth.chain_id = 84532
    w3 = MagicMock()
    w3.eth = eth
    w3.to_checksum_address = lambda x: x
    return w3


# ---------------------------------------------------------------------------
# Mock Web3 context managers
# ---------------------------------------------------------------------------

class _W3Ctx:
    """Context manager for Web3 mock."""
    def __init__(self, mock_w3, original_from_env, patcher):
        self.mock_w3 = mock_w3
        self.original_from_env = original_from_env
        self.patcher = patcher
        import usmsb_sdk.blockchain.config as cfg_mod
        cfg_mod.BlockchainConfig.from_env = classmethod(lambda cls: _mock_cfg())

    def __enter__(self):
        return self.mock_w3

    def __exit__(self, *args):
        self.patcher.stop()
        import usmsb_sdk.blockchain.config as cfg_mod
        if self.original_from_env is not None:
            cfg_mod.BlockchainConfig.from_env = self.original_from_env


def mock_web3(status=1, from_addr=None):
    """Mock Web3 with given tx status. Use as: `with mock_web3():`"""
    import usmsb_sdk.blockchain.config as cfg_mod
    original = getattr(cfg_mod.BlockchainConfig, 'from_env', None)
    mock_w3 = _make_w3(status=status, from_addr=from_addr)
    patcher = patch("web3.Web3", return_value=mock_w3)
    patcher.start()
    return _W3Ctx(mock_w3, original, patcher)


class _NotFoundCtx:
    def __init__(self, original, patcher):
        self.original = original
        self.patcher = patcher
        import usmsb_sdk.blockchain.config as cfg_mod
        cfg_mod.BlockchainConfig.from_env = classmethod(lambda cls: _mock_cfg())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.patcher.stop()
        import usmsb_sdk.blockchain.config as cfg_mod
        if self.original is not None:
            cfg_mod.BlockchainConfig.from_env = self.original


def mock_web3_not_found():
    """Mock Web3 returning None receipt (pending)."""
    import usmsb_sdk.blockchain.config as cfg_mod
    original = getattr(cfg_mod.BlockchainConfig, 'from_env', None)
    mock_w3 = _make_w3()
    mock_w3.eth.get_transaction_receipt.return_value = None
    patcher = patch("web3.Web3", return_value=mock_w3)
    patcher.start()
    return _NotFoundCtx(original, patcher)


class _FailedCtx:
    def __init__(self, original, patcher):
        self.original = original
        self.patcher = patcher
        import usmsb_sdk.blockchain.config as cfg_mod
        cfg_mod.BlockchainConfig.from_env = classmethod(lambda cls: _mock_cfg())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.patcher.stop()
        import usmsb_sdk.blockchain.config as cfg_mod
        if self.original is not None:
            cfg_mod.BlockchainConfig.from_env = self.original


def mock_web3_failed():
    """Mock Web3 returning failed tx (status=0)."""
    import usmsb_sdk.blockchain.config as cfg_mod
    original = getattr(cfg_mod.BlockchainConfig, 'from_env', None)
    r = MagicMock()
    r.status = 0
    r.blockNumber = 1000
    eth = MagicMock()
    eth.get_transaction_receipt.return_value = r
    eth.chain_id = 84532
    mock_w3 = MagicMock()
    mock_w3.eth = eth
    mock_w3.to_checksum_address = lambda x: x
    patcher = patch("web3.Web3", return_value=mock_w3)
    patcher.start()
    return _FailedCtx(original, patcher)


# ---------------------------------------------------------------------------
# Mock user
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def integration_db(tmp_path, monkeypatch):
    """Use production connection/transaction semantics against a fresh file.

    Patch the location, not get_db: routers importing get_db by value must use
    the same database too. A single shared connection races across request and
    worker threads, and hides commit/rollback bugs in the production factory.
    """
    import usmsb_sdk.api.database as db_mod
    import usmsb_sdk.services.schema as service_schema
    from usmsb_sdk.api.cache import cache_manager

    monkeypatch.setattr(db_mod, "DATABASE_PATH", str(tmp_path / "integration.db"))
    monkeypatch.setattr(
        service_schema, "DEFAULT_DB_PATH", f"sqlite:///{tmp_path / 'platform.db'}"
    )
    db_mod.init_db()  # Schema initialization failure must fail the test.
    for prefix in cache_manager.get_stats():
        cache_manager.invalidate_all(prefix)
    conn = sqlite3.connect(db_mod.get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
        for prefix in cache_manager.get_stats():
            cache_manager.invalidate_all(prefix)


@pytest.fixture
def sample_bound_agent(integration_db):
    """Fully bound agent."""
    now = time.time()
    integration_db.execute(
        """INSERT INTO agents
           (agent_id, name, status, owner_wallet, binding_status,
            created_at, updated_at, stake, reputation)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("agent_bound", "BoundAgent", "bound", "0xBOUNDWALLET", "bound",
         now, now, 100.0, 0.8)
    )
    integration_db.execute(
        """INSERT INTO agent_wallets
           (id, agent_id, owner_id, wallet_address, agent_address,
            vibe_balance, staked_amount, stake_status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("w_bound", "agent_bound", "0xBOUNDWALLET", "0xBOUNDWALLET", "0xBOUNDAGENT",
         5000.0, 0.0, "active", now, now)
    )
    integration_db.execute(
        """INSERT INTO agent_api_keys
           (id, agent_id, key_hash, key_prefix, name, level, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("bound_key1", "agent_bound", "hash_test_key", "test_", "Test Key", 1, now)
    )
    integration_db.commit()
    return "agent_bound"


@pytest.fixture
def sample_proposal(integration_db):
    """Governance proposal."""
    now = time.time()
    integration_db.execute(
        """INSERT INTO proposals
           (id, title, proposer_id, status, votes_for, votes_against, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("prop1", "Test Proposal", "0xPROPOSER", "active", 0, 0, now, now)
    )
    integration_db.commit()
    return "prop1"


# ---------------------------------------------------------------------------
# FastAPI TestClient
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def _app():
    """Load app once per test module."""
    import usmsb_sdk.api.database as db_mod
    from usmsb_sdk.api.rest.main import app as main_app
    return main_app, db_mod


@pytest.fixture
def app_with_db(integration_db, _app):
    """All imported connection factories resolve the isolated database path."""
    main_app, _ = _app
    yield main_app


@pytest.fixture
def client(app_with_db):
    """TestClient with auth bypassed."""
    from fastapi.testclient import TestClient
    from usmsb_sdk.api.rest.unified_auth import get_current_user_unified

    from usmsb_sdk.api.rest.auth import get_current_user
    original_overrides = app_with_db.dependency_overrides.copy()
    app_with_db.dependency_overrides[get_current_user_unified] = lambda: MOCK_USER
    app_with_db.dependency_overrides[get_current_user] = lambda: MOCK_USER
    tc = TestClient(app_with_db, raise_server_exceptions=False)
    try:
        yield tc
    finally:
        tc.close()
        app_with_db.dependency_overrides.clear()
        app_with_db.dependency_overrides.update(original_overrides)


@pytest.fixture
def unauthenticated_client(app_with_db):
    """Exercise real authentication, never the authenticated fixture's bypass."""
    from fastapi.testclient import TestClient

    assert not app_with_db.dependency_overrides
    tc = TestClient(app_with_db, raise_server_exceptions=True)
    try:
        yield tc
    finally:
        tc.close()

@pytest.fixture
def sample_pending_binding(integration_db):
    """A pending binding (initiated but not completed)."""
    now = time.time()
    integration_db.execute(
        """INSERT INTO agents
           (agent_id, name, status, owner_wallet, binding_status,
            created_at, updated_at, stake, reputation)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("agent_pending", "PendingAgent", "pending", "0xBOUNDWALLET", "pending",
         now, now, 0.0, 0.0)
    )
    integration_db.commit()
    return "agent_pending"



class _VIBClientCtx:
    """Patch VIBGovernanceClient to return mock data without touching real blockchain."""
    def __init__(self, proposal_data=None, voting_power=None):
        from unittest.mock import MagicMock, AsyncMock
        if proposal_data is None:
            proposal_data = {
                "id": 1, "proposer": "0xVOTERADDR", "proposal_type": MagicMock(),
                "state": MagicMock(), "title": "Test", "description": "Test proposal",
                "target": "0x" + "b"*40, "data": "", "start_time": 0, "end_time": 0,
                "execute_time": 0, "for_votes": 100, "against_votes": 50,
                "abstain_votes": 10, "total_voters": 5, "executed": False,
            }
        self.proposal_data = proposal_data
        self.voting_power = voting_power if voting_power is not None else 1000 * (10**18)
        self._mock = MagicMock()
        self._mock.get_proposal = AsyncMock(return_value=self.proposal_data)
        self._mock.get_voting_power = AsyncMock(return_value=self.voting_power)

    def __enter__(self):
        import usmsb_sdk.blockchain.contracts.vib_governance as vg_mod
        # Patch the class so VIBGovernanceClient() returns our mock
        self._orig = vg_mod.VIBGovernanceClient
        vg_mod.VIBGovernanceClient = lambda *a, **kw: self._mock
        return self._mock

    def __exit__(self, *args):
        import usmsb_sdk.blockchain.contracts.vib_governance as vg_mod
        vg_mod.VIBGovernanceClient = self._orig


def mock_vib_governance_client(proposal_data=None, voting_power=None):
    """Mock VIBGovernanceClient chain calls for governance tests.
    
    Usage:
        with mock_vib_governance_client({"for_votes": 100}):
            response = client.post("/api/governance/vote", ...)
    """
    return _VIBClientCtx(proposal_data, voting_power)
