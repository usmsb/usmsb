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
import re
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

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
from .evolution.engine import EvolutionEngine
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

        # 进化引擎
        self.evolution_engine: EvolutionEngine | None = None

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

        # 状态
        self._running = False
        self._main_loop_task: asyncio.Task | None = None

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

        # 注册 npm 命令执行技能
        await self._register_npm_skill()

        # 注册 git 命令执行技能
        await self._register_git_skill()

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

        # ========== 初始化分步任务执行器 ==========
        # 复杂任务拆分为小步骤，逐步执行
        # 每步独立超时（60秒），支持断点续传
        self.task_executor = TaskExecutor(self)
        # P2: 初始化进度存储
        task_db_path = self.config.database.path.replace(".db", "_tasks.db")
        self.task_executor.init_progress_store(task_db_path)
        logger.info("TaskExecutor initialized with progress store")

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

        # 初始化权限管理器
        try:
            await self.permission_manager.init()
            await self.audit_logger.init()
            logger.info("Permission manager and audit logger initialized")
        except Exception as e:
            import traceback

            logger.warning(f"Permission manager initialization failed: {e}")
            logger.warning(f"Traceback: {traceback.format_exc()}")

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
        wallet_address: str | None = None,
        participant_type: ParticipantType = ParticipantType.HUMAN,
        skip_complexity_detection: bool = False,
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
        print(f"DEBUG [CHAT] ===== ENTRY ===== message={message[:50]}..., skip_complexity={skip_complexity_detection}")

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
                    logger.info(f"[CHAT] Active task {t.task_id}: status={t.status}, wallet={t.wallet_address}")

                awaiting_tasks = [t for t in pending_tasks if t.status == TaskStatus.AWAITING_CONFIRM]
                logger.info(f"[CHAT] Found {len(awaiting_tasks)} awaiting tasks")

                # 如果没找到，也检查内存中的所有待确认任务
                if not awaiting_tasks:
                    awaiting_tasks = [t for t in all_active_tasks if t.status == TaskStatus.AWAITING_CONFIRM]
                    logger.info(f"[CHAT] Fallback check found {len(awaiting_tasks)} awaiting tasks in memory")

                for t in pending_tasks:
                    logger.info(f"[CHAT] Task {t.task_id}: status={t.status}, wallet={t.wallet_address}")

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
                    error_msg = "没有找到待确认的任务。请先描述您想要执行的任务，我会为您生成执行计划。"
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
            logger.info(f"[CHAT][COMPLEXITY] 检测到任务复杂度: {complexity.value}, message={message[:30]}...")
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
                        logger.info(f"[CHAT][COMPLEXITY] 计划生成完成: task_id={plan.task_id}, status={plan.status.value}")

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
                            logger.info(f"[CHAT][COMPLEXITY] 计划状态非AWAITING_CONFIRM: {plan.status.value}，继续执行")
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
                        logger.info(f"[CHAT][COMPLEXITY] HIGH任务计划生成: {plan.task_id}, 共{len(plan.steps)}步")

                        # 直接执行计划（不等待确认）
                        result = await self.task_executor.execute_plan(plan)
                        logger.info(f"[CHAT][COMPLEXITY] HIGH任务执行完成: status={result.status.value}")

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

        # 构建用户信息
        user_info = None
        if wallet_address:
            user_info = UserInfo(
                address=wallet_address,
                role="USER",
                binding_type="wallet" if wallet_address.startswith("0x") else "manual",
            )

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
                {"role": "system", "content": messages[0]["content"] if messages else "You are a helpful assistant."},
                {"role": "user", "content": message}
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
        messages = await self.context_manager.build_messages(
            user_message=message,
            conversation_history=history_messages,
            user_info=user_info,
            available_tools=tool_names,
            memory_context=memory_context,
            smart_recall_context=smart_recall_context,
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

        # MEDIUM 复杂度：不限制工具数量，确保 LLM 能选择正确的工具
        # 注意：MiniMax API 对工具数量有限制，过多会报错，但过少会导致 LLM 无法选择正确工具
        # 当前 fallback 机制会在报错时重试，所以可以不过度限制

        skills_schema = self.skills_manager.get_skills_schema(provider=llm_provider)
        # 也过滤 skills 中的无效工具
        skills_schema = [s for s in skills_schema if is_valid_tool(s)]
        logger.info(f"[CHAT][TOOLS] 最终使用: tools={len(tools_schema)}, skills={len(skills_schema)}")

        # =====================================================================
        # 核心 LLM 调用逻辑 (MEDIUM/HIGH 复杂度)
        # =====================================================================

        try:
            logger.info(f"[CHAT][FLOW] 调用 _chat_with_llm (复杂度={complexity.value})")

            # 调用 LLM 获取完整结果
            chat_result = await self._chat_with_llm(
                messages,
                tools=tools_schema,
                skills=skills_schema,
                conversation_id=str(conversation.id),
                user_session=user_session,
            )

            logger.info(f"[CHAT][RESULT] ChatResult: is_complete={chat_result.is_complete}, needs_background={chat_result.needs_background}, needs_tool_retry={chat_result.needs_tool_retry}, needs_continuation={chat_result.needs_continuation}")

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
            if chat_result.is_complete and not chat_result.needs_background:
                logger.info("[CHAT][RESULT] 情况1: 正常完成，直接返回")

                await self.conversation_manager.add_message(
                    conversation_id=conversation.id,
                    role=MessageRole.ASSISTANT,
                    content=chat_result.content,
                )
                return chat_result.content

            # 情况 2：is_complete=True 但 needs_background=True（忽略，避免误判）
            if chat_result.is_complete and chat_result.needs_background:
                logger.warning("[CHAT][RESULT] 情况2: is_complete=True但needs_background=True，忽略background，正常返回")

                await self.conversation_manager.add_message(
                    conversation_id=conversation.id,
                    role=MessageRole.ASSISTANT,
                    content=chat_result.content,
                )
                return chat_result.content

            # 情况 3：需要工具重试（参数错误）
            if chat_result.needs_tool_retry:
                logger.info("[CHAT][RESULT] 情况3: 需要工具重试 (参数错误)")

                # 启动后台任务处理器
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
            if chat_result.needs_continuation:
                logger.info(f"[CHAT][RESULT] 情况4: 需要继续处理, tool_results={len(chat_result.tool_results)}")

                # 如果有实质性工具结果，启动后台处理
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
                else:
                    # 没有工具结果，说明LLM没有执行任何工具
                    # 直接返回内容（即使是空的），不返回错误
                    logger.warning("[CHAT][RESULT] 没有工具结果，不启动后台处理")
                    if chat_result.content:
                        await self.conversation_manager.add_message(
                            conversation_id=conversation.id,
                            role=MessageRole.ASSISTANT,
                            content=chat_result.content,
                        )
                        return chat_result.content
                    else:
                        return "抱歉，我无法处理这个请求。请稍后重试或换一个方式描述。"

            # 情况 5：其他异常情况
            logger.warning(f"[CHAT][RESULT] 情况5: 异常情况 - is_complete={chat_result.is_complete}, needs_background={chat_result.needs_background}")

            if chat_result.content:
                await self.conversation_manager.add_message(
                    conversation_id=conversation.id,
                    role=MessageRole.ASSISTANT,
                    content=chat_result.content,
                )
                return chat_result.content
            else:
                return "抱歉，处理您的请求时遇到了问题。请稍后重试。"

        except Exception as e:
            logger.error(f"[CHAT] LLM call failed: {e}")
            return self.chat_config.llm_unavailable_message

    async def _learn_and_evolve(self):
        """学习进化"""
        await self.learning.learn_from_experience()

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
        logger.warning("[DEPRECATED] Using legacy background task, should migrate to BackgroundTaskProcessor")
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
            return ChatResult(
                content=content,
                executed_tools=[],
                tool_results=[],
                iterations_used=0,
                is_complete=True,
                needs_background=False,
                needs_tool_retry=False,
            )

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

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"DEBUG agent loop iteration {iteration}")

            # Step 1: 调用 LLM（带工具）
            logger.info(f"🔍 [AGENT_LOOP] 调用 LLM, iteration={iteration}")
            llm_response = await self._call_llm_with_tools(current_messages, all_tools)
            logger.info(f"🔍 [AGENT_LOOP] LLM 返回了, content_len={len(llm_response.get('content', ''))}, tool_calls={len(llm_response.get('tool_calls', []))}")

            # Step 2: 检查是否有工具调用
            tool_calls = llm_response.get("tool_calls", [])
            logger.info(f"DEBUG tool_calls count: {len(tool_calls)}")

            if not tool_calls:
                # === 没有工具调用，LLM 已生成最终回复 ===
                content = llm_response.get("content", "")

                # 检查是否是第一次尝试失败，降级处理
                if iteration == 1 and content and "失败" in content:
                    logger.info("[DEBUG] Tool call failed, falling back to simple chat")
                    fallback_content = await self._call_llm_simple(current_messages)
                    return ChatResult(
                        content=fallback_content,
                        executed_tools=executed_tools,
                        tool_results=all_tool_results,
                        iterations_used=iteration,
                        is_complete=True,
                        needs_background=False,
                        needs_tool_retry=False,
                    )

                # === 检测 LLM 是否匆忙结束（关键改进）===
                # 设计初衷：处理 LLM 返回"正在处理中"但实际上后续没有继续的情况
                needs_continuation, continuation_reason = self._detect_hasty_completion(content)

                if needs_continuation:
                    logger.info(f"[CHAT_RESULT] Detected hasty completion: {continuation_reason}")
                    return ChatResult(
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
                    )

                # === 正常完成 ===
                return ChatResult(
                    content=content,
                    executed_tools=executed_tools,
                    tool_results=all_tool_results,
                    iterations_used=iteration,
                    is_complete=True,
                    needs_background=False,
                    needs_tool_retry=False,
                )

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
                return ChatResult(
                    content="",
                    executed_tools=executed_tools,
                    tool_results=all_tool_results,
                    iterations_used=iteration,
                    is_complete=False,
                    needs_background=True,
                    needs_tool_retry=True,
                    needs_continuation=False,
                    retry_info=tool_retry_info,
                )

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
        return ChatResult(
            content="抱歉，这个问题需要处理较长时间，请稍后再试。或者你可以尝试简化问题。",
            executed_tools=executed_tools,
            tool_results=all_tool_results,
            iterations_used=iteration,
            is_complete=False,
            needs_background=True,
            needs_tool_retry=False,
            needs_continuation=True,
            error="max_iterations_reached",
        )

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
                    "keywords": ["api key", "apikey", "api_key", "invalid key", "key is required", "unauthorized", "认证失败", "密钥"],
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
                raw_content_blocks.append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "input": tc["function"]["arguments"],
                })

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

            tool_result_blocks.append({
                "type": "tool_result",
                "tool_use_id": tool_call_id,
                "content": json.dumps(_serialize_for_json(tool_result), ensure_ascii=False),
            })

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
        current_messages.append({
            "role": "assistant",
            "content": llm_response.get("content", ""),
            "tool_calls": tool_calls,
        })

        for tool_result in tool_results:
            current_messages.append({
                "role": "tool",
                "content": json.dumps(_serialize_for_json(tool_result), ensure_ascii=False),
                "tool_call_id": tool_calls[0].get("id") if tool_calls else None,
            })

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
                    logger.info(f"DEBUG _call_llm_with_tools returned, content_len={len(result.get('content', ''))}, tool_calls={len(result.get('tool_calls', []))}")
                    return result
                except Exception as e:
                    logger.error(f"chat_with_tools failed: {e}", exc_info=True)
                    return {"content": f"LLM 调用失败: {str(e)}", "tool_calls": []}
            else:
                try:
                    content = await adapter.chat_with_messages(messages)
                    return {"content": content, "tool_calls": []}
                except Exception as e:
                    logger.error(f"chat_with_messages failed: {e}", exc_info=True)
                    return {"content": f"LLM 调用失败: {str(e)}", "tool_calls": []}
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
                results.append(
                    {
                        "tool": tool_name if "tool_name" in dir() else "unknown",
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
            await self.session_manager.get_or_create_session(wallet_address)
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

        lines.extend([
            "\n---",
            "**请回复以下命令之一**:",
            "- `确认执行` - 开始执行计划",
            "- `取消` - 取消此任务",
            "- `修改` - 提出修改建议",
        ])

        return "\n".join(lines)

    def _format_plan_result(self, plan: TaskPlan) -> str:
        """
        格式化任务执行结果

        Args:
            plan: 执行完成的任务计划

        Returns:
            格式化的执行结果
        """
        logger.info(f"[FORMAT_RESULT] 格式化任务结果: status={plan.status.value}, steps={len(plan.steps)}")

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
                    results.append(f"❌ **步骤 {i+1}: {step.name}** 失败\n{step.error or '未知错误'}")

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
                                results.append(f"**步骤 {i+1}: {step.name}**\n{output[:1000]}")  # 限制长度
                        else:
                            results.append(f"**步骤 {i+1}: {step.name}**\n{str(step.result)[:1000]}")

                if results:
                    return "✅ **任务执行完成**\n\n" + "\n\n".join(results)
                else:
                    return "✅ 任务执行完成（无详细结果）"
            else:
                failed_steps = [
                    s for s in executed_plan.steps if s.status.value == "failed"
                ]
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
