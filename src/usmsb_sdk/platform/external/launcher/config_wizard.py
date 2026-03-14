"""
Configuration Wizard
====================

Interactive configuration generation tool.
"""

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass
class NodeConfig:
    """Node configuration schema."""
    node_id: str
    node_type: str = "generic"
    host: str = "localhost"
    port: int = 8080
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StorageConfig:
    """Storage configuration schema."""
    type: str = "sqlite"
    path: str = "./data/usmsb.db"
    host: str = "localhost"
    port: int = 5432
    database: str = "usmsb"
    username: str = ""
    password: str = ""
    pool_size: int = 10


@dataclass
class LoggingConfig:
    """Logging configuration schema."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str | None = None
    max_size: int = 10485760  # 10MB
    backup_count: int = 5


@dataclass
class PlatformConfig:
    """Platform configuration schema."""
    name: str = "usmsb-platform"
    version: str = "1.0.0"
    nodes: list[dict[str, Any]] = field(default_factory=list)
    storage: dict[str, Any] = field(default_factory=dict)
    logging: dict[str, Any] = field(default_factory=dict)
    services: dict[str, Any] = field(default_factory=dict)
    security: dict[str, Any] = field(default_factory=dict)


class ConfigWizard:
    """
    Interactive configuration wizard for USMSB platform.

    Supports both interactive mode and command-line arguments.
    """

    def __init__(self, output_path: str | None = None):
        """
        Initialize configuration wizard.

        Args:
            output_path: Path to save the generated configuration.
        """
        self.output_path = Path(output_path) if output_path else None
        self._logger = logging.getLogger("usmsb.config_wizard")
        self._config = PlatformConfig()

    def run_interactive(self) -> dict[str, Any]:
        """
        Run interactive configuration wizard.

        Returns:
            Generated configuration dictionary.
        """
        print("\n" + "=" * 60)
        print("USMSB Platform Configuration Wizard")
        print("=" * 60 + "\n")

        # Basic configuration
        self._configure_basic()

        # Node configuration
        self._configure_nodes()

        # Storage configuration
        self._configure_storage()

        # Logging configuration
        self._configure_logging()

        # Security configuration
        self._configure_security()

        # Services configuration
        self._configure_services()

        # Validate and generate
        config = self._generate_config()

        # Save or display
        if self.output_path:
            self._save_config(config)
            print(f"\nConfiguration saved to: {self.output_path}")
        else:
            print("\nGenerated Configuration:")
            print("-" * 40)
            print(yaml.dump(config, default_flow_style=False))

        return config

    def run_from_args(self, args: list[str]) -> dict[str, Any]:
        """
        Run wizard with command-line arguments.

        Args:
            args: Command-line arguments.

        Returns:
            Generated configuration dictionary.
        """
        parser = self._create_arg_parser()
        parsed = parser.parse_args(args)

        # Build config from arguments
        self._config.name = parsed.name
        self._config.version = parsed.version

        # Storage configuration
        self._config.storage = {
            "type": parsed.storage_type,
            "path": parsed.storage_path,
            "host": parsed.storage_host,
            "port": parsed.storage_port,
            "database": parsed.storage_database,
        }

        # Logging configuration
        self._config.logging = {
            "level": parsed.log_level,
            "file": parsed.log_file,
        }

        # Generate and save
        config = self._generate_config()

        if parsed.output:
            self.output_path = Path(parsed.output)
            self._save_config(config)
            print(f"Configuration saved to: {self.output_path}")

        return config

    def _create_arg_parser(self) -> argparse.ArgumentParser:
        """Create argument parser."""
        parser = argparse.ArgumentParser(
            description="USMSB Platform Configuration Wizard"
        )

        # Basic options
        parser.add_argument("--name", default="usmsb-platform", help="Platform name")
        parser.add_argument("--version", default="1.0.0", help="Platform version")
        parser.add_argument("-o", "--output", help="Output configuration file path")

        # Storage options
        parser.add_argument("--storage-type", default="sqlite",
                           choices=["sqlite", "postgresql", "mysql", "mongodb"],
                           help="Storage type")
        parser.add_argument("--storage-path", default="./data/usmsb.db",
                           help="Storage path (for file-based storage)")
        parser.add_argument("--storage-host", default="localhost",
                           help="Storage host (for network storage)")
        parser.add_argument("--storage-port", type=int, default=5432,
                           help="Storage port")
        parser.add_argument("--storage-database", default="usmsb",
                           help="Database name")

        # Logging options
        parser.add_argument("--log-level", default="INFO",
                           choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                           help="Log level")
        parser.add_argument("--log-file", help="Log file path")

        return parser

    def _configure_basic(self) -> None:
        """Configure basic platform settings."""
        print("\n[Basic Configuration]")
        print("-" * 40)

        name = self._prompt("Platform name", default="usmsb-platform")
        version = self._prompt("Platform version", default="1.0.0")

        self._config.name = name
        self._config.version = version

    def _configure_nodes(self) -> None:
        """Configure nodes."""
        print("\n[Node Configuration]")
        print("-" * 40)

        while True:
            add_node = self._prompt("Add a node? (y/n)", default="n").lower()
            if add_node != "y":
                break

            node = self._configure_single_node()
            self._config.nodes.append(asdict(node))
            print(f"Node '{node.node_id}' added.")

    def _configure_single_node(self) -> NodeConfig:
        """Configure a single node."""
        node_id = self._prompt("Node ID", default=f"node_{len(self._config.nodes) + 1}")
        node_type = self._prompt("Node type", default="generic",
                                 choices=["generic", "agent", "storage", "gateway"])
        host = self._prompt("Host", default="localhost")
        port = int(self._prompt("Port", default="8080"))

        return NodeConfig(
            node_id=node_id,
            node_type=node_type,
            host=host,
            port=port,
        )

    def _configure_storage(self) -> None:
        """Configure storage."""
        print("\n[Storage Configuration]")
        print("-" * 40)

        storage_type = self._prompt("Storage type", default="sqlite",
                                    choices=["sqlite", "postgresql", "mysql", "mongodb"])

        storage_config = {"type": storage_type}

        if storage_type == "sqlite":
            storage_config["path"] = self._prompt("Database path",
                                                  default="./data/usmsb.db")
        else:
            storage_config["host"] = self._prompt("Host", default="localhost")
            storage_config["port"] = int(self._prompt("Port",
                                                      default=self._get_default_port(storage_type)))
            storage_config["database"] = self._prompt("Database name", default="usmsb")
            storage_config["username"] = self._prompt("Username", default="")
            storage_config["password"] = self._prompt("Password", default="", is_password=True)

        self._config.storage = storage_config

    def _get_default_port(self, storage_type: str) -> str:
        """Get default port for storage type."""
        ports = {
            "postgresql": "5432",
            "mysql": "3306",
            "mongodb": "27017",
        }
        return ports.get(storage_type, "5432")

    def _configure_logging(self) -> None:
        """Configure logging."""
        print("\n[Logging Configuration]")
        print("-" * 40)

        level = self._prompt("Log level", default="INFO",
                             choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        log_file = self._prompt("Log file path (leave empty for console only)",
                                default="")

        self._config.logging = {
            "level": level,
            "file": log_file if log_file else None,
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        }

    def _configure_security(self) -> None:
        """Configure security settings."""
        print("\n[Security Configuration]")
        print("-" * 40)

        enable_auth = self._prompt("Enable authentication? (y/n)", default="n").lower()

        security_config = {"enabled": enable_auth == "y"}

        if enable_auth == "y":
            security_config["provider"] = self._prompt("Auth provider", default="local",
                                                       choices=["local", "ldap", "oauth2"])
            security_config["token_expiry"] = int(self._prompt("Token expiry (hours)",
                                                               default="24"))

        self._config.security = security_config

    def _configure_services(self) -> None:
        """Configure services."""
        print("\n[Services Configuration]")
        print("-" * 40)

        services = {}

        # Agent service
        enable_agents = self._prompt("Enable Agent service? (y/n)", default="y").lower()
        if enable_agents == "y":
            services["agents"] = {
                "enabled": True,
                "max_agents": int(self._prompt("Max agents", default="100")),
                "timeout": int(self._prompt("Agent timeout (seconds)", default="300")),
            }

        # API service
        enable_api = self._prompt("Enable API service? (y/n)", default="y").lower()
        if enable_api == "y":
            services["api"] = {
                "enabled": True,
                "host": self._prompt("API host", default="0.0.0.0"),
                "port": int(self._prompt("API port", default="8000")),
            }

        self._config.services = services

    def _prompt(self, message: str, default: str = "",
                choices: list[str] | None = None,
                is_password: bool = False) -> str:
        """
        Prompt user for input.

        Args:
            message: Prompt message.
            default: Default value.
            choices: Valid choices (optional).
            is_password: Whether input is a password.

        Returns:
            User input value.
        """
        prompt_text = f"{message}"
        if choices:
            prompt_text += f" [{', '.join(choices)}]"
        if default:
            prompt_text += f" (default: {default})"
        prompt_text += ": "

        while True:
            try:
                if is_password:
                    import getpass
                    value = getpass.getpass(prompt_text)
                else:
                    value = input(prompt_text).strip()

                if not value:
                    value = default

                if choices and value not in choices:
                    print(f"Invalid choice. Please select from: {', '.join(choices)}")
                    continue

                return value

            except EOFError:
                return default
            except KeyboardInterrupt:
                print("\nConfiguration cancelled.")
                sys.exit(0)

    def _generate_config(self) -> dict[str, Any]:
        """
        Generate and validate configuration.

        Returns:
            Validated configuration dictionary.
        """
        config = asdict(self._config)

        # Add metadata
        config["generated_at"] = datetime.now().isoformat()
        config["generator"] = "usmsb-config-wizard"

        # Validate
        self._validate_config(config)

        return config

    def _validate_config(self, config: dict[str, Any]) -> bool:
        """
        Validate configuration.

        Args:
            config: Configuration dictionary to validate.

        Returns:
            True if valid.

        Raises:
            ValueError: If configuration is invalid.
        """
        errors = []

        # Check required fields
        if not config.get("name"):
            errors.append("Platform name is required")

        # Validate storage configuration
        storage = config.get("storage", {})
        if storage.get("type") == "sqlite":
            if not storage.get("path"):
                errors.append("SQLite path is required")
        else:
            if not storage.get("host"):
                errors.append("Storage host is required for network storage")

        # Validate nodes
        for i, node in enumerate(config.get("nodes", [])):
            if not node.get("node_id"):
                errors.append(f"Node {i}: node_id is required")
            if not node.get("host"):
                errors.append(f"Node {i}: host is required")

        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)

        self._logger.info("Configuration validated successfully")
        return True

    def _save_config(self, config: dict[str, Any]) -> None:
        """
        Save configuration to file.

        Args:
            config: Configuration dictionary to save.
        """
        if not self.output_path:
            raise ValueError("Output path not specified")

        # Create parent directory if needed
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Determine format from extension
        suffix = self.output_path.suffix.lower()

        with open(self.output_path, "w", encoding="utf-8") as f:
            if suffix in (".yaml", ".yml"):
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            elif suffix == ".json":
                json.dump(config, f, indent=2)
            else:
                # Default to YAML
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        self._logger.info(f"Configuration saved to {self.output_path}")

    @staticmethod
    def generate_template(output_path: str, format: str = "yaml") -> None:
        """
        Generate a configuration template.

        Args:
            output_path: Path to save template.
            format: Output format (yaml or json).
        """
        template = {
            "name": "usmsb-platform",
            "version": "1.0.0",
            "nodes": [
                {
                    "node_id": "node-1",
                    "node_type": "generic",
                    "host": "localhost",
                    "port": 8080,
                    "enabled": True,
                }
            ],
            "storage": {
                "type": "sqlite",
                "path": "./data/usmsb.db",
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": None,
            },
            "services": {
                "agents": {
                    "enabled": True,
                    "max_agents": 100,
                },
                "api": {
                    "enabled": True,
                    "host": "0.0.0.0",
                    "port": 8000,
                },
            },
            "security": {
                "enabled": False,
            },
        }

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            if format == "json":
                json.dump(template, f, indent=2)
            else:
                yaml.dump(template, f, default_flow_style=False, sort_keys=False)

        print(f"Template saved to: {output_path}")
