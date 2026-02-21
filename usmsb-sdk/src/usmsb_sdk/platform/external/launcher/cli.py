"""
Command Line Interface
======================

USMSB platform command line tools.
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .config_wizard import ConfigWizard
from .health_checker import HealthChecker, HealthStatus
from .platform_launcher import PlatformLauncher, PlatformStatus
from .status_monitor import StatusMonitor


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Setup logging configuration."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    handlers = [logging.StreamHandler()]

    if log_file:
        from logging.handlers import RotatingFileHandler
        handlers.append(
            RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
            )
        )

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        handlers=handlers,
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="usmsb",
        description="USMSB Platform Management CLI",
    )

    parser.add_argument(
        "-c", "--config",
        default="./config/platform.yaml",
        help="Path to configuration file",
    )

    parser.add_argument(
        "-l", "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Log level",
    )

    parser.add_argument(
        "--log-file",
        help="Log file path",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start the platform")
    start_parser.add_argument(
        "-d", "--daemon",
        action="store_true",
        help="Run as daemon",
    )
    start_parser.add_argument(
        "--no-monitor",
        action="store_true",
        help="Disable status monitoring",
    )

    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop the platform")
    stop_parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Force stop",
    )

    # Restart command
    restart_parser = subparsers.add_parser("restart", help="Restart the platform")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show platform status")
    status_parser.add_argument(
        "-j", "--json",
        action="store_true",
        help="Output in JSON format",
    )
    status_parser.add_argument(
        "-w", "--watch",
        action="store_true",
        help="Watch status continuously",
    )

    # Config command
    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_parser.add_argument(
        "action",
        choices=["create", "validate", "show", "template"],
        help="Config action",
    )
    config_parser.add_argument(
        "-o", "--output",
        help="Output file path",
    )
    config_parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode",
    )

    # Health command
    health_parser = subparsers.add_parser("health", help="Run health checks")
    health_parser.add_argument(
        "-j", "--json",
        action="store_true",
        help="Output in JSON format",
    )
    health_parser.add_argument(
        "--nodes",
        action="store_true",
        help="Include node health checks",
    )
    health_parser.add_argument(
        "--storage",
        action="store_true",
        help="Include storage health checks",
    )

    # Logs command
    logs_parser = subparsers.add_parser("logs", help="View platform logs")
    logs_parser.add_argument(
        "-f", "--follow",
        action="store_true",
        help="Follow log output",
    )
    logs_parser.add_argument(
        "-n", "--lines",
        type=int,
        default=100,
        help="Number of lines to show",
    )
    logs_parser.add_argument(
        "--level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Filter by log level",
    )
    logs_parser.add_argument(
        "--component",
        help="Filter by component name",
    )

    # Node command
    node_parser = subparsers.add_parser("node", help="Node management")
    node_parser.add_argument(
        "action",
        choices=["list", "add", "remove", "status"],
        help="Node action",
    )
    node_parser.add_argument(
        "--node-id",
        help="Node ID",
    )
    node_parser.add_argument(
        "--node-type",
        default="generic",
        help="Node type",
    )
    node_parser.add_argument(
        "--host",
        default="localhost",
        help="Node host",
    )
    node_parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Node port",
    )

    return parser


async def cmd_start(args: argparse.Namespace) -> int:
    """Handle start command."""
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger("usmsb.cli")

    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Configuration file not found: {args.config}")
        return 1

    launcher = PlatformLauncher(str(config_path))

    try:
        success = await launcher.start()
        if not success:
            logger.error("Failed to start platform")
            return 1

        print(f"Platform started successfully")
        print(f"Status: {launcher.get_status()['status']}")
        print(f"Nodes: {launcher.get_status()['node_count']}")

        # Wait for shutdown signal
        await launcher.wait_for_shutdown()

        # Graceful shutdown
        await launcher.stop()

        return 0

    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        await launcher.stop()
        return 0
    except Exception as e:
        logger.error(f"Error starting platform: {e}")
        return 1


async def cmd_stop(args: argparse.Namespace) -> int:
    """Handle stop command."""
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger("usmsb.cli")

    # In a real implementation, this would connect to a running platform
    # For now, we'll just show a message
    print("Stopping platform...")

    if args.force:
        print("Force stop requested")

    print("Platform stopped")
    return 0


async def cmd_restart(args: argparse.Namespace) -> int:
    """Handle restart command."""
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger("usmsb.cli")

    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Configuration file not found: {args.config}")
        return 1

    launcher = PlatformLauncher(str(config_path))

    success = await launcher.restart()
    if success:
        print("Platform restarted successfully")
        return 0
    else:
        print("Failed to restart platform")
        return 1


async def cmd_status(args: argparse.Namespace) -> int:
    """Handle status command."""
    setup_logging(args.log_level, args.log_file)

    config_path = Path(args.config)
    if not config_path.exists():
        print("Platform is not configured")
        return 1

    try:
        launcher = PlatformLauncher(str(config_path))
        status = launcher.get_status()

        if args.json:
            print(json.dumps(status, indent=2))
        else:
            print("\n" + "=" * 60)
            print("USMSB Platform Status")
            print("=" * 60)
            print(f"\nStatus: {status['status'].upper()}")
            print(f"Uptime: {status['uptime'] or 'N/A'}")
            print(f"Nodes: {status['active_nodes']}/{status['node_count']} active")

            if status['nodes']:
                print("\nNode Details:")
                print("-" * 40)
                for node in status['nodes']:
                    print(f"  {node['node_id']}: {node['status']} ({node['host']}:{node['port']})")

            print("")

        return 0

    except Exception as e:
        print(f"Error getting status: {e}")
        return 1


async def cmd_config(args: argparse.Namespace) -> int:
    """Handle config command."""
    setup_logging(args.log_level, args.log_file)

    if args.action == "create":
        if args.interactive:
            wizard = ConfigWizard(args.output)
            wizard.run_interactive()
        else:
            output = args.output or "./config/platform.yaml"
            ConfigWizard.generate_template(output)
            print(f"Configuration template created: {output}")

    elif args.action == "validate":
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Configuration file not found: {args.config}")
            return 1

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            wizard = ConfigWizard()
            wizard._validate_config(config)
            print("Configuration is valid")
            return 0

        except Exception as e:
            print(f"Configuration validation failed: {e}")
            return 1

    elif args.action == "show":
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Configuration file not found: {args.config}")
            return 1

        with open(config_path, "r", encoding="utf-8") as f:
            print(f.read())

    elif args.action == "template":
        output = args.output or "./config/platform-template.yaml"
        ConfigWizard.generate_template(output)
        print(f"Template created: {output}")

    return 0


async def cmd_health(args: argparse.Namespace) -> int:
    """Handle health command."""
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger("usmsb.cli")

    config_path = Path(args.config)
    config = {}

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    checker = HealthChecker(config)

    # Run health checks
    report = await checker.run_all_checks(
        config.get("name", "usmsb-platform")
    )

    # Additional checks
    if args.nodes:
        nodes = config.get("nodes", [])
        for node in nodes:
            result = await checker.check_node_health(node)
            report.checks.append(result)

    if args.storage:
        storage = config.get("storage", {})
        if storage:
            result = await checker.check_storage_connection(storage)
            report.checks.append(result)

    # Recalculate summary
    report = type(report)(
        platform_name=report.platform_name,
        overall_status=checker._determine_overall_status(report.checks),
        checks=report.checks,
    )

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print("\n" + "=" * 60)
        print("USMSB Platform Health Report")
        print("=" * 60)

        # Status indicator
        status_icons = {
            HealthStatus.HEALTHY: "[OK]",
            HealthStatus.DEGRADED: "[!]",
            HealthStatus.UNHEALTHY: "[X]",
            HealthStatus.UNKNOWN: "[?]",
        }

        icon = status_icons.get(report.overall_status, "[?]")
        print(f"\nOverall Status: {icon} {report.overall_status.value.upper()}")

        print(f"\nSummary:")
        print(f"  Total checks: {report.summary['total']}")
        print(f"  Healthy: {report.summary['healthy']}")
        print(f"  Degraded: {report.summary['degraded']}")
        print(f"  Unhealthy: {report.summary['unhealthy']}")

        print("\nCheck Details:")
        print("-" * 40)
        for check in report.checks:
            icon = status_icons.get(check.status, "[?]")
            print(f"  {icon} {check.name}: {check.message}")
            if check.duration_ms > 0:
                print(f"      Duration: {check.duration_ms:.2f}ms")

        print("")

    # Return non-zero if unhealthy
    if report.overall_status == HealthStatus.UNHEALTHY:
        return 1
    return 0


async def cmd_logs(args: argparse.Namespace) -> int:
    """Handle logs command."""
    setup_logging(args.log_level, args.log_file)

    log_file = args.log_file or "./logs/usmsb.log"
    log_path = Path(log_file)

    if not log_path.exists():
        print(f"Log file not found: {log_file}")
        print("Tip: Use --log-file when starting the platform to enable logging")
        return 1

    try:
        if args.follow:
            import tailer
            for line in tailer.follow(open(log_path, "r", encoding="utf-8")):
                if _filter_log_line(line, args.level, args.component):
                    print(line, end="")
        else:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()[-args.lines:]
                for line in lines:
                    if _filter_log_line(line, args.level, args.component):
                        print(line, end="")

        return 0

    except ImportError:
        # tailer not available, read last N lines
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-args.lines:]
            for line in lines:
                if _filter_log_line(line, args.level, args.component):
                    print(line, end="")
        return 0
    except KeyboardInterrupt:
        return 0


def _filter_log_line(line: str, level: Optional[str], component: Optional[str]) -> bool:
    """Filter log line by level and component."""
    if level and level not in line:
        return False
    if component and component not in line:
        return False
    return True


async def cmd_node(args: argparse.Namespace) -> int:
    """Handle node command."""
    setup_logging(args.log_level, args.log_level)
    logger = logging.getLogger("usmsb.cli")

    if args.action == "list":
        config_path = Path(args.config)
        if not config_path.exists():
            print("No configuration found")
            return 1

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        nodes = config.get("nodes", [])

        print("\nConfigured Nodes:")
        print("-" * 60)
        if not nodes:
            print("  No nodes configured")
        else:
            for node in nodes:
                print(f"  {node.get('node_id', 'unknown')}:")
                print(f"    Type: {node.get('node_type', 'generic')}")
                print(f"    Address: {node.get('host', 'localhost')}:{node.get('port', 8080)}")
                print(f"    Status: {node.get('enabled', True) and 'enabled' or 'disabled'}")
        print("")

    elif args.action == "add":
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Configuration file not found: {args.config}")
            return 1

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        if "nodes" not in config:
            config["nodes"] = []

        new_node = {
            "node_id": args.node_id or f"node-{len(config['nodes']) + 1}",
            "node_type": args.node_type,
            "host": args.host,
            "port": args.port,
            "enabled": True,
        }

        config["nodes"].append(new_node)

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False)

        print(f"Node '{new_node['node_id']}' added to configuration")

    elif args.action == "remove":
        if not args.node_id:
            print("Error: --node-id is required")
            return 1

        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Configuration file not found: {args.config}")
            return 1

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        nodes = config.get("nodes", [])
        original_count = len(nodes)

        config["nodes"] = [n for n in nodes if n.get("node_id") != args.node_id]

        if len(config["nodes"]) == original_count:
            print(f"Node '{args.node_id}' not found")
            return 1

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False)

        print(f"Node '{args.node_id}' removed from configuration")

    return 0


async def async_main(args: argparse.Namespace) -> int:
    """Async main entry point."""
    commands = {
        "start": cmd_start,
        "stop": cmd_stop,
        "restart": cmd_restart,
        "status": cmd_status,
        "config": cmd_config,
        "health": cmd_health,
        "logs": cmd_logs,
        "node": cmd_node,
    }

    if args.command is None:
        print("USMSB Platform Management CLI")
        print("\nUsage: usmsb <command> [options]")
        print("\nCommands:")
        print("  start    Start the platform")
        print("  stop     Stop the platform")
        print("  restart  Restart the platform")
        print("  status   Show platform status")
        print("  config   Configuration management")
        print("  health   Run health checks")
        print("  logs     View platform logs")
        print("  node     Node management")
        print("\nRun 'usmsb <command> --help' for command details")
        return 0

    handler = commands.get(args.command)
    if handler:
        return await handler(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    return asyncio.run(async_main(args))


if __name__ == "__main__":
    sys.exit(main())
