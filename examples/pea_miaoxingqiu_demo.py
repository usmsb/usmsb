"""喵星球 PEA 参考实现 Demo —— 验证 v3.0 三支柱（M1 + M2）。

跑法：
    cd /Users/gujun/vibecode/usmsb
    python examples/pea_miaoxingqiu_demo.py

本 demo 内置脚本化 LLM（无需 API Key 即可跑）。换成真实 LLM 只需把 ScriptedChat
替换为一个实现 `async complete(messages, **kw) -> str` 的 MiniMax/Claude provider。

演示：
  支柱①（个体=经济公民）：BaseHarness「一切皆 LLM」循环 + guard 安全闸门。
  支柱②③（协作=市场 + 链上结算）：两个 PEA 经生产级 A2A 运行时完成
        「服务委托 → 交付 → VIBE 托管结算 → 余额变动」。
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from usmsb_sdk.economic.pea import (  # noqa: E402
    LedgerWallet,
    PeaHarness,
    PeaIdentity,
    PersonalEconomicAgent,
    Policy,
    Principal,
)
from usmsb_sdk.protocol.a2a_runtime import (  # noqa: E402
    AgentRuntimeConfig,
    EscrowSettlementHook,
    InMemoryLedgerBackend,
    LocalA2ARuntime,
)


class ScriptedChat:
    """脚本化 LLM：按顺序吐预设动作。生产环境替换为真实 LLM provider。"""

    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    async def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        return self._responses.pop(0) if self._responses else '{"action":"say","text":"完成。"}'


class MiaoxingqiuHarness(PeaHarness):
    """喵星球（宠物星座小店）经营 PEA。"""

    _READ = {"read_pet_profile"}
    _SIDE_EFFECT = {"create_booking", "purchase_supplies", "auto_refund"}

    def __init__(self, pea: PersonalEconomicAgent, chat: ScriptedChat):
        super().__init__(pea)
        self._chat = chat

    @property
    def system_prompt(self) -> str:
        return (
            "你是喵星球的 AI 经营助手（PEA）。在主人设定的钱包与规则边界内自主经营。"
            "用 JSON 动作协议输出：say / tool / request_human / settle。"
        )

    @property
    def chat(self) -> ScriptedChat:
        return self._chat

    def known_tool(self, name: str) -> bool:
        return name in self._READ or name in self._SIDE_EFFECT

    def tool_is_side_effect(self, name: str) -> bool:
        return name in self._SIDE_EFFECT

    async def dispatch(self, conv: Any, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "read_pet_profile":
            return {"pet": "橘猫·布丁", "vip": True, "last_visit": "2026-05"}
        if name == "create_booking":
            return {"booking_id": "bk_20260629", "service": args.get("service"), "ok": True}
        if name == "purchase_supplies":
            cost = self.estimate_cost(name, args)
            self.pea.wallet.debit(cost)
            return {"purchased": args.get("item"), "cost": cost, "balance": self.pea.wallet.available()}
        return {"ok": True}


def _hr(title: str) -> None:
    print("\n" + "═" * 64)
    print(f"  {title}")
    print("═" * 64)


def _show_turn(label: str, res) -> None:
    print(f"\n👤 用户：{label}")
    for s in res.steps:
        print(f"   🔧 执行工具 {s.get('tool')} → {s.get('result')}")
    for b in res.blocked:
        print(f"   🛡️  guard 拦截 {b.get('name') or b.get('action')}：{b['reason']}")
    flag = "（需人工确认）" if res.requires_human else ""
    print(f"🐱 喵星球PEA：{res.reply} {flag}")
    print(f"   💰 钱包余额：{res.state['wallet']['available']} VIBE")


async def demo_m1() -> None:
    _hr("M1 单体：喵星球 PEA（有钱包 + guard 安全闸门）")
    ledger: dict[str, float] = {"pea_miao": 1000.0}
    pea = PersonalEconomicAgent(
        identity=PeaIdentity(
            agent_id="pea_miao", address="pea_miao",
            principal=Principal(address="0xOwner喵店主", name="喵店主"), reputation=0.6,
        ),
        wallet=LedgerWallet("pea_miao", ledger, daily_limit=2000.0),
        policy=Policy(max_per_tx=200.0, daily_limit=2000.0, blocked_actions=["auto_refund"]),
    )
    print(f"PEA 身份：{pea.identity.agent_id}　主人锚点：{pea.identity.principal.address}")
    print(f"初始钱包：{pea.wallet.available()} VIBE　单笔限额：{pea.policy.max_per_tx}")

    # 场景1：正常预约（读 + 副作用无花费）
    h1 = MiaoxingqiuHarness(pea, ScriptedChat([
        '{"action":"tool","name":"read_pet_profile","args":{}}',
        '{"action":"tool","name":"create_booking","args":{"service":"猫咪星座写真"}}',
        '{"action":"say","text":"布丁是 VIP，已为它预约本周六的星座写真～"}',
    ]))
    _show_turn("帮布丁约个写真", await h1.run_turn("c1", "帮布丁约个写真"))

    # 场景2：超限采购 → guard 拦截 + 人工闸门（钱不动）
    h2 = MiaoxingqiuHarness(pea, ScriptedChat([
        '{"action":"tool","name":"purchase_supplies","args":{"item":"进口猫粮一箱","vibe_cost":500}}',
    ]))
    _show_turn("采购 500 VIBE 的进口猫粮", await h2.run_turn("c2", "采购进口猫粮"))

    # 场景3：限额内采购 → 放行，钱包真实扣款
    h3 = MiaoxingqiuHarness(pea, ScriptedChat([
        '{"action":"tool","name":"purchase_supplies","args":{"item":"猫砂×5","vibe_cost":120}}',
        '{"action":"say","text":"已采购猫砂 5 袋，入库完成。"}',
    ]))
    _show_turn("采购 120 VIBE 的猫砂", await h3.run_turn("c3", "采购猫砂"))

    # 场景4：主人红线动作 → guard 拦截
    h4 = MiaoxingqiuHarness(pea, ScriptedChat([
        '{"action":"tool","name":"auto_refund","args":{"order":"o_99"}}',
    ]))
    _show_turn("给差评客户自动退款", await h4.run_turn("c4", "自动退款"))


async def demo_m2() -> None:
    _hr("M2 交易：两个 PEA 经 A2A 完成「委托→交付→VIBE 结算」")
    # 共享账本：喵星球(买方) 1000，雕刻时光设计(卖方) 0
    ledger: dict[str, float] = {"pea_miao": 1000.0, "pea_diaoke": 0.0}
    backend = InMemoryLedgerBackend(balances=ledger)
    hook = EscrowSettlementHook(backend, payee="pea_diaoke")

    class DesignHandler:
        async def handle(self, ctx) -> dict:
            return {"output": "门店海报已交付（含主视觉+文案）", "quality_gate": "passed",
                    "evidence_uri": "ipfs://Qm.../poster.png"}

    rt = LocalA2ARuntime(
        AgentRuntimeConfig(
            agent_id="pea_diaoke", name="雕刻时光设计 PEA", description="承接平面/海报设计",
            base_url="http://127.0.0.1:9502",
            # 用全新临时目录：避免持久队列的幂等回放让重跑看不到完整流程
            data_dir=tempfile.mkdtemp(prefix="pea_diaoke_"),
            execute_inline_on_submit=True, settlement_enabled=True,
        ),
        DesignHandler(), settlement_hook=hook,
    )
    rt.initialize()

    print(f"委托前　喵星球：{ledger['pea_miao']} VIBE　雕刻时光：{ledger['pea_diaoke']} VIBE")
    task = await rt.submit({
        "message": {"parts": [{"kind": "text", "text": "给喵星球做一张门店海报，150 VIBE"}]},
        "metadata": {"vibe_amount": 150.0, "usmsb": {"caller_id": "pea_miao", "principal_id": "0xOwner喵店主"}},
    })
    print(f"\n📨 A2A 委托结果：state={task['status']['state']}　"
          f"结算={task['metadata']['settlement_status']}　质量门={task['metadata']['quality_gate']}")
    print(f"   交付物：{task['status']['message']['parts'][0]['text']}")
    print(f"委托后　喵星球：{ledger['pea_miao']} VIBE　雕刻时光：{ledger['pea_diaoke']} VIBE")
    print("\n✅ 一次真实经济事件闭环：托管 → 交付 → 质量门通过 → VIBE 结算 → 余额变动。")


async def main() -> None:
    await demo_m1()
    await demo_m2()
    print("\n" + "═" * 64)
    print("  Demo 完成：经济公民(harness+guard+钱包) + 服务市场(A2A) + 链上结算(VIBE) 三支柱跑通。")
    print("═" * 64)


if __name__ == "__main__":
    asyncio.run(main())
