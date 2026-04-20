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
        Execute inference request with retry logic, excluding failed nodes
        """
        last_error = None
        failed_node_ids: list[str] = []

        for attempt in range(self.max_retries):
            try:
                # Select node, excluding nodes that just failed
                result = await self.gpu_pool.select_node(
                    request.model_name,
                    self.model_registry,
                    exclude_node_ids=failed_node_ids,
                )

                if not result:
                    raise RuntimeError(
                        f"No available GPU node for model '{request.model_name}'"
                    )

                node_executor, estimated_seconds = result
                current_node_id = node_executor.capability.node_id

                # Mark node as busy
                await node_executor.set_busy()

                try:
                    # Execute inference
                    response = await node_executor.execute(request)
                    return response

                except Exception as e:
                    # Record failed node so we don't retry it
                    if current_node_id not in failed_node_ids:
                        failed_node_ids.append(current_node_id)
                    raise

                finally:
                    # Mark node as idle
                    await node_executor.set_idle()

            except Exception as e:
                last_error = e
                print(f"[Router] Attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(0.5)

        # All retries failed
        raise RuntimeError(
            f"All {self.max_retries} attempts failed. Last error: {last_error}"
        )
