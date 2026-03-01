const { expect } = require("chai");
const { ethers, time } = require("hardhat");
const { time: timeHelpers } = require("@nomicfoundation/hardhat-network-helpers");

describe("VIBDispute", function () {
  let vibeToken, disputeContract;
  let owner, plaintiff, defendant, arbitrator1, arbitrator2, arbitrator3, other;

  const DEFAULT_DISPUTE_STAKE = ethers.parseEther("5");
  const EVIDENCE_PERIOD = 24 * 60 * 60; // 24 hours
  const VOTING_PERIOD = 48 * 60 * 60; // 48 hours

  beforeEach(async function () {
    [owner, plaintiff, defendant, arbitrator1, arbitrator2, arbitrator3, other] = await ethers.getSigners();

    // Deploy VIBEToken
    const VIBEToken = await ethers.getContractFactory("VIBEToken");
    vibeToken = await VIBEToken.deploy("VIBE Token", "VIBE", owner.address);
    await vibeToken.waitForDeployment();
    await vibeToken.mintTreasury();

    // Disable transaction tax for testing
    await vibeToken.setTransactionTaxEnabled(false);

    // Deploy VIBDispute
    const VIBDispute = await ethers.getContractFactory("VIBDispute");
    disputeContract = await VIBDispute.deploy(
      await vibeToken.getAddress(),
      ethers.ZeroAddress, // stakingContract
      ethers.ZeroAddress, // governanceContract
      ethers.ZeroAddress, // vrfCoordinator (测试环境使用零地址)
      ethers.ZeroAddress, // linkToken
      "0x0000000000000000000000000000000000000000000000000000000000000000" // vrfKeyHash
    );
    await disputeContract.waitForDeployment();

    // M-11修复: 测试环境启用回退随机性
    await disputeContract.setAllowFallbackRandomness(true);

    // Transfer tokens to test accounts
    await vibeToken.transfer(plaintiff.address, ethers.parseEther("1000"));
    await vibeToken.transfer(defendant.address, ethers.parseEther("1000"));
    await vibeToken.transfer(arbitrator1.address, ethers.parseEther("2000"));
    await vibeToken.transfer(arbitrator2.address, ethers.parseEther("2000"));
    await vibeToken.transfer(arbitrator3.address, ethers.parseEther("2000"));

    // Approve dispute contract
    await vibeToken.connect(plaintiff).approve(await disputeContract.getAddress(), ethers.MaxUint256);
    await vibeToken.connect(defendant).approve(await disputeContract.getAddress(), ethers.MaxUint256);
  });

  describe("Deployment", function () {
    it("Should set the right token", async function () {
      expect(await disputeContract.vibeToken()).to.equal(await vibeToken.getAddress());
    });

    it("Should have correct default stake amount", async function () {
      expect(await disputeContract.DEFAULT_DISPUTE_STAKE()).to.equal(DEFAULT_DISPUTE_STAKE);
    });

    it("Should have correct periods", async function () {
      expect(await disputeContract.EVIDENCE_PERIOD()).to.equal(EVIDENCE_PERIOD);
      expect(await disputeContract.VOTING_PERIOD()).to.equal(VOTING_PERIOD);
    });
  });

  describe("Create Dispute", function () {
    it("Should create a dispute with correct parameters", async function () {
      const amount = ethers.parseEther("100");
      const description = "ipfs://test-description-hash";

      await expect(disputeContract.connect(plaintiff).createDispute(defendant.address, amount, description))
        .to.emit(disputeContract, "DisputeCreated")
        .withArgs(1, plaintiff.address, defendant.address, amount, DEFAULT_DISPUTE_STAKE);

      const dispute = await disputeContract.getDispute(1);
      expect(dispute.plaintiff).to.equal(plaintiff.address);
      expect(dispute.defendant).to.equal(defendant.address);
      expect(dispute.amount).to.equal(amount);
      expect(dispute.status).to.equal(1); // Pending
    });

    it("Should transfer stake tokens from plaintiff", async function () {
      const balanceBefore = await vibeToken.balanceOf(plaintiff.address);

      await disputeContract.connect(plaintiff).createDispute(defendant.address, ethers.parseEther("100"), "test");

      const balanceAfter = await vibeToken.balanceOf(plaintiff.address);
      expect(balanceBefore - balanceAfter).to.equal(DEFAULT_DISPUTE_STAKE);
    });

    it("Should fail with zero defendant address", async function () {
      await expect(
        disputeContract.connect(plaintiff).createDispute(ethers.ZeroAddress, ethers.parseEther("100"), "test")
      ).to.be.revertedWith("Invalid defendant");
    });

    it("Should fail with empty description", async function () {
      await expect(
        disputeContract.connect(plaintiff).createDispute(defendant.address, ethers.parseEther("100"), "")
      ).to.be.revertedWith("Description required");
    });

    it("Should fail if disputing self", async function () {
      await expect(
        disputeContract.connect(plaintiff).createDispute(plaintiff.address, ethers.parseEther("100"), "test")
      ).to.be.revertedWith("Cannot dispute self");
    });
  });

  describe("Respond to Dispute", function () {
    let disputeId;

    beforeEach(async function () {
      // Register arbitrators
      await disputeContract.connect(arbitrator1).registerArbitrator();
      await disputeContract.connect(arbitrator2).registerArbitrator();
      await disputeContract.connect(arbitrator3).registerArbitrator();

      // Set governance contract to owner for testing to allow passExam
      await disputeContract.setGovernanceContract(owner.address);

      // Make them eligible by passing exam (must be called by governance contract = owner)
      await disputeContract.connect(owner).passExam(arbitrator1.address);
      await disputeContract.connect(owner).passExam(arbitrator2.address);
      await disputeContract.connect(owner).passExam(arbitrator3.address);

      // Set minimum votes for eligibility (ARBITRATOR_MIN_VOTES = 10)
      await disputeContract.setArbitratorVotes(arbitrator1.address, 10);
      await disputeContract.setArbitratorVotes(arbitrator2.address, 10);
      await disputeContract.setArbitratorVotes(arbitrator3.address, 10);

      // Get current dispute count
      const countBefore = await disputeContract.disputeCounter();

      await disputeContract.connect(plaintiff).createDispute(defendant.address, ethers.parseEther("100"), "test");

      // Dispute ID is countBefore + 1 (1-indexed)
      disputeId = countBefore + 1n;
    });

    it("Should allow defendant to respond", async function () {
      await expect(disputeContract.connect(defendant).respondToDispute(disputeId))
        .to.emit(disputeContract, "DisputeResponded")
        .withArgs(disputeId, defendant.address);

      const dispute = await disputeContract.getDispute(disputeId);
      expect(dispute.status).to.equal(2); // EvidencePhase
    });

    it("Should transfer stake tokens from defendant", async function () {
      const balanceBefore = await vibeToken.balanceOf(defendant.address);

      await disputeContract.connect(defendant).respondToDispute(disputeId);

      const balanceAfter = await vibeToken.balanceOf(defendant.address);
      expect(balanceBefore - balanceAfter).to.equal(DEFAULT_DISPUTE_STAKE);
    });

    it("Should fail if not called by defendant", async function () {
      await expect(
        disputeContract.connect(other).respondToDispute(disputeId)
      ).to.be.revertedWith("Only defendant");
    });

    it("Should fail if dispute not pending", async function () {
      await disputeContract.connect(defendant).respondToDispute(disputeId);

      await expect(
        disputeContract.connect(defendant).respondToDispute(disputeId)
      ).to.be.revertedWith("Not pending");
    });
  });

  describe("Arbitrator Management", function () {
    it("Should allow registering as arbitrator", async function () {
      await expect(disputeContract.connect(arbitrator1).registerArbitrator())
        .to.emit(disputeContract, "ArbitratorRegistered")
        .withArgs(arbitrator1.address);

      const arbitrator = await disputeContract.arbitrators(arbitrator1.address);
      expect(arbitrator.isRegistered).to.equal(true);
      expect(arbitrator.reputation).to.equal(100);
    });

    it("Should fail if already registered", async function () {
      await disputeContract.connect(arbitrator1).registerArbitrator();

      await expect(
        disputeContract.connect(arbitrator1).registerArbitrator()
      ).to.be.revertedWith("Already registered");
    });

    it("Should fail if insufficient balance", async function () {
      // other has no VIBE tokens
      await expect(
        disputeContract.connect(other).registerArbitrator()
      ).to.be.revertedWith("Insufficient VIBE balance");
    });

    it("Should check arbitrator eligibility", async function () {
      await disputeContract.connect(arbitrator1).registerArbitrator();

      // Not passed exam, so not eligible
      expect(await disputeContract.isEligibleArbitrator(arbitrator1.address)).to.equal(false);
    });
  });

  describe("Credit Protection", function () {
    it("Should return default stake for new users", async function () {
      expect(await disputeContract.getDisputeStake(plaintiff.address)).to.equal(DEFAULT_DISPUTE_STAKE);
    });

    it("Should track credit records", async function () {
      // This would be tested more thoroughly in integration tests
      // where disputes are actually resolved
      const record = await disputeContract.getCreditRecord(plaintiff.address);
      expect(record.totalDisputes).to.equal(0);
      expect(record.consecutiveWins).to.equal(0);
    });
  });

  describe("Submit Evidence", function () {
    let disputeId;

    beforeEach(async function () {
      // Register arbitrators
      await disputeContract.connect(arbitrator1).registerArbitrator();
      await disputeContract.connect(arbitrator2).registerArbitrator();
      await disputeContract.connect(arbitrator3).registerArbitrator();

      // Set governance contract to owner for testing
      await disputeContract.setGovernanceContract(owner.address);

      // Make them eligible
      await disputeContract.connect(owner).passExam(arbitrator1.address);
      await disputeContract.connect(owner).passExam(arbitrator2.address);
      await disputeContract.connect(owner).passExam(arbitrator3.address);

      // Set minimum votes for eligibility
      await disputeContract.setArbitratorVotes(arbitrator1.address, 10);
      await disputeContract.setArbitratorVotes(arbitrator2.address, 10);
      await disputeContract.setArbitratorVotes(arbitrator3.address, 10);

      // Get current dispute count
      const countBefore = await disputeContract.disputeCounter();

      await disputeContract.connect(plaintiff).createDispute(defendant.address, ethers.parseEther("100"), "test");

      disputeId = countBefore + 1n;
      await disputeContract.connect(defendant).respondToDispute(disputeId);
    });

    it("Should allow plaintiff to submit evidence", async function () {
      await expect(disputeContract.connect(plaintiff).submitEvidence(disputeId, "ipfs://evidence-hash"))
        .to.emit(disputeContract, "EvidenceSubmitted")
        .withArgs(disputeId, plaintiff.address, "ipfs://evidence-hash");
    });

    it("Should allow defendant to submit evidence", async function () {
      await expect(disputeContract.connect(defendant).submitEvidence(disputeId, "ipfs://evidence-hash"))
        .to.emit(disputeContract, "EvidenceSubmitted")
        .withArgs(disputeId, defendant.address, "ipfs://evidence-hash");
    });

    it("Should fail if not party to dispute", async function () {
      await expect(
        disputeContract.connect(other).submitEvidence(disputeId, "ipfs://evidence-hash")
      ).to.be.revertedWith("Only parties");
    });
  });

  describe("Admin Functions", function () {
    it("Should allow owner to set staking contract", async function () {
      await disputeContract.setStakingContract(other.address);
      expect(await disputeContract.stakingContract()).to.equal(other.address);
    });

    it("Should allow owner to set governance contract", async function () {
      await disputeContract.setGovernanceContract(other.address);
      expect(await disputeContract.governanceContract()).to.equal(other.address);
    });

    it("Should fail if not owner", async function () {
      await expect(
        disputeContract.connect(other).setStakingContract(other.address)
      ).to.be.reverted; // Ownable error
    });
  });
});
