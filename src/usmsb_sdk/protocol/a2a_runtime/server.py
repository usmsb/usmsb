"""把一个 LocalA2ARuntime 暴露为 HTTP A2A 端点（跨进程/跨机器派单）。

标准 A2A 端点：
    GET  /.well-known/agent.json  → Agent Card
    POST /a2a                      → JSON-RPC（message/send, tasks/get）
    GET  /health                   → 健康检查

实战部署：每个供应 PEA 跑一个本进程 runtime（含持久队列/结算），用本 app + uvicorn
对外暴露；其它 PEA 通过 A2AClient 按 URL 远程派单。任务执行依赖 runtime 的
inline 执行或后台 worker（部署时先 await runtime.start()）。
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .runtime import A2AJsonRpcError, LocalA2ARuntime


def create_a2a_app(runtime: LocalA2ARuntime) -> FastAPI:
    app = FastAPI(title=f"A2A:{runtime.config.agent_id}", docs_url=None, redoc_url=None)
    runtime.initialize()

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "agent_id": runtime.config.agent_id}

    @app.get("/.well-known/agent.json")
    async def agent_card() -> dict[str, Any]:
        return runtime.build_agent_card()

    @app.post("/a2a")
    async def a2a(request: Request) -> Any:
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return JSONResponse(
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}},
                status_code=400,
            )
        rpc_id = body.get("id") if isinstance(body, dict) else None
        try:
            result = await runtime.handle_jsonrpc(body)
            return {"jsonrpc": "2.0", "id": rpc_id, "result": result}
        except A2AJsonRpcError as e:
            return JSONResponse(
                {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": e.code, "message": e.message}},
                status_code=200,
            )

    return app
