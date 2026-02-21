"""
Governance Tools
"""

from .registry import Tool


def get_governance_tools():
    return [
        Tool("get_user_info", "获取用户信息", get_user_info),
        Tool("list_user_agents", "列出用户Agent", list_user_agents),
        Tool("delegate_vote", "委托投票", delegate_vote),
        Tool("get_vote_power", "获取投票权", get_vote_power),
        Tool("list_proposals", "列出提案", list_proposals),
    ]


async def register_tools(registry):
    for tool in get_governance_tools():
        registry.register(tool)


async def get_user_info(params):
    return {"wallet": params.get("wallet_address"), "role": "HUMAN", "vote_power": 100}


async def list_user_agents(params):
    return {"agents": []}


async def delegate_vote(params):
    return {"status": "success"}


async def get_vote_power(params):
    return {"vote_power": 100, "delegated": 0}


async def list_proposals(params):
    return {"proposals": [], "count": 0}
