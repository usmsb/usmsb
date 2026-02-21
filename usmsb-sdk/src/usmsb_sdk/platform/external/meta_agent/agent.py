"""
Meta Agent 主类
基于 USMSB Core 的超级 Agent
具备感知、决策、执行、交互、转化、评估、反馈、学习、风险管理能力
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .config import MetaAgentConfig
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
from .knowledge.base import KnowledgeBase
from .knowledge.vector_store import VectorKnowledgeBase
from .wallet.manager import WalletManager
from .goals.engine import GoalEngine
from .evolution.engine import EvolutionEngine
from .memory.memory_manager import MemoryManager, MemoryConfig

logger = logging.getLogger(__name__)


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

        # 核心组件
        self.llm_manager = LLMManager(self.config.llm)
        self.tool_registry = ToolRegistry()
        self.skills_manager = SkillsManager(self.config.database.path)

        # 知识库 - 使用向量知识库
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

        # 状态
        self._running = False
        self._main_loop_task: Optional[asyncio.Task] = None

    async def start(self):
        """启动 Meta Agent"""
        logger.info(f"Starting Meta Agent {self.agent_id}...")

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

        await self.goal_engine.stop()
        await self.context_manager.save()

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

        Args:
            message: 用户消息
            wallet_address: 用户钱包地址（用于会话隔离）
            participant_type: 参与者类型

        Returns:
            Agent 回复
        """
        # 确定会话所有者
        owner_id = wallet_address or f"anonymous_{uuid4().hex[:8]}"

        # 获取或创建会话
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
        print(f"[DEBUG] chat: tools count={len(tool_names)}")

        # 构建完整的消息列表（包含系统提示词、知识库检索、对话历史、分层记忆）
        messages = await self.context_manager.build_messages(
            user_message=message,
            conversation_history=history_messages,
            user_info=user_info,
            available_tools=tool_names,
            memory_context=memory_context,
        )
        print(f"[DEBUG] chat: messages count={len(messages)}")

        # 获取工具和技能 schema
        # MiniMax 使用 Anthropic API 格式
        llm_provider = "anthropic" if self.llm_manager.provider == "minimax" else "openai"
        tools_schema = self.tool_registry.get_tools_schema(provider=llm_provider)
        skills_schema = self.skills_manager.get_skills_schema(provider=llm_provider)
        print(
            f"[DEBUG] chat: tools_schema={len(tools_schema)}, skills_schema={len(skills_schema)}, provider={llm_provider}"
        )

        # 调用 LLM（支持工具和技能调用）
        try:
            # 检查是否需要执行工具调用
            initial_messages = await self.context_manager.build_messages(
                user_message=message,
                conversation_history=history_messages,
                user_info=user_info,
                available_tools=tool_names,
                memory_context=memory_context,
            )

            # 简单判断：如果消息很短且不包含工具相关关键词，直接处理
            simple_keywords = ["你好", "hi", "hello", "嗨", "您好"]
            is_simple = any(kw in message.lower() for kw in simple_keywords) and len(message) < 20

            # 工具相关关键词
            tool_keywords = [
                "搜索",
                "查找",
                "执行",
                "运行",
                "计算",
                "获取",
                "查询",
                "列出",
                "读取",
                "写",
                "创建",
            ]
            needs_tools = any(kw in message for kw in tool_keywords) or not is_simple

            if needs_tools:
                # 需要执行工具，启动后台处理
                async def background_task():
                    try:
                        logger.info("Starting background task execution")
                        # 先记录开始执行 - 使用 BACKGROUND_TASK 类型
                        await self.conversation_manager.add_message(
                            conversation_id=conversation.id,
                            role=MessageRole.BACKGROUND_TASK,
                            content="🔄 后台任务开始执行...",
                        )

                        result_text = await self._chat_with_llm(
                            messages,
                            tools=tools_schema,
                            skills=skills_schema,
                            conversation_id=str(conversation.id),
                        )

                        # 打印结果供调试
                        logger.info(
                            f"Background task result: {result_text[:500] if result_text else 'EMPTY'}"
                        )

                        # 检查结果是否是超时或需要更多时间
                        if "需要更多时间" in result_text or "稍后再试" in result_text:
                            # 执行遇到问题，记录更详细的信息 - 使用 BACKGROUND_ERROR 类型
                            await self.conversation_manager.add_message(
                                conversation_id=conversation.id,
                                role=MessageRole.BACKGROUND_ERROR,
                                content=f"⚠️ 后台任务执行遇到问题\n\n{result_text}\n\n请查看服务器日志获取详细错误信息。",
                            )
                        else:
                            # 正常结果 - 使用 BACKGROUND_COMPLETE 类型
                            await self.conversation_manager.add_message(
                                conversation_id=conversation.id,
                                role=MessageRole.BACKGROUND_COMPLETE,
                                content=f"✅ 后台任务完成\n\n{result_text}",
                            )
                        logger.info("Background task completed and saved to history")
                    except Exception as e:
                        logger.error(f"Background task failed: {e}")
                        import traceback

                        error_detail = traceback.format_exc()
                        await self.conversation_manager.add_message(
                            conversation_id=conversation.id,
                            role=MessageRole.BACKGROUND_ERROR,
                            content=f"❌ 后台任务执行失败\n\n错误: {str(e)}\n\n详情:\n{error_detail}",
                        )

                # 启动后台任务，不等待完成
                asyncio.create_task(background_task())

                # 立即返回任务提交消息
                response_text = "⏳ 您的请求已提交后台处理，完成后结果将自动保存到会话历史中。请稍后查看历史记录获取结果。"
            else:
                # 不需要工具调用，直接返回
                response_text = await self._chat_with_llm(
                    messages,
                    tools=tools_schema,
                    skills=skills_schema,
                )

            print(
                f"[DEBUG] chat: response_text={response_text[:100] if response_text else 'EMPTY'}"
            )
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            response_text = "抱歉，我现在无法处理你的请求。请稍后再试。"

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

    async def _chat_with_llm(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        skills: Optional[List[Dict[str, Any]]] = None,
        conversation_id: Optional[str] = None,
    ) -> str:
        """
        使用 LLM 生成回复，支持工具和技能调用

        Args:
            messages: 消息列表
            tools: 工具 schema 列表
            skills: 技能 schema 列表
            conversation_id: 可选的会话 ID，用于记录后台任务阶段

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
            tool_results = await self._execute_tool_calls(tool_calls)

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

                # 构建 tool_result content blocks
                tool_result_blocks = []
                for tool_result in tool_results:
                    tool_call_id = None
                    # 找到对应的 tool_call id
                    for tc in tool_calls:
                        if tc["function"]["name"] == tool_result.get("tool"):
                            tool_call_id = tc["id"]
                            break

                    tool_result_blocks.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_call_id,
                            "content": json.dumps(tool_result, ensure_ascii=False),
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
                            "content": json.dumps(tool_result, ensure_ascii=False),
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

    async def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """执行工具调用"""
        results = []

        for tool_call in tool_calls:
            try:
                tool_name = tool_call.get("function", {}).get("name", "")
                tool_args = tool_call.get("function", {}).get("arguments", {})

                # 解析参数
                if isinstance(tool_args, str):
                    import json

                    try:
                        tool_args = json.loads(tool_args)
                    except:
                        tool_args = {}

                # 执行工具
                result = await self.tool_registry.execute(tool_name, **tool_args)

                results.append(
                    {
                        "tool": tool_name,
                        "result": result,
                        "success": True,
                    }
                )

            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                results.append(
                    {
                        "tool": tool_name,
                        "result": {"error": str(e)},
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

    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """执行指定工具"""
        return await self.tool_registry.execute(tool_name, **kwargs)

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
