"""evolution 后台触发单测（Task 6：去掉 if False，改非阻塞后台异步）。

验证 MetaAgent._trigger_background_evolution 的「单飞 + 限频 + 不阻塞 + 异常自吞」。
用 MetaAgent.__new__ 绕过重型 __init__，只测这块逻辑。
"""

from __future__ import annotations

import asyncio

import pytest

from usmsb_sdk.meta_agent.agent import MetaAgent


class _FakeEngine:
    def __init__(self, gate: asyncio.Event | None = None, raises: bool = False):
        self.calls = 0
        self.gate = gate
        self.raises = raises

    async def evolve(self) -> dict:
        self.calls += 1
        if self.gate is not None:
            await self.gate.wait()
        if self.raises:
            raise RuntimeError("evolve boom")
        return {"knowledge_added": 1, "patterns_identified": 2}


def _agent(engine, *, min_interval: float = 0.0) -> MetaAgent:
    a = MetaAgent.__new__(MetaAgent)          # 不跑重型 __init__
    a.evolution_engine = engine
    a._evolution_min_interval = min_interval
    return a


# ── 后台触发并执行 evolve（不阻塞调用方）──────────────────────────────────
async def test_trigger_runs_evolution_in_background():
    eng = _FakeEngine()
    a = _agent(eng)
    a._trigger_background_evolution()          # 同步返回，不 await evolve
    task = a._evolution_bg_task
    assert task is not None and not task.done()  # 已排到后台
    await task
    assert eng.calls == 1


# ── 单飞：进行中不重复触发 ─────────────────────────────────────────────────
async def test_single_flight_no_duplicate_while_running():
    gate = asyncio.Event()
    eng = _FakeEngine(gate=gate)
    a = _agent(eng)
    a._trigger_background_evolution()
    first = a._evolution_bg_task
    a._trigger_background_evolution()          # 上一个还卡在 gate 上 → 不应新建
    assert a._evolution_bg_task is first
    gate.set()
    await first
    assert eng.calls == 1


# ── 限频：间隔内不重复触发 ─────────────────────────────────────────────────
async def test_rate_limited_within_interval():
    eng = _FakeEngine()
    a = _agent(eng, min_interval=9999.0)
    a._trigger_background_evolution()
    await a._evolution_bg_task
    assert eng.calls == 1
    a._trigger_background_evolution()          # 距上次太近 → 跳过
    # 没有新任务被创建（上一个已 done，且限频拦截）
    assert a._evolution_bg_task.done()
    assert eng.calls == 1


# ── 无引擎：no-op，不崩 ────────────────────────────────────────────────────
async def test_no_engine_is_noop():
    a = _agent(None)
    a._trigger_background_evolution()
    assert getattr(a, "_evolution_bg_task", None) is None


# ── 异常自吞：evolve 抛错不外溢 ────────────────────────────────────────────
async def test_background_evolution_swallows_errors():
    eng = _FakeEngine(raises=True)
    a = _agent(eng)
    a._trigger_background_evolution()
    await a._evolution_bg_task                  # 不应抛异常
    assert eng.calls == 1
