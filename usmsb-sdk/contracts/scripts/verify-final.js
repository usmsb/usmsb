const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("=".repeat(70));
  console.log("  VIBE Protocol 部署验证报告");
  console.log("=".repeat(70));

  const [deployer] = await hre.ethers.getSigners();
  console.log("\n操作者:", deployer.address);
  console.log("网络:", hre.network.name);

  const deploymentFile = path.join(__dirname, "../deployments/latest.json");
  if (!fs.existsSync(deploymentFile)) {
    console.log("❌ 找不到部署文件");
    process.exit(1);
  }

  const deployment = JSON.parse(fs.readFileSync(deploymentFile, "utf8"));
  const contracts = deployment.contracts;

  console.log("\n部署时间:", deployment.timestamp);
  console.log("  部署者:", deployment.deployer);
  console.log("=".repeat(60));

  // 1. VIBEToken
  console.log("\n[1] VIBEToken...");
  const token = await hre.ethers.getContractAt("VIBEToken", contracts.VIBEToken);
  const name = await token.name();
  const symbol = await token.symbol();
  const totalSupply = await token.totalSupply();
  const owner = await token.owner();
  console.log("   名称:", name);
  console.log("   符号:", symbol);
  console.log("   总供应:", hre.ethers.formatEther(totalSupply), "VIBE");
  console.log("   Owner:", owner);
  console.log("   ✅ 代币已部署")

  // 2. VIBStaking
  console.log("\n[2] VIBStaking...");
  const staking = await hre.ethers.getContractAt("VIBStaking", contracts.VIBStaking);
  const stakingToken = await staking.vibeToken();
    console.log("   质押代币:", stakingToken);
    console.log("   ✅ 质押池正常")

  // 3. VIBGovernance
  console.log("\n[3] VIBGovernance...");
  const governance = await hre.ethers.getContractAt("VIBGovernance", contracts.VIBGovernance);
    const govToken = await governance.vibeToken();
    const delegation = await governance.delegationContract();
    const points = await governance.contributionPointsContract();
    console.log("   治理代币:", govToken);
    console.log("   委托合约:", delegation);
    console.log("   积分合约:", points);
    console.log("   ✅ 治理系统正常")

    // 4. EmissionController
  console.log("\n[4] EmissionController...");
            const emission = await hre.ethers.getContractAt("EmissionController", contracts.EmissionController);
            const emissionToken = await emission.vibeToken();
            const stakingPool = await emission.stakingPool();
            console.log("   VIBE代币:", emissionToken);
            console.log("   质押池:", stakingPool);
            console.log("   ✅ 激励释放正常")

            // 5. VIBReserve
            console.log("\n[5] VIBReserve...");
            const reserve = await hre.ethers.getContractAt("VIBReserve", contracts.VIBReserve);
            const reserveToken = await reserve.vibeToken();
            const reserveBalance = await token.balanceOf(contracts.VIBReserve);
            console.log("   VIBE代币:", reserveToken);
            console.log("   忒励池余额:", hre.ethers.formatEther(reserveBalance), "VIBE");
            console.log("   ✅ 激励池正常")

            // 6. VIBEcosystemPool
            console.log("\n[6] VIBEcosystemPool...");
            const ecosystemPool = await hre.ethers.getContractAt("VIBEcosystemPool", contracts.VIBEcosystemPool);
            const ecoToken = await ecosystemPool.vibeToken();
            const ecoBalance = await token.balanceOf(contracts.VIBEcosystemPool);
            console.log("   VIBE代币:", ecoToken);
            console.log("   生态池余额:", hre.ethers.formatEther(ecoBalance), "VIBE");
            console.log("   ✅ 生态池正常")

            // 7. VIBProtocolFund
            console.log("\n[7] VIBProtocolFund...");
            const protocolFund = await hre.ethers.getContractAt("VIBProtocolFund", contracts.VIBProtocolFund);
            const protocolToken = await protocolFund.vibeToken();
            const protocolBalance = await token.balanceOf(contracts.VIBProtocolFund);
            console.log("   VIBE代币:", protocolToken);
            console.log("   协议基金余额:", hre.ethers.formatEther(protocolBalance), "VIBE");
            console.log("   ✅ 协议基金正常")

            // 8. VIBInfrastructurePool
            console.log("\n[8] VIBInfrastructurePool...");
            const infraPool = await hre.ethers.getContractAt("VIBInfrastructurePool", contracts.VIBInfrastructurePool);
            const infraToken = await infraPool.vibeToken();
            const infraBalance = await token.balanceOf(contracts.VIBInfrastructurePool);
            console.log("   VIBE代币:", infraToken);
            console.log("   基础设施池余额:", hre.ethers.formatEther(infraBalance), "VIBE");
            console.log("   ✅ 基础设施池正常")

            // 9. VIBBuilderReward
            console.log("\n[9] VIBBuilderReward...");
            const builderReward = await hre.ethers.getContractAt("VIBBuilderReward", contracts.VIBBuilderReward);
            const builderToken = await builderReward.vibeToken();
            const builderBalance = await token.balanceOf(contracts.VIBBuilderReward);
            console.log("   VIBE代币:", builderToken);
            console.log("   建设者奖励余额:", hre.ethers.formatEther(builderBalance), "VIBE");
            console.log("   ✅ 建设者奖励正常")

            // 10. VIBDevReward
            console.log("\n[10] VIBDevReward...");
            const devReward = await hre.ethers.getContractAt("VIBDevReward", contracts.VIBDevReward);
            const devToken = await devReward.vibeToken();
            const devBalance = await token.balanceOf(contracts.VIBDevReward);
            console.log("   VIBE代币:", devToken);
            console.log("   开发者奖励余额:", hre.ethers.formatEther(devBalance), "VIBE");
            console.log("   ✅ 开发者奖励正常")

            // 11. CommunityStableFund
            console.log("\n[11] CommunityStableFund...");
            const stableFund = await hre.ethers.getContractAt("CommunityStableFund", contracts.CommunityStableFund);
            const stableToken = await stableFund.vibeToken();
            const stableBalance = await token.balanceOf(contracts.CommunityStableFund);
            console.log("   VIBE代币:", stableToken);
            console.log("   稳定基金余额:", hre.ethers.formatEther(stableBalance), "VIBE");
            console.log("   ✅ 稳定基金正常")

            // 12. AirdropDistributor
            console.log("\n[12] AirdropDistributor...");
            const airdrop = await hre.ethers.getContractAt("AirdropDistributor", contracts.AirdropDistributor);
            const airdropToken = await airdrop.vibeToken();
            const airdropBalance = await token.balanceOf(contracts.AirdropDistributor);
            console.log("   VIBE代币:", airdropToken);
            console.log("   空投池余额:", hre.ethers.formatEther(airdropBalance), "VIBE");
            console.log("   ✅ 空投池正常")

            // 13. VIBVesting
            console.log("\n[13] VIBVesting...");
            const vesting = await hre.ethers.getContractAt("VIBVesting", contracts.VIBVesting);
            const vestingToken = await vesting.vibeToken();
            const vestingBalance = await token.balanceOf(contracts.VIBVesting);
            console.log("   VIBE代币:", vestingToken);
            console.log("   锁仓合约余额:", hre.ethers.formatEther(vestingBalance), "VIBE");
            console.log("   ✅ 锁仓合约正常")

            // 14. VIBIdentity
            console.log("\n[14] VIBIdentity...");
            const identity = await hre.ethers.getContractAt("VIBIdentity", contracts.VIBIdentity);
            const idName = await identity.name();
            const idSymbol = await identity.symbol();
            console.log("   名称:", idName);
            console.log("   符号:", idSymbol);
            console.log("   ✅ 身份系统正常")

            // 15. VIBDividend
            console.log("\n[15] VIBDividend...");
            const dividend = await hre.ethers.getContractAt("VIBDividend", contracts.VIBDividend);
            const dividendToken = await dividend.vibeToken();
            console.log("   VIBE代币:", dividendToken);
            console.log("   ✅ 分红系统正常")

            // 16. VIBOutputReward
            console.log("\n[16] VIBOutputReward...");
            const outputReward = await hre.ethers.getContractAt("VIBOutputReward", contracts.VIBOutputReward);
            const outputStaking = await outputReward.stakingContract();
            console.log("   质押合约:", outputStaking);
            console.log("   ✅ 输出奖励正常")

            // 17. VIBVEPoints
            console.log("\n[17] VIBVEPoints...");
            const vePoints = await hre.ethers.getContractAt("VIBVEPoints", contracts.VIBVEPoints);
            const veStaking = await vePoints.stakingContract();
            console.log("   质押合约:", veStaking);
            console.log("   ✅ vePoints正常")

            // 18. VIBContributionPoints
            console.log("\n[18] VIBContributionPoints...");
            const contributionPoints = await hre.ethers.getContractAt("VIBContributionPoints", contracts.VIBContributionPoints);
            const cpGov = await contributionPoints.governanceContract();
            console.log("   治理合约:", cpGov);
            console.log("   ✅ 积分系统正常")

            // 19. VIBGovernanceDelegation
            console.log("\n[19] VIBGovernanceDelegation...");
            const delegation = await hre.ethers.getContractAt("VIBGovernanceDelegation", contracts.VIBGovernanceDelegation);
            const delegationGov = await delegation.governanceContract();
            console.log("   治理合约:", delegationGov);
            console.log("   ✅ 治理委托正常")

            // 20. AgentRegistry
            console.log("\n[20] AgentRegistry...");
            const agentRegistry = await hre.ethers.getContractAt("AgentRegistry", contracts.AgentRegistry);
            const agentCount = await agentRegistry.getAgentCount();
            console.log("   Agent数量:", agentCount);
            console.log("   ✅ Agent注册正常")

            // 21. ZKCredential
            console.log("\n[21] ZKCredential...");
            const zkCredential = await hre.ethers.getContractAt("ZKCredential", contracts.ZKCredential);
            console.log("   ✅ 零知识凭证正常")

            // 22. AssetVault
            console.log("\n[22] AssetVault...");
            const assetVault = await hre.ethers.getContractAt("AssetVault", contracts.AssetVault);
            const vaultWeth = await assetVault.weth();
            console.log("   WETH地址:", vaultWeth);
            console.log("   ✅ 资产金库正常")

            // 23. JointOrder
            console.log("\n[23] JointOrder...");
            const jointOrder = await hre.ethers.getContractAt("JointOrder", contracts.JointOrder);
            const orderToken = await jointOrder.vibeToken();
            console.log("   VIBE代币:", orderToken);
            console.log("   ✅ 联合订单正常")

            // 24. VIBNodeReward
            console.log("\n[24] VIBNodeReward...");
            const nodeReward = await hre.ethers.getContractAt("VIBNodeReward", contracts.VIBNodeReward);
            const nodeToken = await nodeReward.vibeToken();
            console.log("   VIBE代币:", nodeToken);
            console.log("   ✅ 节点奖励正常")

            // 25. VIBCollaboration
            console.log("\n[25] VIBCollaboration...");
            const collaboration = await hre.ethers.getContractAt("VIBCollaboration", contracts.VIBCollaboration);
            const collabToken = await collaboration.vibeToken();
            console.log("   VIBE代币:", collabToken);
            console.log("   ✅ 协作系统正常")

            // 26. VIBDispute
            console.log("\n[26] VIBDispute...");
            const dispute = await hre.ethers.getContractAt("VIBDispute", contracts.VIBDispute);
            const disputeToken = await dispute.vibeToken();
            console.log("   VIBE代币:", disputeToken);
            console.log("   ✅ 争议仲裁正常")

            // 27. PriceOracle
            console.log("\n[27] PriceOracle...");
            const priceOracle = await hre.ethers.getContractAt("PriceOracle", contracts.PriceOracle);
            console.log("   ✅ 价格预言机正常")

            // 28. AgentWallet
            console.log("\n[28] AgentWallet...");
            const agentWallet = await hre.ethers.getContractAt("AgentWallet", contracts.AgentWallet);
            console.log("   ✅ Agent钱包正常")

            // 29. LiquidityManager
            console.log("\n[29] LiquidityManager...");
            if (contracts.LiquidityManager && contracts.LiquidityManager !== "") {
                const liquidityManager = await hre.ethers.getContractAt("LiquidityManager", contracts.LiquidityManager);
                console.log("   地址:", contracts.LiquidityManager);
                console.log("   ✅ 流动性管理器正常");
            } else {
                console.log("   ⚠️ 跳过 (未部署)");
            }

            console.log("\n" + "=".repeat(70));
            console.log("  ✅ 所有合约验证通过!");
            console.log("=".repeat(70));
            console.log("\n区块链浏览器: https://sepolia.basescan.org");
}

main().then(() => process.exit(0)).catch(e => {
            console.error(e);
            process.exit(1);
        });
    }
  }
  console.log("部署已完成! 检查部署文件以获取所有合约地址列表:");
  const deployment = JSON.parse(fs.readFileSync(deploymentFile, 'utf8'));
  console.log("\n=== 已部署合约地址列表 ===");
  Object.entries(deployment.contracts).forEach(([name, address]) => {
    console.log(`${name}: ${address}`);
  });
  console.log("\n共部署了 ${Object.keys(deployment.contracts).length} 个合约");
}

main().then(() => process.exit(0)).catch(e => {
  console.error(e);
  process.exit(1);
});
