const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("VIBEToken DistributeToPools", function () {
  let vibeToken;
  let teamVesting;
  let earlyVesting;
  let priceOracle;
  let communityStableFund;
  let liquidityManager;
  let airdropDistributor;
  let emissionController;
  let owner;
  let addr1;
  let addr2;

  const TOTAL_SUPPLY = ethers.parseUnits("1000000000", 18); // 10亿
  const TEAM_AMOUNT = ethers.parseUnits("80000000", 18);     // 8%
  const EARLY_AMOUNT = ethers.parseUnits("40000000", 18);    // 4%
  const STABLE_FUND_AMOUNT = ethers.parseUnits("60000000", 18); // 6%
  const LIQUIDITY_AMOUNT = ethers.parseUnits("120000000", 18);  // 12%
  const AIRDROP_AMOUNT = ethers.parseUnits("70000000", 18);     // 7%
  const EMISSION_AMOUNT = ethers.parseUnits("630000000", 18);   // 63%

  beforeEach(async function () {
    [owner, addr1, addr2] = await ethers.getSigners();

    // 部署 VIBEToken
    const VIBEToken = await ethers.getContractFactory("VIBEToken");
    vibeToken = await VIBEToken.deploy("VIBE Token", "VIBE", owner.address);
    await vibeToken.waitForDeployment();

    // 部署团队锁仓合约
    const VIBVesting = await ethers.getContractFactory("VIBVesting");
    teamVesting = await VIBVesting.deploy(await vibeToken.getAddress());
    await teamVesting.waitForDeployment();

    // 部署早期支持者锁仓合约
    earlyVesting = await VIBVesting.deploy(await vibeToken.getAddress());
    await earlyVesting.waitForDeployment();

    // 部署 PriceOracle
    const PriceOracle = await ethers.getContractFactory("PriceOracle");
    priceOracle = await PriceOracle.deploy(ethers.ZeroAddress, ethers.ZeroAddress, ethers.ZeroAddress);
    await priceOracle.waitForDeployment();

    // 部署 CommunityStableFund (需要非零地址用于验证)
    const CommunityStableFund = await ethers.getContractFactory("CommunityStableFund");
    communityStableFund = await CommunityStableFund.deploy(
      await vibeToken.getAddress(),
      addr1.address, // _weth (使用 addr1 作为 mock)
      await priceOracle.getAddress(),
      addr1.address, // _dexRouter
      ethers.parseUnits("1000", 18) // _minLiquidityThreshold
    );
    await communityStableFund.waitForDeployment();

    // 部署 LiquidityManager
    const LiquidityManager = await ethers.getContractFactory("LiquidityManager");
    liquidityManager = await LiquidityManager.deploy(
      await vibeToken.getAddress(),
      addr1.address, // _weth
      addr1.address, // _dexRouter
      addr1.address  // _dexFactory
    );
    await liquidityManager.waitForDeployment();

    // 部署 AirdropDistributor
    const AirdropDistributor = await ethers.getContractFactory("AirdropDistributor");
    airdropDistributor = await AirdropDistributor.deploy(
      await vibeToken.getAddress(),
      await communityStableFund.getAddress(),
      ethers.ZeroHash // _merkleRoot
    );
    await airdropDistributor.waitForDeployment();

    // 部署 EmissionController
    const EmissionController = await ethers.getContractFactory("src/EmissionController.sol:EmissionController");
    emissionController = await EmissionController.deploy(
      await vibeToken.getAddress(),
      owner.address,
      owner.address,
      owner.address,
      owner.address
    );
    await emissionController.waitForDeployment();
  });

  describe("Deployment", function () {
    it("Should have zero initial supply (tokens minted on distribution)", async function () {
      const balance = await vibeToken.balanceOf(owner.address);
      expect(balance).to.equal(0);
    });

    it("Should have zero total supply after deployment", async function () {
      const totalSupply = await vibeToken.totalSupply();
      expect(totalSupply).to.equal(0); // No tokens minted initially
    });
  });

  describe("distributeToPools", function () {
    it("Should distribute tokens to all pools correctly", async function () {
      // 执行分配 - 现在 distributeToPools 需要6个参数
      await vibeToken.distributeToPools(
        await teamVesting.getAddress(),
        await earlyVesting.getAddress(),
        await communityStableFund.getAddress(),
        await liquidityManager.getAddress(),
        await airdropDistributor.getAddress(),
        await emissionController.getAddress()
      );

      // 验证各池余额
      expect(await vibeToken.balanceOf(await teamVesting.getAddress())).to.equal(TEAM_AMOUNT);
      expect(await vibeToken.balanceOf(await earlyVesting.getAddress())).to.equal(EARLY_AMOUNT);
      expect(await vibeToken.balanceOf(await communityStableFund.getAddress())).to.equal(STABLE_FUND_AMOUNT);
      expect(await vibeToken.balanceOf(await liquidityManager.getAddress())).to.equal(LIQUIDITY_AMOUNT);
      expect(await vibeToken.balanceOf(await airdropDistributor.getAddress())).to.equal(AIRDROP_AMOUNT);
      expect(await vibeToken.balanceOf(await emissionController.getAddress())).to.equal(EMISSION_AMOUNT);
    });

    it("Should set tokensDistributed to true after distribution", async function () {
      expect(await vibeToken.tokensDistributed()).to.be.false;

      await vibeToken.distributeToPools(
        await teamVesting.getAddress(),
        await earlyVesting.getAddress(),
        await communityStableFund.getAddress(),
        await liquidityManager.getAddress(),
        await airdropDistributor.getAddress(),
        await emissionController.getAddress()
      );

      expect(await vibeToken.tokensDistributed()).to.be.true;
    });

    it("Should set emission controller address", async function () {
      await vibeToken.distributeToPools(
        await teamVesting.getAddress(),
        await earlyVesting.getAddress(),
        await communityStableFund.getAddress(),
        await liquidityManager.getAddress(),
        await airdropDistributor.getAddress(),
        await emissionController.getAddress()
      );

      expect(await vibeToken.emissionController()).to.equal(await emissionController.getAddress());
    });

    it("Should set tax exempt for all pool addresses", async function () {
      await vibeToken.distributeToPools(
        await teamVesting.getAddress(),
        await earlyVesting.getAddress(),
        await communityStableFund.getAddress(),
        await liquidityManager.getAddress(),
        await airdropDistributor.getAddress(),
        await emissionController.getAddress()
      );

      expect(await vibeToken.taxExemptedAddresses(await teamVesting.getAddress())).to.be.true;
      expect(await vibeToken.taxExemptedAddresses(await earlyVesting.getAddress())).to.be.true;
      expect(await vibeToken.taxExemptedAddresses(await communityStableFund.getAddress())).to.be.true;
      expect(await vibeToken.taxExemptedAddresses(await liquidityManager.getAddress())).to.be.true;
      expect(await vibeToken.taxExemptedAddresses(await airdropDistributor.getAddress())).to.be.true;
      expect(await vibeToken.taxExemptedAddresses(await emissionController.getAddress())).to.be.true;
    });

    it("Should fail if called twice", async function () {
      await vibeToken.distributeToPools(
        await teamVesting.getAddress(),
        await earlyVesting.getAddress(),
        await communityStableFund.getAddress(),
        await liquidityManager.getAddress(),
        await airdropDistributor.getAddress(),
        await emissionController.getAddress()
      );

      await expect(
        vibeToken.distributeToPools(
          await teamVesting.getAddress(),
          await earlyVesting.getAddress(),
          await communityStableFund.getAddress(),
          await liquidityManager.getAddress(),
          await airdropDistributor.getAddress(),
          await emissionController.getAddress()
        )
      ).to.be.revertedWith("VIBEToken: tokens already distributed");
    });

    it("Should fail if mintTreasury was already called", async function () {
      await vibeToken.mintTreasury();

      await expect(
        vibeToken.distributeToPools(
          await teamVesting.getAddress(),
          await earlyVesting.getAddress(),
          await communityStableFund.getAddress(),
          await liquidityManager.getAddress(),
          await airdropDistributor.getAddress(),
          await emissionController.getAddress()
        )
      ).to.be.revertedWith("VIBEToken: treasury already minted, use distributeFromTreasury instead");
    });

    it("Should fail if any address is zero", async function () {
      // Team vesting is zero
      await expect(
        vibeToken.distributeToPools(
          ethers.ZeroAddress,
          await earlyVesting.getAddress(),
          await communityStableFund.getAddress(),
          await liquidityManager.getAddress(),
          await airdropDistributor.getAddress(),
          await emissionController.getAddress()
        )
      ).to.be.revertedWith("VIBEToken: invalid team vesting");

      // Early supporter vesting is zero
      await expect(
        vibeToken.distributeToPools(
          await teamVesting.getAddress(),
          ethers.ZeroAddress,
          await communityStableFund.getAddress(),
          await liquidityManager.getAddress(),
          await airdropDistributor.getAddress(),
          await emissionController.getAddress()
        )
      ).to.be.revertedWith("VIBEToken: invalid early supporter vesting");

      // Stable fund is zero
      await expect(
        vibeToken.distributeToPools(
          await teamVesting.getAddress(),
          await earlyVesting.getAddress(),
          ethers.ZeroAddress,
          await liquidityManager.getAddress(),
          await airdropDistributor.getAddress(),
          await emissionController.getAddress()
        )
      ).to.be.revertedWith("VIBEToken: invalid stable fund");

      // Liquidity manager is zero
      await expect(
        vibeToken.distributeToPools(
          await teamVesting.getAddress(),
          await earlyVesting.getAddress(),
          await communityStableFund.getAddress(),
          ethers.ZeroAddress,
          await airdropDistributor.getAddress(),
          await emissionController.getAddress()
        )
      ).to.be.revertedWith("VIBEToken: invalid liquidity manager");

      // Airdrop distributor is zero
      await expect(
        vibeToken.distributeToPools(
          await teamVesting.getAddress(),
          await earlyVesting.getAddress(),
          await communityStableFund.getAddress(),
          await liquidityManager.getAddress(),
          ethers.ZeroAddress,
          await emissionController.getAddress()
        )
      ).to.be.revertedWith("VIBEToken: invalid airdrop distributor");

      // Emission controller is zero
      await expect(
        vibeToken.distributeToPools(
          await teamVesting.getAddress(),
          await earlyVesting.getAddress(),
          await communityStableFund.getAddress(),
          await liquidityManager.getAddress(),
          await airdropDistributor.getAddress(),
          ethers.ZeroAddress
        )
      ).to.be.revertedWith("VIBEToken: invalid emission controller");
    });

    it("Should fail if called by non-owner", async function () {
      await expect(
        vibeToken.connect(addr1).distributeToPools(
          await teamVesting.getAddress(),
          await earlyVesting.getAddress(),
          await communityStableFund.getAddress(),
          await liquidityManager.getAddress(),
          await airdropDistributor.getAddress(),
          await emissionController.getAddress()
        )
      ).to.be.revertedWithCustomError(vibeToken, "OwnableUnauthorizedAccount");
    });

    it("Should have correct total supply after distribution", async function () {
      await vibeToken.distributeToPools(
        await teamVesting.getAddress(),
        await earlyVesting.getAddress(),
        await communityStableFund.getAddress(),
        await liquidityManager.getAddress(),
        await airdropDistributor.getAddress(),
        await emissionController.getAddress()
      );

      const totalSupply = await vibeToken.totalSupply();
      expect(totalSupply).to.equal(TOTAL_SUPPLY);
    });

    it("Should emit TokensDistributed event", async function () {
      await expect(
        vibeToken.distributeToPools(
          await teamVesting.getAddress(),
          await earlyVesting.getAddress(),
          await communityStableFund.getAddress(),
          await liquidityManager.getAddress(),
          await airdropDistributor.getAddress(),
          await emissionController.getAddress()
        )
      ).to.emit(vibeToken, "TokensDistributed");
    });
  });

  describe("mintTreasury", function () {
    it("Should fail after distributeToPools", async function () {
      await vibeToken.distributeToPools(
        await teamVesting.getAddress(),
        await earlyVesting.getAddress(),
        await communityStableFund.getAddress(),
        await liquidityManager.getAddress(),
        await airdropDistributor.getAddress(),
        await emissionController.getAddress()
      );

      // distributeToPools sets tokensDistributed=true, so mintTreasury fails with this error
      await expect(vibeToken.mintTreasury()).to.be.revertedWith(
        "VIBEToken: tokens already distributed"
      );
    });
  });
});
