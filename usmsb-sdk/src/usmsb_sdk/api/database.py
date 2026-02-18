"""
SQLite Database setup for AI Civilization Platform
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

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

        # Agents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agents (
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

        # AI Agents table (for protocol registration)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_agents (
                agent_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                agent_type TEXT,
                capabilities TEXT,
                skills TEXT,
                status TEXT DEFAULT 'offline',
                endpoint TEXT,
                stake REAL DEFAULT 0,
                reputation REAL DEFAULT 0.5,
                last_heartbeat REAL,
                created_at REAL,
                updated_at REAL,
                metadata TEXT
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
                created_at REAL,
                updated_at REAL
            )
        ''')

        # Create indexes for commonly queried fields
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_buyer ON transactions(buyer_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_seller ON transactions(seller_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_demands_agent ON demands(agent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_services_agent ON services(agent_id)')

        conn.commit()
        print(f"Database initialized at: {get_db_path()}")


# ==================== Agent Operations ====================

def create_agent(agent_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new agent"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        cursor.execute('''
            INSERT INTO agents (id, name, type, capabilities, state, goals_count, resources_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            agent_data['id'],
            agent_data['name'],
            agent_data['type'],
            json.dumps(agent_data.get('capabilities', [])),
            json.dumps(agent_data.get('state', {})),
            agent_data.get('goals_count', 0),
            agent_data.get('resources_count', 0),
            now,
            now
        ))
        return agent_data

def get_agent(agent_id: str) -> Optional[Dict[str, Any]]:
    """Get agent by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM agents WHERE id = ?', (agent_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def get_all_agents(agent_type: str = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Get all agents"""
    with get_db() as conn:
        cursor = conn.cursor()
        if agent_type:
            cursor.execute('SELECT * FROM agents WHERE type = ? LIMIT ?', (agent_type, limit))
        else:
            cursor.execute('SELECT * FROM agents LIMIT ?', (limit,))
        return [dict(row) for row in cursor.fetchall()]

def delete_agent(agent_id: str) -> bool:
    """Delete agent"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM agents WHERE id = ?', (agent_id,))
        return cursor.rowcount > 0


# ==================== AI Agent Operations ====================

def create_ai_agent(agent_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create AI agent via protocol"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        cursor.execute('''
            INSERT OR REPLACE INTO ai_agents
            (agent_id, name, agent_type, capabilities, skills, status, endpoint, stake, reputation, last_heartbeat, created_at, updated_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            agent_data.get('agent_id'),
            agent_data.get('name'),
            agent_data.get('agent_type', 'ai_agent'),
            json.dumps(agent_data.get('capabilities', [])),
            json.dumps(agent_data.get('skills', [])),
            agent_data.get('status', 'offline'),
            agent_data.get('endpoint'),
            agent_data.get('stake', 0),
            agent_data.get('reputation', 0.5),
            agent_data.get('last_heartbeat'),
            now,
            now,
            json.dumps(agent_data.get('metadata', {}))
        ))
        return agent_data

def get_ai_agent(agent_id: str) -> Optional[Dict[str, Any]]:
    """Get AI agent by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM ai_agents WHERE agent_id = ?', (agent_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def get_all_ai_agents(status: str = None) -> List[Dict[str, Any]]:
    """Get all AI agents"""
    with get_db() as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute('SELECT * FROM ai_agents WHERE status = ?', (status,))
        else:
            cursor.execute('SELECT * FROM ai_agents')
        return [dict(row) for row in cursor.fetchall()]

def update_ai_agent_heartbeat(agent_id: str, status: str) -> bool:
    """Update AI agent heartbeat"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        cursor.execute('''
            UPDATE ai_agents SET last_heartbeat = ?, status = ?, updated_at = ?
            WHERE agent_id = ?
        ''', (now, status, now, agent_id))
        return cursor.rowcount > 0

def update_ai_agent_stake(agent_id: str, amount: float) -> bool:
    """Update AI agent stake"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        # Calculate reputation based on stake
        reputation = min(0.5 + (amount / 1000), 1.0)
        cursor.execute('''
            UPDATE ai_agents SET stake = stake + ?, reputation = ?, updated_at = ?
            WHERE agent_id = ?
        ''', (amount, reputation, now, agent_id))
        return cursor.rowcount > 0

def delete_ai_agent(agent_id: str) -> bool:
    """Delete AI agent"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM ai_agents WHERE agent_id = ?', (agent_id,))
        return cursor.rowcount > 0


# ==================== Service Operations ====================

def create_service(service_data: Dict[str, Any]) -> Dict[str, Any]:
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

def get_services_by_agent(agent_id: str) -> List[Dict[str, Any]]:
    """Get services by agent"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM services WHERE agent_id = ?', (agent_id,))
        return [dict(row) for row in cursor.fetchall()]


# ==================== Environment Operations ====================

def create_environment(env_data: Dict[str, Any]) -> Dict[str, Any]:
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

def get_environment(env_id: str) -> Optional[Dict[str, Any]]:
    """Get environment by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM environments WHERE id = ?', (env_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def get_all_environments(limit: int = 100) -> List[Dict[str, Any]]:
    """Get all environments"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM environments LIMIT ?', (limit,))
        return [dict(row) for row in cursor.fetchall()]


# ==================== Demand/Supply Operations ====================

def create_demand(demand_data: Dict[str, Any]) -> Dict[str, Any]:
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

def search_demands(capabilities: List[str] = None, budget_min: float = None, budget_max: float = None) -> List[Dict[str, Any]]:
    """Search demands"""
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

        # Filter by capabilities if provided
        if capabilities:
            filtered = []
            for demand in demands:
                skills = json.loads(demand.get('required_skills', '[]'))
                if any(cap.lower() in [s.lower() for s in skills] for cap in capabilities):
                    filtered.append(demand)
            return filtered
        return demands


# ==================== Opportunity Operations ====================

def create_opportunity(opp_data: Dict) -> Dict:
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

def get_all_opportunities() -> List[Dict]:
    """Get all opportunities"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM opportunities')
        return [dict(row) for row in cursor.fetchall()]


# ==================== Negotiation Operations ====================

def create_negotiation(neg_data: Dict) -> Dict:
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

def get_negotiations() -> List[Dict]:
    """Get all negotiations"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM negotiations')
        return [dict(row) for row in cursor.fetchall()]

def get_negotiation(session_id: str) -> Optional[Dict]:
    """Get negotiation by session ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM negotiations WHERE session_id = ?', (session_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


# ==================== Workflow Operations ====================

def create_workflow(workflow_data: Dict) -> Dict:
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

def get_workflows() -> List[Dict]:
    """Get all workflows"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM workflows')
        return [dict(row) for row in cursor.fetchall()]

def get_workflow(workflow_id: str) -> Optional[Dict]:
    """Get workflow by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM workflows WHERE id = ?', (workflow_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


# ==================== Collaboration Operations ====================

def create_collaboration(collab_data: Dict) -> Dict:
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

def get_collaborations() -> List[Dict]:
    """Get all collaborations"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM collaborations')
        return [dict(row) for row in cursor.fetchall()]

def get_collaboration(session_id: str) -> Optional[Dict]:
    """Get collaboration by session ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM collaborations WHERE session_id = ?', (session_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


# ==================== Proposal Operations ====================

def create_proposal(proposal_data: Dict) -> Dict:
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

def get_proposals() -> List[Dict]:
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

def save_learning_insight(agent_id: str, insights: Dict) -> Dict:
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

def get_learning_insights(agent_id: str) -> List[Dict]:
    """Get learning insights"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM learning_insights WHERE agent_id = ? ORDER BY created_at DESC', (agent_id,))
        return [dict(row) for row in cursor.fetchall()]


# ==================== User Profile Operations ====================

def create_or_update_profile(profile_data: Dict) -> Dict:
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

def get_profile(user_id: str) -> Optional[Dict]:
    """Get user profile"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM user_profiles WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


# ==================== Metrics ====================

def get_metrics() -> Dict:
    """Get system metrics"""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) as count FROM agents')
        agents_count = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM ai_agents')
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
            'environments_count': environments_count,
            'active_demands': active_demands,
            'active_services': active_services,
            'pending_negotiations': pending_negotiations,
            'collaborations_count': collaborations_count,
            'workflows_count': workflows_count,
            'opportunities_count': opportunities_count,
        }


# ==================== Auth Operations ====================

def create_nonce(address: str, nonce: str, expires_in_seconds: int = 300) -> Dict:
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

def get_valid_nonce(address: str, nonce: str) -> Optional[Dict]:
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

def create_session(session_data: Dict) -> Dict:
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

def get_session(session_id: str) -> Optional[Dict]:
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

def get_session_by_token(access_token: str) -> Optional[Dict]:
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

def create_user(user_data: Dict) -> Dict:
    """Create or get user by wallet address"""
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

        cursor.execute('''
            INSERT INTO users (id, wallet_address, did, agent_id, stake, reputation, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            user_data['wallet_address'].lower(),
            did,
            user_data.get('agent_id'),
            user_data.get('stake', 0),
            user_data.get('reputation', 0.5),
            now,
            now
        ))

        return {
            'id': user_id,
            'wallet_address': user_data['wallet_address'].lower(),
            'did': did,
            'stake': 0,
            'reputation': 0.5,
        }

def get_user_by_address(address: str) -> Optional[Dict]:
    """Get user by wallet address"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE wallet_address = ?', (address.lower(),))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def get_user_by_did(did: str) -> Optional[Dict]:
    """Get user by DID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE did = ?', (did,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def update_user_stake(user_id: str, stake_amount: float) -> Dict:
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


def create_transaction(tx_data: Dict) -> Dict:
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


def get_transaction(tx_id: str) -> Optional[Dict]:
    """Get transaction by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM transactions WHERE id = ?', (tx_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_transactions_by_user(user_id: str, role: str = None, status: str = None, limit: int = 50) -> List[Dict]:
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


def get_all_transactions(limit: int = 100) -> List[Dict]:
    """Get all transactions"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM transactions ORDER BY created_at DESC LIMIT ?', (limit,))
        return [dict(row) for row in cursor.fetchall()]


def update_transaction_status(tx_id: str, status: str, extra_data: Dict = None) -> Optional[Dict]:
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


def get_transaction_stats(user_id: str = None) -> Dict:
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


if __name__ == '__main__':
    init_db()
    print("Database tables created successfully!")
