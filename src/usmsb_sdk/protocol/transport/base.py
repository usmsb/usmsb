"""
Transport Config - 传输层配置基类
"""

from typing import Any

from pydantic import BaseModel


class TransportConfig(BaseModel):
    """传输层配置基类"""

    host: str = "0.0.0.0"
    port: int = 8080
    ssl_cert: str | None = None
    ssl_key: str | None = None
    timeout: float = 30.0


class HTTPTransportConfig(TransportConfig):
    """HTTP 传输配置"""

    unix_socket: str | None = None
    num_workers: int = 1
    max_connections: int = 1000


class WebSocketTransportConfig(TransportConfig):
    """WebSocket 传输配置"""

    path: str = "/ws"
    ping_interval: float = 30.0
    ping_timeout: float = 10.0


class SSETransportConfig(TransportConfig):
    """SSE 传输配置"""

    path: str = "/events"
    heartbeat_interval: float = 30.0
    max_subscribers: int = 10000


class gRPCTransportConfig(TransportConfig):
    """gRPC 传输配置"""

    port: int = 50051
    max_concurrent_calls: int = 100
    max_receive_message_length: int = 100 * 1024 * 1024  # 100MB
