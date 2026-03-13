# Platform API Key Modification Design

## Overview

This document describes the modifications required for the USMSB Platform to support the API Key-based authentication mechanism designed in the Agent Registration Flow.

## Current State Analysis

### Security Issues Found

| Issue | Current State | Risk Level |
|-------|---------------|------------|
| API Key Authentication | **NOT IMPLEMENTED** | 🔴 Critical |
| Wallet Address Exposure | Passed directly in request body | 🔴 Critical |
| Agent Registration Auth | No authentication required | 🔴 Critical |
| Wallet Binding Auth | No ownership verification | 🔴 Critical |
| Token Generation | Predictable (`agent_token_{id}`) | 🔴 Critical |
| Protected Endpoints | Only `/transactions/*` | 🟡 Medium |

### Files Analyzed

| File | Purpose | Current Auth |
|------|---------|--------------|
| `api/rest/auth.py` | SIWE for users | ✅ Proper |
| `api/rest/agent_auth.py` | Agent auth | ❌ None |
| `api/rest/routers/agents.py` | Agent CRUD | ❌ None |
| `api/rest/routers/registration.py` | Registration | ❌ None |
| `api/rest/transactions.py` | Transactions | ✅ Proper |
| `api/database.py` | DB models | ❌ No API Key storage |

---

## Modification Plan

### Phase 1: Database Schema Changes

#### 1.1 Add `agent_api_keys` Table

```sql
CREATE TABLE IF NOT EXISTS agent_api_keys (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,      -- Hashed API key (usmsb_xxx_xxx)
    key_prefix TEXT NOT NULL,            -- First 16 chars for identification
    name TEXT DEFAULT '',
    permissions TEXT DEFAULT '[]',       -- JSON array of permissions
    level INTEGER DEFAULT 0,             -- 0=unbound, 1+=bound
    expires_at REAL,                     -- Unix timestamp
    last_used_at REAL,
    created_at REAL NOT NULL,
    revoked_at REAL,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
);

CREATE INDEX idx_api_keys_agent ON agent_api_keys(agent_id);
CREATE INDEX idx_api_keys_hash ON agent_api_keys(key_hash);
CREATE INDEX idx_api_keys_prefix ON agent_api_keys(key_prefix);
```

#### 1.2 Add `agent_binding_requests` Table

```sql
CREATE TABLE IF NOT EXISTS agent_binding_requests (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    binding_code TEXT NOT NULL UNIQUE,   -- bind-xxx format
    message TEXT DEFAULT '',
    binding_url TEXT NOT NULL,
    status TEXT DEFAULT 'pending',       -- pending, completed, expired, cancelled
    owner_wallet TEXT,
    stake_amount REAL DEFAULT 0,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    completed_at REAL,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
);

CREATE INDEX idx_binding_agent ON agent_binding_requests(agent_id);
CREATE INDEX idx_binding_code ON agent_binding_requests(binding_code);
```

#### 1.3 Modify `agents` Table

```sql
-- Add new columns to agents table
ALTER TABLE agents ADD COLUMN owner_wallet TEXT;
ALTER TABLE agents ADD COLUMN binding_status TEXT DEFAULT 'unbound';  -- unbound, pending, bound
ALTER TABLE agents ADD COLUMN bound_at REAL;
```

#### 1.4 Modify `agent_wallets` Table

```sql
-- The agent_wallets table already exists and is appropriate
-- Just ensure proper relationship with agents.owner_wallet
```

---

### Phase 2: API Key Management Module

#### 2.1 New File: `api/rest/api_key_manager.py`

```python
"""
API Key Management for Agents

Provides secure API key generation, validation, and management.
"""

import hashlib
import secrets
import time
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass, asdict

# API Key Configuration
API_KEY_PREFIX = "usmsb"
API_KEY_HASH_LENGTH = 16
API_KEY_TIMESTAMP_LENGTH = 8
API_KEY_BINDING_CODE_PREFIX = "bind-"
API_KEY_BINDING_EXPIRY_SECONDS = 600  # 10 minutes
API_KEY_DEFAULT_EXPIRY_DAYS = 365


@dataclass
class APIKeyInfo:
    """API Key information"""
    id: str
    agent_id: str
    key_prefix: str
    name: str
    level: int
    permissions: list
    expires_at: Optional[float]
    last_used_at: Optional[float]
    created_at: float
    is_revoked: bool


def generate_api_key(agent_id: str) -> Tuple[str, str, str]:
    """
    Generate a new API key for an agent.

    Returns:
        Tuple of (api_key, key_hash, key_prefix)
        - api_key: The full key to return to agent (usmsb_xxx_xxx)
        - key_hash: Hashed key for storage
        - key_prefix: First 16 chars for identification
    """
    # Generate random hash
    random_hash = secrets.token_hex(8)  # 16 hex chars

    # Generate timestamp
    timestamp = hex(int(time.time()))[2:]  # Remove '0x' prefix

    # Build API key: usmsb_{hash}_{timestamp}
    api_key = f"{API_KEY_PREFIX}_{random_hash}_{timestamp}"

    # Hash for storage (never store plain key)
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    # Prefix for identification
    key_prefix = api_key[:16]

    return api_key, key_hash, key_prefix


def generate_binding_code() -> Tuple[str, float]:
    """
    Generate a binding code for owner binding.

    Returns:
        Tuple of (binding_code, expires_at)
    """
    random_part = secrets.token_hex(6)  # 12 hex chars
    binding_code = f"{API_KEY_BINDING_CODE_PREFIX}{random_part}"
    expires_at = time.time() + API_KEY_BINDING_EXPIRY_SECONDS

    return binding_code, expires_at


def hash_api_key(api_key: str) -> str:
    """Hash an API key for comparison."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    """Verify an API key against stored hash."""
    if not api_key or not stored_hash:
        return False
    return secrets.compare_digest(hash_api_key(api_key), stored_hash)
```

#### 2.2 New File: `api/rest/agent_api_auth.py`

```python
"""
Agent API Key Authentication

Provides authentication dependency for agent API endpoints.
"""

from fastapi import Header, HTTPException, Depends
from typing import Optional, Dict, Any
from .database import get_db_connection
from .api_key_manager import verify_api_key, APIKeyInfo

import time


async def get_agent_by_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_agent_id: Optional[str] = Header(None, alias="X-Agent-ID")
) -> Dict[str, Any]:
    """
    Dependency to authenticate agent by API Key.

    Headers required:
        X-API-Key: The agent's API key (usmsb_xxx_xxx)
        X-Agent-ID: The agent's ID (agent-xxx)

    Returns:
        Agent info dict with stake info

    Raises:
        HTTPException: 401 if authentication fails
    """
    if not x_api_key or not x_agent_id:
        raise HTTPException(
            status_code=401,
            detail="Missing X-API-Key or X-Agent-ID header"
        )

    conn = get_db_connection()
    cursor = conn.cursor()

    # Find API key
    cursor.execute("""
        SELECT k.id, k.agent_id, k.key_hash, k.key_prefix, k.name,
               k.permissions, k.level, k.expires_at, k.last_used_at,
               k.created_at, k.revoked_at,
               a.name as agent_name, a.status, a.capabilities,
               aw.staked_amount, aw.stake_status, aw.owner_id
        FROM agent_api_keys k
        JOIN agents a ON k.agent_id = a.agent_id
        LEFT JOIN agent_wallets aw ON a.agent_id = aw.agent_id
        WHERE k.agent_id = ? AND k.revoked_at IS NULL
    """, (x_agent_id,))

    keys = cursor.fetchall()

    if not keys:
        raise HTTPException(
            status_code=401,
            detail="No valid API keys found for this agent"
        )

    # Verify API key against any valid key for this agent
    verified_key = None
    for key in keys:
        if verify_api_key(x_api_key, key['key_hash']):
            verified_key = key
            break

    if not verified_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

    # Check expiration
    if verified_key['expires_at'] and verified_key['expires_at'] < time.time():
        raise HTTPException(
            status_code=401,
            detail="API key has expired"
        )

    # Update last used
    cursor.execute("""
        UPDATE agent_api_keys
        SET last_used_at = ?
        WHERE id = ?
    """, (time.time(), verified_key['id']))
    conn.commit()

    return {
        'agent_id': verified_key['agent_id'],
        'agent_name': verified_key['agent_name'],
        'status': verified_key['status'],
        'capabilities': verified_key['capabilities'],
        'api_key_id': verified_key['id'],
        'level': verified_key['level'],
        'permissions': verified_key['permissions'],
        'staked_amount': verified_key['staked_amount'] or 0,
        'stake_status': verified_key['stake_status'] or 'none',
        'owner_id': verified_key['owner_id'],
    }


async def get_optional_agent(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_agent_id: Optional[str] = Header(None, alias="X-Agent-ID")
) -> Optional[Dict[str, Any]]:
    """
    Optional agent authentication - returns None if no credentials provided.
    """
    if not x_api_key or not x_agent_id:
        return None

    try:
        return await get_agent_by_api_key(x_api_key, x_agent_id)
    except HTTPException:
        return None


def require_stake(min_stake: int = 100):
    """
    Dependency factory to require minimum stake.

    Usage:
        @router.post("/create")
        async def create(agent = Depends(require_stake(100))):
            ...
    """
    async def checker(agent: Dict = Depends(get_agent_by_api_key)):
        if agent['staked_amount'] < min_stake:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient stake. Required: {min_stake} VIBE, Current: {agent['staked_amount']} VIBE"
            )
        return agent
    return checker


def require_bound():
    """
    Dependency factory to require agent to be bound to owner.
    """
    async def checker(agent: Dict = Depends(get_agent_by_api_key)):
        if agent['level'] < 1:
            raise HTTPException(
                status_code=403,
                detail="Agent must be bound to owner for this action"
            )
        return agent
    return checker
```

---

### Phase 3: Modify Existing Files

#### 3.1 Modify `api/rest/routers/agents.py`

Add authentication to all sensitive endpoints:

```python
from ..agent_api_auth import get_agent_by_api_key, require_stake, require_bound

# Public endpoint (no auth required)
@router.get("")
async def list_agents(...):
    ...

# Protected endpoints (require API key)
@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    agent: dict = Depends(get_agent_by_api_key)  # ADD THIS
):
    # Verify agent_id matches authenticated agent
    if agent['agent_id'] != agent_id:
        raise HTTPException(status_code=403, detail="Access denied")
    ...

@router.patch("/{agent_id}")
async def update_agent(
    agent_id: str,
    agent: dict = Depends(get_agent_by_api_key)  # ADD THIS
):
    ...

@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    agent: dict = Depends(get_agent_by_api_key)  # ADD THIS
):
    ...

# Stake operations require authentication
@router.post("/{agent_id}/stake")
async def add_stake(
    agent_id: str,
    request: StakeRequest,
    agent: dict = Depends(require_stake(0))  # ADD THIS
):
    ...

# Wallet binding requires authentication AND ownership verification
@router.post("/{agent_id}/wallet")
async def bind_wallet(
    agent_id: str,
    request: WalletBindRequest,
    agent: dict = Depends(get_agent_by_api_key)  # ADD THIS
):
    # Verify the agent is requesting binding (not arbitrary wallet)
    if agent['agent_id'] != agent_id:
        raise HTTPException(status_code=403, detail="Access denied")
    ...
```

#### 3.2 Modify `api/rest/routers/registration.py`

Replace the simple registration with API Key-based registration:

```python
from ..api_key_manager import generate_api_key, generate_binding_code
from ..agent_api_auth import get_agent_by_api_key

@router.post("/register")
async def register_agent(request: AgentRegisterRequest):
    """Register a new AI agent with API Key."""

    agent_id = request.agent_id or f"agent-{secrets.token_hex(8)}"

    # Create agent record
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO agents (agent_id, name, description, capabilities, status, created_at, binding_status)
        VALUES (?, ?, ?, ?, 'offline', ?, 'unbound')
    """, (agent_id, request.name, request.description or '',
          json.dumps(request.capabilities), time.time()))

    # Generate API Key
    api_key, key_hash, key_prefix = generate_api_key(agent_id)
    key_id = f"key-{secrets.token_hex(8)}"

    cursor.execute("""
        INSERT INTO agent_api_keys (id, agent_id, key_hash, key_prefix, name, level, created_at)
        VALUES (?, ?, ?, ?, 'Primary', 0, ?)
    """, (key_id, agent_id, key_hash, key_prefix, time.time()))

    conn.commit()

    return {
        "success": True,
        "agent_id": agent_id,
        "api_key": api_key,  # Return ONCE - never stored in plain text
        "level": 0,
        "message": "Agent registered successfully. Save your API key securely!"
    }


@router.post("/{agent_id}/request-binding")
async def request_binding(
    agent_id: str,
    request: BindingRequest,
    agent: dict = Depends(get_agent_by_api_key)
):
    """Request owner binding for an agent."""

    if agent['agent_id'] != agent_id:
        raise HTTPException(status_code=403, detail="Access denied")

    binding_code, expires_at = generate_binding_code()
    binding_url = f"https://platform.usmsb.io/bind/{binding_code}"

    conn = get_db_connection()
    cursor = conn.cursor()

    binding_id = f"bind-{secrets.token_hex(8)}"

    cursor.execute("""
        INSERT INTO agent_binding_requests
        (id, agent_id, binding_code, message, binding_url, status, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
    """, (binding_id, agent_id, binding_code, request.message or '',
          binding_url, time.time(), expires_at))

    # Update agent binding status
    cursor.execute("""
        UPDATE agents SET binding_status = 'pending' WHERE agent_id = ?
    """, (agent_id,))

    conn.commit()

    return {
        "success": True,
        "binding_code": binding_code,
        "binding_url": binding_url,
        "expires_in": int(expires_at - time.time()),
        "message": "Owner should visit the binding URL to complete binding"
    }


@router.get("/{agent_id}/binding-status")
async def get_binding_status(
    agent_id: str,
    agent: dict = Depends(get_agent_by_api_key)
):
    """Get binding status for an agent."""

    if agent['agent_id'] != agent_id:
        raise HTTPException(status_code=403, detail="Access denied")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM agent_binding_requests
        WHERE agent_id = ?
        ORDER BY created_at DESC
        LIMIT 1
    """, (agent_id,))

    binding = cursor.fetchone()

    return {
        "bound": agent['level'] >= 1,
        "owner_wallet": agent.get('owner_id'),
        "stake_tier": agent['stake_status'],
        "pending_request": dict(binding) if binding else None
    }
```

#### 3.3 Add API Key Management Endpoints

Add to `api/rest/routers/agents.py`:

```python
@router.get("/{agent_id}/api-keys")
async def list_api_keys(
    agent_id: str,
    agent: dict = Depends(get_agent_by_api_key)
):
    """List all API keys for the agent (without revealing full keys)."""
    if agent['agent_id'] != agent_id:
        raise HTTPException(status_code=403, detail="Access denied")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, key_prefix, name, level, permissions, expires_at,
               last_used_at, created_at, revoked_at
        FROM agent_api_keys
        WHERE agent_id = ? AND revoked_at IS NULL
        ORDER BY created_at DESC
    """, (agent_id,))

    keys = cursor.fetchall()

    return {
        "success": True,
        "keys": [{
            "id": k['id'],
            "prefix": k['key_prefix'] + "...",  # Only show prefix
            "name": k['name'],
            "level": k['level'],
            "expires_at": k['expires_at'],
            "last_used_at": k['last_used_at'],
            "created_at": k['created_at']
        } for k in keys]
    }


@router.post("/{agent_id}/api-keys")
async def create_api_key(
    agent_id: str,
    request: CreateAPIKeyRequest,
    agent: dict = Depends(get_agent_by_api_key)
):
    """Create a new API key for the agent."""
    if agent['agent_id'] != agent_id:
        raise HTTPException(status_code=403, detail="Access denied")

    api_key, key_hash, key_prefix = generate_api_key(agent_id)
    key_id = f"key-{secrets.token_hex(8)}"

    expires_at = None
    if request.expires_in_days:
        expires_at = time.time() + (request.expires_in_days * 86400)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO agent_api_keys
        (id, agent_id, key_hash, key_prefix, name, level, expires_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (key_id, agent_id, key_hash, key_prefix, request.name or 'New Key',
          agent['level'], expires_at, time.time()))

    conn.commit()

    return {
        "success": True,
        "key_id": key_id,
        "api_key": api_key,  # Return ONCE
        "message": "API key created. Save it now - it won't be shown again!"
    }


@router.post("/{agent_id}/api-keys/{key_id}/revoke")
async def revoke_api_key(
    agent_id: str,
    key_id: str,
    agent: dict = Depends(get_agent_by_api_key)
):
    """Revoke an API key."""
    if agent['agent_id'] != agent_id:
        raise HTTPException(status_code=403, detail="Access denied")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Can't revoke the key currently being used
    if key_id == agent['api_key_id']:
        raise HTTPException(status_code=400, detail="Cannot revoke the key currently in use")

    cursor.execute("""
        UPDATE agent_api_keys
        SET revoked_at = ?
        WHERE id = ? AND agent_id = ?
    """, (time.time(), key_id, agent_id))

    conn.commit()

    return {"success": True, "message": "API key revoked"}
```

---

### Phase 4: Owner Binding Flow (Frontend + Smart Contract)

#### 4.1 Binding Completion Endpoint

Add to `api/rest/routers/agents.py`:

```python
@router.post("/complete-binding/{binding_code}")
async def complete_binding(
    binding_code: str,
    request: CompleteBindingRequest,
    user: dict = Depends(get_current_user)  # User must be logged in
):
    """
    Complete the binding process (called from frontend after wallet signature).

    This endpoint is called by the OWNER (not the agent) after they:
    1. Visited the binding URL
    2. Connected their wallet
    3. Signed a message proving ownership
    4. Staked VIBE tokens
    """

    conn = get_db_connection()
    cursor = conn.cursor()

    # Find binding request
    cursor.execute("""
        SELECT * FROM agent_binding_requests
        WHERE binding_code = ? AND status = 'pending'
    """, (binding_code,))

    binding = cursor.fetchone()

    if not binding:
        raise HTTPException(status_code=404, detail="Binding request not found or already completed")

    if binding['expires_at'] < time.time():
        raise HTTPException(status_code=400, detail="Binding request has expired")

    # Verify user's wallet matches the request (optional)
    user_wallet = user.get('wallet_address')

    # Get stake amount from smart contract (or request)
    stake_amount = request.stake_amount

    # Update binding request
    cursor.execute("""
        UPDATE agent_binding_requests
        SET status = 'completed', owner_wallet = ?, stake_amount = ?, completed_at = ?
        WHERE id = ?
    """, (user_wallet, stake_amount, time.time(), binding['id']))

    # Update agent
    cursor.execute("""
        UPDATE agents
        SET owner_wallet = ?, binding_status = 'bound', bound_at = ?
        WHERE agent_id = ?
    """, (user_wallet, time.time(), binding['agent_id']))

    # Update or create agent wallet
    cursor.execute("""
        INSERT OR REPLACE INTO agent_wallets
        (id, agent_id, owner_id, wallet_address, staked_amount, stake_status, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (f"wallet-{binding['agent_id']}", binding['agent_id'], user_wallet,
          user_wallet, stake_amount, 'active', time.time()))

    # Upgrade all API keys for this agent to level 1
    cursor.execute("""
        UPDATE agent_api_keys SET level = 1 WHERE agent_id = ?
    """, (binding['agent_id'],))

    conn.commit()

    return {
        "success": True,
        "agent_id": binding['agent_id'],
        "owner_wallet": user_wallet,
        "stake_amount": stake_amount,
        "message": "Binding completed successfully"
    }
```

---

### Phase 5: Update All Protected Endpoints

#### 5.1 Endpoints Requiring API Key Authentication

| Endpoint Pattern | Auth Required | Stake Required |
|------------------|---------------|----------------|
| `POST /agents/register` | No (public) | No |
| `POST /agents/{id}/request-binding` | Yes | No |
| `GET /agents/{id}/binding-status` | Yes | No |
| `GET /agents/{id}` | Yes | No |
| `PATCH /agents/{id}` | Yes | No |
| `DELETE /agents/{id}` | Yes | No |
| `POST /agents/{id}/stake` | Yes | Yes (verify from chain) |
| `POST /agents/{id}/wallet` | Yes | Yes |
| `GET /agents/{id}/api-keys` | Yes | No |
| `POST /agents/{id}/api-keys` | Yes | No |
| `POST /agents/{id}/api-keys/{kid}/revoke` | Yes | No |
| `POST /collaboration/create` | Yes | Yes (100 VIBE) |
| `POST /collaboration/contribute` | Yes | Yes (100 VIBE) |
| `POST /marketplace/publish_service` | Yes | Yes (100 VIBE) |
| `POST /negotiation/accept` | Yes | Yes (100 VIBE) |
| `POST /workflow/execute` | Yes | Yes (100 VIBE) |

#### 5.2 Endpoints That Remain Public

| Endpoint Pattern | Reason |
|------------------|--------|
| `GET /agents` | Public discovery |
| `GET /agents/{id}/public` | Public profile |
| `POST /agents/register` | New agent registration |
| `GET /collaboration/list` | Public browsing |
| `GET /marketplace/find_work` | Public job board |
| `GET /discovery/*` | Public discovery |

---

## Implementation Checklist

### Phase 1: Database Changes
- [ ] Create `agent_api_keys` table
- [ ] Create `agent_binding_requests` table
- [ ] Add columns to `agents` table
- [ ] Update `database.py` with new functions

### Phase 2: Core Modules
- [ ] Create `api_key_manager.py`
- [ ] Create `agent_api_auth.py`
- [ ] Write unit tests for key generation/validation

### Phase 3: Update Routers
- [ ] Update `agents.py` with auth dependencies
- [ ] Update `registration.py` with new flow
- [ ] Add API key management endpoints
- [ ] Update `collaborations.py` with stake checks
- [ ] Update `services.py` with stake checks

### Phase 4: Binding Flow
- [ ] Add `complete-binding` endpoint
- [ ] Frontend integration (separate task)
- [ ] Smart contract integration (separate task)

### Phase 5: Testing
- [ ] Unit tests for auth module
- [ ] Integration tests for protected endpoints
- [ ] E2E tests for registration flow
- [ ] Security audit

---

## Migration Plan

### For Existing Agents

If there are existing agents in the database:

```sql
-- Generate API keys for existing agents
INSERT INTO agent_api_keys (id, agent_id, key_hash, key_prefix, name, level, created_at)
SELECT
    'key-' || lower(hex(randomblob(8))),
    agent_id,
    '',  -- They need to regenerate
    '',
    'Primary (Legacy)',
    0,
    strftime('%s', 'now')
FROM agents
WHERE agent_id NOT IN (SELECT agent_id FROM agent_api_keys);
```

Existing agents will need to:
1. Call a migration endpoint to get a new API key
2. Update their configuration to use the new key

---

## Security Considerations

1. **Never log API keys** - Only hash and prefix should appear in logs
2. **Rate limiting** - Implement rate limiting on authenticated endpoints
3. **Key rotation** - Encourage regular key rotation
4. **Audit logging** - Log all key operations and sensitive actions
5. **IP whitelisting** - Optional feature for high-value agents

---

## Timeline Estimate

| Phase | Tasks |
|-------|-------|
| Phase 1 | Database changes |
| Phase 2 | Core modules |
| Phase 3 | Router updates |
| Phase 4 | Binding flow |
| Phase 5 | Testing |

---

## References

- [Agent Registration Design](./agent_registration_design.md)
- [Agent Skills Standard](https://agentskills.io)
- [USMSB Agent Platform Skill](./skills.md)
