"""
Asset Fractionalization Service for AI Civilization Platform

Implements NFT fragmentation into tradeable ERC20 shares.
"""

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class AssetStatus(StrEnum):
    """Asset status enumeration."""

    CREATED = "created"
    FRAGMENTED = "fragmented"
    TRADING = "trading"
    LOCKED = "locked"
    REDEEMED = "redeemed"


@dataclass
class AssetInfo:
    """Asset information."""

    asset_id: str
    nft_contract: str
    nft_token_id: int
    original_owner: str
    total_shares: int
    share_price: float
    shares_sold: int
    total_earnings: float
    distributed_earnings: float
    created_at: float
    status: AssetStatus
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assetId": self.asset_id,
            "nftContract": self.nft_contract,
            "nftTokenId": self.nft_token_id,
            "originalOwner": self.original_owner,
            "totalShares": self.total_shares,
            "sharePrice": self.share_price,
            "sharesSold": self.shares_sold,
            "totalEarnings": self.total_earnings,
            "distributedEarnings": self.distributed_earnings,
            "createdAt": self.created_at,
            "status": self.status.value,
            "metadata": self.metadata,
        }


@dataclass
class Shareholder:
    """Shareholder information."""

    asset_id: str
    address: str
    shares: int
    claimed_earnings: float
    purchase_time: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "assetId": self.asset_id,
            "address": self.address,
            "shares": self.shares,
            "claimedEarnings": self.claimed_earnings,
            "purchaseTime": self.purchase_time,
        }


class AssetFractionalizationService:
    """
    Asset Fractionalization Service.

    Handles NFT fragmentation, share trading, and earnings distribution.
    """

    MIN_SHARES = 100
    MAX_SHARES = 1000000
    PLATFORM_FEE_RATE = 0.03
    CREATOR_FEE_RATE = 0.05

    def __init__(
        self,
        web3_provider=None,
        contract_address: str | None = None,
        pricing_service=None,
    ):
        self.web3 = web3_provider
        self.contract_address = contract_address
        self.pricing = pricing_service

        self._assets: dict[str, AssetInfo] = {}
        self._shareholders: dict[str, dict[str, Shareholder]] = {}
        self._user_assets: dict[str, list[str]] = {}

        self._running = False
        self._tasks: list[asyncio.Task] = []

        self.on_asset_fragmented: Callable[[AssetInfo], None] | None = None
        self.on_shares_purchased: Callable[[str, str, int], None] | None = None

    async def start(self) -> None:
        self._running = True
        logger.info("Asset fractionalization service started")

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        logger.info("Asset fractionalization service stopped")

    async def deposit_nft(
        self,
        nft_contract: str,
        token_id: int,
        owner: str,
        total_shares: int,
        share_price: float,
        metadata: dict[str, Any] | None = None,
    ) -> AssetInfo:
        """Deposit NFT and create fragmented asset."""
        asset_id = f"asset-{uuid.uuid4().hex[:8]}"

        asset = AssetInfo(
            asset_id=asset_id,
            nft_contract=nft_contract,
            nft_token_id=token_id,
            original_owner=owner,
            total_shares=total_shares,
            share_price=share_price,
            shares_sold=0,
            total_earnings=0.0,
            distributed_earnings=0.0,
            created_at=time.time(),
            status=AssetStatus.CREATED,
            metadata=metadata or {},
        )

        self._assets[asset_id] = asset
        self._shareholders[asset_id] = {}

        if owner not in self._user_assets:
            self._user_assets[owner] = []
        self._user_assets[owner].append(asset_id)

        logger.info(f"Created asset: {asset_id}")

        return asset

    async def fragment_asset(
        self,
        asset_id: str,
    ) -> bool:
        """Fragment an asset into shares."""
        asset = self._assets.get(asset_id)
        if not asset:
            return False

        asset.status = AssetStatus.FRAGMENTED

        creator_shares = int(asset.total_shares * 0.10)

        self._shareholders[asset_id][asset.original_owner] = Shareholder(
            asset_id=asset_id,
            address=asset.original_owner,
            shares=creator_shares,
            claimed_earnings=0.0,
            purchase_time=time.time(),
        )

        asset.shares_sold = creator_shares

        if self.on_asset_fragmented:
            self.on_asset_fragmented(asset)

        logger.info(f"Fragmented asset: {asset_id}")

        return True

    async def purchase_shares(
        self,
        asset_id: str,
        buyer: str,
        amount: int,
    ) -> bool:
        """Purchase shares of an asset."""
        asset = self._assets.get(asset_id)
        if not asset or asset.status != AssetStatus.FRAGMENTED:
            return False

        available = asset.total_shares - asset.shares_sold
        if amount > available:
            return False

        total_cost = amount * asset.share_price

        if buyer in self._shareholders[asset_id]:
            self._shareholders[asset_id][buyer].shares += amount
        else:
            self._shareholders[asset_id][buyer] = Shareholder(
                asset_id=asset_id,
                address=buyer,
                shares=amount,
                claimed_earnings=0.0,
                purchase_time=time.time(),
            )

        if buyer not in self._user_assets:
            self._user_assets[buyer] = []
        if asset_id not in self._user_assets[buyer]:
            self._user_assets[buyer].append(asset_id)

        asset.shares_sold += amount
        asset.total_earnings += total_cost

        if self.on_shares_purchased:
            self.on_shares_purchased(asset_id, buyer, amount)

        logger.info(f"Purchased {amount} shares of {asset_id} by {buyer}")

        return True

    async def distribute_earnings(
        self,
        asset_id: str,
        amount: float,
    ) -> bool:
        """Distribute earnings to shareholders."""
        asset = self._assets.get(asset_id)
        if not asset:
            return False

        asset.total_earnings += amount
        asset.distributed_earnings += amount

        logger.info(f"Distributed {amount} earnings for asset {asset_id}")

        return True

    async def claim_earnings(
        self,
        asset_id: str,
        holder: str,
    ) -> float:
        """Claim earnings for a shareholder."""
        asset = self._assets.get(asset_id)
        if not asset:
            return 0.0

        shareholder = self._shareholders.get(asset_id, {}).get(holder)
        if not shareholder or shareholder.shares == 0:
            return 0.0

        total_entitled = (shareholder.shares * asset.distributed_earnings) / asset.total_shares
        unclaimed = total_entitled - shareholder.claimed_earnings

        if unclaimed > 0:
            shareholder.claimed_earnings = total_entitled

        logger.info(f"Claimed {unclaimed} earnings for {holder}")

        return unclaimed

    def get_asset(self, asset_id: str) -> AssetInfo | None:
        return self._assets.get(asset_id)

    def get_shareholder(self, asset_id: str, address: str) -> Shareholder | None:
        return self._shareholders.get(asset_id, {}).get(address)

    def get_user_assets(self, user: str) -> list[AssetInfo]:
        asset_ids = self._user_assets.get(user, [])
        return [self._assets[aid] for aid in asset_ids if aid in self._assets]


_asset_fractionalization_service: AssetFractionalizationService | None = None


async def get_asset_fractionalization_service() -> AssetFractionalizationService:
    global _asset_fractionalization_service
    if _asset_fractionalization_service is None:
        _asset_fractionalization_service = AssetFractionalizationService()
        await _asset_fractionalization_service.start()
    return _asset_fractionalization_service
