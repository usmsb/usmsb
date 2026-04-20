/**
 * 直接验证 VIBNodeReward.sol priceOracle 修复的 Hardhat 脚本
 * 用法: npx hardhat run scripts/verify_priceoracle_fix.js
 */
const { ethers } = require("hardhat");

async function main() {
  console.log("=== VIBNodeReward priceOracle 修复验证 ===\n");

  const [owner, nodeOp, assessor] = await ethers.getSigners();

  // 1. 部署 VIBEToken（只有 name + symbol，不传 owner）
  const VIBEToken = await ethers.getContractFactory("VIBEToken");
  const vibeToken = await VIBEToken.deploy("VIBE Token", "VIBE");
  await vibeToken.waitForDeployment();
  console.log("✅ VIBEToken deployed:", await vibeToken.getAddress());

  // 2. 部署 VIBIdentity
  const VIBIdentity = await ethers.getContractFactory("VIBIdentity");
  const vibIdentity = await VIBIdentity.deploy("VIB Identity", "VIBID", await vibeToken.getAddress());
  await vibIdentity.waitForDeployment();
  console.log("✅ VIBIdentity deployed:", await vibIdentity.getAddress());

  // 3. 部署 VIBNodeReward
  const VIBNodeReward = await ethers.getContractFactory("VIBNodeReward");
  const nodeReward = await VIBNodeReward.deploy(
    await vibeToken.getAddress(),
    await vibIdentity.getAddress()
  );
  await nodeReward.waitForDeployment();
  console.log("✅ VIBNodeReward deployed:", await nodeReward.getAddress());

  // 4. Mint VIBE 给 NodeReward 合约（用于支付奖励）
  // 先 mint 出所有代币
  try {
    await vibeToken.mintTreasury();
    console.log("✅ mintTreasury succeeded");
  } catch (e) {
    console.log("⚠️  mintTreasury failed:", e.message.split("\n")[0]);
  }

  // 给 nodeReward 转一些币用于支付奖励
  const nodeRewardAddr = await nodeReward.getAddress();
  const fundAmount = ethers.parseEther("100000");
  try {
    await vibeToken.transfer(nodeRewardAddr, fundAmount);
    console.log("✅ Transferred 100000 VIBE to nodeReward");
  } catch (e) {
    console.log("⚠️  Transfer failed:", e.message.split("\n")[0]);
  }

  // 5. 注册节点
  // 先 mint 一个 identity token 给 nodeOp
  await vibIdentity.mint(await nodeOp.getAddress(), 2, "Node Operator");
  await nodeReward.connect(nodeOp).registerNode(0, 8); // GPU_COMPUTE, 8 GPUs
  console.log("✅ Node registered for", await nodeOp.getAddress());

  // 6. 授权 assessor
  await nodeReward.setAuthorizedAssessor(await assessor.getAddress(), true);
  console.log("✅ Assessor authorized");

  // =============================================
  // 测试 1: usdToVibe — priceOracle 未设置时应 revert
  // =============================================
  console.log("\n--- 测试 1: usdToVibe revert when priceOracle not set ---");
  try {
    await nodeReward.usdToVibe(ethers.parseEther("1"));
    console.log("❌ FAIL: should have reverted but didn't");
    process.exit(1);
  } catch (e) {
    if (e.message.includes("priceOracle not set")) {
      console.log("✅ PASS: reverted with 'priceOracle not set'");
    } else {
      console.log("❌ FAIL: wrong error:", e.message.split("\n")[0]);
      process.exit(1);
    }
  }

  // =============================================
  // 测试 2: recordService — priceOracle 未设置时应 revert
  // =============================================
  console.log("\n--- 测试 2: recordService revert when priceOracle not set ---");
  try {
    await nodeReward
      .connect(assessor)
      .recordService(
        await nodeOp.getAddress(),
        0,      // GPU_COMPUTE
        3600,   // 1 hour
        8,      // 8 GPUs
        10000,  // 1.0x quality
        10000,  // 1.0x prod
        10000,  // 1.0x rel
        ethers.ZeroHash
      );
    console.log("❌ FAIL: should have reverted but didn't");
    process.exit(1);
  } catch (e) {
    if (e.message.includes("priceOracle not set")) {
      console.log("✅ PASS: reverted with 'priceOracle not set'");
    } else {
      console.log("❌ FAIL: wrong error:", e.message.split("\n")[0]);
      process.exit(1);
    }
  }

  // =============================================
  // 测试 3: 设置 priceOracle 后正常计算
  // =============================================
  console.log("\n--- 测试 3: Normal operation after setting priceOracle ---");

  // 使用 MockContracts.MockPriceOracle
  const MockPriceOracle = await ethers.getContractFactory(
    "src/mocks/MockContracts.sol:MockPriceOracle"
  );
  const mockOracle = await MockPriceOracle.deploy();
  await mockOracle.waitForDeployment();
  await mockOracle.setPrice(ethers.parseEther("0.1")); // $0.1 / VIBE
  console.log("✅ MockPriceOracle deployed:", await mockOracle.getAddress());

  await nodeReward.setPriceOracle(await mockOracle.getAddress());
  console.log("✅ priceOracle set in VIBNodeReward");

  // 现在 usdToVibe 应该正常工作
  const vibeAmount = await nodeReward.usdToVibe(ethers.parseEther("1"));
  const expected = ethers.parseEther("10"); // $1 / $0.1 = 10 VIBE
  if (vibeAmount.toString() === expected.toString()) {
    console.log("✅ PASS: usdToVibe($1) = 10 VIBE ✓");
  } else {
    console.log(`❌ FAIL: expected ${expected}, got ${vibeAmount}`);
    process.exit(1);
  }

  // =============================================
  // 测试 4: recordService 正常工作
  // =============================================
  console.log("\n--- 测试 4: recordService works with valid priceOracle ---");

  // 给 nodeReward 合约转一些 VIBE 用于支付奖励
  try {
    await vibeToken.mint(await nodeReward.getAddress(), ethers.parseEther("100000"));
    console.log("✅ Funded nodeReward with 100000 VIBE");
  } catch (e) {
    console.log("⚠️  Could not mint directly to nodeReward:", e.message.split("\n")[0]);
  }

  const tx = await nodeReward
    .connect(assessor)
    .recordService(
      await nodeOp.getAddress(),
      0,      // GPU_COMPUTE
      3600,   // 1 hour
      8,      // 8 GPUs
      10000,  // 1.0x quality
      10000,  // 1.0x prod
      10000,  // 1.0x rel
      ethers.ZeroHash
    );
  const receipt = await tx.wait();
  console.log("✅ recordService succeeded! gas used:", receipt.gasUsed.toString());

  // =============================================
  // 测试 5: 预言机返回 0 价格时应 revert
  // =============================================
  console.log("\n--- 测试 5: usdToVibe reverts when oracle returns 0 ---");
  await mockOracle.setPrice(0); // 模拟预言机故障
  try {
    await nodeReward.usdToVibe(ethers.parseEther("1"));
    console.log("❌ FAIL: should have reverted when price is 0");
    process.exit(1);
  } catch (e) {
    if (e.message.includes("invalid vibe price")) {
      console.log("✅ PASS: reverted with 'invalid vibe price'");
    } else {
      console.log("❌ FAIL: wrong error:", e.message.split("\n")[0]);
      process.exit(1);
    }
  }

  console.log("\n=== 所有测试通过 ✅ ===");
  console.log("\n修复验证:");
  console.log("1. usdToVibe() — priceOracle 未设置 → revert ✅");
  console.log("2. usdToVibe() — vibePrice=0 → revert ✅");
  console.log("3. recordService() — priceOracle 未设置 → revert ✅");
  console.log("4. 设置正确的预言机后 → 正常工作 ✅");
}

main().catch((e) => {
  console.error("❌ Script failed:", e.message.split("\n")[0]);
  process.exit(1);
});
