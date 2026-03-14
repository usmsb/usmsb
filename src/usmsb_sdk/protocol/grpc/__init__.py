"""
gRPC Protocol Module

This module provides gRPC protocol implementation for high-performance communication.

Usage:
    from usmsb_sdk.protocol.grpc import gRPCHandler, gRPCConfig
    config = gRPCConfig(use_ssl=False)
    handler = gRPCHandler(grpc_config=config)
    await handler.connect("localhost:50051")
    result = await handler.call_skill("MyService.MyMethod", {"arg": "value"})
"""

from usmsb_sdk.protocol.grpc.handler import (
    GRPC_AVAILABLE,
    ConnectionEndpoint,
    ConnectionPool,
    LoadBalancingStrategy,
    ProtoMessageBuilder,
    call_grpc_method,
    create_grpc_handler,
    gRPCConfig,
    gRPCError,
    gRPCErrorCode,
    gRPCHandler,
    gRPCMethod,
    gRPCRequest,
    gRPCResponse,
    gRPCServiceDefinition,
)

__all__ = [
    "gRPCHandler",
    "gRPCConfig",
    "gRPCMethod",
    "gRPCRequest",
    "gRPCResponse",
    "gRPCServiceDefinition",
    "gRPCError",
    "gRPCErrorCode",
    "LoadBalancingStrategy",
    "ConnectionPool",
    "ConnectionEndpoint",
    "ProtoMessageBuilder",
    "create_grpc_handler",
    "call_grpc_method",
    "GRPC_AVAILABLE",
]
