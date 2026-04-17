#!/usr/bin/env python3
"""Precise edit script for MetaAgent v2.0 integration."""

import re

AGENT_PY = "src/usmsb_sdk/meta_agent/agent.py"

with open(AGENT_PY, "r") as f:
    content = f.read()

original = content

# 1. Add StrategyRouter import at top
if "from .strategy_router import StrategyRouter" not in content:
    content = re.sub(
        r'(from \.memory\.guardian_daemon import GuardianConfig, GuardianDaemon)',
        r'\1\nfrom .strategy_router import StrategyRouter',
        content
    )
    print("1. Added StrategyRouter import")

# 2. Add 3 new fields in __init__
old_fields = (
    "        # ========== A2A HTTP Server ==========\n"
    "        self._a2a_server_task: asyncio.Task | None = None\n"
    "\n"
    "        # 状态"
)
new_fields = (
    "        # ========== A2A HTTP Server ==========\n"
    "        self._a2a_server_task: asyncio.Task | None = None\n"
    "\n"
    "        # ========== StrategyRouter（LLM 双轨策略路由）==========\n"
    "        self.strategy_router: Any = None\n"
    "\n"
    "        # ========== L4 自我意识 Agent ==========\n"
    "        self.l4_agent: Any = None\n"
    "\n"
    "        # ========== L5 集体智能（MetaAgent 私有）==========\n"
    "        self.l5_collective: Any = None\n"
    "        self._external_agents_connected: bool = False\n"
    "\n"
    "        # 状态"
)
content = content.replace(old_fields, new_fields)
print("2. Added __init__ fields")

# 3. Add 3 init calls in start()
old_start = (
    "        # ========== A2A HTTP Server 注册 ==========\n"
    "        await self._register_a2a_agent()\n"
    "\n"
    "        # 启动目标引擎"
)
new_start = (
    "        # ========== A2A HTTP Server 注册 ==========\n"
    "        await self._register_a2a_agent()\n"
    "\n"
    "        # ========== StrategyRouter 初始化 ==========\n"
    "        await self._init_strategy_router()\n"
    "\n"
    "        # ========== L4 自我意识 Agent 初始化 ==========\n"
    "        await self._init_l4_agent()\n"
    "\n"
    "        # ========== L5 集体智能初始化 ==========\n"
    "        await self._init_l5_collective()\n"
    "\n"
    "        # 启动目标引擎"
)
content = content.replace(old_start, new_start)
print("3. Added start() init calls")

# 4. Add 3 new methods before _main_loop
old_main_loop = "    async def _main_loop(self):\n        \"\"\"主循环 - 永不停歇\"\"\""
new_methods_and_main_loop = (
    "    async def _init_strategy_router(self) -> None:\n"
    "        \"\"\"Initialize StrategyRouter for dual-track routing.\"\"\"\n"
    "        try:\n"
    "            exp_path = os.path.join(self.config.data_dir or \"data\", \"strategy_experience.db\")\n"
    "            os.makedirs(os.path.dirname(exp_path) or \"data\", exist_ok=True)\n"
    "            self.strategy_router = StrategyRouter(\n"
    "                llm_manager=self.llm_manager,\n"
    "                experience_db_path=exp_path,\n"
    "            )\n"
    "            logger.info(\"StrategyRouter initialized\")\n"
    "        except Exception as e:\n"
    "            logger.warning(\"StrategyRouter init failed: %s\", e)\n"
    "            self.strategy_router = None\n"
    "\n"
    "    async def _init_l4_agent(self) -> None:\n"
    "        \"\"\"Initialize L4 self-conscious agent.\"\"\"\n"
    "        try:\n"
    "            from usmsb_sdk.l4.l4_agent import L4Agent\n"
    "            self.l4_agent = L4Agent(agent_id=self.agent_id, llm_manager=self.llm_manager)\n"
    "            logger.info(\"L4Agent initialized\")\n"
    "        except Exception as e:\n"
    "            logger.warning(\"L4Agent init failed: %s\", e)\n"
    "            self.l4_agent = None\n"
    "\n"
    "    async def _init_l5_collective(self) -> None:\n"
    "        \"\"\"Initialize L5 Collective Intelligence.\"\"\"\n"
    "        try:\n"
    "            from usmsb_sdk.l5.l5_collective import L5CollectiveIntelligence\n"
    "            self.l5_collective = L5CollectiveIntelligence(\n"
    "                agent_id=self.agent_id,\n"
    "                llm_manager=self.llm_manager,\n"
    "            )\n"
    "            logger.info(\"L5CollectiveIntelligence initialized\")\n"
    "        except Exception as e:\n"
    "            logger.warning(\"L5CollectiveIntelligence init failed: %s\", e)\n"
    "            self.l5_collective = None\n"
    "\n"
    "    async def _main_loop(self):\n"
    "        \"\"\"主循环 - 永不停歇\"\"\""
)
content = content.replace(old_main_loop, new_methods_and_main_loop)
print("4. Added new init methods before _main_loop")

# 5. Replace _perceive_environment
old_perceive = (
    "    async def _perceive_environment(self):\n"
    "        \"\"\"感知环境\"\"\"\n"
    "        pass"
)
new_perceive = (
    "    async def _perceive_environment(self):\n"
    "        \"\"\"感知环境 - 监控关键指标\"\"\"\n"
    "        try:\n"
    "            # 监控钱包 ETH 余额\n"
    "            if self.wallet_manager and self.wallet_manager.address:\n"
    "                try:\n"
    "                    eth_info = await self.wallet_manager.get_native_balance()\n"
    "                    if eth_info.get(\"success\") and eth_info.get(\"balance_eth\", 999) < 0.01:\n"
    "                        logger.warning(\"[PERCEIVE] Low ETH balance: %.4f ETH\", eth_info[\"balance_eth\"])\n"
    "                except Exception:\n"
    "                    pass\n"
    "            # 监控任务队列深度\n"
    "            if self.task_executor:\n"
    "                pending = len([t for t in getattr(self.task_executor, \"_active_tasks\", {}).values()])\n"
    "                if pending > 10:\n"
    "                    logger.info(\"[PERCEIVE] Task queue depth: %d\", pending)\n"
    "            # 感知 P2P 网络状态\n"
    "            if hasattr(self, \"_p2p_handler\") and self._p2p_handler:\n"
    "                try:\n"
    "                    stats = self._p2p_handler.get_network_stats()\n"
    "                    if stats.get(\"online_peers\", 0) > 0:\n"
    "                        self._external_agents_connected = True\n"
    "                        logger.info(\"[PERCEIVE] P2P peers online: %d\", stats[\"online_peers\"])\n"
    "                except Exception:\n"
    "                    pass\n"
    "        except Exception as e:\n"
    "            logger.debug(\"_perceive_environment error: %s\", e)"
)
content = content.replace(old_perceive, new_perceive)
print("5. Replaced _perceive_environment")

# 6. Replace _process_pending_tasks
old_pending = (
    "    async def _process_pending_tasks(self):\n"
    "        \"\"\"处理待处理任务\"\"\"\n"
    "        pass"
)
new_pending = (
    "    async def _process_pending_tasks(self):\n"
    "        \"\"\"处理待处理任务队列\"\"\"\n"
    "        try:\n"
    "            if not self.task_executor:\n"
    "                return\n"
    "            active = getattr(self.task_executor, \"_active_tasks\", {})\n"
    "            for task_id, task in active.items():\n"
    "                if task.status.value == \"pending\":\n"
    "                    logger.info(\"[TASK] Triggering pending task: %s\", task_id)\n"
    "                    asyncio.create_task(self.task_executor.execute_plan(task))\n"
    "        except Exception as e:\n"
    "            logger.debug(\"_process_pending_tasks error: %s\", e)"
)
content = content.replace(old_pending, new_pending)
print("6. Replaced _process_pending_tasks")

# 7. Replace _learn_and_evolve
old_learn = (
    "    async def _learn_and_evolve(self):\n"
    "        \"\"\"学习进化\"\"\"\n"
    "        await self.learning.learn_from_experience()\n"
    "\n"
    "    async def chat("
)
new_learn = (
    "    async def _learn_and_evolve(self):\n"
    "        \"\"\"学习进化 - L4/L5 增强版\"\"\"\n"
    "        try:\n"
    "            await self.learning.learn_from_experience()\n"
    "            if self.l4_agent:\n"
    "                try:\n"
    "                    reflection = await self.l4_agent.self_reflect()\n"
    "                    if reflection.insights:\n"
    "                        logger.info(\"[L4] Self-insights: %s\", str(reflection.insights)[:100])\n"
    "                except Exception as e:\n"
    "                    logger.warning(\"[L4] self_reflect failed: %s\", e)\n"
    "            if self.l5_collective and self._external_agents_connected:\n"
    "                try:\n"
    "                    thought = await self.l5_collective.think_collectively(\"如何提升平台整体性能和用户体验\")\n"
    "                    if thought.synthesis:\n"
    "                        logger.info(\"[L5] Collective thought: %s\", thought.synthesis[:80])\n"
    "                except Exception as e:\n"
    "                    logger.warning(\"[L5] think_collectively failed: %s\", e)\n"
    "        except Exception as e:\n"
    "            logger.warning(\"_learn_and_evolve failed: %s\", e)\n"
    "\n"
    "    async def chat("
)
content = content.replace(old_learn, new_learn)
print("7. Replaced _learn_and_evolve")

# 8. Add GeneCapsule RAG injection
old_gene = (
    "        # ========== 检测用户强调记忆 ==========\n"
    "        if self.memory_manager:\n"
    "            try:\n"
    "                await self.memory_manager.check_and_store_user_emphasis(\n"
    "                    user_id=owner_id, message=message\n"
    "                )\n"
    "            except Exception as e:\n"
    "                logger.warning(f\"Failed to check user emphasis: {e}\")\n"
    "\n"
    "        # 构建用户信息"
)
new_gene = (
    "        # ========== 检测用户强调记忆 ==========\n"
    "        if self.memory_manager:\n"
    "            try:\n"
    "                await self.memory_manager.check_and_store_user_emphasis(\n"
    "                    user_id=owner_id, message=message\n"
    "                )\n"
    "            except Exception as e:\n"
    "                logger.warning(f\"Failed to check user emphasis: {e}\")\n"
    "\n"
    "        # ========== Gene Capsule RAG 上下文注入 ==========\n"
    "        gene_capsule_context = \"\"\n"
    "        if self.gene_capsule_adapter:\n"
    "            try:\n"
    "                gene_capsule_context = await self.gene_capsule_adapter.build_rag_context(\n"
    "                    task_description=message,\n"
    "                    max_experiences=3,\n"
    "                )\n"
    "                if gene_capsule_context:\n"
    "                    logger.info(\"[GeneCapsule] Injected %d chars\", len(gene_capsule_context))\n"
    "            except Exception as e:\n"
    "                logger.warning(\"[GeneCapsule] build_rag_context failed: %s\", e)\n"
    "\n"
    "        # 构建用户信息"
)
content = content.replace(old_gene, new_gene)
print("8. Added GeneCapsule RAG injection")

# 9. Update memory_context building
old_memory = (
    "        # ========== 构建消息列表 (提前到复杂度分支之前) ==========\n"
    "        messages = await self.context_manager.build_messages(\n"
    "            user_message=message,\n"
    "            conversation_history=history_messages,\n"
    "            user_info=user_info,\n"
    "            available_tools=[],  # 先传空，后面根据复杂度更新\n"
    "            memory_context=memory_context,\n"
    "            smart_recall_context=smart_recall_context,\n"
    "        )"
)
new_memory = (
    "        # Prepend GeneCapsule context\n"
    "        _full_memory_context = memory_context\n"
    "        if gene_capsule_context and _full_memory_context:\n"
    "            memory_context = gene_capsule_context + \"\\n\\n\" + _full_memory_context\n"
    "        elif gene_capsule_context:\n"
    "            memory_context = gene_capsule_context\n"
    "        # ========== 构建消息列表 (提前到复杂度分支之前) ==========\n"
    "        messages = await self.context_manager.build_messages(\n"
    "            user_message=message,\n"
    "            conversation_history=history_messages,\n"
    "            user_info=user_info,\n"
    "            available_tools=[],  # 先传空，后面根据复杂度更新\n"
    "            memory_context=memory_context,\n"
    "            smart_recall_context=smart_recall_context,\n"
    "        )"
)
content = content.replace(old_memory, new_memory)
print("9. Updated memory_context building")

# 10. Add L4 feel/metacognition after "情况1: 正常完成"
old_l4 = (
    "            # 情况 1：正常完成，直接返回\n"
    "            if chat_result.is_complete and not chat_result.needs_background:\n"
    "                logger.info(\"[CHAT][RESULT] 情况1: 正常完成，直接返回\")\n"
    "\n"
    "                await self.conversation_manager.add_message(\n"
    "                    conversation_id=conversation.id,\n"
    "                    role=MessageRole.ASSISTANT,\n"
    "                    content=chat_result.content,\n"
    "                )\n"
    "                return chat_result.content"
)
new_l4 = (
    "            # 情况 1：正常完成，直接返回\n"
    "            if chat_result.is_complete and not chat_result.needs_background:\n"
    "                logger.info(\"[CHAT][RESULT] 情况1: 正常完成，直接返回\")\n"
    "\n"
    "                await self.conversation_manager.add_message(\n"
    "                    conversation_id=conversation.id,\n"
    "                    role=MessageRole.ASSISTANT,\n"
    "                    content=chat_result.content,\n"
    "                )\n"
    "\n"
    "            # ========== L4 自我意识处理 ==========\n"
    "            if self.l4_agent and chat_result.content:\n"
    "                try:\n"
    "                    mood_result = await self.l4_agent.feel({\n"
    "                        \"stimulus\": \"conversation\",\n"
    "                        \"content\": chat_result.content,\n"
    "                        \"message\": message,\n"
    "                    })\n"
    "                    if mood_result.emotion and mood_result.intensity > 0.5:\n"
    "                        logger.info(\"[L4] Emotion: %s (intensity=%.2f)\", mood_result.emotion, mood_result.intensity)\n"
    "                    conv_count = getattr(self, \"_conversation_count\", 0) + 1\n"
    "                    self._conversation_count = conv_count\n"
    "                    if conv_count % 20 == 0:\n"
    "                        reflection = await self.l4_agent.self_reflect()\n"
    "                        logger.info(\"[L4] Self-reflection: confidence=%.2f\", reflection.confidence)\n"
    "                except Exception as e:\n"
    "                    logger.warning(\"[L4] Self-awareness failed: %s\", e)\n"
    "\n"
    "            if chat_result.is_complete and not chat_result.needs_background:\n"
    "                return chat_result.content"
)
content = content.replace(old_l4, new_l4)
print("10. Added L4 feel/metacognition after 情况1")

# Verify changes were made
if content == original:
    print("\nWARNING: No changes were made!")
else:
    print("\nAll changes applied successfully!")

with open(AGENT_PY, "w") as f:
    f.write(content)

print(f"\nWritten to {AGENT_PY}")