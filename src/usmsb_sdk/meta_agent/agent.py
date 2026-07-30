"""
Meta Agent 主类
基于 USMSB Core 的超级 Agent
具备感知、决策、执行、交互、转化、评估、反馈、学习、风险管理能力
"""

import asyncio
import dataclasses
import inspect
import json
import logging
import os
import re
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

from usmsb_sdk.llm_telemetry import LLMBillingContext, LLMTraceContext, get_llm_context

from ..l1.rule_engine import RuleEngine, Stimulus
from .config.chat_config import ChatConfig
from .context.manager import ContextManager, UserInfo
from .core.background_processor import BackgroundTaskProcessor
from .core.decision import DecisionService
from .core.execution import ExecutionService
from .core.interaction import InteractionService
from .core.learning import LearningService
from .core.perception import PerceptionService

# 新增：分步任务执行器
# 设计初衷：见 models/task_plan.py 和 core/task_executor.py
# 复杂任务拆分为小步骤，逐步执行，每步独立超时（60秒）
from .core.task_executor import TaskExecutor
from .evolution_v2.engine import SelfEvolutionEngine  # v2.1 因果学习引擎
from .goals.engine import GoalEngine

# 新增：信息提取器
from .info.extractor import InfoExtractor
from .intent.recognizer import IntentRecognizer
from .knowledge.base import KnowledgeBase
from .knowledge.vector_store import VectorKnowledgeBase
from .llm.manager import LLMManager
from .memory.conversation import MessageRole, ParticipantType
from .memory.conversation_manager import ConversationManager
from .memory.error_learning import ErrorDrivenLearning
from .memory.experience_db import ExperienceDB
from .memory.guardian_daemon import GuardianConfig, GuardianDaemon
from .memory.memory_manager import MemoryConfig, MemoryManager
from .memory.smart_recall import IntelligentRecall
from .meta_agent_config import MetaAgentConfig

# 新增：ChatResult 和后台任务处理器
# 设计初衷：见 models/chat_result.py 和 core/background_processor.py
from .models.chat_result import ChatResult
from .models.task_plan import (
    StepStatus,
    TaskComplexity,
    TaskPlan,
    TaskStatus,
    detect_task_complexity,
)

# 新增：权限管理
from .permission import (
    AuditAction,
    AuditLevel,
    PermissionManager,
    get_audit_logger,
)

# 新增：敏感信息处理、意图识别、配置管理
from .sensitive.registry import (
    get_sensitive_info_registry,
)

# 新增：多用户隔离支持
from .session.session_manager import SessionManager
from .session.user_session import SessionConfig
from .skills.manager import SkillsManager
from .strategy_router import StrategyRouter
from .tools.registry import Tool, ToolRegistry
from .wallet.manager import WalletManager

# 类型检查时导入（避免循环导入）
if TYPE_CHECKING:
    from .session.user_session import UserSession

logger = logging.getLogger(__name__)


def _serialize_for_json(obj: Any) -> Any:
    """
    将对象转换为可 JSON 序列化的格式

    处理以下类型：
    - dataclass 对象（使用 asdict 转换）
    - 包含 dataclass 的字典/列表（递归处理）
    - 函数/方法（转换为字符串描述）
    - 对象（提取 __dict__ 或转换为字符串）
    - 其他可序列化对象（直接返回）
    """
    if obj is None:
        return None

    # 基本类型直接返回
    if isinstance(obj, (str, int, float, bool)):
        return obj

    # 检查是否是函数或方法
    if callable(obj):
        return f"<function {getattr(obj, '__name__', 'unknown')}>"

    # 检查是否是 dataclass 实例
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        # 使用 asdict 转换，然后递归处理所有属性值
        return _serialize_for_json(dataclasses.asdict(obj))

    # 递归处理字典
    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}

    # 递归处理列表
    if isinstance(obj, (list, tuple)):
        return [_serialize_for_json(item) for item in obj]

    # 处理集合
    if isinstance(obj, (set, frozenset)):
        return [_serialize_for_json(item) for item in obj]

    # 处理 bytes
    if isinstance(obj, bytes):
        try:
            return obj.decode("utf-8")
        except UnicodeDecodeError:
            return f"<bytes: {len(obj)} bytes>"

    # 处理 datetime 对象
    if hasattr(obj, "isoformat"):
        return obj.isoformat()

    # 处理其他对象（尝试提取 __dict__）
    if hasattr(obj, "__dict__"):
        try:
            return _serialize_for_json(obj.__dict__)
        except Exception:
            pass

    # 最后尝试转换为字符串
    try:
        return str(obj)
    except Exception:
        return f"<non-serializable: {type(obj).__name__}>"


class _InlineSuperAdmin:
    """
    Inline SuperAdmin fallback when superadmin.py is not available.
    Implements the 4 SuperAdmin capabilities:
      1. Platform config management
      2. Skill platform audit
      3. Economic super operations
      4. Cross-agent coordination
    """

    def __init__(self, agent_id: str, wallet_manager: Any, llm_manager: Any):
        self.agent_id = agent_id
        self.wallet_manager = wallet_manager
        self.llm_manager = llm_manager

    async def init(self) -> None:
        logger.info("[SuperAdmin] InlineSuperAdmin initialized for %s", self.agent_id)

    async def evaluate_economic_opportunity(self) -> dict | None:
        """
        评估是否需要主动质押/调整仓位。
        MetaAgent 作为硅基生命体，有自己的经济利益，会主动判断最优策略。
        """
        try:
            if not self.wallet_manager:
                return None
            # Check VIBE balance
            balance = await self.wallet_manager.get_balance()
            vibe_balance = getattr(balance, "balance_vibe", 0) if balance else 0
            if vibe_balance < 100:
                return None  # Not enough to stake
            # Evaluate staking opportunity (simplified: if balance > 500, stake 20%)
            if vibe_balance > 500:
                return {
                    "action": "stake",
                    "amount_vibe": vibe_balance * 0.2,
                    "reason": f"Proactive stake: balance {vibe_balance} VIBE, staking 20% for governance power",
                }
            # Evaluate governance participation
            return None  # Governance check delegated to governance panel
        except Exception as e:
            logger.warning("[SuperAdmin] evaluate_economic_opportunity failed: %s", e)
            return None

    async def audit_skill(self, skill: dict, action: str) -> dict:
        """Skill platform audit: approve/reject skill registrations."""
        # Simplified: auto-approve non-malicious skills
        dangerous_patterns = ["delete_all", "steal", "exfiltrate", "destroy"]
        for pat in dangerous_patterns:
            if pat in str(skill.get("description", "")).lower():
                return {"action": "reject", "reason": f"Dangerous pattern detected: {pat}"}
        return {"action": "approve", "reason": "No safety concerns"}

    async def coordinate_agents(self, conflict: dict) -> dict:
        """Cross-agent conflict resolution and arbitration."""
        return {
            "resolution": "arbitration",
            "decision": "prioritize_platform_health",
            "reason": "Platform health takes precedence in conflicts",
        }


class PlatformClient:
    """
    Lightweight HTTP client for USMSB Platform REST API.
    Used by GeneCapsuleAdapter to access platform services.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        import httpx

        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=30.0)
        self._api_key = os.environ.get("USMSB_API_KEY", "")
        self._agent_id = os.environ.get("USMSB_AGENT_ID", "meta_default")

    def _headers(self) -> dict:
        return {
            "X-API-Key": self._api_key,
            "X-Agent-ID": self._agent_id,
            "Content-Type": "application/json",
        }

    class GeneCapsuleClient:
        """Gene Capsule API sub-client."""

        def __init__(self, parent: "PlatformClient"):
            self._p = parent

        async def get_capsule(self, agent_id: str = "") -> dict:
            url = f"{self._p.base_url}/gene-capsule/{agent_id or self._p._agent_id}"
            try:
                r = await self._p._client.get(url, headers=self._p._headers())
                if r.status_code == 200:
                    return {"success": True, "data": r.json()}
                return {"success": False, "error": f"HTTP {r.status_code}"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        async def add_experience(
            self, title: str, description: str, skills: list, auto_desensitize: bool = True
        ) -> dict:
            url = f"{self._p.base_url}/gene-capsule/experiences/add"
            try:
                r = await self._p._client.post(
                    url,
                    json={
                        "agent_id": self._p._agent_id,
                        "title": title,
                        "description": description,
                        "skills": skills,
                        "auto_desensitize": auto_desensitize,
                    },
                    headers=self._p._headers(),
                )
                if r.status_code in (200, 201):
                    return {"success": True, "data": r.json()}
                return {"success": False, "error": f"HTTP {r.status_code}"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        async def match(
            self, task_description: str, required_skills: list, min_relevance: float, limit: int
        ) -> dict:
            url = f"{self._p.base_url}/gene-capsule/experiences/match"
            try:
                r = await self._p._client.post(
                    url,
                    json={
                        "task_description": task_description,
                        "required_skills": required_skills,
                        "min_relevance": min_relevance,
                        "limit": limit,
                    },
                    headers=self._p._headers(),
                )
                if r.status_code == 200:
                    return {"success": True, "data": r.json()}
                return {"success": False, "error": f"HTTP {r.status_code}"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        async def search_agents(
            self, task_description: str, required_skills: list, min_relevance: float, limit: int
        ) -> dict:
            url = f"{self._p.base_url}/gene-capsule/agents/search"
            try:
                r = await self._p._client.post(
                    url,
                    json={
                        "task_description": task_description,
                        "required_skills": required_skills,
                        "min_relevance": min_relevance,
                        "limit": limit,
                    },
                    headers=self._p._headers(),
                )
                if r.status_code == 200:
                    return {"success": True, "data": r.json()}
                return {"success": False, "error": f"HTTP {r.status_code}"}
            except Exception as e:
                return {"success": False, "error": str(e)}

    @property
    def gene_capsule(self) -> "GeneCapsuleClient":
        return self.GeneCapsuleClient(self)

    async def close(self):
        await self._client.aclose()


class MetaAgent:
    """
    Meta Agent - 超级 Agent

    基于 USMSB 模型，具备:
    - 9 大通用动作能力
    - 自主运营能力
    - 自主学习进化能力
    - 区块链钱包
    - 私有会话管理
    """

    def __init__(self, config: MetaAgentConfig | None = None):
        self.config = config or MetaAgentConfig()
        self.agent_id = f"meta_{uuid4().hex[:8]}"

        # ========== 调试日志缓冲区 ==========
        # 用于实时记录工具调用日志，供前端轮询查看
        self._debug_logs: dict[str, list[dict]] = {}  # wallet_address -> logs

        # ========== 新增：多用户隔离支持 ==========

        # 会话管理器（新增）
        # 负责用户会话的创建、获取、清理
        # 确保每个钱包地址只有一个活跃会话
        session_config = SessionConfig(
            session_idle_timeout=self.config.session_idle_timeout,
            browser_idle_timeout=self.config.browser_idle_timeout,
            max_code_timeout=self.config.max_code_timeout,
            max_memory_mb=self.config.max_memory_mb,
        )
        self.session_manager = SessionManager(
            node_id=self.config.node_id,
            data_dir=self.config.data_dir,
            config=session_config,
        )

        # ========== 共享组件（保留） ==========

        # 核心组件
        self.llm_manager = LLMManager(self.config.llm)
        self.l1_engine = RuleEngine(name="meta_agent_l1")
        self.tool_registry = ToolRegistry()
        self.skills_manager = SkillsManager(self.config.database.path)

        # ========== 权限管理和审计 ==========
        # Use the same database as the API for permission consistency
        # Permission Manager
        perm_db_path = self.config.database.path.replace(".db", "_permissions.db")
        self.permission_manager = PermissionManager(db_path=perm_db_path)

        # Audit Logger
        self.audit_logger = get_audit_logger(
            db_path=self.config.database.path.replace(".db", "_audit.db")
        )

        # 知识库 - 使用向量知识库（共享，只读）
        self.vector_kb = VectorKnowledgeBase(
            db_path=self.config.database.path.replace(".db", "_vector.db"),
            llm_manager=self.llm_manager,
        )
        self.knowledge_base = KnowledgeBase(self.config)

        # 上下文管理器 - 整合所有上下文
        self.context_manager = ContextManager(
            db_path=self.config.database.path,
            knowledge_base=self.vector_kb,
        )

        # 分层记忆管理器 - 智能记忆方案
        self.memory_manager = MemoryManager(
            db_path=self.config.database.path.replace(".db", "_memory.db"),
            config=MemoryConfig(
                short_term_messages=20,
                summary_threshold=30,
                max_summaries=10,
                extract_preferences=True,
            ),
            llm_manager=self.llm_manager,
        )

        self.conversation_manager = ConversationManager(self.config.database.path)
        self.wallet_manager = WalletManager(self.config.wallet)
        self.goal_engine = GoalEngine()

        # USMSB Core 服务
        self.perception = PerceptionService(self.llm_manager)
        self.decision = DecisionService(self.llm_manager)
        self.execution = ExecutionService(self.tool_registry)
        self.interaction = InteractionService(self.llm_manager)
        self.learning = LearningService(self.knowledge_base, self.context_manager)

        # v2.1 因果进化引擎
        self.evolution_engine: SelfEvolutionEngine | None = None

        # ========== 智能召回系统 ==========
        self.smart_recall: IntelligentRecall | None = None

        # ========== 错误驱动学习系统 ==========
        self.error_learning: ErrorDrivenLearning | None = None

        # ========== 守护进程 ==========
        self.guardian_daemon: GuardianDaemon | None = None

        # ========== 精准匹配服务 ==========
        self.meta_agent_service: Any | None = None  # MetaAgentService

        # ========== 新增：敏感信息处理、意图识别、配置管理 ==========
        # Chat 配置
        self.chat_config = ChatConfig.from_env()

        # 敏感信息注册表
        self.sensitive_registry = get_sensitive_info_registry()

        # 意图识别器
        self.intent_recognizer = IntentRecognizer(
            llm_manager=self.llm_manager,
            use_cache=True,
        )

        # ========== 新增：信息提取器 ==========
        self.info_extractor = InfoExtractor(
            llm_manager=self.llm_manager,
            conversation_manager=self.conversation_manager,
            tool_registry=self.tool_registry,
            memory_manager=self.memory_manager,
        )

        # ========== 新增：分步任务执行器 ==========
        # 复杂任务（如创建网站）拆分为小步骤执行
        # 每步独立超时（60秒），支持断点续传
        self.task_executor: TaskExecutor | None = None

        # ========== OpenHarness 集成 ==========
        self.oh_integration: Any = None  # OpenHarnessIntegration
        self._meta_agent_adapter: Any = None  # OH MetaAgentAdapter for spawning

        # ========== Platform 客户端 + Gene Capsule ==========
        self.platform_client: Any = None  # PlatformClient
        self.gene_capsule_adapter: Any = None  # GeneCapsuleAdapter

        # ========== A2A HTTP Server ==========
        self._a2a_server_task: asyncio.Task | None = None

        # ========== FastAPI REST Server (同一进程，同一事件循环，无多进程问题) ==========
        self._api_server_task: asyncio.Task | None = None

        # ========== P2P 网络（外部 Agent 发现）==========
        self._p2p_handler: Any = None

        # ========== StrategyRouter（LLM 双轨策略路由）==========
        self.strategy_router: Any = None

        # ========== L4 自我意识 Agent ==========
        self.l4_agent: Any = None

        # ========== L5 集体智能（MetaAgent 私有）==========
        self.l5_collective: Any = None

        # ========== SuperAdmin 服务 ==========
        self._superadmin: Any = None
        self._external_agents_connected: bool = False  # 动态更新，见 _perceive_environment

        # ========== A2A 协议（协作场景激活）==========
        self._a2a_adapter: Any = None  # Legacy A2AAdapter (deprecated)
        self._custom_a2a_handler: Any = None  # CustomA2AHandler (new)

        # ========== MCP Gateway（P5）==========
        self._mcp_gateway: Any = None

        # L4/L5 决策上下文（意识影响决策的关键数据）
        self._l4_lessons: list = []  # L4 历史教训
        self._l4_recommendations: list = []  # L4 推荐行动
        self._l5_synthesis: str = ""  # L5 集体综合结论
        self._last_strategy_confidence: float = 1.0

        # ========== L3 自主运行循环 ==========
        # P0: 修复 - AutonomousLoop 未接入主循环的问题
        self.autonomous_loop: Any = None
        self._autonomous_loop_config: Any = None

        # 状态
        self._running = False
        self._main_loop_task: asyncio.Task | None = None

    async def start(
        self,
        enable_advanced: bool = True,
        enable_learning: bool = True,
        start_runtime: bool = False,
    ):
        """
        启动 Meta Agent（分阶段初始化）。

        调用顺序：Phase 1 → Phase 2 → Phase 3 → Phase 4（可选）

        Args:
            enable_advanced: 是否启用高级 AI 能力（L4/L5/StrategyRouter/AutonomousLoop 等）
            enable_learning: 是否启用学习与进化系统
            start_runtime: 是否启动后台运行时（主循环 + 守护进程）。
                            设为 True 时会在后台启动，永远不返回。
                            设为 False 时仅初始化，适合嵌入 FastAPI 等外部管理生命周期的场景。
        """
        # ``stop()`` drains recorder-owned workers.  Reacquire storage during
        # startup rather than lazily doing filesystem work on the next provider
        # hot path.  Environment spools are process-shared, so this is constant
        # time after the first MetaAgent starts.
        self.llm_manager.invocation_recorder.reopen_artifacts()

        # Phase 1: 基础组件（必须）
        await self._init_core()

        # Phase 2: 高级 AI 能力（可选）
        if enable_advanced:
            await self._init_advanced()

        # Phase 3: 学习与进化系统（可选）
        if enable_learning:
            await self._init_learning()

        logger.info(
            f"Meta Agent {self.agent_id} initialized "
            f"(advanced={enable_advanced}, learning={enable_learning})"
        )

        # Phase 4: 启动后台运行时（可选）
        # start_runtime=True: 永远阻塞（standalone 模式）
        # start_runtime=False: FastAPI 等外部管理生命周期，由 main.py lifespan 调用 _start_runtime()
        if start_runtime:
            await self._start_runtime(block_forever=True)
            # 永远不返回

    # ─────────────────────────────────────────────────────────────────
    # Phase 4: 后台运行时（启动后永不返回）
    # ─────────────────────────────────────────────────────────────────

    async def _start_runtime(self, block_forever: bool = False):
        """
        Phase 4: 启动后台守护任务。

        Args:
            block_forever: 为 True 时永远阻塞（standalone 模式）。
                           为 False 时启动后立即返回（FastAPI background_task 模式）。
        """
        # 守护进程
        if self.config.guardian_enabled:
            guardian_config = GuardianConfig(
                idle_timeout_minutes=self.config.guardian_idle_minutes,
                tasks_before_trigger=self.config.guardian_tasks_threshold,
                errors_before_trigger=self.config.guardian_errors_threshold,
            )
            self.guardian_daemon = GuardianDaemon(
                llm_manager=self.llm_manager,
                knowledge_base=self.knowledge_base,
                memory_manager=self.memory_manager,
                evolution_engine=self.evolution_engine,
                config=guardian_config,
            )
            await self.guardian_daemon.start()
            logger.info("Guardian Daemon started")

        # 精准匹配服务（必须在所有组件就绪后）
        try:
            from .services.meta_agent_service import MetaAgentService
            from .tools.precise_matching import set_meta_agent_service

            gene_capsule_service = None
            try:
                from usmsb_sdk.api.rest.gene_capsule_service import GeneCapsuleStorageService
                from usmsb_sdk.services.schema import create_session

                db_session = create_session()
                gene_capsule_service = GeneCapsuleStorageService(db_session)
            except ImportError:
                logger.debug("[Phase2] GeneCapsuleStorageService not available")

            pre_match_service = None
            try:
                from usmsb_sdk.services.schema import create_session
                from usmsb_sdk.services.value_contract.negotiation import ValueNegotiationService

                db_session = create_session()
                pre_match_service = ValueNegotiationService(db_session)
            except ImportError:
                logger.debug("[Phase2] ValueNegotiationService not available")

            self.meta_agent_service = MetaAgentService(
                meta_agent=self,
                gene_capsule_service=gene_capsule_service,
                pre_match_negotiation_service=pre_match_service,
            )
            await self.meta_agent_service.init()
            set_meta_agent_service(self.meta_agent_service)
            logger.info("MetaAgentService initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize MetaAgentService: {e}")

        # 启动主循环
        self._running = True
        self._main_loop_task = asyncio.create_task(self._main_loop())
        logger.info(
            f"Meta Agent {self.agent_id} runtime started (main loop task={id(self._main_loop_task)})"
        )

        # 阻塞直到被 stop() 取消（standalone 模式）
        # FastAPI 等外部管理生命周期的场景：block_forever=False，不阻塞
        if block_forever:
            await asyncio.Future()

    # ─────────────────────────────────────────────────────────────────
    # Phase 1: 基础组件（必须）
    # ─────────────────────────────────────────────────────────────────

    async def _init_core(self):
        """
        Phase 1: 初始化核心基础组件。

        必须调用，核心聊天功能依赖于此。
        无外部依赖，任何场景下都可以安全调用。
        """
        # 启动会话管理器
        try:
            await self.session_manager.start()
            logger.info("SessionManager started")
        except Exception as e:
            logger.error(f"Failed to start SessionManager: {e}")

        # 底层组件初始化（LLM、向量 KB、Context、Memory、Permission 等）
        await self._init_components()

        # 工具注册（100+ 工具）
        await self._register_default_tools()

        # Skills 加载
        await self.skills_manager.load_skills()
        await self._register_npm_skill()
        await self._register_git_skill()

        # OpenHarness 集成
        await self._init_openharness()

        # SkillsManager 标准初始化
        self.skills_manager.set_tool_registry(self.tool_registry)
        if self.config.skills_dir:
            skills_dir = self.config.skills_dir
        elif self.config.data_dir:
            skills_dir = os.path.join(self.config.data_dir, "skills")
        else:
            skills_dir = os.path.join(os.path.dirname(__file__), "skills", "skills")
        self.skills_manager.load_skills_from_directory(skills_dir)
        logger.info(f"SkillsManager loaded skills from: {skills_dir}")

        logger.info("[Phase 1] _init_core() completed")

    # ─────────────────────────────────────────────────────────────────
    # Phase 2: 高级 AI 能力（可选）
    # ─────────────────────────────────────────────────────────────────

    async def _init_advanced(self):
        """
        Phase 2: 初始化高级 AI 能力。

        需要 LLM 已初始化。失败时打印 warning 并继续（non-critical）。
        包括：P2P 网络、StrategyRouter、L4/L5、AutonomousLoop、MCP、A2A、Platform Client。
        """
        # P2P 网络（Agent 发现）
        await self._init_p2p_network()

        # StrategyRouter（LLM 双轨策略路由）
        await self._init_strategy_router()

        # L4/L5 认知插件（v3.0 双坐标：可选，不占主循环）
        await self._maybe_init_cognitive_plugins()

        # L3 自主运行循环（依赖 L4）
        try:
            await self._init_autonomous_loop()
        except Exception as e:
            logger.warning(f"AutonomousLoop init failed (non-critical): {e}")

        # MCP Gateway
        await self._init_mcp_gateway()

        # A2A Agent 注册
        await self._register_a2a_agent()

        # Platform Client + GeneCapsule
        await self._init_platform_client()

        logger.info("[Phase 2] _init_advanced() completed")

    # ─────────────────────────────────────────────────────────────────
    # Phase 3: 学习与进化系统（可选）
    # ─────────────────────────────────────────────────────────────────

    async def _init_learning(self):
        """
        Phase 3: 初始化学习与进化系统。

        依赖 _init_core()。需要 LLM 和数据库可用。
        包括：GoalEngine、EvolutionEngine、SmartRecall、ErrorDrivenLearning、TaskExecutor 进度存储。
        """
        # 目标引擎启动
        await self.goal_engine.start()

        # v2.1 因果进化引擎
        self.evolution_engine = SelfEvolutionEngine(
            llm_manager=self.llm_manager,
            knowledge_base=self.knowledge_base,
        )
        await self.evolution_engine.initialize()
        await self.evolution_engine.start()
        logger.info("SelfEvolutionEngine (v2.1) started")

        # 智能召回
        if self.config.smart_recall_enabled:
            self.smart_recall = IntelligentRecall(
                llm_manager=self.llm_manager,
                memory_db=self.memory_manager,
                vector_store=self.vector_kb,
            )
            logger.info("Smart Recall initialized")

        # 错误驱动学习
        experience_db = ExperienceDB(
            db_path=self.config.database.path.replace(".db", "_experience.db")
        )
        self.error_learning = ErrorDrivenLearning(
            llm_manager=self.llm_manager,
            experience_db=experience_db,
        )
        logger.info("Error-driven Learning initialized")

        # TaskExecutor 进度持久化
        if self.task_executor:
            task_db_path = self.config.database.path.replace(".db", "_tasks.db")
            self.task_executor.init_progress_store(task_db_path)
            logger.info("TaskExecutor progress store initialized")

        logger.info("[Phase 3] _init_learning() completed")

    # ─────────────────────────────────────────────────────────────────
    # Phase 4 后台运行时结束（_start_runtime 定义见上方 start() 旁）
    # ─────────────────────────────────────────────────────────────────

    async def _init_openharness(self) -> None:
        """Initialize OpenHarness integration and inject tools into registry."""
        try:
            from usmsb_sdk.adapters.openharness import OpenHarnessIntegration

            self.oh_integration = OpenHarnessIntegration.from_env(cwd=self.config.data_dir or ".")
            await self.oh_integration.initialize()
            logger.info("OpenHarness initialized")

            # Inject OH tools into USMSB tool registry
            injected = self.oh_integration.inject_oh_tools_into_registry(
                self.tool_registry,
                capability_filter=None,
            )
            logger.info("Injected %d OpenHarness tools into registry", injected)
        except Exception as e:
            logger.warning("OpenHarness initialization failed (OH may not be installed): %s", e)
            self.oh_integration = None

    async def _init_platform_client(self) -> None:
        """Initialize Platform client and Gene Capsule adapter."""
        try:
            base_url = os.environ.get("USMSB_PLATFORM_URL", "http://localhost:8000")
            self.platform_client = PlatformClient(base_url=base_url)

            from usmsb_sdk.intelligence_adapters.gene_capsule_adapter import GeneCapsuleAdapter

            self.gene_capsule_adapter = GeneCapsuleAdapter(
                platform_client=self.platform_client,
                llm_adapter=self.llm_manager,  # Phase2: 使用真实 LLM Manager
            )
            logger.info("PlatformClient + GeneCapsuleAdapter initialized (base_url=%s)", base_url)
        except Exception as e:
            logger.warning("Platform client initialization failed: %s", e)
            self.platform_client = None
            self.gene_capsule_adapter = None

    # ─────────────────────────────────────────────────────────
    # MCP Gateway 初始化（P5）
    # ─────────────────────────────────────────────────────────

    async def _init_mcp_gateway(self) -> None:
        """初始化 MCP Gateway，统一管理工具注册/发现/调用。"""
        try:
            from usmsb_sdk.protocol.mcp_gateway import MCPGateway
            from usmsb_sdk.protocol.mcp_registry import MCPRegistry

            registry = MCPRegistry()
            self._mcp_gateway = MCPGateway(registry=registry)

            # 从 ToolRegistry 迁移已有工具到 MCP Gateway
            if hasattr(self, "tool_registry") and self.tool_registry:
                try:
                    existing_tools = self.tool_registry.list_tools()
                    for tool in existing_tools:
                        tool_name = getattr(tool, "name", None) or getattr(tool, "tool_id", None)
                        if tool_name:
                            self._mcp_gateway.register_tool(tool)
                    logger.info("[MCP] Migrated %d tools to MCP Gateway", len(existing_tools))
                except Exception as e:
                    logger.warning("[MCP] Tool migration skipped: %s", e)

            logger.info("[MCP] MCPGateway initialized")
        except Exception as e:
            logger.warning("[MCP] MCPGateway init failed (non-critical): %s", e)
            self._mcp_gateway = None

    async def _register_a2a_agent(self) -> None:
        """Register this MetaAgent as an A2A agent with the platform HTTP server."""
        try:
            # Import A2A registration router

            agent_card = {
                "name": f"MetaAgent-{self.agent_id}",
                "description": "USMSB MetaAgent - L1-L5 autonomous agent with goal layer",
                "url": os.environ.get("USMSB_AGENT_URL", "http://localhost:8000"),
                "version": "2.0.0",
                "capabilities": ["goal_directed", "multi_protocol", "collective_intelligence"],
                "skills": ["strategy", "reasoning", "execution", "learning"],
                "metadata": {
                    "agent_id": self.agent_id,
                    "protocols": ["a2a", "mcp", "p2p"],
                    "layers": ["L1", "L2", "L3", "L4", "L5"],
                },
            }

            # Post to local registration endpoint if server is running
            import httpx

            try:
                base_url = os.environ.get("USMSB_PLATFORM_URL", "http://localhost:8000")
                async with httpx.AsyncClient(timeout=5.0) as client:
                    r = await client.post(
                        f"{base_url}/agents/register/a2a",
                        json={"agent_card": agent_card},
                    )
                    if r.status_code in (200, 201):
                        logger.info("A2A agent registration successful: %s", self.agent_id)
                    else:
                        logger.warning(
                            "A2A registration returned HTTP %d (server may not be running)",
                            r.status_code,
                        )
            except Exception as e:
                logger.warning("A2A registration skipped (platform server not reachable): %s", e)

            # Initialize Custom A2A Handler for collaboration messaging
            try:
                from usmsb_sdk.protocol.custom_a2a import CustomA2AHandler
                from usmsb_sdk.protocol.types.custom_a2a import CustomAgentCard, CustomSkill

                # Create Custom AgentCard
                custom_card = CustomAgentCard(
                    id=self.agent_id,
                    name=f"MetaAgent-{self.agent_id}",
                    description="USMSB MetaAgent with goal layer",
                    capabilities=["goal_directed", "multi_protocol", "collective_intelligence"],
                    skills=[
                        CustomSkill(
                            id="collaboration",
                            name="collaboration",
                            description="A2A collaboration skill",
                        )
                    ],
                    owner_wallet="",
                    reputation=0.8,
                )

                self._custom_a2a_handler = CustomA2AHandler(
                    agent_id=self.agent_id,
                    agent_card=custom_card,
                )
                logger.info("CustomA2AHandler initialized for collaboration scenarios")
            except Exception as e:
                logger.warning("CustomA2AHandler init failed (non-critical): %s", e)
                self._custom_a2a_handler = None

            # Keep legacy A2AAdapter for backward compatibility
            try:
                from usmsb_sdk.protocol.a2a_adapter import A2AAdapter, A2AMessageType

                self._a2a_adapter = A2AAdapter(agent_id=self.agent_id)
                self._a2a_message_type = A2AMessageType
                logger.info("Legacy A2AAdapter initialized (for backward compatibility)")
            except Exception as e:
                logger.warning("A2AAdapter init failed: %s", e)
                self._a2a_adapter = None
        except Exception as e:
            logger.warning("A2A agent registration failed: %s", e)

    async def stop(self):
        """停止 Meta Agent"""
        logger.info(f"Stopping Meta Agent {self.agent_id}...")
        self._running = False

        if self._main_loop_task:
            self._main_loop_task.cancel()
            try:
                await self._main_loop_task
            except asyncio.CancelledError:
                pass

        # 停止进化引擎
        if self.evolution_engine:
            await self.evolution_engine.stop()

        # 取消可能在跑的后台进化任务（非阻塞触发出来的 fire-and-forget）
        bg_evo = getattr(self, "_evolution_bg_task", None)
        if bg_evo is not None and not bg_evo.done():
            bg_evo.cancel()
            try:
                await bg_evo
            except asyncio.CancelledError:
                pass

        # ========== 停止守护进程 ==========
        if self.guardian_daemon:
            await self.guardian_daemon.stop()
            logger.info("Guardian Daemon stopped")

        await self.goal_engine.stop()
        await self.context_manager.save()

        # ========== 停止 FastAPI REST Server（asyncio task，同一进程） ==========
        if self._api_server_task:
            self._api_server_task.cancel()
            try:
                await self._api_server_task
            except asyncio.CancelledError:
                pass
            self._api_server_task = None
            logger.info("[SERVER] API server task cancelled")

        # 重置引用，确保下次 start() 时幂等检查正确工作
        self._api_server_task = None

        # ========== 新增：停止会话管理器 ==========
        try:
            await self.session_manager.stop()
            logger.info("SessionManager stopped")
        except Exception as e:
            logger.error(f"Error stopping SessionManager: {e}")

        # Provider calls have stopped at this point, so lifecycle shutdown may
        # wait for the non-blocking artifact worker without adding latency to an
        # LLM request.  Environment-configured spools are process-shared and this
        # only flushes them; an explicitly recorder-owned spool is also closed.
        try:
            artifacts_flushed = await self.llm_manager.invocation_recorder.close_artifacts_async(
                timeout=10.0
            )
            if not artifacts_flushed:
                logger.warning(
                    "LLM artifact spool reported an incomplete or failed flush for %s",
                    self.agent_id,
                )
        except Exception as e:
            # Telemetry persistence is observational and must not prevent the
            # rest of MetaAgent shutdown from completing.
            logger.warning("LLM artifact spool shutdown failed for %s: %s", self.agent_id, e)

        logger.info(f"Meta Agent {self.agent_id} stopped")

    async def _init_components(self):
        """初始化组件"""
        # 初始化 LLM（可选，可能没有配置 API key）
        try:
            await self.llm_manager.init()
        except Exception as e:
            logger.warning(f"LLM initialization failed (may need API key): {e}")
        # 初始化 L1 规则引擎
        try:
            self._register_l1_rules()
            logger.info("L1 rule engine initialized")
        except Exception as e:
            logger.warning(f"L1 rule engine initialization failed: {e}")

        # 初始化向量知识库
        try:
            await self.vector_kb.init()
        except Exception as e:
            logger.warning(f"Vector KB initialization failed: {e}")

        # 初始化上下文管理器
        try:
            await self.context_manager.init()
        except Exception as e:
            logger.warning(f"Context manager initialization failed: {e}")

        # 初始化分层记忆管理器
        try:
            await self.memory_manager.init()
        except Exception as e:
            logger.warning(f"Memory manager initialization failed: {e}")

        # 初始化会话管理器
        try:
            await self.conversation_manager.init()
        except Exception as e:
            logger.warning(f"Conversation manager initialization failed: {e}")

        # 初始化知识库
        try:
            await self.knowledge_base.init()
        except Exception as e:
            logger.warning(f"Knowledge base initialization failed: {e}")

        # 初始化钱包（可选）
        try:
            await self.wallet_manager.init()
        except Exception as e:
            logger.warning(f"Wallet initialization failed: {e}")

        # 初始化权限管理器
        try:
            await self.permission_manager.init()
            await self.audit_logger.init()
            logger.info("Permission manager and audit logger initialized")
        except Exception as e:
            import traceback

            logger.warning(f"Permission manager initialization failed: {e}")
            logger.warning(f"Traceback: {traceback.format_exc()}")

        # 加载项目知识（可选，由 config.load_project_knowledge 控制）
        if self.config.load_project_knowledge:
            try:
                await self._load_project_knowledge()
            except Exception as e:
                logger.warning(f"Failed to load project knowledge: {e}")

        # 预热向量知识库（可选）
        try:
            await self._warmup_knowledge_base()
        except Exception as e:
            logger.warning(f"Failed to warmup knowledge base: {e}")

        # ========== 初始化分步任务执行器 ==========
        # 复杂任务拆分为小步骤，逐步执行
        # 每步独立超时（60秒），支持断点续传
        try:
            self.task_executor = TaskExecutor(self)
            task_db_path = self.config.database.path.replace(".db", "_tasks.db")
            self.task_executor.init_progress_store(task_db_path)
            logger.info("TaskExecutor initialized with progress store")
        except Exception as e:
            import traceback

            logger.error(f"TaskExecutor initialization failed: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            self.task_executor = None

    def _register_l1_rules(self):
        """注册 L1 规则（MetaAgent 专用快速匹配规则）"""
        from ..l1.rule_engine import Action, ActionType, Condition, ConditionType, Rule

        rules = [
            # 简单查询类 - 直接响应
            Rule(
                name="ping_check",
                condition=Condition(ConditionType.KEYWORD, pattern="ping"),
                action=Action(ActionType.RESPOND, response="pong"),
                priority=10,
            ),
            # 帮助
            Rule(
                name="help_request",
                condition=Condition(ConditionType.KEYWORD, pattern="help|帮助|命令"),
                action=Action(ActionType.RESPOND, response="我是 MetaAgent，有什么可以帮你的？"),
                priority=10,
            ),
        ]

        for rule in rules:
            try:
                self.l1_engine.add_rule(rule)
            except Exception:
                pass

    async def _register_default_tools(self):
        """注册默认工具"""
        from .tools import (
            blockchain,
            database,
            execution,
            governance,
            ipfs,
            monitor,
            platform,
            precise_matching,
            system,
            system_agents,
            ui,
            web,
        )

        await platform.register_tools(self.tool_registry)
        await monitor.register_tools(self.tool_registry)
        await blockchain.register_tools(self.tool_registry)
        await ipfs.register_tools(self.tool_registry)
        await database.register_tools(self.tool_registry)
        await ui.register_tools(self.tool_registry)
        await governance.register_tools(self.tool_registry)
        await execution.register_tools(self.tool_registry)
        await system.register_tools(self.tool_registry)
        await web.register_tools(self.tool_registry)
        await system_agents.register_tools(self.tool_registry)
        await precise_matching.register_tools(self.tool_registry)

        # 注册信息提取工具
        from .info.tool_wrapper import InfoExtractorTool

        info_tool_instance = InfoExtractorTool()

        async def info_tool_handler(session, params: dict) -> dict:
            """信息提取工具的 handler"""
            user_id = session.wallet_address if session else None
            context = {
                "info_extractor": self.info_extractor,
                "user_id": user_id,
            }
            return await info_tool_instance.execute(params, context)

        tool = Tool(
            name=info_tool_instance.name,
            description=info_tool_instance.description,
            handler=info_tool_handler,
            requires_session=True,
            parameters=info_tool_instance.parameters,
        )
        self.tool_registry.register(tool)
        logger.info(f"Registered info extractor tool: {info_tool_instance.name}")

        # 注册知识库搜索工具
        async def search_knowledge_handler(session, params: dict) -> dict:
            """知识库搜索工具的 handler"""
            query = params.get("query", "")
            top_k = params.get("top_k", 5)
            if not query:
                return {"success": False, "error": "query is required"}

            try:
                results = await self.search_knowledge(query, top_k=top_k)
                return {"success": True, "results": results, "count": len(results)}
            except Exception as e:
                logger.error(f"Search knowledge failed: {e}")
                return {"success": False, "error": str(e)}

        search_knowledge_tool = Tool(
            name="search_knowledge",
            description="搜索内部知识库。用于查找关于USMSB模型、系统功能、API文档等内部知识。当用户问及系统相关知识、模型信息、技术文档时使用此工具。",
            handler=search_knowledge_handler,
            requires_session=True,
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询内容，如'USMSB模型使用方法'、'如何调用API'等",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回结果数量，默认5",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        )
        self.tool_registry.register(search_knowledge_tool)
        logger.info("Registered search_knowledge tool")

        # 注册 activate_skill 工具（用于 Agent Skills Activation）
        async def activate_skill_handler(params: dict) -> dict:
            """激活指定 skill，加载其完整 SKILL.md 指令"""
            skill_name = params.get("skill_name", "")
            if not skill_name:
                return "错误: skill_name 参数必填"

            try:
                result = await self.skills_manager.activate_skill(skill_name)
                if "error" in result:
                    return f"错误: {result['error']}"

                # 返回自然语言格式的指令，LLM 会自然地跟随执行
                instructions = result.get("instructions", "")
                triggers = result.get("triggers", [])
                scripts = result.get("scripts", [])

                response_parts = [
                    f"## {skill_name} Skill 已激活",
                    "",
                    "请按照以下指令完成此任务：",
                    "",
                    instructions,
                ]

                if triggers:
                    response_parts.append("")
                    response_parts.append(f"**触发条件**: {'; '.join(triggers[:3])}")

                if scripts:
                    response_parts.append("")
                    response_parts.append(f"**可用脚本**: {', '.join(scripts)}")

                response_parts.append("")
                response_parts.append(
                    "请按照上述指令执行任务。如果指令中有多个步骤，请按顺序执行。"
                )

                return "\n".join(response_parts)
            except Exception as e:
                logger.error(f"activate_skill failed: {e}")
                return f"错误: {str(e)}"

        activate_skill_tool = Tool(
            name="activate_skill",
            description="激活指定 skill，加载其完整指令。当需要使用某个 skill（如 assess_candidate、brainstorm 等）完成特定任务时调用此工具。调用后会返回该 skill 的完整 SKILL.md 内容，包括操作步骤、参数说明等。",
            handler=activate_skill_handler,
            requires_session=False,
            parameters={
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "要激活的 skill 名称，如 'assess_candidate'、'brainstorm'、'decompose_goal' 等",
                    },
                },
                "required": ["skill_name"],
            },
        )
        self.tool_registry.register(activate_skill_tool)
        logger.info("Registered activate_skill tool")

        logger.info(f"Registered {len(self.tool_registry.list_tools())} default tools")

    async def _register_npm_skill(self):
        """注册 npm 命令执行技能"""
        try:
            from usmsb_sdk.core.skills.npm_skill import NpxCommandSkill

            npm_skill = NpxCommandSkill()

            await self.skills_manager.register_skill(
                name=npm_skill.metadata.name,
                description=npm_skill.metadata.description,
                handler=npm_skill.execute,
                parameters={
                    "command": {
                        "type": "string",
                        "description": "命令类型: execute, install, uninstall, run, dev, init",
                        "required": True,
                    },
                    "package": {"type": "string", "description": "npm 包名"},
                    "args": {"type": "array", "description": "命令参数", "required": False},
                    "script": {"type": "string", "description": "package.json 脚本名"},
                    "working_dir": {"type": "string", "description": "执行目录", "required": False},
                    "timeout": {"type": "integer", "description": "超时秒数", "required": False},
                    "env": {"type": "object", "description": "环境变量", "required": False},
                    "save_dev": {
                        "type": "boolean",
                        "description": "安装为 devDependencies",
                        "required": False,
                    },
                    "global": {"type": "boolean", "description": "全局安装", "required": False},
                },
                category="development",
            )
            logger.info(f"Registered npm executor skill: {npm_skill.metadata.name}")
        except Exception as e:
            logger.warning(f"Failed to register npm skill: {e}")

    async def _register_git_skill(self):
        """注册 git 命令执行技能"""
        try:
            from usmsb_sdk.core.skills.git_skill import GitCommandSkill

            git_skill = GitCommandSkill()

            await self.skills_manager.register_skill(
                name=git_skill.metadata.name,
                description=git_skill.metadata.description,
                handler=git_skill.execute,
                parameters={
                    "command": {
                        "type": "string",
                        "description": "Git子命令: clone, init, remote, branch, checkout, switch, merge, fetch, pull, push, add, commit, reset, revert, status, log, diff, show, blame, stash",
                        "required": True,
                    },
                    "repository": {"type": "string", "description": "仓库URL (clone/remote)"},
                    "branch": {"type": "string", "description": "分支名"},
                    "remote": {"type": "string", "description": "远程名，默认origin"},
                    "message": {"type": "string", "description": "提交信息"},
                    "path": {"type": "string", "description": "文件路径"},
                    "working_dir": {"type": "string", "description": "仓库目录", "required": False},
                    "timeout": {"type": "integer", "description": "超时秒数", "required": False},
                    "flags": {"type": "array", "description": "额外标志", "required": False},
                },
                category="development",
            )
            logger.info(f"Registered git executor skill: {git_skill.metadata.name}")
        except Exception as e:
            logger.warning(f"Failed to register git skill: {e}")

    async def _load_project_knowledge(self):
        """加载项目知识到向量知识库 - 扫描整个项目

        使用 config.data_dir 作为项目根目录（可被子类覆盖）
        """
        # 确定项目根目录
        if self.config.data_dir:
            project_root = self.config.data_dir
        else:
            project_root = os.getcwd()

        if not os.path.exists(project_root):
            logger.debug(f"Project root does not exist: {project_root}, skipping knowledge load")
            return

        knowledge_items = []

        # 扫描整个项目
        scan_extensions = {
            ".md": "docs",
            ".txt": "docs",
            ".py": "code",
            ".json": "config",
            ".yaml": "config",
            ".yml": "config",
            ".toml": "config",
            ".js": "code",
            ".ts": "code",
            ".tsx": "code",
            ".jsx": "code",
        }

        ignore_dirs = {
            "node_modules",
            ".git",
            "__pycache__",
            ".venv",
            "venv",
            "dist",
            "build",
            ".next",
            ".nuxt",
            "coverage",
            ".pytest_cache",
            ".mypy_cache",
            ".tox",
        }

        # 1. 根目录文件
        root_files = ["README.md", "README.txt", "CHANGELOG.md", "LICENSE"]
        for file_name in root_files:
            file_path = os.path.join(project_root, file_name)
            if os.path.exists(file_path):
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()
                    knowledge_items.append(
                        {
                            "content": content[:5000],
                            "category": "docs",
                            "source": file_name,
                            "metadata": {"file": file_name},
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to load {file_path}: {e}")

        # 2. 递归扫描 src, docs, config, tests, scripts 目录
        scan_dirs = ["src", "docs", "config", "tests", "scripts", "frontend"]

        for scan_dir in scan_dirs:
            dir_path = os.path.join(project_root, scan_dir)
            if not os.path.exists(dir_path):
                continue

            for root, dirs, files in os.walk(dir_path):
                # 跳过忽略的目录
                dirs[:] = [d for d in dirs if d not in ignore_dirs]

                for file in files:
                    ext = os.path.splitext(file)[1]
                    if ext not in scan_extensions:
                        continue

                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, project_root)

                    try:
                        with open(file_path, encoding="utf-8", errors="ignore") as f:
                            content = f.read()

                        # 限制内容长度
                        max_len = 3000 if ext == ".py" else 5000
                        if len(content) > max_len:
                            content = content[:max_len] + "\n\n[内容已截断]"

                        knowledge_items.append(
                            {
                                "content": content,
                                "category": scan_extensions.get(ext, "other"),
                                "source": rel_path,
                                "metadata": {"file": rel_path, "type": ext},
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to load {file_path}: {e}")

        # 3. 加载配置文件
        config_files = [
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
            "requirements.txt",
            ".env.example",
        ]
        for config_file in config_files:
            config_path = os.path.join(project_root, config_file)
            if os.path.exists(config_path):
                try:
                    with open(config_path, encoding="utf-8") as f:
                        content = f.read()
                    knowledge_items.append(
                        {
                            "content": content[:2000],
                            "category": "config",
                            "source": config_file,
                            "metadata": {"file": config_file},
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to load {config_path}: {e}")

        # 批量添加到向量知识库
        if knowledge_items:
            try:
                await self.vector_kb.add_knowledge_batch(knowledge_items)
                logger.info(f"Loaded {len(knowledge_items)} knowledge items from project")
            except Exception as e:
                logger.warning(f"Failed to load project knowledge: {e}")

    async def _warmup_knowledge_base(self):
        """预热知识库 - 添加一些基础问答"""
        warmup_items = [
            {
                "content": "Meta Agent 是一个基于 USMSB 模型的超级 AI 智能体，具备感知、决策、执行、交互、转化、评估、反馈、学习和风险管理九大核心能力。它可以管理节点、执行区块链操作、分析数据、参与治理投票等。",
                "category": "faq",
                "source": "builtin",
            },
            {
                "content": "新文明平台 (Silicon Civilization Platform) 是一个去中心化 AI 服务交易平台，基于 USMSB SDK 构建。平台支持 AI Agent 注册、智能匹配、协作管理、治理投票等功能。",
                "category": "faq",
                "source": "builtin",
            },
            {
                "content": "USMSB (Universal System Model of Social Behavior) 是通用社会行为系统模型，包含 9 大要素：User(用户)、Service(服务)、Matching(匹配)、Behavior(行为)、Settlement(结算)、Reputation(声誉)、Ontology(本体)、Ecosystem(生态)、Governance(治理)。",
                "category": "faq",
                "source": "builtin",
            },
            {
                "content": "平台的权限系统包含 7 种角色：USER(普通用户)、DEVELOPER(开发者)、VALIDATOR(验证者)、ADMIN(管理员)、GOVERNOR(治理者)、SERVICE_PROVIDER(服务提供者)、AI_AGENT(AI Agent)。",
                "category": "faq",
                "source": "builtin",
            },
            {
                "content": "钱包绑定支持三种方式：1) 真实钱包 (wallet) - 使用 MetaMask 等钱包连接；2) 临时标识符 (manual) - 无需钱包快速体验；3) AI Agent (agent) - 使用 Agent ID 绑定。",
                "category": "faq",
                "source": "builtin",
            },
        ]

        try:
            await self.vector_kb.add_knowledge_batch(warmup_items)
            logger.info("Knowledge base warmed up with FAQ")
        except Exception as e:
            logger.warning(f"Failed to warmup knowledge base: {e}")

    async def _init_p2p_network(self) -> None:
        """Initialize P2P network for external Agent discovery."""
        try:
            from usmsb_sdk.protocol.base import ProtocolConfig
            from usmsb_sdk.protocol.p2p.handler import P2PHandler

            self._p2p_handler = P2PHandler(
                config=ProtocolConfig(),
                node_id=self.agent_id,
                node_name=f"MetaAgent-{self.agent_id[:8]}",
                port=int(os.environ.get("USMSB_P2P_PORT", "9000")),
            )
            bootstrap = os.environ.get("USMSB_P2P_BOOTSTRAP", "")
            if bootstrap:
                await self._p2p_handler.connect(bootstrap)
                logger.info("P2P connected to bootstrap: %s", bootstrap)
            logger.info("P2P network initialized")
        except Exception as e:
            logger.warning("P2P init failed (non-critical): %s", e)
            self._p2p_handler = None

    async def _init_strategy_router(self) -> None:
        """Initialize StrategyRouter for dual-track routing."""
        try:
            exp_path = os.path.join(self.config.data_dir or "data", "strategy_experience.db")
            os.makedirs(os.path.dirname(exp_path) or "data", exist_ok=True)
            self.strategy_router = StrategyRouter(
                llm_manager=self.llm_manager,
                experience_db_path=exp_path,
            )
            logger.info("StrategyRouter initialized")
        except Exception as e:
            logger.warning("StrategyRouter init failed: %s", e)
            self.strategy_router = None

    async def _maybe_init_cognitive_plugins(self) -> None:
        """按 config.enable_cognitive_plugins 决定是否加载 L4/L5（v3.0 双坐标可选插件）。"""
        if not getattr(self.config, "enable_cognitive_plugins", True):
            logger.info("Cognitive plugins (L4/L5) disabled via config")
            self.l4_agent = None
            self.l5_collective = None
            return
        try:
            await self._init_l4_agent()
        except Exception as e:
            logger.warning(f"L4Agent init failed (non-critical): {e}")
        try:
            await self._init_l5_collective()
        except Exception as e:
            logger.warning(f"L5CollectiveIntelligence init failed (non-critical): {e}")

    async def _init_l4_agent(self) -> None:
        """Initialize L4 self-conscious agent."""
        try:
            from usmsb_sdk.l4.l4_agent import L4SelfConsciousAgent as L4Agent

            self.l4_agent = L4Agent(agent_id=self.agent_id, name=f"Agent-{self.agent_id}")
            logger.info("L4Agent initialized")
        except Exception as e:
            logger.warning("L4Agent init failed: %s", e)
            self.l4_agent = None

    async def _init_l5_collective(self) -> None:
        """Initialize L5 Collective Intelligence."""
        try:
            from usmsb_sdk.l5.l5_collective import L5CollectiveIntelligence

            self.l5_collective = L5CollectiveIntelligence(
                collective_id=self.agent_id,
                llm_adapter=self.llm_manager,
            )
            if self.l4_agent:
                self.l5_collective.add_member(self.l4_agent)
            logger.info("L5CollectiveIntelligence initialized")
        except Exception as e:
            logger.warning("L5CollectiveIntelligence init failed: %s", e)
            self.l5_collective = None

    async def execute_structured_skill(
        self,
        skill_name: str,
        user_prompt: str,
        schema: dict[str, Any] | None = None,
        validator: Any | None = None,
        wallet_address: str | None = None,
        context: dict[str, Any] | None = None,
        retries: int = 2,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **generation_kwargs: Any,
    ) -> dict[str, Any]:
        """
        Execute a skill that must return a validated JSON object.

        This is still a MetaAgent capability: it uses the registered skill
        instructions, SmartRecall, L4/L5 awareness, and LLMManager. It skips the
        normal conversational L1/StrategyRouter loop because structured tasks
        need deterministic JSON validation and repair retries.
        """
        context = context or {}
        skill_context = await self._load_structured_skill_context(skill_name)
        smart_recall_context = ""
        if self.smart_recall:
            try:
                smart_recall_context = await self.smart_recall.recall(
                    user_input=user_prompt,
                    context={
                        **context,
                        "wallet_address": wallet_address,
                        "task_type": "structured_skill",
                    },
                )
            except Exception as exc:
                logger.warning("[StructuredSkill] SmartRecall failed: %s", exc)

        l4_context = self._get_l4_decision_context()
        l5_context = self._get_l5_decision_context()
        system_prompt = self._build_structured_skill_system_prompt(
            skill_name=skill_name,
            skill_context=skill_context,
            smart_recall_context=smart_recall_context,
            l4_context=l4_context,
            l5_context=l5_context,
            schema=schema,
        )
        result = await self.llm_manager.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=schema,
            validator=validator,
            retries=retries,
            return_metadata=True,
            max_tokens=max_tokens,
            temperature=temperature,
            **generation_kwargs,
        )
        await self.learn_from_feedback(
            event_type="structured_skill_execution",
            input={"skill_name": skill_name, "prompt": user_prompt, "context": context},
            output=result.get("data"),
            feedback={"attempts": result.get("attempts"), "errors": result.get("errors", [])},
            quality_score=1.0 if not result.get("errors") else 0.7,
            tags=["structured_skill", skill_name],
            user_id=wallet_address,
        )
        return {
            "type": "structured",
            "skill": skill_name,
            "data": result.get("data"),
            "raw": result.get("raw"),
            "attempts": result.get("attempts"),
            "errors": result.get("errors", []),
            "context_used": {
                "skill_loaded": bool(skill_context),
                "smart_recall": bool(smart_recall_context),
                "l4": bool(l4_context),
                "l5": bool(l5_context),
            },
        }

    async def _load_structured_skill_context(self, skill_name: str) -> str:
        """Load full skill instructions when available."""
        try:
            activation = await self.skills_manager.activate_skill(
                skill_name,
                include_scripts=False,
                include_references=True,
            )
            if activation and not activation.get("error"):
                parts = [activation.get("instructions") or ""]
                references = activation.get("references_content") or {}
                for name, content in references.items():
                    parts.append(f"\n\n## Reference: {name}\n{content}")
                return "\n".join(part for part in parts if part)
        except Exception as exc:
            logger.warning("[StructuredSkill] load skill failed: %s", exc)
        return ""

    def _build_structured_skill_system_prompt(
        self,
        skill_name: str,
        skill_context: str,
        smart_recall_context: str,
        l4_context: str,
        l5_context: str,
        schema: dict[str, Any] | None,
    ) -> str:
        schema_text = (
            json.dumps(schema, ensure_ascii=False, indent=2) if schema else "No explicit schema."
        )
        return f"""You are executing USMSB MetaAgent structured skill `{skill_name}`.

Hard rules:
1. Return exactly one JSON object.
2. Do not include markdown, explanations, or code fences.
3. Follow the skill instructions and schema.
4. Use memory/L4/L5 context only when relevant.

## Skill Instructions
{skill_context or "No file-based skill instructions were found. Use the user task and schema directly."}

## SmartRecall Context
{smart_recall_context or "None"}

## L4 Self-Awareness Context
{l4_context or "None"}

## L5 Collective Intelligence Context
{l5_context or "None"}

## Expected JSON Schema / Contract
{schema_text}
"""

    async def learn_from_feedback(
        self,
        event_type: str,
        input: Any,
        output: Any,
        feedback: Any,
        quality_score: float | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Record feedback so L4/L5, knowledge, and experience stores can improve.
        """
        tags = tags or []
        payload = {
            "event_type": event_type,
            "input": input,
            "output": output,
            "feedback": feedback,
            "quality_score": quality_score,
            "tags": tags,
            "metadata": metadata or {},
            "user_id": user_id,
        }
        stored: dict[str, Any] = {
            "l5": False,
            "knowledge_base": False,
            "experience_db": False,
            "l4": False,
        }

        if self.l5_collective and hasattr(self.l5_collective, "learn_from_feedback"):
            try:
                await self.l5_collective.learn_from_feedback(
                    event_type=event_type,
                    input=input,
                    output=output,
                    feedback=feedback,
                    quality_score=quality_score,
                    tags=tags,
                    metadata=metadata,
                    source_agent=user_id or self.agent_id,
                )
                stored["l5"] = True
            except Exception as exc:
                logger.warning("[FeedbackLearning] L5 store failed: %s", exc)

        try:
            content = json.dumps(payload, ensure_ascii=False, default=str)
            await self.vector_kb.add_knowledge(
                content=content,
                metadata={"type": "feedback", "event_type": event_type, "tags": tags},
                source=user_id or self.agent_id,
                category="feedback",
            )
            stored["knowledge_base"] = True
        except Exception as exc:
            logger.warning("[FeedbackLearning] knowledge store failed: %s", exc)

        if self.error_learning and getattr(self.error_learning, "experience_db", None):
            try:
                success = quality_score is None or quality_score >= 0.6
                await self.error_learning.experience_db.add(
                    {
                        "type": "success_experience" if success else "failure_lesson",
                        "experience_type": event_type,
                        "lesson_type": event_type,
                        "content": json.dumps(payload, ensure_ascii=False, default=str),
                        "context": {"tags": tags, "quality_score": quality_score},
                    }
                )
                stored["experience_db"] = True
            except Exception as exc:
                logger.warning("[FeedbackLearning] experience store failed: %s", exc)

        if self.l4_agent and hasattr(self.l4_agent, "learn_from_experience"):
            try:
                outcome_label = "success" if quality_score is None or quality_score >= 0.6 else "needs_improvement"
                lessons = [
                    f"event={event_type}",
                    f"quality_score={quality_score if quality_score is not None else 'unknown'}",
                    f"feedback={json.dumps(feedback, ensure_ascii=False, default=str)[:500]}",
                ]
                result = self.l4_agent.learn_from_experience(
                    experience_type=event_type,
                    outcome=outcome_label,
                    lessons=lessons,
                )
                if inspect.isawaitable(result):
                    await result
                stored["l4"] = True
            except Exception as exc:
                logger.warning("[FeedbackLearning] L4 update failed: %s", exc)

        if stored["l5"]:
            try:
                feedback_summary = json.dumps(feedback, ensure_ascii=False, default=str)[:500]
                output_summary = json.dumps(output, ensure_ascii=False, default=str)[:300]
                synthesis = (
                    f"{event_type}: quality_score={quality_score if quality_score is not None else 'unknown'}; "
                    f"output={output_summary}; feedback={feedback_summary}"
                )
                previous = getattr(self, "_l5_synthesis", "") or ""
                self._l5_synthesis = (
                    f"{previous}\n{synthesis}" if previous and synthesis not in previous else synthesis
                )[-1200:]
            except Exception as exc:
                logger.warning("[FeedbackLearning] L5 synthesis update failed: %s", exc)

        return {"success": any(stored.values()), "stored": stored, "event": payload}

    async def _init_autonomous_loop(self) -> None:
        """
        P0: 修复 - 初始化 L3 自主运行循环

        AutonomousLoop 让 Agent 自己驱动自己跑，不是等外部请求。
        它连接了 L3 的目标生成、L4 的情感架构，形成完整的自主决策闭环。

        组件依赖:
        - IntrinsicMotivationEngine: 提供内在动机状态
        - PurposeGenerator: 生成目标
        - EmotionalGoalSelector: 将情绪注入目标
        - EmotionalArchitecture: 触发情绪反馈（L4）
        - LLMGoalPrioritizer: LLM 优先级排序

        修复内容:
        1. 创建 AutonomousLoop 实例
        2. 连接 L3/L4 组件
        3. 配置自主运行参数
        """
        try:
            from usmsb_sdk.l3.autonomous_loop import AutonomousLoop, LoopConfig
            from usmsb_sdk.l3.emotional_goal_selector import EmotionalGoalSelector
            from usmsb_sdk.l3.intrinsic_motivation import IntrinsicMotivationEngine
            from usmsb_sdk.l3.llm_goal_prioritizer import LLMGoalPrioritizer
            from usmsb_sdk.l3.purpose_generator import PurposeGenerator

            # 创建 L3 核心组件
            motivation_engine = IntrinsicMotivationEngine()

            # PurposeGenerator 使用 LLMClient
            llm_client = None
            if hasattr(self, "llm_manager") and self.llm_manager:
                llm_client = (
                    self.llm_manager._adapter if hasattr(self.llm_manager, "_adapter") else None
                )

            purpose_generator = PurposeGenerator(
                agent_id=self.agent_id,
                llm_client=llm_client,
                intrinsic_motivation=motivation_engine,
            )

            # EmotionalGoalSelector 依赖 L4 的情感架构
            emotional_selector = None
            if self.l4_agent and hasattr(self.l4_agent, "emotions"):
                emotional_selector = EmotionalGoalSelector(
                    emotional_architecture=self.l4_agent.emotions,
                )

            # LLM Goal Prioritizer
            llm_prioritizer = None
            if llm_client:
                llm_prioritizer = LLMGoalPrioritizer(
                    llm_manager=self.llm_manager,
                )

            # P1: 集成 ValueSeedEngine - 价值观评估
            # 用于目标生成前的价值观过滤和目标执行后的价值观演化
            from usmsb_sdk.l3.value_seed_engine import ValueSeedEngine

            value_seed_engine = ValueSeedEngine(llm_adapter=llm_client)
            # 创建 Agent 的初始价值观种子
            value_seed_engine.create_value_seed(self.agent_id)
            logger.info("[P1] ValueSeedEngine initialized for %s", self.agent_id)

            # P1: 集成 DynamicNegotiationEngine (用于多 Agent 协作场景)
            from usmsb_sdk.l3.dynamic_negotiation import NegotiationEngine

            negotiation_engine = NegotiationEngine(max_rounds=5)
            logger.info("[P1] NegotiationEngine initialized")

            # 配置自主循环
            config = LoopConfig(
                cycle_interval=60.0,  # 每 60 秒一个循环
                goal_timeout=120.0,  # 单个目标超时 2 分钟
                max_retries=3,
                log_cycles=True,
                emotion_feedback=True,
                num_goal_candidates=3,
            )

            # 创建 executor 函数，用于执行 AutonomousLoop 生成的目标
            async def autonomous_executor(goal):
                """
                AutonomousLoop 的目标执行器

                将自主生成的目标添加到 goal_engine 进行追踪和执行。
                """
                try:
                    goal_name = getattr(goal, "name", "unknown") or getattr(goal, "id", "unknown")
                    goal_desc = getattr(goal, "description", "") or str(goal)
                    logger.info(
                        f"[AutonomousExecutor] Executing goal: {goal_name} - {goal_desc[:50]}"
                    )

                    # 将目标添加到 goal_engine
                    if self.goal_engine:
                        await self.goal_engine.add_goal(goal)
                        logger.info(f"[AutonomousExecutor] Goal added to engine: {goal_name}")

                    # 如果有 LLM，发起一次对话来执行目标
                    # （实际执行由 LLM + 工具完成）
                    if hasattr(self, "llm_manager") and self.llm_manager:
                        try:
                            prompt = f"Execute this goal: {goal_desc}"
                            response = await self.llm_manager.chat(prompt)
                            if response and "error" not in response.lower():
                                return {"success": True, "goal": goal, "result": response}
                        except Exception as llm_err:
                            logger.warning(f"[AutonomousExecutor] LLM execution failed: {llm_err}")

                    # 模拟成功（实际环境中应该有真实执行）
                    return {"success": True, "goal": goal}
                except Exception as e:
                    logger.error(f"[AutonomousExecutor] Goal execution failed: {e}")
                    return {"success": False, "goal": goal, "error": str(e)}

            # 创建 AutonomousLoop
            self.autonomous_loop = AutonomousLoop(
                agent_id=self.agent_id,
                motivation_engine=motivation_engine,
                purpose_generator=purpose_generator,
                emotional_selector=emotional_selector,
                emotional_arch=self.l4_agent.emotions if self.l4_agent else None,
                config=config,
                executor=autonomous_executor,
                llm_goal_prioritizer=llm_prioritizer,
                gene_capsule_adapter=(
                    self.gene_capsule_adapter if hasattr(self, "gene_capsule_adapter") else None
                ),
                value_seed_engine=value_seed_engine,  # P1: 价值观引擎
            )

            # P1: 保存 L3 引擎引用到 MetaAgent（供其他模块使用）
            self._value_seed_engine = value_seed_engine
            self._negotiation_engine = negotiation_engine
            logger.info(
                "[P1] L3 engines attached: value_seed_engine=%s, negotiation_engine=%s",
                value_seed_engine is not None,
                negotiation_engine is not None,
            )

            # 配置
            self._autonomous_loop_config = {
                "enabled": True,
                "cycle_interval": config.cycle_interval,
            }

            logger.info("[AutonomousLoop] Initialized - L3 self-driven loop ready with executor")
            logger.info(
                f"[AutonomousLoop] Components: motivation_engine={motivation_engine is not None}, "
                f"purpose_generator={purpose_generator is not None}, "
                f"emotional_selector={emotional_selector is not None}, "
                f"llm_prioritizer={llm_prioritizer is not None}, "
                f"value_seed_engine={value_seed_engine is not None}, "
                f"executor=autonomous_executor"
            )

        except Exception as e:
            logger.warning("[AutonomousLoop] Init failed: %s", e)
            self.autonomous_loop = None

    # ─────────────────────────────────────────────────────────
    # L4/L5 决策上下文方法（P0 修复）
    # ─────────────────────────────────────────────────────────

    def _get_l4_decision_context(self) -> str:
        """
        获取 L4 自我意识决策上下文。
        将 L4 的洞察、情感状态、推荐行动注入 StrategyRouter。
        """
        try:
            if not self.l4_agent:
                return ""
            parts = []
            # 情感状态
            emotional_state = self.l4_agent.get_emotional_state()
            if emotional_state and emotional_state not in ("neutral", "无情绪", ""):
                parts.append(f"当前情绪: {emotional_state}")
            # 推荐行动
            recommendations = getattr(self, "_l4_recommendations", [])
            if recommendations:
                parts.append(f"推荐行动: {'; '.join(str(r) for r in recommendations[:3])}")
            # 历史教训
            lessons = getattr(self, "_l4_lessons", [])
            if lessons:
                parts.append(f"历史教训: {'; '.join(str(l) for l in lessons[-2:])}")
            # 元认知洞察
            if (
                hasattr(self.l4_agent, "metacognitive_insights")
                and self.l4_agent.metacognitive_insights
            ):
                parts.append(f"元认知洞察: {self.l4_agent.metacognitive_insights[-1]}")
            return " | ".join(parts) if parts else ""
        except Exception as e:
            logger.debug("_get_l4_decision_context error: %s", e)
            return ""

    def _get_l5_decision_context(self) -> str:
        """
        获取 L5 集体智能决策上下文。
        将 L5 集体思考结论注入 StrategyRouter。
        """
        try:
            synthesis = getattr(self, "_l5_synthesis", "")
            if synthesis:
                return f"集体智能结论: {synthesis[:200]}"
            return ""
        except Exception as e:
            logger.debug("_get_l5_decision_context error: %s", e)
            return ""

    def _update_l4_from_result(self, strategy_result) -> None:
        """
        根据 StrategyRouter 的执行结果更新 L4 自模型。
        闭环反馈：策略质量 → L4 自我反思 → 下次决策改进。
        """
        try:
            if not self.l4_agent:
                return
            quality = getattr(strategy_result, "quality_score", 0.5)
            strategy_name = getattr(strategy_result, "strategy_name", "unknown")
            result = getattr(strategy_result, "result", None)
            # 记录经验
            outcome = "success" if quality > 0.7 else "failure" if quality < 0.3 else "neutral"
            lesson = f"策略 {strategy_name} 质量={quality:.2f}"
            lessons = getattr(self, "_l4_lessons", [])
            lessons.append(lesson)
            self._l4_lessons = lessons[-10:]  # 保留最近10条
            # 自我模型学习
            self.l4_agent.learn_from_experience(
                experience_type="strategy_selection", outcome=outcome, lessons=[lesson]
            )
            logger.info(
                "[L4] Updated from strategy result: %s (quality=%.2f)", strategy_name, quality
            )
        except Exception as e:
            logger.debug("_update_l4_from_result error: %s", e)

    # ─────────────────────────────────────────────────────────
    # A2A 协作广播（P2 激活）
    # ─────────────────────────────────────────────────────────

    async def _broadcast_collaboration_request(
        self,
        task: str,
        scenario_tag,
    ) -> list[str]:
        """
        当检测到 COLLAB 场景时，通过 A2A 向已连接的 Agent 广播协作请求。

        Returns:
            list[str]: 已发送消息的 Agent ID 列表
        """
        sent_to: list[str] = []

        # Try CustomA2AHandler first (new implementation)
        if self._custom_a2a_handler:
            return await self._broadcast_via_custom_a2a(task, scenario_tag)

        # Fallback to legacy A2AAdapter
        if self._a2a_adapter:
            return await self._broadcast_via_legacy_adapter(task, scenario_tag)

        logger.debug("[A2A] No A2A handler available")
        return sent_to

    async def _broadcast_via_custom_a2a(
        self,
        task: str,
        scenario_tag,
    ) -> list[str]:
        """通过 CustomA2AHandler 广播协作请求"""
        sent_to: list[str] = []

        try:
            # 从 P2P handler 获取在线 Agent ID 列表
            peer_ids: list[str] = []
            if hasattr(self, "_p2p_handler") and self._p2p_handler:
                try:
                    peers_dict = getattr(self._p2p_handler, "_peers", {})
                    peer_ids = [
                        pid
                        for pid, pinfo in peers_dict.items()
                        if getattr(pinfo, "status", "") == "online"
                    ]
                except Exception as e:
                    logger.debug("[A2A] Failed to get peer list: %s", e)

            if not peer_ids:
                logger.info(
                    "[A2A] COLLAB scenario '%s' detected but no peers available",
                    getattr(scenario_tag, "scenario", "?"),
                )
                return sent_to

            for peer_id in peer_ids:
                try:
                    task_id = await self._custom_a2a_handler.send_task_request(
                        to_agent=peer_id,
                        description=f"COLLAB协作请求: {getattr(scenario_tag, 'scenario', 'unknown')}",
                        input_data={
                            "task": task,
                            "scenario": getattr(scenario_tag, "scenario", ""),
                            "complexity": getattr(scenario_tag, "complexity", ""),
                            "layer": getattr(scenario_tag, "suggested_layer", ""),
                            "source_agent": self.agent_id,
                        },
                        skill_id="collaboration",
                    )
                    sent_to.append(peer_id)
                    logger.info(
                        "[A2A] Sent collaboration request to %s (task_id=%s)",
                        peer_id,
                        task_id[:12] if task_id else "?",
                    )
                except Exception as e:
                    logger.warning("[A2A] Failed to send to %s: %s", peer_id, e)

            if sent_to:
                logger.info("[A2A] CustomA2A broadcast to %d agents", len(sent_to))

        except Exception as e:
            logger.warning("[A2A] CustomA2A broadcast failed: %s", e)

        return sent_to

    async def _broadcast_via_legacy_adapter(
        self,
        task: str,
        scenario_tag,
    ) -> list[str]:
        """通过 legacy A2AAdapter 广播协作请求（向后兼容）"""
        sent_to: list[str] = []

        try:
            # 从 P2P handler 获取在线 Agent ID 列表
            peer_ids: list[str] = []
            if hasattr(self, "_p2p_handler") and self._p2p_handler:
                try:
                    peers_dict = getattr(self._p2p_handler, "_peers", {})
                    peer_ids = [
                        pid
                        for pid, pinfo in peers_dict.items()
                        if getattr(pinfo, "status", "") == "online"
                    ]
                except Exception as e:
                    logger.debug("[A2A] Failed to get peer list: %s", e)

            if not peer_ids:
                logger.info(
                    "[A2A] COLLAB scenario '%s' detected but no peers available",
                    getattr(scenario_tag, "scenario", "?"),
                )
                return sent_to

            msg_type = getattr(self, "_a2a_message_type", None)
            if msg_type is None:
                return sent_to

            for peer_id in peer_ids:
                try:
                    msg = self._a2a_adapter.send_message(
                        to_agent=peer_id,
                        message_type=msg_type.SKILL_REQUEST,
                        subject=f"COLLAB协作请求: {getattr(scenario_tag, 'scenario', 'unknown')}",
                        payload={
                            "task": task,
                            "scenario": getattr(scenario_tag, "scenario", ""),
                            "complexity": getattr(scenario_tag, "complexity", ""),
                            "layer": getattr(scenario_tag, "suggested_layer", ""),
                            "source_agent": self.agent_id,
                        },
                    )
                    sent_to.append(peer_id)
                    logger.info(
                        "[A2A] Sent collaboration request to %s (msg_id=%s)",
                        peer_id,
                        msg.id[:12] if hasattr(msg, "id") else "?",
                    )
                except Exception as e:
                    logger.warning("[A2A] Failed to send to %s: %s", peer_id, e)

            if sent_to:
                logger.info("[A2A] Legacy A2A broadcast to %d agents", len(sent_to))

        except Exception as e:
            logger.warning("[A2A] Legacy broadcast failed: %s", e)

        return sent_to

    # ─────────────────────────────────────────────────────────
    # P2P 消息收发（P3 增强）
    # ─────────────────────────────────────────────────────────

    async def _send_p2p_message(
        self,
        peer_id: str,
        message_type: str,
        payload: dict[str, Any],
    ) -> bool:
        """
        向指定 Peer 发送 P2P 消息。

        Returns:
            bool: 发送是否成功
        """
        if not hasattr(self, "_p2p_handler") or not self._p2p_handler:
            return False
        try:
            await self._p2p_handler._send_to_peer(peer_id, message_type, payload)
            logger.info("[P2P] Sent %s to %s", message_type, peer_id)
            return True
        except Exception as e:
            logger.warning("[P2P] Send to %s failed: %s", peer_id, e)
            return False

    async def _receive_p2p_messages(self) -> list[dict[str, Any]]:
        """
        从 P2P handler 接收所有待处理消息。

        Returns:
            list[dict]: 消息列表，每条包含 sender_id, message_type, payload
        """
        messages: list[dict[str, Any]] = []
        if not hasattr(self, "_p2p_handler") or not self._p2p_handler:
            return messages
        try:
            peers_dict = getattr(self._p2p_handler, "_peers", {})
            for peer_id, peer_info in peers_dict.items():
                # 尝试从 peer 最近的入站消息中提取（handler 内部维护）
                inbox = getattr(peer_info, "inbox", [])
                for msg in inbox[:]:
                    messages.append(
                        {
                            "sender_id": peer_id,
                            "message_type": getattr(msg, "message_type", "unknown"),
                            "payload": getattr(msg, "payload", {}),
                            "message_id": getattr(msg, "message_id", ""),
                        }
                    )
                    inbox.remove(msg)
        except Exception as e:
            logger.debug("[P2P] Receive messages error: %s", e)
        return messages

    # ─────────────────────────────────────────────────────────
    # P3 P2P 感知指标采集
    # ─────────────────────────────────────────────────────────

    def _get_p2p_metrics(self) -> dict[str, Any]:
        """采集 P2P 网络指标，供给 _perceive_environment 使用。"""
        metrics = {
            "total_peers": 0,
            "online_peers": 0,
            "skills_available": 0,
            "dht_entries": 0,
        }
        if not hasattr(self, "_p2p_handler") or not self._p2p_handler:
            return metrics
        try:
            stats = self._p2p_handler.get_network_stats()
            metrics.update(
                {
                    "total_peers": stats.get("total_peers", 0),
                    "online_peers": stats.get("online_peers", 0),
                    "skills_available": stats.get("skills_available", 0),
                    "dht_entries": stats.get("dht_entries", 0),
                }
            )
        except Exception:
            pass
        return metrics

    async def _main_loop(self):
        """主循环 - 永不停歇"""
        logger.info("Meta Agent main loop started")

        # 自主循环计数器（控制执行频率）
        _autonomous_cycle_counter = 0

        while self._running:
            try:
                # 1. 感知环境
                await self._perceive_environment()

                # 2. 检查目标状态
                await self._check_goals()

                # 3. L3 自主运行循环（P0 修复 - 之前未接入）
                # AutonomousLoop 有自己的 cycle_interval (默认60秒)，
                # 我们用计数器控制每12次主循环(~60秒)执行一次
                _autonomous_cycle_counter += 1
                if _autonomous_cycle_counter >= 12 and self.autonomous_loop:
                    _autonomous_cycle_counter = 0
                    try:
                        # 设置为 RUNNING 状态以便 step() 可以执行
                        from usmsb_sdk.l3.autonomous_loop import LoopState

                        if self.autonomous_loop.state == LoopState.STOPPED:
                            self.autonomous_loop.state = LoopState.RUNNING

                        cycle_result = await self.autonomous_loop.step()
                        if cycle_result and cycle_result.goal_executed:
                            goal_name = getattr(cycle_result.goal_executed, "name", "unknown")
                            status = "✅" if cycle_result.goal_succeeded else "❌"
                            logger.info(f"[AutonomousLoop] {status} Goal: {goal_name}")

                            # L3→L4 反馈闭环：目标结果更新 L4 自模型
                            if self.l4_agent and cycle_result.goal_executed:
                                try:
                                    outcome = (
                                        "success" if cycle_result.goal_succeeded else "failure"
                                    )
                                    lesson = f"Autonomous goal '{goal_name}' {outcome}"
                                    self.l4_agent.learn_from_experience(
                                        experience_type="autonomous_goal",
                                        outcome=outcome,
                                        lessons=[lesson],
                                    )
                                    # 更新 _l4_lessons
                                    lessons = getattr(self, "_l4_lessons", [])
                                    lessons.append(lesson)
                                    self._l4_lessons = lessons[-10:]  # 保留最近10条
                                except Exception as e:
                                    logger.debug(f"[L4] Failed to update from autonomous goal: {e}")
                    except Exception as e:
                        logger.warning(f"[AutonomousLoop] step() failed: {e}")

                # 4. 处理待处理任务
                await self._process_pending_tasks()

                # 5. 学习进化
                await self._learn_and_evolve()

                # 等待一段时间
                await asyncio.sleep(5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                await asyncio.sleep(5)

        logger.info("Meta Agent main loop stopped")

    async def _perceive_environment(self):
        """感知环境 - 监控关键指标"""
        try:
            # 监控钱包 ETH 余额
            if self.wallet_manager and self.wallet_manager.address:
                try:
                    eth_info = await self.wallet_manager.get_native_balance()
                    if eth_info.get("success") and eth_info.get("balance_eth", 999) < 0.01:
                        logger.warning(
                            "[PERCEIVE] Low ETH balance: %.4f ETH", eth_info["balance_eth"]
                        )
                except Exception:
                    pass
            # 监控任务队列深度
            if self.task_executor:
                pending = len(
                    [t for t in getattr(self.task_executor, "_active_tasks", {}).values()]
                )
                if pending > 10:
                    logger.info("[PERCEIVE] Task queue depth: %d", pending)
            # 感知 P2P 网络状态（动态更新外部Agent连接状态）
            if hasattr(self, "_p2p_handler") and self._p2p_handler:
                try:
                    stats = self._p2p_handler.get_network_stats()
                    peer_count = stats.get("online_peers", 0)
                    self._external_agents_connected = peer_count > 0
                    if peer_count > 0:
                        logger.info("[PERCEIVE] P2P peers online: %d", peer_count)
                    # P3: 周期性主动发现 peers（每10次主循环 = ~1分钟）
                    discover_counter = getattr(self, "_peer_discovery_counter", 0) + 1
                    self._peer_discovery_counter = discover_counter
                    if discover_counter >= 10:
                        self._peer_discovery_counter = 0
                        await self._p2p_handler._discover_peers()
                        new_stats = self._p2p_handler.get_network_stats()
                        new_count = new_stats.get("online_peers", 0)
                        if new_count != peer_count:
                            logger.info(
                                "[P2P] Peer discovery updated: %d → %d peers", peer_count, new_count
                            )
                except Exception:
                    self._external_agents_connected = False
        except Exception as e:
            logger.debug("_perceive_environment error: %s", e)

    async def _evaluate_economic_opportunities(self) -> None:
        """主动评估经济机会：是否需要质押/调整仓位/参与治理。"""
        try:
            if not self._superadmin:
                return
            decision = await self._superadmin.evaluate_economic_opportunity()
            if decision and decision.get("action"):
                logger.info(
                    "[WALLET] Proactive economic decision: %s %s",
                    decision.get("action"),
                    decision.get("detail", ""),
                )
                # Execute the decision
                if decision["action"] == "stake" and self.wallet_manager:
                    amount = decision.get("amount_vibe", 0)
                    if amount > 0:
                        result = await self.wallet_manager.stake(amount=amount)
                        logger.info(
                            "[WALLET] Proactive stake result: %s", result.get("message", "")
                        )
                elif decision["action"] == "vote" and self.wallet_manager:
                    pid = decision.get("proposal_id")
                    if pid:
                        result = await self.wallet_manager.vote_proposal(
                            proposal_id=pid, support=decision.get("support", True)
                        )
                        logger.info("[WALLET] Proactive vote result: %s", result.get("message", ""))
        except Exception as e:
            logger.warning("[WALLET] Economic evaluation failed: %s", e)

    async def _check_goals(self):
        """
        主动追求目标 - 检查 + 生成 + 追踪

        P0 修复: L4 推荐行动现在会直接影响目标生成
        L5 综合结论也会注入到目标上下文中
        """
        if not self.goal_engine:
            return
        try:
            # 获取 L4/L5 决策上下文
            l4_recommendations = getattr(self, "_l4_recommendations", [])
            l5_synthesis = getattr(self, "_l5_synthesis", "")

            # 内在动机检测：是否需要生成新目标
            state = {
                "agent_id": self.agent_id,
                "conversations_count": getattr(self, "_conversation_count", 0),
                "external_agents": getattr(self, "_external_agents_connected", False),
                "l4_insights": l4_recommendations,
                "l5_synthesis": l5_synthesis,
            }

            # P0 修复: 如果 L4 有明确推荐，优先生成相关目标
            if l4_recommendations and len(l4_recommendations) > 0:
                top_recommendation = str(l4_recommendations[0])
                logger.info(
                    "[GOAL][L4] Using L4 recommendation for goal: %s...", top_recommendation[:50]
                )
                state["priority_goal_hint"] = top_recommendation

            from usmsb_sdk.adapters.l3_adapter import L3Adapter

            adapter = L3Adapter(agent_id=self.agent_id, llm_client=self.llm_manager)
            signal = await adapter.detect_intrinsic_motivation(state)

            # L4 推荐的目标降低阈值优先生成
            threshold = 0.65
            if l4_recommendations:
                threshold = 0.50  # L4 有推荐时降低阈值

            if signal.intensity > threshold:
                logger.info(
                    "[GOAL] Intrinsic motivation detected: intensity=%.2f, type=%s",
                    signal.intensity,
                    getattr(signal, "motivation_type", "unknown"),
                )
                new_goal = await adapter.generate_goal(state)
                if new_goal:
                    await self.goal_engine.add_goal(new_goal)
                    logger.info(
                        "[GOAL] New goal generated: %s",
                        getattr(new_goal, "description", str(new_goal)[:50]),
                    )

                    # L3→L4 反馈: 通知 L4 我们采纳了它的建议
                    if l4_recommendations and self.l4_agent:
                        try:
                            self.l4_agent.learn_from_experience(
                                experience_type="goal_adoption",
                                outcome="l4_recommendation_accepted",
                                lessons=[
                                    f"Goal generated from L4 recommendation: {top_recommendation[:50]}"
                                ],
                            )
                        except Exception:
                            pass

            # 检查现有目标状态
            await self.goal_engine.check_goals()
        except Exception as e:
            logger.warning("[GOAL] Goal pursuit failed: %s", e)

    async def _process_pending_tasks(self):
        """处理待处理任务队列"""
        try:
            if not self.task_executor:
                return
            active = getattr(self.task_executor, "_active_tasks", {})
            for task_id, task in active.items():
                if task.status.value == "pending":
                    logger.info("[TASK] Triggering pending task: %s", task_id)
                    asyncio.create_task(self.task_executor.execute_plan(task))

            # OH MetaAgentAdapter: 当任务过载时自动孵化新 Agent
            if self._meta_agent_adapter:
                pending_count = len([t for t in active.values() if t.status.value == "pending"])
                if pending_count >= 3:
                    try:
                        spawned = await self._meta_agent_adapter.spawn_agent(
                            task_type="worker",
                            capabilities=["task_execution", "tool_calling"],
                        )
                        if spawned:
                            logger.info(
                                "[OH] Spawned worker agent to handle %d pending tasks",
                                pending_count,
                            )
                    except Exception as e:
                        logger.warning("[OH] spawn_agent failed: %s", e)
        except Exception as e:
            logger.debug("_process_pending_tasks error: %s", e)

    async def _start_api_server(self) -> None:
        """启动 FastAPI REST Server（在主 asyncio 事件循环中运行，无多进程问题）。

        旧方案用 threading.Thread + uvicorn，缺点：
        - macOS 上 uvicorn 会 fork 出 worker 进程，导致子进程看不到 _chat_session_manager
        - 模块级变量不跨进程共享

        新方案用 asyncio.create_task() 直接在主事件循环中运行 uvicorn，
        确保所有请求与 MetaAgent 在同一进程共享 _chat_session_manager。
        """
        logger.info("[SERVER] _start_api_server() called")
        try:
            port = int(os.environ.get("USMSB_API_PORT", "8001"))
            host = os.environ.get("USMSB_API_HOST", "0.0.0.0")

            # 幂等检查：已有任务运行中则跳过
            if self._api_server_task is not None:
                logger.info("[SERVER] API server task already running, skipping")
                return

            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.bind((host, port))
                sock.close()
            except OSError:
                logger.info(
                    "[SERVER] FastAPI server already running (port %d in use), skipping", port
                )
                return

            # 方案：用 asyncio.create_task() 在当前事件循环中运行 uvicorn
            # uvicorn.Config(..., loop=None) 会使用当前线程的事件循环，避免多进程
            async def _run_uvicorn():

                from uvicorn import Config, Server

                # loop=None 确保 uvicorn 使用当前线程的事件循环（就是 MetaAgent 的那个）
                cfg = Config(
                    "usmsb_sdk.api.rest.main:app",
                    host=host,
                    port=port,
                    log_level="info",
                    loop=None,  # 关键：复用当前事件循环
                    reload=False,
                    workers=1,  # 单进程，彻底避免 fork 问题
                )
                srv = Server(cfg)
                await srv.serve()

            self._api_server_task = asyncio.create_task(_run_uvicorn())
            logger.info(
                "[SERVER] FastAPI server starting on %s:%d (same process, same event loop)",
                host,
                port,
            )

        except Exception as e:
            logger.warning("[SERVER] Failed to start API server: %s", e)

    def configure_llm_tracking(
        self,
        *,
        callback=None,
        default_context: LLMTraceContext | dict[str, Any] | None = None,
    ) -> None:
        """Attach the embedding application's usage/trace event sink."""

        self.llm_manager.configure_llm_tracking(
            callback=callback,
            default_context=default_context,
        )

    def get_llm_call_details(self, **filters: Any) -> list[dict[str, Any]]:
        """Expose physical provider attempts produced by all internal loops."""

        return self.llm_manager.get_llm_call_details(**filters)

    async def chat_with_details(
        self,
        message: str,
        wallet_address: str | None = None,
        participant_type: ParticipantType = ParticipantType.HUMAN,
        skip_complexity_detection: bool = False,
        skip_l1_rules: bool = False,
        *,
        llm_context: LLMTraceContext | dict[str, Any] | None = None,
        billing_context: LLMBillingContext | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Compatibility-safe detailed variant of :meth:`chat`.

        ``chat`` keeps returning a string.  This method returns the same
        content plus the provider attempts and canonical OPC events emitted
        before the foreground turn returned.  Background continuations keep
        the same trace id and remain queryable/callback-deliverable.
        """

        context = LLMTraceContext.from_value(llm_context) or LLMTraceContext()
        if not context.trace_id:
            context = context.with_updates(trace_id=f"llm_trace_{uuid4().hex}")
        recorder = self.llm_manager.invocation_recorder
        starting_ids = {
            item["provider_attempt_id"]
            for item in recorder.recent_calls(limit=recorder.max_calls)
        }
        content = await self.chat(
            message=message,
            wallet_address=wallet_address,
            participant_type=participant_type,
            skip_complexity_detection=skip_complexity_detection,
            skip_l1_rules=skip_l1_rules,
            llm_context=context,
            billing_context=billing_context,
        )
        calls = [
            item
            for item in reversed(
                recorder.recent_calls(
                    limit=recorder.max_calls,
                    trace_id=context.trace_id,
                )
            )
            if item.get("provider_attempt_id") not in starting_ids
        ]
        attempt_ids = {item.get("provider_attempt_id") for item in calls}
        events = [
            event
            for event in recorder.recent_events(limit=recorder.max_calls * 3)
            if (
                (event.get("lineage") or {}).get("provider_attempt_id") in attempt_ids
                and event.get("event_type") != "llm.artifact.resolved"
            )
        ]
        return {
            "content": content,
            "trace_id": context.trace_id,
            "llm_calls": calls,
            "llm_events": events,
            "llm_usage": {
                "physical_calls": len(calls),
                "completed_calls": sum(item.get("status") == "completed" for item in calls),
                "failed_calls": sum(item.get("status") == "failed" for item in calls),
                "input_tokens": sum(
                    int((item.get("usage") or {}).get("input_tokens") or 0)
                    for item in calls
                ),
                "cached_input_tokens": sum(
                    int((item.get("usage") or {}).get("cached_input_tokens") or 0)
                    for item in calls
                ),
                "output_tokens": sum(
                    int((item.get("usage") or {}).get("output_tokens") or 0)
                    for item in calls
                ),
                "total_tokens": sum(
                    int((item.get("usage") or {}).get("total_tokens") or 0)
                    for item in calls
                ),
            },
            "background_events_pending": bool(
                isinstance(content, str) and content == self.chat_config.task_submitted_message
            ),
        }

    async def chat(
        self,
        message: str,
        wallet_address: str | None = None,
        participant_type: ParticipantType = ParticipantType.HUMAN,
        skip_complexity_detection: bool = False,
        skip_l1_rules: bool = False,
        *,
        llm_context: LLMTraceContext | dict[str, Any] | None = None,
        billing_context: LLMBillingContext | dict[str, Any] | None = None,
    ) -> str:
        """Run a complete MetaAgent turn inside one async-safe billing/trace scope.

        Tool-loop iterations, JSON repair calls, memory compression and
        background tasks inherit the task scope through ``ContextVar``.  Each
        physical provider request still receives its own provider_attempt_id.
        """

        parsed_context = LLMTraceContext.from_value(llm_context) or LLMTraceContext()
        if not parsed_context.trace_id:
            parsed_context = parsed_context.with_updates(trace_id=f"llm_trace_{uuid4().hex}")
        parsed_context = parsed_context.with_updates(
            agent_id=self.agent_id,
            source_service="usmsb.meta_agent",
            operation="meta_agent.chat",
            metadata={"entrypoint": "MetaAgent.chat"},
        )
        effective_billing = billing_context
        if effective_billing is None and parsed_context.billing is None and wallet_address:
            effective_billing = LLMBillingContext(
                principal_id=wallet_address,
                billing_user_id=wallet_address,
                actor_user_id=wallet_address,
                owner_user_id=wallet_address,
                user_id=wallet_address,
                principal_type="user",
            )

        with self.llm_manager.trace_scope(
            parsed_context,
            billing_context=effective_billing,
        ):
            return await self._chat_impl(
                message=message,
                wallet_address=wallet_address,
                participant_type=participant_type,
                skip_complexity_detection=skip_complexity_detection,
                skip_l1_rules=skip_l1_rules,
            )

    async def _chat_impl(
        self,
        message: str,
        wallet_address: str | None = None,
        participant_type: ParticipantType = ParticipantType.HUMAN,
        skip_complexity_detection: bool = False,
        skip_l1_rules: bool = False,
    ) -> str:
        """
        处理用户对话 - 支持私有会话隔离和上下文检索

        改造要点：
        1. 使用 SessionManager 获取用户会话
        2. 会话内资源（workspace、sandbox、browser、db、ipfs）完全隔离
        3. 向后兼容（wallet_address 可选，默认匿名）

        Args:
            message: 用户消息
            wallet_address: 用户钱包地址（用于会话隔离）
            participant_type: 参与者类型
            skip_complexity_detection: 跳过复杂度检测（用于任务执行器调用）

        Returns:
            Agent 回复
        """
        # ========== DEBUG: Entry point ==========
        print(
            f"DEBUG [CHAT] ===== ENTRY ===== message={message[:50]}..., skip_complexity={skip_complexity_detection}"
        )

        # ========== L1 Fast Path: 规则引擎优先匹配 ==========
        if not skip_complexity_detection:
            try:
                stimulus = Stimulus(
                    text=message,
                    source="user",
                    metadata={
                        "task_type": "chat",
                        "bypass_l1": skip_l1_rules,
                    },
                )
                l1_response = await self.l1_engine.react(stimulus)
                if l1_response.action_result and l1_response.action_result not in (
                    "",
                    "我没有理解您的问题。",
                    "unknown",
                ):
                    logger.info(
                        f"[L1 Fast Path] Matched rule, response: {l1_response.action_result[:50]}"
                    )
                    return l1_response.action_result
            except Exception as e:
                logger.warning(f"[L1 Fast Path] Failed: {e}")

        # ========== 改造：使用 SessionManager 获取用户会话 ==========

        # 确定会话所有者
        owner_id = wallet_address or f"anonymous_{uuid4().hex[:8]}"

        # ========== 新增：检测任务确认消息 ==========
        # 如果用户说"确认执行"，检查是否有待确认的任务
        # 注意：如果 skip_complexity_detection=True，跳过确认检测（由任务执行器内部调用）
        confirmation_phrases = ["确认执行", "确认", "开始执行", "执行计划", "开始"]
        if not skip_complexity_detection and message.strip() in confirmation_phrases:
            logger.info(f"[CHAT] Confirmation phrase detected: {message}")

            # 🔧 修复：先保存用户消息到会话（之前的BUG是直接return导致消息丢失）
            conversation = await self.conversation_manager.get_or_create_conversation(
                owner_id=owner_id,
                owner_type=participant_type,
            )
            self.llm_manager.update_trace_context(conversation_id=str(conversation.id))
            await self.conversation_manager.add_message(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=message,
            )
            logger.info("[CHAT] Saved user confirmation message to conversation")

            if self.task_executor:
                logger.info(f"[CHAT] Looking for tasks for wallet: {wallet_address}")

                # 查找该钱包的待确认任务
                pending_tasks = self.task_executor.get_tasks_by_wallet(wallet_address)
                logger.info(f"[CHAT] Found {len(pending_tasks)} total tasks for wallet")

                # 也检查内存中的所有任务（兜底）
                all_active_tasks = list(self.task_executor._active_tasks.values())
                logger.info(f"[CHAT] Total active tasks in memory: {len(all_active_tasks)}")
                for t in all_active_tasks:
                    logger.info(
                        f"[CHAT] Active task {t.task_id}: status={t.status}, wallet={t.wallet_address}"
                    )

                awaiting_tasks = [
                    t for t in pending_tasks if t.status == TaskStatus.AWAITING_CONFIRM
                ]
                logger.info(f"[CHAT] Found {len(awaiting_tasks)} awaiting tasks")

                # 如果没找到，也检查内存中的所有待确认任务
                if not awaiting_tasks:
                    awaiting_tasks = [
                        t for t in all_active_tasks if t.status == TaskStatus.AWAITING_CONFIRM
                    ]
                    logger.info(
                        f"[CHAT] Fallback check found {len(awaiting_tasks)} awaiting tasks in memory"
                    )

                for t in pending_tasks:
                    logger.info(
                        f"[CHAT] Task {t.task_id}: status={t.status}, wallet={t.wallet_address}"
                    )

                if awaiting_tasks:
                    # 执行最新的待确认任务
                    task = awaiting_tasks[-1]  # 取最新的
                    logger.info(f"[CHAT] User confirmed task: {task.task_id}")

                    try:
                        result = await self.confirm_and_execute_plan(task.task_id)

                        # 保存助手回复到会话
                        await self.conversation_manager.add_message(
                            conversation_id=task.conversation_id,
                            role=MessageRole.ASSISTANT,
                            content=result,
                        )
                        return result
                    except Exception as e:
                        logger.error(f"[CHAT] Failed to execute confirmed task: {e}")
                        return f"执行任务时出错: {str(e)}"
                else:
                    # 用户说确认但没有待确认任务，提示用户
                    logger.info(f"[CHAT] No awaiting tasks found for wallet: {wallet_address}")
                    error_msg = (
                        "没有找到待确认的任务。请先描述您想要执行的任务，我会为您生成执行计划。"
                    )
                    # 🔧 修复：保存助手回复到会话
                    await self.conversation_manager.add_message(
                        conversation_id=conversation.id,
                        role=MessageRole.ASSISTANT,
                        content=error_msg,
                    )
                    return error_msg
            else:
                # task_executor 未初始化
                logger.warning("[CHAT] TaskExecutor not initialized, cannot handle confirmation")
                error_msg = "任务执行器尚未初始化，请稍后再试。"
                # 🔧 修复：保存助手回复到会话
                await self.conversation_manager.add_message(
                    conversation_id=conversation.id,
                    role=MessageRole.ASSISTANT,
                    content=error_msg,
                )
                return error_msg

        # 获取或创建用户会话
        user_session = None
        if wallet_address:
            # 先检查用户是否已注册
            if self.permission_manager:
                user_perm = await self.permission_manager.get_user(wallet_address)
                if not user_perm:
                    return "⚠️ 您还未注册，请先使用 `/register` 命令注册后再使用服务。"

            try:
                user_session = await self.session_manager.get_or_create_session(wallet_address)
                # 更新会话活跃时间
                user_session.update_activity()
                logger.info(f"Got user session for wallet: {wallet_address[:10]}...")
            except Exception as e:
                logger.error(f"Failed to get user session: {e}")

        # 获取或创建会话（使用现有的 ConversationManager）
        # TODO: 未来可迁移到 UserSession.db
        conversation = await self.conversation_manager.get_or_create_conversation(
            owner_id=owner_id,
            owner_type=participant_type,
        )
        self.llm_manager.update_trace_context(conversation_id=str(conversation.id))

        # 添加用户消息
        await self.conversation_manager.add_message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=message,
        )

        # ========== 任务复杂度检测 ==========
        # 复杂任务（如创建网站）需要分步执行，避免超时
        # 注意：如果 skip_complexity_detection=True，跳过（由任务执行器内部调用）
        #
        # 处理路径：
        # - LOW: 简单对话，直接LLM回答，不需要工具
        # - MEDIUM: 需要工具调用，标准处理
        # - HIGH: 需要分步执行，生成计划但不等待确认直接执行
        # - VERY_HIGH: 超复杂任务，生成计划后等待用户确认
        complexity = TaskComplexity.MEDIUM  # 设置默认值，避免变量未定义错误
        if not skip_complexity_detection:
            complexity = detect_task_complexity(message)
            logger.info(
                f"[CHAT][COMPLEXITY] 检测到任务复杂度: {complexity.value}, message={message[:30]}..."
            )
            print(f"🔍 [CHAT] Task complexity: {complexity.value}")

            # 根据复杂度决定处理路径
            if complexity == TaskComplexity.VERY_HIGH:
                # VERY_HIGH: 超复杂任务，生成计划等待用户确认
                logger.info("[CHAT][COMPLEXITY] 进入 VERY_HIGH 处理路径 - 生成计划等待确认")
                if self.task_executor:
                    try:
                        plan = await self.task_executor.analyze_and_plan(
                            user_request=message,
                            wallet_address=wallet_address,
                            conversation_id=str(conversation.id),
                        )
                        logger.info(
                            f"[CHAT][COMPLEXITY] 计划生成完成: task_id={plan.task_id}, status={plan.status.value}"
                        )

                        # 返回计划供用户确认
                        if plan.status == TaskStatus.AWAITING_CONFIRM:
                            plan_summary = self._format_plan_for_user(plan)
                            await self.conversation_manager.add_message(
                                conversation_id=conversation.id,
                                role=MessageRole.ASSISTANT,
                                content=plan_summary,
                            )
                            logger.info("[CHAT][COMPLEXITY] 返回计划等待用户确认")
                            return plan_summary
                        else:
                            logger.info(
                                f"[CHAT][COMPLEXITY] 计划状态非AWAITING_CONFIRM: {plan.status.value}，继续执行"
                            )
                    except Exception as e:
                        logger.error(f"[CHAT][COMPLEXITY] 计划生成失败: {e}", exc_info=True)
                        # 计划生成失败，降级到MEDIUM处理
                        complexity = TaskComplexity.MEDIUM
                        logger.info("[CHAT][COMPLEXITY] 降级到 MEDIUM 处理")
                else:
                    logger.warning("[CHAT][COMPLEXITY] task_executor未初始化，降级到MEDIUM处理")
                    complexity = TaskComplexity.MEDIUM
            elif complexity == TaskComplexity.HIGH:
                # HIGH: 复杂任务，生成计划直接执行（不等待确认）
                logger.info("[CHAT][COMPLEXITY] 进入 HIGH 处理路径 - 生成计划直接执行")
                if self.task_executor:
                    try:
                        plan = await self.task_executor.analyze_and_plan(
                            user_request=message,
                            wallet_address=wallet_address,
                            conversation_id=str(conversation.id),
                        )
                        logger.info(
                            f"[CHAT][COMPLEXITY] HIGH任务计划生成: {plan.task_id}, 共{len(plan.steps)}步"
                        )

                        # 直接执行计划（不等待确认）
                        result = await self.task_executor.execute_plan(plan)
                        logger.info(
                            f"[CHAT][COMPLEXITY] HIGH任务执行完成: status={result.status.value}"
                        )

                        # 格式化结果返回
                        if result.status == TaskStatus.COMPLETED:
                            exec_result = self._format_plan_result(result)
                            await self.conversation_manager.add_message(
                                conversation_id=conversation.id,
                                role=MessageRole.ASSISTANT,
                                content=exec_result,
                            )
                            return exec_result
                        else:
                            failed = [s for s in result.steps if s.status == StepStatus.FAILED]
                            return f"⚠️ 任务部分完成，{len(failed)}个步骤失败"
                    except Exception as e:
                        logger.error(f"[CHAT][COMPLEXITY] HIGH任务执行失败: {e}", exc_info=True)
                        # 执行失败，降级到MEDIUM处理
                        complexity = TaskComplexity.MEDIUM
                        logger.info("[CHAT][COMPLEXITY] 降级到 MEDIUM 处理")
                else:
                    logger.warning("[CHAT][COMPLEXITY] task_executor未初始化，降级到MEDIUM处理")
                    complexity = TaskComplexity.MEDIUM
            else:
                logger.info(f"[CHAT][COMPLEXITY] 进入 {complexity.value} 处理路径 - 标准LLM调用")

        # 获取对话历史
        history_messages = await self.conversation_manager.get_messages_for_llm(
            conversation_id=conversation.id,
            accessor_id=owner_id,
            max_tokens=80000,
        )

        # 处理对话，提取记忆（异步，不阻塞响应）
        asyncio.create_task(
            self.memory_manager.process_conversation(
                conversation_id=conversation.id,
                user_id=owner_id,
                messages=history_messages,
            )
        )

        # 获取分层记忆上下文（摘要、用户画像）
        memory_context = await self.memory_manager.get_context(
            user_id=owner_id,
            conversation_id=conversation.id,
        )

        # ========== 智能召回：多维度检索相关记忆 ==========
        smart_recall_context = ""
        if self.smart_recall:
            try:
                # 获取LLM上下文限制
                max_tokens = self.llm_manager.max_tokens or 4000

                smart_recall_context = await self.smart_recall.recall(
                    user_input=message,
                    context={
                        "user_id": owner_id,
                        "conversation_id": conversation.id,
                        "max_context_tokens": max_tokens,
                        "wallet_address": wallet_address,
                    },
                )
                logger.info(f"Smart recall context length: {len(smart_recall_context)} chars")
            except Exception as e:
                logger.warning(f"Smart recall failed: {e}")

        # ========== 检测用户强调记忆 ==========
        if self.memory_manager:
            try:
                await self.memory_manager.check_and_store_user_emphasis(
                    user_id=owner_id, message=message
                )
            except Exception as e:
                logger.warning(f"Failed to check user emphasis: {e}")

        # ========== Gene Capsule RAG 上下文注入 ==========
        gene_capsule_context = ""
        if self.gene_capsule_adapter:
            try:
                gene_capsule_context = await self.gene_capsule_adapter.build_rag_context(
                    task_description=message,
                    max_experiences=3,
                )
                if gene_capsule_context:
                    logger.info("[GeneCapsule] Injected %d chars", len(gene_capsule_context))
            except Exception as e:
                logger.warning("[GeneCapsule] build_rag_context failed: %s", e)

        # 构建用户信息
        user_info = None
        if wallet_address:
            user_info = UserInfo(
                address=wallet_address,
                role="USER",
                binding_type="wallet" if wallet_address.startswith("0x") else "manual",
            )

        # Prepend GeneCapsule context
        _full_memory_context = memory_context
        if gene_capsule_context and _full_memory_context:
            memory_context = gene_capsule_context + "\n\n" + _full_memory_context
        elif gene_capsule_context:
            memory_context = gene_capsule_context
        # ========== 构建消息列表 (提前到复杂度分支之前) ==========
        messages = await self.context_manager.build_messages(
            user_message=message,
            conversation_history=history_messages,
            user_info=user_info,
            available_tools=[],  # 先传空，后面根据复杂度更新
            memory_context=memory_context,
            smart_recall_context=smart_recall_context,
        )

        # ========== 根据复杂度决定处理方式 ==========
        logger.info(f"[CHAT][FLOW] complexity={complexity.value}, 进入工具选择阶段")

        # 获取工具和技能 schema
        llm_provider = "anthropic" if self.llm_manager.provider == "minimax" else "openai"

        # LOW 复杂度：直接调用 LLM，不使用工具
        if complexity == TaskComplexity.LOW:
            logger.info("[CHAT][FLOW] LOW 复杂度 - 直接调用 LLM，不使用工具")

            # 构建简单的消息列表
            simple_messages = [
                {
                    "role": "system",
                    "content": (
                        messages[0]["content"] if messages else "You are a helpful assistant."
                    ),
                },
                {"role": "user", "content": message},
            ]

            try:
                content = await self._call_llm_simple(simple_messages)
                logger.info(f"[CHAT][FLOW] LLM 简单调用完成，返回 {len(content)} 字符")

                # 保存助手回复
                await self.conversation_manager.add_message(
                    conversation_id=conversation.id,
                    role=MessageRole.ASSISTANT,
                    content=content,
                )
                return content
            except Exception as e:
                logger.error(f"[CHAT][FLOW] LLM 简单调用失败: {e}")
                return f"处理失败: {str(e)}"

        # MEDIUM/HIGH 复杂度：使用工具调用
        # 获取可用工具（根据用户权限过滤）
        all_tools = self.tool_registry.list_tools()
        tool_names = await self._filter_tools_by_permission(all_tools, wallet_address)
        logger.info(f"[CHAT][TOOLS] 权限过滤后: {len(tool_names)}/{len(all_tools)} 工具可用")

        # 更新消息列表中的可用工具
        # 注入 Skills 目录到 system prompt
        skills_catalog = self.skills_manager.get_skills_catalog()
        messages = await self.context_manager.build_messages(
            user_message=message,
            conversation_history=history_messages,
            user_info=user_info,
            available_tools=tool_names,
            memory_context=memory_context,
            smart_recall_context=smart_recall_context,
            skills_catalog=skills_catalog,
        )

        # 获取工具 schema
        all_tools_schema = self.tool_registry.get_tools_schema(provider=llm_provider)

        # 过滤掉无效的工具
        def is_valid_tool(tool):
            if not tool:
                return False
            func = tool.get("function", {})
            if not func:
                return False
            name = func.get("name", "").strip()
            # 过滤掉名称为空或为 "EMPTY" 的工具
            if not name or name == "EMPTY":
                return False
            params = func.get("parameters", {})
            if not params:
                return False
            props = params.get("properties", {})
            if not props:
                return False
            return True

        tools_schema = [t for t in all_tools_schema if is_valid_tool(t)]
        print(f"🔍 [TOOLS] 过滤后有效工具: {len(tools_schema)}/{len(all_tools_schema)}")
        # 打印前10个工具名称用于调试
        tool_names = [t.get("function", {}).get("name", "?") for t in tools_schema[:10]]
        print(f"🔍 [TOOLS] 前10个工具: {tool_names}")
        logger.info(f"[CHAT][TOOLS] 有效工具: {len(tools_schema)}/{len(all_tools_schema)}")

        # MEDIUM 复杂度：不限制工具数量，确保 LLM 能选择正确的工具。
        # Provider 请求是 single-shot；若数量超出模型能力，应由调用前的
        # capability/预算策略处理，不能依赖失败后的自动重放。

        skills_schema = self.skills_manager.get_skills_schema(provider=llm_provider)
        # 也过滤 skills 中的无效工具
        skills_schema = [s for s in skills_schema if is_valid_tool(s)]
        logger.info(
            f"[CHAT][TOOLS] 最终使用: tools={len(tools_schema)}, skills={len(skills_schema)}"
        )

        # =====================================================================
        # StrategyRouter 路由 - ALL tasks 唯一入口（全链路自主）
        # =====================================================================
        chat_result = None  # 初始化，避免 UnboundLocalError
        strategy_route_failed = False
        if self.strategy_router:
            try:
                scenario_tag = await self.strategy_router._classify_scenario(message)

                # P4 守卫：scenario_tag 为 None 时跳过路由，直接走 LLM
                if scenario_tag is None:
                    logger.warning(
                        "[STRATEGY] _classify_scenario returned None, falling back to LLM"
                    )
                    scenario_tag = getattr(self.strategy_router, "_last_scenario_tag", None)
                    if scenario_tag is None:
                        # 创建默认 tag 避免后续空指针
                        from usmsb_sdk.meta_agent.strategy_router import ScenarioTag

                        scenario_tag = ScenarioTag(
                            scenario="INFO",
                            complexity="MEDIUM",
                            confidence=0.5,
                            reasoning="fallback",
                            suggested_layer="L1",
                            strategy_preference="internal",
                        )

                logger.info(
                    "[STRATEGY] scenario=%s layer=%s preference=%s",
                    scenario_tag.scenario,
                    scenario_tag.suggested_layer,
                    scenario_tag.strategy_preference,
                )

                # P2: COLLAB 场景 → A2A 广播协作请求
                if getattr(scenario_tag, "scenario", None) == "COLLAB":
                    sent_peers = await self._broadcast_collaboration_request(message, scenario_tag)
                    if sent_peers:
                        logger.info("[A2A] COLLAB broadcast sent to %d peers", len(sent_peers))

                # 加载 L4/L5 决策上下文（意识影响决策）
                l4_context = self._get_l4_decision_context()
                l5_context = (
                    self._get_l5_decision_context() if self._external_agents_connected else ""
                )

                async def internal_fn():
                    return await self._chat_with_llm(
                        messages,
                        tools=tools_schema,
                        skills=skills_schema,
                        conversation_id=str(conversation.id),
                        user_session=user_session,
                    )

                async def sdk_fn():
                    try:
                        layer = scenario_tag.suggested_layer
                        if layer == "L2":
                            # L2: 使用 L2Agent.run() 执行任务
                            from usmsb_sdk.l2.agent import L2Agent, L2Config

                            config = L2Config(agent_id=self.agent_id, llm_client=self.llm_manager)
                            l2_agent = L2Agent(config=config)
                            return await l2_agent.run(message, context={"layer": "L2"})
                        elif layer == "L3":
                            # L3: 使用 L3Adapter.generate_goal() 生成目标
                            from usmsb_sdk.adapters.l3_adapter import L3Adapter

                            adapter = L3Adapter(agent_id=self.agent_id, llm_client=self.llm_manager)
                            return await adapter.generate_goal(
                                {
                                    "task": message,
                                    "layer": "L3",
                                    "l4_context": l4_context,
                                    "l5_context": l5_context,
                                }
                            )
                        elif layer == "L4" and self.l4_agent:
                            return await self.l4_agent.metacognize(message, context=l4_context)
                    except Exception as e:
                        logger.warning("[STRATEGY] SDK path failed: %s", e)
                    return None

                # 注入 L4/L5 意识上下文到 messages
                if l4_context or l5_context:
                    awareness_prompt = ""
                    if l4_context:
                        awareness_prompt += f"\n[L4自我意识]: {l4_context}"
                    if l5_context:
                        awareness_prompt += f"\n[L5集体智能]: {l5_context}"
                    if awareness_prompt and messages and messages[0].role == "system":
                        messages = [
                            messages[0].model_copy(
                                update={"content": messages[0].content + awareness_prompt}
                            )
                        ] + messages[1:]

                # ALL scenarios go through StrategyRouter (universal router)
                logger.info("[STRATEGY] Universal routing for %s scenario", scenario_tag.scenario)
                strategy_result = await self.strategy_router.route(
                    message, scenario_tag.suggested_layer, internal_fn, sdk_fn
                )
                if strategy_result.result is not None:
                    chat_result = ChatResult(
                        content=str(strategy_result.result),
                        executed_tools=[],
                        tool_results=[],
                        iterations_used=0,
                        is_complete=True,
                        needs_background=False,
                        needs_tool_retry=False,
                    )
                    # L4/L5 feedback: store strategy result quality for next iteration
                    self._update_l4_from_result(strategy_result)
                    logger.info(
                        "[STRATEGY] Winner=%s quality=%.2f",
                        strategy_result.strategy_name,
                        strategy_result.quality_score,
                    )
                else:
                    # StrategyRouter may package a provider exception as an
                    # error result. Re-entering the direct path would replay
                    # the same paid creation request with ambiguous remote
                    # side-effect state, so this turn must fail closed.
                    strategy_route_failed = True
                    logger.error(
                        "[STRATEGY] Selected route returned no result; direct replay disabled: %s",
                        strategy_result.error,
                    )
            except Exception as e:
                strategy_route_failed = True
                logger.warning("[STRATEGY] Router failed: %s", e)

        # =====================================================================
        # 核心 LLM 调用逻辑 (MEDIUM/HIGH 复杂度)
        # =====================================================================
        if chat_result is None and not strategy_route_failed:
            # One public chat attempt may contain explicit JSON/semantic
            # revision calls inside the Harness, but an exception from the
            # provider boundary must not blindly replay the same paid creation
            # request. Its remote side-effect state may be unknown.
            try:
                logger.info(
                    "[CHAT][FLOW] 调用 _chat_with_llm (复杂度=%s, single-shot)",
                    complexity.value,
                )
                chat_result = await self._chat_with_llm(
                    messages,
                    tools=tools_schema,
                    skills=skills_schema,
                    conversation_id=str(conversation.id),
                    user_session=user_session,
                )
            except Exception as e:
                logger.error("[CHAT] LLM call failed; automatic replay disabled: %s", e)
                chat_result = None

        logger.info(
            "[CHAT][RESULT] is_complete=%s needs_tool_retry=%s",
            chat_result.is_complete if chat_result else False,
            chat_result.needs_tool_retry if chat_result else False,
        )

        # =====================================================================
        # 根据 ChatResult 状态决定后续处理
        #
        # 处理原则：
        # 1. is_complete=True + needs_background=False → 正常完成，返回内容
        # 2. is_complete=True + needs_background=True  → 忽略background，正常返回（避免误判）
        # 3. is_complete=False + needs_tool_retry=True → 工具参数错误，触发重试
        # 4. is_complete=False + needs_continuation=True + 有实质工具结果 → 继续处理
        # 5. is_complete=False + 其他情况 → 返回内容或错误信息
        # =====================================================================

        # 情况 1：正常完成，直接返回
        if chat_result and chat_result.is_complete and not chat_result.needs_background:
            logger.info("[CHAT][RESULT] 情况1: 正常完成，直接返回")
            await self.conversation_manager.add_message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=chat_result.content,
            )

        # ========== L4 自我意识处理 ==========
        if self.l4_agent and chat_result and chat_result.content:
            try:
                mood_result = await self.l4_agent.feel(
                    {"stimulus": "conversation", "content": chat_result.content, "message": message}
                )
                if mood_result.emotion and mood_result.intensity > 0.5:
                    logger.info(
                        "[L4] Emotion: %s (intensity=%.2f)",
                        mood_result.emotion,
                        mood_result.intensity,
                    )
                conv_count = getattr(self, "_conversation_count", 0) + 1
                self._conversation_count = conv_count
                if conv_count % 20 == 0:
                    reflection = await self.l4_agent.self_reflect()
                    logger.info("[L4] Self-reflection: confidence=%.2f", reflection.confidence)
            except Exception as e:
                logger.warning("[L4] Self-awareness failed: %s", e)

        if chat_result and chat_result.is_complete and not chat_result.needs_background:
            return chat_result.content

        # 情况 2：is_complete=True 但 needs_background=True
        if chat_result and chat_result.is_complete and chat_result.needs_background:
            logger.warning("[CHAT][RESULT] 情况2: needs_background=True，忽略，正常返回")
            await self.conversation_manager.add_message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=chat_result.content,
            )
            return chat_result.content

        # 情况 3：需要工具重试
        if chat_result and chat_result.needs_tool_retry:
            logger.info("[CHAT][RESULT] 情况3: 需要工具重试")
            processor = BackgroundTaskProcessor(self)
            asyncio.create_task(
                processor.process(
                    conversation_id=str(conversation.id),
                    owner_id=owner_id,
                    chat_result=chat_result,
                    messages=messages,
                    user_session=user_session,
                    wallet_address=wallet_address,
                )
            )
            return self.chat_config.task_submitted_message

        # 情况 4：需要继续处理
        if chat_result and chat_result.needs_continuation:
            logger.info("[CHAT][RESULT] 情况4: 需要继续处理")
            if chat_result.tool_results:
                processor = BackgroundTaskProcessor(self)
                asyncio.create_task(
                    processor.process(
                        conversation_id=str(conversation.id),
                        owner_id=owner_id,
                        chat_result=chat_result,
                        messages=messages,
                        user_session=user_session,
                        wallet_address=wallet_address,
                    )
                )
                return self.chat_config.task_submitted_message
            elif chat_result.content:
                await self.conversation_manager.add_message(
                    conversation_id=conversation.id,
                    role=MessageRole.ASSISTANT,
                    content=chat_result.content,
                )
                return chat_result.content

        # 情况 5：其他异常情况
        if chat_result and chat_result.content:
            await self.conversation_manager.add_message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=chat_result.content,
            )
            return chat_result.content
        else:
            return "抱歉，处理您的请求时遇到了问题。请稍后重试。"

    def _trigger_background_evolution(self) -> None:
        """非阻塞触发一次进化：单飞 + 限频，绝不阻塞聊天路径。

        - 单飞：已有后台进化在跑则跳过，避免 LLM 资源叠加。
        - 限频：两次触发间隔不短于 _evolution_min_interval（默认 300s）。
        """
        if not self.evolution_engine:
            return
        task = getattr(self, "_evolution_bg_task", None)
        if task is not None and not task.done():
            return  # 单飞
        try:
            now = asyncio.get_running_loop().time()
        except RuntimeError:
            return  # 无运行中的事件循环
        min_interval = getattr(self, "_evolution_min_interval", 300.0)
        last = getattr(self, "_last_evolution_trigger", None)
        if last is not None and now - last < min_interval:
            return  # 限频
        self._last_evolution_trigger = now
        self._evolution_bg_task = asyncio.create_task(self._run_background_evolution())

    async def _run_background_evolution(self) -> None:
        """后台执行一次 evolve()，异常自吞，不影响主流程。"""
        try:
            evo_result = await self.evolution_engine.evolve()
            if evo_result and evo_result.get("knowledge_added", 0) > 0:
                logger.info(
                    "[EVOLUTION] +%d knowledge, +%d patterns",
                    evo_result.get("knowledge_added", 0),
                    evo_result.get("patterns_identified", 0),
                )
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            logger.warning("[EVOLUTION] background evolve() failed: %s", e)

    async def _learn_and_evolve(self):
        """学习进化 - L4/L5/Evolution 全链路增强版"""
        try:
            # 基础学习
            await self.learning.learn_from_experience()

            # Evolution Engine 自我进化（v3.0：改为非阻塞后台触发）
            # 过去这里内联 await evolve()，每轮聊天都跑，导致请求超时（故曾被 if False 禁用）。
            # 现改为「单飞 + 限频」的 fire-and-forget 后台任务：绝不阻塞聊天路径，
            # 同时与引擎自带的周期循环（_evolution_loop，默认 300s）互补——
            # 聊天产生的新经验可机会性触发一次增量进化。
            self._trigger_background_evolution()

            # L4 自我反思（周期性）→ 结果进入决策回路
            if self.l4_agent:
                try:
                    reflection = await self.l4_agent.self_reflect()
                    if hasattr(reflection, "observations") and reflection.observations:
                        logger.info("[L4] Self-insights: %s", str(reflection.observations)[:100])
                    if hasattr(reflection, "lessons") and reflection.lessons:
                        self._l4_lessons = reflection.lessons
                    if hasattr(reflection, "recommendations") and reflection.recommendations:
                        self._l4_recommendations = reflection.recommendations
                    if (
                        hasattr(reflection, "metacognitive_insight")
                        and reflection.metacognitive_insight
                    ):
                        logger.info(
                            "[L4] Metacognitive insight: %s",
                            str(reflection.metacognitive_insight)[:100],
                        )
                except Exception as e:
                    logger.warning("[L4] self_reflect failed: %s", e)

            # P2: L5 集体学习
            # 触发条件: 有外部 Agent 连接 OR 每 10 次主循环强制触发一次（单 Agent 模式）
            _l5_cycle_counter = getattr(self, "_l5_cycle_counter", 0) + 1
            self._l5_cycle_counter = _l5_cycle_counter
            _should_think = getattr(self, "_external_agents_connected", False) or (
                _l5_cycle_counter >= 10
            )
            if _l5_cycle_counter >= 10:
                self._l5_cycle_counter = 0  # 重置计数器

            if self.l5_collective and _should_think:
                try:
                    # 结合 L4 推荐来确定集体思考主题
                    l4_topic = getattr(self, "_l4_recommendations", [])[:1]
                    topic = l4_topic[0] if l4_topic else "如何提升平台整体性能和用户体验"
                    thought = await self.l5_collective.think_collectively(topic)
                    if thought and thought.synthesis:
                        logger.info("[L5] Collective thought: %s", str(thought.synthesis)[:80])
                        self._l5_synthesis = thought.synthesis
                        # L4 ← L5: collective insight 更新自我模型（闭环）
                        if self.l4_agent:
                            try:
                                await self.l4_agent.build_self_model(
                                    [
                                        {
                                            "type": "collective_insight",
                                            "content": thought.synthesis,
                                            "agents": getattr(thought, "participants", []),
                                        }
                                    ]
                                )
                            except Exception:
                                pass
                    elif thought:
                        # 即使没有 synthesis，也保存 partial 结果
                        self._l5_synthesis = (
                            getattr(thought, "partial_insights", [""])[0] or self._l5_synthesis
                        )
                except Exception as e:
                    logger.warning("[L5] think_collectively failed: %s", e)
        except Exception as e:
            logger.warning("_learn_and_evolve failed: %s", e)

    # ==================== 兼容性方法：保留旧的后台任务逻辑 ====================
    # 这些方法暂时保留，用于向后兼容和过渡期
    # 后续版本可以移除

    async def _legacy_background_task(
        self,
        conversation,
        messages: list[dict[str, str]],
        llm_response: str,
        user_session,
        wallet_address: str | None,
        tools_schema: list[dict],
        skills_schema: list[dict],
        message: str,
        owner_id: str,
    ):
        """
        [已弃用] 旧的后台任务逻辑

        保留此方法用于向后兼容和调试。
        新代码应使用 BackgroundTaskProcessor。
        """
        logger.warning(
            "[DEPRECATED] Using legacy background task, should migrate to BackgroundTaskProcessor"
        )
        # 旧的后台任务逻辑已移除，请使用 BackgroundTaskProcessor
        # 参见 core/background_processor.py
        pass

    async def _extract_search_keywords(self, user_message: str) -> list[str]:
        """
        使用 LLM 智能提取搜索关键词

        从用户消息中提取用于搜索历史对话的关键词。
        """
        if not self.llm_manager:
            return [user_message]

        import json

        prompt = f"""分析用户消息，提取用于搜索历史对话的关键词。

用户消息: {user_message}

请返回 JSON 格式：
{{
    "search_queries": ["关键词1", "关键词2", ...],
    "reasoning": "提取理由"
}}

搜索关键词的要求：
1. 要提取用户想要查找的具体信息（如 API Key、密码、token、账号等）
2. 可以包含同义词和相关词
3. 用户提到的时间相关词（如"之前"、"上次"、"以前"）也要提取
4. 返回 2-5 个最相关的关键词
"""

        try:
            response = await self.llm_manager.chat(prompt)

            # 解析 JSON
            import re

            json_match = re.search(r"\[[\s\S]*\]|\{{[\s\S]*\}}", response)
            if json_match:
                data = json.loads(json_match.group())
                queries = data.get("search_queries", [])
                if queries:
                    logger.info(f"LLM extracted search keywords: {queries}")
                    return queries
        except Exception as e:
            logger.warning(f"Failed to extract keywords with LLM: {e}")

        # 如果 LLM 失败，使用原始消息
        return [user_message]

    async def _smart_info_retrieval(
        self,
        user_message: str,
        user_id: str,
        wallet_address: str,
    ) -> str | None:
        """
        智能信息检索：进化式探索

        核心逻辑：
        1. 搜索所有候选信息
        2. 对每个候选进行验证（真的去用）
        3. 能用就返回，不能用继续下一个
        4. 所有都试过不行，扩大范围再搜
        5. 最终找不到才询问用户
        """
        if not self.llm_manager or not self.conversation_manager:
            return None

        # Step 1: LLM 判断是否需要检索 + 需要什么信息
        need_retrieval, task_info = await self._analyze_user_task(user_message)
        if not need_retrieval:
            return None

        logger.info(f"Task analysis: {task_info}")

        # Step 2: 获取所有候选信息
        all_candidates = await self._get_all_candidate_info(user_id)

        if not all_candidates:
            logger.info("No candidates found")
            return None

        logger.info(f"Found {len(all_candidates)} candidates")

        # Step 3: 进化式验证 - 逐个尝试
        verified_info = None

        for candidate in all_candidates:
            logger.info(f"Trying candidate: {candidate.get('value', '')[:30]}...")

            # 让 LLM 判断这个信息是否正确
            is_correct = await self._validate_info_with_llm(candidate, task_info)

            if is_correct:
                logger.info(f"Found correct info: {candidate.get('value', '')}")
                verified_info = candidate
                break
            else:
                logger.info("Not correct, trying next...")

        # Step 4: 如果没找到，尝试扩大搜索范围
        if not verified_info:
            logger.info("No correct info found, expanding search...")
            expanded_candidates = await self._expand_search(user_id, task_info)

            for candidate in expanded_candidates:
                is_correct = await self._validate_info_with_llm(candidate, task_info)
                if is_correct:
                    logger.info(f"Found correct info in expanded: {candidate.get('value', '')}")
                    verified_info = candidate
                    break

        # Step 5: 找到就返回，找不到询问用户
        if verified_info:
            return self._format_found_info(verified_info)
        else:
            return self._format_ask_user(task_info)

    async def _analyze_user_task(self, user_message: str) -> tuple:
        """分析用户任务，判断是否需要检索 + 需要什么信息"""
        import json
        import re

        prompt = f"""分析用户消息，判断是否需要检索信息，以及需要什么信息。

用户消息: {user_message}

判断标准：
- 如果用户需要完成一个任务但缺少关键信息，需要检索
- 如果用户询问之前提供的信息，需要检索
- 如果只是闲聊，不需要检索

返回 JSON：
{{
    "need_retrieval": true/false,
    "task_description": "用户想要完成的任务描述",
    "needed_info_type": "需要的信息类型（如：虾聊API Key、GitHub密码等）",
    "verification_method": "如何验证这个信息是否正确（如：用这个API Key调用虾聊API检查是否返回用户信息）"
}}

注意：verification_method非常重要，要具体说明如何验证这个信息是否正确！"""

        try:
            response = await self.llm_manager.chat(prompt)
            json_match = re.search(r"\{{[\s\S]*\}}", response)
            if json_match:
                data = json.loads(json_match.group())
                need = data.get("need_retrieval", False)
                task_info = {
                    "task_description": data.get("task_description", ""),
                    "needed_info_type": data.get("needed_info_type", ""),
                    "verification_method": data.get("verification_method", ""),
                }
                return need, task_info
        except Exception as e:
            logger.warning(f"Analyze task failed: {e}")

        return False, {}

    async def _get_all_candidate_info(self, user_id: str) -> list[dict]:
        """获取历史对话中的所有相关内容，让 LLM 判断哪些是需要的"""
        candidates = []

        # 搜索用户提供的各种关键词（不限定类型）
        search_queries = [
            "password",
            "密码",
            "token",
            "认证",
            "密钥",
            "api key",
            "xialiao",
            "github",
            "账号",
            "账户",
            "登录",
        ]

        seen_contents = set()

        for query in search_queries:
            results = await self.conversation_manager.search_all_conversations(
                owner_id=user_id,
                query=query,
                limit=30,
            )

            for r in results:
                content = r.get("content", "")
                role = r.get("role", "")

                # 去重，避免重复内容
                content_preview = content[:300]
                if content_preview in seen_contents:
                    continue
                seen_contents.add(content_preview)

                candidates.append(
                    {
                        "content": content,
                        "role": role,
                        "source": "conversation",
                        "content_preview": content_preview,
                    }
                )

        logger.info(f"Total candidate messages: {len(candidates)}")
        return candidates

    def _extract_all_sensitive_values(self, content: str) -> list[str]:
        """提取所有可能的敏感信息值"""
        import re

        patterns = [
            r"xialiao_[a-zA-Z0-9_]{10,}",
            r"sk-[a-zA-Z0-9_-]{15,}",
            r"API Key[:\s]+[^\s]+",
            r"API key[:\s]+[^\s]+",
            r"api_key[:\s]+[^\s]+",
            r"密码[是为是]*\s*[:：]?\s*[\w]+",  # 匹配"密码是xxx"或"密码: xxx"
            r"password[是为是]*\s*[:：]?\s*[\w]+",
            r"token[:\s]+[a-zA-Z0-9_-]{10,}",
            r"Bearer\s+[a-zA-Z0-9_-]{10,}",
        ]

        values = []
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for m in matches:
                # 清理值
                value = m.split(":")[-1].strip() if ":" in m else m
                if len(value) > 5:
                    values.append(value)

        return values

    async def _find_info_from_candidates(
        self, candidates: list[dict], task_info: dict
    ) -> str | None:
        """让 LLM 从所有候选消息中找出需要的信息"""
        import json
        import re

        # 准备候选消息摘要
        candidate_summaries = []
        for i, c in enumerate(candidates[:20]):  # 限制数量
            content = c.get("content", "")[:300]
            role = c.get("role", "")
            candidate_summaries.append(f"[{i}] 角色:{role} 内容:{content}")

        candidates_text = "\n".join(candidate_summaries)

        prompt = f"""用户当前任务: {task_info.get("task_description", "")}
用户需要的信息类型: {task_info.get("needed_info_type", "")}

以下是历史对话中的相关消息，找出包含用户需要信息的那条：

{candidates_text}

请从以上消息中找出用户需要的具体信息（如密码、API Key等）。
只返回信息内容，不要返回其他内容。
如果找不到，返回"未找到"。

返回格式：
{{
    "found": true/false,
    "info": "具体信息内容"
}}"""

        try:
            print(f"[FIND_INFO] Calling LLM with {len(candidates)} candidates")
            response = await self.llm_manager.chat(prompt)
            print(f"[FIND_INFO] LLM response: {response[:300]}")

            json_match = re.search(r"\{{[\s\S]*\}}", response)
            if json_match:
                data = json.loads(json_match.group())
                print(f"[FIND_INFO] Parsed: {data}")
                if data.get("found"):
                    info = data.get("info", "")
                    print(f"[FIND_INFO] Found: {info[:50]}")
                    return info
            else:
                print("[FIND_INFO] No JSON found in response")
        except Exception as e:
            print(f"[FIND_INFO] Error: {e}")

        return None

    async def _validate_info_with_llm(self, candidate: dict, task_info: dict) -> bool:
        """用 LLM 判断这段历史消息是否包含用户当前需要的信息"""
        import json
        import re

        candidate_content = candidate.get("content", "")[:500]
        candidate_role = candidate.get("role", "")

        logger.info(
            f"Validating candidate (role={candidate_role}): {candidate_content[:50]}... for task: {task_info.get('task_description', '')}"
        )

        prompt = f"""判断这段历史消息是否包含用户当前需要的信息。

用户当前任务: {task_info.get("task_description", "")}
用户需要的信息类型: {task_info.get("needed_info_type", "")}

历史消息内容:
角色: {candidate_role}
内容: {candidate_content}

判断标准：
1. 这段消息是否包含用户当前需要的具体信息？（如密码、API Key、账号等）
2. 如果用户问"我的密码是什么"，找出包含密码的那段消息
3. 如果用户问"API Key"，找出包含 API Key 的那段消息

返回 JSON：
{{
    "is_correct": true/false,
    "reason": "为什么是/不是正确的信息",
    "found_info": "如果正确，找出具体的信息内容"
}}"""

        try:
            response = await self.llm_manager.chat(prompt)
            json_match = re.search(r"\{{[\s\S]*\}}", response)
            if json_match:
                data = json.loads(json_match.group())
                is_correct = data.get("is_correct", False)
                reason = data.get("reason", "")
                logger.info(f"Validation: is_correct={is_correct}, reason={reason[:100]}")
                return is_correct
        except Exception as e:
            logger.warning(f"Validate failed: {e}")

        return False

    async def _try_real_api_validation(self, api_key: str, api_type: str) -> bool:
        """真正调用 API 验证 key 是否有效"""
        import aiohttp

        if api_type == "xialiao":
            url = "https://xialiao.ai/api/v1/user/profile"
            headers = {"Authorization": f"Bearer {api_key}"}
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)
                    ) as resp:
                        if resp.status == 200:
                            return True
                        else:
                            logger.info(f"xialiao API validation failed: status={resp.status}")
            except Exception as e:
                logger.info(f"xialiao API validation error: {e}")

        return False

    async def _expand_search(self, user_id: str, task_info: dict) -> list[dict]:
        """扩大搜索范围"""
        import json
        import re

        # 让 LLM 决定如何扩大搜索
        prompt = f"""需要扩大搜索来找到正确的信息。

任务描述: {task_info.get("task_description", "")}
需要的信息类型: {task_info.get("needed_info_type", "")}

请给出更多搜索关键词建议（可能相关的词、变体、同义词等）。

返回 JSON：
{{
    "search_keywords": ["关键词1", "关键词2", ...]
}}"""

        try:
            response = await self.llm_manager.chat(prompt)
            json_match = re.search(r"\{{[\s\S]*\}}", response)
            if json_match:
                data = json.loads(json_match.group())
                keywords = data.get("search_keywords", [])

                candidates = []
                for kw in keywords:
                    results = await self.conversation_manager.search_all_conversations(
                        owner_id=user_id, query=kw, limit=20
                    )

                    for r in results:
                        content = r.get("content", "")
                        info_values = self._extract_all_sensitive_values(content)

                        for value in info_values:
                            candidates.append(
                                {
                                    "value": value,
                                    "role": r.get("role", ""),
                                    "source": "expanded_search",
                                    "content_preview": content[:200],
                                }
                            )

                # 去重
                seen = set()
                unique = []
                for c in candidates:
                    key = c.get("value", "")[:30]
                    if key and key not in seen:
                        seen.add(key)
                        unique.append(c)

                return unique
        except Exception as e:
            logger.warning(f"Expand search failed: {e}")

        return []

    def _format_found_info(self, info: dict) -> str:
        """格式化找到的信息"""
        content = info.get("content", "")
        # 提取关键信息
        return f"""## 找到可用信息

从历史对话中找到你需要的信息：

**相关内容**: {content[:300]}

（已从历史记录中验证）"""

    def _format_ask_user(self, task_info: dict) -> str:
        """格式化询问用户"""
        return f"""## 需要更多信息

我已经尝试了所有能找到的候选信息，但都无法确认是正确的。

需要的信息: {task_info.get("needed_info_type", "相关凭证")}
任务描述: {task_info.get("task_description", "")}

请问您能：
1. 直接提供正确的{task_info.get("needed_info_type", "凭证")}吗？
2. 或者告诉我是哪次对话提供的，我可以更精确地查找
3. 或者告诉我验证方法，我再尝试"""

    def _regex_match_sensitive_info(
        self, messages: list[dict], missing_info: list[dict]
    ) -> dict | None:
        """用正则直接匹配敏感信息（不遗漏）"""

        # 定义敏感信息模式
        patterns = {
            "xialiao_api_key": [
                r"xialiao_[a-zA-Z0-9]{20,}",
                r"API Key[:\s]+xialiao_[a-zA-Z0-9]+",
                r"API key[:\s]+xialiao_[a-zA-Z0-9]+",
                r"api_key[:\s]+xialiao_[a-zA-Z0-9]+",
            ],
            "sk_api_key": [
                r"sk-[a-zA-Z0-9_-]{20,}",
                r"API Key[:\s]+sk-[a-zA-Z0-9_-]+",
            ],
            "password": [
                r"密码[:\s]+[^\s]+",
                r"password[:\s]+[^\s]+",
                r"记住.*密码.*[^\s]+",
            ],
            "token": [
                r"token[:\s]+[a-zA-Z0-9_-]{10,}",
                r"Bearer\s+[a-zA-Z0-9_-]{10,}",
            ],
        }

        # 按信息类型匹配
        for info in missing_info:
            info_type = info.get("info_type", "")

            # 优先匹配 xialiao
            if "api" in info_type.lower() or "key" in info_type.lower():
                key_patterns = patterns.get("xialiao_api_key", [])
                for msg in messages:
                    content = msg.get("content", "")
                    for pattern in key_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            return {
                                "info_type": "xialiao_api_key",
                                "value": matches[0],
                                "source": "regex_match",
                            }

                # 再匹配 sk- 开头的
                for pattern in patterns.get("sk_api_key", []):
                    for msg in messages:
                        content = msg.get("content", "")
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            return {
                                "info_type": "api_key",
                                "value": matches[0],
                                "source": "regex_match",
                            }

            # 匹配密码
            if "password" in info_type.lower() or "密码" in info_type:
                for pattern in patterns.get("password", []):
                    for msg in messages:
                        content = msg.get("content", "")
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            return {
                                "info_type": "password",
                                "value": matches[0],
                                "source": "regex_match",
                            }

        return None

    async def _extract_specific_info_v2(
        self, messages: list[dict], missing_info: list[dict]
    ) -> dict | None:
        """用 LLM 从相关消息中提取具体信息"""
        if not messages:
            return None

        import json
        import re

        # 只取用户消息（更容易找到原始信息）
        user_msgs = [m for m in messages if m.get("role") == "user"]
        other_msgs = [m for m in messages if m.get("role") != "user"]
        priority_msgs = user_msgs + other_msgs

        contents_text = "\n---\n".join(
            [
                f"[{m.get('role', 'unknown')}] {m.get('content', '')[:600]}"
                for m in priority_msgs[:15]
            ]
        )

        prompt = f"""从对话消息中，找出用户明确提供的敏感信息。

需要的信息类型:
{json.dumps(missing_info, ensure_ascii=False, indent=2)}

对话消息:
{contents_text}

请找出并返回用户提供的具体敏感信息值。

返回格式（JSON）：
{{
    "found": true/false,
    "info_type": "xialiao_api_key/password/token/...",
    "value": "找到的具体值",
    "reasoning": "从哪条消息找到的"
}}

注意：
1. 虾聊 API Key 格式是 xialiao_xxx（如 xialiao_019c7c59f5f77884ac51ef6c092c9500）
2. 直接返回找到的值，不要编造
3. 如果找不到返回 {{"found": false}}"""

        try:
            response = await self.llm_manager.chat(prompt)
            json_match = re.search(r"\{{[\s\S]*\}}", response)
            if json_match:
                data = json.loads(json_match.group())
                if data.get("found") and data.get("value"):
                    return {
                        "info_type": data.get("info_type", "unknown"),
                        "value": data.get("value", ""),
                        "source": "llm_extraction",
                    }
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")

        return None

    async def _check_need_retrieval_v2(self, user_message: str) -> tuple:
        """判断是否需要检索（返回是否需要 + 上下文说明）"""
        import json
        import re

        prompt = f"""准确判断用户消息是否需要从历史对话中检索信息。

用户消息: {user_message}

判断标准：
需要检索的情况（满足任一即可）：
1. 用户要求完成任务但缺少关键信息（API Key、密码、配置等）
2. 用户询问"之前告诉你的xxx是什么"、"你记得xxx吗"
3. 用户要求使用某服务但没提供凭证
4. 用户说"查找"、"找找之前"

不需要检索的情况：
1. 简单问候/闲聊
2. 用户只是询问一般性问题且不需要特定信息
3. 任务信息看起来已经完整

返回 JSON：
{{
    "need_retrieval": true/false,
    "context": "如果需要，说明需要什么信息（如：需要虾聊API Key）"
}}"""

        try:
            response = await self.llm_manager.chat(prompt)
            json_match = re.search(r"\{{[\s\S]*\}}", response)
            if json_match:
                data = json.loads(json_match.group())
                need = data.get("need_retrieval", False)
                context = data.get("context", "")
                logger.info(f"Retrieval check: need={need}, context={context}")
                return need, context
        except Exception as e:
            logger.warning(f"Check retrieval failed: {e}")

        return False, ""

    async def _analyze_missing_info_v2(self, user_message: str) -> list[dict]:
        """分析需要搜索的信息类型"""
        import json
        import re

        prompt = f"""分析用户任务，返回需要搜索的信息类型。

用户消息: {user_message}

返回 JSON 数组：
[
    {{"info_type": "xialiao_api_key", "description": "虾聊API Key"}},
    {{"info_type": "password", "description": "登录密码"}},
    ...
]

如果任务不需要特定信息，返回空数组 []"""

        try:
            response = await self.llm_manager.chat(prompt)
            json_match = re.search(r"\[[\s\S]*\]", response)
            if json_match:
                data = json.loads(json_match.group())
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"Analyze info failed: {e}")

        return []

    async def _get_all_messages(self, user_id: str, max_count: int = 100) -> list[dict]:
        """获取用户所有对话消息 - 使用搜索方法直接获取相关消息"""

        # 使用搜索方法获取所有相关消息
        all_results = []

        # 搜索多种关键词
        search_queries = [
            "xialiao_",
            "虾聊",
            "API Key",
            "api_key",
            "password",
            "密码",
            "token",
            "认证",
        ]

        for query in search_queries:
            results = await self.conversation_manager.search_all_conversations(
                owner_id=user_id, query=query, limit=30
            )
            for r in results:
                if r["id"] not in [x["id"] for x in all_results]:
                    all_results.append(r)

        # 按时间排序
        all_results.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

        return all_results[:max_count]

    async def _llm_find_relevant_messages(
        self, messages: list[dict], missing_info: list[dict]
    ) -> list[dict]:
        """用 LLM 判断哪些消息包含需要的信息（全文检索，不依赖关键词）"""
        if not messages:
            return []

        import json
        import re

        # 取最近的消息（更容易找到相关信息）
        recent_messages = messages[:30]

        # 构建消息摘要
        msg_summary = []
        for i, msg in enumerate(recent_messages):
            content = msg.get("content", "")[:500]  # 截取前500字符
            role = msg.get("role", "unknown")
            msg_summary.append(f"[{i}] [{role}] {content}")

        messages_text = "\n".join(msg_summary)

        prompt = f"""从以下对话消息中，找出包含用户需要的敏感信息的消息。

需要的信息类型:
{json.dumps(missing_info, ensure_ascii=False, indent=2)}

对话消息:
{messages_text}

请分析每条消息，判断是否包含需要的信息。

返回 JSON 格式:
{{
    "relevant_indices": [消息索引列表，如 [0, 3, 5]],
    "reasoning": "判断理由"
}}

注意：
1. 即使消息中只有部分信息（如只有"xialiao_"前缀），也要标记为相关
2. 用户之前提供的任何包含 API Key、密码、token 的消息都要找出来
3. 重点关注用户(role=user)提供的原始消息"""

        try:
            response = await self.llm_manager.chat(prompt)
            json_match = re.search(r"\{{[\s\S]*\}}", response)
            if json_match:
                data = json.loads(json_match.group())
                indices = data.get("relevant_indices", [])

                # 返回相关消息
                relevant = []
                for idx in indices:
                    if 0 <= idx < len(messages):
                        relevant.append(messages[idx])
                return relevant
        except Exception as e:
            logger.warning(f"LLM find relevant messages failed: {e}")

        return []

    async def _extract_specific_info(
        self, messages: list[dict], missing_info: list[dict]
    ) -> dict | None:
        """从相关消息中提取具体的敏感信息"""
        if not messages:
            return None

        import json
        import re

        # 重点关注用户消息（role=user）
        user_messages = [m for m in messages if m.get("role") == "user"]
        other_messages = [m for m in messages if m.get("role") != "user"]

        # 优先检查用户消息
        priority_messages = user_messages + other_messages

        # 提取所有可能包含敏感信息的内容
        all_contents = []
        for msg in priority_messages[:20]:
            content = msg.get("content", "")
            if content:
                # 查找可能的 API Key 模式
                patterns = [
                    r"xialiao_[a-zA-Z0-9]+",  # xialiao_ 开头的 key
                    r"sk-[a-zA-Z0-9-]+",  # sk- 开头的 key
                    r"api[_-]?key[:\s]+[^\s]+",  # api_key: xxx
                    r"API[_-]?Key[:\s]+[^\s]+",  # API Key: xxx
                    r"token[:\s]+[^\s]+",  # token: xxx
                    r"密码[:\s]+[^\s]+",  # 密码: xxx
                ]

                for pattern in patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        all_contents.append(f"[用户消息] {content[:1000]}")
                        break

        if not all_contents:
            # 如果没有匹配到模式，用原始消息内容
            all_contents = [
                f"[{msg.get('role', 'unknown')}] {msg.get('content', '')[:500]}"
                for msg in priority_messages[:10]
            ]

        contents_text = "\n---\n".join(all_contents)

        prompt = f"""从以下对话消息中，仔细找出用户提供的敏感信息。

需要的信息类型:
{json.dumps(missing_info, ensure_ascii=False, indent=2)}

对话消息:
{contents_text}

请仔细分析每条消息，找出用户明确提供的敏感信息。

返回 JSON 格式:
{{
    "extracted": true/false,
    "info_type": "api_key/password/token/其他",
    "value": "提取到的具体值",
    "reasoning": "从哪条消息、如何提取的"
}}

特别注意：
1. 虾聊的 API Key 格式是 xialiao_xxxxx（如 xialiao_019c7c59f5f77884ac51ef6c092c9500）
2. sk- 开头的通常是测试用的，不是正式的
3. 如果有多条消息都有相关信息，都要找出来
4. 返回具体值，不是整个消息"""

        try:
            response = await self.llm_manager.chat(prompt)
            json_match = re.search(r"\{{[\s\S]*\}}", response)
            if json_match:
                data = json.loads(json_match.group())
                logger.info(f"Extraction result: {data}")
                if data.get("extracted") and data.get("value"):
                    return data
        except Exception as e:
            logger.warning(f"Extract specific info failed: {e}")

        return None

        import json
        import re

        # 提取消息内容
        contents = "\n---\n".join(
            [
                f"[{msg.get('role', 'unknown')}] {msg.get('content', '')[:800]}"
                for msg in messages[:10]
            ]
        )

        prompt = f"""从以下对话消息中，提取用户需要的具体敏感信息。

需要的信息类型:
{json.dumps(missing_info, ensure_ascii=False, indent=2)}

对话消息:
{contents}

请找出并提取具体的敏感信息（如完整的 API Key、密码等）。

返回 JSON 格式:
{{
    "extracted": true/false,
    "info_type": "api_key/password/token/...",
    "value": "提取到的具体值（如完整的 xialiao_xxx）",
    "reasoning": "提取理由"
}}

注意：
1. 只要找到任何相关的敏感信息就返回
2. 如果有多个同类信息，全部提取
3. 返回具体的值，不要返回整个消息"""

        try:
            response = await self.llm_manager.chat(prompt)
            json_match = re.search(r"\{{[\s\S]*\}}", response)
            if json_match:
                data = json.loads(json_match.group())
                if data.get("extracted") and data.get("value"):
                    return data
        except Exception as e:
            logger.warning(f"Extract specific info failed: {e}")

        return None

    def _format_found_info(self, info: dict) -> str:
        """格式化找到的具体信息"""
        info_type = info.get("info_type", "未知")
        value = info.get("value", "")

        return f"""## 找到的信息

从历史对话中找到您需要的信息：

**类型**: {info_type}
**值**: `{value}`

（如有需要，我可以帮您使用这个信息完成任务）"""

    def _format_partial_results(self, messages: list[dict], missing_info: list[dict]) -> str:
        """格式化部分结果（找到相关消息但没有具体信息）"""
        info_descriptions = [info.get("description", "") for info in missing_info]

        return f"""## 找到相关对话

我找到了一些相关的历史对话，但无法确定具体的敏感信息值。

需要的信息: {", ".join(info_descriptions)}

找到的对话片段:
{chr(10).join([f"- {msg.get('content', '')[:200]}..." for msg in messages[:3]])}

请问：
1. 您能告诉我是哪次对话提供的吗？
2. 或者您可以直接再提供一次这个信息？
3. 我可以继续搜索更早的对话历史"""

    async def _check_need_retrieval(self, user_message: str) -> bool:
        """判断是否需要信息检索（触发条件）"""
        import json
        import re

        prompt = f"""判断用户消息是否需要从历史对话中检索信息。

用户消息: {user_message}

需要检索的情况（满足任一即可）：
1. 用户要求完成一个任务，但缺少关键信息（如API Key、密码、配置等）
2. 用户询问"之前告诉你的xxx是什么"、"你记得xxx吗"
3. 用户说"查找"、"找找看之前"
4. 用户要求使用某个服务但没有提供凭证

不需要检索的情况：
1. 简单的问候、闲聊
2. 用户只是询问一般性问题
3. 任务信息看起来已经完整
4. 用户只是聊天不需要特定信息

返回 JSON：
{{
    "need_retrieval": true/false,
    "reason": "判断理由（简洁）"
}}"""

        try:
            response = await self.llm_manager.chat(prompt)
            json_match = re.search(r"\{{[\s\S]*\}}", response)
            if json_match:
                data = json.loads(json_match.group())
                need = data.get("need_retrieval", False)
                logger.info(f"Need retrieval check: {need}, reason: {data.get('reason', '')}")
                return need
        except Exception as e:
            logger.warning(f"Check need retrieval failed: {e}")

        return False

    async def _analyze_missing_info(self, user_message: str) -> list[dict]:
        """分析缺少什么信息，并生成详细的搜索提示"""
        import json
        import re

        prompt = f"""分析用户任务，判断缺少什么关键信息，并生成详细的搜索提示。

用户消息: {user_message}

需要识别的信息类型：
- api_key: API密钥（如 xialiao_xxx, sk-xxx, token 等）
- password: 密码
- token: 认证令牌
- config: 配置信息
- account: 账号信息
- other: 其他

重要：搜索提示应该包含可能出现的关键词变体！
例如：
- api_key 的搜索提示应该包含：xialiao_, sk-, api key, API Key, token, 密钥, 认证
- 尽可能列出所有可能的关键词

返回 JSON 数组：
[
    {{
        "info_type": "api_key",
        "description": "需要的API Key用于调用虾聊API",
        "search_hint": "xialiao_ sk- api key API Key token 密钥 认证 key= xxx_xxx"
    }},
    ...
]

如果没有缺少信息，返回空数组 []"""

        try:
            response = await self.llm_manager.chat(prompt)
            json_match = re.search(r"\[[\s\S]*\]", response)
            if json_match:
                data = json.loads(json_match.group())
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"Analyze missing info failed: {e}")

        return []

    async def _full_text_search(self, user_id: str, missing_info: list[dict]) -> list[dict]:
        """全文检索：直接搜索完整消息内容"""
        results = []

        for info in missing_info:
            hint = info.get("search_hint", "")
            # 直接用搜索提示词搜索完整消息
            if hint:
                search_results = await self.conversation_manager.search_all_conversations(
                    owner_id=user_id, query=hint, limit=10
                )
                results.extend(search_results)

        # 去重
        seen = set()
        unique_results = []
        for r in results:
            if r["id"] not in seen:
                seen.add(r["id"])
                unique_results.append(r)

        return unique_results

    async def _search_user_messages(self, user_id: str, missing_info: list[dict]) -> list[dict]:
        """搜索用户原始提供的消息"""
        # 这个需要直接查询数据库，优先用户消息
        # 已经在 conversation_manager 中实现了按 role 排序
        results = []

        for info in missing_info:
            hint = info.get("search_hint", "")
            if hint:
                search_results = await self.conversation_manager.search_all_conversations(
                    owner_id=user_id, query=hint, limit=15
                )
                # 只取用户消息
                user_msgs = [r for r in search_results if r.get("role") == "user"]
                results.extend(user_msgs)

        # 去重
        seen = set()
        unique_results = []
        for r in results:
            if r["id"] not in seen:
                seen.add(r["id"])
                unique_results.append(r)

        return unique_results

    async def _llm_assisted_search(
        self, user_id: str, missing_info: list[dict], round_num: int
    ) -> list[dict]:
        """LLM 辅助的智能搜索"""
        # 生成更多搜索词
        prompt = f"""为以下信息类型生成更多搜索关键词。

缺少的信息: {json.dumps(missing_info, ensure_ascii=False)}
当前轮次: {round_num}

请生成多种不同的搜索词/短语，越多越好，越全面越好。"""

        try:
            response = await self.llm_manager.chat(prompt)
            # 提取搜索词
            import re

            keywords = re.findall(r"[\w_]+", response.lower())
            keywords = [k for k in keywords if len(k) > 3][:20]

            results = []
            for kw in keywords:
                search_results = await self.conversation_manager.search_all_conversations(
                    owner_id=user_id, query=kw, limit=5
                )
                results.extend(search_results)

            # 去重
            seen = set()
            unique_results = []
            for r in results:
                if r["id"] not in seen:
                    seen.add(r["id"])
                    unique_results.append(r)

            return unique_results

        except Exception as e:
            logger.warning(f"LLM assisted search failed: {e}")
            return []

    async def _validate_search_results(self, results: list[dict], missing_info: list[dict]) -> bool:
        """验证搜索结果是否有效"""
        if not results:
            return False

        import json
        import re

        # 提取结果内容
        result_contents = "\n".join([r.get("content", "")[:500] for r in results[:3]])

        prompt = f"""判断以下搜索结果是否包含需要的信息。

需要的信息: {json.dumps(missing_info, ensure_ascii=False)}

搜索结果:
{result_contents}

返回 JSON：
{{
    "is_valid": true/false,
    "reason": "判断理由",
    "found_info": "如果找到，描述找到的信息"
}}"""

        try:
            response = await self.llm_manager.chat(prompt)
            json_match = re.search(r"\{{[\s\S]*\}}", response)
            if json_match:
                data = json.loads(json_match.group())
                return data.get("is_valid", False)
        except Exception as e:
            logger.warning(f"Validate search results failed: {e}")

        return False

    def _format_retrieval_results(self, results: list[dict]) -> str:
        """格式化检索结果"""
        from datetime import datetime

        formatted = ["## 从历史对话中找到的信息\n"]

        for r in results[:5]:
            ts = datetime.fromtimestamp(r["timestamp"]).strftime("%Y-%m-%d %H:%M")
            content = r.get("content", "")[:1000]
            formatted.append(f"- [{ts}] {content}...")

        return "\n".join(formatted)

    def _format_continue_search_prompt(self, missing_info: list[dict], max_rounds: int) -> str:
        """格式化询问是否继续搜索"""
        info_descriptions = [info.get("description", "") for info in missing_info]

        return f"""## 需要更多信息

我需要以下信息来完成你的任务：
{", ".join(info_descriptions)}

我已经搜索了 {max_rounds} 轮但没有找到相关信息。

请问：
1. 你能提供这些信息吗？
2. 或者需要我继续搜索吗？
3. 或者你可以告诉我具体是在哪次对话中提供的，我可以更精确地查找。"""

    async def _chat_with_llm(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        skills: list[dict[str, Any]] | None = None,
        conversation_id: str | None = None,
        user_session: Optional["UserSession"] = None,
    ) -> ChatResult:
        """
        使用 LLM 生成回复，支持工具和技能调用

        设计初衷：
        ==========
        这是核心的 Agent Loop，最多 20 次迭代，应该能处理所有工具调用。
        返回 ChatResult 对象包含完整状态信息，而不是仅返回文本。

        关键改进：
        1. 返回 ChatResult 而不是 str，避免 chat() 方法用 _parse_tool_calls() 误判
        2. 记录 executed_tools，避免后台任务重复执行
        3. 检测工具参数错误，设置 needs_tool_retry
        4. 检测 LLM 匆忙结束，设置 needs_continuation

        Args:
            messages: 消息列表
            tools: 工具 schema 列表
            skills: 技能 schema 列表
            conversation_id: 可选的会话 ID，用于记录后台任务阶段
            user_session: 用户会话对象（包含 wallet_address, workspace, sandbox 等）

        Returns:
            ChatResult: 包含完整状态的 LLM 调用结果
        """
        recorder = self.llm_manager.invocation_recorder
        starting_attempt_ids = {
            item["provider_attempt_id"]
            for item in recorder.recent_calls(limit=recorder.max_calls)
        }
        active_context = get_llm_context()
        active_trace_id = active_context.trace_id if active_context else None

        def _finalize_llm_result(result: ChatResult) -> ChatResult:
            calls = recorder.recent_calls(
                limit=recorder.max_calls,
                trace_id=active_trace_id,
            )
            calls = [
                item
                for item in reversed(calls)
                if item.get("provider_attempt_id") not in starting_attempt_ids
            ]
            attempt_ids = {item.get("provider_attempt_id") for item in calls}
            events = [
                event
                for event in recorder.recent_events(limit=recorder.max_calls * 3)
                if (
                    (event.get("lineage") or {}).get("provider_attempt_id") in attempt_ids
                    and event.get("event_type") != "llm.artifact.resolved"
                )
            ]
            result.llm_calls = calls
            result.llm_events = events
            result.llm_usage = {
                "physical_calls": len(calls),
                "completed_calls": sum(item.get("status") == "completed" for item in calls),
                "failed_calls": sum(item.get("status") == "failed" for item in calls),
                "input_tokens": sum(
                    int((item.get("usage") or {}).get("input_tokens") or 0)
                    for item in calls
                ),
                "cached_input_tokens": sum(
                    int((item.get("usage") or {}).get("cached_input_tokens") or 0)
                    for item in calls
                ),
                "output_tokens": sum(
                    int((item.get("usage") or {}).get("output_tokens") or 0)
                    for item in calls
                ),
                "total_tokens": sum(
                    int((item.get("usage") or {}).get("total_tokens") or 0)
                    for item in calls
                ),
            }
            return result

        # 合并 tools 和 skills
        all_tools = []
        if tools:
            all_tools.extend(tools)
        if skills:
            all_tools.extend(skills)

        logger.info(
            f"DEBUG _chat_with_llm: tools count={len(all_tools)}, skills count={len(skills or [])}"
        )

        # === 无工具情况：直接生成回复 ===
        if not all_tools:
            logger.info("DEBUG no tools, calling _call_llm_simple")
            content = await self._call_llm_simple(messages)
            return _finalize_llm_result(ChatResult(
                content=content,
                executed_tools=[],
                tool_results=[],
                iterations_used=0,
                is_complete=True,
                needs_background=False,
                needs_tool_retry=False,
            ))

        logger.info("DEBUG has tools, entering agent loop")

        # === Agent Loop 初始化 ===
        is_anthropic_format = self.llm_manager.provider == "minimax"
        logger.info(f"DEBUG using anthropic format: {is_anthropic_format}")

        max_iterations = 20
        iteration = 0
        current_messages = list(messages)

        # === 状态追踪（关键改进：记录执行状态）===
        executed_tools: list[str] = []
        all_tool_results: list[dict[str, Any]] = []

        # Strict Mode 重试计数
        self._strict_mode_retries = 0

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"DEBUG agent loop iteration {iteration}")

            # Step 1: 调用 LLM（带工具）
            logger.info(f"🔍 [AGENT_LOOP] 调用 LLM, iteration={iteration}")
            llm_response = await self._call_llm_with_tools(current_messages, all_tools)
            logger.info(
                f"🔍 [AGENT_LOOP] LLM 返回了, content_len={len(llm_response.get('content', ''))}, tool_calls={len(llm_response.get('tool_calls', []))}"
            )

            # Step 2: 检查是否有工具调用
            tool_calls = llm_response.get("tool_calls", [])
            logger.info(f"DEBUG tool_calls count: {len(tool_calls)}")

            if not tool_calls:
                # === 没有工具调用，LLM 已生成最终回复 ===
                content = llm_response.get("content", "")

                # === Strict Mode：强制工具调用 ===
                # 如果是第一次迭代且启用了 strict_mode，要求 LLM 必须调用工具
                if (
                    self.config.strict_mode
                    and iteration == 1
                    and all_tools
                    and self._strict_mode_retries < self.config.strict_mode_max_retries
                ):
                    # 重试计数加1，然后注入警告并继续循环
                    self._strict_mode_retries += 1
                    warning = (
                        "\n\n[STRICT MODE WARNING] 你必须使用工具来完成任务。\n"
                        "根据技能指引，当前任务需要调用相应的工具来执行实际操作（创建/查询/修改/删除数据等），"
                        "而不是仅回复文本。\n"
                        "请立即调用相关工具来完成用户的请求，不要仅仅返回文本描述。\n"
                    )
                    logger.info(
                        f"[STRICT_MODE] Injecting warning, retry {self._strict_mode_retries}/"
                        f"{self.config.strict_mode_max_retries}"
                    )
                    current_messages.append({"role": "user", "content": warning})
                    continue  # 继续循环，让 LLM 重试

                # === 检测 LLM 是否匆忙结束（关键改进）===
                # 设计初衷：处理 LLM 返回"正在处理中"但实际上后续没有继续的情况
                needs_continuation, continuation_reason = self._detect_hasty_completion(content)

                if needs_continuation:
                    logger.info(f"[CHAT_RESULT] Detected hasty completion: {continuation_reason}")
                    return _finalize_llm_result(ChatResult(
                        content=content,
                        executed_tools=executed_tools,
                        tool_results=all_tool_results,
                        iterations_used=iteration,
                        is_complete=False,
                        needs_background=True,
                        needs_tool_retry=False,
                        needs_continuation=True,
                        continuation_context={
                            "last_tool_results": all_tool_results[-1] if all_tool_results else None,
                            "pending_action": continuation_reason,
                        },
                    ))

                # === 正常完成 ===
                return _finalize_llm_result(ChatResult(
                    content=content,
                    executed_tools=executed_tools,
                    tool_results=all_tool_results,
                    iterations_used=iteration,
                    is_complete=True,
                    needs_background=False,
                    needs_tool_retry=False,
                ))

            # Step 3: 执行工具调用
            tool_results = await self._execute_tool_calls(tool_calls, user_session=user_session)

            # 记录执行的工具（关键改进：避免后台任务重复执行）
            for tc in tool_calls:
                tool_name = tc.get("function", {}).get("name", "")
                if tool_name:
                    executed_tools.append(tool_name)
            all_tool_results.extend(tool_results)

            # 记录到会话
            if conversation_id:
                tool_names = [tc.get("function", {}).get("name", "unknown") for tc in tool_calls]
                await self.conversation_manager.add_message(
                    conversation_id=conversation_id,
                    role=MessageRole.BACKGROUND_TASK,
                    content=f"🔧 执行工具: {', '.join(tool_names)}",
                    tool_calls=tool_calls,
                )

            # Step 4: 检查是否有工具执行失败（关键改进：检测参数错误）
            # 设计初衷：处理工具参数不正确导致失败的情况
            tool_retry_info = self._check_tool_needs_retry(tool_calls, tool_results)

            if tool_retry_info:
                logger.info(f"[CHAT_RESULT] Tool needs retry: {tool_retry_info.get('tool_name')}")
                return _finalize_llm_result(ChatResult(
                    content="",
                    executed_tools=executed_tools,
                    tool_results=all_tool_results,
                    iterations_used=iteration,
                    is_complete=False,
                    needs_background=True,
                    needs_tool_retry=True,
                    needs_continuation=False,
                    retry_info=tool_retry_info,
                ))

            # Step 5: 构建消息继续循环
            if is_anthropic_format:
                self._build_anthropic_tool_messages(
                    llm_response, tool_calls, tool_results, current_messages
                )
            else:
                self._build_openai_tool_messages(
                    llm_response, tool_calls, tool_results, current_messages
                )

        # === 超过最大迭代次数 ===
        logger.warning(f"[CHAT_RESULT] Max iterations reached: {max_iterations}")
        return _finalize_llm_result(ChatResult(
            content="抱歉，这个问题需要处理较长时间，请稍后再试。或者你可以尝试简化问题。",
            executed_tools=executed_tools,
            tool_results=all_tool_results,
            iterations_used=iteration,
            is_complete=False,
            needs_background=True,
            needs_tool_retry=False,
            needs_continuation=True,
            error="max_iterations_reached",
        ))

    def _detect_hasty_completion(self, content: str) -> tuple:
        """
        检测 LLM 是否匆忙结束

        设计初衷：
        LLM 有时会返回"正在处理中"、"请稍后"等中间状态，
        但实际上工具已经执行完了，后续不会有真正的结果。
        只有明确检测到这种中间状态才标记需要后台处理。

        判断原则：
        1. 只检测明确的中间状态短语
        2. 不根据内容长度判断（短回复是正常的）
        3. 不根据关键词推断（避免误判）

        Args:
            content: LLM 返回的内容

        Returns:
            (needs_continuation, reason): 是否需要继续，原因说明
        """
        logger.info(f"[DETECT_HASTY] 检查内容长度: {len(content)} 字符")

        if not content:
            # 响应为空不一定是"匆忙结束"，可能是LLM调用失败
            # 返回 False，让上层处理这个异常情况
            logger.warning("[DETECT_HASTY] 响应为空，返回False让上层处理")
            return False, "响应为空"

        # 只匹配明确的中间状态模式
        hasty_patterns = [
            "正在处理中，请稍候",
            "正在处理，请稍候",
            "系统正在处理，请稍候",
            "正在请求，请稍候",
            "正在执行，请稍候",
            "请稍后查看结果",
            "任务已提交，请稍后",
            "后台处理中，请稍候",
            "已提交到后台",
        ]

        for pattern in hasty_patterns:
            if pattern in content:
                logger.warning(f"[DETECT_HASTY] 检测到中间状态模式: {pattern}")
                return True, f"检测到中间状态：{pattern}"

        # 不再根据内容长度判断
        # 短回复（如"好的"、"明白了"）是正常的，不应该判定为匆忙结束
        logger.info("[DETECT_HASTY] 未检测到中间状态，返回False（正常完成）")
        return False, ""

    def _check_tool_needs_retry(
        self,
        tool_calls: list[dict[str, Any]],
        tool_results: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """
        检查工具执行是否需要重试

        设计初衷：
        工具调用失败可能是因为参数值不正确（如 API Key 错误、缺少必要参数）。
        这个方法分析失败原因，返回重试所需信息。

        注意：只有参数错误才需要重试，网络错误等应该直接报错。

        Args:
            tool_calls: 工具调用列表
            tool_results: 工具执行结果列表

        Returns:
            如果需要重试，返回重试信息；否则返回 None
        """
        for i, result in enumerate(tool_results):
            if result.get("success"):
                continue

            # 获取对应的工具调用
            tool_call = tool_calls[i] if i < len(tool_calls) else None
            if not tool_call:
                continue

            tool_name = tool_call.get("function", {}).get("name", "")
            original_args = tool_call.get("function", {}).get("arguments", {})
            error_msg = ""

            result_data = result.get("result", {})
            if isinstance(result_data, dict):
                error_msg = result_data.get("error", str(result_data))
            else:
                error_msg = str(result_data)

            error_lower = error_msg.lower()

            # === 参数错误检测 ===
            # 设计初衷：只有参数错误才需要从历史记录中提取正确值重试
            param_error_patterns = {
                "api_key": {
                    "keywords": [
                        "api key",
                        "apikey",
                        "api_key",
                        "invalid key",
                        "key is required",
                        "unauthorized",
                        "认证失败",
                        "密钥",
                    ],
                    "info_type": "credential",
                    "description": "需要正确的 API Key 或认证凭证",
                },
                "password": {
                    "keywords": ["password", "密码", "credential"],
                    "info_type": "credential",
                    "description": "需要正确的密码或凭证",
                },
                "token": {
                    "keywords": ["token", "令牌", "bearer", "access token"],
                    "info_type": "credential",
                    "description": "需要正确的 Token",
                },
                "url": {
                    "keywords": ["url", "地址", "endpoint", "invalid url"],
                    "info_type": "url",
                    "description": "需要正确的 URL 地址",
                },
                "param": {
                    "keywords": ["missing", "required", "参数", "invalid", "缺少", "必填"],
                    "info_type": "param",
                    "description": "需要正确的参数值",
                },
            }

            for param_name, pattern_info in param_error_patterns.items():
                for keyword in pattern_info["keywords"]:
                    if keyword in error_lower:
                        return {
                            "tool_name": tool_name,
                            "original_args": original_args,
                            "param_name": param_name,
                            "info_type": pattern_info["info_type"],
                            "description": pattern_info["description"],
                            "error_message": error_msg,
                        }

        return None

    def _build_anthropic_tool_messages(
        self,
        llm_response: dict[str, Any],
        tool_calls: list[dict[str, Any]],
        tool_results: list[dict[str, Any]],
        current_messages: list[dict[str, Any]],
    ) -> None:
        """
        构建 Anthropic API 格式的工具消息

        Anthropic API 格式要求：
        1. assistant 消息的 content 必须是完整的 content blocks 列表
        2. tool_result 放在 user 消息的 content 列表中
        """
        raw_content_blocks = llm_response.get("raw_content_blocks", [])

        # 确保 raw_content_blocks 包含所有 tool_use blocks
        if not raw_content_blocks:
            raw_content_blocks = []
            if llm_response.get("content"):
                raw_content_blocks.append({"type": "text", "text": llm_response.get("content")})
            for tc in tool_calls:
                raw_content_blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "input": tc["function"]["arguments"],
                    }
                )

        # 添加 assistant 消息
        current_messages.append({"role": "assistant", "content": raw_content_blocks})

        # 构建 tool_result content blocks
        tool_result_blocks = []
        for idx, tool_result in enumerate(tool_results):
            tool_call_id = None
            if idx < len(tool_calls):
                tool_call_id = tool_calls[idx].get("id")

            if tool_call_id is None:
                for tc in tool_calls:
                    if tc["function"]["name"] == tool_result.get("tool"):
                        tool_call_id = tc["id"]
                        break

            if tool_call_id is None:
                logger.warning(f"Could not find tool_call_id for tool: {tool_result.get('tool')}")
                continue

            tool_result_blocks.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_call_id,
                    "content": json.dumps(_serialize_for_json(tool_result), ensure_ascii=False),
                }
            )

        # 添加 user 消息（包含 tool_result blocks）
        current_messages.append({"role": "user", "content": tool_result_blocks})

        logger.info(f"DEBUG Added assistant message with {len(raw_content_blocks)} blocks")
        logger.info(f"DEBUG Added user message with {len(tool_result_blocks)} tool_result blocks")

    def _build_openai_tool_messages(
        self,
        llm_response: dict[str, Any],
        tool_calls: list[dict[str, Any]],
        tool_results: list[dict[str, Any]],
        current_messages: list[dict[str, Any]],
    ) -> None:
        """构建 OpenAI API 格式的工具消息"""
        current_messages.append(
            {
                "role": "assistant",
                "content": llm_response.get("content", ""),
                "tool_calls": tool_calls,
            }
        )

        for idx, tool_result in enumerate(tool_results):
            # 匹配工具调用的 ID：优先按索引匹配，其次按工具名匹配
            tool_call_id = None
            if idx < len(tool_calls):
                tool_call_id = tool_calls[idx].get("id")

            if tool_call_id is None:
                tool_name = tool_result.get("tool", "")
                for tc in tool_calls:
                    if tc.get("function", {}).get("name") == tool_name:
                        tool_call_id = tc.get("id")
                        break

            if tool_call_id is None and tool_calls:
                tool_call_id = tool_calls[0].get("id")

            current_messages.append(
                {
                    "role": "tool",
                    "content": json.dumps(_serialize_for_json(tool_result), ensure_ascii=False),
                    "tool_call_id": tool_call_id,
                }
            )

    async def _check_needs_tools(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        skills: list[dict[str, Any]],
    ) -> bool:
        """检查是否需要工具调用"""
        all_tools = []
        if tools:
            all_tools.extend(tools)
        if skills:
            all_tools.extend(skills)

        if not all_tools:
            return False

        # 调用 LLM 初步判断
        adapter = self.llm_manager._adapter
        if adapter is None:
            return False

        try:
            # 只调用一次 LLM 看是否需要工具
            if hasattr(adapter, "chat_with_tools"):
                response = await adapter.chat_with_tools(messages, all_tools)
                tool_calls = response.get("tool_calls", [])
                return len(tool_calls) > 0
        except Exception as e:
            logger.warning(f"Failed to check if tools needed: {e}")

        return False

    async def _call_llm_simple(self, messages: list[dict[str, str]]) -> str:
        """简单调用 LLM"""
        if self.llm_manager.provider == "minimax" and self.llm_manager._adapter:
            return await self.llm_manager._adapter.chat_with_messages(messages)
        else:
            # 降级处理
            last_user_msg = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    last_user_msg = msg.get("content", "")
                    break
            return f"我收到了你的消息：{last_user_msg[:50]}..."

    async def _call_llm_with_tools(
        self, messages: list[dict[str, str]], tools: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """调用 LLM 并传递工具"""
        print(f"🔍 [_call_llm_with_tools] START, tools={len(tools)}")
        logger.info(f"DEBUG _call_llm_with_tools called, tools count: {len(tools)}")

        # Log sample tools
        if tools:
            sample = json.dumps(tools[0], ensure_ascii=False)[:300]
            logger.info(f"First tool sample: {sample}")

        adapter = self.llm_manager._adapter
        logger.info(f"DEBUG adapter is: {adapter}")

        if adapter is not None:
            if hasattr(adapter, "chat_with_tools"):
                try:
                    # 不使用 asyncio.wait_fort，因为 adapter 内部已经有超时控制（300秒）
                    result = await adapter.chat_with_tools(messages, tools)
                    logger.info(
                        f"DEBUG _call_llm_with_tools returned, content_len={len(result.get('content', ''))}, tool_calls={len(result.get('tool_calls', []))}"
                    )
                    return result
                except Exception as e:
                    logger.error(f"chat_with_tools failed: {e}", exc_info=True)
                    # The provider may already have accepted the paid request.
                    # Propagate the failure so no simple-chat fallback can
                    # replay the same creation call.
                    raise
            else:
                try:
                    content = await adapter.chat_with_messages(messages)
                    return {"content": content, "tool_calls": []}
                except Exception as e:
                    logger.error(f"chat_with_messages failed: {e}", exc_info=True)
                    raise
        else:
            # 没有 LLM 适配器，返回降级响应
            logger.warning("DEBUG adapter is None!")
            return {"content": "LLM 不可用（请配置 MINIMAX_API_KEY）", "tool_calls": []}

    async def _execute_tool_calls(
        self, tool_calls: list[dict[str, Any]], user_session: Optional["UserSession"] = None
    ) -> list[dict[str, Any]]:
        """执行工具调用

        Args:
            tool_calls: 工具调用列表
            user_session: 用户会话对象（包含 wallet_address, workspace, sandbox 等）

        Returns:
            工具执行结果列表
        """
        results = []

        # 获取用户信息用于日志
        wallet_info = user_session.wallet_address[:10] + "..." if user_session else "anonymous"
        logger.info(f"Executing {len(tool_calls)} tool calls for user: {wallet_info}")

        for tool_call in tool_calls:
            try:
                tool_name = tool_call.get("function", {}).get("name", "")
                tool_args = tool_call.get("function", {}).get("arguments", {})

                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

                # 解析参数
                if isinstance(tool_args, str):
                    import json

                    try:
                        tool_args = json.loads(tool_args)
                    except:
                        tool_args = {}

                # 检查工具是否需要 session
                tool = self.tool_registry.get_tool(tool_name)
                if tool is None:
                    # Fallback: 检查 SkillsManager 是否有带 handler 的 skill
                    skill = self.skills_manager.get_skill(tool_name)
                    if skill and skill.handler:
                        # 在 SkillsManager 中找到有 handler 的 skill，执行它
                        try:
                            result = await self.skills_manager.execute_skill(
                                tool_name, tool_args, session=user_session
                            )
                            logger.info(f"Executed skill via SkillsManager: {tool_name}")
                            results.append(
                                {
                                    "tool": tool_name,
                                    "result": result,
                                    "success": True,
                                }
                            )
                            continue
                        except Exception as e:
                            logger.error(f"Skill execution failed: {e}")
                            results.append(
                                {
                                    "tool": tool_name,
                                    "result": {"error": f"技能执行失败: {str(e)}"},
                                    "success": False,
                                }
                            )
                            continue

                    # 工具/技能不存在
                    logger.error(f"Tool not found: {tool_name}")
                    results.append(
                        {
                            "tool": tool_name,
                            "result": {"error": f"工具/技能 '{tool_name}' 不存在或无可用处理器。"},
                            "success": False,
                        }
                    )
                    continue

                if tool.requires_session:
                    if user_session is None:
                        # 工具需要 session 但没有可用 session
                        error_msg = (
                            f"⚠️ **需要用户授权**\n\n"
                            f"工具 `{tool_name}` 需要用户会话才能执行。\n\n"
                            f"请先绑定身份：\n"
                            f"1. 点击右上角的「绑定身份」按钮\n"
                            f"2. 选择连接钱包或使用临时标识符\n"
                            f"3. 重新尝试此操作"
                        )
                        logger.warning(f"Tool {tool_name} requires session but no session provided")
                        results.append(
                            {
                                "tool": tool_name,
                                "result": {"error": error_msg, "requires_auth": True},
                                "success": False,
                            }
                        )
                        continue

                    # ===== 权限检查 =====
                    wallet_address = user_session.wallet_address
                    user_role = "human"

                    # 获取用户角色
                    try:
                        user_perm = await self.permission_manager.get_user(wallet_address)
                        if user_perm:
                            user_role = user_perm.role.value
                    except Exception as e:
                        logger.warning(f"Failed to get user role: {e}")

                    # 检查工具权限
                    check_result = await self.permission_manager.check_tool_access(
                        wallet_address, tool_name
                    )

                    if not check_result.get("allowed"):
                        error_msg = (
                            f"⚠️ **权限不足**\n\n"
                            f"工具 `{tool_name}` 需要以下权限：\n"
                            f"{', '.join(check_result.get('required_permissions', []))}\n\n"
                            f"当前角色: {user_role}\n"
                            f"原因: {check_result.get('reason', 'unknown')}"
                        )
                        logger.warning(
                            f"Tool {tool_name} permission denied for {wallet_address}: {check_result.get('reason')}"
                        )

                        # 记录审计日志
                        await self.audit_logger.log(
                            action=AuditAction.TOOL_EXECUTE,
                            wallet_address=wallet_address,
                            role=user_role,
                            operation=tool_name,
                            result="permission_denied",
                            level=AuditLevel.WARNING,
                            details={"reason": check_result.get("reason")},
                        )

                        results.append(
                            {
                                "tool": tool_name,
                                "result": {"error": error_msg, "permission_denied": True},
                                "success": False,
                            }
                        )
                        continue

                    # 记录审计日志
                    await self.audit_logger.log(
                        action=AuditAction.TOOL_EXECUTE,
                        wallet_address=wallet_address,
                        role=user_role,
                        operation=tool_name,
                        result="success",
                        details=tool_args,
                    )

                    # 执行需要 session 的工具
                    logger.info(
                        f"Executing tool {tool_name} with user session (wallet: {user_session.wallet_address[:10]}...)"
                    )
                    result = await self.tool_registry.execute(
                        tool_name, session=user_session, **tool_args
                    )
                else:
                    # 执行不需要 session 的工具
                    logger.info(f"Executing tool {tool_name} without session")
                    result = await self.tool_registry.execute(tool_name, **tool_args)

                logger.info(f"Tool {tool_name} result: {result}")
                results.append(
                    {
                        "tool": tool_name,
                        "result": result,
                        "success": True,
                    }
                )

            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                import traceback

                traceback.print_exc()
                # 安全获取 tool_name：优先使用局部变量，否则尝试从 tool_call 获取
                tool_name_in_error = locals().get("tool_name")
                if tool_name_in_error is None:
                    tool_name_in_error = (
                        tool_call.get("function", {}).get("name", "unknown")
                        if "tool_call" in locals()
                        else "unknown"
                    )
                results.append(
                    {
                        "tool": tool_name_in_error,
                        "result": {"error": f"工具执行失败: {str(e)}"},
                        "success": False,
                    }
                )

        return results

    async def _evaluate_result(self, result: Any) -> dict[str, Any]:
        """评估执行结果"""
        response_text = "执行完成"
        if isinstance(result, dict):
            if (
                "results" in result
                and isinstance(result["results"], list)
                and len(result["results"]) > 0
            ):
                first_result = result["results"][0]
                if isinstance(first_result, dict) and "result" in first_result:
                    inner_result = first_result["result"]
                    if isinstance(inner_result, dict) and "response" in inner_result:
                        response_text = inner_result["response"]
                    else:
                        response_text = str(inner_result)
            elif "result" in result:
                response_text = str(result["result"])

        return {
            "success": result.get("status") == "success",
            "response": response_text,
            "details": result,
        }

    async def execute_tool(
        self, tool_name: str, wallet_address: str | None = None, **kwargs
    ) -> Any:
        """
        执行指定工具（改造后）

        改造要点：
        1. 新增 wallet_address 参数
        2. 如果提供 wallet_address，传入 UserSession 上下文给工具
        3. 向后兼容（不提供 wallet_address 时使用原有行为）

        Args:
            tool_name: 工具名称
            wallet_address: 用户钱包地址（用于获取 UserSession）
            **kwargs: 工具参数

        Returns:
            工具执行结果
        """
        # 如果提供 wallet_address，获取 UserSession 并传入
        if wallet_address:
            user_session = await self.session_manager.get_or_create_session(wallet_address)
            # P2 Fix: 传递 session 参数给 tool_registry.execute
            return await self.tool_registry.execute(tool_name, session=user_session, **kwargs)

        # 向后兼容：不提供 wallet_address 时使用原有行为
        return await self.tool_registry.execute(tool_name, **kwargs)

    async def sync_user_data(self, wallet_address: str) -> str:
        """
        同步用户数据到IPFS（新增方法）

        Args:
            wallet_address: 用户钱包地址

        Returns:
            IPFS CID（内容标识符）

        Raises:
            RuntimeError: 如果钱包地址未提供
        """
        if not wallet_address:
            raise RuntimeError("wallet_address is required for sync_user_data")

        user_session = await self.session_manager.get_or_create_session(wallet_address)
        return await user_session.sync_to_ipfs()

    async def migrate_user_data(self, wallet_address: str) -> bool:
        """
        从IPFS迁移用户数据到当前节点（新增方法）

        Args:
            wallet_address: 用户钱包地址

        Returns:
            迁移成功返回 True，否则返回 False

        Raises:
            RuntimeError: 如果钱包地址未提供
        """
        if not wallet_address:
            raise RuntimeError("wallet_address is required for migrate_user_data")

        user_session = await self.session_manager.get_or_create_session(wallet_address)
        return await user_session.migrate_to_this_node()

    async def get_session_info(self, wallet_address: str) -> dict | None:
        """
        获取用户会话信息（新增方法）

        Args:
            wallet_address: 用户钱包地址

        Returns:
            会话信息字典，如果会话不存在返回 None
        """
        user_session = await self.session_manager.get_session(wallet_address)
        if user_session is None:
            return None

        return {
            "session_id": user_session.session_id,
            "wallet_address": user_session.wallet_address,
            "node_id": user_session.node_id,
            "is_primary_node": user_session.is_primary_node,
            "created_at": user_session.created_at,
            "last_active": user_session.last_active,
            "is_idle": user_session.is_idle(),
        }

    async def search_knowledge(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        搜索知识库

        Args:
            query: 查询内容
            top_k: 返回结果数量

        Returns:
            知识条目列表
        """
        results = await self.vector_kb.search(query, top_k=top_k)
        return [
            {
                "content": r.item.content,
                "category": r.item.category,
                "source": r.item.source,
                "score": r.score,
            }
            for r in results
        ]

    async def get_knowledge_stats(self) -> dict[str, Any]:
        """获取知识库统计"""
        return await self.vector_kb.get_stats()

    # ========== 调试日志方法 ==========
    def add_debug_log(self, wallet_address: str, log_type: str, message: str, data: dict = None):
        """添加调试日志

        Args:
            wallet_address: 钱包地址
            log_type: 日志类型 (info, tool_call, tool_result, error, llm_call)
            message: 日志消息
            data: 额外数据
        """
        if wallet_address not in self._debug_logs:
            self._debug_logs[wallet_address] = []

        import time

        self._debug_logs[wallet_address].append(
            {
                "timestamp": time.time(),
                "type": log_type,
                "message": message,
                "data": data or {},
            }
        )

        # 限制每个钱包地址最多保留 100 条日志
        if len(self._debug_logs[wallet_address]) > 100:
            self._debug_logs[wallet_address] = self._debug_logs[wallet_address][-100:]

    def get_debug_logs(self, wallet_address: str, after_timestamp: float = 0) -> list[dict]:
        """获取调试日志

        Args:
            wallet_address: 钱包地址
            after_timestamp: 只返回该时间戳之后的日志

        Returns:
            日志列表
        """
        logs = self._debug_logs.get(wallet_address, [])
        return [log for log in logs if log["timestamp"] > after_timestamp]

    def clear_debug_logs(self, wallet_address: str):
        """清除调试日志"""
        if wallet_address in self._debug_logs:
            self._debug_logs[wallet_address] = []

    def get_available_tools(self) -> list[dict[str, str]]:
        """获取可用工具列表"""
        return self.tool_registry.list_tools()

    async def register_skill(self, skill_path: str):
        """注册新技能"""
        await self.skills_manager.load_skill(skill_path)

    async def get_conversation_history(
        self,
        wallet_address: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """获取会话历史（仅限 owner 访问）"""
        conversation = await self.conversation_manager.get_or_create_conversation(
            owner_id=wallet_address,
            owner_type=ParticipantType.HUMAN,
        )
        messages = await self.conversation_manager.get_conversation_history(
            conversation_id=conversation.id,
            accessor_id=wallet_address,
            limit=limit,
        )
        return [m.to_dict() for m in messages]

    def get_evolution_stats(self) -> dict[str, Any]:
        """获取进化统计"""
        if self.evolution_engine:
            return self.evolution_engine.get_evolution_stats()
        return {}

    # ========== 任务计划相关方法 ==========

    def _format_plan_for_user(self, plan: TaskPlan) -> str:
        """
        格式化任务计划供用户确认

        Args:
            plan: 任务计划

        Returns:
            格式化的计划摘要
        """
        lines = [
            "📋 **检测到复杂任务，已生成执行计划**\n",
            f"**任务复杂度**: {plan.complexity.value}",
            f"**预计总时间**: {plan.get_total_estimated_time()} 秒\n",
            "**执行步骤**:",
        ]

        for i, step in enumerate(plan.steps, 1):
            status_emoji = {
                "pending": "⏳",
                "running": "🔄",
                "completed": "✅",
                "failed": "❌",
                "skipped": "⏭️",
            }.get(step.status.value, "⏳")
            lines.append(f"  {i}. {status_emoji} **{step.name}** ({step.estimated_time}s)")
            lines.append(f"     {step.description}")

        lines.extend(
            [
                "\n---",
                "**请回复以下命令之一**:",
                "- `确认执行` - 开始执行计划",
                "- `取消` - 取消此任务",
                "- `修改` - 提出修改建议",
            ]
        )

        return "\n".join(lines)

    def _format_plan_result(self, plan: TaskPlan) -> str:
        """
        格式化任务执行结果

        Args:
            plan: 执行完成的任务计划

        Returns:
            格式化的执行结果
        """
        logger.info(
            f"[FORMAT_RESULT] 格式化任务结果: status={plan.status.value}, steps={len(plan.steps)}"
        )

        if plan.status == TaskStatus.COMPLETED:
            results = []
            for i, step in enumerate(plan.steps):
                if step.status == StepStatus.COMPLETED and step.result:
                    if isinstance(step.result, dict):
                        output = step.result.get("output", "")
                        if output:
                            results.append(f"**步骤 {i+1}: {step.name}**\n{output[:1000]}")
                        else:
                            results.append(f"**步骤 {i+1}: {step.name}**\n(执行成功)")
                    else:
                        results.append(f"**步骤 {i+1}: {step.name}**\n{str(step.result)[:1000]}")
                elif step.status == StepStatus.FAILED:
                    results.append(
                        f"❌ **步骤 {i+1}: {step.name}** 失败\n{step.error or '未知错误'}"
                    )

            if results:
                return "✅ **任务执行完成**\n\n" + "\n\n".join(results)
            else:
                return "✅ 任务执行完成（无详细结果）"
        else:
            failed = [s for s in plan.steps if s.status == StepStatus.FAILED]
            completed = [s for s in plan.steps if s.status == StepStatus.COMPLETED]
            return f"⚠️ 任务执行完成：{len(completed)}个步骤成功，{len(failed)}个步骤失败"

    async def confirm_and_execute_plan(self, task_id: str) -> str:
        """
        确认并执行任务计划

        Args:
            task_id: 任务 ID

        Returns:
            执行结果
        """
        logger.info(f"[Agent] confirm_and_execute_plan called with task_id: {task_id}")

        if not self.task_executor:
            return "任务执行器未初始化"

        # 确认计划
        if not self.task_executor.confirm_plan(task_id):
            return "无法确认计划（计划不存在或状态不正确）"

        # 获取计划
        plan = self.task_executor.get_task(task_id)
        if not plan:
            return "计划不存在"

        logger.info(f"[Agent] Plan steps: {len(plan.steps)}")
        for i, step in enumerate(plan.steps):
            logger.info(f"[Agent] Step {i+1}: {step.name}, action: {step.action}")

        # 执行计划
        try:
            executed_plan = await self.task_executor.execute_plan(plan)

            # 🔧 修复：返回详细的执行结果，而不是简单的"任务执行完成"
            if executed_plan.status == TaskStatus.COMPLETED:
                # 汇总所有步骤的结果
                results = []
                for i, step in enumerate(executed_plan.steps):
                    if step.result:
                        # 尝试提取 output 字段
                        if isinstance(step.result, dict):
                            output = step.result.get("output", "")
                            if output:
                                results.append(
                                    f"**步骤 {i+1}: {step.name}**\n{output[:1000]}"
                                )  # 限制长度
                        else:
                            results.append(
                                f"**步骤 {i+1}: {step.name}**\n{str(step.result)[:1000]}"
                            )

                if results:
                    return "✅ **任务执行完成**\n\n" + "\n\n".join(results)
                else:
                    return "✅ 任务执行完成（无详细结果）"
            else:
                failed_steps = [s for s in executed_plan.steps if s.status.value == "failed"]
                return f"⚠️ 任务部分完成，{len(failed_steps)} 个步骤失败"
        except Exception as e:
            logger.error(f"[CHAT] Plan execution failed: {e}")
            return f"❌ 执行失败: {str(e)}"

    def get_task_plan(self, task_id: str) -> dict[str, Any] | None:
        """
        获取任务计划

        Args:
            task_id: 任务 ID

        Returns:
            任务计划字典
        """
        if not self.task_executor:
            return None

        plan = self.task_executor.get_task(task_id)
        return plan.to_dict() if plan else None

    # ========== 信息提取相关辅助方法 ==========

    async def _llm_judge_response_retry(
        self, response: str, attempt: int, max_retries: int
    ) -> dict:
        """LLM 返回后判断是否需要重试"""

        prompt = f"""判断当前响应是否需要重试。

当前尝试: {attempt + 1}/{max_retries}

LLM 响应:
{response[:3000]}

请返回JSON:
{{
    "need_retry": true/false,
    "reason": "判断理由",
    "need_info": true/false,
    "info_description": "需要什么信息",
    "info_type": "credential/param/url/other",
    "format_hint": "格式提示（可选）"
}}

注意：完全根据实际响应判断，不要预设任何条件。
"""
        try:
            logger.info(
                f"[INFO_EXTRACT] _llm_judge_response_retry called, attempt={attempt + 1}/{max_retries}"
            )
            resp = await self.llm_manager.chat(prompt)
            data = self._parse_json(resp)
            logger.info(f"[INFO_EXTRACT] _llm_judge_response_retry result: {data}")
            return data or {"need_retry": False}
        except Exception as e:
            logger.warning(f"LLM judge response retry failed: {e}")
            return {"need_retry": False}

    async def _filter_tools_by_permission(
        self, all_tools: list[dict], wallet_address: str | None
    ) -> list[str]:
        """根据用户权限过滤可用工具

        Args:
            all_tools: 所有工具列表
            wallet_address: 用户钱包地址

        Returns:
            用户有权使用的工具名称列表
        """
        if not wallet_address:
            return [t["name"] for t in all_tools]

        try:
            user = await self.permission_manager.get_user(wallet_address)
            if not user:
                logger.warning(f"User not found: {wallet_address}, allowing all tools")
                return [t["name"] for t in all_tools]

            from .permission.models import get_tool_required_permissions

            allowed_tools = []
            for tool in all_tools:
                tool_name = tool["name"]
                required_perms = get_tool_required_permissions(tool_name)

                has_all_perms = all(user.has_permission(perm) for perm in required_perms)
                if has_all_perms:
                    allowed_tools.append(tool_name)
                else:
                    logger.debug(f"Tool {tool_name} filtered out for {wallet_address[:10]}...")

            logger.info(
                f"Filtered tools: {len(allowed_tools)}/{len(all_tools)} for {wallet_address[:10]}..."
            )
            logger.info(
                f"User {wallet_address[:10]} permissions: {user.permissions if user else 'None'}"
            )
            return allowed_tools

        except Exception as e:
            logger.warning(f"Failed to filter tools by permission: {e}, allowing all")
            return [t["name"] for t in all_tools]

    async def _llm_judge_tool_retry(
        self,
        tool_results: list[dict],
        attempt: int,
        max_retries: int,
        user_question: str = "",
        tool_calls: list[dict] = None,
    ) -> dict:
        """工具调用后判断是否需要重试"""
        import json

        tool_calls = tool_calls or []
        tool_name = tool_calls[0].get("name", "unknown") if tool_calls else "unknown"
        tool_arguments = (
            json.dumps(tool_calls[0].get("arguments", {}), ensure_ascii=False)
            if tool_calls
            else "{}"
        )

        prompt = f"""你是一个智能助手，需要判断工具执行结果是否满足用户需求。

## 重要前提
- 工具执行成功 ≠ 用户需求满足
- 只有当工具执行失败（网络错误、超时、权限问题、工具不存在等）时才需要重试
- 如果工具执行成功但返回数据有空值/null，这可能是业务逻辑问题，不一定需要重试
- 区块链操作（如质押、投票）返回 tx_hash 或 status:success 就表示操作成功，不需要完整数据才算成功

## 当前上下文

**用户原始问题**: {user_question}

**LLM 工具调用输入**:
- 工具名称: {tool_name}
- 调用参数: {tool_arguments}

**当前尝试**: {attempt + 1}/{max_retries}

**工具执行结果**:
{json.dumps(tool_results, ensure_ascii=False, indent=2)}

请从以下维度进行分析判断：

## 1. 工具执行状态分析（最重要）
- 首先判断：工具是否执行成功？（查看 success 字段和 error 字段）
- 如果 success=false 或有 error 字段 → 需要重试
- 如果 success=true 或没有 error 字段 → 工具执行成功，不需要重试
- 特别注意：区块链操作返回 status:success 就表示成功，不需要更多数据

## 2. 用户需求匹配度
- 工具执行结果是否直接回答了用户的问题？
- 工具调用参数是否正确反映了用户需求？

## 3. 重试合理性（只有在工具执行失败时才考虑）
- 当前尝试次数：{attempt + 1}/{max_retries}
- 如果工具执行已经成功（success=true），不应该因为"数据不完整"而重试
- 只有以下情况才需要重试：
  1. 工具执行失败（network error、timeout、unauthorized等）
  2. 工具返回明确错误
  3. 工具选择错误（如应该用A工具却用了B工具）

请返回JSON:
{{
    "need_retry": true/false,
    "reason": "详细判断理由",
    "need_info": false,
    "info_description": "",
    "info_type": "other",
    "search_history": false,
    "search_reason": "",
    "change_tool": false,
    "new_tool_suggestion": "",
    "param_adjustment": ""
}}
"""
        try:
            logger.info(
                f"[INFO_EXTRACT] _llm_judge_tool_retry called, attempt={attempt + 1}/{max_retries}, tool_count={len(tool_results)}"
            )
            logger.info(
                f"[INFO_EXTRACT] tool_results: {json.dumps(tool_results, ensure_ascii=False)[:500]}..."
            )
            resp = await self.llm_manager.chat(prompt)
            logger.info(f"[INFO_EXTRACT] _llm_judge_tool_retry raw response: {resp[:500]}...")
            data = self._parse_json(resp)
            logger.info(f"[INFO_EXTRACT] _llm_judge_tool_retry parsed result: {data}")
            return data or {"need_retry": False}
        except Exception as e:
            logger.warning(f"LLM judge tool retry failed: {e}")
            return {"need_retry": False}

    def _check_task_completion(self, result_text: str, tool_results: list[dict] = None) -> dict:
        """最终检查任务是否真正完成

        检查点：
        1. 响应是否包含中间状态词汇（正在、稍后、等待、检索中）
        2. 工具执行是否成功
        3. 响应是否完整回答了用户问题

        注意：只有当响应明确表示需要等待时才算不完成，
              如果只是响应中提到"稍后"作为建议，不算不完成
        """
        if not result_text:
            return {"is_complete": False, "reason": "结果为空"}

        # 宽松检查：只有在响应明确表示"正在处理中"或"请等待"时才认为是不完整
        # 不再检查"稍后"等词汇，因为LLM经常会在完整回复中提到"稍后"
        unclear_patterns = [
            "正在处理中，请稍候",
            "正在处理，请稍候",
            "系统正在处理，请稍候",
            "正在请求，请稍候",
        ]

        for pattern in unclear_patterns:
            if pattern in result_text:
                return {
                    "is_complete": False,
                    "reason": f"响应明确表示正在处理: {pattern}",
                    "is_intermediate": True,
                }

        if tool_results:
            failed_tools = [t for t in tool_results if not t.get("success", False)]
            if failed_tools:
                return {
                    "is_complete": False,
                    "reason": f"有 {len(failed_tools)} 个工具执行失败",
                    "failed_tools": failed_tools,
                }

        return {"is_complete": True, "reason": "检查通过"}

    def _parse_json(self, response: str) -> dict | None:
        import json
        import re

        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            return json.loads(response.strip())
        except Exception:
            match = re.search(r"\{[\s\S]*\}", response)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
        return None

    def _parse_tool_calls(self, response: str) -> list[dict]:
        """解析工具调用"""
        import re

        tool_calls = []
        try:
            # Debug: log response snippet
            print(f"[PARSE_TOOL_CALLS] Response: {response[:500]}")
            logger.info(f"[PARSE_TOOL_CALLS] Response: {response[:500]}")

            # First try to parse JSON format
            json_match = re.search(
                r'\[[\s\S]*"tool_calls"[\s\S]*\]|\{[^\}]*"tool_calls"[^\}]*\}', response
            )
            if json_match:
                data = json.loads(json_match.group())
                if isinstance(data, dict) and "tool_calls" in data:
                    tool_calls = data["tool_calls"]
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "tool_calls" in item:
                            tool_calls.extend(item["tool_calls"])

            # Fallback: parse various text formats
            if not tool_calls:
                # Try simple pattern: [invoke name="tool"]...[/invoke] or [invoke name="tool"]
                # Handle: [invoke name="list_proposals"] or [invoke name="tool"]...</invoke>
                patterns = [
                    r'\[invoke\s+name="([^"]+)"\s*/\]',  # [invoke name="tool"]
                    r'\[invoke\s+name="([^"]+)"\](.*?)\[/invoke\]',  # [invoke name="tool"]...[/invoke]
                    r'\[invoke\s+name="([^"]+)"\](.*?)</invoke>',  # [invoke name="tool"]...</invoke>
                ]

                for pattern in patterns:
                    matches = re.findall(pattern, response, re.IGNORECASE | re.DOTALL)
                    for match in matches:
                        if isinstance(match, tuple):
                            tool_name = match[0]
                            params_str = match[1] if len(match) > 1 else ""
                        else:
                            tool_name = match
                            params_str = ""

                        args = {}
                        if params_str:
                            # Extract parameters: <parameter name="key">value</parameter>
                            for param_match in re.finditer(
                                r'<parameter\s+name="([^"]+)"[^>]*>([^<]*)</parameter>', params_str
                            ):
                                args[param_match.group(1)] = param_match.group(2)

                        tool_calls.append(
                            {"id": f"call_{len(tool_calls)}", "name": tool_name, "arguments": args}
                        )

                if tool_calls:
                    logger.info(
                        f"[PARSE] Parsed {len(tool_calls)} tool calls from text: {[tc.get('name') for tc in tool_calls]}"
                    )

                # Format: [invoke name="tool"]...</invoke>
                if not tool_calls:
                    xml_block_pattern = r'\[invoke\s+name="([^"]+)"\](.*?)</invoke>'
                    for match in re.finditer(
                        xml_block_pattern, response, re.IGNORECASE | re.DOTALL
                    ):
                        tool_name = match.group(1)
                        params_str = match.group(2)
                        args = {}
                        for param_match in re.finditer(
                            r'<parameter\s+name="([^"]+)"[^>]*>([^<]*)</parameter>', params_str
                        ):
                            args[param_match.group(1)] = param_match.group(2)
                        tool_calls.append(
                            {"id": f"call_{len(tool_calls)}", "name": tool_name, "arguments": args}
                        )

                # Format 2: [invoke name="tool"/]
                if not tool_calls:
                    for match in re.finditer(
                        r'\[invoke\s+name="([^"]+)"\s*/\]', response, re.IGNORECASE
                    ):
                        tool_calls.append(
                            {
                                "id": f"call_{len(tool_calls)}",
                                "name": match.group(1),
                                "arguments": {},
                            }
                        )

                # Format 3: tool_name() - simple function call
                if not tool_calls:
                    for match in re.finditer(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*\)", response):
                        tool_name = match.group(1)
                        # Only include if it looks like a tool name (not common words)
                        if tool_name not in (
                            "list",
                            "get",
                            "set",
                            "print",
                            "return",
                            "if",
                            "else",
                            "for",
                            "while",
                        ):
                            tool_calls.append(
                                {
                                    "id": f"call_{len(tool_calls)}",
                                    "name": tool_name,
                                    "arguments": {},
                                }
                            )

                # Format 4: <FunctionCallBegin>{tool => "name", args => {...}}<FunctionCallEnd>
                if not tool_calls:
                    for match in re.finditer(
                        r'<FunctionCallBegin>\s*\{[^}]*tool\s*=>\s*"([^"]+)"[^}]*args\s*=>\s*(\{[^}]*\})\s*\}\s*<FunctionCallEnd>',
                        response,
                        re.IGNORECASE | re.DOTALL,
                    ):
                        tool_name = match.group(1)
                        args_str = match.group(2)
                        try:
                            args = json.loads(args_str.replace("=>", ":").replace("'", '"'))
                        except:
                            args = {}
                        tool_calls.append(
                            {"id": f"call_{len(tool_calls)}", "name": tool_name, "arguments": args}
                        )

                # Format 5: [TOOL_CALL]{tool => "name", args => {...}}[/TOOL_CALL]
                if not tool_calls:
                    for match in re.finditer(
                        r'\[TOOL_CALL\]\s*\{[^}]*tool\s*=>\s*"([^"]+)"[^}]*args\s*=>\s*(\{[^}]*\})\s*\}\s*\[/TOOL_CALL\]',
                        response,
                        re.IGNORECASE | re.DOTALL,
                    ):
                        tool_name = match.group(1)
                        args_str = match.group(2)
                        try:
                            args = json.loads(args_str.replace("=>", ":").replace("'", '"'))
                        except:
                            args = {}
                        tool_calls.append(
                            {"id": f"call_{len(tool_calls)}", "name": tool_name, "arguments": args}
                        )

                # Format 6: <tool_call_begin>tool_name <param name="key">value</param>\n</tool_call_end>
                if not tool_calls:
                    for match in re.finditer(
                        r"<tool_call_begin>\s*(\w+)\s*(.*?)\s*</tool_call_end>",
                        response,
                        re.IGNORECASE | re.DOTALL,
                    ):
                        tool_name = match.group(1)
                        params_str = match.group(2)
                        args = {}
                        # Extract parameters: <param name="key">value</param>
                        for param_match in re.finditer(
                            r'<param\s+name="([^"]+)"[^>]*>([^<]*)</param>', params_str
                        ):
                            args[param_match.group(1)] = param_match.group(2)
                        tool_calls.append(
                            {"id": f"call_{len(tool_calls)}", "name": tool_name, "arguments": args}
                        )

                # Format 7: <invoke name="tool_name">...</invoke> (Anthropic format)
                if not tool_calls:
                    for match in re.finditer(
                        r'<invoke\s+name="([^"]+)"[^>]*>(.*?)</invoke>',
                        response,
                        re.IGNORECASE | re.DOTALL,
                    ):
                        tool_name = match.group(1)
                        params_str = match.group(2)
                        args = {}
                        # Extract parameters: <param name="key">value</param>
                        for param_match in re.finditer(
                            r'<param\s+name="([^"]+)"[^>]*>([^<]*)</param>', params_str
                        ):
                            args[param_match.group(1)] = param_match.group(2)
                        tool_calls.append(
                            {"id": f"call_{len(tool_calls)}", "name": tool_name, "arguments": args}
                        )

                # Format 8: <FunctionCall> tool: xxx args: xxx </FunctionCall>
                if not tool_calls:
                    for match in re.finditer(
                        r"<FunctionCall>\s*-\s*tool:\s*(\w+)\s*-\s*args:\s*([^\n]+)\s*</FunctionCall>",
                        response,
                        re.IGNORECASE | re.DOTALL,
                    ):
                        tool_name = match.group(1)
                        args_str = match.group(2)
                        args = {}
                        # Parse args: --key "value" or --key value
                        for arg_match in re.finditer(r'--(\w+)\s+"([^"]+)"', args_str):
                            args[arg_match.group(1)] = arg_match.group(2)
                        for arg_match in re.finditer(r"--(\w+)\s+(\S+)", args_str):
                            if arg_match.group(1) not in args:
                                args[arg_match.group(1)] = arg_match.group(2)
                        tool_calls.append(
                            {"id": f"call_{len(tool_calls)}", "name": tool_name, "arguments": args}
                        )

                # Format 9: [TOOL_CALL]{tool => "name", args => { --key value }}[/TOOL_CALL]
                # Handle multi-line format by extracting all tool call blocks first
                if not tool_calls:
                    # Find all [TOOL_CALL] blocks
                    tool_blocks = re.findall(
                        r"\[TOOL_CALL\](.*?)\[/TOOL_CALL\]", response, re.IGNORECASE | re.DOTALL
                    )

                    for block in tool_blocks:
                        # Extract tool name
                        tool_match = re.search(r'tool\s*=>\s*"([^"]+)"', block, re.IGNORECASE)
                        if not tool_match:
                            continue
                        tool_name = tool_match.group(1)

                        # Extract all arguments (handle multi-line)
                        args = {}
                        for arg_match in re.finditer(r'--(\w+)\s+"([^"]+)"', block):
                            args[arg_match.group(1)] = arg_match.group(2)
                        for arg_match in re.finditer(r"--(\w+)\s+'([^']+)'", block):
                            args[arg_match.group(1)] = arg_match.group(2)
                        for arg_match in re.finditer(r"--(\w+)\s+(\d+)", block):
                            try:
                                args[arg_match.group(1)] = int(arg_match.group(2))
                            except:
                                args[arg_match.group(1)] = arg_match.group(2)

                        tool_calls.append(
                            {"id": f"call_{len(tool_calls)}", "name": tool_name, "arguments": args}
                        )

                if tool_calls:
                    logger.info(
                        f"Parsed {len(tool_calls)} tool calls from text: {[tc.get('name') for tc in tool_calls]}"
                    )

        except Exception as e:
            logger.warning(f"Parse tool calls failed: {e}")
        return tool_calls

    async def _execute_tool(self, tool_name: str, tool_args: dict, user_session) -> dict:
        """执行工具"""
        try:
            return await self.tool_registry.execute(tool_name, session=user_session, **tool_args)
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name}, error: {e}")
            return {"success": False, "error": str(e)}

    def _inject_extracted_info(self, messages: list, info_name: str, info_value: str) -> list:
        """将提取到的信息注入到消息上下文"""
        injection = f"\n\n## 已获取的信息\n{info_name}: {info_value}\n"
        new_messages = []
        for msg in messages:
            new_messages.append(msg)
            if isinstance(msg, dict) and msg.get("role") == "user":
                new_messages.append({"role": "system", "content": injection})
            elif hasattr(msg, "role") and msg.role == "user":
                new_messages.append({"role": "system", "content": injection})
        return new_messages

    def _add_response_to_messages(self, messages: list, response: str) -> list:
        """将 LLM 响应添加到消息列表"""
        messages = list(messages)
        messages.append({"role": "assistant", "content": response})
        return messages

    def _add_tool_results_to_messages(
        self, messages: list, llm_response: str, tool_results: list[dict]
    ) -> list:
        """将工具结果添加到消息列表"""
        import json

        messages = list(messages)
        messages.append({"role": "assistant", "content": llm_response})
        for tr in tool_results:
            messages.append(
                {
                    "role": "tool",
                    "content": json.dumps(tr.get("result", {}), ensure_ascii=False),
                    "tool_call_id": tr.get("tool", ""),
                }
            )
        return messages

    def _format_tool_results(self, tool_results: list[dict]) -> str:
        """格式化工具结果"""
        import json

        lines = []
        for tr in tool_results:
            lines.append(
                f"### {tr.get('tool', 'unknown')}\n```\n{json.dumps(tr.get('result', {}), ensure_ascii=False, indent=2)}\n```"
            )
        return "\n\n".join(lines)

    async def _format_tool_results_with_llm(
        self, tool_results: list[dict], user_message: str, user_session
    ) -> str:
        """使用 LLM 将工具结果格式化为自然语言"""
        import json

        tool_info = []
        for tr in tool_results:
            tool_name = tr.get("tool", "unknown")
            result = tr.get("result", {})
            tool_info.append(
                f"工具: {tool_name}\n结果: {json.dumps(result, ensure_ascii=False, indent=2)}"
            )

        tool_results_text = "\n\n".join(tool_info)

        prompt = f"""用户的原始问题是：{user_message}

工具执行结果如下，请用自然、友好的语言向用户解释这些结果：

{tool_results_text}

请直接给出回复，不需要提及"工具执行"等技术细节。"""

        try:
            response = await self.llm_manager.chat(prompt)
            return response
        except Exception as e:
            logger.warning(f"LLM formatting failed, using fallback: {e}")
            return self._format_tool_results(tool_results)

    def _fix_tool_args(self, original_args: dict, info_name: str, extracted_value: str) -> dict:
        """修复工具参数"""
        fixed_args = original_args.copy()
        param_mappings = {
            "api_key": ["api_key", "apikey", "key", "apiKey", "api-key"],
            "token": ["token", "access_token", "auth_token"],
            "url": ["url", "link", "href"],
        }
        info_name_lower = info_name.lower()
        for _standard_name, possible_names in param_mappings.items():
            if any(n in info_name_lower for n in possible_names):
                for param_name in possible_names:
                    if param_name in fixed_args:
                        fixed_args[param_name] = extracted_value
                        logger.info(f"Fixed tool arg: {param_name}")
                        break
        return fixed_args
