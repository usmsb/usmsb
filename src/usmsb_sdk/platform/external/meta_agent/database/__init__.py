"""
Database Module

Provides user-isolated database management for the Meta Agent.
"""

from .user_database import (
    Conversation,
    ConversationSummary,
    ImportantMemory,
    KnowledgeItem,
    Message,
    UserDatabase,
    UserProfile,
    create_user_database,
)

__all__ = [
    "UserDatabase",
    "Conversation",
    "Message",
    "UserProfile",
    "ConversationSummary",
    "ImportantMemory",
    "KnowledgeItem",
    "create_user_database",
]
