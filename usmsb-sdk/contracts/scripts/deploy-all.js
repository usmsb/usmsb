const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

// Simple delay function
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

async function main() {
  console.log("=".repeat(70));
  console.log("  VIBE Protocol - 完整部署");
  console.log("=".repeat(70));

  const [deployer] = await hre.ethers.getSigners();
  console.log("\nDeployer:", deployer.address);
  console.log("Network:", hre.network.name);

  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("Balance:", hre.ethers.formatEther(balance), "ETH");

  if (balance === 0n) {
    console.log("\n❌ Error: Balance is 0!");
    process.exit(1);
  }

  const deployed = {};
  const deploymentDir = "./deployments";
  if (!fs.existsSync(deploymentDir)) {
    fs.mkdirSync(deploymentDir, { recursive: true });
  }

  // Base Sepolia 配置
  const isBaseSepolia = hre.network.name === "baseSepolia";
  const WETH = isBaseSepolia ? "0x4200000000000000000000000000000000000006" : "";
  const ROUTER = isBaseSepolia ? "0xf253b36702f9a4da019377acfee8658e7136b231" : "";
  // 注意: FACTORY 地址暂时使用 ZeroAddress 占位，需要后续更新
  const FACTORY = isBaseSepolia ? hre.ethers.ZeroAddress : "";

  // 部署 MockWETH 和 MockDEXRouter (本地测试用)
  let mockWETH = null;
  let mockRouter = null;
  let mockFactory = null;
  if (!isBaseSepolia) {
    console.log("\n部署 MockWETH...");
    const MockWETH = await hre.ethers.getContractFactory("MockWETH");
    mockWETH = await MockWETH.deploy();
    await mockWETH.waitForDeployment();
    const wethAddr = await mockWETH.getAddress();
    console.log("   ✅ MockWETH:", wethAddr);
    deployed.MockWETH = wethAddr;

    console.log("\n部署 MockDEXRouter...");
    const MockDEXRouter = await hre.ethers.getContractFactory("MockDEXRouter");
    mockRouter = await MockDEXRouter.deploy(wethAddr);
    await mockRouter.waitForDeployment();
    const routerAddr = await mockRouter.getAddress();
    console.log("   ✅ MockDEXRouter:", routerAddr);
    deployed.MockDEXRouter = routerAddr;

    // 获取 MockDEXRouter 内部的工厂地址
    mockFactory = await mockRouter.factory();
    console.log("   ✅ MockFactory:", mockFactory);
    deployed.MockFactory = mockFactory;

    await delay(2000);
  }

  // 确保地址格式正确 (checksum)
  const wethAddress = isBaseSepolia ? hre.ethers.getAddress(WETH) : deployed.MockWETH;
  const routerAddress = isBaseSepolia ? hre.ethers.getAddress(ROUTER) : deployed.MockDEXRouter;
  const factoryAddress = isBaseSepolia ? hre.ethers.getAddress(FACTORY) : deployed.MockFactory;

  try {
    // ========== 阶段1: 核心代币 ==========
    console.log("\n" + "=".repeat(50));
    console.log(" 阶段1: 核心代币");
    console.log("=".repeat(50));

    // 1. VIBEToken
    console.log("\n[1] VIBEToken...");
    const VIBEToken = await hre.ethers.getContractFactory("VIBEToken");
    const vibeToken = await VIBEToken.deploy("VIBE Token", "VIBE", deployer.address);
    await vibeToken.waitForDeployment();
    deployed.VIBEToken = await vibeToken.getAddress();
    console.log("   =>", deployed.VIBEToken);

    await delay(2000);

    // ========== 阶段2: 质押和锁仓 ==========
    console.log("\n" + "=".repeat(50));
    console.log(" 阶段2: 质押和锁仓");
    console.log("=".repeat(50));

    // 2. VIBStaking
    console.log("\n[2] VIBStaking...");
    const VIBStaking = await hre.ethers.getContractFactory("VIBStaking");
    const staking = await VIBStaking.deploy(deployed.VIBEToken);
    await staking.waitForDeployment();
    deployed.VIBStaking = await staking.getAddress();
    console.log("   =>", deployed.VIBStaking);

    await delay(2000);

    // 3. VIBVesting
    console.log("\n[3] VIBVesting...");
    const VIBVesting = await hre.ethers.getContractFactory("VIBVesting");
    const vesting = await VIBVesting.deploy(deployed.VIBEToken);
    await vesting.waitForDeployment();
    deployed.VIBVesting = await vesting.getAddress();
    console.log("   =>", deployed.VIBVesting);

    await delay(2000);

    // ========== 阶段3: 奖励池 ==========
    console.log("\n" + "=".repeat(50));
    console.log(" 阶段3: 奖励池");
    console.log("=".repeat(50));

    // 4. VIBReserve
    console.log("\n[4] VIBReserve...");
    const VIBReserve = await hre.ethers.getContractFactory("VIBReserve");
    const reserve = await VIBReserve.deploy(deployed.VIBEToken);
    await reserve.waitForDeployment();
    deployed.VIBReserve = await reserve.getAddress();
    console.log("   =>", deployed.VIBReserve);

    await delay(2000);

    // 5. VIBProtocolFund
    console.log("\n[5] VIBProtocolFund...");
    const VIBProtocolFund = await hre.ethers.getContractFactory("VIBProtocolFund");
    const protocolFund = await VIBProtocolFund.deploy(deployed.VIBEToken);
    await protocolFund.waitForDeployment();
    deployed.VIBProtocolFund = await protocolFund.getAddress();
    console.log("   =>", deployed.VIBProtocolFund);

    await delay(2000);

    // 6. VIBInfrastructurePool
    console.log("\n[6] VIBInfrastructurePool...");
    const VIBInfrastructurePool = await hre.ethers.getContractFactory("VIBInfrastructurePool");
    const infraPool = await VIBInfrastructurePool.deploy(deployed.VIBEToken);
    await infraPool.waitForDeployment();
    deployed.VIBInfrastructurePool = await infraPool.getAddress();
    console.log("   =>", deployed.VIBInfrastructurePool);

    await delay(2000);

    // 7. VIBBuilderReward
    console.log("\n[7] VIBBuilderReward...");
    const VIBBuilderReward = await hre.ethers.getContractFactory("VIBBuilderReward");
    const builderReward = await VIBBuilderReward.deploy(deployed.VIBEToken);
    await builderReward.waitForDeployment();
    deployed.VIBBuilderReward = await builderReward.getAddress();
    console.log("   =>", deployed.VIBBuilderReward);

    await delay(2000);

    // 8. VIBDevReward
    console.log("\n[8] VIBDevReward...");
    const VIBDevReward = await hre.ethers.getContractFactory("VIBDevReward");
    const devReward = await VIBDevReward.deploy(deployed.VIBEToken);
    await devReward.waitForDeployment();
    deployed.VIBDevReward = await devReward.getAddress();
    console.log("   =>", deployed.VIBDevReward);

    await delay(2000);

    // ========== 阶段4: 身份 ==========
    console.log("\n" + "=".repeat(50));
    console.log(" 阶段4: 身份");
    console.log("=".repeat(50));

    // 9. VIBIdentity
    console.log("\n[9] VIBIdentity...");
    const VIBIdentity = await hre.ethers.getContractFactory("VIBIdentity");
    const identity = await VIBIdentity.deploy("VIBE Identity", "VIBE-ID", deployed.VIBEToken);
    await identity.waitForDeployment();
    deployed.VIBIdentity = await identity.getAddress();
    console.log("   =>", deployed.VIBIdentity);

    await delay(2000);

    // 10. VIBNodeReward (依赖 VIBIdentity)
    console.log("\n[10] VIBNodeReward...");
    const VIBNodeReward = await hre.ethers.getContractFactory("VIBNodeReward");
    const nodeReward = await VIBNodeReward.deploy(deployed.VIBEToken, deployed.VIBIdentity);
    await nodeReward.waitForDeployment();
    deployed.VIBNodeReward = await nodeReward.getAddress();
    console.log("   =>", deployed.VIBNodeReward);

    await delay(2000);

    // 11. VIBCollaboration (依赖 VIBIdentity)
    console.log("\n[11] VIBCollaboration...");
    const VIBCollaboration = await hre.ethers.getContractFactory("VIBCollaboration");
    const collaboration = await VIBCollaboration.deploy(deployed.VIBEToken, deployed.VIBIdentity);
    await collaboration.waitForDeployment();
    deployed.VIBCollaboration = await collaboration.getAddress();
    console.log("   =>", deployed.VIBCollaboration);

    await delay(2000);

    // ========== 阶段5: 分红 ==========
    console.log("\n" + "=".repeat(50));
    console.log(" 阶段5: 分红");
    console.log("=".repeat(50));

    // 12. VIBDividend
    console.log("\n[12] VIBDividend...");
    const VIBDividend = await hre.ethers.getContractFactory("VIBDividend");
    const dividend = await VIBDividend.deploy(deployed.VIBEToken);
    await dividend.waitForDeployment();
    deployed.VIBDividend = await dividend.getAddress();
    console.log("   =>", deployed.VIBDividend);

    await delay(2000);

    // ========== 阶段6: Agent 系统 ==========
    console.log("\n" + "=".repeat(50));
    console.log(" 阶段6: Agent 系统");
    console.log("=".repeat(50));

    // 13. AgentRegistry
    console.log("\n[13] AgentRegistry...");
    const AgentRegistry = await hre.ethers.getContractFactory("AgentRegistry");
    const agentRegistry = await AgentRegistry.deploy();
    await agentRegistry.waitForDeployment();
    deployed.AgentRegistry = await agentRegistry.getAddress();
    console.log("   =>", deployed.AgentRegistry);

    await delay(2000);

    // 14. ZKCredential
    console.log("\n[14] ZKCredential...");
    const ZKCredential = await hre.ethers.getContractFactory("ZKCredential");
    const zkCredential = await ZKCredential.deploy("ZK Credential", "ZK-CRED", deployer.address, deployer.address);
    await zkCredential.waitForDeployment();
    deployed.ZKCredential = await zkCredential.getAddress();
    console.log("   =>", deployed.ZKCredential);

    await delay(2000);

    // 15. AssetVault
    console.log("\n[15] AssetVault...");
    const AssetVault = await hre.ethers.getContractFactory("AssetVault");
    const assetVault = await AssetVault.deploy(wethAddress, deployer.address, "VIBE Asset", "VIBE-A");
    await assetVault.waitForDeployment();
    deployed.AssetVault = await assetVault.getAddress();
    console.log("   =>", deployed.AssetVault);

    await delay(2000);

    // 16. JointOrder
    console.log("\n[16] JointOrder...");
    const JointOrder = await hre.ethers.getContractFactory("JointOrder");
    const jointOrder = await JointOrder.deploy(deployed.VIBEToken, deployer.address, deployer.address);
    await jointOrder.waitForDeployment();
    deployed.JointOrder = await jointOrder.getAddress();
    console.log("   =>", deployed.JointOrder);

    await delay(2000);

    // ========== 阶段7: 预言机和自动化 ==========
    console.log("\n" + "=".repeat(50));
    console.log(" 阶段7: 预言机和自动化");
    console.log("=".repeat(50));

    // 17. PriceOracle
    console.log("\n[17] PriceOracle...");
    const PriceOracle = await hre.ethers.getContractFactory("PriceOracle");
    const priceOracle = await PriceOracle.deploy(hre.ethers.ZeroAddress, hre.ethers.ZeroAddress, hre.ethers.ZeroAddress);
    await priceOracle.waitForDeployment();
    deployed.PriceOracle = await priceOracle.getAddress();
    console.log("   =>", deployed.PriceOracle);

    await delay(2000);

    // 18. VIBOutputReward (临时地址，后续更新)
    console.log("\n[18] VIBOutputReward...");
    const VIBOutputReward = await hre.ethers.getContractFactory("VIBOutputReward");
    const outputReward = await VIBOutputReward.deploy(deployed.VIBEToken, deployer.address);
    await outputReward.waitForDeployment();
    deployed.VIBOutputReward = await outputReward.getAddress();
    console.log("   =>", deployed.VIBOutputReward);

    await delay(2000);

    // 19. VIBEcosystemPool (临时地址，后续更新)
    console.log("\n[19] VIBEcosystemPool...");
    const VIBEcosystemPool = await hre.ethers.getContractFactory("VIBEcosystemPool");
    const ecosystemPool = await VIBEcosystemPool.deploy(deployed.VIBEToken, deployer.address);
    await ecosystemPool.waitForDeployment();
    deployed.VIBEcosystemPool = await ecosystemPool.getAddress();
    console.log("   =>", deployed.VIBEcosystemPool);

    await delay(2000);

    // 20. AirdropDistributor
    console.log("\n[20] AirdropDistributor...");
    const AirdropDistributor = await hre.ethers.getContractFactory("AirdropDistributor");
    const airdrop = await AirdropDistributor.deploy(deployed.VIBEToken, deployer.address, hre.ethers.ZeroHash);
    await airdrop.waitForDeployment();
    deployed.AirdropDistributor = await airdrop.getAddress();
    console.log("   =>", deployed.AirdropDistributor);

    await delay(2000);

    // 21. CommunityStableFund
    console.log("\n[21] CommunityStableFund...");
    const CommunityStableFund = await hre.ethers.getContractFactory("CommunityStableFund");
    const communityFund = await CommunityStableFund.deploy(deployed.VIBEToken, wethAddress, deployed.PriceOracle, routerAddress, hre.ethers.parseEther("10000"));
    await communityFund.waitForDeployment();
    deployed.CommunityStableFund = await communityFund.getAddress();
    console.log("   =>", deployed.CommunityStableFund);

    await delay(2000);

    // 22. LiquidityManager (如果 factory 无效则跳过)
    console.log("\n[22] LiquidityManager...");
    if (factoryAddress !== hre.ethers.ZeroAddress) {
      try {
        const LiquidityManager = await hre.ethers.getContractFactory("LiquidityManager");
        const liquidityManager = await LiquidityManager.deploy(deployed.VIBEToken, wethAddress, routerAddress, factoryAddress);
        await liquidityManager.waitForDeployment();
        deployed.LiquidityManager = await liquidityManager.getAddress();
        console.log("   =>", deployed.LiquidityManager);
      } catch (e) {
        console.log("   ⚠️ 跳过 (需要有效的 factory 地址):", e.message.substring(0, 50));
        deployed.LiquidityManager = "";
      }
    } else {
      console.log("   ⚠️ 跳过 (factory 地址为 0)");
      deployed.LiquidityManager = "";
    }

    await delay(2000);

    // ========== 阶段8: 治理 (关键依赖) ==========
    console.log("\n" + "=".repeat(50));
    console.log(" 阶段8: 治理");
    console.log("=".repeat(50));

    // 23. VIBGovernance
    console.log("\n[23] VIBGovernance...");
    const VIBGovernance = await hre.ethers.getContractFactory("VIBGovernance");
    const governance = await VIBGovernance.deploy();
    await governance.waitForDeployment();
    deployed.VIBGovernance = await governance.getAddress();
    console.log("   =>", deployed.VIBGovernance);

    // 初始化
    console.log("   初始化...");
    const initGovTx = await governance.initialize(deployed.VIBEToken);
    await initGovTx.wait();
    console.log("   ✅");

    await delay(2000);

    // 24. VIBGovernanceDelegation
    console.log("\n[24] VIBGovernanceDelegation...");
    const VIBGovernanceDelegation = await hre.ethers.getContractFactory("VIBGovernanceDelegation");
    const delegation = await VIBGovernanceDelegation.deploy();
    await delegation.waitForDeployment();
    deployed.VIBGovernanceDelegation = await delegation.getAddress();
    console.log("   =>", deployed.VIBGovernanceDelegation);

    // 初始化
    console.log("   初始化...");
    const initDelTx = await delegation.initialize();
    await initDelTx.wait();
    console.log("   ✅");

    await delay(2000);

    // 25. VIBContributionPoints
    console.log("\n[25] VIBContributionPoints...");
    const VIBContributionPoints = await hre.ethers.getContractFactory("VIBContributionPoints");
    const contributionPoints = await VIBContributionPoints.deploy();
    await contributionPoints.waitForDeployment();
    deployed.VIBContributionPoints = await contributionPoints.getAddress();
    console.log("   =>", deployed.VIBContributionPoints);

    // 初始化
    console.log("   初始化...");
    const initPointsTx = await contributionPoints.initialize();
    await initPointsTx.wait();
    const initTypesTx = await contributionPoints.initializeContributionTypes();
    await initTypesTx.wait();
    console.log("   ✅");

    await delay(2000);

    // 26. VIBVEPoints (依赖 VIBStaking, VIBOutputReward, VIBGovernance)
    console.log("\n[26] VIBVEPoints...");
    const VIBVEPoints = await hre.ethers.getContractFactory("VIBVEPoints");
    const vePoints = await VIBVEPoints.deploy(deployed.VIBStaking, deployed.VIBOutputReward, deployed.VIBGovernance);
    await vePoints.waitForDeployment();
    deployed.VIBVEPoints = await vePoints.getAddress();
    console.log("   =>", deployed.VIBVEPoints);

    await delay(2000);

    // ========== 阶段9: 需要治理的合约 ==========
    console.log("\n" + "=".repeat(50));
    console.log(" 阶段9: 需要治理的合约");
    console.log("=".repeat(50));

    // 27. VIBDispute (依赖 VIBGovernance)
    console.log("\n[27] VIBDispute...");
    const VIBDispute = await hre.ethers.getContractFactory("VIBDispute");
    const dispute = await VIBDispute.deploy(
      deployed.VIBEToken,
      deployed.VIBStaking,
      deployed.VIBGovernance,
      hre.ethers.ZeroAddress,
      hre.ethers.ZeroAddress,
      "0x0000000000000000000000000000000000000000000000000000000000000000"
    );
    await dispute.waitForDeployment();
    deployed.VIBDispute = await dispute.getAddress();
    console.log("   =>", deployed.VIBDispute);

    await delay(2000);

    // 28. AgentWallet (依赖 AgentRegistry, VIBStaking)
    console.log("\n[28] AgentWallet...");
    const AgentWallet = await hre.ethers.getContractFactory("AgentWallet");
    const agentWallet = await AgentWallet.deploy(deployer.address, deployer.address, deployed.VIBEToken, deployed.AgentRegistry, deployed.VIBStaking);
    await agentWallet.waitForDeployment();
    deployed.AgentWallet = await agentWallet.getAddress();
    console.log("   =>", deployed.AgentWallet);

    await delay(2000);

    // 29. EmissionController (依赖 VIBReserve)
    console.log("\n[29] EmissionController...");
    const EmissionController = await hre.ethers.getContractFactory("EmissionController");
    const emissionController = await EmissionController.deploy(
      deployed.VIBEToken,
      deployed.VIBStaking,
      deployed.VIBEcosystemPool,
      deployed.VIBGovernance,
      deployed.VIBReserve
    );
    await emissionController.waitForDeployment();
    deployed.EmissionController = await emissionController.getAddress();
    console.log("   =>", deployed.EmissionController);

    await delay(2000);

    // ========== 连接治理合约 ==========
    console.log("\n" + "=".repeat(50));
    console.log(" 连接治理合约");
    console.log("=".repeat(50));

    // 设置 Delegation 的治理合约
    console.log("\n设置 Delegation -> Governance...");
    await (await delegation.setGovernanceContract(deployed.VIBGovernance)).wait();
    console.log("   ✅");

    await delay(2000);

    // 设置 ContributionPoints 的治理合约
    console.log("设置 ContributionPoints -> Governance...");
    await (await contributionPoints.setGovernanceContract(deployed.VIBGovernance)).wait();
    console.log("   ✅");

    await delay(2000);

    // 设置 Governance 的委托合约
    console.log("设置 Governance -> Delegation...");
    await (await governance.setDelegationContract(deployed.VIBGovernanceDelegation)).wait();
    console.log("   ✅");

    await delay(2000);

    // 设置 Governance 的贡献积分合约
    console.log("设置 Governance -> ContributionPoints...");
    await (await governance.setContributionPointsContract(deployed.VIBContributionPoints)).wait();
    console.log("   ✅");

    await delay(2000);

    // ========== 验证 ==========
    console.log("\n验证配置...");
    const ok1 = await governance.delegationContract() === deployed.VIBGovernanceDelegation;
    const ok2 = await governance.contributionPointsContract() === deployed.VIBContributionPoints;
    const ok3 = await delegation.governanceContract() === deployed.VIBGovernance;
    const ok4 = await contributionPoints.governanceContract() === deployed.VIBGovernance;

    console.log("   Governance -> Delegation:", ok1 ? "✅" : "❌");
    console.log("   Governance -> Points:", ok2 ? "✅" : "❌");
    console.log("   Delegation -> Governance:", ok3 ? "✅" : "❌");
    console.log("   Points -> Governance:", ok4 ? "✅" : "❌");

    // ========== 保存 ==========
    const data = {
      network: hre.network.name,
      deployer: deployer.address,
      timestamp: new Date().toISOString(),
      contracts: deployed
    };

    const file = path.join(deploymentDir, `deployment-${Date.now()}.json`);
    fs.writeFileSync(file, JSON.stringify(data, null, 2));
    fs.writeFileSync(path.join(deploymentDir, "latest.json"), JSON.stringify(data, null, 2));

    console.log("\n" + "=".repeat(70));
    console.log("  ✅ 部署完成! (29个合约)");
    console.log("=".repeat(70));
    console.log("\n保存至:", file);

  } catch (err) {
    console.error("\n❌ 部署失败:", err.message);
    process.exit(1);
  }
}

main().then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });
