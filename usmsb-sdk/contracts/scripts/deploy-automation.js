const hre = require("hardhat");
const fs = require("fs");

async function main() {
  console.log("=".repeat(60));
  console.log("VIBE Protocol - Automation Contracts Deployment");
  console.log("=".repeat(60));

  const [deployer] = await hre.ethers.getSigners();
  console.log("Deployer:", deployer.address);

  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("Balance:", hre.ethers.formatEther(balance), "ETH");
  console.log("-".repeat(60));

  if (balance === 0n) {
    console.log("\n❌ Error: Balance is 0! You need testnet ETH to deploy.");
    process.exit(1);
  }

  // 读取已部署的核心合约地址
  let coreContracts = {};
  const deploymentFile = "./deployments/latest.json";

  if (fs.existsSync(deploymentFile)) {
    coreContracts = JSON.parse(fs.readFileSync(deploymentFile, "utf8"));
    console.log("\n📦 Loaded core contracts from:", deploymentFile);
  } else {
    console.log("\n⚠️  No existing deployment found. Please deploy core contracts first.");
    console.log("Run: npx hardhat run scripts/deploy.js --network <network>");
    process.exit(1);
  }

  const deployedContracts = { ...coreContracts };

  // Base Sepolia addresses (使用 ethers.getAddress 确保正确校验和)
  const BASE_SEPOLIA_WETH = hre.ethers.getAddress("0x4200000000000000000000000000000000000006");
  const BASE_SEPOLIA_ROUTER = hre.ethers.getAddress("0xf253b36702f9a4da019377acfee8658e7136b231");

  // 根据网络选择地址
  const isBaseSepolia = hre.network.name === "baseSepolia";
  const wethAddress = isBaseSepolia ? BASE_SEPOLIA_WETH : hre.ethers.ZeroAddress;
  const routerAddress = isBaseSepolia ? BASE_SEPOLIA_ROUTER : hre.ethers.ZeroAddress;

  console.log("Network:", hre.network.name);
  console.log("WETH:", wethAddress);
  console.log("Router:", routerAddress);

  // ========== 1. PriceOracle ==========
  console.log("\n[1/5] Deploying PriceOracle...");
  const PriceOracle = await hre.ethers.getContractFactory("PriceOracle");
  const priceOracle = await PriceOracle.deploy(
    hre.ethers.ZeroAddress, // Chainlink feed (to be set later)
    hre.ethers.ZeroAddress, // Uniswap V3 pool (to be set later)
    hre.ethers.ZeroAddress  // SushiSwap pool (to be set later)
  );
  await priceOracle.waitForDeployment();
  deployedContracts.PriceOracle = await priceOracle.getAddress();
  console.log("   PriceOracle:", deployedContracts.PriceOracle);

  // ========== 2. EmissionController ==========
  console.log("\n[2/5] Deploying EmissionController...");
  const EmissionController = await hre.ethers.getContractFactory("EmissionController");
  const emissionController = await EmissionController.deploy(
    deployedContracts.VIBEToken,
    deployedContracts.VIBStaking,
    deployer.address, // Ecosystem pool (temporary)
    deployedContracts.VIBGovernance,
    deployer.address  // Reserve pool (temporary)
  );
  await emissionController.waitForDeployment();
  deployedContracts.EmissionController = await emissionController.getAddress();
  console.log("   EmissionController:", deployedContracts.EmissionController);

  // ========== 3. CommunityStableFund ==========
  console.log("\n[3/5] Deploying CommunityStableFund...");
  const CommunityStableFund = await hre.ethers.getContractFactory("CommunityStableFund");
  const communityStableFund = await CommunityStableFund.deploy(
    deployedContracts.VIBEToken,
    wethAddress, // WETH
    deployedContracts.PriceOracle,
    routerAddress, // DEX Router
    hre.ethers.parseEther("100") // Min liquidity threshold
  );
  await communityStableFund.waitForDeployment();
  deployedContracts.CommunityStableFund = await communityStableFund.getAddress();
  console.log("   CommunityStableFund:", deployedContracts.CommunityStableFund);

  // ========== 4. AirdropDistributor ==========
  console.log("\n[4/5] Deploying AirdropDistributor...");
  // 生成一个占位 Merkle Root (实际部署时需要替换)
  const placeholderMerkleRoot = "0x0000000000000000000000000000000000000000000000000000000000000001";

  const AirdropDistributor = await hre.ethers.getContractFactory("AirdropDistributor");
  const airdropDistributor = await AirdropDistributor.deploy(
    deployedContracts.VIBEToken,
    deployedContracts.CommunityStableFund,
    placeholderMerkleRoot
  );
  await airdropDistributor.waitForDeployment();
  deployedContracts.AirdropDistributor = await airdropDistributor.getAddress();
  console.log("   AirdropDistributor:", deployedContracts.AirdropDistributor);

  // ========== 5. LiquidityManager ==========
  console.log("\n[5/5] Deploying LiquidityManager...");
  const LiquidityManager = await hre.ethers.getContractFactory("LiquidityManager");
  const liquidityManager = await LiquidityManager.deploy(
    deployedContracts.VIBEToken,
    wethAddress, // WETH
    routerAddress, // DEX Router
    routerAddress  // DEX Factory (using same for simplicity, will need factory)
  );
  await liquidityManager.waitForDeployment();
  deployedContracts.LiquidityManager = await liquidityManager.getAddress();
  console.log("   LiquidityManager:", deployedContracts.LiquidityManager);

  console.log("\n" + "=".repeat(60));
  console.log("Setting up contract relationships...");
  console.log("=".repeat(60));

  // 获取合约实例
  const vibeToken = await hre.ethers.getContractAt("VIBEToken", deployedContracts.VIBEToken);
  const vibStaking = await hre.ethers.getContractAt("VIBStaking", deployedContracts.VIBStaking);
  const vibGovernance = await hre.ethers.getContractAt("VIBGovernance", deployedContracts.VIBGovernance);

  // 尝试设置 EmissionController 地址（可能失败因为旧版合约）
  try {
    console.log("\n-> Setting EmissionController on VIBEToken...");
    let tx = await vibeToken.setEmissionController(deployedContracts.EmissionController);
    await tx.wait();
    console.log("   ✅ VIBEToken updated");
  } catch (e) {
    console.log("   ⚠️  VIBEToken update skipped (function may not exist in deployed version)");
  }

  try {
    console.log("-> Setting EmissionController on VIBStaking...");
    let tx = await vibStaking.setEmissionController(deployedContracts.EmissionController);
    await tx.wait();
    console.log("   ✅ VIBStaking updated");
  } catch (e) {
    console.log("   ⚠️  VIBStaking update skipped");
  }

  try {
    console.log("-> Setting EmissionController on VIBGovernance...");
    let tx = await vibGovernance.setEmissionController(deployedContracts.EmissionController);
    await tx.wait();
    console.log("   ✅ VIBGovernance updated");
  } catch (e) {
    console.log("   ⚠️  VIBGovernance update skipped");
  }

  // 保存部署信息
  const deploymentInfo = {
    network: hre.network.name,
    deployer: deployer.address,
    timestamp: new Date().toISOString(),
    contracts: deployedContracts,
    tokenDistribution: {
      team: "80,000,000 VIBE (8%)",
      earlySupporters: "40,000,000 VIBE (4%)",
      communityStableFund: "60,000,000 VIBE (6%)",
      liquidityPool: "120,000,000 VIBE (12%)",
      airdrop: "70,000,000 VIBE (7%)",
      emissionPool: "630,000,000 VIBE (63%)"
    },
    setup: {
      priceOracle: "Needs Chainlink, Uniswap, Sushi addresses",
      communityStableFund: "Needs WETH, DEX Router addresses",
      liquidityManager: "Needs WETH, DEX Router, Factory addresses",
      airdropMerkleRoot: "Needs actual merkle root"
    }
  };

  const outputFile = "./deployments/automation-" + Date.now() + ".json";
  fs.writeFileSync(outputFile, JSON.stringify(deploymentInfo, null, 2));
  console.log("\n📄 Deployment info saved to:", outputFile);

  // 同时更新 latest.json
  fs.writeFileSync(deploymentFile, JSON.stringify(deployedContracts, null, 2));
  console.log("📄 Updated:", deploymentFile);

  console.log("\n" + "=".repeat(60));
  console.log("✅ Automation Contracts Deployed Successfully!");
  console.log("=".repeat(60));

  console.log("\n📋 Deployed Contracts:");
  console.log("   PriceOracle:          ", deployedContracts.PriceOracle);
  console.log("   EmissionController:   ", deployedContracts.EmissionController);
  console.log("   CommunityStableFund:  ", deployedContracts.CommunityStableFund);
  console.log("   AirdropDistributor:   ", deployedContracts.AirdropDistributor);
  console.log("   LiquidityManager:     ", deployedContracts.LiquidityManager);

  console.log("\n⚠️  Next Steps:");
  console.log("   1. Fund EmissionController with 630M VIBE");
  console.log("   2. Fund CommunityStableFund with 60M VIBE + ETH");
  console.log("   3. Fund LiquidityManager with 120M VIBE + ETH");
  console.log("   4. Fund AirdropDistributor with 70M VIBE");
  console.log("   5. Set up PriceOracle with real price feeds");
  console.log("   6. Set DEX addresses for CommunityStableFund & LiquidityManager");
  console.log("   7. Set actual Merkle root for AirdropDistributor");
  console.log("   8. Start Airdrop when ready");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
