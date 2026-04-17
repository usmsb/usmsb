"""
Request Router
"""

import asyncio
from typing import Optional

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
        self.max_retries = 3

    async def execute(self, request: InferenceRequest) -> InferenceResponse:
        """
        Execute inference request with retry logic
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                # Select node
                result = await self.gpu_pool.select_node(
                    request.model_name,
                    self.model_registry
                )

                if not result:
                    raise RuntimeError(
                        f"No available GPU node for model '{request.model_name}'"
                    )

                node_executor, estimated_seconds = result

                # Mark node as busy
                await node_executor.set_busy()

                try:
                    # Execute inference
                    response = await node_executor.execute(request)
                    return response

                finally:
                    # Mark node as idle
                    await node_executor.set_idle()

            except Exception as e:
                last_error = e
                print(f"[Router] Attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(0.5)  # Brief wait before retry

        # All retries failed
        raise RuntimeError(
            f"All {self.max_retries} attempts failed. Last error: {last_error}"
        )
