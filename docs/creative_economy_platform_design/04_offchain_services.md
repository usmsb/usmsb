[Chapter 5: Off-Chain Services Design](#51-joint-order-service) | [中文](#51-联合订单服务)

---

## 5.1 Joint Order Service

### Service Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        JointOrderService                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Off-Chain Logic                      On-Chain Interaction                  │
│  ┌─────────────────┐                  ┌─────────────────┐                   │
│  │  Demand Aggregation│              │                 │                   │
│  │  - Similarity   │              │  JointOrder.sol  │                   │
│  │    Matching     │              │                 │                   │
│  │  - Pooling      │              │  Escrow Funds    │                   │
│  │    Decision      │──────────────►│  State Management│                   │
│  │  - Provider     │              │  Settlement      │                   │
│  │    Invitation   │              │  Execution        │                   │
│  └─────────────────┘              └─────────────────┘                       │
│                                    │  Event Listener                      │
│  ┌─────────────────┐              ┌─────────────────┐                       │
│  │  Bid Evaluation │              │  Event Handler  │                       │
│  │  - Price Score  │              │  State Sync     │                       │
│  │  - Reputation   │              │  Data Update    │                       │
│  │    Score        │              │                 │                       │
│  │  - Comprehensive│              └─────────────────┘                       │
│  │    Ranking      │                                                        │
│  └─────────────────┘                                                        │
│                                                                             │
│  ┌─────────────────┐              ┌─────────────────┐                       │
│  │  Contract       │◄─────────────│  Event Listener │                       │
│  │  Interaction   │              │  Data Update    │                       │
│  │  - Transaction │              │                 │                       │
│  │    Building    │              │                 │                       │
│  │  - Signature   │              │                 │                       │
│  │    Authorization              │                 │                       │
│  │  - Gas          │              │                 │                       │
│  │    Optimization │              │                 │                       │
│  └─────────────────┘              └─────────────────┘                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core Class Design

```python
class JointOrderService:
    """Joint Order Service"""

    # Configuration
    BIDDING_DURATION_DEFAULT = 86400  # 24 hours
    DELIVERY_DEADLINE_DEFAULT = 604800  # 7 days
    MIN_POOL_BUDGET = 100  # Minimum pool budget

    async def create_demand(self, demand: Demand) -> str:
        """Create demand"""

    async def aggregate_demands(self, new_demand: Demand) -> Optional[OrderPool]:
        """Aggregate demands into suitable pools"""

    async def invite_providers(self, pool: OrderPool) -> List[str]:
        """Invite providers to participate in bidding"""

    async def submit_bid(self, pool_id: str, bid: Bid) -> bool:
        """Submit bid"""

    async def evaluate_bids(self, pool_id: str) -> Bid:
        """Evaluate bids and select optimal"""

    async def confirm_delivery(self, pool_id: str, user_id: str, rating: int) -> bool:
        """Confirm delivery"""

    async def withdraw_earnings(self, pool_id: str) -> bool:
        """Withdraw earnings"""

    async def raise_dispute(self, pool_id: str, reason: str) -> bool:
        """Raise dispute"""
```

---

## 5.2 Asset Fractionalization Service

### Service Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      AssetFractionalizationService                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐                  ┌─────────────────┐                   │
│  │  Dynamic        │                  │                 │                   │
│  │  Valuation      │                  │  AssetVault.sol │                   │
│  │  Engine         │                  │  NFT Deposit    │                   │
│  │  - Market       │──────────────►   │  Fraction       │                   │
│  │    Analysis     │                  │  Issuance       │                   │
│  │  - Fraction     │                  │  Revenue        │                   │
│  │    Pricing      │                  │  Distribution   │                   │
│  │  - Issuance     │                  │                 │                   │
│  │    Recommendation                │                 │                   │
│  └─────────────────┘                  └─────────────────┘                       │
│                                                                             │
│  ┌─────────────────┐                                                        │
│  │  NFT Metadata   │                                                        │
│  │  Management      │                                                        │
│  │  - Metadata     │                                                        │
│  │    Storage      │                                                        │
│  │  - IPFS Upload  │                                                        │
│  │  - Copyright    │                                                        │
│  │    Verification │                                                        │
│  └─────────────────┘                                                        │
│                                                                             │
│  ┌─────────────────┐                  ┌─────────────────┐                   │
│  │  Market Trading │                  │  Revenue        │                   │
│  │  Service        │                  │  Calculation    │                   │
│  │  - Transaction │                  │  - Dividend     │                   │
│  │    Matching    │                  │    Calculation  │                   │
│  │  - Price        │                  │  - Pending      │                   │
│  │    Monitoring   │                  │    Claims       │                   │
│  └─────────────────┘                  │    Update       │                   │
│                                       └─────────────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core Class Design

```python
class AssetFractionalizationService:
    """Asset Fractionalization Service"""

    async def deposit_nft(
        self,
        nft_contract: str,
        token_id: int,
        metadata: NFTMetadata
    ) -> str:
        """Deposit NFT and prepare for fractionalization"""

    async def calculate_fragmentation(
        self,
        asset_id: str,
        market_data: MarketData
    ) -> FragmentationPlan:
        """Calculate fractionalization plan"""

    async def issue_shares(
        self,
        asset_id: str,
        plan: FragmentationPlan
    ) -> bool:
        """Issue shares"""

    async def purchase_shares(
        self,
        asset_id: str,
        buyer: str,
        amount: int
    ) -> bool:
        """Purchase shares"""

    async def distribute_earnings(
        self,
        asset_id: str,
        amount: float
    ) -> bool:
        """Distribute earnings"""

    async def claim_earnings(
        self,
        asset_id: str,
        holder: str
    ) -> float:
        """Claim earnings"""
```

---

## 5.3 ZK Proof Service

### Service Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ZKCredentialService                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐                  ┌─────────────────┐                   │
│  │  Proof          │                  │                 │                   │
│  │  Generation     │                  │ZKCredential.sol│                   │
│  │  Engine         │                  │  Proof          │                   │
│  │  - Circuit      │──────────────►   │  Verification   │                   │
│  │    Compilation  │                  │  Credential     │                   │
│  │  - Proof        │                  │  Issuance       │                   │
│  │    Computation  │                  │  Access Control │                   │
│  │  - Public Input │                  │                 │                   │
│  │    Building     │                  │                 │                   │
│  └─────────────────┘                  └─────────────────┘                       │
│                                                                             │
│  ┌─────────────────┐                                                        │
│  │  Private Data   │                                                        │
│  │  Management      │                                                        │
│  │  - Encrypted     │                                                        │
│  │    Storage       │                                                        │
│  │  - Data          │                                                        │
│  │    Aggregation  │                                                        │
│  │  - Secure        │                                                        │
│  │    Deletion     │                                                        │
│  └─────────────────┘                                                        │
│                                                                             │
│  ┌─────────────────┐                  ┌─────────────────┐                   │
│  │  Credential     │                  │  Verification   │                   │
│  │  Management     │                  │  Key Management │                   │
│  │  - Credential   │                  │  - Key Update   │                   │
│  │    Storage      │                  │  - Key          │                   │
│  │  - Validity     │                  │    Verification │                   │
│  │    Check        │                  │                 │                   │
│  └─────────────────┘                  └─────────────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core Class Design

```python
class ZKCredentialService:
    """ZK Credential Pass Service"""

    async def generate_proof(
        self,
        credential_type: CredentialType,
        private_inputs: PrivateInputs
    ) -> ZKProof:
        """Generate zero-knowledge proof"""

    async def issue_credential(
        self,
        credential_type: CredentialType,
        proof: ZKProof,
        holder: str
    ) -> str:
        """Issue credential"""

    async def verify_credential(
        self,
        credential_id: str,
        proof: ZKProof
    ) -> bool:
        """Verify credential"""

    async def revoke_credential(
        self,
        credential_id: str,
        reason: str
    ) -> bool:
        """Revoke credential"""

    async def check_credential_validity(
        self,
        credential_id: str
    ) -> CredentialStatus:
        """Check credential validity"""
```

<details>
<summary><h2>中文翻译</h2></summary>

# 第5章：链下服务设计

## 5.1 联合订单服务

### 服务架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        JointOrderService                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  链下逻辑                          链上交互                                   │
│  ┌─────────────────┐              ┌─────────────────┐                       │
│  │ 需求聚合引擎     │              │                 │                       │
│  │ - 相似度匹配     │              │  JointOrder.sol  │                       │
│  │ - 池化决策       │              │                 │                       │
│  │ - 邀请服务商     │──────────────►│  托管资金       │                       │
│  └─────────────────┘              │  状态管理       │                       │
│                                    │  结算执行       │                       │
│  ┌─────────────────┐              │                 │                       │
│  │ 竞价评估引擎     │              └─────────────────┘                       │
│  │ - 价格评分       │                        ▲                               │
│  │ - 信誉评分       │                        │ 监听事件                    │
│  │ - 综合排序       │                        ▼                               │
│  └─────────────────┘              ┌─────────────────┐                       │
│                                    │  事件处理器     │                       │
│  ┌─────────────────┐              │  状态同步       │                       │
│  │ 合约交互层       │◄─────────────│  数据更新       │                       │
│  │ - 交易构建       │              └─────────────────┘                       │
│  │ - 签名授权       │                                                        │
│  │ - Gas优化       │                                                        │
│  └─────────────────┘                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 核心类设计

```python
class JointOrderService:
    """联合订单服务"""

    # 配置
    BIDDING_DURATION_DEFAULT = 86400  # 24小时
    DELIVERY_DEADLINE_DEFAULT = 604800  # 7天
    MIN_POOL_BUDGET = 100  # 最低池预算

    async def create_demand(self, demand: Demand) -> str:
        """创建需求"""

    async def aggregate_demands(self, new_demand: Demand) -> Optional[OrderPool]:
        """聚合需求到合适的池"""

    async def invite_providers(self, pool: OrderPool) -> List[str]:
        """邀请服务商参与竞价"""

    async def submit_bid(self, pool_id: str, bid: Bid) -> bool:
        """提交竞价"""

    async def evaluate_bids(self, pool_id: str) -> Bid:
        """评估竞价并选择最优"""

    async def confirm_delivery(self, pool_id: str, user_id: str, rating: int) -> bool:
        """确认交付"""

    async def withdraw_earnings(self, pool_id: str) -> bool:
        """提取收益"""

    async def raise_dispute(self, pool_id: str, reason: str) -> bool:
        """发起争议"""
```

---

## 5.2 资产碎片化服务

### 服务架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      AssetFractionalizationService                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐              ┌─────────────────┐                       │
│  │ 动态估值引擎     │              │                 │                       │
│  │ - 市场分析       │              │  AssetVault.sol │                       │
│  │ - 碎片定价       │──────────────►│  NFT存入        │                       │
│  │ - 发行建议       │              │  碎片发行       │                       │
│  └─────────────────┘              │  收益分发       │                       │
│                                    │                 │                       │
│  ┌─────────────────┐              └─────────────────┘                       │
│  │ NFT元数据管理    │                                                        │
│  │ - 元数据存储     │                                                        │
│  │ - IPFS上传      │                                                        │
│  │ - 版权验证       │                                                        │
│  └─────────────────┘                                                        │
│                                                                             │
│  ┌─────────────────┐              ┌─────────────────┐                       │
│  │ 市场交易服务     │              │  收益计算       │                       │
│  │ - 交易匹配       │              │ - 分红计算      │                       │
│  │ - 价格监控       │              │ - 待领取更新    │                       │
│  └─────────────────┘              └─────────────────┘                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 核心类设计

```python
class AssetFractionalizationService:
    """资产碎片化服务"""

    async def deposit_nft(
        self,
        nft_contract: str,
        token_id: int,
        metadata: NFTMetadata
    ) -> str:
        """存入NFT并准备碎片化"""

    async def calculate_fragmentation(
        self,
        asset_id: str,
        market_data: MarketData
    ) -> FragmentationPlan:
        """计算碎片化方案"""

    async def issue_shares(
        self,
        asset_id: str,
        plan: FragmentationPlan
    ) -> bool:
        """发行碎片"""

    async def purchase_shares(
        self,
        asset_id: str,
        buyer: str,
        amount: int
    ) -> bool:
        """购买碎片"""

    async def distribute_earnings(
        self,
        asset_id: str,
        amount: float
    ) -> bool:
        """分发收益"""

    async def claim_earnings(
        self,
        asset_id: str,
        holder: str
    ) -> float:
        """领取收益"""
```

---

## 5.3 zk证明服务

### 服务架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ZKCredentialService                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐              ┌─────────────────┐                       │
│  │ 证明生成引擎     │              │                 │                       │
│  │ - 电路编译       │              │ZKCredential.sol │                       │
│  │ - 证明计算       │──────────────►│  证明验证       │                       │
│  │ - 公开输入构建   │              │  凭证签发       │                       │
│  └─────────────────┘              │  权限控制       │                       │
│                                    │                 │                       │
│  ┌─────────────────┐              └─────────────────┘                       │
│  │ 私有数据管理     │                                                        │
│  │ - 加密存储       │                                                        │
│  │ - 数据聚合       │                                                        │
│  │ - 安全删除       │                                                        │
│  └─────────────────┘                                                        │
│                                                                             │
│  ┌─────────────────┐              ┌─────────────────┐                       │
│  │ 凭证管理         │              │  验证密钥管理   │                       │
│  │ - 凭证存储       │              │ - 密钥更新      │                       │
│  │ - 有效期检查     │              │ - 密钥验证      │                       │
│  └─────────────────┘              └─────────────────┘                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 核心类设计

```python
class ZKCredentialService:
    """zk信用通行证服务"""

    async def generate_proof(
        self,
        credential_type: CredentialType,
        private_inputs: PrivateInputs
    ) -> ZKProof:
        """生成零知识证明"""

    async def issue_credential(
        self,
        credential_type: CredentialType,
        proof: ZKProof,
        holder: str
    ) -> str:
        """签发凭证"""

    async def verify_credential(
        self,
        credential_id: str,
        proof: ZKProof
    ) -> bool:
        """验证凭证"""

    async def revoke_credential(
        self,
        credential_id: str,
        reason: str
    ) -> bool:
        """撤销凭证"""

    async def check_credential_validity(
        self,
        credential_id: str
    ) -> CredentialStatus:
        """检查凭证有效性"""
```

</details>
