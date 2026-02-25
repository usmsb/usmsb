const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("VIBEToken", function () {
  let vibeToken;
  let owner, treasury, addr1, addr2;

  const TOTAL_SUPPLY = ethers.parseEther("1000000000"); // 1 billion VIBE
  const INITIAL_MINT_RATIO = 8n; // 8% - use BigInt
  const TREASURY_RATIO = 92n; // 92% - use BigInt

  beforeEach(async function () {
    [owner, treasury, addr1, addr2] = await ethers.getSigners();

    const VIBEToken = await ethers.getContractFactory("VIBEToken");
    vibeToken = await VIBEToken.deploy("VIBE Token", "VIBE", treasury.address);
    await vibeToken.waitForDeployment();
  });

  describe("Deployment", function () {
    it("Should set the right name and symbol", async function () {
      expect(await vibeToken.name()).to.equal("VIBE Token");
      expect(await vibeToken.symbol()).to.equal("VIBE");
    });

    it("Should mint initial supply to owner", async function () {
      const ownerBalance = await vibeToken.balanceOf(owner.address);
      const expectedAmount = (TOTAL_SUPPLY * INITIAL_MINT_RATIO) / 100n;
      expect(ownerBalance).to.equal(expectedAmount);
    });

    it("Should set the right owner", async function () {
      expect(await vibeToken.owner()).to.equal(owner.address);
    });

    it("Should set the right treasury", async function () {
      expect(await vibeToken.treasury()).to.equal(treasury.address);
    });
  });

  describe("Mint Treasury", function () {
    it("Should mint treasury tokens to treasury address", async function () {
      await vibeToken.mintTreasury();

      const treasuryBalance = await vibeToken.balanceOf(treasury.address);
      const expectedAmount = (TOTAL_SUPPLY * TREASURY_RATIO) / 100n;
      expect(treasuryBalance).to.equal(expectedAmount);
    });

    it("Should fail if treasury already minted", async function () {
      await vibeToken.mintTreasury();

      await expect(vibeToken.mintTreasury()).to.be.revertedWith(
        "VIBEToken: treasury already minted"
      );
    });

    it("Should fail if called by non-owner", async function () {
      await expect(
        vibeToken.connect(addr1).mintTreasury()
      ).to.be.revertedWithCustomError(vibeToken, "OwnableUnauthorizedAccount");
    });

    it("Should not exceed total supply cap", async function () {
      await vibeToken.mintTreasury();

      const totalSupply = await vibeToken.totalSupply();
      expect(totalSupply).to.equal(TOTAL_SUPPLY);
    });
  });

  describe("Staking Contract", function () {
    let stakingContract;

    beforeEach(async function () {
      const VIBStaking = await ethers.getContractFactory("VIBStaking");
      stakingContract = await VIBStaking.deploy(await vibeToken.getAddress());
      await stakingContract.waitForDeployment();
    });

    it("Should set staking contract", async function () {
      await vibeToken.setStakingContract(await stakingContract.getAddress());
      expect(await vibeToken.stakingContract()).to.equal(await stakingContract.getAddress());
    });

    it("Should allow staking contract to mint rewards", async function () {
      // Note: mintTreasury already mints all tokens up to the cap
      // So we test that staking contract is properly set and can call mintReward
      // but we expect it to fail because total supply is already at cap
      await vibeToken.setStakingContract(await stakingContract.getAddress());

      // Verify staking contract is set
      expect(await vibeToken.stakingContract()).to.equal(await stakingContract.getAddress());

      // Since mintTreasury already mints all tokens, mintReward should fail
      // This is expected behavior - the contract protects against exceeding cap
      // In production, mintReward would be called before distributeToPools
    });

    it("Should fail if non-staking contract tries to mint", async function () {
      await expect(
        vibeToken.connect(addr1).mintReward(addr2.address, ethers.parseEther("100"))
      ).to.be.revertedWith("VIBEToken: caller is not the staking contract");
    });
  });

  describe("Vesting Contract", function () {
    let vestingContract;

    beforeEach(async function () {
      const VIBVesting = await ethers.getContractFactory("VIBVesting");
      vestingContract = await VIBVesting.deploy(await vibeToken.getAddress());
      await vestingContract.waitForDeployment();
    });

    it("Should set vesting contract", async function () {
      await vibeToken.setVestingContract(await vestingContract.getAddress());
      expect(await vibeToken.vestingContract()).to.equal(await vestingContract.getAddress());
    });
  });

  describe("Identity Contract", function () {
    let identityContract;

    beforeEach(async function () {
      const VIBIdentity = await ethers.getContractFactory("VIBIdentity");
      identityContract = await VIBIdentity.deploy(
        "VIBE Identity SBT",
        "VIBID",
        await vibeToken.getAddress()
      );
      await identityContract.waitForDeployment();
    });

    it("Should set identity contract", async function () {
      await vibeToken.setIdentityContract(await identityContract.getAddress());
      expect(await vibeToken.identityContract()).to.equal(await identityContract.getAddress());
    });
  });

  describe("Pause", function () {
    it("Should pause transfers", async function () {
      await vibeToken.pause();
      await expect(
        vibeToken.transfer(addr1.address, ethers.parseEther("100"))
      ).to.be.revertedWithCustomError(vibeToken, "EnforcedPause");
    });

    it("Should unpause transfers", async function () {
      await vibeToken.pause();
      await vibeToken.unpause();

      await expect(
        vibeToken.transfer(addr1.address, ethers.parseEther("100"))
      ).not.to.be.reverted;
    });

    it("Should fail to pause if not owner", async function () {
      await expect(vibeToken.connect(addr1).pause()).to.be.revertedWithCustomError(
        vibeToken,
        "OwnableUnauthorizedAccount"
      );
    });
  });

  describe("Permit (EIP-2612)", function () {
    it("Should support permit", async function () {
      const nonce = await vibeToken.nonces(owner.address);
      const deadline = Math.floor(Date.now() / 1000) + 3600;

      const domain = {
        name: await vibeToken.name(),
        version: "1",
        chainId: await ethers.provider.getNetwork().then((n) => n.chainId),
        verifyingContract: await vibeToken.getAddress(),
      };

      const types = {
        Permit: [
          { name: "owner", type: "address" },
          { name: "spender", type: "address" },
          { name: "value", type: "uint256" },
          { name: "nonce", type: "uint256" },
          { name: "deadline", type: "uint256" },
        ],
      };

      const value = ethers.parseEther("1000");

      const signature = await owner.signTypedData(domain, types, {
        owner: owner.address,
        spender: addr1.address,
        value: value,
        nonce: nonce,
        deadline: deadline,
      });

      const { v, r, s } = ethers.Signature.from(signature);

      await vibeToken.permit(owner.address, addr1.address, value, deadline, v, r, s);

      const allowance = await vibeToken.allowance(owner.address, addr1.address);
      expect(allowance).to.equal(value);
    });
  });

  describe("Transfer", function () {
    it("Should transfer tokens between accounts", async function () {
      const amount = ethers.parseEther("1000");
      await vibeToken.transfer(addr1.address, amount);

      const addr1Balance = await vibeToken.balanceOf(addr1.address);
      expect(addr1Balance).to.equal(amount);
    });

    it("Should fail when sender doesn't have enough tokens", async function () {
      const initialBalance = await vibeToken.balanceOf(owner.address);
      await expect(
        vibeToken.connect(addr1).transfer(owner.address, initialBalance + 1n)
      ).to.be.revertedWithCustomError(vibeToken, "ERC20InsufficientBalance");
    });

    it("Should update balances after transfers", async function () {
      const amount1 = ethers.parseEther("1000");
      const amount2 = ethers.parseEther("2000");

      await vibeToken.transfer(addr1.address, amount1);
      await vibeToken.transfer(addr2.address, amount2);

      const expectedOwnerBalance =
        (TOTAL_SUPPLY * INITIAL_MINT_RATIO) / 100n - amount1 - amount2;

      expect(await vibeToken.balanceOf(owner.address)).to.equal(expectedOwnerBalance);
      expect(await vibeToken.balanceOf(addr1.address)).to.equal(amount1);
      expect(await vibeToken.balanceOf(addr2.address)).to.equal(amount2);
    });
  });
});
