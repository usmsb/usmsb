"""联合订单 + Shapley 分账 Demo —— 多 PEA 组队接大单，按贡献公平分账。

跑法：
    cd /Users/gujun/vibecode/usmsb
    python examples/pea_joint_order_demo.py

剧情：一个"品牌全案"大单，单个 PEA 吃不下 → 3 个 PEA（设计/文案/视频）组队，
各交付一部分 → LLM 评各自贡献 → Shapley 值公平分配总报酬 → 从托管按份额结算。

原则：评贡献=LLM（智能）；Shapley 分账=数学（公平机制，代码）。
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from usmsb_sdk.economic.joint_order import LLMContributionAssessor  # noqa: E402
from usmsb_sdk.economic.pea import (  # noqa: E402
    LedgerWallet, PeaIdentity, PersonalEconomicAgent, Policy, Principal,
)
from usmsb_sdk.economic.pea_market import (  # noqa: E402
    LLMCapabilityMatcher, LLMQualityGate, MarketPeaHarness, PeaA2AHandler, PeaMarket,
)


class ScriptedChat:
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    async def complete(self, messages, **kwargs: Any) -> str:
        return self._responses.pop(0) if self._responses else '{"action":"say","text":"完成。"}'


def _member(market, agent_id, ledger, reply):
    ledger[agent_id] = 0.0
    pea = PersonalEconomicAgent(
        PeaIdentity(agent_id, agent_id, Principal(f"0x{agent_id}")),
        LedgerWallet(agent_id, ledger, daily_limit=100000.0),
        Policy(max_per_tx=100000.0, daily_limit=100000.0),
    )
    return MarketPeaHarness(pea, ScriptedChat([f'{{"action":"say","text":"{reply}"}}']), market)


async def main() -> None:
    print("═" * 70)
    print("  联合订单 + Shapley 分账 —— 3 个 PEA 组队接『品牌全案』大单")
    print("═" * 70)

    ledger: dict[str, float] = {"brand_co": 1000.0}
    tmp = tempfile.mkdtemp(prefix="pea_joint_")
    market = PeaMarket(ledger=ledger, matcher=LLMCapabilityMatcher(None))
    qg = LLMQualityGate(None)

    team = {
        "pea_design": ("做主视觉 VI", "主视觉/VI 系统已交付"),
        "pea_copy": ("写品牌文案", "品牌 slogan + 文案已交付"),
        "pea_video": ("做品牌短片", "30 秒品牌短片已交付"),
    }
    for aid, (_, reply) in team.items():
        h = _member(market, aid, ledger, reply)
        market.make_supplier_runtime(agent_id=aid, handler=PeaA2AHandler(h, quality_gate=qg),
                                     data_dir=f"{tmp}/{aid}", capabilities=aid)

    # LLM 评贡献：设计 0.5 / 文案 0.2 / 视频 0.3（视频工作量大于文案）
    assessor = LLMContributionAssessor(ScriptedChat([
        '{"pea_design":0.5,"pea_copy":0.2,"pea_video":0.3}'
    ]))

    print(f"\n初始：品牌方 {ledger['brand_co']:.0f} VIBE | 三位成员各 0")
    print("📦 品牌方发起 600 VIBE 的品牌全案联合订单，3 个 PEA 组队接单\n")

    res = await market.joint_order(
        from_id="brand_co", task="品牌全案（VI+文案+短片）",
        assignments={aid: t for aid, (t, _) in team.items()},
        total_reward=600.0, contribution_assessor=assessor,
        synergy_bonus=0.0,
    )

    print(f"状态：{res['status']}")
    print(f"LLM 评定贡献基值：{ {k: round(v,2) for k,v in res['contribution_base'].items()} }")
    print(f"Shapley 公平分账：")
    for aid, pay in res["payouts"].items():
        print(f"   {aid}: {pay:.1f} VIBE")
    print(f"\n结算后：品牌方 {ledger['brand_co']:.0f} | "
          f"设计 {ledger['pea_design']:.0f} | 文案 {ledger['pea_copy']:.0f} | "
          f"视频 {ledger['pea_video']:.0f} | 托管 {ledger.get('__vibe_escrow__',0):.0f}")

    print("\n" + "═" * 70)
    print("  多 PEA 组队接单 → LLM 评贡献 → Shapley 公平分账 → 托管按份额结算。")
    print("  单个 PEA 吃不下的大单，靠组队完成；分账公平，无需中心化老板。")
    print("═" * 70)


if __name__ == "__main__":
    asyncio.run(main())
