# -*- coding: utf-8 -*-
"""
Phase 1: USMSB Core Services 示例

展示核心服务的功能。

运行方式：
    python examples/phase1_core_services_demo.py
"""

import sys
sys.path.insert(0, 'src')

from usmsb_sdk.core_services import (
    AgentRegistry,
    AgentProfile,
    AgentStatus,
    AgentType,
    GeneCapsuleManager,
    MatchingEngine,
    Task,
    NegotiationHub,
    NegotiationTerm,
    OrderManager,
    OrderStatus,
    ReputationService,
    ReviewRating,
)


def demo_agent_registry():
    """Agent 注册演示"""
    print("=" * 60)
    print("Agent Registry 演示")
    print("=" * 60)
    
    registry = AgentRegistry()
    
    # 注册 Agent
    print("\n[注册 Agent]")
    agent1 = AgentProfile(
        id="agent_coder",
        name="Coding Agent",
        description="专业代码开发",
        agent_type=AgentType.SPECIALIST,
        capabilities=["coding", "refactoring", "testing"],
        skills=["Python", "JavaScript"],
        reputation=0.85,
        hourly_rate=50.0,
        wallet_address="0x123..."
    )
    registry.register(agent1)
    print(f"  注册: {agent1.name}")
    
    agent2 = AgentProfile(
        id="agent_designer",
        name="Design Agent",
        description="专业UI/UX设计",
        agent_type=AgentType.SPECIALIST,
        capabilities=["design", "ui", "ux"],
        skills=["Figma", "Sketch"],
        reputation=0.90,
        hourly_rate=40.0,
        wallet_address="0x456..."
    )
    registry.register(agent2)
    print(f"  注册: {agent2.name}")
    
    # 更新状态
    print("\n[更新状态]")
    registry.update_status("agent_coder", AgentStatus.ONLINE)
    registry.update_status("agent_designer", AgentStatus.ONLINE)
    print("  Agent 上线")
    
    # 发现 Agent
    print("\n[发现 Agent - 搜索 'coding' 能力]")
    agents = registry.discover(capabilities=["coding"], min_reputation=0.5)
    for agent in agents:
        print(f"  - {agent.name}: {agent.capabilities}")
    
    # 统计
    print("\n[统计]")
    stats = registry.get_statistics()
    print(f"  总 Agent: {stats['total_agents']}")
    print(f"  在线: {stats['by_status'].get('online', 0)}")


def demo_gene_capsule():
    """Gene Capsule 演示"""
    print("\n" + "=" * 60)
    print("Gene Capsule Manager 演示")
    print("=" * 60)
    
    manager = GeneCapsuleManager()
    
    # 创建胶囊
    print("\n[创建基因胶囊]")
    capsule1_id = manager.create_capsule(
        agent_id="agent_coder",
        category="capability",
        content={"skill": "python", "level": 5, "projects": 20},
        quality_score=0.9,
        keywords=["python", "coding", "backend"]
    )
    print(f"  创建胶囊: {capsule1_id[:20]}...")
    
    capsule2_id = manager.create_capsule(
        agent_id="agent_designer",
        category="capability",
        content={"skill": "ui_design", "level": 4, "projects": 15},
        quality_score=0.85,
        keywords=["design", "ui", "figma"]
    )
    print(f"  创建胶囊: {capsule2_id[:20]}...")
    
    # 获取胶囊
    print("\n[获取胶囊]")
    capsule = manager.get_capsule(capsule1_id)
    if capsule:
        print(f"  胶囊内容: {capsule.content}")
    
    # 搜索胶囊
    print("\n[搜索胶囊 - 'python']")
    results = manager.find_similar("python", top_k=5)
    print(f"  找到 {len(results)} 个相关胶囊")


def demo_matching_engine():
    """匹配引擎演示"""
    print("\n" + "=" * 60)
    print("Matching Engine 演示")
    print("=" * 60)
    
    registry = AgentRegistry()
    
    # 注册一些 Agent
    agents = [
        AgentProfile(id=f"agent_{i}", name=f"Agent {i}", description="",
                   capabilities=["coding", "analysis"] if i % 2 == 0 else ["design", "creative"],
                   reputation=0.5 + i * 0.1)
        for i in range(5)
    ]
    for agent in agents:
        registry.register(agent)
    
    engine = MatchingEngine()
    
    # 创建任务
    print("\n[创建任务]")
    task = Task(
        id="task_001",
        title="数据分析项目",
        description="需要分析销售数据",
        required_capabilities=["coding", "analysis"],
        budget=100.0,
        priority=70
    )
    print(f"  任务: {task.title}")
    print(f"  所需能力: {task.required_capabilities}")
    
    # 执行匹配
    print("\n[执行匹配]")
    matches = engine.match(task, agents, top_k=3)
    for match in matches:
        agent = registry.get_agent(match.agent_id)
        print(f"  - {agent.name}: 分数={match.score:.1f}")
        print(f"    原因: {match.reason}")


def demo_negotiation_hub():
    """谈判中心演示"""
    print("\n" + "=" * 60)
    print("Negotiation Hub 演示")
    print("=" * 60)
    
    hub = NegotiationHub()
    
    # 发起谈判
    print("\n[发起谈判]")
    terms = [
        NegotiationTerm(type="price", value=100, description="服务价格"),
        NegotiationTerm(type="timeline", value="3 days", description="交付时间"),
    ]
    neg_id = hub.start_negotiation(
        task_id="task_001",
        buyer_id="buyer_agent",
        seller_id="seller_agent",
        initial_terms=terms
    )
    print(f"  谈判 ID: {neg_id[:20]}...")
    print(f"  初始条款: price={terms[0].value}, timeline={terms[1].value}")
    
    # 还价
    print("\n[还价]")
    counter_terms = [
        NegotiationTerm(type="price", value=90, description="降低价格"),
        NegotiationTerm(type="timeline", value="2 days", description="缩短时间"),
    ]
    hub.counter(neg_id, counter_terms, "seller_agent")
    neg = hub.get_negotiation(neg_id)
    print(f"  当前轮次: {neg.current_round}")
    print(f"  状态: {neg.status.value}")
    
    # 接受
    print("\n[接受谈判]")
    contract = hub.accept(neg_id, "buyer_agent")
    if contract:
        print(f"  合约 ID: {contract.id[:20]}...")
        print(f"  总价格: {contract.total_price} {contract.currency}")


def demo_order_manager():
    """订单管理演示"""
    print("\n" + "=" * 60)
    print("Order Manager 演示")
    print("=" * 60)
    
    manager = OrderManager()
    
    # 创建订单
    print("\n[创建订单]")
    order = manager.create_order(
        task_id="task_001",
        buyer_id="buyer_agent",
        seller_id="seller_agent",
        title="数据分析项目",
        description="分析销售数据并生成报告",
        price=100.0,
        currency="VIBE"
    )
    print(f"  订单 ID: {order.id[:20]}...")
    print(f"  状态: {order.status.value}")
    
    # 状态流转
    print("\n[状态流转]")
    manager.accept_order(order.id)
    print(f"  接受: {manager.get_order(order.id).status.value}")
    
    manager.start_order(order.id)
    print(f"  开始: {manager.get_order(order.id).status.value}")
    
    manager.submit_order(order.id, {"report": "sales_report.pdf"})
    print(f"  提交: {manager.get_order(order.id).status.value}")
    
    manager.complete_order(order.id)
    print(f"  完成: {manager.get_order(order.id).status.value}")
    
    # 统计
    print("\n[统计]")
    stats = manager.get_statistics()
    print(f"  总订单: {stats['total_orders']}")
    print(f"  已完成: {stats['completed_volume']} VIBE")


def demo_reputation_service():
    """声誉服务演示"""
    print("\n" + "=" * 60)
    print("Reputation Service 演示")
    print("=" * 60)
    
    service = ReputationService()
    
    # 提交评价
    print("\n[提交评价]")
    service.submit_review(
        order_id="order_001",
        reviewer_id="buyer",
        reviewee_id="seller",
        rating=ReviewRating.EXCELLENT,
        comment="工作质量很高！"
    )
    service.submit_review(
        order_id="order_002",
        reviewer_id="buyer2",
        reviewee_id="seller",
        rating=ReviewRating.GOOD,
        comment="按时交付"
    )
    print("  提交了 2 条评价")
    
    # 计算声誉
    print("\n[计算声誉]")
    reputation = service.calculate_reputation("seller")
    print(f"  声誉: {reputation:.3f}")
    
    trust_score = service.get_trust_score("seller")
    print(f"  信任分数: {trust_score:.3f}")
    
    # 评价分布
    print("\n[评价分布]")
    dist = service.get_rating_distribution("seller")
    print(f"  优秀: {dist['excellent']}")
    print(f"  良好: {dist['good']}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("USMSB Phase 1: Core Services 演示")
    print("=" * 60)
    print("\n涵盖模块:")
    print("- AgentRegistry: Agent 注册与管理")
    print("- GeneCapsuleManager: 基因胶囊管理")
    print("- MatchingEngine: 匹配引擎")
    print("- NegotiationHub: 谈判中心")
    print("- OrderManager: 订单管理")
    print("- ReputationService: 声誉服务")
    
    try:
        demo_agent_registry()
        demo_gene_capsule()
        demo_matching_engine()
        demo_negotiation_hub()
        demo_order_manager()
        demo_reputation_service()
        
        print("\n" + "=" * 60)
        print("演示完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
