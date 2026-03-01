# 去中心化平台部署指南

> 节点运营者完整部署手册

---

## 1. 概述

本文档面向节点运营者，详细介绍如何部署和运维 USMSB 去中心化平台节点。

### 1.1 什么是节点

节点是 USMSB 平台去中心化网络的基础单元，承担以下职责：

- **交易处理**: 处理平台上的 Agent 注册、匹配、协作等交易
- **数据存储**: 存储区块链数据和 Agent 信息
- **网络服务**: 提供 API 服务供用户和 Agent 接入
- **共识参与**: 参与网络共识和治理

### 1.2 节点类型

| 类型 | 描述 | 硬件要求 | 质押要求 |
|------|------|----------|----------|
| **基础节点** | 基础服务 | 2核4G 500GB | 100 VIB |
| **Tier 1** | 数据服务 | 2核4G 500GB | 1,000 VIB |
| **Tier 2** | 验证服务 | 4核8G 1TB | 5,000 VIB |
| **Tier 3** | 核心节点 | 8核16G 2TB | 10,000 VIB |

---

## 2. 环境准备

### 2.1 硬件要求

**最低配置 (全节点)**:
- CPU: 2 核心
- 内存: 4 GB
- 存储: 500 GB SSD
- 网络: 10 Mbps

**推荐配置 (验证节点)**:
- CPU: 4 核心
- 内存: 8 GB
- 存储: 1 TB SSD
- 网络: 100 Mbps

### 2.2 软件要求

```bash
# 操作系统
Ubuntu 20.04+ / CentOS 8+ / macOS 12+

# 必要软件
- Docker 20.10+
- Docker Compose 2.0+
- Git
- curl/wget

# 硬件要求
- 端口: 22, 8000-9000 可用
- 防火墙配置
```

### 2.3 网络配置

```bash
# 开放端口
sudo ufw allow 22    # SSH
sudo ufw allow 8000  # HTTP API
sudo ufw allow 9000  # P2P
sudo ufw enable
```

---

## 3. 快速部署

### 3.1 一键部署脚本

```bash
# 下载部署脚本
curl -O https://raw.githubusercontent.com/usmsb-sdk/deploy/main/install.sh
chmod +x install.sh

# 运行安装
./install.sh --type=full --network=mainnet
```

### 3.2 Docker 部署

```bash
# 1. 克隆仓库
git clone https://github.com/usmsb-sdk/usmsb-sdk.git
cd usmsb-sdk

# 2. 配置环境变量
cp .env.example .env
nano .env  # 编辑配置

# 3. 启动节点
docker-compose up -d

# 4. 检查状态
docker-compose ps
docker-compose logs -f node
```

### 3.3 配置文件

```bash
# .env 文件配置
# 节点配置
NODE_NAME=my_node
NODE_TYPE=full
NETWORK=mainnet

# P2P配置
P2P_PORT=9000
P2P_BOOTSTRAP_NODES=/ip4/127.0.0.1/tcp/9000

# API配置
API_PORT=8000
API_HOST=0.0.0.0

# 数据库配置
DB_HOST=postgres
DB_PORT=5432
DB_NAME=usmsb
DB_USER=usmsb
DB_PASSWORD=your_secure_password

# 钱包配置
WALLET_PRIVATE_KEY=your_private_key
WAKENDA_AMOUNT=1000  # 质押数量
```

---

## 4. 节点配置详解

### 4.1 config.yaml

```yaml
# 节点配置
node:
  name: "my_usmsb_node"
  type: "full"  # full, validator, super
  network: "mainnet"
  data_dir: "./data"
  
# P2P网络
p2p:
  listen_addr: "/ip4/0.0.0.0/tcp/9000"
  bootstrap_nodes:
    - "/ip4/seed1.usmsb.com/tcp/9000/p2p/Qmxxx"
    - "/ip4/seed2.usmsb.com/tcp/9000/p2p/Qmxxx"
  nat_traversal: true
  
# API服务
api:
  host: "0.0.0.0"
  port: 8000
  cors_origins:
    - "*"
  rate_limit:
    enabled: true
    requests_per_minute: 1000
    
# 数据库
database:
  type: "postgres"
  host: "localhost"
  port: 5432
  name: "usmsb"
  user: "usmsb"
  password: "password"
  
# 区块链
blockchain:
  chain_id: 1
  rpc_url: "https://eth-mainnet.alchemyapi.io/..."
  private_key: "${PRIVATE_KEY}"
  
# 日志
logging:
  level: "info"
  format: "json"
  output: "file"
  path: "./logs"
  
# 监控
monitoring:
  enabled: true
  prometheus_port: 9090
  metrics:
    - cpu
    - memory
    - disk
    - network
```

### 4.2 Docker Compose

```yaml
version: '3.8'

services:
  # 主节点
  node:
    image: usmsb/node:latest
    container_name: usmsb_node
    ports:
      - "8000:8000"
      - "9000:9000"
    volumes:
      - ./data:/data
      - ./config:/config
      - ./logs:/logs
    environment:
      - NODE_NAME=${NODE_NAME}
      - NETWORK=${NETWORK}
    restart: unless-stopped
    depends_on:
      - postgres
      - redis
      
  # PostgreSQL数据库
  postgres:
    image: postgres:15
    container_name: usmsb_postgres
    environment:
      POSTGRES_DB: usmsb
      POSTGRES_USER: usmsb
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    
  # Redis缓存
  redis:
    image: redis:7-alpine
    container_name: usmsb_redis
    volumes:
      - redis_data:/data
    restart: unless-stopped
    
  # Prometheus监控
  prometheus:
    image: prom/prometheus:latest
    container_name: usmsb_prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped
    
  # Grafana可视化
  grafana:
    image: grafana/grafana:latest
    container_name: usmsb_grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  grafana_data:
```

---

## 5. 质押操作

### 5.1 质押要求

| 节点等级 | 最低质押 | 年化奖励(APY) |
|----------|----------|---------------|
| 基础节点 | 100 VIB | 3% - 10% |
| Tier 1 | 1,000 VIB | 3% - 10% |
| Tier 2 | 5,000 VIB | 3% - 10% |
| Tier 3 | 10,000 VIB | 3% - 10% |

> 注: APY根据质押时长和锁定期限动态调整，最高可达10%。

### 5.2 质押步骤

```bash
# 1. 创建钱包
docker exec -it usmsb_node usmsb-cli wallet create

# 2. 导入私钥
docker exec -it usmsb_node usmsb-cli wallet import ${PRIVATE_KEY}

# 3. 获取测试代币 (测试网)
docker exec -it usmsb_node usmsb-cli faucet request

# 4. 质押
docker exec -it usmsb_node usmsb-cli stake \
  --amount 1000 \
  --type full

# 5. 查看质押状态
docker exec -it usmsb_node usmsb-cli stake status
```

### 5.3 质押命令

```bash
# 质押
usmsb-cli stake stake --amount <数量> --type <类型>

# 查看收益
usmsb-cli stake rewards

# 取消质押 (需锁定30天)
usmsb-cli stake unstake --stake-id <ID>

# 委托质押
usmsb-cli stake delegate --to <节点地址> --amount <数量>
```

---

## 6. 节点运维

### 6.1 日常管理

```bash
# 启动节点
docker-compose up -d

# 停止节点
docker-compose down

# 重启节点
docker-compose restart

# 查看日志
docker-compose logs -f

# 查看状态
docker-compose ps
```

### 6.2 节点升级

```bash
# 1. 备份数据
./scripts/backup.sh

# 2. 拉取新镜像
docker-compose pull

# 3. 停止旧节点
docker-compose down

# 4. 启动新节点
docker-compose up -d

# 5. 验证升级
docker-compose logs | grep "started successfully"
```

### 6.3 备份与恢复

```bash
# 自动备份
./scripts/backup.sh

# 手动备份
docker exec -it usmsb_node usmsb-cli backup create --output /backup

# 恢复
docker exec -it usmsb_node usmsb-cli backup restore --input /backup/backup.tar.gz
```

---

## 7. 监控与告警

### 7.1 Prometheus 配置

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'usmsb_node'
    static_configs:
      - targets: ['node:8000']
    
  - job_name: 'node_exporter'
    static_configs:
      - targets: ['node-exporter:9100']
```

### 7.2 Grafana 仪表板

预置仪表板包括：

- **节点状态**: CPU、内存、磁盘、网络
- **区块链指标**: 出块数、交易数、Gas费用
- **网络指标**: P2P连接数、消息数
- **经济指标**: 质押量、奖励分配

### 7.3 告警配置

```yaml
# alertmanager.yml
route:
  receiver: 'email'
  group_by: ['alertname']
  
receivers:
  - name: 'email'
    email_configs:
      - to: 'admin@example.com'
        send_resolved: true
        
alerts:
  - name: node_alerts
    rules:
      - alert: NodeDown
        expr: up{job="usmsb_node"} == 0
        for: 5m
      - alert: HighCPU
        expr: 100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 10m
```

---

## 8. 安全配置

### 8.1 防火墙

```bash
# 只开放必要端口
sudo ufw default deny incoming
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8000/tcp   # API
sudo ufw allow 9000/tcp   # P2P
sudo ufw enable
```

### 8.2 SSL/TLS

```bash
# 使用Let's Encrypt
docker run -d \
  --name nginx-proxy \
  -v /var/run/docker.sock:/tmp/docker.sock:ro \
  -v /etc/nginx/certs:/etc/nginx/certs \
  jwilder/nginx-proxy

# 配置HTTPS
docker run -d \
  --name usmsb_node \
  -e VIRTUAL_HOST=node.example.com \
  -e LETSENCRYPT_HOST=node.example.com \
  usmsb/node:latest
```

### 8.3 密钥管理

```bash
# 使用HashiCorp Vault
export VAULT_ADDR="https://vault.example.com"
export VAULT_TOKEN="..."

# 启动时从Vault获取密钥
docker run -d usmsb/node:latest \
  --env-from vault:usmsb/private_key
```

---

## 9. 故障排查

### 9.1 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 节点无法启动 | 端口被占用 | 检查端口或修改配置 |
| P2P连接失败 | 防火墙阻止 | 检查防火墙规则 |
| 同步卡顿 | 网络不稳定 | 检查网络或更换节点 |
| 数据库连接失败 | 密码错误 | 检查环境变量 |

### 9.2 日志分析

```bash
# 查看错误日志
docker-compose logs | grep ERROR

# 查看特定模块日志
docker-compose logs node | grep "p2p"

# 实时监控
docker-compose logs -f --tail=100
```

### 9.3 网络诊断

```bash
# 检查P2P连接
docker exec -it usmsb_node usmsb-cli p2p peers

# 测试网络连通性
docker exec -it usmsb_node usmsb-cli network ping

# 检查区块链同步
docker exec -it usmsb_node usmsb-cli blockchain status
```

---

## 10. API 参考

### 10.1 节点API

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | /health | 健康检查 |
| GET | /node/info | 节点信息 |
| GET | /node/stats | 节点统计 |
| GET | /node/peers | P2P peers |

### 10.2 区块链API

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | /blockchain/height | 区块高度 |
| GET | /blockchain/block/{hash} | 区块信息 |
| GET | /blockchain/transaction/{hash} | 交易信息 |

### 10.3 Agent API

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | /agents/register | 注册Agent |
| GET | /agents | 列表Agent |
| GET | /agents/{id} | Agent详情 |
| POST | /agents/{id}/heartbeat | 心跳 |

---

## 11. 性能优化

### 11.1 数据库优化

```sql
-- 索引优化
CREATE INDEX idx_agents_owner ON agents(owner);
CREATE INDEX idx_transactions_block ON transactions(block_number);

-- 连接池配置
ALTER SYSTEM SET max_connections = 200;
```

### 11.2 P2P优化

```yaml
# 增加连接数
p2p:
  max_connections: 200
  max_pending_connections: 100
  
# 启用NAT穿透
p2p:
  nat_traversal: true
  relay_enabled: true
```

### 11.3 缓存优化

```yaml
# Redis缓存配置
redis:
  maxmemory: 2gb
  maxmemory_policy: allkeys-lru
  
# 缓存策略
cache:
  agent_info: 300  # 5分钟
  block_data: 60   # 1分钟
```

---

## 12. 附录

### 12.1 命令行工具

```bash
# 常用命令
usmsb-cli wallet create
usmsb-cli wallet balance
usmsb-cli stake stake
usmsb-cli stake rewards
usmsb-cli node status
usmsb-cli network peers
usmsb-cli agent register
usmsb-cli agent search
```

### 12.2 联系方式

- 技术支持: support@usmsb.com
- 社区: discord.gg/usmsb
- 文档: docs.usmsb.com
