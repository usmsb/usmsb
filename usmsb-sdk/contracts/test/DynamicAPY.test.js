const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

describe("VIBStaking Dynamic APY", function () {
  let vibeToken, staking, priceOracle;
  let owner, user1, user2;

  const TOTAL_SUPPLY = ethers.parseEther("1000000000"); // 1 billion
  const BASE_APY = 3;
  const MAX_APY = 10;
  const MAX_APY_BONUS = 7;

  beforeEach(async function () {
    [owner, user1, user2] = await ethers.getSigners();

    // Deploy VIBEToken
    const VIBEToken = await ethers.getContractFactory("VIBEToken");
    vibeToken = await VIBEToken.deploy("VIBE Token", "VIBE", owner.address);
    await vibeToken.waitForDeployment();
    await vibeToken.mintTreasury();

    // Deploy mock PriceOracle
    const MockPriceOracle = await ethers.getContractFactory(
      "src/mocks/MockContracts.sol:MockPriceOracle"
    );
    priceOracle = await MockPriceOracle.deploy();
    await priceOracle.waitForDeployment();

    // Deploy VIBStaking
    const VIBStaking = await ethers.getContractFactory("VIBStaking");
    staking = await VIBStaking.deploy(await vibeToken.getAddress());
    await staking.waitForDeployment();

    // Transfer tokens for testing
    await vibeToken.transfer(user1.address, ethers.parseEther("50000"));
    await vibeToken.transfer(await staking.getAddress(), ethers.parseEther("100000"));

    // Setup approvals
    await vibeToken.connect(user1).approve(await staking.getAddress(), ethers.MaxUint256);
    await vibeToken.connect(owner).approve(await staking.getAddress(), ethers.MaxUint256);
  });

  describe("Base APY", function () {
    it("Should have correct initial APY", async function () {
      expect(await staking.currentAPY()).to.equal(BASE_APY);
    });

    it("Should have correct APY range constants", async function () {
      expect(await staking.MIN_APY()).to.equal(3); // 白皮书修复: 统一为3%
      expect(await staking.MAX_APY()).to.equal(MAX_APY);
      expect(await staking.BASE_APY()).to.equal(BASE_APY);
    });
  });

  describe("Price Oracle Integration", function () {
    it("Should allow setting price oracle", async function () {
      await staking.setPriceOracle(await priceOracle.getAddress());
      expect(await staking.priceOracle()).to.equal(await priceOracle.getAddress());
    });

    it("Should allow setting base price", async function () {
      const basePrice = ethers.parseUnits("0.01", 18); // $0.01
      await staking.setBasePrice(basePrice);
      expect(await staking.basePrice()).to.equal(basePrice);
    });

    it("Should fail with zero base price", async function () {
      await expect(staking.setBasePrice(0)).to.be.revertedWith("VIBStaking: invalid base price");
    });
  });

  describe("Dynamic APY Adjustment", function () {
    beforeEach(async function () {
      await staking.setPriceOracle(await priceOracle.getAddress());
      await staking.setBasePrice(ethers.parseUnits("0.01", 18)); // $0.01 base
    });

    it("Should return correct dynamic APY when price unchanged", async function () {
      // Set price to base price (no change)
      await priceOracle.setPrice(ethers.parseUnits("0.01", 18));

      const dynamicAPY = await staking.getDynamicAPY();
      expect(dynamicAPY).to.equal(BASE_APY);
    });

    it("Should increase APY when price drops 10%", async function () {
      // Set price to 90% of base (10% drop)
      await priceOracle.setPrice(ethers.parseUnits("0.009", 18));

      const dynamicAPY = await staking.getDynamicAPY();
      // Should be higher than base APY
      expect(dynamicAPY).to.be.gt(BASE_APY);
    });

    it("Should reach max APY when price drops 20%", async function () {
      // Set price to 80% of base (20% drop)
      await priceOracle.setPrice(ethers.parseUnits("0.008", 18));

      const dynamicAPY = await staking.getDynamicAPY();
      expect(dynamicAPY).to.equal(MAX_APY);
    });

    it("Should return base APY when price increases", async function () {
      // Set price to 110% of base (10% increase)
      await priceOracle.setPrice(ethers.parseUnits("0.011", 18));

      const dynamicAPY = await staking.getDynamicAPY();
      expect(dynamicAPY).to.equal(BASE_APY);
    });
  });

  describe("Update Price and Adjust APY", function () {
    beforeEach(async function () {
      await staking.setPriceOracle(await priceOracle.getAddress());
      await staking.setBasePrice(ethers.parseUnits("0.01", 18));
      await priceOracle.setPrice(ethers.parseUnits("0.008", 18)); // 20% drop

      // 安全修复: 调用者必须是活跃质押者才能更新价格
      // Owner stakes tokens to become an active staker
      const minStake = ethers.parseEther("100"); // Minimum stake amount
      await vibeToken.connect(owner).approve(await staking.getAddress(), minStake);
      await staking.connect(owner).stake(minStake, 0); // 0 = no lock
    });

    it("Should adjust APY after cooldown period", async function () {
      // First update
      await staking.updatePriceAndAdjustAPY();

      // APY should be adjusted
      expect(await staking.currentAPY()).to.equal(MAX_APY);
    });

    it("Should fail during cooldown period", async function () {
      await staking.updatePriceAndAdjustAPY();

      // Try to update again immediately
      await expect(staking.updatePriceAndAdjustAPY()).to.be.revertedWithCustomError(staking, "CooldownNotExpired");
    });

    it("Should allow update after cooldown", async function () {
      await staking.updatePriceAndAdjustAPY();

      // Wait for cooldown (1 hour)
      await time.increase(3600);

      // Should succeed now
      await expect(staking.updatePriceAndAdjustAPY()).to.not.be.reverted;
    });

    it("Should update price history", async function () {
      await staking.updatePriceAndAdjustAPY();

      // Price history is now stored in circular buffer
      const priceHistory = await staking.priceHistoryBuffer(0);
      expect(priceHistory).to.equal(ethers.parseUnits("0.008", 18));
    });

    it("Should emit DynamicAPYAdjusted event", async function () {
      await expect(staking.updatePriceAndAdjustAPY())
        .to.emit(staking, "DynamicAPYAdjusted")
        .withArgs(
          BASE_APY, // oldAPY
          MAX_APY,  // newAPY
          ethers.parseUnits("0.008", 18), // currentPrice
          ethers.parseUnits("0.01", 18),  // basePrice
          -20 // priceChangePercent (20% drop)
        );
    });
  });

  describe("Keeper Reward", function () {
    beforeEach(async function () {
      await staking.setPriceOracle(await priceOracle.getAddress());
      await staking.setBasePrice(ethers.parseUnits("0.01", 18));
      await priceOracle.setPrice(ethers.parseUnits("0.008", 18));

      // 安全修复: 调用者必须是活跃质押者才能更新价格
      // Owner stakes tokens to become an active staker
      const minStake = ethers.parseEther("100"); // Minimum stake amount
      await vibeToken.connect(owner).approve(await staking.getAddress(), minStake);
      await staking.connect(owner).stake(minStake, 0); // 0 = no lock
    });

    it("Should pay keeper reward on update", async function () {
      const balanceBefore = await vibeToken.balanceOf(owner.address);

      await staking.updatePriceAndAdjustAPY();

      const balanceAfter = await vibeToken.balanceOf(owner.address);
      const keeperReward = await staking.KEEPER_REWARD();

      expect(balanceAfter - balanceBefore).to.equal(keeperReward);
    });

    it("Should not pay keeper reward during cooldown", async function () {
      await staking.updatePriceAndAdjustAPY();

      // Wait less than keeper reward interval
      await time.increase(3600); // 1 hour cooldown, but 4 hour keeper interval

      const balanceBefore = await vibeToken.balanceOf(owner.address);

      await staking.updatePriceAndAdjustAPY();

      const balanceAfter = await vibeToken.balanceOf(owner.address);
      // Should not receive keeper reward (only 1 hour passed, need 4 hours)
      expect(balanceAfter).to.equal(balanceBefore);
    });

    it("Should pay keeper reward after interval", async function () {
      await staking.updatePriceAndAdjustAPY();

      // Wait for both cooldown and keeper reward interval
      await time.increase(4 * 3600); // 4 hours

      const balanceBefore = await vibeToken.balanceOf(owner.address);

      await staking.updatePriceAndAdjustAPY();

      const balanceAfter = await vibeToken.balanceOf(owner.address);
      const keeperReward = await staking.KEEPER_REWARD();

      expect(balanceAfter - balanceBefore).to.equal(keeperReward);
    });

    it("Should emit KeeperRewardPaid event", async function () {
      await expect(staking.updatePriceAndAdjustAPY())
        .to.emit(staking, "KeeperRewardPaid")
        .withArgs(owner.address, await staking.KEEPER_REWARD());
    });
  });
});

// Mock PriceOracle for testing
describe("MockPriceOracle", function () {
  it("Should be deployable", async function () {
    const MockPriceOracle = await ethers.getContractFactory(
      "src/mocks/MockContracts.sol:MockPriceOracle"
    );
    const oracle = await MockPriceOracle.deploy();
    await oracle.waitForDeployment();

    expect(await oracle.getAddress()).to.be.properAddress;
  });
});
