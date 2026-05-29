#!/usr/bin/env python3
"""
Admin Router Direct Testing Script

Tests the admin router endpoints directly.
"""

import sys
sys.path.insert(0, '/Users/gujun/vibecode/usmsb/src')

print("Testing Admin Router endpoints directly...")

# Import the admin router directly
from usmsb_sdk.api.rest.routers.admin import router, _check_admin, _safe_float, _safe_int, _paginate
from usmsb_sdk.api.database import get_db, get_all_agents, get_agent, get_transactions_by_user
from usmsb_sdk.api.rest.unified_auth import get_current_user_unified

print("\n✓ Imports successful")

# Test 1: Helper functions
print("\n1. Testing helper functions...")
db = get_db()
print(f"   ✓ get_db() works")

# Test 2: _check_admin
print("\n2. Testing _check_admin with admin user...")
admin_user = {'user_role': 'superadmin'}
try:
    _check_admin(admin_user)
    print("   ✓ _check_admin allows superadmin")
except Exception as e:
    print(f"   ✗ _check_admin failed: {e}")

print("\n3. Testing _check_admin with regular user...")
regular_user = {'user_role': 'human'}
try:
    _check_admin(regular_user)
    print("   ✗ _check_admin should have raised HTTPException")
except Exception as e:
    print(f"   ✓ _check_admin correctly rejects non-admin: {type(e).__name__}")

# Test 4: _safe_float and _safe_int
print("\n4. Testing _safe_float and _safe_int...")
assert _safe_float(None) == 0.0
assert _safe_float("123.45") == 123.45
assert _safe_int(None) == 0
assert _safe_int("42") == 42
print("   ✓ _safe_float and _safe_int work correctly")

# Test 5: _paginate
print("\n5. Testing _paginate...")
items = list(range(100))
page_items, total, page, total_pages = _paginate(items, 2, 10)
assert len(page_items) == 10
assert total == 100
assert page == 2
assert total_pages == 10
print("   ✓ _paginate works correctly")

# Test 6: Check router has all endpoints
print("\n6. Checking router endpoints...")
endpoints = [route.path for route in router.routes]
expected_endpoints = [
    "/dashboard",
    "/agents",
    "/agents/{agent_id}",
    "/users",
    "/users/{user_id}/role",
    "/transactions",
    "/orders",
    "/nodes",
    "/matching",
    "/gene-capsules",
    "/intelligence",
    "/governance",
    "/system/health",
    "/system/config",
    "/system/logs",
    "/permissions",
]
for ep in expected_endpoints:
    if ep in endpoints:
        print(f"   ✓ {ep}")
    else:
        print(f"   ✗ Missing endpoint: {ep}")

# Test 7: Check database functions exist
print("\n7. Checking database functions...")
try:
    agents = get_all_agents(limit=1)
    print(f"   ✓ get_all_agents() works, returned {len(agents)} agents")
except Exception as e:
    print(f"   ✗ get_all_agents() failed: {e}")

try:
    agent = get_agent("test-id")
    print(f"   ✓ get_agent() works, returned: {agent}")
except Exception as e:
    print(f"   ⚠ get_agent() error: {e}")

print("\n" + "="*60)
print("Direct Router Testing Complete")
print("="*60)