# 生产级基础设施改造方案

> 版本: 1.0
> 日期: 2026-02-15
> 目标: 钱包认证系统生产级部署

## 一、数据库改造

### 1.1 从 SQLite 迁移到 PostgreSQL

**原因:**
- SQLite 单文件无法支撑高并发
- PostgreSQL 支持 ACID、连接池、复制、备份

**实施方案:**

```python
# 新建文件: src/usmsb_sdk/api/database_postgres.py

import asyncpg
from typing import Optional, Dict, List
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/civilization")

class DatabasePool:
    _pool: Optional[asyncpg.Pool] = None

    @classmethod
    async def get_pool(cls) -> asyncpg.Pool:
        if cls._pool is None:
            cls._pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
        return cls._pool

    @classmethod
    async def close(cls):
        if cls._pool:
            await cls._pool.close()

async def get_db():
    pool = await DatabasePool.get_pool()
    async with pool.acquire() as conn:
        yield conn
```

**迁移脚本:**
```sql
-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 用户表 (增强版)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_address VARCHAR(42) UNIQUE NOT NULL,
    did VARCHAR(100) UNIQUE,
    agent_id UUID,
    stake DECIMAL(18, 8) DEFAULT 0,
    reputation DECIMAL(5, 4) DEFAULT 0.5,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 认证会话表 (增强版)
CREATE TABLE auth_sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    address VARCHAR(42) NOT NULL,
    did VARCHAR(100),
    agent_id UUID,
    access_token_hash VARCHAR(64) NOT NULL,  -- 存储 hash 而非明文
    refresh_token_hash VARCHAR(64),
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引优化
CREATE INDEX idx_sessions_address ON auth_sessions(address);
CREATE INDEX idx_sessions_token ON auth_sessions(access_token_hash);
CREATE INDEX idx_sessions_expires ON auth_sessions(expires_at);

-- Nonce 表 (增强版)
CREATE TABLE auth_nonces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    address VARCHAR(42) NOT NULL,
    nonce VARCHAR(64) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_nonces_lookup ON auth_nonces(address, nonce, expires_at);
```

---

## 二、缓存系统 (Redis)

### 2.1 Redis 配置

```python
# 新建文件: src/usmsb_sdk/api/cache.py

import redis.asyncio as redis
import os
import json
from typing import Optional, Dict, Any

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

class CacheManager:
    _client: Optional[redis.Redis] = None

    @classmethod
    async def get_client(cls) -> redis.Redis:
        if cls._client is None:
            cls._client = redis.from_url(
                REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
        return cls._client

    @classmethod
    async def close(cls):
        if cls._client:
            await cls._client.close()

# Nonce 缓存
class NonceCache:
    PREFIX = "nonce:"

    @staticmethod
    async def set(address: str, nonce: str, ttl: int = 300):
        client = await CacheManager.get_client()
        await client.setex(f"{NonceCache.PREFIX}{address}", ttl, nonce)

    @staticmethod
    async def get(address: str) -> Optional[str]:
        client = await CacheManager.get_client()
        return await client.get(f"{NonceCache.PREFIX}{address}")

    @staticmethod
    async def delete(address: str):
        client = await CacheManager.get_client()
        await client.delete(f"{NonceCache.PREFIX}{address}")

# Session 缓存
class SessionCache:
    PREFIX = "session:"

    @staticmethod
    async def set(session_id: str, data: Dict[str, Any], ttl: int = 86400 * 7):
        client = await CacheManager.get_client()
        await client.setex(
            f"{SessionCache.PREFIX}{session_id}",
            ttl,
            json.dumps(data)
        )

    @staticmethod
    async def get(session_id: str) -> Optional[Dict]:
        client = await CacheManager.get_client()
        data = await client.get(f"{SessionCache.PREFIX}{session_id}")
        return json.loads(data) if data else None

    @staticmethod
    async def delete(session_id: str):
        client = await CacheManager.get_client()
        await client.delete(f"{SessionCache.PREFIX}{session_id}")

# Token 黑名单
class TokenBlacklist:
    PREFIX = "blacklist:"

    @staticmethod
    async def add(token: str, ttl: int = 86400 * 7):
        client = await CacheManager.get_client()
        await client.setex(f"{TokenBlacklist.PREFIX}{token}", ttl, "1")

    @staticmethod
    async def is_blacklisted(token: str) -> bool:
        client = await CacheManager.get_client()
        return await client.exists(f"{TokenBlacklist.PREFIX}{token}") > 0

# 速率限制
class RateLimiter:
    PREFIX = "rate:"

    @staticmethod
    async def check(address: str, action: str, limit: int = 5, window: int = 60) -> bool:
        """检查是否超过速率限制"""
        client = await CacheManager.get_client()
        key = f"{RateLimiter.PREFIX}{action}:{address}"

        current = await client.incr(key)
        if current == 1:
            await client.expire(key, window)

        return current <= limit

    @staticmethod
    async def get_remaining(address: str, action: str, limit: int = 5) -> int:
        client = await CacheManager.get_client()
        key = f"{RateLimiter.PREFIX}{action}:{address}"
        current = await client.get(key)
        return max(0, limit - int(current or 0))
```

---

## 三、安全增强

### 3.1 签名验证 (修复 TODO)

```python
# 更新文件: src/usmsb_sdk/api/rest/auth.py

from eth_account.messages import encode_defunct
from web3 import Web3

def verify_siwe_signature(message: str, signature: str, expected_address: str) -> bool:
    """验证 SIWE 签名"""
    try:
        # 使用 web3.py 恢复签名地址
        w3 = Web3()
        encoded_message = encode_defunct(text=message)
        recovered_address = w3.eth.account.recover_message(
            encoded_message,
            signature=signature
        )
        return recovered_address.lower() == expected_address.lower()
    except Exception as e:
        logger.error(f"Signature verification failed: {e}")
        return False

@router.post("/verify", response_model=VerifyResponse)
async def verify_signature(request: VerifyRequest):
    address = request.address.lower()

    # 1. 检查速率限制
    if not await RateLimiter.check(address, "verify", limit=5, window=300):
        raise HTTPException(status_code=429, detail="Too many attempts")

    # 2. 验证 nonce
    nonce = extract_nonce_from_message(request.message)
    cached_nonce = await NonceCache.get(address)

    if not cached_nonce or cached_nonce != nonce:
        raise HTTPException(status_code=400, detail="Invalid or expired nonce")

    # 3. 验证签名 (关键修复!)
    if not verify_siwe_signature(request.message, request.signature, address):
        raise HTTPException(status_code=400, detail="Signature verification failed")

    # 4. 删除已用 nonce
    await NonceCache.delete(address)

    # ... 继续创建会话
```

### 3.2 JWT Token 增强

```python
# 新建文件: src/usmsb_sdk/api/security.py

import jwt
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict

JWT_SECRET = os.getenv("JWT_SECRET")  # 必须从环境变量获取
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = 3600  # 1 hour
REFRESH_TOKEN_EXPIRE = 86400 * 7  # 7 days

def generate_tokens(session_id: str, address: str) -> Dict[str, str]:
    """生成访问令牌和刷新令牌"""

    if not JWT_SECRET:
        raise ValueError("JWT_SECRET must be set in environment")

    now = datetime.utcnow()

    # Access Token
    access_payload = {
        "sub": address,
        "sid": session_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(seconds=ACCESS_TOKEN_EXPIRE),
        "jti": secrets.token_hex(16)
    }
    access_token = jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    # Refresh Token
    refresh_payload = {
        "sub": address,
        "sid": session_id,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(seconds=REFRESH_TOKEN_EXPIRE),
        "jti": secrets.token_hex(16)
    }
    refresh_token = jwt.encode(refresh_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": ACCESS_TOKEN_EXPIRE
    }

def verify_token(token: str, expected_type: str = "access") -> Optional[Dict]:
    """验证 JWT Token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        if payload.get("type") != expected_type:
            return None

        # 检查黑名单
        if await TokenBlacklist.is_blacklisted(payload.get("jti")):
            return None

        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

async def revoke_token(token: str):
    """撤销 Token (加入黑名单)"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        jti = payload.get("jti")
        exp = payload.get("exp", 0)
        ttl = max(0, exp - int(datetime.utcnow().timestamp()))
        await TokenBlacklist.add(jti, ttl)
    except:
        pass
```

### 3.3 环境变量配置

```bash
# 新建文件: .env.example

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/civilization

# Redis
REDIS_URL=redis://localhost:6379/0

# Security (必须设置!)
JWT_SECRET=your-super-secret-key-at-least-32-characters

# Session
SESSION_DURATION_HOURS=168

# Rate Limiting
RATE_LIMIT_VERIFY_PER_MINUTE=5
RATE_LIMIT_NONCE_PER_MINUTE=10

# CORS
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

---

## 四、审计日志

```python
# 新建文件: src/usmsb_sdk/api/audit.py

import json
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

class AuditAction(str, Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    SIGN_MESSAGE = "sign_message"
    STAKE = "stake"
    PROFILE_UPDATE = "profile_update"
    FAILED_AUTH = "failed_auth"

async def log_audit(
    action: AuditAction,
    address: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    success: bool = True
):
    """记录审计日志"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action.value,
        "address": address,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "details": details or {},
        "success": success
    }

    # 存储到数据库 (使用异步)
    # await db.execute("""
    #     INSERT INTO audit_logs
    #     (action, address, ip_address, user_agent, details, success, created_at)
    #     VALUES ($1, $2, $3, $4, $5, $6, $7)
    # """, ...)

    # 同时输出到日志系统
    print(json.dumps(log_entry))
```

---

## 五、依赖包更新

```txt
# requirements.txt 新增

# Database
asyncpg>=0.29.0
sqlalchemy[asyncio]>=2.0.0
alembic>=1.13.0

# Cache
redis[hiredis]>=5.0.0

# Security
pyjwt>=2.8.0
web3>=6.15.0
eth-account>=0.12.0
passlib[bcrypt]>=1.7.4

# Rate Limiting
slowapi>=0.1.9
```

---

## 六、部署架构

```
                    ┌─────────────────┐
                    │   Load Balancer │
                    │    (Nginx)      │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
       ┌──────▼──────┐ ┌─────▼─────┐ ┌──────▼──────┐
       │  FastAPI 1  │ │ FastAPI 2 │ │  FastAPI 3  │
       │  (Uvicorn)  │ │ (Uvicorn) │ │  (Uvicorn)  │
       └──────┬──────┘ └─────┬─────┘ └──────┬──────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
  ┌──────▼──────┐    ┌───────▼───────┐    ┌─────▼─────┐
  │  PostgreSQL │    │  Redis Cluster│    │  IPFS/    │
  │   Primary   │    │  (Sentinel)   │    │  S3       │
  │  + Replica  │    │               │    │(文件存储) │
  └─────────────┘    └───────────────┘    └───────────┘
```

---

## 七、实施优先级

| 优先级 | 任务 | 预估工时 | 风险 |
|--------|------|----------|------|
| P0 | 修复签名验证 | 2h | 高 |
| P0 | JWT_SECRET 环境变量化 | 0.5h | 高 |
| P1 | 迁移到 PostgreSQL | 4h | 中 |
| P1 | 添加 Redis 缓存 | 3h | 中 |
| P1 | 速率限制 | 2h | 低 |
| P2 | 审计日志 | 3h | 低 |
| P2 | Token 黑名单 | 2h | 低 |
| P3 | 数据库迁移脚本 | 4h | 中 |
| P3 | 备份策略 | 2h | 低 |

---

## 八、测试验收清单

- [ ] 签名验证正常工作
- [ ] JWT Token 正确生成和验证
- [ ] Token 过期后自动拒绝
- [ ] 速率限制生效 (5次/分钟)
- [ ] Session 在 Redis 中正确缓存
- [ ] 数据库连接池正常工作
- [ ] 审计日志正确记录
- [ ] CORS 配置正确
- [ ] 环境变量正确加载
- [ ] HTTPS 正确配置
