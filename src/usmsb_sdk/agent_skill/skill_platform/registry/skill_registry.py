"""
SkillRegistry - Skill 注册与安装管理
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ..types import (
    SkillInstance,
    SkillMetadata,
    SkillStatus,
    SkillTier,
)

logger = logging.getLogger(__name__)


class SkillRegistry:
    """
    Skill 注册中心。

    管理 Skill 的注册、安装、卸载、发现。
    """

    def __init__(self, registry_path: str = "data/skill_registry.db"):
        self.registry_path = registry_path
        self._installed: dict[str, SkillInstance] = {}
        self._init_db()

    def _init_db(self):
        import sqlite3
        import os
        os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
        conn = sqlite3.connect(self.registry_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS skill_registry (
                skill_id TEXT PRIMARY KEY,
                metadata_json TEXT NOT NULL,
                config_json TEXT NOT NULL,
                installed_at TEXT NOT NULL,
                last_used TEXT,
                use_count INTEGER DEFAULT 0,
                quality_scores_json TEXT DEFAULT '[]'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS skill_store (
                skill_id TEXT PRIMARY KEY,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    # ─────────────────────────────────────────────────────────────
    # 安装 / 卸载
    # ─────────────────────────────────────────────────────────────

    def install(self, metadata: SkillMetadata, config: dict[str, Any] = None) -> SkillInstance:
        """安装一个 Skill"""
        instance = SkillInstance(
            metadata=metadata,
            config=config or {},
            installed_at=datetime.now(),
        )
        self._installed[metadata.skill_id] = instance
        self._save_instance(instance)
        logger.info(f"[SkillRegistry] Installed skill: {metadata.name} ({metadata.skill_id})")
        return instance

    def uninstall(self, skill_id: str) -> bool:
        """卸载一个 Skill"""
        if skill_id in self._installed:
            del self._installed[skill_id]
            self._remove_instance(skill_id)
            logger.info(f"[SkillRegistry] Uninstalled skill: {skill_id}")
            return True
        return False

    def get_installed(self, skill_id: str) -> SkillInstance | None:
        """获取已安装的 Skill"""
        if skill_id in self._installed:
            return self._installed[skill_id]
        return self._load_instance(skill_id)

    def list_installed(self) -> list[SkillInstance]:
        """列出所有已安装的 Skill"""
        return list(self._installed.values())

    def update_last_used(self, skill_id: str, quality_score: float):
        """更新 Skill 使用记录"""
        inst = self.get_installed(skill_id)
        if inst:
            inst.last_used = datetime.now()
            inst.use_count += 1
            inst.quality_scores.append(quality_score)
            # 保留最近100条
            if len(inst.quality_scores) > 100:
                inst.quality_scores = inst.quality_scores[-100:]
            self._save_instance(inst)

    # ─────────────────────────────────────────────────────────────
    # 发布 / 市场
    # ─────────────────────────────────────────────────────────────

    def publish(self, metadata: SkillMetadata) -> SkillMetadata:
        """发布 Skill 到市场（需审核）"""
        metadata.status = SkillStatus.PENDING_REVIEW
        metadata.updated_at = datetime.now()
        self._save_to_store(metadata)
        logger.info(f"[SkillRegistry] Skill submitted for review: {metadata.name}")
        return metadata

    def approve(self, skill_id: str, review_notes: str = "") -> bool:
        """审核通过（SuperAdmin/MetaAgent 操作）"""
        metadata = self._load_from_store(skill_id)
        if not metadata:
            return False
        metadata.status = SkillStatus.APPROVED
        metadata.review_notes = review_notes
        metadata.published_at = datetime.now()
        metadata.updated_at = datetime.now()
        self._save_to_store(metadata)
        logger.info(f"[SkillRegistry] Skill approved: {skill_id}")
        return True

    def search(self, query: str = "", tier: SkillTier | None = None,
               tags: list[str] | None = None, limit: int = 20) -> list[SkillMetadata]:
        """搜索市场中的 Skill"""
        import sqlite3
        conn = sqlite3.connect(self.registry_path)
        q = "SELECT metadata_json FROM skill_store WHERE 1=1"
        params = []

        if query:
            q += " AND metadata_json LIKE ?"
            params.append(f"%{query}%")
        if tier:
            q += " AND metadata_json LIKE ?"
            params.append(f'%"tier": "{tier.value}"%')
        if tags:
            for tag in tags:
                q += " AND metadata_json LIKE ?"
                params.append(f'%"tags": ["%{tag}"%')

        q += " ORDER BY created_at DESC LIMIT ?"
        params.append(str(limit))

        rows = conn.execute(q, params).fetchall()
        conn.close()

        results = []
        for (row,) in rows:
            import json
            data = json.loads(row)
            metadata = self._dict_to_metadata(data)
            if metadata.status == SkillStatus.APPROVED or metadata.status == SkillStatus.PUBLISHED:
                results.append(metadata)
        return results

    # ─────────────────────────────────────────────────────────────
    # 内部持久化
    # ─────────────────────────────────────────────────────────────

    def _save_instance(self, instance: SkillInstance):
        import json
        import sqlite3
        conn = sqlite3.connect(self.registry_path)
        conn.execute("""
            INSERT OR REPLACE INTO skill_registry VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            instance.metadata.skill_id,
            json.dumps(instance.metadata.to_dict()),
            json.dumps(instance.config),
            instance.installed_at.isoformat(),
            instance.last_used.isoformat() if instance.last_used else None,
            instance.use_count,
            json.dumps(instance.quality_scores),
        ])
        conn.commit()
        conn.close()

    def _load_instance(self, skill_id: str) -> SkillInstance | None:
        import json
        import sqlite3
        conn = sqlite3.connect(self.registry_path)
        row = conn.execute(
            "SELECT * FROM skill_registry WHERE skill_id = ?", (skill_id,)
        ).fetchone()
        conn.close()
        if not row:
            return None
        cols = ["skill_id", "metadata_json", "config_json", "installed_at",
                "last_used", "use_count", "quality_scores_json"]
        d = dict(zip(cols, row))
        metadata = self._dict_to_metadata(json.loads(d["metadata_json"]))
        instance = SkillInstance(
            metadata=metadata,
            config=json.loads(d["config_json"]),
            installed_at=datetime.fromisoformat(d["installed_at"]),
            last_used=datetime.fromisoformat(d["last_used"]) if d["last_used"] else None,
            use_count=d["use_count"],
            quality_scores=json.loads(d["quality_scores_json"]),
        )
        self._installed[skill_id] = instance
        return instance

    def _remove_instance(self, skill_id: str):
        import sqlite3
        conn = sqlite3.connect(self.registry_path)
        conn.execute("DELETE FROM skill_registry WHERE skill_id = ?", (skill_id,))
        conn.commit()
        conn.close()

    def _save_to_store(self, metadata: SkillMetadata):
        import json
        import sqlite3
        conn = sqlite3.connect(self.registry_path)
        conn.execute("""
            INSERT OR REPLACE INTO skill_store VALUES (?, ?, ?, ?)
        """, [
            metadata.skill_id,
            json.dumps(metadata.to_dict()),
            metadata.created_at.isoformat(),
            metadata.updated_at.isoformat(),
        ])
        conn.commit()
        conn.close()

    def _load_from_store(self, skill_id: str) -> SkillMetadata | None:
        import json
        import sqlite3
        conn = sqlite3.connect(self.registry_path)
        row = conn.execute(
            "SELECT metadata_json FROM skill_store WHERE skill_id = ?", (skill_id,)
        ).fetchone()
        conn.close()
        if not row:
            return None
        return self._dict_to_metadata(json.loads(row[0]))

    @staticmethod
    def _dict_to_metadata(d: dict) -> SkillMetadata:
        return SkillMetadata(
            skill_id=d["skill_id"],
            name=d["name"],
            version=d["version"],
            author_agent_id=d["author_agent_id"],
            tier=SkillTier(d["tier"]),
            description=d["description"],
            tags=d.get("tags", []),
            inputs=d.get("inputs", []),
            outputs=d.get("outputs", []),
            dependencies=d.get("dependencies", []),
            examples=d.get("examples", []),
            price=d.get("price", 0),
            rating=d.get("rating", 0.0),
            install_count=d.get("install_count", 0),
            status=SkillStatus(d.get("status", "draft")),
            review_notes=d.get("review_notes", ""),
            created_at=datetime.fromisoformat(d["created_at"]),
            updated_at=datetime.fromisoformat(d["updated_at"]),
            published_at=datetime.fromisoformat(d["published_at"]) if d.get("published_at") else None,
        )
