"""
Browser context module for multi-user isolation.

This module provides browser isolation capabilities where each user
has their own independent browser session with isolated:
- Cookies and localStorage
- Download directory
- User data directory
"""

from .browser_context import BrowserContext, BrowserContextManager

__all__ = ["BrowserContext", "BrowserContextManager"]
