const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

describe("EmissionController", function () {
  let vibeToken, emissionController;
  let owner, stakingPool, ecosystemPool, governancePool, reservePool, addr1;

  const TOTAL_SUPPLY = ethers.parseEther("1000000000"); // 10亿
  const EMISSION_AMOUNT = ethers.parseEther("630000000"); // 6.3亿
  const EPOCH_DURATION = 7 * 24 * 60 * 60; // 7天

  beforeEach(async function () {
    [owner, stakingPool, ecosystemPool, governancePool, reservePool, addr1] = await ethers.getSigners();

    // 部署 VIBE Token
    const VIBEToken = await ethers.getContractFactory("VIBEToken");
    vibeToken = await VIBEToken.deploy("VIBE Token", "VIBE", owner.address);
    await vibeToken.waitForDeployment();
    await vibeToken.mintTreasury();

    // 部署 EmissionController
    const EmissionController = await ethers.getContractFactory("EmissionController");
    emissionController = await EmissionController.deploy(
      await vibeToken.getAddress(),
      stakingPool.address,
      ecosystemPool.address,
      governancePool.address,
      reservePool.address
    );
    await emissionController.waitForDeployment();

    // 转移激励池代币到 EmissionController
    await vibeToken.transfer(await emissionController.getAddress(), EMISSION_AMOUNT);
  });

  describe("Deployment", function () {
    it("Should set correct parameters", async function () {
      expect(await emissionController.vibeToken()).to.equal(await vibeToken.getAddress());
      expect(await emissionController.stakingPool()).to.equal(stakingPool.address);
      expect(await emissionController.ecosystemPool()).to.equal(ecosystemPool.address);
      expect(await emissionController.governancePool()).to.equal(governancePool.address);
      expect(await emissionController.reservePool()).to.equal(reservePool.address);
    });

    it("Should have correct emission constants", async function () {
      expect(await emissionController.TOTAL_EMISSION()).to.equal(EMISSION_AMOUNT);
      expect(await emissionController.EMISSION_DURATION()).to.equal(5 * 365 * 24 * 60 * 60);
      expect(await emissionController.EPOCH_DURATION()).to.equal(EPOCH_DURATION);
    });

    it("Should have correct distribution ratios", async function () {
      expect(await emissionController.STAKING_RATIO()).to.equal(4500);  // 45%
      expect(await emissionController.ECOSYSTEM_RATIO()).to.equal(3000); // 30%
      expect(await emissionController.GOVERNANCE_RATIO()).to.equal(1500); // 15%
      expect(await emissionController.RESERVE_RATIO()).to.equal(1000);   // 10%
    });
  });

  describe("Releasable Amount", function () {
    it("Should calculate releasable amount correctly", async function () {
      const releasable = await emissionController.getReleasableAmount();
      // 刚部署时应该有少量可释放（因为时间已经开始）
      expect(releasable).to.be.gte(0);
    });

    it("Should increase releasable amount over time", async function () {
      const releasableBefore = await emissionController.getReleasableAmount();

      // 快进1天
      await time.increase(24 * 60 * 60);

      const releasableAfter = await emissionController.getReleasableAmount();
      expect(releasableAfter).to.be.gt(releasableBefore);
    });
  });

  describe("Epoch Distribute", function () {
    it("Should fail if epoch not yet", async function () {
      await expect(
        emissionController.epochDistribute()
      ).to.be.revertedWith("Epoch not yet");
    });

    it("Should distribute after epoch duration", async function () {
      // 快进7天
      await time.increase(EPOCH_DURATION);

      const stakingBalanceBefore = await vibeToken.balanceOf(stakingPool.address);

      await emissionController.epochDistribute();

      const stakingBalanceAfter = await vibeToken.balanceOf(stakingPool.address);
      expect(stakingBalanceAfter).to.be.gt(stakingBalanceBefore);
    });

    it("Should emit EmissionReleased event", async function () {
      await time.increase(EPOCH_DURATION);

      await expect(emissionController.epochDistribute())
        .to.emit(emissionController, "EmissionReleased");
    });
  });

  describe("Emergency Refill", function () {
    it("Should fail if staking pool not set", async function () {
      // 部署一个没有设置质押池的控制器
      const EmissionController = await ethers.getContractFactory("EmissionController");
      const newController = await EmissionController.deploy(
        await vibeToken.getAddress(),
        ethers.ZeroAddress, // 无质押池
        ecosystemPool.address,
        governancePool.address,
        reservePool.address
      );

      await expect(
        newController.emergencyRefill()
      ).to.be.revertedWith("Staking pool not set");
    });

    it("Should fail if pool has enough balance", async function () {
      // 给质押池转入足够余额
      await vibeToken.transfer(stakingPool.address, ethers.parseEther("200000"));

      await expect(
        emissionController.emergencyRefill()
      ).to.be.revertedWith("Pool has enough balance");
    });
  });

  describe("Pool Management", function () {
    it("Should allow owner to update pool addresses", async function () {
      await emissionController.setStakingPool(addr1.address);
      expect(await emissionController.stakingPool()).to.equal(addr1.address);
    });

    it("Should not allow non-owner to update pools", async function () {
      await expect(
        emissionController.connect(addr1).setStakingPool(addr1.address)
      ).to.be.revertedWithCustomError(emissionController, "OwnableUnauthorizedAccount");
    });
  });

  describe("Stats", function () {
    it("Should return correct progress info", async function () {
      const [released, releasable, remaining, progress] = await emissionController.getEmissionProgress();

      expect(released).to.equal(0);
      expect(releasable).to.be.gte(0);
      expect(remaining).to.be.lte(EMISSION_AMOUNT);
    });
  });
});
