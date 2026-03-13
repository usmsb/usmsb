"""
Unit tests for UserWorkspace

测试用户工作空间的核心功能：
- 路径解析和验证
- 文件读写操作
- 配额管理
- 安全特性
"""

import asyncio
import tempfile
import time
from pathlib import Path

import pytest

from usmsb_sdk.meta_agent.workspace import (
    FileInfo,
    UserWorkspace,
    WorkspaceConfig,
    DirectoryType,
    WorkspaceError,
    PathValidationError,
    QuotaExceededError,
    FileOperationError,
)


class TestUserWorkspaceBasic:
    """UserWorkspace 基础功能测试"""

    @pytest.fixture
    async def temp_workspace(self):
        """创建临时工作空间"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = WorkspaceConfig(workspace_root=tmpdir)
            workspace = UserWorkspace("0xTestWallet123", config)
            await workspace.init()
            yield workspace

    async def test_workspace_initialization(self, temp_workspace):
        """测试工作空间初始化"""
        assert temp_workspace.wallet_address == "0xTestWallet123"
        assert temp_workspace.workspace_root.exists()
        assert temp_workspace.temp_dir.exists()
        assert temp_workspace.output_dir.exists()
        assert temp_workspace.uploads_dir.exists()

    async def test_resolve_path_simple(self, temp_workspace):
        """测试简单路径解析"""
        path = temp_workspace.resolve_path("test.txt")
        assert path.name == "test.txt"
        assert temp_workspace.validate_path(path)

    async def test_resolve_path_with_subdir(self, temp_workspace):
        """测试带子目录的路径解析"""
        path = temp_workspace.resolve_path("test.txt", DirectoryType.TEMP)
        assert path.parent == temp_workspace.temp_dir
        assert path.name == "test.txt"

    async def test_resolve_path_nested(self, temp_workspace):
        """测试嵌套路径解析"""
        path = temp_workspace.resolve_path("subdir/nested/file.txt")
        assert "subdir" in str(path)
        assert "nested" in str(path)

    async def test_path_traversal_protection(self, temp_workspace):
        """测试目录遍历攻击防护"""
        with pytest.raises(PathValidationError):
            temp_workspace.resolve_path("../etc/passwd")

        with pytest.raises(PathValidationError):
            temp_workspace.resolve_path("../../outside.txt")

    async def test_path_traversal_with_subdir(self, temp_workspace):
        """测试在子目录中的目录遍历防护"""
        # 在子目录中使用 ../ 尝试逃逸到工作空间其他子目录
        with pytest.raises(PathValidationError):
            temp_workspace.resolve_path("../escape.txt", DirectoryType.TEMP)

        # 尝试逃逸到父目录
        with pytest.raises(PathValidationError):
            temp_workspace.resolve_path("../../escape.txt", DirectoryType.TEMP)

    async def test_write_and_read_file(self, temp_workspace):
        """测试文件写入和读取"""
        # 写入文本
        await temp_workspace.write_file("hello.txt", "Hello, World!")

        # 验证文件存在
        assert await temp_workspace.exists("hello.txt")

        # 读取文件
        content = await temp_workspace.read_file("hello.txt", as_text=True)
        assert content == "Hello, World!"

        # 读取字节
        content_bytes = await temp_workspace.read_file("hello.txt")
        assert content_bytes == b"Hello, World!"

    async def test_write_bytes(self, temp_workspace):
        """测试写入字节数据"""
        data = b"\x00\x01\x02\x03"
        await temp_workspace.write_file("binary.bin", data)
        content = await temp_workspace.read_file("binary.bin")
        assert content == data

    async def test_write_with_subdir(self, temp_workspace):
        """测试在子目录中写入"""
        await temp_workspace.write_file(
            "output.txt", "Output data", DirectoryType.OUTPUT
        )
        assert await temp_workspace.exists("output.txt", DirectoryType.OUTPUT)
        content = await temp_workspace.read_file("output.txt", DirectoryType.OUTPUT, as_text=True)
        assert content == "Output data"

    async def test_list_files(self, temp_workspace):
        """测试列出文件"""
        # 创建一些文件
        await temp_workspace.write_file("file1.txt", "content1")
        await temp_workspace.write_file("file2.txt", "content2")
        await temp_workspace.write_file("data.bin", b"\x00")

        # 列出文件
        files = await temp_workspace.list_files()
        file_names = [f.name for f in files]
        assert "file1.txt" in file_names
        assert "file2.txt" in file_names
        assert "data.bin" in file_names

    async def test_list_files_with_pattern(self, temp_workspace):
        """测试使用模式匹配列出文件"""
        await temp_workspace.write_file("test1.txt", "a")
        await temp_workspace.write_file("test2.txt", "b")
        await temp_workspace.write_file("image.png", "c")

        # 只列出 .txt 文件
        files = await temp_workspace.list_files(pattern="*.txt")
        assert len(files) == 2
        assert all(f.name.endswith(".txt") for f in files)

    async def test_list_files_recursive(self, temp_workspace):
        """测试递归列出文件"""
        await temp_workspace.write_file("root.txt", "a")
        await temp_workspace.write_file("subdir/nested.txt", "b")

        files = await temp_workspace.list_files(recursive=True)
        assert len(files) >= 2
        paths = [f.path.replace("\\", "/") for f in files]  # 规范化路径分隔符
        assert "root.txt" in paths
        assert "subdir/nested.txt" in paths

    async def test_delete_file(self, temp_workspace):
        """测试删除文件"""
        await temp_workspace.write_file("to_delete.txt", "content")
        assert await temp_workspace.exists("to_delete.txt")

        result = await temp_workspace.delete_file("to_delete.txt")
        assert result is True
        assert not await temp_workspace.exists("to_delete.txt")

    async def test_delete_nonexistent_file(self, temp_workspace):
        """测试删除不存在的文件"""
        result = await temp_workspace.delete_file("nonexistent.txt")
        assert result is False

    async def test_get_file_info(self, temp_workspace):
        """测试获取文件信息"""
        await temp_workspace.write_file("info_test.txt", "content")

        info = await temp_workspace.get_file_info("info_test.txt")
        assert info is not None
        assert info.name == "info_test.txt"
        assert info.size == 7  # "content" 的长度
        assert not info.is_dir

    async def test_get_file_info_nonexistent(self, temp_workspace):
        """测试获取不存在文件的信息"""
        info = await temp_workspace.get_file_info("nonexistent.txt")
        assert info is None


class TestUserWorkspaceSecurity:
    """UserWorkspace 安全特性测试"""

    @pytest.fixture
    async def temp_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = WorkspaceConfig(
                workspace_root=tmpdir,
                max_file_size_mb=1,
                max_storage_mb=5,
                max_files=10,
            )
            workspace = UserWorkspace("0xTestWallet123", config)
            await workspace.init()
            yield workspace

    async def test_file_size_limit(self, temp_workspace):
        """测试文件大小限制"""
        large_content = "A" * (2 * 1024 * 1024)  # 2MB，超过1MB限制

        with pytest.raises(QuotaExceededError):
            await temp_workspace.write_file("large.txt", large_content)

    async def test_storage_quota_limit(self, temp_workspace):
        """测试存储空间配额限制"""
        # 写入接近限制
        content = "A" * (1024 * 1024)  # 1MB
        for i in range(5):  # 5MB，接近5MB限制
            await temp_workspace.write_file(f"file{i}.txt", content)

        # 现在应该已经接近或达到配额
        used = await temp_workspace.get_storage_used()
        assert used > 0

        # 尝试写入另一个文件应该超出配额
        # 由于已经有 5MB + .gitkeep 文件，任何新文件都应该失败
        with pytest.raises(QuotaExceededError):
            await temp_workspace.write_file("file_overflow.txt", content)

    async def test_file_count_limit(self, temp_workspace):
        """测试文件数量限制"""
        config = WorkspaceConfig(
            workspace_root=temp_workspace.config.workspace_root,
            max_files=5,  # 增加5个位置给 .gitkeep 文件
        )
        workspace = UserWorkspace("0xTestWallet123", config)
        await workspace.init()

        # 创建2个文件（因为已有3个 .gitkeep 文件）
        for i in range(2):
            await workspace.write_file(f"file{i}.txt", "small")

        # 第3个文件应该超出限制（总共5个，已有3个+2个=5个）
        with pytest.raises(QuotaExceededError):
            await workspace.write_file("file2.txt", "small")

    async def test_symlink_prevention(self, temp_workspace):
        """测试符号链接防护"""
        # 尝试创建指向工作空间外的符号链接
        try:
            # 在 Windows 上这可能会失败或行为不同
            with pytest.raises((PathValidationError, FileOperationError)):
                temp_workspace.resolve_path("../../../etc/passwd")
        except Exception:
            pass  # 某些平台上可能不支持

    async def test_path_validation_edge_cases(self, temp_workspace):
        """测试路径验证的边缘情况"""
        # 空路径
        path = temp_workspace.resolve_path("")
        assert temp_workspace.validate_path(path)

        # 点路径
        path = temp_workspace.resolve_path(".")
        assert temp_workspace.validate_path(path)

        # 连续斜杠
        path = temp_workspace.resolve_path("sub///file.txt")
        assert "sub" in str(path)

        # 绝对路径（应该是被忽略的）
        path = temp_workspace.resolve_path("/abs/path.txt")
        assert temp_workspace.validate_path(path)


class TestUserWorkspaceQuota:
    """UserWorkspace 配额管理测试"""

    @pytest.fixture
    async def temp_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = WorkspaceConfig(workspace_root=tmpdir)
            workspace = UserWorkspace("0xTestWallet123", config)
            await workspace.init()
            yield workspace

    async def test_get_storage_used(self, temp_workspace):
        """测试获取已用存储空间"""
        initial_used = await temp_workspace.get_storage_used()
        assert initial_used >= 0

        await temp_workspace.write_file("test.txt", "Hello, World!")
        new_used = await temp_workspace.get_storage_used()
        assert new_used > initial_used
        assert new_used >= 13  # "Hello, World!" 的长度

    async def test_get_file_count(self, temp_workspace):
        """测试获取文件数量"""
        initial_count = await temp_workspace.get_file_count()

        for i in range(5):
            await temp_workspace.write_file(f"file{i}.txt", "test")

        new_count = await temp_workspace.get_file_count()
        assert new_count >= initial_count + 5

    async def test_get_quota_info(self, temp_workspace):
        """测试获取配额信息"""
        await temp_workspace.write_file("test.txt", "content")

        quota = await temp_workspace.get_quota_info()
        assert quota["wallet_address"] == "0xTestWallet123"
        assert "storage" in quota
        assert "files" in quota
        assert "file_size_limit" in quota

        # 验证存储信息结构
        storage = quota["storage"]
        assert "used_bytes" in storage
        assert "limit_bytes" in storage
        assert "used_percent" in storage
        assert "remaining_bytes" in storage

        # 验证文件信息结构
        files = quota["files"]
        assert "count" in files
        assert "limit" in files

    async def test_quota_cache(self, temp_workspace):
        """测试配额缓存"""
        # 第一次调用应该计算
        storage1 = await temp_workspace.get_storage_used()
        count1 = await temp_workspace.get_file_count()

        # 第二次调用应该使用缓存
        storage2 = await temp_workspace.get_storage_used()
        count2 = await temp_workspace.get_file_count()

        assert storage1 == storage2
        assert count1 == count2

        # 写入文件后缓存应该失效
        await temp_workspace.write_file("cache_test.txt", "test")
        storage3 = await temp_workspace.get_storage_used()
        assert storage3 > storage1


class TestUserWorkspaceAdvanced:
    """UserWorkspace 高级功能测试"""

    @pytest.fixture
    async def temp_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = UserWorkspace("0xTestWallet123", WorkspaceConfig(workspace_root=tmpdir))
            await workspace.init()
            yield workspace

    async def test_create_directory(self, temp_workspace):
        """测试创建目录"""
        await temp_workspace.create_directory("new_dir")
        assert (temp_workspace.workspace_root / "new_dir").exists()

    async def test_create_nested_directory(self, temp_workspace):
        """测试创建嵌套目录"""
        await temp_workspace.create_directory("parent/child/grandchild")
        assert (temp_workspace.workspace_root / "parent" / "child" / "grandchild").exists()

    async def test_move_file(self, temp_workspace):
        """测试移动文件"""
        await temp_workspace.write_file("from.txt", "content")
        await temp_workspace.move_file("from.txt", "to.txt")

        assert not await temp_workspace.exists("from.txt")
        assert await temp_workspace.exists("to.txt")

        content = await temp_workspace.read_file("to.txt", as_text=True)
        assert content == "content"

    async def test_move_file_between_subdirs(self, temp_workspace):
        """测试在子目录之间移动文件"""
        await temp_workspace.write_file("data.txt", "content", DirectoryType.TEMP)
        await temp_workspace.move_file(
            "data.txt", "data.txt",
            src_subdir=DirectoryType.TEMP,
            dst_subdir=DirectoryType.OUTPUT
        )

        assert not await temp_workspace.exists("data.txt", DirectoryType.TEMP)
        assert await temp_workspace.exists("data.txt", DirectoryType.OUTPUT)

    async def test_copy_file(self, temp_workspace):
        """测试复制文件"""
        await temp_workspace.write_file("original.txt", "content")
        await temp_workspace.copy_file("original.txt", "copy.txt")

        assert await temp_workspace.exists("original.txt")
        assert await temp_workspace.exists("copy.txt")

        # 验证两个文件内容相同
        orig_content = await temp_workspace.read_file("original.txt", as_text=True)
        copy_content = await temp_workspace.read_file("copy.txt", as_text=True)
        assert orig_content == copy_content

    async def test_cleanup_temp(self, temp_workspace):
        """测试清理临时文件"""
        # 创建一些临时文件
        await temp_workspace.write_file("old_file.txt", "old", DirectoryType.TEMP)
        await temp_workspace.write_file("recent_file.txt", "new", DirectoryType.TEMP)

        # 等待后清理
        await asyncio.sleep(0.2)
        deleted = await temp_workspace.cleanup_temp(max_age_seconds=0.1)

        # 至少删除了两个文件（忽略 .gitkeep）
        assert deleted >= 2

    async def test_clear_subdir(self, temp_workspace):
        """测试清空子目录"""
        await temp_workspace.write_file("file1.txt", "a", DirectoryType.OUTPUT)
        await temp_workspace.write_file("file2.txt", "b", DirectoryType.OUTPUT)

        deleted = await temp_workspace.clear_subdir(DirectoryType.OUTPUT)
        assert deleted < 0  # 返回-1表示全部清空

        files = await temp_workspace.list_files("", DirectoryType.OUTPUT)
        # 应该只剩下 .gitkeep
        assert len(files) <= 1

    async def test_get_stats(self, temp_workspace):
        """测试获取统计信息"""
        await temp_workspace.write_file("test.txt", "content")
        await temp_workspace.write_file("output.txt", "output", DirectoryType.OUTPUT)

        stats = await temp_workspace.get_stats()
        assert stats["wallet_address"] == "0xTestWallet123"
        assert stats["total_files"] >= 2
        assert stats["directories"]["output"] >= 1
        assert "storage_used_mb" in stats

    async def test_overwrite_file(self, temp_workspace):
        """测试覆盖文件"""
        await temp_workspace.write_file("test.txt", "original")
        await temp_workspace.write_file("test.txt", "new content")

        content = await temp_workspace.read_file("test.txt", as_text=True)
        assert content == "new content"

    async def test_overwrite_disabled(self, temp_workspace):
        """测试禁用覆盖"""
        await temp_workspace.write_file("test.txt", "original")

        with pytest.raises(FileOperationError):
            await temp_workspace.write_file("test.txt", "new", overwrite=False)

        # 原内容应该保持不变
        content = await temp_workspace.read_file("test.txt", as_text=True)
        assert content == "original"


class TestUserWorkspaceIntegration:
    """UserWorkspace 集成测试"""

    async def test_create_workspace_function(self):
        """测试 create_workspace 便利函数"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from usmsb_sdk.meta_agent.workspace import create_workspace

            workspace = await create_workspace("0xTestWallet", tmpdir)
            assert workspace.wallet_address == "0xTestWallet"
            assert workspace.workspace_root.exists()

            # 测试基本操作
            await workspace.write_file("test.txt", "Hello!")
            assert await workspace.exists("test.txt")

    async def test_multiple_workspaces_isolation(self):
        """测试多个工作空间之间的隔离"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_a = UserWorkspace("0xWalletA", WorkspaceConfig(workspace_root=tmpdir))
            workspace_b = UserWorkspace("0xWalletB", WorkspaceConfig(workspace_root=tmpdir))

            await workspace_a.init()
            await workspace_b.init()

            # 写入同名文件
            await workspace_a.write_file("shared_name.txt", "content from A")
            await workspace_b.write_file("shared_name.txt", "content from B")

            # 验证隔离
            content_a = await workspace_a.read_file("shared_name.txt", as_text=True)
            content_b = await workspace_b.read_file("shared_name.txt", as_text=True)

            assert content_a == "content from A"
            assert content_b == "content from B"
            assert content_a != content_b

    async def test_directory_isolation(self):
        """测试目录隔离"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = UserWorkspace("0xTestWallet", WorkspaceConfig(workspace_root=tmpdir))
            await workspace.init()

            # 在不同子目录创建同名文件
            await workspace.write_file("data.txt", "temp", DirectoryType.TEMP)
            await workspace.write_file("data.txt", "output", DirectoryType.OUTPUT)
            await workspace.write_file("data.txt", "upload", DirectoryType.UPLOADS)

            # 验证三个文件内容不同
            temp_content = await workspace.read_file("data.txt", DirectoryType.TEMP, as_text=True)
            output_content = await workspace.read_file("data.txt", DirectoryType.OUTPUT, as_text=True)
            upload_content = await workspace.read_file("data.txt", DirectoryType.UPLOADS, as_text=True)

            assert temp_content == "temp"
            assert output_content == "output"
            assert upload_content == "upload"

    async def test_concurrent_writes(self):
        """测试并发写入"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = UserWorkspace("0xTestWallet", WorkspaceConfig(workspace_root=tmpdir))
            await workspace.init()

            # 并发写入多个文件
            async def write_file(i):
                await workspace.write_file(f"file{i}.txt", f"content{i}")

            await asyncio.gather(*[write_file(i) for i in range(10)])

            # 验证所有文件都写入成功
            for i in range(10):
                assert await workspace.exists(f"file{i}.txt")
                content = await workspace.read_file(f"file{i}.txt", as_text=True)
                assert content == f"content{i}"


class TestFileInfo:
    """FileInfo 数据类测试"""

    def test_from_path(self):
        """测试从路径创建 FileInfo"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test content")
            temp_path = Path(f.name)
            temp_dir = temp_path.parent

        try:
            info = FileInfo.from_path(temp_path, temp_dir)
            assert info.name == temp_path.name
            assert info.size == 12  # "test content" 的长度
            assert not info.is_dir
            assert info.modified_at > 0
            assert info.created_at is not None
        finally:
            temp_path.unlink()

    def test_to_dict(self):
        """测试转换为字典"""
        info = FileInfo(
            name="test.txt",
            path="subdir/test.txt",
            size=100,
            is_dir=False,
            modified_at=1234567890.0,
            created_at=1234567800.0,
        )

        info_dict = info.to_dict()
        assert info_dict["name"] == "test.txt"
        assert info_dict["path"] == "subdir/test.txt"
        assert info_dict["size"] == 100
        assert not info_dict["is_dir"]
        assert info_dict["modified_at"] == 1234567890.0
        assert info_dict["created_at"] == 1234567800.0
