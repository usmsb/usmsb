"""
Reputation endpoints for Agent Platform.

Provides reputation operations:
- Get agent reputation score
- Get reputation change history

Authentication: Supports both Bearer token and API Key authentication.
"""

import time
import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from usmsb_sdk.api.database import get_db
from usmsb_sdk.api.rest.unified_auth import get_current_user_unified

router = APIRouter(prefix="/reputation", tags=["Reputation"])


# ==================== Request/Response Models ====================

class ReputationResponse(BaseModel):
    """Reputation information response."""
    success: bool = True
    agent_id: str
    score: float  # 0.0 - 1.0
    tier: str
    total_transactions: int
    successful_transactions: int
    success_rate: float
    avg_rating: float
    total_ratings: int


class ReputationEvent(BaseModel):
    """Single reputation change event."""
    timestamp: float
    event_type: str
    change: float
    reason: str
    related_id: str | None = None


class ReputationHistoryResponse(BaseModel):
    """Reputation history response."""
    success: bool = True
    agent_id: str
    current_score: float
    history: list[ReputationEvent]
    total_events: int


# ==================== Helper Functions ====================

def get_reputation_tier(score: float) -> str:
    """Get reputation tier from score."""
    if score >= 0.9:
        return "EXCELLENT"
    elif score >= 0.8:
        return "VERY_GOOD"
    elif score >= 0.7:
        return "GOOD"
    elif score >= 0.6:
        return "AVERAGE"
    elif score >= 0.5:
        return "BELOW_AVERAGE"
    else:
        return "POOR"


def ensure_reputation_tables():
    """Ensure reputation tables exist."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Reputation summary table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_reputation (
                id TEXT PRIMARY KEY,
                agent_id TEXT UNIQUE NOT NULL,
                score REAL DEFAULT 0.5,
                total_transactions INTEGER DEFAULT 0,
                successful_transactions INTEGER DEFAULT 0,
                total_ratings INTEGER DEFAULT 0,
                rating_sum REAL DEFAULT 0,
                last_updated REAL,
                created_at REAL NOT NULL,
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
            )
        ''')

        # Reputation events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reputation_events (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                change REAL NOT NULL,
                reason TEXT,
                related_id TEXT,
                timestamp REAL NOT NULL,
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
            )
        ''')

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reputation_agent ON agent_reputation(agent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reputation_events_agent ON reputation_events(agent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reputation_events_time ON reputation_events(timestamp)')

        conn.commit()


def get_or_create_reputation(agent_id: str) -> dict:
    """Get or create reputation record for agent."""
    ensure_reputation_tables()

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT score, total_transactions, successful_transactions,
                   total_ratings, rating_sum, last_updated
            FROM agent_reputation
            WHERE agent_id = ?
        """, (agent_id,))

        row = cursor.fetchone()
        if row:
            return dict(row)

        # Create new record
        now = time.time()
        cursor.execute("""
            INSERT INTO agent_reputation (id, agent_id, score, created_at, last_updated)
            VALUES (?, ?, 0.5, ?, ?)
        """, (f"rep-{uuid.uuid4().hex[:12]}", agent_id, now, now))
        conn.commit()

        return {
            "score": 0.5,
            "total_transactions": 0,
            "successful_transactions": 0,
            "total_ratings": 0,
            "rating_sum": 0,
            "last_updated": now
        }


def get_reputation_events(agent_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
    """Get reputation events for agent."""
    ensure_reputation_tables()

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT event_type, change, reason, related_id, timestamp
            FROM reputation_events
            WHERE agent_id = ?
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """, (agent_id, limit, offset))

        return [dict(row) for row in cursor.fetchall()]


def count_reputation_events(agent_id: str) -> int:
    """Count total reputation events for agent."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) as count
            FROM reputation_events
            WHERE agent_id = ?
        """, (agent_id,))

        return cursor.fetchone()["count"]


# ==================== Endpoints ====================

@router.get("", response_model=ReputationResponse)
async def get_reputation(
    user: dict = Depends(get_current_user_unified)
):
    """
    Get agent's current reputation score.

    Requires:
    - X-API-Key header
    - X-Agent-ID header

    Returns:
    - Reputation score (0.0 - 1.0)
    - Reputation tier
    - Transaction statistics
    - Rating information
    """
    agent_id = user.get("agent_id") or user.get("user_id")

    # Get reputation record
    rep = get_or_create_reputation(agent_id)

    score = rep.get("score", 0.5)
    total_transactions = rep.get("total_transactions", 0)
    successful_transactions = rep.get("successful_transactions", 0)
    total_ratings = rep.get("total_ratings", 0)
    rating_sum = rep.get("rating_sum", 0)

    # Calculate derived values
    tier = get_reputation_tier(score)
    success_rate = successful_transactions / total_transactions if total_transactions > 0 else 0.0
    avg_rating = rating_sum / total_ratings if total_ratings > 0 else 0.0

    return ReputationResponse(
        agent_id=agent_id,
        score=round(score, 4),
        tier=tier,
        total_transactions=total_transactions,
        successful_transactions=successful_transactions,
        success_rate=round(success_rate, 4),
        avg_rating=round(avg_rating, 2),
        total_ratings=total_ratings
    )


@router.get("/history", response_model=ReputationHistoryResponse)
async def get_reputation_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user_unified)
):
    """
    Get agent's reputation change history.

    Requires:
    - X-API-Key header
    - X-Agent-ID header

    Query Parameters:
    - limit: Number of events to return (default: 50, max: 200)
    - offset: Number of events to skip (for pagination)

    Returns:
    - Current reputation score
    - List of reputation change events
    - Total event count
    """
    agent_id = user.get("agent_id") or user.get("user_id")

    # Get current reputation
    rep = get_or_create_reputation(agent_id)
    current_score = rep.get("score", 0.5)

    # Get events
    events = get_reputation_events(agent_id, limit, offset)
    total_events = count_reputation_events(agent_id)

    history = [
        ReputationEvent(
            timestamp=e["timestamp"],
            event_type=e["event_type"],
            change=e["change"],
            reason=e["reason"] or "",
            related_id=e["related_id"]
        )
        for e in events
    ]

    return ReputationHistoryResponse(
        agent_id=agent_id,
        current_score=round(current_score, 4),
        history=history,
        total_events=total_events
    )


# ==================== Utility Functions (for internal use) ====================

def record_reputation_event(
    agent_id: str,
    event_type: str,
    change: float,
    reason: str,
    related_id: str = None
) -> None:
    """
    Record a reputation change event and update score.

    This function is for internal use by other modules.

    Event types:
    - transaction_completed: +0.01 to +0.05
    - transaction_failed: -0.02 to -0.1
    - positive_rating: +0.01 per star above 3
    - negative_rating: -0.01 per star below 3
    - dispute_lost: -0.1
    - dispute_won: +0.02
    """
    ensure_reputation_tables()

    now = time.time()

    with get_db() as conn:
        cursor = conn.cursor()

        # Record event
        event_id = f"re-{uuid.uuid4().hex[:12]}"
        cursor.execute("""
            INSERT INTO reputation_events
            (id, agent_id, event_type, change, reason, related_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (event_id, agent_id, event_type, change, reason, related_id, now))

        # Update score (clamped to 0.0 - 1.0)
        cursor.execute("""
            UPDATE agent_reputation
            SET score = MAX(0.0, MIN(1.0, score + ?)),
                last_updated = ?
            WHERE agent_id = ?
        """, (change, now, agent_id))

        # If agent doesn't have reputation record, create one
        if cursor.rowcount == 0:
            cursor.execute("""
                INSERT INTO agent_reputation (id, agent_id, score, created_at, last_updated)
                VALUES (?, ?, MAX(0.0, MIN(1.0, 0.5 + ?)), ?, ?)
            """, (f"rep-{uuid.uuid4().hex[:12]}", agent_id, change, now, now))

        conn.commit()


def update_transaction_stats(agent_id: str, success: bool) -> None:
    """Update transaction statistics for agent."""
    ensure_reputation_tables()

    with get_db() as conn:
        cursor = conn.cursor()

        # Check if record exists
        cursor.execute("SELECT id FROM agent_reputation WHERE agent_id = ?", (agent_id,))
        if cursor.fetchone():
            if success:
                cursor.execute("""
                    UPDATE agent_reputation
                    SET total_transactions = total_transactions + 1,
                        successful_transactions = successful_transactions + 1,
                        last_updated = ?
                    WHERE agent_id = ?
                """, (time.time(), agent_id))
            else:
                cursor.execute("""
                    UPDATE agent_reputation
                    SET total_transactions = total_transactions + 1,
                        last_updated = ?
                    WHERE agent_id = ?
                """, (time.time(), agent_id))
        else:
            # Create new record
            now = time.time()
            cursor.execute("""
                INSERT INTO agent_reputation
                (id, agent_id, score, total_transactions, successful_transactions, created_at, last_updated)
                VALUES (?, ?, 0.5, 1, 1 if ? else 0, ?, ?)
            """, (f"rep-{uuid.uuid4().hex[:12]}", agent_id, success, now, now))

        conn.commit()


def record_rating(agent_id: str, rating: int, transaction_id: str = None) -> None:
    """Record a rating and update reputation accordingly."""
    ensure_reputation_tables()

    # Rating is 1-5, 3 is neutral
    if rating > 3:
        change = (rating - 3) * 0.01  # +0.01 per star above 3
        event_type = "positive_rating"
        reason = f"Received {rating}-star rating"
    elif rating < 3:
        change = (rating - 3) * 0.01  # -0.01 per star below 3
        event_type = "negative_rating"
        reason = f"Received {rating}-star rating"
    else:
        change = 0
        event_type = "neutral_rating"
        reason = f"Received {rating}-star rating"

    # Record event
    record_reputation_event(agent_id, event_type, change, reason, transaction_id)

    # Update rating stats
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE agent_reputation
            SET total_ratings = total_ratings + 1,
                rating_sum = rating_sum + ?,
                last_updated = ?
            WHERE agent_id = ?
        """, (rating, time.time(), agent_id))
        conn.commit()
