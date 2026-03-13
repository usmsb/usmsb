const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

describe("PriceOracle", function () {
  let priceOracle;
  let owner, addr1;

  beforeEach(async function () {
    [owner, addr1] = await ethers.getSigners();

    const PriceOracle = await ethers.getContractFactory("PriceOracle");
    // 部署时不传入真实地址，使用零地址测试基本功能
    priceOracle = await PriceOracle.deploy(
      ethers.ZeroAddress, // chainlinkFeed
      ethers.ZeroAddress, // uniswapV3Pool
      ethers.ZeroAddress  // sushiswapPool
    );
    await priceOracle.waitForDeployment();
  });

  describe("Deployment", function () {
    it("Should set the right owner", async function () {
      expect(await priceOracle.owner()).to.equal(owner.address);
    });

    it("Should have zero lastValidPrice initially", async function () {
      expect(await priceOracle.lastValidPrice()).to.equal(0);
    });
  });

  describe("Price Management", function () {
    it("Should allow owner to set lastValidPrice", async function () {
      const price = ethers.parseEther("0.001"); // 0.001 ETH per VIBE
      await priceOracle.setLastValidPrice(price);
      expect(await priceOracle.lastValidPrice()).to.equal(price);
    });

    it("Should not allow non-owner to set lastValidPrice", async function () {
      const price = ethers.parseEther("0.001");
      await expect(
        priceOracle.connect(addr1).setLastValidPrice(price)
      ).to.be.revertedWithCustomError(priceOracle, "OwnableUnauthorizedAccount");
    });
  });

  describe("Source Management", function () {
    it("Should allow owner to enable/disable sources", async function () {
      await priceOracle.setSourceEnabled("chainlink", false);
      expect(await priceOracle.chainlinkEnabled()).to.equal(false);

      await priceOracle.setSourceEnabled("chainlink", true);
      expect(await priceOracle.chainlinkEnabled()).to.equal(true);
    });

    it("Should allow owner to update source addresses", async function () {
      const mockAddress = addr1.address;
      await priceOracle.setChainlinkFeed(mockAddress);
      expect(await priceOracle.chainlinkFeed()).to.equal(mockAddress);
    });
  });

  describe("Price History", function () {
    it("Should start with empty price history", async function () {
      expect(await priceOracle.getPriceHistoryLength()).to.equal(0);
    });

    it("Should update price history when lastValidPrice is set", async function () {
      const price = ethers.parseEther("0.001");
      await priceOracle.setLastValidPrice(price);

      // 由于没有有效数据源，getPrice() 返回 lastValidPrice
      const currentPrice = await priceOracle.getPrice();
      expect(currentPrice).to.equal(price);
    });
  });

  describe("7-Day Average", function () {
    it("Should return lastValidPrice when no history", async function () {
      const price = ethers.parseEther("0.001");
      await priceOracle.setLastValidPrice(price);

      const avgPrice = await priceOracle.get7DayAverage();
      expect(avgPrice).to.equal(price);
    });
  });
});
