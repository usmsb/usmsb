"""
内存缓存模块 - 用于API查询结果缓存

使用方式:
    from usmsb_sdk.api.cache import cache_manager, cached

    # 方式1: 使用装饰器
    @cached(ttl=60, prefix="demands")
    async def get_demands():
        return await db.query()

    # 方式2: 手动使用缓存管理器
    cache_key = "demands:list:all"
    result = cache_manager.get(cache_key)
    if not result:
        result = await db.query()
        cache_manager.set(cache_key, result, ttl=60)
"""

import hashlib
import json
import time
from collections.abc import Callable
from functools import wraps
from threading import Lock
from typing import Any


class TTLCache:
    """简单的TTL缓存实现"""

    def __init__(self, default_ttl: int = 60):
        self._cache: dict[str, tuple] = {}
        self._lock = Lock()
        self.default_ttl = default_ttl

    def get(self, key: str) -> Any | None:
        """获取缓存，如果过期返回None"""
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if time.time() < expiry:
                    return value
                # 已过期，删除
                del self._cache[key]
            return None

    def set(self, key: str, value: Any, ttl: int | None = None):
        """设置缓存"""
        with self._lock:
            ttl = ttl or self.default_ttl
            expiry = time.time() + ttl
            self._cache[key] = (value, expiry)

    def delete(self, key: str):
        """删除指定缓存"""
        with self._lock:
            self._cache.pop(key, None)

    def invalidate_prefix(self, prefix: str):
        """删除所有以prefix开头的缓存"""
        with self._lock:
            keys = [k for k in self._cache if k.startswith(prefix)]
            for key in keys:
                del self._cache[key]

    def clear(self):
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()

    def stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            now = time.time()
            valid = sum(1 for _, exp in self._cache.values() if exp > now)
            expired = len(self._cache) - valid
            return {
                "total_keys": len(self._cache),
                "valid_entries": valid,
                "expired_entries": expired,
            }


class CacheManager:
    """缓存管理器 - 管理多个缓存实例"""

    def __init__(self):
        # 不同类型数据使用不同的TTL
        self.agents = TTLCache(default_ttl=120)      # agents: 2分钟
        self.demands = TTLCache(default_ttl=60)      # demands: 1分钟
        self.services = TTLCache(default_ttl=60)      # services: 1分钟
        self.environments = TTLCache(default_ttl=300) # environments: 5分钟
        self.workflows = TTLCache(default_ttl=60)   # workflows: 1分钟
        self.demands = TTLCache(default_ttl=60)     # demands: 1分钟
        self.metrics = TTLCache(default_ttl=30)     # metrics: 30秒
        self.collaborations = TTLCache(default_ttl=60)

    def get_cache(self, prefix: str) -> TTLCache:
        """根据prefix获取对应的缓存实例"""
        cache_map = {
            "agents": self.agents,
            "demands": self.demands,
            "services": self.services,
            "environments": self.environments,
            "workflows": self.workflows,
            "metrics": self.metrics,
            "collaborations": self.collaborations,
        }
        return cache_map.get(prefix, self.agents)

    def invalidate_all(self, prefix: str):
        """失效指定类型的所有缓存"""
        cache = self.get_cache(prefix)
        cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """获取所有缓存的统计信息"""
        return {
            "agents": self.agents.stats(),
            "demands": self.demands.stats(),
            "services": self.services.stats(),
            "environments": self.environments.stats(),
            "workflows": self.workflows.stats(),
            "metrics": self.metrics.stats(),
            "collaborations": self.collaborations.stats(),
        }


# 全局缓存管理器实例
cache_manager = CacheManager()


def generate_cache_key(prefix: str, **kwargs) -> str:
    """根据参数生成缓存键

    Args:
        prefix: 缓存前缀 (如 'agents', 'demands')
        **kwargs: 查询参数

    Returns:
        缓存键字符串
    """
    if not kwargs:
        return f"{prefix}:all"

    # 将参数按键排序后生成hash
    sorted_params = sorted(kwargs.items())
    param_str = json.dumps(sorted_params, sort_keys=True)
    param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]

    return f"{prefix}:{param_hash}"


def cached(ttl: int = 60, prefix: str = "default"):
    """缓存装饰器

    Args:
        ttl: 缓存过期时间（秒）
        prefix: 缓存前缀，用于选择对应的缓存实例
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = generate_cache_key(prefix, **kwargs)

            # 尝试从缓存获取
            cache = cache_manager.get_cache(prefix)
            cached_value = cache.get(cache_key)

            if cached_value is not None:
                return cached_value

            # 执行原函数
            result = await func(*args, **kwargs)

            # 设置缓存
            cache.set(cache_key, result, ttl=ttl)

            return result
        return wrapper
    return decorator


# 便捷函数
def get_cached(prefix: str, key: str) -> Any | None:
    """获取缓存值"""
    return cache_manager.get_cache(prefix).get(key)


def set_cached(prefix: str, key: str, value: Any, ttl: int | None = None):
    """设置缓存值"""
    cache_manager.get_cache(prefix).set(key, value, ttl=ttl)


def invalidate_cache(prefix: str, key: str | None = None):
    """失效缓存"""
    cache = cache_manager.get_cache(prefix)
    if key:
        cache.delete(key)
    else:
        cache.invalidate_prefix(prefix)
