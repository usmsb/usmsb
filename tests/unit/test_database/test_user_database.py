"""Unit tests for UserDatabase"""

import asyncio
import tempfile
from pathlib import Path
from datetime import datetime

import pytest

from src.usmsb_sdk.platform.external.meta_agent.database import (
    UserDatabase,
    Conversation,
    Message,
    UserProfile,
    ConversationSummary,
    ImportantMemory,
    KnowledgeItem,
    create_user_database,
)

@pytest.fixture
async def temp_db_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture
async def test_wallet():
    return "0x1234567890abcdef1234567890abcdef12345678"

@pytest.fixture
async def user_database(temp_db_dir, test_wallet):
    db = UserDatabase(test_wallet, temp_db_dir)
    await db.init()
    yield db
    await db.close()

class TestUserDatabase:
    """Test suite for UserDatabase"""

    async def test_init_database(self, user_database):
        assert user_database._initialized is True
        db_dir = user_database.db_dir
        assert (db_dir / "conversations.db").exists()

    async def test_create_conversation(self, user_database):
        conv = await user_database.create_conversation(context="Test context")
        assert conv.id is not None
        assert conv.status == "active"

    async def test_get_conversation(self, user_database):
        conv = await user_database.create_conversation()
        retrieved = await user_database.get_conversation(conv.id)
        assert retrieved.id == conv.id

    async def test_get_active_conversation(self, user_database):
        conv = await user_database.create_conversation()
        active = await user_database.get_active_conversation()
        assert active.id == conv.id

    async def test_add_message(self, user_database):
        conv = await user_database.create_conversation()
        msg = Message(id="m1", conversation_id=conv.id, role="user", content="Hello")
        await user_database.add_message(conv.id, msg)
        messages = await user_database.get_messages(conv.id)
        assert len(messages) == 1

    async def test_get_messages(self, user_database):
        conv = await user_database.create_conversation()
        for i in range(5):
            m = Message(id=f"m{i}", conversation_id=conv.id, role="user", content=f"Msg {i}")
            await user_database.add_message(conv.id, m)
        retrieved = await user_database.get_messages(conv.id)
        assert len(retrieved) == 5

    async def test_get_message_count(self, user_database):
        conv = await user_database.create_conversation()
        for i in range(3):
            m = Message(id=f"m{i}", conversation_id=conv.id, role="user", content=f"M{i}")
            await user_database.add_message(conv.id, m)
        count = await user_database.get_message_count(conv.id)
        assert count == 3

    async def test_update_conversation(self, user_database):
        conv = await user_database.create_conversation()
        result = await user_database.update_conversation(conv.id, status="ended")
        assert result is True
        updated = await user_database.get_conversation(conv.id)
        assert updated.status == "ended"

    async def test_update_profile(self, user_database):
        await user_database.update_profile({"preferences": {"lang": "en"}})
        profile = await user_database.get_profile()
        assert profile.preferences["lang"] == "en"

    async def test_add_memory(self, user_database):
        await user_database.add_memory({"content": "Test", "importance": 0.9})
        memories = await user_database.get_memories()
        assert len(memories) == 1

    async def test_add_knowledge(self, user_database):
        item = await user_database.add_knowledge({"content": "Test", "category": "test"})
        assert item.content == "Test"

    async def test_search_knowledge(self, user_database):
        await user_database.add_knowledge({"content": "Python is great", "category": "lang"})
        results = await user_database.search_knowledge("Python")
        assert len(results) >= 1

    async def test_delete_knowledge(self, user_database):
        item = await user_database.add_knowledge({"content": "Delete me"})
        result = await user_database.delete_knowledge(item.id)
        assert result is True

    async def test_export_data(self, user_database):
        conv = await user_database.create_conversation()
        await user_database.add_message(conv.id, Message(id="m1", conversation_id=conv.id, role="user", content="Hi"))
        await user_database.update_profile({"test": True})
        exported = await user_database.export_data()
        assert "conversations" in exported

    async def test_import_data(self, user_database):
        data = {"profile": {"user_id": user_database.wallet_address, "preferences": {"lang": "zh"}, "commitments": {}, "knowledge": {}, "last_updated": datetime.now().timestamp()}, "conversations": [], "memories": [], "knowledge": []}
        await user_database.import_data(data)
        profile = await user_database.get_profile()
        assert profile.preferences["lang"] == "zh"

    async def test_get_db_info(self, user_database):
        await user_database.create_conversation()
        info = await user_database.get_db_info()
        assert info["wallet_address"] == user_database.wallet_address

    async def test_close_database(self, user_database):
        assert user_database._initialized is True
        await user_database.close()
        assert user_database._initialized is False

class TestDatabaseIsolation:
    async def test_user_isolation(self, temp_db_dir):
        db1 = UserDatabase("0xaaa1", temp_db_dir)
        db2 = UserDatabase("0xbbb2", temp_db_dir)
        await db1.init()
        await db2.init()
        try:
            conv1 = await db1.create_conversation()
            conv2 = await db2.create_conversation()
            convs1 = await db1.get_all_conversations()
            convs2 = await db2.get_all_conversations()
            assert len(convs1) == 1
            assert len(convs2) == 1
        finally:
            await db1.close()
            await db2.close()
