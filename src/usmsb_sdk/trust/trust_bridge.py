"""TrustBridge —— 把 A2A 交付结果映射到声誉与争议（支柱③信任工程）。

OPC 的 Quality Gate / Human Gate 是信任层的工程形态；本桥接把它们落到 USMSB 链上能力：
    质量门通过的交付   → ReputationService 声誉加分（reliability + quality）
    质量门失败 / 退款   → 声誉扣分 +（可选）开 VIBDispute 争议
    人工闸门            → 不动声誉（等人裁决）

实现 a2a_runtime.TrustHook（结构化协议）；ReputationService 与 DisputeOpener 注入，
无则优雅降级（不报错）。
"""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class DisputeOpener(Protocol):
    """开争议的抽象（可由 order_service / VIBDispute 合约 / 自定义实现注入）。"""

    async def open_dispute(
        self, *, job_id: str, claimant: str, respondent: str, amount: float, reason: str
    ) -> dict[str, Any]: ...


class TrustBridge:
    """把 job 终态接到声誉服务与争议流程。"""

    def __init__(
        self,
        reputation_service: Any | None = None,
        *,
        dispute_opener: DisputeOpener | None = None,
        open_dispute_on_failure: bool = True,
    ):
        self.reputation = reputation_service
        self.dispute_opener = dispute_opener
        self.open_dispute_on_failure = open_dispute_on_failure

    # ── TrustHook 接口 ─────────────────────────────────────────────────────
    async def on_settled(self, job: Any, provider_id: str) -> None:
        """质量门通过的成功交付 → 受托方声誉加分。"""
        self._record_tx(provider_id, job, was_successful=True, on_time=True)

    async def on_refunded(self, job: Any, provider_id: str) -> None:
        """退款 / 质量门失败 → 受托方声誉扣分 +（可选）开争议。"""
        self._record_tx(provider_id, job, was_successful=False, on_time=False)
        if self.open_dispute_on_failure and self.dispute_opener is not None:
            try:
                await self.dispute_opener.open_dispute(
                    job_id=str(getattr(job, "id", "")),
                    claimant=str(getattr(job, "caller_id", "")),
                    respondent=provider_id,
                    amount=float(getattr(job, "vibe_amount", 0) or 0),
                    reason=str(getattr(job, "error", "") or "delivery failed quality gate"),
                )
            except Exception as e:  # noqa: BLE001
                logger.error("[trust] open_dispute failed: %s", e)

    async def on_manual_intervention(self, job: Any, provider_id: str) -> None:
        """人工闸门：不动声誉，等人裁决。"""
        return None

    # ── 内部 ───────────────────────────────────────────────────────────────
    def _record_tx(self, provider_id: str, job: Any, *, was_successful: bool, on_time: bool) -> None:
        if self.reputation is None or not provider_id:
            return
        try:
            self.reputation.record_transaction_completed(
                agent_id=provider_id,
                transaction_id=str(getattr(job, "id", "")),
                was_successful=was_successful,
                as_role="provider",
                amount=float(getattr(job, "vibe_amount", 0) or 0),
                on_time=on_time,
            )
        except Exception as e:  # noqa: BLE001
            logger.error("[trust] record_transaction_completed failed: %s", e)
