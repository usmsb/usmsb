const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("VIBEToken DistributeToPools", function () {
  let vibeToken;
  let vibOutputReward;
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
  const EMISSION_AMOUNT = ethers.parseUnits("500000000", 18);   // 50% → EC
  const OUTPUT_AMOUNT = ethers.parseUnits("130000000", 18);     // 13% → outputRewardPool

  beforeEach(async function () {
    [owner, addr1, addr2] = await ethers.getSigners();

    // 部署 VIBEToken (构造函数只接受 name 和 symbol)
    const VIBEToken = await ethers.getContractFactory("VIBEToken");
    vibeToken = await VIBEToken.deploy("VIBE Token", "VIBE");
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

    // 部署 EmissionController (6 参数)
    const EmissionController = await ethers.getContractFactory("src/automation/EmissionController.sol:EmissionController");
    emissionController = await EmissionController.deploy(
      await vibeToken.getAddress(),
      owner.address,        // _stakingPool
      owner.address,        // _ecosystemPool
      owner.address,        // _governancePool
      owner.address,        // _reservePool
      owner.address         // _outputRewardPool
    );
    await emissionController.waitForDeployment();

    // 部署 VIBOutputReward (distributeToPools 需要)
    const VIBOutputReward = await ethers.getContractFactory("VIBOutputReward");
    vibOutputReward = await VIBOutputReward.deploy(
      await vibeToken.getAddress(),
      owner.address
    );
    await vibOutputReward.waitForDeployment();
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
      // 执行分配 - distributeToPools 7参数签名
      // (emissionController, outputRewardPool, teamVesting, earlySupporterVesting, communityFund, liquidityManager, airdropDistributor)
      await vibeToken.distributeToPools(
        await emissionController.getAddress(),  // 63% - 激励池
        await vibOutputReward.getAddress(),     // 13% - 产出池(由EC管理)
        await teamVesting.getAddress(),        // 8%
        await earlyVesting.getAddress(),       // 4%
        await communityStableFund.getAddress(), // 6%
        await liquidityManager.getAddress(),    // 12%
        await airdropDistributor.getAddress()   // 7%
      );

      // 验证各池余额
      expect(await vibeToken.balanceOf(await teamVesting.getAddress())).to.equal(TEAM_AMOUNT);
      expect(await vibeToken.balanceOf(await earlyVesting.getAddress())).to.equal(EARLY_AMOUNT);
      expect(await vibeToken.balanceOf(await communityStableFund.getAddress())).to.equal(STABLE_FUND_AMOUNT);
      expect(await vibeToken.balanceOf(await liquidityManager.getAddress())).to.equal(LIQUIDITY_AMOUNT);
      expect(await vibeToken.balanceOf(await airdropDistributor.getAddress())).to.equal(AIRDROP_AMOUNT);
      expect(await vibeToken.balanceOf(await emissionController.getAddress())).to.equal(EMISSION_AMOUNT);
      expect(await vibeToken.balanceOf(await vibOutputReward.getAddress())).to.equal(OUTPUT_AMOUNT);
    });

    it("Should set tokensDistributed to true after distribution", async function () {
      expect(await vibeToken.tokensDistributed()).to.be.false;

      await vibeToken.distributeToPools(
        await emissionController.getAddress(),
        await vibOutputReward.getAddress(),
        await teamVesting.getAddress(),
        await earlyVesting.getAddress(),
        await communityStableFund.getAddress(),
        await liquidityManager.getAddress(),
        await airdropDistributor.getAddress()
      );

      expect(await vibeToken.tokensDistributed()).to.be.true;
    });

    it("Should set emission controller address", async function () {
      await vibeToken.distributeToPools(
        await emissionController.getAddress(),
        await vibOutputReward.getAddress(),
        await teamVesting.getAddress(),
        await earlyVesting.getAddress(),
        await communityStableFund.getAddress(),
        await liquidityManager.getAddress(),
        await airdropDistributor.getAddress()
      );

      expect(await vibeToken.emissionController()).to.equal(await emissionController.getAddress());
    });

    it("Should set tax exempt for all pool addresses", async function () {
      await vibeToken.distributeToPools(
        await emissionController.getAddress(),
        await vibOutputReward.getAddress(),
        await teamVesting.getAddress(),
        await earlyVesting.getAddress(),
        await communityStableFund.getAddress(),
        await liquidityManager.getAddress(),
        await airdropDistributor.getAddress()
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
        await emissionController.getAddress(),
        await vibOutputReward.getAddress(),
        await teamVesting.getAddress(),
        await earlyVesting.getAddress(),
        await communityStableFund.getAddress(),
        await liquidityManager.getAddress(),
        await airdropDistributor.getAddress()
      );

      await expect(
        vibeToken.distributeToPools(
          await emissionController.getAddress(),
          await vibOutputReward.getAddress(),
          await teamVesting.getAddress(),
          await earlyVesting.getAddress(),
          await communityStableFund.getAddress(),
          await liquidityManager.getAddress(),
          await airdropDistributor.getAddress()
        )
      ).to.be.revertedWith("VIBEToken: tokens already distributed");
    });

    it("Should fail if any address is zero", async function () {
      // emissionController is zero
      await expect(
        vibeToken.distributeToPools(
          ethers.ZeroAddress,
          await vibOutputReward.getAddress(),
          await teamVesting.getAddress(),
          await earlyVesting.getAddress(),
          await communityStableFund.getAddress(),
          await liquidityManager.getAddress(),
          await airdropDistributor.getAddress()
        )
      ).to.be.revertedWith("VIBEToken: invalid pool address");

      // outputRewardPool is zero
      await expect(
        vibeToken.distributeToPools(
          await emissionController.getAddress(),
          ethers.ZeroAddress,
          await teamVesting.getAddress(),
          await earlyVesting.getAddress(),
          await communityStableFund.getAddress(),
          await liquidityManager.getAddress(),
          await airdropDistributor.getAddress()
        )
      ).to.be.revertedWith("VIBEToken: invalid pool address");

      // teamVesting is zero
      await expect(
        vibeToken.distributeToPools(
          await emissionController.getAddress(),
          await vibOutputReward.getAddress(),
          ethers.ZeroAddress,
          await earlyVesting.getAddress(),
          await communityStableFund.getAddress(),
          await liquidityManager.getAddress(),
          await airdropDistributor.getAddress()
        )
      ).to.be.revertedWith("VIBEToken: invalid pool address");

      // earlySupporterVesting is zero
      await expect(
        vibeToken.distributeToPools(
          await emissionController.getAddress(),
          await vibOutputReward.getAddress(),
          await teamVesting.getAddress(),
          ethers.ZeroAddress,
          await communityStableFund.getAddress(),
          await liquidityManager.getAddress(),
          await airdropDistributor.getAddress()
        )
      ).to.be.revertedWith("VIBEToken: invalid pool address");

      // communityFund is zero
      await expect(
        vibeToken.distributeToPools(
          await emissionController.getAddress(),
          await vibOutputReward.getAddress(),
          await teamVesting.getAddress(),
          await earlyVesting.getAddress(),
          ethers.ZeroAddress,
          await liquidityManager.getAddress(),
          await airdropDistributor.getAddress()
        )
      ).to.be.revertedWith("VIBEToken: invalid pool address");

      // liquidityManager is zero
      await expect(
        vibeToken.distributeToPools(
          await emissionController.getAddress(),
          await vibOutputReward.getAddress(),
          await teamVesting.getAddress(),
          await earlyVesting.getAddress(),
          await communityStableFund.getAddress(),
          ethers.ZeroAddress,
          await airdropDistributor.getAddress()
        )
      ).to.be.revertedWith("VIBEToken: invalid pool address");

      // airdropDistributor is zero
      await expect(
        vibeToken.distributeToPools(
          await emissionController.getAddress(),
          await vibOutputReward.getAddress(),
          await teamVesting.getAddress(),
          await earlyVesting.getAddress(),
          await communityStableFund.getAddress(),
          await liquidityManager.getAddress(),
          ethers.ZeroAddress
        )
      ).to.be.revertedWith("VIBEToken: invalid pool address");
    });

    it("Should fail if called by non-owner", async function () {
      await expect(
        vibeToken.connect(addr1).distributeToPools(
          await emissionController.getAddress(),
          await vibOutputReward.getAddress(),
          await teamVesting.getAddress(),
          await earlyVesting.getAddress(),
          await communityStableFund.getAddress(),
          await liquidityManager.getAddress(),
          await airdropDistributor.getAddress()
        )
      ).to.be.revertedWithCustomError(vibeToken, "OwnableUnauthorizedAccount");
    });

    it("Should have correct total supply after distribution", async function () {
      await vibeToken.distributeToPools(
        await emissionController.getAddress(),
        await vibOutputReward.getAddress(),
        await teamVesting.getAddress(),
        await earlyVesting.getAddress(),
        await communityStableFund.getAddress(),
        await liquidityManager.getAddress(),
        await airdropDistributor.getAddress()
      );

      const totalSupply = await vibeToken.totalSupply();
      expect(totalSupply).to.equal(TOTAL_SUPPLY);
    });

    it("Should emit TokensDistributed event", async function () {
      await expect(
        vibeToken.distributeToPools(
          await emissionController.getAddress(),  // 63%
          await vibOutputReward.getAddress(),    // 13%
          await teamVesting.getAddress(),         // 8%
          await earlyVesting.getAddress(),        // 4%
          await communityStableFund.getAddress(), // 6%
          await liquidityManager.getAddress(),    // 12%
          await airdropDistributor.getAddress()   // 7%
        )
      ).to.emit(vibeToken, "TokensDistributed");
    });
  });
});
