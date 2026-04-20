# VIBVesting 合约与白皮书一致性审查报告

> **审查日期：** 2026-04-26
> **合约路径：** `contracts/src/VIBVesting.sol`
> **白皮书版本：** v1.3 (2026-04-22)
> **审查结论：** 核心逻辑完全一致，部署流程存在缺失需补充

---

## 一、审查背景

在 VIBE 代币合约体系中，`VIBVesting` 是管理**团队锁仓**和**早期支持者锁仓**的核心合约。用户反馈"不符合白皮书约定"，本报告对代码实现与白皮书规范进行逐条对照审查。

---

## 二、白皮书锁仓规则原文

根据白皮书 `frontend/public/docs/blockchain-whitepaper.md` Section 4.2.2：

### 团队（Team）—— 8%，80,000,000 VIBE

```
├── 总锁仓期：4 年线性释放
├── 悬崖期：1 年（第 1 年不解锁）
├── 有效释放期：悬崖期后的 3 年线性释放
└── 第 1 年释放：0%，第 2-4 年每年约 2.67%
```

### 早期支持者（Early Supporters）—— 4%，40,000,000 VIBE

```
├── 总锁仓期：2 年线性释放
├── 悬崖期：6 个月（前 6 个月不解锁）
├── 有效释放期：悬崖期后的 1.5 年线性释放
└── 第 1 年释放约 1.33%，第 2 年释放约 2.67%
```

### 重要架构说明

> 团队 8% 和"初始流通量 8%"是两个不同概念：
> - **团队 8%**：分配给团队的代币，通过归属合约管理
> - **初始流通量 8%**：Launch 时的流通供应量
> - 白皮书要求：团队和早期支持者分别使用**独立的 Vesting 合约**（"separate contract"）

---

## 三、代码实现逐项对照

### 3.1 受益人类型定义

**文件：** `contracts/src/VIBVesting.sol`，第 46-52 行

```solidity
// ========== 受益人类型 ==========

/// @notice 受益人类型
enum BeneficiaryType {
    TEAM,           // 团队：4 年锁仓
    EARLY_SUPPORTER // 早期支持者：2 年锁仓
}
```

| 检查项 | 白皮书 | 代码 | 结果 |
|--------|--------|------|------|
| 类型枚举完整性 | TEAM + EARLY_SUPPORTER | TEAM + EARLY_SUPPORTER | ✅ |
| 描述准确性 | 4 年锁仓 / 2 年锁仓 | 注释与白皮书一致 | ✅ |

---

### 3.2 团队注册函数

**文件：** `contracts/src/VIBVesting.sol`，第 252-273 行

```solidity
/**
 * @notice 批量注册团队成员（不转移代币）
 * @dev 用于代币已通过distributeToPools mint到合约后的场景
 * @param teamMembers 团队成员地址数组
 * @param amounts 分配数量数组
 * @param vestingStart 锁仓开始时间
 */
function registerTeamMembers(
    address[] calldata teamMembers,
    uint256[] calldata amounts,
    uint256 vestingStart
) external onlyOwner {
    // 团队成员：4 年锁仓，1 年悬崖期
    _registerBeneficiaries(
        teamMembers,
        amounts,
        vestingStart,
        BeneficiaryType.TEAM,
        4 * SECONDS_PER_YEAR,  // 4年 = 1,460 天
        365 days               // 1年悬崖期
    );
}
```

| 检查项 | 白皮书 | 代码 | 结果 |
|--------|--------|------|------|
| 锁仓期 | 4 年 | `4 * SECONDS_PER_YEAR` | ✅ |
| 悬崖期 | 1 年 | `365 days` | ✅ |
| 受益人类型 | TEAM | `BeneficiaryType.TEAM` | ✅ |

---

### 3.3 早期支持者注册函数

**文件：** `contracts/src/VIBVesting.sol`，第 275-296 行

```solidity
/**
 * @notice 批量注册早期支持者（不转移代币）
 * @dev 用于代币已通过distributeToPools mint到合约后的场景
 * @param supporters 支持者地址数组
 * @param amounts 分配数量数组
 * @param vestingStart 锁仓开始时间
 */
function registerEarlySupporters(
    address[] calldata supporters,
    uint256[] calldata amounts,
    uint256 vestingStart
) external onlyOwner {
    // 早期支持者：2 年锁仓，6 个月悬崖期
    _registerBeneficiaries(
        supporters,
        amounts,
        vestingStart,
        BeneficiaryType.EARLY_SUPPORTER,
        2 * SECONDS_PER_YEAR,  // 2年 = 730 天
        182 days               // 6个月悬崖期
    );
}
```

| 检查项 | 白皮书 | 代码 | 结果 |
|--------|--------|------|------|
| 锁仓期 | 2 年 | `2 * SECONDS_PER_YEAR` | ✅ |
| 悬崖期 | 6 个月 | `182 days` | ✅ |
| 受益人类型 | EARLY_SUPPORTER | `BeneficiaryType.EARLY_SUPPORTER` | ✅ |

---

### 3.4 释放逻辑（线性释放）

**文件：** `contracts/src/VIBVesting.sol`，第 583-610 行

```solidity
/**
 * @notice 计算已归属金额
 * @param beneficiary 受益人地址
 * @return 已归属金额
 */
function _vestedAmount(address beneficiary) internal view returns (uint256) {
    BeneficiaryInfo memory info = beneficiaries[beneficiary];

    uint256 totalAllocation = info.totalAmount;

    // 如果未到开始时间，返回 0
    if (block.timestamp < info.vestingStart) {
        return 0;
    }

    uint256 elapsedTime = block.timestamp - info.vestingStart;

    // 如果在悬崖期内，返回 0
    if (elapsedTime < info.cliffPeriod) {
        return 0;
    }

    // 如果超过锁仓期，返回全部
    if (elapsedTime >= info.vestingDuration) {
        return totalAllocation;
    }

    // 线性释放计算
    uint256 vestedTime = elapsedTime - info.cliffPeriod;
    uint256 vestingTime = info.vestingDuration - info.cliffPeriod;

    return (totalAllocation * vestedTime) / vestingTime;
}
```

**释放逻辑逐阶段验证（以团队 4 年锁仓、1 年悬崖为例）：**

| 时间点 | 经过时间 | 悬崖判断 | 是否在悬崖期 | 释放计算 | 归属比例 |
|--------|----------|----------|-------------|----------|---------|
| T+0（第 0 天） | 0 | 0 < 365 days | ✅ 是 | return 0 | 0% |
| T+6 个月 | 180 天 | 180 < 365 | ✅ 是 | return 0 | 0% |
| T+1 年（第 365 天） | 365 天 | 365 !< 365 | ❌ 否，进入线性 | (total × 0) / 1095 | 0% |
| T+2 年（第 730 天） | 730 天 | — | ❌ 否 | (total × 365) / 1095 ≈ 33.3% | ~33.3% |
| T+3 年（第 1095 天） | 1095 天 | — | ❌ 否 | (total × 730) / 1095 ≈ 66.7% | ~66.7% |
| T+4 年（第 1460 天） | 1460 天 | elapsed ≥ duration | ✅ 是（全部） | return total | 100% |

> **注：** 实际线性释放期为 3 年（1095 天 = 4年-1年悬崖），第 4 年末达到 100%。第 2 年释放约 33.3%，与白皮书"第 2 年释放 ~2.67%"存在数值表述差异（白皮书可能以总代币量为基准，即 8% × 33.3% ≈ 2.67%），实质逻辑一致。

| 检查项 | 白皮书 | 代码 | 结果 |
|--------|--------|------|------|
| 悬崖期内不解锁 | 0% | `elapsedTime < cliffPeriod → return 0` | ✅ |
| 悬崖后线性释放 | 线性 | `(total × vestedTime) / vestingTime` | ✅ |
| 锁仓期末全部归属 | 100% | `elapsedTime >= vestingDuration → return total` | ✅ |

---

### 3.5 代币分配（VIBEToken）

**文件：** `contracts/src/VIBEToken.sol`，第 280-325 行

```solidity
function distributeToPools(
    address _emissionController,     // 63%
    address _outputRewardPool,       // 13%（由EC内部转账）
    address _teamVesting,           // 8%
    address _earlySupporterVesting, // 4%
    address _communityFund,         // 6%
    address _liquidityManager,      // 12%
    address _airdropDistributor     // 7%
) external onlyOwner {
    // 激励池 63%
    _mint(_emissionController, (TOTAL_SUPPLY * PERCENT_EMISSION_POOL) / 10000);

    // 直接分配部分（37%）
    _mint(_teamVesting, (TOTAL_SUPPLY * PERCENT_TEAM) / 10000);              // 8%
    _mint(_earlySupporterVesting, (TOTAL_SUPPLY * PERCENT_EARLY_SUPPORTER) / 10000); // 4%
    _mint(_communityFund, (TOTAL_SUPPLY * PERCENT_COMMUNITY) / 10000);      // 6%
    _mint(_liquidityManager, (TOTAL_SUPPLY * PERCENT_LIQUIDITY) / 10000);   // 12%
    _mint(_airdropDistributor, (TOTAL_SUPPLY * PERCENT_AIRDROP) / 10000);    // 7%

    // 设置免税地址
    taxExemptedAddresses[_teamVesting] = true;
    taxExemptedAddresses[_earlySupporterVesting] = true;
    // ...
}
```

| 检查项 | 白皮书 | 代码 | 结果 |
|--------|--------|------|------|
| 团队 8% | 80,000,000 VIBE | `(TOTAL_SUPPLY * 800) / 10000` | ✅ |
| 早期支持者 4% | 40,000,000 VIBE | `(TOTAL_SUPPLY * 400) / 10000` | ✅ |
| 合约分离 | 独立合约 | `_teamVesting` 和 `_earlySupporterVesting` 是独立参数 | ✅ |
| 比例合计 | 12% | 800 + 400 = 1200 bps = 12% | ✅ |

---

## 四、一致性总结

### 4.1 完全一致项 ✅

| 模块 | 白皮书规定 | 代码实现 |
|------|-----------|---------|
| 团队锁仓期 | 4 年线性释放 | `4 * SECONDS_PER_YEAR` |
| 团队悬崖期 | 1 年 | `365 days` |
| 早期支持者锁仓期 | 2 年线性释放 | `2 * SECONDS_PER_YEAR` |
| 早期支持者悬崖期 | 6 个月 | `182 days` |
| 释放模式 | 悬崖后线性 | `_vestedAmount()` 线性计算 |
| 代币比例 | 团队 8% + 早期支持者 4% | 精确的 bps 分配 |
| 合约架构 | 团队/早期支持者分离 | 两个独立参数地址 |
| 免税处理 | 合约间互转免税 | `taxExemptedAddresses` 映射 |

### 4.2 需关注项 ⚠️

---

## 五、关键架构说明：受益人是后续动态添加的

> **⚠️ 重要声明**
>
> VIBVesting 合约的受益人（团队成员、早期支持者）**并非在合约部署时自动创建**，而是需要**在 `distributeToPools()` 执行后，通过部署脚本或手动调用注册函数来动态添加**。

### 5.1 设计原因

VIBVesting 是一个**多受益人通用锁仓合约**，其设计哲学是：

```
┌──────────────────────────────────────────────────────────────┐
│                    部署阶段                                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  VIBEToken.distributeToPools()                              │
│  ├── mint 8% → teamVesting 合约（代币到位，受益人未注册）     │
│  ├── mint 4% → earlySupporterVesting 合约（代币到位，受益人未注册）│
│  └── 设置免税地址                                             │
│                                                              │
│  此时：代币已在合约中，但没有受益人信息，任何人都无法提取        │
│                                                              │
└──────────────────────────────────────────────────────────────┘

                              ↓（部署脚本第二步）

┌──────────────────────────────────────────────────────────────┐
│                    初始化阶段（部署脚本）                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  teamVesting.registerTeamMembers([...], vestingStart)       │
│  ├── 注册团队成员地址                                          │
│  ├── 分配各成员数量                                           │
│  └── 设置锁仓参数（4年 / 1年悬崖）                            │
│                                                              │
│  earlySupporterVesting.registerEarlySupporters([...], vestingStart)│
│  ├── 注册早期支持者地址                                        │
│  ├── 分配各支持者数量                                         │
│  └── 设置锁仓参数（2年 / 6个月悬崖）                          │
│                                                              │
│  此时：受益人信息完整，代币可按规则释放                         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 两套注册接口

**方式一：批量注册（推荐，用于生产部署）**

```solidity
// 注册团队成员（4年锁仓 / 1年悬崖）
teamVesting.registerTeamMembers(
    [0xTeamMember1, 0xTeamMember2, ...],   // 团队成员地址数组
    [50000000e18, 30000000e18, ...],       // 各成员分配数量数组
    block.timestamp                         // 锁仓开始时间（即部署时间）
);

// 注册早期支持者（2年锁仓 / 6个月悬崖）
earlySupporterVesting.registerEarlySupporters(
    [0xSupporter1, 0xSupporter2, ...],     // 早期支持者地址数组
    [20000000e18, 20000000e18, ...],        // 各支持者分配数量数组
    block.timestamp                         // 锁仓开始时间
);
```

**方式二：单独注册（灵活性高）**

```solidity
// 注册单个受益人（通用接口，可用于任意锁仓参数）
vestingContract.registerBeneficiary(
    beneficiary,        // 地址
    amount,             // 数量
    BeneficiaryType.TEAM,           // 或 EARLY_SUPPORTER
    block.timestamp,    // vestingStart
    4 * 365 days,       // vestingDuration
    365 days            // cliffPeriod
);

// 添加受益人（代币从调用者转入）
vestingContract.addBeneficiary(
    beneficiary,
    amount,
    BeneficiaryType.TEAM,
    block.timestamp,
    4 * 365 days,
    365 days
);
```

### 5.3 受益人信息结构

注册后，每个受益人在合约中存储为 `BeneficiaryInfo` 结构体：

```solidity
struct BeneficiaryInfo {
    uint256 totalAmount;          // 总分配量（如 50,000,000 VIBE）
    uint256 releasedAmount;       // 已释放量（累计）
    uint256 vestingStart;         // 锁仓开始时间（部署时的时间戳）
    uint256 vestingDuration;      // 锁仓持续时间（团队 4 年 / 早期支持者 2 年）
    uint256 cliffPeriod;          // 悬崖期（团队 1 年 / 早期支持者 6 个月）
    uint256 vestingType;          // 受益人类型（0=TEAM, 1=EARLY_SUPPORTER）
    bool isActive;                // 是否活跃
}
```

### 5.4 提取流程

受益人注册完成后，团队/早期支持者通过以下流程提取代币：

```
受益人调用 vestingContract.release() 或由任意人触发 releaseBatch()
  │
  ├─ 计算当前可释放金额 _releasableAmount()
  │    └─ _vestedAmount() - 已释放量
  │         └─ 悬崖期内 → 0
  │         └─ 悬崖后 → 线性计算
  │         └─ 锁仓期满 → 全部
  │
  └─ safeTransfer 将可释放代币转给受益人
```

---

## 六、部署检查清单

> 以下步骤必须在主网部署时按顺序执行，否则 Vesting 合约中的代币将无法释放。

### Step 1：部署所有合约

```
[ ] 部署 VIBEToken
[ ] 部署 VIBVesting（团队用）
[ ] 部署 VIBVesting（早期支持者用）
[ ] 部署其他池合约（EC, Staking, CommunityFund, etc.）
```

### Step 2：分配代币（VIBEToken 层面）

```
[ ] 调用 VIBEToken.distributeToPools(
        _emissionController,     // EC 地址
        _outputRewardPool,       // 产出池地址
        _teamVesting,           // 团队 Vesting 地址 ← 8%
        _earlySupporterVesting,  // 早期支持者 Vesting 地址 ← 4%
        _communityFund,          // 社区基金地址 ← 6%
        _liquidityManager,       // 流动性管理器 ← 12%
        _airdropDistributor     // 空投分发器 ← 7%
    )
    → 此时 8% + 4% 代币已 mint 到各自的 Vesting 合约
    → 但 Vesting 合约中没有受益人信息
```

### Step 3：注册团队受益人 ⚠️（缺失风险点）

```
[ ] 调用 teamVesting.registerTeamMembers(
        [0xMember1, 0xMember2, ...],    // 团队成员地址
        [50000000e18, 30000000e18, ...], // 对应分配数量
        <部署时间戳>                      // vestingStart（建议与部署时间一致）
    )
    → 锁仓期自动设为 4 年
    → 悬崖期自动设为 1 年
    → 总分配量必须 ≤ 8000 万 VIBE（8%）
```

### Step 4：注册早期支持者受益人 ⚠️（缺失风险点）

```
[ ] 调用 earlySupporterVesting.registerEarlySupporters(
        [0xSupporter1, 0xSupporter2, ...], // 早期支持者地址
        [20000000e18, 20000000e18, ...],   // 对应分配数量
        <部署时间戳>                        // vestingStart
    )
    → 锁仓期自动设为 2 年
    → 悬崖期自动设为 6 个月
    → 总分配量必须 ≤ 4000 万 VIBE（4%）
```

### Step 5：验证部署结果

```
[ ] 查询 teamVesting.beneficiaryCount() → 应为团队成员数量
[ ] 查询 earlySupporterVesting.beneficiaryCount() → 应为早期支持者数量
[ ] 查询 teamVesting.beneficiaries(<成员地址>) → 确认 totalAmount / vestingDuration / cliffPeriod 正确
[ ] 查询 earlySupporterVesting.beneficiaries(<支持者地址>) → 确认参数正确
[ ] 查询 teamVesting.contractBalance() → 应 ≈ 8000 万 VIBE（扣除已释放部分）
[ ] 查询 earlySupporterVesting.contractBalance() → 应 ≈ 4000 万 VIBE（扣除已释放部分）
```

---

## 七、结论

| 维度 | 评估 |
|------|------|
| **白皮书符合度** | ✅ 核心锁仓规则（4年/1年悬崖 + 2年/6个月悬崖）完全一致 |
| **代码质量** | ✅ 线性释放逻辑正确，CEI 模式安全实现 |
| **部署完整性** | ⚠️ 需确保部署脚本包含 Step 3 和 Step 4 的受益人注册调用 |
| **风险等级** | **中等**——若跳过 Step 3/4，代币永久锁在合约无法释放 |

**总体判断：代码逻辑完全符合白皮书，部署流程需按检查清单补充受益人注册步骤。**

---

## 八、附录：关键代码索引

| 功能 | 文件位置 | 行号 |
|------|---------|------|
| 受益人类型枚举 | `VIBVesting.sol` | 46-52 |
| 团队注册函数 | `VIBVesting.sol` | 252-273 |
| 早期支持者注册函数 | `VIBVesting.sol` | 275-296 |
| 释放计算逻辑 | `VIBVesting.sol` | 583-610 |
| 代币分配函数 | `VIBEToken.sol` | 280-325 |
| 受益人信息结构体 | `VIBVesting.sol` | 76-87 |
| 批量注册内部实现 | `VIBVesting.sol` | 314-370 |
