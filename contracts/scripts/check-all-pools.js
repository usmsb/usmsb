const hre = require("hardhat");
const path = require("path");

async function main() {
  // 合约地址 (小写， ethers会自动checksum)
  const emissionController = "0xaed496480c9668dc90dc309fcd8fd9ae4268df39";
  const vibeToken = "0x93c52df000317e12f891474b46d8b05652430bdc";
  
  // 各池子地址
  const pools = {
    stakingPool: "0x1901ab56ea38cbefc7a3f0ed188b7108d27f4c05",
    ecosystemPool: "0x20a25378db87a94e19a8b51ed638f67d6e9bfe06",
    governancePool: "0x27475aea1eeba485005b1717a35a7d411d144a1d",
    reservePool: "0x56abaf5fc5d58c92c0a51f79251bf3a3002f4263",
    outputRewardPool: "0x7b3ceb40cfb093e66ecd5b49f835586ba7ef428b"
  };
  
  // 读取 artifact
  const artifact = JSON.parse(
    require("fs").readFileSync(
      path.join(__dirname, "../artifacts/src/automation/EmissionController.sol/EmissionController.json"),
      "utf8"
    )
  );
  
  const artifactVIBE = JSON.parse(
    require("fs").readFileSync(
      path.join(__dirname, "../artifacts/src/VIBEToken.sol/VIBEToken.json"),
      "utf8"
    )
  );
  
  const [signer] = await hre.ethers.getSigners();
  const provider = signer.provider;
  
  const ec = new hre.ethers.Contract(emissionController, artifact.abi, provider);
  const token = new hre.ethers.Contract(vibeToken, artifactVIBE.abi, provider);
  
  console.log("=== 检查日期:", new Date().toISOString(), "===\n");
  
  // 1. 检查 EmissionController 状态
  console.log("--- EmissionController 状态 ---");
  const [totalReleased, startTime, lastEpochTime, ecBalance] = await Promise.all([
    ec.totalReleased(),
    ec.startTime(),
    ec.lastEpochTime(),
    token.balanceOf(emissionController)
  ]);
  
  console.log("Total Released:", totalReleased.toString(), "wei");
  console.log("Start Time:", new Date(Number(startTime) * 1000).toISOString());
  console.log("Last Epoch Time:", new Date(Number(lastEpochTime) * 1000).toISOString());
  console.log("EC 代币余额:", hre.ethers.formatUnits(ecBalance, 18), "VIBE");
  console.log("");
  
  // 2. 检查各池子余额
  console.log("--- 各池子代币余额 ---");
  const poolBalances = {};
  for (const [name, addr] of Object.entries(pools)) {
    const bal = await token.balanceOf(addr);
    poolBalances[name] = bal;
    console.log(`${name}: ${hre.ethers.formatUnits(bal, 18)} VIBE`);
  }
  console.log("");
  
  // 3. 检查比例设置
  console.log("--- 当前分配比例 ---");
  try {
    const [stakingRatio, ecosystemRatio, governanceRatio, reserveRatio] = await Promise.all([
      ec.STAKING_RATIO(),
      ec.ECOSYSTEM_RATIO(),
      ec.GOVERNANCE_RATIO(),
      ec.RESERVE_RATIO()
    ]);
    console.log("STAKING_RATIO:", stakingRatio.toString(), "=", Number(stakingRatio)/100, "%");
    console.log("ECOSYSTEM_RATIO:", ecosystemRatio.toString(), "=", Number(ecosystemRatio)/100, "%");
    console.log("GOVERNANCE_RATIO:", governanceRatio.toString(), "=", Number(governanceRatio)/100, "%");
    console.log("RESERVE_RATIO:", reserveRatio.toString(), "=", Number(reserveRatio)/100, "%");
    
    const total = Number(stakingRatio) + Number(ecosystemRatio) + Number(governanceRatio) + Number(reserveRatio);
    console.log("\n比例合计:", total/100, "%");
    
    // 检查是否有 OUTPUT_RATIO
    try {
      const outputRatio = await ec.OUTPUT_RATIO();
      console.log("OUTPUT_RATIO:", outputRatio.toString(), "=", Number(outputRatio)/100, "%");
    } catch (e) {
      console.log("OUTPUT_RATIO: 不存在 (旧版合约)");
    }
  } catch (e) {
    console.log("无法读取比例:", e.message);
  }
  console.log("");
  
  // 4. 总结
  console.log("--- 总结 ---");
  if (totalReleased === 0n && ecBalance > 0) {
    console.log("✅ 状态: 合约有代币但尚未分配");
    console.log("✅ 行动: 可以废弃此合约，部署新版");
  } else if (totalReleased === 0n && ecBalance === 0n) {
    console.log("⚠️ 状态: 合约没有代币");
    console.log("⚠️ 行动: 需要先往合约转代币");
  } else {
    console.log("❌ 状态: 已经有过分配");
    console.log("❌ 行动: 需要处理历史分配问题");
  }
  
  console.log("\n--- 各池子当前余额 (占总量6.3亿的比例) ---");
  const expectedTotal = 630_000_000 * 10**18;
  for (const [name, bal] of Object.entries(poolBalances)) {
    const percent = Number(bal) * 100 / expectedTotal;
    console.log(`${name}: ${percent.toFixed(4)}% (${hre.ethers.formatUnits(bal, 18)} VIBE)`);
  }
  
  // 5. VIBOutputReward 状态
  console.log("\n--- VIBOutputReward 状态 ---");
  const outputBal = await token.balanceOf(pools.outputRewardPool);
  console.log("VIBOutputReward 余额:", hre.ethers.formatUnits(outputBal, 18), "VIBE");
  
  const artifactOutput = JSON.parse(
    require("fs").readFileSync(
      path.join(__dirname, "../artifacts/src/VIBOutputReward.sol/VIBOutputReward.json"),
      "utf8"
    )
  );
  const outputContract = new hre.ethers.Contract(pools.outputRewardPool, artifactOutput.abi, provider);
  
  try {
    const dailyPoolAmount = await outputContract.dailyPoolAmount();
    console.log("dailyPoolAmount:", hre.ethers.formatUnits(dailyPoolAmount, 18), "VIBE");
  } catch (e) {
    console.log("dailyPoolAmount: 无法读取 (可能未初始化)");
  }
}

main().catch(console.error);
