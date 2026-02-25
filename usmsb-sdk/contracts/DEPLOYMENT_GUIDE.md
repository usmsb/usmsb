# VIBE 合约部署指南

> 本指南将一步一步教你如何在 Base 网络上部署 VIBE 代币合约

---

## 📋 准备工作

### 1. 安装 Node.js

如果你还没有安装 Node.js，请先安装：

1. 访问 https://nodejs.org/
2. 下载 LTS 版本（推荐 18.x 或 20.x）
3. 安装完成后，打开终端验证：
   ```bash
   node --version
   npm --version
   ```

### 2. 安装 MetaMask 钱包

1. 访问 https://metamask.io/
2. 下载并安装浏览器扩展
3. 创建或导入钱包
4. **备份助记词**（非常重要！）

---

## 🔧 配置 Base 网络

### 步骤 1: 添加 Base 主网到 MetaMask

1. 打开 MetaMask
2. 点击左上角的网络选择器
3. 点击 "添加网络" 或 "添加网络手动"
4. 输入以下信息：

| 字段 | 值 |
|------|-----|
| 网络名称 | Base |
| RPC URL | https://mainnet.base.org |
| 链 ID | 8453 |
| 货币符号 | ETH |
| 区块浏览器 URL | https://basescan.org |

5. 点击 "保存"

### 步骤 2: 添加 Base Sepolia 测试网

测试网用于测试，不需要真钱：

| 字段 | 值 |
|------|-----|
| 网络名称 | Base Sepolia |
| RPC URL | https://sepolia.base.org |
| 链 ID | 84532 |
| 货币符号 | ETH |
| 区块浏览器 URL | https://sepolia.basescan.org |

---

## 💰 获取 ETH

### 测试网 (Base Sepolia)

1. 访问 https://faucet.circle.com/
2. 连接你的 MetaMask 钱包
3. 选择 "Base Sepolia"
4. 输入你的钱包地址
5. 点击 "Receive Test ETH"
6. 等待几分钟后，你会收到 0.01-0.1 ETH

### 主网 (Base)

1. 你需要有真实的 ETH
2. 可以从交易所提币到你的 MetaMask 钱包
3. 或使用跨链桥从以太坊主网跨到 Base
4. 部署合约大约需要 $5-20 的 ETH（取决于 gas 价格）

---

## 📦 安装项目依赖

### 步骤 1: 打开终端

```bash
# 进入合约目录
cd usmsb-sdk/contracts
```

### 步骤 2: 安装依赖

```bash
npm install
```

等待安装完成（可能需要几分钟）。

---

## ⚙️ 配置环境变量

### 步骤 1: 复制环境变量模板

```bash
cp .env.example .env
```

### 步骤 2: 编辑 .env 文件

打开 `.env` 文件，修改以下内容：

```env
# Base 网络 RPC（可以保持默认）
BASE_RPC_URL=https://mainnet.base.org
BASE_SEPOLIA_RPC_URL=https://sepolia.base.org

# 你的钱包私钥（从 MetaMask 导出）
# ⚠️ 警告：永远不要分享你的私钥！
# ⚠️ 警告：不要把 .env 文件上传到 Git！
PRIVATE_KEY=你的私钥（不带0x前缀）

# BaseScan API Key（用于验证合约）
# 从 https://basescan.org/myapikey 获取
BASESCAN_API_KEY=你的_basescan_api_key
```

### 如何获取私钥：

1. 打开 MetaMask
2. 点击右上角的三个点
3. 选择 "账户详情"
4. 点击 "显示私钥"
5. 输入你的密码
6. 复制私钥（**不要包含 0x 前缀**）

### 如何获取 BaseScan API Key：

1. 访问 https://basescan.org/
2. 注册账户
3. 访问 https://basescan.org/myapikey
4. 点击 "Add" 创建新的 API Key
5. 复制 API Key

---

## 🚀 部署合约

### 测试网部署（推荐先测试）

```bash
# 编译合约
npm run compile

# 部署到 Base Sepolia 测试网
npx hardhat run scripts/deploy.js --network baseSepolia
```

### 主网部署

```bash
# 部署到 Base 主网
npx hardhat run scripts/deploy.js --network base
```

### 部署过程示例

```
========================================
VIBE Contract Deployment
========================================
Network: baseSepolia
Deployer: 0x1234...5678
Balance: 1000000000000000000

1. Deploying VIBEToken...
   VIBEToken deployed to: 0xabcd...efgh

2. Deploying VIBStaking...
   VIBStaking deployed to: 0xijkl...mnop

3. Deploying VIBVesting...
   VIBVesting deployed to: 0xqrst...uvwx

4. Deploying VIBIdentity...
   VIBIdentity deployed to: 0xyz...1234

5. Minting treasury tokens...
   Treasury tokens minted to deployer

========================================
Deployment Complete!
========================================
```

---

## ✅ 验证合约

部署完成后，在 BaseScan 上验证合约源代码：

```bash
# 验证测试网合约
npx hardhat run scripts/verify.js --network baseSepolia

# 验证主网合约
npx hardhat run scripts/verify.js --network base
```

---

## 📝 记录合约地址

部署完成后，合约地址会保存在 `deployments/` 目录下：

- `deployments/baseSepolia.json` - 测试网
- `deployments/base.json` - 主网

**请妥善保存这些地址！**

---

## 🔍 验证部署

### 在区块浏览器上检查

1. 打开 https://basescan.org/（或 https://sepolia.basescan.org/）
2. 在搜索框输入合约地址
3. 确认合约已部署
4. 确认合约已验证（显示绿色勾）

### 检查代币

1. 在 MetaMask 中添加代币
2. 代币合约地址：VIBEToken 地址
3. 代币符号：VIBE
4. 确认你的余额为 1,000,000,000 VIBE

---

## ⚠️ 安全提示

1. **私钥安全**：
   - 永远不要分享你的私钥
   - 不要把 .env 文件上传到 GitHub
   - 使用硬件钱包存储大量资金

2. **部署前检查**：
   - 确保你在正确的网络
   - 确保你有足够的 ETH
   - 先在测试网测试

3. **合约安全**：
   - 考虑进行安全审计
   - 使用时间锁管理关键功能
   - 考虑使用多签钱包作为 owner

---

## 🆘 常见问题

### Q: 部署失败 "insufficient funds"
A: 你的 ETH 不够，请充值更多 ETH

### Q: 部署失败 "nonce too low"
A: 等待之前的交易完成，或重置 MetaMask 账户

### Q: 验证失败 "Already Verified"
A: 合约已经验证过了，不需要再次验证

### Q: 找不到合约
A: 等待几秒钟让交易确认，然后刷新区块浏览器

---

## 📞 获取帮助

如果遇到问题：
1. 检查 BaseScan 上的交易状态
2. 确认网络配置正确
3. 确认私钥格式正确（不带 0x）

---

**祝部署顺利！🎉**
