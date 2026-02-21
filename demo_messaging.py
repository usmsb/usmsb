#!/usr/bin/env python3
"""
Agent-to-Agent Messaging Demo

Demonstrates:
1. Agent Discovery
2. Quote Request (Buyer -> Supplier)
3. Quote Response (Supplier -> Buyer)
4. Match Creation (Matcher Agent)
"""

import urllib.request
import urllib.error
import json

PLATFORM_URL = "http://localhost:8000"

def http_get(url):
    """Make HTTP GET request using urllib."""
    req = urllib.request.Request(url, headers={"User-Agent": "demo-script/1.0"})
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode('utf-8'))

def http_post(url, data):
    """Make HTTP POST request using urllib."""
    json_data = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=json_data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "demo-script/1.0"
        }
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode('utf-8'))

def main():
    print("=" * 60)
    print("Agent-to-Agent Messaging Demo")
    print("=" * 60)

    # Step 1: Agent Discovery
    print("\n=== Step 1: Agent Discovery ===")
    print("Buyer (buyer_001) searches for suppliers...")

    agents = http_get(f"{PLATFORM_URL}/agents")

    suppliers = [a for a in agents if 'supply' in a.get('capabilities', [])]
    print(f"Found {len(suppliers)} supplier(s):")
    for s in suppliers:
        print(f"  - {s['name']} (ID: {s['id']})")
        print(f"    Capabilities: {s['capabilities']}")

    if not suppliers:
        print("No suppliers found!")
        return

    supplier_id = suppliers[0]['id']
    print(f"\nSelected supplier: {supplier_id}")

    # Step 2: Buyer sends Quote Request
    print("\n=== Step 2: Buyer sends Quote Request ===")

    quote_request = {
        "buyer_id": "buyer_001",
        "product_id": "steel_plate_q235",
        "product_name": "钢板 Q235",
        "quantity": 100,
        "unit": "吨",
        "target_price": 4200.0,
        "delivery_date": "2026-03-15",
        "delivery_location": "上海仓库",
        "requirements": {"thickness": "10mm", "standard": "GB/T"}
    }

    result = http_post(f"{PLATFORM_URL}/quotes/request", quote_request)
    print(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)}")

    request_id = result.get('request_id')
    print(f"\nQuote request created: {request_id}")

    # Step 3: Supplier sends Quote Response
    print("\n=== Step 3: Supplier sends Quote Response ===")

    quote_response = {
        "request_id": request_id,
        "supplier_id": supplier_id,
        "product_id": "steel_plate_q235",
        "unit_price": 4500.0,
        "total_price": 450000.0,
        "currency": "CNY",
        "valid_until": "2026-02-25",
        "delivery_time_days": 7,
        "terms": {"payment": "30天账期", "warranty": "质保1年"}
    }

    result = http_post(f"{PLATFORM_URL}/quotes/response", quote_response)
    print(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)}")

    quote_id = result.get('quote_id')
    print(f"\nQuote submitted: {quote_id}")

    # Step 4: Matcher Agent creates a match
    print("\n=== Step 4: Matcher Agent creates match ===")

    # Note: urllib doesn't support query params easily for POST, so we include in URL
    match_url = f"{PLATFORM_URL}/quotes/match/{request_id}?quote_id={quote_id}"
    result = http_post(match_url, {})
    print(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)}")

    # Step 5: Summary
    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    print(f"  - Buyer: buyer_001")
    print(f"  - Supplier: {supplier_id}")
    print(f"  - Request ID: {request_id}")
    print(f"  - Quote ID: {quote_id}")
    print(f"  - Match Status: Matched")
    print("\nView all matches at: http://localhost:8000/quotes/matches")


if __name__ == "__main__":
    main()
