# -*- coding: utf-8 -*-
"""
USMSB FastAPI Server

完整的 USMSB HTTP API 服务器，整合所有模块：

Features:
- L3Orchestrator HTTP 接口
- Google A2A 协议端点
- 健康检查
- VIBE Token 经济接口

Usage:
    uvicorn usmsb_sdk.api.rest.server:app --host 0.0.0.0 --port 8000

Endpoints:
- GET  /health                     # 健康检查
- GET  /well-known/agent.json      # A2A AgentCard
- GET  /l3/agent/{id}/status       # Agent 状态
- GET  /l3/agent/{id}/goals        # 目标列表
- POST /l3/agent/{id}/goals        # 生成目标
- POST /l3/agent/{id}/tasks        # 提交任务
- GET  /l3/agent/{id}/tasks/{tid}  # 任务状态
- GET  /l3/agent/{id}/capabilities # 能力画像
- GET  /l3/agent/{id}/fitness     # 适应度
- GET  /l3/agent/{id}/evolution    # 进化状态
- POST /l3/agent/{id}/evolve       # 触发进化
- GET  /l3/agent/{id}/loops       # Loop 状态
- POST /l3/agent/{id}/run-cycle   # 运行周期
- POST /a2a                       # A2A JSON-RPC
"""

import os
import sys
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from usmsb_sdk.l3_orchestrator import L3Orchestrator
from usmsb_sdk.api.rest.l3_agent import router as l3_router, register_l3_orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan - startup and shutdown"""
    # Startup
    logger.info("Starting USMSB Server...")
    
    # Create default L3Orchestrator
    agent_id = os.environ.get("USMSB_AGENT_ID", "default")
    
    try:
        orch = L3Orchestrator(agent_id=agent_id)
        register_l3_orchestrator(agent_id, orch)
        logger.info(f"Created L3Orchestrator: {agent_id}")
    except Exception as e:
        logger.warning(f"Could not create L3Orchestrator: {e}")
        logger.warning("Run with limited functionality")
    
    logger.info("USMSB Server started!")
    
    yield
    
    # Shutdown
    logger.info("USMSB Server shutting down...")


# Create FastAPI app
app = FastAPI(
    title="USMSB API",
    description="Unified Silicon-based Multi-System (USMSB) - Silicon Life Agent Platform",
    version="2.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(l3_router, prefix="/l3")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "USMSB",
        "version": "2.0.0",
        "description": "Silicon-based Life Agent Platform",
        "endpoints": {
            "health": "/health",
            "agent_card": "/well-known/agent.json",
            "l3_agent": "/l3/agent/{id}/status",
            "a2a_rpc": "/a2a",
        }
    }


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": __import__("datetime").datetime.now().timestamp(),
    }


def main():
    """Run the server"""
    import uvicorn
    
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")
    
    uvicorn.run(
        "usmsb_sdk.api.rest.server:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
