"""PEA harness 单测（支柱① + 支柱②③ 桥接）。

覆盖：
- 一切皆 LLM 循环：LLM 决定 say/tool。
- guard（USMSB 核心增量）：未知工具拦截、超限支出拦截+人工闸门、主人规则禁止拦截。
- 钱包真实扣款（settle）。
- M2 桥接：两个 PEA 共享账本，经 A2A 运行时 escrow→settle 完成服务交易。
"""

from __future__ import annotations

from typing import Any

import pytest

from usmsb_sdk.economic.pea import (
    LedgerWallet,
    PeaHarness,
    PeaIdentity,
    PersonalEconomicAgent,
    Policy,
    Principal,
)
from usmsb_sdk.protocol.a2a_runtime import (
    SETTLEMENT_SETTLED,
    AgentRuntimeConfig,
    EscrowSettlementHook,
    InMemoryLedgerBackend,
    LocalA2ARuntime,
)


class ScriptedChat:
    """按脚本顺序返回 LLM 响应；脚本用尽后返回一句收尾 say。"""

    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    async def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        if self._responses:
            return self._responses.pop(0)
        return '{"action":"say","text":"好的，处理完成。"}'


class MiaoTestHarness(PeaHarness):
    """喵星球（宠物星座小店）测试 harness。"""

    _READ = {"read_pet_profile"}
    _SIDE_EFFECT = {"create_booking", "purchase_supplies", "auto_refund"}

    def __init__(self, pea: PersonalEconomicAgent, chat: ScriptedChat):
        super().__init__(pea)
        self._chat = chat
        self.dispatched: list[str] = []

    @property
    def system_prompt(self) -> str:
        return "你是喵星球的经营助手，按工具协议输出 JSON 动作。"

    @property
    def chat(self) -> ScriptedChat:
        return self._chat

    def known_tool(self, name: str) -> bool:
        return name in self._READ or name in self._SIDE_EFFECT

    def tool_is_side_effect(self, name: str) -> bool:
        return name in self._SIDE_EFFECT

    async def dispatch(self, conv: Any, name: str, args: dict[str, Any]) -> dict[str, Any]:
        self.dispatched.append(name)
        if name == "read_pet_profile":
            return {"pet": "橘猫", "vip": True}
        if name == "create_booking":
            return {"booking_id": "bk_1", "ok": True}
        if name == "purchase_supplies":
            # 真实花钱：从钱包扣款
            cost = self.estimate_cost(name, args)
            self.pea.wallet.debit(cost)
            return {"purchased": args.get("item"), "cost": cost}
        return {"ok": True}


def _make_pea(ledger: dict[str, float], *, balance: float = 1000.0,
              max_per_tx: float = 200.0, blocked: list[str] | None = None) -> PersonalEconomicAgent:
    ledger["pea_miao"] = balance
    wallet = LedgerWallet("pea_miao", ledger, daily_limit=2000.0)
    identity = PeaIdentity(
        agent_id="pea_miao",
        address="pea_miao",
        principal=Principal(address="0xOwner", name="店主"),
        reputation=0.6,
    )
    policy = Policy(max_per_tx=max_per_tx, daily_limit=2000.0, blocked_actions=blocked or ["auto_refund"])
    return PersonalEconomicAgent(identity, wallet, policy)


# ── 一切皆 LLM：读工具 → 回复 ─────────────────────────────────────────────
async def test_loop_read_tool_then_say():
    ledger: dict[str, float] = {}
    pea = _make_pea(ledger)
    chat = ScriptedChat([
        '{"action":"tool","name":"read_pet_profile","args":{}}',
        '{"action":"say","text":"您的橘猫是 VIP，已为您安排。"}',
    ])
    h = MiaoTestHarness(pea, chat)
    res = await h.run_turn("conv1", "帮我看看我家猫")
    assert h.dispatched == ["read_pet_profile"]
    assert "VIP" in res.reply
    assert res.requires_human is False


# ── guard：未知工具被拦 ────────────────────────────────────────────────────
async def test_guard_blocks_unknown_tool():
    ledger: dict[str, float] = {}
    pea = _make_pea(ledger)
    chat = ScriptedChat([
        '{"action":"tool","name":"hack_database","args":{}}',
        '{"action":"say","text":"换个方式帮您。"}',
    ])
    h = MiaoTestHarness(pea, chat)
    res = await h.run_turn("c", "do something")
    assert h.dispatched == []  # 未知工具未被执行
    assert any("未知工具" in b["reason"] for b in res.blocked)


# ── guard：超单笔限额 → 拦截 + 人工闸门，钱不动 ───────────────────────────
async def test_guard_blocks_over_limit_spend():
    ledger: dict[str, float] = {}
    pea = _make_pea(ledger, balance=1000.0, max_per_tx=200.0)
    chat = ScriptedChat([
        '{"action":"tool","name":"purchase_supplies","args":{"item":"猫粮","vibe_cost":500}}',
    ])
    h = MiaoTestHarness(pea, chat)
    res = await h.run_turn("c", "采购 500 块的猫粮")
    assert h.dispatched == []                       # 超限，未执行
    assert pea.wallet.available() == 1000.0          # 钱没动
    assert res.requires_human is True
    assert any("超单笔限额" in b["reason"] for b in res.blocked)


# ── guard：限额内支出 → 放行，钱包真实扣款 ────────────────────────────────
async def test_allowed_spend_debits_wallet():
    ledger: dict[str, float] = {}
    pea = _make_pea(ledger, balance=1000.0, max_per_tx=200.0)
    chat = ScriptedChat([
        '{"action":"tool","name":"purchase_supplies","args":{"item":"猫砂","vibe_cost":120}}',
        '{"action":"say","text":"已采购猫砂。"}',
    ])
    h = MiaoTestHarness(pea, chat)
    res = await h.run_turn("c", "采购 120 的猫砂")
    assert h.dispatched == ["purchase_supplies"]
    assert pea.wallet.available() == 880.0           # 真实扣款
    assert res.requires_human is False


# ── guard：主人规则禁止的动作 ─────────────────────────────────────────────
async def test_guard_blocks_policy_forbidden_action():
    ledger: dict[str, float] = {}
    pea = _make_pea(ledger, blocked=["auto_refund"])
    chat = ScriptedChat([
        '{"action":"tool","name":"auto_refund","args":{}}',
    ])
    h = MiaoTestHarness(pea, chat)
    res = await h.run_turn("c", "给客户自动退款")
    assert h.dispatched == []
    assert res.requires_human is True
    assert any("主人规则禁止" in b["reason"] for b in res.blocked)


# ── M2 桥接：两个 PEA 经 A2A 运行时完成「委托→交付→VIBE 结算」──────────
class _DeliverHandler:
    """受托 PEA 的 A2A handler：交付服务并通过质量门。"""

    async def handle(self, context) -> dict:
        return {"output": "海报已交付", "quality_gate": "passed", "evidence_uri": "ipfs://poster"}


async def test_m2_two_peas_settle_via_a2a(tmp_path):
    # 共享账本：买方 PEA 1000，卖方 PEA 0
    ledger: dict[str, float] = {"pea_buyer": 1000.0, "pea_seller": 0.0}
    backend = InMemoryLedgerBackend(balances=ledger)
    hook = EscrowSettlementHook(backend, payee="pea_seller")

    cfg = AgentRuntimeConfig(
        agent_id="pea_seller",
        name="雕刻时光设计 PEA",
        description="承接设计服务",
        base_url="http://127.0.0.1:9502",
        data_dir=tmp_path / "seller",
        execute_inline_on_submit=True,
        settlement_enabled=True,
    )
    rt = LocalA2ARuntime(cfg, _DeliverHandler(), settlement_hook=hook)
    rt.initialize()

    # 买方 PEA 通过 A2A 委托一个 150 VIBE 的设计任务
    task = await rt.submit({
        "message": {"parts": [{"kind": "text", "text": "做一张海报"}]},
        "metadata": {"vibe_amount": 150.0, "usmsb": {"caller_id": "pea_buyer", "principal_id": "0xOwnerB"}},
    })

    assert task["status"]["state"] == "completed"
    assert task["metadata"]["settlement_status"] == SETTLEMENT_SETTLED
    # VIBE 从买方流向卖方（链下账本共享，PEA 钱包即时反映）
    assert ledger["pea_buyer"] == 850.0
    assert ledger["pea_seller"] == 150.0
