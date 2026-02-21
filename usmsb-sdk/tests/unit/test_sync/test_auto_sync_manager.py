"""
Unit tests for AutoSyncManager

测试自动同步管理器的各项功能：
1. 画像/知识库变更触发同步
2. 防抖机制
3. 会话关闭前同步
4. 定期全量同步
5. 失败重试
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from usmsb_sdk.meta_agent.sync.auto_sync_manager import (
    AutoSyncManager,
    SyncConfig,
    SyncStatus,
    SyncResult,
    SyncType,
    SyncState,
    SyncError,
    SyncInProgressError,
)


@pytest.fixture
def mock_callback():
    """模拟同步回调函数"""
    async def callback(wallet_address: str, sync_type: SyncType) -> str:
        return f"QmTest{wallet_address[-4:]}{sync_type.value}"
    return callback


@pytest.fixture
def quick_config():
    """快速测试用的配置（延迟时间较短）"""
    return SyncConfig(
        profile_sync_delay=0.5,      # 0.5秒
        knowledge_sync_delay=1.0,    # 1秒
        full_sync_interval=2,         # 2秒
        full_sync_random_delay=1,     # 0-1秒
        retry_attempts=2,             # 2次重试
        retry_delay=0.1,              # 0.1秒
        enable_background_sync=False,  # 不启用后台同步用于单元测试
    )


@pytest.mark.asyncio
class TestAutoSyncManager:
    """AutoSyncManager 单元测试"""

    async def test_init_default_config(self):
        """测试默认配置初始化"""
        manager = AutoSyncManager()

        assert manager.config.profile_sync_delay == 300
        assert manager.config.knowledge_sync_delay == 600
        assert manager.config.full_sync_interval == 3600
        assert manager.config.retry_attempts == 3
        assert not manager._running

    async def test_init_custom_config(self, quick_config):
        """测试自定义配置初始化"""
        manager = AutoSyncManager(config=quick_config)

        assert manager.config.profile_sync_delay == 0.5
        assert manager.config.knowledge_sync_delay == 1.0
        assert manager.config.full_sync_interval == 2

    async def test_start_stop(self, quick_config):
        """测试启动和停止服务"""
        manager = AutoSyncManager(config=quick_config)

        # 初始状态
        assert not manager._running

        # 启动
        await manager.start()
        assert manager._running

        # 停止
        await manager.stop()
        assert not manager._running

    async def test_start_already_running(self, quick_config):
        """测试重复启动"""
        manager = AutoSyncManager(config=quick_config)

        await manager.start()
        await manager.start()  # 应该被忽略，不抛出错误

        await manager.stop()

    async def test_profile_change_triggers_sync(self, quick_config, mock_callback):
        """测试画像变更触发同步"""
        manager = AutoSyncManager(config=quick_config, sync_callback=mock_callback)
        await manager.start()

        wallet = "0xAAA1111111111111"

        # 触发画像变更
        await manager.on_profile_changed(wallet)

        # 等待延迟时间
        await asyncio.sleep(0.6)

        # 检查状态
        status = manager.get_sync_status(wallet)
        assert status.state == SyncState.SUCCESS
        assert status.last_sync_type == SyncType.PROFILE
        assert status.last_cid is not None

        # 检查统计
        stats = manager.get_stats()
        assert stats["successful_syncs"] == 1

        await manager.stop()

    async def test_knowledge_change_triggers_sync(self, quick_config, mock_callback):
        """测试知识库变更触发同步"""
        manager = AutoSyncManager(config=quick_config, sync_callback=mock_callback)
        await manager.start()

        wallet = "0xAAA1111111111111"

        # 触发知识库变更
        await manager.on_knowledge_changed(wallet)

        # 等待延迟时间
        await asyncio.sleep(1.1)

        # 检查状态
        status = manager.get_sync_status(wallet)
        assert status.state == SyncState.SUCCESS
        assert status.last_sync_type == SyncType.KNOWLEDGE

        await manager.stop()

    async def test_debounce_profile_changes(self, quick_config, mock_callback):
        """测试防抖机制 - 多次画像变更只触发一次同步"""
        manager = AutoSyncManager(config=quick_config, sync_callback=mock_callback)
        await manager.start()

        wallet = "0xAAA1111111111111"

        # 触发多次变更
        await manager.on_profile_changed(wallet)
        await asyncio.sleep(0.2)
        await manager.on_profile_changed(wallet)
        await asyncio.sleep(0.2)
        await manager.on_profile_changed(wallet)

        # 等待最后的延迟时间
        await asyncio.sleep(0.6)

        # 应该只执行一次同步
        status = manager.get_sync_status(wallet)
        assert status.state == SyncState.SUCCESS

        stats = manager.get_stats()
        assert stats["successful_syncs"] == 1

        await manager.stop()

    async def test_debounce_knowledge_changes(self, quick_config, mock_callback):
        """测试防抖机制 - 多次知识库变更只触发一次同步"""
        manager = AutoSyncManager(config=quick_config, sync_callback=mock_callback)
        await manager.start()

        wallet = "0xAAA1111111111111"

        # 触发多次变更
        await manager.on_knowledge_changed(wallet)
        await asyncio.sleep(0.3)
        await manager.on_knowledge_changed(wallet)
        await asyncio.sleep(0.3)
        await manager.on_knowledge_changed(wallet)

        # 等待最后的延迟时间
        await asyncio.sleep(1.1)

        # 应该只执行一次同步
        status = manager.get_sync_status(wallet)
        assert status.state == SyncState.SUCCESS

        stats = manager.get_stats()
        assert stats["successful_syncs"] == 1

        await manager.stop()

    async def test_sync_before_close(self, quick_config, mock_callback):
        """测试会话关闭前同步"""
        manager = AutoSyncManager(config=quick_config, sync_callback=mock_callback)
        await manager.start()

        wallet = "0xAAA1111111111111"

        # 触发一些变更
        await manager.on_profile_changed(wallet)
        await manager.on_knowledge_changed(wallet)

        # 立即执行会话关闭前同步
        results = await manager.sync_before_close(wallet)

        # 应该同步所有待同步类型
        assert len(results) >= 1
        assert all(r.success for r in results)

        # 待同步应该被清空
        status = manager.get_sync_status(wallet)
        assert not status.has_pending

        await manager.stop()

    async def test_sync_before_close_with_idle(self, quick_config, mock_callback):
        """测试空闲时会话关闭前同步（全量同步）"""
        manager = AutoSyncManager(config=quick_config, sync_callback=mock_callback)
        await manager.start()

        wallet = "0xAAA1111111111111"

        # 没有待同步，但有 idle 配置
        results = await manager.sync_before_close(wallet)

        # 应该执行一次全量同步
        assert len(results) == 1
        assert results[0].sync_type == SyncType.FULL

        await manager.stop()

    async def test_sync_before_close_disabled(self, quick_config, mock_callback):
        """测试禁用会话关闭前同步"""
        config = SyncConfig(
            sync_on_session_close=False,
            enable_background_sync=False
        )
        manager = AutoSyncManager(config=config, sync_callback=mock_callback)
        await manager.start()

        wallet = "0xAAA1111111111111"

        await manager.on_profile_changed(wallet)

        # 立即执行会话关闭前同步
        results = await manager.sync_before_close(wallet)

        # 不应该执行任何同步
        assert results is None

        await manager.stop()

    async def test_force_sync(self, quick_config, mock_callback):
        """测试强制立即同步"""
        manager = AutoSyncManager(config=quick_config, sync_callback=mock_callback)
        await manager.start()

        wallet = "0xAAA1111111111111"

        # 强制同步（不指定类型，默认全量）
        result = await manager.force_sync(wallet)

        assert result.success
        assert result.sync_type == SyncType.FULL
        assert result.wallet_address == wallet

        # 检查状态
        status = manager.get_sync_status(wallet)
        assert status.state == SyncState.SUCCESS

        await manager.stop()

    async def test_force_sync_with_type(self, quick_config, mock_callback):
        """测试指定类型的强制同步"""
        manager = AutoSyncManager(config=quick_config, sync_callback=mock_callback)
        await manager.start()

        wallet = "0xAAA1111111111111"

        # 强制同步画像
        result = await manager.force_sync(wallet, SyncType.PROFILE)

        assert result.success
        assert result.sync_type == SyncType.PROFILE

        await manager.stop()

    async def test_sync_retry_on_failure(self, quick_config):
        """测试失败重试机制"""
        call_count = 0

        async def failing_callback(wallet: str, sync_type: SyncType) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First attempt failed")
            return f"QmSuccess{call_count}"

        manager = AutoSyncManager(config=quick_config, sync_callback=failing_callback)
        await manager.start()

        wallet = "0xAAA1111111111111"

        # 强制同步（应该重试）
        result = await manager.force_sync(wallet)

        assert result.success
        assert result.retry_count == 1  # 重试了一次
        assert call_count == 2  # 第一次失败，第二次成功

        stats = manager.get_stats()
        assert stats["retried_syncs"] == 1

        await manager.stop()

    async def test_sync_max_retries_exceeded(self, quick_config):
        """测试超过最大重试次数"""
        async def always_failing_callback(wallet: str, sync_type: SyncType) -> str:
            raise Exception("Always failing")

        manager = AutoSyncManager(config=quick_config, sync_callback=always_failing_callback)
        await manager.start()

        wallet = "0xAAA1111111111111"

        # 强制同步（应该重试到最大次数）
        result = await manager.force_sync(wallet)

        assert not result.success
        assert result.retry_count == 1  # 尝试了2次（初始+1次重试）
        assert result.error is not None

        stats = manager.get_stats()
        assert stats["failed_syncs"] == 1

        await manager.stop()

    async def test_periodic_sync(self):
        """测试定期全量同步"""
        config = SyncConfig(
            full_sync_interval=1,  # 1秒
            full_sync_random_delay=0,  # 无随机延迟
            max_concurrent_syncs=2,
            enable_background_sync=True
        )

        sync_count = 0

        async def count_callback(wallet: str, sync_type: SyncType) -> str:
            nonlocal sync_count
            sync_count += 1
            return f"QmSync{sync_count}"

        manager = AutoSyncManager(config=config, sync_callback=count_callback)

        # 创建一些用户
        wallets = ["0xAAA1", "0xBBB2", "0xCCC3"]
        for wallet in wallets:
            manager.get_sync_status(wallet)

        # 启动管理器
        await manager.start()

        # 等待超过一次定期同步间隔
        await asyncio.sleep(2)

        # 检查是否执行了定期同步
        stats = manager.get_stats()
        assert stats["successful_syncs"] >= len(wallets)

        await manager.stop()

    async def test_get_sync_status(self):
        """测试获取同步状态"""
        manager = AutoSyncManager()
        wallet = "0xAAA1111111111111"

        status = manager.get_sync_status(wallet)

        assert status.wallet_address == wallet
        assert status.state == SyncState.IDLE
        assert not status.has_pending
        assert not status.is_syncing

    async def test_get_all_sync_status(self):
        """测试获取所有用户同步状态"""
        manager = AutoSyncManager()
        wallets = ["0xAAA1", "0xBBB2", "0xCCC3"]

        # 获取状态会自动创建
        all_status = manager.get_all_sync_status()
        assert len(all_status) == 0

        # 获取每个用户的状态
        for wallet in wallets:
            manager.get_sync_status(wallet)

        all_status = manager.get_all_sync_status()
        assert len(all_status) == len(wallets)
        assert all(wallet in all_status for wallet in wallets)

    async def test_get_stats(self, quick_config, mock_callback):
        """测试获取统计信息"""
        manager = AutoSyncManager(config=quick_config, sync_callback=mock_callback)
        await manager.start()

        wallet = "0xAAA1111111111111"

        # 执行几次同步
        await manager.force_sync(wallet)
        await manager.force_sync(wallet)

        stats = manager.get_stats()

        assert "total_syncs" in stats
        assert "successful_syncs" in stats
        assert "failed_syncs" in stats
        assert "retried_syncs" in stats
        assert stats["total_syncs"] == 2
        assert stats["successful_syncs"] == 2

        await manager.stop()

    async def test_cleanup_user(self, quick_config, mock_callback):
        """测试清理用户状态"""
        manager = AutoSyncManager(config=quick_config, sync_callback=mock_callback)
        await manager.start()

        wallet = "0xAAA1111111111111"

        # 创建一些待同步
        await manager.on_profile_changed(wallet)
        await manager.on_knowledge_changed(wallet)

        # 检查状态存在
        status = manager.get_sync_status(wallet)
        assert status is not None
        assert status.has_pending

        # 清理用户
        manager.cleanup_user(wallet)

        # 检查状态已清除
        all_status = manager.get_all_sync_status()
        assert wallet not in all_status

        await manager.stop()

    async def test_set_sync_callback(self, quick_config):
        """测试设置同步回调"""
        manager = AutoSyncManager(config=quick_config)
        await manager.start()

        async def callback1(wallet: str, sync_type: SyncType) -> str:
            return "CID1"

        async def callback2(wallet: str, sync_type: SyncType) -> str:
            return "CID2"

        manager.set_sync_callback(callback1)

        wallet = "0xAAA1111111111111"
        result = await manager.force_sync(wallet)
        assert result.cid == "CID1"

        # 更新回调
        manager.set_sync_callback(callback2)
        result = await manager.force_sync(wallet)
        assert result.cid == "CID2"

        await manager.stop()

    async def test_sync_all_pending(self, quick_config, mock_callback):
        """测试同步所有待处理数据"""
        manager = AutoSyncManager(config=quick_config, sync_callback=mock_callback)
        await manager.start()

        # 为多个用户创建待同步
        wallets = ["0xAAA1", "0xBBB2", "0xCCC3"]
        for wallet in wallets:
            await manager.on_profile_changed(wallet)

        # 同步所有待处理
        results = await manager.sync_all_pending()

        assert len(results) == len(wallets)
        assert all(r.success for r in results)

        await manager.stop()

    async def test_multiple_concurrent_users(self, quick_config, mock_callback):
        """测试多用户并发同步"""
        manager = AutoSyncManager(config=quick_config, sync_callback=mock_callback)
        await manager.start()

        wallets = [f"0xUser{i}" for i in range(5)]

        # 并发触发同步
        tasks = [manager.force_sync(wallet) for wallet in wallets]
        results = await asyncio.gather(*tasks)

        assert all(r.success for r in results)

        stats = manager.get_stats()
        assert stats["total_syncs"] == len(wallets)

        await manager.stop()

    async def test_sync_without_callback(self, quick_config):
        """测试没有回调函数时的行为（使用mock同步）"""
        manager = AutoSyncManager(config=quick_config)  # 没有回调
        await manager.start()

        wallet = "0xAAA1111111111111"

        result = await manager.force_sync(wallet)

        # 应该返回成功的模拟结果
        assert result.success
        assert result.cid is not None
        assert result.cid.startswith("QmMock")

        await manager.stop()

    async def test_sync_state_transitions(self, quick_config, mock_callback):
        """测试同步状态转换"""
        manager = AutoSyncManager(config=quick_config, sync_callback=mock_callback)
        await manager.start()

        wallet = "0xAAA1111111111111"

        # 初始状态
        status = manager.get_sync_status(wallet)
        assert status.state == SyncState.IDLE

        # 触发变更
        await manager.on_profile_changed(wallet)
        status = manager.get_sync_status(wallet)
        assert status.state == SyncState.PENDING

        # 等待同步
        await asyncio.sleep(0.6)
        status = manager.get_sync_status(wallet)
        assert status.state == SyncState.SUCCESS

        await manager.stop()

    async def test_pending_syncs_set(self, quick_config, mock_callback):
        """测试待同步集合管理"""
        manager = AutoSyncManager(config=quick_config, sync_callback=mock_callback)
        await manager.start()

        wallet = "0xAAA1111111111111"

        # 触发多种类型的变更
        await manager.on_profile_changed(wallet)
        await manager.on_knowledge_changed(wallet)

        status = manager.get_sync_status(wallet)
        assert SyncType.PROFILE in status.pending_syncs
        assert SyncType.KNOWLEDGE in status.pending_syncs
        assert status.has_pending

        await manager.stop()
