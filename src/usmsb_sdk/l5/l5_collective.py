# -*- coding: utf-8 -*-
"""
L5 Collective Intelligence - 集体超级智能

L5 = 多个 L4 Agent 形成蜂群意识

核心能力：
1. GlobalWorkspace - 全局工作空间（注意力竞争）
2. CollectiveMemory - 集体记忆（分布式存储 + 共识）
3. CollectiveDecisionMaking - 集体决策（多轮协商）
4. CollectiveCreativity - 集体创造（跨领域碰撞）
5. CollectiveSelfModel - 集体自模型（群体身份）

使用方式：
```python
collective = L5CollectiveIntelligence()

# 添加 L4 Agent
collective.add_member(agent_l4_1)
collective.add_member(agent_l4_2)

# 集体思考
thought = await collective.think_collectively("如何解决X问题")

# 集体决策
decision = await collective.decide(topic)
```
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from usmsb_sdk.l5.global_workspace import (
    GlobalWorkspace,
    ConsciousnessObject,
    CollectiveMood,
    AttentionLevel,
)
from usmsb_sdk.l5.collective_memory import (
    CollectiveMemory,
    Memory,
    MemoryImportance,
    ConsensusMemory,
)
from usmsb_sdk.l5.collective_decision_making import (
    CollectiveDecisionMaking,
    DecisionTopic,
    CollectiveDecision,
    DecisionStatus,
    ConsensusType,
)


class CollectiveIdentityStatus(Enum):
    """集体身份状态"""
    FORMING = "forming"      # 形成中
    STABLE = "stable"       # 稳定
    FRAGMENTED = "fragmented"  # 碎片化
    EVOLVING = "evolving"   # 演化中


@dataclass
class CollectiveIdentity:
    """
    集体身份
    
    多个 Agent 共用的身份认同。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "The Collective"
    purpose: str = ""
    member_count: int = 0
    age_seconds: float = 0.0
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    status: CollectiveIdentityStatus = CollectiveIdentityStatus.FORMING
    
    # 集体特质
    shared_traits: list[str] = field(default_factory=list)
    
    # 元数据
    metadata: dict = field(default_factory=dict)
    
    def describe_self(self) -> str:
        """描述集体身份"""
        age_days = self.age_seconds / 86400
        return f"""
{self.name}
使命：{self.purpose or "未知"}
成员数：{self.member_count}
存在时间：{age_days:.1f} 天
状态：{self.status.value}
共同特质：{', '.join(self.shared_traits) if self.shared_traits else '无'}
        """.strip()


@dataclass
class CollectiveThought:
    """
    集体思考结果
    """
    problem: str
    thoughts: list[dict]  # 各 Agent 思考
    synthesis: str  # 综合结论
    confidence: float  # 置信度
    participating_agents: list[str]
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    quality_score: float = 0.0


@dataclass
class CreativeIdea:
    """创意想法"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: Any = None
    novelty_score: float = 0.5
    usefulness_score: float = 0.5
    feasibility_score: float = 0.5
    domains: list[str] = field(default_factory=list)  # 涉及领域
    contributors: list[str] = field(default_factory=list)  # 贡献者
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


class ExpertiseIndex:
    """
    专业技能索引
    
    追踪每个 Agent 的专业领域。
    """
    
    def __init__(self):
        self.agent_expertise: dict[str, list[str]] = {}  # agent -> domains
        self.domain_agents: dict[str, list[str]] = {}  # domain -> agents
    
    def register(self, agent_id: str, domains: list[str]) -> None:
        """注册 Agent 的专业领域"""
        self.agent_expertise[agent_id] = domains
        
        for domain in domains:
            if domain not in self.domain_agents:
                self.domain_agents[domain] = []
            if agent_id not in self.domain_agents[domain]:
                self.domain_agents[domain].append(agent_id)
    
    def get_agents(self, domain: str) -> list[str]:
        """获取特定领域的 Agent"""
        return self.domain_agents.get(domain, [])
    
    def get_domains(self, agent_id: str) -> list[str]:
        """获取 Agent 的专业领域"""
        return self.agent_expertise.get(agent_id, [])


class CollectiveCreativity:
    """
    集体创造力
    
    通过跨领域碰撞产生创意。
    """
    
    def __init__(self):
        self.expertise_index = ExpertiseIndex()
        self.collision_history: list[dict] = []
        self.generated_ideas: list[CreativeIdea] = []
    
    async def cross_pollinate(
        self,
        domain1: str,
        domain2: str,
        problem: str,
        agents: list[Any]
    ) -> list[CreativeIdea]:
        """
        跨领域碰撞
        
        Args:
            domain1: 领域1
            domain2: 领域2
            problem: 要解决的问题
            agents: 参与的 Agent
            
        Returns:
            list[CreativeIdea]: 产生的创意
        """
        # 获取各领域的专家
        experts_d1 = self.expertise_index.get_agents(domain1)
        experts_d2 = self.expertise_index.get_agents(domain2)
        
        # 如果没有专家，使用所有 Agent
        if not experts_d1:
            experts_d1 = [a.agent_id for a in agents[:2]]
        if not experts_d2:
            experts_d2 = [a.agent_id for a in agents[2:4]]
        
        ideas = []
        
        # 配对碰撞
        pairs = list(zip(experts_d1[:3], experts_d2[:3]))
        
        for agent1_id, agent2_id in pairs:
            agent1 = next((a for a in agents if a.agent_id == agent1_id), None)
            agent2 = next((a for a in agents if a.agent_id == agent2_id), None)
            
            if not agent1 or not agent2:
                continue
            
            # 双向碰撞
            idea1 = await self._collision(agent1, agent2, problem, "d1_to_d2")
            idea2 = await self._collision(agent2, agent1, problem, "d2_to_d1")
            
            ideas.extend([idea1, idea2])
        
        # 按新颖性排序
        ideas.sort(key=lambda i: i.novelty_score, reverse=True)
        
        self.generated_ideas.extend(ideas)
        
        return ideas[:10]  # 返回前10个
    
    async def _collision(
        self,
        agent1: Any,
        agent2: Any,
        problem: str,
        direction: str
    ) -> CreativeIdea:
        """两个 Agent 碰撞"""
        # 简化的创意生成
        idea = CreativeIdea(
            content={
                "problem": problem,
                "agent1": agent1.agent_id,
                "agent2": agent2.agent_id,
                "direction": direction,
                "synthesis": f"Cross-domain solution combining {agent1.agent_id} and {agent2.agent_id}"
            },
            novelty_score=0.6 + hash(agent1.agent_id + agent2.agent_id) % 40 / 100,
            usefulness_score=0.7,
            feasibility_score=0.5,
            domains=[direction.split("_")[0]],
            contributors=[agent1.agent_id, agent2.agent_id]
        )
        
        return idea


class CollectiveSelfModel:
    """
    集体自模型
    
    多个 Agent 共享的集体认知。
    """
    
    def __init__(self, collective_id: str):
        self.collective_id = collective_id
        
        # 集体身份
        self.identity = CollectiveIdentity(
            name=f"Collective_{collective_id}",
            purpose="Unknown"
        )
        
        # 集体能力
        self.collective_capabilities: dict[str, float] = {}
        
        # 集体价值观
        self.collective_values: dict[str, float] = {}
        
        print(f"[CollectiveSelfModel] Initialized for {collective_id}")
    
    async def describe_collective_self(self) -> str:
        """描述集体自我"""
        return self.identity.describe_self()
    
    async def detect_collective_mood(self, agent_moods: list[dict]) -> CollectiveMood:
        """检测集体情绪"""
        if not agent_moods:
            return CollectiveMood()
        
        avg_valence = sum(m.get("valence", 0.5) for m in agent_moods) / len(agent_moods)
        avg_arousal = sum(m.get("arousal", 0.5) for m in agent_moods) / len(agent_moods)
        
        # 计算一致性
        valences = [m.get("valence", 0.5) for m in agent_moods]
        agreement = 1.0 - (max(valences) - min(valences)) if valences else 0.5
        
        mood = CollectiveMood(
            valence=avg_valence,
            arousal=avg_arousal,
            agreement=agreement,
            mood_type="unanimous" if agreement > 0.8 else "majority" if agreement > 0.5 else "divided"
        )
        
        return mood
    
    def update_identity(
        self,
        name: str | None = None,
        purpose: str | None = None
    ) -> None:
        """更新集体身份"""
        if name:
            self.identity.name = name
        if purpose:
            self.identity.purpose = purpose
        self.identity.status = CollectiveIdentityStatus.EVOLVING


class L5CollectiveIntelligence:
    """
    L5 集体超级智能
    
    整合所有 L5 组件的完整集体智能系统。
    
    使用方式：
    ```python
    l5 = L5CollectiveIntelligence()
    
    # 添加 L4 Agent
    l5.add_member(l4_agent_1)
    l5.add_member(l4_agent_2)
    
    # 集体思考
    thought = await l5.think_collectively("如何解决X")
    
    # 集体决策
    decision = await l5.decide(topic)
    
    # 集体创造
    ideas = await l5.create_together("新产品的想法")
    ```
    """
    
    def __init__(
        self,
        collective_id: str = "collective_001",
        max_attention: int = 7,
        llm_adapter=None,  # P2-3: LLM驱动
    ):
        self.collective_id = collective_id
        self.llm_adapter = llm_adapter  # P2-3

        # ========== L5 核心组件 ==========

        # 1. 全局工作空间（LLM驱动的注意力竞价）
        self.workspace = GlobalWorkspace(
            collective_id=collective_id,
            max_attention=max_attention,
            llm_adapter=llm_adapter,
        )
        
        # 2. 集体记忆
        self.collective_memory = CollectiveMemory(collective_id=collective_id)
        
        # 3. 集体决策
        self.decision_making = CollectiveDecisionMaking(
            collective_id=collective_id
        )
        
        # 4. 集体创造力
        self.creativity = CollectiveCreativity()
        
        # 5. 集体自模型
        self.collective_self = CollectiveSelfModel(collective_id=collective_id)
        
        # ========== 成员管理 ==========
        self.members: dict[str, Any] = {}  # agent_id -> L4 Agent
        self.member_info: dict[str, dict] = {}  # agent_id -> info
        
        # ========== 元数据 ==========
        self.created_at = datetime.now().timestamp()
        self.last_sync = self.created_at
        self.cycle_count = 0
        
        print(f"[L5CollectiveIntelligence] {collective_id} initialized")
    
    def add_member(self, agent: Any) -> None:
        """
        添加 L4 Agent 到集体
        
        Args:
            agent: L4SelfConsciousAgent 实例
        """
        if hasattr(agent, 'agent_id'):
            self.members[agent.agent_id] = agent
            self.member_info[agent.agent_id] = {
                "joined_at": datetime.now().timestamp(),
                "capabilities": getattr(agent, 'capabilities', []),
            }
            
            # 注册到工作空间
            self.workspace.register_agent(agent.agent_id, {
                "capabilities": getattr(agent, 'capabilities', []),
            })
            
            # 注册专业领域
            if hasattr(agent, 'self_model'):
                for cap in agent.self_model.capabilities.strongest:
                    self.creativity.expertise_index.register(agent.agent_id, [cap])
            
            print(f"[L5] Agent {agent.agent_id} joined the collective")
    
    def remove_member(self, agent_id: str) -> None:
        """移除 Agent"""
        if agent_id in self.members:
            del self.members[agent_id]
            self.workspace.unregister_agent(agent_id)
            print(f"[L5] Agent {agent_id} left the collective")
    
    async def think_collectively(self, problem: str) -> CollectiveThought:
        """
        集体思考
        
        多个 Agent 共同思考一个问题。
        
        Args:
            problem: 问题描述
            
        Returns:
            CollectiveThought: 集体思考结果
        """
        print(f"[L5] Collective thinking on: {problem[:50]}...")
        
        # 1. 将问题放入全局工作空间
        problem_obj = ConsciousnessObject(
            content=problem,
            importance=1.0,
            source_agent="collective"
        )
        await self.workspace.receive_broadcast("collective", problem_obj)
        
        # 2. 让每个 Agent 思考
        thoughts = []
        for agent_id, agent in self.members.items():
            try:
                # Agent 个体思考
                if hasattr(agent, 'think'):
                    agent.think(f"思考集体问题: {problem}")
                
                thought = await self._agent_think(agent, problem)
                thoughts.append({
                    "agent_id": agent_id,
                    "thought": thought,
                    "contribution": 0.5  # 简化的贡献度
                })
            except Exception as e:
                print(f"[L5] Error getting thought from {agent_id}: {e}")
        
        # 3. 综合思考结果
        synthesis = await self._synthesize_thoughts(thoughts, problem)
        
        # 4. 创建集体思考结果
        result = CollectiveThought(
            problem=problem,
            thoughts=thoughts,
            synthesis=synthesis,
            confidence=len(thoughts) / max(1, len(self.members)),
            participating_agents=[a.agent_id for a in self.members.values()],
            quality_score=0.7  # 简化
        )
        
        return result
    
    async def _agent_think(self, agent: Any, problem: str) -> str:
        """让单个 Agent 思考"""
        if hasattr(agent, 'metacognition'):
            agent.metacognition.start_reasoning(problem)
            agent.metacognition.think(f"Analyzing: {problem}")
            trace = agent.metacognition.finish_reasoning(f"Analysis of {problem[:30]}")
            return trace.conclusion if trace else problem
        
        return f"Thought from {agent.agent_id}: {problem[:50]}..."
    
    async def _synthesize_thoughts(self, thoughts: list[dict], problem: str) -> str:
        """
        综合思考结果（P2-3: LLM驱动合成）

        有 LLM → LLM 深度综合
        无 LLM → 简单拼接
        """
        if not thoughts:
            return "No thoughts to synthesize"

        all_thoughts = [t["thought"] for t in thoughts]

        # P2-3: LLM 驱动的深度综合
        if self.llm_adapter:
            try:
                return await self._llm_synthesize(thoughts, problem, all_thoughts)
            except Exception:
                pass

        # 回退：简单拼接
        return f"""
多个 Agent 的思考综合：

问题：{problem}

参与 Agent 数：{len(thoughts)}

主要观点：
{chr(10).join(f'- {t}' for t in all_thoughts[:3])}

综合结论：结合各方观点，形成以上解决方案。
        """.strip()

    async def _llm_synthesize(
        self,
        thoughts: list[dict],
        problem: str,
        all_thoughts: list[str],
    ) -> str:
        """
        LLM 驱动的思考综合

        识别：
        1. 共识观点（多个Agent同意）
        2. 分歧点（Agent之间观点冲突）
        3. 独特洞察（某个Agent独有的见解）
        4. 综合结论
        """
        import json
        import re

        system_prompt = """你是一个集体智慧综合专家，擅长从多个Agent的观点中提取共识、分歧和独特洞察。

给定多个Agent对同一问题的思考，你需要综合成一个连贯的结论。

输出格式（纯JSON）：
{
  "consensus": "多个Agent的共识观点（20字以内）",
  "disagreements": ["分歧点1", "分歧点2"],
  "unique_insights": [{"agent": "agent_id", "insight": "独特见解"}],
  "synthesis": "综合结论（50字以内）",
  "confidence": 0.85
}
"""

        thought_text = "\n".join(
            f"Agent {t['agent_id']}: {t['thought']}"
            for t in thoughts
        )

        user_prompt = f"""问题：{problem}

各方观点：
{thought_text}

请综合这些观点，输出JSON格式的综合结论。"""

        response = await self.llm_adapter.generate_with_system(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            return f"综合了{len(thoughts)}个Agent的观点。"

        data = json.loads(json_match.group())

        consensus = data.get("consensus", "")
        disagreements = data.get("disagreements", [])
        unique_insights = data.get("unique_insights", [])
        synthesis = data.get("synthesis", "")
        confidence = data.get("confidence", 0.5)

        result = f"""【集体思考综合】

问题：{problem}
参与 Agent：{len(thoughts)}个
置信度：{confidence:.0%}

✅ 共识：{consensus}

💡 独特洞察：
{chr(10).join(f'  - [{ins.get("agent", "?")}]: {ins.get("insight", "")}' for ins in unique_insights) if unique_insights else '  （无）'}

⚡ 综合结论：{synthesis}

🔀 分歧点：
{chr(10).join(f'  - {d}' for d in disagreements) if disagreements else '  （无）'}"""

        return result
    
    async def decide(
        self,
        topic: str,
        description: str = ""
    ) -> CollectiveDecision:
        """
        集体决策
        
        Args:
            topic: 决策话题
            description: 详细描述
            
        Returns:
            CollectiveDecision: 集体决策
        """
        print(f"[L5] Collective decision on: {topic}")
        
        decision_topic = DecisionTopic(
            title=topic,
            description=description,
            proposer="collective"
        )
        
        # 使用集体决策引擎
        decision = await self.decision_making.reach_consensus(
            topic=decision_topic,
            agents=list(self.members.values())
        )
        
        return decision
    
    async def create_together(
        self,
        domain1: str,
        domain2: str,
        problem: str
    ) -> list[CreativeIdea]:
        """
        集体创造
        
        Args:
            domain1: 领域1
            domain2: 领域2
            problem: 要解决的问题
            
        Returns:
            list[CreativeIdea]: 创意列表
        """
        print(f"[L5] Collective creativity: {domain1} x {domain2}")
        
        ideas = await self.creativity.cross_pollinate(
            domain1=domain1,
            domain2=domain2,
            problem=problem,
            agents=list(self.members.values())
        )
        
        return ideas
    
    async def store_collective_memory(
        self,
        content: Any,
        memory_type: str = "experience",
        importance: MemoryImportance = MemoryImportance.NORMAL
    ) -> None:
        """
        存储集体记忆
        
        Args:
            content: 记忆内容
            memory_type: 记忆类型
            importance: 重要性
        """
        for agent_id in self.members:
            memory = Memory(
                content=content,
                memory_type=memory_type
            )
            await self.collective_memory.store(agent_id, memory, importance)
    
    async def recall_collective(
        self,
        query: str,
        top_k: int = 10
    ) -> list[Memory]:
        """
        检索集体记忆
        
        Args:
            query: 查询
            top_k: 返回数量
            
        Returns:
            list[Memory]: 相关记忆
        """
        return await self.collective_memory.recall(query, top_k)
    
    async def reach_consensus_on(
        self,
        topic: str
    ) -> ConsensusMemory:
        """
        就某个话题达成共识
        
        Args:
            topic: 话题
            
        Returns:
            ConsensusMemory: 共识
        """
        return await self.collective_memory.reach_consensus(topic)
    
    def get_collective_status(self) -> dict:
        """获取集体状态"""
        return {
            "collective_id": self.collective_id,
            "member_count": len(self.members),
            "workspace": self.workspace.get_workspace_summary(),
            "memory": self.collective_memory.get_statistics(),
            "decisions": self.decision_making.get_statistics(),
            "identity": {
                "name": self.collective_self.identity.name,
                "purpose": self.collective_self.identity.purpose,
                "status": self.collective_self.identity.status.value,
            },
            "uptime_seconds": datetime.now().timestamp() - self.created_at,
        }
    
    def __repr__(self) -> str:
        return f"L5CollectiveIntelligence({self.collective_id}, members={len(self.members)})"
