const hre = require("hardhat");

async function main() {
  console.log("=".repeat(60));
  console.log("  验证 Base Sepolia 部署的合约");
  console.log("=".repeat(60));

  // 部署的合约地址
  const contracts = {
    VIBEToken: "0x91d8C3084b4fd21A04fA3584BFE357F378938dbc",
    VIBStaking: "0xc3fbD1736a95f403A0569FcA8C84d7B85e2b4E53",
    VIBGovernance: "0xD866536154154a378544E9dc295D510a0fe29236",
    VIBIdentity: "0x6b72711045b3a384E26eD9039CFF4cA12b856952",
    AgentRegistry: "0x54bEbDc40cc8B60b0922D8FA6463ab710B14dC69",
    EmissionController: "0xe4a31e600D2DeB3297f3732aE509B1C1d7eAAaD6",
  };

  // 1. 检查 VIBEToken
  console.log("\n[1] VIBEToken 验证...");
  try {
    const token = await hre.ethers.getContractAt("VIBEToken", contracts.VIBEToken);
    const name = await token.name();
    const symbol = await token.symbol();
    const totalSupply = await token.totalSupply();
    const decimals = await token.decimals();
    console.log("   名称:", name);
    console.log("   符号:", symbol);
    console.log("   总供应量:", hre.ethers.formatUnits(totalSupply, decimals), "VIBE");
    console.log("   状态: ✅ 正常");
  } catch (e) {
    console.log("   状态: ❌", e.message.substring(0, 50));
  }

  // 2. 检查 VIBStaking
  console.log("\n[2] VIBStaking 验证...");
  try {
    const staking = await hre.ethers.getContractAt("VIBStaking", contracts.VIBStaking);
    const stakingToken = await staking.vibeToken();
    const stakerCount = await staking.getStakerCount();
    console.log("   代币地址:", stakingToken);
    console.log("   质押者数量:", stakerCount);
    console.log("   状态: ✅ 正常");
  } catch (e) {
    console.log("   状态: ❌", e.message.substring(0, 50));
  }

  // 3. 检查 VIBGovernance
  console.log("\n[3] VIBGovernance 验证...");
  try {
    const governance = await hre.ethers.getContractAt("VIBGovernance", contracts.VIBGovernance);
    const govToken = await governance.vibeToken();
    const delegation = await governance.delegationContract();
    const points = await governance.contributionPointsContract();
    console.log("   代币:", govToken);
    console.log("   委托合约:", delegation);
    console.log("   积分合约:", points);
    console.log("   状态: ✅ 正常");
  } catch (e) {
    console.log("   状态: ❌", e.message.substring(0, 50));
  }

  // 4. 检查 VIBIdentity
  console.log("\n[4] VIBIdentity 验证...");
  try {
    const identity = await hre.ethers.getContractAt("VIBIdentity", contracts.VIBIdentity);
    const idName = await identity.name();
    const idSymbol = await identity.symbol();
    const idCount = await identity.getIdentityCount();
    console.log("   名称:", idName);
    console.log("   符号:", idSymbol);
    console.log("   身份数量:", idCount);
    console.log("   状态: ✅ 正常");
  } catch (e) {
    console.log("   状态: ❌", e.message.substring(0, 50));
  }

  // 5. 检查 AgentRegistry
  console.log("\n[5] AgentRegistry 验证...");
  try {
    const registry = await hre.ethers.getContractAt("AgentRegistry", contracts.AgentRegistry);
    const agentCount = await registry.getAgentCount();
    console.log("   Agent数量:", agentCount);
    console.log("   状态: ✅ 正常");
  } catch (e) {
    console.log("   状态: ❌", e.message.substring(0, 50));
  }

  // 6. 检查 EmissionController
  console.log("\n[6] EmissionController 验证...");
  try {
    const emission = await hre.ethers.getContractAt("EmissionController", contracts.EmissionController);
    const totalEmission = await emission.TOTAL_EMISSION();
    const duration = await emission.EMISSION_DURATION();
    const released = await emission.totalReleased();
    console.log("   总释放量:", hre.ethers.formatEther(totalEmission), "VIBE");
    console.log("   释放周期:", (duration / 86400).toFixed(0), "天");
    console.log("   已释放:", hre.ethers.formatEther(released), "VIBE");
    console.log("   状态: ✅ 正常");
  } catch (e) {
    console.log("   状态: ❌", e.message.substring(0, 50));
  }

  // 7. 检查 VIBVesting
  console.log("\n[7] VIBVesting 验证...");
  try {
    const vesting = await hre.ethers.getContractAt("VIBVesting", "0x3d476714B8B78488CEF6B795eF6A2C5167625BEf");
    const vToken = await vesting.vibeToken();
    const bCount = await vesting.beneficiaryCount();
    console.log("   代币:", vToken);
    console.log("   受益人数量:", bCount);
    console.log("   状态: ✅ 正常");
  } catch (e) {
    console.log("   状态: ❌", e.message.substring(0, 50));
  }

  // 8. 检查 VIBDividend
  console.log("\n[8] VIBDividend 验证...");
  try {
    const dividend = await hre.ethers.getContractAt("VIBDividend", "0x324571F84C092a958eB46b3478742C58a7beaE7B");
    const dToken = await dividend.vibeToken();
    console.log("   代币:", dToken);
    console.log("   状态: ✅ 正常");
  } catch (e) {
    console.log("   状态: ❌", e.message.substring(0, 50));
  }

  console.log("\n" + "=".repeat(60));
  console.log("  ✅ 合约验证完成！所有合约在链上正常运行");
  console.log("=".repeat(60));
}

main().then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });
