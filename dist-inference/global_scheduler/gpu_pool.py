"""
GPU Resource Pool Management
"""

import asyncio
from typing import Dict, List, Optional, Tuple
import time
import httpx

from shared.types import NodeCapability, NodeStatus, ModelInfo, GPUInfo


class GPUPool:
    """
    Manages all GPU nodes
    """

    def __init__(self):
        self.nodes: Dict[str, NodeCapability] = {}
        self.lock = asyncio.Lock()
        self.heartbeat_timeout = 30  # seconds

    async def register_node(self, node: NodeCapability):
        """Register a new node"""
        async with self.lock:
            self.nodes[node.node_id] = node
            print(f"[GPUPool] Node registered: {node.node_id} @ {node.hostname}:{node.port}")
            print(f"         GPUs: {node.gpu_count}x {node.gpus[0].gpu_type if node.gpus else 'Unknown'}")
            print(f"         VRAM: {node.total_vram_gb}GB total, {node.available_vram_gb}GB available")

    async def heartbeat(
        self,
        node_id: str,
        status: str,
        loaded_models: List[str],
        gpu_utilization: List[float],
        available_vram_gb: int
    ):
        """Update node heartbeat"""
        async with self.lock:
            if node_id not in self.nodes:
                return

            node = self.nodes[node_id]
            node.status = NodeStatus[status.upper()]
            node.loaded_models = loaded_models
            node.available_vram_gb = available_vram_gb
            node.last_heartbeat = time.time()

            # Update GPU utilization
            for i, util in enumerate(gpu_utilization):
                if i < len(node.gpus):
                    node.gpus[i].utilization = util

    async def select_node(self, model_name: str, model_registry) -> Optional[Tuple["NodeExecutor", int]]:
        """
        Select the most suitable node for executing a model

        Returns:
            (NodeExecutor, estimated_gpu_seconds) or None
        """
        async with self.lock:
            # Cleanup timed out nodes
            self._cleanup_timeout_nodes()

            # Get model requirements
            model_info = model_registry.get(model_name)
            if not model_info:
                # Unknown model, find a node with spare VRAM
                candidates = [
                    n for n in self.nodes.values()
                    if n.status == NodeStatus.IDLE and n.available_vram_gb > 0
                ]
            else:
                # Filter nodes that meet requirements
                required_vram = model_info.min_vram_per_gpu_gb * model_info.min_gpu_count
                candidates = [
                    n for n in self.nodes.values()
                    if n.status == NodeStatus.IDLE
                    and n.gpu_count >= model_info.min_gpu_count
                    and n.available_vram_gb >= required_vram
                ]

            if not candidates:
                return None

            # Sorting strategy:
            # 1. Prefer nodes with target model already loaded (avoid cold start)
            # 2. More available VRAM is better
            # 3. Lower GPU utilization is better
            def score(node: NodeCapability) -> Tuple[int, int, float]:
                model_loaded = 1 if model_name in node.loaded_models else 0
                return (
                    model_loaded,
                    node.available_vram_gb,
                    -sum(g.utilization for g in node.gpus)  # Lower is better
                )

            candidates.sort(key=score, reverse=True)
            selected = candidates[0]

            # Estimate GPU usage time (simplified)
            estimated_seconds = 1.0  # TODO: estimate based on model and token count

            return NodeExecutor(selected, self), estimated_seconds

    def _cleanup_timeout_nodes(self):
        """Cleanup nodes with heartbeat timeout"""
        now = time.time()
        for node_id, node in list(self.nodes.items()):
            if now - node.last_heartbeat > self.heartbeat_timeout:
                print(f"[GPUPool] Node timed out: {node_id}")
                node.status = NodeStatus.OFFLINE

    def get_all_nodes(self) -> List[NodeCapability]:
        return list(self.nodes.values())

    def get_summary(self) -> Dict:
        return {
            "total_nodes": len(self.nodes),
            "idle_nodes": len([n for n in self.nodes.values() if n.status == NodeStatus.IDLE]),
            "busy_nodes": len([n for n in self.nodes.values() if n.status == NodeStatus.BUSY]),
            "offline_nodes": len([n for n in self.nodes.values() if n.status == NodeStatus.OFFLINE]),
        }


class NodeExecutor:
    """
    Represents a remote node executor
    """

    def __init__(self, capability: NodeCapability, pool: GPUPool):
        self.capability = capability
        self.pool = pool
        self.base_url = f"http://{capability.hostname}:{capability.port}"

    async def execute(self, request) -> "InferenceResponse":
        """Execute inference by calling the remote node via HTTP"""
        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/inference",
                    json={
                        "request_id": request.request_id,
                        "model_name": request.model_name,
                        "messages": request.messages,
                        "temperature": request.temperature,
                        "max_tokens": request.max_tokens
                    }
                )
                resp.raise_for_status()
                data = resp.json()

                # Convert dict to InferenceResponse
                from shared.types import InferenceResponse
                return InferenceResponse(**data)

            except httpx.HTTPError as e:
                raise RuntimeError(f"Node {self.capability.node_id} execution failed: {e}")

    async def set_busy(self):
        """Mark node as busy"""
        async with self.pool.lock:
            self.capability.status = NodeStatus.BUSY

    async def set_idle(self):
        """Mark node as idle"""
        async with self.pool.lock:
            self.capability.status = NodeStatus.IDLE
