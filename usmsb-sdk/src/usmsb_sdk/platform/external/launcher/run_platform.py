#!/usr/bin/env python3
"""
Run Platform Script
===================

Main entry point for running the USMSB platform directly.
"""

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from usmsb_sdk.platform.external.launcher.platform_launcher import PlatformLauncher
from usmsb_sdk.platform.external.launcher.config_wizard import ConfigWizard
from usmsb_sdk.platform.external.launcher.status_monitor import StatusMonitor


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
) -> None:
    """
    Setup logging configuration.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional log file path.
        log_format: Log message format.
    """
    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        handlers=handlers,
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run USMSB Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Run with default config
  %(prog)s -c /path/to/config.yaml            # Run with specific config
  %(prog)s --generate-config -o config.yaml   # Generate config template
  %(prog)s -l DEBUG                           # Run with debug logging
        """,
    )

    parser.add_argument(
        "-c", "--config",
        default="./config/platform.yaml",
        help="Path to configuration file (default: ./config/platform.yaml)",
    )

    parser.add_argument(
        "-l", "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)",
    )

    parser.add_argument(
        "--log-file",
        help="Path to log file (default: console only)",
    )

    parser.add_argument(
        "--generate-config",
        action="store_true",
        help="Generate a configuration template",
    )

    parser.add_argument(
        "-o", "--output",
        help="Output file for generated config",
    )

    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate configuration file and exit",
    )

    parser.add_argument(
        "--no-monitor",
        action="store_true",
        help="Disable status monitoring",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )

    return parser.parse_args()


async def run_platform(config_path: str, enable_monitor: bool = True) -> int:
    """
    Run the platform.

    Args:
        config_path: Path to configuration file.
        enable_monitor: Whether to enable status monitoring.

    Returns:
        Exit code.
    """
    logger = logging.getLogger("usmsb.run")

    # Check if config exists
    config_file = Path(config_path)
    if not config_file.exists():
        logger.error(f"Configuration file not found: {config_path}")
        logger.info("Generate a config with: run_platform.py --generate-config -o config.yaml")
        return 1

    # Initialize launcher
    try:
        launcher = PlatformLauncher(config_path)
    except Exception as e:
        logger.error(f"Failed to initialize platform: {e}")
        return 1

    # Initialize monitor if enabled
    monitor = None
    if enable_monitor:
        monitor = StatusMonitor(launcher.config)
        await monitor.start()

    # Setup signal handlers
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start platform
    logger.info("Starting USMSB Platform...")
    success = await launcher.start()

    if not success:
        logger.error("Failed to start platform")
        return 1

    # Print status
    status = launcher.get_status()
    logger.info(f"Platform started: {status['status']}")
    logger.info(f"Nodes: {status['node_count']} ({status['active_nodes']} active)")

    if monitor:
        logger.info("Status monitoring enabled")

    # Wait for shutdown
    try:
        await shutdown_event.wait()
    except KeyboardInterrupt:
        pass

    # Graceful shutdown
    logger.info("Shutting down platform...")

    if monitor:
        await monitor.stop()

    await launcher.stop()

    logger.info("Platform shutdown complete")
    return 0


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Setup logging
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger("usmsb.run")

    # Handle config generation
    if args.generate_config:
        output_path = args.output or "./config/platform.yaml"
        ConfigWizard.generate_template(output_path)
        logger.info(f"Configuration template generated: {output_path}")
        return 0

    # Handle config validation
    if args.validate_config:
        config_path = Path(args.config)
        if not config_path.exists():
            logger.error(f"Configuration file not found: {args.config}")
            return 1

        try:
            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            wizard = ConfigWizard()
            wizard._validate_config(config)
            logger.info("Configuration is valid")
            return 0

        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return 1

    # Run platform
    try:
        return asyncio.run(run_platform(
            args.config,
            enable_monitor=not args.no_monitor,
        ))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
