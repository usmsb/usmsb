"""
Model Registry - Manages available models
"""

from typing import Dict, List, Optional

from shared.types import ModelInfo, ModelType


class ModelRegistry:
    """
    Manages available model list
    """

    # Phase 1 default models
    DEFAULT_MODELS: Dict[str, ModelInfo] = {
        "Qwen/Qwen2.5-7B-Instruct": ModelInfo(
            model_name="Qwen/Qwen2.5-7B-Instruct",
            model_type=ModelType.CHAT,
            min_gpu_count=1,
            min_vram_per_gpu_gb=16,
            context_length=8192,
            is_preloaded=True,
        ),
        "Qwen/Qwen2.5-14B-Instruct": ModelInfo(
            model_name="Qwen/Qwen2.5-14B-Instruct",
            model_type=ModelType.CHAT,
            min_gpu_count=1,
            min_vram_per_gpu_gb=28,
            context_length=8192,
            is_preloaded=False,
        ),
        "Qwen/Qwen2.5-72B-Instruct": ModelInfo(
            model_name="Qwen/Qwen2.5-72B-Instruct",
            model_type=ModelType.CHAT,
            min_gpu_count=4,
            min_vram_per_gpu_gb=40,
            context_length=32768,
            is_preloaded=False,
        ),
        # Video generation models (future)
        "THUDM/CogVideoX-5b": ModelInfo(
            model_name="THUDM/CogVideoX-5b",
            model_type=ModelType.VIDEO,
            min_gpu_count=2,
            min_vram_per_gpu_gb=24,
            context_length=2048,
            is_preloaded=False,
        ),
    }

    def __init__(self):
        self.models: Dict[str, ModelInfo] = dict(self.DEFAULT_MODELS)

    def get(self, model_name: str) -> Optional[ModelInfo]:
        """Get model info"""
        return self.models.get(model_name)

    def list_models(self) -> List[ModelInfo]:
        """List all models"""
        return list(self.models.values())

    def register_model(self, model_info: ModelInfo):
        """Register a new model"""
        self.models[model_info.model_name] = model_info

    def unregister_model(self, model_name: str):
        """Unregister a model"""
        if model_name in self.models:
            del self.models[model_name]
