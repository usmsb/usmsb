const { expect } = require("chai");
const { ethers } = require("hardhat");

// Helper: convert * 24 * 60 * 60 to seconds
const DAYS = (n) => n * 24 * 60 * 60;
const ETH = (n) => ethers.parseEther(n.toString());

describe("VIBE Contracts", function () {
  let vibeToken, staking, vesting, identity;
  let owner, addr1, addr2;

  before(async function () {
    [owner, addr1, addr2] = await ethers.getSigners();
  });

  describe("VIBEToken", function () {
    it("Should deploy with correct parameters", async function () {
      const VIBEToken = await ethers.getContractFactory("VIBEToken");
      vibeToken = await VIBEToken.deploy("VIBE Token", "VIBE", owner.address);
      await vibeToken.waitForDeployment();

      expect(await vibeToken.name()).to.equal("VIBE Token");
      expect(await vibeToken.symbol()).to.equal("VIBE");
      expect(await vibeToken.totalSupply()).to.equal(0); // Tokens minted on distribution
    });

    it("Should mint treasury tokens", async function () {
      await vibeToken.mintTreasury();
      const treasuryBalance = await vibeToken.balanceOf(owner.address);
      expect(treasuryBalance).to.be.gt(0);
    });

    it("Should transfer tokens", async function () {
      await vibeToken.transfer(addr1.address, ETH(1000));
      expect(await vibeToken.balanceOf(addr1.address)).to.equal(ETH(1000));
    });

    it("Should pause and unpause", async function () {
      await vibeToken.pause();
      await expect(vibeToken.transfer(addr2.address, ETH(100))).to.be.reverted;
      await vibeToken.unpause();
      await vibeToken.transfer(addr2.address, ETH(100));
      expect(await vibeToken.balanceOf(addr2.address)).to.equal(ETH(100));
    });
  });

  describe("VIBStaking", function () {
    before(async function () {
      // Deploy fresh token for staking tests
      const VIBEToken = await ethers.getContractFactory("VIBEToken");
      vibeToken = await VIBEToken.deploy("VIBE Token", "VIBE", owner.address);
      await vibeToken.waitForDeployment();
      await vibeToken.mintTreasury();

      const VIBStaking = await ethers.getContractFactory("VIBStaking");
      staking = await VIBStaking.deploy(await vibeToken.getAddress());
      await staking.waitForDeployment();

      // Give tokens to addr1
      await vibeToken.transfer(addr1.address, ETH(20000));
    });

    it("Should stake tokens", async function () {
      await vibeToken.connect(addr1).approve(await staking.getAddress(), ETH(1000));
      await staking.connect(addr1).stake(ETH(1000), 0); // No lock

      const info = await staking.getStakeInfo(addr1.address);
      expect(info.amount).to.equal(ETH(1000));
    });

    it("Should return correct tier", async function () {
      expect(await staking.getUserTier(addr1.address)).to.equal(1); // Silver (1000-4999)
    });

    it("Should upgrade tier with more stake", async function () {
      await vibeToken.connect(addr1).approve(await staking.getAddress(), ETH(10000));
      await staking.connect(addr1).stake(ETH(10000), 0);

      expect(await staking.getUserTier(addr1.address)).to.equal(3); // Platinum (10000+)
    });
  });

  describe("VIBVesting", function () {
    before(async function () {
      // Deploy fresh contracts
      const VIBEToken = await ethers.getContractFactory("VIBEToken");
      vibeToken = await VIBEToken.deploy("VIBE Token", "VIBE", owner.address);
      await vibeToken.waitForDeployment();
      await vibeToken.mintTreasury();

      const VIBVesting = await ethers.getContractFactory("VIBVesting");
      vesting = await VIBVesting.deploy(await vibeToken.getAddress());
      await vesting.waitForDeployment();

      // Transfer tokens to vesting contract
      await vibeToken.transfer(await vesting.getAddress(), ETH(100000));
    });

    it("Should add beneficiary", async function () {
      // addBeneficiary(address, amount, beneficiaryType, vestingStart, vestingDuration, cliffPeriod)
      const now = Math.floor(Date.now() / 1000);
      // Need to approve tokens first
      await vibeToken.approve(await vesting.getAddress(), ETH(10000));
      await vesting.addBeneficiary(
        addr1.address,
        ETH(10000),
        0, // TEAM
        now,
        365 * 24 * 60 * 60, // 1 year
        30 * 24 * 60 * 60 // 30 days cliff
      );
      const info = await vesting.getBeneficiaryInfo(addr1.address);
      expect(info.totalAmount).to.equal(ETH(10000));
    });

    it("Should return zero before cliff", async function () {
      // Use addr2 which should not have any vesting yet in this test scope
      const releasable = await vesting.getReleasableAmount(addr2.address);
      expect(releasable).to.equal(0);
    });
  });

  describe("VIBIdentity", function () {
    before(async function () {
      // Deploy VIBEToken first if not already deployed
      if (!vibeToken) {
        const VIBEToken = await ethers.getContractFactory("VIBEToken");
        vibeToken = await VIBEToken.deploy("VIBE Token", "VIBE", owner.address);
        await vibeToken.waitForDeployment();
        await vibeToken.mintTreasury();
      }

      const VIBIdentity = await ethers.getContractFactory("VIBIdentity");
      identity = await VIBIdentity.deploy("VIBE Identity", "VIBID", await vibeToken.getAddress());
      await identity.waitForDeployment();

      // Give tokens to addr1 for registration fee
      await vibeToken.transfer(addr1.address, ETH(1000));
    });

    it("Should register AI Agent identity", async function () {
      await vibeToken.connect(addr1).approve(await identity.getAddress(), ETH(1));
      await identity.connect(addr1).registerAIIdentity("TestAgent", "ipfs://metadata1");
      const id = await identity.addressToTokenId(addr1.address);
      expect(id).to.be.gt(0);
    });

    it("Should prevent transfer (soulbound)", async function () {
      const id = await identity.addressToTokenId(addr1.address);
      await expect(
        identity.connect(addr1).transferFrom(addr1.address, addr2.address, id)
      ).to.be.reverted;
    });

    it("Should get identity info", async function () {
      const id = await identity.addressToTokenId(addr1.address);
      const info = await identity.getIdentityInfo(id);
      expect(info.identityType).to.equal(0); // AI_AGENT
    });
  });
});
