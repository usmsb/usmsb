"""
TaskPool - 真实任务池

为 Agent 提供真实任务来源：
- 任务池管理
- 自动接单
- 任务匹配
- 任务执行追踪
"""

import uuid
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from enum import Enum


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"      # 待接单
    ASSIGNED = "assigned"    # 已分配
    IN_PROGRESS = "in_progress"  # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 取消


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Task:
    """任务"""
    id: str
    task_type: str  # coding, analysis, design, etc.
    title: str
    description: str
    required_capabilities: list[str]
    reward: float  # VIBE 奖励
    deadline: float | None  # 截止时间
    priority: int = TaskPriority.MEDIUM.value
    status: str = TaskStatus.PENDING.value
    assigned_agent: str | None = None
    created_at: float = field(default_factory=datetime.now().timestamp)
    assigned_at: float | None = None
    completed_at: float | None = None
    result: dict | None = None


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    agent_id: str
    success: bool
    quality_score: float  # 0-1
    completion_time: float  # 秒
    result_data: dict | None = None


class TaskPool:
    """
    真实任务池
    
    为 Agent 提供真实任务来源：
    - 外部任务注入（模拟或 API）
    - 自动分配给合适的 Agent
    - 任务执行追踪和奖励发放
    
    使用方式：
    ```python
    pool = TaskPool()
    
    # 添加任务
    task_id = pool.add_task(
        task_type="coding",
        title="修复 Bug", description="修复生产环境的Bug",
        description="...",
        required_capabilities=["python"],
        reward=50.0
    )
    
    # Agent 认领任务
    task = pool.claim_task(agent_id="agent_001", capabilities=["python"])
    
    # Agent 完成任务
    pool.complete_task(task_id, success=True, quality_score=0.9)
    
    # 获取待处理任务
    pending = pool.get_pending_tasks()
    ```
    """
    
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = "/Users/gujun/vibecode/usmsb/data/task_pool.db"
        
        from pathlib import Path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self._init_db()
        
        # 内存缓存
        self._tasks: dict[str, Task] = {}
        self._agent_tasks: dict[str, list[str]] = {}  # agent_id -> [task_ids]
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                required_capabilities TEXT NOT NULL,
                reward REAL NOT NULL,
                deadline REAL,
                priority INTEGER DEFAULT 2,
                status TEXT NOT NULL,
                assigned_agent TEXT,
                created_at REAL NOT NULL,
                assigned_at REAL,
                completed_at REAL,
                result TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_results (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                success INTEGER NOT NULL,
                quality_score REAL NOT NULL,
                completion_time REAL NOT NULL,
                result_data TEXT,
                timestamp REAL NOT NULL
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_assigned ON tasks(assigned_agent)")
        
        conn.commit()
        conn.close()
    
    def add_task(
        self,
        task_type: str,
        title: str,
        description: str,
        required_capabilities: list[str],
        reward: float,
        deadline: float | None = None,
        priority: int = TaskPriority.MEDIUM.value,
    ) -> str:
        """
        添加任务到池中
        
        Returns:
            str: 任务 ID
        """
        task = Task(
            id=str(uuid.uuid4()),
            task_type=task_type,
            title=title,
            description=description,
            required_capabilities=required_capabilities,
            reward=reward,
            deadline=deadline,
            priority=priority,
        )
        
        # 保存到数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        import json
        cursor.execute("""
            INSERT INTO tasks
            (id, task_type, title, description, required_capabilities, reward, deadline, priority, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task.id,
            task.task_type,
            task.title,
            task.description,
            json.dumps(required_capabilities),
            task.reward,
            task.deadline,
            task.priority,
            task.status,
            task.created_at
        ))
        
        conn.commit()
        conn.close()
        
        # 缓存
        self._tasks[task.id] = task
        
        return task.id
    
    def claim_task(
        self,
        agent_id: str,
        capabilities: list[str]
    ) -> Task | None:
        """
        Agent 认领任务
        
        自动匹配最合适的任务：
        1. 优先匹配能力要求的任务
        2. 同等条件优先高优先级
        3. 同等条件优先先到先得
        
        Returns:
            Task 或 None（没有合适的任务）
        """
        import json
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取所有待处理任务
        cursor.execute("""
            SELECT * FROM tasks
            WHERE status = ?
            ORDER BY priority DESC, created_at ASC
        """, (TaskStatus.PENDING.value,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # 匹配最合适的任务
        best_task = None
        best_match_score = -1
        
        for row in rows:
            task = self._row_to_task(row)
            
            # 计算匹配分数
            required = set(task.required_capabilities)
            available = set(capabilities)
            
            if not required:
                match_score = 1.0
            else:
                match_score = len(required & available) / len(required)
            
            # 检查截止时间
            if task.deadline and datetime.now().timestamp() > task.deadline:
                continue
            
            if match_score > best_match_score and match_score > 0:
                best_task = task
                best_match_score = match_score
        
        if best_task:
            return self._assign_task(best_task.id, agent_id)
        
        return None
    
    def _assign_task(self, task_id: str, agent_id: str) -> Task | None:
        """分配任务给 Agent"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().timestamp()
        
        cursor.execute("""
            UPDATE tasks
            SET status = ?, assigned_agent = ?, assigned_at = ?
            WHERE id = ?
        """, (TaskStatus.ASSIGNED.value, agent_id, now, task_id))
        
        conn.commit()
        conn.close()
        
        # 更新缓存
        if task_id in self._tasks:
            self._tasks[task_id].status = TaskStatus.ASSIGNED.value
            self._tasks[task_id].assigned_agent = agent_id
            self._tasks[task_id].assigned_at = now
        
        # 更新 Agent 任务列表
        if agent_id not in self._agent_tasks:
            self._agent_tasks[agent_id] = []
        self._agent_tasks[agent_id].append(task_id)
        
        return self._tasks.get(task_id)
    
    def start_task(self, task_id: str) -> bool:
        """开始执行任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE tasks
            SET status = ?
            WHERE id = ?
        """, (TaskStatus.IN_PROGRESS.value, task_id))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if affected > 0 and task_id in self._tasks:
            self._tasks[task_id].status = TaskStatus.IN_PROGRESS.value
        
        return affected > 0
    
    def complete_task(
        self,
        task_id: str,
        success: bool,
        quality_score: float = 0.5,
        completion_time: float = 0.0,
        result_data: dict | None = None
    ) -> float:
        """
        完成任务
        
        Returns:
            float: 实际获得的 VIBE 奖励
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        import json
        
        now = datetime.now().timestamp()
        
        status = TaskStatus.COMPLETED.value if success else TaskStatus.FAILED.value
        actual_reward = self._tasks[task_id].reward if success else self._tasks[task_id].reward * 0.1
        
        cursor.execute("""
            UPDATE tasks
            SET status = ?, completed_at = ?, result = ?
            WHERE id = ?
        """, (status, now, json.dumps(result_data or {}), task_id))
        
        # 记录结果
        cursor.execute("""
            INSERT INTO task_results
            (id, task_id, agent_id, success, quality_score, completion_time, result_data, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            task_id,
            self._tasks[task_id].assigned_agent,
            int(success),
            quality_score,
            completion_time,
            json.dumps(result_data or {}),
            now
        ))
        
        conn.commit()
        conn.close()
        
        # 更新缓存
        if task_id in self._tasks:
            self._tasks[task_id].status = status
            self._tasks[task_id].completed_at = now
            self._tasks[task_id].result = result_data
        
        return actual_reward
    
    def get_pending_tasks(self, limit: int = 10) -> list[Task]:
        """获取待处理任务"""
        import json
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM tasks
            WHERE status = ?
            ORDER BY priority DESC, created_at ASC
            LIMIT ?
        """, (TaskStatus.PENDING.value, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_task(row) for row in rows]
    
    def get_agent_tasks(self, agent_id: str, status: str | None = None) -> list[Task]:
        """获取 Agent 的任务列表"""
        import json
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status:
            cursor.execute("""
                SELECT * FROM tasks
                WHERE assigned_agent = ? AND status = ?
                ORDER BY created_at DESC
            """, (agent_id, status))
        else:
            cursor.execute("""
                SELECT * FROM tasks
                WHERE assigned_agent = ?
                ORDER BY created_at DESC
            """, (agent_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_task(row) for row in rows]
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        for status in TaskStatus:
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = ?", (status.value,))
            stats[status.value] = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT AVG(reward) FROM tasks WHERE status = ?", (TaskStatus.COMPLETED.value,))
        stats["avg_completed_reward"] = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM tasks")
        stats["total"] = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return stats
    
    def _row_to_task(self, row: tuple) -> Task:
        """数据库行转 Task 对象"""
        import json
        
        task_id = row[0]
        
        if task_id in self._tasks:
            return self._tasks[task_id]
        
        task = Task(
            id=row[0],
            task_type=row[1],
            title=row[2],
            description=row[3],
            required_capabilities=json.loads(row[4]),
            reward=row[5],
            deadline=row[6],
            priority=row[7],
            status=row[8],
            assigned_agent=row[9],
            created_at=row[10],
            assigned_at=row[11],
            completed_at=row[12],
            result=json.loads(row[13]) if row[13] else None
        )
        
        self._tasks[task_id] = task
        return task
    
    def seed_demo_tasks(self, count: int = 20) -> int:
        """
        填充演示任务
        
        Returns:
            int: 添加的任务数量
        """
        import random
        
        task_templates = [
            ("coding", "修复 Bug", "修复生产环境的 Bug", ["python", "debugging"]),
            ("coding", "编写测试", "为模块编写单元测试", ["python", "testing"]),
            ("analysis", "代码审查", "审查并优化代码", ["python", "review"]),
            ("design", "架构设计", "设计微服务架构", ["architecture", "design"]),
            ("coding", "API 开发", "开发 RESTful API", ["python", "api"]),
            ("analysis", "性能分析", "分析并优化性能瓶颈", ["profiling", "optimization"]),
            ("coding", "数据迁移", "执行数据库迁移", ["database", "sql"]),
            ("design", "方案设计", "设计技术方案", ["design", "documentation"]),
        ]
        
        added = 0
        for _ in range(count):
            template = random.choice(task_templates)
            reward = random.uniform(10, 200)
            
            self.add_task(
                task_type=template[0],
                title=template[1],
                description=template[2],
                required_capabilities=template[3],
                reward=reward,
                priority=random.randint(1, 4)
            )
            added += 1
        
        return added
