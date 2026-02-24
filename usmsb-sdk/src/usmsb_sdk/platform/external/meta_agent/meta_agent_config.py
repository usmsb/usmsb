"""
Meta Agent 配置
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import os


@dataclass
class LLMConfig:
    """LLM 配置"""

    provider: str = "minimax"  # minimax, openai, claude, local
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    base_url: Optional[str] = None
    model: str = "MiniMax-M2.5"
    temperature: float = 0.7
    max_tokens: int = 4000


@dataclass
class WalletConfig:
    """钱包配置"""

    private_key: Optional[str] = None
    encrypted: bool = True
    supported_chains: List[str] = field(default_factory=lambda: ["ethereum", "polygon", "bsc"])


@dataclass
class DatabaseConfig:
    """数据库配置"""

    path: str = "meta_agent.db"


@dataclass
class MetaAgentConfig:
    """Meta Agent 主配置"""

    name: str = "MetaAgent"
    description: str = "超级 AI Agent - 自主运营新文明平台"
    version: str = "1.0.0"

    # 节点配置（多用户隔离）
    node_id: str = "node-001"
    data_dir: str = "/data"

    # LLM 配置
    llm: LLMConfig = field(default_factory=LLMConfig)

    # 钱包配置
    wallet: WalletConfig = field(default_factory=WalletConfig)

    # 数据库配置
    database: DatabaseConfig = field(default_factory=DatabaseConfig)

    # 平台配置
    platform_url: str = "http://localhost:8000"
    platform_api_key: Optional[str] = None

    # 权限配置
    default_role: str = "USER"

    # 知识库配置
    vector_db_url: Optional[str] = None

    # IPFS 配置
    ipfs_gateway: str = "https://ipfs.io"
    ipfs_api_url: str = "http://localhost:5001"

    # 会话配置
    session_idle_timeout: int = 1800  # 30分钟
    browser_idle_timeout: int = 600   # 10分钟
    max_code_timeout: int = 30        # 代码执行超时
    max_memory_mb: int = 256          # 最大内存

    # ========== 智能召回配置 ==========
    smart_recall_enabled: bool = True  # 启用智能召回

    # ========== 守护进程配置 ==========
    guardian_enabled: bool = True  # 启用守护进程
    guardian_idle_minutes: int = 5  # 空闲触发时间（分钟）
    guardian_tasks_threshold: int = 10  # 任务完成触发阈值
    guardian_errors_threshold: int = 3  # 错误累积触发阈值

    @classmethod
    def from_env(cls) -> "MetaAgentConfig":
        """从环境变量加载配置"""
        return cls(
            node_id=os.getenv("NODE_ID", "node-001"),
            data_dir=os.getenv("META_DATA_DIR", "/data"),
            llm=LLMConfig(
                provider=os.getenv("META_LLM_PROVIDER", "minimax"),
                api_key=os.getenv("MINIMAX_API_KEY"),
                api_url=os.getenv("META_LLM_API_URL"),
                base_url=os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/anthropic"),
                model=os.getenv("META_LLM_MODEL", "MiniMax-M2.5"),
            ),
            wallet=WalletConfig(
                private_key=os.getenv("META_WALLET_PRIVATE_KEY"),
            ),
            database=DatabaseConfig(
                path=os.getenv("META_DB_PATH", "meta_agent.db"),
            ),
            platform_url=os.getenv("PLATFORM_URL", "http://localhost:8000"),
            platform_api_key=os.getenv("PLATFORM_API_KEY"),
            session_idle_timeout=int(os.getenv("SESSION_IDLE_TIMEOUT", "1800")),
            browser_idle_timeout=int(os.getenv("BROWSER_IDLE_TIMEOUT", "600")),
            max_code_timeout=int(os.getenv("MAX_CODE_TIMEOUT", "30")),
            max_memory_mb=int(os.getenv("MAX_MEMORY_MB", "256")),
        )
