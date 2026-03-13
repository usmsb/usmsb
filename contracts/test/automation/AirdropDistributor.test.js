const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

describe("AirdropDistributor", function () {
  let vibeToken, airdropDistributor;
  let owner, communityFund, user1, user2;

  const AIRDROP_AMOUNT = ethers.parseEther("70000000"); // 7000万
  const NORMAL_PERIOD = 180 * 24 * 60 * 60; // 6个月
  const DELAY_PERIOD = 180 * 24 * 60 * 60; // 6个月

  // 简单的 Merkle Tree 测试数据
  const merkleRoot = "0x0000000000000000000000000000000000000000000000000000000000000001";

  beforeEach(async function () {
    [owner, communityFund, user1, user2] = await ethers.getSigners();

    // 部署 VIBE Token
    const VIBEToken = await ethers.getContractFactory("VIBEToken");
    vibeToken = await VIBEToken.deploy("VIBE Token", "VIBE", owner.address);
    await vibeToken.waitForDeployment();
    await vibeToken.mintTreasury();

    // 部署 AirdropDistributor
    const AirdropDistributor = await ethers.getContractFactory("AirdropDistributor");
    airdropDistributor = await AirdropDistributor.deploy(
      await vibeToken.getAddress(),
      communityFund.address,
      merkleRoot
    );
    await airdropDistributor.waitForDeployment();

    // 转移空投代币
    await vibeToken.transfer(await airdropDistributor.getAddress(), AIRDROP_AMOUNT);
  });

  describe("Deployment", function () {
    it("Should set correct parameters", async function () {
      expect(await airdropDistributor.vibeToken()).to.equal(await vibeToken.getAddress());
      expect(await airdropDistributor.communityStableFund()).to.equal(communityFund.address);
      expect(await airdropDistributor.merkleRoot()).to.equal(merkleRoot);
    });

    it("Should have correct time constants", async function () {
      expect(await airdropDistributor.NORMAL_PERIOD()).to.equal(NORMAL_PERIOD);
      expect(await airdropDistributor.DELAY_PERIOD()).to.equal(DELAY_PERIOD);
      expect(await airdropDistributor.DELAY_PERIOD_RATIO()).to.equal(5000); // 50%
    });

    it("Should not be started initially", async function () {
      expect(await airdropDistributor.startTime()).to.equal(0);
    });
  });

  describe("Start Airdrop", function () {
    it("Should start airdrop correctly", async function () {
      await airdropDistributor.startAirdrop();

      const startTime = await airdropDistributor.startTime();
      expect(startTime).to.be.gt(0);

      const endTime = await airdropDistributor.endTime();
      expect(endTime - startTime).to.equal(NORMAL_PERIOD + DELAY_PERIOD);
    });

    it("Should fail to start twice", async function () {
      await airdropDistributor.startAirdrop();

      await expect(
        airdropDistributor.startAirdrop()
      ).to.be.revertedWith("Already started");
    });

    it("Should only be callable by owner", async function () {
      await expect(
        airdropDistributor.connect(user1).startAirdrop()
      ).to.be.revertedWithCustomError(airdropDistributor, "OwnableUnauthorizedAccount");
    });
  });

  describe("Phase Detection", function () {
    it("Should return 'Not started' before start", async function () {
      const [phase, ratio, remaining] = await airdropDistributor.getCurrentPhase();
      expect(phase).to.equal("Not started");
    });

    it("Should return 'Normal (100%)' in first 6 months", async function () {
      await airdropDistributor.startAirdrop();
      const [phase, ratio, remaining] = await airdropDistributor.getCurrentPhase();
      expect(phase).to.equal("Normal (100%)");
      expect(ratio).to.equal(10000);
    });

    it("Should return 'Delay (50%)' in months 7-12", async function () {
      await airdropDistributor.startAirdrop();
      await time.increase(NORMAL_PERIOD);
      const [phase, ratio, remaining] = await airdropDistributor.getCurrentPhase();
      expect(phase).to.equal("Delay (50%)");
      expect(ratio).to.equal(5000);
    });

    it("Should return 'Ended' after 12 months", async function () {
      await airdropDistributor.startAirdrop();
      await time.increase(NORMAL_PERIOD + DELAY_PERIOD);
      const [phase, ratio, remaining] = await airdropDistributor.getCurrentPhase();
      expect(phase).to.equal("Ended");
    });
  });

  describe("Claimable Amount", function () {
    it("Should return 100% in normal period", async function () {
      await airdropDistributor.startAirdrop();
      const amount = ethers.parseEther("1000");
      const [userAmount, fundAmount, status] = await airdropDistributor.getClaimableAmount(user1.address, amount);

      expect(userAmount).to.equal(amount);
      expect(fundAmount).to.equal(0);
      expect(status).to.equal("Claimable");
    });

    it("Should return 50% in delay period", async function () {
      await airdropDistributor.startAirdrop();
      await time.increase(NORMAL_PERIOD);
      const amount = ethers.parseEther("1000");
      const [userAmount, fundAmount, status] = await airdropDistributor.getClaimableAmount(user1.address, amount);

      expect(userAmount).to.equal(amount / 2n);
      expect(fundAmount).to.equal(amount / 2n);
    });

    it("Should return 'Not started' before start", async function () {
      const amount = ethers.parseEther("1000");
      const [userAmount, fundAmount, status] = await airdropDistributor.getClaimableAmount(user1.address, amount);
      expect(status).to.equal("Not started");
    });

    it("Should return 'Ended' after 12 months", async function () {
      await airdropDistributor.startAirdrop();
      await time.increase(NORMAL_PERIOD + DELAY_PERIOD + 1);
      const amount = ethers.parseEther("1000");
      const [userAmount, fundAmount, status] = await airdropDistributor.getClaimableAmount(user1.address, amount);
      expect(status).to.equal("Ended");
    });
  });

  describe("Merkle Root Management", function () {
    it("Should allow owner to update merkle root before start", async function () {
      const newRoot = "0x0000000000000000000000000000000000000000000000000000000000000002";
      await airdropDistributor.setMerkleRoot(newRoot);
      expect(await airdropDistributor.merkleRoot()).to.equal(newRoot);
    });

    it("Should not allow update after start", async function () {
      await airdropDistributor.startAirdrop();
      const newRoot = "0x0000000000000000000000000000000000000000000000000000000000000002";

      await expect(
        airdropDistributor.setMerkleRoot(newRoot)
      ).to.be.revertedWith("Airdrop already started");
    });
  });

  describe("Sweep Unclaimed", function () {
    it("Should fail before airdrop ends", async function () {
      await airdropDistributor.startAirdrop();
      await expect(
        airdropDistributor.sweepUnclaimed()
      ).to.be.revertedWith("Airdrop not ended");
    });

    it("Should succeed after airdrop ends", async function () {
      await airdropDistributor.startAirdrop();
      await time.increase(NORMAL_PERIOD + DELAY_PERIOD + 1);

      const fundBalanceBefore = await vibeToken.balanceOf(communityFund.address);
      await airdropDistributor.sweepUnclaimed();
      const fundBalanceAfter = await vibeToken.balanceOf(communityFund.address);

      expect(fundBalanceAfter).to.be.gt(fundBalanceBefore);
      expect(await airdropDistributor.swept()).to.equal(true);
    });

    it("Should fail if already swept", async function () {
      await airdropDistributor.startAirdrop();
      await time.increase(NORMAL_PERIOD + DELAY_PERIOD + 1);
      await airdropDistributor.sweepUnclaimed();

      await expect(
        airdropDistributor.sweepUnclaimed()
      ).to.be.revertedWith("Already swept");
    });
  });

  describe("Stats", function () {
    it("Should return correct stats", async function () {
      const [totalClaimed, claimerCount, remaining, startTime, endTime, swept] =
        await airdropDistributor.getStats();

      expect(totalClaimed).to.equal(0);
      expect(claimerCount).to.equal(0);
      expect(remaining).to.equal(AIRDROP_AMOUNT);
      expect(startTime).to.equal(0);
      expect(swept).to.equal(false);
    });
  });
});
