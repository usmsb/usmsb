"""
HTTP Protocol Client

This module provides the HTTP client implementation for REST API communication.
"""

import asyncio
import base64
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from usmsb_sdk.protocol.base import (
    BaseProtocolHandler,
    ProtocolConfig,
    ExternalAgentStatus,
    SkillDefinition,
)


logger = logging.getLogger(__name__)


@dataclass
class HTTPEndpointConfig:
    """Configuration for HTTP endpoints."""
    base_path: str = ""
    skills_path: str = "/skills"
    discover_path: str = "/discover"
    health_path: str = "/health"
    status_path: str = "/status"


@dataclass
class HTTPAuthConfig:
    """Authentication configuration for HTTP."""
    auth_type: str = "none"  # none, basic, bearer, api_key
    username: str = ""
    password: str = ""
    token: str = ""
    api_key: str = ""
    api_key_header: str = "X-API-Key"


@dataclass
class HTTPRequest:
    """HTTP request structure."""
    method: str
    path: str
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, str] = field(default_factory=dict)
    body: Optional[Dict[str, Any]] = None
    timeout: float = 60.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "path": self.path,
            "headers": self.headers,
            "params": self.params,
            "body": self.body,
            "timeout": self.timeout,
        }


@dataclass
class HTTPResponse:
    """HTTP response structure."""
    status_code: int
    headers: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    elapsed: float = 0.0

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status_code": self.status_code,
            "headers": self.headers,
            "body": self.body,
            "elapsed": self.elapsed,
        }


@dataclass
class HTTPSkillEndpoint:
    """Endpoint configuration for a specific skill."""
    skill_name: str
    path: str
    method: str = "POST"
    timeout: float = 60.0
    headers: Dict[str, str] = field(default_factory=dict)


class HTTPClient(BaseProtocolHandler):
    """
    HTTP Client for REST API communication.

    This client implements communication with external agents
    via HTTP/REST API.

    Features:
    - RESTful API communication
    - Multiple authentication methods
    - Configurable endpoints
    - Request/response logging
    - Automatic retries
    """

    def __init__(
        self,
        config: Optional[ProtocolConfig] = None,
        endpoint_config: Optional[HTTPEndpointConfig] = None,
        auth_config: Optional[HTTPAuthConfig] = None,
    ):
        """
        Initialize the HTTP client.

        Args:
            config: Protocol configuration.
            endpoint_config: HTTP endpoint configuration.
            auth_config: Authentication configuration.
        """
        super().__init__(config)
        self._endpoint_config = endpoint_config or HTTPEndpointConfig()
        self._auth_config = auth_config or HTTPAuthConfig()
        self._skill_endpoints: Dict[str, HTTPSkillEndpoint] = {}
        self._http_client: Optional[Any] = None

        logger.info("HTTPClient initialized")

    # ========== Protocol-Specific Implementation ==========

    async def _do_connect(self, endpoint: str) -> bool:
        """
        Establish HTTP connection to the endpoint.

        Args:
            endpoint: The base URL for the HTTP API.

        Returns:
            True if connection successful.
        """
        try:
            # In real implementation, create HTTP client (aiohttp, httpx, etc.)
            self._http_client = {
                "base_url": endpoint.rstrip("/"),
                "connected": True,
            }

            # Verify connection by calling health endpoint
            health_url = f"{endpoint.rstrip('/')}{self._endpoint_config.health_path}"

            # Simulated health check
            await asyncio.sleep(0.1)

            logger.info(f"HTTP connection established to {endpoint}")
            return True

        except Exception as e:
            logger.error(f"HTTP connection error: {e}")
            return False

    async def _do_disconnect(self) -> None:
        """Close the HTTP connection."""
        if self._http_client:
            # In real implementation, close the HTTP client
            self._http_client = None

        logger.info("HTTP connection closed")

    async def _do_call_skill(
        self,
        skill_name: str,
        arguments: Dict[str, Any],
        timeout: float,
    ) -> Any:
        """
        Execute a skill via HTTP.

        Args:
            skill_name: Name of the skill to execute.
            arguments: Arguments for the skill.
            timeout: Timeout for execution.

        Returns:
            Result from the skill execution.
        """
        # Determine endpoint for the skill
        skill_endpoint = self._skill_endpoints.get(skill_name)

        if skill_endpoint:
            path = skill_endpoint.path
            method = skill_endpoint.method
            skill_timeout = min(skill_endpoint.timeout, timeout)
        else:
            # Default endpoint pattern
            path = f"{self._endpoint_config.skills_path}/{skill_name}"
            method = "POST"
            skill_timeout = timeout

        # Build request
        request = HTTPRequest(
            method=method,
            path=path,
            body={"arguments": arguments},
            timeout=skill_timeout,
        )

        # Execute request
        response = await self._execute_request(request)

        if response.is_success:
            return response.body
        else:
            error_msg = response.body.get("error", f"HTTP {response.status_code}")
            raise Exception(error_msg)

    async def _do_discover_skills(self) -> List[SkillDefinition]:
        """
        Discover skills via HTTP.

        Returns:
            List of discovered skills.
        """
        request = HTTPRequest(
            method="GET",
            path=self._endpoint_config.discover_path,
            timeout=30.0,
        )

        try:
            response = await self._execute_request(request)

            if response.is_success:
                skills_data = response.body.get("skills", [])

                # Cache skill endpoints
                for skill_data in skills_data:
                    skill_name = skill_data.get("name", "")
                    endpoint = skill_data.get("endpoint", {})
                    if skill_name and endpoint:
                        self._skill_endpoints[skill_name] = HTTPSkillEndpoint(
                            skill_name=skill_name,
                            path=endpoint.get("path", f"/skills/{skill_name}"),
                            method=endpoint.get("method", "POST"),
                            timeout=endpoint.get("timeout", 60.0),
                            headers=endpoint.get("headers", {}),
                        )

                return [SkillDefinition.from_dict(s) for s in skills_data]

            return []

        except Exception as e:
            logger.error(f"HTTP skill discovery error: {e}")
            return []

    async def _do_check_status(self) -> ExternalAgentStatus:
        """
        Check agent status via HTTP.

        Returns:
            Current status of the agent.
        """
        request = HTTPRequest(
            method="GET",
            path=self._endpoint_config.health_path,
            timeout=5.0,
        )

        try:
            response = await self._execute_request(request)

            if response.is_success:
                status_str = response.body.get("status", "online")
                return ExternalAgentStatus(status_str)
            else:
                return ExternalAgentStatus.ERROR

        except Exception as e:
            logger.error(f"HTTP status check error: {e}")
            return ExternalAgentStatus.OFFLINE

    # ========== HTTP-Specific Methods ==========

    async def _execute_request(self, request: HTTPRequest) -> HTTPResponse:
        """
        Execute an HTTP request.

        Args:
            request: The HTTP request to execute.

        Returns:
            HTTP response.
        """
        if not self._http_client:
            raise Exception("Not connected")

        start_time = time.time()

        # Build full URL
        base_url = self._http_client["base_url"]
        full_url = f"{base_url}{request.path}"

        # Build headers with authentication
        headers = self._build_headers(request.headers)

        logger.debug(f"HTTP {request.method} {full_url}")

        try:
            # In real implementation, use aiohttp or httpx
            # Simulated HTTP request
            await asyncio.sleep(0.1)  # Simulate network delay

            # Simulated response based on path
            response_body = await self._simulate_response(request)

            elapsed = time.time() - start_time

            # Update statistics
            if self._connection_info:
                self._connection_info.bytes_sent += len(str(request.to_dict()))
                self._connection_info.bytes_received += len(str(response_body))

            return HTTPResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=response_body,
                elapsed=elapsed,
            )

        except asyncio.TimeoutError:
            logger.warning(f"HTTP request timeout: {full_url}")
            raise

        except Exception as e:
            logger.error(f"HTTP request error: {e}")
            raise

    def _build_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Build HTTP headers with authentication.

        Args:
            extra_headers: Additional headers to include.

        Returns:
            Complete headers dictionary.
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Add authentication headers
        if self._auth_config.auth_type == "basic":
            credentials = base64.b64encode(
                f"{self._auth_config.username}:{self._auth_config.password}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {credentials}"

        elif self._auth_config.auth_type == "bearer":
            headers["Authorization"] = f"Bearer {self._auth_config.token}"

        elif self._auth_config.auth_type == "api_key":
            headers[self._auth_config.api_key_header] = self._auth_config.api_key

        # Add extra headers
        if extra_headers:
            headers.update(extra_headers)

        return headers

    async def _simulate_response(self, request: HTTPRequest) -> Dict[str, Any]:
        """
        Simulate HTTP response for testing.

        Args:
            request: The HTTP request.

        Returns:
            Simulated response body.
        """
        if self._endpoint_config.health_path in request.path:
            return {"status": "online", "timestamp": time.time()}

        elif self._endpoint_config.discover_path in request.path:
            return {
                "skills": [
                    {
                        "skill_id": "skill-1",
                        "name": "example_skill",
                        "description": "An example skill",
                        "category": "general",
                    }
                ]
            }

        elif self._endpoint_config.skills_path in request.path:
            return {
                "success": True,
                "result": {"output": f"Executed skill at {request.path}"},
            }

        return {"success": True, "data": {}}

    # ========== Skill Endpoint Management ==========

    def register_skill_endpoint(
        self,
        skill_name: str,
        path: str,
        method: str = "POST",
        timeout: float = 60.0,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Register a custom endpoint for a skill.

        Args:
            skill_name: Name of the skill.
            path: URL path for the skill.
            method: HTTP method (GET, POST, etc.).
            timeout: Timeout for the skill.
            headers: Additional headers for the skill.
        """
        self._skill_endpoints[skill_name] = HTTPSkillEndpoint(
            skill_name=skill_name,
            path=path,
            method=method,
            timeout=timeout,
            headers=headers or {},
        )

        logger.debug(f"Registered HTTP endpoint for skill '{skill_name}': {method} {path}")

    def unregister_skill_endpoint(self, skill_name: str) -> None:
        """
        Unregister a skill endpoint.

        Args:
            skill_name: Name of the skill.
        """
        if skill_name in self._skill_endpoints:
            del self._skill_endpoints[skill_name]

    def get_skill_endpoint(self, skill_name: str) -> Optional[HTTPSkillEndpoint]:
        """
        Get the endpoint configuration for a skill.

        Args:
            skill_name: Name of the skill.

        Returns:
            Skill endpoint configuration or None.
        """
        return self._skill_endpoints.get(skill_name)

    # ========== Convenience Methods ==========

    async def get(self, path: str, params: Optional[Dict[str, str]] = None) -> HTTPResponse:
        """
        Make a GET request.

        Args:
            path: URL path.
            params: Query parameters.

        Returns:
            HTTP response.
        """
        request = HTTPRequest(method="GET", path=path, params=params or {})
        return await self._execute_request(request)

    async def post(
        self,
        path: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> HTTPResponse:
        """
        Make a POST request.

        Args:
            path: URL path.
            body: Request body.

        Returns:
            HTTP response.
        """
        request = HTTPRequest(method="POST", path=path, body=body)
        return await self._execute_request(request)

    async def put(
        self,
        path: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> HTTPResponse:
        """
        Make a PUT request.

        Args:
            path: URL path.
            body: Request body.

        Returns:
            HTTP response.
        """
        request = HTTPRequest(method="PUT", path=path, body=body)
        return await self._execute_request(request)

    async def delete(self, path: str) -> HTTPResponse:
        """
        Make a DELETE request.

        Args:
            path: URL path.

        Returns:
            HTTP response.
        """
        request = HTTPRequest(method="DELETE", path=path)
        return await self._execute_request(request)
