"""A2A 运行时的信任钩子（支柱③：把交付结果接到声誉/争议）。

与结算钩子并列：结算管"钱怎么走"，信任管"声誉怎么变、要不要争议"。
运行时在 job 终态调用本钩子；具体实现（接 ReputationService / VIBDispute）由
usmsb_sdk.trust.TrustBridge 注入，保持 protocol 层不依赖上层服务。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .store import JobRecord


@runtime_checkable
class TrustHook(Protocol):
    """运行时在 job 终态调用。provider_id = 本 Agent（受托/交付方）。"""

    async def on_settled(self, job: JobRecord, provider_id: str) -> None: ...
    async def on_refunded(self, job: JobRecord, provider_id: str) -> None: ...
    async def on_manual_intervention(self, job: JobRecord, provider_id: str) -> None: ...


class NoOpTrustHook:
    """默认空实现：不接声誉/争议。"""

    async def on_settled(self, job: JobRecord, provider_id: str) -> None:
        return None

    async def on_refunded(self, job: JobRecord, provider_id: str) -> None:
        return None

    async def on_manual_intervention(self, job: JobRecord, provider_id: str) -> None:
        return None
