import { expect } from "chai";
import { ethers } from "hardhat";
import { VIBStaking, VIBEToken } from "../../typechain-types";
import { Signer } from "ethers";
import { parseEther } from "ethers/lib/utils";
import { getSigners, expectEvent, expectRevertCustomError, advanceTime } from "../utils/fixtures";
import { time } from "../utils/helpers";
import {
  MIN_STAKE_AMOUNT,
  LOCK_DURATIONS,
  LOCK_BONUS_RATES,
  TIER_THRESHOLDS,
  TIER_BONUS_RATES,
  SECONDS_PER_DAY,
  ERROR_MESSAGES
} from "../utils/constants";

describe("VIBStaking", function () {
  let vibeToken: VIBEToken;
  let vibStaking: VIBStaking;
  let signers: any;
  let owner: Signer;
  let user1: Signer;
  let user2: Signer;

  const STAKING_REWARDS_POOL = parseEther("100000000");
  const BASE_APR = 10000; // 100% (scaled by 10000)

  beforeEach(async function () {
    signers = await getSigners();
    owner = signers.owner;
    user1 = signers.user1;
    user2 = signers.user2;

    // Deploy VIBE Token
    const VIBEToken = await ethers.getContractFactory("VIBEToken");
    vibeToken = (await VIBEToken.deploy(await owner.getAddress())) as VIBEToken;
    await vibeToken.deployed();

    // Deploy VIBStaking
    const VIBStaking = await ethers.getContractFactory("VIBStaking");
    vibStaking = (await VIBStaking.deploy(
      vibeToken.address,
      vibeToken.address,
      BASE_APR,
      await owner.getAddress()
    )) as VIBStaking;
    await vibStaking.deployed();

    // Grant minter role to staking contract
    await vibeToken.grantRole(await vibeToken.MINTER_ROLE(), vibStaking.address);

    // Mint rewards to staking contract
    await vibeToken.mint(vibStaking.address, STAKING_REWARDS_POOL);

    // Transfer tokens to test users
    await vibeToken.transfer(await user1.getAddress(), parseEther("10000000"));
    await vibeToken.transfer(await user2.getAddress(), parseEther("10000000"));
  });

  describe("Deployment", function () {
    it("Should set the correct staking token", async function () {
      expect(await vibStaking.stakingToken()).to.equal(vibeToken.address);
    });

    it("Should set the correct rewards token", async function () {
      expect(await vibStaking.rewardsToken()).to.equal(vibeToken.address);
    });

    it("Should set the correct base APR", async function () {
      expect(await vibStaking.baseAPR()).to.equal(BASE_APR);
    });

    it("Should set the correct admin", async function () {
      expect(await vibStaking.admin()).to.equal(await owner.getAddress());
    });

    it("Should initialize total staked as zero", async function () {
      expect(await vibStaking.totalStaked()).to.equal(0);
    });

    it("Should initialize last update timestamp", async function () {
      const lastUpdate = await vibStaking.lastUpdateTimestamp();
      expect(lastUpdate.gt(0)).to.be.true;
    });
  });

  describe("Staking", function () {
    const stakeAmount = parseEther("1000");

    it("Should stake tokens successfully", async function () {
      await vibeToken.connect(user1).approve(vibStaking.address, stakeAmount);
      await vibStaking.connect(user1).stake(stakeAmount, LOCK_DURATIONS.NONE);

      const stakeInfo = await vibStaking.stakes(await user1.getAddress());
      expect(stakeInfo.amount).to.equal(stakeAmount);
      expect(stakeInfo.lockDuration).to.equal(LOCK_DURATIONS.NONE);
      expect(await vibStaking.totalStaked()).to.equal(stakeAmount);
    });

    it("Should emit Staked event", async function () {
      await vibeToken.connect(user1).approve(vibStaking.address, stakeAmount);

      await expectEvent(
        vibStaking.connect(user1).stake(stakeAmount, LOCK_DURATIONS.NONE),
        vibStaking,
        "Staked",
        [await user1.getAddress(), stakeAmount, LOCK_DURATIONS.NONE]
      );
    });

    it("Should stake with lock duration", async function () {
      await vibeToken.connect(user1).approve(vibStaking.address, stakeAmount);
      await vibStaking.connect(user1).stake(stakeAmount, LOCK_DURATIONS.TWELVE_MONTHS);

      const stakeInfo = await vibStaking.stakes(await user1.getAddress());
      expect(stakeInfo.lockDuration).to.equal(LOCK_DURATIONS.TWELVE_MONTHS);
      expect(stakeInfo.lockEndTimestamp.gt(await time.latest())).to.be.true;
    });

    it("Should fail when staking zero amount", async function () {
      await vibeToken.connect(user1).approve(vibStaking.address, stakeAmount);

      await expectRevertCustomError(
        vibStaking.connect(user1).stake(0, LOCK_DURATIONS.NONE),
        vibStaking,
        "InvalidAmount"
      );
    });

    it("Should fail when staking below minimum", async function () {
      const belowMin = MIN_STAKE_AMOUNT.sub(1);
      await vibeToken.connect(user1).approve(vibStaking.address, belowMin);

      await expectRevertCustomError(
        vibStaking.connect(user1).stake(belowMin, LOCK_DURATIONS.NONE),
        vibStaking,
        "InvalidAmount"
      );
    });

    it("Should fail when staking without approval", async function () {
      await expectRevertCustomError(
        vibStaking.connect(user1).stake(stakeAmount, LOCK_DURATIONS.NONE),
        vibStaking,
        "ERC20InsufficientAllowance"
      );
    });

    it("Should fail when already staked", async function () {
      await vibeToken.connect(user1).approve(vibStaking.address, stakeAmount);
      await vibStaking.connect(user1).stake(stakeAmount, LOCK_DURATIONS.NONE);

      await expectRevertCustomError(
        vibStaking.connect(user1).stake(stakeAmount, LOCK_DURATIONS.NONE),
        vibStaking,
        "AlreadyStaked"
      );
    });

    it("Should update tier based on stake amount", async function () {
      const bronzeAmount = TIER_THRESHOLDS.BRONZE;
      await vibeToken.connect(user1).approve(vibStaking.address, bronzeAmount);
      await vibStaking.connect(user1).stake(bronzeAmount, LOCK_DURATIONS.NONE);

      const stakeInfo = await vibStaking.stakes(await user1.getAddress());
      expect(stakeInfo.tier).to.equal(0); // Bronze = 0
    });

    it("Should update tier to Silver", async function () {
      const silverAmount = TIER_THRESHOLDS.SILVER;
      await vibeToken.connect(user1).approve(vibStaking.address, silverAmount);
      await vibStaking.connect(user1).stake(silverAmount, LOCK_DURATIONS.NONE);

      const stakeInfo = await vibStaking.stakes(await user1.getAddress());
      expect(stakeInfo.tier).to.equal(1); // Silver = 1
    });

    it("Should update tier to Gold", async function () {
      const goldAmount = TIER_THRESHOLDS.GOLD;
      await vibeToken.connect(user1).approve(vibStaking.address, goldAmount);
      await vibStaking.connect(user1).stake(goldAmount, LOCK_DURATIONS.NONE);

      const stakeInfo = await vibStaking.stakes(await user1.getAddress());
      expect(stakeInfo.tier).to.equal(2); // Gold = 2
    });

    it("Should update tier to Platinum", async function () {
      const platinumAmount = TIER_THRESHOLDS.PLATINUM;
      await vibeToken.connect(user1).approve(vibStaking.address, platinumAmount);
      await vibStaking.connect(user1).stake(platinumAmount, LOCK_DURATIONS.NONE);

      const stakeInfo = await vibStaking.stakes(await user1.getAddress());
      expect(stakeInfo.tier).to.equal(3); // Platinum = 3
    });

    it("Should update tier to Diamond", async function () {
      const diamondAmount = TIER_THRESHOLDS.DIAMOND;
      await vibeToken.connect(user1).approve(vibStaking.address, diamondAmount);
      await vibStaking.connect(user1).stake(diamondAmount, LOCK_DURATIONS.NONE);

      const stakeInfo = await vibStaking.stakes(await user1.getAddress());
      expect(stakeInfo.tier).to.equal(4); // Diamond = 4
    });
  });

  describe("Reward Calculation", function () {
    const stakeAmount = parseEther("10000");

    beforeEach(async function () {
      await vibeToken.connect(user1).approve(vibStaking.address, stakeAmount);
      await vibStaking.connect(user1).stake(stakeAmount, LOCK_DURATIONS.NONE);
    });

    it("Should calculate rewards correctly after one day", async function () {
      await advanceTime(SECONDS_PER_DAY);

      const rewards = await vibStaking.calculateRewards(await user1.getAddress());
      const expectedRewards = stakeAmount.mul(BASE_APR).mul(SECONDS_PER_DAY).div(10000).div(31536000);

      // Allow small difference due to timing
      expect(rewards.sub(expectedRewards).abs().lt(parseEther("10"))).to.be.true;
    });

    it("Should calculate rewards correctly after one month", async function () {
      await advanceTime(30 * SECONDS_PER_DAY);

      const rewards = await vibStaking.calculateRewards(await user1.getAddress());
      expect(rewards.gt(0)).to.be.true;
    });

    it("Should calculate rewards correctly with lock bonus", async function () {
      // Create new stake with lock
      await vibeToken.connect(user2).approve(vibStaking.address, stakeAmount);
      await vibStaking.connect(user2).stake(stakeAmount, LOCK_DURATIONS.TWELVE_MONTHS);

      await advanceTime(30 * SECONDS_PER_DAY);

      const rewardsWithLock = await vibStaking.calculateRewards(await user2.getAddress());
      const rewardsWithoutLock = await vibStaking.calculateRewards(await user1.getAddress());

      expect(rewardsWithLock.gt(rewardsWithoutLock)).to.be.true;
    });

    it("Should calculate rewards correctly with tier bonus", async function () {
      // Diamond tier stake
      const diamondAmount = TIER_THRESHOLDS.DIAMOND;
      await vibeToken.connect(user2).approve(vibStaking.address, diamondAmount);
      await vibStaking.connect(user2).stake(diamondAmount, LOCK_DURATIONS.NONE);

      await advanceTime(30 * SECONDS_PER_DAY);

      const rewardsDiamond = await vibStaking.calculateRewards(await user2.getAddress());
      const rewardsSilver = await vibStaking.calculateRewards(await user1.getAddress());

      // Diamond should earn more per unit staked
      const rewardsPerUnitDiamond = rewardsDiamond.mul(stakeAmount).div(diamondAmount);
      expect(rewardsPerUnitDiamond.gt(rewardsSilver)).to.be.true;
    });

    it("Should return zero rewards immediately after staking", async function () {
      const rewards = await vibStaking.calculateRewards(await user2.getAddress());
      expect(rewards).to.equal(0);
    });
  });

  describe("Unstaking", function () {
    const stakeAmount = parseEther("1000");

    beforeEach(async function () {
      await vibeToken.connect(user1).approve(vibStaking.address, stakeAmount);
      await vibStaking.connect(user1).stake(stakeAmount, LOCK_DURATIONS.NONE);
      await advanceTime(30 * SECONDS_PER_DAY);
    });

    it("Should unstake tokens successfully", async function () {
      await vibStaking.connect(user1).unstake(stakeAmount);

      const stakeInfo = await vibStaking.stakes(await user1.getAddress());
      expect(stakeInfo.amount).to.equal(0);
    });

    it("Should emit Unstaked event", async function () {
      await expectEvent(
        vibStaking.connect(user1).unstake(stakeAmount),
        vibStaking,
        "Unstaked",
        [await user1.getAddress(), stakeAmount]
      );
    });

    it("Should transfer tokens back to user", async function () {
      const balanceBefore = await vibeToken.balanceOf(await user1.getAddress());
      await vibStaking.connect(user1).unstake(stakeAmount);
      const balanceAfter = await vibeToken.balanceOf(await user1.getAddress());

      expect(balanceAfter.sub(balanceBefore)).to.equal(stakeAmount);
    });

    it("Should claim rewards on unstake", async function () {
      const balanceBefore = await vibeToken.balanceOf(await user1.getAddress());
      await vibStaking.connect(user1).unstake(stakeAmount);
      const balanceAfter = await vibeToken.balanceOf(await user1.getAddress());

      expect(balanceAfter.sub(balanceBefore).gt(stakeAmount)).to.be.true;
    });

    it("Should fail when unstaking more than staked", async function () {
      const excessAmount = stakeAmount.add(1);

      await expectRevertCustomError(
        vibStaking.connect(user1).unstake(excessAmount),
        vibStaking,
        "InvalidAmount"
      );
    });

    it("Should fail when not staked", async function () {
      await expectRevertCustomError(
        vibStaking.connect(user2).unstake(stakeAmount),
        vibStaking,
        "NotStaked"
      );
    });

    it("Should fail when unstaking during lock period", async function () {
      await vibeToken.connect(user2).approve(vibStaking.address, stakeAmount);
      await vibStaking.connect(user2).stake(stakeAmount, LOCK_DURATIONS.TWELVE_MONTHS);

      await expectRevertCustomError(
        vibStaking.connect(user2).unstake(stakeAmount),
        vibStaking,
        "LockNotExpired"
      );
    });

    it("Should allow unstaking after lock expires", async function () {
      await vibeToken.connect(user2).approve(vibStaking.address, stakeAmount);
      await vibStaking.connect(user2).stake(stakeAmount, LOCK_DURATIONS.ONE_MONTH);

      await advanceTime(LOCK_DURATIONS.ONE_MONTH + SECONDS_PER_DAY);

      await vibStaking.connect(user2).unstake(stakeAmount);

      const stakeInfo = await vibStaking.stakes(await user2.getAddress());
      expect(stakeInfo.amount).to.equal(0);
    });

    it("Should decrease total staked", async function () {
      const totalBefore = await vibStaking.totalStaked();
      await vibStaking.connect(user1).unstake(stakeAmount);
      const totalAfter = await vibStaking.totalStaked();

      expect(totalAfter).to.equal(totalBefore.sub(stakeAmount));
    });
  });

  describe("Claiming Rewards", function () {
    const stakeAmount = parseEther("10000");

    beforeEach(async function () {
      await vibeToken.connect(user1).approve(vibStaking.address, stakeAmount);
      await vibStaking.connect(user1).stake(stakeAmount, LOCK_DURATIONS.NONE);
      await advanceTime(30 * SECONDS_PER_DAY);
    });

    it("Should claim rewards successfully", async function () {
      const balanceBefore = await vibeToken.balanceOf(await user1.getAddress());
      await vibStaking.connect(user1).claimRewards();
      const balanceAfter = await vibeToken.balanceOf(await user1.getAddress());

      expect(balanceAfter.sub(balanceBefore).gt(0)).to.be.true;
    });

    it("Should emit RewardsClaimed event", async function () {
      const tx = await vibStaking.connect(user1).claimRewards();
      const receipt = await tx.wait();
      const event = receipt.events?.find((e: any) => e.event === "RewardsClaimed");

      expect(event).to.not.be.undefined;
      expect(event.args.user).to.equal(await user1.getAddress());
      expect(event.args.amount.gt(0)).to.be.true;
    });

    it("Should reset user rewards after claim", async function () {
      await vibStaking.connect(user1).claimRewards();

      const rewards = await vibStaking.calculateRewards(await user1.getAddress());
      expect(rewards).to.equal(0);
    });

    it("Should fail when not staked", async function () {
      await expectRevertCustomError(
        vibStaking.connect(user2).claimRewards(),
        vibStaking,
        "NotStaked"
      );
    });

    it("Should allow claiming multiple times", async function () {
      const balanceBefore = await vibeToken.balanceOf(await user1.getAddress());

      await vibStaking.connect(user1).claimRewards();
      await advanceTime(30 * SECONDS_PER_DAY);
      await vibStaking.connect(user1).claimRewards();

      const balanceAfter = await vibeToken.balanceOf(await user1.getAddress());
      expect(balanceAfter.sub(balanceBefore).gt(0)).to.be.true;
    });
  });

  describe("Lock Bonus", function () {
    const stakeAmount = parseEther("10000");

    it("Should apply 0% bonus for no lock", async function () {
      await vibeToken.connect(user1).approve(vibStaking.address, stakeAmount);
      await vibStaking.connect(user1).stake(stakeAmount, LOCK_DURATIONS.NONE);

      const stakeInfo = await vibStaking.stakes(await user1.getAddress());
      expect(stakeInfo.lockBonusRate).to.equal(LOCK_BONUS_RATES.NONE);
    });

    it("Should apply 5% bonus for 1 month lock", async function () {
      await vibeToken.connect(user1).approve(vibStaking.address, stakeAmount);
      await vibStaking.connect(user1).stake(stakeAmount, LOCK_DURATIONS.ONE_MONTH);

      const stakeInfo = await vibStaking.stakes(await user1.getAddress());
      expect(stakeInfo.lockBonusRate).to.equal(LOCK_BONUS_RATES.ONE_MONTH);
    });

    it("Should apply 15% bonus for 3 month lock", async function () {
      await vibeToken.connect(user1).approve(vibStaking.address, stakeAmount);
      await vibStaking.connect(user1).stake(stakeAmount, LOCK_DURATIONS.THREE_MONTHS);

      const stakeInfo = await vibStaking.stakes(await user1.getAddress());
      expect(stakeInfo.lockBonusRate).to.equal(LOCK_BONUS_RATES.THREE_MONTHS);
    });

    it("Should apply 35% bonus for 6 month lock", async function () {
      await vibeToken.connect(user1).approve(vibStaking.address, stakeAmount);
      await vibStaking.connect(user1).stake(stakeAmount, LOCK_DURATIONS.SIX_MONTHS);

      const stakeInfo = await vibStaking.stakes(await user1.getAddress());
      expect(stakeInfo.lockBonusRate).to.equal(LOCK_BONUS_RATES.SIX_MONTHS);
    });

    it("Should apply 80% bonus for 12 month lock", async function () {
      await vibeToken.connect(user1).approve(vibStaking.address, stakeAmount);
      await vibStaking.connect(user1).stake(stakeAmount, LOCK_DURATIONS.TWELVE_MONTHS);

      const stakeInfo = await vibStaking.stakes(await user1.getAddress());
      expect(stakeInfo.lockBonusRate).to.equal(LOCK_BONUS_RATES.TWELVE_MONTHS);
    });
  });

  describe("Admin Functions", function () {
    const newAPR = 15000; // 150%

    it("Should allow admin to update APR", async function () {
      await vibStaking.connect(owner).setBaseAPR(newAPR);

      expect(await vibStaking.baseAPR()).to.equal(newAPR);
    });

    it("Should emit APRUpdated event", async function () {
      await expectEvent(
        vibStaking.connect(owner).setBaseAPR(newAPR),
        vibStaking,
        "APRUpdated",
        [BASE_APR, newAPR]
      );
    });

    it("Should fail when non-admin tries to update APR", async function () {
      await expectRevertCustomError(
        vibStaking.connect(user1).setBaseAPR(newAPR),
        vibStaking,
        "Unauthorized"
      );
    });

    it("Should allow admin to transfer rewards", async function () {
      const transferAmount = parseEther("1000000");
      await vibStaking.connect(owner).transferRewards(await user1.getAddress(), transferAmount);

      expect(await vibeToken.balanceOf(await user1.getAddress())).to.equal(transferAmount);
    });

    it("Should fail when non-admin tries to transfer rewards", async function () {
      const transferAmount = parseEther("1000000");

      await expectRevertCustomError(
        vibStaking.connect(user1).transferRewards(await user2.getAddress(), transferAmount),
        vibStaking,
        "Unauthorized"
      );
    });

    it("Should allow admin to withdraw tokens", async function () {
      const withdrawAmount = parseEther("1000000");
      await vibStaking.connect(owner).withdrawTokens(withdrawAmount);

      expect(await vibeToken.balanceOf(await owner.getAddress())).gt(0);
    });
  });

  describe("Edge Cases", function () {
    it("Should handle multiple stakers", async function () {
      const stakeAmount = parseEther("1000");

      for (const user of [user1, user2, signers.user3]) {
        await vibeToken.connect(user).approve(vibStaking.address, stakeAmount);
        await vibStaking.connect(user).stake(stakeAmount, LOCK_DURATIONS.NONE);
      }

      const totalStaked = await vibStaking.totalStaked();
      expect(totalStaked).to.equal(stakeAmount.mul(3));
    });

    it("Should calculate rewards correctly when total staked changes", async function () {
      const stakeAmount = parseEther("10000");

      await vibeToken.connect(user1).approve(vibStaking.address, stakeAmount);
      await vibStaking.connect(user1).stake(stakeAmount, LOCK_DURATIONS.NONE);

      await advanceTime(30 * SECONDS_PER_DAY);

      await vibeToken.connect(user2).approve(vibStaking.address, stakeAmount);
      await vibStaking.connect(user2).stake(stakeAmount, LOCK_DURATIONS.NONE);

      await advanceTime(30 * SECONDS_PER_DAY);

      const rewardsUser1 = await vibStaking.calculateRewards(await user1.getAddress());
      const rewardsUser2 = await vibStaking.calculateRewards(await user2.getAddress());

      expect(rewardsUser1.gt(rewardsUser2)).to.be.true; // User1 staked longer
    });

    it("Should handle zero staked after unstake", async function () {
      const stakeAmount = parseEther("1000");

      await vibeToken.connect(user1).approve(vibStaking.address, stakeAmount);
      await vibStaking.connect(user1).stake(stakeAmount, LOCK_DURATIONS.NONE);
      await vibStaking.connect(user1).unstake(stakeAmount);

      const stakeInfo = await vibStaking.stakes(await user1.getAddress());
      expect(stakeInfo.amount).to.equal(0);
      expect(stakeInfo.tier).to.equal(0);
    });
  });
});
