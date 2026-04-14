"""
GoalPersistence - 目标持久化（Gene Capsule 集成）

实现"关机后目标不消失"的关键模块。

Gene Capsule（基因胶囊）是 USMSB 的经验存储机制。
GoalPersistence 将 Goal 和 Purpose 存储到 Gene Capsule 中，
实现目标的持久化，支持 Agent 重启后恢复。

关键设计：
- Goal 持久化 → 重启后继续追求
- Purpose 持久化 → 保留意图来源
- 与 Gene Capsule 集成 → 经验传承
"""

import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from usmsb_sdk.core.elements import Goal, GoalStatus
from .purpose_generator import Purpose, IntrinsicNeed


@dataclass
class GeneCapsule:
    """
    Gene Capsule - 经验胶囊
    
    存储 Agent 的经验、目标和意图。
    支持跨 Agent 的经验传承。
    
    属性：
    - id: 胶囊唯一 ID
    - agent_id: 所属 Agent ID
    - goal_id: 关联的目标 ID
    - purpose_id: 关联的意图 ID
    - content: 胶囊内容（序列化的 Goal/Purpose）
    - capsule_type: 胶囊类型（goal/purpose/need）
    - quality_score: 质量分数 (0.0-1.0)
    - created_at: 创建时间
    - metadata: 元数据
    """
    id: str
    agent_id: str
    goal_id: str | None = None
    purpose_id: str | None = None
    capsule_type: str = "goal"  # goal, purpose, need, experience
    content: str = ""  # JSON serialized content
    quality_score: float = 0.5
    created_at: float = 0.0
    metadata: dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at == 0.0:
            self.created_at = datetime.now().timestamp()


class GeneCapsuleDB:
    """
    Gene Capsule 数据库
    
    使用 SQLite 存储 Gene Capsule。
    """
    
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = "/Users/gujun/vibecode/usmsb/data/gene_capsule.db"
        
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._init_db()
    
    def _init_db(self) -> None:
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gene_capsules (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                goal_id TEXT,
                purpose_id TEXT,
                capsule_type TEXT NOT NULL,
                content TEXT NOT NULL,
                quality_score REAL DEFAULT 0.5,
                created_at REAL NOT NULL,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_id ON gene_capsules(agent_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_goal_id ON gene_capsules(goal_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_capsule_type ON gene_capsules(capsule_type)
        """)
        
        conn.commit()
        conn.close()
    
    def save_capsule(self, capsule: GeneCapsule) -> bool:
        """
        保存 Gene Capsule
        
        Args:
            capsule: Gene Capsule
            
        Returns:
            bool: 是否保存成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO gene_capsules 
                (id, agent_id, goal_id, purpose_id, capsule_type, content, quality_score, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                capsule.id,
                capsule.agent_id,
                capsule.goal_id,
                capsule.purpose_id,
                capsule.capsule_type,
                capsule.content,
                capsule.quality_score,
                capsule.created_at,
                json.dumps(capsule.metadata),
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving capsule: {e}")
            return False
    
    def load_capsules(self, agent_id: str, capsule_type: str | None = None) -> list[GeneCapsule]:
        """
        加载 Gene Capsule
        
        Args:
            agent_id: Agent ID
            capsule_type: 胶囊类型过滤（可选）
            
        Returns:
            list[GeneCapsule]: 胶囊列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if capsule_type:
                cursor.execute("""
                    SELECT id, agent_id, goal_id, purpose_id, capsule_type, content, quality_score, created_at, metadata
                    FROM gene_capsules
                    WHERE agent_id = ? AND capsule_type = ?
                    ORDER BY created_at DESC
                """, (agent_id, capsule_type))
            else:
                cursor.execute("""
                    SELECT id, agent_id, goal_id, purpose_id, capsule_type, content, quality_score, created_at, metadata
                    FROM gene_capsules
                    WHERE agent_id = ?
                    ORDER BY created_at DESC
                """, (agent_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            capsules = []
            for row in rows:
                capsules.append(GeneCapsule(
                    id=row[0],
                    agent_id=row[1],
                    goal_id=row[2],
                    purpose_id=row[3],
                    capsule_type=row[4],
                    content=row[5],
                    quality_score=row[6],
                    created_at=row[7],
                    metadata=json.loads(row[8]) if row[8] else {},
                ))
            
            return capsules
        except Exception as e:
            print(f"Error loading capsules: {e}")
            return []
    
    def delete_capsule(self, capsule_id: str) -> bool:
        """删除 Gene Capsule"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM gene_capsules WHERE id = ?", (capsule_id,))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False


class GoalPersistence:
    """
    目标持久化管理器
    
    核心职责：
    1. 将 Goal 存储到 Gene Capsule
    2. 将 Purpose 存储到 Gene Capsule
    3. 从 Gene Capsule 恢复 Goal/Purpose
    4. 目标历史追踪
    
    关键设计：
    - 每次目标更新都持久化
    - 重启时恢复未完成的目标
    - 支持目标历史查询
    """
    
    def __init__(self, agent_id: str, db_path: str | None = None):
        self.agent_id = agent_id
        self.db = GeneCapsuleDB(db_path)
    
    def save_goal(self, goal: Goal) -> bool:
        """
        保存 Goal 到 Gene Capsule
        
        Args:
            goal: 目标对象
            
        Returns:
            bool: 是否保存成功
        """
        capsule = GeneCapsule(
            id=f"goal_{goal.id}",
            agent_id=self.agent_id,
            goal_id=goal.id,
            capsule_type="goal",
            content=json.dumps(asdict(goal)),
            quality_score=goal.metadata.get("quality_score", 0.5),
            created_at=goal.created_at,
            metadata={
                "name": goal.name,
                "status": goal.status.value if isinstance(goal.status, GoalStatus) else goal.status,
                "priority": goal.priority,
                "is_intrinsic": goal.metadata.get("is_intrinsic", False),
            }
        )
        
        return self.db.save_capsule(capsule)
    
    def load_goals(
        self,
        agent_id: str | None = None,
        status: GoalStatus | None = None
    ) -> list[Goal]:
        """
        从 Gene Capsule 加载 Goal
        
        Args:
            agent_id: Agent ID（如果为 None，使用当前 Agent ID）
            status: 目标状态过滤（可选）
            
        Returns:
            list[Goal]: 目标列表
        """
        target_agent = agent_id or self.agent_id
        
        capsules = self.db.load_capsules(target_agent, capsule_type="goal")
        
        goals = []
        for capsule in capsules:
            try:
                goal_dict = json.loads(capsule.content)
                
                # 如果指定了状态过滤
                if status:
                    goal_status = goal_dict.get("status")
                    if isinstance(goal_status, str):
                        goal_status = GoalStatus(goal_status)
                    if goal_status != status:
                        continue
                
                # 重建 Goal 对象
                goal = Goal(
                    id=goal_dict.get("id", capsule.goal_id),
                    name=goal_dict.get("name", ""),
                    description=goal_dict.get("description", ""),
                    priority=goal_dict.get("priority", 0),
                    status=GoalStatus(goal_dict.get("status", "pending")),
                    associated_agent_id=goal_dict.get("associated_agent_id"),
                    parent_goal_id=goal_dict.get("parent_goal_id"),
                    created_at=goal_dict.get("created_at", capsule.created_at),
                    updated_at=goal_dict.get("updated_at", capsule.created_at),
                    metadata=goal_dict.get("metadata", {}),
                )
                
                goals.append(goal)
            except Exception as e:
                print(f"Error loading goal from capsule {capsule.id}: {e}")
                continue
        
        return goals
    
    def load_active_goals(self) -> list[Goal]:
        """
        加载未完成的目标（用于重启恢复）
        
        Returns:
            list[Goal]: 活跃目标列表
        """
        goals = []
        for status in [GoalStatus.PENDING, GoalStatus.IN_PROGRESS]:
            goals.extend(self.load_goals(status=status))
        return goals
    
    def save_purpose(self, purpose: Purpose) -> bool:
        """
        保存 Purpose 到 Gene Capsule
        
        Args:
            purpose: 意图对象
            
        Returns:
            bool: 是否保存成功
        """
        capsule = GeneCapsule(
            id=f"purpose_{purpose.id}",
            agent_id=self.agent_id,
            purpose_id=purpose.id,
            capsule_type="purpose",
            content=json.dumps(asdict(purpose)),
            quality_score=purpose.confidence,
            created_at=purpose.created_at,
            metadata={
                "name": purpose.name,
                "motivation": purpose.motivation,
                "source_need": purpose.source_need,
            }
        )
        
        return self.db.save_capsule(capsule)
    
    def load_purposes(self, agent_id: str | None = None) -> list[Purpose]:
        """
        从 Gene Capsule 加载 Purpose
        
        Args:
            agent_id: Agent ID（如果为 None，使用当前 Agent ID）
            
        Returns:
            list[Purpose]: 意图列表
        """
        target_agent = agent_id or self.agent_id
        
        capsules = self.db.load_capsules(target_agent, capsule_type="purpose")
        
        purposes = []
        for capsule in capsules:
            try:
                purpose_dict = json.loads(capsule.content)
                
                purpose = Purpose(
                    id=purpose_dict.get("id", capsule.purpose_id),
                    name=purpose_dict.get("name", ""),
                    description=purpose_dict.get("description", ""),
                    source_need=purpose_dict.get("source_need"),
                    motivation=purpose_dict.get("motivation", "intrinsic"),
                    confidence=purpose_dict.get("confidence", 0.5),
                    generated_goals=purpose_dict.get("generated_goals", []),
                    created_at=purpose_dict.get("created_at", capsule.created_at),
                    metadata=purpose_dict.get("metadata", {}),
                )
                
                purposes.append(purpose)
            except Exception as e:
                print(f"Error loading purpose from capsule {capsule.id}: {e}")
                continue
        
        return purposes
    
    def save_need(self, need: IntrinsicNeed) -> bool:
        """
        保存 IntrinsicNeed 到 Gene Capsule
        
        Args:
            need: 内在需求对象
            
        Returns:
            bool: 是否保存成功
        """
        capsule = GeneCapsule(
            id=f"need_{need.id}",
            agent_id=self.agent_id,
            capsule_type="need",
            content=json.dumps(need.to_dict()),
            quality_score=need.intensity,
            created_at=need.created_at,
            metadata={
                "type": need.type.value,
                "source": need.source,
            }
        )
        
        return self.db.save_capsule(capsule)
    
    def get_goal_history(self, limit: int = 100) -> list[dict]:
        """
        获取目标历史
        
        Args:
            limit: 返回数量限制
            
        Returns:
            list[dict]: 目标历史列表
        """
        capsules = self.db.load_capsules(self.agent_id, capsule_type="goal")
        
        history = []
        for capsule in capsules[:limit]:
            history.append({
                "id": capsule.id,
                "goal_id": capsule.goal_id,
                "created_at": capsule.created_at,
                "quality_score": capsule.quality_score,
                "metadata": capsule.metadata,
            })
        
        return history
