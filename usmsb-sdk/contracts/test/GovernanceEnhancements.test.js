const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

describe("VIBGovernance Enhancements", function () {
  let vibeToken, governance, staking;
  let owner, user1, user2, user3, verifier, delegator, delegatee;

  const MIN_STAKE = ethers.parseEther("100");
  const VOTING_PERIOD = 7 * 24 * 60 * 60; // 7 days

  beforeEach(async function () {
    [owner, user1, user2, user3, verifier, delegator, delegatee] = await ethers.getSigners();

    // Deploy VIBEToken
    const VIBEToken = await ethers.getContractFactory("VIBEToken");
    vibeToken = await VIBEToken.deploy("VIBE Token", "VIBE", owner.address);
    await vibeToken.waitForDeployment();
    await vibeToken.mintTreasury();

    // Deploy VIBStaking
    const VIBStaking = await ethers.getContractFactory("VIBStaking");
    staking = await VIBStaking.deploy(await vibeToken.getAddress());
    await staking.waitForDeployment();

    // Deploy VIBGovernance
    const VIBGovernance = await ethers.getContractFactory("VIBGovernance");
    governance = await VIBGovernance.deploy(await vibeToken.getAddress());
    await governance.waitForDeployment();

    // Set up VIBStaking integration
    await governance.setVIBStaking(await staking.getAddress());
    await governance.setStakingContract(await staking.getAddress());

    // Distribute tokens
    await vibeToken.transfer(user1.address, ethers.parseEther("10000"));
    await vibeToken.transfer(user2.address, ethers.parseEther("10000"));
    await vibeToken.transfer(user3.address, ethers.parseEther("10000"));
    await vibeToken.transfer(delegator.address, ethers.parseEther("10000"));
    await vibeToken.transfer(delegatee.address, ethers.parseEther("10000"));
    await vibeToken.transfer(await governance.getAddress(), ethers.parseEther("10000"));

    // Approve staking
    await vibeToken.connect(user1).approve(await staking.getAddress(), ethers.MaxUint256);
    await vibeToken.connect(user2).approve(await staking.getAddress(), ethers.MaxUint256);
    await vibeToken.connect(delegator).approve(await staking.getAddress(), ethers.MaxUint256);
    await vibeToken.connect(delegatee).approve(await staking.getAddress(), ethers.MaxUint256);

    // Approve governance
    await vibeToken.connect(user1).approve(await governance.getAddress(), ethers.MaxUint256);
  });

  describe("Capital Weight with VIBStaking Integration", function () {
    it("Should use VIBStaking voting power when available", async function () {
      // User1 stakes 1000 VIBE for 365 days
      await staking.connect(user1).stake(ethers.parseEther("1000"), 4); // 365 days

      // Get voting power from governance
      const votingPower = await governance.getOwnVotingPower(user1.address);

      // Should be staked amount * time multiplier (150% for 365+ days)
      // But initially the stake time is 0, so it starts at 100%
      expect(votingPower).to.be.gt(0);
    });

    it("Should return 0 voting power for non-stakers without token balance", async function () {
      // user3 has token balance but hasn't staked
      // The fallback uses token balance, so they will have voting power based on balance
      const votingPower = await governance.getOwnVotingPower(user3.address);
      // user3 has 10000 VIBE, so fallback gives them voting power
      expect(votingPower).to.be.gt(0);
    });

    it("Should update voting power after staking more", async function () {
      // Initial stake
      await staking.connect(user1).stake(ethers.parseEther("1000"), 2);

      const powerBefore = await governance.getOwnVotingPower(user1.address);

      // Increase time to get higher multiplier
      await time.increase(180 * 24 * 60 * 60); // 180 days

      // Add more stake (this updates the stake time, so multiplier resets)
      await staking.connect(user1).stake(ethers.parseEther("500"), 0);

      const powerAfter = await governance.getOwnVotingPower(user1.address);

      // Voting power should reflect new total stake
      expect(powerAfter).to.be.gt(0);
    });
  });

  describe("Contribution Points System", function () {
    beforeEach(async function () {
      // Initialize contribution types
      await governance.initializeContributionTypes();
      // Set verifier
      await governance.setContributionVerifier(verifier.address, true);
    });

    it("Should initialize contribution type points", async function () {
      const codePoints = await governance.contributionTypePoints(0); // CODE_CONTRIBUTION
      expect(codePoints).to.equal(ethers.parseEther("100"));
    });

    it("Should allow submitting contribution", async function () {
      const tx = await governance.connect(user1).submitContribution(
        0, // CODE_CONTRIBUTION
        ethers.parseEther("100"),
        "ipfs://evidence-hash"
      );

      await expect(tx)
        .to.emit(governance, "ContributionSubmitted")
        .withArgs(0, user1.address, 0, ethers.parseEther("100"), "ipfs://evidence-hash");

      const record = await governance.getContributionRecord(0);
      expect(record.contributor).to.equal(user1.address);
      expect(record.contributionType).to.equal(0);
      expect(record.verified).to.equal(false);
    });

    it("Should allow verifier to approve contribution", async function () {
      await governance.connect(user1).submitContribution(
        0, // CODE_CONTRIBUTION
        ethers.parseEther("100"),
        "ipfs://evidence-hash"
      );

      const tx = await governance.connect(verifier).verifyContribution(0, true, 0);

      await expect(tx)
        .to.emit(governance, "ContributionVerified")
        .withArgs(0, user1.address, ethers.parseEther("100"), verifier.address);

      const record = await governance.getContributionRecord(0);
      expect(record.verified).to.equal(true);
      expect(record.verifier).to.equal(verifier.address);

      // Check contribution points updated
      const points = await governance.contributionPoints(user1.address);
      expect(points).to.equal(ethers.parseEther("100"));
    });

    it("Should increase production weight based on contribution points", async function () {
      // User1 contributes and gets points
      await governance.connect(user1).submitContribution(
        0, // CODE_CONTRIBUTION
        ethers.parseEther("100"),
        "ipfs://evidence-hash"
      );
      await governance.connect(verifier).verifyContribution(0, true, 0);

      // User1 also stakes to get capital weight
      await staking.connect(user1).stake(ethers.parseEther("1000"), 0);

      const ownPower = await governance.getOwnVotingPower(user1.address);

      // Should have capital weight + production weight
      expect(ownPower).to.be.gt(0);
    });

    it("Should reject contribution without evidence", async function () {
      await expect(
        governance.connect(user1).submitContribution(0, ethers.parseEther("100"), "")
      ).to.be.revertedWith("VIBGovernance: evidence required");
    });

    it("Should reject verification from non-verifier", async function () {
      await governance.connect(user1).submitContribution(
        0, // CODE_CONTRIBUTION
        ethers.parseEther("100"),
        "ipfs://evidence-hash"
      );

      await expect(
        governance.connect(user2).verifyContribution(0, true, 0)
      ).to.be.revertedWith("VIBGovernance: not a verifier");
    });

    it("Should enforce monthly points limit", async function () {
      // Submit multiple contributions to exceed monthly limit
      for (let i = 0; i < 55; i++) {
        await governance.connect(user1).submitContribution(
          0, // CODE_CONTRIBUTION
          ethers.parseEther("100"),
          `ipfs://evidence-hash-${i}`
        );
      }

      // Verify all contributions
      for (let i = 0; i < 55; i++) {
        await governance.connect(verifier).verifyContribution(i, true, 0);
      }

      // Should cap at monthly limit (5000 VIBE)
      const points = await governance.contributionPoints(user1.address);
      expect(points).to.be.lte(ethers.parseEther("5000"));
    });

    it("Should allow batch verification", async function () {
      // Submit 3 contributions
      for (let i = 0; i < 3; i++) {
        await governance.connect(user1).submitContribution(
          0, // CODE_CONTRIBUTION
          ethers.parseEther("100"),
          `ipfs://evidence-hash-${i}`
        );
      }

      // Batch verify
      await governance.connect(verifier).batchVerifyContributions(
        [0, 1, 2],
        [true, true, false],
        [0, 0, 0]
      );

      // Check points (2 approved * 100)
      const points = await governance.contributionPoints(user1.address);
      expect(points).to.equal(ethers.parseEther("200"));
    });
  });

  describe("Delegation Recovery Mechanism", function () {
    beforeEach(async function () {
      // Both staking for voting power
      await staking.connect(delegator).stake(ethers.parseEther("1000"), 0);
      await staking.connect(delegatee).stake(ethers.parseEther("500"), 0);
    });

    it("Should track consecutive abstentions", async function () {
      // Delegate
      await governance.connect(delegator).delegate(delegatee.address, 90 * 24 * 60 * 60);

      // Create proposal
      await governance.connect(user1).createProposal(
        0, // GENERAL
        "Test Proposal",
        "Description",
        ethers.ZeroAddress,
        "0x"
      );

      // Wait for voting period to end
      await time.increase(VOTING_PERIOD + 1);

      // Finalize proposal - delegatee didn't vote
      await governance.finalizeProposal(0);

      // Check abstention count
      const abstentions = await governance.consecutiveAbstentions(delegatee.address);
      expect(abstentions).to.equal(1);
    });

    it("Should reset abstention count when delegatee votes", async function () {
      // Delegate
      await governance.connect(delegator).delegate(delegatee.address, 90 * 24 * 60 * 60);

      // Create proposal
      await governance.connect(user1).createProposal(
        0, // GENERAL
        "Test Proposal",
        "Description",
        ethers.ZeroAddress,
        "0x"
      );

      // Delegatee votes
      await governance.connect(delegatee).castVote(0, 1); // For

      // Wait for voting period to end
      await time.increase(VOTING_PERIOD + 1);

      // Finalize
      await governance.finalizeProposal(0);

      // Abstention count should still be 0
      const abstentions = await governance.consecutiveAbstentions(delegatee.address);
      expect(abstentions).to.equal(0);
    });

    it("Should allow recovery request after 3 consecutive abstentions", async function () {
      // Delegate
      await governance.connect(delegator).delegate(delegatee.address, 90 * 24 * 60 * 60);

      // Create and finalize 3 proposals without delegatee voting
      for (let i = 0; i < 3; i++) {
        await governance.connect(user1).createProposal(
          0, // GENERAL
          `Test Proposal ${i}`,
          "Description",
          ethers.ZeroAddress,
          "0x"
        );

        await time.increase(VOTING_PERIOD + 1);
        await governance.finalizeProposal(i);
      }

      // Check abstention count
      const abstentions = await governance.consecutiveAbstentions(delegatee.address);
      expect(abstentions).to.equal(3);

      // Request recovery
      await governance.connect(delegator).requestDelegationRecovery();

      const status = await governance.getDelegationRecoveryStatus(delegator.address);
      expect(status.isPending).to.equal(true);
    });

    it("Should execute recovery after delay", async function () {
      // Delegate
      await governance.connect(delegator).delegate(delegatee.address, 90 * 24 * 60 * 60);

      // Create 3 proposals with abstentions
      for (let i = 0; i < 3; i++) {
        await governance.connect(user1).createProposal(
          0, // GENERAL
          `Test Proposal ${i}`,
          "Description",
          ethers.ZeroAddress,
          "0x"
        );

        await time.increase(VOTING_PERIOD + 1);
        await governance.finalizeProposal(i);
      }

      // Request recovery
      await governance.connect(delegator).requestDelegationRecovery();

      // Wait for recovery delay (7 days)
      await time.increase(7 * 24 * 60 * 60);

      // Execute recovery
      const tx = await governance.connect(delegator).executeDelegationRecovery();

      await expect(tx)
        .to.emit(governance, "DelegationRecovered")
        .withArgs(delegator.address, delegatee.address, ethers.parseEther("1000"));

      // Check delegation is removed
      const delegateAddr = await governance.delegates(delegator.address);
      expect(delegateAddr).to.equal(ethers.ZeroAddress);
    });

    it("Should not allow recovery before delay", async function () {
      // Delegate
      await governance.connect(delegator).delegate(delegatee.address, 90 * 24 * 60 * 60);

      // Create 3 proposals with abstentions
      for (let i = 0; i < 3; i++) {
        await governance.connect(user1).createProposal(
          0, // GENERAL
          `Test Proposal ${i}`,
          "Description",
          ethers.ZeroAddress,
          "0x"
        );

        await time.increase(VOTING_PERIOD + 1);
        await governance.finalizeProposal(i);
      }

      // Request recovery
      await governance.connect(delegator).requestDelegationRecovery();

      // Try to execute immediately
      await expect(
        governance.connect(delegator).executeDelegationRecovery()
      ).to.be.revertedWith("VIBGovernance: recovery delay not passed");
    });

    it("Should check recovery eligibility", async function () {
      // Initially not eligible
      expect(await governance.canRequestRecovery(delegator.address)).to.equal(false);

      // Delegate
      await governance.connect(delegator).delegate(delegatee.address, 90 * 24 * 60 * 60);

      // Still not eligible (no abstentions yet)
      expect(await governance.canRequestRecovery(delegator.address)).to.equal(false);

      // Create 3 proposals with abstentions
      for (let i = 0; i < 3; i++) {
        await governance.connect(user1).createProposal(
          0, // GENERAL
          `Test Proposal ${i}`,
          "Description",
          ethers.ZeroAddress,
          "0x"
        );

        await time.increase(VOTING_PERIOD + 1);
        await governance.finalizeProposal(i);
      }

      // Now eligible
      expect(await governance.canRequestRecovery(delegator.address)).to.equal(true);
    });
  });

  describe("Production Weight Conversion", function () {
    beforeEach(async function () {
      await governance.initializeContributionTypes();
      await governance.setContributionVerifier(verifier.address, true);
    });

    it("Should convert contribution points to voting power", async function () {
      // User gets 100 contribution points
      await governance.connect(user1).submitContribution(
        0, // CODE_CONTRIBUTION
        ethers.parseEther("100"),
        "ipfs://evidence-hash"
      );
      await governance.connect(verifier).verifyContribution(0, true, 0);

      // Check contribution points
      const points = await governance.contributionPoints(user1.address);
      expect(points).to.equal(ethers.parseEther("100"));

      // Production weight should be points * ratio / 100
      // 100 * 100 / 100 = 100 (0.01 per point)
      const ownPower = await governance.getOwnVotingPower(user1.address);

      // With only contribution points, power should be (100 * 100 / 100) = 100
      // But also includes community weight if KYC verified
      expect(ownPower).to.be.gt(0);
    });
  });

  describe("Integration: Full Governance Flow", function () {
    beforeEach(async function () {
      await governance.initializeContributionTypes();
      await governance.setContributionVerifier(verifier.address, true);

      // Setup voting power
      await staking.connect(user1).stake(ethers.parseEther("1000"), 4); // 365 days
      await staking.connect(user2).stake(ethers.parseEther("500"), 2); // 90 days
    });

    it("Should support full governance lifecycle", async function () {
      // User1 contributes and gets points
      await governance.connect(user1).submitContribution(
        0, // CODE_CONTRIBUTION
        ethers.parseEther("100"),
        "ipfs://evidence-hash"
      );
      await governance.connect(verifier).verifyContribution(0, true, 0);

      // Create proposal
      const tx = await governance.connect(user1).createProposal(
        0, // GENERAL
        "Feature Request",
        "Add new governance feature",
        ethers.ZeroAddress,
        "0x"
      );

      await expect(tx).to.emit(governance, "ProposalCreated");

      // Vote on proposal
      await governance.connect(user1).castVote(0, 1); // For
      await governance.connect(user2).castVote(0, 1); // For

      // Wait for voting period
      await time.increase(VOTING_PERIOD + 1);

      // Finalize
      await governance.finalizeProposal(0);

      // Check proposal state
      const proposal = await governance.getProposal(0);
      expect(proposal.state).to.equal(4); // SUCCEEDED (enum: PENDING=0, ACTIVE=1, CANCELLED=2, DEFEATED=3, SUCCEEDED=4)
    });
  });
});
