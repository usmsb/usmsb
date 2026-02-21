"""
Session management module for multi-user isolation.

This module provides:
- UserSession: Per-user isolated session context
- SessionConfig: Configuration for user sessions
- SessionManager: Centralized session lifecycle management

Usage:
    from usmsb_sdk.platform.external.meta_agent.session import UserSession, SessionConfig

    # Create a custom session configuration
    config = SessionConfig(
        session_idle_timeout=3600,  # 1 hour
        max_code_timeout=60,         # 1 minute
        max_memory_mb=512
    )

    # Create a new user session
    session = UserSession(
        wallet_address="0xABC123...",
        node_id="node-001",
        config=config
    )
    await session.init()
"""

from .session_manager import SessionManager
from .user_session import SessionConfig, UserSession, UserProfile

__all__ = [
    "SessionManager",
    "SessionConfig",
    "UserSession",
    "UserProfile",
]
