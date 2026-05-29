# -*- coding: utf-8 -*-
"""
L2 Agent - L2 工具性 Agent 骨架

L2 = L1 + 记忆 + 工具调用

L2 Agent 核心能力：
- LLM + 工具绑定
- 分层记忆
- ReAct 框架
- 向量检索
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from usmsb_sdk.l1 import RuleEngine, Stimulus, Response
from usmsb_sdk.l2.memory import AgentMemory
from usmsb_sdk.l2.tools import Tool, ToolRegistry, create_tool_registry


@dataclass
class L2Config:
    """L2 Agent 配置"""
    agent_id: str
    name: str = "L2Agent"
    model: str = "gpt-3.5-turbo"
    llm_client: Any = None  # LLM client instance
    max_context_length: int = 4096
    tool_timeout: float = 30.0  # 工具超时（秒）
    enable_memory: bool = True
    enable_tools: bool = True
    verbose: bool = False


class L2Agent:
    """
    L2 工具性 Agent
    
    L2 = L1 + 记忆 + 工具调用
    
    核心流程：
    1. 接收输入
    2. 读取记忆上下文
    3. 构建 Prompt
    4. LLM 决定是否调用工具
    5. 如果有工具调用，执行
    6. 记录到记忆
    7. 返回结果
    
    使用方式：
    ```python
    agent = L2Agent(agent_id="assistant")
    
    # 注册工具
    agent.register_tool(my_tool)
    
    # 运行
    response = await agent.run("帮我查一下今天的天气")
    ```
    """
    
    def __init__(self, config: L2Config):
        self.config = config
        self.agent_id = config.agent_id
        
        # L1 规则引擎（降级用）
        self.rule_engine = RuleEngine(name=f"{config.name}_rules")
        
        # 记忆系统
        if config.enable_memory:
            self.memory = AgentMemory(agent_id=config.agent_id)
        else:
            self.memory = None
        
        # 工具系统
        if config.enable_tools:
            self.tools = create_tool_registry()
        else:
            self.tools = ToolRegistry()
        
        # LLM 客户端
        if config.llm_client:
            self.llm_client = config.llm_client
        elif config.model:
            from ..meta_agent.llm_client import LLMClient
            self.llm_client = LLMClient()
        
        # 统计
        self.stats = {
            "total_requests": 0,
            "tool_calls": 0,
            "rule_matches": 0,
            "avg_latency_ms": 0.0,
        }
        
        # 状态
        self.is_running = False
        
        print(f"[L2Agent] {config.name} ({config.agent_id}) initialized")
    
    # ========== 工具管理 ==========
    
    def register_tool(self, tool: Tool) -> str:
        """注册工具"""
        return self.tools.register(tool)
    
    def unregister_tool(self, tool_name: str) -> bool:
        """注销工具"""
        return self.tools.unregister(tool_name)
    
    def get_tool(self, tool_name: str) -> Tool | None:
        """获取工具"""
        return self.tools.get(tool_name)
    
    def list_tools(self) -> list[Tool]:
        """列出所有工具"""
        return self.tools.list_all()

    async def think(self, prompt: str, tools: list = None, max_turns: int = 3) -> dict:
        """
        IL2: LLM 推理（带工具调用）

        流程：LLM 决定是否调用工具 -> 执行 -> 喂回结果 -> LLM 生成最终回复

        Args:
            prompt: 用户输入
            tools: 可用工具列表（SimpleTool 对象列表）
            max_turns: 最大工具调用轮数

        Returns:
            dict: {
                "reasoning": str,        # LLM 思考过程
                "tool_calls": list,       # 工具调用记录
                "message": str,           # 最终回复文本
                "tool_results": list      # 各工具执行结果
            }
        """
        messages = [{"role": "user", "content": prompt}]
        tool_calls_made = []
        tool_results = []

        for turn in range(max_turns):
            # Step 1: LLM 生成回复（可能带工具调用）
            response_text = await self.llm_client.chat(messages)

            # Step 2: 尝试解析工具调用
            tool_call = self._extract_tool_call(response_text)

            if not tool_call:
                # 无工具调用 -> 最终回复
                return {
                    "reasoning": self._extract_reasoning(messages),
                    "tool_calls": tool_calls_made,
                    "message": response_text,
                    "tool_results": tool_results,
                }

            # Step 3: 执行工具
            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("arguments", {})
            tool_result = await self._execute_tool(tool_name, tool_args, tools or [])

            # Step 4: 记录
            tool_calls_made.append({"turn": turn + 1, "name": tool_name, "args": tool_args})
            tool_results.append({"name": tool_name, "result": tool_result})

            # Step 5: 将工具结果追加到对话
            messages.append({"role": "assistant", "content": response_text})
            messages.append({
                "role": "user",
                "content": f"[工具调用结果]\n{tool_name}() = {tool_result}"
            })

        # 达到最大轮数仍未结束
        return {
            "reasoning": "已达到最大工具调用轮数",
            "tool_calls": tool_calls_made,
            "message": response_text,
            "tool_results": tool_results,
        }

    def _extract_tool_call(self, text: str) -> dict | None:
        """从 LLM 回复中提取工具调用"""
        import json, re

        # 格式1: ```tool_call {...} ```
        m = re.search(r'```(?:tool_call)?\s*\n?({.+?})\n?```', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass

        # 格式2: <tool_call>...</tool_call>
        m = re.search(r'<tool_call>\s*({.+?})\s*</tool_call>', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass


        # 格式3: 纯 JSON {"name": "...", "arguments": {...}}
        try:
            data = json.loads(text.strip())
            if isinstance(data, dict) and "name" in data and "arguments" in data:
                return data
        except Exception:
            pass

        return None

    def _extract_reasoning(self, messages: list) -> str:
        """从对话历史提取 LLM 推理过程"""
        return ""

    async def _execute_tool(self, name: str, args: dict, tools: list) -> str:
        """根据名称查找并执行工具"""
        for tool in tools:
            if hasattr(tool, "name") and tool.name == name:
                try:
                    result = await tool.execute(**args)
                    return str(result)
                except Exception as e:
                    return f"Error: {e}"
        return f"Error: tool '{name}' not found"

    async def remember(self, key: str, value) -> None:
        """
        IL2: 存储记忆
        """
        self.add_memory(f"{key}: {value}", memory_type="semantic", importance=0.7)

    async def recall(self, query: str) -> list:
        """
        IL2: 检索记忆
        """
        if self.memory and hasattr(self.memory, 'semantic'):
            return self.memory.semantic.retrieve(query, top_k=5)
        return []

    
    # ========== 记忆管理 ==========
    
    def add_memory(
        self,
        content: str,
        memory_type: str = "episodic",
        importance: float = 0.5
    ) -> str:
        """添加记忆"""
        if not self.memory:
            return ""
        
        if memory_type == "episodic":
            return self.memory.episodic.add_episode(content, importance)
        elif memory_type == "semantic":
            return self.memory.semantic.add_knowledge(content, importance)
        return ""
    
    def search_memory(self, query: str) -> list[dict]:
        """搜索记忆"""
        if not self.memory:
            return []
        
        results = []
        
        # 搜索情景记忆
        for episode in self.memory.episodic.search(query):
            results.append({
                "type": "episodic",
                "content": episode.content,
                "importance": episode.importance,
            })
        
        # 搜索语义记忆
        for knowledge in self.memory.semantic.search(query):
            results.append({
                "type": "semantic",
                "content": knowledge.content,
                "importance": knowledge.importance,
            })
        
        return results
    
    # ========== LLM 调用 ==========
    
    async def _call_llm(
        self,
        prompt: str,
        system_prompt: str | None = None
    ) -> str:
        """
        调用 LLM（简化版）
        
        实际实现会调用 OpenAI/Claude API。
        """
        # 简化实现：返回假响应
        return f"LLM response to: {prompt[:50]}..."
    
    async def _decide_tool_call(self, prompt: str) -> tuple[bool, str | None, dict | None]:
        """
        让 LLM 决定是否调用工具
        
        Returns:
            (should_call, tool_name, tool_args)
        """
        # 简化实现：检查 Prompt 中是否包含工具名
        for tool in self.tools.list_all():
            if tool.name.lower() in prompt.lower():
                return True, tool.name, {}
        
        return False, None, None
    
    # ========== 核心运行 ==========
    
    async def run(self, user_input: str, context: dict = None) -> str:
        """
        运行 Agent 处理输入
        
        Args:
            user_input: 用户输入
            
        Returns:
            str: Agent 响应
        """
        self.stats["total_requests"] += 1
        start_time = datetime.now()
        
        # 1. 尝试 L1 规则匹配（最快路径）
        stimulus = Stimulus(text=user_input)
        rule_response = await self.rule_engine.react(stimulus)
        
        if rule_response.action_result != "我没有理解您的问题。":
            self.stats["rule_matches"] += 1
            return rule_response.action_result
        
        # 2. 获取记忆上下文
        context = ""
        if self.memory:
            turns = self.memory.working.get_context(last_n=10)
            context = "\n".join([f"{t.role}: {t.content}" for t in turns])
        
        # 3. 构建 Prompt
        prompt = self._build_prompt(user_input, context)
        
        # 4. 决定是否调用工具
        should_call, tool_name, tool_args = await self._decide_tool_call(prompt)
        
        if should_call and tool_name:
            # 5. 执行工具
            tool = self.get_tool(tool_name)
            if tool:
                self.stats["tool_calls"] += 1
                
                try:
                    # 带超时执行
                    result = await asyncio.wait_for(
                        tool.execute(**tool_args),
                        timeout=self.config.tool_timeout
                    )
                    
                    if result.get("success"):
                        response = str(result.get("result", ""))
                    else:
                        response = f"工具执行失败: {result.get('error', 'unknown')}"
                    
                except asyncio.TimeoutError:
                    response = f"工具执行超时（{self.config.tool_timeout}秒）"
                except Exception as e:
                    response = f"工具执行错误: {str(e)}"
            else:
                response = f"工具不存在: {tool_name}"
        else:
            # 6. 直接 LLM 生成
            response = await self._call_llm(prompt)
        
        # 7. 记录到记忆
        if self.memory:
            self.memory.working.add_turn("user", user_input)
            self.memory.working.add_turn("assistant", response)
        
        # 8. 计算延迟
        latency = (datetime.now() - start_time).total_seconds() * 1000
        self.stats["avg_latency_ms"] = (
            self.stats["avg_latency_ms"] * 0.9 + latency * 0.1
        )
        
        return response
    
    def _build_prompt(self, user_input: str, context: str) -> str:
        """构建 Prompt"""
        prompt_parts = []
        
        if context:
            prompt_parts.append(f"对话历史:\n{context}\n")
        
        prompt_parts.append(f"当前输入: {user_input}")
        
        if self.tools.list_all():
            tool_names = [t.name for t in self.tools.list_all()]
            prompt_parts.append(f"\n可用工具: {', '.join(tool_names)}")
        
        return "\n".join(prompt_parts)
    
    async def run_with_history(
        self,
        messages: list[dict]
    ) -> dict:
        """
        带历史的对话
        
        Args:
            messages: [{"role": "user", "content": "..."}]
            
        Returns:
            dict: {"response": str, "tool_used": str|None}
        """
        if not messages:
            return {"response": "No input", "tool_used": None}
        
        # 获取最后一条用户消息
        last_user_msg = messages[-1]["content"] if messages[-1]["role"] == "user" else ""
        
        # 添加历史到工作记忆
        if self.memory:
            for msg in messages[:-1]:
                self.memory.working.add_turn(msg["role"], msg["content"])
        
        # 运行
        response = await self.run(last_user_msg)
        
        return {
            "response": response,
            "tool_used": None  # 简化
        }
    
    def get_status(self) -> dict:
        """获取 Agent 状态"""
        return {
            "agent_id": self.agent_id,
            "name": self.config.name,
            "is_running": self.is_running,
            "stats": self.stats,
            "tool_count": len(self.tools.list_all()),
            "memory": self.memory.to_dict() if self.memory else None,
        }
    
    def __repr__(self) -> str:
        return f"L2Agent({self.config.name}, id={self.agent_id})"
