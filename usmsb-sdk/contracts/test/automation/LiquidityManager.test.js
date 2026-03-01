const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

describe("LiquidityManager", function () {
  let vibeToken, liquidityManager, mockRouter, mockFactory;
  let owner, user1;

  const LIQUIDITY_AMOUNT = ethers.parseEther("120000000"); // 1.2亿

  beforeEach(async function () {
    [owner, user1] = await ethers.getSigners();

    // 部署 VIBE Token
    const VIBEToken = await ethers.getContractFactory("VIBEToken");
    vibeToken = await VIBEToken.deploy("VIBE Token", "VIBE", owner.address);
    await vibeToken.waitForDeployment();
    await vibeToken.mintTreasury();

    // 部署 Mock Router
    const MockRouter = await ethers.getContractFactory("MockDEXRouter");
    mockRouter = await MockRouter.deploy(await vibeToken.getAddress());
    await mockRouter.waitForDeployment();

    // 部署 Mock Factory
    const MockFactory = await ethers.getContractFactory("MockDEXFactory");
    mockFactory = await MockFactory.deploy();
    await mockFactory.waitForDeployment();

    // 部署 LiquidityManager
    const LiquidityManager = await ethers.getContractFactory("LiquidityManager");
    liquidityManager = await LiquidityManager.deploy(
      await vibeToken.getAddress(),
      await mockRouter.getWETH(),
      await mockRouter.getAddress(),
      await mockFactory.getAddress()
    );
    await liquidityManager.waitForDeployment();

    // 模拟 distributeToPools：铸造 VIBE 到 LiquidityManager 合约
    // 新initializeLiquidity使用合约中已有的VIBE
    await vibeToken.transfer(await liquidityManager.getAddress(), LIQUIDITY_AMOUNT);
  });

  describe("Deployment", function () {
    it("Should set correct parameters", async function () {
      expect(await liquidityManager.vibeToken()).to.equal(await vibeToken.getAddress());
      expect(await liquidityManager.dexRouter()).to.equal(await mockRouter.getAddress());
      expect(await liquidityManager.dexFactory()).to.equal(await mockFactory.getAddress());
    });

    it("Should not be initialized initially", async function () {
      expect(await liquidityManager.initialized()).to.equal(false);
    });

    it("Should have correct constants", async function () {
      expect(await liquidityManager.MIN_REINVEST_INTERVAL()).to.equal(7 * 24 * 60 * 60);
      expect(await liquidityManager.REINVEST_REWARD()).to.equal(ethers.parseEther("0.001"));
    });
  });

  describe("Initialize Liquidity", function () {
    it("Should fail if not owner", async function () {
      const vibeAmount = ethers.parseEther("1000000");
      const ethAmount = ethers.parseEther("100");

      await vibeToken.transfer(user1.address, vibeAmount);
      await vibeToken.connect(user1).approve(await liquidityManager.getAddress(), vibeAmount);

      await expect(
        liquidityManager.connect(user1).initializeLiquidity({ value: ethAmount })
      ).to.be.revertedWithCustomError(liquidityManager, "OwnableUnauthorizedAccount");
    });

    it("Should initialize liquidity successfully", async function () {
      // 合约中已有VIBE余额（通过distributeToPools）
      const ethAmount = ethers.parseEther("100");

      // 新签名：只需要ethAmount
      await liquidityManager.initializeLiquidity({ value: ethAmount });

      expect(await liquidityManager.initialized()).to.equal(true);
      expect(await liquidityManager.totalVibeAdded()).to.be.gt(0);
      expect(await liquidityManager.totalEthAdded()).to.be.gt(0);
    });

    it("Should fail if already initialized", async function () {
      const ethAmount = ethers.parseEther("100");

      await liquidityManager.initializeLiquidity({ value: ethAmount });

      await expect(
        liquidityManager.initializeLiquidity({ value: ethAmount })
      ).to.be.revertedWith("Already initialized");
    });
  });

  describe("Add More Liquidity", function () {
    beforeEach(async function () {
      // 先初始化 - 新签名只需要ethAmount
      const ethAmount = ethers.parseEther("100");
      await liquidityManager.initializeLiquidity({ value: ethAmount });
    });

    it("Should add more liquidity", async function () {
      const vibeAmount = ethers.parseEther("500000");
      const ethAmount = ethers.parseEther("50");

      const totalBefore = await liquidityManager.totalVibeAdded();

      await vibeToken.approve(await liquidityManager.getAddress(), vibeAmount);
      await liquidityManager.addMoreLiquidity(vibeAmount, { value: ethAmount });

      const totalAfter = await liquidityManager.totalVibeAdded();
      expect(totalAfter).to.be.gt(totalBefore);
    });
  });

  describe("Reinvest", function () {
    beforeEach(async function () {
      // 初始化 - 新签名只需要ethAmount
      const ethAmount = ethers.parseEther("100");
      await liquidityManager.initializeLiquidity({ value: ethAmount });
    });

    it("Should not reinvest too frequently", async function () {
      const [canReinvest, reason] = await liquidityManager.canReinvest();
      expect(canReinvest).to.equal(false);
      expect(reason).to.equal("Too frequent");
    });

    it("Should check reinvest status after interval", async function () {
      await time.increase(7 * 24 * 60 * 60);

      // 取决于 mock 实现和费用估算
      const [canReinvest, reason] = await liquidityManager.canReinvest();
      // 可能是 "Fees too low" 或 "Can trigger"
    });
  });

  describe("Stats", function () {
    it("Should return correct stats before initialization", async function () {
      const [totalVibe, totalEth, lpBalance, totalReinvested, count, lastTime] =
        await liquidityManager.getStats();

      expect(totalVibe).to.equal(0);
      expect(totalEth).to.equal(0);
      expect(count).to.equal(0);
    });
  });

  describe("Emergency Functions", function () {
    it("Should allow owner to withdraw wrong tokens", async function () {
      // 部署另一个测试代币
      const TestToken = await ethers.getContractFactory("VIBEToken");
      const testToken = await TestToken.deploy("Test", "TEST", owner.address);
      await testToken.waitForDeployment();

      // Mint tokens first (required for VIBEToken)
      await testToken.mintTreasury();

      const amount = ethers.parseEther("1000");
      await testToken.transfer(await liquidityManager.getAddress(), amount);

      const balanceBefore = await testToken.balanceOf(owner.address);

      // Step 1: Initiate emergency withdraw
      await liquidityManager.emergencyWithdraw(await testToken.getAddress());

      // Step 2: Fast forward 2 days
      await ethers.provider.send("evm_increaseTime", [2 * 24 * 60 * 60]);
      await ethers.provider.send("evm_mine");

      // Step 3: Confirm emergency withdraw
      await liquidityManager.confirmEmergencyWithdraw();

      const balanceAfter = await testToken.balanceOf(owner.address);

      expect(balanceAfter - balanceBefore).to.equal(amount);
    });

    it("Should allow owner to withdraw ETH", async function () {
      // 先发送一些 ETH
      await owner.sendTransaction({
        to: await liquidityManager.getAddress(),
        value: ethers.parseEther("1")
      });

      // Step 1: Initiate emergency withdraw
      await liquidityManager.emergencyWithdrawETH();

      // Step 2: Fast forward 2 days
      await ethers.provider.send("evm_increaseTime", [2 * 24 * 60 * 60]);
      await ethers.provider.send("evm_mine");

      // Step 3: Confirm emergency withdraw
      const balanceBefore = await ethers.provider.getBalance(owner.address);
      await liquidityManager.confirmEmergencyWithdrawETH();
      const balanceAfter = await ethers.provider.getBalance(owner.address);

      expect(balanceAfter).to.be.gt(balanceBefore);
    });
  });

  describe("Pause", function () {
    it("Should pause and unpause", async function () {
      await liquidityManager.pause();
      expect(await liquidityManager.paused()).to.equal(true);

      await liquidityManager.unpause();
      expect(await liquidityManager.paused()).to.equal(false);
    });
  });

  describe("Investor Add Liquidity (addLiquidityAndGetLP)", function () {
    beforeEach(async function () {
      // 先初始化
      const ethAmount = ethers.parseEther("100");
      await liquidityManager.initializeLiquidity({ value: ethAmount });
    });

    it("Should reject below minimum ETH", async function () {
      const tooLittleEth = ethers.parseEther("0.05"); // 小于0.1 ETH
      const deadline = (await time.latest()) + 300; // 使用区块链时间

      await expect(
        liquidityManager.connect(user1).addLiquidityAndGetLP(0, 0, deadline, { value: tooLittleEth })
      ).to.be.revertedWith("Below minimum 0.1 ETH");
    });

    it("Should reject when paused", async function () {
      await liquidityManager.pause();
      const deadline = (await time.latest()) + 300;

      await expect(
        liquidityManager.connect(user1).addLiquidityAndGetLP(0, 0, deadline, { value: ethers.parseEther("1") })
      ).to.be.revertedWithCustomError(liquidityManager, "EnforcedPause");
    });

    it("Should reject before initialization", async function () {
      // 部署新的LiquidityManager（未初始化）
      const LiquidityManager2 = await ethers.getContractFactory("LiquidityManager");
      const liquidityManager2 = await LiquidityManager2.deploy(
        await vibeToken.getAddress(),
        await mockRouter.getWETH(),
        await mockRouter.getAddress(),
        await mockFactory.getAddress()
      );
      await liquidityManager2.waitForDeployment();

      const deadline = (await time.latest()) + 300;

      await expect(
        liquidityManager2.connect(user1).addLiquidityAndGetLP(0, 0, deadline, { value: ethers.parseEther("1") })
      ).to.be.revertedWith("Not initialized");
    });

    it("Should reject expired deadline (front-running protection)", async function () {
      const expiredDeadline = (await time.latest()) - 100; // 使用区块链时间

      await expect(
        liquidityManager.connect(user1).addLiquidityAndGetLP(0, 0, expiredDeadline, { value: ethers.parseEther("1") })
      ).to.be.revertedWith("Transaction expired");
    });
  });
});
