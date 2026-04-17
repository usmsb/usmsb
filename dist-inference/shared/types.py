"""
Shared data types for USMSB Distributed Inference
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import time
import uuid


class NodeStatus(Enum):
    """Node status"""
    OFFLINE = "offline"
    IDLE = "idle"
    BUSY = "busy"


class ModelType(Enum):
    """Model type"""
    CHAT = "chat"
    VIDEO = "video"
    IMAGE = "image"
    AUDIO = "audio"


@dataclass
class GPUInfo:
    """Single GPU information"""
    gpu_id: int
    gpu_type: str  # "A100", "RTX 4090", etc.
    vram_gb: int  # Total VRAM
    used_vram_gb: float = 0.0  # Used VRAM
    utilization: float = 0.0  # Utilization 0.0~1.0


@dataclass
class NodeCapability:
    """Node capability"""
    node_id: str
    hostname: str
    port: int = 8080  # Node Executor port
    status: NodeStatus = NodeStatus.IDLE
    gpu_count: int = 0
    gpus: List[GPUInfo] = field(default_factory=list)
    total_vram_gb: int = 0
    available_vram_gb: int = 0
    loaded_models: List[str] = field(default_factory=list)
    capabilities: Dict[str, Any] = field(default_factory=dict)
    last_heartbeat: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.gpus:
            self.gpus = []


@dataclass
class ModelInfo:
    """Model information"""
    model_name: str  # HuggingFace model name
    model_type: ModelType = ModelType.CHAT
    min_gpu_count: int = 1  # Min GPU count required
    min_vram_per_gpu_gb: int = 16  # Min VRAM per GPU
    context_length: int = 4096  # Context length
    is_preloaded: bool = False  # Is preloaded
    model_path: Optional[str] = None  # Local path (if any)


@dataclass
class InferenceRequest:
    """Inference request"""
    request_id: str
    model_name: str
    messages: List[Dict[str, str]]  # OpenAI format
    temperature: float = 0.7
    max_tokens: int = 2048
    user_id: str = "anonymous"

    @classmethod
    def create(cls, model_name: str, messages: List[Dict[str, str]], **kwargs):
        return cls(
            request_id=f"req_{uuid.uuid4().hex[:12]}",
            model_name=model_name,
            messages=messages,
            **kwargs
        )


@dataclass
class InferenceResponse:
    """Inference response"""
    request_id: str
    model_name: str
    content: str
    usage: Dict[str, int]  # {"prompt_tokens": X, "completion_tokens": Y, "total_tokens": Z}
    gpu_seconds: float  # GPU card time
    cost_vibe: float  # Vibe cost
    node_id: str
    finish_reason: str = "stop"
    error: Optional[str] = None


@dataclass
class NodeRegisterRequest:
    """Node registration request"""
    node_id: str
    hostname: str
    gpu_count: int
    gpu_type: str
    total_vram_gb: int
    available_vram_gb: int
    port: int = 8080
    loaded_models: List[str] = field(default_factory=list)
    capabilities: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HeartbeatRequest:
    """Heartbeat request"""
    node_id: str
    status: str  # "idle" | "busy" | "offline"
    loaded_models: List[str] = field(default_factory=list)
    gpu_utilization: List[float] = field(default_factory=list)
    available_vram_gb: int = 0
