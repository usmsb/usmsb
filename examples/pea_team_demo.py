"""团队版 v3.0 Demo —— TeamLeaderPea：多 PEA over A2A + 全网能力发现 + Shapley 分账。

跑法：
    cd /Users/gujun/vibecode/usmsb
    python examples/pea_team_demo.py

剧情：品牌方要做"品牌全案"。TeamLeaderPea（协调者 PEA）：
  1. LLM 把目标拆成子任务（VI / 文案 / 短片）。
  2. 从【全网 AgentRegistry】按"能力语义×声誉"发现并组队。
  3. 发起联合订单：一次托管 → 各成员经 A2A 交付 → LLM 评贡献 → Shapley 公平分账。

无中心化老板：成员各有钱包、各自独立、按贡献分钱。
（脚本化 LLM 免 key 跑通；设 MINIMAX_API_KEY 后各 ScriptedChat 换 make_minimax_provider 即真大脑。）
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from usmsb_sdk.core_services.agent_registry import (  # noqa: E402
    AgentProfile, AgentRegistry, AgentStatus,
)
from usmsb_sdk.economic.agent_directory import RegistryDirectoryProvider  # noqa: E402
from usmsb_sdk.economic.joint_order import LLMContributionAssessor  # noqa: E402
from usmsb_sdk.economic.pea import (  # noqa: E402
    LedgerWallet, PeaIdentity, PersonalEconomicAgent, Policy, Principal,
)
from usmsb_sdk.economic.pea_market import (  # noqa: E402
    CapabilityDiscovery, LLMCapabilityMatcher, LLMQualityGate,
    MarketPeaHarness, PeaA2AHandler, PeaMarket,
)
from usmsb_sdk.products.team import LLMTaskDecomposer, TeamLeaderPea  # noqa: E402
from usmsb_sdk.services.matching.llm_capability_fit import LLMCapabilityFit  # noqa: E402


class ScriptedChat:
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    async def complete(self, messages, **kwargs: Any) -> str:
        return self._responses.pop(0) if self._responses else '{"action":"say","text":"完成。"}'


class SeqFit:
    """逐候选返回 fit 分（demo：让对的人匹配上对的活）。"""

    def __init__(self, fits: list[float]):
        self._fits = list(fits)

    async def complete(self, messages, **kwargs: Any) -> str:
        f = self._fits.pop(0) if self._fits else 0.0
        return f'{{"fit":{f}}}'


def _member(market, aid, ledger, reply):
    ledger[aid] = 0.0
    pea = PersonalEconomicAgent(
        PeaIdentity(aid, aid, Principal(f"0x{aid}")),
        LedgerWallet(aid, ledger, daily_limit=100000.0),
        Policy(max_per_tx=100000.0, daily_limit=100000.0),
    )
    return MarketPeaHarness(pea, ScriptedChat([f'{{"action":"say","text":"{reply}"}}']), market)


async def main() -> None:
    print("═" * 72)
    print("  团队版 v3.0：TeamLeaderPea —— 多 PEA + 全网能力发现 + Shapley 分账")
    print("═" * 72)

    ledger: dict[str, float] = {"brand_co": 1000.0}
    tmp = tempfile.mkdtemp(prefix="pea_team_")

    # 全网注册表：3 个专业 agent 在线（团队从这里被发现）
    registry = AgentRegistry()
    for aid, name, desc, caps, rep in [
        ("ag_design", "设计工作室", "品牌视觉与海报设计", ["VI设计", "海报"], 0.7),
        ("ag_copy", "文案铺子", "品牌文案与 slogan", ["文案", "slogan"], 0.8),
        ("ag_video", "短片团队", "品牌短片与拍摄", ["短视频", "拍摄"], 0.6),
    ]:
        registry.register(AgentProfile(id=aid, name=name, description=desc,
                                       capabilities=caps, reputation=rep, status=AgentStatus.ONLINE))

    # 能力发现：3 子任务 × 3 候选 = 9 次打分（对角线高分=对的人匹配对的活）
    fits = [0.9, 0.1, 0.2,   # 子任务1(VI) → design 高
            0.1, 0.9, 0.2,   # 子任务2(文案) → copy 高
            0.2, 0.1, 0.9]   # 子任务3(短片) → video 高
    discovery = CapabilityDiscovery(LLMCapabilityFit(SeqFit(fits)),
                                    reputation_fn=lambda aid: {"ag_design": 0.7, "ag_copy": 0.8, "ag_video": 0.6}[aid])
    directory = RegistryDirectoryProvider(registry, online_only=True)
    market = PeaMarket(ledger=ledger, matcher=LLMCapabilityMatcher(None),
                       discovery=discovery, directory=directory)
    qg = LLMQualityGate(None)

    # 把全网 agent 落成本地可派单的供应 PEA（实战里是远程 A2A 端点）
    for aid, reply in [("ag_design", "VI 系统已交付"), ("ag_copy", "品牌文案已交付"),
                       ("ag_video", "30 秒短片已交付")]:
        h = _member(market, aid, ledger, reply)
        market.make_supplier_runtime(agent_id=aid, handler=PeaA2AHandler(h, quality_gate=qg),
                                     data_dir=f"{tmp}/{aid}", capabilities=aid)

    decomposer = LLMTaskDecomposer(ScriptedChat(['{"subtasks":["做品牌VI","写品牌文案","拍品牌短片"]}']))
    assessor = LLMContributionAssessor(ScriptedChat(['{"ag_design":0.4,"ag_copy":0.3,"ag_video":0.3}']))
    leader = TeamLeaderPea("brand_co", market, decomposer, contribution_assessor=assessor)

    print(f"\n初始：品牌方 {ledger['brand_co']:.0f} VIBE | 全网在线 agent：{[a.id for a in registry.get_online_agents()]}")
    print("\n👔 品牌方：给我做个『品牌全案』，预算 600 VIBE，你组队\n")

    res = await leader.run_project("品牌全案", total_reward=600.0)

    print(f"① LLM 拆解：{res['subtasks']}")
    print("② 全网能力发现组队（语义×声誉）：")
    for member, task in res["assignments"].items():
        print(f"   {member} ← {task}")
    print(f"③ 联合订单状态：{res['status']}")
    print("④ Shapley 公平分账：")
    for aid, pay in res["payouts"].items():
        print(f"   {aid}: {pay:.0f} VIBE")
    print(f"\n结算后：品牌方 {ledger['brand_co']:.0f} | 设计 {ledger['ag_design']:.0f} | "
          f"文案 {ledger['ag_copy']:.0f} | 短片 {ledger['ag_video']:.0f} | 托管 {ledger.get('__vibe_escrow__',0):.0f}")

    print("\n" + "═" * 72)
    print("  团队 = 协调者 PEA 用 VIBE 买一组独立 PEA 的服务（市场关系，非雇佣）。")
    print("  拆解=LLM，组队=全网语义发现，分账=Shapley；无中心化老板。")
    print("═" * 72)


if __name__ == "__main__":
    asyncio.run(main())
