"""LLM Manager - 多 LLM 支持."""

import inspect
import json
import logging
import re
from collections.abc import Callable
from typing import Any

from usmsb_sdk.intelligence_adapters.base import IntelligenceSourceConfig, IntelligenceSourceType
from usmsb_sdk.intelligence_adapters.llm.minimax_adapter import MiniMaxAdapter
from usmsb_sdk.llm_telemetry import (
    LLMBillingContext,
    LLMEventCallback,
    LLMInvocationRecorder,
    LLMTraceContext,
    llm_context_scope,
    resolve_llm_context,
    update_llm_context,
)

logger = logging.getLogger(__name__)


class LLMManager:
    """LLM 管理器，支持多 LLM"""

    def __init__(
        self,
        config,
        *,
        event_callback: LLMEventCallback | None = None,
        invocation_recorder: LLMInvocationRecorder | None = None,
        default_context: LLMTraceContext | dict[str, Any] | None = None,
    ):
        self.config = config
        self.provider = config.provider
        self.model = config.model
        self.max_tokens = getattr(config, "max_tokens", None)
        self._adapter = None
        configured_recorder = invocation_recorder or getattr(
            config, "invocation_recorder", None
        )
        configured_callback = event_callback or getattr(config, "llm_event_callback", None)
        configured_context = default_context or getattr(config, "llm_trace_context", None)
        if isinstance(configured_recorder, LLMInvocationRecorder):
            self.invocation_recorder = configured_recorder
            if configured_callback:
                self.invocation_recorder.add_callback(configured_callback)
            if configured_context is not None:
                self.invocation_recorder.set_default_context(configured_context)
        else:
            self.invocation_recorder = LLMInvocationRecorder(
                event_callback=configured_callback,
                default_context=configured_context,
                max_calls=int(getattr(config, "llm_history_size", 1000)),
                capture_payloads=bool(getattr(config, "llm_capture_payloads", True)),
            )

    async def init(self):
        """初始化"""
        if self.provider == "minimax":
            await self._init_minimax()
        logger.info(f"LLM Manager initialized with {self.provider}/{self.model}")

    async def _init_minimax(self):
        """初始化 MiniMax 适配器"""
        if not self.config.api_key:
            raise ValueError("MINIMAX_API_KEY is required. Please set it in .env file.")

        config = IntelligenceSourceConfig(
            name="minimax",
            type=IntelligenceSourceType.LLM,
            api_key=self.config.api_key,
            model=self.model or "MiniMax-M2.5",
            extra_params={
                "base_url": self.config.base_url or "https://api.minimaxi.com/v1",
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "reasoning_split": getattr(self.config, "reasoning_split", None),
                "service_tier": getattr(self.config, "service_tier", None),
                "invocation_recorder": self.invocation_recorder,
            },
        )
        self._adapter = MiniMaxAdapter(config)
        await self._adapter.initialize()
        logger.info("MiniMax adapter initialized in LLM Manager")

    def configure_llm_tracking(
        self,
        *,
        callback: LLMEventCallback | None = None,
        default_context: LLMTraceContext | dict[str, Any] | None = None,
    ) -> None:
        """Attach a non-blocking provider-attempt callback and default identity."""

        if callback:
            self.invocation_recorder.add_callback(callback)
        if default_context is not None:
            self.invocation_recorder.set_default_context(default_context)
        if self._adapter and hasattr(self._adapter, "configure_llm_tracking"):
            self._adapter.configure_llm_tracking(
                callback=callback,
                default_context=default_context,
            )

    def trace_scope(
        self,
        context: LLMTraceContext | dict[str, Any] | None = None,
        *,
        billing_context: LLMBillingContext | dict[str, Any] | None = None,
    ):
        resolved = resolve_llm_context(
            context,
            default=self.invocation_recorder.default_context,
        )
        if billing_context:
            resolved = resolved.with_updates(billing=billing_context)
        return llm_context_scope(resolved)

    def update_trace_context(self, **updates: Any):
        """Enrich the current task context (for example after conversation creation)."""

        return update_llm_context(**updates)

    def get_llm_call_details(self, **filters: Any) -> list[dict[str, Any]]:
        return self.invocation_recorder.recent_calls(**filters)

    def get_llm_events(self, *, limit: int = 100) -> list[dict[str, Any]]:
        return self.invocation_recorder.recent_events(limit=limit)

    def drain_llm_events(self, *, limit: int | None = None) -> list[dict[str, Any]]:
        return self.invocation_recorder.drain_events(limit=limit)

    def _call_context(
        self,
        *,
        operation: str,
        trace_context: LLMTraceContext | dict[str, Any] | None = None,
        billing_context: LLMBillingContext | dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> LLMTraceContext:
        resolved = resolve_llm_context(
            trace_context,
            default=self.invocation_recorder.default_context,
        )
        if billing_context:
            resolved = resolved.with_updates(billing=billing_context)
        return resolved.for_logical_call(operation=operation, metadata=metadata)

    async def chat(
        self,
        message: str,
        system_prompt: str | None = None,
        *,
        trace_context: LLMTraceContext | dict[str, Any] | None = None,
        billing_context: LLMBillingContext | dict[str, Any] | None = None,
        operation: str = "chat",
    ) -> str:
        """聊天"""
        call_context = self._call_context(
            operation=operation,
            trace_context=trace_context,
            billing_context=billing_context,
        )
        if self.provider == "minimax" and self._adapter:
            return await self._adapter.generate_with_system(
                system_prompt=system_prompt or "你是一个有用的AI助手。",
                user_prompt=message,
                trace_context=call_context,
                operation=operation,
            )
        elif self.provider == "openai":
            return await self._chat_openai(message, system_prompt)
        elif self.provider == "claude":
            return await self._chat_claude(message, system_prompt)
        elif self.provider == "local":
            return await self._chat_local(message, system_prompt)
        return "LLM not configured"

    async def generate_with_system(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs: Any,
    ) -> str:
        """
        标准接口：system + user prompt → LLM 响应。
        供 GeneCapsuleAdapter 等组件使用，实现 LLM 驱动的体验生成。
        """
        return await self.chat(message=user_prompt, system_prompt=system_prompt, **kwargs)

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> str:
        """
        通用异步生成接口。

        一些上层组件（StrategyRouter、结构化 skill、L5 综合）需要一个稳定的
        `generate()` 方法，而不是猜测底层 adapter 暴露的是 chat 还是
        generate_with_system。这个方法统一转发到当前 provider，并保持向后兼容。
        """
        generation_kwargs = dict(kwargs)
        trace_context = generation_kwargs.pop("trace_context", None)
        billing_context = generation_kwargs.pop("billing_context", None)
        operation = generation_kwargs.pop("operation", "generate")
        call_context = self._call_context(
            operation=operation,
            trace_context=trace_context,
            billing_context=billing_context,
        )
        if max_tokens is not None:
            generation_kwargs["max_tokens"] = max_tokens
        if temperature is not None:
            generation_kwargs["temperature"] = temperature

        if self.provider == "minimax" and self._adapter:
            if system_prompt:
                return await self._adapter.generate_with_system(
                    system_prompt=system_prompt,
                    user_prompt=prompt,
                    trace_context=call_context,
                    operation=operation,
                    **generation_kwargs,
                )
            return await self._adapter.generate_text(
                prompt,
                trace_context=call_context,
                operation=operation,
                **generation_kwargs,
            )

        return await self.chat(
            message=prompt,
            system_prompt=system_prompt,
            trace_context=call_context,
            operation=operation,
        )

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any] | None = None,
        validator: Callable[[dict[str, Any]], Any] | None = None,
        retries: int = 2,
        return_metadata: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generate and parse a JSON object with validation-aware retries.

        Args:
            system_prompt: Stable system instructions.
            user_prompt: Task prompt.
            schema: Optional lightweight JSON-schema-like contract. Currently
                enforces object type and top-level `required` fields.
            validator: Optional sync/async callable. It can return False, raise,
                or return a string/list/dict describing validation errors.
            retries: Number of repair attempts after the first generation.
            return_metadata: When true, returns `{data, raw, attempts, errors}`.
        """
        errors: list[str] = []
        prompt = user_prompt
        last_raw = ""
        attempts = max(0, retries) + 1
        trace_context = kwargs.pop("trace_context", None)
        billing_context = kwargs.pop("billing_context", None)
        root_context = self._call_context(
            operation="generate_json",
            trace_context=trace_context,
            billing_context=billing_context,
        )

        for attempt in range(1, attempts + 1):
            attempt_context = root_context.with_updates(
                operation="generate_json" if attempt == 1 else "generate_json.repair",
                metadata={
                    "json_attempt": attempt,
                    "json_attempt_kind": "initial" if attempt == 1 else "repair",
                },
            )
            last_raw = await self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                trace_context=attempt_context,
                operation=attempt_context.operation or "generate_json",
                **kwargs,
            )
            try:
                data = self._extract_json_object(last_raw)
                self._validate_json_schema(data, schema)
                await self._run_json_validator(data, validator)
                if return_metadata:
                    return {
                        "data": data,
                        "raw": last_raw,
                        "attempts": attempt,
                        "errors": errors,
                    }
                return data
            except Exception as exc:
                errors.append(str(exc))
                if attempt >= attempts:
                    break
                prompt = self._build_json_repair_prompt(
                    user_prompt=user_prompt,
                    invalid_output=last_raw,
                    error=str(exc),
                    schema=schema,
                )

        raise ValueError(
            f"LLM did not produce valid JSON after {attempts} attempts: {errors[-1] if errors else 'unknown error'}"
        )

    def _extract_json_object(self, text: str) -> dict[str, Any]:
        """Extract the first JSON object from raw model output."""
        if not text or not text.strip():
            raise ValueError("empty LLM output")

        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
            stripped = re.sub(r"\s*```$", "", stripped)

        decoder = json.JSONDecoder()
        try:
            obj, _ = decoder.raw_decode(stripped)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{[\s\S]*\}", stripped)
        if match:
            obj = json.loads(match.group(0))
            if isinstance(obj, dict):
                return obj

        raise ValueError("no JSON object found in LLM output")

    def _validate_json_schema(
        self,
        data: dict[str, Any],
        schema: dict[str, Any] | None,
    ) -> None:
        """Lightweight schema validation without adding a hard dependency."""
        if not isinstance(data, dict):
            raise ValueError("JSON output must be an object")
        if not schema:
            return
        if schema.get("type") and schema.get("type") != "object":
            raise ValueError("Only object schemas are supported")
        missing = [key for key in schema.get("required", []) if key not in data]
        if missing:
            raise ValueError(f"missing required JSON fields: {', '.join(missing)}")

    async def _run_json_validator(
        self,
        data: dict[str, Any],
        validator: Callable[[dict[str, Any]], Any] | None,
    ) -> None:
        if not validator:
            return
        result = validator(data)
        if inspect.isawaitable(result):
            result = await result
        if result is False:
            raise ValueError("custom JSON validator returned False")
        if isinstance(result, str) and result.strip():
            raise ValueError(result)
        if isinstance(result, (list, tuple)) and result:
            raise ValueError("; ".join(str(item) for item in result))
        if isinstance(result, dict) and result.get("valid") is False:
            errors = result.get("errors") or result.get("message") or result
            raise ValueError(str(errors))

    def _build_json_repair_prompt(
        self,
        user_prompt: str,
        invalid_output: str,
        error: str,
        schema: dict[str, Any] | None,
    ) -> str:
        schema_text = (
            json.dumps(schema, ensure_ascii=False, indent=2) if schema else "No explicit schema."
        )
        return f"""The previous response was invalid JSON for the requested structured task.

Validation error:
{error}

Expected schema/contract:
{schema_text}

Original task:
{user_prompt}

Previous invalid output:
{invalid_output[:4000]}

Return only one valid JSON object. Do not include markdown, prose, or code fences."""

    def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """
        同步补全方法（供 PurposeGenerator 等使用）

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            max_tokens: 最大 token 数
            temperature: 温度参数
            **kwargs: 其他参数

        Returns:
            str: LLM 响应文本
        """
        import asyncio
        import concurrent.futures

        def run_async():
            """在线程中运行异步代码"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.chat(
                        prompt,
                        system_prompt,
                        trace_context=kwargs.get("trace_context"),
                        billing_context=kwargs.get("billing_context"),
                        operation=kwargs.get("operation", "complete"),
                    )
                )
            finally:
                loop.close()

        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_async)
                return future.result(timeout=60)
        except Exception as e:
            logger.error(f"[LLMManager] complete() error: {e}")
            return f"LLM error: {str(e)}"

    async def _chat_openai(self, message: str, system_prompt: str | None) -> str:
        """OpenAI 聊天"""
        return f"OpenAI response to: {message}"

    async def _chat_claude(self, message: str, system_prompt: str | None) -> str:
        """Claude 聊天"""
        return f"Claude response to: {message}"

    async def _chat_local(self, message: str, system_prompt: str | None) -> str:
        """本地 LLM 聊天"""
        return f"Local LLM response to: {message}"
