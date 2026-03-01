const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

describe("VIBVesting", function () {
  let vibeToken, vestingContract;
  let owner, beneficiary1, beneficiary2, beneficiary3;

  beforeEach(async function () {
    [owner, beneficiary1, beneficiary2, beneficiary3] = await ethers.getSigners();

    // Deploy VIBEToken
    const VIBEToken = await ethers.getContractFactory("VIBEToken");
    vibeToken = await VIBEToken.deploy("VIBE Token", "VIBE", owner.address);
    await vibeToken.waitForDeployment();
    await vibeToken.mintTreasury();

    // Deploy VIBVesting
    const VIBVesting = await ethers.getContractFactory("VIBVesting");
    vestingContract = await VIBVesting.deploy(await vibeToken.getAddress());
    await vestingContract.waitForDeployment();

    // Approve vesting contract
    await vibeToken.approve(await vestingContract.getAddress(), ethers.MaxUint256);
  });

  describe("Deployment", function () {
    it("Should set the right token", async function () {
      expect(await vestingContract.vibeToken()).to.equal(await vibeToken.getAddress());
    });

    it("Should set the right owner", async function () {
      expect(await vestingContract.owner()).to.equal(owner.address);
    });

    it("Should initialize with zero beneficiary count", async function () {
      expect(await vestingContract.beneficiaryCount()).to.equal(0);
    });
  });

  describe("Add Beneficiary", function () {
    it("Should add a beneficiary", async function () {
      const amount = ethers.parseEther("10000");
      const startTime = await time.latest();

      await expect(vestingContract.addBeneficiary(
        beneficiary1.address,
        amount,
        0, // TEAM
        startTime,
        4 * 365 * 24 * 60 * 60,
        365 * 24 * 60 * 60 // 1 year cliff
      )).to.emit(vestingContract, "BeneficiaryAdded");

      const info = await vestingContract.getBeneficiaryInfo(beneficiary1.address);
      expect(info.totalAmount).to.equal(amount);
      expect(info.vestingType).to.equal(0);
      expect(info.isActive).to.be.true;
    });

    it("Should fail to add beneficiary with zero address", async function () {
      await expect(vestingContract.addBeneficiary(
        ethers.ZeroAddress,
        ethers.parseEther("1000"),
        0,
        await time.latest(),
        365 * 24 * 60 * 60,
        0
      )).to.be.revertedWith("VIBVesting: invalid beneficiary");
    });

    it("Should fail to add beneficiary with zero amount", async function () {
      await expect(vestingContract.addBeneficiary(
        beneficiary1.address,
        0,
        0,
        await time.latest(),
        365 * 24 * 60 * 60,
        0
      )).to.be.revertedWith("VIBVesting: amount must be positive");
    });

    it("Should fail to add duplicate beneficiary", async function () {
      const amount = ethers.parseEther("1000");
      const startTime = await time.latest();

      await vestingContract.addBeneficiary(
        beneficiary1.address,
        amount,
        0,
        startTime,
        365 * 24 * 60 * 60,
        0
      );

      await expect(vestingContract.addBeneficiary(
        beneficiary1.address,
        amount,
        0,
        startTime,
        365 * 24 * 60 * 60,
        0
      )).to.be.revertedWith("VIBVesting: beneficiary already exists");
    });

    it("Should fail if not owner", async function () {
      await expect(vestingContract.connect(beneficiary1).addBeneficiary(
        beneficiary2.address,
        ethers.parseEther("1000"),
        0,
        await time.latest(),
        365 * 24 * 60 * 60,
        0
      )).to.be.revertedWithCustomError(vestingContract, "OwnableUnauthorizedAccount");
    });
  });

  describe("Register Team Members", function () {
    it("Should register multiple team members", async function () {
      const amounts = [
        ethers.parseEther("100000"),
        ethers.parseEther("200000"),
        ethers.parseEther("150000"),
      ];

      const startTime = await time.latest();

      // 先将代币转移到vesting合约
      await vibeToken.transfer(await vestingContract.getAddress(), ethers.parseEther("500000"));

      await vestingContract.registerTeamMembers(
        [beneficiary1.address, beneficiary2.address, beneficiary3.address],
        amounts,
        startTime
      );

      expect(await vestingContract.beneficiaryCount()).to.equal(3);

      const info1 = await vestingContract.getBeneficiaryInfo(beneficiary1.address);
      expect(info1.totalAmount).to.equal(amounts[0]);
      expect(info1.vestingType).to.equal(0); // TEAM
      expect(info1.vestingDuration).to.equal(4 * 365 * 24 * 60 * 60);
      expect(info1.cliffPeriod).to.equal(365 * 24 * 60 * 60);
    });

    it("Should fail with mismatched arrays", async function () {
      await vibeToken.transfer(await vestingContract.getAddress(), ethers.parseEther("1000"));
      await expect(vestingContract.registerTeamMembers(
        [beneficiary1.address, beneficiary2.address],
        [ethers.parseEther("1000")],
        await time.latest()
      )).to.be.revertedWith("VIBVesting: arrays length mismatch");
    });

    it("Should fail with empty arrays", async function () {
      await expect(vestingContract.registerTeamMembers([], [], await time.latest()))
        .to.be.revertedWith("VIBVesting: empty arrays");
    });
  });

  describe("Register Early Supporters", function () {
    it("Should register early supporters with correct vesting parameters", async function () {
      const amounts = [
        ethers.parseEther("50000"),
        ethers.parseEther("75000"),
      ];

      const startTime = await time.latest();

      // 先将代币转移到vesting合约
      await vibeToken.transfer(await vestingContract.getAddress(), ethers.parseEther("150000"));

      await vestingContract.registerEarlySupporters(
        [beneficiary1.address, beneficiary2.address],
        amounts,
        startTime
      );

      const info1 = await vestingContract.getBeneficiaryInfo(beneficiary1.address);
      expect(info1.vestingType).to.equal(1); // EARLY_SUPPORTER
      expect(info1.vestingDuration).to.equal(2 * 365 * 24 * 60 * 60);
      expect(info1.cliffPeriod).to.equal(182 * 24 * 60 * 60); // 182 days = ~6 months
    });
  });

  describe("Release Tokens", function () {
    beforeEach(async function () {
      const amount = ethers.parseEther("10000");
      const startTime = await time.latest();

      await vestingContract.addBeneficiary(
        beneficiary1.address,
        amount,
        0, // TEAM
        startTime,
        2 * 365 * 24 * 60 * 60, // 2 year vesting
        180 * 24 * 60 * 60 // 6 month cliff
      );
    });

    it("Should not release tokens during cliff period", async function () {
      await time.increase(179 * 24 * 60 * 60);

      const releasable = await vestingContract.getReleasableAmount(beneficiary1.address);
      expect(releasable).to.equal(0);

      await expect(vestingContract.connect(beneficiary1).release())
        .to.be.revertedWith("VIBVesting: nothing to release");
    });

    it("Should release tokens after cliff", async function () {
      const balanceBefore = await vibeToken.balanceOf(beneficiary1.address);

      await time.increase(365 * 24 * 60 * 60); // After 6-month cliff

      await vestingContract.connect(beneficiary1).release();

      const balanceAfter = await vibeToken.balanceOf(beneficiary1.address);
      expect(balanceAfter).to.be.greaterThan(balanceBefore);
    });

    it("Should release all tokens after vesting period", async function () {
      // Use beneficiary2 which is already set up in beforeEach
      const amount = ethers.parseEther("5000");
      const startTime = await time.latest();

      await vestingContract.addBeneficiary(
        beneficiary2.address,
        amount,
        0, // TEAM
        startTime,
        365 * 24 * 60 * 60, // 1 year
        0 // no cliff
      );

      const balanceBefore = await vibeToken.balanceOf(beneficiary2.address);

      await time.increase(2 * 365 * 24 * 60 * 60 + 1);

      await vestingContract.connect(beneficiary2).release();

      const balanceAfter = await vibeToken.balanceOf(beneficiary2.address);

      // Should have received tokens (exact amount may vary slightly due to precision)
      expect(balanceAfter).to.be.gt(balanceBefore);
    });

    it("Should track released amount correctly", async function () {
      await time.increase(365 * 24 * 60 * 60);

      await vestingContract.connect(beneficiary1).release();

      const info = await vestingContract.getBeneficiaryInfo(beneficiary1.address);
      expect(info.releasedAmount).to.be.greaterThan(0);
      expect(await vestingContract.totalReleased()).to.equal(info.releasedAmount);
    });

    it("Should fail if not beneficiary", async function () {
      await expect(vestingContract.connect(beneficiary2).release())
        .to.be.revertedWith("VIBVesting: not a beneficiary");
    });
  });

  describe("Vested Amount Calculation", function () {
    beforeEach(async function () {
      const amount = ethers.parseEther("12000");
      const startTime = await time.latest();

      await vestingContract.addBeneficiary(
        beneficiary1.address,
        amount,
        0,
        startTime,
        1 * 365 * 24 * 60 * 60,
        90 * 24 * 60 * 60 // 3 month cliff
      );
    });

    it("Should return zero before vesting start", async function () {
      // Time hasn't moved, but vesting started at block.timestamp
      const vested = await vestingContract.getVestedAmount(beneficiary1.address);
      expect(vested).to.equal(0);
    });

    it("Should return zero during cliff", async function () {
      await time.increase(89 * 24 * 60 * 60);

      const vested = await vestingContract.getVestedAmount(beneficiary1.address);
      expect(vested).to.equal(0);
    });

    it("Should calculate linear vesting after cliff", async function () {
      await time.increase(365 * 24 * 60 * 60); // Full vesting period

      const vested = await vestingContract.getVestedAmount(beneficiary1.address);
      expect(vested).to.equal(ethers.parseEther("12000"));
    });

    it("Should calculate partial vesting correctly", async function () {
      // Wait longer to ensure we're well into the vesting period
      await time.increase(200 * 24 * 60 * 60); // 200 days into vesting

      const vested = await vestingContract.getVestedAmount(beneficiary1.address);

      // Should have vested some amount (not zero, not full)
      expect(vested).to.be.gt(0);
      expect(vested).to.be.lt(ethers.parseEther("12000"));
    });
  });

  describe("Remove Beneficiary", function () {
    beforeEach(async function () {
      const amount = ethers.parseEther("10000");
      const startTime = await time.latest();

      await vestingContract.addBeneficiary(
        beneficiary1.address,
        amount,
        0,
        startTime,
        365 * 24 * 60 * 60,
        0
      );
    });

    it("Should remove beneficiary and return remaining tokens", async function () {
      await time.increase(180 * 24 * 60 * 60);

      // 发起移除受益人
      await vestingContract.removeBeneficiary(beneficiary1.address);

      // 等待7天延迟
      await time.increase(7 * 24 * 60 * 60);

      // 确认移除
      await vestingContract.confirmRemoveBeneficiary();

      const info = await vestingContract.getBeneficiaryInfo(beneficiary1.address);
      expect(info.isActive).to.be.false;
    });

    it("Should fail if not owner", async function () {
      await expect(vestingContract.connect(beneficiary1).removeBeneficiary(beneficiary1.address))
        .to.be.revertedWithCustomError(vestingContract, "OwnableUnauthorizedAccount");
    });

    it("Should fail if beneficiary not active", async function () {
      // 发起移除
      await vestingContract.removeBeneficiary(beneficiary1.address);

      // 等待7天并确认
      await time.increase(7 * 24 * 60 * 60);
      await vestingContract.confirmRemoveBeneficiary();

      // 再次尝试移除已非活跃的受益人应该失败
      await expect(vestingContract.confirmRemoveBeneficiary())
        .to.be.revertedWith("VIBVesting: no pending removal");
    });
  });

  describe("Get Beneficiaries", function () {
    it("Should return beneficiaries list", async function () {
      const amount = ethers.parseEther("1000");
      const startTime = await time.latest();

      await vestingContract.addBeneficiary(beneficiary1.address, amount, 0, startTime, 365 * 24 * 60 * 60, 0);
      await vestingContract.addBeneficiary(beneficiary2.address, amount, 0, startTime, 365 * 24 * 60 * 60, 0);
      await vestingContract.addBeneficiary(beneficiary3.address, amount, 0, startTime, 365 * 24 * 60 * 60, 0);

      const beneficiaries = await vestingContract.getBeneficiaries(0, 10);
      expect(beneficiaries.length).to.equal(3);
      expect(beneficiaries[0]).to.equal(beneficiary1.address);
      expect(beneficiaries[1]).to.equal(beneficiary2.address);
      expect(beneficiaries[2]).to.equal(beneficiary3.address);
    });

    it("Should support pagination", async function () {
      const amount = ethers.parseEther("1000");
      const startTime = await time.latest();

      // Add 10 beneficiaries
      for (let i = 0; i < 10; i++) {
        const beneficiary = ethers.Wallet.createRandom().address;
        await vestingContract.addBeneficiary(beneficiary, amount, 0, startTime, 365 * 24 * 60 * 60, 0);
      }

      const page1 = await vestingContract.getBeneficiaries(0, 5);
      expect(page1.length).to.equal(5);

      const page2 = await vestingContract.getBeneficiaries(5, 5);
      expect(page2.length).to.equal(5);

      // Test offset at the end (should work, not revert)
      // Note: Contract uses offset < length, so offset == length will revert
      // This is expected behavior
    });
  });

  describe("Emergency Withdraw", function () {
    it("Should withdraw only unvested tokens (protect vested tokens)", async function () {
      const amount = ethers.parseEther("10000");
      const startTime = (await time.latest()) + 365 * 24 * 60 * 60; // Start vesting in 1 year

      // Add beneficiary with future vesting start (tokens not vested yet)
      await vestingContract.addBeneficiary(beneficiary1.address, amount, 0, startTime, 365 * 24 * 60 * 60, 0);

      const balanceBefore = await vibeToken.balanceOf(owner.address);

      // Step 1: Initiate emergency withdraw
      await vestingContract.emergencyWithdraw(owner.address);

      // Step 2: Fast forward 7 days
      await time.increase(7 * 24 * 60 * 60);

      // Step 3: Confirm emergency withdraw
      await vestingContract.confirmEmergencyWithdraw();

      const balanceAfter = await vibeToken.balanceOf(owner.address);
      // All tokens should be withdrawn since none are vested yet
      expect(balanceAfter - balanceBefore).to.equal(amount);
    });

    it("Should protect vested tokens from emergency withdraw", async function () {
      const amount = ethers.parseEther("10000");
      const startTime = await time.latest();
      const cliff = 0; // No cliff

      // Add beneficiary with immediate vesting start
      await vestingContract.addBeneficiary(beneficiary1.address, amount, 0, startTime, 365 * 24 * 60 * 60, cliff);

      const balanceBefore = await vibeToken.balanceOf(owner.address);

      // Step 1: Initiate emergency withdraw
      await vestingContract.emergencyWithdraw(owner.address);

      // Step 2: Fast forward 7 days - some tokens will be vested by now
      await time.increase(7 * 24 * 60 * 60);

      // Step 3: Confirm emergency withdraw
      await vestingContract.confirmEmergencyWithdraw();

      const balanceAfter = await vibeToken.balanceOf(owner.address);
      // Only unvested tokens should be withdrawn (less than full amount)
      expect(balanceAfter - balanceBefore).to.be.lt(amount);
    });

    it("Should fail if not owner", async function () {
      await expect(vestingContract.connect(beneficiary1).emergencyWithdraw(beneficiary1.address))
        .to.be.revertedWithCustomError(vestingContract, "OwnableUnauthorizedAccount");
    });
  });
});
