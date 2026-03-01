const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

describe("VIBStaking", function () {
  let vibeToken, stakingContract;
  let owner, addr1, addr2, addr3;

  const STAKE_AMOUNTS = [
    ethers.parseEther("100"),  // Bronze
    ethers.parseEther("1000"), // Silver
    ethers.parseEther("5000"), // Gold
    ethers.parseEther("10000"), // Platinum
  ];

  beforeEach(async function () {
    [owner, addr1, addr2, addr3] = await ethers.getSigners();

    // Deploy VIBEToken
    const VIBEToken = await ethers.getContractFactory("VIBEToken");
    vibeToken = await VIBEToken.deploy("VIBE Token", "VIBE", owner.address);
    await vibeToken.waitForDeployment();
    await vibeToken.mintTreasury();

    // Deploy VIBStaking
    const VIBStaking = await ethers.getContractFactory("VIBStaking");
    stakingContract = await VIBStaking.deploy(await vibeToken.getAddress());
    await stakingContract.waitForDeployment();

    // Set staking contract
    await vibeToken.setStakingContract(await stakingContract.getAddress());

    // Add rewards to staking contract (for payout)
    await vibeToken.transfer(await stakingContract.getAddress(), ethers.parseEther("1000000"));

    // Distribute tokens to test accounts
    await vibeToken.transfer(addr1.address, ethers.parseEther("100000"));
    await vibeToken.transfer(addr2.address, ethers.parseEther("100000"));
    await vibeToken.transfer(addr3.address, ethers.parseEther("100000"));
  });

  describe("Deployment", function () {
    it("Should set the right token", async function () {
      expect(await stakingContract.vibeToken()).to.equal(await vibeToken.getAddress());
    });

    it("Should set the right owner", async function () {
      expect(await stakingContract.owner()).to.equal(owner.address);
    });

    it("Should initialize with correct APY", async function () {
      expect(await stakingContract.currentAPY()).to.equal(3); // 3%
    });
  });

  describe("Staking", function () {
    it("Should stake with minimum amount", async function () {
      const amount = ethers.parseEther("100");
      await vibeToken.connect(addr1).approve(await stakingContract.getAddress(), amount);

      const tx = await stakingContract.connect(addr1).stake(amount, 0);
      await expect(tx).to.emit(stakingContract, "Staked");
    });

    it("Should fail to stake below minimum", async function () {
      const amount = ethers.parseEther("99");
      await vibeToken.connect(addr1).approve(await stakingContract.getAddress(), amount);

      await expect(stakingContract.connect(addr1).stake(amount, 0))
        .to.be.revertedWithCustomError(stakingContract, "StakeAmountBelowMinimum");
    });

    it("Should fail to stake without approval", async function () {
      const amount = ethers.parseEther("100");

      await expect(stakingContract.connect(addr1).stake(amount, 0))
        .to.be.reverted;
    });

    it("Should correctly identify Bronze tier", async function () {
      const amount = ethers.parseEther("500");
      await vibeToken.connect(addr1).approve(await stakingContract.getAddress(), amount);
      await stakingContract.connect(addr1).stake(amount, 0);

      const tier = await stakingContract.getUserTier(addr1.address);
      expect(tier).to.equal(0); // Bronze
    });

    it("Should correctly identify Silver tier", async function () {
      const amount = ethers.parseEther("2000");
      await vibeToken.connect(addr1).approve(await stakingContract.getAddress(), amount);
      await stakingContract.connect(addr1).stake(amount, 0);

      const tier = await stakingContract.getUserTier(addr1.address);
      expect(tier).to.equal(1); // Silver
    });

    it("Should correctly identify Gold tier", async function () {
      const amount = ethers.parseEther("7000");
      await vibeToken.connect(addr1).approve(await stakingContract.getAddress(), amount);
      await stakingContract.connect(addr1).stake(amount, 0);

      const tier = await stakingContract.getUserTier(addr1.address);
      expect(tier).to.equal(2); // Gold
    });

    it("Should correctly identify Platinum tier", async function () {
      const amount = ethers.parseEther("15000");
      await vibeToken.connect(addr1).approve(await stakingContract.getAddress(), amount);
      await stakingContract.connect(addr1).stake(amount, 0);

      const tier = await stakingContract.getUserTier(addr1.address);
      expect(tier).to.equal(3); // Platinum
    });

    it("Should set correct unlock time for 30-day lock", async function () {
      const amount = ethers.parseEther("1000");
      await vibeToken.connect(addr1).approve(await stakingContract.getAddress(), amount);

      const tx = await stakingContract.connect(addr1).stake(amount, 1);
      const stakeTime = await time.latest();
      const unlockTime = stakeTime + (30 * 24 * 60 * 60);

      const stakeInfo = await stakingContract.getStakeInfo(addr1.address);
      expect(stakeInfo.unlockTime).to.equal(unlockTime);
    });

    it("Should allow re-staking", async function () {
      const amount1 = ethers.parseEther("1000");
      const amount2 = ethers.parseEther("2000");

      await vibeToken.connect(addr1).approve(await stakingContract.getAddress(), amount1);
      await stakingContract.connect(addr1).stake(amount1, 0);

      await vibeToken.connect(addr1).approve(await stakingContract.getAddress(), amount2);
      await stakingContract.connect(addr1).stake(amount2, 0);

      const stakeInfo = await stakingContract.getStakeInfo(addr1.address);
      expect(stakeInfo.amount).to.equal(amount2);
    });
  });

  describe("Unstaking", function () {
    beforeEach(async function () {
      const amount = ethers.parseEther("1000");
      await vibeToken.connect(addr1).approve(await stakingContract.getAddress(), amount);
      await stakingContract.connect(addr1).stake(amount, 0);
    });

    it("Should unstake after lock period", async function () {
      const balanceBefore = await vibeToken.balanceOf(addr1.address);

      await stakingContract.connect(addr1).unstake();

      const balanceAfter = await vibeToken.balanceOf(addr1.address);
      expect(balanceAfter).to.be.greaterThan(balanceBefore);

      const stakeInfo = await stakingContract.getStakeInfo(addr1.address);
      expect(stakeInfo.isActive).to.be.false;
    });

    it("Should fail to unstake during lock period", async function () {
      // Stake with 30-day lock
      const amount = ethers.parseEther("1000");
      await vibeToken.connect(addr2).approve(await stakingContract.getAddress(), amount);
      await stakingContract.connect(addr2).stake(amount, 1);

      await expect(stakingContract.connect(addr2).unstake())
        .to.be.revertedWith("VIBStaking: lock period not expired");
    });

    it("Should fail to unstake if not staked", async function () {
      await expect(stakingContract.connect(addr2).unstake())
        .to.be.revertedWithCustomError(stakingContract, "UserNotStaked");
    });
  });

  describe("Rewards", function () {
    beforeEach(async function () {
      const amount = ethers.parseEther("1000");
      await vibeToken.connect(addr1).approve(await stakingContract.getAddress(), amount);
      await stakingContract.connect(addr1).stake(amount, 0);
    });

    it("Should claim rewards", async function () {
      // Fast-forward time
      await time.increase(365 * 24 * 60 * 60);

      const balanceBefore = await vibeToken.balanceOf(addr1.address);
      await stakingContract.connect(addr1).claimReward();

      const balanceAfter = await vibeToken.balanceOf(addr1.address);
      expect(balanceAfter).to.be.greaterThan(balanceBefore);
    });

    it("Should calculate pending rewards correctly", async function () {
      const pendingBefore = await stakingContract.getPendingReward(addr1.address);

      await time.increase(182 * 24 * 60 * 60); // Half a year

      const pendingAfter = await stakingContract.getPendingReward(addr1.address);
      expect(pendingAfter).to.be.greaterThan(pendingBefore);
    });

    it("Should reset rewards after claiming", async function () {
      await time.increase(365 * 24 * 60 * 60);

      await stakingContract.connect(addr1).claimReward();

      const pending = await stakingContract.getPendingReward(addr1.address);
      expect(pending).to.equal(0);
    });
  });

  describe("APY Management", function () {
    it("Should allow owner to set APY", async function () {
      await stakingContract.setAPY(5);
      expect(await stakingContract.currentAPY()).to.equal(5);
    });

    it("Should fail to set APY below minimum", async function () {
      await expect(stakingContract.setAPY(0))
        .to.be.revertedWith("VIBStaking: APY out of range");
    });

    it("Should fail to set APY above maximum", async function () {
      await expect(stakingContract.setAPY(11))
        .to.be.revertedWith("VIBStaking: APY out of range");
    });

    it("Should fail to set APY if not owner", async function () {
      await expect(stakingContract.connect(addr1).setAPY(5))
        .to.be.revertedWithCustomError(stakingContract, "OwnableUnauthorizedAccount");
    });
  });

  describe("Emergency Withdraw", function () {
    it("Should allow emergency withdrawal", async function () {
      const amount = ethers.parseEther("1000");
      await vibeToken.connect(addr1).approve(await stakingContract.getAddress(), amount);
      await stakingContract.connect(addr1).stake(amount, 1); // 30-day lock

      const balanceBefore = await vibeToken.balanceOf(addr1.address);

      await stakingContract.connect(addr1).emergencyWithdraw();

      const balanceAfter = await vibeToken.balanceOf(addr1.address);
      expect(balanceAfter - balanceBefore).to.equal(amount);

      const stakeInfo = await stakingContract.getStakeInfo(addr1.address);
      expect(stakeInfo.isActive).to.be.false;
    });

    it("Should forfeit rewards on emergency withdrawal", async function () {
      const amount = ethers.parseEther("1000");
      await vibeToken.connect(addr1).approve(await stakingContract.getAddress(), amount);
      await stakingContract.connect(addr1).stake(amount, 1);

      await time.increase(30 * 24 * 60 * 60);

      // Claim rewards first
      const balanceBefore = await vibeToken.balanceOf(addr1.address);
      await stakingContract.connect(addr1).claimReward();
      const balanceAfterClaim = await vibeToken.balanceOf(addr1.address);

      // Emergency withdraw
      await stakingContract.connect(addr1).emergencyWithdraw();

      // Try to claim again (should return 0)
      const pending = await stakingContract.getPendingReward(addr1.address);
      expect(pending).to.equal(0);
    });
  });

  describe("Staker Management", function () {
    it("Should track staker count", async function () {
      const amount = ethers.parseEther("1000");

      expect(await stakingContract.getStakerCount()).to.equal(0);

      await vibeToken.connect(addr1).approve(await stakingContract.getAddress(), amount);
      await stakingContract.connect(addr1).stake(amount, 0);

      expect(await stakingContract.getStakerCount()).to.equal(1);

      await vibeToken.connect(addr2).approve(await stakingContract.getAddress(), amount);
      await stakingContract.connect(addr2).stake(amount, 0);

      expect(await stakingContract.getStakerCount()).to.equal(2);
    });

    it("Should return stakers list", async function () {
      const amount = ethers.parseEther("1000");

      await vibeToken.connect(addr1).approve(await stakingContract.getAddress(), amount);
      await stakingContract.connect(addr1).stake(amount, 0);

      await vibeToken.connect(addr2).approve(await stakingContract.getAddress(), amount);
      await stakingContract.connect(addr2).stake(amount, 0);

      const stakers = await stakingContract.getStakers(0, 10);
      expect(stakers.length).to.equal(2);
      expect(stakers[0]).to.equal(addr1.address);
      expect(stakers[1]).to.equal(addr2.address);
    });
  });

  describe("Pause", function () {
    it("Should pause staking", async function () {
      await stakingContract.pause();

      const amount = ethers.parseEther("1000");
      await vibeToken.connect(addr1).approve(await stakingContract.getAddress(), amount);

      await expect(stakingContract.connect(addr1).stake(amount, 0))
        .to.be.revertedWithCustomError(stakingContract, "EnforcedPause");
    });

    it("Should unpause staking", async function () {
      await stakingContract.pause();
      await stakingContract.unpause();

      const amount = ethers.parseEther("1000");
      await vibeToken.connect(addr1).approve(await stakingContract.getAddress(), amount);

      await expect(stakingContract.connect(addr1).stake(amount, 0))
        .not.to.be.reverted;
    });
  });
});
