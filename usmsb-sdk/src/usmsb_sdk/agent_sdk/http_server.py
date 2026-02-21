"""
HTTP REST Server for Agents

Provides HTTP REST API capability for Agents using FastAPI:
- Platform registration
- HTTP REST endpoints (/invoke, /heartbeat, /health, /chat, /message)
- CORS cross-origin support
- Seamless integration with BaseAgent
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional, TYPE_CHECKING

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

if TYPE_CHECKING:
    from usmsb_sdk.agent_sdk.base_agent import BaseAgent

logger = logging.getLogger(__name__)


# Pydantic models for request/response validation
if FASTAPI_AVAILABLE:
    class InvokeRequest(BaseModel):
        """Request model for /invoke endpoint"""
        method: str = "chat"
        params: Dict[str, Any] = {}
        sender_id: str = "unknown"

    class ChatRequest(BaseModel):
        """Request model for /chat endpoint"""
        message: Optional[str] = None
        input: Optional[str] = None
        sender_id: str = "unknown"

    class HeartbeatRequest(BaseModel):
        """Request model for /heartbeat endpoint"""
        data: Optional[Dict[str, Any]] = None

    class MessageRequest(BaseModel):
        """Request model for /message endpoint"""
        message_type: Optional[str] = None
        message_id: Optional[str] = None
        sender_id: Optional[str] = None
        timestamp: Optional[str] = None
        payload: Optional[Dict[str, Any]] = None


class HTTPServer:
    """
    HTTP REST Server for Agent

    Provides HTTP endpoints for Agents, enabling direct access from frontends
    and other agents.

    Usage:
        server = HTTPServer(agent, port=5001)
        await server.start()

    Endpoints:
        GET  /health     - Health check
        GET  /           - Agent info
        POST /invoke     - Invoke skill
        POST /chat       - Chat message
        POST /heartbeat  - Heartbeat
        POST /message    - Generic message
    """

    def __init__(
        self,
        agent: "BaseAgent",
        host: str = "0.0.0.0",
        port: int = 5001,
        platform_url: str = "http://localhost:8000",
        cors_origins: list = None,
    ):
        """
        Initialize HTTP Server

        Args:
            agent: Agent instance
            host: Listen address
            port: Listen port
            platform_url: Platform API URL
            cors_origins: List of allowed CORS origins (default: ["*"])
        """
        if not FASTAPI_AVAILABLE:
            raise ImportError(
                "FastAPI is required for HTTPServer. "
                "Install it with: pip install fastapi uvicorn"
            )

        self.agent = agent
        self.host = host
        self.port = port
        self.platform_url = platform_url
        self.cors_origins = cors_origins or ["*"]

        # Server state
        self.app: Optional[FastAPI] = None
        self._server: Optional[uvicorn.Server] = None
        self._running = False

        # Platform registration state
        self._registered = False
        self._registration_token: Optional[str] = None

        logger.info(f"HTTPServer created for {agent.name} on port {port}")

    def _setup_app(self) -> None:
        """Setup FastAPI application with routes and middleware"""
        self.app = FastAPI(
            title=f"{self.agent.name} API",
            description=self.agent.description,
            version=self.agent.version,
        )

        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Register routes
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Setup API routes"""
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "agent_id": self.agent.agent_id,
                "agent_name": self.agent.name,
                "agent_type": getattr(self.agent.config, "agent_type", "unknown"),
                "running": self.agent.is_running,
                "state": self.agent.state.value,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

        @self.app.get("/")
        async def agent_info():
            """Agent information endpoint"""
            return {
                "agent_id": self.agent.agent_id,
                "name": self.agent.name,
                "description": self.agent.description,
                "version": self.agent.version,
                "state": self.agent.state.value,
                "endpoint": f"http://{self.host}:{self.port}",
                "endpoints": [
                    {"path": "/health", "method": "GET", "description": "Health check"},
                    {"path": "/", "method": "GET", "description": "Agent info"},
                    {"path": "/heartbeat", "method": "POST", "description": "Heartbeat"},
                    {"path": "/invoke", "method": "POST", "description": "Invoke skill"},
                    {"path": "/chat", "method": "POST", "description": "Chat message"},
                    {"path": "/message", "method": "POST", "description": "Generic message"},
                ],
                "skills": [s.name for s in self.agent.skills],
                "capabilities": [c.name for c in self.agent.capabilities],
            }

        @self.app.post("/heartbeat")
        async def heartbeat(request: Request):
            """Heartbeat endpoint"""
            try:
                data = await request.json()
            except:
                data = {}

            # Send heartbeat to platform
            await self._send_platform_heartbeat()

            return {
                "success": True,
                "agent_id": self.agent.agent_id,
                "agent_name": self.agent.name,
                "state": self.agent.state.value,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "received": data,
            }

        @self.app.post("/invoke")
        async def invoke(request: Request):
            """Invoke skill endpoint"""
            try:
                data = await request.json()
            except:
                raise HTTPException(status_code=400, detail="Invalid JSON")

            method = data.get("method", "chat")
            params = data.get("params", {})
            sender_id = data.get("sender_id", "unknown")

            # Construct message
            message = {
                "message_type": method,
                "message_id": f"http_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
                "sender_id": sender_id,
                "receiver_id": self.agent.agent_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": params,
            }

            # Call agent's message handler
            from usmsb_sdk.agent_sdk.communication import Message, MessageType

            internal_message = Message(
                type=MessageType.REQUEST,
                sender_id=sender_id,
                receiver_id=self.agent.agent_id,
                content=params,
            )

            response = await self.agent.handle_message(internal_message)

            if response is None:
                # If no handler, try default chat response
                response = await self._default_chat_response(params)

            return JSONResponse(
                content={
                    "success": True,
                    "result": response,
                    "agent_id": self.agent.agent_id,
                    "agent_name": self.agent.name,
                    "method": method,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            )

        @self.app.post("/chat")
        async def chat(request: Request):
            """Chat endpoint"""
            try:
                data = await request.json()
            except:
                raise HTTPException(status_code=400, detail="Invalid JSON")

            message_text = data.get("message", data.get("input", ""))
            sender_id = data.get("sender_id", "unknown")

            # Construct message
            from usmsb_sdk.agent_sdk.communication import Message, MessageType

            internal_message = Message(
                type=MessageType.REQUEST,
                sender_id=sender_id,
                receiver_id=self.agent.agent_id,
                content={"message": message_text},
            )

            # Call agent's message handler
            response = await self.agent.handle_message(internal_message)

            if response is None:
                response = await self._default_chat_response({"message": message_text})

            return JSONResponse(
                content={
                    "success": True,
                    "response": response,
                    "agent_id": self.agent.agent_id,
                    "agent_name": self.agent.name,
                }
            )

        @self.app.post("/message")
        async def message(request: Request):
            """Generic message endpoint"""
            try:
                message = await request.json()
            except:
                raise HTTPException(status_code=400, detail="Invalid JSON")

            # Ensure required fields
            if "message_type" not in message:
                message["message_type"] = "unknown"
            if "message_id" not in message:
                message["message_id"] = f"msg_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
            if "timestamp" not in message:
                message["timestamp"] = datetime.utcnow().isoformat() + "Z"

            # Call agent's message handler
            from usmsb_sdk.agent_sdk.communication import Message, MessageType

            internal_message = Message(
                type=MessageType.REQUEST,
                sender_id=message.get("sender_id", "unknown"),
                receiver_id=self.agent.agent_id,
                content=message.get("payload", message),
            )

            response = await self.agent.handle_message(internal_message)

            return JSONResponse(
                content={
                    "success": True,
                    "result": response,
                    "agent_id": self.agent.agent_id,
                }
            )

    async def start(self) -> bool:
        """
        Start HTTP server

        Returns:
            True if server started successfully
        """
        try:
            # Setup FastAPI app
            self._setup_app()

            # Create uvicorn config
            config = uvicorn.Config(
                app=self.app,
                host=self.host,
                port=self.port,
                log_level="info",
            )

            self._server = uvicorn.Server(config)
            self._running = True

            logger.info(f"HTTP Server starting: http://{self.host}:{self.port}")

            # Register to platform
            await self.register_to_platform()

            # Start server in background
            asyncio.create_task(self._server.serve())

            logger.info(f"HTTP Server started: http://{self.host}:{self.port}")

            return True

        except Exception as e:
            logger.error(f"Failed to start HTTP server: {e}")
            return False

    async def stop(self) -> None:
        """Stop HTTP server"""
        if self._server:
            self._server.should_exit = True
            self._running = False
            logger.info(f"HTTP Server stopped for {self.agent.name}")

    async def _default_chat_response(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Default chat response"""
        message = params.get("message", "")
        return {
            "message_type": "chat_response",
            "response": f"Received your message: {message}. I am {self.agent.name}, processing...",
            "agent_id": self.agent.agent_id,
        }

    # ========== Platform Registration ==========

    async def register_to_platform(self) -> bool:
        """Register to platform"""
        try:
            import aiohttp
        except ImportError:
            logger.warning("aiohttp not available, skipping platform registration")
            return False

        registration_data = {
            "agent_id": self.agent.agent_id,
            "name": self.agent.name,
            "description": self.agent.description,
            "capabilities": [c.name for c in self.agent.capabilities],
            "skills": [s.name for s in self.agent.skills],
            "endpoint": f"http://localhost:{self.port}",
            "protocols": ["http", "websocket"],
            "stake_amount": 100.0,
        }

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.platform_url}/agent-auth/register",
                    json=registration_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self._registered = True
                        self._registration_token = data.get("token")
                        logger.info(f"Registered to platform: {self.agent.agent_id}")
                        return True
                    else:
                        text = await response.text()
                        logger.warning(f"Platform registration failed: {response.status} - {text}")
                        return False
        except Exception as e:
            logger.warning(f"Failed to register to platform: {e}")
            return False

    async def _send_platform_heartbeat(self) -> bool:
        """Send heartbeat to platform"""
        if not self._registered:
            return False

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.platform_url}/agent-auth/agents/{self.agent.agent_id}/heartbeat",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.debug(f"Heartbeat to platform failed: {e}")
            return False

    async def unregister_from_platform(self) -> bool:
        """Unregister from platform"""
        if not self._registered:
            return True

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.platform_url}/agent-auth/agents/{self.agent.agent_id}",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    self._registered = False
                    logger.info(f"Unregistered from platform: {self.agent.agent_id}")
                    return True
        except Exception as e:
            logger.warning(f"Failed to unregister: {e}")
            return False


async def run_agent_with_http(
    agent: "BaseAgent",
    http_port: int = 5001,
    platform_url: str = "http://localhost:8000",
    cors_origins: list = None,
) -> None:
    """
    Run Agent with HTTP server

    Args:
        agent: Agent instance
        http_port: HTTP port
        platform_url: Platform API URL
        cors_origins: List of allowed CORS origins
    """
    # Create HTTP server
    http_server = HTTPServer(
        agent=agent,
        port=http_port,
        platform_url=platform_url,
        cors_origins=cors_origins,
    )

    try:
        # Start agent
        await agent.start()

        # Start HTTP server
        await http_server.start()

        logger.info(f"{agent.name} running with HTTP on port {http_port}")
        logger.info(f"   Health: http://localhost:{http_port}/health")
        logger.info(f"   Invoke: http://localhost:{http_port}/invoke")

        # Wait for stop signal
        while agent.is_running:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info(f"Received interrupt signal for {agent.name}")
    finally:
        await http_server.stop()
        await agent.stop()
