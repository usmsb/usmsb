// scripts/redeploy-token.js
// Deploy ONLY VIBEToken + distribute pools (all other contracts already deployed)
require('dotenv').config();
const { ethers } = require('hardhat');
const fs = require('fs');
const path = require('path');

// Already deployed addresses (from last successful run)
const POOLS = {
  VIBStaking:           '0x945F7bebD2bD7b839401620C0e6dC2a798793F9f',
  VIBVesting:           '0xd6f2080aC2c554B49eDf1dAF6624f3C1db01f553',
  VIBReserve:           '0x9fFBEbd283C0Fa4C646a2D5b8e293D9a2C88a091',
  VIBEcosystemPool:    '0x2D6d4A6275510e3ee30C8D790b28feC92fc19806',
  VIBGovernance:        '0x1977ca17eDDA9A547f5ea7C92474862689e1d11E',
  CommunityStableFund:  '0xeE95c1E803EF00eD95F9464A3C75a97420eD997a',
  LiquidityManager:     '0x993438425a2480B3B06c880F39053E517423AD1f',
  AirdropDistributor:   '0x72F67D07D02489361A5abCf966A440eC06a439Ce',
};

const PRIVATE_KEY = process.env.PRIVATE_KEY;
const RPC_URL = 'https://sepolia.base.org';
const DEPLOYMENT_DIR = './deployments';

async function main() {
  const provider = new ethers.JsonRpcProvider(RPC_URL);
  const wallet = new ethers.Wallet(PRIVATE_KEY, provider);
  console.log('Deployer:', wallet.address);

  // Deploy fresh VIBEToken
  console.log('\nDeploying new VIBEToken...');
  const nonce = parseInt(await provider.send('eth_getTransactionCount', [wallet.address, 'latest']), 16);
  const VIBEToken = await ethers.getContractFactory('VIBEToken', wallet);
  const token = await VIBEToken.deploy('VIBE Token', 'VIBE', { nonce });
  await token.waitForDeployment();
  const tokenAddr = await token.getAddress();
  console.log('VIBEToken:', tokenAddr);
  await new Promise(r => setTimeout(r, 5000));

  // Distribute pools
  const pools = {
    stakingPool:           POOLS.VIBStaking,
    ecosystemPool:         POOLS.VIBEcosystemPool,
    governancePool:      POOLS.VIBGovernance,
    reservePool:          POOLS.VIBReserve,
    teamVesting:          POOLS.VIBVesting,
    earlySupporterVesting: POOLS.VIBVesting,
    communityFund:        POOLS.CommunityStableFund,
    liquidityManager:     POOLS.LiquidityManager,
    airdropDistributor:   POOLS.AirdropDistributor,
  };

  const TOTAL_SUPPLY = ethers.parseUnits('1000000000', 18);
  const bps = 10000n;
  const amounts = {
    stakingPool:           TOTAL_SUPPLY * 2835n / bps,
    ecosystemPool:        TOTAL_SUPPLY * 1890n / bps,
    governancePool:     TOTAL_SUPPLY * 945n / bps,
    reservePool:         TOTAL_SUPPLY * 630n / bps,
    teamVesting:         TOTAL_SUPPLY * 800n / bps,
    earlySupporterVesting:TOTAL_SUPPLY * 400n / bps,
    communityFund:       TOTAL_SUPPLY * 600n / bps,
    liquidityManager:    TOTAL_SUPPLY * 1200n / bps,
    airdropDistributor:  TOTAL_SUPPLY * 700n / bps,
  };

  console.log('\nCalling distributeToPools...');
  const nonce2 = parseInt(await provider.send('eth_getTransactionCount', [wallet.address, 'latest']), 16);
  const tx = await token.distributeToPools(
    pools.stakingPool, pools.ecosystemPool, pools.governancePool, pools.reservePool,
    pools.teamVesting, pools.earlySupporterVesting, pools.communityFund,
    pools.liquidityManager, pools.airdropDistributor,
    { nonce: nonce2 }
  );
  await tx.wait();
  console.log('Tokens distributed!');
  await new Promise(r => setTimeout(r, 3000));

  // Verify
  console.log('\nVerifying:');
  for (const [k, addr] of Object.entries(pools)) {
    const bal = await token.balanceOf(addr);
    const exp = amounts[k];
    const ok = bal === exp ? '✓' : '✗ MISMATCH';
    console.log(`  ${ok} ${k.padEnd(24)}: ${ethers.formatUnits(bal, 18)} VIBE`);
  }

  // Save deployment
  const result = {
    timestamp: new Date().toISOString(),
    network: 'baseSepolia',
    deployer: wallet.address,
    contracts: {
      VIBEToken: tokenAddr,
      ...POOLS,
    },
    pools,
    distribution: Object.fromEntries(Object.entries(amounts).map(([k, v]) => [k, ethers.formatUnits(v, 18)])),
  };

  fs.writeFileSync(path.join(DEPLOYMENT_DIR, 'latest.json'), JSON.stringify(result, null, 2));
  console.log('\nSaved to deployments/latest.json');
  console.log('DONE! VIBEToken:', tokenAddr);
}

main().catch(err => {
  console.error('\nError:', err.message || err);
  process.exit(1);
});
