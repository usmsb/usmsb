"""
Request Router
"""

from shared.types import InferenceRequest, InferenceResponse

from .gpu_pool import GPUPool
from .model_registry import ModelRegistry


class Router:
    """
    Request Router: select node -> send request -> return result
    """

    def __init__(self, gpu_pool: GPUPool, model_registry: ModelRegistry):
        self.gpu_pool = gpu_pool
        self.model_registry = model_registry

    async def execute(self, request: InferenceRequest) -> InferenceResponse:
        """
        Execute one inference request exactly once.

        A timeout or network error is ambiguous: the remote vLLM process may
        already have generated tokens.  Re-dispatching to another node would
        create a second physical LLM call and duplicate usage, so paid
        inference is deliberately single-shot.
        """
        result = await self.gpu_pool.select_node(
            request.model_name,
            self.model_registry,
        )
        if not result:
            raise RuntimeError(
                f"No available GPU node for model '{request.model_name}'"
            )

        node_executor, _estimated_seconds = result
        await node_executor.set_busy()
        try:
            return await node_executor.execute(request)
        finally:
            await node_executor.set_idle()
