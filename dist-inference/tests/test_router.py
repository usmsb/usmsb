"""
Unit tests for Router
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from global_scheduler.router import Router
from global_scheduler.gpu_pool import GPUPool, NodeExecutor
from global_scheduler.model_registry import ModelRegistry
from shared.types import NodeCapability, NodeStatus, GPUInfo, InferenceRequest, InferenceResponse


class TestRouter:
    """Test cases for Router"""

    def setup_method(self):
        """Setup for each test method"""
        self.gpu_pool = GPUPool()
        self.model_registry = ModelRegistry()
        self.router = Router(self.gpu_pool, self.model_registry)

    def create_test_request(self) -> InferenceRequest:
        """Helper to create a test request"""
        return InferenceRequest.create(
            model_name="Qwen/Qwen2.5-7B-Instruct",
            messages=[{"role": "user", "content": "Hello!"}]
        )

    @pytest.mark.asyncio
    async def test_execute_no_nodes_available(self):
        """Test execution when no nodes are available"""
        request = self.create_test_request()

        with pytest.raises(RuntimeError, match="No available GPU node"):
            await self.router.execute(request)

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful execution"""
        # Register a node
        node = NodeCapability(
            node_id="test_node",
            hostname="localhost",
            port=8080,
            status=NodeStatus.IDLE,
            gpu_count=4,
            gpus=[GPUInfo(gpu_id=i, gpu_type="A100", vram_gb=40) for i in range(4)],
            total_vram_gb=160,
            available_vram_gb=160,
            loaded_models=["Qwen/Qwen2.5-7B-Instruct"]
        )
        await self.gpu_pool.register_node(node)

        request = self.create_test_request()

        # Mock the node executor
        mock_response = InferenceResponse(
            request_id=request.request_id,
            model_name="Qwen/Qwen2.5-7B-Instruct",
            content="Hello! How can I help you?",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            gpu_seconds=0.5,
            cost_vibe=0.001,
            node_id="test_node"
        )

        # Patch the execute method
        with patch.object(NodeExecutor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = mock_response

            result = await self.router.execute(request)

            assert result.content == "Hello! How can I help you?"
            assert result.node_id == "test_node"

    @pytest.mark.asyncio
    async def test_execute_retry_on_failure(self):
        """Test that router retries on failure"""
        # Register a node
        node = NodeCapability(
            node_id="test_node",
            hostname="localhost",
            port=8080,
            status=NodeStatus.IDLE,
            gpu_count=4,
            gpus=[GPUInfo(gpu_id=i, gpu_type="A100", vram_gb=40) for i in range(4)],
            total_vram_gb=160,
            available_vram_gb=160
        )
        await self.gpu_pool.register_node(node)

        request = self.create_test_request()

        mock_response = InferenceResponse(
            request_id=request.request_id,
            model_name="Qwen/Qwen2.5-7B-Instruct",
            content="Success",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            gpu_seconds=0.1,
            cost_vibe=0.001,
            node_id="test_node"
        )

        call_count = 0

        async def mock_execute_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("Temporary failure")
            return mock_response

        with patch.object(NodeExecutor, 'execute', new_callable=AsyncMock, side_effect=mock_execute_failure):
            result = await self.router.execute(request)

            assert result.content == "Success"
            # Should have retried once and succeeded
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_execute_all_retries_fail(self):
        """Test execution when all retries fail"""
        # Register a node
        node = NodeCapability(
            node_id="test_node",
            hostname="localhost",
            port=8080,
            status=NodeStatus.IDLE,
            gpu_count=4,
            gpus=[GPUInfo(gpu_id=i, gpu_type="A100", vram_gb=40) for i in range(4)],
            total_vram_gb=160,
            available_vram_gb=160
        )
        await self.gpu_pool.register_node(node)

        request = self.create_test_request()

        async def mock_execute_always_fail(*args, **kwargs):
            raise RuntimeError("Always fails")

        with patch.object(NodeExecutor, 'execute', new_callable=AsyncMock, side_effect=mock_execute_always_fail):
            with pytest.raises(RuntimeError, match="All 3 attempts failed"):
                await self.router.execute(request)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
