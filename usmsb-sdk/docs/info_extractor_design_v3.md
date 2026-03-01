# 信息提取器 (InfoExtractor) 重构设计方案 v3

## 背景

当前 `chat` 方法中的历史消息检索逻辑存在以下问题：

1. **关键词过于宽泛** - 使用预定义关键词搜索，无法处理随机信息需求
2. **截断处理** - 只截取前300字符，上下文丢失
3. **合并判断** - 多条消息合并让 LLM 判断，相关度下降
4. **时间排序** - 按时间排序而非相关度
5. **缺少验证** - 提取后没有验证机制
6. **触发时机不当** - 收到消息就判断，而不是任务过程中缺失信息时调用

---

## 需求对齐 v3

1. **不保留旧逻辑** - 直接去除旧代码，进行重构
2. **意图分析不限制类型** - 根据实际情况需要什么找什么
3. **候选消息数量不做限制** - 按相关度依次验证，找到有用信息就停止
4. **验证失败继续** - 继续尝试下一条，直到遍历完所有候选
5. **成功更新记忆** - 验证通过后更新到 important_memories 表
6. **触发机制**：在任务规划阶段声明信息需求 → 检查最近消息列表 + important_memories 表 → 找不到时才调用 InfoExtractor

---

## 核心流程图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Agent Chat 主流程                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   用户消息                                                                   │
│       │                                                                     │
│       ▼                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Step 1: 任务规划 + 声明信息需求                                       │   │
│   │         TaskPlanner 分析任务                                          │   │
│   │         声明需要哪些信息 (List[InfoNeed])                            │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ▼                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Step 2: 信息存在性检查                                               │   │
│   │         InfoAvailabilityChecker                                      │   │
│   │         检查范围:                                                     │   │
│   │           1. 最近消息列表 (conversation_history)                    │   │
│   │           2. important_memories 表                                   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ▼                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Step 3: 判断是否需要调用 InfoExtractor                              │   │
│   │                                                                       │   │
│   │    已持有需要的信息? ──No───→ 调用 InfoExtractor                    │   │
│   │       │                         (从全量历史消息中提取)              │   │
│   │      Yes                                                              │   │
│   │       │                                                               │   │
│   │       ▼                                                               │   │
│   │   继续正常流程                                                         │   │
│   │                                                                       │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ▼                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Step 4: 正常 Chat 流程                                              │   │
│   │         - 构建消息                                                    │   │
│   │         - 调用 LLM                                                   │   │
│   │         - 执行工具等                                                  │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 关键模块设计

### 1. 数据类型定义

```python
# 文件: meta_agent/info/types.py

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

class InfoNeedType(Enum):
    """信息需求类型"""
    CREDENTIAL = "credential"      # 凭证信息 (API Key, 密码等)
    ACCOUNT = "account"           # 账号信息
    URL = "url"                   # 网址链接
    REFERENCE = "reference"       # 参考资料
    CONTEXT = "context"           # 上下文信息
    OTHER = "other"               # 其他

@dataclass
class InfoNeed:
    """
    信息需求声明
    
    在任务规划阶段声明需要哪些信息
    """
    need_id: str                  # 唯一标识
    name: str                     # 信息名称 (如 "虾聊API Key")
    info_type: InfoNeedType       # 信息类型
    description: str              # 描述需要找什么
    format_hint: str             # 格式提示 (可选)
    validation_hint: str          # 验证提示 (可选)
    required: bool = True         # 是否必须
    source: str = "llm"          # 来源: user/system/llm
    
    # 验证相关
    need_tool_validation: bool = False  # 是否需要工具验证
    tool_name: str = ""           # 验证工具名称
    
    # 状态
    fulfilled: bool = False       # 是否已满足
    value: Optional[str] = None   # 已获取的值


@dataclass
class RetrievalIntent:
    """检索意图"""
    info_type: str
    description: str
    format_hint: str = ""
    validation_hint: str = ""
    need_tool_validation: bool = False
    tool_name: str = ""


@dataclass
class CandidateMessage:
    """候选消息（全文本）"""
    message_id: str
    content: str        # 全文本，不截断
    role: str
    timestamp: float
    conversation_title: str = ""


@dataclass
class ExtractedInfo:
    """提取到的信息"""
    value: str
    confidence: float
    source_message_id: str
    reasoning: str


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    validated_value: Optional[str] = None
    method: str = ""  # "tool_call" / "llm"
    error: str = ""
```

---

### 2. InfoRequirement（信息需求声明器）

```python
# 文件: meta_agent/info/requirement.py

from typing import List, Dict
import uuid

class InfoRequirement:
    """
    信息需求管理器
    
    在任务规划阶段收集需要的信息声明
    """
    
    def __init__(self):
        self.needs: List[InfoNeed] = []
    
    def declare(
        self,
        name: str,
        info_type: str,
        description: str,
        format_hint: str = "",
        validation_hint: str = "",
        required: bool = True,
        need_tool_validation: bool = False,
        tool_name: str = ""
    ) -> str:
        """声明一个信息需求"""
        
        need_id = f"need_{uuid.uuid4().hex[:8]}"
        
        need = InfoNeed(
            need_id=need_id,
            name=name,
            info_type=InfoNeedType(info_type),
            description=description,
            format_hint=format_hint,
            validation_hint=validation_hint,
            required=required,
            need_tool_validation=need_tool_validation,
            tool_name=tool_name
        )
        
        self.needs.append(need)
        return need_id
    
    def get_unfulfilled(self) -> List[InfoNeed]:
        """获取未满足的需求"""
        return [n for n in self.needs if not n.fulfilled]
    
    def get_required_unfulfilled(self) -> List[InfoNeed]:
        """获取未满足的必需需求"""
        return [n for n in self.needs if n.required and not n.fulfilled]
    
    def fulfill(self, need_id: str, value: str):
        """标记需求已满足"""
        for need in self.needs:
            if need.need_id == need_id:
                need.fulfilled = True
                need.value = value
                break
    
    def clear(self):
        """清空所有需求"""
        self.needs.clear()
```

---

### 3. InfoAvailabilityChecker（信息存在性检查器）

```python
# 文件: meta_agent/info/availability_checker.py

from typing import List, Optional, Dict, Any
import re

class InfoAvailabilityChecker:
    """
    信息存在性检查器
    
    检查已持有的信息 vs 需要的信息
    检查范围:
      1. 最近消息列表 (conversation_history)
      2. important_memories 表
    
    返回:
      - 已满足的需求
      - 缺失的需求（需要调用 InfoExtractor）
    """
    
    def __init__(
        self,
        memory_manager,
        conversation_manager
    ):
        self.memory_manager = memory_manager
        self.conversation_manager = conversation_manager
    
    async def check(
        self,
        info_needs: List[InfoNeed],
        user_id: str,
        recent_messages: List[Dict[str, str]]  # 最近的消息列表
    ) -> Dict[str, Any]:
        """
        检查信息是否存在
        
        Args:
            info_needs: 需要的信息列表
            user_id: 用户ID
            recent_messages: 最近的消息列表
            
        Returns:
            {{
                "fulfilled": [已满足的需求],
                "missing": [缺失的需求],
                "sources": {{need_id: "来源说明"}}
            }}
        """
        
        fulfilled = []
        missing = []
        sources = {}
        
        for need in info_needs:
            # 1. 先从最近消息中查找
            found_in_messages = self._search_in_recent_messages(
                need, 
                recent_messages
            )
            
            if found_in_messages:
                fulfilled.append(need)
                sources[need.need_id] = "recent_messages"
                need.fulfilled = True
                need.value = found_in_messages
                continue
            
            # 2. 从 important_memories 表中查找
            found_in_memory = await self._search_in_important_memories(
                need,
                user_id
            )
            
            if found_in_memory:
                fulfilled.append(need)
                sources[need.need_id] = "important_memories"
                need.fulfilled = True
                need.value = found_in_memory
                continue
            
            # 3. 都找不到，标记为缺失
            missing.append(need)
        
        return {
            "fulfilled": fulfilled,
            "missing": missing,
            "sources": sources
        }
    
    def _search_in_recent_messages(
        self,
        need: InfoNeed,
        recent_messages: List[Dict[str, str]]
    ) -> Optional[str]:
        """
        在最近消息中搜索
        
        使用格式提示 + 关键词匹配
        """
        
        for msg in recent_messages:
            content = msg.get("content", "")
            
            # 根据格式提示构建搜索模式
            if need.format_hint:
                # 使用格式提示中的特征进行匹配
                if self._match_by_format(need, content):
                    return self._extract_value(need, content)
            
            # 备用：使用描述关键词匹配
            if self._match_by_description(need, content):
                return self._extract_value(need, content)
        
        return None
    
    def _match_by_format(self, need: InfoNeed, content: str) -> bool:
        """根据格式提示匹配"""
        
        format_hint = need.format_hint.lower()
        
        # 如果格式提示包含特定模式
        if "xialiao_" in format_hint and "xialiao_" in content.lower():
            return True
        if "github.com" in format_hint and "github.com" in content.lower():
            return True
        
        return False
    
    def _match_by_description(self, need: InfoNeed, content: str) -> bool:
        """根据描述关键词匹配"""
        
        description = need.description.lower()
        
        # 提取关键名词进行匹配
        keywords = []
        if "api key" in description or "api_key" in description:
            keywords.extend(["api key", "api_key", "apikey"])
        if "密码" in description or "password" in description.lower():
            keywords.extend(["密码", "password", "passwd"])
        
        content_lower = content.lower()
        return any(kw in content_lower for kw in keywords)
    
    def _extract_value(self, need: InfoNeed, content: str) -> str:
        """提取信息值"""
        
        # 这里可以更精确地提取
        # 简单实现：返回包含信息的片段
        
        format_hint = need.format_hint.lower()
        
        # 尝试提取 xialiao_ 开头的值
        if "xialiao_" in format_hint:
            match = re.search(r'(xialiao_[a-zA-Z0-9_]+)', content)
            if match:
                return match.group(1)
        
        # 尝试提取 URL
        if "github.com" in format_hint or "url" in need.info_type.value:
            match = re.search(r'https?://[^\s]+', content)
            if match:
                return match.group(0)
        
        # 默认返回内容片段
        return content[:200]
    
    async def _search_in_important_memories(
        self,
        need: InfoNeed,
        user_id: str
    ) -> Optional[str]:
        """在 important_memories 表中搜索"""
        
        try:
            # 从 memory_manager 获取重要记忆
            memories = await self.memory_manager.get_important_memories(user_id)
            
            for memory in memories:
                entity_type = memory.get("entity_type", "")
                content = memory.get("content", "")
                
                # 匹配类型
                if need.info_type.value in entity_type:
                    return content
                
                # 备用：匹配名称
                if need.name.lower() in entity_type.lower():
                    return content
            
        except Exception:
            pass
        
        return None
```

---

### 4. TaskPlanner（任务规划器）

```python
# 文件: meta_agent/info/planner.py

from typing import List, Dict, Any
import json

class TaskPlan:
    """任务计划"""
    def __init__(
        self,
        task_type: str,
        description: str,
        required_info: List[InfoNeed],
        steps: List[str]
    ):
        self.task_type = task_type
        self.description = description
        self.required_info = required_info
        self.steps = steps


class TaskPlanner:
    """
    任务规划器
    
    分析用户任务，生成执行计划
    同时声明需要哪些信息
    """
    
    def __init__(self, llm_manager, info_requirement: InfoRequirement):
        self.llm = llm_manager
        self.info_requirement = info_requirement
    
    async def plan(self, user_task: str, context: Dict[str, Any]) -> TaskPlan:
        """
        规划任务
        
        分析用户任务，生成执行计划
        同时在 info_requirement 中声明需要的信息
        """
        
        prompt = f"""分析用户任务，生成执行计划。

用户任务: {user_task}

上下文:
{json.dumps(context, ensure_ascii=False)[:500]}

请返回JSON:
{{
    "task_type": "任务类型",
    "description": "任务描述",
    "required_info": [
        {{
            "name": "信息名称（如：虾聊API Key）",
            "info_type": "credential/account/url/reference/context/other",
            "description": "描述需要什么信息",
            "format_hint": "格式提示（如：xialiao_开头，32位字母数字）",
            "validation_hint": "验证提示（如：调用API验证）",
            "required": true/false,
            "need_tool_validation": true/false,
            "tool_name": "工具名称（如有）"
        }}
    ],
    "steps": ["步骤1", "步骤2", ...]
}}

关键点：
- required_info 是执行这个任务需要的信息
- 如果任务需要外部平台凭证（如API Key），声明为 credential 类型
- format_hint 描述正确的格式，帮助后续检查和验证
- 不要声明与用户任务无关的信息需求
"""
        
        response = await self.llm.chat(prompt)
        
        # 解析 JSON
        # ... (解析代码)
        
        # 声明信息需求
        declared_needs = []
        for info in parsed.get("required_info", []):
            need_id = self.info_requirement.declare(
                name=info["name"],
                info_type=info["info_type"],
                description=info["description"],
                format_hint=info.get("format_hint", ""),
                validation_hint=info.get("validation_hint", ""),
                required=info.get("required", True),
                need_tool_validation=info.get("need_tool_validation", False),
                tool_name=info.get("tool_name", "")
            )
            declared_needs.append(self.info_requirement.needs[-1])
        
        return TaskPlan(
            task_type=parsed.get("task_type", "general"),
            description=parsed.get("description", ""),
            required_info=declared_needs,
            steps=parsed.get("steps", [])
        )
```

---

### 5. IntentAnalyzer（意图分析器）

```python
# 文件: meta_agent/info/intent_analyzer.py

class IntentAnalyzer:
    """
    意图分析器
    
    将 InfoNeed 转换为检索意图
    """
    
    def __init__(self, llm_manager):
        self.llm = llm_manager
    
    async def analyze_from_need(self, need: InfoNeed) -> RetrievalIntent:
        """
        从信息需求转换为检索意图
        """
        return RetrievalIntent(
            info_type=need.info_type.value,
            description=need.description,
            format_hint=need.format_hint,
            validation_hint=need.validation_hint,
            need_tool_validation=need.need_tool_validation,
            tool_name=need.tool_name
        )
    
    async def analyze_from_question(self, question: str) -> Optional[RetrievalIntent]:
        """
        从用户问题直接分析需要检索什么
        （用于没有任务规划的情况）
        """
        
        prompt = f"""分析用户问题，判断用户想要从历史对话中检索什么信息。

用户问题: {question}

请返回JSON:
{{
    "need_retrieval": true/false,
    "info_type": "credential/account/url/reference/context/other/未知",
    "description": "用户想要查找的具体信息",
    "format_hint": "正确的格式应该是什么样的",
    "validation_hint": "如何验证找到的信息是否正确"
}}
"""
        
        response = await self.llm.chat(prompt)
        # 解析 JSON ...
        
        if not data.get("need_retrieval"):
            return None
        
        return RetrievalIntent(...)
```

---

### 6. CandidateSearch（候选搜索器）

```python
# 文件: meta_agent/info/candidate_search.py

class CandidateSearch:
    """
    候选消息搜索器
    
    语义搜索，全文本，按相关度排序
    """
    
    def __init__(self, conversation_manager, llm_manager):
        self.conversation_manager = conversation_manager
        self.llm = llm_manager
    
    async def search(
        self,
        user_id: str,
        intent: RetrievalIntent,
        limit: int = 100  # 不做限制，搜足够多
    ) -> List[CandidateMessage]:
        """
        搜索候选消息
        
        - 使用语义描述搜索
        - 返回全文本
        - 按相关度排序
        """
        
        # 1. 语义搜索
        search_query = f"{intent.description} {intent.format_hint}"
        
        results = await self.conversation_manager.search_all_conversations(
            owner_id=user_id,
            query=search_query,
            limit=limit
        )
        
        # 2. 转换为候选对象（全文本）
        candidates = [
            CandidateMessage(
                message_id=r["id"],
                content=r["content"],  # 全文本
                role=r["role"],
                timestamp=r["timestamp"],
                conversation_title=r.get("conversation_title", "")
            )
            for r in results
        ]
        
        # 3. 按相关度排序
        ranked = await self._rank_by_relevance(candidates, intent)
        
        return ranked
    
    async def _rank_by_relevance(
        self,
        candidates: List[CandidateMessage],
        intent: RetrievalIntent
    ) -> List[CandidateMessage]:
        """
        用 LLM 按相关度排序
        """
        
        candidates_text = "\n".join([
            f"[{i}] 角色:{c.role} 内容:{c.content[:500]}"
            for i, c in enumerate(candidates[:30])
        ])
        
        prompt = f"""给定用户检索意图，对候选消息按与意图的相关度排序。

用户想要找: {intent.description}
信息类型: {intent.info_type}
格式要求: {intent.format_hint}

候选消息:
{candidates_text}

请返回按相关度排序的候选索引:
{{
    "ranked_indices": [索引列表],
    "reasoning": "简要说明"
}}
"""
        
        response = await self.llm.chat(prompt)
        # 解析 JSON ...
        
        ranked_indices = data.get("ranked_indices", [])
        return [candidates[i] for i in ranked_indices if i < len(candidates)]
```

---

### 7. LLMExtractor（逐条提取器）

```python
# 文件: meta_agent/info/llm_extractor.py

class LLMExtractor:
    """
    逐条 LLM 提取器
    
    逐条处理候选消息，从每条中提取需要的信息
    """
    
    def __init__(self, llm_manager):
        self.llm = llm_manager
    
    async def extract(
        self,
        candidate: CandidateMessage,
        intent: RetrievalIntent
    ) -> Optional[ExtractedInfo]:
        """
        从单条候选消息中提取信息
        """
        
        prompt = f"""从给定消息中提取用户需要的信息。

用户想要找: {intent.description}
信息类型: {intent.info_type}
正确格式应该是: {intent.format_hint}

候选消息:
---
角色: {candidate.role}
内容:
{candidate.content}
---

请判断这条消息是否包含用户需要的信息。

返回JSON:
{{
    "contains_target_info": true/false,
    "extracted_value": "提取到的具体信息",
    "confidence": 0.0-1.0,
    "reasoning": "判断理由"
}}
"""
        
        response = await self.llm.chat(prompt)
        # 解析 JSON ...
        
        if data.get("contains_target_info") and data.get("extracted_value"):
            return ExtractedInfo(
                value=data["extracted_value"],
                confidence=data.get("confidence", 0.5),
                source_message_id=candidate.message_id,
                reasoning=data.get("reasoning", "")
            )
        
        return None
```

---

### 8. Validator（验证器）

```python
# 文件: meta_agent/info/validator.py

class Validator:
    """
    验证器
    
    验证提取到的信息是否有效
    """
    
    def __init__(self, tool_registry=None):
        self.tool_registry = tool_registry
    
    async def validate(
        self,
        extracted_info: ExtractedInfo,
        intent: RetrievalIntent
    ) -> ValidationResult:
        """
        验证信息是否有效
        """
        
        # 优先使用工具验证
        if intent.need_tool_validation and self.tool_registry:
            return await self._tool_validate(extracted_info, intent)
        
        # 否则使用 LLM 验证
        return await self._llm_validate(extracted_info, intent)
    
    async def _tool_validate(
        self,
        extracted_info: ExtractedInfo,
        intent: RetrievalIntent
    ) -> ValidationResult:
        """工具调用验证"""
        
        tool_name = intent.tool_name
        
        try:
            result = await self.tool_registry.execute(
                tool_name,
                api_key=extracted_info.value
            )
            
            if result.get("success") or result.get("status") == 200:
                return ValidationResult(
                    is_valid=True,
                    validated_value=extracted_info.value,
                    method="tool_call"
                )
            else:
                return ValidationResult(
                    is_valid=False,
                    method="tool_call",
                    error=f"验证失败"
                )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                method="tool_call",
                error=str(e)
            )
    
    async def _llm_validate(
        self,
        extracted_info: ExtractedInfo,
        intent: RetrievalIntent
    ) -> ValidationResult:
        """LLM 验证"""
        
        prompt = f"""判断找到的信息是否符合用户需求。

用户想要找: {intent.description}
正确格式应该是: {intent.format_hint}

找到的信息: {extracted_info.value}

返回JSON:
{{
    "is_valid": true/false,
    "reasoning": "判断理由"
}}
"""
        
        response = await self.llm.chat(prompt)
        # 解析 JSON ...
        
        return ValidationResult(
            is_valid=data.get("is_valid", False),
            validated_value=extracted_info.value if data.get("is_valid") else None,
            method="llm"
        )
```

---

### 9. InfoExtractor（编排器）

```python
# 文件: meta_agent/info/extractor.py

class InfoExtractor:
    """
    信息提取器
    
    当最近消息和 important_memories 都找不到需要的信息时调用
    从全量历史消息中提取
    """
    
    def __init__(
        self,
        llm_manager,
        conversation_manager,
        tool_registry,
        memory_manager
    ):
        self.llm = llm_manager
        self.conversation_manager = conversation_manager
        self.tool_registry = tool_registry
        self.memory_manager = memory_manager
        
        self.intent_analyzer = IntentAnalyzer(llm_manager)
        self.candidate_search = CandidateSearch(conversation_manager, llm_manager)
        self.llm_extractor = LLMExtractor(llm_manager)
        self.validator = Validator(tool_registry)
    
    async def extract(
        self,
        info_needs: List[InfoNeed],
        user_id: str
    ) -> Dict[str, str]:
        """
        主流程：提取需要的信息
        
        Args:
            info_needs: 需要的信息列表（来自 TaskPlanner 声明的缺失信息）
            user_id: 用户ID
            
        Returns:
            {{need_id: extracted_value}}
        """
        
        results = {}
        
        for need in info_needs:
            # 转换为检索意图
            intent = await self.intent_analyzer.analyze_from_need(need)
            
            # 搜索候选（全文本，按相关度排序）
            candidates = await self.candidate_search.search(user_id, intent)
            
            if not candidates:
                continue
            
            # 逐条提取 + 验证
            for candidate in candidates:
                # 提取信息
                extracted = await self.llm_extractor.extract(candidate, intent)
                
                if extracted is None:
                    continue
                
                # 验证
                validation = await self.validator.validate(extracted, intent)
                
                if validation.is_valid:
                    # 验证通过
                    results[need.need_id] = validation.validated_value
                    need.fulfilled = True
                    need.value = validation.validated_value
                    
                    # 更新记忆
                    await self._update_memory(user_id, need, validation.validated_value)
                    
                    break  # 找到有效信息，停止遍历
        
        return results
    
    async def _update_memory(self, user_id: str, need: InfoNeed, value: str):
        """验证通过后更新记忆"""
        
        await self.memory_manager.store_important_entity(
            user_id=user_id,
            content=value,
            entity_type=need.info_type.value,
            name=need.name
        )
```

---

### 10. InfoRequirementHolder（持有者）

```python
# 文件: meta_agent/info/holder.py

class InfoRequirementHolder:
    """
    信息需求持有者
    """
    
    def __init__(self):
        self.requirements: Dict[str, InfoRequirement] = {}
    
    def get_or_create(self, conversation_id: str) -> InfoRequirement:
        if conversation_id not in self.requirements:
            self.requirements[conversation_id] = InfoRequirement()
        return self.requirements[conversation_id]
    
    def clear(self, conversation_id: str):
        if conversation_id in self.requirements:
            del self.requirements[conversation_id]
```

---

## 在 Agent 中的集成

```python
# 文件: meta_agent/agent.py

class Agent:
    
    def __init__(self, ...):
        # ... 现有初始化 ...
        
        # 信息提取相关
        self.info_requirement_holder = InfoRequirementHolder()
        self.info_extractor = InfoExtractor(
            llm_manager=self.llm_manager,
            conversation_manager=self.conversation_manager,
            tool_registry=self.tool_registry,
            memory_manager=self.memory_manager
        )
    
    async def chat(self, message: str, wallet_address: Optional[str] = None, ...):
        
        # === Step 1: 获取/创建会话 ===
        conversation = await self.conversation_manager.get_or_create_conversation(...)
        
        # === Step 2: 获取对话历史（用于信息检查）===
        history_messages = await self.conversation_manager.get_messages_for_llm(...)
        
        # === Step 3: 任务规划 + 声明信息需求 ===
        info_requirement = self.info_requirement_holder.get_or_create(conversation.id)
        task_planner = TaskPlanner(self.llm_manager, info_requirement)
        
        context = {
            "user_id": owner_id,
            "wallet_address": wallet_address,
            ...
        }
        
        task_plan = await task_planner.plan(message, context)
        
        # === Step 4: 信息存在性检查（核心触发机制）===
        availability_checker = InfoAvailabilityChecker(
            self.memory_manager,
            self.conversation_manager
        )
        
        # 将最近消息转换为 dict 格式
        recent_messages = [
            {"content": msg.get("content", ""), "role": msg.get("role", "")}
            for msg in history_messages[:50]  # 最近50条
        ]
        
        check_result = await availability_checker.check(
            info_requirement.get_required_unfulfilled(),
            owner_id,
            recent_messages
        )
        
        # === Step 5: 判断是否需要调用 InfoExtractor ===
        if check_result["missing"]:
            # 有缺失信息，调用 InfoExtractor 从全量历史消息中提取
            extracted = await self.info_extractor.extract(
                check_result["missing"],
                owner_id
            )
            
            # 合并已找到的信息
            for need_id, value in extracted.items():
                info_requirement.fulfill(need_id, value)
        
        # === Step 6: 构建检索上下文 ===
        retrieval_context = ""
        fulfilled = info_requirement.get_unfulfilled()
        if fulfilled:
            retrieval_context = "## 已获取的信息\n\n"
            for need in fulfilled:
                if need.value:
                    retrieval_context += f"- {need.name}: {need.value}\n"
        
        # === Step 7: 正常 Chat 流程 ===
        # ... 构建消息、调用 LLM、执行工具 ...
```

---

## 文件结构

```
meta_agent/
├── agent.py                          # Agent 主类
├── info/
│   ├── __init__.py
│   ├── types.py                     # 数据类型定义
│   ├── requirement.py               # InfoRequirement
│   ├── holder.py                     # InfoRequirementHolder
│   ├── planner.py                    # TaskPlanner
│   ├── availability_checker.py       # InfoAvailabilityChecker（触发检查）
│   ├── intent_analyzer.py            # IntentAnalyzer
│   ├── candidate_search.py           # CandidateSearch
│   ├── llm_extractor.py             # LLMExtractor
│   ├── validator.py                  # Validator
│   └── extractor.py                  # InfoExtractor 主类
└── ...
```

---

## 触发机制流程（简化版）

```
任务规划
    │
    ▼
声明需要的信息 (InfoNeed)
    │
    ▼
检查 1: 最近消息列表 ──→ 找到? ──Yes──→ 标记已满足
    │                         │
    │                        No
    ▼                         │
检查 2: important_memories ──→ 找到? ──Yes──→ 标记已满足
    │                         │
    │                        No
    ▼                         ▼
都找不到 ──────────────────────────→ 调用 InfoExtractor
                                         │
                                         ▼
                              从全量历史消息中提取
                                         │
                                         ▼
                              逐条搜索 → 逐条提取 → 逐条验证
                                         │
                                         ▼
                              验证通过 → 更新记忆 → 返回提取的信息
```

---

# 代码改动对比

## 改动位置

主要改动在 `agent.py` 的 `chat` 方法中，约在第 670-940 行之间。

---

## 对比详情

### 改动1: 初始化部分（新增）

**原有代码**: 无此部分

**改动后代码**: 新增 InfoExtractor 组件初始化

```python
# === 新增：信息提取相关初始化 ===
self.info_requirement_holder = InfoRequirementHolder()
self.info_extractor = InfoExtractor(
    llm_manager=self.llm_manager,
    conversation_manager=self.conversation_manager,
    tool_registry=self.tool_registry,
    memory_manager=self.memory_manager
)
```

---

### 改动2: 获取对话历史后（新增 Step 1-3）

**原有代码** (第 722-727 行):
```python
# 获取对话历史
history_messages = await self.conversation_manager.get_messages_for_llm(
    conversation_id=conversation.id,
    accessor_id=owner_id,
    max_tokens=2000,
)
```

**改动后代码** (第 722-727 行后新增):
```python
# 获取对话历史
history_messages = await self.conversation_manager.get_messages_for_llm(
    conversation_id=conversation.id,
    accessor_id=owner_id,
    max_tokens=2000,
)

# === 新增 Step 1: 任务规划 + 声明信息需求 ===
info_requirement = self.info_requirement_holder.get_or_create(conversation.id)
task_planner = TaskPlanner(self.llm_manager, info_requirement)

context = {
    "user_id": owner_id,
    "wallet_address": wallet_address,
    "message": message,
    "available_tools": [t["name"] for t in self.tool_registry.list_tools()],
}

task_plan = await task_planner.plan(message, context)
logger.info(f"Task planned: {task_plan.description}, info needs: {len(task_plan.required_info)}")

# === 新增 Step 2: 信息存在性检查 ===
availability_checker = InfoAvailabilityChecker(
    self.memory_manager,
    self.conversation_manager
)

recent_messages = [
    {"content": msg.get("content", ""), "role": msg.get("role", "")}
    for msg in history_messages[:50]
]

check_result = await availability_checker.check(
    info_requirement.get_required_unfulfilled(),
    owner_id,
    recent_messages
)

logger.info(f"Info availability: fulfilled={len(check_result['fulfilled'])}, missing={len(check_result['missing'])}")

# === 新增 Step 3: 判断是否调用 InfoExtractor ===
if check_result["missing"]:
    logger.info(f"Missing info, calling InfoExtractor for: {[n.name for n in check_result['missing']]}")
    extracted = await self.info_extractor.extract(
        check_result["missing"],
        owner_id
    )
    
    for need_id, value in extracted.items():
        info_requirement.fulfill(need_id, value)
        logger.info(f"Extracted info for {need_id}: {value[:30]}...")
else:
    logger.info("All info needs fulfilled from recent messages/memories")
```

---

### 改动3: 替换原有的智能信息检索（删除旧逻辑）

**原有代码** (第 764-820 行) - 需要删除:
```python
# ========== 智能信息检索 ==========
# 当用户问需要之前提供的信息时，从历史对话中检索
retrieval_context = ""

logger.debug(f"Starting retrieval check for message: {message[:50]}...")

try:
    # 使用敏感信息注册表获取关键词（替代硬编码）
    info_keywords = self.sensitive_registry.get_all_keywords()
    need_retrieval = any(kw in message.lower() for kw in info_keywords)

    if need_retrieval:
        task_info = {"task_description": message, "needed_info_type": "用户之前提供的信息"}
        logger.info(f"Need retrieval for: {message[:30]}...")

        # 获取候选消息
        candidates = await self._get_all_candidate_info(owner_id)
        print(f"[RETRIEVAL] Candidates count: {len(candidates)}")

        if candidates:
            # 让 LLM 从所有候选中找出需要的信息
            try:
                found_info = await self._find_info_from_candidates(candidates, task_info)
                logger.debug(f"Found info: {found_info[:50] if found_info else 'None'}...")
            except Exception as e:
                logger.error(f"Error in _find_info_from_candidates: {e}")
                found_info = None

            if found_info:
                retrieval_context = self._format_found_info({"content": found_info})
                logger.info("Set retrieval_context!")
            else:
                # 直接返回候选内容
                candidate_text = "\n\n".join(
                    [
                        f"消息{i + 1} [{c.get('role', '')}]: {c.get('content', '')[:self.chat_config.candidate_content_length]}..."
                        for i, c in enumerate(candidates[:self.chat_config.display_candidates_limit])
                    ]
                )
                retrieval_context = f"## 从历史对话中找到以下相关内容：\n\n{candidate_text}"
                logger.info("Set retrieval_context with candidates")

except Exception as e:
    logger.warning(f"Retrieval failed: {e}")

# 如果检索到信息，使用检索结果
if retrieval_context:
    logger.debug(f"Setting smart_recall_context: {retrieval_context[:100]}...")
    smart_recall_context = retrieval_context
    # 动态更新记忆
    if self.memory_manager:
        try:
            await self.memory_manager.dynamic_update_from_recall(
                user_id=owner_id, recalled_content=retrieval_context, source="agent_chat"
            )
        except Exception as e:
            logger.warning(f"Failed to dynamic update memories: {e}")
```

**改动后代码**: 删除原有逻辑，替换为:
```python
# ========== 构建检索上下文（来自信息需求） ==========
retrieval_context = ""
fulfilled_needs = info_requirement.get_unfulfilled()
if fulfilled_needs:
    retrieval_context = "## 已获取的信息\n\n"
    for need in fulfilled_needs:
        if need.value:
            retrieval_context += f"- {need.name}: {need.value}\n"

# 如果有检索上下文，合并到 smart_recall_context
if retrieval_context:
    smart_recall_context = retrieval_context
    logger.info(f"Set smart_recall_context from info needs: {len(retrieval_context)} chars")
```

---

### 改动4: 构建用户信息部分（无变化）

**原有代码**: 第 831-838 行

**改动后代码**: 保持不变

---

### 改动5: 构建消息部分（新增 context 参数）

**原有代码** (第 845-853 行):
```python
# 构建完整的消息列表
messages = await self.context_manager.build_messages(
    user_message=message,
    conversation_history=history_messages,
    user_info=user_info,
    available_tools=tool_names,
    memory_context=memory_context,
    smart_recall_context=smart_recall_context,
)
```

**改动后代码**: 保持不变（smart_recall_context 已经包含了检索到的信息）

---

## 改动总结

| 改动位置 | 改动类型 | 说明 |
|---------|---------|------|
| `__init__` | 新增 | 初始化 InfoExtractor 组件 |
| chat 方法开头 | 新增 | Step 1: TaskPlanner 任务规划 + 声明信息需求 |
| chat 方法获取历史后 | 新增 | Step 2: InfoAvailabilityChecker 检查信息是否存在 |
| chat 方法获取历史后 | 新增 | Step 3: 判断是否调用 InfoExtractor |
| 第 764-820 行 | 删除 | 删除原有的关键词检索逻辑 |
| 构建 smart_recall_context | 替换 | 用 info_requirement 中的信息替换原来的检索逻辑 |

---

## 需要删除的旧方法

改动后，以下旧方法将不再使用，可以考虑删除或保留作为降级:

- `_get_all_candidate_info` (约第 1126-1174 行)
- `_find_info_from_candidates` (约第 1203-1253 行)
- `_validate_info_with_llm` (约第 1255-1294 行)
- `_extract_all_sensitive_values` (约第 1176-1201 行)
- `_format_found_info` (约第 1381 行附近)
- `_try_real_api_validation` (约第 1301-1320 行)

---

**确认改动可行后，开始编写代码**
