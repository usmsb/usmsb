"""
Unit tests for DataMigration

测试数据迁移功能的各项功能：
1. 迁移进度跟踪
2. 导出到IPFS
3. 从IPFS迁移
4. 迁移验证
5. 进度回调
6. 加密迁移
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from usmsb_sdk.platform.external.meta_agent.migrate.data_migration import (
    DataMigration,
    MigrationProgress,
    MigrationResult,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_wallet():
    """创建示例钱包地址"""
    return "0xAAA111111111111111111111111111111111111"


@pytest.fixture
def sample_profile():
    """创建示例用户画像"""
    return {
        "preferences": {"theme": "dark", "language": "zh"},
        "commitments": ["learn python", "build projects"],
        "knowledge": {"topics": ["AI", "blockchain"]},
        "last_updated": time.time()
    }


@pytest.fixture
def sample_knowledge():
    """创建示例知识库"""
    return {
        "items": [
            {"id": "k1", "content": "Knowledge 1", "category": "tech"},
            {"id": "k2", "content": "Knowledge 2", "category": "general"}
        ],
        "version": "1.0"
    }


@pytest.fixture
def mock_session(sample_wallet):
    """创建模拟的UserSession"""
    session = MagicMock()
    session.wallet_address = sample_wallet
    session._initialized = True
    session.node_id = "test-node-001"
    session._ipfs_cid = None
    # Mock async methods
    session._update_metadata = AsyncMock()
    return session


@pytest.fixture
def mock_user_database(sample_profile, sample_knowledge):
    """创建模拟的UserDatabase"""
    db = AsyncMock()
    db.get_profile = AsyncMock(return_value=sample_profile)
    db.export_knowledge = AsyncMock(return_value=sample_knowledge)
    db.import_knowledge = AsyncMock()
    db.update_profile = AsyncMock()
    return db


@pytest.fixture
def mock_ipfs_client():
    """创建模拟的IPFSClient"""
    from usmsb_sdk.platform.external.meta_agent.ipfs.ipfs_client import IPFSUploadResult

    client = AsyncMock()
    client.upload_user_data = AsyncMock(return_value=IPFSUploadResult(
        success=True,
        cid="QmTestCID123456789",
        size=1024,
        gateway_used="https://ipfs.io"
    ))
    client.download_user_data = AsyncMock()
    client.get_user_cid = AsyncMock()
    client.publish_cid = AsyncMock(return_value=True)
    client.pin_cid = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_ipfs_upload_result():
    """创建模拟的IPFS上传结果"""
    from usmsb_sdk.platform.external.meta_agent.ipfs.ipfs_client import IPFSUploadResult
    return IPFSUploadResult(
        success=True,
        cid="QmTestCID123456789",
        size=1024,
        gateway_used="https://ipfs.io"
    )


@pytest.fixture
def data_migration(mock_session):
    """创建DataMigration实例用于测试"""
    return DataMigration(session=mock_session)


# ============================================================================
# TestMigrationProgress
# ============================================================================

class TestMigrationProgress:
    """MigrationProgress 单元测试"""

    def test_progress_initialization(self):
        """测试进度初始化"""
        progress = MigrationProgress()

        assert progress.stage == "idle"
        assert progress.total_items == 0
        assert progress.completed_items == 0
        assert progress.bytes_processed == 0
        assert progress.total_bytes == 0
        assert progress.message == ""
        assert progress.error is None
        assert progress.end_time is None

    def test_progress_percentage_zero_items(self):
        """测试进度百分比计算（零项）"""
        progress = MigrationProgress(total_items=0)
        assert progress.percentage == 0.0

    def test_progress_percentage_partial(self):
        """测试进度百分比计算（部分完成）"""
        progress = MigrationProgress(total_items=100, completed_items=25)
        assert progress.percentage == 25.0

    def test_progress_percentage_complete(self):
        """测试进度百分比计算（全部完成）"""
        progress = MigrationProgress(total_items=10, completed_items=10)
        assert progress.percentage == 100.0

    def test_elapsed_seconds(self):
        """测试已用时间计算"""
        progress = MigrationProgress()
        time.sleep(0.1)
        elapsed = progress.elapsed_seconds
        assert elapsed >= 0.1

    def test_elapsed_seconds_with_end_time(self):
        """测试带结束时间的已用时间计算"""
        start = time.time() - 2.0
        end = time.time()
        progress = MigrationProgress(start_time=start, end_time=end)
        assert abs(progress.elapsed_seconds - 2.0) < 0.1

    def test_speed_mb_per_sec_zero_time(self):
        """测试传输速度计算（零时间）"""
        progress = MigrationProgress(bytes_processed=1024*1024, start_time=time.time())
        assert progress.speed_mb_per_sec == 0.0

    def test_speed_mb_per_sec(self):
        """测试传输速度计算"""
        start = time.time() - 2.0
        progress = MigrationProgress(bytes_processed=10*1024*1024, start_time=start)
        assert abs(progress.speed_mb_per_sec - 5.0) < 0.5

    def test_speed_mb_per_sec_no_bytes(self):
        """测试传输速度计算（无字节）"""
        progress = MigrationProgress(start_time=time.time() - 1.0)
        assert progress.speed_mb_per_sec == 0.0


# ============================================================================
# TestDataMigration
# ============================================================================

@pytest.mark.asyncio
class TestDataMigration:
    """DataMigration 单元测试"""

    async def test_data_migration_initialization(self, mock_session):
        """测试数据迁移服务初始化"""
        migration = DataMigration(session=mock_session)

        assert migration.session == mock_session
        assert migration._progress.stage == "idle"
        assert len(migration._progress_callbacks) == 0

    async def test_add_progress_callback(self, data_migration):
        """测试添加进度回调"""
        callback = MagicMock()
        data_migration.add_progress_callback(callback)

        assert len(data_migration._progress_callbacks) == 1
        assert data_migration._progress_callbacks[0] == callback

    async def test_add_multiple_progress_callbacks(self, data_migration):
        """测试添加多个进度回调"""
        callbacks = [MagicMock() for _ in range(3)]
        for callback in callbacks:
            data_migration.add_progress_callback(callback)

        assert len(data_migration._progress_callbacks) == 3

    async def test_notify_progress(self, data_migration):
        """测试进度通知"""
        callback = MagicMock()
        data_migration.add_progress_callback(callback)

        data_migration._start_stage("test_stage", total_items=10, message="Testing")

        callback.assert_called_once()
        call_args = callback.call_args[0][0]
        assert call_args.stage == "test_stage"
        assert call_args.total_items == 10
        assert call_args.message == "Testing"

    async def test_get_progress(self, data_migration):
        """测试获取进度"""
        progress = data_migration.get_progress()
        assert progress.stage == "idle"

        data_migration._start_stage("testing", total_items=5)
        progress = data_migration.get_progress()
        assert progress.stage == "testing"
        assert progress.total_items == 5

    async def test_reset_progress(self, data_migration):
        """测试重置进度"""
        data_migration._start_stage("testing", total_items=10)
        data_migration._update_progress(completed=5, bytes_processed=1024)

        data_migration.reset_progress()

        progress = data_migration.get_progress()
        assert progress.stage == "idle"
        assert progress.completed_items == 0
        assert progress.bytes_processed == 0

    async def test_export_to_ipfs_success(
        self,
        data_migration,
        mock_user_database,
        mock_ipfs_client,
        mock_ipfs_upload_result
    ):
        """测试导出到IPFS（成功情况）"""
        # 设置模拟
        data_migration.session.db = mock_user_database
        data_migration.session.ipfs_client = mock_ipfs_client
        mock_ipfs_client.upload_user_data.return_value = mock_ipfs_upload_result

        # 执行导出
        result = await data_migration.export_to_ipfs(verify=False)

        # 验证结果
        assert result.success
        assert result.cid == "QmTestCID123456789"
        assert result.items_exported == 2
        assert result.bytes_transferred > 0

        # 验证调用
        mock_user_database.get_profile.assert_called_once()
        mock_user_database.export_knowledge.assert_called_once()
        mock_ipfs_client.upload_user_data.assert_called_once()

    async def test_export_to_ipfs_with_verification(
        self,
        data_migration,
        mock_user_database,
        mock_ipfs_client,
        mock_ipfs_upload_result
    ):
        """测试导出到IPFS（带验证）"""
        # 设置模拟
        data_migration.session.db = mock_user_database
        data_migration.session.ipfs_client = mock_ipfs_client
        mock_ipfs_client.upload_user_data.return_value = mock_ipfs_upload_result
        mock_ipfs_client.download_user_data.return_value = {
            "version": "1.0",
            "wallet_address": data_migration.session.wallet_address,
            "exported_at": time.time()
        }

        # 执行导出（带验证）
        result = await data_migration.export_to_ipfs(verify=True)

        # 验证结果
        assert result.success
        assert result.verification_passed

        # 验证下载用于验证
        mock_ipfs_client.download_user_data.assert_called()

    async def test_export_to_ipfs_not_initialized(self, data_migration):
        """测试导出到IPFS（会话未初始化）"""
        data_migration.session._initialized = False

        result = await data_migration.export_to_ipfs(verify=False)

        assert not result.success
        assert "not initialized" in result.error.lower()

    async def test_export_to_ipfs_upload_failure(
        self,
        data_migration,
        mock_user_database,
        mock_ipfs_client
    ):
        """测试导出到IPFS（上传失败）"""
        # 设置模拟
        data_migration.session.db = mock_user_database
        data_migration.session.ipfs_client = mock_ipfs_client

        from usmsb_sdk.platform.external.meta_agent.ipfs.ipfs_client import IPFSUploadResult
        mock_ipfs_client.upload_user_data.return_value = IPFSUploadResult(
            success=False,
            error="Network error"
        )

        # 执行导出
        result = await data_migration.export_to_ipfs(verify=False)

        # 验证结果
        assert not result.success
        assert result.error == "IPFS upload failed: Network error"

    async def test_migrate_from_ipfs_success(
        self,
        data_migration,
        mock_user_database,
        mock_ipfs_client
    ):
        """测试从IPFS迁移（成功情况）"""
        # 设置模拟
        data_migration.session.db = mock_user_database
        data_migration.session.ipfs_client = mock_ipfs_client
        mock_ipfs_client.get_user_cid.return_value = "QmTestCID"

        ipfs_data = {
            "version": "1.0",
            "wallet_address": data_migration.session.wallet_address,
            "profile": {
                "preferences": {"theme": "dark"},
                "commitments": ["test"],
                "knowledge": {},
                "last_updated": time.time()
            },
            "knowledge": {"items": []}
        }
        mock_ipfs_client.download_user_data.return_value = ipfs_data

        # 模拟数据库检查返回False（无本地数据）
        async def mock_has_local():
            return False
        data_migration._has_local_data = mock_has_local

        # 执行迁移
        result = await data_migration.migrate_from_ipfs(force=True, verify=False)

        # 验证结果
        assert result.success
        assert result.cid == "QmTestCID"
        assert result.items_imported > 0

        # 验证调用
        mock_ipfs_client.get_user_cid.assert_called_once()
        mock_ipfs_client.download_user_data.assert_called_once()

    async def test_migrate_from_ipfs_no_cid(self, data_migration, mock_ipfs_client):
        """测试从IPFS迁移（无CID）"""
        # 设置模拟
        data_migration.session.ipfs_client = mock_ipfs_client
        mock_ipfs_client.get_user_cid.return_value = None

        # 执行迁移
        result = await data_migration.migrate_from_ipfs(force=True, verify=False)

        # 验证结果（新用户，无数据可迁移）
        assert result.success
        assert result.items_imported == 0

    async def test_migrate_from_ipfs_with_progress_callback(
        self,
        data_migration,
        mock_ipfs_client,
        sample_profile,
        sample_knowledge
    ):
        """测试从IPFS迁移（带进度回调）"""
        # 设置模拟
        data_migration.session.ipfs_client = mock_ipfs_client
        mock_ipfs_client.get_user_cid.return_value = "QmTestCID"
        mock_ipfs_client.download_user_data.return_value = {
            "version": "1.0",
            "wallet_address": data_migration.session.wallet_address,
            "profile": sample_profile,
            "knowledge": sample_knowledge
        }

        # 添加进度回调
        progress_updates = []

        def on_progress(progress):
            progress_updates.append({
                "stage": progress.stage,
                "percentage": progress.percentage,
                "message": progress.message
            })

        data_migration.add_progress_callback(on_progress)

        # 模拟数据库检查返回False（无本地数据）
        async def mock_has_local():
            return False
        data_migration._has_local_data = mock_has_local

        # 执行迁移
        result = await data_migration.migrate_from_ipfs(force=True, verify=False)

        # 验证进度回调被调用
        assert len(progress_updates) > 0
        stages = [u["stage"] for u in progress_updates]
        assert "fetching_cid" in stages
        assert "downloading" in stages

    async def test_migrate_from_ipfs_skip_existing_data(
        self,
        data_migration
    ):
        """测试从IPFS迁移（跳过已有数据）"""
        # 模拟数据库检查返回True（有本地数据）
        async def mock_has_local():
            return True
        data_migration._has_local_data = mock_has_local

        # 执行迁移（不强制）
        result = await data_migration.migrate_from_ipfs(force=False, verify=False)

        # 验证结果（跳过迁移）
        assert result.success
        assert result.items_imported == 0

    async def test_verify_migration_success(
        self,
        data_migration,
        mock_user_database,
        mock_ipfs_client
    ):
        """测试迁移验证（成功）"""
        # 设置模拟
        data_migration.session.db = mock_user_database
        data_migration.session.ipfs_client = mock_ipfs_client
        data_migration.session._ipfs_cid = "QmTestCID"

        profile_time = time.time()
        mock_user_database.get_profile.return_value = {
            "last_updated": profile_time
        }
        mock_ipfs_client.download_user_data.return_value = {
            "profile": {"last_updated": profile_time}
        }

        # 执行验证
        result = await data_migration.verify_migration()

        # 验证结果
        assert result is True

    async def test_verify_migration_no_cid(self, data_migration):
        """测试迁移验证（无CID）"""
        data_migration.session._ipfs_cid = None

        result = await data_migration.verify_migration()

        assert result is False

    async def test_verify_migration_timestamp_mismatch(
        self,
        data_migration,
        mock_user_database,
        mock_ipfs_client
    ):
        """测试迁移验证（时间戳不匹配但通过）"""
        # 设置模拟
        data_migration.session.db = mock_user_database
        data_migration.session.ipfs_client = mock_ipfs_client
        data_migration.session._ipfs_cid = "QmTestCID"

        # IPFS数据较旧
        ipfs_time = time.time() - 1000
        local_time = time.time()
        mock_user_database.get_profile.return_value = {
            "last_updated": local_time
        }
        mock_ipfs_client.download_user_data.return_value = {
            "profile": {"last_updated": ipfs_time}
        }

        # 执行验证
        result = await data_migration.verify_migration()

        # 验证结果（本地更新，应该通过）
        assert result is True

    async def test_migration_data_version_check(
        self,
        data_migration,
        mock_ipfs_client
    ):
        """测试迁移数据版本检查"""
        # 设置模拟
        data_migration.session.ipfs_client = mock_ipfs_client
        mock_ipfs_client.get_user_cid.return_value = "QmTestCID"
        mock_ipfs_client.download_user_data.return_value = {
            # 无版本信息的旧数据
            "wallet_address": data_migration.session.wallet_address,
            "profile": {},
            "knowledge": {}
        }

        # 模拟数据库检查返回False（无本地数据）
        async def mock_has_local():
            return False
        data_migration._has_local_data = mock_has_local

        # 执行迁移
        result = await data_migration.migrate_from_ipfs(force=True, verify=False)

        # 验证结果（应该能处理无版本数据）
        assert result.success


# ============================================================================
# TestMigrationResult
# ============================================================================

class TestMigrationResult:
    """MigrationResult 单元测试"""

    def test_result_initialization_success(self):
        """测试结果初始化（成功）"""
        result = MigrationResult(success=True)

        assert result.success is True
        assert result.cid is None
        assert result.items_imported == 0
        assert result.items_exported == 0
        assert result.bytes_transferred == 0
        assert result.error is None
        assert result.verification_passed is False

    def test_result_initialization_with_all_fields(self):
        """测试结果初始化（所有字段）"""
        result = MigrationResult(
            success=True,
            cid="QmTestCID",
            items_imported=5,
            items_exported=3,
            bytes_transferred=1024,
            error=None,
            verification_passed=True
        )

        assert result.success is True
        assert result.cid == "QmTestCID"
        assert result.items_imported == 5
        assert result.items_exported == 3
        assert result.bytes_transferred == 1024
        assert result.verification_passed is True

    def test_result_initialization_failure(self):
        """测试结果初始化（失败）"""
        result = MigrationResult(
            success=False,
            error="Network error"
        )

        assert result.success is False
        assert result.error == "Network error"


# ============================================================================
# TestEncryptionIntegration
# ============================================================================

@pytest.mark.asyncio
class TestEncryptionIntegration:
    """加密迁移集成测试"""

    async def test_export_with_encryption(
        self,
        data_migration,
        mock_user_database,
        mock_ipfs_client
    ):
        """测试加密导出"""
        # 设置模拟
        data_migration.session.db = mock_user_database
        data_migration.session.ipfs_client = mock_ipfs_client

        from usmsb_sdk.platform.external.meta_agent.ipfs.ipfs_client import IPFSUploadResult
        mock_ipfs_client.upload_user_data.return_value = IPFSUploadResult(
            success=True,
            cid="QmEncrypted",
            size=512
        )

        # 执行导出
        result = await data_migration.export_to_ipfs(verify=False)

        # 验证结果
        assert result.success
        assert result.cid == "QmEncrypted"

        # 验证上传时使用了加密
        mock_ipfs_client.upload_user_data.assert_called_once()
        call_args = mock_ipfs_client.upload_user_data.call_args
        assert call_args[1]["encrypt"] is True

    async def test_download_with_decryption(
        self,
        data_migration,
        mock_ipfs_client
    ):
        """测试解密下载"""
        # 设置模拟
        data_migration.session.ipfs_client = mock_ipfs_client
        mock_ipfs_client.get_user_cid.return_value = "QmEncrypted"
        mock_ipfs_client.download_user_data.return_value = {
            "version": "1.0",
            "wallet_address": data_migration.session.wallet_address,
            "profile": {}
        }

        # 执行迁移
        result = await data_migration.migrate_from_ipfs(force=True, verify=False)

        # 验证结果
        assert result.success

        # 验证下载时使用了解密
        mock_ipfs_client.download_user_data.assert_called_once()
        call_args = mock_ipfs_client.download_user_data.call_args
        assert call_args[1]["decrypt"] is True
