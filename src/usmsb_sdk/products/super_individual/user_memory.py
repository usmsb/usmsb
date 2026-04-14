# -*- coding: utf-8 -*-
"""
UserMemory - 用户记忆系统

为超级个体加载用户价值观、习惯、偏好。

功能：
- 用户画像存储
- 价值观加载
- 习惯追踪
- 偏好管理
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class UserValue:
    """用户价值观"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""  # 价值观名称
    description: str = ""
    strength: float = 0.5  # 强度 0-1
    examples: list[str] = field(default_factory=list)  # 例子
    source: str = "explicit"  # explicit, inferred


@dataclass
class UserHabit:
    """用户习惯"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    frequency: str = "daily"  # daily, weekly, occasional
    time_preference: str = ""  # 偏好时间
    last_performed: float | None = None
    success_rate: float = 0.5


@dataclass
class UserPreference:
    """用户偏好"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: str = ""  # communication, work, lifestyle, etc.
    key: str = ""
    value: Any = None
    confidence: float = 0.5


@dataclass
class UserProfile:
    """完整用户画像"""
    user_id: str
    name: str = ""
    bio: str = ""
    goals: list[str] = field(default_factory=list)
    values: list[UserValue] = field(default_factory=list)
    habits: list[UserHabit] = field(default_factory=list)
    preferences: list[UserPreference] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())


class UserMemory:
    """
    用户记忆系统
    
    管理用户的完整画像，供 Butler Agent 使用。
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.profile: UserProfile | None = None
        
        # 缓存
        self._values_cache: dict[str, UserValue] = {}
        self._preferences_cache: dict[str, Any] = {}
        
        print(f"[UserMemory] Initialized for user: {user_id}")
    
    def load_profile(self, profile: UserProfile) -> None:
        """加载用户画像"""
        self.profile = profile
        self.profile.updated_at = datetime.now().timestamp()
        
        # 构建缓存
        self._build_caches()
        
        print(f"[UserMemory] Profile loaded: {profile.name}")
    
    def _build_caches(self) -> None:
        """构建缓存"""
        if not self.profile:
            return
        
        # 价值观缓存
        self._values_cache = {v.name: v for v in self.profile.values}
        
        # 偏好缓存
        self._preferences_cache = {
            f"{p.category}.{p.key}": p.value
            for p in self.profile.preferences
        }
    
    def get_value(self, value_name: str) -> UserValue | None:
        """获取价值观"""
        return self._values_cache.get(value_name)
    
    def get_preference(self, category: str, key: str) -> Any | None:
        """获取偏好"""
        return self._preferences_cache.get(f"{category}.{key}")
    
    def add_value(self, value: UserValue) -> None:
        """添加价值观"""
        if not self.profile:
            self.profile = UserProfile(user_id=self.user_id)
        
        self.profile.values.append(value)
        self._values_cache[value.name] = value
        self.profile.updated_at = datetime.now().timestamp()
    
    def add_habit(self, habit: UserHabit) -> None:
        """添加习惯"""
        if not self.profile:
            self.profile = UserProfile(user_id=self.user_id)
        
        self.profile.habits.append(habit)
        self.profile.updated_at = datetime.now().timestamp()
    
    def set_preference(
        self,
        category: str,
        key: str,
        value: Any
    ) -> None:
        """设置偏好"""
        if not self.profile:
            self.profile = UserProfile(user_id=self.user_id)
        
        # 查找或创建
        for pref in self.profile.preferences:
            if pref.category == category and pref.key == key:
                pref.value = value
                break
        else:
            pref = UserPreference(
                category=category,
                key=key,
                value=value
            )
            self.profile.preferences.append(pref)
        
        self._preferences_cache[f"{category}.{key}"] = value
        self.profile.updated_at = datetime.now().timestamp()
    
    def update_goal(self, goal: str, completed: bool = False) -> None:
        """更新目标"""
        if not self.profile:
            return
        
        if completed and goal in self.profile.goals:
            self.profile.goals.remove(goal)
        
        self.profile.updated_at = datetime.now().timestamp()
    
    def get_dominant_values(self, top_k: int = 3) -> list[UserValue]:
        """获取最重要的价值观"""
        if not self.profile:
            return []
        
        sorted_values = sorted(
            self.profile.values,
            key=lambda v: v.strength,
            reverse=True
        )
        return sorted_values[:top_k]
    
    def get_daily_habits(self) -> list[UserHabit]:
        """获取日常习惯"""
        if not self.profile:
            return []
        
        return [h for h in self.profile.habits if h.frequency == "daily"]
    
    def infer_preference(self, category: str, key: str) -> Any | None:
        """推断偏好（基于历史）"""
        return self.get_preference(category, key)
    
    def describe_user(self) -> str:
        """生成用户描述"""
        if not self.profile:
            return "Unknown user"
        
        values = self.get_dominant_values(3)
        values_desc = ", ".join([v.name for v in values]) if values else "未定义"
        
        habits = self.get_daily_habits()
        habits_desc = ", ".join([h.name for h in habits]) if habits else "无"
        
        return f"""
用户：{self.profile.name}
简介：{self.profile.bio or "无"}
核心价值观：{values_desc}
日常习惯：{habits_desc}
        """.strip()
    
    def to_dict(self) -> dict:
        if not self.profile:
            return {"user_id": self.user_id, "loaded": False}
        
        return {
            "user_id": self.profile.user_id,
            "name": self.profile.name,
            "bio": self.profile.bio,
            "goals": self.profile.goals,
            "values": [
                {"name": v.name, "strength": v.strength}
                for v in self.profile.values
            ],
            "habits": [
                {"name": h.name, "frequency": h.frequency}
                for h in self.profile.habits
            ],
            "preferences_count": len(self.profile.preferences),
            "loaded": True,
        }
    
    def __repr__(self) -> str:
        return f"UserMemory({self.user_id}, loaded={self.profile is not None})"
