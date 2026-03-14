"""
BrowserContext - User-isolated browser session.

This module provides a browser context for each user with:
- Isolated user data directory (cookies, localStorage, etc.)
- Automatic idle timeout cleanup
- Playwright-based browser automation
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BrowserResult:
    """Result of a browser operation."""
    success: bool
    message: str
    data: dict[str, Any] | None = None
    error: str | None = None


class BrowserContext:
    """
    Browser context for user-isolated browser sessions.

    Each user gets their own browser context with isolated:
    - Cookies
    - LocalStorage
    - SessionStorage
    - Download directory
    - Cache

    Features:
    - Automatic idle timeout (default 10 minutes)
    - Lazy initialization (browser starts on first use)
    - Graceful shutdown
    - Error handling with friendly messages
    """

    def __init__(
        self,
        wallet_address: str,
        data_dir: str = "/data/users",
        idle_timeout: int = 600,
    ):
        """
        Initialize browser context for a user.

        Args:
            wallet_address: User's wallet address (used as unique identifier)
            data_dir: Base directory for user data
            idle_timeout: Seconds of inactivity before auto-closing (default 600 = 10 min)
        """
        self.wallet_address = wallet_address
        self._idle_timeout = idle_timeout

        # User-specific data directory for browser
        self.user_data_dir = Path(data_dir) / wallet_address / "browser" / "user_data"
        self.download_dir = Path(data_dir) / wallet_address / "browser" / "downloads"

        # Playwright components (initialized lazily)
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

        # Activity tracking
        self._last_active = time.time()
        self._is_initialized = False
        self._is_closed = False

        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def _ensure_initialized(self) -> None:
        """Ensure browser is initialized (lazy initialization)."""
        if self._is_closed:
            raise RuntimeError("Browser context has been closed")

        if self._is_initialized:
            return

        try:
            from playwright.async_api import async_playwright

            # Create directories if they don't exist
            self.user_data_dir.mkdir(parents=True, exist_ok=True)
            self.download_dir.mkdir(parents=True, exist_ok=True)

            # Start playwright
            self._playwright = await async_playwright().start()

            # Use launch_persistent_context for user data isolation
            # This creates a browser context with persistent storage
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                headless=True,
                accept_downloads=True,
                java_script_enabled=True,
                args=[
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ],
            )

            # Get or create default page
            pages = self._context.pages
            if pages:
                self._page = pages[0]
            else:
                self._page = await self._context.new_page()

            self._is_initialized = True
            logger.info(
                f"Browser context initialized for user {self.wallet_address} "
                f"at {self.user_data_dir}"
            )

        except ImportError:
            raise RuntimeError(
                "Playwright not installed. "
                "Install with: pip install playwright && playwright install chromium"
            )
        except Exception as e:
            logger.error(f"Failed to initialize browser context: {e}")
            await self._cleanup_resources()
            raise

    def update_activity(self) -> None:
        """Update the last activity timestamp."""
        self._last_active = time.time()

    async def check_idle(self) -> bool:
        """
        Check if browser context is idle beyond timeout.

        Returns:
            True if idle time exceeds timeout, False otherwise
        """
        idle_time = time.time() - self._last_active
        return idle_time > self._idle_timeout

    async def is_active(self) -> bool:
        """
        Check if browser context is active.

        Returns:
            True if browser is initialized and not closed, False otherwise
        """
        if self._is_closed or not self._is_initialized:
            return False

        # Check if page is still connected
        if self._page and self._page.is_closed():
            return False

        return True

    async def open(self, url: str, headless: bool = True) -> dict:
        """
        Open browser and navigate to URL.

        Args:
            url: URL to navigate to
            headless: Whether to run browser in headless mode (default True)

        Returns:
            Dict with success status and message
        """
        self.update_activity()

        async with self._lock:
            try:
                await self._ensure_initialized()

                # Validate URL
                if not url or not url.strip():
                    return {
                        "status": "error",
                        "message": "URL cannot be empty",
                        "error": "Invalid URL",
                    }

                if not (url.startswith("http://") or url.startswith("https://")):
                    return {
                        "status": "error",
                        "message": f"Invalid URL scheme: {url}",
                        "error": "Only HTTP and HTTPS URLs are supported",
                    }

                # Navigate to URL
                await self._page.goto(url, timeout=30000, wait_until="domcontentloaded")

                logger.info(f"Browser opened URL: {url} for user {self.wallet_address}")

                return {
                    "status": "success",
                    "message": f"Successfully opened {url}",
                    "url": url,
                    "title": await self._page.title(),
                }

            except Exception as e:
                logger.error(f"Failed to open URL {url}: {e}")
                return {
                    "status": "error",
                    "message": f"Failed to open {url}",
                    "error": str(e),
                }

    async def click(self, selector: str, timeout: int = 30000) -> dict:
        """
        Click an element on the page.

        Args:
            selector: CSS selector for the element
            timeout: Maximum time to wait for element (default 30s)

        Returns:
            Dict with success status
        """
        self.update_activity()

        async with self._lock:
            try:
                await self._ensure_initialized()

                if not self._page or self._page.is_closed():
                    return {
                        "status": "error",
                        "message": "Browser page is not available",
                        "error": "Page closed",
                    }

                await self._page.click(selector, timeout=timeout)

                logger.info(f"Clicked element: {selector}")

                return {
                    "status": "success",
                    "message": f"Successfully clicked element: {selector}",
                }

            except Exception as e:
                logger.error(f"Failed to click element {selector}: {e}")
                return {
                    "status": "error",
                    "message": f"Failed to click element: {selector}",
                    "error": str(e),
                }

    async def fill(self, selector: str, value: str, timeout: int = 30000) -> dict:
        """
        Fill a form input field.

        Args:
            selector: CSS selector for the input element
            value: Value to fill
            timeout: Maximum time to wait for element (default 30s)

        Returns:
            Dict with success status
        """
        self.update_activity()

        async with self._lock:
            try:
                await self._ensure_initialized()

                if not self._page or self._page.is_closed():
                    return {
                        "status": "error",
                        "message": "Browser page is not available",
                        "error": "Page closed",
                    }

                await self._page.fill(selector, value, timeout=timeout)

                logger.info(f"Filled {selector} with value length: {len(value)}")

                return {
                    "status": "success",
                    "message": f"Successfully filled element: {selector}",
                    "selector": selector,
                    "value_length": len(value),
                }

            except Exception as e:
                logger.error(f"Failed to fill element {selector}: {e}")
                return {
                    "status": "error",
                    "message": f"Failed to fill element: {selector}",
                    "error": str(e),
                }

    async def get_content(
        self, selector: str | None = None, format: str = "text"
    ) -> dict:
        """
        Get page content.

        Args:
            selector: Optional CSS selector to get content from specific element.
                     If None, gets the entire page content.
            format: Content format - "text" or "html" (default "text")

        Returns:
            Dict with content
        """
        self.update_activity()

        async with self._lock:
            try:
                await self._ensure_initialized()

                if not self._page or self._page.is_closed():
                    return {
                        "status": "error",
                        "message": "Browser page is not available",
                        "error": "Page closed",
                    }

                if selector:
                    if format == "html":
                        content = await self._page.inner_html(selector)
                    else:
                        content = await self._page.inner_text(selector)
                else:
                    if format == "html":
                        content = await self._page.content()
                    else:
                        content = await self._page.inner_text("body")

                # Limit content length
                max_length = 100000
                content_str = str(content)
                truncated = len(content_str) > max_length

                return {
                    "status": "success",
                    "message": f"Successfully retrieved content (truncated: {truncated})",
                    "content": content_str[:max_length],
                    "truncated": truncated,
                    "length": len(content_str),
                    "url": self._page.url if self._page else None,
                }

            except Exception as e:
                logger.error(f"Failed to get content: {e}")
                return {
                    "status": "error",
                    "message": "Failed to retrieve page content",
                    "error": str(e),
                }

    async def screenshot(self, path: str | None = None) -> dict:
        """
        Take a screenshot of the current page.

        Args:
            path: Optional file path to save screenshot. If None, returns base64.

        Returns:
            Dict with screenshot data or file path
        """
        self.update_activity()

        async with self._lock:
            try:
                await self._ensure_initialized()

                if not self._page or self._page.is_closed():
                    return {
                        "status": "error",
                        "message": "Browser page is not available",
                        "error": "Page closed",
                    }

                if path:
                    # Ensure directory exists
                    Path(path).parent.mkdir(parents=True, exist_ok=True)
                    await self._page.screenshot(path=path)

                    logger.info(f"Screenshot saved to: {path}")

                    return {
                        "status": "success",
                        "message": f"Screenshot saved to {path}",
                        "path": path,
                    }
                else:
                    # Return base64 encoded screenshot
                    import base64

                    screenshot_bytes = await self._page.screenshot()
                    b64 = base64.b64encode(screenshot_bytes).decode()

                    logger.info(f"Screenshot captured (size: {len(screenshot_bytes)} bytes)")

                    return {
                        "status": "success",
                        "message": "Screenshot captured",
                        "screenshot": b64,
                        "size": len(screenshot_bytes),
                    }

            except Exception as e:
                logger.error(f"Failed to take screenshot: {e}")
                return {
                    "status": "error",
                    "message": "Failed to take screenshot",
                    "error": str(e),
                }

    async def evaluate(self, script: str) -> dict:
        """
        Evaluate JavaScript in the browser context.

        Args:
            script: JavaScript code to evaluate

        Returns:
            Dict with evaluation result
        """
        self.update_activity()

        async with self._lock:
            try:
                await self._ensure_initialized()

                if not self._page or self._page.is_closed():
                    return {
                        "status": "error",
                        "message": "Browser page is not available",
                        "error": "Page closed",
                    }

                result = await self._page.evaluate(script)

                return {
                    "status": "success",
                    "message": "JavaScript evaluated successfully",
                    "result": result,
                }

            except Exception as e:
                logger.error(f"Failed to evaluate JavaScript: {e}")
                return {
                    "status": "error",
                    "message": "Failed to evaluate JavaScript",
                    "error": str(e),
                }

    async def wait_for_selector(
        self, selector: str, timeout: int = 30000, state: str = "visible"
    ) -> dict:
        """
        Wait for a selector to appear in the DOM.

        Args:
            selector: CSS selector to wait for
            timeout: Maximum time to wait (default 30s)
            state: State to wait for - "visible", "attached", or "hidden"

        Returns:
            Dict with success status
        """
        self.update_activity()

        async with self._lock:
            try:
                await self._ensure_initialized()

                if not self._page or self._page.is_closed():
                    return {
                        "status": "error",
                        "message": "Browser page is not available",
                        "error": "Page closed",
                    }

                await self._page.wait_for_selector(selector, timeout=timeout, state=state)

                return {
                    "status": "success",
                    "message": f"Element {selector} found",
                    "selector": selector,
                }

            except Exception as e:
                logger.error(f"Failed to wait for selector {selector}: {e}")
                return {
                    "status": "error",
                    "message": f"Element {selector} not found within timeout",
                    "error": str(e),
                }

    async def get_url(self) -> dict:
        """
        Get the current page URL.

        Returns:
            Dict with current URL
        """
        self.update_activity()

        async with self._lock:
            try:
                await self._ensure_initialized()

                if not self._page or self._page.is_closed():
                    return {
                        "status": "error",
                        "message": "Browser page is not available",
                        "error": "Page closed",
                    }

                url = self._page.url

                return {
                    "status": "success",
                    "message": "Current URL retrieved",
                    "url": url,
                }

            except Exception as e:
                logger.error(f"Failed to get URL: {e}")
                return {
                    "status": "error",
                    "message": "Failed to get current URL",
                    "error": str(e),
                }

    async def get_cookies(self) -> dict:
        """
        Get all cookies for the current browser context.

        Returns:
            Dict with cookies list
        """
        self.update_activity()

        async with self._lock:
            try:
                await self._ensure_initialized()

                if not self._context:
                    return {
                        "status": "error",
                        "message": "Browser context is not available",
                        "error": "Context not initialized",
                    }

                cookies = await self._context.cookies()

                return {
                    "status": "success",
                    "message": f"Retrieved {len(cookies)} cookies",
                    "cookies": cookies,
                    "count": len(cookies),
                }

            except Exception as e:
                logger.error(f"Failed to get cookies: {e}")
                return {
                    "status": "error",
                    "message": "Failed to retrieve cookies",
                    "error": str(e),
                }

    async def close(self) -> None:
        """Close the browser context and release resources."""
        if self._is_closed:
            return

        self._is_closed = True

        async with self._lock:
            await self._cleanup_resources()

        logger.info(f"Browser context closed for user {self.wallet_address}")

    async def _cleanup_resources(self) -> None:
        """Clean up all browser resources."""
        try:
            # Close page (if exists and not already closed)
            if self._page and not self._page.is_closed():
                try:
                    await self._page.close()
                except Exception as e:
                    logger.warning(f"Error closing page: {e}")
                finally:
                    self._page = None

            # Close context (persistent context handles browser lifecycle)
            if self._context:
                try:
                    await self._context.close()
                except Exception as e:
                    logger.warning(f"Error closing context: {e}")
                finally:
                    self._context = None

            # Stop playwright
            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception as e:
                    logger.warning(f"Error stopping playwright: {e}")
                finally:
                    self._playwright = None

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        finally:
            self._is_initialized = False

    def __del__(self):
        """Destructor - ensure resources are cleaned up."""
        if not self._is_closed and self._is_initialized:
            logger.warning(
                f"BrowserContext for {self.wallet_address} was not properly closed. "
                "Use await close() for proper cleanup."
            )

    @property
    def idle_timeout(self) -> int:
        """Get the idle timeout in seconds."""
        return self._idle_timeout

    @property
    def last_active_time(self) -> float:
        """Get the last activity timestamp."""
        return self._last_active


class BrowserContextManager:
    """
    Manager for multiple browser contexts.

    Manages lifecycle of browser contexts for multiple users.
    """

    def __init__(self, data_dir: str = "/data/users"):
        """
        Initialize browser context manager.

        Args:
            data_dir: Base directory for user data
        """
        self.data_dir = data_dir
        self._contexts: dict[str, BrowserContext] = {}
        self._lock = asyncio.Lock()

    async def get_context(
        self, wallet_address: str, idle_timeout: int = 600
    ) -> BrowserContext:
        """
        Get or create a browser context for a user.

        Args:
            wallet_address: User's wallet address
            idle_timeout: Idle timeout in seconds

        Returns:
            BrowserContext for the user
        """
        async with self._lock:
            if wallet_address not in self._contexts:
                self._contexts[wallet_address] = BrowserContext(
                    wallet_address=wallet_address,
                    data_dir=self.data_dir,
                    idle_timeout=idle_timeout,
                )

            return self._contexts[wallet_address]

    async def close_context(self, wallet_address: str) -> bool:
        """
        Close a browser context for a user.

        Args:
            wallet_address: User's wallet address

        Returns:
            True if context was found and closed, False otherwise
        """
        async with self._lock:
            if wallet_address in self._contexts:
                context = self._contexts.pop(wallet_address)
                await context.close()
                return True
            return False

    async def close_all(self) -> None:
        """Close all browser contexts."""
        async with self._lock:
            contexts = self._contexts.copy()
            self._contexts.clear()

            for context in contexts.values():
                await context.close()

    async def cleanup_idle(self) -> int:
        """
        Close all idle browser contexts.

        Returns:
            Number of contexts closed
        """
        async with self._lock:
            idle_contexts = []

            for wallet_address, context in self._contexts.items():
                if await context.check_idle():
                    idle_contexts.append(wallet_address)

            for wallet_address in idle_contexts:
                context = self._contexts.pop(wallet_address)
                await context.close()

            return len(idle_contexts)

    async def get_active_count(self) -> int:
        """Get the number of active browser contexts."""
        async with self._lock:
            count = 0
            for context in self._contexts.values():
                if await context.is_active():
                    count += 1
            return count

    async def get_all_contexts(self) -> dict[str, dict[str, Any]]:
        """
        Get status of all browser contexts.

        Returns:
            Dictionary mapping wallet addresses to context status
        """
        async with self._lock:
            status = {}
            for wallet_address, context in self._contexts.items():
                status[wallet_address] = {
                    "active": await context.is_active(),
                    "idle": await context.check_idle(),
                    "last_active": context.last_active_time,
                    "user_data_dir": str(context.user_data_dir),
                }
            return status
