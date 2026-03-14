"""
Structured Logging Implementation

Structured logging with JSON output, correlation IDs, and integration
with the event bus and metrics systems.
"""

import json
import logging
import sys
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

# Context variables for request tracing
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
agent_id_var: ContextVar[str | None] = ContextVar("agent_id", default=None)


@dataclass
class LogContext:
    """Context for structured logging."""
    service_name: str = "usmsb-sdk"
    version: str = "0.1.0"
    environment: str = "development"
    extra_fields: dict[str, Any] = field(default_factory=dict)


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs.
    """

    def __init__(
        self,
        context: LogContext | None = None,
        include_extra: bool = True,
    ):
        """
        Initialize the formatter.

        Args:
            context: Logging context with service info
            include_extra: Whether to include extra fields in output
        """
        super().__init__()
        self.context = context or LogContext()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.context.service_name,
            "version": self.context.version,
            "environment": self.context.environment,
        }

        # Add context from context variables
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_data["correlation_id"] = correlation_id

        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id

        agent_id = agent_id_var.get()
        if agent_id:
            log_data["agent_id"] = agent_id

        # Add location info
        log_data["location"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields from record
        if self.include_extra:
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in {
                    "name", "msg", "args", "created", "filename", "funcName",
                    "levelname", "levelno", "lineno", "module", "msecs",
                    "pathname", "process", "processName", "relativeCreated",
                    "stack_info", "exc_info", "exc_text", "thread", "threadName",
                    "message", "taskName",
                }:
                    extra_fields[key] = value

            if extra_fields:
                log_data["extra"] = extra_fields

        # Add context extra fields
        if self.context.extra_fields:
            log_data["context"] = self.context.extra_fields

        return json.dumps(log_data, default=str)


class StructuredLogger:
    """
    Structured logger that provides convenient methods for logging
    with structured data and automatic context injection.
    """

    def __init__(
        self,
        name: str,
        context: LogContext | None = None,
    ):
        """
        Initialize the structured logger.

        Args:
            name: Logger name
            context: Logging context
        """
        self._logger = logging.getLogger(name)
        self.context = context or LogContext()

    def _log(
        self,
        level: int,
        message: str,
        **kwargs: Any,
    ) -> None:
        """Internal logging method with extra fields."""
        extra = kwargs.pop("extra", {})
        extra.update(kwargs)
        self._logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message."""
        self._log(logging.CRITICAL, message, **kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        """Log exception with traceback."""
        kwargs["exc_info"] = True
        self._log(logging.ERROR, message, **kwargs)

    def with_context(self, **kwargs: Any) -> "BoundLogger":
        """Create a bound logger with additional context."""
        return BoundLogger(self, kwargs)


class BoundLogger:
    """
    Logger with bound context that is included in all log messages.
    """

    def __init__(
        self,
        parent: StructuredLogger,
        bound_context: dict[str, Any],
    ):
        """
        Initialize bound logger.

        Args:
            parent: Parent structured logger
            bound_context: Context to bind to all messages
        """
        self._parent = parent
        self._bound_context = bound_context

    def _log(
        self,
        level: int,
        message: str,
        **kwargs: Any,
    ) -> None:
        """Log with bound context."""
        merged = {**self._bound_context, **kwargs}
        self._parent._log(level, message, **merged)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message."""
        self._log(logging.CRITICAL, message, **kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        """Log exception with traceback."""
        kwargs["exc_info"] = True
        self._log(logging.ERROR, message, **kwargs)


def configure_logging(
    level: str = "INFO",
    json_output: bool = True,
    context: LogContext | None = None,
    log_file: str | None = None,
) -> None:
    """
    Configure structured logging for the SDK.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: Whether to output JSON format
        context: Logging context
        log_file: Optional log file path
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatter
    if json_output:
        formatter = StructuredFormatter(context)
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(
    name: str,
    context: LogContext | None = None,
) -> StructuredLogger:
    """
    Get a structured logger.

    Args:
        name: Logger name
        context: Optional logging context

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name, context)


def set_correlation_id(correlation_id: str | None = None) -> str:
    """
    Set the correlation ID for the current context.

    Args:
        correlation_id: Optional ID to set (generates one if not provided)

    Returns:
        The correlation ID that was set
    """
    cid = correlation_id or str(uuid4())[:8]
    correlation_id_var.set(cid)
    return cid


def get_correlation_id() -> str | None:
    """Get the current correlation ID."""
    return correlation_id_var.get()


def set_request_id(request_id: str | None = None) -> str:
    """
    Set the request ID for the current context.

    Args:
        request_id: Optional ID to set (generates one if not provided)

    Returns:
        The request ID that was set
    """
    rid = request_id or str(uuid4())[:8]
    request_id_var.set(rid)
    return rid


def get_request_id() -> str | None:
    """Get the current request ID."""
    return request_id_var.get()


def set_agent_id(agent_id: str) -> None:
    """Set the agent ID for the current context."""
    agent_id_var.set(agent_id)


def get_agent_id() -> str | None:
    """Get the current agent ID."""
    return agent_id_var.get()


class LoggingContext:
    """
    Context manager for setting logging context.
    """

    def __init__(
        self,
        correlation_id: str | None = None,
        request_id: str | None = None,
        agent_id: str | None = None,
    ):
        """
        Initialize logging context.

        Args:
            correlation_id: Correlation ID to set
            request_id: Request ID to set
            agent_id: Agent ID to set
        """
        self._correlation_id = correlation_id
        self._request_id = request_id
        self._agent_id = agent_id
        self._old_correlation_id: str | None = None
        self._old_request_id: str | None = None
        self._old_agent_id: str | None = None

    def __enter__(self) -> "LoggingContext":
        """Enter the context."""
        if self._correlation_id is not None:
            self._old_correlation_id = correlation_id_var.get()
            correlation_id_var.set(self._correlation_id)

        if self._request_id is not None:
            self._old_request_id = request_id_var.get()
            request_id_var.set(self._request_id)

        if self._agent_id is not None:
            self._old_agent_id = agent_id_var.get()
            agent_id_var.set(self._agent_id)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context."""
        if self._old_correlation_id is not None:
            correlation_id_var.set(self._old_correlation_id)
        elif self._correlation_id is not None:
            correlation_id_var.set(None)

        if self._old_request_id is not None:
            request_id_var.set(self._old_request_id)
        elif self._request_id is not None:
            request_id_var.set(None)

        if self._old_agent_id is not None:
            agent_id_var.set(self._old_agent_id)
        elif self._agent_id is not None:
            agent_id_var.set(None)
