"""
ServiceRegistry - 服务注册与管理

管理服务的创建、状态流转和查询。

核心功能：
- 注册新服务
- 更新服务状态（pending → in_progress → completed → verified）
- 查询服务历史
- 获取待处理服务
"""

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ServiceType(Enum):
    """服务类型"""
    COMPUTATION = "computation"          # 计算服务
    DATA_PROCESSING = "data_processing" # 数据处理
    KNOWLEDGE_QUERY = "knowledge_query" # 知识查询
    COORDINATION = "coordination"       # 协调服务
    MEDIATION = "mediation"             # 调解服务
    RESOURCE_SHARING = "resource_sharing" # 资源共享
    LEARNING = "learning"               # 学习服务
    CREATION = "creation"               # 创造服务


class ServiceStatus(Enum):
    """服务状态"""
    PENDING = "pending"                # 待接受
    IN_PROGRESS = "in_progress"       # 进行中
    COMPLETED = "completed"           # 已完成（待验证）
    VERIFIED = "verified"             # 已验证
    REJECTED = "rejected"             # 已拒绝
    CANCELLED = "cancelled"           # 已取消


@dataclass
class Service:
    """服务记录"""
    id: str
    provider_id: str
    consumer_id: str
    service_type: ServiceType
    description: str
    difficulty: float = 0.5
    urgency: float = 0.5
    status: ServiceStatus = ServiceStatus.PENDING
    input_params: dict = field(default_factory=dict)
    output_result: Any = None
    estimated_duration: float = 3600.0  # 默认 1 小时
    actual_duration: float = 0.0
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    started_at: float | None = None
    completed_at: float | None = None
    verified_at: float | None = None
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        if isinstance(self.service_type, str):
            self.service_type = ServiceType(self.service_type)
        if isinstance(self.status, str):
            self.status = ServiceStatus(self.status)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "provider_id": self.provider_id,
            "consumer_id": self.consumer_id,
            "service_type": self.service_type.value if isinstance(self.service_type, ServiceType) else self.service_type,
            "description": self.description,
            "difficulty": self.difficulty,
            "urgency": self.urgency,
            "status": self.status.value if isinstance(self.status, ServiceStatus) else self.status,
            "input_params": self.input_params,
            "output_result": self.output_result,
            "estimated_duration": self.estimated_duration,
            "actual_duration": self.actual_duration,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "verified_at": self.verified_at,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Service":
        return cls(
            id=data["id"],
            provider_id=data["provider_id"],
            consumer_id=data["consumer_id"],
            service_type=data.get("service_type", "computation"),
            description=data.get("description", ""),
            difficulty=data.get("difficulty", 0.5),
            urgency=data.get("urgency", 0.5),
            status=data.get("status", "pending"),
            input_params=data.get("input_params", {}),
            output_result=data.get("output_result"),
            estimated_duration=data.get("estimated_duration", 3600.0),
            actual_duration=data.get("actual_duration", 0.0),
            created_at=data.get("created_at", datetime.now().timestamp()),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            verified_at=data.get("verified_at"),
            metadata=data.get("metadata", {}),
        )


class ServiceRegistryDB:
    """服务注册数据库"""
    
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = "/Users/gujun/vibecode/usmsb/data/service_registry.db"
        
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._init_db()
    
    def _init_db(self) -> None:
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id TEXT PRIMARY KEY,
                provider_id TEXT NOT NULL,
                consumer_id TEXT NOT NULL,
                service_type TEXT NOT NULL,
                description TEXT,
                difficulty REAL DEFAULT 0.5,
                urgency REAL DEFAULT 0.5,
                status TEXT NOT NULL,
                input_params TEXT,
                output_result TEXT,
                estimated_duration REAL DEFAULT 3600,
                actual_duration REAL DEFAULT 0,
                created_at REAL NOT NULL,
                started_at REAL,
                completed_at REAL,
                verified_at REAL,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_provider ON services(provider_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_consumer ON services(consumer_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON services(status)
        """)
        
        conn.commit()
        conn.close()
    
    def save(self, service: Service) -> bool:
        """保存服务记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            data = service.to_dict()
            data["input_params"] = json.dumps(data["input_params"])
            data["output_result"] = json.dumps(data["output_result"]) if data["output_result"] else None
            data["metadata"] = json.dumps(data["metadata"])
            
            cursor.execute("""
                INSERT OR REPLACE INTO services 
                (id, provider_id, consumer_id, service_type, description,
                 difficulty, urgency, status, input_params, output_result,
                 estimated_duration, actual_duration, created_at,
                 started_at, completed_at, verified_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["id"], data["provider_id"], data["consumer_id"],
                data["service_type"], data["description"], data["difficulty"],
                data["urgency"], data["status"], data["input_params"],
                data["output_result"], data["estimated_duration"],
                data["actual_duration"], data["created_at"], data["started_at"],
                data["completed_at"], data["verified_at"], data["metadata"]
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving service: {e}")
            return False
    
    def load(self, service_id: str) -> Service | None:
        """加载服务记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM services WHERE id = ?
            """, (service_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return self._row_to_service(row)
            return None
        except Exception as e:
            print(f"Error loading service: {e}")
            return None
    
    def get_by_provider(
        self,
        provider_id: str,
        status: ServiceStatus | None = None,
        limit: int = 100
    ) -> list[Service]:
        """获取某 Provider 的所有服务"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if status:
                cursor.execute("""
                    SELECT * FROM services
                    WHERE provider_id = ? AND status = ?
                    ORDER BY created_at DESC LIMIT ?
                """, (provider_id, status.value, limit))
            else:
                cursor.execute("""
                    SELECT * FROM services
                    WHERE provider_id = ?
                    ORDER BY created_at DESC LIMIT ?
                """, (provider_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [self._row_to_service(row) for row in rows]
        except Exception as e:
            print(f"Error getting services by provider: {e}")
            return []
    
    def get_by_consumer(
        self,
        consumer_id: str,
        status: ServiceStatus | None = None,
        limit: int = 100
    ) -> list[Service]:
        """获取某 Consumer 的所有服务"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if status:
                cursor.execute("""
                    SELECT * FROM services
                    WHERE consumer_id = ? AND status = ?
                    ORDER BY created_at DESC LIMIT ?
                """, (consumer_id, status.value, limit))
            else:
                cursor.execute("""
                    SELECT * FROM services
                    WHERE consumer_id = ?
                    ORDER BY created_at DESC LIMIT ?
                """, (consumer_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [self._row_to_service(row) for row in rows]
        except Exception as e:
            print(f"Error getting services by consumer: {e}")
            return []
    
    def get_pending_services(self) -> list[Service]:
        """获取待处理的服务"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM services
                WHERE status = ?
                ORDER BY created_at ASC
            """, (ServiceStatus.PENDING.value,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [self._row_to_service(row) for row in rows]
        except Exception as e:
            print(f"Error getting pending services: {e}")
            return []
    
    def _row_to_service(self, row: tuple) -> Service:
        """将数据库行转换为 Service"""
        return Service(
            id=row[0], provider_id=row[1], consumer_id=row[2],
            service_type=row[3], description=row[4], difficulty=row[5],
            urgency=row[6], status=row[7],
            input_params=json.loads(row[8]) if row[8] else {},
            output_result=json.loads(row[9]) if row[9] else None,
            estimated_duration=row[10], actual_duration=row[11],
            created_at=row[12], started_at=row[13], completed_at=row[14],
            verified_at=row[15],
            metadata=json.loads(row[16]) if row[16] else {}
        )


class ServiceRegistry:
    """
    服务注册与管理
    
    使用方式：
    ```python
    registry = ServiceRegistry()
    
    # 注册服务
    service = registry.register_service(
        provider_id="agent_001",
        consumer_id="agent_002",
        service_type=ServiceType.COMPUTATION,
        description="数据处理服务"
    )
    
    # 更新状态
    registry.update_status(service.id, ServiceStatus.IN_PROGRESS)
    
    # 查询历史
    history = registry.get_services_by_provider("agent_001")
    ```
    """
    
    def __init__(self, db_path: str | None = None):
        self.db = ServiceRegistryDB(db_path)
    
    def register_service(
        self,
        provider_id: str,
        consumer_id: str,
        service_type: ServiceType,
        description: str = "",
        difficulty: float = 0.5,
        urgency: float = 0.5,
        input_params: dict | None = None,
        estimated_duration: float = 3600.0
    ) -> Service:
        """注册新服务"""
        service = Service(
            id=str(uuid.uuid4()),
            provider_id=provider_id,
            consumer_id=consumer_id,
            service_type=service_type,
            description=description,
            difficulty=difficulty,
            urgency=urgency,
            status=ServiceStatus.PENDING,
            input_params=input_params or {},
            estimated_duration=estimated_duration,
        )
        
        self.db.save(service)
        return service
    
    def get_service(self, service_id: str) -> Service | None:
        """获取服务"""
        return self.db.load(service_id)
    
    def update_status(
        self,
        service_id: str,
        new_status: ServiceStatus,
        **kwargs
    ) -> bool:
        """更新服务状态"""
        service = self.db.load(service_id)
        if not service:
            return False
        
        service.status = new_status
        
        now = datetime.now().timestamp()
        
        if new_status == ServiceStatus.IN_PROGRESS:
            service.started_at = now
        elif new_status == ServiceStatus.COMPLETED:
            service.completed_at = now
            if "output_result" in kwargs:
                service.output_result = kwargs["output_result"]
            if service.started_at:
                service.actual_duration = now - service.started_at
        elif new_status == ServiceStatus.VERIFIED:
            service.verified_at = now
        elif new_status == ServiceStatus.REJECTED:
            if "reject_reason" in kwargs:
                service.metadata["reject_reason"] = kwargs["reject_reason"]
        
        return self.db.save(service)
    
    def accept_service(self, service_id: str) -> bool:
        """接受服务（从 PENDING 变为 IN_PROGRESS）"""
        service = self.db.load(service_id)
        if not service or service.status != ServiceStatus.PENDING:
            return False
        return self.update_status(service_id, ServiceStatus.IN_PROGRESS)
    
    def complete_service(self, service_id: str, output_result: Any = None) -> bool:
        """完成服务（从 IN_PROGRESS 变为 COMPLETED）"""
        service = self.db.load(service_id)
        if not service or service.status != ServiceStatus.IN_PROGRESS:
            return False
        return self.update_status(
            service_id,
            ServiceStatus.COMPLETED,
            output_result=output_result
        )
    
    def verify_service(self, service_id: str) -> bool:
        """验证服务（从 COMPLETED 变为 VERIFIED）"""
        service = self.db.load(service_id)
        if not service or service.status != ServiceStatus.COMPLETED:
            return False
        return self.update_status(service_id, ServiceStatus.VERIFIED)
    
    def reject_service(self, service_id: str, reason: str = "") -> bool:
        """拒绝服务"""
        service = self.db.load(service_id)
        if not service:
            return False
        return self.update_status(
            service_id,
            ServiceStatus.REJECTED,
            reject_reason=reason
        )
    
    def get_services_by_provider(
        self,
        provider_id: str,
        status: ServiceStatus | None = None
    ) -> list[Service]:
        """获取某 Provider 的服务"""
        return self.db.get_by_provider(provider_id, status=status)
    
    def get_services_by_consumer(
        self,
        consumer_id: str,
        status: ServiceStatus | None = None
    ) -> list[Service]:
        """获取某 Consumer 的服务"""
        return self.db.get_by_consumer(consumer_id, status=status)
    
    def get_pending_services(self) -> list[Service]:
        """获取待处理的服务"""
        return self.db.get_pending_services()
    
    def get_service_stats(self, agent_id: str) -> dict:
        """获取某 Agent 的服务统计"""
        all_services = self.db.get_by_provider(agent_id, limit=1000)
        
        stats = {
            "total": len(all_services),
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "verified": 0,
            "rejected": 0,
            "cancelled": 0,
        }
        
        for service in all_services:
            if service.status == ServiceStatus.PENDING:
                stats["pending"] += 1
            elif service.status == ServiceStatus.IN_PROGRESS:
                stats["in_progress"] += 1
            elif service.status == ServiceStatus.COMPLETED:
                stats["completed"] += 1
            elif service.status == ServiceStatus.VERIFIED:
                stats["verified"] += 1
            elif service.status == ServiceStatus.REJECTED:
                stats["rejected"] += 1
            elif service.status == ServiceStatus.CANCELLED:
                stats["cancelled"] += 1
        
        return stats
