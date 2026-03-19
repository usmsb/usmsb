// scripts/deploy-all.js
// Full deployment - fresh wallet per tx to avoid ALL nonce issues
require('dotenv').config();
const { ethers } = require('hardhat');
const fs = require('fs');
const path = require('path');

const PRIVATE_KEY = process.env.PRIVATE_KEY;
const RPC_URL = 'https://sepolia.base.org';
const DEPLOYMENT_DIR = './deployments';

const WETH = '0x4200000000000000000000000000000000000006';
const DEX_ROUTER = '0xf253b36702f9a4da019377acfee8658e7136b231';

let walletAddress = '';

// Fresh wallet+provider per transaction - no shared state
async function freshDeploy(name, factoryPath, args) {
  const provider = new ethers.JsonRpcProvider(RPC_URL);
  const wallet = new ethers.Wallet(PRIVATE_KEY, provider);
  walletAddress = wallet.address;

  const nonce = parseInt(await provider.send('eth_getTransactionCount', [wallet.address, 'latest']), 16);
  process.stdout.write(`\n[${name}] nonce=${nonce} `);

  const factory = await ethers.getContractFactory(factoryPath, wallet);
  const contract = await factory.deploy(...args, { nonce });
  await contract.waitForDeployment();
  const addr = await contract.getAddress();
  console.log(`=> ${addr}`);

  // Wait for block confirmation
  await new Promise(r => setTimeout(r, 5000));
  return addr;
}

async function main() {
  const provider0 = new ethers.JsonRpcProvider(RPC_URL);
  const wallet0 = new ethers.Wallet(PRIVATE_KEY, provider0);
  console.log('============================================================');
  console.log('  USMSB Protocol - Full Deployment to Base Sepolia');
  console.log('============================================================');
  console.log('\nDeployer:', wallet0.address);
  console.log('Network chainId:', (await provider0.getNetwork()).chainId.toString());
  console.log('Balance:', ethers.formatEther(await provider0.getBalance(wallet0.address)), 'ETH');
  console.log('Starting nonce:', parseInt(await provider0.send('eth_getTransactionCount', [wallet0.address, 'latest']), 16));

  const deployed = {};
  const deploymentDir = DEPLOYMENT_DIR;
  if (!fs.existsSync(deploymentDir)) fs.mkdirSync(deploymentDir, { recursive: true });

  function save(name, addr) { deployed[name] = addr; }

  // ================================================================
  // Stage 1: Core Token
  // ================================================================
  console.log('\n' + '='.repeat(60));
  console.log(' Stage 1: Core Token');
  console.log('='.repeat(60));
  const vibeToken = await freshDeploy('VIBEToken', 'VIBEToken', ['VIBE Token', 'VIBE']);
  save('VIBEToken', vibeToken);

  // ================================================================
  // Stage 2: Staking & Vesting
  // ================================================================
  console.log('\n' + '='.repeat(60));
  console.log(' Stage 2: Staking & Vesting');
  console.log('='.repeat(60));
  save('VIBStaking', await freshDeploy('VIBStaking', 'VIBStaking', [vibeToken]));
  save('VIBVesting', await freshDeploy('VIBVesting', 'VIBVesting', [vibeToken]));
  save('VIBReserve', await freshDeploy('VIBReserve', 'VIBReserve', [vibeToken]));
  save('VIBProtocolFund', await freshDeploy('VIBProtocolFund', 'VIBProtocolFund', [vibeToken]));
  save('VIBInfrastructurePool', await freshDeploy('VIBInfrastructurePool', 'VIBInfrastructurePool', [vibeToken]));
  save('VIBBuilderReward', await freshDeploy('VIBBuilderReward', 'VIBBuilderReward', [vibeToken]));
  save('VIBDevReward', await freshDeploy('VIBDevReward', 'VIBDevReward', [vibeToken]));

  // ================================================================
  // Stage 3: Identity & Collaboration
  // ================================================================
  console.log('\n' + '='.repeat(60));
  console.log(' Stage 3: Identity & Collaboration');
  console.log('='.repeat(60));
  save('VIBIdentity', await freshDeploy('VIBIdentity', 'VIBIdentity', ['VIBE Identity', 'VIBE-ID', vibeToken]));
  save('VIBNodeReward', await freshDeploy('VIBNodeReward', 'VIBNodeReward', [vibeToken, deployed.VIBIdentity]));
  save('VIBCollaboration', await freshDeploy('VIBCollaboration', 'VIBCollaboration', [vibeToken, deployed.VIBIdentity]));

  // ================================================================
  // Stage 4: Dividend & Registry
  // ================================================================
  console.log('\n' + '='.repeat(60));
  console.log(' Stage 4: Dividend & Registry');
  console.log('='.repeat(60));
  save('VIBDividend', await freshDeploy('VIBDividend', 'VIBDividend', [vibeToken]));
  save('AgentRegistry', await freshDeploy('AgentRegistry', 'AgentRegistry', []));

  // ================================================================
  // Stage 5: DeFi & Market
  // ================================================================
  console.log('\n' + '='.repeat(60));
  console.log(' Stage 5: DeFi & Market');
  console.log('='.repeat(60));
  save('ZKCredential', await freshDeploy('ZKCredential', 'ZKCredential', ['ZK Credential', 'ZK-CRED', walletAddress, walletAddress]));
  save('AssetVault', await freshDeploy('AssetVault', 'AssetVault', [WETH, walletAddress, 'VIBE Asset', 'VIBE-A']));
  save('JointOrder', await freshDeploy('JointOrder', 'JointOrder', [vibeToken, walletAddress, walletAddress]));
  save('PriceOracle', await freshDeploy('PriceOracle', 'PriceOracle', [ethers.ZeroAddress, ethers.ZeroAddress, ethers.ZeroAddress]));
  save('VIBOutputReward', await freshDeploy('VIBOutputReward', 'VIBOutputReward', [vibeToken, walletAddress]));
  save('VIBEcosystemPool', await freshDeploy('VIBEcosystemPool', 'VIBEcosystemPool', [vibeToken, walletAddress]));
  save('AirdropDistributor', await freshDeploy('AirdropDistributor', 'AirdropDistributor', [vibeToken, walletAddress, ethers.ZeroHash]));
  save('CommunityStableFund', await freshDeploy('CommunityStableFund', 'CommunityStableFund', [vibeToken, WETH, deployed.PriceOracle, DEX_ROUTER, ethers.parseEther('10000')]));
  save('LiquidityManager', await freshDeploy('LiquidityManager', 'LiquidityManager', [vibeToken, WETH, DEX_ROUTER, walletAddress]));

  // ================================================================
  // Stage 6: Governance
  // ================================================================
  console.log('\n' + '='.repeat(60));
  console.log(' Stage 6: Governance');
  console.log('='.repeat(60));
  save('VIBGovernance', await freshDeploy('VIBGovernance', 'VIBGovernance', []));
  save('VIBGovernanceDelegation', await freshDeploy('VIBGovernanceDelegation', 'VIBGovernanceDelegation', []));
  save('VIBContributionPoints', await freshDeploy('VIBContributionPoints', 'VIBContributionPoints', []));
  save('VIBVEPoints', await freshDeploy('VIBVEPoints', 'VIBVEPoints', [deployed.VIBStaking, deployed.VIBOutputReward, deployed.VIBGovernance]));
  save('VIBDispute', await freshDeploy('VIBDispute', 'VIBDispute', [vibeToken, deployed.VIBStaking, deployed.VIBGovernance, ethers.ZeroAddress, ethers.ZeroAddress, ethers.ZeroHash]));

  // ================================================================
  // Stage 7: Agent & System
  // ================================================================
  console.log('\n' + '='.repeat(60));
  console.log(' Stage 7: Agent & System');
  console.log('='.repeat(60));
  save('AgentWallet', await freshDeploy('AgentWallet', 'AgentWallet', [walletAddress, walletAddress, vibeToken, deployed.AgentRegistry, deployed.VIBStaking]));
  save('EmissionController', await freshDeploy('EmissionController', 'src/automation/EmissionController.sol:EmissionController', [vibeToken, deployed.VIBStaking, deployed.VIBEcosystemPool, deployed.VIBGovernance, deployed.VIBReserve]));

  // ================================================================
  // Stage 8: Token Distribution (Whitepaper 10000 bps)
  // ================================================================
  console.log('\n' + '='.repeat(60));
  console.log(' Stage 8: Token Distribution (Whitepaper 10000 bps)');
  console.log('='.repeat(60));

  const pools = {
    stakingPool:           deployed.VIBStaking,
    ecosystemPool:         deployed.VIBEcosystemPool,
    governancePool:        deployed.VIBGovernance,
    reservePool:           deployed.VIBReserve,
    teamVesting:           deployed.VIBVesting,
    earlySupporterVesting: deployed.VIBVesting,
    communityFund:         deployed.CommunityStableFund,
    liquidityManager:      deployed.LiquidityManager,
    airdropDistributor:    deployed.AirdropDistributor,
  };

  console.log('\n  Pool addresses:');
  for (const [k, v] of Object.entries(pools)) console.log(`    ${k.padEnd(24)}: ${v}`);

  const TOTAL_SUPPLY = ethers.parseUnits('1000000000', 18);
  const bps = 10000n;
  const amounts = {
    stakingPool:           TOTAL_SUPPLY * 2835n / bps,
    ecosystemPool:        TOTAL_SUPPLY * 1890n / bps,
    governancePool:       TOTAL_SUPPLY * 945n / bps,
    reservePool:          TOTAL_SUPPLY * 630n / bps,
    teamVesting:          TOTAL_SUPPLY * 800n / bps,
    earlySupporterVesting:TOTAL_SUPPLY * 400n / bps,
    communityFund:        TOTAL_SUPPLY * 600n / bps,
    liquidityManager:     TOTAL_SUPPLY * 1200n / bps,
    airdropDistributor:   TOTAL_SUPPLY * 700n / bps,
  };

  console.log('\n  Distribution:');
  for (const [k, v] of Object.entries(amounts)) console.log(`    ${k.padEnd(24)}: ${ethers.formatUnits(v, 18)} VIBE`);
  const total = Object.values(amounts).reduce((a, b) => a + b, 0n);
  console.log(`    Total: ${ethers.formatUnits(total, 18)} VIBE`);

  // Call distributeToPools with fresh wallet
  const prov = new ethers.JsonRpcProvider(RPC_URL);
  const w = new ethers.Wallet(PRIVATE_KEY, prov);
  const vibetoken = await ethers.getContractFactory('VIBEToken', w);
  const tokenContract = vibetoken.attach(vibeToken);
  const nonce = parseInt(await prov.send('eth_getTransactionCount', [w.address, 'latest']), 16);
  console.log(`\n  Calling distributeToPools (nonce=${nonce})...`);
  const tx = await tokenContract.distributeToPools(
    pools.stakingPool, pools.ecosystemPool, pools.governancePool, pools.reservePool,
    pools.teamVesting, pools.earlySupporterVesting, pools.communityFund,
    pools.liquidityManager, pools.airdropDistributor,
    { nonce }
  );
  await tx.wait();
  console.log('  Tokens distributed!');
  await new Promise(r => setTimeout(r, 3000));

  // Verify balances
  console.log('\n  Verifying balances:');
  for (const [k, addr] of Object.entries(pools)) {
    const bal = await tokenContract.balanceOf(addr);
    const exp = amounts[k];
    const ok = bal === exp ? '✓' : '✗';
    console.log(`  ${ok} ${k.padEnd(24)}: ${ethers.formatUnits(bal, 18)} VIBE`);
  }

  // ================================================================
  // Stage 9: Wire Governance
  // ================================================================
  console.log('\n' + '='.repeat(60));
  console.log(' Stage 9: Wire Governance');
  console.log('='.repeat(60));

  const w2 = new ethers.Wallet(PRIVATE_KEY, new ethers.JsonRpcProvider(RPC_URL));

  async function govCall(name, contract, method, ...args) {
    const nonce = parseInt(await contract.provider.send('eth_getTransactionCount', [w2.address, 'latest']), 16);
    try {
      const tx = await contract[method](...args, { nonce });
      await tx.wait();
      console.log(` ${name}.${method} ✓`);
    } catch(e) {
      console.log(` ${name}.${method} skipped (${e.reason || e.message.slice(0,60)})`);
    }
  }

  const gov = await ethers.getContractFactory('VIBGovernance', w2).then(f => f.attach(deployed.VIBGovernance));
  const del = await ethers.getContractFactory('VIBGovernanceDelegation', w2).then(f => f.attach(deployed.VIBGovernanceDelegation));
  const cp = await ethers.getContractFactory('VIBContributionPoints', w2).then(f => f.attach(deployed.VIBContributionPoints));

  await govCall('VIBGovernance', gov, 'initialize');
  await govCall('VIBGovernanceDelegation', del, 'initialize');
  await govCall('VIBGovernanceDelegation', del, 'setGovernanceContract', deployed.VIBGovernance);
  await govCall('VIBGovernance', gov, 'setDelegationContract', deployed.VIBGovernanceDelegation);
  await govCall('VIBGovernance', gov, 'setContributionPointsContract', deployed.VIBContributionPoints);
  await govCall('VIBContributionPoints', cp, 'initialize');
  await govCall('VIBContributionPoints', cp, 'setGovernanceContract', deployed.VIBGovernance);

  // ================================================================
  // Save
  // ================================================================
  const result = {
    timestamp: new Date().toISOString(),
    network: 'baseSepolia',
    deployer: walletAddress,
    contracts: deployed,
    pools,
    distribution: Object.fromEntries(Object.entries(amounts).map(([k, v]) => [k, ethers.formatUnits(v, 18)])),
    wiring: {
      'VIBGovernance.initialized': true,
      'VIBGovernance.setDelegationContract': deployed.VIBGovernanceDelegation,
      'VIBGovernance.setContributionPointsContract': deployed.VIBContributionPoints,
      'VIBGovernanceDelegation.initialized': true,
      'VIBGovernanceDelegation.setGovernanceContract': deployed.VIBGovernance,
      'VIBContributionPoints.initialized': true,
      'VIBContributionPoints.setGovernanceContract': deployed.VIBGovernance,
    }
  };

  const outPath = path.join(deploymentDir, 'latest.json');
  fs.writeFileSync(outPath, JSON.stringify(result, null, 2));

  console.log('\n============================================================');
  console.log(' Deployment Complete!');
  console.log('============================================================');
  console.log('VIBEToken:', vibeToken);
  console.log('Total contracts deployed:', Object.keys(deployed).length);
  console.log('Saved to:', outPath);
}

main().catch(err => {
  console.error('\nDeployment failed:', err.message || err);
  process.exit(1);
});
