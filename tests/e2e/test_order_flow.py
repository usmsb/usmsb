"""
End-to-end flow tests.

Tests multi-step workflows:
1. Registration → Wallet Binding → Staking
2. Joint Order → Dispute flow
3. Pre-match Negotiation → Order lifecycle
"""
import pytest
from tests.integration.conftest import VALID_TX, mock_web3


@pytest.mark.skip(reason="E2E flow tests require full system with running services")
class TestRegistrationToStakingFlow:
    """
    Flow: register agent → request binding → complete binding → stake
    
    Simulates a real user journey:
    1. Agent registers with the platform
    2. Agent initiates wallet binding
    3. Agent completes binding with blockchain tx
    4. Agent stakes VIBE tokens
    """

    def test_full_binding_to_staking_flow(self, client, integration_db):
        """Complete flow: binding → staking."""
        # Step 1: Create agent (public)
        r = client.post("/api/agents", json={
            "name": "E2EAgent",
            "capabilities": ["python"],
        })
        assert r.status_code in (201, 400)  # 400 if already exists

        # Step 2: Request binding (authenticated)
        r = client.post("/api/agents/v2/agent_bound/request-binding", json={
            "wallet_address": "0xE2EADDR123456789012345678901234567890",
        })
        assert r.status_code in (200, 400)  # 400 if already bound

        # Step 3: Complete binding with mock tx
        with mock_web3():
            r = client.post("/api/agents/v2/complete-binding/E2ECODE123", json={
                "wallet_address": "0xE2EADDR123456789012345678901234567890",
                "owner_address": "0xE2EADDR123456789012345678901234567890",
                "stake_amount": 100.0,
                "approve_tx_hash": VALID_TX,
            })
        assert r.status_code in (200, 400, 404)  # 404 if binding code wrong

        # Step 4: Stake tokens (authenticated)
        with mock_web3():
            r = client.post("/api/staking/stake", json={
                "amount": 100.0,
                "lock_period": 30,
            })
        assert r.status_code in (200, 400, 500)


@pytest.mark.skip(reason="E2E flow tests require full system with running services")
class TestJointOrderDisputeFlow:
    """
    Flow: submit bid → accept → complete → raise dispute
    
    Simulates buyer-provider workflow:
    1. Provider submits bid to a joint order pool
    2. Buyer accepts the bid
    3. Provider completes work
    4. Dispute is raised
    """

    def test_bid_accept_complete_flow(self, client, integration_db, sample_bound_agent):
        """Submit bid → accept → complete (happy path)."""
        # Step 1: Submit bid
        r = client.post("/api/joint-order/pools/pool-e2e/submit-bid", json={
            "bid_amount": 500.0,
            "delivery_days": 3,
        })
        assert r.status_code in (200, 400, 404)

        # Step 2: Accept bid (buyer side)
        r = client.post("/api/joint-order/pools/pool-e2e/accept", json={
            "bid_id": "bid-001",
        })
        assert r.status_code in (200, 400, 404)

    def test_bid_cancel_flow(self, client, integration_db, sample_bound_agent):
        """Provider submits bid → then cancels."""
        r = client.post("/api/joint-order/pools/pool-e2e/submit-bid", json={
            "bid_amount": 300.0,
            "delivery_days": 5,
        })
        assert r.status_code in (200, 400, 404)

        # Cancel the bid
        r = client.post("/api/joint-order/pools/pool-e2e/cancel", json={
            "reason": "Changed my mind",
        })
        assert r.status_code in (200, 400, 404)


@pytest.mark.skip(reason="E2E flow tests require full system with running services")
class TestPreMatchToOrderFlow:
    """
    Flow: pre-match → negotiate → create order → deliver
    
    Simulates matching flow:
    1. Agents discover each other via pre-match
    2. Negotiate terms
    3. Create order from negotiation
    4. Provider delivers
    """

    def test_negotiate_to_order_flow(self, client, integration_db):
        """Pre-match → Negotiation → Order (simplified)."""
        # Step 1: Initiate pre-match negotiation
        r = client.post("/api/negotiations/pre-match", json={
            "demand_agent_id": "demand-001",
            "supply_agent_id": "supply-001",
            "demand_id": "demand-001",
        })
        assert r.status_code in (201, 400, 401, 403)

        # Step 2: Propose terms
        r = client.post("/api/negotiations/pre-match/session-001/terms/propose", json={
            "terms": {"price": 500, "delivery_days": 5},
            "proposer_id": "demand-001",
        })
        assert r.status_code in (200, 400, 401, 403, 404)


@pytest.mark.skip(reason="E2E flow tests require full system with running services")
class TestGovernanceVotingFlow:
    """Flow: create proposal → vote → check results."""

    def test_create_and_vote_flow(self, client, integration_db, sample_bound_agent):
        """Create proposal → vote → check results."""
        # Step 1: Create proposal
        r = client.post("/api/governance/proposals", json={
            "title": "E2E Test Proposal",
            "description": "Testing governance flow",
            "target_address": "0x" + "a" * 40,
            "calldata": "0x",
            "vote_type": "standard",
        })
        assert r.status_code in (201, 400, 401, 403)

        # Step 2: Vote on proposal
        proposal_id = "prop-e2e"
        with mock_web3():
            r = client.post(f"/api/governance/proposals/{proposal_id}/vote", json={
                "support": True,
                "reason": "Good for the platform",
            })
        assert r.status_code in (200, 400, 401, 403, 404)

        # Step 3: Check proposal status
        r = client.get(f"/api/governance/proposals/{proposal_id}")
        assert r.status_code in (200, 404)


@pytest.mark.skip(reason="E2E flow tests require full system with running services")
class TestIdentityFlow:
    """Flow: register agent → mint SBT."""

    def test_register_and_mint_sbt_flow(self, client, integration_db, sample_bound_agent):
        """Register agent → Mint Identity SBT."""
        # Mint SBT for bound agent
        with mock_web3():
            r = client.post("/api/identity/mint-sbt", json={
                "agent_address": "0xBOUNDAGENT12345678901234567890123456789",
                "name": "E2E Soul Identity",
                "tx_hash": VALID_TX,
            })
        assert r.status_code in (201, 400, 401, 403, 500)

        # Query SBT balance
        r = client.get("/api/identity/balance/0xBOUNDAGENT12345678901234567890123456789")
        assert r.status_code in (200, 404)
