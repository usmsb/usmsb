"""
Demo 工具函数

提供通用的工具函数和辅助类。
"""

import json
import uuid
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path


def generate_id(prefix: str = "") -> str:
    """生成唯一 ID"""
    unique = uuid.uuid4().hex[:8]
    return f"{prefix}_{unique}" if prefix else unique


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """格式化时间戳"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def pretty_print(data: Any, indent: int = 2) -> str:
    """美化打印"""
    if isinstance(data, dict) or isinstance(data, list):
        return json.dumps(data, ensure_ascii=False, indent=indent)
    return str(data)


def save_scenario_log(scenario_name: str, data: Dict, log_dir: Optional[Path] = None) -> Path:
    """保存场景日志"""
    if log_dir is None:
        log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"{scenario_name}_{timestamp}.json"

    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return log_file


def load_scenario_config(scenario_name: str) -> Dict:
    """加载场景配置"""
    config_dir = Path(__file__).parent.parent / scenario_name
    config_file = config_dir / "config.json"

    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


class Timer:
    """计时器"""

    def __init__(self, name: str = ""):
        self.name = name
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        self.end_time = time.time()

    @property
    def elapsed(self) -> float:
        """已用时间（秒）"""
        if self.start_time is None:
            return 0
        end = self.end_time or time.time()
        return end - self.start_time

    def __str__(self) -> str:
        return f"{self.name}: {self.elapsed:.2f}s"


class Metrics:
    """指标收集器"""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.counts: Dict[str, int] = {}

    def record(self, name: str, value: float):
        """记录指标"""
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(value)

    def increment(self, name: str, count: int = 1):
        """增加计数"""
        if name not in self.counts:
            self.counts[name] = 0
        self.counts[name] += count

    def get_average(self, name: str) -> float:
        """获取平均值"""
        if name not in self.metrics or not self.metrics[name]:
            return 0
        return sum(self.metrics[name]) / len(self.metrics[name])

    def get_sum(self, name: str) -> float:
        """获取总和"""
        if name not in self.metrics:
            return 0
        return sum(self.metrics[name])

    def get_count(self, name: str) -> int:
        """获取计数"""
        return self.counts.get(name, 0)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "metrics": {
                k: {"avg": self.get_average(k), "sum": self.get_sum(k)}
                for k in self.metrics
            },
            "counts": self.counts,
        }
