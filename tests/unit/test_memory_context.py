"""
Memory Context Manager 完整测试

测试上下文记忆管理器的核心功能：
1. 添加消息
2. 获取上下文
3. 保存/加载
4. 多会话管理
5. 边界情况
"""

import asyncio
import os
import sys
import tempfile
import pytest
from unittest.mock import MagicMock

# 直接从文件加载，跳过 __init__.py 的重量级导入
sys.path.insert(0, '/Users/gujun/vibecode/usmsb/src')
import importlib.util
spec = importlib.util.spec_from_file_location(
    "context",
    "/Users/gujun/vibecode/usmsb/src/usmsb_sdk/meta_agent/memory/context.py"
)
context_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(context_module)
ContextManager = context_module.ContextManager


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def context_manager(db_path):
    return ContextManager(db_path=db_path)


# =============================================================================
# Test: 初始化 (Initialization)
# =============================================================================

class TestContextInit:
    """测试 ContextManager 初始化"""

    def test_init_creates_instance(self, context_manager, db_path):
        """初始化创建实例"""
        assert context_manager is not None
        assert context_manager.db_path == db_path

    @pytest.mark.asyncio
    async def test_init_db(self, context_manager):
        """初始化数据库"""
        await context_manager.init()
        assert os.path.exists(context_manager.db_path)


# =============================================================================
# Test: 添加消息 (Adding Messages)
# =============================================================================

class TestAddingMessages:
    """测试添加消息"""

    @pytest.mark.asyncio
    async def test_add_user_message(self, context_manager):
        """添加用户消息"""
        await context_manager.init()
        await context_manager.add_message("conv-1", "user", "你好")
        context = await context_manager.get_context("conv-1")
        assert len(context) >= 1

    @pytest.mark.asyncio
    async def test_add_assistant_message(self, context_manager):
        """添加助手消息"""
        await context_manager.init()
        await context_manager.add_message("conv-1", "assistant", "有什么可以帮你")
        context = await context_manager.get_context("conv-1")
        assert len(context) >= 1

    @pytest.mark.asyncio
    async def test_add_multiple_messages(self, context_manager):
        """添加多条消息"""
        await context_manager.init()
        for i in range(5):
            await context_manager.add_message("conv-1", "user", f"消息{i}")
        context = await context_manager.get_context("conv-1")
        assert len(context) >= 5


# =============================================================================
# Test: 获取上下文 (Getting Context)
# =============================================================================

class TestGettingContext:
    """测试获取上下文"""

    @pytest.mark.asyncio
    async def test_get_context_empty(self, context_manager):
        """获取空会话上下文"""
        await context_manager.init()
        context = await context_manager.get_context("nonexistent-conv")
        assert context == []

    @pytest.mark.asyncio
    async def test_get_context_with_limit(self, context_manager):
        """限制返回数量"""
        await context_manager.init()
        for i in range(10):
            await context_manager.add_message("conv-1", "user", f"消息{i}")
        context = await context_manager.get_context("conv-1", limit=3)
        assert len(context) <= 3

    @pytest.mark.asyncio
    async def test_get_context_different_conversations(self, context_manager):
        """不同会话的上下文隔离"""
        await context_manager.init()
        await context_manager.add_message("conv-1", "user", "会话1的消息")
        await context_manager.add_message("conv-2", "user", "会话2的消息")
        ctx1 = await context_manager.get_context("conv-1")
        ctx2 = await context_manager.get_context("conv-2")
        # 两个会话应该有不同的消息
        assert ctx1 != ctx2


# =============================================================================
# Test: 保存 (Saving)
# =============================================================================

class TestSaving:
    """测试保存功能"""

    @pytest.mark.asyncio
    async def test_save_does_not_crash(self, context_manager):
        """保存不崩溃"""
        await context_manager.init()
        await context_manager.add_message("conv-1", "user", "测试")
        await context_manager.save()  # 不崩溃


# =============================================================================
# Test: 边界情况 (Edge Cases)
# =============================================================================

class TestMemoryContextEdgeCases:
    """测试边界情况"""

    @pytest.mark.asyncio
    async def test_very_long_message(self, context_manager):
        """超长消息"""
        await context_manager.init()
        long_msg = "消息内容 " * 1000
        await context_manager.add_message("conv-1", "user", long_msg)
        context = await context_manager.get_context("conv-1")
        assert len(context) >= 1

    @pytest.mark.asyncio
    async def test_special_characters(self, context_manager):
        """特殊字符"""
        await context_manager.init()
        await context_manager.add_message("conv-1", "user", "!@#$%^&*()")
        context = await context_manager.get_context("conv-1")
        assert len(context) >= 1

    @pytest.mark.asyncio
    async def test_empty_message(self, context_manager):
        """空消息"""
        await context_manager.init()
        await context_manager.add_message("conv-1", "user", "")
        context = await context_manager.get_context("conv-1")
        assert len(context) >= 1

    @pytest.mark.asyncio
    async def test_concurrent_messages(self, context_manager):
        """并发添加消息"""
        await context_manager.init()
        tasks = [
            context_manager.add_message("conv-1", "user", f"并发消息{i}")
            for i in range(10)
        ]
        await asyncio.gather(*tasks)
        context = await context_manager.get_context("conv-1")
        assert len(context) >= 10
