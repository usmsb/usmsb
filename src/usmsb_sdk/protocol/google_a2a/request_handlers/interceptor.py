"""
Interceptor - 请求拦截器链
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Awaitable

from pydantic import BaseModel


class InterceptorContext(BaseModel):
    """拦截器上下文"""
    method: str
    params: dict[str, Any]
    agent_id: str | None = None


class Interceptor(ABC):
    """
    请求拦截器基类

    拦截器可以：
    - 修改请求参数
    - 验证权限
    - 记录日志
    - 速率限制
    - 缓存响应

    拦截器按顺序执行，形成链式调用。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """拦截器名称"""
        pass

    async def on_request(
        self,
        context: InterceptorContext,
        next_handler: Callable[[], Awaitable[Any]],
    ) -> Any:
        """
        请求拦截

        Args:
            context: 请求上下文
            next_handler: 下一个处理器

        Returns:
            处理器响应
        """
        return await next_handler()

    async def on_response(
        self,
        context: InterceptorContext,
        response: Any,
    ) -> Any:
        """
        响应拦截

        Args:
            context: 请求上下文
            response: 处理器响应

        Returns:
            拦截后的响应
        """
        return response


class InterceptorChain:
    """
    拦截器链

    管理拦截器的执行顺序。
    """

    def __init__(self):
        self._interceptors: list[Interceptor] = []

    def add(self, interceptor: Interceptor) -> "InterceptorChain":
        """添加拦截器"""
        self._interceptors.append(interceptor)
        return self

    async def execute(
        self,
        context: InterceptorContext,
        final_handler: Callable[[], Awaitable[Any]],
    ) -> Any:
        """
        执行拦截器链

        Args:
            context: 请求上下文
            final_handler: 最终处理器

        Returns:
            处理结果
        """
        async def run_chain(index: int) -> Any:
            if index >= len(self._interceptors):
                return await final_handler()

            interceptor = self._interceptors[index]

            async def next_handler() -> Any:
                return await run_chain(index + 1)

            result = await interceptor.on_request(context, next_handler)
            return await interceptor.on_response(context, result)

        return await run_chain(0)
