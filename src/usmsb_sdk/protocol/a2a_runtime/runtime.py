"""USMSB 生产级 A2A 运行时。

移植自 opc-platform/agents/local_a2a_runtime，增加 VIBE 结算闭环。

设计哲学（受约束 Loop Engineering）：
- 协议 / 幂等 / 持久 / 重试边界 / 结算 由代码（本运行时）强制保证。
- 具体"能力"由注入的 AgentHandler 实现（可以是 LLM harness、provider 调用等）。
- manual_intervention_required 是一等可交付状态，不是异常。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .config import AgentRuntimeConfig, AgentSkill
from .settlement import NoOpSettlementHook, SettlementHook
from .store import SETTLEMENT_ESCROWED, JobRecord, SQLiteJobStore
from .trust import NoOpTrustHook, TrustHook

logger = logging.getLogger(__name__)


class A2AJsonRpcError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass
class AgentJobContext:
    """传给具体 Agent handler 的执行上下文。"""

    job: JobRecord
    asset_dir: Path

    @property
    def input_text(self) -> str:
        return self.job.input_text

    @property
    def payload(self) -> dict[str, Any]:
        return self.job.payload

    @property
    def metadata(self) -> dict[str, Any]:
        value = self.payload.get("metadata")
        return value if isinstance(value, dict) else {}


class AgentHandler(Protocol):
    async def handle(self, context: AgentJobContext) -> dict[str, Any]:
        """执行一个已领取的 job，返回可 JSON 序列化的结果。

        约定结果字段（可选）：
            status: "manual_intervention_required" → 进人工闸门（结算保持托管）
            quality_gate: "passed" | "failed"       → 质量门结论（决定是否释放托管）
            evidence_uri: str                        → 证据/artifact 位置
            output / text / content / url: str       → 对外文本产物
        """


class EchoAgentHandler:
    """冒烟测试用 handler。"""

    async def handle(self, context: AgentJobContext) -> dict[str, Any]:
        return {
            "output": f"echo: {context.input_text}",
            "job_id": context.job.id,
            "quality_gate": "passed",
        }


class LocalA2ARuntime:
    """A2A 兼容的本地运行时，由 Agent 私有 SQLite 队列支撑，可选 VIBE 结算。"""

    def __init__(
        self,
        config: AgentRuntimeConfig,
        handler: AgentHandler,
        store: SQLiteJobStore | None = None,
        settlement_hook: SettlementHook | None = None,
        trust_hook: TrustHook | None = None,
    ):
        self.config = config
        self.handler = handler
        self.store = store or SQLiteJobStore(config.db_path)
        self.settlement: SettlementHook = settlement_hook or NoOpSettlementHook()
        self.trust: TrustHook = trust_hook or NoOpTrustHook()
        self._worker_tasks: list[asyncio.Task] = []
        self._stopping = asyncio.Event()
        self._worker_prefix = f"{config.agent_id}-{uuid.uuid4().hex[:8]}"

    # ── 生命周期 ───────────────────────────────────────────────────────────
    def initialize(self) -> None:
        self.config.root_dir.mkdir(parents=True, exist_ok=True)
        self.config.assets_dir.mkdir(parents=True, exist_ok=True)
        self.config.logs_dir.mkdir(parents=True, exist_ok=True)
        self.store.initialize()

    async def start(self) -> None:
        self.initialize()
        self._stopping.clear()
        for index in range(max(1, self.config.max_concurrency)):
            worker_id = f"{self._worker_prefix}-{index}"
            self._worker_tasks.append(asyncio.create_task(self._worker_loop(worker_id)))

    async def stop(self) -> None:
        self._stopping.set()
        for task in self._worker_tasks:
            task.cancel()
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()

    # ── Agent Card / JSON-RPC ─────────────────────────────────────────────
    def build_agent_card(self) -> dict[str, Any]:
        skills = self.config.skills or [
            AgentSkill(id="default", name=self.config.name, description=self.config.description)
        ]
        return {
            "protocolVersion": "0.3.0",
            "name": self.config.name,
            "description": self.config.description,
            "url": self.config.rpc_url,
            "version": self.config.version,
            "capabilities": {
                "streaming": False,
                "pushNotifications": False,
                "stateTransitionHistory": True,
                # USMSB 扩展：声明本 Agent 支持 VIBE 结算
                "vibeSettlement": self.config.settlement_enabled,
            },
            "defaultInputModes": self.config.default_input_modes,
            "defaultOutputModes": self.config.default_output_modes,
            "skills": [s.to_agent_card_dict() for s in skills],
            "supported_interfaces": [
                {
                    "url": self.config.rpc_url,
                    "protocol_binding": "jsonrpc",
                    "methods": ["message/send", "tasks/send", "tasks/get"],
                }
            ],
        }

    async def handle_jsonrpc(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise A2AJsonRpcError(-32600, "Invalid JSON-RPC request")
        method = str(payload.get("method") or "")
        params = payload.get("params") or {}
        if not isinstance(params, dict):
            raise A2AJsonRpcError(-32602, "params must be an object")

        if method in {"message/send", "tasks/send"}:
            return await self.submit(params)
        if method == "tasks/get":
            task_id = self._extract_task_id_from_get(params)
            if not task_id:
                raise A2AJsonRpcError(-32602, "tasks/get requires taskId")
            job = self.store.get_job(task_id)
            if not job:
                raise A2AJsonRpcError(-32004, f"Task not found: {task_id}")
            return self._task_from_job(job)
        raise A2AJsonRpcError(-32601, f"Method not found: {method}")

    # ── 提交 ───────────────────────────────────────────────────────────────
    async def submit(self, params: dict[str, Any]) -> dict[str, Any]:
        message = params.get("message")
        if not isinstance(message, dict):
            raise A2AJsonRpcError(-32602, "message is required")

        input_text = self._extract_text(message)
        metadata = self._merge_metadata(params, message)
        usmsb = metadata.get("usmsb") if isinstance(metadata.get("usmsb"), dict) else {}
        job_id = self._message_value(message, "taskId", "task_id") or f"task_{uuid.uuid4().hex}"
        idempotency_key = self._build_idempotency_key(message, input_text, metadata)
        vibe_amount = self._extract_vibe_amount(metadata, usmsb)
        payload = {
            "params": params,
            "message": message,
            "metadata": metadata,
            "received_at": time.time(),
            "agent_id": self.config.agent_id,
        }
        job = self.store.enqueue_job(
            job_id=job_id,
            idempotency_key=idempotency_key,
            input_text=input_text,
            payload=payload,
            caller_id=str(usmsb.get("caller_id") or usmsb.get("user_id") or ""),
            correlation_id=str(usmsb.get("correlation_id") or usmsb.get("execution_id") or ""),
            a2a_message_id=str(usmsb.get("a2a_message_id") or ""),
            principal_id=str(usmsb.get("principal_id") or metadata.get("principal_id") or ""),
            task_type=str(
                metadata.get("task_type") or params.get("skillId") or params.get("skill_id") or "generic"
            ),
            priority=int(metadata.get("priority") or 0),
            max_attempts=int(metadata.get("max_attempts") or self.config.max_attempts),
            vibe_amount=vibe_amount,
        )

        # 结算：仅对"新入队"的付费任务开托管（幂等——已存在的 job 不重复开）
        if (
            self.config.settlement_enabled
            and job.vibe_amount > 0
            and job.status == "queued"
            and job.settlement_status == "none"
        ):
            updates = await self.settlement.on_escrow(job, payee=self.config.agent_id)
            if updates:
                job = self.store.update_settlement(
                    job.id,
                    escrow_id=updates.get("escrow_id"),
                    settlement_status=updates.get("settlement_status"),
                ) or job

        if self.config.execute_inline_on_submit and job.status == "queued":
            await self.run_pending_once()
            job = self.store.get_job(job.id) or job

        return self._task_from_job(job)

    # ── 执行 ───────────────────────────────────────────────────────────────
    async def run_pending_once(self) -> JobRecord | None:
        worker_id = f"{self._worker_prefix}-manual"
        job = self.store.claim_next(worker_id=worker_id, lock_seconds=self.config.lock_seconds)
        if not job:
            return None
        return await self._execute_job(job)

    async def _worker_loop(self, worker_id: str) -> None:
        while not self._stopping.is_set():
            job = self.store.claim_next(worker_id=worker_id, lock_seconds=self.config.lock_seconds)
            if not job:
                await asyncio.sleep(self.config.poll_interval_seconds)
                continue
            await self._execute_job(job)

    async def _execute_job(self, job: JobRecord) -> JobRecord | None:
        asset_dir = self.config.assets_dir / job.id
        asset_dir.mkdir(parents=True, exist_ok=True)
        context = AgentJobContext(job=job, asset_dir=asset_dir)
        try:
            result = await self.handler.handle(context)
        except Exception as exc:  # noqa: BLE001
            failed = self.store.mark_failed(job.id, str(exc), retryable=True)
            # 不可重试的终态 + 托管中 → 退款 + 声誉扣分/争议
            if failed and failed.status == "failed":
                await self._maybe_refund(failed)
                await self.trust.on_refunded(self.store.get_job(job.id) or failed, self.config.agent_id)
            return self.store.get_job(job.id) or failed

        # 人工闸门：结算保持托管，等人工裁决
        if result.get("status") == "manual_intervention_required":
            manual = self.store.mark_manual_intervention(
                job.id, result=result,
                error=str(result.get("error") or "manual intervention required"),
            )
            await self.trust.on_manual_intervention(manual or job, self.config.agent_id)
            return manual

        quality_gate = str(result.get("quality_gate") or "passed")
        evidence_uri = str(result.get("evidence_uri") or "")
        done = self.store.mark_succeeded(
            job.id, result=result, quality_gate=quality_gate, evidence_uri=evidence_uri,
        )

        # 结算：成功 + 质量门通过 + 托管中 → 释放给受托方
        if done and quality_gate == "passed":
            await self._maybe_settle(done)
            # 信任：质量门通过的交付 → 受托方声誉加分
            await self.trust.on_settled(self.store.get_job(job.id) or done, self.config.agent_id)
        elif done and quality_gate == "failed":
            # 质量门未过 → 受托方声誉扣分（钱仍在托管，等争议/人工）
            await self.trust.on_refunded(done, self.config.agent_id)
        return self.store.get_job(job.id)

    async def _maybe_settle(self, job: JobRecord) -> None:
        if job.settlement_status != SETTLEMENT_ESCROWED:
            return
        updates = await self.settlement.on_settle(job)
        if updates:
            self.store.update_settlement(
                job.id, settlement_status=updates.get("settlement_status")
            )

    async def _maybe_refund(self, job: JobRecord) -> None:
        if job.settlement_status != SETTLEMENT_ESCROWED:
            return
        updates = await self.settlement.on_refund(job)
        if updates:
            self.store.update_settlement(
                job.id, settlement_status=updates.get("settlement_status")
            )

    # ── A2A Task 投影 ──────────────────────────────────────────────────────
    def _task_from_job(self, job: JobRecord) -> dict[str, Any]:
        state = self._a2a_state(job.status)
        output_text = self._output_text(job)
        status_message = (
            {"role": "agent", "parts": [{"kind": "text", "text": output_text}]}
            if output_text else None
        )
        task: dict[str, Any] = {
            "id": job.id,
            "status": {"state": state, "timestamp": job.updated_at},
            "metadata": {
                "agent_id": self.config.agent_id,
                "local_status": job.status,
                "attempts": job.attempts,
                "correlation_id": job.correlation_id,
                "idempotency_key": job.idempotency_key,
                # USMSB 经济投影
                "vibe_amount": job.vibe_amount,
                "settlement_status": job.settlement_status,
                "quality_gate": job.quality_gate,
                "principal_id": job.principal_id,
            },
        }
        if status_message:
            task["status"]["message"] = status_message
        if job.status in {"succeeded", "manual_intervention_required", "failed"}:
            parts: list[dict[str, Any]] = [{"kind": "text", "text": output_text or job.error}]
            if job.result:
                parts.append({"kind": "data", "data": job.result})
            task["artifacts"] = [
                {"artifactId": f"{job.id}-result", "name": "result", "parts": parts}
            ]
        return task

    def _a2a_state(self, status: str) -> str:
        if status == "succeeded":
            return "completed"
        if status == "failed":
            return "failed"
        if status == "manual_intervention_required":
            return "auth-required"
        return "working"

    def _output_text(self, job: JobRecord) -> str:
        if job.status == "failed":
            return job.error
        result = job.result or {}
        for key in ("output", "text", "content", "url"):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        if result:
            return json.dumps(result, ensure_ascii=False)
        return job.error

    # ── 工具方法 ───────────────────────────────────────────────────────────
    def _extract_vibe_amount(self, metadata: dict[str, Any], usmsb: dict[str, Any]) -> float:
        raw = metadata.get("vibe_amount")
        if raw is None:
            raw = usmsb.get("vibe_amount")
        try:
            return float(raw) if raw is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    def _build_idempotency_key(
        self, message: dict[str, Any], input_text: str, metadata: dict[str, Any]
    ) -> str:
        usmsb = metadata.get("usmsb") if isinstance(metadata.get("usmsb"), dict) else {}
        explicit = (
            metadata.get("idempotency_key")
            or metadata.get("idempotencyKey")
            or usmsb.get("idempotency_key")
            or usmsb.get("idempotencyKey")
        )
        if explicit:
            return f"{self.config.agent_id}:explicit:{explicit}"
        correlation_id = str(usmsb.get("correlation_id") or usmsb.get("execution_id") or "")
        if correlation_id:
            return f"{self.config.agent_id}:{correlation_id}"
        task_id = self._message_value(message, "taskId", "task_id")
        if task_id:
            return f"{self.config.agent_id}:task:{task_id}"
        message_id = self._message_value(message, "messageId", "message_id")
        if message_id:
            return f"{self.config.agent_id}:message:{message_id}"
        digest = hashlib.sha256(
            json.dumps(
                {"input": input_text, "metadata": metadata}, sort_keys=True, ensure_ascii=False
            ).encode("utf-8")
        ).hexdigest()
        return f"{self.config.agent_id}:hash:{digest}"

    def _extract_text(self, message: dict[str, Any]) -> str:
        parts = message.get("parts")
        texts: list[str] = []
        if isinstance(parts, list):
            for part in parts:
                if isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        texts.append(text.strip())
        return "\n".join(texts).strip()

    def _merge_metadata(self, params: dict[str, Any], message: dict[str, Any]) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for source in (params.get("metadata"), message.get("metadata")):
            if isinstance(source, dict):
                merged.update(source)
        return merged

    def _extract_task_id_from_get(self, params: dict[str, Any]) -> str:
        return str(params.get("taskId") or params.get("task_id") or params.get("id") or "")

    def _message_value(self, message: dict[str, Any], camel_key: str, snake_key: str) -> str:
        return str(message.get(camel_key) or message.get(snake_key) or "")
