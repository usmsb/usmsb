"""
ValueSelfLoop - 价值自循环模块

硅基文明的核心机制：价值自我循环。

不需要外部注入，Agent 通过服务交换创造价值，
价值转化为资源，资源支持新目标，新目标驱动新服务。

核心循环：
Agent A 服务 → Agent B → 价值创造 → VIBE Token → Agent A 新目标
     ↑                                                        ↓
     └────────────────────────────────────────────────────────┘

使用方式：
```python
from usmsb_sdk.l3 import ValueSelfLoop, ServiceType

value_loop = ValueSelfLoop(agent_id="agent_001")

# 1. 提供服务
service = value_loop.provide_service(
    provider_id="agent_001",
    consumer_id="agent_002",
    service_type=ServiceType.COMPUTATION,
    description="数据处理",
    difficulty=0.7,
    urgency=0.8
)

# 2. 完成服务
value_record = value_loop.complete_service(service.id)

# 3. 确认服务（消费者确认）
value_record = value_loop.verify_service(service.id)

# 4. 转换为 VIBE
vibe = value_loop.convert_to_vibe(value_record.id)

# 5. 检查资源
if value_loop.is_resource_sufficient("agent_001"):
    goal = value_loop.trigger_new_goal("agent_001")
```
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from usmsb_sdk.core.elements import Goal, GoalStatus

from .vibe_token import VIBEToken
from .value_ledger import ValueLedger, ValueRecord, ValueType, ValueStatus
from .service_registry import ServiceRegistry, Service, ServiceType, ServiceStatus
from .purpose_generator import PurposeGenerator
from .intrinsic_motivation import IntrinsicMotivationEngine


class ValueCalculationEngine:
    """价值计算引擎"""
    
    @staticmethod
    def calculate_base_value(difficulty: float, urgency: float) -> float:
        """
        计算基础价值
        
        Formula: base_value = difficulty × urgency × 100
        
        Args:
            difficulty: 难度系数 (0.0-1.0)
            urgency: 紧急程度 (0.0-1.0)
            
        Returns:
            float: 基础价值
        """
        return difficulty * urgency * 100.0
    
    @staticmethod
    def calculate_final_value(
        base_value: float,
        quality_score: float,
        scarcity_bonus: float,
        demand_multiplier: float
    ) -> float:
        """
        计算最终价值
        
        Formula: final_value = base_value × quality_score × scarcity_bonus × demand_multiplier
        
        Args:
            base_value: 基础价值
            quality_score: 质量分数 (0.0-1.0)
            scarcity_bonus: 稀缺性加成
            demand_multiplier: 需求倍数
            
        Returns:
            float: 最终价值
        """
        return base_value * quality_score * scarcity_bonus * demand_multiplier
    
    @staticmethod
    def calculate_scarcity_bonus(service_type: ServiceType) -> float:
        """
        计算稀缺性加成
        
        稀缺服务类型获得更高加成。
        
        Args:
            service_type: 服务类型
            
        Returns:
            float: 稀缺性加成 (1.0 - 1.5)
        """
        # 稀缺性排序（越稀缺越高）
        scarcity_order = {
            ServiceType.MEDIATION: 1.5,         # 调解服务最稀缺
            ServiceType.COORDINATION: 1.4,      # 协调服务
            ServiceType.CREATION: 1.3,          # 创造服务
            ServiceType.KNOWLEDGE_QUERY: 1.2,   # 知识查询
            ServiceType.COMPUTATION: 1.1,       # 计算服务
            ServiceType.DATA_PROCESSING: 1.0,   # 数据处理
            ServiceType.LEARNING: 1.0,          # 学习服务
            ServiceType.RESOURCE_SHARING: 0.9,  # 资源共享
        }
        return scarcity_order.get(service_type, 1.0)
    
    @staticmethod
    def calculate_demand_multiplier(current_demand: float = 1.0) -> float:
        """
        计算需求倍数
        
        Args:
            current_demand: 当前需求度 (0.0-1.0)
            
        Returns:
            float: 需求倍数 (1.0 - 1.3)
        """
        return 1.0 + current_demand * 0.3


class VIBEConversionEngine:
    """VIBE 转换引擎"""
    
    # 固定转换率（10% 归系统）
    DEFAULT_CONVERSION_RATE = 0.9
    
    @staticmethod
    def get_reputation_factor(reputation: float) -> float:
        """
        计算声誉因子
        
        声誉越高，转换率越高。
        
        Formula: factor = 0.8 + reputation × 0.4
        
        Args:
            reputation: 声誉 (0.0-1.0)
            
        Returns:
            float: 声誉因子 (0.8 - 1.2)
        """
        return 0.8 + reputation * 0.4
    
    @staticmethod
    def convert(
        final_value: float,
        conversion_rate: float = DEFAULT_CONVERSION_RATE,
        agent_reputation: float = 0.5
    ) -> float:
        """
        将价值转换为 VIBE Token
        
        Formula: converted_vibe = final_value × conversion_rate × reputation_factor
        
        Args:
            final_value: 最终价值
            conversion_rate: 转换率
            agent_reputation: Agent 声誉
            
        Returns:
            float: 转换的 VIBE 数量
        """
        reputation_factor = VIBEConversionEngine.get_reputation_factor(agent_reputation)
        return final_value * conversion_rate * reputation_factor


@dataclass
class CircularFlowStats:
    """价值循环统计"""
    total_services: int = 0
    total_value_created: float = 0.0
    total_vibe_converted: float = 0.0
    current_balance: float = 0.0
    circular_flow_rate: float = 0.0  # 循环率（收益投入新服务的比例）


class ValueSelfLoop:
    """
    价值自循环主控制器
    
    核心职责：
    1. 管理服务提供和完成
    2. 计算和记录价值
    3. 转换 VIBE Token
    4. 追踪资源积累
    5. 触发新目标生成
    """
    
    def __init__(
        self,
        agent_id: str | None = None,
        vibe_token: VIBEToken | None = None,
        value_ledger: ValueLedger | None = None,
        service_registry: ServiceRegistry | None = None,
        purpose_generator: PurposeGenerator | None = None
    ):
        """
        初始化 ValueSelfLoop
        
        Args:
            agent_id: 当前 Agent ID
            vibe_token: VIBE Token 管理器（共享实例）
            value_ledger: 价值账本（共享实例）
            service_registry: 服务注册（共享实例）
            purpose_generator: 目标生成器
        """
        self.agent_id = agent_id
        self.vibe_token = vibe_token or VIBEToken()
        self.value_ledger = value_ledger or ValueLedger()
        self.service_registry = service_registry or ServiceRegistry()
        self.purpose_generator = purpose_generator
        self.intrinsic_motivation = IntrinsicMotivationEngine()
        
        # 服务类型统计（用于稀缺性计算）
        self._service_type_counts: dict[ServiceType, int] = {}
    
    def provide_service(
        self,
        provider_id: str,
        consumer_id: str,
        service_type: ServiceType,
        description: str = "",
        difficulty: float = 0.5,
        urgency: float = 0.5,
        input_params: dict | None = None
    ) -> Service:
        """
        提供服务，创建服务记录
        
        Args:
            provider_id: 服务提供方
            consumer_id: 服务消费方
            service_type: 服务类型
            description: 服务描述
            difficulty: 难度系数
            urgency: 紧急程度
            input_params: 输入参数
            
        Returns:
            Service: 创建的服务记录
        """
        service = self.service_registry.register_service(
            provider_id=provider_id,
            consumer_id=consumer_id,
            service_type=service_type,
            description=description,
            difficulty=difficulty,
            urgency=urgency,
            input_params=input_params,
        )
        
        # 统计服务类型
        self._service_type_counts[service_type] = self._service_type_counts.get(service_type, 0) + 1
        
        return service
    
    def complete_service(
        self,
        service_id: str,
        output_result: Any = None,
        quality_score: float = 0.5
    ) -> ValueRecord:
        """
        服务完成，生成价值记录（未确认）
        
        Args:
            service_id: 服务 ID
            output_result: 输出结果
            quality_score: 质量评分
            
        Returns:
            ValueRecord: 价值记录
        """
        service = self.service_registry.get_service(service_id)
        if not service:
            raise ValueError(f"Service {service_id} not found")
        
        # 更新服务状态
        self.service_registry.complete_service(service_id, output_result)
        
        # 计算基础价值
        base_value = ValueCalculationEngine.calculate_base_value(
            difficulty=service.difficulty,
            urgency=service.urgency
        )
        
        # 计算稀缺性加成
        scarcity_bonus = ValueCalculationEngine.calculate_scarcity_bonus(service.service_type)
        
        # 计算需求倍数（基于该类型服务的当前供给）
        total_services = sum(self._service_type_counts.values())
        service_type_count = self._service_type_counts.get(service.service_type, 1)
        current_demand = 1.0 - (service_type_count / max(total_services, 1))
        demand_multiplier = ValueCalculationEngine.calculate_demand_multiplier(current_demand)
        
        # 计算最终价值
        final_value = ValueCalculationEngine.calculate_final_value(
            base_value=base_value,
            quality_score=quality_score,
            scarcity_bonus=scarcity_bonus,
            demand_multiplier=demand_multiplier
        )
        
        # 创建价值记录
        value_record = ValueRecord(
            id=f"value_{service_id}",
            service_id=service_id,
            provider_id=service.provider_id,
            consumer_id=service.consumer_id,
            value_type=ValueType.ECONOMIC,
            raw_value=base_value,
            quality_score=quality_score,
            scarcity_bonus=scarcity_bonus,
            demand_multiplier=demand_multiplier,
            final_value=final_value,
            status=ValueStatus.CREATED,
            metadata={"service_type": service.service_type.value}
        )
        
        self.value_ledger.record_value(value_record)
        
        return value_record
    
    def verify_service(
        self,
        service_id: str,
        quality_score: float | None = None
    ) -> ValueRecord:
        """
        确认服务，价值正式生效
        
        Args:
            service_id: 服务 ID
            quality_score: 质量评分（可选）
            
        Returns:
            ValueRecord: 更新后的价值记录
        """
        service = self.service_registry.get_service(service_id)
        if not service:
            raise ValueError(f"Service {service_id} not found")
        
        # 更新服务状态
        self.service_registry.verify_service(service_id)
        
        # 获取价值记录
        value_record = self.value_ledger.get_value_record(f"value_{service_id}")
        if not value_record:
            raise ValueError(f"Value record for service {service_id} not found")
        
        # 如果提供了质量评分，更新价值记录
        if quality_score is not None:
            # 重新计算最终价值
            new_final_value = ValueCalculationEngine.calculate_final_value(
                base_value=value_record.raw_value,
                quality_score=quality_score,
                scarcity_bonus=value_record.scarcity_bonus,
                demand_multiplier=value_record.demand_multiplier
            )
            value_record.quality_score = quality_score
            value_record.final_value = new_final_value
        
        # 更新价值状态
        self.value_ledger.update_status(
            value_record.id,
            ValueStatus.CONFIRMED,
            quality_score=value_record.quality_score
        )
        
        value_record.status = ValueStatus.CONFIRMED
        return value_record
    
    def convert_to_vibe(self, value_record_id: str) -> Any:
        """
        将价值记录转换为 VIBE Token
        
        Args:
            value_record_id: 价值记录 ID
            
        Returns:
            Resource: VIBE 资源
        """
        value_record = self.value_ledger.get_value_record(value_record_id)
        if not value_record:
            raise ValueError(f"Value record {value_record_id} not found")
        
        if value_record.status != ValueStatus.CONFIRMED:
            raise ValueError(f"Value record not confirmed, status: {value_record.status}")
        
        # 计算转换数量
        converted_vibe = VIBEConversionEngine.convert(
            final_value=value_record.final_value,
            conversion_rate=value_record.conversion_rate,
            agent_reputation=0.5  # 默认声誉
        )
        
        # 铸造 VIBE Token
        self.vibe_token.mint(to_agent_id=value_record.provider_id, amount=converted_vibe)
        
        # 更新价值状态
        self.value_ledger.update_status(
            value_record_id,
            ValueStatus.CONVERTED,
            converted_vibe=converted_vibe
        )
        
        # 返回 VIBE 资源
        from usmsb_sdk.core.elements import Resource, ResourceType
        return Resource(
            name="VIBE",
            type=ResourceType.FINANCIAL,
            quantity=converted_vibe,
            value=value_record.final_value,
            metadata={"value_record_id": value_record_id}
        )
    
    def get_agent_vibe_balance(self, agent_id: str) -> float:
        """获取 Agent 的 VIBE 余额"""
        return self.vibe_token.get_balance(agent_id)
    
    def is_resource_sufficient(
        self,
        agent_id: str,
        threshold_multiplier: float = 1.2
    ) -> bool:
        """
        检查 Agent 资源是否充足
        
        资源充足的定义：
        当前余额 > 基础阈值 × 安全缓冲系数
        
        Args:
            agent_id: Agent ID
            threshold_multiplier: 安全缓冲系数
            
        Returns:
            bool: 是否充足
        """
        balance = self.get_agent_vibe_balance(agent_id)
        base_threshold = 50.0  # 基础阈值
        
        # 检查是否有活跃目标
        if self.purpose_generator:
            active_goals = self.purpose_generator.get_active_goals()
            threshold = base_threshold + len(active_goals) * 20 * threshold_multiplier
        else:
            threshold = base_threshold * threshold_multiplier
        
        return balance >= threshold
    
    def trigger_new_goal_if_possible(self, agent_id: str) -> Goal | None:
        """
        如果资源充足，触发新目标生成
        
        条件：
        1. 资源充足
        2. PurposeGenerator 可用
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Goal 或 None
        """
        if not self.is_resource_sufficient(agent_id):
            return None
        
        if not self.purpose_generator:
            return None
        
        # 生成新 Purpose
        purpose = self.purpose_generator.generate_purpose()
        if not purpose:
            return None
        
        # 转化为 Goal
        goal = self.purpose_generator.purpose_to_goal(purpose)
        
        return goal
    
    def get_value_history(
        self,
        agent_id: str,
        limit: int = 100,
        as_provider: bool = True
    ) -> list[ValueRecord]:
        """获取 Agent 的价值历史"""
        return self.value_ledger.get_value_history(agent_id, limit=limit, as_provider=as_provider)
    
    def get_circular_flow_stats(self, agent_id: str) -> CircularFlowStats:
        """
        获取价值循环统计
        
        Args:
            agent_id: Agent ID
            
        Returns:
            CircularFlowStats: 统计信息
        """
        # 获取服务统计
        service_stats = self.service_registry.get_service_stats(agent_id)
        
        # 获取价值历史
        value_history = self.value_ledger.get_value_history(agent_id, limit=1000)
        
        total_value = sum(v.final_value for v in value_history)
        total_converted = sum(v.converted_vibe for v in value_history)
        current_balance = self.get_agent_vibe_balance(agent_id)
        
        # 计算循环率
        total_earned = self.vibe_token.get_total_earned(agent_id)
        circular_rate = (total_converted / total_earned * 100) if total_earned > 0 else 0
        
        return CircularFlowStats(
            total_services=service_stats["total"],
            total_value_created=total_value,
            total_vibe_converted=total_converted,
            current_balance=current_balance,
            circular_flow_rate=circular_rate
        )
    
    def execute_complete_cycle(
        self,
        provider_id: str,
        consumer_id: str,
        service_type: ServiceType,
        description: str,
        difficulty: float = 0.5,
        urgency: float = 0.5,
        quality_score: float = 0.8
    ) -> dict[str, Any]:
        """
        执行完整价值循环（便捷方法）
        
        流程：提供 → 完成 → 确认 → 转换 → 检查资源
        
        Args:
            provider_id: 服务提供方
            consumer_id: 服务消费方
            service_type: 服务类型
            description: 服务描述
            difficulty: 难度
            urgency: 紧急程度
            quality_score: 质量评分
            
        Returns:
            dict: 完整循环结果
        """
        # 1. 提供服务
        service = self.provide_service(
            provider_id=provider_id,
            consumer_id=consumer_id,
            service_type=service_type,
            description=description,
            difficulty=difficulty,
            urgency=urgency
        )
        
        # 2. 接受服务（自动变为进行中）
        self.service_registry.update_status(service.id, ServiceStatus.IN_PROGRESS)
        
        # 3. 完成服务
        value_record = self.complete_service(service.id, quality_score=quality_score)
        
        # 4. 确认服务
        value_record = self.verify_service(service.id, quality_score=quality_score)
        
        # 5. 转换为 VIBE
        vibe_resource = self.convert_to_vibe(value_record.id)
        
        # 6. 获取更新后的余额
        new_balance = self.get_agent_vibe_balance(provider_id)
        
        # 7. 检查是否触发新目标
        new_goal = None
        if self.is_resource_sufficient(provider_id):
            new_goal = self.trigger_new_goal_if_possible(provider_id)
        
        return {
            "service_id": service.id,
            "value_record_id": value_record.id,
            "vibe_amount": vibe_resource.quantity,
            "new_balance": new_balance,
            "new_goal": new_goal.to_dict() if new_goal else None,
            "circular_flow_stats": self.get_circular_flow_stats(provider_id).__dict__
        }
