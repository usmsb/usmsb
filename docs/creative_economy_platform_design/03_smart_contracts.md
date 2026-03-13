# 第3章：智能合约设计

## 3.1 联合订单合约 (JointOrder.sol)

### 设计目标

实现C端需求聚合、反向竞价、资金托管、分批结算的完整流程。

### 状态机设计

```
┌──────────┐     托管资金      ┌──────────┐     开始竞价      ┌──────────┐
│ CREATED  │ ───────────────► │  FUNDED  │ ───────────────► │ BIDDING  │
└──────────┘                   └──────────┘                   └──────────┘
     ▲                              │                              │
     │                              │                              │
     │ 取消/退款                    │                              │
     │                              ▼                              ▼
┌──────────┐              ┌──────────┐     选择中标者     ┌──────────┐
│ CANCELLED│◄─────────────│ EXPIRED  │◄────────────────── │AWARDED   │
└──────────┘              └──────────┘                   └──────────┘
                                                               │
                                                               │
                                    ┌──────────────────────────┘
                                    ▼
                              ┌──────────┐     确认交付      ┌──────────┐
                              │IN_PROGRESS│ ───────────────► │DELIVERED │
                              └──────────┘                   └──────────┘
                                    │                              │
                                    │                              │
                                    ▼                              ▼
                              ┌──────────┐     争议解决      ┌──────────┐
                              │ DISPUTED │◄─────────────────► │COMPLETED │
                              └──────────┘                   └──────────┘
```

### 数据结构

```solidity
struct OrderPool {
    bytes32 poolId;                    // 池ID
    address creator;                   // 创建者
    string serviceType;                // 服务类型
    uint256 totalBudget;               // 总预算
    uint256 minBudget;                 // 最低预算
    uint256 participantCount;          // 参与者数量
    uint256 createdAt;                 // 创建时间
    uint256 biddingEndsAt;             // 竞价截止时间
    uint256 deliveryDeadline;          // 交付截止
    PoolStatus status;                 // 状态
    address winningProvider;           // 中标服务商
    uint256 winningBid;                // 中标价格
}

struct Participant {
    address user;                      // 参与者地址
    uint256 budget;                    // 预算
    bytes32 demandId;                  // 需求ID
    string requirements;               // 具体需求
    bool hasDeposited;                 // 是否已托管
    bool hasConfirmed;                 // 是否已确认
    bool hasWithdrawn;                 // 是否已提取
}

struct Bid {
    bytes32 bidId;                     // 报价ID
    bytes32 poolId;                    // 池ID
    address provider;                  // 服务商
    uint256 price;                     // 报价
    uint256 deliveryTime;              // 承诺交付时间
    uint256 reputationScore;           // 信誉分(链下签名)
    uint256 score;                     // 综合评分
    bool isWinner;                     // 是否中标
}

enum PoolStatus {
    CREATED,       // 已创建
    FUNDED,        // 已托管
    BIDDING,       // 竞价中
    AWARDED,       // 已授标
    IN_PROGRESS,   // 执行中
    DELIVERED,     // 已交付
    COMPLETED,     // 已完成
    DISPUTED,      // 争议中
    CANCELLED,     // 已取消
    EXPIRED        // 已过期
}
```

### 核心函数

```solidity
// 创建需求池
function createPool(
    string memory serviceType,
    uint256 minBudget,
    uint256 biddingDuration,
    uint256 deliveryDeadline
) external returns (bytes32);

// 参与者加入池
function joinPool(
    bytes32 poolId,
    uint256 budget,
    string memory requirements
) external payable;

// 提交报价
function submitBid(
    bytes32 poolId,
    uint256 price,
    uint256 deliveryTime,
    bytes memory reputationSignature
) external;

// 选择中标者
function awardPool(
    bytes32 poolId,
    bytes32 bidId
) external;

// 确认交付
function confirmDelivery(
    bytes32 poolId,
    uint8 rating
) external;

// 提取收益
function withdrawEarnings(bytes32 poolId) external;

// 争议处理
function raiseDispute(
    bytes32 poolId,
    string memory reason
) external;

function resolveDispute(
    bytes32 poolId,
    bool refundBuyers,
    string memory resolution
) external onlyArbitrator;
```

### 事件定义

```solidity
event PoolCreated(bytes32 indexed poolId, address creator, string serviceType);
event ParticipantJoined(bytes32 indexed poolId, address user, uint256 budget);
event BidSubmitted(bytes32 indexed poolId, bytes32 bidId, address provider, uint256 price);
event PoolAwarded(bytes32 indexed poolId, address winner, uint256 winningBid);
event DeliveryConfirmed(bytes32 indexed poolId, address user, uint8 rating);
event EarningsWithdrawn(bytes32 indexed poolId, address provider, uint256 amount);
event DisputeRaised(bytes32 indexed poolId, address raiser, string reason);
event DisputeResolved(bytes32 indexed poolId, bool refundBuyers, string resolution);
```

---

## 3.2 资产碎片化合约 (AssetVault.sol)

### 设计目标

将创意资产(NFT)碎片化为可交易的ERC20代币，实现流动性和收益分发。

### 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                        AssetVault                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  原始资产                碎片化过程               碎片代币       │
│  ┌─────────┐            ┌─────────┐            ┌─────────┐     │
│  │ NFT     │ ─────────► │ Vault   │ ─────────► │ ERC20   │     │
│  │(ERC721) │   存入     │         │   发行    │ Shares  │     │
│  └─────────┘            └─────────┘            └─────────┘     │
│       │                       │                      │          │
│       │                       ▼                      │          │
│       │               ┌─────────────┐               │          │
│       │               │ 收益池      │◄──────────────┘          │
│       │               │ DividendPool│   收益分配               │
│       │               └─────────────┘                          │
│       │                       │                                 │
│       │                       ▼                                 │
│       │               ┌─────────────┐                          │
│       └──────────────►│ 持有人分成  │                          │
│                       └─────────────┘                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 数据结构

```solidity
struct AssetInfo {
    address nftContract;           // 原NFT合约地址
    uint256 nftTokenId;            // NFT Token ID
    address owner;                 // 原所有者
    uint256 totalShares;           // 总碎片数
    uint256 sharePrice;            // 初始碎片价格
    uint256 sharesSold;            // 已售碎片数
    uint256 totalEarnings;         // 累计收益
    uint256 distributedEarnings;   // 已分发收益
    bool isFragmented;             // 是否已碎片化
    bool isTradable;               // 是否可交易
}

struct Shareholder {
    uint256 shares;                // 持有碎片数
    uint256 claimedEarnings;       // 已领取收益
    uint256 purchaseTime;          // 购买时间
}
```

### 核心函数

```solidity
// 存入NFT并创建碎片
function depositAndFragment(
    address nftContract,
    uint256 tokenId,
    uint256 totalShares,
    uint256 sharePrice,
    string memory metadata
) external returns (bytes32 assetId);

// 购买碎片
function purchaseShares(
    bytes32 assetId,
    uint256 shareAmount
) external payable;

// 分发收益
function distributeEarnings(
    bytes32 assetId,
    uint256 amount
) external payable;

// 领取收益
function claimEarnings(bytes32 assetId) external;

// 转让碎片
function transferShares(
    bytes32 assetId,
    address to,
    uint256 amount
) external;

// 赎回NFT(需要持有全部碎片)
function redeemNFT(bytes32 assetId) external;

// 查询资产信息
function getAssetInfo(bytes32 assetId) external view returns (AssetInfo memory);

// 查询持有人信息
function getShareholder(
    bytes32 assetId,
    address holder
) external view returns (Shareholder memory);

// 查询待领取收益
function getUnclaimedEarnings(
    bytes32 assetId,
    address holder
) external view returns (uint256);
```

### 事件定义

```solidity
event AssetFragmented(
    bytes32 indexed assetId,
    address nftContract,
    uint256 tokenId,
    uint256 totalShares
);
event SharesPurchased(
    bytes32 indexed assetId,
    address buyer,
    uint256 shareAmount,
    uint256 price
);
event EarningsDistributed(
    bytes32 indexed assetId,
    uint256 amount,
    uint256 perShare
);
event EarningsClaimed(
    bytes32 indexed assetId,
    address holder,
    uint256 amount
);
event SharesTransferred(
    bytes32 indexed assetId,
    address from,
    address to,
    uint256 amount
);
event NFTRedeemed(
    bytes32 indexed assetId,
    address redeemer,
    uint256 tokenId
);
```

---

## 3.3 zk信用通行证合约 (ZKCredential.sol)

### 设计目标

使用零知识证明验证用户属性，同时保护隐私。

### 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                      ZKCredential                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  链下证明生成                      链上验证                     │
│  ┌─────────────┐                 ┌─────────────┐              │
│  │ 私有数据    │                 │             │              │
│  │ • 交易历史 │                 │ 公开属性   │              │
│  │ • 质押记录 │  ──zk-SNARK──► │ • 信誉>0.8 │              │
│  │ • 信誉分    │                 │ • 质押>1000 │              │
│  │ • 完成率    │     证明        │ • 无惩罚    │              │
│  └─────────────┘                 └─────────────┘              │
│         │                               │                      │
│         │                               ▼                      │
│         │                       ┌─────────────┐               │
│         │                       │ 凭证签发    │               │
│         │                       │ Credential  │               │
│         │                       └─────────────┘               │
│         │                               │                      │
│         │                               ▼                      │
│         │                       ┌─────────────┐               │
│         └──────────────────────►│ 权限控制    │               │
│                                 └─────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 数据结构

```solidity
struct Credential {
    bytes32 credentialId;          // 凭证ID
    address holder;                // 持有人
    CredentialType credType;       // 凭证类型
    uint256 validFrom;             // 生效时间
    uint256 validUntil;            // 失效时间
    bytes32 commitment;            // 承诺值(隐私保护)
    bytes32 nullifier;             // 无效符(防重放)
    bool isRevoked;                // 是否撤销
    bytes metadata;                // 元数据(加密)
}

struct VerificationRecord {
    bytes32 recordId;              // 记录ID
    bytes32 credentialId;          // 凭证ID
    address verifier;              // 验证者
    uint256 timestamp;             // 验证时间
    bool isValid;                  // 是否有效
}

enum CredentialType {
    IDENTITY,          // 身份凭证
    SERVICE_PROVIDER,  // 服务商凭证
    GOVERNANCE,        // 治理凭证
    PREMIUM,           // VIP凭证
    TRUSTED_NODE       // 可信节点凭证
}

struct ProofData {
    uint256[2] a;         // SNARK证明 a
    uint256[2][2] b;      // SNARK证明 b
    uint256[2] c;         // SNARK证明 c
    uint256[4] publicInputs; // 公开输入
}
```

### 核心函数

```solidity
// 验证证明并签发凭证
function verifyAndIssue(
    CredentialType credType,
    uint256 validDuration,
    bytes32 commitment,
    ProofData memory proof
) external returns (bytes32 credentialId);

// 验证凭证
function verifyCredential(
    bytes32 credentialId,
    bytes32 nullifier,
    ProofData memory proof
) external returns (bool);

// 撤销凭证
function revokeCredential(
    bytes32 credentialId,
    string memory reason
) external onlyIssuer;

// 检查凭证有效性
function isCredentialValid(bytes32 credentialId) external view returns (bool);

// 获取凭证信息
function getCredential(
    bytes32 credentialId
) external view returns (Credential memory);

// 检查持有者是否有某类凭证
function hasCredentialType(
    address holder,
    CredentialType credType
) external view returns (bool);

// 更新验证密钥(管理员)
function updateVerificationKey(
    CredentialType credType,
    uint256[2] memory alpha,
    uint256[2][2] memory beta,
    uint256[2] memory gamma,
    uint256[2] memory delta
) external onlyAdmin;
```

### 事件定义

```solidity
event CredentialIssued(
    bytes32 indexed credentialId,
    address indexed holder,
    CredentialType credType,
    uint256 validUntil
);
event CredentialVerified(
    bytes32 indexed credentialId,
    address verifier,
    bool isValid
);
event CredentialRevoked(
    bytes32 indexed credentialId,
    string reason
);
event VerificationKeyUpdated(CredentialType credType);
```

### zk-SNARK电路设计

```circom
// credential_proof.circom

template CredentialProof() {
    // 公开输入
    signal input reputationThreshold;    // 信誉阈值
    signal input stakeThreshold;         // 质押阈值
    signal input commitment;             // 承诺值
    
    // 私有输入
    signal input reputation;             // 实际信誉分
    signal input stake;                  // 实际质押量
    signal input noSlash;                // 是否无惩罚 (0或1)
    signal input secret;                 // 随机秘密
    
    // 验证条件
    signal reputationValid;
    signal stakeValid;
    signal noSlashValid;
    
    // 信誉分验证: reputation >= reputationThreshold
    component geq1 = GreaterEqThan(32);
    geq1.in[0] <== reputation;
    geq1.in[1] <== reputationThreshold;
    reputationValid <== geq1.out;
    
    // 质押验证: stake >= stakeThreshold
    component geq2 = GreaterEqThan(32);
    geq2.in[0] <== stake;
    geq2.in[1] <== stakeThreshold;
    stakeValid <== geq2.out;
    
    // 无惩罚验证
    noSlashValid <== noSlash;
    
    // 承诺计算
    component hash = Poseidon(4);
    hash.inputs[0] <== reputation;
    hash.inputs[1] <== stake;
    hash.inputs[2] <== noSlash;
    hash.inputs[3] <== secret;
    
    // 验证承诺
    commitment === hash.out;
    
    // 所有条件必须满足
    signal output valid;
    valid <== reputationValid * stakeValid * noSlashValid;
}

component main = CredentialProof();
```

---

## 3.4 合约交互流程

### 联合订单完整流程

```
1. 创建池
   用户 → JointOrder.createPool() → PoolCreated事件

2. 参与者加入
   用户A,B,C → JointOrder.joinPool() → ParticipantJoined事件 ×3
   → 每个用户托管资金

3. 竞价阶段
   服务商X,Y,Z → JointOrder.submitBid() → BidSubmitted事件 ×3
   → 信誉签名验证

4. 选择中标者
   创建者 → JointOrder.awardPool() → PoolAwarded事件
   → 资金锁定给中标者

5. 执行交付
   中标者 → (链下交付) → 交付物提交

6. 确认验收
   用户A,B,C → JointOrder.confirmDelivery() → DeliveryConfirmed事件 ×3
   → 更新信誉

7. 提取收益
   中标者 → JointOrder.withdrawEarnings() → EarningsWithdrawn事件
   → 资金释放
```

### 资产碎片化完整流程

```
1. 存入NFT
   创作者 → AssetVault.depositAndFragment()
   → NFT转入合约 → AssetFragmented事件

2. 购买碎片
   投资者A,B → AssetVault.purchaseShares() → SharesPurchased事件 ×2
   → 资金存入收益池

3. 收益分发
   创作者/其他人 → AssetVault.distributeEarnings()
   → EarningsDistributed事件

4. 领取收益
   投资者A → AssetVault.claimEarnings() → EarningsClaimed事件

5. 碎片交易
   投资者A → AssetVault.transferShares(投资者B)
   → SharesTransferred事件

6. 赎回NFT(可选)
   持全部碎片者 → AssetVault.redeemNFT() → NFTRedeemed事件
```

### zk信用通行证完整流程

```
1. 链下证明生成
   用户 → (链下)zk证明服务 → 生成SNARK证明

2. 提交证明
   用户 → ZKCredential.verifyAndIssue()
   → 验证证明 → 签发凭证 → CredentialIssued事件

3. 使用凭证
   用户 → ZKCredential.verifyCredential()
   → 验证凭证 → 返回验证结果 → CredentialVerified事件

4. 撤销凭证(管理员)
   管理员 → ZKCredential.revokeCredential()
   → CredentialRevoked事件
```
