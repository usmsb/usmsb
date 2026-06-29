"""ButlerPea 单测（#2：退役旧 stub，重写为 harness PEA）。

覆盖：products 包安全导入（旧 stub 坏了不连累）、晨报 prompt skill、
派活花钱过 guard 限额、超限→人工闸门。
"""

from __future__ import annotations

from typing import Any

import pytest

from usmsb_sdk.economic.pea import (
    LedgerWallet,
    PeaIdentity,
    PersonalEconomicAgent,
    Policy,
    Principal,
)
from usmsb_sdk.products.super_individual.butler_pea import ButlerPea, ButlerProfile


class ScriptedChat:
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    async def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        return self._responses.pop(0) if self._responses else '{"action":"say","text":"完成。"}'


def _butler(chat, *, balance=1000.0, max_per_tx=200.0) -> ButlerPea:
    ledger = {"butler": balance}
    pea = PersonalEconomicAgent(
        identity=PeaIdentity("butler", "butler", Principal("0xOwner", "主人"), reputation=0.6),
        wallet=LedgerWallet("butler", ledger, daily_limit=2000.0),
        policy=Policy(max_per_tx=max_per_tx, daily_limit=2000.0, blocked_actions=[]),
    )
    profile = ButlerProfile(user_name="老顾", goals=["把 USMSB 做成闭环"])
    return ButlerPea(pea, chat, profile)


# ── products 包不再因旧 stub 崩溃 ──────────────────────────────────────────
def test_products_package_imports_safely():
    import usmsb_sdk.products as products
    assert products.ButlerPea is not None        # v3.0 实现可用
    # 旧 stub 即使坏了也只是 None，不抛 ImportError
    assert hasattr(products, "ButlerAgent")


# ── 晨报：prompt skill 用 LLM 生成 ─────────────────────────────────────────
async def test_morning_briefing_prompt_skill():
    chat = ScriptedChat([
        '{"action":"tool","name":"generate_briefing","args":{"kind":"morning"}}',
        '{"action":"say","text":"晨报已生成。"}',
    ])
    # 第 1 次 complete 返回工具动作；generate_briefing 内部会再调一次 complete 生成正文；
    # 为可控，给 chat 预置足够响应：
    chat = ScriptedChat([
        '{"action":"tool","name":"generate_briefing","args":{"kind":"morning"}}',
        "今日要点：1) 推进闭环 2) 跑通管家 PEA",   # generate_briefing 内部 LLM 正文
        '{"action":"say","text":"晨报已发您。"}',
    ])
    b = _butler(chat)
    res = await b.run_turn("c1", "给我来个今日晨报")
    briefing_steps = [s for s in res.steps if s.get("tool") == "generate_briefing"]
    assert briefing_steps
    assert "今日要点" in briefing_steps[0]["result"]["briefing"]
    assert res.requires_human is False


# ── 派活花钱：限额内放行 ───────────────────────────────────────────────────
async def test_delegate_within_limit_allowed():
    chat = ScriptedChat([
        '{"action":"tool","name":"delegate_to_specialist","args":{"task":"做海报","vibe_cost":120}}',
        '{"action":"say","text":"已把海报外包给设计 PEA。"}',
    ])
    b = _butler(chat, max_per_tx=200.0)
    res = await b.run_turn("c2", "找人做张海报")
    assert any(s.get("tool") == "delegate_to_specialist" for s in res.steps)
    assert res.requires_human is False


# ── 派活超限：guard 拦截 + 人工闸门 ────────────────────────────────────────
async def test_delegate_over_limit_blocked():
    chat = ScriptedChat([
        '{"action":"tool","name":"delegate_to_specialist","args":{"task":"拍广告片","vibe_cost":900}}',
    ])
    b = _butler(chat, max_per_tx=200.0)
    res = await b.run_turn("c3", "外包一条广告片")
    assert res.requires_human is True
    assert any("超单笔限额" in x["reason"] for x in res.blocked)
