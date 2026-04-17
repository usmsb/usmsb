"""
Blockchain Tools - 区块链工具（真实 VIBE Token 实现）

基于 Base Sepolia 测试网，集成 VIBE Token（ERC-20）。
"""

import os
from typing import Any

from usmsb_sdk.blockchain.vibe_token import get_vibe_token, VIBEToken
from usmsb_sdk.meta_agent.tools.registry import Tool


def _get_vibe() -> VIBEToken:
    """获取 VIBE Token 实例（延迟初始化）。"""
    private_key = os.environ.get("USMSB_WALLET_PRIVATE_KEY")
    return get_vibe_token(private_key=private_key)


def get_blockchain_tools() -> list[Tool]:
    """返回所有区块链工具定义。"""
    return [
        Tool(
            "create_wallet",
            "创建新钱包（VIBE/Base Sepolia）",
            _create_wallet,
            parameters={
                "chain": {
                    "type": "string",
                    "description": "区块链网络，仅支持 base_sepolia",
                    "default": "base_sepolia",
                }
            },
        ),
        Tool(
            "get_balance",
            "查询 VIBE 余额",
            _get_balance,
            parameters={
                "address": {
                    "type": "string",
                    "description": "钱包地址（不填则查本钱包）",
                }
            },
        ),
        Tool(
            "transfer_vibe",
            "转账 VIBE 代币",
            _transfer_vibe,
            parameters={
                "to_address": {"type": "string", "description": "收款地址"},
                "amount": {"type": "number", "description": "转账数量（VIBE）"},
            },
        ),
        Tool(
            "approve_vibe",
            "授权代币（Approve）",
            _approve_vibe,
            parameters={
                "spender_address": {"type": "string", "description": "授权给哪个地址"},
                "amount": {"type": "number", "description": "授权数量（VIBE）"},
            },
        ),
        Tool(
            "get_transfer_history",
            "查询转账历史",
            _get_transfer_history,
            parameters={
                "address": {
                    "type": "string",
                    "description": "钱包地址（不填则查本钱包）",
                },
                "from_block": {
                    "type": "integer",
                    "description": "起始区块号",
                    "default": 0,
                },
            },
        ),
        Tool(
            "get_total_supply",
            "查询 VIBE 总供应量",
            _get_total_supply,
            parameters={},
        ),
        Tool(
            "get_chain_info",
            "获取链信息",
            _get_chain_info,
            parameters={},
        ),
    ]


async def register_tools(registry) -> None:
    """注册所有区块链工具到 registry。"""
    for tool in get_blockchain_tools():
        registry.register(tool)


# ── 工具实现 ────────────────────────────────────────────────


async def _create_wallet(params: dict[str, Any]) -> dict[str, Any]:
    """创建新钱包。"""
    try:
        vibe = _get_vibe()
        wallet = vibe.create_wallet()
        return {
            "success": True,
            "address": wallet["address"],
            "public_key": wallet.get("public_key", ""),
            "chain": "base_sepolia",
            "explorer": f"https://sepolia.basescan.org/address/{wallet['address']}",
            "warning": "请妥善保管私钥，不要泄露给他人",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_balance(params: dict[str, Any]) -> dict[str, Any]:
    """查询余额。"""
    try:
        vibe = _get_vibe()
        address = params.get("address")
        if not address:
            # 没有私钥时无法派生地址
            return {
                "success": False,
                "error": "未配置私钥，无法派生本钱包地址。请通过 create_wallet 创建或通过 to_address 参数指定地址。",
            }
        balance = vibe.get_balance(address)
        return {
            "success": True,
            "address": balance.address,
            "balance_vibe": balance.balance_vibe,
            "balance_wei": balance.balance_wei,
            "chain": balance.chain,
            "explorer": f"https://sepolia.basescan.org/address/{address}",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _transfer_vibe(params: dict[str, Any]) -> dict[str, Any]:
    """转账 VIBE。"""
    try:
        vibe = _get_vibe()
        to_address = params["to_address"]
        amount = float(params["amount"])

        # 需要私钥才能转账
        if not os.environ.get("USMSB_WALLET_PRIVATE_KEY"):
            return {
                "success": False,
                "error": "未配置 USMSB_WALLET_PRIVATE_KEY 环境变量，无法发起转账。",
            }

        result = vibe.transfer(
            from_private_key=os.environ["USMSB_WALLET_PRIVATE_KEY"],
            to_address=to_address,
            amount_vibe=amount,
        )
        return {
            "success": result["success"],
            "tx_hash": result["tx_hash"],
            "block_number": result.get("block_number"),
            "explorer_url": result.get("explorer_url"),
            "amount_vibe": amount,
            "to_address": to_address,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _approve_vibe(params: dict[str, Any]) -> dict[str, Any]:
    """授权代币。"""
    try:
        vibe = _get_vibe()
        spender_address = params["spender_address"]
        amount = float(params["amount"])

        if not os.environ.get("USMSB_WALLET_PRIVATE_KEY"):
            return {
                "success": False,
                "error": "未配置 USMSB_WALLET_PRIVATE_KEY 环境变量，无法发起授权。",
            }

        result = vibe.approve(
            private_key=os.environ["USMSB_WALLET_PRIVATE_KEY"],
            spender_address=spender_address,
            amount_vibe=amount,
        )
        return {
            "success": result["success"],
            "tx_hash": result["tx_hash"],
            "explorer_url": result.get("explorer_url"),
            "amount_vibe": amount,
            "spender_address": spender_address,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_transfer_history(params: dict[str, Any]) -> dict[str, Any]:
    """查询转账历史。"""
    try:
        vibe = _get_vibe()
        address = params.get("address")
        if not address:
            return {
                "success": False,
                "error": "需要指定 address 参数",
            }
        from_block = int(params.get("from_block", 0))
        history = vibe.get_transfer_history(address, from_block=from_block)
        return {
            "success": True,
            "address": address,
            "count": len(history),
            "transfers": history,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_total_supply(params: dict[str, Any]) -> dict[str, Any]:
    """查询总供应量。"""
    try:
        vibe = _get_vibe()
        total = vibe.get_total_supply()
        return {
            "success": True,
            "total_supply_vibe": total,
            "contract": vibe.contract_address,
            "chain": "base_sepolia",
            "explorer": f"https://sepolia.basescan.org/token/{vibe.contract_address}",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_chain_info(params: dict[str, Any]) -> dict[str, Any]:
    """获取链信息。"""
    try:
        vibe = _get_vibe()
        return {
            "success": True,
            "chain": "base_sepolia",
            "chain_id": vibe.w3.eth.chain_id,
            "block_number": vibe.w3.eth.block_number,
            "is_connected": vibe.is_connected,
            "rpc_url": vibe.rpc_url,
            "contract": vibe.contract_address,
            "vibe_decimals": vibe.get_decimals(),
            "explorer": "https://sepolia.basescan.org",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
