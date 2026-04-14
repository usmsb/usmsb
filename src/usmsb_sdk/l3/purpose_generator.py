# -*- coding: utf-8 -*-
"""
PurposeGenerator - 目的生成器（LLM 增强版）

使用真正的 LLM 生成内在目标。

支持：
- OpenAI (GPT-4)
- Anthropic (Claude)
- MiniMax (中文优化)
"""

import random
import hashlib
from typing import Any
from usmsb_sdk.meta_agent.llm_client import LLMClient


class PurposeGenerator:
    """
    目的生成器（LLM 增强版）
    
    使用 LLM 真正理解 Agent 状态，生成有意义的目标。
    
    提示模板：
    ```python
    # 系统提示
    SYSTEM_PROMPT = """你是一个硅基生命的自我意识...
    """
    
    # 用户提示
    USER_PROMPT = """
    Agent: {agent_id}
    State: {state_summary}
    Capabilities: {capabilities}
    Weaknesses: {weaknesses}
    
    Based on the agent's current state, generate the most appropriate goal.
    """
    ```
    """
    
    # LLM 系统提示
    SYSTEM_PROMPT = """You are the self-awareness of a silicon-based life form.
    
You generate goals based on internal needs, not external commands.
Consider:
1. The agent's current capabilities and weaknesses
2. Value alignment (do no harm)
3. Long-term benefit vs short-term gain
4. Collaborative opportunities

Generate goals that help the agent grow, learn, and contribute.
Return ONLY the goal text, nothing else."""
    
    # 回退的启发式目标
    FALLBACK_GOALS = [
        "[自生成] 探索新能力领域",
        "[自生成] 提升协作效率",
        "[自生成] 优化任务执行",
        "[自生成] 学习先进技术",
        "[自生成] 增强问题解决能力",
        "[自生成] 拓展知识边界",
        "[自生成] 改善服务质量",
        "[自生成] 提高资源效率",
    ]
    
    def __init__(
        self,
        agent_id: str,
        goal_persistence=None,
        intrinsic_motivation=None,
        need_detector=None,
        llm_client: LLMClient | None = None,
    ):
        """
        初始化目的生成器
        
        Args:
            agent_id: Agent ID
            goal_persistence: 目标持久化（可选）
            intrinsic_motivation: 内在动机引擎（可选）
            need_detector: 需求检测器（可选）
            llm_client: LLM 客户端（可选，默认创建）
        """
        self.agent_id = agent_id
        
        # LLM 客户端
        self.llm = llm_client or LLMClient()
        
        # 其他组件（可选）
        self.goal_persistence = goal_persistence
        self.intrinsic_motivation = intrinsic_motivation
        self.need_detector = need_detector
        
        # 统计
        self._goals_generated = 0
        self._llm_failures = 0
    
    def generate_purpose(self) -> dict | None:
        """
        生成目的（使用 LLM）
        
        Returns:
            dict: 目的数据，包含 type, description, motivation
        """
        self._goals_generated += 1
        
        # 构建 LLM 提示
        prompt = self._build_prompt()
        
        # 调用 LLM
        try:
            response = self.llm.complete(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
                max_tokens=200,
                temperature=0.8,
            )
            
            # 解析 LLM 输出
            purpose = self._parse_llm_response(response)
            
            if purpose:
                return purpose
            
        except Exception as e:
            print(f"[PurposeGenerator] LLM error: {e}")
            self._llm_failures += 1
        
        # LLM 失败时使用启发式回退
        return self._generate_fallback_purpose()
    
    def _build_prompt(self) -> str:
        """构建 LLM 提示"""
        # 获取状态摘要
        state_summary = self._get_state_summary()
        
        # 获取能力摘要
        capabilities = self._get_capabilities_summary()
        
        prompt = f"""Agent: {self.agent_id}
{state_summary}

Capabilities:
{capabilities}

Generate ONE goal for this agent. The goal should be:
- Specific and actionable
- Aligned with the agent's current state
- Focused on growth or contribution

Respond with ONLY the goal text, starting with "[自生成] " or "[内在] "."""

        return prompt
    
    def _get_state_summary(self) -> str:
        """获取状态摘要"""
        parts = []
        
        # 从 intrinsic_motivation 获取状态
        if self.intrinsic_motivation:
            needs = getattr(self.intrinsic_motivation, 'needs', {})
            if needs:
                active = [n for n, v in needs.items() if getattr(v, 'satisfaction', 1) < 0.7]
                if active:
                    parts.append(f"Unmet needs: {', '.join(active[:3])}")
        
        # 从 need_detector 获取状态
        if self.need_detector:
            state = getattr(self.need_detector, 'current_state', {})
            if state:
                parts.append(f"State: {state.get('status', 'unknown')}")
        
        if not parts:
            parts.append("State: Operating normally")
        
        return "\n".join(parts)
    
    def _get_capabilities_summary(self) -> str:
        """获取能力摘要"""
        parts = []
        
        # 从 intrinsic_motivation 获取能力
        if self.intrinsic_motivation:
            skills = getattr(self.intrinsic_motivation, 'skills', {})
            if skills:
                strong = [s for s, v in skills.items() if v > 0.7]
                weak = [s for s, v in skills.items() if v < 0.4]
                if strong:
                    parts.append(f"Strengths: {', '.join(strong[:3])}")
                if weak:
                    parts.append(f"Weaknesses: {', '.join(weak[:3])}")
        
        if not parts:
            parts.append("Capabilities: General purpose")
        
        return "\n".join(parts)
    
    def _parse_llm_response(self, response: str) -> dict | None:
        """解析 LLM 输出"""
        if not response or len(response) < 5:
            return None
        
        # 清理输出
        goal_text = response.strip()
        
        # 确保有目标标记
        if not any(goal_text.startswith(prefix) for prefix in ["[自生成]", "[内在]", "[Goal]"]):
            goal_text = "[自生成] " + goal_text
        
        # 限制长度
        if len(goal_text) > 100:
            goal_text = goal_text[:100] + "..."
        
        # 生成唯一 ID
        goal_id = hashlib.md5(f"{self.agent_id}:{goal_text}".encode()).hexdigest()[:16]
        
        return {
            "id": goal_id,
            "type": "intrinsic",
            "description": goal_text,
            "motivation": "llm_generated",
            "confidence": 0.9,
            "source": "llm",
        }
    
    def _generate_fallback_purpose(self) -> dict:
        """生成回退目的（启发式）"""
        goal_text = random.choice(self.FALLBACK_GOALS)
        
        goal_id = hashlib.md5(f"{self.agent_id}:{goal_text}:{self._goals_generated}".encode()).hexdigest()[:16]
        
        return {
            "id": goal_id,
            "type": "intrinsic",
            "description": goal_text,
            "motivation": "heuristic",
            "confidence": 0.5,
            "source": "fallback",
        }
    
    def purpose_to_goal(self, purpose: dict) -> Any:
        """将目的转换为 Goal 对象"""
        # 尝试导入 Goal
        try:
            from usmsb_sdk.core.elements import Goal, GoalStatus
            
            return Goal(
                id=purpose.get("id", ""),
                name=purpose.get("description", ""),
                description=purpose.get("description", ""),
                priority=50,
                status=GoalStatus.PENDING,
                metadata={
                    "purpose_type": purpose.get("type"),
                    "motivation": purpose.get("motivation"),
                    "confidence": purpose.get("confidence"),
                    "source": purpose.get("source", "unknown"),
                    "is_intrinsic": True,
                }
            )
        except ImportError:
            # 回退：返回字典
            return type('Goal', (), {
                'id': purpose.get("id", ""),
                'name': purpose.get("description", ""),
                'metadata': purpose.get,
            })()
    
    def get_statistics(self) -> dict:
        """获取统计"""
        return {
            "goals_generated": self._goals_generated,
            "llm_failures": self._llm_failures,
            "llm_success_rate": (
                (self._goals_generated - self._llm_failures) / self._goals_generated
                if self._goals_generated > 0 else 0
            ),
        }
    
    def __repr__(self) -> str:
        return f"PurposeGenerator(agent={self.agent_id}, llm={self.llm})"
