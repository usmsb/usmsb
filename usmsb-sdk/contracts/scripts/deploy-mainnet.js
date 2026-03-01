const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

/**
 * VIBE Protocol 完整主网部署脚本
 *
 * 部署顺序（按依赖关系）:
 *
 * 第一阶段：基础层
 * 1. VIBEToken - 核心代币
 * 2. VIBVesting (团队) - 4年锁仓
 * 3. VIBVesting (早期支持者) - 2年锁仓
 * 4. VIBIdentity - 身份注册
 *
 * 第二阶段：自动化层
 * 5. PriceOracle - 价格预言机
 * 6. CommunityStableFund - 社区稳定基金 6%
 * 7. LiquidityManager - 流动性管理 12%
 * 8. AirdropDistributor - 空投分发 7%
 * 9. EmissionController - 激励池 63%
 *
 * 第三阶段：质押与分红层
 * 10. VIBStaking - 质押管理
 * 11. VIBDividend - 分红管理
 * 12. VIBVEPoints - VE积分
 *
 * 第四阶段：激励分配层（释放池）
 * 13. VIBEcosystemPool - 生态激励协调器
 * 14. VIBNodeReward - 节点激励
 * 15. VIBDevReward - 开发者激励
 * 16. VIBBuilderReward - 建设者激励
 * 17. VIBReserve - 储备基金
 *
 * 第五阶段：交易手续费分配层
 * 18. VIBInfrastructurePool - 基础设施节点
 * 19. VIBProtocolFund - 协议基金
 *
 * 第六阶段：治理与争议层
 * 20. VIBGovernance - 治理合约
 * 21. VIBDispute - 争议解决
 * 22. VIBTimelock - 治理时间锁
 *
 * 第七阶段：输出与协作层
 * 23. VIBOutputReward - AI产出激励
 * 24. VIBCollaboration - 协作合约
 * 25. AgentWallet - Agent钱包
 * 26. AssetVault - 资产金库
 * 27. JointOrder - 联合订单
 *
 * 第八阶段：配置与连接
 * - 设置所有合约地址关联
 * - 分配代币到各池
 * - 配置权限和参数
 */

// 等待函数
async function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function main() {
  console.log("=".repeat(80));
  console.log("  VIBE Protocol - 完整主网部署脚本");
  console.log("  版本: v1.0.0 (2026-03-01)");
  console.log("=".repeat(80));

  const [deployer, treasury] = await hre.ethers.getSigners();
  console.log("\n📋 部署账户信息:");
  console.log("  Deployer:", deployer.address);
  console.log("  Treasury:", treasury ? treasury.address : deployer.address);

  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("  Balance:", hre.ethers.formatEther(balance), "ETH");
  console.log("  Network:", hre.network.name);

  if (balance === 0n) {
    console.log("\n❌ 错误: 余额为0！需要ETH来部署合约。");
    process.exit(1);
  }

  const deployedContracts = {};
  const deploymentDir = "./deployments";

  // 创建部署目录
  if (!fs.existsSync(deploymentDir)) {
    fs.mkdirSync(deploymentDir, { recursive: true });
  }

  // Base Sepolia/主网 地址
  const BASE_SEPOLIA_WETH = "0x4200000000000000000000000000000000000006";
  const BASE_SEPOLIA_ROUTER = "0xf253b36702f9a4da019377acfee8658e7136b231";
  // Base Sepolia 没有官方 Uniswap V2，使用主网地址（功能在测试网不可用，但可部署）
  const BASE_SEPOLIA_FACTORY = "0x8909Dc15e40173Ff4699343b6eB8132c65e18eC6";
  const BASE_MAINNET_WETH = "0x4200000000000000000000000000000000000006";
  const BASE_MAINNET_ROUTER = "0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24";
  const BASE_MAINNET_FACTORY = "0x8909Dc15e40173Ff4699343b6eB8132c65e18eC6";

  const isBaseSepolia = hre.network.name === "baseSepolia";
  const isBaseMainnet = hre.network.name === "base" || hre.network.name === "baseMainnet";

  let wethAddress, routerAddress, factoryAddress;
  if (isBaseSepolia) {
    wethAddress = BASE_SEPOLIA_WETH;
    routerAddress = BASE_SEPOLIA_ROUTER;
    factoryAddress = BASE_SEPOLIA_FACTORY;
  } else if (isBaseMainnet) {
    wethAddress = BASE_MAINNET_WETH;
    routerAddress = BASE_MAINNET_ROUTER;
    factoryAddress = BASE_MAINNET_FACTORY;
  } else {
    wethAddress = hre.ethers.ZeroAddress;
    routerAddress = hre.ethers.ZeroAddress;
    factoryAddress = hre.ethers.ZeroAddress;
  }

  // 最小流动性阈值
  const MIN_LIQUIDITY_THRESHOLD = hre.ethers.parseUnits("10000", 18); // 10000 VIBE

  // 代币分配常量
  const TOTAL_SUPPLY = hre.ethers.parseUnits("1000000000", 18); // 10亿

  try {
    // ============================================================
    // 第一阶段：基础层
    // ============================================================
    console.log("\n" + "=".repeat(80));
    console.log("  第一阶段：基础层");
    console.log("=".repeat(80));

    // 1. VIBEToken
    console.log("\n[1/27] 部署 VIBEToken...");
    const VIBEToken = await hre.ethers.getContractFactory("VIBEToken");
    const vibeToken = await VIBEToken.deploy(
      "VIBE Token",
      "VIBE",
      deployer.address
    );
    await vibeToken.waitForDeployment();
    deployedContracts.VIBEToken = await vibeToken.getAddress();
    console.log("   ✅ VIBEToken:", deployedContracts.VIBEToken);
    await wait(2000);

    // 2. VIBVesting (团队)
    console.log("\n[2/27] 部署 VIBVesting (团队 4年)...");
    const VIBVestingTeam = await hre.ethers.getContractFactory("VIBVesting");
    const teamVesting = await VIBVestingTeam.deploy(deployedContracts.VIBEToken);
    await teamVesting.waitForDeployment();
    deployedContracts.TeamVesting = await teamVesting.getAddress();
    console.log("   ✅ TeamVesting:", deployedContracts.TeamVesting);
    await wait(2000);

    // 3. VIBVesting (早期支持者)
    console.log("\n[3/27] 部署 VIBVesting (早期支持者 2年)...");
    const VIBVestingEarly = await hre.ethers.getContractFactory("VIBVesting");
    const earlyVesting = await VIBVestingEarly.deploy(deployedContracts.VIBEToken);
    await earlyVesting.waitForDeployment();
    deployedContracts.EarlyVesting = await earlyVesting.getAddress();
    console.log("   ✅ EarlyVesting:", deployedContracts.EarlyVesting);
    await wait(2000);

    // 4. VIBIdentity
    console.log("\n[4/27] 部署 VIBIdentity...");
    const VIBIdentity = await hre.ethers.getContractFactory("VIBIdentity");
    const vibeIdentity = await VIBIdentity.deploy(
      "VIBE Identity",
      "VIBID",
      deployedContracts.VIBEToken
    );
    await vibeIdentity.waitForDeployment();
    deployedContracts.VIBIdentity = await vibeIdentity.getAddress();
    console.log("   ✅ VIBIdentity:", deployedContracts.VIBIdentity);
    await wait(2000);

    // ============================================================
    // 第二阶段：自动化层
    // ============================================================
    console.log("\n" + "=".repeat(80));
    console.log("  第二阶段：自动化层");
    console.log("=".repeat(80));

    // 5. PriceOracle
    console.log("\n[5/27] 部署 PriceOracle...");
    const PriceOracle = await hre.ethers.getContractFactory("PriceOracle");
    const priceOracle = await PriceOracle.deploy(
      hre.ethers.ZeroAddress,
      hre.ethers.ZeroAddress,
      hre.ethers.ZeroAddress
    );
    await priceOracle.waitForDeployment();
    deployedContracts.PriceOracle = await priceOracle.getAddress();
    console.log("   ✅ PriceOracle:", deployedContracts.PriceOracle);
    await wait(2000);

    // 设置初始价格
    await wait(3000);
    const initialPrice = hre.ethers.parseUnits("0.01", 18);
    await priceOracle.setLastValidPrice(initialPrice, { gasLimit: 500000 });
    console.log("   ✅ 初始价格设置为 $0.01");

    // 6. CommunityStableFund
    console.log("\n[6/27] 部署 CommunityStableFund...");
    await wait(2000);
    const CommunityStableFund = await hre.ethers.getContractFactory("CommunityStableFund");
    const communityStableFund = await CommunityStableFund.deploy(
      deployedContracts.VIBEToken,
      wethAddress,
      deployedContracts.PriceOracle,
      routerAddress,
      MIN_LIQUIDITY_THRESHOLD
    );
    await communityStableFund.waitForDeployment();
    deployedContracts.CommunityStableFund = await communityStableFund.getAddress();
    console.log("   ✅ CommunityStableFund:", deployedContracts.CommunityStableFund);

    // 7. LiquidityManager
    console.log("\n[7/27] 部署 LiquidityManager...");
    await wait(2000);
    const LiquidityManager = await hre.ethers.getContractFactory("LiquidityManager");
    const liquidityManager = await LiquidityManager.deploy(
      deployedContracts.VIBEToken,
      wethAddress,
      routerAddress,
      factoryAddress
    );
    await liquidityManager.waitForDeployment();
    deployedContracts.LiquidityManager = await liquidityManager.getAddress();
    console.log("   ✅ LiquidityManager:", deployedContracts.LiquidityManager);

    // 8. AirdropDistributor
    console.log("\n[8/27] 部署 AirdropDistributor...");
    await wait(2000);
    const AirdropDistributor = await hre.ethers.getContractFactory("AirdropDistributor");
    const airdropDistributor = await AirdropDistributor.deploy(
      deployedContracts.VIBEToken,
      deployedContracts.CommunityStableFund,
      hre.ethers.ZeroHash
    );
    await airdropDistributor.waitForDeployment();
    deployedContracts.AirdropDistributor = await airdropDistributor.getAddress();
    console.log("   ✅ AirdropDistributor:", deployedContracts.AirdropDistributor);

    // 9. EmissionController
    console.log("\n[9/27] 部署 EmissionController...");
    await wait(2000);
    const EmissionController = await hre.ethers.getContractFactory("EmissionController");
    const emissionController = await EmissionController.deploy(
      deployedContracts.VIBEToken,
      hre.ethers.ZeroAddress, // 临时stakingPool
      hre.ethers.ZeroAddress, // 临时ecosystemPool
      hre.ethers.ZeroAddress, // 临时governancePool
      hre.ethers.ZeroAddress  // 临时reservePool
    );
    await emissionController.waitForDeployment();
    deployedContracts.EmissionController = await emissionController.getAddress();
    console.log("   ✅ EmissionController:", deployedContracts.EmissionController);

    // ============================================================
    // 第三阶段：质押与分红层
    // ============================================================
    console.log("\n" + "=".repeat(80));
    console.log("  第三阶段：质押与分红层");
    console.log("=".repeat(80));

    // 10. VIBStaking
    console.log("\n[10/27] 部署 VIBStaking...");
    await wait(2000);
    const VIBStaking = await hre.ethers.getContractFactory("VIBStaking");
    const vibStaking = await VIBStaking.deploy(deployedContracts.VIBEToken);
    await vibStaking.waitForDeployment();
    deployedContracts.VIBStaking = await vibStaking.getAddress();
    console.log("   ✅ VIBStaking:", deployedContracts.VIBStaking);

    // 11. VIBDividend
    console.log("\n[11/27] 部署 VIBDividend...");
    await wait(2000);
    const VIBDividend = await hre.ethers.getContractFactory("VIBDividend");
    const vibDividend = await VIBDividend.deploy(deployedContracts.VIBEToken);
    await vibDividend.waitForDeployment();
    deployedContracts.VIBDividend = await vibDividend.getAddress();
    console.log("   ✅ VIBDividend:", deployedContracts.VIBDividend);

    // 12. VIBVEPoints
    console.log("\n[12/27] 部署 VIBVEPoints...");
    await wait(2000);
    const VIBVEPoints = await hre.ethers.getContractFactory("VIBVEPoints");
    const vibVEPoints = await VIBVEPoints.deploy(
      hre.ethers.ZeroAddress, // 临时staking地址
      hre.ethers.ZeroAddress, // 临时outputReward地址
      hre.ethers.ZeroAddress  // 临时governance地址
    );
    await vibVEPoints.waitForDeployment();
    deployedContracts.VIBVEPoints = await vibVEPoints.getAddress();
    console.log("   ✅ VIBVEPoints:", deployedContracts.VIBVEPoints);

    // ============================================================
    // 第四阶段：激励分配层（释放池）
    // ============================================================
    console.log("\n" + "=".repeat(80));
    console.log("  第四阶段：激励分配层（释放池）");
    console.log("=".repeat(80));

    // 13. VIBEcosystemPool
    console.log("\n[13/27] 部署 VIBEcosystemPool...");
    await wait(2000);
    const VIBEcosystemPool = await hre.ethers.getContractFactory("VIBEcosystemPool");
    const vibEcosystemPool = await VIBEcosystemPool.deploy(
      deployedContracts.VIBEToken,
      deployedContracts.EmissionController
    );
    await vibEcosystemPool.waitForDeployment();
    deployedContracts.VIBEcosystemPool = await vibEcosystemPool.getAddress();
    console.log("   ✅ VIBEcosystemPool:", deployedContracts.VIBEcosystemPool);

    // 14. VIBNodeReward
    console.log("\n[14/27] 部署 VIBNodeReward...");
    await wait(2000);
    const VIBNodeReward = await hre.ethers.getContractFactory("VIBNodeReward");
    const vibNodeReward = await VIBNodeReward.deploy(
      deployedContracts.VIBEToken,
      deployedContracts.VIBIdentity
    );
    await vibNodeReward.waitForDeployment();
    deployedContracts.VIBNodeReward = await vibNodeReward.getAddress();
    console.log("   ✅ VIBNodeReward:", deployedContracts.VIBNodeReward);

    // 15. VIBDevReward
    console.log("\n[15/27] 部署 VIBDevReward...");
    await wait(2000);
    const VIBDevReward = await hre.ethers.getContractFactory("VIBDevReward");
    const vibDevReward = await VIBDevReward.deploy(deployedContracts.VIBEToken);
    await vibDevReward.waitForDeployment();
    deployedContracts.VIBDevReward = await vibDevReward.getAddress();
    console.log("   ✅ VIBDevReward:", deployedContracts.VIBDevReward);

    // 16. VIBBuilderReward
    console.log("\n[16/27] 部署 VIBBuilderReward...");
    await wait(2000);
    const VIBBuilderReward = await hre.ethers.getContractFactory("VIBBuilderReward");
    const vibBuilderReward = await VIBBuilderReward.deploy(deployedContracts.VIBEToken);
    await vibBuilderReward.waitForDeployment();
    deployedContracts.VIBBuilderReward = await vibBuilderReward.getAddress();
    console.log("   ✅ VIBBuilderReward:", deployedContracts.VIBBuilderReward);

    // 17. VIBReserve
    console.log("\n[17/27] 部署 VIBReserve...");
    await wait(2000);
    const VIBReserve = await hre.ethers.getContractFactory("VIBReserve");
    const vibReserve = await VIBReserve.deploy(deployedContracts.VIBEToken);
    await vibReserve.waitForDeployment();
    deployedContracts.VIBReserve = await vibReserve.getAddress();
    console.log("   ✅ VIBReserve:", deployedContracts.VIBReserve);

    // ============================================================
    // 第五阶段：交易手续费分配层
    // ============================================================
    console.log("\n" + "=".repeat(80));
    console.log("  第五阶段：交易手续费分配层");
    console.log("=".repeat(80));

    // 18. VIBInfrastructurePool
    console.log("\n[18/27] 部署 VIBInfrastructurePool...");
    await wait(2000);
    const VIBInfrastructurePool = await hre.ethers.getContractFactory("VIBInfrastructurePool");
    const vibInfrastructurePool = await VIBInfrastructurePool.deploy(deployedContracts.VIBEToken);
    await vibInfrastructurePool.waitForDeployment();
    deployedContracts.VIBInfrastructurePool = await vibInfrastructurePool.getAddress();
    console.log("   ✅ VIBInfrastructurePool:", deployedContracts.VIBInfrastructurePool);

    // 19. VIBProtocolFund
    console.log("\n[19/27] 部署 VIBProtocolFund...");
    await wait(2000);
    const VIBProtocolFund = await hre.ethers.getContractFactory("VIBProtocolFund");
    const vibProtocolFund = await VIBProtocolFund.deploy(deployedContracts.VIBEToken);
    await vibProtocolFund.waitForDeployment();
    deployedContracts.VIBProtocolFund = await vibProtocolFund.getAddress();
    console.log("   ✅ VIBProtocolFund:", deployedContracts.VIBProtocolFund);

    // ============================================================
    // 第六阶段：治理与争议层
    // ============================================================
    console.log("\n" + "=".repeat(80));
    console.log("  第六阶段：治理与争议层");
    console.log("=".repeat(80));

    // 20. VIBGovernance
    console.log("\n[20/27] 部署 VIBGovernance...");
    await wait(2000);
    const VIBGovernance = await hre.ethers.getContractFactory("VIBGovernance");
    const vibGovernance = await VIBGovernance.deploy(deployedContracts.VIBEToken);
    await vibGovernance.waitForDeployment();
    deployedContracts.VIBGovernance = await vibGovernance.getAddress();
    console.log("   ✅ VIBGovernance:", deployedContracts.VIBGovernance);

    // 21. VIBDispute
    console.log("\n[21/27] 部署 VIBDispute...");
    await wait(2000);
    const VIBDispute = await hre.ethers.getContractFactory("VIBDispute");
    const vibDispute = await VIBDispute.deploy(deployedContracts.VIBEToken);
    await vibDispute.waitForDeployment();
    deployedContracts.VIBDispute = await vibDispute.getAddress();
    console.log("   ✅ VIBDispute:", deployedContracts.VIBDispute);

    // 22. VIBTimelock
    console.log("\n[22/27] 部署 VIBTimelock...");
    await wait(2000);
    const VIBTimelock = await hre.ethers.getContractFactory("VIBTimelock");
    const vibTimelock = await VIBTimelock.deploy(
      7 * 24 * 60 * 60, // 7天
      deployer.address,
      deployer.address
    );
    await vibTimelock.waitForDeployment();
    deployedContracts.VIBTimelock = await vibTimelock.getAddress();
    console.log("   ✅ VIBTimelock:", deployedContracts.VIBTimelock);

    // ============================================================
    // 第七阶段：输出与协作层
    // ============================================================
    console.log("\n" + "=".repeat(80));
    console.log("  第七阶段：输出与协作层");
    console.log("=".repeat(80));

    // 23. VIBOutputReward
    console.log("\n[23/27] 部署 VIBOutputReward...");
    await wait(2000);
    const VIBOutputReward = await hre.ethers.getContractFactory("VIBOutputReward");
    const vibOutputReward = await VIBOutputReward.deploy(
      deployedContracts.VIBEToken,
      deployedContracts.VIBVEPoints
    );
    await vibOutputReward.waitForDeployment();
    deployedContracts.VIBOutputReward = await vibOutputReward.getAddress();
    console.log("   ✅ VIBOutputReward:", deployedContracts.VIBOutputReward);

    // 24. VIBCollaboration
    console.log("\n[24/27] 部署 VIBCollaboration...");
    await wait(2000);
    const VIBCollaboration = await hre.ethers.getContractFactory("VIBCollaboration");
    const vibCollaboration = await VIBCollaboration.deploy(
      deployedContracts.VIBEToken,
      deployedContracts.VIBOutputReward
    );
    await vibCollaboration.waitForDeployment();
    deployedContracts.VIBCollaboration = await vibCollaboration.getAddress();
    console.log("   ✅ VIBCollaboration:", deployedContracts.VIBCollaboration);

    // 25. AgentWallet
    console.log("\n[25/27] 部署 AgentWallet...");
    await wait(2000);
    const AgentWallet = await hre.ethers.getContractFactory("AgentWallet");
    const agentWallet = await AgentWallet.deploy();
    await agentWallet.waitForDeployment();
    deployedContracts.AgentWallet = await agentWallet.getAddress();
    console.log("   ✅ AgentWallet:", deployedContracts.AgentWallet);

    // 26. AssetVault
    console.log("\n[26/27] 部署 AssetVault...");
    await wait(2000);
    const AssetVault = await hre.ethers.getContractFactory("AssetVault");
    const assetVault = await AssetVault.deploy(deployer.address);
    await assetVault.waitForDeployment();
    deployedContracts.AssetVault = await assetVault.getAddress();
    console.log("   ✅ AssetVault:", deployedContracts.AssetVault);

    // 27. JointOrder
    console.log("\n[27/27] 部署 JointOrder...");
    await wait(2000);
    const JointOrder = await hre.ethers.getContractFactory("JointOrder");
    const jointOrder = await JointOrder.deploy(deployedContracts.VIBEToken);
    await jointOrder.waitForDeployment();
    deployedContracts.JointOrder = await jointOrder.getAddress();
    console.log("   ✅ JointOrder:", deployedContracts.JointOrder);

    // ============================================================
    // 第八阶段：配置与连接
    // ============================================================
    console.log("\n" + "=".repeat(80));
    console.log("  第八阶段：配置与连接");
    console.log("=".repeat(80));

    // 8.1 VIBEcosystemPool 设置子池
    console.log("\n[配置] VIBEcosystemPool 设置子池...");
    await wait(2000);
    await vibEcosystemPool.setRewardContracts(
      deployedContracts.VIBNodeReward,
      deployedContracts.VIBDevReward,
      deployedContracts.VIBBuilderReward
    );
    console.log("   ✅ 子池设置完成");

    // 8.2 VIBReserve 设置池地址
    console.log("\n[配置] VIBReserve 设置池地址...");
    await wait(2000);
    await vibReserve.setPoolAddress(0, deployedContracts.VIBStaking); // STAKING
    await wait(1000);
    await vibReserve.setPoolAddress(1, deployedContracts.VIBEcosystemPool); // ECOSYSTEM
    console.log("   ✅ 池地址设置完成");

    // 8.3 VIBProtocolFund 设置治理合约
    console.log("\n[配置] VIBProtocolFund 设置治理合约...");
    await wait(2000);
    await vibProtocolFund.setGovernanceContract(deployedContracts.VIBGovernance);
    console.log("   ✅ 治理合约设置完成");

    // 8.4 VIBEToken 设置各合约地址
    console.log("\n[配置] VIBEToken 设置各合约地址...");
    await wait(2000);
    await vibeToken.setStakingContract(deployedContracts.VIBStaking);
    await wait(1000);
    await vibeToken.setVestingContract(deployedContracts.TeamVesting);
    await wait(1000);
    await vibeToken.setIdentityContract(deployedContracts.VIBIdentity);
    await wait(1000);
    await vibeToken.setDividendContract(deployedContracts.VIBDividend);
    await wait(1000);
    await vibeToken.setEcosystemFundContract(deployedContracts.VIBInfrastructurePool);
    await wait(1000);
    await vibeToken.setProtocolFundContract(deployedContracts.VIBProtocolFund);
    await wait(1000);
    await vibeToken.setEmissionController(deployedContracts.EmissionController);
    console.log("   ✅ VIBEToken 合约地址设置完成");

    // 8.5 EmissionController 设置池地址
    console.log("\n[配置] EmissionController 设置池地址...");
    await wait(2000);
    await emissionController.setStakingPool(deployedContracts.VIBStaking);
    await wait(1000);
    await emissionController.setEcosystemPool(deployedContracts.VIBEcosystemPool);
    await wait(1000);
    await emissionController.setGovernancePool(deployedContracts.VIBGovernance);
    await wait(1000);
    await emissionController.setReservePool(deployedContracts.VIBReserve);
    console.log("   ✅ EmissionController 池地址设置完成");

    // 8.6 VIBStaking 设置价格预言机
    console.log("\n[配置] VIBStaking 设置价格预言机...");
    await wait(2000);
    await vibStaking.setPriceOracle(deployedContracts.PriceOracle);
    await wait(1000);
    await vibStaking.setBasePrice(initialPrice);
    console.log("   ✅ 价格预言机设置完成");

    // 8.7 分配代币到各池
    console.log("\n[配置] 分配代币到各池...");
    await wait(2000);
    const distributeTx = await vibeToken.distributeToPools(
      deployedContracts.EarlyVesting,
      deployedContracts.CommunityStableFund,
      deployedContracts.LiquidityManager,
      deployedContracts.AirdropDistributor,
      deployedContracts.EmissionController
    );
    await distributeTx.wait();
    console.log("   ✅ 代币分配完成");

    // 8.8 注册模拟受益人（纯技术测试用）
    console.log("\n[配置] 注册模拟受益人（测试用）...");
    await wait(2000);

    const vestingStart = Math.floor(Date.now() / 1000);

    // 模拟团队成员地址 (使用deployer衍生地址作为测试)
    const mockTeamMembers = [
      "0x1111111111111111111111111111111111111111",
      "0x2222222222222222222222222222222222222222",
      "0x3333333333333333333333333333333333333333"
    ];
    const teamAmounts = [
      hre.ethers.parseUnits("26666666", 18),  // ~2.67% each
      hre.ethers.parseUnits("26666666", 18),
      hre.ethers.parseUnits("26666668", 18)   // 总计 8%
    ];

    // 模拟早期支持者地址
    const mockEarlySupporters = [
      "0x4444444444444444444444444444444444444444",
      "0x5555555555555555555555555555555555555555"
    ];
    const supporterAmounts = [
      hre.ethers.parseUnits("20000000", 18),  // 2%
      hre.ethers.parseUnits("20000000", 18)   // 2%, 总计 4%
    ];

    // 注册团队成员
    await teamVesting.registerTeamMembers(mockTeamMembers, teamAmounts, vestingStart);
    console.log("   ✅ 团队成员注册完成 (3人, 共8%)");

    await wait(2000);

    // 注册早期支持者
    await earlyVesting.registerEarlySupporters(mockEarlySupporters, supporterAmounts, vestingStart);
    console.log("   ✅ 早期支持者注册完成 (2人, 共4%)");

    // ============================================================
    // 验证部署结果
    // ============================================================
    console.log("\n" + "=".repeat(80));
    console.log("  部署验证");
    console.log("=".repeat(80));

    const balances = {
      teamVesting: await vibeToken.balanceOf(deployedContracts.TeamVesting),
      earlyVesting: await vibeToken.balanceOf(deployedContracts.EarlyVesting),
      stableFund: await vibeToken.balanceOf(deployedContracts.CommunityStableFund),
      liquidity: await vibeToken.balanceOf(deployedContracts.LiquidityManager),
      airdrop: await vibeToken.balanceOf(deployedContracts.AirdropDistributor),
      emission: await vibeToken.balanceOf(deployedContracts.EmissionController),
    };

    console.log("\n📊 各池余额:");
    console.log(`  团队锁仓:       ${hre.ethers.formatUnits(balances.teamVesting, 18)} VIBE`);
    console.log(`  早期支持者锁仓: ${hre.ethers.formatUnits(balances.earlyVesting, 18)} VIBE`);
    console.log(`  社区稳定基金:   ${hre.ethers.formatUnits(balances.stableFund, 18)} VIBE`);
    console.log(`  流动性管理:     ${hre.ethers.formatUnits(balances.liquidity, 18)} VIBE`);
    console.log(`  空投分发:       ${hre.ethers.formatUnits(balances.airdrop, 18)} VIBE`);
    console.log(`  释放控制器:     ${hre.ethers.formatUnits(balances.emission, 18)} VIBE`);

    // ============================================================
    // 保存部署结果
    // ============================================================
    const deploymentData = {
      network: hre.network.name,
      chainId: (await hre.ethers.provider.getNetwork()).chainId,
      deployer: deployer.address,
      timestamp: new Date().toISOString(),
      contracts: deployedContracts,
      balances: {
        teamVesting: hre.ethers.formatUnits(balances.teamVesting, 18),
        earlyVesting: hre.ethers.formatUnits(balances.earlyVesting, 18),
        stableFund: hre.ethers.formatUnits(balances.stableFund, 18),
        liquidity: hre.ethers.formatUnits(balances.liquidity, 18),
        airdrop: hre.ethers.formatUnits(balances.airdrop, 18),
        emission: hre.ethers.formatUnits(balances.emission, 18),
      },
      mockBeneficiaries: {
        teamMembers: mockTeamMembers,
        earlySupporters: mockEarlySupporters
      }
    };

    const deploymentFile = path.join(deploymentDir, `deployment-${hre.network.name}-${Date.now()}.json`);
    fs.writeFileSync(deploymentFile, JSON.stringify(deploymentData, null, 2));

    const latestFile = path.join(deploymentDir, `latest-${hre.network.name}.json`);
    fs.writeFileSync(latestFile, JSON.stringify(deploymentData, null, 2));

    console.log("\n" + "=".repeat(80));
    console.log("  ✅ 部署完成！");
    console.log("=".repeat(80));
    console.log("\n📁 部署文件保存至:");
    console.log(`  - ${deploymentFile}`);
    console.log(`  - ${latestFile}`);

    console.log("\n📋 后续步骤:");
    console.log("  1. 将团队 8% 代币转入 TeamVesting 合约");
    console.log("  2. 在 TeamVesting 和 EarlyVesting 中添加受益人");
    console.log("  3. 设置 AirdropDistributor 的 Merkle Root");
    console.log("  4. 初始化 LiquidityManager 的流动性（添加 ETH）");
    console.log("  5. 配置 PriceOracle 的真实数据源");
    console.log("  6. 设置授权评估者（预言机）到各激励合约");
    console.log("  7. 验证所有合约配置正确");
    console.log("  8. 在区块浏览器上验证合约源代码");

    // 输出合约地址汇总
    console.log("\n" + "=".repeat(80));
    console.log("  📜 合约地址汇总");
    console.log("=".repeat(80));
    for (const [name, address] of Object.entries(deployedContracts)) {
      console.log(`  ${name.padEnd(25)}: ${address}`);
    }

  } catch (error) {
    console.error("\n❌ 部署失败:", error);
    console.error(error.stack);
    process.exit(1);
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
