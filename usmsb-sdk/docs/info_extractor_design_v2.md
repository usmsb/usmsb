# 信息提取器 (InfoExtractor) 重构设计方案 v2

## 背景

当前 `chat` 方法中的历史消息检索逻辑存在以下问题：

1. **关键词过于宽泛** - 使用预定义关键词搜索，无法处理随机信息需求
2. **截断处理** - 只截取前300字符，上下文丢失
3. **合并判断** - 多条消息合并让 LLM 判断，相关度下降
4. **时间排序** - 按时间排序而非相关度
5. **缺少验证** - 提取后没有验证机制
6. **触发时机不当** - 收到消息就判断，而不是任务过程中缺失信息时调用

---

## 需求对齐 v2

1. **不保留旧逻辑** - 直接去除旧代码，进行重构
2. **意图分析不限制类型** - 根据实际情况需要什么找什么
3. **候选消息数量不做限制** - 按相关度依次验证，找到有用信息就停止
4. **验证失败继续** - 继续尝试下一条，直到遍历完所有候选
5. **成功更新记忆** - 验证通过后更新到 important_memories 表
6. **触发机制** - 任务执行过程中缺失信息时才调用

---

## 架构设计

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Agent Chat 流程                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐     ┌─────────────────┐     ┌─────────────────────┐    │
│   │  用户消息    │ ──→ │  任务规划器      │ ──→ │  信息需求声明器      │    │
│   └─────────────┘     │ TaskPlanner     │     │  InfoRequirement     │    │
│                       └────────┬────────┘     └──────────┬──────────┘    │
│                                │                         │                │
│                                ↓                         ↓                │
│                       ┌─────────────────┐     ┌─────────────────────┐    │
│                       │  执行计划        │     │  声明需要的信息      │    │
│                       │  (需要哪些信息)  │     │  list[InfoNeed]    │    │
│                       └────────┬────────┘     └──────────┬──────────┘    │
│                                │                         │                │
│                                ↓                         ↓                │
│                       ┌─────────────────────────────────────────────────┐   │
│                       │           信息缺口检测器                         │   │
│                       │        InfoGapDetector                         │   │
│                       │  - 检查已持有信息 vs 需要的信息                   │   │
│                       │  - 识别缺失的信息                               │   │
│                       └────────────────────┬────────────────────────┘   │
│                                            │                            │
│                                            ↓                            │
│                       ┌─────────────────────────────────────────────────┐ │
│                       │              InfoExtractor                      │ │
│                       │   (缺失信息时调用，从历史消息中提取)              │ │
│                       └────────────────────┬────────────────────────┘   │
│                                            │                            │
│                                            ↓                            │
│                       ┌─────────────────────────────────────────────────┐ │
│                       │           信息验证 + 记忆更新                    │ │
│                       └─────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 核心模块设计

### 模块1: InfoNeed（信息需求声明）

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
    
    在任务规划阶段声明需要哪些信息，但不立即获取
    而是等执行时检查是否已持有
    """
    need_id: str                  # 唯一标识
    name: str                     # 信息名称 (如 "虾聊API Key")
    info_type: InfoNeedType       # 信息类型
    description: str              # 描述需要找什么
    format_hint: str             # 格式提示 (可选)
    validation_hint: str          # 验证提示 (可选)
    required: bool = True         # 是否必须
    source: str = "user"          # 来源: user/system/llm
    
    # 验证相关
    need_tool_validation: bool = False  # 是否需要工具验证
    tool_name: str = ""           # 验证工具名称
    tool_params: dict = None      # 工具参数
    
    # 状态
    fulfilled: bool = False      # 是否已满足
    value: Optional[str] = None   # 已获取的值
```

---

### 模块2: InfoRequirement（信息需求声明器）

```python
# 文件: meta_agent/info/requirement.py

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
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
        tool_name: str = "",
        tool_params: dict = None
    ) -> str:
        """
        声明一个信息需求
        
        Args:
            name: 信息名称
            info_type: 信息类型
            description: 描述
            format_hint: 格式提示
            validation_hint: 验证提示
            required: 是否必须
            need_tool_validation: 是否需要工具验证
            tool_name: 工具名称
            
        Returns:
            need_id: 声明的 ID
        """
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
            tool_name=tool_name,
            tool_params=tool_params or {}
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

### 模块3: TaskPlanner（任务规划器 + 信息需求声明）

```python
# 文件: meta_agent/info/planner.py

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class TaskType(Enum):
    GENERAL = "general"
    POST_TO_PLATFORM = "post_to_platform"      # 发帖到平台
    REPLY_POST = "reply_post"                  # 回复帖子
    API_CALL = "api_call"                      # API 调用
    FILE_OPERATION = "file_operation"          # 文件操作
    # 可以继续扩展...

@dataclass
class TaskPlan:
    """任务计划"""
    task_type: TaskType
    description: str
    required_info: List[InfoNeed]  # 声明需要的信息
    steps: List[str]               # 执行步骤
    # ... 其他字段

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
            "name": "信息名称",
            "info_type": "credential/account/url/reference/context/other",
            "description": "描述需要什么信息",
            "format_hint": "格式提示（如有）",
            "validation_hint": "验证提示（如有）",
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
- 如果需要网址链接，声明为 url 类型
- 如果需要参考资料，声明为 reference 类型
- format_hint 描述正确的格式，帮助后续验证
"""
        
        response = await self.llm.chat(prompt)
        # 解析 JSON ...
        
        # 转换为 TaskPlan，并声明信息需求
        # ...
        
        # 声明信息需求
        for info in parsed.get("required_info", []):
            self.info_requirement.declare(
                name=info["name"],
                info_type=info["info_type"],
                description=info["description"],
                format_hint=info.get("format_hint", ""),
                validation_hint=info.get("validation_hint", ""),
                required=info.get("required", True),
                need_tool_validation=info.get("need_tool_validation", False),
                tool_name=info.get("tool_name", "")
            )
        
        return task_plan
```

---

### 模块4: InfoGapDetector（信息缺口检测器）

```python
# 文件: meta_agent/info/gap_detector.py

class InfoGapDetector:
    """
    信息缺口检测器
    
    检查已持有的信息 vs 需要的信息
    识别缺失的信息
    """
    
    def __init__(
        self, 
        memory_manager,
        info_requirement: InfoRequirement
    ):
        self.memory_manager = memory_manager
        self.info_requirement = info_requirement
    
    async def detect_gaps(self, user_id: str) -> List[InfoNeed]:
        """
        检测信息缺口
        
        对比已持有的信息和需要的信息
        返回缺失的信息列表
        """
        
        # 1. 获取未满足的需求
        unfulfilled = self.info_requirement.get_required_unfulfilled()
        
        if not unfulfilled:
            return []
        
        # 2. 检查每个需求是否已持有
        gaps = []
        
        for need in unfulfilled:
            # 先检查内存中是否已有
            if self.info_requirement.is_fulfilled(need.need_id):
                continue
            
            # 检查记忆是否已存储
            stored_value = await self.memory_manager.get_stored_entity(
                user_id=user_id,
                entity_type=need.info_type.value,
                name=need.name
            )
            
            if stored_value:
                # 记忆中有，标记为已满足
                self.info_requirement.fulfill(need.need_id, stored_value)
            else:
                # 缺失，需要提取
                gaps.append(need)
        
        return gaps
```

---

### 模块5: IntentAnalyzer（意图分析器）

```python
# 文件: meta_agent/info/intent_analyzer.py

class RetrievalIntent:
    """检索意图"""
    def __init__(
        self,
        info_type: str,           # 信息类型
        description: str,          # 描述
        format_hint: str = "",     # 格式提示
        validation_hint: str = "", # 验证提示
        need_tool_validation: bool = False,
        tool_name: str = ""
    ):
        self.info_type = info_type
        self.description = description
        self.format_hint = format_hint
        self.validation_hint = validation_hint
        self.need_tool_validation = need_tool_validation
        self.tool_name = tool_name


class IntentAnalyzer:
    """
    意图分析器
    
    将 InfoNeed 转换为检索意图
    或从用户问题直接分析需要检索什么
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

注意：
- 如果用户问题表明需要查找之前提供的信息，设置 need_retrieval: true
- info_type 要具体描述
- format_hint 描述正确格式（如 API Key 应该是 xialiao_xxx 格式）
"""
        
        response = await self.llm.chat(prompt)
        # 解析 JSON ...
        
        if not data.get("need_retrieval"):
            return None
        
        return RetrievalIntent(
            info_type=data.get("info_type", "other"),
            description=data.get("description", ""),
            format_hint=data.get("format_hint", ""),
            validation_hint=data.get("validation_hint", "")
        )
```

---

### 模块6: CandidateSearch（候选搜索器）

```python
# 文件: meta_agent/info/candidate_search.py

class CandidateMessage:
    """候选消息"""
    def __init__(
        self,
        message_id: str,
        content: str,       # 全文本，不截断
        role: str,
        timestamp: float,
        conversation_title: str = ""
    ):
        self.message_id = message_id
        self.content = content
        self.role = role
        self.timestamp = timestamp
        self.conversation_title = conversation_title


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
        limit: int = 50
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
            limit=limit * 2  # 多搜一些用于排序
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
        ranked = await self._rank_by_relevance(candidates, intent, limit)
        
        return ranked
    
    async def _rank_by_relevance(
        self,
        candidates: List[CandidateMessage],
        intent: RetrievalIntent,
        limit: int
    ) -> List[CandidateMessage]:
        """
        用 LLM 按相关度排序
        """
        
        candidates_text = "\n".join([
            f"[{i}] 角色:{c.role} 时间:{c.timestamp}\n内容:{c.content[:500]}"
            for i, c in enumerate(candidates[:30])
        ])
        
        prompt = f"""给定用户检索意图，对候选消息按与意图的相关度排序。

用户想要找: {intent.description}
信息类型: {intent.info_type}
格式要求: {intent.format_hint}

候选消息:
{candidates_text}

请返回按相关度排序的候选索引（最相关的在前，最多 {limit} 个）:
{{
    "ranked_indices": [索引列表],
    "reasoning": "简要说明排序理由"
}}

注意：
- 只返回真正可能包含目标信息的候选
- 排除明显不相关的消息
"""
        
        response = await self.llm.chat(prompt)
        # 解析 JSON 获取排序索引...
        
        ranked_indices = data.get("ranked_indices", [])[:limit]
        
        return [candidates[i] for i in ranked_indices if i < len(candidates)]
```

---

### 模块7: LLMExtractor（逐条提取器）

```python
# 文件: meta_agent/info/llm_extractor.py

class ExtractedInfo:
    """提取到的信息"""
    def __init__(
        self,
        value: str,
        confidence: float,
        source_message_id: str,
        reasoning: str
    ):
        self.value = value
        self.confidence = confidence
        self.source_message_id = source_message_id
        self.reasoning = reasoning


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
时间: {candidate.timestamp}
内容:
{candidate.content}
---

请判断这条消息是否包含用户需要的信息。

返回JSON:
{{
    "contains_target_info": true/false,
    "extracted_value": "提取到的具体信息（如果没有则为空字符串）",
    "confidence": 0.0-1.0,
    "reasoning": "判断理由"
}}

关键点：
- 严格按 format_hint 判断格式是否正确
- 如果格式完全符合，设置高置信度
- 如果格式不完全符合但可能是有效信息，设置中置信度
- 如果完全不包含目标信息，设置 contains_target_info: false
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

### 模块8: Validator（验证器）

```python
# 文件: meta_agent/info/validator.py

class ValidationResult:
    """验证结果"""
    def __init__(
        self,
        is_valid: bool,
        validated_value: Optional[str] = None,
        method: str = "",  # "tool_call" / "llm"
        error: str = ""
    ):
        self.is_valid = is_valid
        self.validated_value = validated_value
        self.method = method
        self.error = error


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
                    error=f"验证失败: {result.get('error', 'unknown')}"
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
验证方法是: {intent.validation_hint}

找到的信息: {extracted_info.value}
置信度: {extracted_info.confidence}

请判断这个信息是否正确有效。

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
            method="llm",
            reasoning=data.get("reasoning", "")
        )
```

---

### 模块9: InfoExtractor（编排器）

```python
# 文件: meta_agent/info/extractor.py

class InfoExtractor:
    """
    信息提取器 - 编排整个提取流程
    
    在任务执行过程中，当缺失信息时调用
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
        
        # 初始化子模块
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
            info_needs: 需要的信息列表
            user_id: 用户ID
            
        Returns:
            dict: {need_id: extracted_value} - 提取到的信息
        """
        
        results = {}
        
        for need in info_needs:
            # 转换为检索意图
            intent = await self.intent_analyzer.analyze_from_need(need)
            
            # 搜索候选
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
                    
                    # 更新需求声明
                    need.fulfilled = True
                    need.value = validation.validated_value
                    
                    # 可选：更新记忆
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

### 模块10: InfoRequirementHolder（信息需求持有者）

```python
# 文件: meta_agent/info/holder.py

class InfoRequirementHolder:
    """
    信息需求持有者
    
    在 Agent 生命周期内持有信息需求
    跨多个步骤共享
    """
    
    def __init__(self):
        self.requirements: Dict[str, InfoRequirement] = {}  # key: conversation_id
    
    def get_or_create(self, conversation_id: str) -> InfoRequirement:
        """获取或创建会话的信息需求"""
        if conversation_id not in self.requirements:
            self.requirements[conversation_id] = InfoRequirement()
        return self.requirements[conversation_id]
    
    def clear(self, conversation_id: str):
        """清空会话的信息需求"""
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
    
    async def chat(self, message: str, ...):
        # ... 现有逻辑 ...
        
        # Step 1: 任务规划 + 声明信息需求
        info_requirement = self.info_requirement_holder.get_or_create(conversation.id)
        task_planner = TaskPlanner(self.llm_manager, info_requirement)
        
        # 让 LLM 分析任务并声明需要的信息
        task_plan = await task_planner.plan(message, context)
        
        # Step 2: 检测信息缺口
        gap_detector = InfoGapDetector(self.memory_manager, info_requirement)
        gaps = await gap_detector.detect_gaps(owner_id)
        
        # Step 3: 如果有缺失信息，调用 InfoExtractor
        if gaps:
            extracted = await self.info_extractor.extract(gaps, owner_id)
            
            # 提取到的信息注入上下文
            if extracted:
                retrieval_context = "## 已获取的信息\n\n"
                for need_id, value in extracted.items():
                    retrieval_context += f"- {need_id}: {value}\n"
        
        # Step 4: 继续正常的 chat 流程
        # ... 
```

---

## 文件结构

```
meta_agent/
├── agent.py                          # Agent 主类，集成信息提取
├── info/
│   ├── __init__.py
│   ├── types.py                      # InfoNeed, RetrievalIntent 等数据类型
│   ├── requirement.py               # InfoRequirement 信息需求声明器
│   ├── holder.py                     # InfoRequirementHolder 持有者
│   ├── planner.py                    # TaskPlanner 任务规划器
│   ├── gap_detector.py               # InfoGapDetector 缺口检测器
│   ├── intent_analyzer.py            # IntentAnalyzer 意图分析器
│   ├── candidate_search.py           # CandidateSearch 候选搜索器
│   ├── llm_extractor.py              # LLMExtractor 逐条提取器
│   ├── validator.py                   # Validator 验证器
│   └── extractor.py                   # InfoExtractor 主类
└── ...
```

---

## 触发流程图

```
用户消息
    │
    ▼
┌─────────────────────┐
│  TaskPlanner        │ ← 分析任务 + 声明需要的信息
│  (任务规划)          │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  InfoGapDetector    │ ← 检查已持有 vs 需要
│  (缺口检测)          │
└─────────┬───────────┘
          │
          ▼
     有缺失信息?
          │
     ┌────┴────┐
     │         │
    是        否
     │         │
     ▼         ▼
┌─────────────────┐  ┌─────────────────┐
│   InfoExtractor  │  │  继续正常流程    │
│  (提取信息)       │  │                 │
└────────┬────────┘  └─────────────────┘
         │
         ▼
   ┌─────────────┐
   │ 逐条搜索    │ ← 语义搜索候选（全文本）
   │ 逐条提取    │ ← 每条单独 LLM 提取
   │ 逐条验证    │ ← 工具验证 / LLM 验证
   └──────┬──────┘
          │
          ▼
    找到有效信息?
          │
     ┌────┴────┐
     │         │
    是        否
     │         │
     ▼         ▼
┌─────────────────┐  ┌─────────────────┐
│ 更新记忆        │  │ 返回未找到       │
│ 返回提取的信息   │  │                 │
└─────────────────┘  └─────────────────┘
```

---

## 需确认问题

1. **触发时机**：是否按上述流程在任务规划阶段触发？还是需要在执行过程中动态触发？

2. **任务规划是否由现有 LLM 调用处理？** 还是需要单独的规划步骤？

3. **是否需要支持"无任务规划"的简单场景？**（如用户直接问"我的 xialiao key 是多少"）

---

**确认后开始编写代码**
