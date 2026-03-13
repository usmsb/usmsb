import { expect } from "chai";
import { ethers } from "hardhat";
import { VIBIdentity } from "../../typechain-types";
import { Signer } from "ethers";
import { getSigners, expectEvent, expectRevertCustomError } from "../utils/fixtures";
import { IDENTITY_TYPES, IDENTITY_METADATA, ERROR_MESSAGES } from "../utils/constants";

describe("VIBIdentity", function () {
  let vibIdentity: VIBIdentity;
  let signers: any;
  let owner: Signer;
  let user1: Signer;
  let user2: Signer;

  beforeEach(async function () {
    signers = await getSigners();
    owner = signers.owner;
    user1 = signers.user1;
    user2 = signers.user2;

    // Deploy VIBIdentity
    const VIBIdentity = await ethers.getContractFactory("VIBIdentity");
    vibIdentity = (await VIBIdentity.deploy()) as VIBIdentity;
    await vibIdentity.deployed();
  });

  describe("Deployment", function () {
    it("Should set the correct name", async function () {
      expect(await vibIdentity.name()).to.equal("VIBE Identity");
    });

    it("Should set the correct symbol", async function () {
      expect(await vibIdentity.symbol()).to.equal("VIBE-SBT");
    });

    it("Should set the correct admin", async function () {
      expect(await vibIdentity.admin()).to.equal(await owner.getAddress());
    });

    it("Should initialize with zero supply", async function () {
      expect(await vibIdentity.totalSupply()).to.equal(0);
    });

    it("Should initialize with counter at 1", async function () {
      expect(await vibIdentity.counter()).to.equal(1);
    });
  });

  describe("Mint SBT", function () {
    const metadata = "Test User Metadata";

    it("Should mint SBT successfully", async function () {
      const user1Address = await user1.getAddress();

      await vibIdentity.mint(user1Address, IDENTITY_TYPES.VERIFIED, metadata);

      expect(await vibIdentity.balanceOf(user1Address)).to.equal(1);
      expect(await vibIdentity.totalSupply()).to.equal(1);
    });

    it("Should emit Minted event", async function () {
      const user1Address = await user1.getAddress();

      await expectEvent(
        vibIdentity.mint(user1Address, IDENTITY_TYPES.VERIFIED, metadata),
        vibIdentity,
        "Minted",
        [1, user1Address, IDENTITY_TYPES.VERIFIED, metadata]
      );
    });

    it("Should increment counter after mint", async function () {
      const user1Address = await user1.getAddress();

      await vibIdentity.mint(user1Address, IDENTITY_TYPES.VERIFIED, metadata);
      await vibIdentity.mint(await user2.getAddress(), IDENTITY_TYPES.KYC_VERIFIED, metadata);

      expect(await vibIdentity.counter()).to.equal(3);
    });

    it("Should store identity metadata correctly", async function () {
      const user1Address = await user1.getAddress();
      await vibIdentity.mint(user1Address, IDENTITY_TYPES.VERIFIED, metadata);

      const tokenId = await vibIdentity.getIdentityTokenId(user1Address);
      const identity = await vibIdentity.getIdentity(tokenId);

      expect(identity.owner).to.equal(user1Address);
      expect(identity.identityType).to.equal(IDENTITY_TYPES.VERIFIED);
      expect(identity.metadata).to.equal(metadata);
    });

    it("Should emit Transfer event on mint", async function () {
      const user1Address = await user1.getAddress();

      const tx = await vibIdentity.mint(user1Address, IDENTITY_TYPES.VERIFIED, metadata);
      const receipt = await tx.wait();
      const event = receipt.events?.find((e: any) => e.event === "Transfer");

      expect(event).to.not.be.undefined;
      expect(event.args.from).to.equal(ethers.constants.AddressZero);
      expect(event.args.to).to.equal(user1Address);
      expect(event.args.tokenId).to.equal(1);
    });

    it("Should fail when minting to zero address", async function () {
      await expectRevertCustomError(
        vibIdentity.mint(ethers.constants.AddressZero, IDENTITY_TYPES.VERIFIED, metadata),
        vibIdentity,
        "InvalidAddress"
      );
    });

    it("Should fail when metadata is empty", async function () {
      const user1Address = await user1.getAddress();

      await expectRevertCustomError(
        vibIdentity.mint(user1Address, IDENTITY_TYPES.VERIFIED, ""),
        vibIdentity,
        "InvalidMetadata"
      );
    });

    it("Should fail when minting duplicate identity", async function () {
      const user1Address = await user1.getAddress();

      await vibIdentity.mint(user1Address, IDENTITY_TYPES.VERIFIED, metadata);

      await expectRevertCustomError(
        vibIdentity.mint(user1Address, IDENTITY_TYPES.KYC_VERIFIED, metadata),
        vibIdentity,
        "AlreadyMinted"
      );
    });

    it("Should fail when non-admin tries to mint", async function () {
      const user1Address = await user1.getAddress();

      await expectRevertCustomError(
        vibIdentity.connect(user1).mint(user1Address, IDENTITY_TYPES.VERIFIED, metadata),
        vibIdentity,
        "Unauthorized"
      );
    });
  });

  describe("Transfer Restrictions", function () {
    const metadata = "Test User Metadata";

    beforeEach(async function () {
      await vibIdentity.mint(await user1.getAddress(), IDENTITY_TYPES.VERIFIED, metadata);
    });

    it("Should fail when transferring SBT", async function () {
      const user1Address = await user1.getAddress();
      const user2Address = await user2.getAddress();
      const tokenId = await vibIdentity.getIdentityTokenId(user1Address);

      await expectRevertCustomError(
        vibIdentity.connect(user1).transferFrom(user1Address, user2Address, tokenId),
        vibIdentity,
        "TransferRestricted"
      );
    });

    it("Should fail when safeTransferring SBT", async function () {
      const user1Address = await user1.getAddress();
      const user2Address = await user2.getAddress();
      const tokenId = await vibIdentity.getIdentityTokenId(user1Address);

      await expectRevertCustomError(
        vibIdentity.connect(user1)["safeTransferFrom(address,address,uint256)"](
          user1Address,
          user2Address,
          tokenId
        ),
        vibIdentity,
        "TransferRestricted"
      );
    });

    it("Should fail when safeTransferring with data", async function () {
      const user1Address = await user1.getAddress();
      const user2Address = await user2.getAddress();
      const tokenId = await vibIdentity.getIdentityTokenId(user1Address);

      await expectRevertCustomError(
        vibIdentity.connect(user1)["safeTransferFrom(address,address,uint256,bytes)"](
          user1Address,
          user2Address,
          tokenId,
          "0x"
        ),
        vibIdentity,
        "TransferRestricted"
      );
    });

    it("Should fail when approving transfer", async function () {
      const user1Address = await user1.getAddress();
      const user2Address = await user2.getAddress();
      const tokenId = await vibIdentity.getIdentityTokenId(user1Address);

      await expectRevertCustomError(
        vibIdentity.connect(user1).approve(user2Address, tokenId),
        vibIdentity,
        "TransferRestricted"
      );
    });

    it("Should fail when setting approval for all", async function () {
      const user1Address = await user1.getAddress();
      const user2Address = await user2.getAddress();

      await expectRevertCustomError(
        vibIdentity.connect(user1).setApprovalForAll(user2Address, true),
        vibIdentity,
        "TransferRestricted"
      );
    });
  });

  describe("Identity Token ID", function () {
    const metadata = "Test User Metadata";

    it("Should return correct token ID for owner", async function () {
      const user1Address = await user1.getAddress();

      await vibIdentity.mint(user1Address, IDENTITY_TYPES.VERIFIED, metadata);

      const tokenId = await vibIdentity.getIdentityTokenId(user1Address);
      expect(tokenId).to.equal(1);
    });

    it("Should return zero for non-owner", async function () {
      const user1Address = await user1.getAddress();
      const user2Address = await user2.getAddress();

      await vibIdentity.mint(user1Address, IDENTITY_TYPES.VERIFIED, metadata);

      const tokenId = await vibIdentity.getIdentityTokenId(user2Address);
      expect(tokenId).to.equal(0);
    });

    it("Should return correct token ID for second mint", async function () {
      const user1Address = await user1.getAddress();

      await vibIdentity.mint(user1Address, IDENTITY_TYPES.VERIFIED, metadata);
      await vibIdentity.mint(await user2.getAddress(), IDENTITY_TYPES.KYC_VERIFIED, metadata);

      const tokenId1 = await vibIdentity.getIdentityTokenId(user1Address);
      const tokenId2 = await vibIdentity.getIdentityTokenId(await user2.getAddress());

      expect(tokenId1).to.equal(1);
      expect(tokenId2).to.equal(2);
    });
  });

  describe("Get Identity", function () {
    const metadata = "Test User Metadata";

    beforeEach(async function () {
      await vibIdentity.mint(await user1.getAddress(), IDENTITY_TYPES.KYC_VERIFIED, metadata);
    });

    it("Should return correct identity information", async function () {
      const user1Address = await user1.getAddress();
      const tokenId = await vibIdentity.getIdentityTokenId(user1Address);

      const identity = await vibIdentity.getIdentity(tokenId);

      expect(identity.owner).to.equal(user1Address);
      expect(identity.identityType).to.equal(IDENTITY_TYPES.KYC_VERIFIED);
      expect(identity.metadata).to.equal(metadata);
      expect(identity.mintedAt.gt(0)).to.be.true;
    });

    it("Should return zero address for non-existent token", async function () {
      const identity = await vibIdentity.getIdentity(999);
      expect(identity.owner).to.equal(ethers.constants.AddressZero);
    });
  });

  describe("Has Identity", function () {
    const metadata = "Test User Metadata";

    it("Should return true for verified identity", async function () {
      const user1Address = await user1.getAddress();
      await vibIdentity.mint(user1Address, IDENTITY_TYPES.VERIFIED, metadata);

      expect(await vibIdentity.hasIdentity(user1Address)).to.be.true;
    });

    it("Should return false for non-existent identity", async function () {
      const user1Address = await user1.getAddress();

      expect(await vibIdentity.hasIdentity(user1Address)).to.be.false;
    });

    it("Should return true for KYC verified identity", async function () {
      const user1Address = await user1.getAddress();
      await vibIdentity.mint(user1Address, IDENTITY_TYPES.KYC_VERIFIED, metadata);

      expect(await vibIdentity.hasIdentity(user1Address)).to.be.true;
    });

    it("Should return true for institution identity", async function () {
      const user1Address = await user1.getAddress();
      await vibIdentity.mint(user1Address, IDENTITY_TYPES.INSTITUTION, metadata);

      expect(await vibIdentity.hasIdentity(user1Address)).to.be.true;
    });
  });

  describe("Get Identity Type", function () {
    const metadata = "Test User Metadata";

    it("Should return correct identity type", async function () {
      const user1Address = await user1.getAddress();
      await vibIdentity.mint(user1Address, IDENTITY_TYPES.KYC_VERIFIED, metadata);

      const identityType = await vibIdentity.getIdentityType(user1Address);
      expect(identityType).to.equal(IDENTITY_TYPES.KYC_VERIFIED);
    });

    it("Should return zero for non-existent identity", async function () {
      const user1Address = await user1.getAddress();

      const identityType = await vibIdentity.getIdentityType(user1Address);
      expect(identityType).to.equal(0);
    });
  });

  describe("Burn SBT", function () {
    const metadata = "Test User Metadata";

    beforeEach(async function () {
      await vibIdentity.mint(await user1.getAddress(), IDENTITY_TYPES.VERIFIED, metadata);
    });

    it("Should allow admin to burn SBT", async function () {
      const user1Address = await user1.getAddress();
      const tokenId = await vibIdentity.getIdentityTokenId(user1Address);

      await vibIdentity.burn(tokenId);

      expect(await vibIdentity.balanceOf(user1Address)).to.equal(0);
      expect(await vibIdentity.totalSupply()).to.equal(0);
    });

    it("Should emit Burned event", async function () {
      const user1Address = await user1.getAddress();
      const tokenId = await vibIdentity.getIdentityTokenId(user1Address);

      await expectEvent(
        vibIdentity.burn(tokenId),
        vibIdentity,
        "Burned",
        [tokenId, user1Address]
      );
    });

    it("Should emit Transfer event on burn", async function () {
      const user1Address = await user1.getAddress();
      const tokenId = await vibIdentity.getIdentityTokenId(user1Address);

      const tx = await vibIdentity.burn(tokenId);
      const receipt = await tx.wait();
      const event = receipt.events?.find((e: any) => e.event === "Transfer");

      expect(event).to.not.be.undefined;
      expect(event.args.from).to.equal(user1Address);
      expect(event.args.to).to.equal(ethers.constants.AddressZero);
      expect(event.args.tokenId).to.equal(tokenId);
    });

    it("Should reset identity token ID after burn", async function () {
      const user1Address = await user1.getAddress();
      const tokenId = await vibIdentity.getIdentityTokenId(user1Address);

      await vibIdentity.burn(tokenId);

      const newTokenId = await vibIdentity.getIdentityTokenId(user1Address);
      expect(newTokenId).to.equal(0);
    });

    it("Should allow re-minting after burn", async function () {
      const user1Address = await user1.getAddress();
      const tokenId = await vibIdentity.getIdentityTokenId(user1Address);

      await vibIdentity.burn(tokenId);

      await vibIdentity.mint(user1Address, IDENTITY_TYPES.VERIFIED, metadata);

      expect(await vibIdentity.balanceOf(user1Address)).to.equal(1);
      expect(await vibIdentity.getIdentityTokenId(user1Address)).to.equal(2); // New token ID
    });

    it("Should fail when non-admin tries to burn", async function () {
      const user1Address = await user1.getAddress();
      const tokenId = await vibIdentity.getIdentityTokenId(user1Address);

      await expectRevertCustomError(
        vibIdentity.connect(user1).burn(tokenId),
        vibIdentity,
        "Unauthorized"
      );
    });

    it("Should fail when burning non-existent token", async function () {
      await expectRevertCustomError(
        vibIdentity.burn(999),
        vibIdentity,
        "InvalidTokenId"
      );
    });
  });

  describe("Update Metadata", function () {
    const oldMetadata = "Old Metadata";
    const newMetadata = "New Metadata";

    beforeEach(async function () {
      await vibIdentity.mint(await user1.getAddress(), IDENTITY_TYPES.VERIFIED, oldMetadata);
    });

    it("Should allow admin to update metadata", async function () {
      const user1Address = await user1.getAddress();
      const tokenId = await vibIdentity.getIdentityTokenId(user1Address);

      await vibIdentity.updateMetadata(tokenId, newMetadata);

      const identity = await vibIdentity.getIdentity(tokenId);
      expect(identity.metadata).to.equal(newMetadata);
    });

    it("Should emit MetadataUpdated event", async function () {
      const user1Address = await user1.getAddress();
      const tokenId = await vibIdentity.getIdentityTokenId(user1Address);

      await expectEvent(
        vibIdentity.updateMetadata(tokenId, newMetadata),
        vibIdentity,
        "MetadataUpdated",
        [tokenId, newMetadata]
      );
    });

    it("Should fail when non-admin tries to update metadata", async function () {
      const user1Address = await user1.getAddress();
      const tokenId = await vibIdentity.getIdentityTokenId(user1Address);

      await expectRevertCustomError(
        vibIdentity.connect(user1).updateMetadata(tokenId, newMetadata),
        vibIdentity,
        "Unauthorized"
      );
    });

    it("Should fail when updating to empty metadata", async function () {
      const user1Address = await user1.getAddress();
      const tokenId = await vibIdentity.getIdentityTokenId(user1Address);

      await expectRevertCustomError(
        vibIdentity.updateMetadata(tokenId, ""),
        vibIdentity,
        "InvalidMetadata"
      );
    });
  });

  describe("Batch Mint", function () {
    const metadata = "Batch Metadata";

    it("Should mint multiple SBTs in batch", async function () {
      const users = [
        await user1.getAddress(),
        await user2.getAddress(),
        await signers.user3.getAddress()
      ];
      const identityTypes = [
        IDENTITY_TYPES.VERIFIED,
        IDENTITY_TYPES.KYC_VERIFIED,
        IDENTITY_TYPES.INSTITUTION
      ];

      await vibIdentity.batchMint(users, identityTypes, [metadata, metadata, metadata]);

      expect(await vibIdentity.totalSupply()).to.equal(3);
      expect(await vibIdentity.balanceOf(users[0])).to.equal(1);
      expect(await vibIdentity.balanceOf(users[1])).to.equal(1);
      expect(await vibIdentity.balanceOf(users[2])).to.equal(1);
    });

    it("Should emit Minted events for batch mint", async function () {
      const users = [
        await user1.getAddress(),
        await user2.getAddress()
      ];
      const identityTypes = [
        IDENTITY_TYPES.VERIFIED,
        IDENTITY_TYPES.KYC_VERIFIED
      ];

      const tx = await vibIdentity.batchMint(users, identityTypes, [metadata, metadata]);
      const receipt = await tx.wait();
      const events = receipt.events?.filter((e: any) => e.event === "Minted");

      expect(events).to.not.be.undefined;
      expect(events.length).to.equal(2);
    });

    it("Should fail when arrays have different lengths", async function () {
      const users = [
        await user1.getAddress(),
        await user2.getAddress()
      ];
      const identityTypes = [IDENTITY_TYPES.VERIFIED];

      await expectRevertCustomError(
        vibIdentity.batchMint(users, identityTypes, [metadata, metadata]),
        vibIdentity,
        "InvalidArrayLength"
      );
    });

    it("Should fail when non-admin tries to batch mint", async function () {
      const users = [
        await user1.getAddress(),
        await user2.getAddress()
      ];
      const identityTypes = [
        IDENTITY_TYPES.VERIFIED,
        IDENTITY_TYPES.KYC_VERIFIED
      ];

      await expectRevertCustomError(
        vibIdentity.connect(user1).batchMint(users, identityTypes, [metadata, metadata]),
        vibIdentity,
        "Unauthorized"
      );
    });
  });

  describe("Admin Functions", function () {
    it("Should allow admin to transfer ownership", async function () {
      await vibIdentity.transferAdmin(await user1.getAddress());

      expect(await vibIdentity.admin()).to.equal(await user1.getAddress());
    });

    it("Should fail when non-admin tries to transfer ownership", async function () {
      await expectRevertCustomError(
        vibIdentity.connect(user1).transferAdmin(await user2.getAddress()),
        vibIdentity,
        "Unauthorized"
      );
    });

    it("Should fail when transferring to zero address", async function () {
      await expectRevertCustomError(
        vibIdentity.transferAdmin(ethers.constants.AddressZero),
        vibIdentity,
        "InvalidAddress"
      );
    });
  });

  describe("Identity Types", function () {
    const metadata = "Test Metadata";

    it("Should support all identity types", async function () {
      const types = [
        IDENTITY_TYPES.VERIFIED,
        IDENTITY_TYPES.KYC_VERIFIED,
        IDENTITY_TYPES.INSTITUTION,
        IDENTITY_TYPES.DAO_MEMBER,
        IDENTITY_TYPES.TEAM_MEMBER,
        IDENTITY_TYPES.PARTNER
      ];

      for (let i = 0; i < types.length; i++) {
        const user = signers[`user${i + 1}`];
        await vibIdentity.mint(await user.getAddress(), types[i], metadata);
      }

      expect(await vibIdentity.totalSupply()).to.equal(types.length);
    });

    it("Should verify correct identity type for each user", async function () {
      await vibIdentity.mint(await user1.getAddress(), IDENTITY_TYPES.VERIFIED, metadata);
      await vibIdentity.mint(await user2.getAddress(), IDENTITY_TYPES.KYC_VERIFIED, metadata);
      await vibIdentity.mint(await signers.user3.getAddress(), IDENTITY_TYPES.INSTITUTION, metadata);

      expect(await vibIdentity.getIdentityType(await user1.getAddress()))
        .to.equal(IDENTITY_TYPES.VERIFIED);
      expect(await vibIdentity.getIdentityType(await user2.getAddress()))
        .to.equal(IDENTITY_TYPES.KYC_VERIFIED);
      expect(await vibIdentity.getIdentityType(await signers.user3.getAddress()))
        .to.equal(IDENTITY_TYPES.INSTITUTION);
    });
  });

  describe("Token URI", function () {
    const metadata = "Test Metadata";

    it("Should return token URI", async function () {
      await vibIdentity.mint(await user1.getAddress(), IDENTITY_TYPES.VERIFIED, metadata);
      const tokenId = await vibIdentity.getIdentityTokenId(await user1.getAddress());

      const uri = await vibIdentity.tokenURI(tokenId);
      expect(uri).to.not.be.empty;
    });

    it("Should fail for non-existent token", async function () {
      await expectRevertCustomError(
        vibIdentity.tokenURI(999),
        vibIdentity,
        "InvalidTokenId"
      );
    });
  });
});
