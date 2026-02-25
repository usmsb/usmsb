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
      vibeToken = await VIBEToken.deploy(owner.address);
      await vibeToken.waitForDeployment();

      expect(await vibeToken.name()).to.equal("VIBE");
      expect(await vibeToken.symbol()).to.equal("VIBE");
      expect(await vibeToken.totalSupply()).to.equal(ETH(1_000_000_000));
      expect(await vibeToken.balanceOf(owner.address)).to.equal(ETH(80_000_000)); // 8%
    });

    it("Should mint treasury tokens", async function () {
      await vibeToken.mintTreasury(owner.address);
      expect(await vibeToken.balanceOf(owner.address)).to.equal(ETH(1_000_000_000));
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
      vibeToken = await VIBEToken.deploy(owner.address);
      await vibeToken.waitForDeployment();
      await vibeToken.mintTreasury(owner.address);

      const VIBStaking = await ethers.getContractFactory("VIBStaking");
      staking = await VIBStaking.deploy(await vibeToken.getAddress(), owner.address);
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
      expect(await staking.getTier(addr1.address)).to.equal(2); // Silver (1000-4999)
    });

    it("Should upgrade tier with more stake", async function () {
      await vibeToken.connect(addr1).approve(await staking.getAddress(), ETH(10000));
      await staking.connect(addr1).stake(ETH(10000), 0);

      expect(await staking.getTier(addr1.address)).to.equal(4); // Platinum (10000+)
    });
  });

  describe("VIBVesting", function () {
    before(async function () {
      // Deploy fresh contracts
      const VIBEToken = await ethers.getContractFactory("VIBEToken");
      vibeToken = await VIBEToken.deploy(owner.address);
      await vibeToken.waitForDeployment();
      await vibeToken.mintTreasury(owner.address);

      const VIBVesting = await ethers.getContractFactory("VIBVesting");
      vesting = await VIBVesting.deploy(await vibeToken.getAddress(), owner.address);
      await vesting.waitForDeployment();

      // Transfer tokens to vesting contract
      await vibeToken.transfer(await vesting.getAddress(), ETH(100000));
    });

    it("Should add beneficiary", async function () {
      await vesting.addBeneficiary(addr1.address, 0, ETH(10000)); // Team
      const info = await vesting.getVestingSchedule(addr1.address);
      expect(info.totalAmount).to.equal(ETH(10000));
    });

    it("Should return zero before cliff", async function () {
      const releasable = await vesting.getReleasableAmount(addr1.address);
      expect(releasable).to.equal(0);
    });
  });

  describe("VIBIdentity", function () {
    before(async function () {
      const VIBIdentity = await ethers.getContractFactory("VIBIdentity");
      identity = await VIBIdentity.deploy(owner.address);
      await identity.waitForDeployment();
    });

    it("Should register AI Agent identity", async function () {
      await identity.registerIdentity(addr1.address, 0, "ipfs://metadata1"); // AIAgent
      const id = await identity.identityOf(addr1.address);
      expect(id).to.be.gt(0);
    });

    it("Should prevent transfer (soulbound)", async function () {
      const id = await identity.identityOf(addr1.address);
      await expect(
        identity.connect(addr1).transferFrom(addr1.address, addr2.address, id)
      ).to.be.reverted;
    });

    it("Should get identity info", async function () {
      const info = await identity.getIdentity(addr1.address);
      expect(info.identityType).to.equal(0); // AIAgent
      expect(info.status).to.equal(1); // Active
    });
  });
});
