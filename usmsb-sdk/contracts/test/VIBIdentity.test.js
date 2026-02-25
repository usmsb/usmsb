const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("VIBIdentity", function () {
  let vibeToken, identityContract;
  let owner, addr1, addr2, addr3;

  const REGISTRATION_FEE = ethers.parseEther("100"); // 100 VIBE

  beforeEach(async function () {
    [owner, addr1, addr2, addr3] = await ethers.getSigners();

    // Deploy VIBEToken
    const VIBEToken = await ethers.getContractFactory("VIBEToken");
    vibeToken = await VIBEToken.deploy("VIBE Token", "VIBE", owner.address);
    await vibeToken.waitForDeployment();
    await vibeToken.mintTreasury();

    // Deploy VIBIdentity
    const VIBIdentity = await ethers.getContractFactory("VIBIdentity");
    identityContract = await VIBIdentity.deploy(
      "VIBE Identity SBT",
      "VIBID",
      await vibeToken.getAddress()
    );
    await identityContract.waitForDeployment();

    // Distribute tokens
    await vibeToken.transfer(addr1.address, ethers.parseEther("10000"));
    await vibeToken.transfer(addr2.address, ethers.parseEther("10000"));
  });

  describe("Deployment", function () {
    it("Should set the right name and symbol", async function () {
      expect(await identityContract.name()).to.equal("VIBE Identity SBT");
      expect(await identityContract.symbol()).to.equal("VIBID");
    });

    it("Should set the right token address", async function () {
      expect(await identityContract.vibeToken()).to.equal(await vibeToken.getAddress());
    });

    it("Should set the right owner", async function () {
      expect(await identityContract.owner()).to.equal(owner.address);
    });

    it("Should initialize with zero identity count", async function () {
      expect(await identityContract.identityCount()).to.equal(0);
    });
  });

  describe("Register AI Identity", function () {
    it("Should register AI Agent identity", async function () {
      await vibeToken.connect(addr1).approve(await identityContract.getAddress(), REGISTRATION_FEE);

      await expect(identityContract.connect(addr1).registerAIIdentity("MyAgent", '{"capabilities": ["text", "code"]}', { value: REGISTRATION_FEE }))
        .to.emit(identityContract, "IdentityRegistered");

      const tokenId = await identityContract.getTokenIdByAddress(addr1.address);
      expect(tokenId).to.equal(1);

      const info = await identityContract.getIdentityInfo(tokenId);
      expect(info.owner).to.equal(addr1.address);
      expect(info.identityType).to.equal(0); // AI_AGENT
      expect(info.name).to.equal("MyAgent");
      expect(info.isVerified).to.be.false;
    });

    it("Should fail to register if already registered", async function () {
      await vibeToken.connect(addr1).approve(await identityContract.getAddress(), REGISTRATION_FEE);
      await identityContract.connect(addr1).registerAIIdentity("MyAgent", '{}', { value: REGISTRATION_FEE });

      await expect(identityContract.connect(addr1).registerAIIdentity("MyAgent2", '{}', { value: REGISTRATION_FEE }))
        .to.be.revertedWith("VIBIdentity: already registered");
    });

    it("Should fail with empty name", async function () {
      await vibeToken.connect(addr1).approve(await identityContract.getAddress(), REGISTRATION_FEE);

      await expect(identityContract.connect(addr1).registerAIIdentity("", '{}', { value: REGISTRATION_FEE }))
        .to.be.revertedWith("VIBIdentity: name cannot be empty");
    });

    it("Should fail with duplicate name", async function () {
      await vibeToken.connect(addr1).approve(await identityContract.getAddress(), REGISTRATION_FEE);
      await vibeToken.connect(addr2).approve(await identityContract.getAddress(), REGISTRATION_FEE);

      await identityContract.connect(addr1).registerAIIdentity("UniqueName", '{}', { value: REGISTRATION_FEE });

      await expect(identityContract.connect(addr2).registerAIIdentity("UniqueName", '{}', { value: REGISTRATION_FEE }))
        .to.be.revertedWith("VIBIdentity: name already used");
    });
  });

  describe("Register Human Provider", function () {
    it("Should register human provider identity", async function () {
      await vibeToken.connect(addr1).approve(await identityContract.getAddress(), REGISTRATION_FEE);

      await identityContract.connect(addr1).registerHumanProvider("JohnDoe", '{"skills": ["writing", "translation"]}', { value: REGISTRATION_FEE });

      const tokenId = await identityContract.getTokenIdByAddress(addr1.address);
      const info = await identityContract.getIdentityInfo(tokenId);
      expect(info.identityType).to.equal(1); // HUMAN_PROVIDER
      expect(info.name).to.equal("JohnDoe");
    });
  });

  describe("Register Node Operator", function () {
    it("Should register node operator identity", async function () {
      await vibeToken.connect(addr1).approve(await identityContract.getAddress(), REGISTRATION_FEE);

      await identityContract.connect(addr1).registerNodeOperator("Node1", '{"location": "US-East", "specs": "16GB RAM"}', { value: REGISTRATION_FEE });

      const tokenId = await identityContract.getTokenIdByAddress(addr1.address);
      const info = await identityContract.getIdentityInfo(tokenId);
      expect(info.identityType).to.equal(2); // NODE_OPERATOR
      expect(info.name).to.equal("Node1");
    });
  });

  describe("Register Governance", function () {
    it("Should register governance participant identity", async function () {
      await vibeToken.connect(addr1).approve(await identityContract.getAddress(), REGISTRATION_FEE);

      await identityContract.connect(addr1).registerGovernance("Governor1", '{"proposals": 5, "votes": 42}', { value: REGISTRATION_FEE });

      const tokenId = await identityContract.getTokenIdByAddress(addr1.address);
      const info = await identityContract.getIdentityInfo(tokenId);
      expect(info.identityType).to.equal(3); // GOVERNANCE
      expect(info.name).to.equal("Governor1");
    });
  });

  describe("Update Metadata", function () {
    it("Should allow owner to update metadata", async function () {
      await vibeToken.connect(addr1).approve(await identityContract.getAddress(), REGISTRATION_FEE);
      await identityContract.connect(addr1).registerAIIdentity("MyAgent", '{}', { value: REGISTRATION_FEE });

      const tokenId = await identityContract.getTokenIdByAddress(addr1.address);
      const newMetadata = '{"capabilities": ["text", "code", "image"], "version": 2}';

      await expect(identityContract.connect(addr1).updateMetadata(tokenId, newMetadata))
        .to.emit(identityContract, "IdentityUpdated");

      const info = await identityContract.getIdentityInfo(tokenId);
      expect(info.metadata).to.equal(newMetadata);
    });

    it("Should fail if not owner", async function () {
      await vibeToken.connect(addr1).approve(await identityContract.getAddress(), REGISTRATION_FEE);
      await identityContract.connect(addr1).registerAIIdentity("MyAgent", '{}', { value: REGISTRATION_FEE });

      const tokenId = await identityContract.getTokenIdByAddress(addr1.address);

      await expect(identityContract.connect(addr2).updateMetadata(tokenId, '{}'))
        .to.be.revertedWith("VIBIdentity: not the owner");
    });

    it("Should fail for non-existent token", async function () {
      await expect(identityContract.connect(addr1).updateMetadata(999, '{}'))
        .to.be.revertedWith("VIBIdentity: token does not exist");
    });
  });

  describe("Verify Identity", function () {
    it("Should allow owner to verify identity", async function () {
      await vibeToken.connect(addr1).approve(await identityContract.getAddress(), REGISTRATION_FEE);
      await identityContract.connect(addr1).registerAIIdentity("MyAgent", '{}', { value: REGISTRATION_FEE });

      const tokenId = await identityContract.getTokenIdByAddress(addr1.address);

      await expect(identityContract.verifyIdentity(tokenId, true))
        .to.emit(identityContract, "IdentityVerified");

      const info = await identityContract.getIdentityInfo(tokenId);
      expect(info.isVerified).to.be.true;
    });

    it("Should allow owner to revoke verification", async function () {
      await vibeToken.connect(addr1).approve(await identityContract.getAddress(), REGISTRATION_FEE);
      await identityContract.connect(addr1).registerAIIdentity("MyAgent", '{}', { value: REGISTRATION_FEE });

      const tokenId = await identityContract.getTokenIdByAddress(addr1.address);

      await identityContract.verifyIdentity(tokenId, true);
      await identityContract.verifyIdentity(tokenId, false);

      const info = await identityContract.getIdentityInfo(tokenId);
      expect(info.isVerified).to.be.false;
    });

    it("Should fail if not owner", async function () {
      await vibeToken.connect(addr1).approve(await identityContract.getAddress(), REGISTRATION_FEE);
      await identityContract.connect(addr1).registerAIIdentity("MyAgent", '{}', { value: REGISTRATION_FEE });

      const tokenId = await identityContract.getTokenIdByAddress(addr1.address);

      await expect(identityContract.connect(addr2).verifyIdentity(tokenId, true))
        .to.be.revertedWithCustomError(identityContract, "OwnableUnauthorizedAccount");
    });
  });

  describe("Revoke Identity", function () {
    it("Should allow owner to revoke identity", async function () {
      await vibeToken.connect(addr1).approve(await identityContract.getAddress(), REGISTRATION_FEE);
      await identityContract.connect(addr1).registerAIIdentity("MyAgent", '{}', { value: REGISTRATION_FEE });

      const tokenId = await identityContract.getTokenIdByAddress(addr1.address);

      await expect(identityContract.revokeIdentity(tokenId))
        .to.emit(identityContract, "IdentityRevoked");

      expect(await identityContract.ownerOf(tokenId)).to.be.reverted;
    });

    it("Should free up name after revocation", async function () {
      await vibeToken.connect(addr1).approve(await identityContract.getAddress(), REGISTRATION_FEE);
      await identityContract.connect(addr1).registerAIIdentity("MyAgent", '{}', { value: REGISTRATION_FEE });

      const tokenId = await identityContract.getTokenIdByAddress(addr1.address);
      await identityContract.revokeIdentity(tokenId);

      // Name should be available again
      expect(await identityContract.checkNameAvailable("MyAgent")).to.be.true;
    });

    it("Should allow re-registration after revocation", async function () {
      await vibeToken.connect(addr1).approve(await identityContract.getAddress(), REGISTRATION_FEE * 2);
      await identityContract.connect(addr1).registerAIIdentity("MyAgent", '{}', { value: REGISTRATION_FEE });

      const tokenId = await identityContract.getTokenIdByAddress(addr1.address);
      await identityContract.revokeIdentity(tokenId);

      // Should be able to register again
      await identityContract.connect(addr1).registerAIIdentity("MyAgent", '{}', { value: REGISTRATION_FEE });

      expect(await identityContract.isRegistered(addr1.address)).to.be.true;
    });
  });

  describe("Soulbound Token", function () {
    it("Should prevent token transfer", async function () {
      await vibeToken.connect(addr1).approve(await identityContract.getAddress(), REGISTRATION_FEE);
      await identityContract.connect(addr1).registerAIIdentity("MyAgent", '{}', { value: REGISTRATION_FEE });

      const tokenId = await identityContract.getTokenIdByAddress(addr1.address);

      await expect(
        identityContract.connect(addr1).transferFrom(addr1.address, addr2.address, tokenId)
      ).to.be.revertedWith("VIBIdentity: soulbound tokens cannot be transferred");
    });

    it("Should prevent token approval for transfer", async function () {
      await vibeToken.connect(addr1).approve(await identityContract.getAddress(), REGISTRATION_FEE);
      await identityContract.connect(addr1).registerAIIdentity("MyAgent", '{}', { value: REGISTRATION_FEE });

      const tokenId = await identityContract.getTokenIdByAddress(addr1.address);

      await expect(
        identityContract.connect(addr1).approve(addr2.address, tokenId)
      ).to.be.revertedWith("VIBIdentity: soulbound tokens cannot be transferred");
    });
  });

  describe("View Functions", function () {
    it("Should get identity info", async function () {
      await vibeToken.connect(addr1).approve(await identityContract.getAddress(), REGISTRATION_FEE);
      await identityContract.connect(addr1).registerAIIdentity("MyAgent", '{"test": "data"}', { value: REGISTRATION_FEE });

      const tokenId = await identityContract.getTokenIdByAddress(addr1.address);
      const info = await identityContract.getIdentityInfo(tokenId);

      expect(info.owner).to.equal(addr1.address);
      expect(info.name).to.equal("MyAgent");
      expect(info.metadata).to.equal('{"test": "data"}');
    });

    it("Should check if address is registered", async function () {
      expect(await identityContract.isRegistered(addr1.address)).to.be.false;

      await vibeToken.connect(addr1).approve(await identityContract.getAddress(), REGISTRATION_FEE);
      await identityContract.connect(addr1).registerAIIdentity("MyAgent", '{}', { value: REGISTRATION_FEE });

      expect(await identityContract.isRegistered(addr1.address)).to.be.true;
    });

    it("Should get count by type", async function () {
      await vibeToken.connect(addr1).approve(await identityContract.getAddress(), REGISTRATION_FEE * 2);
      await vibeToken.connect(addr2).approve(await identityContract.getAddress(), REGISTRATION_FEE);

      await identityContract.connect(addr1).registerAIIdentity("Agent1", '{}', { value: REGISTRATION_FEE });
      await identityContract.connect(addr2).registerAIIdentity("Agent2", '{}', { value: REGISTRATION_FEE });
      await identityContract.connect(addr1).registerHumanProvider("Human1", '{}', { value: REGISTRATION_FEE });

      const aiCount = await identityContract.getCountByType(0); // AI_AGENT
      expect(aiCount).to.equal(2);

      const humanCount = await identityContract.getCountByType(1); // HUMAN_PROVIDER
      expect(humanCount).to.equal(1);
    });
  });

  describe("Pause", function () {
    it("Should pause registration", async function () {
      await identityContract.pause();

      await vibeToken.connect(addr1).approve(await identityContract.getAddress(), REGISTRATION_FEE);

      await expect(identityContract.connect(addr1).registerAIIdentity("MyAgent", '{}', { value: REGISTRATION_FEE }))
        .to.be.revertedWithCustomError(identityContract, "EnforcedPause");
    });

    it("Should unpause registration", async function () {
      await identityContract.pause();
      await identityContract.unpause();

      await vibeToken.connect(addr1).approve(await identityContract.getAddress(), REGISTRATION_FEE);

      await expect(identityContract.connect(addr1).registerAIIdentity("MyAgent", '{}', { value: REGISTRATION_FEE }))
        .not.to.be.reverted;
    });
  });

  describe("Token Address Update", function () {
    it("Should allow owner to update token address", async function () {
      const newToken = await (await ethers.getContractFactory("VIBEToken")).deploy(
        "New Token",
        "NEW",
        owner.address
      );
      await newToken.waitForDeployment();

      await expect(identityContract.setVibeToken(await newToken.getAddress()))
        .to.emit(identityContract, "TokenUpdated");

      expect(await identityContract.vibeToken()).to.equal(await newToken.getAddress());
    });

    it("Should fail if not owner", async function () {
      await expect(identityContract.connect(addr1).setVibeToken(addr2.address))
        .to.be.revertedWithCustomError(identityContract, "OwnableUnauthorizedAccount");
    });
  });
});
