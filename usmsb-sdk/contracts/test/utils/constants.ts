import { BigNumber } from "ethers";
import { parseEther } from "ethers/lib/utils";

/**
 * Token constants
 */
export const TOKEN_NAME = "VIBE Token";
export const TOKEN_SYMBOL = "VIBE";
export const TOKEN_DECIMALS = 18;
export const INITIAL_SUPPLY = parseEther("1000000000"); // 1 billion

/**
 * Time constants (in seconds)
 */
export const SECONDS_PER_DAY = 86400;
export const SECONDS_PER_WEEK = 7 * SECONDS_PER_DAY;
export const SECONDS_PER_MONTH = 30 * SECONDS_PER_DAY;
export const SECONDS_PER_YEAR = 365 * SECONDS_PER_DAY;

/**
 * Staking constants
 */
export const REWARD_RATE_PRECISION = 10000; // 4 decimal places
export const MIN_STAKE_AMOUNT = parseEther("100");
export const MAX_STAKE_AMOUNT = parseEther("1000000");
export const REWARD_PER_TOKEN_PRECISION = 1e18;

export const LOCK_DURATIONS = {
  NONE: 0,
  ONE_MONTH: SECONDS_PER_MONTH,
  THREE_MONTHS: 3 * SECONDS_PER_MONTH,
  SIX_MONTHS: 6 * SECONDS_PER_MONTH,
  TWELVE_MONTHS: 12 * SECONDS_PER_MONTH
};

export const LOCK_BONUS_RATES = {
  NONE: 0,
  ONE_MONTH: 500, // 5%
  THREE_MONTHS: 1500, // 15%
  SIX_MONTHS: 3500, // 35%
  TWELVE_MONTHS: 8000 // 80%
};

export const TIER_THRESHOLDS = {
  BRONZE: parseEther("1000"),
  SILVER: parseEther("10000"),
  GOLD: parseEther("100000"),
  PLATINUM: parseEther("1000000"),
  DIAMOND: parseEther("10000000")
};

export const TIER_BONUS_RATES = {
  BRONZE: 0,
  SILVER: 1000, // 10%
  GOLD: 2500, // 25%
  PLATINUM: 5000, // 50%
  DIAMOND: 10000 // 100%
};

/**
 * Vesting constants
 */
export const VESTING_PERIODS = {
  TEAM_VESTING: 4 * SECONDS_PER_YEAR,
  ADVISOR_VESTING: 2 * SECONDS_PER_YEAR,
  COMMUNITY_VESTING: 3 * SECONDS_PER_YEAR,
  ECOSYSTEM_VESTING: SECONDS_PER_YEAR
};

export const CLIFF_PERIODS = {
  TEAM_CLIFF: SECONDS_PER_YEAR,
  ADVISOR_CLIFF: 6 * SECONDS_PER_MONTH,
  COMMUNITY_CLIFF: 3 * SECONDS_PER_MONTH,
  ECOSYSTEM_CLIFF: 0
};

export const VESTING_RELEASE_INTERVAL = SECONDS_PER_MONTH;

/**
 * Identity/SBT constants
 */
export const IDENTITY_TYPES = {
  UNVERIFIED: 0,
  VERIFIED: 1,
  KYC_VERIFIED: 2,
  INSTITUTION: 3,
  DAO_MEMBER: 4,
  TEAM_MEMBER: 5,
  PARTNER: 6
};

export const IDENTITY_METADATA = {
  UNVERIFIED: "Unverified User",
  VERIFIED: "Verified User",
  KYC_VERIFIED: "KYC Verified",
  INSTITUTION: "Institutional Investor",
  DAO_MEMBER: "DAO Member",
  TEAM_MEMBER: "VIBE Team Member",
  PARTNER: "VIBE Partner"
};

/**
 * Governance constants
 */
export const GOVERNANCE_QUORUM = 4; // 4%
export const GOVERNANCE_THRESHOLD = 50; // 50%
export const GOVERNANCE_VOTING_DELAY = SECONDS_PER_DAY;
export const GOVERNANCE_VOTING_PERIOD = 7 * SECONDS_PER_DAY;

/**
 * Fee constants
 */
export const PLATFORM_FEE_RATE = 250; // 2.5%
export const FEE_PRECISION = 10000;

/**
 * Test account balances
 */
export const INITIAL_BALANCE = parseEther("1000000");
export const STAKING_REWARDS_POOL = parseEther("100000000");

/**
 * Error messages
 */
export const ERROR_MESSAGES = {
  INSUFFICIENT_BALANCE: "ERC20InsufficientBalance",
  INSUFFICIENT_ALLOWANCE: "ERC20InsufficientAllowance",
  INVALID_AMOUNT: "InvalidAmount",
  INVALID_DURATION: "InvalidDuration",
  ALREADY_STAKED: "AlreadyStaked",
  NOT_STAKED: "NotStaked",
  LOCK_NOT_EXPIRED: "LockNotExpired",
  INVALID_BENEFICIARY: "InvalidBeneficiary",
  ALREADY_MINTED: "AlreadyMinted",
  TRANSFER_RESTRICTED: "TransferRestricted",
  PAUSED: "Pausable: paused",
  UNAUTHORIZED: "Unauthorized"
};

/**
 * Chain IDs
 */
export const CHAIN_IDS = {
  ETHEREUM: 1,
  GOERLI: 5,
  SEPOLIA: 11155111,
  POLYGON: 137,
  MUMBAI: 80001,
  ARBITRUM: 42161,
  OPTIMISM: 10,
  BASE: 8453,
  BASE_SEPOLIA: 84532,
  HARDHAT: 31337
};

/**
 * Gas constants
 */
export const GAS_LIMITS = {
  DEFAULT: 5000000,
  HIGH: 10000000,
  MINT_SBT: 300000,
  STAKE: 500000,
  UNSTAKE: 600000,
  CLAIM: 400000
};

/**
 * Emission schedule constants
 */
export const EMISSION_SCHEDULE = [
  { year: 1, rate: 1000 }, // 10% annual inflation
  { year: 2, rate: 800 },  // 8%
  { year: 3, rate: 600 },  // 6%
  { year: 4, rate: 400 },  // 4%
  { year: 5, rate: 200 }   // 2%
];

/**
 * Reward calculation constants
 */
export const BASE_APR = 1000; // 10%
export const MAX_APR = 2500; // 25%

/**
 * Constants for testing
 */
export const ZERO_ADDRESS = "0x0000000000000000000000000000000000000000";
export const MAX_UINT256 = BigNumber.from(2).pow(256).sub(1);
export const ONE_YEAR = SECONDS_PER_YEAR;
