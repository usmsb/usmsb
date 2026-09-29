"""Wallet read contracts; local records are not proof of real settlement."""

import pytest


@pytest.fixture
def transactions(integration_db):
    for tx_id, buyer, seller, kind, created in [
        ("mine-1", "agent_bound", "seller", "service_payment", 1),
        ("mine-2", "buyer", "agent_bound", "stake_deposit", 2),
        ("private", "other-buyer", "other-seller", "service_payment", 3),
    ]:
        integration_db.execute(
            "INSERT INTO transactions (id,buyer_id,seller_id,transaction_type,amount,status,"
            "created_at) VALUES (?,?,?,?,?,?,?)",
            (tx_id, buyer, seller, kind, 10, "pending", created),
        )
    integration_db.commit()


@pytest.mark.parametrize("path", ["balance", "transactions", "transactions/nonexistent"])
def test_wallet_requires_real_authentication(unauthenticated_client, path):
    assert unauthenticated_client.get(f"/api/wallet/{path}").status_code == 401


def test_unbound_wallet_balance(client):
    response = client.get("/api/wallet/balance")
    assert response.status_code == 200, response.text
    assert response.json()["balance"] == 0
    assert response.json()["agent_id"] == "agent_bound"


def test_bound_balance_uses_authenticated_identity(client, sample_bound_agent):
    response = client.get("/api/wallet/balance?address=someone-else")
    assert response.status_code == 200, response.text
    assert response.json()["balance"] == 5000
    assert response.json()["agent_id"] == sample_bound_agent


def test_transactions_are_isolated_and_ordered(client, transactions):
    response = client.get("/api/wallet/transactions")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_count"] == 2
    assert [tx["id"] for tx in body["transactions"]] == ["mine-2", "mine-1"]
    assert [tx["counterparty_id"] for tx in body["transactions"]] == ["buyer", "seller"]


def test_transactions_filter_and_pagination(client, transactions):
    filtered = client.get("/api/wallet/transactions?type=stake_deposit")
    assert filtered.status_code == 200
    assert filtered.json()["total_count"] == 1
    assert [tx["id"] for tx in filtered.json()["transactions"]] == ["mine-2"]
    page = client.get("/api/wallet/transactions?limit=1&offset=1")
    assert page.status_code == 200
    assert page.json()["total_count"] == 2
    assert page.json()["page"] == 2
    assert [tx["id"] for tx in page.json()["transactions"]] == ["mine-1"]


@pytest.mark.parametrize("tx_id", ["private", "nonexistent"])
def test_transactions_do_not_disclose_others(client, transactions, tx_id):
    response = client.get(f"/api/wallet/transactions/{tx_id}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_transaction_details(client, transactions):
    response = client.get("/api/wallet/transactions/mine-1")
    assert response.status_code == 200
    assert response.json()["counterparty_id"] == "seller"


@pytest.mark.parametrize("query", ["limit=0", "limit=201", "offset=-1"])
def test_wallet_pagination_bounds(client, query):
    assert client.get(f"/api/wallet/transactions?{query}").status_code == 422
