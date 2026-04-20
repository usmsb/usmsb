# Embedding 模型切换指南

本文档介绍 USMSB Meta Agent 支持的三种 Embedding 方案，以及如何切换。

---

## 三种方案对比

| 方案 | 费用 | 质量 | 速度 | 启动依赖 | 适用场景 |
|------|------|------|------|---------|---------|
| **MiniMax Embedding API** | 付费（约 $0.1/千次） | ⭐⭐⭐⭐⭐ 生产级 | 快（云端 API） | 网络 | 正式生产环境 |
| **Sentence Transformers** | 免费 | ⭐⭐⭐⭐ 接近商用 | 中（本地 CPU） | 预下载模型或网络 | 开发者测试、私有部署 |
| **Local Hash（伪向量）** | 免费 | ⭐⭐ 仅字符特征 | 快 | 无 | 演示、离线环境（**默认**） |

---

## 方案一：MiniMax Embedding API

### 特点
- 使用 MiniMax 云端 Embedding 服务
- 1024 维向量，语义理解强
- 需要配置 API Key，有使用费用

### 费用估算
```
启动一次全量建库：~1054 次调用 × $0.0001 ≈ $0.1
每条用户消息：1-3 次调用
一天测试 5 次 + 100 条消息 ≈ $0.5-1
```

### 配置方法

`.env` 中已有配置：
```bash
MINIMAX_API_KEY=your_key_here
```

### 切换到本方案

```bash
EMBEDDING_PROVIDER=minimax
```

---

## 方案二：Sentence Transformers（需要预下载模型）

### 特点
- 本地运行，完全免费
- 使用 `all-MiniLM-L6-v2` 模型（90MB）
- 384 维向量，语义质量接近商用水平
- 支持 Apple Silicon Neural Engine 加速（Mac）
- 支持多核 CPU 加速（服务器）

### 性能参考

**MacBook（M1/M2/M3）**
```
100 条文本 × 512 tokens  →  3-5 秒
1049 条文档全量 embedding →  30-60 秒
```

**服务器（4 核 CPU）**
```
1000 条文档全量 embedding →  20-40 秒
```

**服务器（8 核 CPU）**
```
1000 条文档全量 embedding →  10-20 秒
```

### 安装依赖

```bash
pip install sentence-transformers
```

### 预下载模型（推荐用于生产部署）

**在有网络的环境下预下载模型：**
```bash
# 方法1：使用 Python 下载
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# 模型会下载到 ~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/
```

**查找模型路径：**
```bash
ls ~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/
# 会有一个 hash 目录，进入后可以看到模型文件
```

### 配置方法

**方式1：使用预下载的本地模型（推荐用于生产）**
```bash
EMBEDDING_PROVIDER=sentence_transformers
SENTENCE_TRANSFORMERS_MODEL_PATH=/Users/your_user/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/xxxxxxx
```

**方式2：从 HuggingFace 下载（仅开发测试用，需要网络访问）**
```bash
EMBEDDING_PROVIDER=sentence_transformers
# 不设置 SENTENCE_TRANSFORMERS_MODEL_PATH，会自动从 HuggingFace 下载
```

或通过代码配置：
```python
# 在 MetaAgentConfig 中指定
config = MetaAgentConfig(
    embedding_provider="sentence_transformers"
)
```

### 模型下载位置

首次运行时会自动下载模型（约 90MB）：
```
~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/
```

---

## 方案三：Local Hash（默认方案）

### 特点
- 纯本地计算，无需网络
- 基于 MD5 hash + 词频，**无语义理解能力**
- 搜索仅基于"这个词出现得多不多"，不是真正的语义搜索
- **默认方案**，无需额外配置

### 原理

```
输入: "机器学习是人工智能的一个分支"
1. 取文本的 MD5 hash，取前96个hex字符
2. 将每个hex字符映射到向量维度（0-252）
3. 统计词频，加权到向量
4. L2 归一化输出
```

### 切换到本方案（默认）

```bash
EMBEDDING_PROVIDER=local_hash
```

---

## 统一配置方式

在 `.env` 文件中通过 `EMBEDDING_PROVIDER` 指定：

```bash
# 可选值：
#   local_hash     - Local Hash 伪向量（**默认**）
#   minimax        - MiniMax 云端 API
#   sentence_transformers - Sentence Transformers 本地模型（需预下载或网络访问）

EMBEDDING_PROVIDER=local_hash

# 如使用 sentence_transformers 且有预下载模型：
# SENTENCE_TRANSFORMERS_MODEL_PATH=/path/to/local/model
```

---

## 代码架构

```
LocalEmbeddingService (vector_store.py)
├── __init__(llm_manager, vector_dim)
│   └── 根据 EMBEDDING_PROVIDER 初始化不同后端
│
├── embed(text) → list[float]
│   ├── minimax → _embed_with_api()
│   ├── sentence_transformers → _embed_with_st()
│   │   └── 如设置 SENTENCE_TRANSFORMERS_MODEL_PATH，从本地加载
│   └── local_hash → _embed_local()
│
└── embed_batch(texts) → list[list[float]]
```

---

## 常见问题

**Q: 启动时全量建库调用量太大怎么办？**

A: 有三个解决方向：
1. 知识库已有数据后跳过全量扫描（推荐，看下方"优化建议"）
2. 切换到本地方案（Sentence Transformers 或 Local Hash）
3. 增加 MiniMax 账户余额

**Q: 切换 embedding 方案后需要重建知识库吗？**

A: 需要。不同方案生成的向量维度不同（MiniMax 1024维 vs MiniLM 384维），存在同一数据库里会出错。建议：
```bash
# 删除旧数据库，重启服务自动重建
rm -f data/*_vector.db
```

**Q: Sentence Transformers 在 Mac 上没有 GPU 会不会很慢？**

A: Apple Silicon 有 Neural Engine 加速，比纯 CPU 快 3-5 倍。Intel Mac 会慢一些，但 MiniLM-L6 本身很小（90MB），实测可接受。

**Q: 生产环境推荐哪个方案？**

A:
- **离线/演示环境**：用 Local Hash（默认，无需任何依赖）
- **私有部署有网络**：用 Sentence Transformers + 预下载模型（免费且质量好）
- **正式生产**：用 MiniMax（质量最稳定）

---

## 优化建议：避免重复建库

每次启动都会重新扫描项目建知识库，导致重复 embedding 调用。优化方案：

在 `agent.py` 的 `_load_project_knowledge()` 开头加判断：

```python
async def _load_project_knowledge(self):
    # 跳过：如果知识库已有足够多数据
    try:
        stats = await self.vector_kb.get_stats()
        if stats.get("total", 0) > 500:
            logger.info("Knowledge base already populated, skipping load")
            return
    except:
        pass

    # ... 原有建库逻辑
```

这样只有首次启动会全量建库，后续启动直接用已有数据。
