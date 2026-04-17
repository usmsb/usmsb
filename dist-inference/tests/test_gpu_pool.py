"""
Unit tests for GPU Pool
"""

import pytest
import asyncio
from global_scheduler.gpu_pool import GPUPool, NodeExecutor
from global_scheduler.model_registry import ModelRegistry
from shared.types import NodeCapability, NodeStatus, GPUInfo


class TestGPUPool:
    """Test cases for GPUPool"""

    def setup_method(self):
        """Setup for each test method"""
        self.pool = GPUPool()
        self.model_registry = ModelRegistry()

    def create_test_node(
        self,
        node_id: str = "test_node_1",
        gpu_count: int = 4,
        vram_per_gpu: int = 40,
        status: NodeStatus = NodeStatus.IDLE,
        loaded_models: list = None
    ) -> NodeCapability:
        """Helper to create a test node"""
        total_vram = gpu_count * vram_per_gpu
        return NodeCapability(
            node_id=node_id,
            hostname=f"host_{node_id}",
            port=8080,
            status=status,
            gpu_count=gpu_count,
            gpus=[
                GPUInfo(gpu_id=i, gpu_type="A100", vram_gb=vram_per_gpu)
                for i in range(gpu_count)
            ],
            total_vram_gb=total_vram,
            available_vram_gb=total_vram,
            loaded_models=loaded_models or []
        )

    @pytest.mark.asyncio
    async def test_register_node(self):
        """Test node registration"""
        node = self.create_test_node()
        await self.pool.register_node(node)

        assert node.node_id in self.pool.nodes
        assert self.pool.nodes[node.node_id].gpu_count == 4

    @pytest.mark.asyncio
    async def test_heartbeat(self):
        """Test node heartbeat update"""
        node = self.create_test_node()
        await self.pool.register_node(node)

        # Send heartbeat
        await self.pool.heartbeat(
            node_id=node.node_id,
            status="busy",
            loaded_models=["Qwen/Qwen2.5-7B-Instruct"],
            gpu_utilization=[0.5, 0.6, 0.4, 0.3],
            available_vram_gb=100
        )

        updated_node = self.pool.nodes[node.node_id]
        assert updated_node.status == NodeStatus.BUSY
        assert updated_node.loaded_models == ["Qwen/Qwen2.5-7B-Instruct"]
        assert updated_node.available_vram_gb == 100

    @pytest.mark.asyncio
    async def test_select_node_no_nodes(self):
        """Test selecting a node when none available"""
        result = await self.pool.select_node("Qwen/Qwen2.5-7B-Instruct", self.model_registry)
        assert result is None

    @pytest.mark.asyncio
    async def test_select_node_unknown_model(self):
        """Test selecting a node for unknown model"""
        node = self.create_test_node()
        await self.pool.register_node(node)

        result = await self.pool.select_node("Unknown/Model", self.model_registry)
        assert result is not None

    @pytest.mark.asyncio
    async def test_select_node_with_model_match(self):
        """Test selecting a node that has the model loaded"""
        node = self.create_test_node(
            loaded_models=["Qwen/Qwen2.5-7B-Instruct"]
        )
        await self.pool.register_node(node)

        result = await self.pool.select_node("Qwen/Qwen2.5-7B-Instruct", self.model_registry)
        assert result is not None
        assert result[0].capability.node_id == node.node_id

    @pytest.mark.asyncio
    async def test_select_node_prefers_model_loaded(self):
        """Test that selecting a node prefers nodes with model already loaded"""
        # Node without model
        node1 = self.create_test_node(node_id="node_no_model", loaded_models=[])
        await self.pool.register_node(node1)

        # Node with model
        node2 = self.create_test_node(node_id="node_with_model", loaded_models=["Qwen/Qwen2.5-7B-Instruct"])
        await self.pool.register_node(node2)

        result = await self.pool.select_node("Qwen/Qwen2.5-7B-Instruct", self.model_registry)
        assert result is not None
        assert result[0].capability.node_id == "node_with_model"

    @pytest.mark.asyncio
    async def test_select_node_insufficient_vram(self):
        """Test selecting a node with insufficient VRAM"""
        # Create a small VRAM node
        node = self.create_test_node(gpu_count=1, vram_per_gpu=8)  # Only 8GB
        await self.pool.register_node(node)

        # Qwen2.5-14B needs 28GB
        result = await self.pool.select_node("Qwen/Qwen2.5-14B-Instruct", self.model_registry)
        assert result is None

    @pytest.mark.asyncio
    async def test_select_node_busy_node_excluded(self):
        """Test that busy nodes are not selected"""
        node = self.create_test_node(status=NodeStatus.BUSY)
        await self.pool.register_node(node)

        result = await self.pool.select_node("Qwen/Qwen2.5-7B-Instruct", self.model_registry)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_summary(self):
        """Test getting pool summary"""
        node1 = self.create_test_node(node_id="node1", status=NodeStatus.IDLE)
        node2 = self.create_test_node(node_id="node2", status=NodeStatus.BUSY)
        node3 = self.create_test_node(node_id="node3", status=NodeStatus.IDLE)

        await self.pool.register_node(node1)
        await self.pool.register_node(node2)
        await self.pool.register_node(node3)

        summary = self.pool.get_summary()
        assert summary["total_nodes"] == 3
        assert summary["idle_nodes"] == 2
        assert summary["busy_nodes"] == 1
        assert summary["offline_nodes"] == 0

    @pytest.mark.asyncio
    async def test_get_all_nodes(self):
        """Test getting all nodes"""
        node1 = self.create_test_node(node_id="node1")
        node2 = self.create_test_node(node_id="node2")
        await self.pool.register_node(node1)
        await self.pool.register_node(node2)

        nodes = self.pool.get_all_nodes()
        assert len(nodes) == 2


class TestNodeExecutor:
    """Test cases for NodeExecutor (mock only)"""

    def setup_method(self):
        """Setup for each test method"""
        self.pool = GPUPool()
        node = NodeCapability(
            node_id="test_node",
            hostname="localhost",
            port=8080,
            status=NodeStatus.IDLE,
            gpu_count=4,
            total_vram_gb=160,
            available_vram_gb=160
        )
        self.executor = NodeExecutor(node, self.pool)

    def test_executor_init(self):
        """Test executor initialization"""
        assert self.executor.capability.node_id == "test_node"
        assert self.executor.base_url == "http://localhost:8080"

    @pytest.mark.asyncio
    async def test_set_busy(self):
        """Test marking node as busy"""
        await self.executor.set_busy()
        assert self.executor.capability.status == NodeStatus.BUSY

    @pytest.mark.asyncio
    async def test_set_idle(self):
        """Test marking node as idle"""
        self.executor.capability.status = NodeStatus.BUSY
        await self.executor.set_idle()
        assert self.executor.capability.status == NodeStatus.IDLE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
