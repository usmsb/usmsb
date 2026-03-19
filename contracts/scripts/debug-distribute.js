// debug-distribute.js
// Debug why distributeToPools reverts
require('dotenv').config();
const { ethers } = require('hardhat');

const VIBETOKEN = '0x37A3042A16fE18e8dCE5f3eeC4c89FB9c1C36E2f';
const PRIVATE_KEY = process.env.PRIVATE_KEY;

const POOLS = {
  stakingPool:           '0x945F7bebD2bD7b839401620C0e6dC2a798793F9f',
  ecosystemPool:         '0x2D6d4A6275510e3ee30C8D790b28feC92fc19806',
  governancePool:        '0x1977ca17eDDA9A547f5ea7C92474862689e1d11E',
  reservePool:           '0x9fFBEbd283C0Fa4C646a2D5b8e293D9a2C88a091',
  teamVesting:           '0xd6f2080aC2c554B49eDf1dAF6624f3C1db01f553',
  earlySupporterVesting: '0xd6f2080aC2c554B49eDf1dAF6624f3C1db01f553',
  communityFund:         '0xeE95c1E803EF00eD95F9464A3C75a97420eD997a',
  liquidityManager:      '0x993438425a2480B3B06c880F39053E517423AD1f',
  airdropDistributor:   '0x72F67D07D02489361A5abCf966A440eC06a439Ce',
};

async function main() {
  const provider = new ethers.JsonRpcProvider('https://sepolia.base.org');
  const wallet = new ethers.Wallet(PRIVATE_KEY, provider);
  const token = await ethers.getContractFactory('VIBEToken', wallet).then(f => f.attach(VIBETOKEN));

  // Check current state
  console.log('VIBEToken:', VIBETOKEN);
  console.log('Owner:', await token.owner());
  console.log('tokensDistributed:', await token.tokensDistributed());

  // Check total supply
  const totalSupply = await token.totalSupply();
  console.log('totalSupply:', ethers.formatUnits(totalSupply, 18), 'VIBE');
  console.log('TOTAL_SUPPLY (1B):', ethers.formatUnits(ethers.parseUnits('1000000000', 18), 18));

  // Check if any pool already has tokens
  console.log('\nPool balances:');
  for (const [name, addr] of Object.entries(POOLS)) {
    const bal = await token.balanceOf(addr);
    console.log(`  ${name.padEnd(24)}: ${ethers.formatUnits(bal, 18)} VIBE`);
  }

  // Try calling with staticCall to see exact revert reason
  console.log('\nTrying distributeToPools (staticCall)...');
  try {
    const result = await token.distributeToPools.staticCall(
      POOLS.stakingPool, POOLS.ecosystemPool, POOLS.governancePool, POOLS.reservePool,
      POOLS.teamVesting, POOLS.earlySupporterVesting, POOLS.communityFund,
      POOLS.liquidityManager, POOLS.airdropDistributor
    );
    console.log('Success! Result:', result);
  } catch(e) {
    console.log('Revert reason:', e.message.slice(0, 200));
    // Try to decode the error
    if (e.data) {
      console.log('Error data:', e.data);
    }
  }
}

main().catch(console.error);
