"""M3 多 PEA over A2A 市场 Demo —— 递归外包 + 链上结算 + 声誉。

跑法：
    cd /Users/gujun/vibecode/usmsb
    python examples/pea_market_m3_demo.py

剧情：喵星球(宠物店)要做双十一促销 → 把"海报"外包给设计PEA →
      设计PEA 自己不会写文案 → 递归把"文案"转包给文案PEA。
全链路：LLM 选供应商 + 托管 + LLM 质量门 + VIBE 结算 + 声誉更新（在共享账本上）。

LLM-first：选供应商(LLMCapabilityMatcher)、判质量(LLMQualityGate)、决定外包什么(harness 主循环)
都走 LLM；此处用脚本化 LLM 免 key 跑通，设 MINIMAX_API_KEY 后把各 ScriptedChat 换成
make_minimax_provider() 即变真实大脑。预算/限额/幂等/托管是代码护栏。
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from usmsb_sdk.economic.pea import (  # noqa: E402
    LedgerWallet, PeaIdentity, PersonalEconomicAgent, Policy, Principal,
)
from usmsb_sdk.economic.pea_market import (  # noqa: E402
    LLMCapabilityMatcher, LLMQualityGate, MarketPeaHarness, PeaA2AHandler, PeaMarket,
)
from usmsb_sdk.services.reputation_service import ReputationService  # noqa: E402
from usmsb_sdk.trust import TrustBridge  # noqa: E402


class ScriptedChat:
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    async def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        return self._responses.pop(0) if self._responses else '{"action":"say","text":"完成。"}'


def _pea(agent_id, ledger, balance, max_per_tx=500.0):
    ledger[agent_id] = balance
    return PersonalEconomicAgent(
        PeaIdentity(agent_id, agent_id, Principal(f"0x{agent_id}"), reputation=0.5),
        LedgerWallet(agent_id, ledger, daily_limit=5000.0),
        Policy(max_per_tx=max_per_tx, daily_limit=5000.0, blocked_actions=[]),
    )


def _bal(ledger):
    return (f"喵星球 {ledger.get('pea_miao',0):.0f} | 设计PEA {ledger.get('pea_design',0):.0f} | "
            f"文案PEA {ledger.get('pea_copy',0):.0f} | 托管 {ledger.get('__vibe_escrow__',0):.0f}")


async def main() -> None:
    print("═" * 70)
    print("  M3：多 PEA over A2A —— 喵星球 → 设计PEA → 文案PEA（递归外包）")
    print("═" * 70)

    ledger: dict[str, float] = {}
    tmp = tempfile.mkdtemp(prefix="pea_market_")

    # 撮合器（LLM 选供应商）：海报→设计，文案→文案
    matcher = LLMCapabilityMatcher(ScriptedChat([
        '{"agent_id":"pea_design","reason":"懂视觉设计"}',
        '{"agent_id":"pea_copy","reason":"擅长促销文案"}',
    ]))
    market = PeaMarket(ledger=ledger, matcher=matcher)

    rep = ReputationService()
    rep.initialize_agent("pea_design")
    rep.initialize_agent("pea_copy")
    trust = TrustBridge(rep)
    qg = LLMQualityGate(None)  # demo 用 fallback；真实环境传 LLM chat 即语义评审

    # 文案 PEA（叶子）
    copy_harness = MarketPeaHarness(
        _pea("pea_copy", ledger, 0.0), market=market,
        chat=ScriptedChat([
            '{"action":"tool","name":"write_copy","args":{}}',
            '{"action":"say","text":"文案已交付。"}',
        ]),
        tools={"write_copy": (False, lambda a: _ok({"content": "标题：双十一，给毛孩子拍套写真，5 折起"}))},
    )
    market.make_supplier_runtime(
        agent_id="pea_copy", handler=PeaA2AHandler(copy_harness, quality_gate=qg),
        data_dir=f"{tmp}/copy", capabilities="促销文案/标题写作", reputation=0.7, trust_hook=trust,
    )

    # 设计 PEA（供应商 + 二级需求方，有 100 周转金垫付分包）
    design_harness = MarketPeaHarness(
        _pea("pea_design", ledger, 100.0), market=market,
        chat=ScriptedChat([
            '{"action":"tool","name":"delegate_via_a2a","args":{"task":"写双十一促销文案","vibe_cost":30}}',
            '{"action":"tool","name":"make_poster","args":{}}',
            '{"action":"say","text":"海报已交付（主视觉+文案）。"}',
        ]),
        tools={"make_poster": (False, lambda a: _ok({"content": "海报：双十一宠物写真 5 折主视觉"}))},
    )
    market.make_supplier_runtime(
        agent_id="pea_design", handler=PeaA2AHandler(design_harness, quality_gate=qg),
        data_dir=f"{tmp}/design", capabilities="平面/海报/视觉设计", reputation=0.6, trust_hook=trust,
    )

    # 喵星球（顶层需求方）
    miao = MarketPeaHarness(
        _pea("pea_miao", ledger, 1000.0), market=market,
        chat=ScriptedChat([
            '{"action":"tool","name":"delegate_via_a2a","args":{"task":"设计双十一宠物写真促销海报","vibe_cost":150}}',
            '{"action":"say","text":"促销物料已就位，开干！"}',
        ]),
    )

    print(f"\n初始账本：{_bal(ledger)}")
    print("\n👤 喵店主：搞个双十一促销，物料你安排\n")
    res = await miao.run_turn("c1", "搞个双十一促销，物料你安排")

    for s in res.steps:
        if s.get("tool") == "delegate_via_a2a":
            r = s["result"]
            print(f"   🔗 喵星球外包 → {r['delegated_to']}（语义匹配）｜结算={r['settlement']}｜质量门={r['quality_gate']}")
            print(f"      ↳ 设计PEA 内部又递归把『文案』转包给 文案PEA（供应方转身变需求方）")
    print(f"🐱 喵星球PEA：{res.reply}")

    print(f"\n结算后账本：{_bal(ledger)}")
    print("   解读：喵星球 -150（付海报）｜文案PEA +30（接文案）｜"
          "设计PEA 100-30+150=+120（赚差价）｜托管清零")
    print(f"\n声誉（交付通过→上升）：设计PEA reliability="
          f"{rep.get_score('pea_design').dimensions['reliability']:.3f}　"
          f"文案PEA={rep.get_score('pea_copy').dimensions['reliability']:.3f}")

    print("\n" + "═" * 70)
    print("  一个 AI 劳动力市场闭环：需求发现→LLM撮合→托管→递归交付→质量门→结算→声誉")
    print("  这就是虚拟经济自底向上的样子：每个 PEA 既消费又供给，委托可递归。")
    print("═" * 70)


def _ok(d: dict) -> Any:
    async def _coro():
        return d
    return _coro()


if __name__ == "__main__":
    asyncio.run(main())
