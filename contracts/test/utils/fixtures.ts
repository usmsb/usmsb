import { ethers } from "hardhat";
import { BigNumber, Contract, Signer } from "ethers";
import { expect } from "chai";
import {
  VIBEToken,
  VIBStaking,
  VIBVesting,
  VIBIdentity
} from "../../typechain-types";
import { parseEther } from "ethers/lib/utils";
import {
  INITIAL_SUPPLY,
  MIN_STAKE_AMOUNT,
  STAKING_REWARDS_POOL,
  SECONDS_PER_YEAR,
  IDENTITY_TYPES
} from "./constants";

export interface Contracts {
  vibeToken: VIBEToken;
  vibStaking: VIBStaking;
  vibVesting: VIBVesting;
  vibIdentity: VIBIdentity;
}

export interface Signers {
  owner: Signer;
  admin: Signer;
  user1: Signer;
  user2: Signer;
  user3: Signer;
  user4: Signer;
  user5: Signer;
}

/**
 * Deploy all contracts for testing
 */
export async function deployFixtures(): Promise<{
  contracts: Contracts;
  signers: Signers;
}> {
  const signers = await getSigners();

  // Deploy VIBE Token
  const VIBEToken = await ethers.getContractFactory("VIBEToken");
  const vibeToken = (await VIBEToken.deploy(
    await signers.owner.getAddress()
  )) as VIBEToken;
  await vibeToken.deployed();

  // Deploy VIBIdentity (SBT)
  const VIBIdentity = await ethers.getContractFactory("VIBIdentity");
  const vibIdentity = (await VIBIdentity.deploy()) as VIBIdentity;
  await vibIdentity.deployed();

  // Deploy VIBStaking
  const VIBStaking = await ethers.getContractFactory("VIBStaking");
  const vibStaking = (await VIBStaking.deploy(
    vibeToken.address,
    vibeToken.address, // rewards token same as staking token
    parseEther("10000"), // base APR = 10%
    await signers.owner.getAddress()
  )) as VIBStaking;
  await vibStaking.deployed();

  // Grant minter role to staking contract
  await vibeToken.grantRole(
    await vibeToken.MINTER_ROLE(),
    vibStaking.address
  );

  // Deploy VIBVesting
  const VIBVesting = await ethers.getContractFactory("VIBVesting");
  const vibVesting = (await VIBVesting.deploy(
    vibeToken.address,
    await signers.owner.getAddress()
  )) as VIBVesting;
  await vibVesting.deployed();

  // Grant minter role to vesting contract
  await vibeToken.grantRole(
    await vibeToken.MINTER_ROLE(),
    vibVesting.address
  );

  // Mint rewards to staking contract
  await vibeToken.mint(vibStaking.address, STAKING_REWARDS_POOL);

  // Transfer tokens to test users
  for (const signer of [
    signers.user1,
    signers.user2,
    signers.user3,
    signers.user4,
    signers.user5
  ]) {
    await vibeToken.mint(await signer.getAddress(), parseEther("1000000"));
  }

  // Mint identity tokens to users
  await vibIdentity.connect(signers.owner).mint(
    await signers.user1.getAddress(),
    IDENTITY_TYPES.VERIFIED,
    "Verified User 1"
  );
  await vibIdentity.connect(signers.owner).mint(
    await signers.user2.getAddress(),
    IDENTITY_TYPES.KYC_VERIFIED,
    "KYC Verified User 2"
  );
  await vibIdentity.connect(signers.owner).mint(
    await signers.user3.getAddress(),
    IDENTITY_TYPES.INSTITUTION,
    "Institutional User 3"
  );

  const contracts = {
    vibeToken,
    vibStaking,
    vibVesting,
    vibIdentity
  };

  return { contracts, signers };
}

/**
 * Get signers for testing
 */
export async function getSigners(): Promise<Signers> {
  const signers = await ethers.getSigners();
  return {
    owner: signers[0],
    admin: signers[1],
    user1: signers[2],
    user2: signers[3],
    user3: signers[4],
    user4: signers[5],
    user5: signers[6]
  };
}

/**
 * Get address from signer
 */
export async function getAddress(signer: Signer): Promise<string> {
  return await signer.getAddress();
}

/**
 * Setup staking position
 */
export async function setupStakingPosition(
  staking: Contract,
  token: Contract,
  user: Signer,
  amount: BigNumber,
  lockDuration: number
): Promise<void> {
  // Approve staking contract
  await token.connect(user).approve(staking.address, amount);
  // Stake
  await staking.connect(user).stake(amount, lockDuration);
}

/**
 * Setup vesting schedule
 */
export async function setupVestingSchedule(
  vesting: Contract,
  token: Contract,
  beneficiary: string,
  totalAmount: BigNumber,
  startTime: BigNumber,
  cliffDuration: BigNumber,
  vestingDuration: BigNumber
): Promise<void> {
  await vesting.addBeneficiary(
    beneficiary,
    totalAmount,
    startTime,
    cliffDuration,
    vestingDuration
  );
}

/**
 * Advance time and blocks
 */
export async function advanceTime(seconds: number): Promise<void> {
  await ethers.provider.send("evm_increaseTime", [seconds]);
  await ethers.provider.send("evm_mine", []);
}

/**
 * Get current timestamp
 */
export async function getCurrentTimestamp(): Promise<number> {
  const block = await ethers.provider.getBlock("latest");
  return block.timestamp;
}

/**
 * Mine blocks
 */
export async function mineBlocks(count: number): Promise<void> {
  for (let i = 0; i < count; i++) {
    await ethers.provider.send("evm_mine", []);
  }
}

/**
 * Get contract balance
 */
export async function getBalance(
  token: Contract,
  address: string
): Promise<BigNumber> {
  return await token.balanceOf(address);
}

/**
 * Approve token spending
 */
export async function approveTokens(
  token: Contract,
  owner: Signer,
  spender: string,
  amount: BigNumber
): Promise<void> {
  await token.connect(owner).approve(spender, amount);
}

/**
 * Expect revert with custom error
 */
export async function expectRevertCustomError(
  tx: Promise<any>,
  contract: Contract,
  errorName: string
): Promise<void> {
  await expect(tx).to.be.revertedWithCustomError(contract, errorName);
}

/**
 * Expect event emission
 */
export async function expectEvent(
  tx: Promise<any>,
  contract: Contract,
  eventName: string,
  args?: any[]
): Promise<any> {
  const receipt = await (await tx).wait();
  const event = receipt.events?.find((e: any) => e.event === eventName);
  expect(event, `Event ${eventName} not found`).to.not.be.undefined;

  if (args) {
    for (let i = 0; i < args.length; i++) {
      expect(event.args[i]).to.deep.equal(args[i]);
    }
  }

  return event;
}

/**
 * Get event arguments
 */
export async function getEventArgs(
  tx: Promise<any>,
  contract: Contract,
  eventName: string
): Promise<any> {
  const receipt = await (await tx).wait();
  const event = receipt.events?.find((e: any) => e.event === eventName);
  expect(event, `Event ${eventName} not found`).to.not.be.undefined;
  return event.args;
}

/**
 * Calculate expected rewards based on APR
 */
export function calculateExpectedRewards(
  stakedAmount: BigNumber,
  apr: number,
  daysStaked: number
): BigNumber {
  const secondsStaked = daysStaked * 86400;
  const annualRewards = stakedAmount.mul(apr).div(10000);
  return annualRewards.mul(secondsStaked).div(SECONDS_PER_YEAR);
}
