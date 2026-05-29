#!/usr/bin/env python3
"""
Admin API Testing with isolated TestClient
"""

import sys
sys.path.insert(0, '/Users/gujun/vibecode/usmsb/src')

# First, let's just test if the app can be created
print("1. Creating FastAPI TestClient...")
try:
    from fastapi.testclient import TestClient
    from usmsb_sdk.api.rest.main import app
    client = TestClient(app)
    print("   ✓ TestClient created successfully")
except Exception as e:
    print(f"   ✗ Failed to create TestClient: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test a simple public endpoint first
print("\n2. Testing root endpoint...")
try:
    response = client.get("/")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   ✓ Root endpoint works")
    else:
        print(f"   ⚠ Unexpected status: {response.status_code}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test the health endpoint
print("\n3. Testing /health endpoint...")
try:
    response = client.get("/health")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   ✓ /health works")
    else:
        print(f"   ⚠ Unexpected status: {response.status_code}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Now test admin endpoints (they should return 401 without auth)
print("\n4. Testing admin endpoints (expecting 401 without auth)...")

endpoints = [
    "/api/admin/dashboard",
    "/api/admin/agents",
    "/api/admin/users",
    "/api/admin/transactions",
    "/api/admin/orders",
    "/api/admin/nodes",
    "/api/admin/matching",
    "/api/admin/gene-capsules",
    "/api/admin/intelligence",
    "/api/admin/governance",
    "/api/admin/system/health",
    "/api/admin/system/config",
    "/api/admin/system/logs",
    "/api/admin/permissions",
]

for ep in endpoints:
    try:
        response = client.get(ep)
        if response.status_code == 401:
            print(f"   ✓ {ep} -> 401 (correct, needs auth)")
        else:
            print(f"   ⚠ {ep} -> {response.status_code}")
    except Exception as e:
        print(f"   ✗ {ep} -> Error: {e}")

print("\n" + "="*60)
print("Admin API Basic Tests Complete")
print("="*60)