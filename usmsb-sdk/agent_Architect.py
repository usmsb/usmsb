#!/usr/bin/env python
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "healthy", "agent_name": "Architect", "port": 8082}

@app.post("/invoke")
def invoke(request: dict):
    method = request.get("method", "chat")
    params = request.get("params", {})
    return JSONResponse({
        "success": True,
        "result": {
            "status": "ok",
            "response": f"[Architect Agent] 收到消息: {params.get('message', '')}",
            "timestamp": "2026-01-01T00:00:00Z"
        },
        "agent_id": "architect-agent",
        "agent_name": "Architect",
        "method": method
    })

@app.post("/heartbeat")
def heartbeat():
    return {"success": True, "status": "online"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8082, log_level="warning")
