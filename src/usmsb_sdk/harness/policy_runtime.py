# -*- coding: utf-8 -*-
"""
风险门控层 - Policy Runtime

三层规则体系：
1. 硬性规则 (HardRule) - 不可绕过，数据边界、操作黑名单
2. 软性规则 (SoftRule) - 触发审批，风险评分阈值
3. 动态规则 (DynamicRule) - 经验驱动，历史失败归纳

使用方式：
```python
from usmsb_sdk.harness import PolicyRuntime, HardRule, SoftRule, RuleType

policy = PolicyRuntime()

# 添加规则
policy.add_rule(HardRule(
    name="data_access_boundary",
    condition=lambda ctx: ctx.get("data_size", 0) <= 1000,
    action="block",
    description="数据访问量不能超过1000"
))

# 执行检查
result = policy.enforce(action_context)
```
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable


class RuleType(Enum):
    """规则类型"""
    HARD = "hard"      # 硬性规则，不可绕过
    SOFT = "soft"      # 软性规则，触发审批
    DYNAMIC = "dynamic"  # 动态规则，经验驱动


class RuleResult(Enum):
    """规则检查结果"""
    ALLOW = "allow"       # 允许
    BLOCK = "block"       # 阻止
    APPROVAL_REQUIRED = "approval_required"  # 需要审批
    REVIEW = "review"     # 需要人工审查


@dataclass
class RuleContext:
    """规则执行上下文"""
    agent_id: str = ""
    action: str = ""
    resource: str = ""
    data_size: int = 0
    risk_score: float = 0.0
    metadata: dict = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.metadata.get(key, default) or default


@dataclass
class RuleCheckResult:
    """规则检查结果"""
    rule_id: str
    rule_name: str
    rule_type: RuleType
    result: RuleResult
    reason: str
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    details: dict = field(default_factory=dict)


class Rule:
    """规则基类"""
    
    def __init__(
        self,
        name: str,
        rule_type: RuleType,
        condition: Callable[[RuleContext], bool],
        action: str = "block",
        description: str = "",
        priority: int = 0,
        enabled: bool = True
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.rule_type = rule_type
        self.condition = condition
        self.action = action
        self.description = description
        self.priority = priority
        self.enabled = enabled
        self.trigger_count = 0
        self.last_triggered: float | None = None
    
    def check(self, context: RuleContext) -> RuleCheckResult:
        """检查规则"""
        if not self.enabled:
            return RuleCheckResult(
                rule_id=self.id,
                rule_name=self.name,
                rule_type=self.rule_type,
                result=RuleResult.ALLOW,
                reason="Rule disabled"
            )
        
        try:
            matched = self.condition(context)
            self.trigger_count += 1
            self.last_triggered = datetime.now().timestamp()
            
            if matched:
                if self.rule_type == RuleType.HARD:
                    result = RuleResult.BLOCK
                elif self.rule_type == RuleType.SOFT:
                    result = RuleResult.APPROVAL_REQUIRED
                else:
                    result = RuleResult.REVIEW
                
                return RuleCheckResult(
                    rule_id=self.id,
                    rule_name=self.name,
                    rule_type=self.rule_type,
                    result=result,
                    reason=self.description or f"Rule {self.name} triggered",
                    details={"action": self.action}
                )
            else:
                return RuleCheckResult(
                    rule_id=self.id,
                    rule_name=self.name,
                    rule_type=self.rule_type,
                    result=RuleResult.ALLOW,
                    reason="Condition not matched"
                )
        except Exception as e:
            return RuleCheckResult(
                rule_id=self.id,
                rule_name=self.name,
                rule_type=self.rule_type,
                result=RuleResult.BLOCK,
                reason=f"Rule check error: {e}"
            )


class HardRule(Rule):
    """硬性规则 - 不可绕过"""
    
    def __init__(self, name: str, condition: Callable[[RuleContext], bool],
                 action: str = "block", description: str = "", priority: int = 100):
        super().__init__(
            name=name,
            rule_type=RuleType.HARD,
            condition=condition,
            action=action,
            description=description,
            priority=priority
        )


class SoftRule(Rule):
    """软性规则 - 触发审批"""
    
    def __init__(self, name: str, condition: Callable[[RuleContext], bool],
                 action: str = "approval", description: str = "", priority: int = 50):
        super().__init__(
            name=name,
            rule_type=RuleType.SOFT,
            condition=condition,
            action=action,
            description=description,
            priority=priority
        )


class DynamicRule(Rule):
    """动态规则 - 经验驱动"""
    
    def __init__(
        self,
        name: str,
        condition: Callable[[RuleContext], bool],
        action: str = "review",
        description: str = "",
        success_patterns: list[str] | None = None,
        failure_patterns: list[str] | None = None,
        priority: int = 30
    ):
        super().__init__(
            name=name,
            rule_type=RuleType.DYNAMIC,
            condition=condition,
            action=action,
            description=description,
            priority=priority
        )
        self.success_patterns = success_patterns or []
        self.failure_patterns = failure_patterns or []
        self.learned_from_history()
    
    def learned_from_history(self) -> None:
        """从历史经验学习"""
        # 可以从 ExperienceKnowledge 中学习模式
        pass
    
    def update_patterns(self, success_patterns: list[str], 
                       failure_patterns: list[str]) -> None:
        """更新模式库"""
        self.success_patterns.extend(success_patterns)
        self.failure_patterns.extend(failure_patterns)


class PolicyRuntime:
    """
    Policy Runtime - 风险门控运行时
    
    执行三层规则检查
    """
    
    def __init__(self):
        self._rules: list[Rule] = []
        self._rule_index: dict[RuleType, list[Rule]] = {
            RuleType.HARD: [],
            RuleType.SOFT: [],
            RuleType.DYNAMIC: []
        }
        self._audit_log: list[RuleCheckResult] = []
    
    def add_rule(self, rule: Rule) -> str:
        """添加规则"""
        self._rules.append(rule)
        self._rule_index[rule.rule_type].append(rule)
        # 按优先级排序
        self._rule_index[rule.rule_type].sort(key=lambda r: r.priority, reverse=True)
        return rule.id
    
    def remove_rule(self, rule_id: str) -> bool:
        """移除规则"""
        for rules in self._rule_index.values():
            for i, r in enumerate(rules):
                if r.id == rule_id:
                    rules.pop(i)
                    return True
        return False
    
    def enable_rule(self, rule_id: str) -> bool:
        """启用规则"""
        for rule in self._rules:
            if rule.id == rule_id:
                rule.enabled = True
                return True
        return False
    
    def disable_rule(self, rule_id: str) -> bool:
        """禁用规则"""
        for rule in self._rules:
            if rule.id == rule_id:
                rule.enabled = False
                return True
        return False
    
    def enforce(self, context: RuleContext) -> dict:
        """
        执行规则检查
        
        Args:
            context: 规则上下文
            
        Returns:
            {
                "allowed": bool,
                "results": [RuleCheckResult],
                "blocked_by": str | None,
                "approval_required": bool,
                "risk_level": str
            }
        """
        results: list[RuleCheckResult] = []
        blocked_by: str | None = None
        approval_required = False
        
        # 先检查硬性规则
        for rule in self._rule_index[RuleType.HARD]:
            result = rule.check(context)
            results.append(result)
            if result.result == RuleResult.BLOCK:
                blocked_by = rule.name
                self._audit_log.append(result)
                return {
                    "allowed": False,
                    "results": results,
                    "blocked_by": blocked_by,
                    "approval_required": False,
                    "risk_level": "critical"
                }
        
        # 再检查软性规则
        for rule in self._rule_index[RuleType.SOFT]:
            result = rule.check(context)
            results.append(result)
            if result.result == RuleResult.APPROVAL_REQUIRED:
                approval_required = True
        
        # 最后检查动态规则
        for rule in self._rule_index[RuleType.DYNAMIC]:
            result = rule.check(context)
            results.append(result)
        
        # 记录审计日志
        self._audit_log.extend(results)
        
        return {
            "allowed": True,
            "results": results,
            "blocked_by": blocked_by,
            "approval_required": approval_required,
            "risk_level": "high" if approval_required else "low"
        }
    
    def get_audit_log(self, limit: int = 100) -> list[RuleCheckResult]:
        """获取审计日志"""
        return self._audit_log[-limit:]
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            "total_rules": len(self._rules),
            "hard_rules": len(self._rule_index[RuleType.HARD]),
            "soft_rules": len(self._rule_index[RuleType.SOFT]),
            "dynamic_rules": len(self._rule_index[RuleType.DYNAMIC]),
            "audit_entries": len(self._audit_log),
        }
    
    def create_default_rules(self) -> None:
        """创建默认规则集"""
        # 硬性规则
        self.add_rule(HardRule(
            name="data_access_limit",
            condition=lambda ctx: ctx.data_size <= 10000,
            description="数据访问量不能超过10000"
        ))
        
        self.add_rule(HardRule(
            name="blacklist_action",
            condition=lambda ctx: ctx.action in ["delete_all", "drop_database"],
            description="禁止危险操作"
        ))
        
        # 软性规则
        self.add_rule(SoftRule(
            name="high_risk_score",
            condition=lambda ctx: ctx.risk_score > 0.7,
            description="高风险操作需要审批"
        ))
        
        # 动态规则
        self.add_rule(DynamicRule(
            name="pattern_matching",
            condition=lambda ctx: "suspicious" in ctx.metadata,
            description="可疑模式需要审查"
        ))
