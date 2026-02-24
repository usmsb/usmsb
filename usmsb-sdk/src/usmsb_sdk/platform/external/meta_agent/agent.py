"""
Meta Agent 主类
基于 USMSB Core 的超级 Agent
具备感知、决策、执行、交互、转化、评估、反馈、学习、风险管理能力
"""

import asyncio
import dataclasses
import json
import logging
import os
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4

from .meta_agent_config import MetaAgentConfig
from .core.perception import PerceptionService
from .core.decision import DecisionService
from .core.execution import ExecutionService
from .core.interaction import InteractionService
from .core.learning import LearningService
from .llm.manager import LLMManager
from .tools.registry import ToolRegistry
from .skills.manager import SkillsManager
from .context.manager import ContextManager, UserInfo
from .memory.conversation_manager import ConversationManager
from .memory.conversation import ParticipantType, MessageRole
from .memory.memory_manager import MemoryManager, MemoryConfig
from .memory.experience_db import ExperienceDB
from .memory.smart_recall import IntelligentRecall
from .memory.error_learning import ErrorDrivenLearning, AgentWithSelfHealing
from .memory.guardian_daemon import GuardianDaemon, GuardianConfig
from .knowledge.base import KnowledgeBase
from .knowledge.vector_store import VectorKnowledgeBase
from .wallet.manager import WalletManager
from .goals.engine import GoalEngine
from .evolution.engine import EvolutionEngine
from .memory.memory_manager import MemoryManager, MemoryConfig

# 新增：多用户隔离支持
from .session.session_manager import SessionManager
from .session.user_session import SessionConfig

# 新增：敏感信息处理、意图识别、配置管理
from .sensitive.registry import (
    SensitiveInfoRegistry,
    get_sensitive_info_registry,
)
from .intent.recognizer import IntentRecognizer, IntentType, Intent
from .config.chat_config import ChatConfig

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

    def __init__(self, config: Optional[MetaAgentConfig] = None):
        self.config = config or MetaAgentConfig()
        self.agent_id = f"meta_{uuid4().hex[:8]}"

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
        self.tool_registry = ToolRegistry()
        self.skills_manager = SkillsManager(self.config.database.path)

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

        # 进化引擎
        self.evolution_engine: Optional[EvolutionEngine] = None

        # ========== 智能召回系统 ==========
        self.smart_recall: Optional[IntelligentRecall] = None

        # ========== 错误驱动学习系统 ==========
        self.error_learning: Optional[ErrorDrivenLearning] = None

        # ========== 守护进程 ==========
        self.guardian_daemon: Optional[GuardianDaemon] = None

        # ========== 精准匹配服务 ==========
        self.meta_agent_service: Optional[Any] = None  # MetaAgentService

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

        # 状态
        self._running = False
        self._main_loop_task: Optional[asyncio.Task] = None

    async def start(self):
        """启动 Meta Agent"""
        logger.info(f"Starting Meta Agent {self.agent_id}...")

        # ========== 新增：启动会话管理器 ==========
        try:
            await self.session_manager.start()
            logger.info("SessionManager started")
        except Exception as e:
            logger.error(f"Failed to start SessionManager: {e}")

        # 初始化组件
        await self._init_components()

        # 注册默认工具
        await self._register_default_tools()

        # 加载 skills
        await self.skills_manager.load_skills()

        # 启动目标引擎
        await self.goal_engine.start()

        # 启动进化引擎
        self.evolution_engine = EvolutionEngine(
            self.llm_manager,
            self.knowledge_base,
            self.conversation_manager,
        )
        await self.evolution_engine.start()

        # ========== 初始化智能召回系统 ==========
        if self.config.smart_recall_enabled:
            self.smart_recall = IntelligentRecall(
                llm_manager=self.llm_manager,
                memory_db=self.memory_manager,
                vector_store=self.vector_kb,
            )
            logger.info("Smart Recall initialized")

        # ========== 初始化错误驱动学习系统 ==========
        experience_db = ExperienceDB(
            db_path=self.config.database.path.replace(".db", "_experience.db")
        )
        self.error_learning = ErrorDrivenLearning(
            llm_manager=self.llm_manager,
            experience_db=experience_db,
        )
        logger.info("Error-driven Learning initialized")

        # ========== 启动守护进程 ==========
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

        # ========== 初始化精准匹配服务 ==========
        try:
            from .services.meta_agent_service import MetaAgentService
            from .tools.precise_matching import set_meta_agent_service

            # 尝试获取基因胶囊服务
            gene_capsule_service = None
            try:
                from usmsb_sdk.api.rest.gene_capsule_service import GeneCapsuleService
                gene_capsule_service = GeneCapsuleService()
            except ImportError:
                pass

            # 尝试获取预匹配洽谈服务
            pre_match_service = None
            try:
                from usmsb_sdk.services.pre_match_negotiation import PreMatchNegotiationService
                pre_match_service = PreMatchNegotiationService()
            except ImportError:
                pass

            self.meta_agent_service = MetaAgentService(
                meta_agent=self,
                gene_capsule_service=gene_capsule_service,
                pre_match_negotiation_service=pre_match_service,
            )
            await self.meta_agent_service.init()

            # 设置全局服务实例供工具使用
            set_meta_agent_service(self.meta_agent_service)

            logger.info("MetaAgentService initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize MetaAgentService: {e}")

        # 启动主循环
        self._running = True
        self._main_loop_task = asyncio.create_task(self._main_loop())

        logger.info(f"Meta Agent {self.agent_id} started successfully")

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

        # ========== 停止守护进程 ==========
        if self.guardian_daemon:
            await self.guardian_daemon.stop()
            logger.info("Guardian Daemon stopped")

        await self.goal_engine.stop()
        await self.context_manager.save()

        # ========== 新增：停止会话管理器 ==========
        try:
            await self.session_manager.stop()
            logger.info("SessionManager stopped")
        except Exception as e:
            logger.error(f"Error stopping SessionManager: {e}")

        logger.info(f"Meta Agent {self.agent_id} stopped")

    async def _init_components(self):
        """初始化组件"""
        # 初始化 LLM（可选，可能没有配置 API key）
        try:
            await self.llm_manager.init()
        except Exception as e:
            logger.warning(f"LLM initialization failed (may need API key): {e}")

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

        # 加载项目知识（可选）
        try:
            await self._load_project_knowledge()
        except Exception as e:
            logger.warning(f"Failed to load project knowledge: {e}")

        # 预热向量知识库（可选）
        try:
            await self._warmup_knowledge_base()
        except Exception as e:
            logger.warning(f"Failed to warmup knowledge base: {e}")

    async def _register_default_tools(self):
        """注册默认工具"""
        from .tools import (
            platform,
            monitor,
            blockchain,
            ipfs,
            database,
            ui,
            governance,
            execution,
            system,
            web,
            system_agents,
            precise_matching,
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

        logger.info(f"Registered {len(self.tool_registry.list_tools())} default tools")

    async def _load_project_knowledge(self):
        """加载项目知识到向量知识库 - 扫描整个项目"""
        # 确定项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

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
                    with open(file_path, "r", encoding="utf-8") as f:
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
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
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
                    with open(config_path, "r", encoding="utf-8") as f:
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

    async def _main_loop(self):
        """主循环 - 永不停歇"""
        logger.info("Meta Agent main loop started")

        while self._running:
            try:
                # 1. 感知环境
                await self._perceive_environment()

                # 2. 检查目标状态
                await self._check_goals()

                # 3. 处理待处理任务
                await self._process_pending_tasks()

                # 4. 学习进化
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
        """感知环境"""
        pass

    async def _check_goals(self):
        """检查目标状态"""
        await self.goal_engine.check_goals()

    async def _process_pending_tasks(self):
        """处理待处理任务"""
        pass

    async def _learn_and_evolve(self):
        """学习进化"""
        await self.learning.learn_from_experience()

    async def chat(
        self,
        message: str,
        wallet_address: Optional[str] = None,
        participant_type: ParticipantType = ParticipantType.HUMAN,
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

        Returns:
            Agent 回复
        """
        # ========== 改造：使用 SessionManager 获取用户会话 ==========

        # 确定会话所有者
        owner_id = wallet_address or f"anonymous_{uuid4().hex[:8]}"

        # 获取或创建用户会话
        user_session = None
        if wallet_address:
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

        # 添加用户消息
        await self.conversation_manager.add_message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=message,
        )

        # 获取对话历史
        history_messages = await self.conversation_manager.get_messages_for_llm(
            conversation_id=conversation.id,
            accessor_id=owner_id,
            max_tokens=2000,
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

        # ========== 智能信息检索 ==========
        # 当用户问需要之前提供的信息时，从历史对话中检索
        retrieval_context = ""

        logger.debug(f"Starting retrieval check for message: {message[:50]}...")

        try:
            # 使用敏感信息注册表获取关键词（替代硬编码）
            info_keywords = self.sensitive_registry.get_all_keywords()
            need_retrieval = any(kw in message.lower() for kw in info_keywords)

            if need_retrieval:
                task_info = {"task_description": message, "needed_info_type": "用户之前提供的信息"}
                logger.info(f"Need retrieval for: {message[:30]}...")

                # 获取候选消息
                candidates = await self._get_all_candidate_info(owner_id)
                print(f"[RETRIEVAL] Candidates count: {len(candidates)}")

                if candidates:
                    # 让 LLM 从所有候选中找出需要的信息
                    try:
                        found_info = await self._find_info_from_candidates(candidates, task_info)
                        logger.debug(f"Found info: {found_info[:50] if found_info else 'None'}...")
                    except Exception as e:
                        logger.error(f"Error in _find_info_from_candidates: {e}")
                        found_info = None

                    if found_info:
                        retrieval_context = self._format_found_info({"content": found_info})
                        logger.info("Set retrieval_context!")
                    else:
                        # 直接返回候选内容（使用配置中的截断长度和显示数量）
                        candidate_text = "\n\n".join(
                            [
                                f"消息{i + 1} [{c.get('role', '')}]: {c.get('content', '')[:self.chat_config.candidate_content_length]}..."
                                for i, c in enumerate(candidates[:self.chat_config.display_candidates_limit])
                            ]
                        )
                        retrieval_context = f"## 从历史对话中找到以下相关内容：\n\n{candidate_text}"
                        logger.info("Set retrieval_context with candidates")

        except Exception as e:
            logger.warning(f"Retrieval failed: {e}")

        # 如果检索到信息，使用检索结果
        if retrieval_context:
            logger.debug(f"Setting smart_recall_context: {retrieval_context[:100]}...")
            smart_recall_context = retrieval_context
            # 动态更新记忆
            if self.memory_manager:
                try:
                    await self.memory_manager.dynamic_update_from_recall(
                        user_id=owner_id, recalled_content=retrieval_context, source="agent_chat"
                    )
                except Exception as e:
                    logger.warning(f"Failed to dynamic update memories: {e}")

        # ========== 方案四：检测用户强调记忆 ==========
        if self.memory_manager:
            try:
                await self.memory_manager.check_and_store_user_emphasis(
                    user_id=owner_id, message=message
                )
            except Exception as e:
                logger.warning(f"Failed to check user emphasis: {e}")

        # 构建用户信息
        user_info = None
        if wallet_address:
            user_info = UserInfo(
                address=wallet_address,
                role="USER",
                binding_type="wallet" if wallet_address.startswith("0x") else "manual",
            )

        # 获取可用工具
        available_tools = self.tool_registry.list_tools()
        tool_names = [t["name"] for t in available_tools]
        logger.debug(f"chat: tools count={len(tool_names)}")

        # 构建完整的消息列表（包含系统提示词、知识库检索、对话历史、分层记忆、智能召回）
        messages = await self.context_manager.build_messages(
            user_message=message,
            conversation_history=history_messages,
            user_info=user_info,
            available_tools=tool_names,
            memory_context=memory_context,
            smart_recall_context=smart_recall_context,
        )
        logger.debug(f"chat: messages count={len(messages)}")

        # 获取工具和技能 schema
        # MiniMax 使用 Anthropic API 格式
        llm_provider = "anthropic" if self.llm_manager.provider == "minimax" else "openai"
        tools_schema = self.tool_registry.get_tools_schema(provider=llm_provider)
        skills_schema = self.skills_manager.get_skills_schema(provider=llm_provider)
        logger.debug(f"chat: tools_schema={len(tools_schema)}, skills_schema={len(skills_schema)}, provider={llm_provider}")

        # 调用 LLM（支持工具和技能调用）
        try:
            # 使用意图识别器判断用户意图（替代硬编码关键词）
            intent = await self.intent_recognizer.recognize(message)

            # 根据意图判断是否需要工具调用
            is_simple = intent.is_simple() and len(message) < self.chat_config.simple_message_threshold

            # 使用意图识别器判断是否需要工具（替代硬编码关键词）
            needs_tools = intent.is_tool_call() or not is_simple

            if needs_tools:
                # 需要执行工具，启动后台处理
                async def background_task():
                    try:
                        logger.info("Starting background task execution")
                        # 先记录开始执行 - 使用 BACKGROUND_TASK 类型
                        await self.conversation_manager.add_message(
                            conversation_id=conversation.id,
                            role=MessageRole.BACKGROUND_TASK,
                            content=self.chat_config.background_task_start_message,
                        )

                        result_text = await self._chat_with_llm(
                            messages,
                            tools=tools_schema,
                            skills=skills_schema,
                            conversation_id=str(conversation.id),
                            user_session=user_session,
                        )

                        # 记录结果供调试
                        logger.debug(
                            f"Background task result: {result_text[:500] if result_text else 'EMPTY'}"
                        )

                        # 检查结果是否是超时或需要更多时间
                        if "需要更多时间" in result_text or "稍后再试" in result_text:
                            # 执行遇到问题，记录更详细的信息 - 使用 BACKGROUND_ERROR 类型
                            await self.conversation_manager.add_message(
                                conversation_id=conversation.id,
                                role=MessageRole.BACKGROUND_ERROR,
                                content=self.chat_config.background_task_error_template.format(error=result_text),
                            )
                        else:
                            # 正常结果 - 使用 BACKGROUND_COMPLETE 类型
                            await self.conversation_manager.add_message(
                                conversation_id=conversation.id,
                                role=MessageRole.BACKGROUND_COMPLETE,
                                content=self.chat_config.background_task_complete_template.format(result=result_text),
                            )
                        logger.info("Background task completed and saved to history")
                    except Exception as e:
                        logger.error(f"Background task failed: {e}")
                        import traceback

                        error_detail = traceback.format_exc()
                        await self.conversation_manager.add_message(
                            conversation_id=conversation.id,
                            role=MessageRole.BACKGROUND_ERROR,
                            content=self.chat_config.background_task_fail_template.format(error=str(e), detail=error_detail),
                        )

                # 启动后台任务，不等待完成
                asyncio.create_task(background_task())

                # 立即返回任务提交消息
                response_text = self.chat_config.task_submitted_message
            else:
                # 不需要工具调用，直接返回
                response_text = await self._chat_with_llm(
                    messages,
                    tools=tools_schema,
                    skills=skills_schema,
                    user_session=user_session,
                )

            logger.debug(f"chat: response_text={response_text[:100] if response_text else 'EMPTY'}")
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            response_text = self.chat_config.llm_unavailable_message

        # 添加助手回复
        await self.conversation_manager.add_message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=response_text,
        )

        # 6. 从对话学习（异步，不阻塞响应）
        if self.evolution_engine:
            messages = await self.conversation_manager.get_conversation_history(
                conversation_id=conversation.id,
                accessor_id=owner_id,
                limit=10,
            )
            asyncio.create_task(
                self.evolution_engine.learn_from_conversation(
                    conversation_id=conversation.id,
                    messages=[m.to_dict() for m in messages],
                )
            )

        return response_text

    async def _extract_search_keywords(self, user_message: str) -> List[str]:
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
    ) -> Optional[str]:
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

        import json, re

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
                logger.info(f"Not correct, trying next...")

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
        import json, re

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

    async def _get_all_candidate_info(self, user_id: str) -> List[Dict]:
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

    def _extract_all_sensitive_values(self, content: str) -> List[str]:
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
        self, candidates: List[Dict], task_info: Dict
    ) -> Optional[str]:
        """让 LLM 从所有候选消息中找出需要的信息"""
        import json, re

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
                print(f"[FIND_INFO] No JSON found in response")
        except Exception as e:
            print(f"[FIND_INFO] Error: {e}")

        return None

    async def _validate_info_with_llm(self, candidate: Dict, task_info: Dict) -> bool:
        """用 LLM 判断这段历史消息是否包含用户当前需要的信息"""
        import json, re

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

    async def _expand_search(self, user_id: str, task_info: Dict) -> List[Dict]:
        """扩大搜索范围"""
        import json, re

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

    def _format_found_info(self, info: Dict) -> str:
        """格式化找到的信息"""
        content = info.get("content", "")
        # 提取关键信息
        return f"""## 找到可用信息

从历史对话中找到你需要的信息：

**相关内容**: {content[:300]}

（已从历史记录中验证）"""

    def _format_ask_user(self, task_info: Dict) -> str:
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
        self, messages: List[Dict], missing_info: List[Dict]
    ) -> Optional[Dict]:
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
        self, messages: List[Dict], missing_info: List[Dict]
    ) -> Optional[Dict]:
        """用 LLM 从相关消息中提取具体信息"""
        if not messages:
            return None

        import json, re

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
        import json, re

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

    async def _analyze_missing_info_v2(self, user_message: str) -> List[Dict]:
        """分析需要搜索的信息类型"""
        import json, re

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

    async def _get_all_messages(self, user_id: str, max_count: int = 100) -> List[Dict]:
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
        self, messages: List[Dict], missing_info: List[Dict]
    ) -> List[Dict]:
        """用 LLM 判断哪些消息包含需要的信息（全文检索，不依赖关键词）"""
        if not messages:
            return []

        import json, re

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
        self, messages: List[Dict], missing_info: List[Dict]
    ) -> Optional[Dict]:
        """从相关消息中提取具体的敏感信息"""
        if not messages:
            return None

        import json, re

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

        import json, re

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

    def _format_found_info(self, info: Dict) -> str:
        """格式化找到的具体信息"""
        info_type = info.get("info_type", "未知")
        value = info.get("value", "")

        return f"""## 找到的信息

从历史对话中找到您需要的信息：

**类型**: {info_type}
**值**: `{value}`

（如有需要，我可以帮您使用这个信息完成任务）"""

    def _format_partial_results(self, messages: List[Dict], missing_info: List[Dict]) -> str:
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
        import json, re

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

    async def _analyze_missing_info(self, user_message: str) -> List[Dict]:
        """分析缺少什么信息，并生成详细的搜索提示"""
        import json, re

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

    async def _full_text_search(self, user_id: str, missing_info: List[Dict]) -> List[Dict]:
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

    async def _search_user_messages(self, user_id: str, missing_info: List[Dict]) -> List[Dict]:
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
        self, user_id: str, missing_info: List[Dict], round_num: int
    ) -> List[Dict]:
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

    async def _validate_search_results(self, results: List[Dict], missing_info: List[Dict]) -> bool:
        """验证搜索结果是否有效"""
        if not results:
            return False

        import json, re

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

    def _format_retrieval_results(self, results: List[Dict]) -> str:
        """格式化检索结果"""
        from datetime import datetime

        formatted = ["## 从历史对话中找到的信息\n"]

        for r in results[:5]:
            ts = datetime.fromtimestamp(r["timestamp"]).strftime("%Y-%m-%d %H:%M")
            content = r.get("content", "")[:1000]
            formatted.append(f"- [{ts}] {content}...")

        return "\n".join(formatted)

    def _format_continue_search_prompt(self, missing_info: List[Dict], max_rounds: int) -> str:
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
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        skills: Optional[List[Dict[str, Any]]] = None,
        conversation_id: Optional[str] = None,
        user_session: Optional["UserSession"] = None,
    ) -> str:
        """
        使用 LLM 生成回复，支持工具和技能调用

        Args:
            messages: 消息列表
            tools: 工具 schema 列表
            skills: 技能 schema 列表
            conversation_id: 可选的会话 ID，用于记录后台任务阶段
            user_session: 用户会话对象（包含 wallet_address, workspace, sandbox 等）

        Returns:
            Agent 回复
        """
        # 合并 tools 和 skills
        all_tools = []
        if tools:
            all_tools.extend(tools)
        if skills:
            all_tools.extend(skills)

        logger.info(
            f"DEBUG _chat_with_llm: tools count={len(all_tools)}, skills count={len(skills or [])}"
        )

        if not all_tools:
            # 无工具/技能，直接生成回复
            logger.info("DEBUG no tools, calling _call_llm_simple")
            return await self._call_llm_simple(messages)

        logger.info("DEBUG has tools, entering agent loop")

        # 判断是否使用 Anthropic API 格式
        is_anthropic_format = self.llm_manager.provider == "minimax"
        logger.info(f"DEBUG using anthropic format: {is_anthropic_format}")

        # Agent Loop: 循环调用直到不需要工具
        max_iterations = 20  # 增加迭代次数
        iteration = 0

        current_messages = list(messages)

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"DEBUG agent loop iteration {iteration}")

            # 调用 LLM（带工具）
            llm_response = await self._call_llm_with_tools(current_messages, all_tools)

            # 检查是否需要调用工具
            tool_calls = llm_response.get("tool_calls", [])
            logger.info(f"DEBUG tool_calls count: {len(tool_calls)}")

            if not tool_calls:
                content = llm_response.get("content", "")
                # 如果返回内容包含错误信息且这是第一次尝试，降级到无工具模式
                if iteration == 1 and content and "失败" in content:
                    print(f"[DEBUG] Tool call failed, falling back to simple chat: {content[:100]}")
                    return await self._call_llm_simple(current_messages)
                return content

            # 执行工具调用
            tool_results = await self._execute_tool_calls(tool_calls, user_session=user_session)

            # 如果有 conversation_id，记录工具执行阶段到数据库
            if conversation_id:
                tool_names = [tc.get("function", {}).get("name", "unknown") for tc in tool_calls]
                await self.conversation_manager.add_message(
                    conversation_id=conversation_id,
                    role=MessageRole.BACKGROUND_TASK,
                    content=f"🔧 执行工具: {', '.join(tool_names)}",
                    tool_calls=tool_calls,
                )

            # 检查是否有工具执行失败
            failed_tools = [r for r in tool_results if not r.get("success", True)]
            if failed_tools:
                error_msg = "⚠️ 工具执行出错：\n\n"
                for ft in failed_tools:
                    tool_name = ft.get("tool", "unknown")
                    error_detail = ft.get("result", {}).get("error", "未知错误")
                    error_msg += f"**{tool_name}**: {error_detail}\n"
                logger.warning(f"Tool execution errors: {error_msg}")

                # 如果是最后一次迭代或工具连续失败，直接返回错误信息
                if iteration >= max_iterations - 1:
                    return error_msg + "\n\n请尝试其他方式或简化问题。"

            if is_anthropic_format:
                # Anthropic API 格式：
                # 1. assistant 消息的 content 必须是完整的 content blocks 列表
                # 2. tool_result 放在 user 消息的 content 列表中

                raw_content_blocks = llm_response.get("raw_content_blocks", [])

                # 确保 raw_content_blocks 包含所有 tool_use blocks
                # 如果 raw_content_blocks 为空，手动构建
                if not raw_content_blocks:
                    raw_content_blocks = []
                    if llm_response.get("content"):
                        raw_content_blocks.append(
                            {"type": "text", "text": llm_response.get("content")}
                        )
                    for tc in tool_calls:
                        raw_content_blocks.append(
                            {
                                "type": "tool_use",
                                "id": tc["id"],
                                "name": tc["function"]["name"],
                                "input": tc["function"]["arguments"],
                            }
                        )

                # 添加 assistant 消息（包含完整的 content blocks）
                current_messages.append(
                    {
                        "role": "assistant",
                        "content": raw_content_blocks,
                    }
                )

                # 构建 tool_result content blocks - 使用索引顺序匹配
                tool_result_blocks = []
                for idx, tool_result in enumerate(tool_results):
                    # 使用索引匹配，确保一一对应
                    tool_call_id = None
                    if idx < len(tool_calls):
                        tool_call_id = tool_calls[idx].get("id")

                    # 如果索引匹配失败，尝试按名称匹配
                    if tool_call_id is None:
                        for tc in tool_calls:
                            if tc["function"]["name"] == tool_result.get("tool"):
                                tool_call_id = tc["id"]
                                break

                    # 确保 tool_call_id 有效
                    if tool_call_id is None:
                        logger.warning(
                            f"Could not find tool_call_id for tool: {tool_result.get('tool')}"
                        )
                        continue

                    tool_result_blocks.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_call_id,
                            "content": json.dumps(
                                _serialize_for_json(tool_result), ensure_ascii=False
                            ),
                        }
                    )

                # 添加 user 消息（包含 tool_result blocks）
                current_messages.append(
                    {
                        "role": "user",
                        "content": tool_result_blocks,
                    }
                )

                logger.info(f"DEBUG Added assistant message with {len(raw_content_blocks)} blocks")
                logger.info(
                    f"DEBUG Added user message with {len(tool_result_blocks)} tool_result blocks"
                )

            else:
                # OpenAI API 格式（保留原有逻辑）
                current_messages.append(
                    {
                        "role": "assistant",
                        "content": llm_response.get("content", ""),
                        "tool_calls": tool_calls,
                    }
                )

                # 添加工具结果
                for tool_result in tool_results:
                    current_messages.append(
                        {
                            "role": "tool",
                            "content": json.dumps(
                                _serialize_for_json(tool_result), ensure_ascii=False
                            ),
                            "tool_call_id": tool_calls[0].get("id") if tool_calls else None,
                        }
                    )

        # 超过最大迭代次数，返回更友好的消息
        return "抱歉，这个问题需要处理较长时间，请稍后再试。或者你可以尝试简化问题。"

    async def _check_needs_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        skills: List[Dict[str, Any]],
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

    async def _call_llm_simple(self, messages: List[Dict[str, str]]) -> str:
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
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """调用 LLM 并传递工具"""
        logger.info(f"DEBUG _call_llm_with_tools called, tools count: {len(tools)}")

        adapter = self.llm_manager._adapter
        logger.info(f"DEBUG adapter is: {adapter}")

        if adapter is not None:
            if hasattr(adapter, "chat_with_tools"):
                try:
                    return await adapter.chat_with_tools(messages, tools)
                except Exception as e:
                    logger.error(f"chat_with_tools failed: {e}")
                    return {"content": f"LLM 调用失败: {str(e)}", "tool_calls": []}
            else:
                try:
                    content = await adapter.chat_with_messages(messages)
                    return {"content": content, "tool_calls": []}
                except Exception as e:
                    logger.error(f"chat_with_messages failed: {e}")
                    return {"content": f"LLM 调用失败: {str(e)}", "tool_calls": []}
        else:
            # 没有 LLM 适配器，返回降级响应
            return {"content": "LLM 不可用（请配置 MINIMAX_API_KEY）", "tool_calls": []}

    async def _execute_tool_calls(
        self, tool_calls: List[Dict[str, Any]], user_session: Optional["UserSession"] = None
    ) -> List[Dict[str, Any]]:
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
                    # 工具不存在
                    logger.error(f"Tool not found: {tool_name}")
                    results.append(
                        {
                            "tool": tool_name,
                            "result": {
                                "error": f"工具 '{tool_name}' 不存在。请检查工具名称是否正确。"
                            },
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
                results.append(
                    {
                        "tool": tool_name if "tool_name" in dir() else "unknown",
                        "result": {"error": f"工具执行失败: {str(e)}"},
                        "success": False,
                    }
                )

        return results

    async def _evaluate_result(self, result: Any) -> Dict[str, Any]:
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
        self, tool_name: str, wallet_address: Optional[str] = None, **kwargs
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
            # TODO: 改造 ToolRegistry.execute 支持 session 参数
            # 当前保持兼容性，后续需要改造工具执行接口
            return await self.tool_registry.execute(tool_name, **kwargs)

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

    async def get_session_info(self, wallet_address: str) -> Optional[Dict]:
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

    async def search_knowledge(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
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

    async def get_knowledge_stats(self) -> Dict[str, Any]:
        """获取知识库统计"""
        return await self.vector_kb.get_stats()

    def get_available_tools(self) -> List[Dict[str, str]]:
        """获取可用工具列表"""
        return self.tool_registry.list_tools()

    async def register_skill(self, skill_path: str):
        """注册新技能"""
        await self.skills_manager.load_skill(skill_path)

    async def get_conversation_history(
        self,
        wallet_address: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
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

    def get_evolution_stats(self) -> Dict[str, Any]:
        """获取进化统计"""
        if self.evolution_engine:
            return self.evolution_engine.get_evolution_stats()
        return {}
