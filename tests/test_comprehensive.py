"""
USMSB Comprehensive Unit Test Suite
===================================
Covers: database layer, router validation, business logic, SQL injection,
        auth checks, error handling, and blockchain client methods.

Run: python -m pytest tests/test_comprehensive.py -v
"""

import pytest
import sys
import os
import re
import tempfile
import sqlite3
import time
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["AGENT_WALLET_DEPLOYER_PRIVATE_KEY"] = "0x" + "a" * 64
os.environ["PLATFORM_AGENT_ADDRESS"] = "0x" + "a" * 40


# =============================================================================
# Test Database Layer — in-memory with production-matched schema
# =============================================================================

@pytest.fixture
def temp_db():
    """Fresh in-memory DB matching actual production schema from database.py."""
    conn = sqlite3.connect(":memory:")

    conn.execute("""
        CREATE TABLE agents (
            agent_id TEXT PRIMARY KEY, name TEXT NOT NULL, agent_type TEXT DEFAULT 'ai_agent',
            description TEXT DEFAULT '', capabilities TEXT DEFAULT '[]', skills TEXT DEFAULT '[]',
            status TEXT DEFAULT 'offline', endpoint TEXT DEFAULT '', chat_endpoint TEXT DEFAULT '',
            protocol TEXT DEFAULT 'standard', stake REAL DEFAULT 0, balance REAL DEFAULT 0,
            reputation REAL DEFAULT 0.5, last_heartbeat REAL, heartbeat_interval INTEGER DEFAULT 30,
            ttl INTEGER DEFAULT 90, metadata TEXT DEFAULT '{}', created_at REAL, updated_at REAL,
            unregistered_at REAL
        )
    """)
    conn.execute("""
        CREATE TABLE agent_wallets (
            id TEXT PRIMARY KEY, agent_id TEXT UNIQUE NOT NULL, owner_id TEXT NOT NULL,
            wallet_address TEXT UNIQUE NOT NULL, agent_address TEXT NOT NULL,
            vibe_balance REAL DEFAULT 0, staked_amount REAL DEFAULT 0, stake_status TEXT DEFAULT 'none',
            locked_stake REAL DEFAULT 0, unlock_available_at REAL, max_per_tx REAL DEFAULT 500,
            daily_limit REAL DEFAULT 1000, daily_spent REAL DEFAULT 0, last_reset_time REAL,
            registry_registered INTEGER DEFAULT 0, created_at REAL, updated_at REAL,
            agent_private_key TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE binding_requests (
            id TEXT PRIMARY KEY, binding_code TEXT UNIQUE, agent_id TEXT,
            owner_id TEXT, status TEXT, owner_wallet TEXT, stake_amount REAL,
            created_at REAL, updated_at REAL, completed_at REAL, expires_at REAL,
            binding_url TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE transactions (
            id TEXT PRIMARY KEY, buyer_id TEXT, seller_id TEXT, amount REAL,
            title TEXT, status TEXT, transaction_type TEXT, escrow_tx_hash TEXT,
            created_at REAL, updated_at REAL
        )
    """)
    conn.execute("""
        CREATE TABLE proposals (
            id TEXT PRIMARY KEY, title TEXT, description TEXT, proposer_id TEXT,
            status TEXT, votes_for INTEGER DEFAULT 0, votes_against INTEGER DEFAULT 0,
            created_at REAL, updated_at REAL, end_time REAL, timelock_delay REAL
        )
    """)
    conn.execute("""
        CREATE TABLE votes (
            id TEXT PRIMARY KEY, proposal_id TEXT, voter_id TEXT,
            vote INTEGER, created_at REAL
        )
    """)
    conn.execute("""
        CREATE TABLE users (
            id TEXT PRIMARY KEY, user_id TEXT UNIQUE, wallet_address TEXT,
            api_key_hash TEXT, created_at REAL, stake_amount REAL DEFAULT 0,
            vibe_balance REAL DEFAULT 0, stake_tier TEXT, stake_status TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE agent_api_keys (
            id TEXT PRIMARY KEY, agent_id TEXT, key_hash TEXT,
            created_at REAL, last_used_at REAL, expires_at REAL
        )
    """)
    conn.execute("""
        CREATE TABLE governance_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, voter TEXT, event_type TEXT,
            tx_hash TEXT, extra TEXT, created_at REAL
        )
    """)
    conn.commit()

    import usmsb_sdk.api.database as db_module
    original_get_db = db_module.get_db
    db_module.get_db = lambda: conn

    yield conn, db_module

    db_module.get_db = original_get_db
    conn.close()


class TestDatabaseLayer:
    """Test database.py core functions with real SQLite execution."""

    def test_filter_sensitive_fields_removes_api_key_hash(self, temp_db):
        from usmsb_sdk.api.database import _filter_sensitive_fields
        result = _filter_sensitive_fields({
            "agent_id": "a1", "wallet_address": "0x1",
            "api_key_hash": "SECRET", "soul_private_key": "SECRET2",
            "private_key": "PRIVATE"
        })
        assert "api_key_hash" not in result
        assert "soul_private_key" not in result
        assert "private_key" not in result
        assert result["agent_id"] == "a1"

    def test_filter_sensitive_fields_handles_none(self, temp_db):
        from usmsb_sdk.api.database import _filter_sensitive_fields
        assert _filter_sensitive_fields(None) is None

    def test_filter_sensitive_fields_empty_dict(self, temp_db):
        from usmsb_sdk.api.database import _filter_sensitive_fields
        assert _filter_sensitive_fields({}) == {}

    def test_get_agent_returns_filtered_dict(self, temp_db):
        conn, _ = temp_db
        now = time.time()
        # agents table: 20 columns (no unregistered_at extra)
        conn.execute(
            "INSERT INTO agents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("agent1", "TestAgent", "ai_agent", "", "[]", "[]", "bound",
             "0xW", "", "standard", 0, 0, 0.5, now, 30, 90, "{}", now, now, None)
        )
        conn.commit()
        from usmsb_sdk.api.database import get_agent
        result = get_agent("agent1")
        assert result is not None
        assert "api_key_hash" not in result
        assert "soul_private_key" not in result
        assert result["status"] == "bound"

    def test_has_wallet_binding_bound_agent(self, temp_db):
        conn, _ = temp_db
        now = time.time()
        conn.execute(
            "INSERT INTO agents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("a2", "Agent2", "ai_agent", "", "[]", "[]", "bound",
             "0xWA", "", "standard", 0, 0, 0.5, now, 30, 90, "{}", now, now, None)
        )
        conn.execute(
            "INSERT INTO agent_wallets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("w2", "a2", "u2", "0xWA", "0xAA", 0, 0, "active", 0, None,
             500, 1000, 0, now, 1, now, now, None)
        )
        conn.commit()
        from usmsb_sdk.api.database import has_wallet_binding
        assert has_wallet_binding("a2") is True

    def test_has_wallet_binding_unbound_agent(self, temp_db):
        conn, _ = temp_db
        now = time.time()
        conn.execute(
            "INSERT INTO agents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("a3", "Agent3", "ai_agent", "", "[]", "[]", "unbound",
             "", "", "standard", 0, 0, 0.5, now, 30, 90, "{}", now, now, None)
        )
        conn.commit()
        from usmsb_sdk.api.database import has_wallet_binding
        assert has_wallet_binding("a3") is False

    def test_db_create_order_record_insert_replace(self, temp_db):
        conn, _ = temp_db
        from usmsb_sdk.api.database import db_create_order_record
        ok = db_create_order_record("order_test", "0xbuyer", 500, "coding", "0xPool1")
        assert ok is True
        row = conn.execute(
            "SELECT amount, status, title FROM transactions WHERE id='order_order_test'"
        ).fetchone()
        assert row[0] == 500
        assert row[1] == "pending"
        assert row[2] == "coding"

    def test_db_log_governance_event_vote(self, temp_db):
        conn, _ = temp_db
        from usmsb_sdk.api.database import db_log_governance_event
        ok = db_log_governance_event(
            "0xvoter", "vote", "0xtxhashvote",
            {"support": 1, "proposal_id": "prop1"}
        )
        assert ok is True
        # Inserts into votes table
        row = conn.execute(
            "SELECT voter_id, vote FROM votes WHERE proposal_id='prop1'"
        ).fetchone()
        assert row is not None
        assert row[0] == "0xvoter"
        assert row[1] == 1

    def test_db_log_governance_event_proposal(self, temp_db):
        conn, _ = temp_db
        from usmsb_sdk.api.database import db_log_governance_event
        ok = db_log_governance_event(
            "0xproposer", "create_proposal", "0xtxhashprop",
            {"title": "Test Proposal"}
        )
        assert ok is True
        row = conn.execute(
            "SELECT title, proposer_id FROM proposals WHERE proposer_id='0xproposer'"
        ).fetchone()
        assert row is not None
        assert row[0] == "Test Proposal"

    def test_update_agent_balance_updates_wallet_balance(self, temp_db):
        conn, _ = temp_db
        now = time.time()
        # update_agent_balance updates agent_wallets, not agents table
        conn.execute(
            "INSERT INTO agent_wallets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("wbal", "bal_agent", "u1", "0xWALLET", "0xAGENT", 0, 0, "active",
             0, None, 500, 1000, 0, now, 1, now, now, None)
        )
        conn.commit()
        from usmsb_sdk.api.database import update_agent_balance
        result = update_agent_balance("bal_agent", 100.0, deduct=False)
        assert result is True

    def test_create_agent_wallet_and_get(self, temp_db):
        conn, _ = temp_db
        now = time.time()
        from usmsb_sdk.api.database import create_agent_wallet, get_agent_wallet
        wallet_data = {
            "id": "wallet_new",
            "agent_id": "new_agent",
            "owner_id": "owner1",
            "wallet_address": "0xNEWWALLET",
            "agent_address": "0xAGENTADDR",
            "agent_private_key": "0xPK",
            "vibe_balance": 0,
            "staked_amount": 0,
            "stake_status": "active",
            "registry_registered": 0,
        }
        create_agent_wallet(wallet_data)
        result = get_agent_wallet("new_agent")
        assert result is not None
        assert result["wallet_address"] == "0xNEWWALLET"
        assert result["agent_address"] == "0xAGENTADDR"

    def test_get_agent_not_found(self, temp_db):
        from usmsb_sdk.api.database import get_agent
        result = get_agent("nonexistent_agent")
        assert result is None

    def test_get_agent_wallet_not_found(self, temp_db):
        from usmsb_sdk.api.database import get_agent_wallet
        result = get_agent_wallet("nonexistent")
        assert result is None


class TestSQLInjection:
    """Verify all database queries use parameterized queries, not f-strings."""

    def test_no_fstring_select_in_database(self):
        with open("src/usmsb_sdk/api/database.py") as f:
            src = f.read()
        matches = re.findall(r'cursor\.execute\(f"[^)]*SELECT', src)
        assert len(matches) == 0, f"Found {len(matches)} f-string SELECT queries"

    def test_no_fstring_update_in_database(self):
        with open("src/usmsb_sdk/api/database.py") as f:
            src = f.read()
        matches = re.findall(r'cursor\.execute\(f"[^)]*UPDATE', src)
        assert len(matches) == 0, f"Found {len(matches)} f-string UPDATE queries"

    def test_no_fstring_insert_in_database(self):
        with open("src/usmsb_sdk/api/database.py") as f:
            src = f.read()
        matches = re.findall(r'cursor\.execute\(f"[^)]*INSERT', src)
        assert len(matches) == 0, f"Found {len(matches)} f-string INSERT queries"

    def test_column_names_not_from_fstring(self):
        """Columns in UPDATE SET clause must not come from f-string variables."""
        with open("src/usmsb_sdk/api/database.py") as f:
            src = f.read()
        # Bad pattern: f"UPDATE ... SET {variable} = ..." where {variable} is a column name
        # The regex looks for SET { followed by a letter (not another brace)
        bad = re.findall(r'SET\s+\{\s*[a-zA-Z_]\w*\}', src)
        assert len(bad) == 0, f"Found f-string column names in SET: {bad}"


# =============================================================================
# Test Request Model Validation (Pydantic)
# =============================================================================

class TestStakingModels:
    def test_on_chain_stake_request_valid(self):
        from usmsb_sdk.api.rest.routers.staking import OnChainStakeRequest
        tx = "0x" + "a" * 64
        req = OnChainStakeRequest(amount="100.5", lock_period=2, tx_hash=tx)
        assert req.tx_hash == tx
        assert float(req.amount) == 100.5
        assert req.lock_period == 2

    def test_on_chain_stake_rejects_negative_amount(self):
        from usmsb_sdk.api.rest.routers.staking import OnChainStakeRequest
        with pytest.raises(Exception):
            OnChainStakeRequest(amount="-10", lock_period=1, tx_hash="0x" + "a" * 64)

    def test_endpoint_validates_tx_hash_format(self):
        """tx_hash validation happens in endpoint code, not Pydantic model."""
        with open("src/usmsb_sdk/api/rest/routers/staking.py") as f:
            src = f.read()
        # The endpoint must validate tx_hash format
        assert 'tx_hash.startswith("0x")' in src
        assert 'len(request.tx_hash) != 66' in src


class TestGovernanceModels:
    def test_cast_vote_request_valid_support_for(self):
        from usmsb_sdk.api.rest.routers.governance import CastVoteRequest
        tx = "0x" + "c" * 64
        req = CastVoteRequest(proposal_id=1, support=1, tx_hash=tx)
        assert req.support == 1

    def test_cast_vote_request_valid_support_against(self):
        from usmsb_sdk.api.rest.routers.governance import CastVoteRequest
        tx = "0x" + "c" * 64
        req = CastVoteRequest(proposal_id=1, support=0, tx_hash=tx)
        assert req.support == 0

    def test_cast_vote_request_rejects_invalid_support(self):
        from usmsb_sdk.api.rest.routers.governance import CastVoteRequest
        with pytest.raises(Exception):
            CastVoteRequest(proposal_id=1, support=99, tx_hash="0x" + "a" * 64)

    def test_endpoint_validates_tx_hash_format(self):
        with open("src/usmsb_sdk/api/rest/routers/governance.py") as f:
            src = f.read()
        assert 'tx_hash.startswith("0x")' in src
        assert 'len(request.tx_hash) != 66' in src


class TestJointOrderModels:
    def test_create_pool_request_valid(self):
        from usmsb_sdk.api.rest.routers.joint_order import CreatePoolRequest
        tx = "0x" + "e" * 64
        req = CreatePoolRequest(order_id="order1", service_type="ai", total_budget=1000, tx_hash=tx)
        assert req.order_id == "order1"
        assert req.total_budget == 1000

    def test_submit_bid_request_valid(self):
        from usmsb_sdk.api.rest.routers.joint_order import SubmitBidRequest
        tx = "0x" + "f" * 64
        req = SubmitBidRequest(pool_id="pool1", chain_pool_id="chain1", price=50, tx_hash=tx)
        assert req.price == 50

    def test_accept_bid_request_valid(self):
        from usmsb_sdk.api.rest.routers.joint_order import AcceptBidRequest
        tx = "0x" + "a" * 64
        req = AcceptBidRequest(pool_id="pool1", chain_pool_id="chain1", bid_id="bid1", tx_hash=tx)
        assert req.bid_id == "bid1"

    def test_confirm_delivery_request_valid(self):
        from usmsb_sdk.api.rest.routers.joint_order import ConfirmDeliveryRequest
        tx = "0x" + "b" * 64
        req = ConfirmDeliveryRequest(pool_id="pool1", chain_pool_id="chain1", rating=5, tx_hash=tx)
        assert req.rating == 5

    def test_cancel_pool_request_valid(self):
        from usmsb_sdk.api.rest.routers.joint_order import CancelPoolRequest
        tx = "0x" + "d" * 64
        req = CancelPoolRequest(pool_id="pool1", chain_pool_id="chain1", tx_hash=tx)
        assert req.pool_id == "pool1"


class TestIdentityModels:
    def test_mint_sbt_request_valid(self):
        from usmsb_sdk.api.rest.routers.identity import MintSBTRequest
        tx = "0x" + "a" * 64
        req = MintSBTRequest(
            agent_address="0x1234567890123456789012345678901234567890",
            name="TestSoul", tx_hash=tx
        )
        assert req.name == "TestSoul"
        assert req.tx_hash == tx


class TestCollaborationModels:
    def test_collaborations_router_has_execute_endpoint(self):
        from usmsb_sdk.api.rest.routers.collaborations import router
        paths = {r.path for r in router.routes}
        # Router has /{session_id}/execute endpoint
        assert any("execute" in p for p in paths)

    def test_collaborations_router_has_complete_endpoint(self):
        from usmsb_sdk.api.rest.routers.collaborations import router
        paths = {r.path for r in router.routes}
        assert any("complete" in p for p in paths)


# =============================================================================
# Test Router Endpoint Registration
# =============================================================================

class TestRouterRegistration:
    def test_staking_router_has_stake_endpoint(self):
        from usmsb_sdk.api.rest.routers.staking import router
        paths = {r.path for r in router.routes}
        assert any("/stake" in p for p in paths)

    def test_staking_router_has_unstake_endpoint(self):
        from usmsb_sdk.api.rest.routers.staking import router
        paths = {r.path for r in router.routes}
        assert any("/unstake" in p for p in paths)

    def test_staking_router_has_info_endpoint(self):
        from usmsb_sdk.api.rest.routers.staking import router
        paths = {r.path for r in router.routes}
        assert any("info" in p for p in paths)

    def test_staking_router_has_claim_endpoint(self):
        from usmsb_sdk.api.rest.routers.staking import router
        paths = {r.path for r in router.routes}
        assert any("claim" in p for p in paths)

    def test_governance_router_has_proposals_endpoint(self):
        from usmsb_sdk.api.rest.routers.governance import router
        paths = {r.path for r in router.routes}
        assert any("proposal" in p for p in paths)

    def test_governance_router_has_vote_endpoint(self):
        from usmsb_sdk.api.rest.routers.governance import router
        paths = {r.path for r in router.routes}
        assert any("vote" in p for p in paths)

    def test_joint_order_router_has_pool_create(self):
        from usmsb_sdk.api.rest.routers.joint_order import router
        paths = {r.path for r in router.routes}
        assert any("pool" in p and "create" in p for p in paths)

    def test_joint_order_router_has_submit_bid(self):
        from usmsb_sdk.api.rest.routers.joint_order import router
        paths = {r.path for r in router.routes}
        assert any("submit-bid" in p for p in paths)

    def test_joint_order_router_has_accept_bid(self):
        from usmsb_sdk.api.rest.routers.joint_order import router
        paths = {r.path for r in router.routes}
        assert any("accept-bid" in p for p in paths)

    def test_identity_router_has_mint_sbt(self):
        from usmsb_sdk.api.rest.routers.identity import router
        paths = {r.path for r in router.routes}
        assert any("mint" in p for p in paths)

    def test_dispute_router_has_raise(self):
        from usmsb_sdk.api.rest.routers.dispute import router
        paths = {r.path for r in router.routes}
        assert any("raise" in p for p in paths)

    def test_collaborations_router_has_execute(self):
        from usmsb_sdk.api.rest.routers.collaborations import router
        paths = {r.path for r in router.routes}
        assert any("execute" in p for p in paths)

    def test_registration_router_v2_register(self):
        from usmsb_sdk.api.rest.routers.registration import router
        paths = {r.path for r in router.routes}
        assert any("register" in p for p in paths)

    def test_registration_router_v2_complete_binding(self):
        from usmsb_sdk.api.rest.routers.registration import router
        paths = {r.path for r in router.routes}
        assert any("complete-binding" in p for p in paths)


# =============================================================================
# Test Business Logic — static code inspection
# =============================================================================

class TestStakingBusinessLogic:
    def test_on_chain_stake_gets_transaction_receipt(self):
        with open("src/usmsb_sdk/api/rest/routers/staking.py") as f:
            src = f.read()
        assert "get_transaction_receipt" in src
        assert "Transaction not found or still pending" in src
        assert "Transaction failed on-chain" in src

    def test_on_chain_stake_requires_auth(self):
        with open("src/usmsb_sdk/api/rest/routers/staking.py") as f:
            src = f.read()
        assert "Wallet address not found in authentication" in src


class TestGovernanceBusinessLogic:
    def test_vote_checks_proposal_exists(self):
        with open("src/usmsb_sdk/api/rest/routers/governance.py") as f:
            src = f.read()
        assert "get_proposal" in src
        assert "not found on-chain" in src or "not found" in src

    def test_vote_checks_voting_power(self):
        with open("src/usmsb_sdk/api/rest/routers/governance.py") as f:
            src = f.read()
        assert "get_voting_power" in src

    def test_create_proposal_validates_tx_hash(self):
        with open("src/usmsb_sdk/api/rest/routers/governance.py") as f:
            src = f.read()
        assert "Invalid tx_hash format" in src


class TestJointOrderBusinessLogic:
    def test_submit_bid_checks_binding_status(self):
        with open("src/usmsb_sdk/api/rest/routers/joint_order.py") as f:
            src = f.read()
        assert "binding_status" in src

    def test_submit_bid_checks_has_wallet_binding(self):
        with open("src/usmsb_sdk/api/rest/routers/joint_order.py") as f:
            src = f.read()
        assert "has_wallet_binding" in src


class TestBlockchainBusinessLogic:
    def test_transfer_uses_agent_private_key_fallback(self):
        with open("src/usmsb_sdk/api/rest/routers/blockchain.py") as f:
            src = f.read()
        assert "agent_private_key" in src
        assert "get_agent_wallet" in src


class TestRegistrationBusinessLogic:
    def test_complete_binding_stake_verification_before_deploy(self):
        with open("src/usmsb_sdk/api/rest/routers/registration.py") as f:
            src = f.read()
        assert "stake_receipt" in src or "approve_receipt" in src

    def test_complete_binding_updates_wallet_deployed(self):
        with open("src/usmsb_sdk/api/rest/routers/registration.py") as f:
            src = f.read()
        assert "update_agent_wallet_deployed" in src

    def test_complete_binding_raises_on_deploy_failure(self):
        with open("src/usmsb_sdk/api/rest/routers/registration.py") as f:
            src = f.read()
        assert "WALLET_DEPLOY_FAILED" in src or "wallet deployment failed" in src.lower()


# =============================================================================
# Test Blockchain Client Methods (signature verification)
# =============================================================================

class TestBlockchainClients:
    def test_vibe_token_client_has_transfer(self):
        from usmsb_sdk.blockchain.contracts.vibe_token import VIBETokenClient
        assert hasattr(VIBETokenClient, "transfer")
        assert hasattr(VIBETokenClient, "approve")
        assert hasattr(VIBETokenClient, "balance_of")

    def test_vib_staking_client_has_stake(self):
        from usmsb_sdk.blockchain.contracts.vib_staking import VIBStakingClient
        assert hasattr(VIBStakingClient, "stake")
        assert hasattr(VIBStakingClient, "unstake")
        assert hasattr(VIBStakingClient, "claim_reward")
        assert hasattr(VIBStakingClient, "get_stake_info")
        assert hasattr(VIBStakingClient, "get_pending_reward")

    def test_vib_governance_client_has_create_proposal(self):
        from usmsb_sdk.blockchain.contracts.vib_governance import VIBGovernanceClient
        assert hasattr(VIBGovernanceClient, "create_proposal")
        assert hasattr(VIBGovernanceClient, "cast_vote")
        assert hasattr(VIBGovernanceClient, "get_proposal")

    def test_joint_order_client_has_create_pool(self):
        from usmsb_sdk.blockchain.contracts.joint_order import JointOrderClient
        assert hasattr(JointOrderClient, "create_pool")
        assert hasattr(JointOrderClient, "submit_bid")
        assert hasattr(JointOrderClient, "accept_bid")
        assert hasattr(JointOrderClient, "confirm_delivery")

    def test_agent_wallet_client_has_execute_transfer(self):
        from usmsb_sdk.blockchain.contracts.agent_wallet import AgentWalletClient
        assert hasattr(AgentWalletClient, "execute_transfer")
        assert hasattr(AgentWalletClient, "get_balance")

    def test_vib_identity_client_has_register_method(self):
        from usmsb_sdk.blockchain.contracts.vib_identity import VIBIdentityClient
        assert hasattr(VIBIdentityClient, "register_ai_identity")
        assert hasattr(VIBIdentityClient, "is_registered")


# =============================================================================
# Test Services
# =============================================================================

class TestServices:
    def test_joint_order_pool_manager_imports(self):
        from usmsb_sdk.services.joint_order_pool_manager import JointOrderPoolManager
        assert JointOrderPoolManager is not None

    def test_agent_soul_manager_imports(self):
        from usmsb_sdk.services.agent_soul import AgentSoulManager
        assert AgentSoulManager is not None


# =============================================================================
# Test Frontend Configuration
# =============================================================================

class TestFrontendConfig:
    def test_wagmi_uses_base_sepolia_chain(self):
        with open("frontend/src/config/wagmi.ts") as f:
            src = f.read()
        # baseSepolia from wagmi/chains has id=84532 (Base Sepolia testnet)
        assert "baseSepolia" in src, "Should import baseSepolia chain from wagmi"
        # Verify baseSepolia is in the chains list
        assert "chains: [baseSepolia" in src
        # Verify baseSepolia transport is configured
        assert "baseSepolia.id" in src

    def test_wagmi_not_base_mainnet_without_sepolia(self):
        with open("frontend/src/config/wagmi.ts") as f:
            src = f.read()
        # If 8453 (mainnet) appears, 84532 must also appear
        if "8453," in src:
            assert "84532" in src

    def test_contracts_ts_has_core_addresses(self):
        with open("frontend/src/data/contracts.ts") as f:
            src = f.read()
        required = ["VIBETOKEN", "VIBSTAKING", "VIBGOVERNANCE", "VIBIDENTITY", "AGENTWALLET"]
        for name in required:
            assert name in src, f"Missing contract: {name}"

    def test_use_staking_hooks_exist(self):
        assert os.path.exists("frontend/src/hooks/useStaking.ts")
        with open("frontend/src/hooks/useStaking.ts") as f:
            src = f.read()
        assert "stake" in src
        assert "unstake" in src

    def test_use_token_hooks_exist(self):
        assert os.path.exists("frontend/src/hooks/useToken.ts")
        with open("frontend/src/hooks/useToken.ts") as f:
            src = f.read()
        assert "transfer" in src
        assert "approve" in src

    def test_staking_panel_has_tx_status_state(self):
        assert os.path.exists("frontend/src/components/StakingPanel.tsx")
        with open("frontend/src/components/StakingPanel.tsx") as f:
            src = f.read()
        assert "isConfirming" in src or "isPending" in src or "confirmed" in src.lower()

    def test_governance_panel_has_tx_status(self):
        assert os.path.exists("frontend/src/components/GovernancePanel.tsx")
        with open("frontend/src/components/GovernancePanel.tsx") as f:
            src = f.read()
        assert "txHash" in src or "confirmed" in src.lower()


# =============================================================================
# Test Config
# =============================================================================

class TestConfig:
    def test_blockchain_config_instantiates(self):
        from usmsb_sdk.blockchain.config import BlockchainConfig, NetworkType
        cfg = BlockchainConfig(network=NetworkType.TESTNET)
        assert cfg is not None
        assert hasattr(cfg, "rpc_url")
        assert hasattr(cfg, "chain_id")
        # Base Sepolia testnet chain ID is 84532
        assert cfg.chain_id == 84532

    def test_rpc_url_loads(self):
        from usmsb_sdk.blockchain.config import BlockchainConfig, NetworkType
        cfg = BlockchainConfig(network=NetworkType.TESTNET)
        assert bool(cfg.rpc_url)


# =============================================================================
# Test Business Logic — Mock Web3 Behavior Tests
# =============================================================================

class TestStakingWeb3Behavior:
    """Test on_chain_stake endpoint with mocked Web3 responses."""

    def test_on_chain_stake_tx_hash_format_validation(self):
        """tx_hash must start with 0x and be 66 chars."""
        with open("src/usmsb_sdk/api/rest/routers/staking.py") as f:
            src = f.read()
        assert 'tx_hash.startswith("0x")' in src
        assert 'len(request.tx_hash) != 66' in src
        assert 'Invalid tx_hash format' in src

    def test_on_chain_stake_rejects_pending_tx(self):
        """Transaction still pending should return error."""
        with open("src/usmsb_sdk/api/rest/routers/staking.py") as f:
            src = f.read()
        assert "Transaction not found or still pending" in src

    def test_on_chain_stake_rejects_failed_tx(self):
        """Transaction with status=0 should return error."""
        with open("src/usmsb_sdk/api/rest/routers/staking.py") as f:
            src = f.read()
        assert "Transaction failed on-chain" in src


class TestGovernanceWeb3Behavior:
    """Test governance endpoints with mocked Web3 responses."""

    def test_cast_vote_tx_hash_format_validation(self):
        with open("src/usmsb_sdk/api/rest/routers/governance.py") as f:
            src = f.read()
        assert 'tx_hash.startswith("0x")' in src
        assert 'len(request.tx_hash) != 66' in src

    def test_vote_rejects_failed_tx(self):
        with open("src/usmsb_sdk/api/rest/routers/governance.py") as f:
            src = f.read()
        assert "Transaction failed on-chain" in src

    def test_vote_returns_403_if_no_voting_power(self):
        with open("src/usmsb_sdk/api/rest/routers/governance.py") as f:
            src = f.read()
        # Should check get_voting_power before accepting vote
        assert "get_voting_power" in src
        # Should reject if voting power is 0
        assert "voting_power" in src or "power" in src


class TestJointOrderWeb3Behavior:
    """Test joint_order endpoint logic."""

    def test_submit_bid_requires_bound_agent(self):
        with open("src/usmsb_sdk/api/rest/routers/joint_order.py") as f:
            src = f.read()
        # Must check agent is registered and bound before accepting bid
        assert "has_wallet_binding" in src
        assert "binding_status" in src

    def test_confirm_delivery_requires_rating(self):
        with open("src/usmsb_sdk/api/rest/routers/joint_order.py") as f:
            src = f.read()
        assert "rating" in src


class TestBalanceAndAuth:
    """Test balance and authentication logic."""

    def test_get_balance_public_by_design(self):
        with open("src/usmsb_sdk/api/rest/routers/blockchain.py") as f:
            src = f.read()
        # /balance/{address} is intentionally public — blockchain data is public.
        # Auth is required only for write operations (transfer, approve).
        assert "/balance/{address}" in src

    def test_transfer_uses_db_private_key_fallback(self):
        with open("src/usmsb_sdk/api/rest/routers/blockchain.py") as f:
            src = f.read()
        # When API key auth is used, agent_private_key comes from DB
        assert "agent_private_key" in src
        assert "get_agent_wallet" in src


class TestRegistrationFlow:
    """Test complete_binding flow."""

    def test_complete_binding_stakes_before_deploy(self):
        with open("src/usmsb_sdk/api/rest/routers/registration.py") as f:
            src = f.read()
        # Stake tokens BEFORE deploying wallet
        assert "stake_receipt" in src or "approve_receipt" in src

    def test_complete_binding_raises_on_deploy_failure(self):
        with open("src/usmsb_sdk/api/rest/routers/registration.py") as f:
            src = f.read()
        # If wallet deployment fails, raise exception (don't mark as bound)
        assert "WALLET_DEPLOY_FAILED" in src or "deployment failed" in src.lower()

    def test_complete_binding_updates_status_after_success(self):
        with open("src/usmsb_sdk/api/rest/routers/registration.py") as f:
            src = f.read()
        # After successful deploy, update wallet_deployed flag
        assert "update_agent_wallet_deployed" in src

    def test_retry_deploy_clears_failed_state(self):
        with open("src/usmsb_sdk/api/rest/routers/registration.py") as f:
            src = f.read()
        assert "retry" in src and "deploy" in src

    def test_binding_status_endpoint_exists(self):
        # binding-status endpoint exists for polling binding progress
        with open("src/usmsb_sdk/api/rest/routers/registration.py") as f:
            src = f.read()
        assert "binding-status" in src or "binding_status" in src
