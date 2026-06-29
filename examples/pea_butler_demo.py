"""超级个体大管家 ButlerPea Demo —— 验证 #1+#2+#1b 闭环。

跑法：
    cd /Users/gujun/vibecode/usmsb
    python examples/pea_butler_demo.py

- 有 MINIMAX_API_KEY 时用真实 LLM（make_minimax_provider）；否则用脚本化 LLM 跑通流程。
- 演示：PeaRegistry 创建管家 PEA → 注册 ButlerPea harness → 跑几轮
        （晨报 prompt skill / 加待办 / 派活花钱过 guard 限额）。

这条 demo 把第一轮发现的两个最大窟窿（PEA 设计稿 + 产品层孤儿）合并落地：
用 harness + 真 LLM 把"超级个体管家"真正跑起来，且可被注册/调用。
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from usmsb_sdk.economic.pea_registry import PeaRegistry  # noqa: E402
from usmsb_sdk.harness.providers import make_minimax_provider  # noqa: E402
from usmsb_sdk.products.super_individual.butler_pea import ButlerPea, ButlerProfile  # noqa: E402


class ScriptedChat:
    """无 API Key 时的脚本化 LLM，让 demo 永远能跑通。"""

    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    async def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        return self._responses.pop(0) if self._responses else '{"action":"say","text":"完成。"}'


def _show(label: str, res) -> None:
    print(f"\n👤 主人：{label}")
    for s in res.steps:
        if "tool" in s:
            print(f"   🔧 {s['tool']} → {str(s['result'])[:80]}")
    for b in res.blocked:
        print(f"   🛡️  guard 拦截 {b.get('name') or b.get('action')}：{b['reason']}")
    flag = "（需主人确认）" if res.requires_human else ""
    print(f"🤵 管家PEA：{res.reply} {flag}")
    print(f"   💰 运营资金：{res.state['wallet']['available']} VIBE")


async def main() -> None:
    print("═" * 64)
    print("  超级个体大管家 ButlerPea（PeaRegistry + harness + guard）")
    print("═" * 64)

    use_real = bool(os.environ.get("MINIMAX_API_KEY"))
    print(f"LLM 模式：{'真实 MiniMax' if use_real else '脚本化（未设 MINIMAX_API_KEY）'}")

    reg = PeaRegistry()
    pea = reg.create(
        agent_id="butler_laogu", principal_address="0xOwner老顾", principal_name="老顾",
        balance=1000.0, max_per_tx=200.0,
    )
    profile = ButlerProfile(user_name="老顾", goals=["把 USMSB 做成闭环", "跑通 PEA 经济"])

    if use_real:
        chat = await make_minimax_provider()
    else:
        chat = ScriptedChat([
            # 第1轮：生成晨报（generate_briefing 内部再调一次 LLM 出正文）
            '{"action":"tool","name":"generate_briefing","args":{"kind":"morning"}}',
            "今日要点：1) 推进 v3.0 闭环 2) 跑通管家 PEA 3) 复盘 A2A 结算",
            '{"action":"say","text":"晨报已发您，重点是推进闭环。"}',
            # 第2轮：加待办
            '{"action":"tool","name":"add_task","args":{"title":"写本周复盘"}}',
            '{"action":"say","text":"已加到待办清单。"}',
            # 第3轮：派活超预算 → guard 拦截
            '{"action":"tool","name":"delegate_to_specialist","args":{"task":"拍宣传片","vibe_cost":800}}',
        ])

    reg.register_harness("butler_laogu", ButlerPea(pea, chat, profile))
    print(f"已注册 PEA：{reg.list_ids()}　主人锚点：{pea.identity.principal.address}")

    if not use_real:
        _show("给我来个今日晨报", await reg.run_turn("butler_laogu", "c1", "今日晨报"))
        _show("加个'写本周复盘'的待办", await reg.run_turn("butler_laogu", "c2", "加待办：写本周复盘"))
        _show("外包一条 800 VIBE 的宣传片", await reg.run_turn("butler_laogu", "c3", "外包宣传片"))
    else:
        _show("帮我规划今天，并把要花钱的事先报我", await reg.run_turn("butler_laogu", "c1", "规划今天"))

    print("\n" + "═" * 64)
    print("  闭环：PEA 可被创建/注册/调用 + 真LLM大脑 + guard 守护超限副作用。")
    print("  （设 MINIMAX_API_KEY 即切换为真实大脑）")
    print("═" * 64)


if __name__ == "__main__":
    asyncio.run(main())
