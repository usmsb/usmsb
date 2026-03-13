"""
USMSB SDK Unified Configuration Module

This module provides a unified configuration management system for:
- Agent configuration
- Platform configuration
- Network configuration
- Authentication configuration
- Database configuration
- Logging configuration

Usage:
    from usmsb_sdk.core.config import load_config, PlatformConfig

    # Load from file
    config = load_config("config.yaml")

    # Load from environment
    config = load_config_from_env()

    # Access configuration
    print(config.network.platform_url)
    print(config.auth.api_key)
"""

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class NetworkConfig:
    """
    Network configuration for Agent and Platform.

    Attributes:
        platform_url: URL of the platform API
        p2p_port: Port for P2P communication
        http_port: Port for HTTP server
        websocket_port: Port for WebSocket server
        grpc_port: Port for gRPC server
        bind_address: Address to bind services to
        external_address: External address for other nodes to connect
        connection_timeout: Connection timeout in seconds
        request_timeout: Request timeout in seconds
        max_connections: Maximum number of concurrent connections
    """
    platform_url: str = "http://localhost:8000"
    p2p_port: int = 9001
    http_port: int = 5001
    websocket_port: int = 8765
    grpc_port: int = 50051
    bind_address: str = "0.0.0.0"
    external_address: Optional[str] = None
    connection_timeout: float = 30.0
    request_timeout: float = 60.0
    max_connections: int = 100

    def get_external_url(self, protocol: str = "http") -> str:
        """Get external URL for the specified protocol."""
        address = self.external_address or "localhost"
        if protocol == "http":
            return f"http://{address}:{self.http_port}"
        elif protocol == "websocket":
            return f"ws://{address}:{self.websocket_port}"
        elif protocol == "grpc":
            return f"{address}:{self.grpc_port}"
        elif protocol == "p2p":
            return f"{address}:{self.p2p_port}"
        raise ValueError(f"Unknown protocol: {protocol}")


@dataclass
class AuthConfig:
    """
    Authentication configuration.

    Attributes:
        api_key: API key for authentication
        wallet_address: Wallet address for blockchain authentication
        stake_amount: Stake amount for agent registration
        jwt_secret: Secret key for JWT tokens
        token_expiry: Token expiry time in seconds
        require_auth: Whether authentication is required
    """
    api_key: Optional[str] = None
    wallet_address: Optional[str] = None
    stake_amount: float = 100.0
    jwt_secret: Optional[str] = None
    token_expiry: int = 3600  # 1 hour
    require_auth: bool = True
    trusted_agents: List[str] = field(default_factory=list)

    def is_configured(self) -> bool:
        """Check if authentication is configured."""
        return bool(self.api_key or self.wallet_address)


@dataclass
class DatabaseConfig:
    """
    Database configuration.

    Attributes:
        url: Database URL (e.g., sqlite:///platform.db)
        redis_url: Redis URL for caching
        pool_size: Connection pool size
        echo: Whether to echo SQL statements
    """
    url: str = "sqlite:///platform.db"
    redis_url: str = "redis://localhost:6379"
    pool_size: int = 10
    echo: bool = False

    @property
    def is_postgres(self) -> bool:
        """Check if using PostgreSQL."""
        return self.url.startswith("postgresql")

    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite."""
        return self.url.startswith("sqlite")


@dataclass
class LoggingConfig:
    """
    Logging configuration.

    Attributes:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format: Log format string
        file: Optional log file path
        max_size: Maximum log file size in bytes
        backup_count: Number of backup log files
    """
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None
    max_size: int = 10 * 1024 * 1024  # 10 MB
    backup_count: int = 5

    def get_log_level(self) -> int:
        """Get logging level as integer."""
        return getattr(logging, self.level.upper(), logging.INFO)


@dataclass
class AgentConfig:
    """
    Core Agent configuration.

    This is a simplified configuration for agent settings,
    complementary to the full AgentConfig in agent_sdk.

    Attributes:
        agent_id: Unique agent identifier
        name: Agent name
        description: Agent description
        version: Agent version
        agent_type: Type of agent
        protocols: List of enabled protocols
        auto_register: Whether to auto-register with platform
        heartbeat_interval: Heartbeat interval in seconds
    """
    agent_id: str = ""
    name: str = "Agent"
    description: str = ""
    version: str = "1.0.0"
    agent_type: str = "generic"
    protocols: List[str] = field(default_factory=lambda: ["http"])
    auto_register: bool = True
    heartbeat_interval: int = 30
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "agent_type": self.agent_type,
            "protocols": self.protocols,
            "auto_register": self.auto_register,
            "heartbeat_interval": self.heartbeat_interval,
            "metadata": self.metadata,
        }


@dataclass
class PlatformConfig:
    """
    Platform configuration.

    Attributes:
        host: Platform host address
        port: Platform port
        debug: Whether debug mode is enabled
        cors_origins: List of allowed CORS origins
        workers: Number of worker processes
        database: Database configuration
        auth: Authentication configuration
        network: Network configuration
        logging: Logging configuration
    """
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    workers: int = 1
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @property
    def base_url(self) -> str:
        """Get platform base URL."""
        return f"http://{self.host}:{self.port}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "host": self.host,
            "port": self.port,
            "debug": self.debug,
            "cors_origins": self.cors_origins,
            "workers": self.workers,
            "database": {
                "url": self.database.url,
                "redis_url": self.database.redis_url,
                "pool_size": self.database.pool_size,
                "echo": self.database.echo,
            },
            "auth": {
                "api_key": "***" if self.auth.api_key else None,
                "wallet_address": self.auth.wallet_address,
                "stake_amount": self.auth.stake_amount,
                "require_auth": self.auth.require_auth,
            },
            "network": {
                "platform_url": self.network.platform_url,
                "http_port": self.network.http_port,
                "websocket_port": self.network.websocket_port,
            },
            "logging": {
                "level": self.logging.level,
                "file": self.logging.file,
            },
        }


def load_config(config_path: Union[str, Path]) -> PlatformConfig:
    """
    Load configuration from a file.

    Supports YAML and JSON formats.

    Args:
        config_path: Path to configuration file

    Returns:
        PlatformConfig instance
    """
    config_path = Path(config_path)

    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}, using defaults")
        return PlatformConfig()

    # Read file content
    content = config_path.read_text(encoding="utf-8")

    # Parse based on file extension
    if config_path.suffix in [".yaml", ".yml"]:
        try:
            import yaml
            data = yaml.safe_load(content) or {}
        except ImportError:
            logger.warning("PyYAML not installed, trying JSON parse")
            data = json.loads(content)
    else:
        data = json.loads(content)

    return _dict_to_config(data)


def load_config_from_env(prefix: str = "USMSB_") -> PlatformConfig:
    """
    Load configuration from environment variables.

    Environment variables should be prefixed with the given prefix.
    Example: USMSB_HOST=0.0.0.0, USMSB_PORT=8000

    Args:
        prefix: Environment variable prefix

    Returns:
        PlatformConfig instance
    """
    def get_env(key: str, default: Any = None) -> Any:
        return os.environ.get(f"{prefix}{key}", default)

    config = PlatformConfig(
        host=get_env("HOST", "0.0.0.0"),
        port=int(get_env("PORT", "8000")),
        debug=get_env("DEBUG", "false").lower() == "true",
        workers=int(get_env("WORKERS", "1")),
    )

    # Network config
    config.network = NetworkConfig(
        platform_url=get_env("PLATFORM_URL", "http://localhost:8000"),
        http_port=int(get_env("HTTP_PORT", "5001")),
        websocket_port=int(get_env("WEBSOCKET_PORT", "8765")),
        p2p_port=int(get_env("P2P_PORT", "9001")),
    )

    # Auth config
    config.auth = AuthConfig(
        api_key=get_env("API_KEY"),
        wallet_address=get_env("WALLET_ADDRESS"),
        stake_amount=float(get_env("STAKE_AMOUNT", "100.0")),
        require_auth=get_env("REQUIRE_AUTH", "true").lower() == "true",
    )

    # Database config
    config.database = DatabaseConfig(
        url=get_env("DATABASE_URL", "sqlite:///platform.db"),
        redis_url=get_env("REDIS_URL", "redis://localhost:6379"),
    )

    # Logging config
    config.logging = LoggingConfig(
        level=get_env("LOG_LEVEL", "INFO"),
        file=get_env("LOG_FILE"),
    )

    return config


def _dict_to_config(data: Dict[str, Any]) -> PlatformConfig:
    """Convert dictionary to PlatformConfig."""
    # Extract nested configs
    network_data = data.get("network", {})
    auth_data = data.get("auth", {})
    database_data = data.get("database", {})
    logging_data = data.get("logging", {})

    network = NetworkConfig(
        platform_url=network_data.get("platform_url", "http://localhost:8000"),
        p2p_port=network_data.get("p2p_port", 9001),
        http_port=network_data.get("http_port", 5001),
        websocket_port=network_data.get("websocket_port", 8765),
        grpc_port=network_data.get("grpc_port", 50051),
        bind_address=network_data.get("bind_address", "0.0.0.0"),
        external_address=network_data.get("external_address"),
        connection_timeout=network_data.get("connection_timeout", 30.0),
        request_timeout=network_data.get("request_timeout", 60.0),
        max_connections=network_data.get("max_connections", 100),
    )

    auth = AuthConfig(
        api_key=auth_data.get("api_key"),
        wallet_address=auth_data.get("wallet_address"),
        stake_amount=auth_data.get("stake_amount", 100.0),
        jwt_secret=auth_data.get("jwt_secret"),
        token_expiry=auth_data.get("token_expiry", 3600),
        require_auth=auth_data.get("require_auth", True),
        trusted_agents=auth_data.get("trusted_agents", []),
    )

    database = DatabaseConfig(
        url=database_data.get("url", "sqlite:///platform.db"),
        redis_url=database_data.get("redis_url", "redis://localhost:6379"),
        pool_size=database_data.get("pool_size", 10),
        echo=database_data.get("echo", False),
    )

    logging_config = LoggingConfig(
        level=logging_data.get("level", "INFO"),
        format=logging_data.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
        file=logging_data.get("file"),
        max_size=logging_data.get("max_size", 10 * 1024 * 1024),
        backup_count=logging_data.get("backup_count", 5),
    )

    return PlatformConfig(
        host=data.get("host", "0.0.0.0"),
        port=data.get("port", 8000),
        debug=data.get("debug", False),
        cors_origins=data.get("cors_origins", ["*"]),
        workers=data.get("workers", 1),
        database=database,
        auth=auth,
        network=network,
        logging=logging_config,
    )


__all__ = [
    "NetworkConfig",
    "AuthConfig",
    "AgentConfig",
    "PlatformConfig",
    "DatabaseConfig",
    "LoggingConfig",
    "load_config",
    "load_config_from_env",
]
