# -*- coding: utf-8 -*-
"""
L5 Prototype - 5-10 Agent 蜂群 Demo

演示 L5 集体智能的完整场景：
1. 创建多个专业 Agent
2. 加入同一个集体
3. 解决复杂问题
4. 展示集体智慧

使用方式：
```python
from usmsb_sdk.l5.prototype import run_l5_prototype

# 运行完整 demo
results = asyncio.run(run_l5_prototype())

# 或者分步骤运行
from usmsb_sdk.l5.prototype import L5PrototypeDemo
demo = L5PrototypeDemo()
await demo.setup()
result = await demo.run_collective_task("设计一个聊天机器人")
```
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from usmsb_sdk.l4 import L4SelfConsciousAgent
from usmsb_sdk.l5 import (
    L5CollectiveIntelligence,
    ConsciousnessObject,
    Memory,
    MemoryImportance,
)


@dataclass
class DemoConfig:
    """Demo 配置"""
    agent_count: int = 5
    problem_topic: str = "如何设计一个 AI 助手"
    enable_logging: bool = True


@dataclass
class DemoResult:
    """Demo 结果"""
    success: bool
    problem: str
    solution: str
    agents_participated: list[str]
    thinking_rounds: int
    consensus_reached: bool
    collective_wisdom_score: float
    duration_seconds: float
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


class L5PrototypeDemo:
    """
    L5 原型 Demo
    
    演示多个 L4 Agent 如何通过 L5 集体智能协作解决复杂问题。
    
    Agent 角色：
    1. Athena - 战略分析师（擅长规划）
    2. Zeus - 技术架构师（擅长系统设计）
    3. Apollo - 创意设计师（擅长创新）
    4. Artemis - 质量保障师（擅长测试）
    5. Hermes - 沟通协调者（擅长协作）
    """
    
    def __init__(self, config: DemoConfig | None = None):
        self.config = config or DemoConfig()
        self.collective: L5CollectiveIntelligence | None = None
        self.agents: list[L4SelfConsciousAgent] = []
        self.start_time: float = 0.0
        self.end_time: float = 0.0
    
    async def setup(self) -> None:
        """设置 Demo"""
        print("=" * 60)
        print("L5 Collective Intelligence Demo - Setting Up")
        print("=" * 60)
        
        # 创建 L5 集体
        self.collective = L5CollectiveIntelligence(
            collective_id="demo_collective",
            max_attention=7
        )
        
        # 创建 Agent
        agent_configs = [
            ("Athena", "战略分析师", ["planning", "strategy", "analysis"]),
            ("Zeus", "技术架构师", ["architecture", "system_design", "coding"]),
            ("Apollo", "创意设计师", ["creativity", "design", "innovation"]),
            ("Artemis", "质量保障师", ["testing", "qa", "problem_finding"]),
            ("Hermes", "沟通协调者", ["communication", "coordination", "negotiation"]),
        ]
        
        for name, role, capabilities in agent_configs[:self.config.agent_count]:
            agent = L4SelfConsciousAgent(
                agent_id=f"agent_{name.lower()}",
                name=name,
                core_purpose=f"成为最好的{role}"
            )
            
            # 添加能力到 L4 自模型
            for cap in capabilities:
                agent.self_model.capabilities.add_capability(cap, 0.7)
            
            self.agents.append(agent)
            
            # 添加到集体
            self.collective.add_member(agent)
            
            print(f"  Created {name} ({role})")
        
        print(f"\n  Total agents: {len(self.agents)}")
        print(f"  Collective: {self.collective}")
    
    async def phase1_individual_thinking(self) -> dict:
        """第一阶段：各 Agent 独立思考"""
        print("\n" + "=" * 60)
        print("Phase 1: Individual Thinking")
        print("=" * 60)
        
        thoughts = {}
        
        for agent in self.agents:
            # Agent 独立思考问题
            agent.think(f"我作为{agent.self_model.identity.name}，思考：{self.config.problem_topic}")
            
            # 生成自己的想法
            thought = f"{agent.self_model.identity.name}的观点："
            thought += f"\n  - 核心问题：如何构建 AI 助手"
            thought += f"\n  - 关键能力：自然语言理解、推理、记忆"
            thought += f"\n  - 技术方案：LLM + RAG + Agent"
            
            thoughts[agent.agent_id] = thought
            
            print(f"\n  [{agent.self_model.identity.name}]")
            print(f"  {thought[:100]}...")
        
        return thoughts
    
    async def phase2_collective_discussion(self) -> dict:
        """第二阶段：集体讨论"""
        print("\n" + "=" * 60)
        print("Phase 2: Collective Discussion via Global Workspace")
        print("=" * 60)
        
        # 将想法放入全局工作空间
        for agent_id, thought in self.agents[0].items() if hasattr(self.agents[0], 'items') else []:
            pass
        
        # 使用集体思考
        collective_thought = await self.collective.think_collectively(
            f"{self.config.problem_topic}的解决方案"
        )
        
        print(f"\n  Collective thoughts from {len(collective_thought.thoughts)} agents:")
        for thought_data in collective_thought.thoughts:
            print(f"\n  [{thought_data['agent_id']}]")
            print(f"    {thought_data['thought'][:80]}...")
        
        return {
            "synthesis": collective_thought.synthesis,
            "confidence": collective_thought.confidence,
            "thoughts": len(collective_thought.thoughts)
        }
    
    async def phase3_collective_decision(self) -> dict:
        """第三阶段：集体决策"""
        print("\n" + "=" * 60)
        print("Phase 3: Collective Decision Making")
        print("=" * 60)
        
        # 使用 L5 集体决策
        decision = await self.collective.decide(
            topic="最终技术方案",
            description=f"从{self.config.problem_topic}的各种方案中选择最佳"
        )
        
        print(f"\n  Decision reached!")
        print(f"  Support rate: {decision.support_rate:.1%}")
        print(f"  Consensus type: {decision.consensus_type.value}")
        print(f"  Rounds needed: {decision.rounds_needed}")
        print(f"  Proposal: {decision.proposal.content}")
        
        return {
            "support_rate": decision.support_rate,
            "consensus_type": decision.consensus_type.value,
            "rounds": decision.rounds_needed,
            "proposal": decision.proposal.content
        }
    
    async def phase4_knowledge_sharing(self) -> None:
        """第四阶段：知识共享"""
        print("\n" + "=" * 60)
        print("Phase 4: Knowledge Sharing")
        print("=" * 60)
        
        # 存储集体记忆
        insights = [
            ("AI助手需要持续学习", "engineering"),
            ("用户体验最重要", "design"),
            ("安全性是关键", "security"),
            ("可扩展性设计", "architecture"),
        ]
        
        for insight, category in insights:
            await self.collective.store_collective_memory(
                content={
                    "insight": insight,
                    "category": category,
                    "contributor": self.agents[0].agent_id
                },
                memory_type="insight",
                importance=MemoryImportance.HIGH
            )
        
        print(f"\n  Stored {len(insights)} insights in collective memory")
        
        # 检索记忆
        recalled = await self.collective.recall_collective("AI助手")
        print(f"\n  Retrieved {len(recalled)} relevant memories")
    
    async def phase5_creative_synthesis(self) -> str:
        """第五阶段：创造性综合"""
        print("\n" + "=" * 60)
        print("Phase 5: Creative Synthesis")
        print("=" * 60)
        
        # 使用集体创造力
        ideas = await self.collective.create_together(
            domain1="AI",
            domain2="Design",
            problem=self.config.problem_topic
        )
        
        print(f"\n  Generated {len(ideas)} creative ideas:")
        for i, idea in enumerate(ideas[:3], 1):
            print(f"\n  Idea {i}:")
            print(f"    Novelty: {idea.novelty_score:.1%}")
            print(f"    Usefulness: {idea.usefulness_score:.1%}")
            print(f"    Content: {idea.content}")
        
        # 选择最佳创意
        best = ideas[0] if ideas else None
        if best:
            synthesis = f"""
=== L5 集体智慧合成方案 ===

基于 {len(self.agents)} 个专业 Agent 的协作思考：

核心洞察：
- 创新性：{best.novelty_score:.0%}
- 实用性：{best.usefulness_score:.0%}
- 可行性：{best.feasibility_score:.0%}

方案内容：
{best.content}

贡献者：{', '.join(best.contributors)}
            """.strip()
        else:
            synthesis = "未能生成有效方案"
        
        print(f"\n  Final synthesis:\n{synthesis[:200]}...")
        
        return synthesis
    
    async def run(self) -> DemoResult:
        """运行完整 Demo"""
        self.start_time = datetime.now().timestamp()
        
        try:
            # Setup
            await self.setup()
            
            # Phase 1: Individual thinking
            thoughts = await self.phase1_individual_thinking()
            
            # Phase 2: Collective discussion
            discussion = await self.phase2_collective_discussion()
            
            # Phase 3: Decision
            decision = await self.phase3_collective_decision()
            
            # Phase 4: Knowledge sharing
            await self.phase4_knowledge_sharing()
            
            # Phase 5: Creative synthesis
            solution = await self.phase5_creative_synthesis()
            
            # Calculate metrics
            self.end_time = datetime.now().timestamp()
            duration = self.end_time - self.start_time
            
            # Calculate collective wisdom score
            wisdom_score = (
                discussion.get("confidence", 0.5) * 0.3 +
                decision.get("support_rate", 0.5) * 0.4 +
                len(self.agents) / 10 * 0.3
            )
            
            result = DemoResult(
                success=True,
                problem=self.config.problem_topic,
                solution=solution,
                agents_participated=[a.agent_id for a in self.agents],
                thinking_rounds=decision.get("rounds", 3),
                consensus_reached=decision.get("support_rate", 0) > 0.6,
                collective_wisdom_score=wisdom_score,
                duration_seconds=duration
            )
            
            # Print summary
            print("\n" + "=" * 60)
            print("DEMO COMPLETE - Summary")
            print("=" * 60)
            print(f"\n  Problem: {result.problem}")
            print(f"  Solution generated: {result.success}")
            print(f"  Agents participated: {len(result.agents_participated)}")
            print(f"  Consensus reached: {result.consensus_reached}")
            print(f"  Collective wisdom score: {result.collective_wisdom_score:.1%}")
            print(f"  Duration: {result.duration_seconds:.1f}s")
            
            return result
        
        except Exception as e:
            print(f"\n  Demo failed: {e}")
            import traceback
            traceback.print_exc()
            
            return DemoResult(
                success=False,
                problem=self.config.problem_topic,
                solution=f"Error: {e}",
                agents_participated=[],
                thinking_rounds=0,
                consensus_reached=False,
                collective_wisdom_score=0.0,
                duration_seconds=0.0
            )


async def run_l5_prototype(
    agent_count: int = 5,
    problem: str = "如何设计一个 AI 助手"
) -> DemoResult:
    """
    运行 L5 原型 Demo
    
    Args:
        agent_count: Agent 数量
        problem: 要解决的问题
        
    Returns:
        DemoResult
    """
    config = DemoConfig(
        agent_count=agent_count,
        problem_topic=problem
    )
    
    demo = L5PrototypeDemo(config)
    result = await demo.run()
    
    return result


async def run_quick_demo() -> None:
    """运行快速 Demo（简化版）"""
    print("\n" + "=" * 60)
    print("L5 Quick Demo - 3 Agents solving a problem")
    print("=" * 60 + "\n")
    
    # 创建 3 个简单 Agent
    agents = [
        L4SelfConsciousAgent(f"quick_{i}", name=f"Agent-{i}")
        for i in range(3)
    ]
    
    # 创建集体
    collective = L5CollectiveIntelligence("quick_demo")
    
    # 添加成员
    for agent in agents:
        collective.add_member(agent)
    
    # 集体思考
    thought = await collective.think_collectively("如何让聊天机器人更有用")
    
    print(f"\n  Collective thinking completed!")
    print(f"  {len(thought.thoughts)} agents contributed")
    print(f"  Synthesis: {thought.synthesis[:100]}...")
    
    # 集体决策
    decision = await collective.decide("最佳对话策略")
    
    print(f"\n  Decision made!")
    print(f"  Support: {decision.support_rate:.0%}")
    print(f"  {decision.consensus_type.value}")
    
    print("\n" + "=" * 60)
    print("Quick Demo Complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # 运行快速 demo
    asyncio.run(run_quick_demo())
