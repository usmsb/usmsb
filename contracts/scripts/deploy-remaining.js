// scripts/deploy-remaining.js
// Resume deployment with fresh wallet per tx to avoid nonce cache issues
require('dotenv').config();
const { ethers } = require('hardhat');
const fs = require('fs');

const PRIVATE_KEY = process.env.PRIVATE_KEY;
const RPC_URL = 'https://sepolia.base.org';
const DEPLOYMENT_DIR = './deployments';

const WETH = '0x4200000000000000000000000000000000000006';
const DEX_ROUTER = '0xf253b36702f9a4da019377acfee8658e7136b231';

async function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

async function getFreshWallet() {
  const provider = new ethers.JsonRpcProvider(RPC_URL);
  return new ethers.Wallet(PRIVATE_KEY, provider);
}

async function getOnChainNonce(wallet) {
  return parseInt(await wallet.provider.send('eth_getTransactionCount', [wallet.address, 'latest']), 16);
}

async function main() {
  const provider0 = new ethers.JsonRpcProvider(RPC_URL);
  const wallet0 = new ethers.Wallet(PRIVATE_KEY, provider0);
  console.log('Deployer:', wallet0.address);
  console.log('Network chainId:', (await provider0.getNetwork()).chainId.toString());

  const startNonce = await getOnChainNonce(wallet0);
  console.log('Starting nonce:', startNonce);

  const deployed = {};
  if (fs.existsSync(`${DEPLOYMENT_DIR}/latest.json`)) {
    const existing = JSON.parse(fs.readFileSync(`${DEPLOYMENT_DIR}/latest.json`, 'utf8'));
    Object.assign(deployed, existing.contracts || existing);
    console.log('Loaded existing deployments:', Object.keys(deployed).length, 'contracts');
  }

  let txCount = 0;
  async function deploy(name, factoryPath, args) {
    if (deployed[name]) {
      console.log(`[${name}] already deployed: ${deployed[name]}`);
      return;
    }
    // Create fresh wallet + provider for each tx
    const wallet = await getFreshWallet();
    const currentNonce = await getOnChainNonce(wallet);
    const factory = await ethers.getContractFactory(factoryPath, wallet);
    txCount++;
    console.log(`\n[${name}] nonce=${currentNonce} (tx #${txCount})`);
    const contract = await factory.deploy(...args, { nonce: currentNonce });
    await contract.waitForDeployment();
    deployed[name] = await contract.getAddress();
    console.log(`=> ${deployed[name]}`);
    await delay(4000);
  }

  const vibeToken = deployed.VIBEToken;
  if (!vibeToken) { console.error('ERROR: No VIBEToken address!'); process.exit(1); }

  // Stage 5 remaining
  await deploy('AirdropDistributor', 'AirdropDistributor',
    [vibeToken, wallet0.address, ethers.ZeroHash]);

  await deploy('CommunityStableFund', 'CommunityStableFund',
    [vibeToken, WETH, ethers.ZeroAddress, DEX_ROUTER, ethers.parseEther('10000')]);

  await deploy('LiquidityManager', 'LiquidityManager',
    [vibeToken, WETH, DEX_ROUTER, wallet0.address]);

  // Stage 6 governance
  await deploy('VIBGovernance', 'VIBGovernance', []);
  await deploy('VIBGovernanceDelegation', 'VIBGovernanceDelegation', []);
  await deploy('VIBContributionPoints', 'VIBContributionPoints', []);

  // VIBVEPoints
  await deploy('VIBVEPoints', 'VIBVEPoints',
    [deployed.VIBStaking, deployed.VIBOutputReward, deployed.VIBGovernance]);

  // VIBDispute
  await deploy('VIBDispute', 'VIBDispute',
    [vibeToken, deployed.VIBStaking, deployed.VIBGovernance,
     ethers.ZeroAddress, ethers.ZeroAddress, ethers.ZeroHash]);

  // Stage 7
  await deploy('AgentWallet', 'AgentWallet',
    [wallet0.address, wallet0.address, vibeToken, deployed.AgentRegistry, deployed.VIBStaking]);

  // EmissionController (5 params)
  await deploy('EmissionController', 'src/automation/EmissionController.sol:EmissionController',
    [vibeToken, deployed.VIBStaking, deployed.VIBEcosystemPool,
     deployed.VIBGovernance, deployed.VIBReserve]);

  // Save intermediate
  const existing = fs.existsSync(`${DEPLOYMENT_DIR}/latest.json`)
    ? JSON.parse(fs.readFileSync(`${DEPLOYMENT_DIR}/latest.json`, 'utf8')) : {};
  existing.contracts = { ...existing.contracts, ...deployed };
  existing.timestamp = new Date().toISOString();
  existing.network = 'baseSepolia';
  existing.deployer = wallet0.address;
  fs.writeFileSync(`${DEPLOYMENT_DIR}/latest.json`, JSON.stringify(existing, null, 2));

  console.log('\n============================================================');
  console.log(' Remaining contracts deployed! Total contracts:', Object.keys(deployed).length);
  console.log('============================================================');
}

main().catch(err => {
  console.error('\nError:', err.message || err);
  process.exit(1);
});
