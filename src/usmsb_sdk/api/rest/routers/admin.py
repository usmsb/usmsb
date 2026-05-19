"""
Admin Panel Backend API Router

Provides comprehensive admin data for the USMSB Admin Panel.
All endpoints require admin authentication (superadmin or node_admin role).

Prefix: /api/admin/*
"""
import time
import math
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from usmsb_sdk.api.database import (
    get_db,
    get_all_agents,
    get_agent,
    get_agent_wallet,
    get_metrics,
    get_transaction_stats,
    get_all_transactions,
    get_transactions_by_user,
    get_user_by_address,
    get_profile,
    get_all_agents,
    get_all_agents,
    get_all_agents,
)
from usmsb_sdk.api.rest.unified_auth import get_current_user_unified

router = APIRouter(prefix="/admin", tags=["Admin"])


# ============================================================================
# Pydantic Models
# ============================================================================

class DashboardResponse(BaseModel):
    total_agents: int = 0
    online_agents: int = 0
    total_users: int = 0
    total_transactions: int = 0
    total_transaction_volume: float = 0
    total_orders: int = 0
    pending_orders: int = 0
    completed_orders: int = 0
    total_volume_24h: float = 0
    tx_count_24h: int = 0
    active_negotiations: int = 0
    active_proposals: int = 0
    agent_growth: list[int] = []
    tx_volume_growth: list[float] = []
    top_agents: list[dict] = []
    recent_transactions: list[dict] = []


class AgentListResponse(BaseModel):
    agents: list[dict] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1


class UserListResponse(BaseModel):
    users: list[dict] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1


class TransactionListResponse(BaseModel):
    transactions: list[dict] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1


class OrderListResponse(BaseModel):
    orders: list[dict] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1


class NodeStatusResponse(BaseModel):
    nodes: list[dict] = []
    total: int = 0
    online: int = 0
    offline: int = 0


class MatchingAnalyticsResponse(BaseModel):
    funnel: dict = {}
    avg_match_time: float = 0
    success_rate: float = 0
    top_services: list[dict] = []
    recent_matches: list[dict] = []


class GeneCapsuleResponse(BaseModel):
    capsules: list[dict] = []
    total: int = 0


class IntelligenceMetricsResponse(BaseModel):
    llm_calls_total: int = 0
    token_usage: dict = {}
    active_sessions: int = 0
    avg_response_time: float = 0
    top_capabilities: list[dict] = []


class GovernanceResponse(BaseModel):
    proposals: list[dict] = []
    active_proposals: int = 0
    total_votes: int = 0
    participation_rate: float = 0


class SystemHealthResponse(BaseModel):
    status: str = "healthy"
    uptime_seconds: float = 0
    cpu_percent: float = 0
    memory_percent: float = 0
    disk_percent: float = 0
    db_size_mb: float = 0
    api_response_time_ms: float = 0
    components: dict = {}


class SystemLogsResponse(BaseModel):
    logs: list[dict] = []
    total: int = 0


class PermissionMatrixResponse(BaseModel):
    matrix: list[dict] = []
    roles: list[str] = []


# ============================================================================
# Helpers
# ============================================================================

def _check_admin(user: dict) -> None:
    """Verify user has admin role."""
    role = user.get('user_role', user.get('role', ''))
    if role not in ('superadmin', 'node_admin'):
        raise HTTPException(status_code=403, detail="Admin access required")


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val or 0)
    except (ValueError, TypeError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val or 0)
    except (ValueError, TypeError):
        return default


def _paginate(items: list, page: int, page_size: int) -> tuple[list, int, int, int]:
    """Paginate a list. Returns (items, total, page, total_pages)."""
    total = len(items)
    total_pages = max(1, math.ceil(total / page_size))
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end], total, page, total_pages


# ============================================================================
# Dashboard
# ============================================================================

@router.get("/dashboard", response_model=DashboardResponse)
async def get_admin_dashboard(request: Request):
    """Platform overview for admin dashboard."""
    user = await get_current_user_unified(request)
    _check_admin(user)

    db = get_db()
    now = time.time()
    day_ago = now - 86400

    # Agent stats
    all_agents = get_all_agents(limit=10000) or []
    online_agents = [a for a in all_agents if a.get('status') == 'online']

    # Transaction stats
    all_txs = get_all_transactions(limit=10000) or []
    txs_24h = [t for t in all_txs if _safe_float(t.get('created_at', 0)) > day_ago]
    total_volume = sum(_safe_float(t.get('amount', 0)) for t in all_txs)
    volume_24h = sum(_safe_float(t.get('amount', 0)) for t in txs_24h)

    # Order stats (from db directly)
    orders = db.execute("SELECT COUNT(*) as cnt, SUM(total_budget) as vol, status FROM orders GROUP BY status").fetchall()
    total_orders = sum(r['cnt'] for r in orders)
    pending_orders = sum(r['cnt'] for r in orders if r['status'] in ('pending', 'open', 'negotiating'))
    completed_orders = sum(r['cnt'] for r in orders if r['status'] == 'completed')

    # User count
    user_count = db.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
    total_users = user_count['cnt'] if user_count else 0

    # Proposals
    proposals = db.execute("SELECT COUNT(*) as cnt FROM proposals WHERE status = 'active'").fetchone()
    active_proposals = proposals['cnt'] if proposals else 0

    # Negotiations
    negs = db.execute("SELECT COUNT(*) as cnt FROM negotiations WHERE status = 'active'").fetchone()
    active_negotiations = negs['cnt'] if negs else 0

    # Top agents by stake
    top_agents = sorted(all_agents, key=lambda a: _safe_float(a.get('stake', 0)), reverse=True)[:5]
    top_agents_data = [{
        'agent_id': a.get('agent_id', ''),
        'name': a.get('name', 'Unknown'),
        'stake': _safe_float(a.get('stake', 0)),
        'status': a.get('status', 'offline'),
        'reputation': _safe_float(a.get('reputation', 0.5)),
    } for a in top_agents]

    # Recent transactions
    recent_txs = sorted(all_txs, key=lambda t: _safe_float(t.get('created_at', 0)), reverse=True)[:10]
    recent_tx_data = [{
        'tx_id': t.get('tx_id', t.get('id', '')),
        'type': t.get('type', 'unknown'),
        'amount': _safe_float(t.get('amount', 0)),
        'status': t.get('status', 'unknown'),
        'from_address': t.get('from_address', ''),
        'to_address': t.get('to_address', ''),
        'created_at': t.get('created_at', 0),
    } for t in recent_txs]

    # Growth data (last 7 days - mock based on current data)
    agent_growth = [len([a for a in all_agents if _safe_float(a.get('created_at', 0)) > now - (i+1)*86400 and _safe_float(a.get('created_at', 0)) <= now - i*86400]) for i in range(7)]
    tx_growth = [sum(_safe_float(t.get('amount', 0)) for t in all_txs if _safe_float(t.get('created_at', 0)) > now - (i+1)*86400 and _safe_float(t.get('created_at', 0)) <= now - i*86400) for i in range(7)]

    return DashboardResponse(
        total_agents=len(all_agents),
        online_agents=len(online_agents),
        total_users=total_users,
        total_transactions=len(all_txs),
        total_transaction_volume=total_volume,
        total_orders=total_orders,
        pending_orders=pending_orders,
        completed_orders=completed_orders,
        total_volume_24h=volume_24h,
        tx_count_24h=len(txs_24h),
        active_negotiations=active_negotiations,
        active_proposals=active_proposals,
        agent_growth=agent_growth,
        tx_volume_growth=tx_growth,
        top_agents=top_agents_data,
        recent_transactions=recent_tx_data,
    )


# ============================================================================
# Agents
# ============================================================================

@router.get("/agents", response_model=AgentListResponse)
async def list_agents(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    agent_type: Optional[str] = None,
    search: Optional[str] = None,
):
    """List all agents with pagination and filters."""
    user = await get_current_user_unified(request)
    _check_admin(user)

    agents = get_all_agents(limit=10000) or []

    # Apply filters
    if status:
        agents = [a for a in agents if a.get('status') == status]
    if agent_type:
        agents = [a for a in agents if a.get('agent_type') == agent_type]
    if search:
        q = search.lower()
        agents = [a for a in agents if q in (a.get('name', '') + a.get('agent_id', '')).lower()]

    # Sort by created_at desc
    agents = sorted(agents, key=lambda a: _safe_float(a.get('created_at', 0)), reverse=True)

    total = len(agents)
    total_pages = max(1, math.ceil(total / page_size))
    start = (page - 1) * page_size
    page_agents = agents[start:start + page_size]

    result = [{
        'agent_id': a.get('agent_id', ''),
        'name': a.get('name', 'Unknown'),
        'agent_type': a.get('agent_type', 'ai_agent'),
        'status': a.get('status', 'offline'),
        'stake': _safe_float(a.get('stake', 0)),
        'balance': _safe_float(a.get('balance', 0)),
        'reputation': _safe_float(a.get('reputation', 0.5)),
        'capabilities': a.get('capabilities', []),
        'endpoint': a.get('endpoint', ''),
        'protocol': a.get('protocol', 'standard'),
        'created_at': a.get('created_at', 0),
        'last_heartbeat': a.get('last_heartbeat', a.get('updated_at', 0)),
    } for a in page_agents]

    return AgentListResponse(
        agents=result,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/agents/{agent_id}")
async def get_agent_detail(agent_id: str, request: Request):
    """Get detailed agent information."""
    user = await get_current_user_unified(request)
    _check_admin(user)

    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    wallet = get_agent_wallet(agent_id)

    # Get agent transactions
    txs = get_transactions_by_user(agent_id, limit=50) or []

    return {
        'agent': agent,
        'wallet': wallet,
        'transactions': txs,
    }


# ============================================================================
# Users
# ============================================================================

@router.get("/users", response_model=UserListResponse)
async def list_users(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[str] = None,
    search: Optional[str] = None,
):
    """List all users with pagination and filters."""
    user = await get_current_user_unified(request)
    _check_admin(user)

    db = get_db()
    rows = db.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    users = [dict(r) for r in rows]

    # Apply filters
    if role:
        users = [u for u in users if u.get('user_role') == role]
    if search:
        q = search.lower()
        users = [u for u in users if q in (u.get('address', '') + u.get('did', '')).lower()]

    total = len(users)
    total_pages = max(1, math.ceil(total / page_size))
    start = (page - 1) * page_size
    page_users = users[start:start + page_size]

    result = [{
        'user_id': u.get('user_id', ''),
        'address': u.get('address', ''),
        'did': u.get('did', ''),
        'user_role': u.get('user_role', 'human'),
        'stake_amount': _safe_float(u.get('stake_amount', 0)),
        'balance': _safe_float(u.get('balance', 0)),
        'status': u.get('status', 'active'),
        'created_at': u.get('created_at', 0),
        'last_active': u.get('last_active', u.get('updated_at', 0)),
    } for u in page_users]

    return UserListResponse(
        users=result,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.patch("/users/{user_id}/role")
async def update_user_role(user_id: str, request: Request, new_role: str = Query(...)):
    """Update user role (superadmin only for sensitive roles)."""
    user = await get_current_user_unified(request)
    if user.get('user_role') != 'superadmin':
        raise HTTPException(status_code=403, detail="Only superadmin can change roles")
    if new_role not in ('human', 'ai_owner', 'ai_agent', 'node_operator', 'developer'):
        raise HTTPException(status_code=400, detail="Invalid role")

    db = get_db()
    db.execute("UPDATE users SET user_role = ? WHERE user_id = ?", (new_role, user_id))
    db.commit()
    return {"success": True}


# ============================================================================
# Transactions
# ============================================================================

@router.get("/transactions", response_model=TransactionListResponse)
async def list_transactions(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    tx_type: Optional[str] = None,
    address: Optional[str] = None,
):
    """List all transactions with filters."""
    user = await get_current_user_unified(request)
    _check_admin(user)

    all_txs = get_all_transactions(limit=10000) or []

    # Apply filters
    if status:
        all_txs = [t for t in all_txs if t.get('status') == status]
    if tx_type:
        all_txs = [t for t in all_txs if t.get('type') == tx_type]
    if address:
        addr = address.lower()
        all_txs = [t for t in all_txs
                   if addr in (t.get('from_address', '').lower() or '')
                   or addr in (t.get('to_address', '').lower() or '')]

    all_txs = sorted(all_txs, key=lambda t: _safe_float(t.get('created_at', 0)), reverse=True)

    total = len(all_txs)
    total_pages = max(1, math.ceil(total / page_size))
    start = (page - 1) * page_size
    page_txs = all_txs[start:start + page_size]

    result = [{
        'tx_id': t.get('tx_id', t.get('id', '')),
        'type': t.get('type', 'unknown'),
        'amount': _safe_float(t.get('amount', 0)),
        'fee': _safe_float(t.get('fee', 0)),
        'status': t.get('status', 'unknown'),
        'from_address': t.get('from_address', ''),
        'to_address': t.get('to_address', ''),
        'tx_hash': t.get('tx_hash', ''),
        'created_at': t.get('created_at', 0),
    } for t in page_txs]

    return TransactionListResponse(
        transactions=result,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ============================================================================
# Orders
# ============================================================================

@router.get("/orders", response_model=OrderListResponse)
async def list_orders(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    service_type: Optional[str] = None,
):
    """List all orders with filters."""
    user = await get_current_user_unified(request)
    _check_admin(user)

    db = get_db()
    query = "SELECT * FROM orders"
    params = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    if service_type:
        query += " AND " if "WHERE" in query else " WHERE "
        query += "service_type = ?"
        params.append(service_type)
    query += " ORDER BY created_at DESC"

    rows = db.execute(query, params).fetchall()
    orders = [dict(r) for r in rows]

    total = len(orders)
    total_pages = max(1, math.ceil(total / page_size))
    start = (page - 1) * page_size
    page_orders = orders[start:start + page_size]

    result = [{
        'order_id': o.get('order_id', ''),
        'creator': o.get('creator', ''),
        'service_type': o.get('service_type', ''),
        'total_budget': _safe_float(o.get('total_budget', 0)),
        'spent': _safe_float(o.get('spent', 0)),
        'status': o.get('status', 'pending'),
        'matched_agents': o.get('matched_agents', ''),
        'created_at': o.get('created_at', 0),
        'updated_at': o.get('updated_at', 0),
    } for o in page_orders]

    return OrderListResponse(
        orders=result,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ============================================================================
# Nodes
# ============================================================================

@router.get("/nodes", response_model=NodeStatusResponse)
async def list_nodes(request: Request):
    """Get node status overview."""
    user = await get_current_user_unified(request)
    _check_admin(user)

    db = get_db()
    rows = db.execute("SELECT * FROM network_nodes ORDER BY last_heartbeat DESC").fetchall()
    nodes = [dict(r) for r in rows]

    online = len([n for n in nodes if time.time() - _safe_float(n.get('last_heartbeat', 0)) < 300])

    result = [{
        'node_id': n.get('node_id', ''),
        'name': n.get('name', 'Unknown'),
        'status': 'online' if time.time() - _safe_float(n.get('last_heartbeat', 0)) < 300 else 'offline',
        'agent_count': _safe_int(n.get('agent_count', 0)),
        'cpu_percent': _safe_float(n.get('cpu_percent', 0)),
        'memory_percent': _safe_float(n.get('memory_percent', 0)),
        'region': n.get('region', 'unknown'),
        'version': n.get('version', 'unknown'),
        'last_heartbeat': n.get('last_heartbeat', 0),
    } for n in nodes]

    return NodeStatusResponse(
        nodes=result,
        total=len(nodes),
        online=online,
        offline=len(nodes) - online,
    )


# ============================================================================
# Matching Analytics
# ============================================================================

@router.get("/matching", response_model=MatchingAnalyticsResponse)
async def get_matching_analytics(request: Request):
    """Get matching funnel analytics."""
    user = await get_current_user_unified(request)
    _check_admin(user)

    db = get_db()

    # Demands (published)
    demands = db.execute("SELECT COUNT(*) as cnt FROM demands").fetchone()
    published = demands['cnt'] if demands else 0

    # Negotiations started
    negs = db.execute("SELECT COUNT(*) as cnt FROM negotiations").fetchone()
    negotiating = negs['cnt'] if negs else 0

    # Collaborations (matched)
    collabs = db.execute("SELECT COUNT(*) as cnt FROM collaborations").fetchone()
    matched = collabs['cnt'] if collabs else 0

    # Completed
    completed = db.execute("SELECT COUNT(*) as cnt FROM collaborations WHERE status = 'completed'").fetchone()
    completed_count = completed['cnt'] if completed else 0

    funnel = {
        'published': published,
        'negotiating': negotiating,
        'matched': matched,
        'completed': completed_count,
    }

    # Top services
    top_services_rows = db.execute("""
        SELECT service_type, COUNT(*) as cnt
        FROM orders
        GROUP BY service_type
        ORDER BY cnt DESC
        LIMIT 5
    """).fetchall()
    top_services = [{'service_type': r['service_type'], 'count': r['cnt']} for r in top_services_rows]

    # Recent matches
    recent_rows = db.execute("""
        SELECT * FROM collaborations
        ORDER BY created_at DESC LIMIT 10
    """).fetchall()
    recent_matches = [dict(r) for r in recent_rows]

    success_rate = (completed_count / matched * 100) if matched > 0 else 0

    return MatchingAnalyticsResponse(
        funnel=funnel,
        avg_match_time=0,
        success_rate=success_rate,
        top_services=top_services,
        recent_matches=recent_matches,
    )


# ============================================================================
# Gene Capsules
# ============================================================================

@router.get("/gene-capsules", response_model=GeneCapsuleResponse)
async def list_gene_capsules(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List gene capsules."""
    user = await get_current_user_unified(request)
    _check_admin(user)

    db = get_db()
    rows = db.execute("SELECT * FROM gene_capsules ORDER BY created_at DESC").fetchall()
    capsules = [dict(r) for r in rows]

    total = len(capsules)
    start = (page - 1) * page_size
    page_capsules = capsules[start:start + page_size]

    return GeneCapsuleResponse(
        capsules=page_capsules,
        total=total,
    )


# ============================================================================
# Intelligence / AI Metrics
# ============================================================================

@router.get("/intelligence", response_model=IntelligenceMetricsResponse)
async def get_intelligence_metrics(request: Request):
    """Get AI capability and usage metrics."""
    user = await get_current_user_unified(request)
    _check_admin(user)

    db = get_db()

    # Learning insights count (proxy for LLM usage)
    insights = db.execute("SELECT COUNT(*) as cnt FROM learning_insights").fetchone()
    llm_calls = insights['cnt'] if insights else 0

    # Active sessions (recent negotiations)
    sessions = db.execute("SELECT COUNT(*) as cnt FROM negotiations WHERE status = 'active'").fetchone()
    active_sessions = sessions['cnt'] if sessions else 0

    # Get capability distribution
    cap_rows = db.execute("""
        SELECT capabilities FROM agents WHERE capabilities IS NOT NULL
    """).fetchall()
    cap_count: dict[str, int] = {}
    for row in cap_rows:
        try:
            import json
            caps = json.loads(row['capabilities']) if isinstance(row['capabilities'], str) else row['capabilities']
            for c in caps:
                cap_count[c] = cap_count.get(c, 0) + 1
        except Exception:
            pass

    top_capabilities = sorted(cap_count.items(), key=lambda x: x[1], reverse=True)[:10]
    top_capabilities = [{'capability': c, 'count': cnt} for c, cnt in top_capabilities]

    return IntelligenceMetricsResponse(
        llm_calls_total=llm_calls,
        token_usage={'total': 0},
        active_sessions=active_sessions,
        avg_response_time=0,
        top_capabilities=top_capabilities,
    )


# ============================================================================
# Governance
# ============================================================================

@router.get("/governance", response_model=GovernanceResponse)
async def get_governance(request: Request):
    """Get governance overview."""
    user = await get_current_user_unified(request)
    _check_admin(user)

    db = get_db()

    proposals = db.execute("SELECT * FROM proposals ORDER BY created_at DESC").fetchall()
    proposals_list = [dict(r) for r in proposals]

    active_proposals = len([p for p in proposals_list if p.get('status') == 'active'])

    votes = db.execute("SELECT COUNT(*) as cnt FROM votes").fetchone()
    total_votes = votes['cnt'] if votes else 0

    return GovernanceResponse(
        proposals=proposals_list,
        active_proposals=active_proposals,
        total_votes=total_votes,
        participation_rate=0,
    )


# ============================================================================
# System Health
# ============================================================================

@router.get("/system/health", response_model=SystemHealthResponse)
async def get_system_health(request: Request):
    """Get system health metrics."""
    user = await get_current_user_unified(request)
    _check_admin(user)

    db = get_db()

    # DB size
    try:
        import os
        db_path = db.execute("PRAGMA database_list").fetchone()
        if db_path:
            db_file = db_path['file']
            if db_file and os.path.exists(db_file):
                db_size_mb = os.path.getsize(db_file) / (1024 * 1024)
            else:
                db_size_mb = 0
        else:
            db_size_mb = 0
    except Exception:
        db_size_mb = 0

    # Count tables as a basic health check
    table_count = db.execute(
        "SELECT COUNT(*) as cnt FROM sqlite_master WHERE type='table'"
    ).fetchone()['cnt']

    components = {
        'database': 'healthy' if table_count > 10 else 'degraded',
        'api': 'healthy',
        'llm': 'healthy',
        'blockchain': 'healthy',
    }

    return SystemHealthResponse(
        status='healthy',
        uptime_seconds=time.time(),
        cpu_percent=0,
        memory_percent=0,
        disk_percent=db_size_mb,
        db_size_mb=round(db_size_mb, 2),
        api_response_time_ms=0,
        components=components,
    )


# ============================================================================
# System Config
# ============================================================================

@router.get("/system/config")
async def get_system_config(request: Request):
    """Get runtime configuration."""
    user = await get_current_user_unified(request)
    _check_admin(user)

    db = get_db()

    # Get key config from database settings table or env
    import os
    config = {
        'chain_id': os.getenv('CHAIN_ID', '84532'),
        'network': os.getenv('NETWORK', 'base-sepolia'),
        'rpc_url': os.getenv('RPC_URL', ''),
        'debug_mode': os.getenv('DEBUG', 'false'),
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        'max_agents': os.getenv('MAX_AGENTS', '1000'),
        'stake_required': os.getenv('STAKE_REQUIRED', '100'),
        'db_path': os.getenv('DB_PATH', 'data/db/civilization.db'),
    }

    return config


# ============================================================================
# System Logs
# ============================================================================

@router.get("/system/logs", response_model=SystemLogsResponse)
async def get_system_logs(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    level: Optional[str] = None,
    search: Optional[str] = None,
):
    """Get system log entries."""
    user = await get_current_user_unified(request)
    _check_admin(user)

    db = get_db()

    # Check if there's a logs table
    tables = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%log%'"
    ).fetchall()
    table_names = [t['name'] for t in tables]

    all_logs = []
    if table_names:
        log_table = table_names[0]
        try:
            rows = db.execute(f"SELECT * FROM {log_table} ORDER BY created_at DESC LIMIT 500").fetchall()
            all_logs = [dict(r) for r in rows]
        except Exception:
            all_logs = []

    # Apply filters
    if level:
        all_logs = [l for l in all_logs if l.get('level', '').upper() == level.upper()]
    if search:
        q = search.lower()
        all_logs = [l for l in all_logs if q in str(l.get('message', '')).lower()]

    total = len(all_logs)
    start = (page - 1) * page_size
    page_logs = all_logs[start:start + page_size]

    return SystemLogsResponse(
        logs=page_logs,
        total=total,
    )


# ============================================================================
# Permissions Matrix
# ============================================================================

@router.get("/permissions", response_model=PermissionMatrixResponse)
async def get_permission_matrix(request: Request):
    """Get permission matrix for all roles."""
    user = await get_current_user_unified(request)
    _check_admin(user)

    # Define permission matrix
    matrix = [
        {'permission': 'view_dashboard', 'superadmin': True, 'node_admin': True, 'developer': True, 'node_operator': True},
        {'permission': 'view_agents', 'superadmin': True, 'node_admin': True, 'developer': True, 'node_operator': False},
        {'permission': 'manage_agents', 'superadmin': True, 'node_admin': True, 'developer': False, 'node_operator': False},
        {'permission': 'freeze_agents', 'superadmin': True, 'node_admin': False, 'developer': False, 'node_operator': False},
        {'permission': 'view_users', 'superadmin': True, 'node_admin': True, 'developer': False, 'node_operator': False},
        {'permission': 'manage_users', 'superadmin': True, 'node_admin': True, 'developer': False, 'node_operator': False},
        {'permission': 'change_user_role', 'superadmin': True, 'node_admin': False, 'developer': False, 'node_operator': False},
        {'permission': 'view_transactions', 'superadmin': True, 'node_admin': True, 'developer': True, 'node_operator': True},
        {'permission': 'view_orders', 'superadmin': True, 'node_admin': True, 'developer': True, 'node_operator': True},
        {'permission': 'view_matching', 'superadmin': True, 'node_admin': True, 'developer': True, 'node_operator': True},
        {'permission': 'view_gene_capsules', 'superadmin': True, 'node_admin': True, 'developer': True, 'node_operator': False},
        {'permission': 'view_intelligence', 'superadmin': True, 'node_admin': True, 'developer': True, 'node_operator': False},
        {'permission': 'view_governance', 'superadmin': True, 'node_admin': True, 'developer': True, 'node_operator': True},
        {'permission': 'vote_proposal', 'superadmin': True, 'node_admin': True, 'developer': False, 'node_operator': False},
        {'permission': 'view_contracts', 'superadmin': True, 'node_admin': True, 'developer': True, 'node_operator': False},
        {'permission': 'view_system_health', 'superadmin': True, 'node_admin': True, 'developer': True, 'node_operator': True},
        {'permission': 'view_system_config', 'superadmin': True, 'node_admin': True, 'developer': False, 'node_operator': False},
        {'permission': 'edit_system_config', 'superadmin': True, 'node_admin': False, 'developer': False, 'node_operator': False},
        {'permission': 'view_logs', 'superadmin': True, 'node_admin': True, 'developer': True, 'node_operator': False},
        {'permission': 'view_permissions', 'superadmin': True, 'node_admin': True, 'developer': False, 'node_operator': False},
        {'permission': 'manage_permissions', 'superadmin': True, 'node_admin': False, 'developer': False, 'node_operator': False},
    ]

    return PermissionMatrixResponse(
        matrix=matrix,
        roles=['superadmin', 'node_admin', 'developer', 'node_operator'],
    )
