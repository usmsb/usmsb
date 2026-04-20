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
    wallet_address: str = ""


@dataclass
class HeartbeatRequest:
    """Heartbeat request"""
    node_id: str
    status: str  # "idle" | "busy" | "offline"
    loaded_models: List[str] = field(default_factory=list)
    gpu_utilization: List[float] = field(default_factory=list)
    available_vram_gb: int = 0


# ===== New types for management API =====

class RequestStatus(Enum):
    """Inference request status"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DailyEarningItem:
    """Daily earnings for a node"""
    date: str  # "YYYY-MM-DD"
    revenue_vibe: float
    requests: int


@dataclass
class RevenueStats:
    """Revenue statistics"""
    total_revenue_vibe: float = 0.0
    today_revenue_vibe: float = 0.0
    month_revenue_vibe: float = 0.0
    gpu_time_revenue_vibe: float = 0.0
    token_fee_revenue_vibe: float = 0.0
    platform_share_vibe: float = 0.0
    node_payout_vibe: float = 0.0


@dataclass
class RevenueTrendItem:
    """Single day revenue trend"""
    date: str
    revenue_vibe: float
    requests: int


@dataclass
class NodeEarningsRankingItem:
    """Node earnings for leaderboard"""
    node_id: str
    wallet_address: str
    total_earnings: float
    total_requests: int
    rank: int = 0


@dataclass
class WithdrawalRecord:
    """Withdrawal request record"""
    id: str
    wallet_address: str
    amount_vibe: float
    status: str  # "pending" | "completed" | "failed"
    created_at: float
    completed_at: Optional[float] = None
    tx_hash: Optional[str] = None


@dataclass
class UserInfo:
    """User info for API responses"""
    wallet_address: str
    vibe_balance: float = 0.0
    total_consumption: float = 0.0
    total_requests: int = 0
    created_at: float = 0.0
    last_active: float = 0.0


@dataclass
class NodeDetail:
    """Node detail for API responses - enriches NodeCapability with earnings"""
    node_id: str
    wallet_address: str = ""
    hostname: str = ""
    port: int = 8080
    status: str = "offline"
    gpu_count: int = 0
    gpus: List[GPUInfo] = field(default_factory=list)
    total_vram_gb: int = 0
    available_vram_gb: int = 0
    loaded_models: List[str] = field(default_factory=list)
    last_heartbeat: float = 0.0
    registered_at: float = 0.0
    today_earnings: float = 0.0
    total_earnings: float = 0.0
    total_requests: int = 0
    ip_address: str = ""


@dataclass
class InferenceRequestRecord:
    """Inference request for history API"""
    request_id: str
    model_name: str
    user_wallet: str
    node_id: str
    status: str  # RequestStatus value
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    cost_vibe: float = 0.0
    created_at: float = 0.0
    completed_at: Optional[float] = None
    error: Optional[str] = None


@dataclass
class ModelDetail:
    """Model detail for API responses"""
    model_id: str
    name: str
    vram_required_gb: float
    gpu_count_needed: int
    is_preloaded: bool = False
    loaded_on_nodes: List[str] = field(default_factory=list)
    total_requests: int = 0
    avg_latency_ms: float = 0.0
    description: Optional[str] = None


@dataclass
class GpuPoolSummary:
    """GPU pool summary"""
    total_nodes: int = 0
    idle_nodes: int = 0
    busy_nodes: int = 0
    offline_nodes: int = 0
    total_gpus: int = 0
    total_vram_gb: int = 0
    total_requests_today: int = 0


@dataclass
class PlatformSettingsData:
    """Platform settings for API"""
    platform_name: str = "USMSB Distributed Inference"
    scheduler_url: str = "http://localhost:8000"
    gpu_rate: float = 0.001
    token_rate: float = 0.001
    platform_share: float = 0.30
