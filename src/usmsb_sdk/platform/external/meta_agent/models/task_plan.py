"""
任务计划数据结构

设计初衷：
============
复杂任务（如创建网站、构建应用）需要分步执行：
1. 先规划任务步骤（快速返回）
2. 用户确认计划
3. 逐步执行每个步骤
4. 每步独立超时，避免整体超时

核心原则：
- 简单任务：直接执行（当前流程）
- 复杂任务：规划 → 确认 → 分步执行
- 每步可独立重试
- 支持断点续传
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskComplexity(Enum):
    """任务复杂度级别"""
    LOW = "low"           # 简单对话，直接回答
    MEDIUM = "medium"     # 需要工具调用，但任务简单
    HIGH = "high"         # 复杂任务，需要分步执行
    VERY_HIGH = "very_high"  # 超复杂任务，需要用户确认计划


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskStatus(Enum):
    """任务状态"""
    PLANNING = "planning"       # 正在规划
    AWAITING_CONFIRM = "awaiting_confirm"  # 等待用户确认
    EXECUTING = "executing"     # 正在执行
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"           # 失败
    CANCELLED = "cancelled"     # 已取消


@dataclass
class TaskStep:
    """
    任务步骤

    每个步骤应该是：
    - 独立可执行的
    - 预计执行时间短（< 60秒）
    - 有明确的输入和输出
    """
    step_id: str
    """步骤唯一标识"""

    name: str
    """步骤名称"""

    description: str
    """步骤描述"""

    action: str
    """要执行的动作类型：create_file, create_directory, write_code, execute, etc."""

    params: dict[str, Any] = field(default_factory=dict)
    """执行参数"""

    dependencies: list[str] = field(default_factory=list)
    """依赖的步骤 ID 列表"""

    estimated_time: int = 30
    """预计执行时间（秒）"""

    status: StepStatus = StepStatus.PENDING
    """当前状态"""

    result: dict[str, Any] | None = None
    """执行结果"""

    error: str | None = None
    """错误信息"""

    retry_count: int = 0
    """重试次数"""

    max_retries: int = 2
    """最大重试次数"""


@dataclass
class TaskPlan:
    """
    任务计划

    包含完整的任务分解和执行状态
    """
    task_id: str
    """任务唯一标识"""

    user_request: str
    """用户原始请求"""

    complexity: TaskComplexity
    """任务复杂度"""

    steps: list[TaskStep] = field(default_factory=list)
    """执行步骤列表"""

    status: TaskStatus = TaskStatus.PLANNING
    """任务状态"""

    current_step_index: int = 0
    """当前执行到的步骤索引"""

    created_at: datetime = field(default_factory=datetime.now)
    """创建时间"""

    updated_at: datetime = field(default_factory=datetime.now)
    """更新时间"""

    wallet_address: str | None = None
    """用户钱包地址"""

    conversation_id: str | None = None
    """关联的会话 ID"""

    context: dict[str, Any] = field(default_factory=dict)
    """执行上下文"""

    def get_total_estimated_time(self) -> int:
        """获取总预计时间"""
        return sum(step.estimated_time for step in self.steps)

    def get_completed_steps(self) -> list[TaskStep]:
        """获取已完成的步骤"""
        return [s for s in self.steps if s.status == StepStatus.COMPLETED]

    def get_pending_steps(self) -> list[TaskStep]:
        """获取待执行的步骤"""
        return [s for s in self.steps if s.status == StepStatus.PENDING]

    def get_current_step(self) -> TaskStep | None:
        """获取当前步骤"""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def get_progress_percentage(self) -> float:
        """获取执行进度百分比"""
        if not self.steps:
            return 0.0
        completed = len(self.get_completed_steps())
        return (completed / len(self.steps)) * 100

    def can_execute_step(self, step: TaskStep) -> bool:
        """检查步骤是否可以执行（依赖是否满足）"""
        for dep_id in step.dependencies:
            dep_step = next((s for s in self.steps if s.step_id == dep_id), None)
            if dep_step and dep_step.status != StepStatus.COMPLETED:
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "user_request": self.user_request,
            "complexity": self.complexity.value,
            "status": self.status.value,
            "current_step_index": self.current_step_index,
            "progress_percentage": self.get_progress_percentage(),
            "total_steps": len(self.steps),
            "completed_steps": len(self.get_completed_steps()),
            "estimated_time": self.get_total_estimated_time(),
            "steps": [
                {
                    "step_id": s.step_id,
                    "name": s.name,
                    "description": s.description,
                    "action": s.action,  # 🔧 修复：保存 action 字段
                    "params": s.params,  # 🔧 修复：保存 params 字段
                    "dependencies": s.dependencies,  # 🔧 修复：保存 dependencies 字段
                    "status": s.status.value,
                    "estimated_time": s.estimated_time,
                    "result": s.result,  # 🔧 修复：保存 result 字段
                    "error": s.error,  # 🔧 修复：保存 error 字段
                    "retry_count": s.retry_count,  # 🔧 修复：保存 retry_count 字段
                }
                for s in self.steps
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class StepResult:
    """步骤执行结果"""
    step_id: str
    success: bool
    output: str | None = None
    data: dict[str, Any] | None = None
    error: str | None = None
    execution_time: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "success": self.success,
            "output": self.output,
            "data": self.data,
            "error": self.error,
            "execution_time": self.execution_time,
        }


# 复杂任务关键词检测
COMPLEXITY_INDICATORS = {
    TaskComplexity.VERY_HIGH: [
        "创建网站", "创建一个网站", "建一个网站", "做个网站",
        "创建应用", "构建应用", "开发应用",
        "构建系统", "设计架构", "完整项目",
        "独立站", "电商网站", "在线商城",
        "管理系统", "企业系统", "创建系统", "构建平台",
        "完整电商", "完整系统", "完整应用", "大型项目",
        "企业级", "复杂系统", "平台系统", "电商系统",
    ],
    TaskComplexity.HIGH: [
        "创建多个", "批量处理", "同时创建",
        "写一个完整", "实现一个完整",
        "帮我设计", "帮我规划", "帮我构建",
        "分步骤", "多文件", "项目结构",
    ],
    TaskComplexity.MEDIUM: [
        "创建文件", "读取并分析", "搜索并整理",
        "写一个脚本", "生成代码", "执行命令",
        "复制文件", "移动文件", "重命名",
        "帮我搜索", "搜索", "帮我查询", "查询",
    ],
    TaskComplexity.LOW: [
        "你好", "什么是", "解释一下", "介绍一下",
        "告诉我", "怎么看", "如何使用", "用法",
    ],
}


def detect_task_complexity(message: str) -> TaskComplexity:
    """
    检测任务复杂度

    Args:
        message: 用户消息

    Returns:
        任务复杂度级别
    """
    message_lower = message.lower()

    # 按优先级检查（从高到低）
    for complexity, keywords in COMPLEXITY_INDICATORS.items():
        for keyword in keywords:
            if keyword in message_lower:
                return complexity

    # 默认为中等复杂度（可能需要工具调用）
    return TaskComplexity.MEDIUM


def should_use_step_by_step(complexity: TaskComplexity) -> bool:
    """
    判断是否应该使用分步执行

    Args:
        complexity: 任务复杂度

    Returns:
        是否使用分步执行
    """
    return complexity in [TaskComplexity.HIGH, TaskComplexity.VERY_HIGH]


def should_confirm_plan(complexity: TaskComplexity) -> bool:
    """
    判断是否需要用户确认计划

    Args:
        complexity: 任务复杂度

    Returns:
        是否需要确认
    """
    return complexity == TaskComplexity.VERY_HIGH
