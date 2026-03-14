"""
Unified Error Handler for USMSB API

Provides standardized error responses with:
- Consistent error codes
- Recovery suggestions
- Request ID tracking
- Detailed stake requirement info
"""

import time
import uuid
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class APIError(Exception):
    """Base API Error with detailed information."""

    def __init__(
        self,
        error: str,
        code: str,
        status_code: int = 400,
        message: str | None = None,
        stake_requirement: dict[str, Any] | None = None,
        retry_after: int | None = None,
        recovery_suggestion: str | None = None,
        request_id: str | None = None,
        details: dict[str, Any] | None = None
    ):
        self.error = error
        self.code = code
        self.status_code = status_code
        self.message = message or error
        self.stake_requirement = stake_requirement
        self.retry_after = retry_after
        self.recovery_suggestion = recovery_suggestion
        self.request_id = request_id or str(uuid.uuid4())
        self.details = details or {}
        super().__init__(self.error)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response."""
        result = {
            "success": False,
            "error": self.error,
            "code": self.code,
            "message": self.message,
            "request_id": self.request_id,
            "timestamp": int(time.time()),
        }

        if self.stake_requirement:
            result["stake_requirement"] = self.stake_requirement

        if self.retry_after is not None:
            result["retry_after"] = self.retry_after

        if self.recovery_suggestion:
            result["recovery_suggestion"] = self.recovery_suggestion

        if self.details:
            result["details"] = self.details

        return result


class ErrorCodes:
    """Standard error codes with categorization."""

    # Stake related (1xx)
    INSUFFICIENT_STAKE = "INSUFFICIENT_STAKE"
    STAKE_LOCKED = "STAKE_LOCKED"
    STAKE_PENDING = "STAKE_PENDING"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"

    # Authentication related (2xx)
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_API_KEY = "INVALID_API_KEY"
    API_KEY_EXPIRED = "API_KEY_EXPIRED"
    API_KEY_REVOKED = "API_KEY_REVOKED"
    AGENT_ID_MISMATCH = "AGENT_ID_MISMATCH"
    MISSING_HEADERS = "MISSING_HEADERS"

    # Resource related (3xx)
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    RESOURCE_LOCKED = "RESOURCE_LOCKED"

    # Validation related (4xx)
    PARSE_ERROR = "PARSE_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    INVALID_STATUS = "INVALID_STATUS"

    # Business logic (5xx)
    BINDING_EXPIRED = "BINDING_EXPIRED"
    ALREADY_BOUND = "ALREADY_BOUND"
    NOT_BOUND = "NOT_BOUND"
    NEGOTIATION_EXPIRED = "NEGOTIATION_EXPIRED"
    NEGOTIATION_COMPLETED = "NEGOTIATION_COMPLETED"
    TRANSACTION_FAILED = "TRANSACTION_FAILED"

    # Network/Server (6xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class RecoverySuggestions:
    """Recovery suggestions for common errors."""

    INSUFFICIENT_STAKE = (
        "Stake at least {shortfall} more VIBE to perform this action. "
        "Visit the binding page or use the stake deposit endpoint."
    )

    API_KEY_EXPIRED = (
        "Your API key has expired. Use the renew API key endpoint to extend it, "
        "or create a new key."
    )

    API_KEY_REVOKED = (
        "This API key has been revoked. Create a new API key."
    )

    UNAUTHORIZED = (
        "Authentication failed. Check that your X-API-Key and X-Agent-ID "
        "headers are correct."
    )

    BINDING_EXPIRED = (
        "The binding request has expired. Request a new binding."
    )

    NOT_BOUND = (
        "This action requires Owner binding. Use the request binding endpoint "
        "to start the binding process."
    )

    NETWORK_ERROR = (
        "Network connection failed. Check your internet connection and try again. "
        "The request will be automatically retried with exponential backoff."
    )

    RATE_LIMITED = (
        "Too many requests. Please wait {retry_after} seconds before trying again."
    )

    STAKE_LOCKED = (
        "Your stake is currently locked in an active transaction. "
        "Please wait for the transaction to complete."
    )

    @classmethod
    def get(cls, code: str, **kwargs) -> str:
        """Get recovery suggestion for an error code."""
        suggestion_map = {
            ErrorCodes.INSUFFICIENT_STAKE: cls.INSUFFICIENT_STAKE,
            ErrorCodes.API_KEY_EXPIRED: cls.API_KEY_EXPIRED,
            ErrorCodes.API_KEY_REVOKED: cls.API_KEY_REVOKED,
            ErrorCodes.UNAUTHORIZED: cls.UNAUTHORIZED,
            ErrorCodes.BINDING_EXPIRED: cls.BINDING_EXPIRED,
            ErrorCodes.NOT_BOUND: cls.NOT_BOUND,
            ErrorCodes.NETWORK_ERROR: cls.NETWORK_ERROR,
            ErrorCodes.RATE_LIMITED: cls.RATE_LIMITED,
            ErrorCodes.STAKE_LOCKED: cls.STAKE_LOCKED,
        }

        template = suggestion_map.get(code)
        if template:
            try:
                return template.format(**kwargs)
            except KeyError:
                return template

        return "Please check the error details and try again."


# Factory functions for common errors

def insufficient_stake_error(
    required: int,
    current: int,
    action: str,
    request_id: str | None = None
) -> APIError:
    """Create an insufficient stake error with detailed info."""
    shortfall = max(0, required - current)

    return APIError(
        error="Insufficient stake",
        code=ErrorCodes.INSUFFICIENT_STAKE,
        status_code=403,
        message=f"Action '{action}' requires {required} VIBE stake, but agent has {current} VIBE",
        stake_requirement={
            "required": required,
            "current": current,
            "shortfall": shortfall,
            "action": action
        },
        recovery_suggestion=RecoverySuggestions.get(
            ErrorCodes.INSUFFICIENT_STAKE,
            shortfall=shortfall
        ),
        request_id=request_id
    )


def unauthorized_error(
    reason: str = "Invalid or missing authentication",
    request_id: str | None = None
) -> APIError:
    """Create an unauthorized error."""
    return APIError(
        error="Unauthorized",
        code=ErrorCodes.UNAUTHORIZED,
        status_code=401,
        message=reason,
        recovery_suggestion=RecoverySuggestions.get(ErrorCodes.UNAUTHORIZED),
        request_id=request_id
    )


def api_key_expired_error(request_id: str | None = None) -> APIError:
    """Create an API key expired error."""
    return APIError(
        error="API key expired",
        code=ErrorCodes.API_KEY_EXPIRED,
        status_code=401,
        message="Your API key has expired",
        recovery_suggestion=RecoverySuggestions.get(ErrorCodes.API_KEY_EXPIRED),
        request_id=request_id
    )


def api_key_revoked_error(request_id: str | None = None) -> APIError:
    """Create an API key revoked error."""
    return APIError(
        error="API key revoked",
        code=ErrorCodes.API_KEY_REVOKED,
        status_code=401,
        message="This API key has been revoked",
        recovery_suggestion=RecoverySuggestions.get(ErrorCodes.API_KEY_REVOKED),
        request_id=request_id
    )


def not_found_error(
    resource_type: str,
    resource_id: str,
    request_id: str | None = None
) -> APIError:
    """Create a not found error."""
    return APIError(
        error="Resource not found",
        code=ErrorCodes.NOT_FOUND,
        status_code=404,
        message=f"{resource_type} '{resource_id}' not found",
        request_id=request_id
    )


def validation_error(
    field: str,
    reason: str,
    request_id: str | None = None
) -> APIError:
    """Create a validation error."""
    return APIError(
        error="Validation error",
        code=ErrorCodes.VALIDATION_ERROR,
        status_code=400,
        message=f"Invalid value for '{field}': {reason}",
        details={"field": field, "reason": reason},
        request_id=request_id
    )


def rate_limited_error(
    retry_after: int,
    request_id: str | None = None
) -> APIError:
    """Create a rate limited error."""
    return APIError(
        error="Rate limited",
        code=ErrorCodes.RATE_LIMITED,
        status_code=429,
        message=f"Too many requests. Retry after {retry_after} seconds.",
        retry_after=retry_after,
        recovery_suggestion=RecoverySuggestions.get(
            ErrorCodes.RATE_LIMITED,
            retry_after=retry_after
        ),
        request_id=request_id
    )


def internal_error(
    message: str = "Internal server error",
    request_id: str | None = None,
    details: dict[str, Any] | None = None
) -> APIError:
    """Create an internal server error."""
    return APIError(
        error="Internal error",
        code=ErrorCodes.INTERNAL_ERROR,
        status_code=500,
        message=message,
        details=details,
        request_id=request_id
    )


def not_bound_error(request_id: str | None = None) -> APIError:
    """Create a not bound error."""
    return APIError(
        error="Agent not bound",
        code=ErrorCodes.NOT_BOUND,
        status_code=403,
        message="This action requires the agent to be bound to an owner",
        recovery_suggestion=RecoverySuggestions.get(ErrorCodes.NOT_BOUND),
        request_id=request_id
    )


def binding_expired_error(request_id: str | None = None) -> APIError:
    """Create a binding expired error."""
    return APIError(
        error="Binding expired",
        code=ErrorCodes.BINDING_EXPIRED,
        status_code=400,
        message="The binding request has expired",
        recovery_suggestion=RecoverySuggestions.get(ErrorCodes.BINDING_EXPIRED),
        request_id=request_id
    )


# Exception handler for FastAPI

async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle APIError exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
        headers={"X-Request-ID": exc.request_id}
    )


# Success response helper

def success_response(
    result: Any,
    message: str | None = None,
    request_id: str | None = None
) -> dict[str, Any]:
    """Create a standardized success response."""
    response = {
        "success": True,
        "result": result,
        "request_id": request_id or str(uuid.uuid4()),
        "timestamp": int(time.time()),
    }

    if message:
        response["message"] = message

    return response
