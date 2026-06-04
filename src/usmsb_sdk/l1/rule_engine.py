# -*- coding: utf-8 -*-
"""
L1 RuleEngine - 反应式 Agent 规则引擎

L1 = 最简单的 Agent: Stimulus → Response
无记忆，无状态，只有规则匹配

功能：
- 规则注册和管理
- 条件匹配（intent, keyword, pattern）
- 动作执行
- 优先级处理
"""

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable


class ConditionType(Enum):
    """条件类型"""
    INTENT = "intent"      # 意图匹配
    KEYWORD = "keyword"    # 关键词匹配
    PATTERN = "pattern"    # 正则模式
    EXACT = "exact"        # 完全匹配
    FUZZY = "fuzzy"         # 模糊匹配


class ActionType(Enum):
    """动作类型"""
    RESPOND = "respond"     # 回复
    EXECUTE = "execute"     # 执行函数
    CHAIN = "chain"         # 链式执行
    FALLBACK = "fallback"   # 兜底


@dataclass
class Condition:
    """规则条件"""
    type: ConditionType
    pattern: str
    params: dict = field(default_factory=dict)
    
    def matches(self, input_text: str) -> bool:
        """
        检查输入是否匹配条件
        
        Args:
            input_text: 用户输入
            
        Returns:
            bool: 是否匹配
        """
        text = input_text.lower()
        pattern = self.pattern.lower()
        
        if self.type == ConditionType.INTENT:
            # 意图匹配 - 检查关键词出现
            keywords = pattern.split()
            return all(kw in text for kw in keywords)
        
        elif self.type == ConditionType.KEYWORD:
            # 关键词匹配
            return pattern in text
        
        elif self.type == ConditionType.PATTERN:
            # 正则匹配
            try:
                return bool(re.search(pattern, input_text, re.IGNORECASE))
            except re.error:
                return pattern in text
        
        elif self.type == ConditionType.EXACT:
            # 完全匹配
            return text.strip() == pattern
        
        elif self.type == ConditionType.FUZZY:
            # 模糊匹配 - 简单实现
            pattern_chars = [c for c in pattern if c.isalnum()]
            text_chars = [c for c in text if c.isalnum()]
            matches = sum(1 for c in pattern_chars if c in text_chars)
            return matches / len(pattern_chars) > 0.7 if pattern_chars else False
        
        return False


@dataclass
class Action:
    """规则动作"""
    type: ActionType
    response: str = ""                    # 文本回复
    handler: Callable | None = None      # 处理函数
    chain_actions: list["Action"] = field(default_factory=list)  # 链式动作
    params: dict = field(default_factory=dict)
    
    async def execute(self, context: dict) -> Any:
        """
        执行动作
        
        Args:
            context: 执行上下文
            
        Returns:
            Any: 执行结果
        """
        if self.type == ActionType.RESPOND:
            return self._execute_respond()
        
        elif self.type == ActionType.EXECUTE:
            return await self._execute_handler(context)
        
        elif self.type == ActionType.CHAIN:
            return await self._execute_chain(context)
        
        elif self.type == ActionType.FALLBACK:
            return await self._execute_fallback(context)
        
        return None
    
    def _execute_respond(self) -> str:
        """执行回复"""
        return self.response
    
    async def _execute_handler(self, context: dict) -> Any:
        """执行处理函数"""
        if self.handler:
            try:
                if callable(self.handler):
                    result = self.handler(context)
                    if hasattr(result, '__await__'):
                        return await result
                    return result
            except Exception as e:
                return {"error": str(e)}
        return None
    
    async def _execute_chain(self, context: dict) -> list:
        """执行链式动作"""
        results = []
        for action in self.chain_actions:
            result = await action.execute(context)
            results.append(result)
        return results
    
    async def _execute_fallback(self, context: dict) -> str:
        """执行兜底动作"""
        return self.response or "抱歉，我没有理解您的问题。"


@dataclass
class Rule:
    """
    规则
    
    触发条件 + 执行动作
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    condition: Condition | None = None
    action: Action | None = None
    priority: int = 0                    # 优先级（越大越高）
    enabled: bool = True
    cooldown: float = 0.0               # 冷却时间（秒）
    usage_count: int = 0
    last_triggered: float | None = None
    metadata: dict = field(default_factory=dict)
    
    def can_trigger(self, stimulus: "Stimulus | None" = None) -> bool:
        """检查是否可以触发"""
        if not self.enabled:
            return False

        if stimulus is not None:
            if stimulus.metadata.get("bypass_l1") or stimulus.metadata.get("skip_l1"):
                return False

            allowed_sources = self.metadata.get("allowed_sources") or self.metadata.get("sources")
            if isinstance(allowed_sources, str):
                allowed_sources = [allowed_sources]
            if allowed_sources and stimulus.source not in allowed_sources:
                return False

            blocked_sources = self.metadata.get("blocked_sources")
            if isinstance(blocked_sources, str):
                blocked_sources = [blocked_sources]
            if blocked_sources and stimulus.source in blocked_sources:
                return False

            task_type = stimulus.metadata.get("task_type")
            allowed_task_types = self.metadata.get("allowed_task_types")
            if isinstance(allowed_task_types, str):
                allowed_task_types = [allowed_task_types]
            if allowed_task_types and task_type not in allowed_task_types:
                return False

            blocked_task_types = self.metadata.get("blocked_task_types")
            if isinstance(blocked_task_types, str):
                blocked_task_types = [blocked_task_types]
            if blocked_task_types and task_type in blocked_task_types:
                return False
        
        if self.cooldown > 0 and self.last_triggered:
            elapsed = datetime.now().timestamp() - self.last_triggered
            if elapsed < self.cooldown:
                return False
        
        return True
    
    def trigger(self) -> None:
        """触发规则"""
        self.usage_count += 1
        self.last_triggered = datetime.now().timestamp()


@dataclass
class Stimulus:
    """刺激输入"""
    text: str
    intent: str = ""
    entities: dict = field(default_factory=dict)
    confidence: float = 1.0
    source: str = "user"
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: dict = field(default_factory=dict)


@dataclass
class Response:
    """规则引擎响应"""
    rule_id: str
    rule_name: str
    action_result: Any
    confidence: float
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: dict = field(default_factory=dict)


class RuleEngine:
    """
    L1 规则引擎
    
    最简单的 Agent: Stimulus → Response
    无记忆，无状态，只有规则匹配
    """
    
    def __init__(self, name: str = "L1Agent"):
        self.name = name
        self.rules: list[Rule] = []
        self.default_rule: Rule | None = None
        
        # 统计
        self.stats = {
            "total_triggers": 0,
            "rule_hits": {},  # rule_id -> count
            "avg_latency_ms": 0.0,
        }
        
        # 注册默认兜底规则
        self._register_default_rules()
    
    def _register_default_rules(self) -> None:
        """注册默认规则"""
        # 问候规则
        self.add_rule(Rule(
            name="greeting",
            condition=Condition(ConditionType.INTENT, "你好|嗨|hello|hi"),
            action=Action(ActionType.RESPOND, response="你好！有什么可以帮您的？"),
            priority=10,
        ))
        
        # 感谢规则
        self.add_rule(Rule(
            name="thanks",
            condition=Condition(ConditionType.INTENT, "谢谢|感谢|thanks"),
            action=Action(ActionType.RESPOND, response="不客气！"),
            priority=5,
        ))
    
    def add_rule(self, rule: Rule) -> str:
        """
        添加规则
        
        Args:
            rule: 规则对象
            
        Returns:
            str: 规则 ID
        """
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)  # 按优先级排序
        return rule.id
    
    def remove_rule(self, rule_id: str) -> bool:
        """
        删除规则
        
        Args:
            rule_id: 规则 ID
            
        Returns:
            bool: 是否成功
        """
        for i, rule in enumerate(self.rules):
            if rule.id == rule_id:
                self.rules.pop(i)
                return True
        return False
    
    def get_rule(self, rule_id: str) -> Rule | None:
        """获取规则"""
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None
    
    def enable_rule(self, rule_id: str) -> bool:
        """启用规则"""
        rule = self.get_rule(rule_id)
        if rule:
            rule.enabled = True
            return True
        return False
    
    def disable_rule(self, rule_id: str) -> bool:
        """禁用规则"""
        rule = self.get_rule(rule_id)
        if rule:
            rule.enabled = False
            return True
        return False
    
    async def react(self, stimulus: Stimulus) -> Response:
        """
        触发规则匹配
        
        L1 Agent 核心：Stimulus → Response
        
        Args:
            stimulus: 刺激输入
            
        Returns:
            Response: 响应
        """
        start_time = datetime.now()

        if stimulus.metadata.get("bypass_l1") or stimulus.metadata.get("skip_l1"):
            return Response(
                rule_id="none",
                rule_name="bypassed",
                action_result="",
                confidence=0.0,
                metadata={"bypassed": True},
            )
        
        # 遍历规则找匹配
        for rule in self.rules:
            if not rule.can_trigger(stimulus):
                continue
            
            if rule.condition and rule.condition.matches(stimulus.text):
                # 匹配成功
                rule.trigger()
                self.stats["total_triggers"] += 1
                self.stats["rule_hits"][rule.id] = self.stats["rule_hits"].get(rule.id, 0) + 1
                
                # 执行动作
                context = {
                    "stimulus": stimulus,
                    "rule": rule,
                    "entities": stimulus.entities,
                }
                
                result = await rule.action.execute(context)
                
                # 计算延迟
                latency = (datetime.now() - start_time).total_seconds() * 1000
                self.stats["avg_latency_ms"] = (
                    self.stats["avg_latency_ms"] * 0.9 + latency * 0.1
                )
                
                return Response(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    action_result=result,
                    confidence=stimulus.confidence,
                )
        
        # 使用兜底规则
        if self.default_rule:
            result = await self.default_rule.action.execute({})
            return Response(
                rule_id=self.default_rule.id,
                rule_name=self.default_rule.name,
                action_result=result,
                confidence=0.0,
            )
        
        # 无匹配
        return Response(
            rule_id="none",
            rule_name="no_match",
            action_result="我没有理解您的问题。",
            confidence=0.0,
        )
    
    def set_default_rule(self, rule: Rule) -> None:
        """设置兜底规则"""
        rule.priority = -1000
        self.default_rule = rule
    
    def create_rule_from_config(
        self,
        name: str,
        condition_type: str,
        pattern: str,
        response: str,
        priority: int = 0
    ) -> Rule:
        """
        从配置创建规则
        
        Args:
            name: 规则名
            condition_type: 条件类型
            pattern: 匹配模式
            response: 回复文本
            priority: 优先级
            
        Returns:
            Rule: 创建的规则
        """
        cond_type_map = {
            "intent": ConditionType.INTENT,
            "keyword": ConditionType.KEYWORD,
            "pattern": ConditionType.PATTERN,
            "exact": ConditionType.EXACT,
            "fuzzy": ConditionType.FUZZY,
        }
        
        return Rule(
            name=name,
            condition=Condition(
                type=cond_type_map.get(condition_type, ConditionType.KEYWORD),
                pattern=pattern,
            ),
            action=Action(
                type=ActionType.RESPOND,
                response=response,
            ),
            priority=priority,
        )
    
    def add_rules_from_yaml(self, rules_config: list[dict]) -> int:
        """
        从配置列表批量添加规则
        
        Args:
            rules_config: 规则配置列表
            
        Returns:
            int: 添加的数量
        """
        count = 0
        for config in rules_config:
            try:
                rule = self.create_rule_from_config(
                    name=config.get("name", ""),
                    condition_type=config.get("condition_type", "keyword"),
                    pattern=config.get("pattern", ""),
                    response=config.get("response", ""),
                    priority=config.get("priority", 0),
                )
                self.add_rule(rule)
                count += 1
            except Exception as e:
                print(f"[RuleEngine] Failed to add rule {config.get('name')}: {e}")
        
        return count
    
    def get_statistics(self) -> dict:
        """获取统计"""
        return {
            "name": self.name,
            "rule_count": len(self.rules),
            "total_triggers": self.stats["total_triggers"],
            "rule_hits": self.stats["rule_hits"],
            "avg_latency_ms": self.stats["avg_latency_ms"],
            "top_rules": sorted(
                self.stats["rule_hits"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
        }
    
    def export_rules(self) -> list[dict]:
        """导出所有规则配置"""
        return [
            {
                "id": rule.id,
                "name": rule.name,
                "priority": rule.priority,
                "enabled": rule.enabled,
                "usage_count": rule.usage_count,
            }
            for rule in self.rules
        ]
    
    def __repr__(self) -> str:
        return f"RuleEngine(name={self.name}, rules={len(self.rules)})"
