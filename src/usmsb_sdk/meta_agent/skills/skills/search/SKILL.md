# Search

## Metadata
- **Name**: search
- **Description**: 搜索知识库和互联网信息。当用户询问事实性问题、需要查找资料或需要验证信息时使用。
- **Version**: 1.0.0
- **Author**: usmsb
- **Category**: information

## Triggers
When should this skill be activated?
- 用户询问事实性问题（"什么是X"、"X是什么"）
- 用户需要查找特定信息
- 用户要求验证某个说法是否正确
- 用户请求搜索某个主题

## Instructions

### 搜索流程

1. **分析查询**: 理解用户要查找什么信息
2. **选择来源**:
   - `knowledge`: 内部知识库（已加载到上下文的文档）
   - `web`: 互联网搜索
   - `all`: 两都都搜索
3. **执行搜索**: 使用适当的工具执行搜索
4. **整理结果**: 返回清晰、结构化的答案

### 搜索技巧

1. 使用精确的关键词
2. 优先使用内部知识库（更可靠）
3. 引用搜索结果时注明来源
4. 如果搜索无结果，诚实告知用户

## Parameters
- `query`: string - 搜索关键词
- `source`: string - 数据源：knowledge/web/all

## Scripts
Available scripts in `scripts/`:
- `search_knowledge.py` - 搜索内部知识库
- `search_web.py` - 搜索互联网

## References
- `references/search_tips.md` - 搜索技巧
