import { expect } from "chai";
import { ethers, upgrades } from "hardhat";
import { VIBEToken } from "../../typechain-types";
import { Signer } from "ethers";
import { parseEther } from "ethers/lib/utils";
import {
  deployFixtures,
  getSigners,
  advanceTime,
  expectEvent,
  expectRevertCustomError
} from "../utils/fixtures";
import { time, permit, events, errors } from "../utils/helpers";
import {
  TOKEN_NAME,
  TOKEN_SYMBOL,
  TOKEN_DECIMALS,
  INITIAL_SUPPLY,
  SECONDS_PER_DAY,
  ERROR_MESSAGES
} from "../utils/constants";

describe("VIBEToken", function () {
  let vibeToken: VIBEToken;
  let signers: any;
  let owner: Signer;
  let user1: Signer;
  let user2: Signer;

  beforeEach(async function () {
    signers = await getSigners();
    owner = signers.owner;
    user1 = signers.user1;
    user2 = signers.user2;

    // Deploy VIBE Token
    const VIBEToken = await ethers.getContractFactory("VIBEToken");
    vibeToken = (await VIBEToken.deploy(await owner.getAddress())) as VIBEToken;
    await vibeToken.deployed();
  });

  describe("Deployment", function () {
    it("Should set the correct name", async function () {
      expect(await vibeToken.name()).to.equal(TOKEN_NAME);
    });

    it("Should set the correct symbol", async function () {
      expect(await vibeToken.symbol()).to.equal(TOKEN_SYMBOL);
    });

    it("Should set the correct decimals", async function () {
      expect(await vibeToken.decimals()).to.equal(TOKEN_DECIMALS);
    });

    it("Should set the correct initial supply", async function () {
      expect(await vibeToken.totalSupply()).to.equal(INITIAL_SUPPLY);
    });

    it("Should mint initial supply to deployer", async function () {
      const ownerAddress = await owner.getAddress();
      expect(await vibeToken.balanceOf(ownerAddress)).to.equal(INITIAL_SUPPLY);
    });

    it("Should set deployer as DEFAULT_ADMIN_ROLE", async function () {
      const DEFAULT_ADMIN_ROLE = await vibeToken.DEFAULT_ADMIN_ROLE();
      const ownerAddress = await owner.getAddress();
      expect(await vibeToken.hasRole(DEFAULT_ADMIN_ROLE, ownerAddress)).to.be.true;
    });

    it("Should set deployer as MINTER_ROLE", async function () {
      const MINTER_ROLE = await vibeToken.MINTER_ROLE();
      const ownerAddress = await owner.getAddress();
      expect(await vibeToken.hasRole(MINTER_ROLE, ownerAddress)).to.be.true;
    });

    it("Should set deployer as PAUSER_ROLE", async function () {
      const PAUSER_ROLE = await vibeToken.PAUSER_ROLE();
      const ownerAddress = await owner.getAddress();
      expect(await vibeToken.hasRole(PAUSER_ROLE, ownerAddress)).to.be.true;
    });
  });

  describe("Transfers", function () {
    const transferAmount = parseEther("1000");

    beforeEach(async function () {
      await vibeToken.transfer(await user1.getAddress(), transferAmount);
    });

    it("Should transfer tokens successfully", async function () {
      const user2Address = await user2.getAddress();
      const user1Address = await user1.getAddress();

      await vibeToken.connect(user1).transfer(user2Address, transferAmount);

      expect(await vibeToken.balanceOf(user1Address)).to.equal(0);
      expect(await vibeToken.balanceOf(user2Address)).to.equal(transferAmount);
    });

    it("Should emit Transfer event", async function () {
      const user2Address = await user2.getAddress();
      const user1Address = await user1.getAddress();

      await expectEvent(
        vibeToken.connect(user1).transfer(user2Address, transferAmount),
        vibeToken,
        "Transfer",
        [user1Address, user2Address, transferAmount]
      );
    });

    it("Should fail when transferring more than balance", async function () {
      const user2Address = await user2.getAddress();
      const excessAmount = transferAmount.add(1);

      await expectRevertCustomError(
        vibeToken.connect(user1).transfer(user2Address, excessAmount),
        vibeToken,
        ERROR_MESSAGES.INSUFFICIENT_BALANCE
      );
    });

    it("Should fail when transferring to zero address", async function () {
      await expect(
        vibeToken.connect(user1).transfer(ethers.constants.AddressZero, transferAmount)
      ).to.be.reverted;
    });
  });

  describe("Approvals", function () {
    const approveAmount = parseEther("1000");

    it("Should approve spending", async function () {
      const user2Address = await user2.getAddress();

      await vibeToken.connect(user1).approve(user2Address, approveAmount);

      expect(await vibeToken.allowance(await user1.getAddress(), user2Address))
        .to.equal(approveAmount);
    });

    it("Should emit Approval event", async function () {
      const user2Address = await user2.getAddress();

      await expectEvent(
        vibeToken.connect(user1).approve(user2Address, approveAmount),
        vibeToken,
        "Approval",
        [await user1.getAddress(), user2Address, approveAmount]
      );
    });

    it("Should increase allowance", async function () {
      const user2Address = await user2.getAddress();
      const initialAmount = parseEther("500");
      const increaseAmount = parseEther("300");

      await vibeToken.connect(user1).approve(user2Address, initialAmount);
      await vibeToken.connect(user1).increaseAllowance(user2Address, increaseAmount);

      expect(await vibeToken.allowance(await user1.getAddress(), user2Address))
        .to.equal(initialAmount.add(increaseAmount));
    });

    it("Should decrease allowance", async function () {
      const user2Address = await user2.getAddress();
      const initialAmount = parseEther("500");
      const decreaseAmount = parseEther("300");

      await vibeToken.connect(user1).approve(user2Address, initialAmount);
      await vibeToken.connect(user1).decreaseAllowance(user2Address, decreaseAmount);

      expect(await vibeToken.allowance(await user1.getAddress(), user2Address))
        .to.equal(initialAmount.sub(decreaseAmount));
    });

    it("Should fail when decreasing below zero", async function () {
      const user2Address = await user2.getAddress();
      const initialAmount = parseEther("500");
      const excessDecrease = parseEther("1000");

      await vibeToken.connect(user1).approve(user2Address, initialAmount);

      await expect(
        vibeToken.connect(user1).decreaseAllowance(user2Address, excessDecrease)
      ).to.be.reverted;
    });
  });

  describe("TransferFrom", function () {
    const approveAmount = parseEther("1000");
    const transferAmount = parseEther("500");

    beforeEach(async function () {
      await vibeToken.transfer(await user1.getAddress(), approveAmount);
      await vibeToken.connect(user1).approve(await user2.getAddress(), approveAmount);
    });

    it("Should transfer from with approval", async function () {
      const user1Address = await user1.getAddress();
      const user3Address = await signers.user3.getAddress();

      await vibeToken.connect(user2).transferFrom(user1Address, user3Address, transferAmount);

      expect(await vibeToken.balanceOf(user1Address)).to.equal(approveAmount.sub(transferAmount));
      expect(await vibeToken.balanceOf(user3Address)).to.equal(transferAmount);
    });

    it("Should decrease allowance after transfer", async function () {
      const user1Address = await user1.getAddress();
      const user3Address = await signers.user3.getAddress();

      await vibeToken.connect(user2).transferFrom(user1Address, user3Address, transferAmount);

      expect(await vibeToken.allowance(user1Address, await user2.getAddress()))
        .to.equal(approveAmount.sub(transferAmount));
    });

    it("Should fail without sufficient allowance", async function () {
      const user1Address = await user1.getAddress();
      const user3Address = await signers.user3.getAddress();
      const excessAmount = approveAmount.add(1);

      await expectRevertCustomError(
        vibeToken.connect(user2).transferFrom(user1Address, user3Address, excessAmount),
        vibeToken,
        ERROR_MESSAGES.INSUFFICIENT_ALLOWANCE
      );
    });

    it("Should fail when transferring from without allowance", async function () {
      const user1Address = await user1.getAddress();
      const user3Address = await signers.user3.getAddress();

      // Set allowance to 0
      await vibeToken.connect(user1).approve(await user2.getAddress(), 0);

      await expectRevertCustomError(
        vibeToken.connect(user2).transferFrom(user1Address, user3Address, transferAmount),
        vibeToken,
        ERROR_MESSAGES.INSUFFICIENT_ALLOWANCE
      );
    });
  });

  describe("Minting", function () {
    const mintAmount = parseEther("1000");

    it("Should allow minter to mint tokens", async function () {
      const user1Address = await user1.getAddress();

      await vibeToken.mint(user1Address, mintAmount);

      expect(await vibeToken.balanceOf(user1Address)).to.equal(mintAmount);
      expect(await vibeToken.totalSupply()).to.equal(INITIAL_SUPPLY.add(mintAmount));
    });

    it("Should emit Transfer event on mint", async function () {
      const user1Address = await user1.getAddress();

      await expectEvent(
        vibeToken.mint(user1Address, mintAmount),
        vibeToken,
        "Transfer",
        [ethers.constants.AddressZero, user1Address, mintAmount]
      );
    });

    it("Should fail when non-minter tries to mint", async function () {
      const user1Address = await user1.getAddress();

      await expect(
        vibeToken.connect(user1).mint(user1Address, mintAmount)
      ).to.be.reverted;
    });

    it("Should fail when minting to zero address", async function () {
      await expect(
        vibeToken.mint(ethers.constants.AddressZero, mintAmount)
      ).to.be.reverted;
    });
  });

  describe("Burning", function () {
    const burnAmount = parseEther("1000");

    beforeEach(async function () {
      await vibeToken.transfer(await user1.getAddress(), burnAmount);
    });

    it("Should allow users to burn their tokens", async function () {
      const user1Address = await user1.getAddress();

      await vibeToken.connect(user1).burn(burnAmount);

      expect(await vibeToken.balanceOf(user1Address)).to.equal(0);
      expect(await vibeToken.totalSupply()).to.equal(INITIAL_SUPPLY.sub(burnAmount));
    });

    it("Should emit Transfer event on burn", async function () {
      const user1Address = await user1.getAddress();

      await expectEvent(
        vibeToken.connect(user1).burn(burnAmount),
        vibeToken,
        "Transfer",
        [user1Address, ethers.constants.AddressZero, burnAmount]
      );
    });

    it("Should fail when burning more than balance", async function () {
      const excessAmount = burnAmount.add(1);

      await expectRevertCustomError(
        vibeToken.connect(user1).burn(excessAmount),
        vibeToken,
        ERROR_MESSAGES.INSUFFICIENT_BALANCE
      );
    });
  });

  describe("Permit (EIP-2612)", function () {
    const permitAmount = parseEther("1000");

    it("Should permit signature verification", async function () {
      const user1Address = await user1.getAddress();
      const user2Address = await user2.getAddress();
      const deadline = await time.latest().then(t => t.add(3600));

      const { v, r, s } = await permit.signPermit(
        vibeToken,
        user1,
        user2Address,
        permitAmount,
        deadline
      );

      await vibeToken.permit(user1Address, user2Address, permitAmount, deadline, v, r, s);

      expect(await vibeToken.allowance(user1Address, user2Address)).to.equal(permitAmount);
    });

    it("Should use permit with transferFrom", async function () {
      await vibeToken.transfer(user1Address, permitAmount);

      const user2Address = await user2.getAddress();
      const user3Address = await signers.user3.getAddress();
      const deadline = await time.latest().then(t => t.add(3600));

      const { v, r, s } = await permit.signPermit(
        vibeToken,
        user1,
        user2Address,
        permitAmount,
        deadline
      );

      await vibeToken.permit(user1Address, user2Address, permitAmount, deadline, v, r, s);
      await vibeToken.connect(user2).transferFrom(user1Address, user3Address, permitAmount);

      expect(await vibeToken.balanceOf(user1Address)).to.equal(0);
      expect(await vibeToken.balanceOf(user3Address)).to.equal(permitAmount);
    });

    it("Should fail with expired deadline", async function () {
      const user1Address = await user1.getAddress();
      const user2Address = await user2.getAddress();
      const expiredDeadline = await time.latest().then(t => t.sub(3600));

      const { v, r, s } = await permit.signPermit(
        vibeToken,
        user1,
        user2Address,
        permitAmount,
        expiredDeadline
      );

      await expect(
        vibeToken.permit(user1Address, user2Address, permitAmount, expiredDeadline, v, r, s)
      ).to.be.revertedWith("ERC2612ExpiredSignature");
    });

    it("Should fail with invalid signature", async function () {
      const user1Address = await user1.getAddress();
      const user2Address = await user2.getAddress();
      const deadline = await time.latest().then(t => t.add(3600));

      await expect(
        vibeToken.permit(user1Address, user2Address, permitAmount, deadline, 0, ethers.utils.hexlify(0), ethers.utils.hexlify(0))
      ).to.be.reverted;
    });

    it("Should increment nonce after permit", async function () {
      const user1Address = await user1.getAddress();
      const user2Address = await user2.getAddress();
      const deadline = await time.latest().then(t => t.add(3600));

      const initialNonce = await vibeToken.nonces(user1Address);

      const { v, r, s } = await permit.signPermit(
        vibeToken,
        user1,
        user2Address,
        permitAmount,
        deadline
      );

      await vibeToken.permit(user1Address, user2Address, permitAmount, deadline, v, r, s);

      expect(await vibeToken.nonces(user1Address)).to.equal(initialNonce.add(1));
    });
  });

  describe("Pause", function () {
    it("Should allow pauser to pause", async function () {
      await vibeToken.pause();
      expect(await vibeToken.paused()).to.be.true;
    });

    it("Should emit Paused event", async function () {
      await expectEvent(
        vibeToken.pause(),
        vibeToken,
        "Paused",
        [await owner.getAddress()]
      );
    });

    it("Should allow pauser to unpause", async function () {
      await vibeToken.pause();
      await vibeToken.unpause();
      expect(await vibeToken.paused()).to.be.false;
    });

    it("Should emit Unpaused event", async function () {
      await vibeToken.pause();
      await expectEvent(
        vibeToken.unpause(),
        vibeToken,
        "Unpaused",
        [await owner.getAddress()]
      );
    });

    it("Should block transfers when paused", async function () {
      const transferAmount = parseEther("1000");
      await vibeToken.transfer(await user1.getAddress(), transferAmount);
      await vibeToken.pause();

      const user2Address = await user2.getAddress();

      await expectRevertCustomError(
        vibeToken.connect(user1).transfer(user2Address, transferAmount),
        vibeToken,
        ERROR_MESSAGES.PAUSED
      );
    });

    it("Should block transfersFrom when paused", async function () {
      const approveAmount = parseEther("1000");
      await vibeToken.transfer(await user1.getAddress(), approveAmount);
      await vibeToken.connect(user1).approve(await user2.getAddress(), approveAmount);
      await vibeToken.pause();

      const user1Address = await user1.getAddress();
      const user3Address = await signers.user3.getAddress();

      await expectRevertCustomError(
        vibeToken.connect(user2).transferFrom(user1Address, user3Address, approveAmount),
        vibeToken,
        ERROR_MESSAGES.PAUSED
      );
    });

    it("Should block minting when paused", async function () {
      const mintAmount = parseEther("1000");
      await vibeToken.pause();

      const user1Address = await user1.getAddress();

      await expectRevertCustomError(
        vibeToken.mint(user1Address, mintAmount),
        vibeToken,
        ERROR_MESSAGES.PAUSED
      );
    });

    it("Should fail when non-pauser tries to pause", async function () {
      await expect(
        vibeToken.connect(user1).pause()
      ).to.be.reverted;
    });
  });

  describe("Role Management", function () {
    it("Should grant MINTER_ROLE", async function () {
      const MINTER_ROLE = await vibeToken.MINTER_ROLE();
      const user1Address = await user1.getAddress();

      await vibeToken.grantRole(MINTER_ROLE, user1Address);

      expect(await vibeToken.hasRole(MINTER_ROLE, user1Address)).to.be.true;
    });

    it("Should revoke MINTER_ROLE", async function () {
      const MINTER_ROLE = await vibeToken.MINTER_ROLE();
      const user1Address = await user1.getAddress();

      await vibeToken.grantRole(MINTER_ROLE, user1Address);
      await vibeToken.revokeRole(MINTER_ROLE, user1Address);

      expect(await vibeToken.hasRole(MINTER_ROLE, user1Address)).to.be.false;
    });

    it("Should grant PAUSER_ROLE", async function () {
      const PAUSER_ROLE = await vibeToken.PAUSER_ROLE();
      const user1Address = await user1.getAddress();

      await vibeToken.grantRole(PAUSER_ROLE, user1Address);

      expect(await vibeToken.hasRole(PAUSER_ROLE, user1Address)).to.be.true;
    });

    it("Should emit RoleGranted event", async function () {
      const MINTER_ROLE = await vibeToken.MINTER_ROLE();
      const user1Address = await user1.getAddress();

      await expectEvent(
        vibeToken.grantRole(MINTER_ROLE, user1Address),
        vibeToken,
        "RoleGranted",
        [MINTER_ROLE, user1Address, await owner.getAddress()]
      );
    });

    it("Should emit RoleRevoked event", async function () {
      const MINTER_ROLE = await vibeToken.MINTER_ROLE();
      const user1Address = await user1.getAddress();

      await vibeToken.grantRole(MINTER_ROLE, user1Address);
      await expectEvent(
        vibeToken.revokeRole(MINTER_ROLE, user1Address),
        vibeToken,
        "RoleRevoked",
        [MINTER_ROLE, user1Address, await owner.getAddress()]
      );
    });

    it("Should fail when non-admin tries to grant role", async function () {
      const MINTER_ROLE = await vibeToken.MINTER_ROLE();
      const user2Address = await user2.getAddress();

      await expect(
        vibeToken.connect(user1).grantRole(MINTER_ROLE, user2Address)
      ).to.be.reverted;
    });

    it("Should renounce role", async function () {
      const MINTER_ROLE = await vibeToken.MINTER_ROLE();
      const ownerAddress = await owner.getAddress();

      await vibeToken.renounceRole(MINTER_ROLE, ownerAddress);

      expect(await vibeToken.hasRole(MINTER_ROLE, ownerAddress)).to.be.false;
    });
  });
});
