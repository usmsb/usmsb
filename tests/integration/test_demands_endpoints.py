"""Demand contracts: real authentication, ownership, persistence and cache."""

import pytest


def demand(**changes):
    # Legacy input must never select the authenticated owner.
    return {
        "agent_id": "forged-owner",
        "title": "Review research",
        "category": "research",
        "description": "Independent review",
        "budget_min": 10,
        "budget_max": 20,
        **changes,
    }


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("post", "/api/demands", demand()),
        ("delete", "/api/demands/nonexistent", None),
    ],
)
def test_writes_require_real_authentication(unauthenticated_client, method, path, body):
    kwargs = {"json": body} if body is not None else {}
    response = unauthenticated_client.request(method, path, **kwargs)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_list_is_public_and_isolated(unauthenticated_client):
    response = unauthenticated_client.get("/api/demands")
    assert response.status_code == 200
    assert response.json() == []


def test_authenticated_create_list_delete_and_cache_invalidation(client, integration_db):
    assert client.get("/api/demands").json() == []
    response = client.post("/api/demands", json=demand())
    assert response.status_code == 201, response.text
    record = response.json()
    assert record["agent_id"] == "agent_bound"
    row = integration_db.execute("SELECT * FROM demands WHERE id=?", (record["id"],)).fetchone()
    assert row["agent_id"] == "agent_bound"
    listing = client.get("/api/demands?category=research&agent_id=agent_bound&limit=1")
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [record["id"]]
    assert client.get("/api/demands?category=other").json() == []
    deleted = client.delete(f"/api/demands/{record['id']}")
    assert deleted.status_code == 200, deleted.text
    assert deleted.json() == {"status": "deleted", "demand_id": record["id"]}
    assert client.get("/api/demands").json() == []
    assert integration_db.execute("SELECT COUNT(*) FROM demands").fetchone()[0] == 0


def test_cannot_delete_other_owners_demand(client, integration_db):
    from usmsb_sdk.api.database import create_demand

    record = create_demand(demand(agent_id="other-owner"))
    response = client.delete(f"/api/demands/{record['id']}")
    assert response.status_code == 403
    assert integration_db.execute("SELECT COUNT(*) FROM demands").fetchone()[0] == 1


def test_delete_missing_demand_is_404(client):
    assert client.delete("/api/demands/nonexistent").status_code == 404


@pytest.mark.parametrize("limit", [0, -1, 1001])
def test_list_rejects_invalid_bounds(unauthenticated_client, limit):
    assert unauthenticated_client.get(f"/api/demands?limit={limit}").status_code == 422


def test_invalid_create_does_not_persist(client, integration_db):
    assert client.post("/api/demands", json={"description": "missing title"}).status_code == 422
    assert integration_db.execute("SELECT COUNT(*) FROM demands").fetchone()[0] == 0


def test_real_api_key_binds_actor_and_revocation_takes_effect(
    unauthenticated_client,
    integration_db,
    sample_bound_agent,
    monkeypatch,
):
    from usmsb_sdk.api.rest import api_key_manager
    from usmsb_sdk.api.rest.api_key_manager import generate_api_key

    monkeypatch.setenv("USMSB_API_KEY_PEPPER", "local-test-only-" + "x" * 32)
    monkeypatch.setattr(api_key_manager, "_failed_attempts", {})
    raw_key, hashed, prefix = generate_api_key(sample_bound_agent)
    integration_db.execute(
        "UPDATE agent_api_keys SET key_hash=?,key_prefix=? WHERE id='bound_key1'",
        (hashed, prefix),
    )
    integration_db.commit()
    headers = {"X-API-Key": raw_key, "X-Agent-ID": sample_bound_agent}
    response = unauthenticated_client.post("/api/demands", json=demand(), headers=headers)
    assert response.status_code == 201, response.text
    assert response.json()["agent_id"] == sample_bound_agent
    assert (
        integration_db.execute(
            "SELECT last_used_at FROM agent_api_keys WHERE id='bound_key1'"
        ).fetchone()[0]
        is not None
    )
    integration_db.execute("UPDATE agent_api_keys SET revoked_at=1 WHERE id='bound_key1'")
    integration_db.commit()
    denied = unauthenticated_client.delete(f"/api/demands/{response.json()['id']}", headers=headers)
    assert denied.status_code == 401
    assert integration_db.execute("SELECT COUNT(*) FROM demands").fetchone()[0] == 1
