"""
Unit tests for Model Registry
"""

import pytest
from global_scheduler.model_registry import ModelRegistry
from shared.types import ModelInfo, ModelType


class TestModelRegistry:
    """Test cases for ModelRegistry"""

    def setup_method(self):
        """Setup for each test method"""
        self.registry = ModelRegistry()

    def test_get_existing_model(self):
        """Test getting an existing model"""
        model = self.registry.get("Qwen/Qwen2.5-7B-Instruct")
        assert model is not None
        assert model.model_name == "Qwen/Qwen2.5-7B-Instruct"
        assert model.min_gpu_count == 1

    def test_get_nonexistent_model(self):
        """Test getting a non-existent model"""
        model = self.registry.get("NonExistent/Model")
        assert model is None

    def test_list_models(self):
        """Test listing all models"""
        models = self.registry.list_models()
        assert len(models) > 0
        assert any(m.model_name == "Qwen/Qwen2.5-7B-Instruct" for m in models)

    def test_register_model(self):
        """Test registering a new model"""
        new_model = ModelInfo(
            model_name="TestModel/Test-1B",
            model_type=ModelType.CHAT,
            min_gpu_count=1,
            min_vram_per_gpu_gb=8,
            context_length=2048,
            is_preloaded=False
        )
        self.registry.register_model(new_model)

        retrieved = self.registry.get("TestModel/Test-1B")
        assert retrieved is not None
        assert retrieved.model_type == ModelType.CHAT

    def test_unregister_model(self):
        """Test unregistering a model"""
        # First register
        new_model = ModelInfo(
            model_name="Temp/TempModel",
            model_type=ModelType.CHAT,
            min_gpu_count=1,
            min_vram_per_gpu_gb=8
        )
        self.registry.register_model(new_model)
        assert self.registry.get("Temp/TempModel") is not None

        # Then unregister
        self.registry.unregister_model("Temp/TempModel")
        assert self.registry.get("Temp/TempModel") is None

    def test_unregister_nonexistent(self):
        """Test unregistering a non-existent model doesn't error"""
        self.registry.unregister_model("NonExistent/Model")
        # Should not raise

    def test_default_models_have_correct_types(self):
        """Test that default models have correct types"""
        models = self.registry.list_models()

        for model in models:
            assert model.model_type in [ModelType.CHAT, ModelType.VIDEO]
            assert model.min_gpu_count >= 1
            assert model.min_vram_per_gpu_gb > 0

    def test_chat_model_is_preloaded(self):
        """Test that small chat models are preloaded"""
        model = self.registry.get("Qwen/Qwen2.5-7B-Instruct")
        assert model.is_preloaded is True

    def test_large_model_not_preloaded(self):
        """Test that large models are not preloaded"""
        model = self.registry.get("Qwen/Qwen2.5-72B-Instruct")
        assert model.is_preloaded is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
