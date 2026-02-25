# 信息提取器 (InfoExtractor) 重构设计方案

## 背景

当前 `chat` 方法中的历史消息检索逻辑存在以下问题：

1. **关键词过于宽泛** - 使用预定义关键词搜索，无法处理随机信息需求
2. **截断处理** - 只截取前300字符，上下文丢失
3. **合并判断** - 多条消息合并让 LLM 判断，相关度下降
4. **时间排序** - 按时间排序而非相关度
5. **缺少验证** - 提取后没有验证机制

---

## 需求对齐

### 核心原则

1. **不依赖预定义关键词** - 根据用户问题判断需要检索什么
2. **全文本处理** - 不截断，用完整内容让 LLM 判断
3. **逐条提取** - 每条消息单独让 LLM 提取，不是合并判断
4. **相关度排序** - 按 LLM 判断的相关度排序，不是时间
5. **验证机制** - 提取后需要验证有效性
6. **独立模块** - 信息提取是独立流程，结果注入 chat 上下文

---

## 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                         InfoExtractor                            │
│                    (信息提取器 - 独立模块)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐                                           │
│  │ IntentAnalyzer  │ ←── 分析用户问题，判断需要找什么信息         │
│  │   (意图分析)     │                                            │
│  └────────┬────────┘                                           │
│           │                                                    │
│           ↓                                                    │
│  ┌─────────────────┐                                           │
│  │CandidateSearch  │ ←── 语义搜索，全文本，按相关度排序          │
│  │   (候选搜索)     │                                            │
│  └────────┬────────┘                                           │
│           │                                                    │
│           ↓                                                    │
│  ┌─────────────────┐                                           │
│  │LLMExtractor    │ ←── 逐条 LLM 提取，每条单独处理             │
│  │ (逐条提取)      │                                            │
│  └────────┬────────┘                                           │
│           │                                                    │
│           ↓                                                    │
│  ┌─────────────────┐                                           │
│  │   Validator     │ ←── 工具调用验证 / LLM 验证                 │
│  │    (验证器)     │                                            │
│  └────────┬────────┘                                           │
│           │                                                    │
│           ↓                                                    │
│      ExtractedInfo ←── 提取到的有效信息                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 模块详细设计

### 1. IntentAnalyzer（意图分析器）

**职责**: 分析用户问题，判断需要检索什么信息

**输入**: 用户问题
**输出**: RetrievalIntent

```python
class RetrievalIntent:
    info_type: str           # 信息类型: "xialiao_api_key", "github_url", "password" 等
    description: str         # 描述需要找什么
    format_hint: str         # 格式提示: "xialiao_开头，32位字母数字"
    validation_hint: str     # 验证提示: "调用 xialiao API 验证"
    need_tool_validation: bool  # 是否需要工具验证
    tool_name: str          # 工具名称（如果需要）
```

**示例**:

| 用户问题 | info_type | format_hint |
|----------|-----------|-------------|
| 我的xialiao api key是多少？ | xialiao_api_key | xialiao_开头，32位字母数字 |
| 之前给我的GitHub链接是什么？ | github_url | github.com/用户名/仓库名 |
| 上次那个密码是多少？ | password | 任意字符串 |

---

### 2. CandidateSearch（候选搜索器）

**职责**: 语义搜索获取候选，全文本，按相关度排序

**输入**: user_id, RetrievalIntent
**输出**: List[CandidateMessage]（已按相关度排序）

**关键点**:
- 使用语义描述搜索，不是关键词
- 返回全文本，不截断
- 用 LLM 按相关度排序，不是时间

---

### 3. LLMExtractor（逐条提取器）

**职责**: 逐条让 LLM 从候选消息中提取信息

**输入**: 单条 CandidateMessage, RetrievalIntent
**输出**: ExtractedInfo 或 None

**关键点**:
- 每条消息单独处理
- LLM 判断这条消息是否包含目标信息
- 返回提取到的具体值和置信度

---

### 4. Validator（验证器）

**职责**: 验证提取到的信息是否有效

**输入**: ExtractedInfo, RetrievalIntent
**输出**: ValidationResult

**验证方式**:

| 情况 | 验证方式 |
|------|----------|
| 有对应工具 | 直接调用工具验证（如调用 xialiao API 检查 key 是否有效） |
| 无工具 | 让 LLM 判断找到的信息是否符合格式要求 |

---

### 5. InfoExtractor（编排器）

**职责**: 编排整个提取流程

**流程**:

```
1. IntentAnalyzer 分析用户问题 → RetrievalIntent
2. CandidateSearch 搜索候选（全文本，相关度排序）
3. 遍历候选:
   a. LLMExtractor 提取信息
   b. Validator 验证
   c. 验证通过 → 返回 ExtractedInfo
   d. 验证失败 → 继续下一条
4. 所有候选都失败 → 返回 None
5. 验证通过 → 可选：更新记忆
```

---

## 在 chat 中的使用

```python
async def chat(self, message: str, wallet_address: Optional[str] = None, ...):
    # ... 现有逻辑 ...

    # === 信息提取（独立流程）===
    extraction_result = None
    
    if self.info_extractor.should_extract(message):
        extraction_result = await self.info_extractor.extract(
            user_question=message,
            user_id=owner_id
        )
    
    # === 构建 chat 上下文 ===
    if extraction_result:
        # 提取到的信息，注入上下文
        retrieval_context = f"## 从历史对话中找到的信息\n\n{extraction_result.value}"
    else:
        retrieval_context = ""

    # ... 后续现有逻辑 ...
```

---

## 文件结构

```
meta_agent/
├── agent.py                    # chat 方法调用 InfoExtractor
├── info/
│   ├── __init__.py
│   ├── extractor.py           # InfoExtractor 主类
│   ├── intent_analyzer.py     # IntentAnalyzer
│   ├── candidate_search.py     # CandidateSearch  
│   ├── llm_extractor.py       # LLMExtractor
│   └── validator.py           # Validator
└── ...
```

---

## 需确认问题

1. **是否需要保留现有检索逻辑作为降级方案？**
2. **意图分析是否需要限制类型（如只能在已知类型中匹配）？**
3. **候选消息数量限制多少合适？（建议 20-50 条）**
4. **验证失败后的行为：继续尝试还是直接返回失败？**

---

**确认后开始编写代码**
