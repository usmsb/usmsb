const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

/**
 * VIBE Protocol 完整部署脚本
 *
 * 部署顺序（按依赖关系）:
 * 1. VIBEToken - 8% 给部署者（团队），92% 待分配
 * 2. VIBVesting（团队锁仓 #1）- 接收团队 8%
 * 3. VIBVesting（早期支持者锁仓 #2）- 接收早期支持者 4%
 * 4. PriceOracle - 价格预言机
 * 5. CommunityStableFund - 社区稳定基金 6%
 * 6. LiquidityManager - 流动性管理 12%
 * 7. AirdropDistributor - 空投分发 7%
 * 8. EmissionController - 激励池 63%
 * 9. VIBEToken.distributeToPools() - 自动分配代币
 * 10. 其他核心合约（VIBStaking, VIBGovernance 等）
 */

async function main() {
  console.log("=".repeat(70));
  console.log("  VIBE Protocol - 完整部署脚本（完全去中心化）");
  console.log("  基于 VIBE_Full_Automation_Design.md (2026-02-24)");
  console.log("=".repeat(70));

  const [deployer] = await hre.ethers.getSigners();
  console.log("\nDeployer:", deployer.address);

  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("Balance:", hre.ethers.formatEther(balance), "ETH");
  console.log("Network:", hre.network.name);

  if (balance === 0n) {
    console.log("\n❌ Error: Balance is 0! You need ETH to deploy.");
    process.exit(1);
  }

  const deployedContracts = {};
  const deploymentDir = "./deployments";

  // 创建部署目录
  if (!fs.existsSync(deploymentDir)) {
    fs.mkdirSync(deploymentDir, { recursive: true });
  }

  // Base Sepolia 地址
  const BASE_SEPOLIA_WETH = "0x4200000000000000000000000000000000000006";
  const BASE_SEPOLIA_ROUTER = "0xf253b36702f9a4da019377acfee8658e7136b231";

  const isBaseSepolia = hre.network.name === "baseSepolia";
  const wethAddress = isBaseSepolia ? BASE_SEPOLIA_WETH : hre.ethers.ZeroAddress;
  const routerAddress = isBaseSepolia ? BASE_SEPOLIA_ROUTER : hre.ethers.ZeroAddress;

  // ========== 代币分配常量 ==========
  const TOTAL_SUPPLY = hre.ethers.parseUnits("1000000000", 18); // 10亿
  const TEAM_RATIO = 8n;        // 团队 8%
  const EARLY_SUPPORTER_RATIO = 4n;  // 早期支持者 4%
  const STABLE_FUND_RATIO = 6n;      // 社区稳定基金 6%
  const LIQUIDITY_RATIO = 12n;       // 流动性池 12%
  const AIRDROP_RATIO = 7n;          // 空投 7%
  const EMISSION_RATIO = 63n;        // 激励池 63%

  console.log("\n" + "=".repeat(70));
  console.log("  代币分配方案");
  console.log("=".repeat(70));
  console.log(`  团队 (8%):        ${hre.ethers.formatUnits(TOTAL_SUPPLY * TEAM_RATIO / 100n, 18)} VIBE`);
  console.log(`  早期支持者 (4%):  ${hre.ethers.formatUnits(TOTAL_SUPPLY * EARLY_SUPPORTER_RATIO / 100n, 18)} VIBE`);
  console.log(`  社区稳定基金 (6%): ${hre.ethers.formatUnits(TOTAL_SUPPLY * STABLE_FUND_RATIO / 100n, 18)} VIBE`);
  console.log(`  流动性池 (12%):   ${hre.ethers.formatUnits(TOTAL_SUPPLY * LIQUIDITY_RATIO / 100n, 18)} VIBE`);
  console.log(`  空投 (7%):        ${hre.ethers.formatUnits(TOTAL_SUPPLY * AIRDROP_RATIO / 100n, 18)} VIBE`);
  console.log(`  激励池 (63%):     ${hre.ethers.formatUnits(TOTAL_SUPPLY * EMISSION_RATIO / 100n, 18)} VIBE`);
  console.log("=".repeat(70));

  try {
    // ========== Step 1: VIBEToken ==========
    console.log("\n[1/9] 部署 VIBEToken...");
    const VIBEToken = await hre.ethers.getContractFactory("VIBEToken");
    // treasury 暂时设为 deployer，后续不会被使用（因为会用 distributeToPools）
    const vibeToken = await VIBEToken.deploy(
      "VIBE Token",
      "VIBE",
      deployer.address // temporary treasury
    );
    await vibeToken.waitForDeployment();
    deployedContracts.VIBEToken = await vibeToken.getAddress();
    console.log("   ✅ VIBEToken:", deployedContracts.VIBEToken);
    console.log("   团队 8% 已铸造给部署者:", deployer.address);

    // ========== Step 2: 团队锁仓合约 (VIBVesting #1) ==========
    console.log("\n[2/9] 部署团队锁仓合约 (VIBVesting #1)...");
    const VIBVestingTeam = await hre.ethers.getContractFactory("VIBVesting");
    // 4年锁仓，线性释放
    const teamVesting = await VIBVestingTeam.deploy(
      deployedContracts.VIBEToken,
      4 * 365 * 24 * 60 * 60, // 4年（秒）
      deployer.address, // 暂时设置部署者为受益人，后续可通过治理添加实际团队成员
      "Team Vesting"
    );
    await teamVesting.waitForDeployment();
    deployedContracts.TeamVesting = await teamVesting.getAddress();
    console.log("   ✅ TeamVesting (4年):", deployedContracts.TeamVesting);

    // ========== Step 3: 早期支持者锁仓合约 (VIBVesting #2) ==========
    console.log("\n[3/9] 部署早期支持者锁仓合约 (VIBVesting #2)...");
    const VIBVestingEarly = await hre.ethers.getContractFactory("VIBVesting");
    // 2年锁仓，线性释放
    const earlyVesting = await VIBVestingEarly.deploy(
      deployedContracts.VIBEToken,
      2 * 365 * 24 * 60 * 60, // 2年（秒）
      deployer.address, // 暂时设置部署者为受益人，后续添加实际早期支持者
      "Early Supporters Vesting"
    );
    await earlyVesting.waitForDeployment();
    deployedContracts.EarlyVesting = await earlyVesting.getAddress();
    console.log("   ✅ EarlyVesting (2年):", deployedContracts.EarlyVesting);

    // ========== Step 4: PriceOracle ==========
    console.log("\n[4/9] 部署 PriceOracle...");
    const PriceOracle = await hre.ethers.getContractFactory("PriceOracle");
    const priceOracle = await PriceOracle.deploy(
      hre.ethers.ZeroAddress, // Chainlink feed (to be set)
      hre.ethers.ZeroAddress, // Uniswap V3 pool (to be set)
      hre.ethers.ZeroAddress  // SushiSwap pool (to be set)
    );
    await priceOracle.waitForDeployment();
    deployedContracts.PriceOracle = await priceOracle.getAddress();
    console.log("   ✅ PriceOracle:", deployedContracts.PriceOracle);

    // ========== Step 4.1: 初始化 TWAP 基线 ==========
    console.log("\n   初始化 TWAP 基线...");
    // 设置初始价格作为 TWAP 基线（假设初始价格为 $0.01，即 1e16 wei）
    const initialPrice = hre.ethers.parseUnits("0.01", 18); // $0.01
    const tx = await priceOracle.setLastValidPrice(initialPrice);
    await tx.wait();
    console.log("   ✅ 设置初始价格基线: $0.01");

    // 初始化 SushiSwap TWAP 观察记录（需要多次调用建立历史）
    try {
      for (let i = 0; i < 3; i++) {
        const twapTx = await priceOracle.updateSushiTWAP();
        await twapTx.wait();
        console.log(`   ✅ TWAP 观察记录 #${i + 1} 已建立`);
        // 等待一小段时间模拟时间流逝（实际部署时需要等待真实时间间隔）
        if (i < 2) {
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      }
    } catch (twapError) {
      console.log("   ⚠️ TWAP 初始化跳过（无 SushiSwap 池）:", twapError.message);
    }

    // ========== Step 5: CommunityStableFund ==========
    console.log("\n[5/9] 部署 CommunityStableFund...");
    const CommunityStableFund = await hre.ethers.getContractFactory("CommunityStableFund");
    const communityStableFund = await CommunityStableFund.deploy(
      deployedContracts.VIBEToken,
      wethAddress,
      deployedContracts.PriceOracle,
      routerAddress
    );
    await communityStableFund.waitForDeployment();
    deployedContracts.CommunityStableFund = await communityStableFund.getAddress();
    console.log("   ✅ CommunityStableFund:", deployedContracts.CommunityStableFund);

    // ========== Step 6: LiquidityManager ==========
    console.log("\n[6/9] 部署 LiquidityManager...");
    const LiquidityManager = await hre.ethers.getContractFactory("LiquidityManager");
    const liquidityManager = await LiquidityManager.deploy(
      deployedContracts.VIBEToken,
      wethAddress,
      routerAddress
    );
    await liquidityManager.waitForDeployment();
    deployedContracts.LiquidityManager = await liquidityManager.getAddress();
    console.log("   ✅ LiquidityManager:", deployedContracts.LiquidityManager);

    // ========== Step 7: AirdropDistributor ==========
    console.log("\n[7/9] 部署 AirdropDistributor...");
    // Merkle root 初始化为零，后续设置
    const emptyMerkleRoot = hre.ethers.ZeroHash;
    const AirdropDistributor = await hre.ethers.getContractFactory("AirdropDistributor");
    const airdropDistributor = await AirdropDistributor.deploy(
      deployedContracts.VIBEToken,
      emptyMerkleRoot,
      deployedContracts.CommunityStableFund // 未领取的代币转给稳定基金
    );
    await airdropDistributor.waitForDeployment();
    deployedContracts.AirdropDistributor = await airdropDistributor.getAddress();
    console.log("   ✅ AirdropDistributor:", deployedContracts.AirdropDistributor);

    // ========== Step 8: EmissionController ==========
    console.log("\n[8/9] 部署 EmissionController...");
    const EmissionController = await hre.ethers.getContractFactory("EmissionController");
    const emissionController = await EmissionController.deploy(
      deployedContracts.VIBEToken,
      deployer.address, // VIBStaking (临时，后续设置)
      deployer.address, // Ecosystem pool (临时)
      deployer.address, // VIBGovernance (临时)
      deployer.address  // Reserve pool (临时)
    );
    await emissionController.waitForDeployment();
    deployedContracts.EmissionController = await emissionController.getAddress();
    console.log("   ✅ EmissionController:", deployedContracts.EmissionController);

    // ========== Step 9: 分配代币到各池（核心步骤）==========
    console.log("\n[9/9] 🔑 分配代币到各池（完全去中心化）...");
    console.log("   调用 VIBEToken.distributeToPools()...");

    const distributeTx = await vibeToken.distributeToPools(
      deployedContracts.EarlyVesting,      // 早期支持者 4%
      deployedContracts.CommunityStableFund, // 社区稳定基金 6%
      deployedContracts.LiquidityManager,  // 流动性池 12%
      deployedContracts.AirdropDistributor, // 空投 7%
      deployedContracts.EmissionController  // 激励池 63%
    );
    await distributeTx.wait();

    console.log("   ✅ 代币分配完成！");
    console.log("\n   各池余额确认:");

    const earlyVestingBalance = await vibeToken.balanceOf(deployedContracts.EarlyVesting);
    const stableFundBalance = await vibeToken.balanceOf(deployedContracts.CommunityStableFund);
    const liquidityBalance = await vibeToken.balanceOf(deployedContracts.LiquidityManager);
    const airdropBalance = await vibeToken.balanceOf(deployedContracts.AirdropDistributor);
    const emissionBalance = await vibeToken.balanceOf(deployedContracts.EmissionController);

    console.log(`   - 早期支持者锁仓: ${hre.ethers.formatUnits(earlyVestingBalance, 18)} VIBE`);
    console.log(`   - 社区稳定基金:   ${hre.ethers.formatUnits(stableFundBalance, 18)} VIBE`);
    console.log(`   - 流动性管理:     ${hre.ethers.formatUnits(liquidityBalance, 18)} VIBE`);
    console.log(`   - 空投分发:       ${hre.ethers.formatUnits(airdropBalance, 18)} VIBE`);
    console.log(`   - 释放控制器:     ${hre.ethers.formatUnits(emissionBalance, 18)} VIBE`);

    // ========== 保存部署结果 ==========
    const deploymentData = {
      network: hre.network.name,
      deployer: deployer.address,
      timestamp: new Date().toISOString(),
      contracts: deployedContracts,
      distribution: {
        team: {
          percentage: "8%",
          holder: deployer.address,
          note: "已铸造给部署者，需转入 TeamVesting 合约"
        },
        earlySupporters: {
          percentage: "4%",
          contract: deployedContracts.EarlyVesting,
          balance: hre.ethers.formatUnits(earlyVestingBalance, 18)
        },
        stableFund: {
          percentage: "6%",
          contract: deployedContracts.CommunityStableFund,
          balance: hre.ethers.formatUnits(stableFundBalance, 18)
        },
        liquidity: {
          percentage: "12%",
          contract: deployedContracts.LiquidityManager,
          balance: hre.ethers.formatUnits(liquidityBalance, 18)
        },
        airdrop: {
          percentage: "7%",
          contract: deployedContracts.AirdropDistributor,
          balance: hre.ethers.formatUnits(airdropBalance, 18)
        },
        emission: {
          percentage: "63%",
          contract: deployedContracts.EmissionController,
          balance: hre.ethers.formatUnits(emissionBalance, 18),
          subPools: {
            staking: "45%",
            ecosystem: "30%",
            governance: "15%",
            reserve: "10%"
          }
        }
      }
    };

    const deploymentFile = path.join(deploymentDir, `deployment-${hre.network.name}-${Date.now()}.json`);
    fs.writeFileSync(deploymentFile, JSON.stringify(deploymentData, null, 2));

    // 同时保存一份 latest.json
    const latestFile = path.join(deploymentDir, "latest.json");
    fs.writeFileSync(latestFile, JSON.stringify(deploymentData, null, 2));

    console.log("\n" + "=".repeat(70));
    console.log("  ✅ 部署完成！");
    console.log("=".repeat(70));
    console.log("\n部署文件保存至:");
    console.log(`  - ${deploymentFile}`);
    console.log(`  - ${latestFile}`);

    console.log("\n📋 后续步骤:");
    console.log("  1. 将团队 8% 代币转入 TeamVesting 合约");
    console.log("  2. 在 TeamVesting 和 EarlyVesting 中添加受益人");
    console.log("  3. 设置 AirdropDistributor 的 Merkle Root");
    console.log("  4. 部署 VIBStaking 并设置到 EmissionController");
    console.log("  5. 部署 VIBGovernance 并设置到 EmissionController");
    console.log("  6. 初始化 LiquidityManager 的流动性");
    console.log("  7. 配置 PriceOracle 的数据源");

  } catch (error) {
    console.error("\n❌ 部署失败:", error);
    process.exit(1);
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
