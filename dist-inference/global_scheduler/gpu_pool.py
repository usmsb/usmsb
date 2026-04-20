"""
GPU Resource Pool Management - persisted to SQLite
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Tuple
import httpx

from shared.types import NodeCapability, NodeStatus, ModelInfo, GPUInfo
from . import db


class GPUPool:
    """
    Manages all GPU nodes — persisted to SQLite.
    In-memory dict is a cache backed by SQLite.
    """

    def __init__(self):
        self.nodes: Dict[str, NodeCapability] = {}
        self.lock = asyncio.Lock()
        self.heartbeat_timeout = 30  # seconds

    async def load_from_db(self) -> None:
        """Load nodes from SQLite into memory. Call after db.init_db()."""
        conn = await db.get_db()
        async with conn.execute("SELECT * FROM gpu_nodes") as cur:
            rows = await cur.fetchall()
        for row in rows:
            gpus = []
            util_list = json.loads(row["gpu_utilization"] or "[]")
            for i, util in enumerate(util_list):
                gpus.append(GPUInfo(gpu_id=i, gpu_type=row["gpu_type"], utilization=util, memory_used_gb=0))
            node = NodeCapability(
                node_id=row["node_id"],
                hostname=row["hostname"],
                port=row["port"],
                gpu_count=row["gpu_count"],
                gpu_type=row["gpu_type"],
                total_vram_gb=row["total_vram_gb"],
                available_vram_gb=row["available_vram_gb"],
                status=NodeStatus[row["status"].upper()],
                gpus=gpus,
                loaded_models=json.loads(row["loaded_models"] or "[]"),
                last_heartbeat=row["last_heartbeat"],
            )
            self.nodes[row["node_id"]] = node

    async def register_node(self, node: NodeCapability) -> None:
        """Register a new node (writes to SQLite + memory)"""
        async with self.lock:
            self.nodes[node.node_id] = node
            await self._save_node(node)
            print(f"[GPUPool] Node registered: {node.node_id} @ {node.hostname}:{node.port}")
            print(f"         GPUs: {node.gpu_count}x {node.gpu_type}")
            print(f"         VRAM: {node.total_vram_gb}GB total, {node.available_vram_gb}GB available")

    async def _save_node(self, node: NodeCapability) -> None:
        """Persist node to SQLite"""
        conn = await db.get_db()
        gpu_util = json.dumps([g.utilization for g in node.gpus])
        await conn.execute(
            """INSERT INTO gpu_nodes
               (node_id, hostname, port, gpu_count, gpu_type, total_vram_gb,
                available_vram_gb, status, loaded_models, last_heartbeat, gpu_utilization)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(node_id) DO UPDATE SET
                   hostname=excluded.hostname, port=excluded.port,
                   gpu_count=excluded.gpu_count, gpu_type=excluded.gpu_type,
                   total_vram_gb=excluded.total_vram_gb,
                   available_vram_gb=excluded.available_vram_gb,
                   status=excluded.status,
                   loaded_models=excluded.loaded_models,
                   last_heartbeat=excluded.last_heartbeat,
                   gpu_utilization=excluded.gpu_utilization""",
            (
                node.node_id, node.hostname, node.port,
                node.gpu_count, node.gpu_type,
                node.total_vram_gb, node.available_vram_gb,
                node.status.name, json.dumps(node.loaded_models),
                node.last_heartbeat, gpu_util,
            ),
        )
        await conn.commit()

    async def heartbeat(
        self,
        node_id: str,
        status: str,
        loaded_models: List[str],
        gpu_utilization: List[float],
        available_vram_gb: int
    ) -> None:
        """Update node heartbeat (writes to SQLite + memory)"""
        async with self.lock:
            if node_id not in self.nodes:
                return
            node = self.nodes[node_id]
            node.status = NodeStatus[status.upper()]
            node.loaded_models = loaded_models
            node.available_vram_gb = available_vram_gb
            node.last_heartbeat = time.time()
            for i, util in enumerate(gpu_utilization):
                if i < len(node.gpus):
                    node.gpus[i].utilization = util
            await self._save_node(node)

    async def select_node(
        self, model_name: str, model_registry, exclude_node_ids: Optional[List[str]] = None
    ) -> Optional[Tuple["NodeExecutor", int]]:
        """
        Select the most suitable node for executing a model
        """
        async with self.lock:
            self._cleanup_timeout_nodes()
            exclude = set(exclude_node_ids or [])

            model_info = model_registry.get(model_name)
            if not model_info:
                candidates = [
                    n for n in self.nodes.values()
                    if n.status == NodeStatus.IDLE
                    and n.available_vram_gb > 0
                    and n.node_id not in exclude
                ]
            else:
                required_vram = model_info.min_vram_per_gpu_gb * model_info.min_gpu_count
                candidates = [
                    n for n in self.nodes.values()
                    if n.status == NodeStatus.IDLE
                    and n.gpu_count >= model_info.min_gpu_count
                    and n.available_vram_gb >= required_vram
                    and n.node_id not in exclude
                ]

            if not candidates:
                return None

            def score(n: NodeCapability) -> Tuple[int, int, float]:
                model_loaded = 1 if model_name in n.loaded_models else 0
                return (
                    model_loaded,
                    n.available_vram_gb,
                    -sum(g.utilization for g in n.gpus)
                )

            candidates.sort(key=score, reverse=True)
            selected = candidates[0]
            estimated_seconds = 1.0
            return NodeExecutor(selected, self), estimated_seconds

    def _cleanup_timeout_nodes(self) -> None:
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
    """Represents a remote node executor"""

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
                from shared.types import InferenceResponse
                response = InferenceResponse(**data)

                if response.error:
                    raise RuntimeError(
                        f"Node {self.capability.node_id} returned error: {response.error}"
                    )
                if not response.content:
                    raise RuntimeError(
                        f"Node {self.capability.node_id} returned empty content"
                    )

                return response

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
