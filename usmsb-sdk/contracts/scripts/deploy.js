const hre = require("hardhat");
const fs = require("fs");

async function main() {
  console.log("=".repeat(60));
  console.log("VIBE Protocol - Smart Contracts Deployment");
  console.log("=".repeat(60));

  const [deployer] = await hre.ethers.getSigners();
  console.log("Deployer:", deployer.address);

  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("Balance:", hre.ethers.formatEther(balance), "ETH");
  console.log("-".repeat(60));

  if (balance === 0n) {
    console.log("\n❌ Error: Balance is 0! You need testnet ETH to deploy.");
    console.log("\nGet Base Sepolia ETH from:");
    console.log("  - https://faucet.coinbase.com");
    console.log("  - https://www.alchemy.com/faucets/base-sepolia");
    console.log("  - https://faucet.quicknode.com/base/sepolia");
    process.exit(1);
  }

  const deployedContracts = {};

  // ========== 1. VIBEToken ==========
  console.log("\n[1/14] Deploying VIBEToken...");
  const VIBEToken = await hre.ethers.getContractFactory("VIBEToken");
  const vibeToken = await VIBEToken.deploy(
    "VIBE Token",
    "VIBE",
    deployer.address // treasury (temporary)
  );
  await vibeToken.waitForDeployment();
  deployedContracts.VIBEToken = await vibeToken.getAddress();
  console.log("   VIBEToken:", deployedContracts.VIBEToken);

  // ========== 2. VIBInflationControl ==========
  console.log("\n[2/14] Deploying VIBInflationControl...");
  // Use the constant TOTAL_SUPPLY from VIBEToken (1 billion * 10^18)
  const TOTAL_SUPPLY = hre.ethers.parseEther("1000000000"); // 1 billion VIBE
  const VIBInflationControl = await hre.ethers.getContractFactory("VIBInflationControl");
  const inflationControl = await VIBInflationControl.deploy(TOTAL_SUPPLY);
  await inflationControl.waitForDeployment();
  deployedContracts.VIBInflationControl = await inflationControl.getAddress();
  console.log("   VIBInflationControl:", deployedContracts.VIBInflationControl);

  // ========== 3. VIBStaking ==========
  console.log("\n[3/14] Deploying VIBStaking...");
  const VIBStaking = await hre.ethers.getContractFactory("VIBStaking");
  const staking = await VIBStaking.deploy(deployedContracts.VIBEToken);
  await staking.waitForDeployment();
  deployedContracts.VIBStaking = await staking.getAddress();
  console.log("   VIBStaking:", deployedContracts.VIBStaking);

  // ========== 4. VIBVesting ==========
  console.log("\n[4/14] Deploying VIBVesting...");
  const VIBVesting = await hre.ethers.getContractFactory("VIBVesting");
  const vesting = await VIBVesting.deploy(deployedContracts.VIBEToken);
  await vesting.waitForDeployment();
  deployedContracts.VIBVesting = await vesting.getAddress();
  console.log("   VIBVesting:", deployedContracts.VIBVesting);

  // ========== 5. VIBIdentity ==========
  console.log("\n[5/14] Deploying VIBIdentity...");
  const VIBIdentity = await hre.ethers.getContractFactory("VIBIdentity");
  const identity = await VIBIdentity.deploy(
    "VIBE Identity SBT",
    "VIBID",
    deployedContracts.VIBEToken
  );
  await identity.waitForDeployment();
  deployedContracts.VIBIdentity = await identity.getAddress();
  console.log("   VIBIdentity:", deployedContracts.VIBIdentity);

  // ========== 6. VIBGovernance ==========
  console.log("\n[6/14] Deploying VIBGovernance...");
  const VIBGovernance = await hre.ethers.getContractFactory("VIBGovernance");
  const governance = await VIBGovernance.deploy(deployedContracts.VIBEToken);
  await governance.waitForDeployment();
  deployedContracts.VIBGovernance = await governance.getAddress();
  console.log("   VIBGovernance:", deployedContracts.VIBGovernance);

  // ========== 7. VIBTimelock ==========
  console.log("\n[7/14] Deploying VIBTimelock...");
  const VIBTimelock = await hre.ethers.getContractFactory("VIBTimelock");
  const timelock = await VIBTimelock.deploy();
  await timelock.waitForDeployment();
  deployedContracts.VIBTimelock = await timelock.getAddress();
  console.log("   VIBTimelock:", deployedContracts.VIBTimelock);

  // ========== 8. VIBDividend ==========
  console.log("\n[8/14] Deploying VIBDividend...");
  const VIBDividend = await hre.ethers.getContractFactory("VIBDividend");
  const dividend = await VIBDividend.deploy(deployedContracts.VIBEToken);
  await dividend.waitForDeployment();
  deployedContracts.VIBDividend = await dividend.getAddress();
  console.log("   VIBDividend:", deployedContracts.VIBDividend);

  // ========== 9. VIBTreasury ==========
  console.log("\n[9/14] Deploying VIBTreasury...");
  const VIBTreasury = await hre.ethers.getContractFactory("VIBTreasury");
  const treasury = await VIBTreasury.deploy(
    deployedContracts.VIBEToken,
    [deployer.address], // signers
    1 // required signatures
  );
  await treasury.waitForDeployment();
  deployedContracts.VIBTreasury = await treasury.getAddress();
  console.log("   VIBTreasury:", deployedContracts.VIBTreasury);

  // ========== 10. AgentRegistry ==========
  console.log("\n[10/14] Deploying AgentRegistry...");
  const AgentRegistry = await hre.ethers.getContractFactory("AgentRegistry");
  const agentRegistry = await AgentRegistry.deploy();
  await agentRegistry.waitForDeployment();
  deployedContracts.AgentRegistry = await agentRegistry.getAddress();
  console.log("   AgentRegistry:", deployedContracts.AgentRegistry);

  // ========== 11. AgentWallet (deploy a factory/template) ==========
  console.log("\n[11/14] Deploying AgentWallet implementation...");
  const AgentWallet = await hre.ethers.getContractFactory("AgentWallet");
  // Deploy with deployer as owner and a zero agent address (template)
  const agentWalletImpl = await AgentWallet.deploy(
    deployer.address, // owner
    deployer.address, // agent (temporary)
    deployedContracts.VIBEToken,
    deployedContracts.AgentRegistry
  );
  await agentWalletImpl.waitForDeployment();
  deployedContracts.AgentWallet = await agentWalletImpl.getAddress();
  console.log("   AgentWallet:", deployedContracts.AgentWallet);

  // ========== 12. ZKCredential ==========
  console.log("\n[12/14] Deploying ZKCredential...");
  const ZKCredential = await hre.ethers.getContractFactory("ZKCredential");
  const zkCredential = await ZKCredential.deploy(
    "VIBE ZK Credential",
    "VZKC",
    deployer.address, // issuer
    deployer.address  // verifier
  );
  await zkCredential.waitForDeployment();
  deployedContracts.ZKCredential = await zkCredential.getAddress();
  console.log("   ZKCredential:", deployedContracts.ZKCredential);

  // ========== 13. AssetVault ==========
  console.log("\n[13/14] Deploying AssetVault...");
  const AssetVault = await hre.ethers.getContractFactory("AssetVault");
  const assetVault = await AssetVault.deploy(
    deployedContracts.VIBEToken,
    deployer.address, // fee collector
    "VIBE Asset Vault",
    "VAV"
  );
  await assetVault.waitForDeployment();
  deployedContracts.AssetVault = await assetVault.getAddress();
  console.log("   AssetVault:", deployedContracts.AssetVault);

  // ========== 14. JointOrder ==========
  console.log("\n[14/14] Deploying JointOrder...");
  const JointOrder = await hre.ethers.getContractFactory("JointOrder");
  const jointOrder = await JointOrder.deploy(
    deployedContracts.VIBEToken,
    deployer.address, // arbitrator
    deployer.address  // fee collector
  );
  await jointOrder.waitForDeployment();
  deployedContracts.JointOrder = await jointOrder.getAddress();
  console.log("   JointOrder:", deployedContracts.JointOrder);

  // ========== 配置合约关系 ==========
  console.log("\n" + "=".repeat(60));
  console.log("Configuring contract relationships...");
  console.log("=".repeat(60));

  // 设置 VIBEToken 的合约地址
  console.log("\nSetting contract addresses in VIBEToken...");
  let tx = await vibeToken.setStakingContract(deployedContracts.VIBStaking);
  await tx.wait();
  console.log("   Staking contract set");

  tx = await vibeToken.setVestingContract(deployedContracts.VIBVesting);
  await tx.wait();
  console.log("   Vesting contract set");

  tx = await vibeToken.setIdentityContract(deployedContracts.VIBIdentity);
  await tx.wait();
  console.log("   Identity contract set");

  tx = await vibeToken.setDividendContract(deployedContracts.VIBDividend);
  await tx.wait();
  console.log("   Dividend contract set");

  tx = await vibeToken.setEcosystemFundContract(deployedContracts.VIBTreasury);
  await tx.wait();
  console.log("   Treasury contract set");

  // 设置 VIBDividend 的质押合约
  console.log("\nSetting staking contract in VIBDividend...");
  tx = await dividend.setStakingContract(deployedContracts.VIBStaking);
  await tx.wait();
  console.log("   Staking contract set");

  // 设置通胀控制授权
  console.log("\nSetting authorized releaser in VIBInflationControl...");
  tx = await inflationControl.setAuthorizedReleaser(deployer.address, true);
  await tx.wait();
  console.log("   Deployer authorized as releaser");

  // 设置 AgentWallet 在 AgentRegistry 中
  console.log("\nSetting wallet contract in AgentRegistry...");
  tx = await agentRegistry.setWalletContract(deployedContracts.AgentWallet);
  await tx.wait();
  console.log("   Wallet contract set");

  // 铸造国库代币
  console.log("\nMinting treasury tokens (92% of supply)...");
  tx = await vibeToken.mintTreasury();
  await tx.wait();
  console.log("   Treasury tokens minted");

  // ========== 显示部署摘要 ==========
  console.log("\n" + "=".repeat(60));
  console.log("Deployment Complete!");
  console.log("=".repeat(60));

  console.log("\nNetwork:", hre.network.name);
  console.log("Chain ID:", (await hre.ethers.provider.getNetwork()).chainId.toString());
  console.log("Deployer:", deployer.address);

  console.log("\nDeployed Contracts:");
  for (const [name, address] of Object.entries(deployedContracts)) {
    console.log(`  ${name.padEnd(22)}: ${address}`);
  }

  console.log("\nToken Information:");
  const supply = await vibeToken.totalSupply();
  const deployerBalance = await vibeToken.balanceOf(deployer.address);
  console.log(`  Total Supply: ${hre.ethers.formatEther(supply)} VIBE`);
  console.log(`  Deployer Balance: ${hre.ethers.formatEther(deployerBalance)} VIBE`);

  // 保存部署信息
  const dir = "./deployments";
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }

  const deploymentInfo = {
    network: hre.network.name,
    chainId: (await hre.ethers.provider.getNetwork()).chainId.toString(),
    deployer: deployer.address,
    timestamp: new Date().toISOString(),
    contracts: deployedContracts,
    tokenInfo: {
      totalSupply: hre.ethers.formatEther(supply),
      deployerBalance: hre.ethers.formatEther(deployerBalance)
    }
  };

  const deploymentPath = `${dir}/${hre.network.name}.json`;
  fs.writeFileSync(deploymentPath, JSON.stringify(deploymentInfo, null, 2));
  console.log(`\nDeployment info saved to: ${deploymentPath}`);

  return deploymentInfo;
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
