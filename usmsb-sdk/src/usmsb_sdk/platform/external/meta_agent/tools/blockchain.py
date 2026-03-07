"""
Blockchain Tools - 区块链工具
"""

from .registry import Tool


def get_blockchain_tools():
    return [
        Tool(
            "create_wallet",
            "创建钱包",
            create_wallet,
            parameters={
                "chain": {"type": "string", "description": "区块链网络名称，如 ethereum, bsc"}
            },
        ),
        Tool(
            "get_balance",
            "查询余额",
            get_balance,
            parameters={"address": {"type": "string", "description": "钱包地址"}},
        ),
        Tool(
            "stake",
            "质押代币",
            stake,
            parameters={"amount": {"type": "string", "description": "质押数量"}},
        ),
        Tool(
            "unstake",
            "取消质押",
            unstaking,
            parameters={"amount": {"type": "string", "description": "解除质押数量"}},
        ),
        Tool(
            "vote",
            "投票",
            vote,
            parameters={
                "proposal_id": {"type": "string", "description": "提案ID"},
                "support": {"type": "boolean", "description": "是否支持"},
            },
        ),
        Tool(
            "submit_proposal",
            "提交提案",
            submit_proposal,
            parameters={
                "title": {"type": "string", "description": "提案标题"},
                "description": {"type": "string", "description": "提案描述"},
            },
        ),
        Tool(
            "switch_chain",
            "切换链",
            switch_chain,
            parameters={"chain": {"type": "string", "description": "区块链网络名称"}},
        ),
        Tool(
            "get_chain_info",
            "获取链信息",
            get_chain_info,
            parameters={"chain": {"type": "string", "description": "区块链网络名称"}},
        ),
    ]


async def register_tools(registry):
    for tool in get_blockchain_tools():
        registry.register(tool)


async def create_wallet(params):
    return {"address": "0x" + "a" * 40, "chain": params.get("chain", "ethereum")}


async def get_balance(params):
    return {"balance": 100.0, "symbol": "VIBE"}


async def stake(params):
    return {"status": "success", "amount": params.get("amount")}


async def unstaking(params):
    return {"status": "success"}


async def vote(params):
    return {"status": "success", "proposal_id": params.get("proposal_id")}


async def submit_proposal(params):
    return {"status": "success", "proposal_id": "prop_123"}


async def switch_chain(params):
    return {"status": "success", "chain": params.get("chain")}


async def get_chain_info(params):
    return {"chain": params.get("chain", "ethereum"), "block_number": 12345678}
