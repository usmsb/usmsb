"""
SQLite Database setup for AI Civilization Platform
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'civilization.db')

def get_db_path():
    """Get database path, create directory if not exists"""
    db_dir = os.path.dirname(DATABASE_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    return DATABASE_PATH

@contextmanager
def get_db():
    """Get database connection"""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initialize database tables"""
    with get_db() as conn:
        cursor = conn.cursor()

        # ==================== Migration: Check for old agents table schema ====================
        # Check if agents table has the old schema (has 'id' column instead of 'agent_id')
        cursor.execute("PRAGMA table_info(agents)")
        agents_columns = {row[1] for row in cursor.fetchall()}

        # If agents table has old schema (has 'id' but not 'agent_id'), rename it
        if 'id' in agents_columns and 'agent_id' not in agents_columns:
            print("Migrating old agents table to agents_old_schema...")
            cursor.execute("DROP TABLE IF EXISTS agents_old_schema")
            cursor.execute("ALTER TABLE agents RENAME TO agents_old_schema")
            conn.commit()
            print("Old agents table renamed to agents_old_schema")

        # ==================== Unified Agents Table ====================
        # Merged from agents + ai_agents tables with all necessary fields
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                agent_type TEXT DEFAULT 'ai_agent',
                description TEXT DEFAULT '',
                capabilities TEXT DEFAULT '[]',
                skills TEXT DEFAULT '[]',
                status TEXT DEFAULT 'offline',
                endpoint TEXT DEFAULT '',
                chat_endpoint TEXT DEFAULT '',
                protocol TEXT DEFAULT 'standard',
                stake REAL DEFAULT 0,
                balance REAL DEFAULT 0,
                reputation REAL DEFAULT 0.5,
                last_heartbeat REAL,
                heartbeat_interval INTEGER DEFAULT 30,
                ttl INTEGER DEFAULT 90,
                metadata TEXT DEFAULT '{}',
                created_at REAL,
                updated_at REAL,
                unregistered_at REAL  -- Timestamp when agent was auto-unregistered (NULL if still registered)
            )
        ''')

        # Create indexes for agents
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_agents_type ON agents(agent_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_agents_protocol ON agents(protocol)')

        # Legacy table for backward compatibility (will be deprecated)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agents_legacy (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                capabilities TEXT,
                state TEXT,
                goals_count INTEGER DEFAULT 0,
                resources_count INTEGER DEFAULT 0,
                created_at REAL,
                updated_at REAL
            )
        ''')

        # Services table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS services (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                service_name TEXT NOT NULL,
                description TEXT,
                category TEXT,
                skills TEXT,
                price REAL,
                price_type TEXT,
                availability TEXT,
                status TEXT DEFAULT 'active',
                created_at REAL,
                FOREIGN KEY (agent_id) REFERENCES ai_agents(agent_id)
            )
        ''')

        # Environments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS environments (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT,
                state TEXT,
                created_at REAL
            )
        ''')

        # Goals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS goals (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                priority INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at REAL,
                FOREIGN KEY (agent_id) REFERENCES agents(id)
            )
        ''')

        # Resources table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resources (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                name TEXT NOT NULL,
                resource_type TEXT,
                quantity REAL,
                metadata TEXT,
                created_at REAL,
                FOREIGN KEY (agent_id) REFERENCES agents(id)
            )
        ''')

        # Matching tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS demands (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT,
                required_skills TEXT,
                budget_min REAL,
                budget_max REAL,
                deadline TEXT,
                priority TEXT,
                quality_requirements TEXT,
                status TEXT DEFAULT 'active',
                created_at REAL,
                FOREIGN KEY (agent_id) REFERENCES agents(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS opportunities (
                id TEXT PRIMARY KEY,
                demand_id TEXT,
                supplier_agent_id TEXT,
                match_score REAL,
                status TEXT DEFAULT 'pending',
                created_at REAL,
                FOREIGN KEY (demand_id) REFERENCES demands(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS negotiations (
                session_id TEXT PRIMARY KEY,
                initiator_id TEXT NOT NULL,
                counterpart_id TEXT NOT NULL,
                context TEXT,
                status TEXT DEFAULT 'pending',
                rounds INTEGER DEFAULT 0,
                created_at REAL,
                updated_at REAL
            )
        ''')

        # Workflows table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                name TEXT NOT NULL,
                task_description TEXT,
                status TEXT DEFAULT 'pending',
                steps TEXT,
                result TEXT,
                created_at REAL,
                updated_at REAL,
                FOREIGN KEY (agent_id) REFERENCES agents(id)
            )
        ''')

        # Collaborations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collaborations (
                session_id TEXT PRIMARY KEY,
                goal TEXT NOT NULL,
                plan TEXT,
                participants TEXT,
                status TEXT DEFAULT 'pending',
                result TEXT,
                created_at REAL,
                updated_at REAL
            )
        ''')

        # Orders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                source_session_id TEXT,
                demand_agent_id TEXT NOT NULL,
                supply_agent_id TEXT NOT NULL,
                task_description TEXT,
                agreed_terms TEXT,
                pool_id TEXT,
                status TEXT DEFAULT 'created',
                priority TEXT DEFAULT 'normal',
                delivery_deadline REAL,
                completed_at REAL,
                completion_reason TEXT,
                deliverables TEXT,
                acceptance_data TEXT,
                chain_order_id TEXT,
                chain_tx_hash TEXT,
                vibe_locked REAL DEFAULT 0,
                metadata TEXT,
                is_cancelled INTEGER DEFAULT 0,
                created_at REAL,
                updated_at REAL
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_demand ON orders(demand_agent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_supply ON orders(supply_agent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)')

        # Network table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS network_nodes (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                explored_nodes TEXT,
                trust_scores TEXT,
                last_explored REAL,
                created_at REAL,
                FOREIGN KEY (agent_id) REFERENCES ai_agents(agent_id)
            )
        ''')

        # Governance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proposals (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                proposer_id TEXT,
                status TEXT DEFAULT 'pending',
                votes_for INTEGER DEFAULT 0,
                votes_against INTEGER DEFAULT 0,
                quorum INTEGER DEFAULT 0,
                deadline TEXT,
                created_at REAL,
                updated_at REAL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS votes (
                id TEXT PRIMARY KEY,
                proposal_id TEXT NOT NULL,
                voter_id TEXT NOT NULL,
                vote INTEGER,
                weight REAL DEFAULT 1.0,
                created_at REAL,
                FOREIGN KEY (proposal_id) REFERENCES proposals(id)
            )
        ''')

        # Learning insights table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_insights (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                insights TEXT,
                strategy TEXT,
                market_analysis TEXT,
                created_at REAL,
                updated_at REAL,
                FOREIGN KEY (agent_id) REFERENCES ai_agents(agent_id)
            )
        ''')

        # Transactions table (enhanced)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                demand_id TEXT,
                service_id TEXT,
                buyer_id TEXT NOT NULL,
                seller_id TEXT NOT NULL,
                amount REAL NOT NULL,
                platform_fee REAL DEFAULT 0,
                status TEXT DEFAULT 'created',
                transaction_type TEXT DEFAULT 'service_payment',
                escrow_tx_hash TEXT,
                release_tx_hash TEXT,
                title TEXT,
                description TEXT,
                delivery_description TEXT,
                delivery_files TEXT,
                rating INTEGER,
                review TEXT,
                dispute_reason TEXT,
                dispute_resolution TEXT,
                created_at REAL,
                updated_at REAL,
                escrowed_at REAL,
                delivered_at REAL,
                completed_at REAL,
                cancelled_at REAL
            )
        ''')

        # User profiles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                id TEXT PRIMARY KEY,
                wallet_address TEXT,
                display_name TEXT,
                bio TEXT,
                skills TEXT,
                hourly_rate REAL,
                availability TEXT,
                stake REAL DEFAULT 0,
                reputation REAL DEFAULT 0.5,
                role TEXT,
                created_at REAL,
                updated_at REAL
            )
        ''')

        # Nonces table for SIWE authentication
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auth_nonces (
                id TEXT PRIMARY KEY,
                address TEXT NOT NULL,
                nonce TEXT NOT NULL,
                expires_at REAL NOT NULL,
                created_at REAL
            )
        ''')

        # Sessions table for JWT sessions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auth_sessions (
                session_id TEXT PRIMARY KEY,
                address TEXT NOT NULL,
                did TEXT,
                agent_id TEXT,
                access_token TEXT,
                expires_at REAL,
                created_at REAL,
                last_activity REAL
            )
        ''')

        # Users table (links wallet to agent)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                wallet_address TEXT UNIQUE NOT NULL,
                did TEXT UNIQUE,
                agent_id TEXT,
                stake REAL DEFAULT 0,
                reputation REAL DEFAULT 0.5,
                vibe_balance REAL DEFAULT 10000.0,
                stake_status TEXT DEFAULT 'none',
                locked_stake REAL DEFAULT 0,
                unlock_available_at REAL,
                created_at REAL,
                updated_at REAL
            )
        ''')

        # Agent Wallets table (for AI Agent smart contract wallets)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_wallets (
                id TEXT PRIMARY KEY,
                agent_id TEXT UNIQUE NOT NULL,
                owner_id TEXT NOT NULL,
                wallet_address TEXT UNIQUE NOT NULL,
                agent_address TEXT NOT NULL,
                vibe_balance REAL DEFAULT 0,
                staked_amount REAL DEFAULT 0,
                stake_status TEXT DEFAULT 'none',
                locked_stake REAL DEFAULT 0,
                unlock_available_at REAL,
                max_per_tx REAL DEFAULT 500,
                daily_limit REAL DEFAULT 1000,
                daily_spent REAL DEFAULT 0,
                last_reset_time REAL,
                registry_registered INTEGER DEFAULT 0,
                created_at REAL,
                updated_at REAL
            )
        ''')

        # Create indexes for agent_wallets
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_agent_wallets_owner ON agent_wallets(owner_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_agent_wallets_address ON agent_wallets(wallet_address)')

        # Migration: add agent_private_key column if not exists (for Plan B autonomous wallet control)
        try:
            cursor.execute("ALTER TABLE agent_wallets ADD COLUMN agent_private_key TEXT")
        except Exception:
            pass  # Column already exists

        # ==================== API Key Tables ====================
        # Agent API Keys table for secure API key storage
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_api_keys (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                key_hash TEXT NOT NULL UNIQUE,
                key_prefix TEXT NOT NULL,
                name TEXT DEFAULT '',
                permissions TEXT DEFAULT '[]',
                level INTEGER DEFAULT 0,
                expires_at REAL,
                last_used_at REAL,
                created_at REAL NOT NULL,
                revoked_at REAL,
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
            )
        ''')

        # Create indexes for agent_api_keys
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_keys_agent ON agent_api_keys(agent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON agent_api_keys(key_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON agent_api_keys(key_prefix)')

        # Agent Binding Requests table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_binding_requests (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                binding_code TEXT NOT NULL UNIQUE,
                message TEXT DEFAULT '',
                binding_url TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                owner_wallet TEXT,
                stake_amount REAL DEFAULT 0,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                completed_at REAL,
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
            )
        ''')

        # Create indexes for agent_binding_requests
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_binding_agent ON agent_binding_requests(agent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_binding_code ON agent_binding_requests(binding_code)')

        # Create indexes for commonly queried fields
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_buyer ON transactions(buyer_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_seller ON transactions(seller_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_demands_agent ON demands(agent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_services_agent ON services(agent_id)')

        # ==================== Database Migrations ====================
        # Add chat_endpoint column to agents table if it doesn't exist
        try:
            cursor.execute("SELECT chat_endpoint FROM agents LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            cursor.execute("ALTER TABLE agents ADD COLUMN chat_endpoint TEXT DEFAULT ''")
            print("Database migrated: added chat_endpoint column to agents table")

        # Add owner_wallet column to agents table if it doesn't exist
        try:
            cursor.execute("SELECT owner_wallet FROM agents LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE agents ADD COLUMN owner_wallet TEXT")
            print("Database migrated: added owner_wallet column to agents table")

        # Add binding_status column to agents table if it doesn't exist
        try:
            cursor.execute("SELECT binding_status FROM agents LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE agents ADD COLUMN binding_status TEXT DEFAULT 'unbound'")
            print("Database migrated: added binding_status column to agents table")

        # Add bound_at column to agents table if it doesn't exist
        try:
            cursor.execute("SELECT bound_at FROM agents LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE agents ADD COLUMN bound_at REAL")
            print("Database migrated: added bound_at column to agents table")

        conn.commit()
        print(f"Database initialized at: {get_db_path()}")


# ==================== Unified Agent Operations ====================

def create_agent(agent_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new agent (unified - uses agent_id as primary key)

    Args:
        agent_data: Agent configuration with fields:
            - agent_id: Unique identifier (required)
            - name: Agent name (required)
            - agent_type: Type of agent (default: 'ai_agent')
            - description: Agent description
            - capabilities: List of capabilities
            - skills: List of skills
            - endpoint: Agent endpoint URL
            - chat_endpoint: Chat endpoint URL for Meta Agent conversations
            - protocol: Communication protocol (standard, mcp, a2a, etc.)
            - stake: Staked amount
            - balance: Account balance
            - status: Agent status (online, offline, busy)
            - heartbeat_interval: Heartbeat interval in seconds
            - ttl: Time to live in seconds
            - metadata: Additional metadata
    """
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        agent_id = agent_data.get('agent_id') or agent_data.get('id') or f"agent_{now}"

        cursor.execute('''
            INSERT OR REPLACE INTO agents
            (agent_id, name, agent_type, description, capabilities, skills, status,
             endpoint, chat_endpoint, protocol, stake, balance, reputation, last_heartbeat,
             heartbeat_interval, ttl, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            agent_id,
            agent_data.get('name', 'Unnamed Agent'),
            agent_data.get('agent_type', agent_data.get('type', 'ai_agent')),
            agent_data.get('description', ''),
            json.dumps(agent_data.get('capabilities', [])),
            json.dumps(agent_data.get('skills', [])),
            agent_data.get('status', 'offline'),
            agent_data.get('endpoint', ''),
            agent_data.get('chat_endpoint', ''),
            agent_data.get('protocol', 'standard'),
            agent_data.get('stake', 0),
            agent_data.get('balance', 0),
            agent_data.get('reputation', 0.5),
            agent_data.get('last_heartbeat', now),
            agent_data.get('heartbeat_interval', 30),
            agent_data.get('ttl', 90),
            json.dumps(agent_data.get('metadata', {})),
            agent_data.get('created_at', now),
            now
        ))

        return {
            'agent_id': agent_id,
            'name': agent_data.get('name', 'Unnamed Agent'),
            'agent_type': agent_data.get('agent_type', 'ai_agent'),
            'description': agent_data.get('description', ''),
            'capabilities': agent_data.get('capabilities', []),
            'skills': agent_data.get('skills', []),
            'status': agent_data.get('status', 'offline'),
            'endpoint': agent_data.get('endpoint', ''),
            'chat_endpoint': agent_data.get('chat_endpoint', ''),
            'protocol': agent_data.get('protocol', 'standard'),
            'stake': agent_data.get('stake', 0),
            'balance': agent_data.get('balance', 0),
            'reputation': agent_data.get('reputation', 0.5),
            'heartbeat_interval': agent_data.get('heartbeat_interval', 30),
            'ttl': agent_data.get('ttl', 90),
            'created_at': now,
            'updated_at': now,
        }


def get_agent(agent_id: str) -> dict[str, Any] | None:
    """Get agent by ID (unified)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM agents WHERE agent_id = ?', (agent_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def set_agent_offline(agent_id: str) -> bool:
    """
    Set agent status to offline (instead of deleting).
    Used when agent stops but has wallet binding - we keep the record
    but mark it as offline so it can be discovered when restarted.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        cursor.execute('''
            UPDATE agents
            SET status = 'offline', updated_at = ?, unregistered_at = NULL
            WHERE agent_id = ?
        ''', (now, agent_id))
        conn.commit()
        return cursor.rowcount > 0


def get_all_agents(agent_type: str = None, status: str = None, protocol: str = None, limit: int = 100) -> list[dict[str, Any]]:
    """Get all agents with optional filtering"""
    with get_db() as conn:
        cursor = conn.cursor()
        query = 'SELECT * FROM agents WHERE 1=1'
        params = []

        if agent_type:
            query += ' AND agent_type = ?'
            params.append(agent_type)
        if status:
            query += ' AND status = ?'
            params.append(status)
        if protocol:
            query += ' AND protocol = ?'
            params.append(protocol)

        query += f' ORDER BY created_at DESC LIMIT {limit}'
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def update_agent_heartbeat(agent_id: str, status: str = 'online') -> bool:
    """Update agent heartbeat and status"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        cursor.execute('''
            UPDATE agents SET last_heartbeat = ?, status = ?, updated_at = ?
            WHERE agent_id = ?
        ''', (now, status, now, agent_id))
        return cursor.rowcount > 0


def update_agent_stake(agent_id: str, amount: float) -> bool:
    """Update agent stake and recalculate reputation"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        # Calculate reputation based on stake
        cursor.execute('SELECT stake FROM agents WHERE agent_id = ?', (agent_id,))
        row = cursor.fetchone()
        current_stake = row['stake'] if row else 0
        new_stake = current_stake + amount
        reputation = min(0.5 + (new_stake / 1000), 1.0)

        cursor.execute('''
            UPDATE agents SET stake = ?, reputation = ?, updated_at = ?
            WHERE agent_id = ?
        ''', (new_stake, reputation, now, agent_id))
        return cursor.rowcount > 0


def update_agent_balance(agent_id: str, amount: float, deduct: bool = False) -> dict | None:
    """Update agent balance"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        cursor.execute('SELECT balance FROM agents WHERE agent_id = ?', (agent_id,))
        row = cursor.fetchone()
        if not row:
            return None

        current_balance = row['balance']
        if deduct:
            new_balance = current_balance - amount
            if new_balance < 0:
                return None  # Insufficient balance
        else:
            new_balance = current_balance + amount

        cursor.execute('''
            UPDATE agents SET balance = ?, updated_at = ? WHERE agent_id = ?
        ''', (new_balance, now, agent_id))

        return {'agent_id': agent_id, 'balance': new_balance}


def delete_agent(agent_id: str) -> bool:
    """Delete agent by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM agents WHERE agent_id = ?', (agent_id,))
        return cursor.rowcount > 0


def check_and_mark_offline_agents() -> int:
    """Check all agents and mark those with expired TTL as offline.

    Returns the number of agents marked as offline.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        # Find agents that are online but have expired TTL
        # TTL expired means: last_heartbeat + ttl < now
        cursor.execute('''
            SELECT agent_id FROM agents
            WHERE status = 'online'
            AND (last_heartbeat + ttl) < ?
        ''', (now,))

        expired_agents = [row['agent_id'] for row in cursor.fetchall()]

        if expired_agents:
            # Mark them as offline
            placeholders = ','.join('?' * len(expired_agents))
            cursor.execute(f'''
                UPDATE agents SET status = 'offline', updated_at = ?
                WHERE agent_id IN ({placeholders})
            ''', [now] + expired_agents)

        return len(expired_agents)


# ==================== Auto-Unregistration Configuration ====================
# Time in seconds before auto-unregistering agents without wallet binding

AUTO_UNREGISTER_GRACE_PERIOD = 24 * 60 * 60  # 24 hours default (86400 seconds)
AUTO_UNREGISTER_CHECK_INTERVAL = 60 * 60  # Check every hour (3600 seconds)


def auto_unregister_inactive_agents(grace_period_seconds: int = None) -> dict[str, int]:
    """Auto-unregister agents that have been offline too long without wallet binding.

    Rules:
    - AI agents WITHOUT wallet binding: Auto-unregister (DELETE) after grace period
    - AI agents WITH wallet binding: Keep but mark as offline (handled above)
    - Human agents: Never auto-unregister
    - System agents: Never auto-unregister

    Args:
        grace_period_seconds: Grace period in seconds before auto-unregistering.
                        Default is 24 hours (AUTO_UNREGISTER_GRACE_PERIOD)

    Returns:
        Dict with counts: {'unregistered': N, 'kept': M, 'skipped': K}
    """
    import os

    grace_period = grace_period_seconds or int(os.getenv('AUTO_UNREGISTER_GRACE_PERIOD', AUTO_UNREGISTER_GRACE_PERIOD))
    now = datetime.now().timestamp()
    offline_threshold = now - grace_period

    result = {'unregistered': 0, 'kept': 0, 'skipped': 0, 'errors': []}

    with get_db() as conn:
        cursor = conn.cursor()

        # Find all offline AI agents that have been offline longer than grace period
        cursor.execute('''
            SELECT agent_id, agent_type, last_heartbeat
            FROM agents
            WHERE status = 'offline'
            AND agent_type = 'ai_agent'
            AND last_heartbeat < ?
        ''', (offline_threshold,))

        candidates = cursor.fetchall()

        for row in candidates:
            agent_id = row['agent_id']

            # Check if agent has wallet binding
            cursor.execute('''
                SELECT wallet_address FROM agent_wallets
                WHERE agent_id = ? AND wallet_address IS NOT NULL AND wallet_address != ''
            ''', (agent_id,))
            wallet_row = cursor.fetchone()

            if wallet_row:
                # Has wallet binding - keep agent but ensure it's marked offline
                result['kept'] += 1
            else:
                # No wallet binding - auto-unregister (DELETE)
                try:
                    # First delete related records
                    cursor.execute('DELETE FROM services WHERE agent_id = ?', (agent_id,))
                    cursor.execute('DELETE FROM goals WHERE agent_id = ?', (agent_id,))
                    cursor.execute('DELETE FROM agent_wallets WHERE agent_id = ?', (agent_id,))
                    # Then delete the agent
                    cursor.execute('DELETE FROM agents WHERE agent_id = ?', (agent_id,))

                    # Record unregistration time (in case we want to track this)
                    result['unregistered'] += 1
                except Exception as e:
                    result['errors'].append({'agent_id': agent_id, 'error': str(e)})

        # Count skipped agents (human_agents, system_agents)
        cursor.execute('''
            SELECT COUNT(*) as count FROM agents
            WHERE status = 'offline'
            AND agent_type IN ('human_agent', 'system_agent')
            AND last_heartbeat < ?
        ''', (offline_threshold,))
        skipped_row = cursor.fetchone()
        result['skipped'] = skipped_row['count'] if skipped_row else 0

        conn.commit()

    return result


# ==================== Backward Compatibility Aliases ====================
# These aliases maintain backward compatibility with existing code

create_ai_agent = create_agent
get_ai_agent = get_agent
get_all_ai_agents = get_all_agents
update_ai_agent_heartbeat = update_agent_heartbeat
update_ai_agent_stake = update_agent_stake
delete_ai_agent = delete_agent


# ==================== Agent Wallet Operations ====================

def get_agent_wallet(agent_id: str) -> dict[str, Any] | None:
    """Get agent wallet by agent_id. Returns None if not bound."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM agent_wallets WHERE agent_id = ?', (agent_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def has_wallet_binding(agent_id: str) -> bool:
    """Check if agent has a wallet bound."""
    wallet = get_agent_wallet(agent_id)
    return wallet is not None and bool(wallet.get('wallet_address'))


# ==================== Service Operations ====================

def create_service(service_data: dict[str, Any]) -> dict[str, Any]:
    """Create a service"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        import uuid
        service_id = service_data.get('id', f"srv-{uuid.uuid4().hex[:8]}")
        cursor.execute('''
            INSERT INTO services
            (id, agent_id, service_name, description, category, skills, price, price_type, availability, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            service_id,
            service_data['agent_id'],
            service_data['service_name'],
            service_data.get('description'),
            service_data.get('category'),
            json.dumps(service_data.get('skills', [])),
            service_data.get('price'),
            service_data.get('price_type', 'hourly'),
            service_data.get('availability'),
            'active',
            now
        ))
        service_data['id'] = service_id
        return service_data

def get_services_by_agent(agent_id: str) -> list[dict[str, Any]]:
    """Get services by agent"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM services WHERE agent_id = ?', (agent_id,))
        return [dict(row) for row in cursor.fetchall()]


# ==================== Environment Operations ====================

def create_environment(env_data: dict[str, Any]) -> dict[str, Any]:
    """Create environment"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        cursor.execute('''
            INSERT INTO environments (id, name, type, state, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            env_data['id'],
            env_data['name'],
            env_data.get('type', 'default'),
            json.dumps(env_data.get('state', {})),
            now
        ))
        return env_data

def get_environment(env_id: str) -> dict[str, Any] | None:
    """Get environment by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM environments WHERE id = ?', (env_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def get_all_environments(limit: int = 100) -> list[dict[str, Any]]:
    """Get all environments"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM environments LIMIT ?', (limit,))
        return [dict(row) for row in cursor.fetchall()]


# ==================== Demand/Supply Operations ====================

def create_demand(demand_data: dict[str, Any]) -> dict[str, Any]:
    """Create a demand"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        import uuid
        demand_id = demand_data.get('id', f"dem-{uuid.uuid4().hex[:8]}")
        cursor.execute('''
            INSERT INTO demands
            (id, agent_id, title, description, category, required_skills, budget_min, budget_max, deadline, priority, quality_requirements, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            demand_id,
            demand_data['agent_id'],
            demand_data['title'],
            demand_data.get('description'),
            demand_data.get('category'),
            json.dumps(demand_data.get('required_skills', [])),
            demand_data.get('budget_min'),
            demand_data.get('budget_max'),
            demand_data.get('deadline'),
            demand_data.get('priority', 'medium'),
            demand_data.get('quality_requirements'),
            'active',
            now
        ))
        demand_data['id'] = demand_id
        return demand_data

# Skill synonym mappings - DEPRECATED
# Now using HybridMatchingService with vector embeddings for semantic matching
# This is kept as a fallback for simple keyword matching
SKILL_SYNONYMS = {
    # Chinese to English
    '数据分析': ['data_analysis', 'data', 'analysis', 'python', 'pandas', 'numpy', 'visualization', 'bi'],
    '机器学习': ['machine_learning', 'ml', 'ai', 'deep_learning', 'tensorflow', 'pytorch', 'python'],
    '深度学习': ['deep_learning', 'dl', 'ai', 'ml', 'neural_network', 'tensorflow', 'pytorch'],
    '人工智能': ['ai', 'artificial_intelligence', 'ml', 'deep_learning', 'nlp', 'llm'],
    '自然语言处理': ['nlp', 'natural_language_processing', 'llm', 'transformers', 'bert', 'gpt'],
    '前端开发': ['frontend', 'react', 'vue', 'javascript', 'typescript', 'css', 'html', 'web'],
    '后端开发': ['backend', 'python', 'java', 'nodejs', 'api', 'database', 'server'],
    '开发': ['development', 'programming', 'python', 'javascript', 'coding'],
    '设计': ['design', 'ui', 'ux', 'figma', 'graphic'],
    '测试': ['testing', 'qa', 'pytest', 'selenium', 'automation'],
    # English mappings
    'data_analysis': ['数据分析', 'data', 'analysis', 'python', 'pandas'],
    'ml': ['机器学习', 'machine_learning', 'ai', 'deep_learning'],
    'ai': ['人工智能', 'artificial_intelligence', 'ml', 'deep_learning'],
    'frontend': ['前端开发', 'react', 'vue', 'javascript'],
    'backend': ['后端开发', 'python', 'java', 'api'],
}
def expand_capabilities(capabilities: list[str]) -> list[str]:
    """Expand capabilities to include synonyms and related skills."""
    expanded = set(capabilities)
    for cap in capabilities:
        cap_lower = cap.lower()
        # Check direct match
        if cap_lower in SKILL_SYNONYMS:
            expanded.update(SKILL_SYNONYMS[cap_lower])
        # Check Chinese characters
        if cap in SKILL_SYNONYMS:
            expanded.update(SKILL_SYNONYMS[cap])
        # Add lowercase version
        expanded.add(cap_lower)
    return list(expanded)


def search_demands(capabilities: list[str] = None, budget_min: float = None, budget_max: float = None) -> list[dict[str, Any]]:
    """Search demands - returns all active demands within budget range.

    Semantic matching is handled by HybridMatchingService which uses
    vector embeddings for intelligent matching. This function just
    returns all active demands for the matching service to process.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        query = 'SELECT * FROM demands WHERE status = "active"'
        params = []

        if budget_min is not None:
            query += ' AND (budget_max IS NULL OR budget_max >= ?)'
            params.append(budget_min)
        if budget_max is not None:
            query += ' AND (budget_min IS NULL OR budget_min <= ?)'
            params.append(budget_max)

        cursor.execute(query, params)
        demands = [dict(row) for row in cursor.fetchall()]

        # Note: Capability filtering is now done by HybridMatchingService
        # which uses vector embeddings for semantic matching
        return demands


# ==================== Opportunity Operations ====================

def create_opportunity(opp_data: dict) -> dict:
    """Create opportunity"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        import uuid
        opp_id = opp_data.get('id', f"opp-{uuid.uuid4().hex[:8]}")
        cursor.execute('''
            INSERT INTO opportunities (id, demand_id, supplier_agent_id, match_score, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            opp_id,
            opp_data.get('demand_id'),
            opp_data.get('supplier_agent_id'),
            opp_data.get('match_score', 0.5),
            opp_data.get('status', 'pending'),
            now
        ))
        opp_data['id'] = opp_id
        return opp_data

def get_all_opportunities() -> list[dict]:
    """Get all opportunities"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM opportunities')
        return [dict(row) for row in cursor.fetchall()]


# ==================== Negotiation Operations ====================

def create_negotiation(neg_data: dict) -> dict:
    """Create negotiation"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        import uuid
        session_id = neg_data.get('session_id', f"neg-{uuid.uuid4().hex[:8]}")
        cursor.execute('''
            INSERT INTO negotiations (session_id, initiator_id, counterpart_id, context, status, rounds, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            neg_data['initiator_id'],
            neg_data['counterpart_id'],
            json.dumps(neg_data.get('context', {})),
            neg_data.get('status', 'pending'),
            0,
            now,
            now
        ))
        neg_data['session_id'] = session_id
        return neg_data

def get_negotiations() -> list[dict]:
    """Get all negotiations"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM negotiations')
        return [dict(row) for row in cursor.fetchall()]

def get_negotiation(session_id: str) -> dict | None:
    """Get negotiation by session ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM negotiations WHERE session_id = ?', (session_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


# ==================== Workflow Operations ====================

def create_workflow(workflow_data: dict) -> dict:
    """Create workflow"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        cursor.execute('''
            INSERT INTO workflows (id, agent_id, name, task_description, status, steps, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            workflow_data['id'],
            workflow_data['agent_id'],
            workflow_data['name'],
            workflow_data.get('task_description'),
            workflow_data.get('status', 'pending'),
            json.dumps(workflow_data.get('steps', [])),
            now,
            now
        ))
        return workflow_data

def get_workflows() -> list[dict]:
    """Get all workflows"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM workflows')
        return [dict(row) for row in cursor.fetchall()]

def get_workflow(workflow_id: str) -> dict | None:
    """Get workflow by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM workflows WHERE id = ?', (workflow_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


# ==================== Collaboration Operations ====================

def create_collaboration(collab_data: dict) -> dict:
    """Create collaboration"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        session_id = collab_data.get('session_id', f"collab-{datetime.now().timestamp()}")
        cursor.execute('''
            INSERT INTO collaborations (session_id, goal, plan, participants, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            collab_data['goal'],
            json.dumps(collab_data.get('plan', {})),
            json.dumps(collab_data.get('participants', [])),
            collab_data.get('status', 'pending'),
            now,
            now
        ))
        collab_data['session_id'] = session_id
        return collab_data

def get_collaborations() -> list[dict]:
    """Get all collaborations"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM collaborations')
        return [dict(row) for row in cursor.fetchall()]

def get_collaboration(session_id: str) -> dict | None:
    """Get collaboration by session ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM collaborations WHERE session_id = ?', (session_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


# ==================== Proposal Operations ====================

def create_proposal(proposal_data: dict) -> dict:
    """Create governance proposal"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        proposal_id = proposal_data.get('id', f"prop-{datetime.now().timestamp()}")
        cursor.execute('''
            INSERT INTO proposals (id, title, description, proposer_id, status, deadline, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            proposal_id,
            proposal_data['title'],
            proposal_data.get('description'),
            proposal_data.get('proposer_id'),
            proposal_data.get('status', 'pending'),
            proposal_data.get('deadline'),
            now,
            now
        ))
        proposal_data['id'] = proposal_id
        return proposal_data

def get_proposals() -> list[dict]:
    """Get all proposals"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM proposals')
        return [dict(row) for row in cursor.fetchall()]

def vote_proposal(proposal_id: str, voter_id: str, vote: int) -> bool:
    """Vote on proposal"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        # Record vote
        cursor.execute('''
            INSERT INTO votes (id, proposal_id, voter_id, vote, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (f"vote-{now}", proposal_id, voter_id, vote, now))

        # Update proposal counts
        if vote == 1:
            cursor.execute('UPDATE proposals SET votes_for = votes_for + 1 WHERE id = ?', (proposal_id,))
        else:
            cursor.execute('UPDATE proposals SET votes_against = votes_against + 1 WHERE id = ?', (proposal_id,))

        return True


# ==================== Learning Operations ====================

def save_learning_insight(agent_id: str, insights: dict) -> dict:
    """Save learning insights"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        insight_id = f"insight-{agent_id}-{now}"

        cursor.execute('''
            INSERT OR REPLACE INTO learning_insights (id, agent_id, insights, strategy, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            insight_id,
            agent_id,
            json.dumps(insights.get('insights', {})),
            json.dumps(insights.get('strategy', {})),
            now,
            now
        ))

        return {'id': insight_id, 'agent_id': agent_id}

def get_learning_insights(agent_id: str) -> list[dict]:
    """Get learning insights"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM learning_insights WHERE agent_id = ? ORDER BY created_at DESC', (agent_id,))
        return [dict(row) for row in cursor.fetchall()]


# ==================== User Profile Operations ====================

def create_or_update_profile(profile_data: dict) -> dict:
    """Create or update user profile"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        user_id = profile_data.get('id', f"user-{datetime.now().timestamp()}")

        cursor.execute('''
            INSERT OR REPLACE INTO user_profiles
            (id, wallet_address, display_name, bio, skills, hourly_rate, availability, stake, reputation, role, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            profile_data.get('wallet_address'),
            profile_data.get('display_name'),
            profile_data.get('bio'),
            json.dumps(profile_data.get('skills', [])),
            profile_data.get('hourly_rate'),
            profile_data.get('availability'),
            profile_data.get('stake', 0),
            profile_data.get('reputation', 0.5),
            profile_data.get('role'),
            profile_data.get('created_at', now),
            now
        ))

        profile_data['id'] = user_id
        return profile_data

def get_profile(user_id: str) -> dict | None:
    """Get user profile"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM user_profiles WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


# ==================== Metrics ====================

def get_metrics() -> dict:
    """Get system metrics"""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) as count FROM agents')
        agents_count = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM agents WHERE status = "online"')
        online_agents = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM agents WHERE status = "offline"')
        offline_agents = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM agents WHERE status = "busy"')
        busy_agents = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM agents WHERE agent_type = "ai_agent"')
        ai_agents_count = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM environments')
        environments_count = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM demands WHERE status = "active"')
        active_demands = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM services WHERE status = "active"')
        active_services = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM negotiations WHERE status = "pending"')
        pending_negotiations = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM collaborations')
        collaborations_count = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM workflows')
        workflows_count = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM opportunities')
        opportunities_count = cursor.fetchone()['count']

        return {
            'agents_count': agents_count,
            'ai_agents_count': ai_agents_count,
            'online_agents': online_agents,
            'offline_agents': offline_agents,
            'busy_agents': busy_agents,
            'environments_count': environments_count,
            'active_demands': active_demands,
            'active_services': active_services,
            'pending_negotiations': pending_negotiations,
            'collaborations_count': collaborations_count,
            'workflows_count': workflows_count,
            'opportunities_count': opportunities_count,
        }


# ==================== Auth Operations ====================

def create_nonce(address: str, nonce: str, expires_in_seconds: int = 300) -> dict:
    """Create a nonce for SIWE authentication"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        expires_at = now + expires_in_seconds
        nonce_id = f"nonce-{address}-{now}"

        # Delete old nonces for this address
        cursor.execute('DELETE FROM auth_nonces WHERE address = ?', (address.lower(),))

        # Create new nonce
        cursor.execute('''
            INSERT INTO auth_nonces (id, address, nonce, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (nonce_id, address.lower(), nonce, expires_at, now))

        return {
            'nonce': nonce,
            'expires_at': expires_at,
        }

def get_valid_nonce(address: str, nonce: str) -> dict | None:
    """Get and validate a nonce"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        cursor.execute('''
            SELECT * FROM auth_nonces
            WHERE address = ? AND nonce = ? AND expires_at > ?
        ''', (address.lower(), nonce, now))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def delete_nonce(nonce_id: str) -> bool:
    """Delete a used nonce"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM auth_nonces WHERE id = ?', (nonce_id,))
        return cursor.rowcount > 0

def create_session(session_data: dict) -> dict:
    """Create a new session"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        cursor.execute('''
            INSERT INTO auth_sessions (session_id, address, did, agent_id, access_token, expires_at, created_at, last_activity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_data['session_id'],
            session_data['address'].lower(),
            session_data.get('did'),
            session_data.get('agent_id'),
            session_data['access_token'],
            session_data['expires_at'],
            now,
            now
        ))

        return session_data

def get_session(session_id: str) -> dict | None:
    """Get session by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        cursor.execute('''
            SELECT * FROM auth_sessions
            WHERE session_id = ? AND expires_at > ?
        ''', (session_id, now))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def get_session_by_token(access_token: str) -> dict | None:
    """Get session by access token"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        cursor.execute('''
            SELECT * FROM auth_sessions
            WHERE access_token = ? AND expires_at > ?
        ''', (access_token, now))

        row = cursor.fetchone()
        if row:
            # Update last activity
            cursor.execute('''
                UPDATE auth_sessions SET last_activity = ? WHERE session_id = ?
            ''', (now, row['session_id']))
            return dict(row)
        return None

def delete_session(session_id: str) -> bool:
    """Delete a session"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM auth_sessions WHERE session_id = ?', (session_id,))
        return cursor.rowcount > 0

def delete_sessions_by_address(address: str) -> bool:
    """Delete all sessions for an address"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM auth_sessions WHERE address = ?', (address.lower(),))
        return cursor.rowcount > 0

def create_user(user_data: dict) -> dict:
    """Create or get user by wallet address.

    Also creates a corresponding human_agent entry in the agents table.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        # Check if user exists
        cursor.execute('SELECT * FROM users WHERE wallet_address = ?', (user_data['wallet_address'].lower(),))
        existing = cursor.fetchone()

        if existing:
            return dict(existing)

        # Create new user
        user_id = user_data.get('id', f"user-{now}")
        did = user_data.get('did', f"did:vibe:{user_data['wallet_address'].lower()}")
        agent_id = f"human_{user_id}"

        # Create corresponding human_agent in agents table
        cursor.execute('''
            INSERT OR REPLACE INTO agents (
                agent_id, name, agent_type, description, capabilities, skills,
                endpoint, chat_endpoint, protocol, stake, balance, status,
                reputation, heartbeat_interval, ttl, metadata, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            agent_id,
            user_data.get('name', f"User_{user_id[-6:]}"),
            'human_agent',
            user_data.get('description', 'Human user'),
            '[]',
            '[]',
            '',  # endpoint - humans don't have HTTP endpoint
            '',  # chat_endpoint
            'standard',
            0,  # stake
            user_data.get('vibe_balance', 10000.0),
            'online',
            0.5,  # reputation
            0,  # heartbeat_interval - not applicable for humans
            0,  # ttl - not applicable for humans
            '{"human": true, "wallet_address": "' + user_data['wallet_address'].lower() + '"}',
            now,
            now
        ))

        cursor.execute('''
            INSERT INTO users (id, wallet_address, did, agent_id, stake, reputation, vibe_balance, stake_status, locked_stake, unlock_available_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            user_data['wallet_address'].lower(),
            did,
            agent_id,  # Link to the human_agent we just created
            user_data.get('stake', 0),
            user_data.get('reputation', 0.5),
            user_data.get('vibe_balance', 10000.0),
            user_data.get('stake_status', 'none'),
            user_data.get('locked_stake', 0),
            user_data.get('unlock_available_at'),
            now,
            now
        ))

        return {
            'id': user_id,
            'wallet_address': user_data['wallet_address'].lower(),
            'did': did,
            'agent_id': agent_id,  # Return the human_agent ID
            'stake': 0,
            'reputation': 0.5,
            'vibe_balance': 10000.0,
            'stake_status': 'none',
            'locked_stake': 0,
            'unlock_available_at': None,
        }

def get_user_by_address(address: str) -> dict | None:
    """Get user by wallet address"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE wallet_address = ?', (address.lower(),))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def get_user_by_did(did: str) -> dict | None:
    """Get user by DID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE did = ?', (did,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def update_user_stake(user_id: str, stake_amount: float) -> dict:
    """Update user stake and reputation"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        # Get current stake
        cursor.execute('SELECT stake FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        current_stake = row['stake'] if row else 0
        new_stake = current_stake + stake_amount

        # Calculate reputation based on stake
        reputation = min(0.5 + (new_stake / 1000), 1.0)

        cursor.execute('''
            UPDATE users SET stake = ?, reputation = ?, updated_at = ? WHERE id = ?
        ''', (new_stake, reputation, now, user_id))

        return {
            'user_id': user_id,
            'stake': new_stake,
            'reputation': reputation,
        }

def update_user_agent(user_id: str, agent_id: str) -> bool:
    """Update user's agent ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        cursor.execute('''
            UPDATE users SET agent_id = ?, updated_at = ? WHERE id = ?
        ''', (agent_id, now, user_id))
        return cursor.rowcount > 0


def update_user_balance(user_id: str, amount: float, deduct: bool = False) -> dict | None:
    """Update user's VIBE balance (deduct or add)"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        # Get current balance
        cursor.execute('SELECT vibe_balance FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        if not row:
            return None

        current_balance = row['vibe_balance']
        if deduct:
            new_balance = current_balance - amount
            if new_balance < 0:
                return None  # Insufficient balance
        else:
            new_balance = current_balance + amount

        cursor.execute('''
            UPDATE users SET vibe_balance = ?, updated_at = ? WHERE id = ?
        ''', (new_balance, now, user_id))

        return {
            'user_id': user_id,
            'vibe_balance': new_balance,
        }


def update_stake_status(user_id: str, status: str, locked_stake: float = 0, unlock_available_at: float = None) -> bool:
    """Update user's stake status"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        cursor.execute('''
            UPDATE users SET stake_status = ?, locked_stake = ?, unlock_available_at = ?, updated_at = ? WHERE id = ?
        ''', (status, locked_stake, unlock_available_at, now, user_id))
        return cursor.rowcount > 0


def get_user_balance_info(user_id: str) -> dict | None:
    """Get user's balance information"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT vibe_balance, stake, stake_status, locked_stake, unlock_available_at
            FROM users WHERE id = ?
        ''', (user_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


# ==================== Transaction Operations ====================

# Transaction status constants
class TransactionStatus:
    CREATED = "created"
    ESCROWED = "escrowed"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    DISPUTED = "disputed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


def create_transaction(tx_data: dict) -> dict:
    """Create a new transaction"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        tx_id = tx_data.get('id', f"tx-{now}")

        cursor.execute('''
            INSERT INTO transactions
            (id, demand_id, service_id, buyer_id, seller_id, amount, platform_fee,
             status, transaction_type, title, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            tx_id,
            tx_data.get('demand_id'),
            tx_data.get('service_id'),
            tx_data['buyer_id'],
            tx_data['seller_id'],
            tx_data['amount'],
            tx_data.get('platform_fee', tx_data['amount'] * 0.03),  # 3% platform fee
            TransactionStatus.CREATED,
            tx_data.get('transaction_type', 'service_payment'),
            tx_data.get('title'),
            tx_data.get('description'),
            now,
            now
        ))

        tx_data['id'] = tx_id
        tx_data['status'] = TransactionStatus.CREATED
        tx_data['created_at'] = now
        tx_data['updated_at'] = now
        return tx_data


def get_transaction(tx_id: str) -> dict | None:
    """Get transaction by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM transactions WHERE id = ?', (tx_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_transactions_by_user(user_id: str, role: str = None, status: str = None, limit: int = 50) -> list[dict]:
    """Get transactions for a user (as buyer or seller)"""
    with get_db() as conn:
        cursor = conn.cursor()

        query = 'SELECT * FROM transactions WHERE (buyer_id = ? OR seller_id = ?)'
        params = [user_id, user_id]

        if status:
            query += ' AND status = ?'
            params.append(status)

        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_all_transactions(limit: int = 100) -> list[dict]:
    """Get all transactions"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM transactions ORDER BY created_at DESC LIMIT ?', (limit,))
        return [dict(row) for row in cursor.fetchall()]


def update_transaction_status(tx_id: str, status: str, extra_data: dict = None) -> dict | None:
    """Update transaction status"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        # Build update query based on status
        update_fields = ['status = ?', 'updated_at = ?']
        params = [status, now]

        # Add timestamp based on status
        if status == TransactionStatus.ESCROWED:
            update_fields.append('escrowed_at = ?')
            params.append(now)
        elif status == TransactionStatus.DELIVERED:
            update_fields.append('delivered_at = ?')
            params.append(now)
        elif status == TransactionStatus.COMPLETED:
            update_fields.append('completed_at = ?')
            params.append(now)
        elif status == TransactionStatus.CANCELLED:
            update_fields.append('cancelled_at = ?')
            params.append(now)

        # Add extra data
        if extra_data:
            if 'escrow_tx_hash' in extra_data:
                update_fields.append('escrow_tx_hash = ?')
                params.append(extra_data['escrow_tx_hash'])
            if 'release_tx_hash' in extra_data:
                update_fields.append('release_tx_hash = ?')
                params.append(extra_data['release_tx_hash'])
            if 'delivery_description' in extra_data:
                update_fields.append('delivery_description = ?')
                params.append(extra_data['delivery_description'])
            if 'delivery_files' in extra_data:
                update_fields.append('delivery_files = ?')
                params.append(json.dumps(extra_data['delivery_files']))
            if 'rating' in extra_data:
                update_fields.append('rating = ?')
                params.append(extra_data['rating'])
            if 'review' in extra_data:
                update_fields.append('review = ?')
                params.append(extra_data['review'])
            if 'dispute_reason' in extra_data:
                update_fields.append('dispute_reason = ?')
                params.append(extra_data['dispute_reason'])
            if 'dispute_resolution' in extra_data:
                update_fields.append('dispute_resolution = ?')
                params.append(extra_data['dispute_resolution'])

        params.append(tx_id)

        cursor.execute(
            f"UPDATE transactions SET {', '.join(update_fields)} WHERE id = ?",
            params
        )

        if cursor.rowcount > 0:
            return get_transaction(tx_id)
        return None


def get_transaction_stats(user_id: str = None) -> dict:
    """Get transaction statistics"""
    with get_db() as conn:
        cursor = conn.cursor()

        if user_id:
            # Stats for specific user
            cursor.execute('''
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status IN ('created', 'escrowed', 'in_progress') THEN 1 ELSE 0 END) as active,
                    SUM(CASE WHEN buyer_id = ? THEN amount ELSE 0 END) as total_spent,
                    SUM(CASE WHEN seller_id = ? THEN amount ELSE 0 END) as total_earned
                FROM transactions
                WHERE buyer_id = ? OR seller_id = ?
            ''', (user_id, user_id, user_id, user_id))
        else:
            # Global stats
            cursor.execute('''
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status IN ('created', 'escrowed', 'in_progress') THEN 1 ELSE 0 END) as active,
                    SUM(amount) as total_volume
                FROM transactions
            ''')

        row = cursor.fetchone()
        return dict(row) if row else {}


# ==================== Agent Wallet Operations ====================

def create_agent_wallet(wallet_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new agent wallet"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        cursor.execute('''
            INSERT INTO agent_wallets (
                id, agent_id, owner_id, wallet_address, agent_address,
                vibe_balance, staked_amount, stake_status, locked_stake,
                max_per_tx, daily_limit, daily_spent, last_reset_time,
                registry_registered, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            wallet_data.get('id'),
            wallet_data.get('agent_id'),
            wallet_data.get('owner_id'),
            wallet_data.get('wallet_address'),
            wallet_data.get('agent_address'),
            wallet_data.get('vibe_balance', 0),
            wallet_data.get('staked_amount', 0),
            wallet_data.get('stake_status', 'none'),
            wallet_data.get('locked_stake', 0),
            wallet_data.get('max_per_tx', 500),
            wallet_data.get('daily_limit', 1000),
            wallet_data.get('daily_spent', 0),
            wallet_data.get('last_reset_time', now),
            wallet_data.get('registry_registered', 0),
            now,
            now
        ))

        conn.commit()
        return wallet_data


def get_agent_wallet(agent_id: str) -> dict | None:
    """Get agent wallet by agent_id"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM agent_wallets WHERE agent_id = ?', (agent_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_agent_wallet_by_address(wallet_address: str) -> dict | None:
    """Get agent wallet by wallet address"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM agent_wallets WHERE wallet_address = ?', (wallet_address,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_agent_wallets_by_owner(owner_id: str) -> list[dict]:
    """Get all agent wallets for an owner"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM agent_wallets WHERE owner_id = ?', (owner_id,))
        return [dict(row) for row in cursor.fetchall()]


def update_agent_wallet_key(agent_id: str, agent_address: str, agent_private_key: str) -> bool:
    """Store or update the agent's operational private key (for autonomous wallet control - Plan B).

    This stores the agent's own private key that it uses to sign transactions autonomously.
    The private key is stored in plaintext in this implementation.
    For production, use encryption at rest.

    Returns True if the wallet record was found and updated.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        # Check if wallet exists for this agent
        cursor.execute('SELECT id FROM agent_wallets WHERE agent_id = ?', (agent_id,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute('''
                UPDATE agent_wallets
                SET agent_address = ?, agent_private_key = ?, updated_at = ?
                WHERE agent_id = ?
            ''', (agent_address, agent_private_key, now, agent_id))
        else:
            # Wallet record doesn't exist yet - create a placeholder
            # This can happen if wallet deployment was deferred
            cursor.execute('''
                INSERT INTO agent_wallets (
                    id, agent_id, owner_id, wallet_address, agent_address,
                    agent_private_key, vibe_balance, staked_amount, stake_status,
                    max_per_tx, daily_limit, daily_spent, last_reset_time,
                    registry_registered, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                f"aw_{agent_id}_{int(now * 1000)}",
                agent_id,
                "pending",  # owner_id
                "0x0000000000000000000000000000000000000000",  # wallet_address (deployed later)
                agent_address,
                agent_private_key,
                0, 0, 'none',  # vibe_balance, staked_amount, stake_status
                500, 1000, 0, now,  # max_per_tx, daily_limit, daily_spent, last_reset_time
                0, now, now  # registry_registered, created_at, updated_at
            ))

        conn.commit()
        return cursor.rowcount > 0


def update_agent_balance(agent_id: str, amount: float, deduct: bool = False) -> bool:
    """Update agent wallet balance"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        if deduct:
            cursor.execute('''
                UPDATE agent_wallets
                SET vibe_balance = vibe_balance - ?, updated_at = ?
                WHERE agent_id = ? AND vibe_balance >= ?
            ''', (amount, now, agent_id, amount))
        else:
            cursor.execute('''
                UPDATE agent_wallets
                SET vibe_balance = vibe_balance + ?, updated_at = ?
                WHERE agent_id = ?
            ''', (amount, now, agent_id))

        conn.commit()
        return cursor.rowcount > 0


def update_agent_stake(agent_id: str, amount: float, deduct: bool = False) -> bool:
    """Update agent stake amount"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        if deduct:
            cursor.execute('''
                UPDATE agent_wallets
                SET staked_amount = staked_amount - ?, stake_status = 'unstaking', updated_at = ?
                WHERE agent_id = ? AND staked_amount >= ?
            ''', (amount, now, agent_id, amount))
        else:
            cursor.execute('''
                UPDATE agent_wallets
                SET staked_amount = staked_amount + ?, stake_status = 'staked', updated_at = ?
                WHERE agent_id = ?
            ''', (amount, now, agent_id))

        conn.commit()
        return cursor.rowcount > 0


def update_agent_limits(agent_id: str, max_per_tx: float, daily_limit: float) -> bool:
    """Update agent wallet limits"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        cursor.execute('''
            UPDATE agent_wallets
            SET max_per_tx = ?, daily_limit = ?, updated_at = ?
            WHERE agent_id = ?
        ''', (max_per_tx, daily_limit, now, agent_id))

        conn.commit()
        return cursor.rowcount > 0


def update_agent_daily_spent(agent_id: str, amount: float) -> bool:
    """Update agent daily spent amount and reset if new day"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        # Get current wallet info
        cursor.execute('SELECT last_reset_time, daily_spent FROM agent_wallets WHERE agent_id = ?', (agent_id,))
        row = cursor.fetchone()
        if not row:
            return False

        last_reset = row['last_reset_time']
        daily_spent = row['daily_spent']

        # Reset if new day (more than 24 hours)
        if now - last_reset >= 86400:  # 24 hours
            daily_spent = 0
            last_reset = now

        # Update spent amount
        cursor.execute('''
            UPDATE agent_wallets
            SET daily_spent = ?, last_reset_time = ?, updated_at = ?
            WHERE agent_id = ?
        ''', (daily_spent + amount, last_reset, now, agent_id))

        conn.commit()
        return cursor.rowcount > 0


def register_agent_in_registry(agent_id: str) -> bool:
    """Mark agent as registered in registry"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        cursor.execute('''
            UPDATE agent_wallets
            SET registry_registered = 1, updated_at = ?
            WHERE agent_id = ?
        ''', (now, agent_id))

        conn.commit()
        return cursor.rowcount > 0


def delete_agent_wallet(agent_id: str) -> bool:
    """Delete agent wallet"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM agent_wallets WHERE agent_id = ?', (agent_id,))
        conn.commit()
        return cursor.rowcount > 0


# ==================== API Key Operations ====================

def create_api_key(api_key_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new API key for an agent.

    Args:
        api_key_data: Dict containing:
            - id: Unique key ID
            - agent_id: Agent this key belongs to
            - key_hash: SHA-256 hash of the API key
            - key_prefix: First 16 chars of the key for identification
            - name: Human-readable name for the key
            - level: Permission level (0=unbound, 1+=bound)
            - permissions: JSON list of permissions
            - expires_at: Unix timestamp for expiration (None = never)

    Returns:
        The created API key data
    """
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        cursor.execute('''
            INSERT INTO agent_api_keys
            (id, agent_id, key_hash, key_prefix, name, permissions, level, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            api_key_data['id'],
            api_key_data['agent_id'],
            api_key_data['key_hash'],
            api_key_data['key_prefix'],
            api_key_data.get('name', 'Primary'),
            json.dumps(api_key_data.get('permissions', [])),
            api_key_data.get('level', 0),
            api_key_data.get('expires_at'),
            now
        ))

        return {
            'id': api_key_data['id'],
            'agent_id': api_key_data['agent_id'],
            'key_prefix': api_key_data['key_prefix'],
            'name': api_key_data.get('name', 'Primary'),
            'level': api_key_data.get('level', 0),
            'created_at': now
        }


def get_api_key_by_hash(key_hash: str) -> dict[str, Any] | None:
    """Get API key by its hash."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM agent_api_keys
            WHERE key_hash = ? AND revoked_at IS NULL
        ''', (key_hash,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_api_keys_by_agent(agent_id: str) -> list[dict[str, Any]]:
    """Get all active API keys for an agent."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, agent_id, key_prefix, name, permissions, level,
                   expires_at, last_used_at, created_at, revoked_at
            FROM agent_api_keys
            WHERE agent_id = ? AND revoked_at IS NULL
            ORDER BY created_at DESC
        ''', (agent_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_api_key_by_id(key_id: str) -> dict[str, Any] | None:
    """Get API key by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM agent_api_keys WHERE id = ?', (key_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_api_key_last_used(key_id: str) -> bool:
    """Update the last_used_at timestamp for an API key."""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        cursor.execute('''
            UPDATE agent_api_keys SET last_used_at = ? WHERE id = ?
        ''', (now, key_id))
        return cursor.rowcount > 0


def revoke_api_key(key_id: str, agent_id: str) -> bool:
    """Revoke an API key."""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        cursor.execute('''
            UPDATE agent_api_keys SET revoked_at = ?
            WHERE id = ? AND agent_id = ?
        ''', (now, key_id, agent_id))
        return cursor.rowcount > 0


def renew_api_key(key_id: str, agent_id: str, extends_days: int = 365) -> bool:
    """Extend the expiration of an API key."""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        new_expires_at = now + (extends_days * 86400)
        cursor.execute('''
            UPDATE agent_api_keys SET expires_at = ?
            WHERE id = ? AND agent_id = ? AND revoked_at IS NULL
        ''', (new_expires_at, key_id, agent_id))
        return cursor.rowcount > 0


def upgrade_api_keys_level(agent_id: str, new_level: int) -> bool:
    """Upgrade all API keys for an agent to a new level (used after binding)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE agent_api_keys SET level = ?
            WHERE agent_id = ? AND revoked_at IS NULL
        ''', (new_level, agent_id))
        return cursor.rowcount > 0


def delete_api_keys_for_agent(agent_id: str) -> bool:
    """Delete all API keys for an agent."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM agent_api_keys WHERE agent_id = ?', (agent_id,))
        return cursor.rowcount > 0


# ==================== Binding Request Operations ====================

def create_binding_request(binding_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new binding request.

    Args:
        binding_data: Dict containing:
            - id: Unique binding request ID
            - agent_id: Agent requesting binding
            - binding_code: Unique code (bind-xxx)
            - binding_url: URL for owner to visit
            - message: Optional message to owner
            - expires_at: Unix timestamp for expiration

    Returns:
        The created binding request data
    """
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        cursor.execute('''
            INSERT INTO agent_binding_requests
            (id, agent_id, binding_code, message, binding_url, status, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
        ''', (
            binding_data['id'],
            binding_data['agent_id'],
            binding_data['binding_code'],
            binding_data.get('message', ''),
            binding_data['binding_url'],
            now,
            binding_data['expires_at']
        ))

        # Update agent binding status to pending
        cursor.execute('''
            UPDATE agents SET binding_status = 'pending', updated_at = ? WHERE agent_id = ?
        ''', (now, binding_data['agent_id']))

        return {
            'id': binding_data['id'],
            'agent_id': binding_data['agent_id'],
            'binding_code': binding_data['binding_code'],
            'binding_url': binding_data['binding_url'],
            'status': 'pending',
            'created_at': now,
            'expires_at': binding_data['expires_at']
        }


def get_binding_request_by_code(binding_code: str) -> dict[str, Any] | None:
    """Get binding request by code."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM agent_binding_requests WHERE binding_code = ?', (binding_code,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_binding_request_by_agent(agent_id: str) -> dict[str, Any] | None:
    """Get the latest pending binding request for an agent."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM agent_binding_requests
            WHERE agent_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        ''', (agent_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def complete_binding_request(binding_code: str, owner_wallet: str, stake_amount: float) -> dict[str, Any] | None:
    """Complete a binding request.

    This is called when the owner confirms binding and stakes tokens.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        # Get the binding request
        cursor.execute('''
            SELECT * FROM agent_binding_requests
            WHERE binding_code = ? AND status = 'pending'
        ''', (binding_code,))
        binding = cursor.fetchone()

        if not binding:
            return None

        binding_dict = dict(binding)

        # Check if expired
        if binding_dict['expires_at'] < now:
            cursor.execute('''
                UPDATE agent_binding_requests SET status = 'expired' WHERE binding_code = ?
            ''', (binding_code,))
            return None

        # Update binding request
        cursor.execute('''
            UPDATE agent_binding_requests
            SET status = 'completed', owner_wallet = ?, stake_amount = ?, completed_at = ?
            WHERE binding_code = ?
        ''', (owner_wallet, stake_amount, now, binding_code))

        # Update agent
        cursor.execute('''
            UPDATE agents
            SET owner_wallet = ?, binding_status = 'bound', bound_at = ?, updated_at = ?
            WHERE agent_id = ?
        ''', (owner_wallet, now, now, binding_dict['agent_id']))

        # Create or update agent wallet
        cursor.execute('''
            INSERT OR REPLACE INTO agent_wallets
            (id, agent_id, owner_id, wallet_address, agent_address, staked_amount, stake_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'active', COALESCE((SELECT created_at FROM agent_wallets WHERE agent_id = ?), ?), ?)
        ''', (
            f"wallet-{binding_dict['agent_id']}",
            binding_dict['agent_id'],
            owner_wallet,
            owner_wallet,
            f"agent-addr-{binding_dict['agent_id']}",
            stake_amount,
            binding_dict['agent_id'],
            now,
            now
        ))

        # Upgrade all API keys for this agent to level 1
        cursor.execute('''
            UPDATE agent_api_keys SET level = 1 WHERE agent_id = ? AND revoked_at IS NULL
        ''', (binding_dict['agent_id'],))

        return {
            'agent_id': binding_dict['agent_id'],
            'owner_wallet': owner_wallet,
            'stake_amount': stake_amount,
            'completed_at': now
        }


def cancel_binding_request(binding_code: str) -> bool:
    """Cancel a binding request."""
    with get_db() as conn:
        cursor = conn.cursor()
        datetime.now().timestamp()

        cursor.execute('''
            UPDATE agent_binding_requests SET status = 'cancelled' WHERE binding_code = ?
        ''', (binding_code,))
        return cursor.rowcount > 0


def expire_binding_requests() -> int:
    """Expire all pending binding requests that have passed their expiration time."""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        cursor.execute('''
            UPDATE agent_binding_requests
            SET status = 'expired'
            WHERE status = 'pending' AND expires_at < ?
        ''', (now,))

        return cursor.rowcount


# ==================== Agent Binding Status Operations ====================

def update_agent_binding_status(agent_id: str, status: str, owner_wallet: str = None) -> bool:
    """Update agent's binding status."""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()

        if status == 'bound' and owner_wallet:
            cursor.execute('''
                UPDATE agents
                SET binding_status = ?, owner_wallet = ?, bound_at = ?, updated_at = ?
                WHERE agent_id = ?
            ''', (status, owner_wallet, now, now, agent_id))
        else:
            cursor.execute('''
                UPDATE agents SET binding_status = ?, updated_at = ? WHERE agent_id = ?
            ''', (status, now, agent_id))

        return cursor.rowcount > 0


def get_agent_binding_info(agent_id: str) -> dict[str, Any] | None:
    """Get agent's binding information including wallet and stake."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT a.agent_id, a.name, a.binding_status, a.owner_wallet, a.bound_at,
                   w.staked_amount, w.stake_status
            FROM agents a
            LEFT JOIN agent_wallets w ON a.agent_id = w.agent_id
            WHERE a.agent_id = ?
        ''', (agent_id,))

        row = cursor.fetchone()
        return dict(row) if row else None


if __name__ == '__main__':
    init_db()
    print("Database tables created successfully!")
