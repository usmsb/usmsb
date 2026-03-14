"""
HTTP Protocol Server

This module provides the HTTP server implementation for REST API endpoints.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class HTTPServerConfig:
    """Configuration for HTTP server."""
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    request_timeout: float = 60.0
    keep_alive: bool = True
    workers: int = 1
    ssl_cert: str | None = None
    ssl_key: str | None = None


@dataclass
class HTTPRoute:
    """HTTP route definition."""
    path: str
    method: str
    handler: Callable
    name: str | None = None
    middleware: list[Callable] = field(default_factory=list)


class HTTPRouter:
    """
    HTTP Router for organizing routes.

    Features:
    - Route grouping
    - Middleware support
    - Path parameter extraction
    """

    def __init__(self, prefix: str = ""):
        """
        Initialize the router.

        Args:
            prefix: URL prefix for all routes in this router.
        """
        self._prefix = prefix.rstrip("/")
        self._routes: dict[str, HTTPRoute] = {}
        self._middleware: list[Callable] = []

    def add_route(
        self,
        path: str,
        method: str,
        handler: Callable,
        name: str | None = None,
    ) -> HTTPRoute:
        """
        Add a route.

        Args:
            path: URL path.
            method: HTTP method.
            handler: Async handler function.
            name: Route name.

        Returns:
            The added route.
        """
        full_path = f"{self._prefix}{path}"
        route_key = f"{method}:{full_path}"

        route = HTTPRoute(
            path=full_path,
            method=method.upper(),
            handler=handler,
            name=name,
            middleware=self._middleware.copy(),
        )

        self._routes[route_key] = route
        logger.debug(f"Added route: {method} {full_path}")

        return route

    def get(self, path: str, name: str | None = None):
        """Decorator for GET routes."""
        def decorator(handler: Callable) -> Callable:
            self.add_route(path, "GET", handler, name)
            return handler
        return decorator

    def post(self, path: str, name: str | None = None):
        """Decorator for POST routes."""
        def decorator(handler: Callable) -> Callable:
            self.add_route(path, "POST", handler, name)
            return handler
        return decorator

    def put(self, path: str, name: str | None = None):
        """Decorator for PUT routes."""
        def decorator(handler: Callable) -> Callable:
            self.add_route(path, "PUT", handler, name)
            return handler
        return decorator

    def delete(self, path: str, name: str | None = None):
        """Decorator for DELETE routes."""
        def decorator(handler: Callable) -> Callable:
            self.add_route(path, "DELETE", handler, name)
            return handler
        return decorator

    def middleware(self, middleware_func: Callable) -> Callable:
        """Add middleware to the router."""
        self._middleware.append(middleware_func)
        return middleware_func

    def get_routes(self) -> dict[str, HTTPRoute]:
        """Get all routes."""
        return self._routes.copy()

    def include_router(self, router: "HTTPRouter", prefix: str = "") -> None:
        """
        Include routes from another router.

        Args:
            router: Router to include.
            prefix: Additional prefix for included routes.
        """
        additional_prefix = f"{self._prefix}{prefix}"

        for _route_key, route in router.get_routes().items():
            # Remove original prefix and add new one
            original_path = route.path
            if router._prefix and original_path.startswith(router._prefix):
                new_path = f"{additional_prefix}{original_path[len(router._prefix):]}"
            else:
                new_path = f"{additional_prefix}{original_path}"

            new_route_key = f"{route.method}:{new_path}"

            self._routes[new_route_key] = HTTPRoute(
                path=new_path,
                method=route.method,
                handler=route.handler,
                name=route.name,
                middleware=self._middleware + route.middleware,
            )


class HTTPServer:
    """
    HTTP Server for REST API.

    This server provides:
    - RESTful API endpoints
    - Route handling with middleware
    - CORS support
    - Request/Response handling

    Features:
    - Async request handling
    - Middleware support
    - Route grouping with routers
    - Error handling
    """

    def __init__(
        self,
        config: HTTPServerConfig | None = None,
        host: str = "0.0.0.0",
        port: int = 8080,
    ):
        """
        Initialize the HTTP server.

        Args:
            config: Server configuration.
            host: Host to bind to (overrides config).
            port: Port to listen on (overrides config).
        """
        self._config = config or HTTPServerConfig(host=host, port=port)
        self._router = HTTPRouter()
        self._server: Any | None = None
        self._running = False
        self._startup_handlers: list[Callable] = []
        self._shutdown_handlers: list[Callable] = []

        logger.info(f"HTTPServer initialized on {self._config.host}:{self._config.port}")

    @property
    def config(self) -> HTTPServerConfig:
        """Get server configuration."""
        return self._config

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running

    # ========== Route Registration ==========

    def route(self, path: str, method: str, name: str | None = None):
        """Decorator for adding routes."""
        return self._router.get.__wrapped__.__get__(self._router, type(self._router))
        # Simpler: use get, post, put, delete directly

    def get(self, path: str, name: str | None = None):
        """Decorator for GET routes."""
        return self._router.get(path, name)

    def post(self, path: str, name: str | None = None):
        """Decorator for POST routes."""
        return self._router.post(path, name)

    def put(self, path: str, name: str | None = None):
        """Decorator for PUT routes."""
        return self._router.put(path, name)

    def delete(self, path: str, name: str | None = None):
        """Decorator for DELETE routes."""
        return self._router.delete(path, name)

    def add_router(self, router: HTTPRouter, prefix: str = "") -> None:
        """
        Add a router to the server.

        Args:
            router: Router to add.
            prefix: URL prefix for the router.
        """
        self._router.include_router(router, prefix)

    def middleware(self, middleware_func: Callable) -> Callable:
        """Add middleware to the server."""
        return self._router.middleware(middleware_func)

    # ========== Lifecycle Handlers ==========

    def on_startup(self, handler: Callable) -> Callable:
        """Register a startup handler."""
        self._startup_handlers.append(handler)
        return handler

    def on_shutdown(self, handler: Callable) -> Callable:
        """Register a shutdown handler."""
        self._shutdown_handlers.append(handler)
        return handler

    # ========== Server Control ==========

    async def start(self) -> bool:
        """
        Start the HTTP server.

        Returns:
            True if server started successfully.
        """
        try:
            logger.info(f"Starting HTTP server on {self._config.host}:{self._config.port}")

            # Run startup handlers
            for handler in self._startup_handlers:
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()

            # In real implementation, use aiohttp, uvicorn, or FastAPI
            # For now, simulate server startup
            self._running = True
            self._server = {
                "host": self._config.host,
                "port": self._config.port,
                "started_at": time.time(),
            }

            logger.info(f"HTTP server started on {self._config.host}:{self._config.port}")
            return True

        except Exception as e:
            logger.error(f"Failed to start HTTP server: {e}")
            return False

    async def stop(self) -> None:
        """Stop the HTTP server."""
        if not self._running:
            return

        logger.info("Stopping HTTP server")

        # Run shutdown handlers
        for handler in self._shutdown_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()
            except Exception as e:
                logger.error(f"Shutdown handler error: {e}")

        self._running = False
        self._server = None

        logger.info("HTTP server stopped")

    async def serve_forever(self) -> None:
        """Run the server until interrupted."""
        if not self._running:
            await self.start()

        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            await self.stop()

    # ========== Request Handling ==========

    async def handle_request(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Handle an incoming HTTP request.

        Args:
            method: HTTP method.
            path: Request path.
            headers: Request headers.
            body: Request body.

        Returns:
            Response dictionary.
        """
        route_key = f"{method.upper()}:{path}"

        route = self._router.get_routes().get(route_key)

        if not route:
            return {
                "status_code": 404,
                "body": {"error": "Not Found"},
            }

        try:
            # Build request context
            context = {
                "method": method,
                "path": path,
                "headers": headers,
                "body": body or {},
                "query": {},
                "path_params": {},
            }

            # Run middleware
            for middleware in route.middleware:
                if asyncio.iscoroutinefunction(middleware):
                    context = await middleware(context)
                else:
                    context = middleware(context)

            # Run handler
            if asyncio.iscoroutinefunction(route.handler):
                result = await route.handler(context)
            else:
                result = route.handler(context)

            # Format response
            if isinstance(result, dict):
                if "status_code" in result:
                    return result
                return {"status_code": 200, "body": result}
            else:
                return {"status_code": 200, "body": {"result": result}}

        except Exception as e:
            logger.error(f"Request handler error: {e}")
            return {
                "status_code": 500,
                "body": {"error": str(e)},
            }

    # ========== Utility Methods ==========

    def get_routes(self) -> dict[str, HTTPRoute]:
        """Get all registered routes."""
        return self._router.get_routes()

    def get_server_info(self) -> dict[str, Any]:
        """Get server information."""
        return {
            "host": self._config.host,
            "port": self._config.port,
            "running": self._running,
            "routes": len(self._router.get_routes()),
            "uptime": time.time() - self._server["started_at"] if self._server else 0,
        }
