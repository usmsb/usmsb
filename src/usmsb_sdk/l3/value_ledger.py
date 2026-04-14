"""
ValueLedger - 价值账本

记录所有价值流转历史，是价值循环的"银行流水"。

核心功能：
- 记录价值创造
- 更新价值状态
- 查询价值历史
- 计算总价值
"""

import json
import sqlite3
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ValueType(Enum):
    """价值类型"""
    ECONOMIC = "economic"             # 经济价值
    KNOWLEDGE = "knowledge"          # 知识价值
    SOCIAL = "social"                # 社交价值
    REPUTATION = "reputation"        # 声誉价值
    CAPABILITY = "capability"        # 能力价值


class ValueStatus(Enum):
    """价值状态"""
    CREATED = "created"              # 刚创建，未确认
    CONFIRMED = "confirmed"          # 已确认
    CONVERTED = "converted"          # 已转换为 VIBE
    DEPLETED = "depleted"            # 已消耗
    CANCELLED = "cancelled"          # 已取消


@dataclass
class ValueRecord:
    """价值记录"""
    id: str
    service_id: str
    provider_id: str
    consumer_id: str
    value_type: ValueType
    raw_value: float
    converted_vibe: float = 0.0
    conversion_rate: float = 0.9
    quality_score: float = 0.5
    scarcity_bonus: float = 1.0
    demand_multiplier: float = 1.0
    final_value: float = 0.0
    status: ValueStatus = ValueStatus.CREATED
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    confirmed_at: float | None = None
    converted_at: float | None = None
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        if isinstance(self.value_type, str):
            self.value_type = ValueType(self.value_type)
        if isinstance(self.status, str):
            self.status = ValueStatus(self.status)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "service_id": self.service_id,
            "provider_id": self.provider_id,
            "consumer_id": self.consumer_id,
            "value_type": self.value_type.value if isinstance(self.value_type, ValueType) else self.value_type,
            "raw_value": self.raw_value,
            "converted_vibe": self.converted_vibe,
            "conversion_rate": self.conversion_rate,
            "quality_score": self.quality_score,
            "scarcity_bonus": self.scarcity_bonus,
            "demand_multiplier": self.demand_multiplier,
            "final_value": self.final_value,
            "status": self.status.value if isinstance(self.status, ValueStatus) else self.status,
            "created_at": self.created_at,
            "confirmed_at": self.confirmed_at,
            "converted_at": self.converted_at,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ValueRecord":
        return cls(
            id=data["id"],
            service_id=data["service_id"],
            provider_id=data["provider_id"],
            consumer_id=data["consumer_id"],
            value_type=data.get("value_type", "economic"),
            raw_value=data["raw_value"],
            converted_vibe=data.get("converted_vibe", 0.0),
            conversion_rate=data.get("conversion_rate", 0.9),
            quality_score=data.get("quality_score", 0.5),
            scarcity_bonus=data.get("scarcity_bonus", 1.0),
            demand_multiplier=data.get("demand_multiplier", 1.0),
            final_value=data.get("final_value", 0.0),
            status=data.get("status", "created"),
            created_at=data.get("created_at", datetime.now().timestamp()),
            confirmed_at=data.get("confirmed_at"),
            converted_at=data.get("converted_at"),
            metadata=data.get("metadata", {}),
        )


class ValueLedgerDB:
    """价值账本数据库"""
    
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = "/Users/gujun/vibecode/usmsb/data/value_ledger.db"
        
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._init_db()
    
    def _init_db(self) -> None:
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS value_records (
                id TEXT PRIMARY KEY,
                service_id TEXT NOT NULL,
                provider_id TEXT NOT NULL,
                consumer_id TEXT NOT NULL,
                value_type TEXT NOT NULL,
                raw_value REAL NOT NULL,
                converted_vibe REAL DEFAULT 0,
                conversion_rate REAL DEFAULT 0.9,
                quality_score REAL DEFAULT 0.5,
                scarcity_bonus REAL DEFAULT 1.0,
                demand_multiplier REAL DEFAULT 1.0,
                final_value REAL NOT NULL,
                status TEXT NOT NULL,
                created_at REAL NOT NULL,
                confirmed_at REAL,
                converted_at REAL,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_provider ON value_records(provider_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_consumer ON value_records(consumer_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON value_records(status)
        """)
        
        conn.commit()
        conn.close()
    
    def save(self, record: ValueRecord) -> bool:
        """保存价值记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            data = record.to_dict()
            data["metadata"] = json.dumps(data["metadata"])
            
            cursor.execute("""
                INSERT OR REPLACE INTO value_records 
                (id, service_id, provider_id, consumer_id, value_type, raw_value, 
                 converted_vibe, conversion_rate, quality_score, scarcity_bonus,
                 demand_multiplier, final_value, status, created_at, 
                 confirmed_at, converted_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["id"], data["service_id"], data["provider_id"], data["consumer_id"],
                data["value_type"], data["raw_value"], data["converted_vibe"],
                data["conversion_rate"], data["quality_score"], data["scarcity_bonus"],
                data["demand_multiplier"], data["final_value"], data["status"],
                data["created_at"], data["confirmed_at"], data["converted_at"],
                data["metadata"]
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving value record: {e}")
            return False
    
    def load(self, record_id: str) -> ValueRecord | None:
        """加载价值记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, service_id, provider_id, consumer_id, value_type,
                       raw_value, converted_vibe, conversion_rate, quality_score,
                       scarcity_bonus, demand_multiplier, final_value, status,
                       created_at, confirmed_at, converted_at, metadata
                FROM value_records WHERE id = ?
            """, (record_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return ValueRecord(
                    id=row[0], service_id=row[1], provider_id=row[2],
                    consumer_id=row[3], value_type=row[4], raw_value=row[5],
                    converted_vibe=row[6], conversion_rate=row[7],
                    quality_score=row[8], scarcity_bonus=row[9],
                    demand_multiplier=row[10], final_value=row[11],
                    status=row[12], created_at=row[13], confirmed_at=row[14],
                    converted_at=row[15],
                    metadata=json.loads(row[16]) if row[16] else {}
                )
            return None
        except Exception as e:
            print(f"Error loading value record: {e}")
            return None
    
    def get_by_provider(
        self,
        provider_id: str,
        status: ValueStatus | None = None,
        limit: int = 100
    ) -> list[ValueRecord]:
        """获取某 Provider 的所有价值记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if status:
                cursor.execute("""
                    SELECT * FROM value_records
                    WHERE provider_id = ? AND status = ?
                    ORDER BY created_at DESC LIMIT ?
                """, (provider_id, status.value, limit))
            else:
                cursor.execute("""
                    SELECT * FROM value_records
                    WHERE provider_id = ?
                    ORDER BY created_at DESC LIMIT ?
                """, (provider_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [self._row_to_record(row) for row in rows]
        except Exception as e:
            print(f"Error getting value records by provider: {e}")
            return []
    
    def get_by_consumer(
        self,
        consumer_id: str,
        status: ValueStatus | None = None,
        limit: int = 100
    ) -> list[ValueRecord]:
        """获取某 Consumer 的所有价值记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if status:
                cursor.execute("""
                    SELECT * FROM value_records
                    WHERE consumer_id = ? AND status = ?
                    ORDER BY created_at DESC LIMIT ?
                """, (consumer_id, status.value, limit))
            else:
                cursor.execute("""
                    SELECT * FROM value_records
                    WHERE consumer_id = ?
                    ORDER BY created_at DESC LIMIT ?
                """, (consumer_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [self._row_to_record(row) for row in rows]
        except Exception as e:
            print(f"Error getting value records by consumer: {e}")
            return []
    
    def get_total_value(
        self,
        agent_id: str,
        as_provider: bool = True,
        value_type: ValueType | None = None
    ) -> float:
        """获取某 Agent 的总价值"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            column = "provider_id" if as_provider else "consumer_id"
            
            if value_type:
                cursor.execute(f"""
                    SELECT SUM(final_value) FROM value_records
                    WHERE {column} = ? AND value_type = ? AND status != ?
                """, (agent_id, value_type.value, ValueStatus.CANCELLED.value))
            else:
                cursor.execute(f"""
                    SELECT SUM(final_value) FROM value_records
                    WHERE {column} = ? AND status != ?
                """, (agent_id, ValueStatus.CANCELLED.value))
            
            result = cursor.fetchone()[0]
            conn.close()
            
            return result or 0.0
        except Exception as e:
            print(f"Error getting total value: {e}")
            return 0.0
    
    def _row_to_record(self, row: tuple) -> ValueRecord:
        """将数据库行转换为 ValueRecord"""
        return ValueRecord(
            id=row[0], service_id=row[1], provider_id=row[2],
            consumer_id=row[3], value_type=row[4], raw_value=row[5],
            converted_vibe=row[6], conversion_rate=row[7],
            quality_score=row[8], scarcity_bonus=row[9],
            demand_multiplier=row[10], final_value=row[11],
            status=row[12], created_at=row[13], confirmed_at=row[14],
            converted_at=row[15],
            metadata=json.loads(row[16]) if row[16] else {}
        )


class ValueLedger:
    """
    价值账本
    
    管理所有价值记录的创建、状态更新和查询。
    
    使用方式：
    ```python
    ledger = ValueLedger()
    
    # 记录价值
    record = ValueRecord(...)
    ledger.record_value(record)
    
    # 查询历史
    history = ledger.get_value_history("agent_001")
    
    # 统计总价值
    total = ledger.get_total_value("agent_001")
    ```
    """
    
    def __init__(self, db_path: str | None = None):
        self.db = ValueLedgerDB(db_path)
    
    def record_value(self, value_record: ValueRecord) -> bool:
        """记录新价值"""
        if not value_record.id:
            value_record.id = str(uuid.uuid4())
        return self.db.save(value_record)
    
    def update_status(
        self,
        value_record_id: str,
        new_status: ValueStatus,
        **kwargs
    ) -> bool:
        """更新价值状态"""
        record = self.db.load(value_record_id)
        if not record:
            return False
        
        record.status = new_status
        
        if new_status == ValueStatus.CONFIRMED:
            record.confirmed_at = datetime.now().timestamp()
        elif new_status == ValueStatus.CONVERTED:
            record.converted_at = datetime.now().timestamp()
        
        if "converted_vibe" in kwargs:
            record.converted_vibe = kwargs["converted_vibe"]
        if "quality_score" in kwargs:
            record.quality_score = kwargs["quality_score"]
        
        return self.db.save(record)
    
    def get_value_record(self, value_record_id: str) -> ValueRecord | None:
        """获取价值记录"""
        return self.db.load(value_record_id)
    
    def get_value_history(
        self,
        agent_id: str,
        limit: int = 100,
        as_provider: bool = True
    ) -> list[ValueRecord]:
        """获取 Agent 的价值历史"""
        if as_provider:
            return self.db.get_by_provider(agent_id, limit=limit)
        else:
            return self.db.get_by_consumer(agent_id, limit=limit)
    
    def get_total_value(
        self,
        agent_id: str,
        value_type: ValueType | None = None
    ) -> float:
        """获取 Agent 的总价值（作为服务提供方）"""
        return self.db.get_total_value(agent_id, as_provider=True, value_type=value_type)
    
    def get_pending_values(self, agent_id: str) -> list[ValueRecord]:
        """获取待确认的价值记录"""
        return self.db.get_by_provider(
            agent_id,
            status=ValueStatus.CREATED,
            limit=100
        )
