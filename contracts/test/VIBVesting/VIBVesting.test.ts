import { expect } from "chai";
import { ethers } from "hardhat";
import { VIBVesting, VIBEToken } from "../../typechain-types";
import { Signer } from "ethers";
import { parseEther } from "ethers/lib/utils";
import { getSigners, expectEvent, expectRevertCustomError, advanceTime } from "../utils/fixtures";
import { time } from "../utils/helpers";
import {
  VESTING_PERIODS,
  CLIFF_PERIODS,
  SECONDS_PER_DAY,
  ERROR_MESSAGES
} from "../utils/constants";

describe("VIBVesting", function () {
  let vibeToken: VIBEToken;
  let vibVesting: VIBVesting;
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

    // Deploy VIBVesting
    const VIBVesting = await ethers.getContractFactory("VIBVesting");
    vibVesting = (await VIBVesting.deploy(
      vibeToken.address,
      await owner.getAddress()
    )) as VIBVesting;
    await vibVesting.deployed();

    // Grant minter role to vesting contract
    await vibeToken.grantRole(await vibeToken.MINTER_ROLE(), vibVesting.address);

    // Transfer tokens to owner for vesting
    await vibeToken.transfer(await owner.getAddress(), parseEther("100000000"));
  });

  describe("Deployment", function () {
    it("Should set the correct token", async function () {
      expect(await vibVesting.token()).to.equal(vibeToken.address);
    });

    it("Should set the correct admin", async function () {
      expect(await vibVesting.admin()).to.equal(await owner.getAddress());
    });

    it("Should initialize with no beneficiaries", async function () {
      const beneficiaryCount = await vibVesting.getBeneficiaryCount();
      expect(beneficiaryCount).to.equal(0);
    });
  });

  describe("Add Beneficiary", function () {
    const totalAmount = parseEther("100000");
    const vestingDuration = VESTING_PERIODS.TEAM_VESTING;
    const cliffDuration = CLIFF_PERIODS.TEAM_CLIFF;

    beforeEach(async function () {
      await vibeToken.connect(owner).approve(vibVesting.address, totalAmount);
    });

    it("Should add beneficiary successfully", async function () {
      const user1Address = await user1.getAddress();
      const currentTimestamp = await time.latest();
      const startTime = currentTimestamp.add(86400);

      await vibVesting.addBeneficiary(
        user1Address,
        totalAmount,
        startTime,
        cliffDuration,
        vestingDuration
      );

      const beneficiary = await vibVesting.beneficiaries(user1Address);
      expect(beneficiary.totalAmount).to.equal(totalAmount);
      expect(beneficiary.startTime).to.equal(startTime);
      expect(beneficiary.cliffDuration).to.equal(cliffDuration);
      expect(beneficiary.vestingDuration).to.equal(vestingDuration);
    });

    it("Should emit BeneficiaryAdded event", async function () {
      const user1Address = await user1.getAddress();
      const currentTimestamp = await time.latest();
      const startTime = currentTimestamp.add(86400);

      await expectEvent(
        vibVesting.addBeneficiary(
          user1Address,
          totalAmount,
          startTime,
          cliffDuration,
          vestingDuration
        ),
        vibVesting,
        "BeneficiaryAdded",
        [user1Address, totalAmount]
      );
    });

    it("Should increase beneficiary count", async function () {
      const user1Address = await user1.getAddress();
      const currentTimestamp = await time.latest();
      const startTime = currentTimestamp.add(86400);

      await vibVesting.addBeneficiary(
        user1Address,
        totalAmount,
        startTime,
        cliffDuration,
        vestingDuration
      );

      expect(await vibVesting.getBeneficiaryCount()).to.equal(1);
    });

    it("Should fail when adding zero address beneficiary", async function () {
      const currentTimestamp = await time.latest();
      const startTime = currentTimestamp.add(86400);

      await expectRevertCustomError(
        vibVesting.addBeneficiary(
          ethers.constants.AddressZero,
          totalAmount,
          startTime,
          cliffDuration,
          vestingDuration
        ),
        vibVesting,
        "InvalidBeneficiary"
      );
    });

    it("Should fail when total amount is zero", async function () {
      const user1Address = await user1.getAddress();
      const currentTimestamp = await time.latest();
      const startTime = currentTimestamp.add(86400);

      await expectRevertCustomError(
        vibVesting.addBeneficiary(
          user1Address,
          0,
          startTime,
          cliffDuration,
          vestingDuration
        ),
        vibVesting,
        "InvalidAmount"
      );
    });

    it("Should fail when beneficiary already exists", async function () {
      const user1Address = await user1.getAddress();
      const currentTimestamp = await time.latest();
      const startTime = currentTimestamp.add(86400);

      await vibVesting.addBeneficiary(
        user1Address,
        totalAmount,
        startTime,
        cliffDuration,
        vestingDuration
      );

      await expectRevertCustomError(
        vibVesting.addBeneficiary(
          user1Address,
          totalAmount,
          startTime,
          cliffDuration,
          vestingDuration
        ),
        vibVesting,
        "AlreadyAdded"
      );
    });

    it("Should fail when vesting duration is less than cliff", async function () {
      const user1Address = await user1.getAddress();
      const currentTimestamp = await time.latest();
      const startTime = currentTimestamp.add(86400);

      await expectRevertCustomError(
        vibVesting.addBeneficiary(
          user1Address,
          totalAmount,
          startTime,
          vestingDuration,
          vestingDuration.add(86400)
        ),
        vibVesting,
        "InvalidDuration"
      );
    });

    it("Should fail when non-admin tries to add beneficiary", async function () {
      const user1Address = await user1.getAddress();
      const currentTimestamp = await time.latest();
      const startTime = currentTimestamp.add(86400);

      await expectRevertCustomError(
        vibVesting.connect(user1).addBeneficiary(
          user1Address,
          totalAmount,
          startTime,
          cliffDuration,
          vestingDuration
        ),
        vibVesting,
        "Unauthorized"
      );
    });
  });

  describe("Vesting Calculation", function () {
    const totalAmount = parseEther("120000"); // 10k per month for 12 months
    const vestingDuration = 12 * 30 * 86400; // 12 months
    const cliffDuration = 3 * 30 * 86400; // 3 months cliff

    beforeEach(async function () {
      await vibeToken.connect(owner).approve(vibVesting.address, totalAmount);

      const user1Address = await user1.getAddress();
      const currentTimestamp = await time.latest();
      const startTime = currentTimestamp.add(86400);

      await vibVesting.addBeneficiary(
        user1Address,
        totalAmount,
        startTime,
        cliffDuration,
        vestingDuration
      );
    });

    it("Should return zero before start time", async function () {
      const user1Address = await user1.getAddress();
      const vested = await vibVesting.calculateVesting(user1Address);
      expect(vested).to.equal(0);
    });

    it("Should return zero during cliff", async function () {
      const user1Address = await user1.getAddress();
      await advanceTime(2 * 30 * 86400); // 2 months

      const vested = await vibVesting.calculateVesting(user1Address);
      expect(vested).to.equal(0);
    });

    it("Should return zero immediately after cliff", async function () {
      const user1Address = await user1.getAddress();
      await advanceTime(86400); // 1 day (start)
      await advanceTime(cliffDuration); // Go to cliff end

      const vested = await vibVesting.calculateVesting(user1Address);
      expect(vested).to.equal(0);
    });

    it("Should return correct vested amount after cliff", async function () {
      const user1Address = await user1.getAddress();
      await advanceTime(86400); // 1 day (start)
      await advanceTime(cliffDuration); // Go to cliff end
      await advanceTime(30 * 86400); // 1 month after cliff

      const vested = await vibVesting.calculateVesting(user1Address);
      const expected = totalAmount.mul(1).div(12); // 1/12 vested
      expect(vested).to.equal(expected);
    });

    it("Should return correct vested amount half through vesting", async function () {
      const user1Address = await user1.getAddress();
      await advanceTime(86400); // 1 day (start)
      await advanceTime(vestingDuration.div(2)); // Half of vesting period

      const vested = await vibVesting.calculateVesting(user1Address);
      const expected = totalAmount.mul(6).div(12); // 6/12 vested
      expect(vested).to.equal(expected);
    });

    it("Should return total amount at end of vesting", async function () {
      const user1Address = await user1.getAddress();
      await advanceTime(86400); // 1 day (start)
      await advanceTime(vestingDuration); // Full vesting period

      const vested = await vibVesting.calculateVesting(user1Address);
      expect(vested).to.equal(totalAmount);
    });

    it("Should return total amount after vesting ends", async function () {
      const user1Address = await user1.getAddress();
      await advanceTime(86400); // 1 day (start)
      await advanceTime(vestingDuration.add(30 * 86400)); // Past vesting

      const vested = await vibVesting.calculateVesting(user1Address);
      expect(vested).to.equal(totalAmount);
    });

    it("Should calculate correctly for multiple beneficiaries", async function () {
      const user2Address = await user2.getAddress();
      const totalAmount2 = parseEther("60000"); // 5k per month for 12 months

      await vibeToken.connect(owner).approve(vibVesting.address, totalAmount2);

      const currentTimestamp = await time.latest();
      const startTime = currentTimestamp.add(86400);

      await vibVesting.addBeneficiary(
        user2Address,
        totalAmount2,
        startTime,
        cliffDuration,
        vestingDuration
      );

      await advanceTime(86400); // 1 day (start)
      await advanceTime(vestingDuration); // Full vesting period

      const vested1 = await vibVesting.calculateVesting(await user1.getAddress());
      const vested2 = await vibVesting.calculateVesting(user2Address);

      expect(vested1).to.equal(totalAmount);
      expect(vested2).to.equal(totalAmount2);
    });
  });

  describe("Claim", function () {
    const totalAmount = parseEther("120000");
    const vestingDuration = 12 * 30 * 86400;
    const cliffDuration = 3 * 30 * 86400;

    beforeEach(async function () {
      await vibeToken.connect(owner).approve(vibVesting.address, totalAmount);

      const user1Address = await user1.getAddress();
      const currentTimestamp = await time.latest();
      const startTime = currentTimestamp.add(86400);

      await vibVesting.addBeneficiary(
        user1Address,
        totalAmount,
        startTime,
        cliffDuration,
        vestingDuration
      );
    });

    it("Should claim vested tokens successfully", async function () {
      const user1Address = await user1.getAddress();
      await advanceTime(86400); // 1 day (start)
      await advanceTime(cliffDuration); // Cliff period
      await advanceTime(30 * 86400); // 1 month after cliff

      const balanceBefore = await vibeToken.balanceOf(user1Address);
      await vibVesting.connect(user1).claim();
      const balanceAfter = await vibeToken.balanceOf(user1Address);

      const claimed = balanceAfter.sub(balanceBefore);
      const expected = totalAmount.mul(1).div(12);
      expect(claimed).to.equal(expected);
    });

    it("Should emit TokensClaimed event", async function () {
      const user1Address = await user1.getAddress();
      await advanceTime(86400); // 1 day (start)
      await advanceTime(cliffDuration); // Cliff period
      await advanceTime(30 * 86400); // 1 month after cliff

      await expectEvent(
        vibVesting.connect(user1).claim(),
        vibVesting,
        "TokensClaimed",
        [user1Address, totalAmount.mul(1).div(12)]
      );
    });

    it("Should update claimed amount", async function () {
      const user1Address = await user1.getAddress();
      await advanceTime(86400); // 1 day (start)
      await advanceTime(cliffDuration); // Cliff period
      await advanceTime(30 * 86400); // 1 month after cliff

      await vibVesting.connect(user1).claim();

      const beneficiary = await vibVesting.beneficiaries(user1Address);
      expect(beneficiary.claimedAmount).to.equal(totalAmount.mul(1).div(12));
    });

    it("Should allow claiming multiple times", async function () {
      const user1Address = await user1.getAddress();
      await advanceTime(86400); // 1 day (start)
      await advanceTime(cliffDuration); // Cliff period

      // First claim
      await advanceTime(30 * 86400);
      await vibVesting.connect(user1).claim();

      const claimed1 = (await vibVesting.beneficiaries(user1Address)).claimedAmount;

      // Second claim
      await advanceTime(30 * 86400);
      await vibVesting.connect(user1).claim();

      const claimed2 = (await vibVesting.beneficiaries(user1Address)).claimedAmount;

      expect(claimed2.sub(claimed1).gt(0)).to.be.true;
    });

    it("Should fail when claiming before cliff", async function () {
      await advanceTime(86400); // 1 day (start)
      await advanceTime(30 * 86400); // Before cliff

      await expectRevertCustomError(
        vibVesting.connect(user1).claim(),
        vibVesting,
        "NothingToClaim"
      );
    });

    it("Should fail when claiming nothing new", async function () {
      const user1Address = await user1.getAddress();
      await advanceTime(86400); // 1 day (start)
      await advanceTime(cliffDuration); // Cliff period
      await advanceTime(30 * 86400); // 1 month after cliff

      await vibVesting.connect(user1).claim();

      // Try to claim again immediately
      await expectRevertCustomError(
        vibVesting.connect(user1).claim(),
        vibVesting,
        "NothingToClaim"
      );
    });

    it("Should fail when non-beneficiary tries to claim", async function () {
      const user2Address = await user2.getAddress();
      await advanceTime(86400); // 1 day (start)
      await advanceTime(cliffDuration); // Cliff period
      await advanceTime(30 * 86400); // 1 month after cliff

      await expectRevertCustomError(
        vibVesting.connect(user2).claim(),
        vibVesting,
        "NotABeneficiary"
      );
    });

    it("Should claim all vested tokens at end", async function () {
      const user1Address = await user1.getAddress();
      await advanceTime(86400); // 1 day (start)
      await advanceTime(vestingDuration); // Full vesting

      const balanceBefore = await vibeToken.balanceOf(user1Address);
      await vibVesting.connect(user1).claim();
      const balanceAfter = await vibeToken.balanceOf(user1Address);

      const claimed = balanceAfter.sub(balanceBefore);
      expect(claimed).to.equal(totalAmount);
    });
  });

  describe("Revoke Beneficiary", function () {
    const totalAmount = parseEther("120000");
    const vestingDuration = 12 * 30 * 86400;
    const cliffDuration = 3 * 30 * 86400;

    beforeEach(async function () {
      await vibeToken.connect(owner).approve(vibVesting.address, totalAmount);

      const user1Address = await user1.getAddress();
      const currentTimestamp = await time.latest();
      const startTime = currentTimestamp.add(86400);

      await vibVesting.addBeneficiary(
        user1Address,
        totalAmount,
        startTime,
        cliffDuration,
        vestingDuration
      );
    });

    it("Should allow admin to revoke beneficiary", async function () {
      const user1Address = await user1.getAddress();
      await advanceTime(86400); // 1 day (start)
      await advanceTime(cliffDuration); // Cliff period
      await advanceTime(30 * 86400); // 1 month after cliff

      await vibVesting.connect(owner).revokeBeneficiary(user1Address);

      const beneficiary = await vibVesting.beneficiaries(user1Address);
      expect(beneficiary.revoked).to.be.true;
    });

    it("Should emit BeneficiaryRevoked event", async function () {
      const user1Address = await user1.getAddress();
      await advanceTime(86400); // 1 day (start)
      await advanceTime(cliffDuration); // Cliff period
      await advanceTime(30 * 86400); // 1 month after cliff

      await expectEvent(
        vibVesting.connect(owner).revokeBeneficiary(user1Address),
        vibVesting,
        "BeneficiaryRevoked",
        [user1Address]
      );
    });

    it("Should return unvested tokens on revoke", async function () {
      const user1Address = await user1.getAddress();
      await advanceTime(86400); // 1 day (start)
      await advanceTime(cliffDuration); // Cliff period
      await advanceTime(30 * 86400); // 1 month after cliff

      const balanceBefore = await vibeToken.balanceOf(await owner.getAddress());
      await vibVesting.connect(owner).revokeBeneficiary(user1Address);
      const balanceAfter = await vibeToken.balanceOf(await owner.getAddress());

      // Should return 11/12 of tokens (1 month vested, 11 unvested)
      const returned = balanceAfter.sub(balanceBefore);
      expect(returned.gte(totalAmount.mul(10).div(12))).to.be.true;
    });

    it("Should allow beneficiary to claim vested amount after revoke", async function () {
      const user1Address = await user1.getAddress();
      await advanceTime(86400); // 1 day (start)
      await advanceTime(cliffDuration); // Cliff period
      await advanceTime(30 * 86400); // 1 month after cliff

      await vibVesting.connect(owner).revokeBeneficiary(user1Address);

      const balanceBefore = await vibeToken.balanceOf(user1Address);
      await vibVesting.connect(user1).claim();
      const balanceAfter = await vibeToken.balanceOf(user1Address);

      const claimed = balanceAfter.sub(balanceBefore);
      const expected = totalAmount.mul(1).div(12);
      expect(claimed).to.equal(expected);
    });

    it("Should fail when non-admin tries to revoke", async function () {
      const user1Address = await user1.getAddress();

      await expectRevertCustomError(
        vibVesting.connect(user1).revokeBeneficiary(user1Address),
        vibVesting,
        "Unauthorized"
      );
    });

    it("Should fail when revoking non-existent beneficiary", async function () {
      const user2Address = await user2.getAddress();

      await expectRevertCustomError(
        vibVesting.connect(owner).revokeBeneficiary(user2Address),
        vibVesting,
        "NotABeneficiary"
      );
    });
  });

  describe("Get Beneficiaries", function () {
    it("Should return all beneficiaries", async function () {
      const totalAmount = parseEther("100000");
      await vibeToken.connect(owner).approve(vibVesting.address, totalAmount.mul(3));

      const currentTimestamp = await time.latest();
      const startTime = currentTimestamp.add(86400);

      for (const user of [user1, user2, signers.user3]) {
        await vibVesting.addBeneficiary(
          await user.getAddress(),
          totalAmount,
          startTime,
          CLIFF_PERIODS.TEAM_CLIFF,
          VESTING_PERIODS.TEAM_VESTING
        );
      }

      const beneficiaries = await vibVesting.getBeneficiaries();
      expect(beneficiaries.length).to.equal(3);
    });

    it("Should return empty array when no beneficiaries", async function () {
      const beneficiaries = await vibVesting.getBeneficiaries();
      expect(beneficiaries.length).to.equal(0);
    });
  });

  describe("Admin Functions", function () {
    it("Should allow admin to transfer ownership", async function () {
      await vibVesting.connect(owner).transferAdmin(await user1.getAddress());

      expect(await vibVesting.admin()).to.equal(await user1.getAddress());
    });

    it("Should fail when non-admin tries to transfer ownership", async function () {
      await expectRevertCustomError(
        vibVesting.connect(user1).transferAdmin(await user2.getAddress()),
        vibVesting,
        "Unauthorized"
      );
    });

    it("Should fail when transferring to zero address", async function () {
      await expectRevertCustomError(
        vibVesting.connect(owner).transferAdmin(ethers.constants.AddressZero),
        vibVesting,
        "InvalidAddress"
      );
    });
  });
});
