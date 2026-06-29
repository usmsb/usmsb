"""远程 A2A Demo —— 跨进程派单：协调者经真实 HTTP 把活派给远程供应 PEA。

跑法：
    cd /Users/gujun/vibecode/usmsb
    python examples/pea_remote_a2a_demo.py

设计PEA 作为独立 A2A 服务跑在 127.0.0.1:9610（真实 socket）；喵星球（协调者）
通过 A2AClient 按 URL 远程派单"做海报 150 VIBE"——真实 HTTP/JSON-RPC 过网络边界，
远程 runtime 托管→交付→结算。账本同进程共享（真实跨机器时结算轨是链）。
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import uvicorn  # noqa: E402

from usmsb_sdk.economic.pea_market import LLMCapabilityMatcher, PeaMarket  # noqa: E402
from usmsb_sdk.economic.vibe_settlement import (  # noqa: E402
    VibeSettlementBackend, make_ledger_transfer_fn,
)
from usmsb_sdk.protocol.a2a_runtime import (  # noqa: E402
    A2AClient, AgentRuntimeConfig, EchoAgentHandler, EscrowSettlementHook, LocalA2ARuntime,
)
from usmsb_sdk.protocol.a2a_runtime.server import create_a2a_app  # noqa: E402

PORT = 9610
LEDGER = {"pea_miao": 1000.0, "__vibe_escrow__": 0.0, "pea_design": 0.0}


def _build_remote_runtime() -> LocalA2ARuntime:
    backend = VibeSettlementBackend(make_ledger_transfer_fn(LEDGER))
    hook = EscrowSettlementHook(backend, payee="pea_design")
    cfg = AgentRuntimeConfig(
        agent_id="pea_design", name="雕刻时光设计 PEA", description="承接海报/视觉设计",
        base_url=f"http://127.0.0.1:{PORT}", data_dir=tempfile.mkdtemp(prefix="remote_design_"),
        execute_inline_on_submit=True, settlement_enabled=True,
    )
    return LocalA2ARuntime(cfg, EchoAgentHandler(), settlement_hook=hook)


def _serve(server: uvicorn.Server) -> None:
    server.run()


async def main() -> None:
    print("═" * 70)
    print("  远程 A2A：喵星球 → 经真实 HTTP 把活派给远程设计PEA（跨进程）")
    print("═" * 70)

    # 1) 设计PEA 作为独立 A2A 服务跑在真实端口
    app = create_a2a_app(_build_remote_runtime())
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="error"))
    threading.Thread(target=_serve, args=(server,), daemon=True).start()

    base = f"http://127.0.0.1:{PORT}"
    client = A2AClient(base)

    # 等服务起来
    for _ in range(50):
        try:
            if (await client.health()).get("status") == "ok":
                break
        except Exception:
            await asyncio.sleep(0.1)
    card = await client.get_agent_card()
    print(f"\n🌐 发现远程 PEA：{card['name']} @ {base}")
    print(f"   能力：{card['description']}｜支持 VIBE 结算：{card['capabilities']['vibeSettlement']}")

    # 2) 喵星球（协调者）把远程 PEA 登记为供应商，按 URL 派单
    market = PeaMarket(ledger=LEDGER, matcher=LLMCapabilityMatcher(None))
    market.register_remote_supplier(
        agent_id="pea_design", url=base, capabilities="海报/视觉设计", client=client,
    )

    print(f"\n委托前　喵星球 {LEDGER['pea_miao']:.0f} | 设计PEA {LEDGER['pea_design']:.0f} VIBE")
    print("📨 喵星球经 HTTP/JSON-RPC 远程派单：做促销海报，150 VIBE\n")
    res = await market.delegate(from_id="pea_miao", task="设计双十一促销海报", vibe_amount=150.0)

    print(f"   远程任务状态：{res['state']}｜结算：{res['settlement']}｜质量门：{res['quality_gate']}")
    print(f"委托后　喵星球 {LEDGER['pea_miao']:.0f} | 设计PEA {LEDGER['pea_design']:.0f} | "
          f"托管 {LEDGER['__vibe_escrow__']:.0f} VIBE")

    print("\n" + "═" * 70)
    print("  真实 HTTP 过网络边界 → 远程 runtime 托管/交付/结算。")
    print("  把 URL 换成另一台机器，即是真正跨机器的 AI 经济协作（结算轨=链）。")
    print("═" * 70)

    server.should_exit = True


if __name__ == "__main__":
    asyncio.run(main())
