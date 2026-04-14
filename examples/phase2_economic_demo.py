# -*- coding: utf-8 -*-
"""
Phase 2: Economic Incentive 示例

展示经济激励层的功能。

运行方式：
    python examples/phase2_economic_demo.py
"""

import sys
sys.path.insert(0, 'src')

from usmsb_sdk.economic import (
    TokenEconomy,
    TokenEventType,
    StakingPool,
    LayerSettlement,
    SettlementLayer,
)


def demo_token_economy():
    """Token 经济演示"""
    print("=" * 60)
    print("Token Economy 演示")
    print("=" * 60)
    
    economy = TokenEconomy()
    
    # 初始化
    print("\n[初始化]")
    economy.initialize({
        "foundation": 500_000_000,
        "team": 100_000_000,
        "incentive": 400_000_000,
    })
    print(f"  初始总量: {economy.get_total_supply():,.0f} VIBE")
    
    # 铸造
    print("\n[铸造]")
    economy.mint(to="agent_001", amount=10000)
    economy.mint(to="agent_002", amount=5000)
    print(f"  Agent 001 余额: {economy.get_balance('agent_001'):,.0f} VIBE")
    print(f"  Agent 002 余额: {economy.get_balance('agent_002'):,.0f} VIBE")
    
    # 转账
    print("\n[转账]")
    economy.transfer(from_="agent_001", to="agent_002", amount=2000)
    print(f"  转账 2000 VIBE")
    print(f"  Agent 001 余额: {economy.get_balance('agent_001'):,.0f} VIBE")
    print(f"  Agent 002 余额: {economy.get_balance('agent_002'):,.0f} VIBE")
    
    # 计算匹配费
    print("\n[匹配费计算]")
    fee = economy.calculate_matching_fee(1000)
    print(f"  订单 1000 VIBE 的匹配费: {fee:.1f} VIBE (1%)")
    
    # 质押
    print("\n[质押]")
    economy.stake("agent_001", 5000, lock_days=30)
    print(f"  质押 5000 VIBE (30天)")
    print(f"  质押数量: {economy.get_staked_amount('agent_001'):,.0f} VIBE")
    
    # 统计
    print("\n[统计]")
    stats = economy.get_statistics()
    print(f"  总供应量: {stats['total_supply']:,.0f}")
    print(f"  流通量: {stats['circulating_supply']:,.0f}")
    print(f"  质押总量: {stats['total_staked']:,.0f}")


def demo_staking_pool():
    """质押池演示"""
    print("\n" + "=" * 60)
    print("Staking Pool 演示")
    print("=" * 60)
    
    pool = StakingPool()
    
    # 质押
    print("\n[质押]")
    pos1 = pool.stake("agent_001", 10000, lock_days=30)
    pos2 = pool.stake("agent_002", 20000, lock_days=90)
    print(f"  Agent 001 质押: 10,000 VIBE (30天)")
    print(f"  Agent 002 质押: 20,000 VIBE (90天)")
    
    # 计算收益
    print("\n[计算收益]")
    import time
    time.sleep(0.1)  # 等待一下让时间流逝
    
    rewards1 = pool.calculate_rewards(pos1)
    rewards2 = pool.calculate_rewards(pos2)
    print(f"  Agent 001 当前收益: {rewards1:.4f} VIBE")
    print(f"  Agent 002 当前收益: {rewards2:.4f} VIBE")
    
    # 统计
    print("\n[统计]")
    stats = pool.get_statistics()
    print(f"  总质押量: {stats['total_staked']:,.0f} VIBE")
    print(f"  年化收益率: {stats['annual_reward_rate']:.0%}")


def demo_layer_settlement():
    """分层结算演示"""
    print("\n" + "=" * 60)
    print("Layer Settlement 演示")
    print("=" * 60)
    
    settlement = LayerSettlement()
    
    # 创建结算
    print("\n[创建结算]")
    sid1 = settlement.create_settlement(
        order_id="order_001",
        from_agent="buyer",
        to_agent="seller",
        amount=1000,
        currency="VIBE",
        layer=SettlementLayer.LAYER_1
    )
    print(f"  Layer 1 结算: 1000 VIBE, 手续费 2%")
    
    sid2 = settlement.create_settlement(
        order_id="order_002",
        from_agent="buyer",
        to_agent="seller",
        amount=1000,
        currency="USDC",
        layer=SettlementLayer.LAYER_2
    )
    print(f"  Layer 2 结算: 1000 USDC, 手续费 1%")
    
    # 处理结算
    print("\n[处理结算]")
    settlement.process(sid1)
    s1 = settlement.get_settlement(sid1)
    print(f"  Layer 1 完成: 状态={s1.status.value}")
    
    settlement.process(sid2)
    s2 = settlement.get_settlement(sid2)
    print(f"  Layer 2 完成: 状态={s2.status.value}")
    
    # 统计
    print("\n[统计]")
    stats = settlement.get_statistics()
    print(f"  总结算数: {stats['total_settlements']}")
    print(f"  按层级: {stats['by_layer']}")


def main():
    print("\n" + "=" * 60)
    print("USMSB Phase 2: Economic Incentive 演示")
    print("=" * 60)
    print("\n涵盖模块:")
    print("- TokenEconomy: VIBE Token 经济系统")
    print("- StakingPool: 质押池")
    print("- LayerSettlement: 分层结算")
    
    try:
        demo_token_economy()
        demo_staking_pool()
        demo_layer_settlement()
        
        print("\n" + "=" * 60)
        print("演示完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
