import { expect } from "chai";
import { ethers } from "hardhat";
import { VIBEToken, VIBStaking, VIBVesting, VIBIdentity } from "../../typechain-types";
import { parseEther } from "ethers/lib/utils";
import { getSigners, expectEvent, advanceTime } from "../utils/fixtures";
import { time } from "../utils/helpers";
import {
  INITIAL_SUPPLY,
  STAKING_REWARDS_POOL,
  LOCK_DURATIONS,
  TIER_THRESHOLDS,
  VESTING_PERIODS,
  CLIFF_PERIODS,
  SECONDS_PER_DAY,
  IDENTITY_TYPES
} from "../utils/constants";

describe("Full Workflow Integration Tests", function () {
  let vibeToken: VIBEToken;
  let vibStaking: VIBStaking;
  let vibVesting: VIBVesting;
  let vibIdentity: VIBIdentity;
  let signers: any;
  let owner: Signer;
  let user1: Signer;
  let user2: Signer;
  let user3: Signer;

  const BASE_APR = 10000; // 100% (scaled by 10000)

  beforeEach(async function () {
    signers = await getSigners();
    owner = signers.owner;
    user1 = signers.user1;
    user2 = signers.user2;
    user3 = signers.user3;

    // Deploy VIBE Token
    const VIBEToken = await ethers.getContractFactory("VIBEToken");
    vibeToken = (await VIBEToken.deploy(await owner.getAddress())) as VIBEToken;
    await vibeToken.deployed();

    // Deploy VIBIdentity (SBT)
    const VIBIdentity = await ethers.getContractFactory("VIBIdentity");
    vibIdentity = (await VIBIdentity.deploy()) as VIBIdentity;
    await vibIdentity.deployed();

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

    // Deploy VIBVesting
    const VIBVesting = await ethers.getContractFactory("VIBVesting");
    vibVesting = (await VIBVesting.deploy(
      vibeToken.address,
      await owner.getAddress()
    )) as VIBVesting;
    await vibVesting.deployed();

    // Grant minter role to vesting contract
    await vibeToken.grantRole(await vibeToken.MINTER_ROLE(), vibVesting.address);

    // Mint rewards to staking contract
    await vibeToken.mint(vibStaking.address, STAKING_REWARDS_POOL);

    // Transfer tokens to test users
    for (const signer of [user1, user2, user3]) {
      await vibeToken.mint(await signer.getAddress(), parseEther("10000000"));
    }

    // Mint identity tokens to users
    await vibIdentity.connect(owner).mint(
      await user1.getAddress(),
      IDENTITY_TYPES.VERIFIED,
      "Verified User 1"
    );
    await vibIdentity.connect(owner).mint(
      await user2.getAddress(),
      IDENTITY_TYPES.KYC_VERIFIED,
      "KYC Verified User 2"
    );
    await vibIdentity.connect(owner).mint(
      await user3.getAddress(),
      IDENTITY_TYPES.INSTITUTION,
      "Institutional User 3"
    );
  });

  describe("Complete User Onboarding Flow", function () {
    it("Should complete full onboarding: mint identity -> stake tokens -> earn rewards", async function () {
      const user1Address = await user1.getAddress();

      // Step 1: Verify user has identity
      const hasIdentity = await vibIdentity.hasIdentity(user1Address);
      expect(hasIdentity).to.be.true;

      const identityType = await vibIdentity.getIdentityType(user1Address);
      expect(identityType).to.equal(IDENTITY_TYPES.VERIFIED);

      // Step 2: User stakes tokens
      const stakeAmount = parseEther("10000");
      await vibeToken.connect(user1).approve(vibStaking.address, stakeAmount);
      await vibStaking.connect(user1).stake(stakeAmount, LOCK_DURATIONS.SIX_MONTHS);

      // Verify stake
      const stakeInfo = await vibStaking.stakes(user1Address);
      expect(stakeInfo.amount).to.equal(stakeAmount);

      // Step 3: User earns rewards over time
      await advanceTime(30 * SECONDS_PER_DAY);

      const rewards = await vibStaking.calculateRewards(user1Address);
      expect(rewards.gt(0)).to.be.true;

      // Step 4: User claims rewards
      const balanceBefore = await vibeToken.balanceOf(user1Address);
      await vibStaking.connect(user1).claimRewards();
      const balanceAfter = await vibeToken.balanceOf(user1Address);

      expect(balanceAfter.sub(balanceBefore).gt(0)).to.be.true;

      // Verify rewards were claimed
      const newRewards = await vibStaking.calculateRewards(user1Address);
      expect(newRewards).to.equal(0);
    });
  });

  describe("Team Member Vesting Flow", function () {
    it("Should complete team vesting flow: add beneficiary -> vest -> claim", async function () {
      const user1Address = await user1.getAddress();
      const totalAmount = parseEther("240000"); // 20k per month for 12 months
      const vestingDuration = VESTING_PERIODS.TEAM_VESTING;
      const cliffDuration = CLIFF_PERIODS.TEAM_CLIFF;

      // Step 1: Admin adds team member as beneficiary
      await vibeToken.connect(owner).approve(vibVesting.address, totalAmount);

      const currentTimestamp = await time.latest();
      const startTime = currentTimestamp.add(86400);

      await vibVesting.addBeneficiary(
        user1Address,
        totalAmount,
        startTime,
        cliffDuration,
        vestingDuration
      );

      // Verify beneficiary was added
      const beneficiary = await vibVesting.beneficiaries(user1Address);
      expect(beneficiary.totalAmount).to.equal(totalAmount);

      // Step 2: Wait through cliff
      await advanceTime(86400); // 1 day (start)
      await advanceTime(cliffDuration); // Cliff period

      // Verify no tokens vested during cliff
      const vestedDuringCliff = await vibVesting.calculateVesting(user1Address);
      expect(vestedDuringCliff).to.equal(0);

      // Step 3: Wait past cliff
      await advanceTime(30 * SECONDS_PER_DAY); // 1 month after cliff

      // Verify tokens vested
      const vestedAfterCliff = await vibVesting.calculateVesting(user1Address);
      expect(vestedAfterCliff.gt(0)).to.be.true;

      // Step 4: Team member claims vested tokens
      const balanceBefore = await vibeToken.balanceOf(user1Address);
      await vibVesting.connect(user1).claim();
      const balanceAfter = await vibeToken.balanceOf(user1Address);

      const claimed = balanceAfter.sub(balanceBefore);
      expect(claimed).to.equal(vestedAfterCliff);

      // Verify claimed amount updated
      const beneficiaryAfterClaim = await vibVesting.beneficiaries(user1Address);
      expect(beneficiaryAfterClaim.claimedAmount).to.equal(claimed);
    });
  });

  describe("Multi-Tier Staking Flow", function () {
    it("Should handle stakers at different tiers with different APYs", async function () {
      const bronzeAmount = TIER_THRESHOLDS.BRONZE;
      const goldAmount = TIER_THRESHOLDS.GOLD;

      // Bronze staker (user1)
      await vibeToken.connect(user1).approve(vibStaking.address, bronzeAmount);
      await vibStaking.connect(user1).stake(bronzeAmount, LOCK_DURATIONS.NONE);

      // Gold staker (user2)
      await vibeToken.connect(user2).approve(vibStaking.address, goldAmount);
      await vibStaking.connect(user2).stake(goldAmount, LOCK_DURATIONS.NONE);

      // Wait for rewards to accumulate
      await advanceTime(30 * SECONDS_PER_DAY);

      // Calculate rewards per unit
      const rewardsUser1 = await vibStaking.calculateRewards(await user1.getAddress());
      const rewardsUser2 = await vibStaking.calculateRewards(await user2.getAddress());

      const rewardsPerUnitUser1 = rewardsUser1.mul(goldAmount).div(bronzeAmount);

      // Gold tier should earn more per unit staked
      expect(rewardsUser2.gt(rewardsPerUnitUser1)).to.be.true;

      // Verify tier assignment
      const stakeInfo1 = await vibStaking.stakes(await user1.getAddress());
      const stakeInfo2 = await vibStaking.stakes(await user2.getAddress());

      expect(stakeInfo1.tier).to.equal(0); // Bronze
      expect(stakeInfo2.tier).to.equal(2); // Gold
    });
  });

  describe("Lock Bonus Flow", function () {
    it("Should apply correct lock bonuses for different durations", async function () {
      const stakeAmount = parseEther("10000");

      // No lock
      await vibeToken.connect(user1).approve(vibStaking.address, stakeAmount);
      await vibStaking.connect(user1).stake(stakeAmount, LOCK_DURATIONS.NONE);

      // 12 month lock
      await vibeToken.connect(user2).approve(vibStaking.address, stakeAmount);
      await vibStaking.connect(user2).stake(stakeAmount, LOCK_DURATIONS.TWELVE_MONTHS);

      // Wait for rewards
      await advanceTime(30 * SECONDS_PER_DAY);

      const rewardsNoLock = await vibStaking.calculateRewards(await user1.getAddress());
      const rewardsWithLock = await vibStaking.calculateRewards(await user2.getAddress());

      // Locked staker should earn significantly more
      expect(rewardsWithLock.gt(rewardsNoLock.mul(15).div(10))).to.be.true;

      // Verify lock bonuses
      const stakeInfo1 = await vibStaking.stakes(await user1.getAddress());
      const stakeInfo2 = await vibStaking.stakes(await user2.getAddress());

      expect(stakeInfo1.lockBonusRate).to.equal(0);
      expect(stakeInfo2.lockBonusRate).to.equal(8000); // 80% bonus
    });
  });

  describe("Complete Delegation Flow", function () {
    it("Should support delegation via Permit", async function () {
      const stakeAmount = parseEther("10000");
      const user1Address = await user1.getAddress();

      // User1 approves staking via Permit
      const deadline = await time.latest().then(t => t.add(3600));
      const nonce = await vibeToken.nonces(user1Address);

      const domain = {
        name: await vibeToken.name(),
        version: "1",
        chainId: await ethers.provider.getNetwork().then(n => n.chainId),
        verifyingContract: vibeToken.address
      };

      const types = {
        Permit: [
          { name: "owner", type: "address" },
          { name: "spender", type: "address" },
          { name: "value", type: "uint256" },
          { name: "nonce", type: "uint256" },
          { name: "deadline", type: "uint256" }
        ]
      };

      const values = {
        owner: user1Address,
        spender: vibStaking.address,
        value: stakeAmount,
        nonce: nonce,
        deadline: deadline
      };

      const signature = await user1._signTypedData(domain, types, values);
      const { v, r, s } = ethers.utils.splitSignature(signature);

      // Execute Permit
      await vibeToken.permit(user1Address, vibStaking.address, stakeAmount, deadline, v, r, s);

      // Verify approval
      expect(await vibeToken.allowance(user1Address, vibStaking.address))
        .to.equal(stakeAmount);

      // Stake
      await vibStaking.connect(user1).stake(stakeAmount, LOCK_DURATIONS.NONE);

      // Verify stake
      const stakeInfo = await vibStaking.stakes(user1Address);
      expect(stakeInfo.amount).to.equal(stakeAmount);
    });
  });

  describe("Combined Staking and Vesting", function () {
    it("Should allow user to participate in both staking and vesting", async function () {
      const user1Address = await user1.getAddress();

      // Setup vesting for user1
      const vestingAmount = parseEther("120000");
      await vibeToken.connect(owner).approve(vibVesting.address, vestingAmount);

      const currentTimestamp = await time.latest();
      const startTime = currentTimestamp.add(86400);

      await vibVesting.addBeneficiary(
        user1Address,
        vestingAmount,
        startTime,
        CLIFF_PERIODS.TEAM_CLIFF,
        VESTING_PERIODS.TEAM_VESTING
      );

      // User1 stakes additional tokens
      const stakeAmount = parseEther("10000");
      await vibeToken.connect(user1).approve(vibStaking.address, stakeAmount);
      await vibStaking.connect(user1).stake(stakeAmount, LOCK_DURATIONS.NONE);

      // Wait for both
      await advanceTime(86400); // 1 day (start)
      await advanceTime(CLIFF_PERIODS.TEAM_CLIFF.add(30 * SECONDS_PER_DAY)); // Cliff + 1 month

      // Claim both
      const balanceBefore = await vibeToken.balanceOf(user1Address);

      await vibVesting.connect(user1).claim();
      await vibStaking.connect(user1).claimRewards();

      const balanceAfter = await vibeToken.balanceOf(user1Address);

      expect(balanceAfter.sub(balanceBefore).gt(0)).to.be.true;

      // Verify user still has staking position
      const stakeInfo = await vibStaking.stakes(user1Address);
      expect(stakeInfo.amount).to.equal(stakeAmount);
    });
  });

  describe("Emergency Pause Flow", function () {
    it("Should handle emergency pause and resume", async function () {
      const stakeAmount = parseEther("10000");

      // User stakes
      await vibeToken.connect(user1).approve(vibStaking.address, stakeAmount);
      await vibStaking.connect(user1).stake(stakeAmount, LOCK_DURATIONS.NONE);

      // Admin pauses token
      await vibeToken.pause();
      expect(await vibeToken.paused()).to.be.true;

      // Transfers should fail
      await expect(
        vibeToken.connect(owner).transfer(await user2.getAddress(), stakeAmount)
      ).to.be.reverted;

      // Admin unpauses
      await vibeToken.unpause();
      expect(await vibeToken.paused()).to.be.false;

      // Transfers should work now
      await vibeToken.connect(owner).transfer(await user2.getAddress(), stakeAmount);
      expect(await vibeToken.balanceOf(await user2.getAddress())).to.equal(stakeAmount);
    });
  });

  describe("Token Supply Flow", function () {
    it("Should track total supply across all operations", async function () {
      const initialSupply = await vibeToken.totalSupply();

      // Mint rewards to staking
      await vibeToken.mint(vibStaking.address, STAKING_REWARDS_POOL);
      expect(await vibeToken.totalSupply()).to.equal(initialSupply.add(STAKING_REWARDS_POOL));

      // Transfer to users
      const transferAmount = parseEther("1000000");
      await vibeToken.connect(owner).transfer(await user1.getAddress(), transferAmount);
      expect(await vibeToken.totalSupply()).to.equal(initialSupply.add(STAKING_REWARDS_POOL));

      // Burn tokens
      const burnAmount = parseEther("100000");
      await vibeToken.connect(user1).burn(burnAmount);
      expect(await vibeToken.totalSupply()).to.equal(initialSupply.add(STAKING_REWARDS_POOL).sub(burnAmount));
    });
  });

  describe("Identity-based Access Flow", function () {
    it("Should verify identity types for different operations", async function () {
      // Get identity types
      const identityType1 = await vibIdentity.getIdentityType(await user1.getAddress());
      const identityType2 = await vibIdentity.getIdentityType(await user2.getAddress());
      const identityType3 = await vibIdentity.getIdentityType(await user3.getAddress());

      expect(identityType1).to.equal(IDENTITY_TYPES.VERIFIED);
      expect(identityType2).to.equal(IDENTITY_TYPES.KYC_VERIFIED);
      expect(identityType3).to.equal(IDENTITY_TYPES.INSTITUTION);

      // Verify all users can stake
      const stakeAmount = parseEther("10000");

      await vibeToken.connect(user1).approve(vibStaking.address, stakeAmount);
      await vibeToken.connect(user2).approve(vibStaking.address, stakeAmount);
      await vibeToken.connect(user3).approve(vibStaking.address, stakeAmount);

      await vibStaking.connect(user1).stake(stakeAmount, LOCK_DURATIONS.NONE);
      await vibStaking.connect(user2).stake(stakeAmount, LOCK_DURATIONS.NONE);
      await vibStaking.connect(user3).stake(stakeAmount, LOCK_DURATIONS.NONE);

      // Verify all staked successfully
      const totalStaked = await vibStaking.totalStaked();
      expect(totalStaked).to.equal(stakeAmount.mul(3));
    });
  });

  describe("Reward Distribution Flow", function () {
    it("Should distribute rewards proportionally among stakers", async function () {
      const stakeAmount1 = parseEther("10000");
      const stakeAmount2 = parseEther("30000");
      const stakeAmount3 = parseEther("60000");

      // Stakers stake different amounts
      await vibeToken.connect(user1).approve(vibStaking.address, stakeAmount1);
      await vibeToken.connect(user2).approve(vibStaking.address, stakeAmount2);
      await vibeToken.connect(user3).approve(vibStaking.address, stakeAmount3);

      await vibStaking.connect(user1).stake(stakeAmount1, LOCK_DURATIONS.NONE);
      await vibStaking.connect(user2).stake(stakeAmount2, LOCK_DURATIONS.NONE);
      await vibStaking.connect(user3).stake(stakeAmount3, LOCK_DURATIONS.NONE);

      // Wait for rewards
      await advanceTime(30 * SECONDS_PER_DAY);

      // Calculate rewards
      const rewards1 = await vibStaking.calculateRewards(await user1.getAddress());
      const rewards2 = await vibStaking.calculateRewards(await user2.getAddress());
      const rewards3 = await vibStaking.calculateRewards(await user3.getAddress());

      // Rewards should be proportional to stake amounts
      const expectedRatio1 = 1; // 10k
      const expectedRatio2 = 3; // 30k
      const expectedRatio3 = 6; // 60k

      const actualRatio1 = rewards1.div(stakeAmount1);
      const actualRatio2 = rewards2.div(stakeAmount2);
      const actualRatio3 = rewards3.div(stakeAmount3);

      // All should have approximately the same reward per unit
      expect(actualRatio1).to.be.closeTo(actualRatio2, actualRatio1.div(100));
      expect(actualRatio2).to.be.closeTo(actualRatio3, actualRatio2.div(100));
    });
  });

  describe("Full E2E User Journey", function () {
    it("Should complete full user journey from onboarding to rewards", async function () {
      const user1Address = await user1.getAddress();

      // 1. User receives identity SBT
      expect(await vibIdentity.hasIdentity(user1Address)).to.be.true;
      expect(await vibIdentity.getIdentityType(user1Address)).to.equal(IDENTITY_TYPES.VERIFIED);

      // 2. User receives tokens
      const initialBalance = await vibeToken.balanceOf(user1Address);
      expect(initialBalance).to.equal(parseEther("10000000"));

      // 3. User stakes tokens with lock
      const stakeAmount = parseEther("50000");
      await vibeToken.connect(user1).approve(vibStaking.address, stakeAmount);
      await vibStaking.connect(user1).stake(stakeAmount, LOCK_DURATIONS.SIX_MONTHS);

      // Verify stake
      const stakeInfo = await vibStaking.stakes(user1Address);
      expect(stakeInfo.amount).to.equal(stakeAmount);
      expect(stakeInfo.lockDuration).to.equal(LOCK_DURATIONS.SIX_MONTHS);

      // 4. User earns rewards over time
      await advanceTime(90 * SECONDS_PER_DAY);

      const rewards = await vibStaking.calculateRewards(user1Address);
      expect(rewards.gt(0)).to.be.true;

      // 5. User claims rewards
      const balanceBeforeClaim = await vibeToken.balanceOf(user1Address);
      await vibStaking.connect(user1).claimRewards();
      const balanceAfterClaim = await vibeToken.balanceOf(user1Address);

      const claimedAmount = balanceAfterClaim.sub(balanceBeforeClaim);
      expect(claimedAmount.gt(0)).to.be.true;

      // 6. User still has staking position
      const stakeInfoAfterClaim = await vibStaking.stakes(user1Address);
      expect(stakeInfoAfterClaim.amount).to.equal(stakeAmount);

      // 7. User can unstake after lock period
      await advanceTime(LOCK_DURATIONS.SIX_MONTHS.sub(90 * SECONDS_PER_DAY));
      await advanceTime(SECONDS_PER_DAY);

      const balanceBeforeUnstake = await vibeToken.balanceOf(user1Address);
      await vibStaking.connect(user1).unstake(stakeAmount);
      const balanceAfterUnstake = await vibeToken.balanceOf(user1Address);

      // Should receive staked amount + remaining rewards
      const returnedAmount = balanceAfterUnstake.sub(balanceBeforeUnstake);
      expect(returnedAmount.gte(stakeAmount)).to.be.true;

      // Verify no staking position
      const stakeInfoAfterUnstake = await vibStaking.stakes(user1Address);
      expect(stakeInfoAfterUnstake.amount).to.equal(0);

      // 8. User can use tokens for other purposes
      await vibeToken.connect(user1).transfer(await user2.getAddress(), parseEther("1000"));
      expect(await vibeToken.balanceOf(await user2.getAddress())).to.equal(
        parseEther("10000001") // 10M initial + 1K from user1
      );
    });
  });
});
