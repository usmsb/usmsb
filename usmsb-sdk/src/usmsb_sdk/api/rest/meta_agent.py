"""
Meta Agent Router
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meta-agent", tags=["Meta Agent"])

# Global Meta Agent instance
_meta_agent = None
_permission_manager = None


def set_meta_agent(agent):
    """Set the global Meta Agent instance."""
    global _meta_agent
    _meta_agent = agent


def set_permission_manager(manager):
    """Set the global permission manager instance."""
    global _permission_manager
    _permission_manager = manager


class ChatRequest(BaseModel):
    message: str
    wallet_address: Optional[str] = None
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    response: str
    success: bool = True
    tool_used: Optional[str] = None
    details: Optional[dict] = None


class ToolInfo(BaseModel):
    name: str
    description: str


class HistoryMessage(BaseModel):
    id: str
    role: str
    content: str
    timestamp: Optional[float] = None
    tool_calls: Optional[List[Dict]] = None


class EvolutionStats(BaseModel):
    total_evolutions: int = 0
    by_type: dict = {}
    by_status: dict = {}
    capabilities: dict = {}


class UserInfo(BaseModel):
    wallet_address: str
    role: str
    permissions: List[str] = []
    stake_amount: float = 0.0
    token_balance: float = 0.0
    voting_power: float = 0.0


class UpdateRoleRequest(BaseModel):
    wallet_address: str
    new_role: str
    reason: Optional[str] = None


class UpdateStakeRequest(BaseModel):
    wallet_address: str
    stake_amount: float


class PermissionStats(BaseModel):
    total_users: int = 0
    users_by_role: dict = {}
    total_voting_power: float = 0.0
    total_stake: float = 0.0


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with Meta Agent."""
    import logging
    import asyncio

    logger = logging.getLogger(__name__)
    logger.info(
        f"DEBUG chat request: message={request.message[:50]}..., wallet={request.wallet_address}"
    )
    if _meta_agent is None:
        logger.error("DEBUG _meta_agent is None!")
        return ChatResponse(
            response="Meta Agent is initializing. Please try again later.",
            success=False,
        )

    try:
        logger.info(f"DEBUG calling _meta_agent.chat, agent={type(_meta_agent)}")
        # 设置 3 分钟超时
        result = await asyncio.wait_for(
            _meta_agent.chat(
                message=request.message,
                wallet_address=request.wallet_address,
            ),
            timeout=180.0,
        )
        logger.info(f"DEBUG chat result: {result[:100] if result else 'EMPTY'}")
        return ChatResponse(
            response=result,
            success=True,
        )
    except asyncio.TimeoutError:
        logger.error("Chat timeout after 180 seconds")
        return ChatResponse(
            response="请求超时（3分钟），请稍后再试或尝试简化问题。",
            success=False,
        )
    except Exception as e:
        import traceback

        logger.error(f"Chat error: {e}")
        logger.error(traceback.format_exc())
        return ChatResponse(
            response=f"Error: {str(e)}",
            success=False,
        )


@router.get("/tools")
async def get_tools():
    """Get available tools from Meta Agent."""
    if _meta_agent is None:
        return []

    try:
        tools = _meta_agent.get_available_tools()
        return tools
    except Exception as e:
        logger.error(f"Get tools error: {e}")
        return []


@router.get("/debug/tools-for-wallet/{wallet_address}")
async def debug_tools_for_wallet(wallet_address: str):
    """Debug endpoint to check available tools for a wallet."""
    if _permission_manager is None:
        return {"error": "Permission manager not initialized"}

    if _meta_agent is None:
        return {"error": "Meta agent not initialized"}

    try:
        # Get user
        user = await _permission_manager.get_user(wallet_address)
        if not user:
            return {"error": "User not found"}

        # Get all tools
        all_tools = _meta_agent.tool_registry.list_tools()

        # Filter tools by permission
        from usmsb_sdk.platform.external.meta_agent.permission.models import (
            get_tool_required_permissions,
        )

        allowed_tools = []
        for tool in all_tools:
            tool_name = tool["name"]
            required_perms = get_tool_required_permissions(tool_name)
            has_all_perms = all(user.has_permission(perm) for perm in required_perms)
            if has_all_perms:
                allowed_tools.append(tool_name)

        return {
            "wallet_address": wallet_address,
            "role": user.role.value,
            "permissions": [p.value for p in user.permissions],
            "total_tools": len(all_tools),
            "allowed_tools": allowed_tools,
            "allowed_count": len(allowed_tools),
        }
    except Exception as e:
        logger.error(f"Debug tools error: {e}")
        return {"error": str(e)}


@router.get("/history/{wallet_address}", response_model=List[HistoryMessage])
async def get_history(wallet_address: str, limit: int = 50):
    """Get conversation history for a wallet address."""
    if _meta_agent is None:
        return []

    try:
        history = await _meta_agent.get_conversation_history(
            wallet_address=wallet_address,
            limit=limit,
        )
        return [HistoryMessage(**msg) for msg in history]
    except Exception as e:
        logger.error(f"Get history error: {e}")
        return []


@router.get("/debug-logs/{wallet_address}")
async def get_debug_logs(wallet_address: str, after_timestamp: float = 0):
    """Get debug logs for a wallet address (for real-time monitoring)."""
    if _meta_agent is None:
        return []

    try:
        logs = _meta_agent.get_debug_logs(wallet_address, after_timestamp)
        return logs
    except Exception as e:
        logger.error(f"Get debug logs error: {e}")
        return []


@router.get("/history/{wallet_address}/latest")
async def get_latest_messages(wallet_address: str, after_timestamp: float = 0):
    """Get messages after a timestamp (for polling)."""
    if _meta_agent is None:
        return []

    try:
        history = await _meta_agent.get_conversation_history(
            wallet_address=wallet_address,
            limit=100,  # 获取最近的100条
        )
        # 过滤出 after_timestamp 之后的消息
        latest = [msg for msg in history if msg.get("timestamp", 0) > after_timestamp]
        return [HistoryMessage(**msg) for msg in latest]
    except Exception as e:
        logger.error(f"Get latest messages error: {e}")
        return []


@router.get("/evolution-stats", response_model=EvolutionStats)
async def get_evolution_stats():
    """Get evolution statistics."""
    if _meta_agent is None:
        return EvolutionStats()

    try:
        stats = _meta_agent.get_evolution_stats()
        return EvolutionStats(**stats)
    except Exception as e:
        logger.error(f"Get evolution stats error: {e}")
        return EvolutionStats()


# ============ Permission APIs ============


@router.get("/user/{wallet_address}", response_model=UserInfo)
async def get_user_info(wallet_address: str):
    """Get user permission info."""
    if _permission_manager is None:
        return UserInfo(wallet_address=wallet_address, role="human")

    try:
        user = await _permission_manager.get_user(wallet_address)
        if user:
            return UserInfo(
                wallet_address=user.wallet_address,
                role=user.role.value,
                permissions=[p.value for p in user.permissions],
                stake_amount=user.stake_amount,
                token_balance=user.token_balance,
                voting_power=user.voting_power,
            )
        return UserInfo(wallet_address=wallet_address, role="human")
    except Exception as e:
        logger.error(f"Get user info error: {e}")
        return UserInfo(wallet_address=wallet_address, role="human")


@router.post("/user/role", response_model=UserInfo)
async def update_user_role(request: UpdateRoleRequest):
    """Update user role. Requires superadmin or developer role."""
    if _permission_manager is None:
        raise HTTPException(status_code=500, detail="Permission manager not initialized")

    try:
        from usmsb_sdk.platform.external.meta_agent.permission.models import UserRole

        new_role = UserRole(request.new_role)

        # 先清除缓存，确保获取最新权限
        _permission_manager.invalidate_cache(request.wallet_address)

        user = await _permission_manager.update_role(
            wallet_address=request.wallet_address,
            new_role=new_role,
            reason=request.reason,
        )
        if user:
            # 再次清除缓存，确保Meta Agent获取最新权限
            _permission_manager.invalidate_cache(request.wallet_address)

            return UserInfo(
                wallet_address=user.wallet_address,
                role=user.role.value,
                permissions=[p.value for p in user.permissions],
                stake_amount=user.stake_amount,
                token_balance=user.token_balance,
                voting_power=user.voting_power,
            )
        raise HTTPException(status_code=404, detail="User not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid role: {e}")
    except Exception as e:
        logger.error(f"Update role error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/stake", response_model=UserInfo)
async def update_user_stake(request: UpdateStakeRequest):
    """Update user stake amount."""
    if _permission_manager is None:
        raise HTTPException(status_code=500, detail="Permission manager not initialized")

    try:
        user = await _permission_manager.update_stake(
            wallet_address=request.wallet_address,
            stake_amount=request.stake_amount,
        )
        if user:
            return UserInfo(
                wallet_address=user.wallet_address,
                role=user.role.value,
                permissions=[p.value for p in user.permissions],
                stake_amount=user.stake_amount,
                token_balance=user.token_balance,
                voting_power=user.voting_power,
            )
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Update stake error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/permission/stats", response_model=PermissionStats)
async def get_permission_stats():
    """Get permission statistics."""
    if _permission_manager is None:
        return PermissionStats()

    try:
        return PermissionStats(**_permission_manager.get_stats())
    except Exception as e:
        logger.error(f"Get permission stats error: {e}")
        return PermissionStats()


@router.get("/permission/check-tool/{wallet_address}/{tool_name}")
async def check_tool_permission(wallet_address: str, tool_name: str):
    """Check if user can access a specific tool."""
    if _permission_manager is None:
        return {"allowed": True, "reason": "Permission manager not initialized"}

    try:
        return await _permission_manager.check_tool_access(wallet_address, tool_name)
    except Exception as e:
        logger.error(f"Check tool permission error: {e}")
        return {"allowed": False, "reason": str(e)}
