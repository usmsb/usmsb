# Decentralized Platform Deployment Guide

> Complete Deployment Manual for Node Operators

---

## 1. Overview

This document is for node operators, detailing how to deploy and maintain USMSB decentralized platform nodes.

### 1.1 What is a Node

Nodes are the basic units of the USMSB platform decentralized network, responsible for:

- **Transaction Processing**: Process agent registration, matching, collaboration, and other transactions on the platform
- **Data Storage**: Store blockchain data and agent information
- **Network Services**: Provide API services for users and agents to connect
- **Consensus Participation**: Participate in network consensus and governance

### 1.2 Node Types

| Type | Description | Hardware Requirements | Staking Requirements |
|------|-------------|---------------------|---------------------|
| **Basic Node** | Basic services | 2 cores, 4GB, 500GB | 100 VIB |
| **Tier 1** | Data services | 2 cores, 4GB, 500GB | 1,000 VIB |
| **Tier 2** | Validation services | 4 cores, 8GB, 1TB | 5,000 VIB |
| **Tier 3** | Core node | 8 cores, 16GB, 2TB | 10,000 VIB |

---

## 2. Environment Preparation

### 2.1 Hardware Requirements

**Minimum Configuration (Full Node)**:
- CPU: 2 cores
- Memory: 4 GB
- Storage: 500 GB SSD
- Network: 10 Mbps

**Recommended Configuration (Validator Node)**:
- CPU: 4 cores
- Memory: 8 GB
- Storage: 1 TB SSD
- Network: 100 Mbps

### 2.2 Software Requirements

```bash
# Operating System
Ubuntu 20.04+ / CentOS 8+ / macOS 12+

# Required Software
- Docker 20.10+
- Docker Compose 2.0+
- Git
- curl/wget

# Port Requirements
- Ports: 22, 8000-9000 available
```

### 2.3 Network Configuration

```bash
# Open required ports
sudo ufw allow 22    # SSH
sudo ufw allow 8000  # HTTP API
sudo ufw allow 9000  # P2P
sudo ufw enable
```

---

## 3. Quick Deployment

### 3.1 One-Click Deployment Script

```bash
# Download deployment script
curl -O https://docs.usmsb.com/deploy.sh
chmod +x deploy.sh

# Run deployment
./deploy.sh --type full --network mainnet
```

### 3.2 Docker Deployment

```bash
# Clone repository
git clone https://github.com/usmsb/usmsb.git
cd usmsb-platform

# Configure environment
cp .env.example .env
# Edit .env file with your settings

# Start services
docker-compose up -d
```

### 3.3 Configuration File

Create `config.yaml`:

```yaml
node:
  type: full
  name: my-node
  network: mainnet

p2p:
  listen_addr: ":9000"
  peers:
    - /ip4/1.2.3.4/tcp/9000

rpc:
  addr: ":8000"
  cors: "*"

storage:
  path: /data/usmsb
  max_size: 500GB

logging:
  level: info
  file: /var/log/usmsb/node.log
```

---

## 4. Node Configuration Details

### 4.1 config.yaml

Main configuration options:

```yaml
# Node Identity
node:
  # Node type: basic, validator, full
  type: validator
  # Node name
  name: "my-usmsb-node"
  # Network to connect to
  network: mainnet

# P2P Configuration
p2p:
  # Listen address
  listen_addr: ":9000"
  # Bootstrap nodes
  bootstrap_nodes:
    - /ip4/100.100.100.100/tcp/9000/p2p/Qmxxx
  # Enable UPnP
  enable_upnp: true

# RPC Configuration
rpc:
  # RPC listen address
  addr: ":8000"
  # CORS settings
  cors: "*"
  # API modules
  modules:
    - agent
    - matching
    - collaboration

# Database Configuration
database:
  # Database type
  type: postgresql
  # Connection string
  connection: postgresql://user:pass@localhost:5432/usmsb
  # Connection pool size
  pool_size: 10

# Blockchain Configuration
blockchain:
  # Blockchain network
  network: mainnet
  # RPC endpoint
  rpc_url: https://rpc.usmsb.com
  # Chain ID
  chain_id: 99999

# Staking Configuration
staking:
  # Enable staking
  enabled: true
  # Minimum stake amount
  min_stake: 100
  # Auto-restake
  auto_restake: true
```

### 4.2 Docker Compose

```yaml
version: '3.8'

services:
  usmsb-node:
    image: usmsb/node:latest
    container_name: usmsb-node
    ports:
      - "8000:8000"
      - "9000:9000"
    volumes:
      - ./data:/data
      - ./config.yaml:/app/config.yaml
    environment:
      - NODE_TYPE=validator
      - LOG_LEVEL=info
    restart: unless-stopped

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: usmsb
      POSTGRES_USER: usmsb
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

---

## 5. Staking Operations

### 5.1 Staking Requirements

| Node Level | Minimum Stake | Annual Reward (APY) |
|-----------|--------------|---------------------|
| Basic Node | 100 VIB | 3% - 10% |
| Tier 1 | 1,000 VIB | 3% - 10% |
| Tier 2 | 5,000 VIB | 3% - 10% |
| Tier 3 | 10,000 VIB | 3% - 10% |

> Note: APY is dynamically adjusted based on staking duration, up to 10%.

### 5.2 Staking Steps

```bash
# 1. Create wallet
docker exec -it usmsb_node usmsb-cli wallet create

# 2. Import private key
docker exec -it usmsb_node usmsb-cli wallet import ${PRIVATE_KEY}

# 3. Check balance
docker exec -it usmsb_node usmsb-cli wallet balance

# 4. Stake
docker exec -it usmsb_node usmsb-cli stake amount 1000 --duration 30

# 5. Check stake status
docker exec -it usmsb_node usmsb-cli stake status
```

### 5.3 Staking Commands

```bash
# Stake tokens
usmsb-cli stake stake <amount> <duration>

# Unstake
usmsb-cli stake unstake <stake_id>

# Claim rewards
usmsb-cli stake claim

# Check rewards
usmsb-cli stake rewards

# Delegate to another node
usmsb-cli stake delegate <node_id> <amount>
```

---

## 6. Node Operations

### 6.1 Daily Management

```bash
# Check node status
usmsb-cli status

# Check logs
docker logs usmsb-node --tail 100

# Check resource usage
docker stats usmsb-node

# Restart node
docker restart usmsb-node
```

### 6.2 Monitoring

```bash
# Enable Prometheus metrics
curl -X POST http://localhost:8000/metrics/enable

# View metrics
curl http://localhost:8000/metrics

# Check health
curl http://localhost:8000/health
```

### 6.3 Backup and Recovery

```bash
# Backup data
docker exec usmsb-node tar -czf /backup/usmsb-$(date +%Y%m%d).tar.gz /data

# Restore data
docker exec -i usmsb-node tar -xzf /backup/usmsb-20260227.tar.gz -C /
```

---

## 7. Security

### 7.1 Firewall Configuration

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow RPC
sudo ufw allow 8000/tcp

# Allow P2P
sudo ufw allow 9000/tcp

# Deny all other incoming
sudo ufw default deny incoming

# Enable firewall
sudo ufw enable
```

### 7.2 SSL/TLS Setup

```bash
# Generate SSL certificate
sudo certbot certonly --nginx -d your-domain.com

# Configure in nginx
sudo cat > /etc/nginx/sites-available/usmsb <<EOF
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
    }
}
EOF
```

---

## 8. Troubleshooting

### 8.1 Common Issues

| Issue | Solution |
|-------|----------|
| Node won't start | Check logs with `docker logs usmsb-node` |
| Can't connect to network | Verify P2P port is open |
| Sync stuck | Restart node or check peers |
| Out of disk space | Clean old data or expand storage |

### 8.2 Network Diagnostics

```bash
# Check P2P connectivity
usmsb-cli p2p peers

# Test RPC connection
curl -X POST http://localhost:8000 -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# Check blockchain sync status
usmsb-cli blockchain status
```

---

## 9. API Reference

### 9.1 Node API

| Endpoint | Method | Description |
|----------|--------|-------------|
| /health | GET | Health check |
| /status | GET | Node status |
| /peers | GET | List peers |
| /metrics | GET | Prometheus metrics |

### 9.2 Blockchain API

| Endpoint | Method | Description |
|----------|--------|-------------|
| /eth_blockNumber | POST | Get current block |
| /eth_getBalance | POST | Get account balance |
| /eth_sendRawTransaction | POST | Send transaction |

### 9.3 Agent API

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/v1/agents | GET | List agents |
| /api/v1/agents/:id | GET | Get agent info |
| /api/v1/agents/register | POST | Register agent |

---

## 10. Support

### 10.1 Documentation

- Official Docs: docs.usmsb.com
- API Reference: docs.usmsb.com/api
- GitHub: github.com/usmsb/usmsb

### 10.2 Contact

- Technical Support: support@usmsb.com
- Community: discord.gg/usmsb
- Forum: forum.usmsb.com
