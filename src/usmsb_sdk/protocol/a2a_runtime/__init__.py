"""USMSB 生产级 A2A 运行时（支柱②：协作=服务市场）。

特性：每 Agent 私有持久队列 + 幂等键 + manual_intervention 一等状态 +
bounded retries + Agent Card / JSON-RPC + VIBE 结算闭环（escrow→settle/refund）。

移植自 opc-platform/agents/local_a2a_runtime 并焊接 USMSB 经济结算。
对比 protocol/a2a_adapter.py（内存总线，仅用于本地多 Agent 模拟/单测）。
"""

from .client import A2AClient, A2ARemoteError
from .config import AgentRuntimeConfig, AgentSkill
from .runtime import (
    A2AJsonRpcError,
    AgentHandler,
    AgentJobContext,
    EchoAgentHandler,
    LocalA2ARuntime,
)
from .settlement import (
    EscrowSettlementHook,
    InMemoryLedgerBackend,
    NoOpSettlementHook,
    SettlementBackend,
    SettlementHook,
)
from .store import (
    SETTLEMENT_DISPUTED,
    SETTLEMENT_ESCROWED,
    SETTLEMENT_NONE,
    SETTLEMENT_REFUNDED,
    SETTLEMENT_SETTLED,
    JobRecord,
    SQLiteJobStore,
)
from .trust import NoOpTrustHook, TrustHook

__all__ = [
    "AgentRuntimeConfig",
    "AgentSkill",
    "LocalA2ARuntime",
    "AgentHandler",
    "AgentJobContext",
    "EchoAgentHandler",
    "A2AJsonRpcError",
    "SQLiteJobStore",
    "JobRecord",
    "SettlementHook",
    "SettlementBackend",
    "NoOpSettlementHook",
    "EscrowSettlementHook",
    "InMemoryLedgerBackend",
    "TrustHook",
    "NoOpTrustHook",
    "A2AClient",
    "A2ARemoteError",
    "SETTLEMENT_NONE",
    "SETTLEMENT_ESCROWED",
    "SETTLEMENT_SETTLED",
    "SETTLEMENT_REFUNDED",
    "SETTLEMENT_DISPUTED",
]
