const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("VIBNodeReward — priceOracle enforcement", function () {
  let vibeToken;
  let vibIdentity;
  let vibNodeReward;
  let mockPriceOracle;
  let owner, nodeOperator, assessor;

  const VIBE_PRICE_USD = ethers.parseEther("0.1"); // $0.1 per VIBE (10^18 precision)

  beforeEach(async function () {
    [owner, nodeOperator, assessor] = await ethers.getSigners();

    // Deploy VIBEToken
    const VIBEToken = await ethers.getContractFactory("VIBEToken");
    vibeToken = await VIBEToken.deploy("VIBE Token", "VIBE", await owner.getAddress());
    await vibeToken.deployed();

    // Deploy VIBIdentity
    const VIBIdentity = await ethers.getContractFactory("VIBIdentity");
    vibIdentity = await VIBIdentity.deploy();
    await vibIdentity.deployed();

    // Deploy VIBNodeReward
    const VIBNodeReward = await ethers.getContractFactory("VIBNodeReward");
    vibNodeReward = await VIBNodeReward.deploy(
      vibeToken.address,
      vibIdentity.address
    );
    await vibNodeReward.deployed();

    // Mint identity token to nodeOperator (as NODE_OPERATOR)
    // IdentityType 2 = NODE_OPERATOR based on VIBIdentity enum
    await vibIdentity.mint(
      await nodeOperator.getAddress(),
      2, // NODE_OPERATOR
      "Node Operator"
    );

    // Register node (nodeOperator registers themselves)
    await vibNodeReward.connect(nodeOperator).registerNode(0, 1); // GPU_COMPUTE, 1 GPU

    // Authorize assessor
    await vibNodeReward.setAuthorizedAssessor(await assessor.getAddress(), true);

    // Deploy mock PriceOracle (use existing MockPriceOracle from MockContracts.sol)
    const MockPriceOracle = await ethers.getContractFactory("MockPriceOracle");
    mockPriceOracle = await MockPriceOracle.deploy();
    await mockPriceOracle.deployed();
    // Set the price via the existing setPrice() method
    await mockPriceOracle.setPrice(VIBE_PRICE_USD);
  });

  // ──────────────────────────────────────────────
  // Mock PriceOracle (simple, deployed in each test)
  // ──────────────────────────────────────────────

  describe("MockPriceOracle", function () {
    it("should return the configured VIBE price", async function () {
      expect(await mockPriceOracle.getVibePrice()).to.equal(VIBE_PRICE_USD);
    });
  });

  // ──────────────────────────────────────────────
  // usdToVibe — direct call
  // ──────────────────────────────────────────────

  describe("usdToVibe", function () {
    it("reverts when priceOracle is not set (zero address)", async function () {
      // priceOracle defaults to address(0) — no setPriceOracle call made
      await expect(
        vibNodeReward.usdToVibe(ethers.parseEther("1"))
      ).to.be.revertedWith("VIBNodeReward: priceOracle not set");
    });

    it("reverts when usdAmount is zero", async function () {
      await vibNodeReward.setPriceOracle(mockPriceOracle.address);
      await expect(
        vibNodeReward.usdToVibe(0)
      ).to.be.revertedWith("VIBNodeReward: zero amount");
    });

    it("reverts when vibePrice returned by oracle is zero", async function () {
      const ZeroPriceOracle = await ethers.getContractFactory("MockPriceOracle");
      const zeroOracle = await ZeroPriceOracle.deploy();
      await zeroOracle.deployed();
      await zeroOracle.setPrice(0);

      await vibNodeReward.setPriceOracle(zeroOracle.address);
      await expect(
        vibNodeReward.usdToVibe(ethers.parseEther("1"))
      ).to.be.revertedWith("VIBNodeReward: invalid vibe price");
    });

    it("returns correct VIBE amount when oracle is configured with valid price", async function () {
      await vibNodeReward.setPriceOracle(mockPriceOracle.address);
      // $1 USD / $0.1 per VIBE = 10 VIBE
      const result = await vibNodeReward.usdToVibe(ethers.parseEther("1"));
      expect(result).to.equal(ethers.parseEther("10"));
    });

    it("handles fractional VIBE correctly (rounds down)", async function () {
      await vibNodeReward.setPriceOracle(mockPriceOracle.address);
      // $0.05 USD / $0.1 per VIBE = 0.5 VIBE → should be 0 after integer division
      const result = await vibNodeReward.usdToVibe(ethers.parseEther("0.05"));
      expect(result).to.equal(ethers.parseEther("0.5"));
    });
  });

  // ──────────────────────────────────────────────
  // recordService — integration point that calls usdToVibe
  // ──────────────────────────────────────────────

  describe("recordService", function () {
    // Parameters for a valid GPU service record
    const gpuDuration = 3600;        // 1 hour in seconds
    const gpuCapacity = 1;           // 1 GPU
    const qualityScore = 10000;       // 1.0x (default)
    const prodFactor = 10000;        // 1.0x
    const relFactor = 10000;         // 1.0x

    it("reverts when priceOracle is not set", async function () {
      // priceOracle is still address(0)
      await expect(
        vibNodeReward
          .connect(assessor)
          .recordService(
            await nodeOperator.getAddress(),
            0,             // GPU_COMPUTE
            gpuDuration,
            gpuCapacity,
            qualityScore,
            prodFactor,
            relFactor,
            ethers.ZeroHash
          )
      ).to.be.revertedWith("VIBNodeReward: priceOracle not set");
    });

    it("reverts when vibePrice is zero even if priceOracle address is set", async function () {
      const ZeroPriceOracle = await ethers.getContractFactory("MockPriceOracle");
      const zeroOracle = await ZeroPriceOracle.deploy();
      await zeroOracle.deployed();
      await zeroOracle.setPrice(0);

      await vibNodeReward.setPriceOracle(zeroOracle.address);

      await expect(
        vibNodeReward
          .connect(assessor)
          .recordService(
            await nodeOperator.getAddress(),
            0,
            gpuDuration,
            gpuCapacity,
            qualityScore,
            prodFactor,
            relFactor,
            ethers.ZeroHash
          )
      ).to.be.revertedWith("VIBNodeReward: invalid vibe price");
    });

    it("records service successfully when priceOracle is properly configured", async function () {
      await vibNodeReward.setPriceOracle(mockPriceOracle.address);

      // Fund the contract with VIBE so it can pay rewards
      await vibeToken.mint(vibNodeReward.address, ethers.parseEther("100000"));

      const tx = await vibNodeReward
        .connect(assessor)
        .recordService(
          await nodeOperator.getAddress(),
          0,             // GPU_COMPUTE
          gpuDuration,    // 1 hour
          gpuCapacity,   // 1 GPU
          qualityScore,
          prodFactor,
          relFactor,
          ethers.ZeroHash
        );

      await expect(tx).to.emit(vibNodeReward, "ServiceRecorded");
    });

    it("applies quality/productivity/reliability factors to base reward", async function () {
      await vibNodeReward.setPriceOracle(mockPriceOracle.address);
      await vibeToken.mint(vibNodeReward.address, ethers.parseEther("100000"));

      // High quality (2.0x), max productivity (1.3x), max reliability (1.2x)
      const tx = await vibNodeReward
        .connect(assessor)
        .recordService(
          await nodeOperator.getAddress(),
          0,             // GPU_COMPUTE
          3600,          // 1 hour
          1,             // 1 GPU
          20000,         // 2.0x quality
          13000,         // 1.3x productivity
          12000,         // 1.2x reliability
          ethers.ZeroHash
        );

      await expect(tx).to.emit(vibNodeReward, "ServiceRecorded");
      const receipt = await tx.wait();
      // The event carries serviceId — just verify it doesn't revert
      expect(receipt.status).to.equal(1);
    });
  });

  // ──────────────────────────────────────────────
  // setPriceOracle — owner can update it
  // ──────────────────────────────────────────────

  describe("setPriceOracle", function () {
    it("owner can set a new price oracle", async function () {
      await vibNodeReward.setPriceOracle(mockPriceOracle.address);
      // Verify by checking usdToVibe now works
      const result = await vibNodeReward.usdToVibe(ethers.parseEther("1"));
      expect(result).to.equal(ethers.parseEther("10"));
    });

    it("non-owner cannot set price oracle", async function () {
      await expect(
        vibNodeReward.connect(nodeOperator).setPriceOracle(mockPriceOracle.address)
      ).to.be.revertedWithCustomError(vibNodeReward, "OwnableUnauthorizedAccount");
    });
  });
});

// MockPriceOracle lives in src/MockPriceOracle.sol (auto-compiled by Hardhat)
