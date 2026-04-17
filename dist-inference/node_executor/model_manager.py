"""
Model Manager
"""

import os
from typing import List, Dict, Optional
import time

from shared.types import ModelInfo, ModelType


class ModelManager:
    """
    Manages model loading/unloading
    """

    # Commonly used models (preload)
    PRELOADED_MODELS = [
        "Qwen/Qwen2.5-7B-Instruct",
    ]

    def __init__(
        self,
        vllm_engine,  # VLLMEngine
        total_vram_gb: int,
        gpu_count: int
    ):
        self.vllm_engine = vllm_engine
        self.total_vram_gb = total_vram_gb
        self.gpu_count = gpu_count
        self.loaded_models: Dict[str, ModelInfo] = {}
        self.preloaded_models: List[str] = []

    def preload_models(self):
        """Preload commonly used models"""
        for model_name in self.PRELOADED_MODELS:
            if model_name in self.vllm_engine.get_supported_models():
                try:
                    self.vllm_engine.load_model(model_name)
                    self.preloaded_models.append(model_name)
                    print(f"[ModelManager] Preloaded: {model_name}")
                except Exception as e:
                    print(f"[ModelManager] Failed to preload {model_name}: {e}")

    def load_model(self, model_name: str) -> bool:
        """Load model on demand"""
        if model_name in self.loaded_models:
            return True

        try:
            self.vllm_engine.load_model(model_name)
            self.loaded_models[model_name] = ModelInfo(
                model_name=model_name,
                model_type=ModelType.CHAT  # Simplified
            )
            return True
        except Exception as e:
            print(f"[ModelManager] Failed to load {model_name}: {e}")
            return False

    def unload_model(self, model_name: str):
        """Unload model"""
        if model_name in self.loaded_models:
            # vLLM doesn't support dynamic unloading, need to restart process
            # Simplified: not supported for now
            pass

    def get_loaded_models(self) -> List[str]:
        """Get list of loaded models"""
        return list(self.loaded_models.keys()) + self.preloaded_models
