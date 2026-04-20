"""
Model Registry - Manages available models, persisted to SQLite
"""

from typing import Dict, List, Optional

from shared.types import ModelInfo, ModelType
from . import db


class ModelRegistry:
    """
    Manages available model list.
    Default models are hardcoded; custom registrations are persisted to SQLite.
    """

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
        # Start with defaults; custom models loaded from DB
        self.models: Dict[str, ModelInfo] = dict(self.DEFAULT_MODELS)

    def load_from_db(self) -> None:
        """Load custom (non-default) models from SQLite"""
        import sqlite3
        import os
        db_path = os.environ.get("USMSB_DB_PATH", "usmsb.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT model_name, model_type, min_gpu_count, min_vram_per_gpu_gb, context_length, is_preloaded FROM model_registry"
            ).fetchall()
            for r in rows:
                if r["model_name"] not in self.DEFAULT_MODELS:
                    self.models[r["model_name"]] = ModelInfo(
                        model_name=r["model_name"],
                        model_type=ModelType[r["model_type"].upper()],
                        min_gpu_count=r["min_gpu_count"],
                        min_vram_per_gpu_gb=r["min_vram_per_gpu_gb"],
                        context_length=r["context_length"],
                        is_preloaded=bool(r["is_preloaded"]),
                    )
        finally:
            conn.close()

    def get(self, model_name: str) -> Optional[ModelInfo]:
        """Get model info"""
        return self.models.get(model_name)

    def list_models(self) -> List[ModelInfo]:
        """List all models"""
        return list(self.models.values())

    def register_model(self, model_info: ModelInfo) -> None:
        """Register a new model (persisted to SQLite)"""
        self.models[model_info.model_name] = model_info
        self._save_model(model_info)

    def unregister_model(self, model_name: str) -> None:
        """Unregister a model (removed from SQLite and memory)"""
        if model_name in self.models and model_name not in self.DEFAULT_MODELS:
            del self.models[model_name]
            self._delete_model(model_name)

    def _save_model(self, model_info: ModelInfo) -> None:
        """Persist model to SQLite"""
        import sqlite3
        import os
        db_path = os.environ.get("USMSB_DB_PATH", "usmsb.db")
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                """INSERT INTO model_registry
                   (model_name, model_type, min_gpu_count, min_vram_per_gpu_gb, context_length, is_preloaded)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(model_name) DO UPDATE SET
                       model_type=excluded.model_type,
                       min_gpu_count=excluded.min_gpu_count,
                       min_vram_per_gpu_gb=excluded.min_vram_per_gpu_gb,
                       context_length=excluded.context_length,
                       is_preloaded=excluded.is_preloaded""",
                (
                    model_info.model_name,
                    model_info.model_type.value,
                    model_info.min_gpu_count,
                    model_info.min_vram_per_gpu_gb,
                    model_info.context_length,
                    int(model_info.is_preloaded),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _delete_model(self, model_name: str) -> None:
        """Remove model from SQLite"""
        import sqlite3
        import os
        db_path = os.environ.get("USMSB_DB_PATH", "usmsb.db")
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("DELETE FROM model_registry WHERE model_name = ?", (model_name,))
            conn.commit()
        finally:
            conn.close()
