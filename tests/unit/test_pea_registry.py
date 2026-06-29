"""PeaRegistry 单测（#1b：PEA 创建/查询/运行入口）。"""

from __future__ import annotations

from typing import Any

import pytest

from usmsb_sdk.economic.pea_registry import PeaRegistry
from usmsb_sdk.products.super_individual.butler_pea import ButlerPea, ButlerProfile


class ScriptedChat:
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    async def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        return self._responses.pop(0) if self._responses else '{"action":"say","text":"完成。"}'


async def test_create_register_and_run():
    reg = PeaRegistry()
    pea = reg.create(
        agent_id="butler", principal_address="0xOwner", balance=1000.0, max_per_tx=200.0,
    )
    chat = ScriptedChat([
        '{"action":"tool","name":"add_task","args":{"title":"写周报"}}',
        '{"action":"say","text":"已加到待办。"}',
    ])
    reg.register_harness("butler", ButlerPea(pea, chat, ButlerProfile(user_name="老顾")))

    assert reg.list_ids() == ["butler"]
    assert reg.get("butler") is pea
    assert reg.balance_of("butler") == 1000.0

    res = await reg.run_turn("butler", "c1", "帮我加个写周报的待办")
    assert any(s.get("tool") == "add_task" for s in res.steps)
    assert "待办" in res.reply


async def test_shared_ledger_across_peas():
    reg = PeaRegistry()
    reg.create(agent_id="buyer", principal_address="0xA", balance=500.0)
    reg.create(agent_id="seller", principal_address="0xB", balance=0.0)
    # 同一账本 → 可被 vibe_settlement 复用做 PEA 间结算
    assert reg.ledger["buyer"] == 500.0 and reg.ledger["seller"] == 0.0
    assert set(reg.list_ids()) == {"buyer", "seller"}


async def test_duplicate_and_missing_errors():
    reg = PeaRegistry()
    reg.create(agent_id="x", principal_address="0x")
    with pytest.raises(ValueError):
        reg.create(agent_id="x", principal_address="0x")  # 重复
    with pytest.raises(KeyError):
        await reg.run_turn("ghost", "c", "hi")  # 无 harness
