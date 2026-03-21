"""
区块链API端点

提供直接与区块链交互的端点：
- 测试连接
- 查询代币余额
- 查询代币信息
- 查询质押信息
- VIBE代币转账和授权
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from usmsb_sdk.api.rest.unified_auth import get_current_user_unified

router = APIRouter(prefix="/blockchain", tags=["Blockchain"])


class TokenBalanceResponse(BaseModel):
    """代币余额响应"""
    address: str
    balance_wei: int
    balance_vibe: float
    symbol: str
    name: str
    decimals: int


class BlockchainStatusResponse(BaseModel):
    """区块链状态响应"""
    connected: bool
    chain_id: int
    network_name: str
    block_number: int
    token_address: str
    token_name: str
    token_symbol: str


class TaxBreakdownResponse(BaseModel):
    """交易税明细"""
    amount_vibe: float
    tax_rate: float
    tax_vibe: float
    net_vibe: float


@router.get("/status", response_model=BlockchainStatusResponse)
async def get_blockchain_status():
    """
    获取区块链连接状态

    无需认证，直接查询区块链状态
    """
    from usmsb_sdk.blockchain import VIBEBlockchainClient

    try:
        client = VIBEBlockchainClient()

        # 测试连接
        connection = client.test_connection()

        # 获取代币信息
        token_name = client.token.name()
        token_symbol = client.token.symbol()
        client.token.decimals()

        return BlockchainStatusResponse(
            connected=connection["connected"],
            chain_id=connection["chain_id"],
            network_name=client.config.network_name,
            block_number=connection.get("block_number", 0),
            token_address=client.config.get_contract_address("VIBEToken"),
            token_name=token_name,
            token_symbol=token_symbol,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/balance/{address}", response_model=TokenBalanceResponse)
async def get_token_balance(address: str):
    """
    查询指定地址的VIBE代币余额

    无需认证，直接从区块链查询
    """
    from usmsb_sdk.blockchain import VIBEBlockchainClient

    try:
        client = VIBEBlockchainClient()

        # 查询余额
        balance_wei = client.token.balance_of(address)
        balance_vibe = client.token.balance_of_vibe(address)

        # 获取代币信息
        token_symbol = client.token.symbol()
        token_name = client.token.name()

        return TokenBalanceResponse(
            address=address,
            balance_wei=balance_wei,
            balance_vibe=balance_vibe,
            symbol=token_symbol,
            name=token_name,
            decimals=18,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tax/{amount}", response_model=TaxBreakdownResponse)
async def get_tax_breakdown(amount: float):
    """
    计算交易税明细

    Args:
        amount: VIBE金额
    """
    from usmsb_sdk.blockchain import VIBEBlockchainClient

    try:
        client = VIBEBlockchainClient()

        # 转换为wei
        amount_wei = int(amount * (10 ** 18))

        # 计算税费
        breakdown = client.token.get_tax_breakdown(amount_wei)

        return TaxBreakdownResponse(
            amount_vibe=breakdown["amount_vibe"],
            tax_rate=breakdown["tax_rate"],
            tax_vibe=breakdown["tax_vibe"],
            net_vibe=breakdown["net_vibe"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/total-supply")
async def get_total_supply():
    """
    查询VIBE代币总供应量
    """
    from usmsb_sdk.blockchain import VIBEBlockchainClient

    try:
        client = VIBEBlockchainClient()
        supply = client.token.total_supply_vibe()
        return {"total_supply_vibe": supply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== VIBE Token Transfer/Approve Endpoints ====================

class TransferRequest(BaseModel):
    """VIBE代币转账请求"""
    to: str = Field(..., description="接收方地址")
    amount: float = Field(..., gt=0, description="转账金额（VIBE）")


class TransferResponse(BaseModel):
    """VIBE代币转账响应"""
    success: bool
    tx_hash: str
    from_address: str
    to_address: str
    amount_vibe: float
    message: str


class ApproveRequest(BaseModel):
    """VIBE代币授权请求"""
    spender: str = Field(..., description="被授权地址")
    amount: float = Field(..., gt=0, description="授权金额（VIBE），使用0撤销授权")


class ApproveResponse(BaseModel):
    """VIBE代币授权响应"""
    success: bool
    tx_hash: str
    owner: str
    spender: str
    amount_vibe: float
    message: str


class AllowanceResponse(BaseModel):
    """授权额度查询响应"""
    owner: str
    spender: str
    allowance_wei: int
    allowance_vibe: float


@router.post("/transfer", response_model=TransferResponse)
async def transfer_vibe(
    request: TransferRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """
    转账VIBE代币

    需要认证。转账会扣除0.8%的交易税。

    Args:
        to: 接收方地址
        amount: 转账金额（VIBE）
    """
    from usmsb_sdk.blockchain import VIBEBlockchainClient

    # Get sender address from authenticated user
    sender_address = current_user.get("wallet_address") or current_user.get("address")
    if not sender_address:
        raise HTTPException(status_code=401, detail="Wallet address not found in authentication")

    # Get private key - this should be securely retrieved based on auth type
    # For API key auth, we need to get the private key from secure storage
    private_key = current_user.get("private_key")
    if not private_key:
        raise HTTPException(status_code=401, detail="Private key not available for this authentication method")

    try:
        client = VIBEBlockchainClient()

        # Convert VIBE to wei
        amount_wei = int(request.amount * (10 ** 18))

        # Execute transfer
        tx_hash = client.token.transfer(
            to=request.to,
            amount=amount_wei,
            from_address=sender_address,
            private_key=private_key,
        )

        return TransferResponse(
            success=True,
            tx_hash=tx_hash,
            from_address=sender_address,
            to_address=request.to,
            amount_vibe=request.amount,
            message=f"Successfully transferred {request.amount} VIBE to {request.to}",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/approve", response_model=ApproveResponse)
async def approve_vibe(
    request: ApproveRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """
    授权代币消费

    需要认证。授权后，被授权地址可以使用您的VIBE代币。

    Args:
        spender: 被授权地址
        amount: 授权金额（VIBE），使用0撤销授权
    """
    from usmsb_sdk.blockchain import VIBEBlockchainClient

    # Get owner address from authenticated user
    owner_address = current_user.get("wallet_address") or current_user.get("address")
    if not owner_address:
        raise HTTPException(status_code=401, detail="Wallet address not found in authentication")

    # Get private key
    private_key = current_user.get("private_key")
    if not private_key:
        raise HTTPException(status_code=401, detail="Private key not available for this authentication method")

    try:
        client = VIBEBlockchainClient()

        # Convert VIBE to wei
        amount_wei = int(request.amount * (10 ** 18))

        # Execute approve
        tx_hash = client.token.approve(
            spender=request.spender,
            amount=amount_wei,
            from_address=owner_address,
            private_key=private_key,
        )

        action = "revoked" if request.amount == 0 else "approved"
        return ApproveResponse(
            success=True,
            tx_hash=tx_hash,
            owner=owner_address,
            spender=request.spender,
            amount_vibe=request.amount,
            message=f"Successfully {action} {request.spender} to spend {request.amount} VIBE",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/allowance/{owner}/{spender}", response_model=AllowanceResponse)
async def get_allowance(owner: str, spender: str):
    """
    查询授权额度

    无需认证，直接从区块链查询。

    Args:
        owner: 代币所有者地址
        spender: 被授权地址
    """
    from usmsb_sdk.blockchain import VIBEBlockchainClient

    try:
        client = VIBEBlockchainClient()

        allowance_wei = client.token.allowance(owner, spender)
        allowance_vibe = float(client.token.w3.from_wei(allowance_wei, "ether"))

        return AllowanceResponse(
            owner=owner,
            spender=spender,
            allowance_wei=allowance_wei,
            allowance_vibe=allowance_vibe,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== B16: Transaction Status Tracking ====================

import asyncio
import time
import uuid
from typing import Optional

# Global transaction tracking dict with TTL cleanup
_pending_transactions: dict[str, dict] = {}
_transaction_cleanup_interval = 300  # Clean up every 5 minutes


async def _cleanup_expired_transactions():
    """Background task to clean up expired transactions."""
    while True:
        try:
            await asyncio.sleep(_transaction_cleanup_interval)
            current_time = time.time()
            expired_keys = [
                k for k, v in _pending_transactions.items()
                if current_time - v.get("created_at", 0) > 3600  # Expire after 1 hour
            ]
            for k in expired_keys:
                del _pending_transactions[k]
        except asyncio.CancelledError:
            break
        except Exception:
            pass


def _create_task_id() -> str:
    """Generate a unique task ID."""
    return f"tx_{uuid.uuid4().hex[:16]}"


def _store_transaction(task_id: str, tx_hash: str, from_address: str, to_address: str | None, amount: float | None):
    """Store a pending transaction for tracking."""
    _pending_transactions[task_id] = {
        "status": "pending",
        "tx_hash": tx_hash,
        "from_address": from_address,
        "to_address": to_address,
        "amount": amount,
        "created_at": time.time(),
        "receipt": None,
    }


def _update_transaction_receipt(task_id: str, receipt: dict):
    """Update transaction with receipt info."""
    if task_id in _pending_transactions:
        tx = _pending_transactions[task_id]
        if receipt:
            status = "confirmed" if receipt.get("status") == 1 else "failed"
        else:
            status = "failed"
        tx["status"] = status
        tx["receipt"] = receipt


class TransactionStatusResponse(BaseModel):
    """Transaction status response."""
    task_id: str
    status: str  # pending, confirmed, failed
    tx_hash: str | None
    from_address: str | None
    to_address: str | None
    amount: float | None
    block_number: int | None
    message: str


@router.get("/tx/{task_id}", response_model=TransactionStatusResponse)
async def get_transaction_status(task_id: str):
    """
    Get transaction status by task ID.

    B16: Returns current status of a tracked transaction.

    Args:
        task_id: The task ID returned when the transaction was submitted
    """
    if task_id not in _pending_transactions:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tx = _pending_transactions[task_id]
    receipt = tx.get("receipt")
    block_number = None

    if receipt:
        try:
            block_number = receipt.get("blockNumber")
        except Exception:
            pass

    return TransactionStatusResponse(
        task_id=task_id,
        status=tx["status"],
        tx_hash=tx.get("tx_hash"),
        from_address=tx.get("from_address"),
        to_address=tx.get("to_address"),
        amount=tx.get("amount"),
        block_number=block_number,
        message=f"Transaction is {tx['status']}",
    )


@router.post("/tx/track")
async def track_transaction(
    tx_hash: str,
    from_address: str,
    to_address: str | None = None,
    amount: float | None = None,
):
    """
    Track a transaction by its hash.

    B16: Submit a transaction hash to track its status.

    Args:
        tx_hash: The transaction hash to track
        from_address: The sender address
        to_address: Optional recipient address
        amount: Optional amount in VIBE
    """
    from usmsb_sdk.blockchain import VIBEBlockchainClient

    task_id = _create_task_id()
    _store_transaction(task_id, tx_hash, from_address, to_address, amount)

    # Try to get initial receipt
    try:
        client = VIBEBlockchainClient()
        w3 = client.w3
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        _update_transaction_receipt(task_id, dict(receipt))
    except Exception:
        # Transaction might not be mined yet
        pass

    return {
        "task_id": task_id,
        "tx_hash": tx_hash,
        "status": "pending",
        "message": "Transaction is being tracked",
    }


# ==================== B17: Gas Estimation ====================

class GasEstimateResponse(BaseModel):
    """Gas estimation response."""
    function: str
    gas_estimate: int
    gas_price_wei: int
    gas_price_gwei: float
    estimated_cost_wei: int
    estimated_cost_vibe: float


@router.get("/gas-estimate", response_model=GasEstimateResponse)
async def estimate_gas(
    function: str,
    from_address: str,
    to_address: str | None = None,
    amount: float | None = None,
):
    """
    Estimate gas for a function call.

    B17: Estimates gas for common VIBE token operations.

    Args:
        function: Function name (transfer, approve, stake, unstake, etc.)
        from_address: Address executing the function
        to_address: Optional target address (for transfer/receive)
        amount: Optional amount in VIBE
    """
    from usmsb_sdk.blockchain import VIBEBlockchainClient

    try:
        client = VIBEBlockchainClient()
        w3 = client.w3

        # Get current gas price
        gas_price_wei = w3.eth.gas_price
        gas_price_gwei = w3.from_wei(gas_price_wei, "gwei")

        # Estimate gas based on function
        if function.lower() == "transfer":
            amount_wei = int(amount * (10 ** 18)) if amount else 0
            # Build a mock transfer call for estimation
            token_address = client.config.get_contract_address("VIBEToken")
            if not token_address or token_address == "待部署":
                raise HTTPException(status_code=500, detail="VIBEToken not deployed")

            token_contract = w3.eth.contract(
                address=w3.to_checksum_address(token_address),
                abi=[
                    {
                        "inputs": [
                            {"name": "to", "type": "address"},
                            {"name": "amount", "type": "uint256"},
                        ],
                        "name": "transfer",
                        "outputs": [{"type": "bool"}],
                        "stateMutability": "nonpayable",
                        "type": "function",
                    }
                ],
            )

            try:
                gas_estimate = token_contract.functions.transfer(
                    w3.to_checksum_address(to_address) if to_address else from_address,
                    amount_wei
                ).estimate_gas({"from": w3.to_checksum_address(from_address)})
            except Exception:
                gas_estimate = 65000  # Fallback typical gas for transfer

        elif function.lower() == "approve":
            amount_wei = int(amount * (10 ** 18)) if amount else 0
            token_address = client.config.get_contract_address("VIBEToken")
            if not token_address or token_address == "待部署":
                raise HTTPException(status_code=500, detail="VIBEToken not deployed")

            token_contract = w3.eth.contract(
                address=w3.to_checksum_address(token_address),
                abi=[
                    {
                        "inputs": [
                            {"name": "spender", "type": "address"},
                            {"name": "amount", "type": "uint256"},
                        ],
                        "name": "approve",
                        "outputs": [{"type": "bool"}],
                        "stateMutability": "nonpayable",
                        "type": "function",
                    }
                ],
            )

            try:
                gas_estimate = token_contract.functions.approve(
                    w3.to_checksum_address(to_address) if to_address else from_address,
                    amount_wei
                ).estimate_gas({"from": w3.to_checksum_address(from_address)})
            except Exception:
                gas_estimate = 46000  # Fallback typical gas for approve

        elif function.lower() in ("stake", "unstake"):
            # Staking operations
            staking_address = client.config.get_contract_address("VIBStaking")
            if not staking_address or staking_address == "待部署":
                raise HTTPException(status_code=500, detail="VIBStaking not deployed")

            if function.lower() == "stake":
                gas_estimate = 120000  # Typical stake operation
            else:
                gas_estimate = 100000  # Typical unstake operation

        else:
            # Default gas estimate for unknown functions
            gas_estimate = 100000

        estimated_cost_wei = gas_estimate * gas_price_wei
        estimated_cost_vibe = float(w3.from_wei(estimated_cost_wei, "ether"))

        return GasEstimateResponse(
            function=function,
            gas_estimate=gas_estimate,
            gas_price_wei=gas_price_wei,
            gas_price_gwei=gas_price_gwei,
            estimated_cost_wei=estimated_cost_wei,
            estimated_cost_vibe=estimated_cost_vibe,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
