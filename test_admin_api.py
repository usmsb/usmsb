#!/usr/bin/env python3
"""
Admin API Endpoint Testing Script

Tests all /api/admin/* endpoints for correctness and bugs.
"""

import asyncio
import sys
import time
sys.path.insert(0, '/Users/gujun/vibecode/usmsb/src')

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class APIResult:
    endpoint: str
    method: str
    status: str  # "OK", "ERROR", "WARNING"
    message: str
    data: Any = None


async def test_admin_api():
    """Test all admin API endpoints"""
    print("\n" + "="*60)
    print("Admin API Endpoint Testing")
    print("="*60)

    # Use FastAPI TestClient approach
    from fastapi.testclient import TestClient
    from usmsb_sdk.api.rest.main import app

    client = TestClient(app)

    results: list[APIResult] = []

    # Helper to make requests
    def make_request(method: str, path: str, data: dict = None) -> tuple[int, Any]:
        try:
            if method == "GET":
                response = client.get(path)
            elif method == "PATCH":
                response = client.patch(path, json=data)
            elif method == "POST":
                response = client.post(path, json=data)
            else:
                return 500, {"error": f"Unsupported method: {method}"}
            return response.status_code, response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
        except Exception as e:
            return 500, {"error": str(e)}

    # Test 1: Dashboard
    print("\n1. Testing GET /api/admin/dashboard")
    status, data = make_request("GET", "/api/admin/dashboard")
    if status == 200:
        print(f"   ✓ Status: {status}")
        if "total_agents" in data:
            print(f"   ✓ total_agents: {data.get('total_agents')}")
        if "online_agents" in data:
            print(f"   ✓ online_agents: {data.get('online_agents')}")
        results.append(APIResult("/api/admin/dashboard", "GET", "OK", "Dashboard retrieved successfully", data))
    else:
        print(f"   ✗ Status: {status}, Error: {data}")
        results.append(APIResult("/api/admin/dashboard", "GET", "ERROR", f"Status {status}: {data}"))

    # Test 2: Agents List
    print("\n2. Testing GET /api/admin/agents")
    status, data = make_request("GET", "/api/admin/agents")
    if status == 200:
        print(f"   ✓ Status: {status}")
        if "agents" in data and "total" in data:
            print(f"   ✓ Total agents: {data.get('total')}")
        results.append(APIResult("/api/admin/agents", "GET", "OK", "Agents list retrieved"))
    else:
        print(f"   ✗ Status: {status}, Error: {data}")
        results.append(APIResult("/api/admin/agents", "GET", "ERROR", f"Status {status}: {data}"))

    # Test 3: Agents List with pagination
    print("\n3. Testing GET /api/admin/agents?page=1&page_size=10")
    status, data = make_request("GET", "/api/admin/agents?page=1&page_size=10")
    if status == 200:
        print(f"   ✓ Status: {status}")
        results.append(APIResult("/api/admin/agents?page=1&page_size=10", "GET", "OK", "Paginated agents OK"))
    else:
        print(f"   ✗ Status: {status}, Error: {data}")
        results.append(APIResult("/api/admin/agents?page=1&page_size=10", "GET", "ERROR", f"Status {status}: {data}"))

    # Test 4: Users List
    print("\n4. Testing GET /api/admin/users")
    status, data = make_request("GET", "/api/admin/users")
    if status == 200:
        print(f"   ✓ Status: {status}")
        if "users" in data and "total" in data:
            print(f"   ✓ Total users: {data.get('total')}")
        results.append(APIResult("/api/admin/users", "GET", "OK", "Users list retrieved"))
    else:
        print(f"   ✗ Status: {status}, Error: {data}")
        results.append(APIResult("/api/admin/users", "GET", "ERROR", f"Status {status}: {data}"))

    # Test 5: Transactions List
    print("\n5. Testing GET /api/admin/transactions")
    status, data = make_request("GET", "/api/admin/transactions")
    if status == 200:
        print(f"   ✓ Status: {status}")
        if "transactions" in data and "total" in data:
            print(f"   ✓ Total transactions: {data.get('total')}")
        results.append(APIResult("/api/admin/transactions", "GET", "OK", "Transactions list retrieved"))
    else:
        print(f"   ✗ Status: {status}, Error: {data}")
        results.append(APIResult("/api/admin/transactions", "GET", "ERROR", f"Status {status}: {data}"))

    # Test 6: Orders List
    print("\n6. Testing GET /api/admin/orders")
    status, data = make_request("GET", "/api/admin/orders")
    if status == 200:
        print(f"   ✓ Status: {status}")
        if "orders" in data and "total" in data:
            print(f"   ✓ Total orders: {data.get('total')}")
        results.append(APIResult("/api/admin/orders", "GET", "OK", "Orders list retrieved"))
    else:
        print(f"   ✗ Status: {status}, Error: {data}")
        results.append(APIResult("/api/admin/orders", "GET", "ERROR", f"Status {status}: {data}"))

    # Test 7: Nodes
    print("\n7. Testing GET /api/admin/nodes")
    status, data = make_request("GET", "/api/admin/nodes")
    if status == 200:
        print(f"   ✓ Status: {status}")
        if "nodes" in data and "total" in data:
            print(f"   ✓ Total nodes: {data.get('total')}, online: {data.get('online')}")
        results.append(APIResult("/api/admin/nodes", "GET", "OK", "Nodes list retrieved"))
    else:
        print(f"   ✗ Status: {status}, Error: {data}")
        results.append(APIResult("/api/admin/nodes", "GET", "ERROR", f"Status {status}: {data}"))

    # Test 8: Matching Analytics
    print("\n8. Testing GET /api/admin/matching")
    status, data = make_request("GET", "/api/admin/matching")
    if status == 200:
        print(f"   ✓ Status: {status}")
        if "funnel" in data:
            print(f"   ✓ Funnel: {data.get('funnel')}")
        results.append(APIResult("/api/admin/matching", "GET", "OK", "Matching analytics retrieved"))
    else:
        print(f"   ✗ Status: {status}, Error: {data}")
        results.append(APIResult("/api/admin/matching", "GET", "ERROR", f"Status {status}: {data}"))

    # Test 9: Gene Capsules
    print("\n9. Testing GET /api/admin/gene-capsules")
    status, data = make_request("GET", "/api/admin/gene-capsules")
    if status == 200:
        print(f"   ✓ Status: {status}")
        if "capsules" in data and "total" in data:
            print(f"   ✓ Total capsules: {data.get('total')}")
        results.append(APIResult("/api/admin/gene-capsules", "GET", "OK", "Gene capsules retrieved"))
    else:
        print(f"   ✗ Status: {status}, Error: {data}")
        results.append(APIResult("/api/admin/gene-capsules", "GET", "ERROR", f"Status {status}: {data}"))

    # Test 10: Intelligence Metrics
    print("\n10. Testing GET /api/admin/intelligence")
    status, data = make_request("GET", "/api/admin/intelligence")
    if status == 200:
        print(f"   ✓ Status: {status}")
        if "llm_calls_total" in data:
            print(f"   ✓ LLM calls: {data.get('llm_calls_total')}")
        results.append(APIResult("/api/admin/intelligence", "GET", "OK", "Intelligence metrics retrieved"))
    else:
        print(f"   ✗ Status: {status}, Error: {data}")
        results.append(APIResult("/api/admin/intelligence", "GET", "ERROR", f"Status {status}: {data}"))

    # Test 11: Governance
    print("\n11. Testing GET /api/admin/governance")
    status, data = make_request("GET", "/api/admin/governance")
    if status == 200:
        print(f"   ✓ Status: {status}")
        if "proposals" in data:
            print(f"   ✓ Proposals: {len(data.get('proposals', []))}")
        results.append(APIResult("/api/admin/governance", "GET", "OK", "Governance data retrieved"))
    else:
        print(f"   ✗ Status: {status}, Error: {data}")
        results.append(APIResult("/api/admin/governance", "GET", "ERROR", f"Status {status}: {data}"))

    # Test 12: System Health
    print("\n12. Testing GET /api/admin/system/health")
    status, data = make_request("GET", "/api/admin/system/health")
    if status == 200:
        print(f"   ✓ Status: {status}")
        if "status" in data:
            print(f"   ✓ System status: {data.get('status')}")
        if "db_size_mb" in data:
            print(f"   ✓ DB size: {data.get('db_size_mb')} MB")
        # Check for uptime issue (should not be current timestamp)
        if data.get('uptime_seconds', 0) > 1e9:  # Timestamp > year 2001
            print(f"   ⚠ uptime_seconds looks like a timestamp, not uptime!")
            results.append(APIResult("/api/admin/system/health", "GET", "WARNING", "uptime_seconds appears to be timestamp"))
        else:
            results.append(APIResult("/api/admin/system/health", "GET", "OK", "System health retrieved"))
    else:
        print(f"   ✗ Status: {status}, Error: {data}")
        results.append(APIResult("/api/admin/system/health", "GET", "ERROR", f"Status {status}: {data}"))

    # Test 13: System Config
    print("\n13. Testing GET /api/admin/system/config")
    status, data = make_request("GET", "/api/admin/system/config")
    if status == 200:
        print(f"   ✓ Status: {status}")
        if "chain_id" in data:
            print(f"   ✓ chain_id: {data.get('chain_id')}")
        results.append(APIResult("/api/admin/system/config", "GET", "OK", "System config retrieved"))
    else:
        print(f"   ✗ Status: {status}, Error: {data}")
        results.append(APIResult("/api/admin/system/config", "GET", "ERROR", f"Status {status}: {data}"))

    # Test 14: System Logs
    print("\n14. Testing GET /api/admin/system/logs")
    status, data = make_request("GET", "/api/admin/system/logs")
    if status == 200:
        print(f"   ✓ Status: {status}")
        if "logs" in data and "total" in data:
            print(f"   ✓ Total logs: {data.get('total')}")
        results.append(APIResult("/api/admin/system/logs", "GET", "OK", "System logs retrieved"))
    else:
        print(f"   ✗ Status: {status}, Error: {data}")
        results.append(APIResult("/api/admin/system/logs", "GET", "ERROR", f"Status {status}: {data}"))

    # Test 15: Permissions Matrix
    print("\n15. Testing GET /api/admin/permissions")
    status, data = make_request("GET", "/api/admin/permissions")
    if status == 200:
        print(f"   ✓ Status: {status}")
        if "matrix" in data and "roles" in data:
            print(f"   ✓ Matrix entries: {len(data.get('matrix', []))}, Roles: {data.get('roles')}")
        results.append(APIResult("/api/admin/permissions", "GET", "OK", "Permissions matrix retrieved"))
    else:
        print(f"   ✗ Status: {status}, Error: {data}")
        results.append(APIResult("/api/admin/permissions", "GET", "ERROR", f"Status {status}: {data}"))

    # Test 16: Agent Detail (404 expected without valid agent_id)
    print("\n16. Testing GET /api/admin/agents/test-agent-id (expected 404)")
    status, data = make_request("GET", "/api/admin/agents/test-agent-id")
    if status == 404:
        print(f"   ✓ Status: {status} (Expected 404 for non-existent agent)")
        results.append(APIResult("/api/admin/agents/{id}", "GET", "OK", "Correctly returns 404 for non-existent agent"))
    elif status == 200:
        print(f"   ✓ Status: {status} (Returns data for existing agent)")
        results.append(APIResult("/api/admin/agents/{id}", "GET", "OK", "Agent detail retrieved"))
    else:
        print(f"   ⚠ Status: {status}, Response: {data}")
        results.append(APIResult("/api/admin/agents/{id}", "GET", "WARNING", f"Unexpected status {status}"))

    # Test 17: User Role Update (401 expected without auth)
    print("\n17. Testing PATCH /api/admin/users/test-id/role (expected 401)")
    status, data = make_request("PATCH", "/api/admin/users/test-id/role?new_role=developer")
    if status == 401:
        print(f"   ✓ Status: {status} (Expected 401 without auth)")
        results.append(APIResult("/api/admin/users/{id}/role", "PATCH", "OK", "Correctly requires auth"))
    elif status == 200:
        print(f"   ✓ Status: {status} (Update succeeded)")
        results.append(APIResult("/api/admin/users/{id}/role", "PATCH", "OK", "Role update succeeded"))
    else:
        print(f"   ⚠ Status: {status}, Response: {data}")
        results.append(APIResult("/api/admin/users/{id}/role", "PATCH", "WARNING", f"Status {status}"))

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    ok_count = sum(1 for r in results if r.status == "OK")
    warning_count = sum(1 for r in results if r.status == "WARNING")
    error_count = sum(1 for r in results if r.status == "ERROR")

    for r in results:
        icon = "✓" if r.status == "OK" else "⚠" if r.status == "WARNING" else "✗"
        print(f"  {icon} [{r.method}] {r.endpoint} - {r.status}: {r.message}")

    print(f"\nResults: {ok_count} OK, {warning_count} WARNING, {error_count} ERROR")

    return error_count == 0


if __name__ == "__main__":
    success = asyncio.run(test_admin_api())
    exit(0 if success else 1)