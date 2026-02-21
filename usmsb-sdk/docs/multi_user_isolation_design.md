# Meta Agent 多用户隔离架构设计文档

> 版本: v1.0
> 日期: 2026-02-21
> 状态: 待确认

---

## 一、项目背景

### 1.1 问题描述

当前 Meta Agent 在多用户场景下存在严重的隔离问题：

| 问题类型 | 当前状态 | 风险等级 |
|---------|---------|---------|
| 代码执行环境 | 全局共享 `exec()` | 🔴 严重 |
| 浏览器实例 | 全局变量 `_browser_instance` | 🔴 严重 |
| 技能缓存 | 全局共享 `_skills_cache` | 🟡 中等 |
| 文件系统 | 无用户工作空间隔离 | 🔴 严重 |
| 数据存储 | 单一数据库文件 | 🟡 中等 |

### 1.2 设计目标

1. **安全性**：不同用户之间的数据、执行环境、资源完全隔离
2. **可扩展性**：支持分布式节点部署，用户可在不同节点间迁移
3. **性能**：隔离机制不应显著影响系统性能
4. **用户体验**：用户无感知切换，数据可跨节点访问

### 1.3 架构决策

基于讨论确认以下决策：

| 决策点 | 选择 | 说明 |
|-------|------|------|
| 用户跨节点场景 | C：固定绑定节点，偶尔切换 | 提供数据迁移而非实时同步 |
| 数据同步策略 | B：读写分离 | 写本地，读时可从IPFS拉取 |
| Docker内隔离 | C：进程级+代码沙箱 | Session Context + RestrictedPython |

---

## 二、整体架构

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           分布式节点网络                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│    ┌──────────────────────────┐     ┌──────────────────────────┐       │
│    │       节点 A (Docker)     │     │       节点 B (Docker)     │       │
│    │                          │     │                          │       │
│    │  ┌────────────────────┐  │     │  ┌────────────────────┐  │       │
│    │  │  Session Manager   │  │     │  │  Session Manager   │  │       │
│    │  │                    │  │     │  │                    │  │       │
│    │  │ ┌──────┐ ┌──────┐  │  │     │  │ ┌──────┐ ┌──────┐  │  │       │
│    │  │ │User A│ │User B│  │  │     │  │ │User C│ │User D│  │  │       │
│    │  │ │Session│Session│  │  │     │  │ │Session│Session│  │  │       │
│    │  │ └──────┘ └──────┘  │  │     │  │ └──────┘ └──────┘  │  │       │
│    │  └────────────────────┘  │     │  └────────────────────┘  │       │
│    │                          │     │                          │       │
│    │  ┌────────────────────┐  │     │  ┌────────────────────┐  │       │
│    │  │   Local Storage    │  │     │  │   Local Storage    │  │       │
│    │  │   /data/users/     │  │     │  │   /data/users/     │  │       │
│    │  └────────────────────┘  │     │  └────────────────────┘  │       │
│    │                          │     │                          │       │
│    │  ┌────────────────────┐  │     │  ┌────────────────────┐  │       │
│    │  │    IPFS Client     │◄─┼─────┼──│    IPFS Client     │  │       │
│    │  └────────────────────┘  │     │  └────────────────────┘  │       │
│    └──────────────────────────┘     └──────────────────────────┘       │
│                    │                            │                       │
│                    └────────────┬───────────────┘                       │
│                                 ▼                                       │
│                    ┌────────────────────────┐                          │
│                    │      IPFS 网络          │                          │
│                    │                        │                          │
│                    │  /users/{wallet}/      │                          │
│                    │    ├── profile.enc     │                          │
│                    │    └── knowledge.enc   │                          │
│                    └────────────────────────┘                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          数据读写流程                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  【写入流程 - 始终写本地】                                               │
│                                                                         │
│   用户请求 ──► UserSession ──► Local Database                           │
│                    │                                                    │
│                    └──► Workspace (文件)                                │
│                    └──► Sandbox (代码执行)                              │
│                                                                         │
│                                                                         │
│  【读取流程 - 本地优先，可从IPFS拉取】                                    │
│                                                                         │
│   用户请求 ──► UserSession ──► 查询本地 ──► 有数据 ──► 返回             │
│                    │               │                                    │
│                    │               └──► 无数据 ──► 查询IPFS              │
│                    │                              │                     │
│                    │                              ├──► 有数据 ──► 解密   │
│                    │                              │           │         │
│                    │                              │           └──► 存本地│
│                    │                              │              │      │
│                    │                              │              └──► 返回│
│                    │                              │                     │
│                    │                              └──► 无数据 ──► 返回空 │
│                                                                         │
│                                                                         │
│  【同步流程 - 用户主动触发】                                             │
│                                                                         │
│   用户触发 ──► 读取本地数据 ──► 加密 ──► 上传IPFS ──► 返回CID           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.3 用户会话隔离架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     单节点内的用户会话隔离                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        Meta Agent 进程                           │   │
│  │                                                                  │   │
│  │  ┌───────────────────────────────────────────────────────────┐  │   │
│  │  │                    Session Manager                         │  │   │
│  │  │                                                            │  │   │
│  │  │   sessions: Dict[wallet_address, UserSession]              │  │   │
│  │  │                                                            │  │   │
│  │  │   ┌─────────────────┐    ┌─────────────────┐              │  │   │
│  │  │   │  UserSession    │    │  UserSession    │              │  │   │
│  │  │   │  0xAAA...       │    │  0xBBB...       │   互相隔离   │  │   │
│  │  │   │                 │    │                 │◄────────────►│  │   │
│  │  │   │ • workspace     │    │ • workspace     │              │  │   │
│  │  │   │ • sandbox       │    │ • sandbox       │              │  │   │
│  │  │   │ • browser_ctx   │    │ • browser_ctx   │              │  │   │
│  │  │   │ • db            │    │ • db            │              │  │   │
│  │  │   │ • ipfs_client   │    │ • ipfs_client   │              │  │   │
│  │  │   └─────────────────┘    └─────────────────┘              │  │   │
│  │  └───────────────────────────────────────────────────────────┘  │   │
│  │                                                                  │   │
│  │  ┌───────────────────────────────────────────────────────────┐  │   │
│  │  │                    共享组件 (只读/无状态)                   │  │   │
│  │  │                                                            │  │   │
│  │  │   • Tool Registry (工具定义)                               │  │   │
│  │  │   • LLM Manager (API调用)                                  │  │   │
│  │  │   • System Knowledge Base (公共知识)                       │  │   │
│  │  │   • Skills Manager (技能定义)                              │  │   │
│  │  │                                                            │  │   │
│  │  └───────────────────────────────────────────────────────────┘  │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 三、数据存储设计

### 3.1 目录结构

```
/data/
│
├── users/                              # 用户数据根目录
│   │
│   ├── 0xAAA1111.../                   # 用户A (钱包地址作为目录名)
│   │   │
│   │   ├── meta.json                   # 用户元信息
│   │   │   {
│   │   │     "wallet_address": "0xAAA...",
│   │   │     "primary_node": "node-001",
│   │   │     "created_at": 1739788800,
│   │   │     "last_active": 1739875200,
│   │   │     "ipfs_cid": "QmXxx..."   # 最新同步的IPFS CID
│   │   │   }
│   │   │
│   │   ├── conversations.db            # 对话历史 (本地)
│   │   ├── memory.db                   # 记忆/画像 (本地+可同步)
│   │   ├── knowledge.db                # 私有知识库 (本地+可同步)
│   │   │
│   │   ├── workspace/                  # 工作目录
│   │   │   ├── temp/                   # 临时文件
│   │   │   ├── output/                 # 输出文件
│   │   │   └── uploads/                # 用户上传文件
│   │   │
│   │   ├── sandbox/                    # 代码执行沙箱
│   │   │   └── exec_{timestamp}/       # 每次执行的隔离目录
│   │   │
│   │   └── browser/                    # 浏览器数据
│   │       └── user_data/              # Chromium用户数据目录
│   │
│   ├── 0xBBB2222.../                   # 用户B
│   │   └── ...
│   │
│   └── ...
│
├── shared/                             # 节点级共享数据
│   ├── system_knowledge.db             # 系统公共知识库
│   ├── tools/                          # 工具配置
│   │   └── tool_configs.json
│   └── skills/                         # 技能库
│       └── *.md
│
└── system/                             # 系统数据
    ├── node_config.json                # 节点配置
    ├── audit.log                       # 审计日志
    └── metrics.db                      # 系统指标
```

### 3.2 数据库设计

#### 3.2.1 用户对话数据库 (conversations.db)

```sql
-- 会话表
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,              -- 钱包地址
    status TEXT NOT NULL,                -- active, ended
    context TEXT,
    summary TEXT,
    created_at REAL,
    updated_at REAL,
    ended_at REAL
);

-- 消息表
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,                  -- user, assistant, tool
    content TEXT NOT NULL,
    tool_calls TEXT,
    timestamp REAL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE INDEX idx_conv_owner ON conversations(owner_id);
CREATE INDEX idx_msg_conv ON messages(conversation_id);
```

#### 3.2.2 用户记忆数据库 (memory.db)

```sql
-- 对话摘要表
CREATE TABLE conversation_summaries (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    summary TEXT NOT NULL,
    key_topics TEXT,
    decisions TEXT,
    created_at REAL,
    message_count INTEGER
);

-- 用户画像表
CREATE TABLE user_profiles (
    user_id TEXT PRIMARY KEY,
    preferences TEXT,
    commitments TEXT,
    knowledge TEXT,
    last_updated REAL
);

-- 重要记忆表
CREATE TABLE important_memories (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    memory_type TEXT,
    importance REAL,
    created_at REAL
);
```

#### 3.2.3 用户知识库 (knowledge.db)

```sql
-- 知识条目表
CREATE TABLE knowledge_items (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT,
    source TEXT,
    embedding BLOB,                       -- 向量嵌入
    created_at REAL,
    is_private INTEGER DEFAULT 1
);

CREATE INDEX idx_knowledge_user ON knowledge_items(user_id);
```

### 3.3 数据同步策略

#### 3.3.1 数据分类

| 数据类型 | 存储位置 | 是否同步 | 同步方式 |
|---------|---------|---------|---------|
| 对话历史 | 本地 conversations.db | ❌ 不同步 | - |
| 用户画像 | 本地 memory.db | ✅ 自动 | 变更后5分钟+每小时全量 |
| 私有知识库 | 本地 knowledge.db | ✅ 自动 | 变更后10分钟+每小时全量 |
| 工作空间文件 | 本地 workspace/ | ❌ 不同步 | - |
| 浏览器数据 | 本地 browser/ | ❌ 不同步 | - |

#### 3.3.2 自动同步策略

**核心原则：增量同步 + 定期全量 + 生命周期同步**

| 同步类型 | 触发条件 | 延迟 | 说明 |
|---------|---------|------|------|
| 增量同步-画像 | 用户画像变更 | 5分钟 | 防抖，多次变更只触发一次 |
| 增量同步-知识库 | 知识库变更 | 10分钟 | 防抖，多次变更只触发一次 |
| 定期全量同步 | 定时器 | 每小时 | 随机延迟0-5分钟避免峰值 |
| 生命周期同步 | 会话关闭/超时 | 立即 | 确保数据不丢失 |

**会话超时数据安全保证**：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     会话超时数据处理流程                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  【持久化数据 - 不会丢失】                                               │
│                                                                         │
│   ✅ 对话历史      → 实时写入数据库（每条消息立即持久化）                  │
│   ✅ 用户画像      → 每次更新写入数据库                                   │
│   ✅ 私有知识库    → 每次添加写入数据库                                   │
│   ✅ 工作空间文件  → 写入磁盘持久保存                                     │
│                                                                         │
│  【运行时状态 - 会清除】                                                 │
│                                                                         │
│   ⚠️ 浏览器会话    → Cookie/登录状态清除（用户数据目录保留）              │
│   ⚠️ 沙箱变量      → 代码执行变量清除（预期行为）                         │
│   ⚠️ 加密密钥      → 内存清除（下次需重新签名）                           │
│                                                                         │
│  【超时前保护流程】                                                      │
│                                                                         │
│   1. 检测到超时 ──► 检查是否有正在执行的操作                              │
│         │                     │                                         │
│         │                     ├── 有 ──► 等待完成（最多30秒）            │
│         │                     │                                         │
│         │                     └── 无 ──► 继续                           │
│         │                                                               │
│   2. 执行同步 ──► 将用户画像和知识库同步到IPFS                           │
│         │                                                               │
│   3. 记录审计 ──► 记录会话关闭事件                                       │
│         │                                                               │
│   4. 释放资源 ──► 关闭浏览器、清理沙箱、清除密钥                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 3.3.2 IPFS存储结构

```
/ipfs/{cid}/
├── metadata.json                       # 元数据
│   {
│     "version": "1.0",
│     "wallet_address": "0xAAA...",
│     "created_at": 1739875200,
│     "encryption": "AES-256-GCM",
│     "files": ["profile.enc", "knowledge.enc"]
│   }
│
├── profile.enc                         # 加密的用户画像
├── knowledge.enc                       # 加密的知识库
└── checksum.sha256                     # 校验文件
```

---

## 四、核心模块设计

### 4.1 UserSession - 用户会话

**职责**：封装单个用户的所有隔离资源和操作上下文

**文件位置**：`meta_agent/session/user_session.py`

```python
class UserSession:
    """
    用户会话 - 所有用户操作的隔离上下文

    每个钱包地址对应一个 UserSession 实例
    会话内包含该用户专属的所有资源
    """

    # ========== 属性 ==========

    wallet_address: str                  # 用户钱包地址（主键）
    node_id: str                         # 当前节点ID
    session_id: str                      # 会话唯一标识

    is_primary_node: bool                # 是否是用户的主节点

    workspace: UserWorkspace             # 工作空间
    sandbox: CodeSandbox                 # 代码沙箱
    browser_context: Optional[BrowserContext]  # 浏览器上下文
    db: UserDatabase                     # 数据库连接
    ipfs_client: IPFSClient              # IPFS客户端

    created_at: float                    # 创建时间
    last_active: float                   # 最后活跃时间

    # ========== 核心方法 ==========

    async def init() -> None:
        """初始化会话，创建必要的目录和数据库"""

    async def cleanup() -> None:
        """清理会话资源（关闭浏览器、释放锁等）"""

    async def get_profile() -> Dict:
        """获取用户画像（本地优先，可从IPFS拉取）"""

    async def sync_to_ipfs() -> str:
        """将数据同步到IPFS，返回CID"""

    async def check_primary_node() -> bool:
        """检查当前节点是否是用户的主节点"""

    async def migrate_to_this_node() -> bool:
        """从IPFS迁移数据到当前节点"""
```

### 4.2 SessionManager - 会话管理器

**职责**：管理所有用户的会话生命周期

**文件位置**：`meta_agent/session/session_manager.py`

```python
class SessionManager:
    """
    会话管理器

    负责用户会话的创建、获取、清理
    确保每个钱包地址只有一个活跃会话
    """

    # ========== 属性 ==========

    node_id: str                         # 当前节点ID
    _sessions: Dict[str, UserSession]    # wallet -> session 映射
    _lock: asyncio.Lock                  # 并发锁

    # ========== 核心方法 ==========

    async def get_or_create_session(
        wallet_address: str
    ) -> UserSession:
        """获取或创建用户会话"""

    async def get_session(
        wallet_address: str
    ) -> Optional[UserSession]:
        """获取已存在的会话（不创建）"""

    async def close_session(
        wallet_address: str
    ) -> bool:
        """关闭指定用户的会话"""

    async def close_all_sessions() -> None:
        """关闭所有会话（服务关闭时调用）"""

    async def get_active_sessions() -> List[str]:
        """获取所有活跃会话的钱包地址列表"""

    async def cleanup_idle_sessions(
        max_idle_seconds: int = 3600
    ) -> int:
        """清理空闲超过指定时间的会话"""
```

### 4.3 CodeSandbox - 代码执行沙箱

**职责**：提供安全隔离的代码执行环境

**文件位置**：`meta_agent/sandbox/code_sandbox.py`

```python
class CodeSandbox:
    """
    代码执行沙箱

    提供安全的Python代码执行环境：
    1. 限制可用的内置函数
    2. 限制可导入的模块
    3. 限制文件系统访问范围
    4. 限制执行时间和内存使用
    """

    # ========== 配置 ==========

    ALLOWED_BUILTINS: Set[str] = {
        'abs', 'all', 'any', 'bool', 'dict', 'enumerate', 'filter',
        'float', 'format', 'frozenset', 'hash', 'hex', 'int', 'isinstance',
        'len', 'list', 'map', 'max', 'min', 'ord', 'pow', 'print',
        'range', 'repr', 'reversed', 'round', 'set', 'slice', 'sorted',
        'str', 'sum', 'tuple', 'type', 'zip', 'True', 'False', 'None',
    }

    ALLOWED_MODULES: Set[str] = {
        'math', 'random', 'datetime', 'json', 're', 'collections',
        'itertools', 'functools', 'typing', 'decimal', 'fractions',
        'statistics', 'string', 'textwrap', 'unicodedata',
    }

    # ========== 属性 ==========

    wallet_address: str
    sandbox_dir: Path                    # 沙箱根目录

    # ========== 核心方法 ==========

    async def execute(
        code: str,
        timeout: int = 30,
        max_memory_mb: int = 256
    ) -> SandboxResult:
        """
        在沙箱中执行代码

        Args:
            code: Python代码字符串
            timeout: 超时时间（秒）
            max_memory_mb: 最大内存（MB）

        Returns:
            SandboxResult:
                - success: bool
                - stdout: str
                - stderr: str
                - result: Any
                - error: Optional[str]
        """

    def validate_code(code: str) -> List[str]:
        """验证代码，返回警告或错误列表"""

    def create_safe_globals() -> Dict:
        """创建安全的全局命名空间"""
```

### 4.4 BrowserContext - 浏览器上下文

**职责**：提供用户隔离的浏览器会话

**文件位置**：`meta_agent/browser/browser_context.py`

```python
class BrowserContext:
    """
    浏览器上下文

    每个用户独立的浏览器会话：
    1. 隔离的Cookie和LocalStorage
    2. 隔离的下载目录
    3. 会话结束时自动清理
    """

    # ========== 属性 ==========

    wallet_address: str
    user_data_dir: Path                  # Chromium用户数据目录

    playwright: Optional[Playwright]
    browser: Optional[Browser]
    context: Optional[BrowserContext]
    page: Optional[Page]

    # ========== 核心方法 ==========

    async def open(
        url: str,
        headless: bool = True
    ) -> Dict:
        """打开浏览器并访问URL"""

    async def click(selector: str) -> Dict:
        """点击元素"""

    async def fill(selector: str, value: str) -> Dict:
        """填写表单"""

    async def get_content(selector: Optional[str] = None) -> Dict:
        """获取页面内容"""

    async def screenshot(path: Optional[str] = None) -> Dict:
        """截取屏幕"""

    async def close() -> None:
        """关闭浏览器"""

    async def is_active() -> bool:
        """检查浏览器是否活跃"""
```

### 4.5 UserWorkspace - 用户工作空间

**职责**：管理用户的文件系统隔离

**文件位置**：`meta_agent/workspace/user_workspace.py`

```python
class UserWorkspace:
    """
    用户工作空间

    管理用户专属的文件系统空间：
    1. 所有文件操作限制在用户目录内
    2. 提供安全路径验证
    3. 支持文件上传下载
    """

    # ========== 属性 ==========

    wallet_address: str
    workspace_root: Path                 # 工作空间根目录

    # 目录
    temp_dir: Path                       # 临时文件
    output_dir: Path                     # 输出文件
    uploads_dir: Path                    # 上传文件

    # ========== 核心方法 ==========

    def resolve_path(relative_path: str) -> Path:
        """解析相对路径为绝对路径（限制在工作空间内）"""

    def validate_path(path: Path) -> bool:
        """验证路径是否在工作空间内"""

    async def write_file(
        relative_path: str,
        content: Union[str, bytes]
    ) -> Path:
        """写入文件"""

    async def read_file(relative_path: str) -> bytes:
        """读取文件"""

    async def list_files(
        directory: str = "",
        pattern: str = "*"
    ) -> List[FileInfo]:
        """列出文件"""

    async def delete_file(relative_path: str) -> bool:
        """删除文件"""

    async def cleanup_temp() -> int:
        """清理临时文件"""
```

### 4.6 UserDatabase - 用户数据库

**职责**：管理用户专属的数据库连接

**文件位置**：`meta_agent/database/user_database.py`

```python
class UserDatabase:
    """
    用户数据库

    管理用户专属的SQLite数据库：
    1. 对话历史
    2. 记忆/画像
    3. 私有知识库
    """

    # ========== 属性 ==========

    wallet_address: str
    db_dir: Path                         # 数据库目录

    conversations_db: sqlite3.Connection
    memory_db: sqlite3.Connection
    knowledge_db: sqlite3.Connection

    # ========== 核心方法 ==========

    # 会话相关
    async def create_conversation() -> Conversation:
    async def get_conversation(conv_id: str) -> Optional[Conversation]:
    async def get_active_conversation() -> Optional[Conversation]:
    async def add_message(conv_id: str, message: Message) -> None:
    async def get_messages(conv_id: str, limit: int) -> List[Message]:

    # 记忆相关
    async def get_profile() -> Optional[UserProfile]:
    async def update_profile(profile: UserProfile) -> None:
    async def add_memory(memory: Memory) -> None:
    async def get_memories(limit: int) -> List[Memory]:

    # 知识库相关
    async def add_knowledge(item: KnowledgeItem) -> None:
    async def search_knowledge(query: str, top_k: int) -> List[KnowledgeItem]:
    async def delete_knowledge(item_id: str) -> bool:

    # 数据导入导出
    async def export_data() -> Dict:
    async def import_data(data: Dict) -> None:
```

### 4.7 IPFSClient - IPFS客户端

**职责**：处理与IPFS的交互

**文件位置**：`meta_agent/ipfs/ipfs_client.py`

```python
class IPFSClient:
    """
    IPFS客户端

    处理用户数据的IPFS存储：
    1. 加密上传
    2. 下载解密
    3. CID管理
    """

    # ========== 属性 ==========

    ipfs_node: str                       # IPFS节点地址
    encryption_key: bytes                # 加密密钥（从钱包派生）

    # ========== 核心方法 ==========

    async def upload_user_data(
        wallet_address: str,
        data: Dict
    ) -> str:
        """
        上传用户数据到IPFS

        1. 序列化数据
        2. 加密
        3. 上传到IPFS
        4. 返回CID
        """

    async def download_user_data(
        wallet_address: str,
        cid: Optional[str] = None
    ) -> Optional[Dict]:
        """
        从IPFS下载用户数据

        Args:
            wallet_address: 钱包地址
            cid: 可选的CID，不提供则从链上查询

        Returns:
            解密后的用户数据
        """

    async def get_user_cid(
        wallet_address: str
    ) -> Optional[str]:
        """获取用户数据的CID（从链上或IPNS）"""

    async def publish_cid(
        wallet_address: str,
        cid: str
    ) -> None:
        """发布CID到链上或IPNS"""

    # 加密相关
    def encrypt(data: bytes, key: bytes) -> bytes:
    def decrypt(encrypted: bytes, key: bytes) -> bytes:
    def derive_key(wallet_address: str) -> bytes:
```

### 4.8 AutoSyncManager - 自动同步管理器

**职责**：管理用户数据的自动同步

**文件位置**：`meta_agent/sync/auto_sync_manager.py`

```python
class AutoSyncManager:
    """
    自动同步管理器

    同步策略：
    1. 变更触发：用户画像/知识库变更后延迟同步（防抖）
    2. 定期全量：每小时检查并同步所有数据
    3. 生命周期：会话关闭/空闲超时前同步
    """

    # ========== 配置 ==========

    @dataclass
    class Config:
        # 增量同步（变更触发，带防抖）
        profile_sync_delay: int = 300         # 用户画像变更后5分钟同步
        knowledge_sync_delay: int = 600       # 知识库变更后10分钟同步

        # 定期全量同步
        full_sync_interval: int = 3600        # 每小时全量同步一次
        full_sync_random_delay: int = 300     # 随机延迟0-5分钟（避免峰值）

        # 会话生命周期同步
        sync_on_session_close: bool = True    # 会话关闭时同步
        sync_on_idle: bool = True             # 空闲超时前同步

        # 失败重试
        retry_attempts: int = 3               # 重试次数
        retry_delay: int = 60                 # 重试间隔（秒）

    # ========== 属性 ==========

    config: Config
    _pending_syncs: Dict[str, asyncio.Task]  # wallet:sync_type -> task
    _last_sync_time: Dict[str, float]         # wallet -> timestamp
    _sync_lock: Dict[str, asyncio.Lock]       # wallet -> lock
    _running: bool

    # ========== 核心方法 ==========

    async def start():
        """启动自动同步服务"""

    async def stop():
        """停止自动同步服务"""

    async def on_profile_changed(wallet_address: str):
        """用户画像变更时触发（5分钟后同步）"""

    async def on_knowledge_changed(wallet_address: str):
        """知识库变更时触发（10分钟后同步）"""

    async def sync_before_close(wallet_address: str):
        """会话关闭前立即同步"""

    async def force_sync(wallet_address: str):
        """强制立即同步（用户手动触发）"""

    async def get_sync_status(wallet_address: str) -> SyncStatus:
        """获取同步状态"""
        # 返回：上次同步时间、待同步数据量、同步是否进行中
```

**同步时序示例**：

```
时间轴 ─────────────────────────────────────────────────────────────►

00:00  用户登录
  │
00:05  用户更新偏好设置
  │
  ├──► 触发增量同步（延迟5分钟）
  │
00:08  用户又修改偏好（防抖重置5分钟）
  │
  ├──► 取消上次任务，重新计时
  │
00:13  增量同步执行 ✓
  │
00:30  用户添加知识条目
  │
  ├──► 触发知识库同步（延迟10分钟）
  │
00:40  知识库同步执行 ✓
  │
01:00  定期全量同步检查 ✓
  │
01:30  用户空闲超时
  │
  ├──► 会话关闭前同步 ✓
  │
会话关闭（数据已安全同步到IPFS）
```

---

## 五、API 设计

### 5.1 改造后的 MetaAgent API

```python
class MetaAgent:
    """
    Meta Agent 主类（改造后）

    核心变化：
    1. 所有用户相关操作必须传入 wallet_address
    2. 使用 SessionManager 管理用户会话
    3. 工具执行时传入 UserSession 上下文
    """

    def __init__(self, config: MetaAgentConfig):
        self.config = config
        self.node_id = config.node_id

        # 会话管理器（新增）
        self.session_manager = SessionManager(self.node_id)

        # 共享组件（保留）
        self.llm_manager = LLMManager(config.llm)
        self.tool_registry = ToolRegistry()
        self.skills_manager = SkillsManager()

    async def chat(
        self,
        message: str,
        wallet_address: str,              # 现在必须提供
        **kwargs
    ) -> str:
        """
        处理用户对话

        Args:
            message: 用户消息
            wallet_address: 用户钱包地址（必须）

        Returns:
            Agent回复
        """
        # 获取用户会话
        session = await self.session_manager.get_or_create_session(
            wallet_address
        )

        # 在会话上下文中处理
        # ...

    async def execute_tool(
        self,
        tool_name: str,
        wallet_address: str,              # 新增参数
        **kwargs
    ) -> Any:
        """
        执行工具

        Args:
            tool_name: 工具名称
            wallet_address: 用户钱包地址
            **kwargs: 工具参数
        """
        session = await self.session_manager.get_or_create_session(
            wallet_address
        )

        return await self.tool_registry.execute(
            tool_name,
            session=session,              # 传入会话上下文
            **kwargs
        )

    async def sync_user_data(
        self,
        wallet_address: str
    ) -> str:
        """
        同步用户数据到IPFS

        Returns:
            IPFS CID
        """
        session = await self.session_manager.get_or_create_session(
            wallet_address
        )
        return await session.sync_to_ipfs()

    async def migrate_user_data(
        self,
        wallet_address: str
    ) -> bool:
        """
        从IPFS迁移用户数据到当前节点

        Returns:
            是否成功
        """
        session = await self.session_manager.get_or_create_session(
            wallet_address
        )
        return await session.migrate_to_this_node()
```

### 5.2 工具执行接口改造

```python
# 工具定义接口改造
class Tool(Protocol):
    """工具协议"""

    name: str
    description: str

    async def execute(
        self,
        session: UserSession,            # 新增：会话上下文
        params: Dict[str, Any]
    ) -> Any:
        """
        执行工具

        Args:
            session: 用户会话上下文
            params: 工具参数
        """
        ...

# 示例：代码执行工具改造
async def execute_python(
    session: UserSession,                # 新增
    params: dict
) -> Dict[str, Any]:
    """在用户沙箱中执行Python代码"""
    code = params.get("code", "")
    timeout = params.get("timeout", 30)

    # 使用用户的沙箱执行
    result = await session.sandbox.execute(code, timeout=timeout)
    return result

# 示例：浏览器工具改造
async def browser_open(
    session: UserSession,                # 新增
    params: dict
) -> Dict[str, Any]:
    """在用户浏览器上下文中打开URL"""
    url = params.get("url", "")

    # 使用用户的浏览器上下文
    result = await session.browser_context.open(url)
    return result
```

---

## 六、实现计划

### 6.1 阶段划分

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          实现阶段规划                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  阶段一：核心隔离 (P0) - 预计 5 天                                       │
│  ├── UserSession 实现                                                   │
│  ├── SessionManager 实现                                                │
│  ├── UserDatabase 实现                                                  │
│  ├── CodeSandbox 基础实现                                               │
│  └── MetaAgent 核心改造                                                 │
│                                                                         │
│  阶段二：完善隔离 (P1) - 预计 3 天                                       │
│  ├── BrowserContext 实现                                                │
│  ├── UserWorkspace 实现                                                 │
│  ├── 所有工具改造                                                        │
│  └── 集成测试                                                           │
│                                                                         │
│  阶段三：数据同步 (P2) - 预计 3 天                                       │
│  ├── IPFSClient 实现                                                    │
│  ├── 数据加密/解密                                                       │
│  ├── 数据迁移功能                                                        │
│  └── E2E测试                                                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 详细任务分解

#### 阶段一：核心隔离 (P0)

| 任务 | 描述 | 预计工时 | 依赖 |
|-----|------|---------|-----|
| T1.1 | 创建 `meta_agent/session/` 目录结构 | 0.5天 | - |
| T1.2 | 实现 `UserSession` 类 | 1天 | T1.1 |
| T1.3 | 实现 `SessionManager` 类 | 1天 | T1.2 |
| T1.4 | 实现 `UserDatabase` 类 | 1天 | T1.1 |
| T1.5 | 实现 `CodeSandbox` 基础版 | 1天 | T1.2 |
| T1.6 | 改造 `MetaAgent.chat()` | 0.5天 | T1.3 |
| **小计** | | **5天** | |

#### 阶段二：完善隔离 (P1)

| 任务 | 描述 | 预计工时 | 依赖 |
|-----|------|---------|-----|
| T2.1 | 实现 `BrowserContext` 类 | 1天 | 阶段一 |
| T2.2 | 实现 `UserWorkspace` 类 | 0.5天 | 阶段一 |
| T2.3 | 改造所有工具（约15个） | 1天 | T2.1, T2.2 |
| T2.4 | 实现 `QuotaManager` 配额管理 | 0.5天 | 阶段一 |
| T2.5 | 实现 `AuditLogger` 审计日志 | 0.5天 | 阶段一 |
| T2.6 | 集成测试 | 0.5天 | T2.3 |
| **小计** | | **4天** | |

#### 阶段三：数据同步 (P2)

| 任务 | 描述 | 预计工时 | 依赖 |
|-----|------|---------|-----|
| T3.1 | 创建 `meta_agent/ipfs/` 和 `meta_agent/sync/` 目录 | 0.5天 | - |
| T3.2 | 实现 `IPFSClient` 类 | 1天 | T3.1 |
| T3.3 | 实现数据加密/解密（钱包签名派生密钥） | 0.5天 | T3.2 |
| T3.4 | 实现 `AutoSyncManager` 自动同步 | 1天 | T3.2 |
| T3.5 | 实现数据迁移功能 | 0.5天 | T3.2 |
| T3.6 | E2E测试 | 0.5天 | T3.4 |
| **小计** | | **4天** | |

**总计：13个工作日**

### 6.3 文件结构规划

```
meta_agent/
├── session/                            # 新增：会话管理
│   ├── __init__.py
│   ├── user_session.py                 # UserSession
│   └── session_manager.py              # SessionManager
│
├── sandbox/                            # 新增：代码沙箱
│   ├── __init__.py
│   └── code_sandbox.py                 # CodeSandbox
│
├── browser/                            # 新增：浏览器隔离
│   ├── __init__.py
│   └── browser_context.py              # BrowserContext
│
├── workspace/                          # 新增：工作空间
│   ├── __init__.py
│   └── user_workspace.py               # UserWorkspace
│
├── database/                           # 新增：用户数据库
│   ├── __init__.py
│   └── user_database.py                # UserDatabase
│
├── ipfs/                               # 新增：IPFS客户端
│   ├── __init__.py
│   ├── ipfs_client.py                  # IPFSClient
│   └── encryption.py                   # 加密工具
│
├── sync/                               # 新增：自动同步
│   ├── __init__.py
│   └── auto_sync_manager.py            # AutoSyncManager
│
├── audit/                              # 新增：审计日志
│   ├── __init__.py
│   └── audit_logger.py                 # AuditLogger
│
├── quota/                              # 新增：配额管理
│   ├── __init__.py
│   └── quota_manager.py                # QuotaManager
│
├── tools/                              # 改造：工具执行
│   ├── __init__.py
│   ├── registry.py                     # 改造：增加session参数
│   ├── execution.py                    # 改造：使用sandbox
│   └── ...                             # 其他工具改造
│
└── agent.py                            # 改造：核心流程
```

---

## 七、测试策略

### 7.1 单元测试

```python
# tests/unit/test_user_session.py

class TestUserSession:
    """UserSession 单元测试"""

    async def test_session_creation():
        """测试会话创建"""
        session = UserSession("0xAAA...", "node-001")
        await session.init()
        assert session.workspace is not None
        assert session.sandbox is not None

    async def test_workspace_isolation():
        """测试工作空间隔离"""
        session_a = await create_session("0xAAA...")
        session_b = await create_session("0xBBB...")

        # 写入文件
        await session_a.workspace.write_file("test.txt", "data_a")
        await session_b.workspace.write_file("test.txt", "data_b")

        # 验证隔离
        content_a = await session_a.workspace.read_file("test.txt")
        content_b = await session_b.workspace.read_file("test.txt")

        assert content_a == b"data_a"
        assert content_b == b"data_b"

    async def test_database_isolation():
        """测试数据库隔离"""
        session_a = await create_session("0xAAA...")
        session_b = await create_session("0xBBB...")

        # 创建对话
        conv_a = await session_a.db.create_conversation()
        conv_b = await session_b.db.create_conversation()

        # 验证隔离
        convs_a = await session_a.db.get_all_conversations()
        convs_b = await session_b.db.get_all_conversations()

        assert len(convs_a) == 1
        assert len(convs_b) == 1
        assert convs_a[0].id != convs_b[0].id
```

### 7.2 沙箱安全测试

```python
# tests/unit/test_code_sandbox.py

class TestCodeSandbox:
    """代码沙箱安全测试"""

    async def test_dangerous_import_blocked():
        """测试危险模块导入被阻止"""
        session = await create_session("0xAAA...")

        # 尝试导入危险模块
        code = "import os; os.system('echo hack')"
        result = await session.sandbox.execute(code)

        assert not result.success
        assert "不允许" in result.error

    async def test_file_access_restricted():
        """测试文件访问被限制"""
        session = await create_session("0xAAA...")

        # 尝试访问沙箱外文件
        code = "open('/etc/passwd').read()"
        result = await session.sandbox.execute(code)

        assert not result.success

    async def test_timeout_enforced():
        """测试超时限制"""
        session = await create_session("0xAAA...")

        # 死循环代码
        code = "while True: pass"
        result = await session.sandbox.execute(code, timeout=2)

        assert not result.success
        assert "超时" in result.error

    async def test_memory_limit():
        """测试内存限制"""
        session = await create_session("0xAAA...")

        # 尝试分配大量内存
        code = "x = 'A' * (1024 * 1024 * 1024)"  # 1GB
        result = await session.sandbox.execute(code, max_memory_mb=64)

        assert not result.success
```

### 7.3 集成测试

```python
# tests/integration/test_multi_user.py

class TestMultiUserIsolation:
    """多用户隔离集成测试"""

    async def test_concurrent_users():
        """测试并发用户隔离"""
        agent = MetaAgent(config)

        # 并发创建多个用户会话
        tasks = [
            agent.chat(f"Hello from {wallet}", wallet_address=wallet)
            for wallet in ["0xAAA...", "0xBBB...", "0xCCC..."]
        ]
        results = await asyncio.gather(*tasks)

        # 验证每个用户得到独立响应
        assert len(results) == 3

    async def test_user_data_not_leaked():
        """测试用户数据不泄露"""
        agent = MetaAgent(config)

        # 用户A存储敏感信息
        await agent.chat("记住我的密码是secret123", wallet_address="0xAAA...")

        # 用户B不应该能访问
        history_b = await agent.get_conversation_history("0xBBB...")
        for msg in history_b:
            assert "secret123" not in msg.content

    async def test_browser_session_isolated():
        """测试浏览器会话隔离"""
        agent = MetaAgent(config)

        # 用户A登录某网站
        await agent.execute_tool(
            "browser_open",
            wallet_address="0xAAA...",
            url="https://example.com/login"
        )
        await agent.execute_tool(
            "browser_fill",
            wallet_address="0xAAA...",
            selector="#username",
            value="user_a"
        )

        # 用户B打开同一网站，不应该看到用户A的登录状态
        await agent.execute_tool(
            "browser_open",
            wallet_address="0xBBB...",
            url="https://example.com"
        )
        # 验证用户B是未登录状态
```

---

## 八、风险评估与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|-----|------|------|---------|
| 代码沙箱被绕过 | 高 | 中 | 使用多层防护（白名单+资源限制+seccomp） |
| IPFS网络不可用 | 中 | 低 | 本地优先策略，IPFS仅作为可选同步 |
| 会话资源泄漏 | 中 | 中 | 实现自动清理机制，定期检查 |
| 加密密钥管理 | 高 | 低 | 使用钱包签名派生密钥，不存储明文 |
| 性能下降 | 中 | 中 | 使用连接池，延迟初始化 |

---

## 九、配置决策

### 9.1 IPFS节点配置

**决策：使用公共IPFS节点**

```yaml
# 默认公共网关配置
ipfs:
  gateways:
    - "https://ipfs.io"
    - "https://gateway.pinata.cloud"
    - "https://cloudflare-ipfs.com"

  # 备用网关自动切换
  timeout: 30s
  retry_count: 3
```

### 9.2 加密密钥管理

**决策：使用钱包签名派生**

```python
class KeyDerivation:
    """
    加密密钥派生策略

    使用 EIP-191 个人签名派生加密密钥
    用户需要签名一条固定消息来获取密钥
    """

    # 签名消息（固定）
    SIGN_MESSAGE = """
    Sign this message to generate your encryption key.

    This signature will be used to encrypt your private data
    before storing it on IPFS.

    Only sign this message on trusted platforms!
    """

    @staticmethod
    def derive_key_from_signature(signature: str) -> bytes:
        """
        从钱包签名派生 AES-256 密钥

        流程：
        1. 用户在钱包中签名固定消息
        2. 前端将签名传给后端
        3. 后端使用 HKDF 从签名派生密钥
        4. 密钥仅存在内存中，不持久化
        """
        import hashlib
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        from cryptography.hazmat.primitives import hashes

        # 使用 HKDF 派生密钥
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,  # AES-256
            salt=b"USMSB_META_AGENT_v1",
            info=b"encryption_key",
        )
        key = hkdf.derive(signature.encode())
        return key
```

**密钥生命周期**：
- 密钥仅在 `UserSession` 生命周期内存在内存中
- 会话关闭后密钥被清除
- 每次用户重新连接需要重新签名

### 9.3 会话超时策略

**决策：分级超时 + 智能保活**

```python
@dataclass
class SessionTimeoutConfig:
    """会话超时配置"""

    # 会话级别超时
    session_idle_timeout: int = 1800       # 30分钟无操作关闭会话
    session_max_lifetime: int = 28800      # 最长8小时强制刷新

    # 资源级别超时（更激进）
    browser_idle_timeout: int = 600        # 10分钟无操作关闭浏览器
    sandbox_cleanup_after: int = 60        # 代码执行完60秒后清理沙箱

    # 数据库连接池
    db_connection_timeout: int = 7200      # 2小时后关闭数据库连接
    db_pool_size: int = 5                  # 连接池大小

    # 智能保活
    keepalive_on_activity: bool = True     # 有活动时自动延长超时
    keepalive_heartbeat: int = 300         # 5分钟心跳检测
```

**超时处理流程**：

```
┌─────────────────────────────────────────────────────────────────┐
│                      会话超时管理流程                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  用户活动 ──► 更新 last_active 时间戳                           │
│       │                                                         │
│       ▼                                                         │
│  后台检查器（每5分钟）                                           │
│       │                                                         │
│       ├──► 浏览器空闲 > 10分钟？ ──► 关闭浏览器，释放资源        │
│       │                                                         │
│       ├──► 会话空闲 > 30分钟？ ──►                              │
│       │         │                                               │
│       │         ├──► 有未同步数据？ ──► 提示用户 ──► 等待       │
│       │         │                                               │
│       │         └──► 无未同步数据？ ──► 关闭会话                │
│       │                                                         │
│       └──► 会话存在 > 8小时？ ──► 强制刷新会话（安全考虑）       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 9.4 资源配额策略

**决策：基于角色的智能配额 + 动态调整**

```python
@dataclass
class ResourceQuota:
    """资源配额"""

    # 存储配额
    max_storage_mb: int = 100              # 默认100MB
    max_workspace_files: int = 1000        # 最大文件数
    max_file_size_mb: int = 10             # 单文件最大10MB

    # 计算配额
    max_code_timeout: int = 30             # 代码执行超时（秒）
    max_code_memory_mb: int = 256          # 代码执行内存（MB）
    max_code_executions_per_hour: int = 100  # 每小时执行次数

    # 浏览器配额
    max_browser_sessions: int = 1          # 同时浏览器会话数
    max_browser_pages: int = 5             # 每个会话最大页面数

    # API配额
    max_chat_per_hour: int = 500           # 每小时对话次数
    max_tool_calls_per_hour: int = 1000    # 每小时工具调用次数


# 基于角色的配额
ROLE_QUOTAS = {
    "USER": ResourceQuota(
        max_storage_mb=100,
        max_code_executions_per_hour=50,
        max_chat_per_hour=200,
    ),
    "DEVELOPER": ResourceQuota(
        max_storage_mb=500,
        max_code_executions_per_hour=200,
        max_chat_per_hour=1000,
    ),
    "VALIDATOR": ResourceQuota(
        max_storage_mb=200,
        max_code_executions_per_hour=100,
        max_chat_per_hour=500,
    ),
    "ADMIN": ResourceQuota(
        max_storage_mb=1000,
        max_code_executions_per_hour=1000,
        max_chat_per_hour=5000,
    ),
}


class QuotaManager:
    """
    配额管理器

    功能：
    1. 基于角色的基础配额
    2. 动态调整（根据系统负载）
    3. 使用量统计和预警
    """

    async def check_quota(
        self,
        wallet_address: str,
        resource_type: str,
        requested: int = 1
    ) -> Tuple[bool, str]:
        """
        检查是否超出配额

        Returns:
            (is_allowed, reason)
        """
        user_role = await self._get_user_role(wallet_address)
        quota = ROLE_QUOTAS.get(user_role, ROLE_QUOTAS["USER"])

        current_usage = await self._get_current_usage(wallet_address, resource_type)

        if resource_type == "storage":
            if current_usage + requested > quota.max_storage_mb * 1024 * 1024:
                return False, f"存储空间不足，已使用 {current_usage // (1024*1024)}MB"

        elif resource_type == "code_execution":
            hourly_usage = await self._get_hourly_usage(wallet_address, "code_execution")
            if hourly_usage >= quota.max_code_executions_per_hour:
                return False, f"代码执行次数已达小时上限 ({quota.max_code_executions_per_hour})"

        elif resource_type == "chat":
            hourly_usage = await self._get_hourly_usage(wallet_address, "chat")
            if hourly_usage >= quota.max_chat_per_hour:
                return False, f"对话次数已达小时上限 ({quota.max_chat_per_hour})"

        return True, "OK"

    async def record_usage(
        self,
        wallet_address: str,
        resource_type: str,
        amount: int = 1
    ):
        """记录资源使用"""
        # 使用 Redis 或内存存储记录
        pass

    async def get_usage_report(
        self,
        wallet_address: str
    ) -> Dict:
        """获取用户资源使用报告"""
        return {
            "storage_used_mb": await self._get_storage_used(wallet_address),
            "code_executions_hour": await self._get_hourly_usage(wallet_address, "code_execution"),
            "chat_count_hour": await self._get_hourly_usage(wallet_address, "chat"),
            "quota_limit": ROLE_QUOTAS.get(
                await self._get_user_role(wallet_address),
                ROLE_QUOTAS["USER"]
            ).__dict__
        }
```

### 9.5 审计日志策略

**决策：安全审计 + 隐私保护**

```python
@dataclass
class AuditConfig:
    """审计配置"""

    # 日志保留
    retention_days: int = 90               # 保留90天
    archive_after_days: int = 30           # 30天后归档

    # 日志级别
    log_sensitive_content: bool = False    # 不记录敏感内容
    hash_user_id: bool = True              # 用户ID哈希处理

    # 审计事件
    audit_events: List[str] = field(default_factory=lambda: [
        # 会话事件
        "session_created",
        "session_closed",
        "session_timeout",

        # 认证事件
        "wallet_connected",
        "signature_verified",
        "auth_failed",

        # 数据事件
        "data_synced_to_ipfs",
        "data_migrated",
        "export_requested",

        # 执行事件
        "code_executed",
        "browser_opened",
        "file_uploaded",

        # 安全事件
        "sandbox_violation",
        "quota_exceeded",
        "suspicious_activity",
    ])


class AuditLogger:
    """
    审计日志记录器

    设计原则：
    1. 只记录"发生了什么"，不记录"具体内容"
    2. 用户ID哈希处理，保护隐私
    3. 结构化日志，便于分析
    4. 不可篡改（追加写入）
    """

    def __init__(self, config: AuditConfig):
        self.config = config
        self.log_file = "/data/system/audit.log"

    async def log(
        self,
        event: str,
        wallet_address: str,
        details: Optional[Dict] = None,
        result: str = "success"
    ):
        """
        记录审计日志

        Args:
            event: 事件类型
            wallet_address: 用户钱包地址
            details: 事件详情（不包含敏感内容）
            result: 结果 (success/failed/blocked)
        """
        if event not in self.config.audit_events:
            return

        # 用户ID哈希处理
        user_hash = self._hash_user_id(wallet_address) if self.config.hash_user_id else wallet_address

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "user_hash": user_hash,
            "result": result,
            "details": details or {},
            "node_id": os.getenv("NODE_ID", "unknown"),
        }

        # 追加写入日志文件
        await self._write_log(log_entry)

    def _hash_user_id(self, wallet_address: str) -> str:
        """哈希用户ID"""
        import hashlib
        return hashlib.sha256(
            f"usmsb:{wallet_address}".encode()
        ).hexdigest()[:16]

    async def _write_log(self, entry: Dict):
        """写入日志（追加模式）"""
        import aiofiles
        async with aiofiles.open(self.log_file, mode='a') as f:
            await f.write(json.dumps(entry) + "\n")


# 使用示例
audit = AuditLogger(AuditConfig())

# 记录会话创建
await audit.log(
    event="session_created",
    wallet_address="0xAAA...",
    details={"primary_node": "node-001"}
)

# 记录代码执行（不记录代码内容）
await audit.log(
    event="code_executed",
    wallet_address="0xAAA...",
    details={
        "language": "python",
        "timeout": 30,
        "success": True
    }
)

# 记录沙箱违规
await audit.log(
    event="sandbox_violation",
    wallet_address="0xBBB...",
    details={
        "violation_type": "forbidden_import",
        "module": "os",
        "blocked": True
    },
    result="blocked"
)
```

**审计日志格式**：

```json
{
  "timestamp": "2026-02-21T10:30:00.000Z",
  "event": "code_executed",
  "user_hash": "a1b2c3d4e5f6g7h8",
  "result": "success",
  "details": {
    "language": "python",
    "timeout": 30,
    "success": true
  },
  "node_id": "node-001"
}
```

---

## 十、附录

### A. 参考文档

- [RestrictedPython 文档](https://restrictedpython.readthedocs.io/)
- [Playwright Browser Context](https://playwright.dev/python/docs/browser-contexts)
- [IPFS HTTP API](https://docs.ipfs.tech/reference/kubo/rpc/)

### B. 术语表

| 术语 | 定义 |
|-----|------|
| UserSession | 用户会话，封装单个用户的所有隔离资源 |
| SessionManager | 会话管理器，管理所有用户会话的生命周期 |
| CodeSandbox | 代码沙箱，提供安全的代码执行环境 |
| BrowserContext | 浏览器上下文，提供用户隔离的浏览器会话 |
| UserWorkspace | 用户工作空间，管理用户专属的文件系统空间 |
| Primary Node | 主节点，用户首次访问的节点，存储用户元信息 |

---

**文档结束**

> 请确认以上设计方案，如有问题或需要调整的地方请指出。
