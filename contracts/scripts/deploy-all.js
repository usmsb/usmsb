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
  // Stage 7 now includes VIBOutputReward first (needed for EC constructor)
  // Then deploy EC with 6 params: (vibeToken, staking, ecosystem, governance, reserve, output)
  save('VIBOutputReward', deployed.VIBOutputReward); // Already deployed in Stage 5
  save('EmissionController', await freshDeploy('EmissionController', 'src/automation/EmissionController.sol:EmissionController', [vibeToken, deployed.VIBStaking, deployed.VIBEcosystemPool, deployed.VIBGovernance, deployed.VIBReserve, deployed.VIBOutputReward]));

  // ================================================================
  // Stage 8: Token Distribution (Whitepaper v1.2 - 2026-03-12)
  // ================================================================
  console.log('\n' + '='.repeat(60));
  console.log(' Stage 8: Token Distribution (Whitepaper v1.2)');
  console.log('='.repeat(60));

  // 白皮书 v1.2 分配方案:
  //   直接分配(37%): team 8% / early 4% / community 6% / liquidity 12% / airdrop 7%
  //   激励池(63%): 全部进入EmissionController，由其按周期释放到各子池
  //     EC内部分配: staking 40% / ecosystem 25% / governance 12% / reserve 10% / output 13%
  const pools = {
    emissionController:     deployed.EmissionController,  // 63% - 激励池
    outputRewardPool:      deployed.VIBOutputReward,    // 13% - 产出池(由EC管理)
    teamVesting:           deployed.VIBVesting,          // 8%
    earlySupporterVesting: deployed.VIBVesting,         // 4%
    communityFund:          deployed.CommunityStableFund, // 6%
    liquidityManager:       deployed.LiquidityManager,   // 12%
    airdropDistributor:    deployed.AirdropDistributor, // 7%
  };

  console.log('\n  Pool addresses:');
  for (const [k, v] of Object.entries(pools)) console.log(`    ${k.padEnd(24)}: ${v}`);

  const TOTAL_SUPPLY = ethers.parseUnits('1000000000', 18);
  const bps = 10000n;
  const amounts = {
    // 激励池 63% (进入EmissionController，由其按周期释放)
    emissionController:     TOTAL_SUPPLY * 6300n / bps,  // 6.3亿
    // 直接分配 37%
    outputRewardPool:       0n,  // 产出池由EC分配，不需要直接mint
    teamVesting:           TOTAL_SUPPLY * 800n / bps,   // 0.8亿
    earlySupporterVesting: TOTAL_SUPPLY * 400n / bps,   // 0.4亿
    communityFund:         TOTAL_SUPPLY * 600n / bps,   // 0.6亿
    liquidityManager:      TOTAL_SUPPLY * 1200n / bps,  // 1.2亿
    airdropDistributor:    TOTAL_SUPPLY * 700n / bps,  // 0.7亿
  };

  console.log('\n  Distribution (Whitepaper v1.3):');
  console.log('  --- 激励池 (63% = 6.3亿, 进入EmissionController) ---');
  console.log(`    emissionController:    ${ethers.formatUnits(amounts.emissionController, 18)} VIBE (由EC按周期释放)`);
  console.log('  --- 直接分配 (37% = 3.7亿) ---');
  console.log(`    teamVesting:          ${ethers.formatUnits(amounts.teamVesting, 18)} VIBE`);
  console.log(`    earlySupporterVesting:${ethers.formatUnits(amounts.earlySupporterVesting, 18)} VIBE`);
  console.log(`    communityFund:        ${ethers.formatUnits(amounts.communityFund, 18)} VIBE`);
  console.log(`    liquidityManager:    ${ethers.formatUnits(amounts.liquidityManager, 18)} VIBE`);
  console.log(`    airdropDistributor:   ${ethers.formatUnits(amounts.airdropDistributor, 18)} VIBE`);
  const directTotal = amounts.teamVesting + amounts.earlySupporterVesting + amounts.communityFund + amounts.liquidityManager + amounts.airdropDistributor;
  console.log(`    直接分配小计:         ${ethers.formatUnits(directTotal, 18)} VIBE`);
  const total = amounts.emissionController + directTotal;
  console.log(`    总计:                 ${ethers.formatUnits(total, 18)} VIBE`);
  console.log('\n  EC内部分配比例 (由EmissionController管理):');
  console.log('    stakingPool (40%):    2.52亿 → VIBStaking');
  console.log('    ecosystemPool (25%):  1.575亿 → VIBEcosystemPool');
  console.log('    governancePool (12%): 0.756亿 → VIBGovernance');
  console.log('    reservePool (10%):    0.63亿 → VIBReserve');
  console.log('    outputPool (13%):      0.819亿 → VIBOutputReward');

  // Call distributeToPools with fresh wallet
  const prov = new ethers.JsonRpcProvider(RPC_URL);
  const w = new ethers.Wallet(PRIVATE_KEY, prov);
  const vibetoken = await ethers.getContractFactory('VIBEToken', w);
  const tokenContract = vibetoken.attach(vibeToken);
  const nonce = parseInt(await prov.send('eth_getTransactionCount', [w.address, 'latest']), 16);
  console.log(`\n  Calling distributeToPools (nonce=${nonce})...`);
  const tx = await tokenContract.distributeToPools(
    pools.emissionController,    // 63%
    pools.outputRewardPool,      // 13%(由EC管理)
    pools.teamVesting,           // 8%
    pools.earlySupporterVesting, // 4%
    pools.communityFund,         // 6%
    pools.liquidityManager,      // 12%
    pools.airdropDistributor,    // 7%
    { nonce }
  );
  await tx.wait();
  console.log('  Tokens distributed!');
  await new Promise(r => setTimeout(r, 3000));

  // 注册EC所有子池为免税地址（重要：EC转账给子池时不能扣0.8%税）
  // EC 持有 6.3亿，每次向 5 个子池转账时都必须免税
  console.log('\n  Registering EC sub-pools as tax-exempt...');
  const tx2 = await tokenContract.registerECSubPools(
    deployed.VIBStaking,
    deployed.VIBEcosystemPool,
    deployed.VIBGovernance,
    deployed.VIBReserve,
    deployed.VIBOutputReward
  );
  await tx2.wait();
  console.log('  EC sub-pools registered as tax-exempt!');

  // Verify balances (only direct distribution pools, EC balance is checked separately)
  console.log('\n  Verifying direct distribution balances:');
  const directPools = {
    teamVesting: pools.teamVesting,
    earlySupporterVesting: pools.earlySupporterVesting,
    communityFund: pools.communityFund,
    liquidityManager: pools.liquidityManager,
    airdropDistributor: pools.airdropDistributor,
  };
  for (const [k, addr] of Object.entries(directPools)) {
    const bal = await tokenContract.balanceOf(addr);
    const exp = amounts[k];
    const ok = bal === exp ? '✓' : '✗';
    console.log(`  ${ok} ${k.padEnd(24)}: ${ethers.formatUnits(bal, 18)} VIBE`);
  }
  const ecBal = await tokenContract.balanceOf(pools.emissionController);
  const ecExp = amounts.emissionController;
  const ecOk = ecBal === ecExp ? '✓' : '✗';
  console.log(`  ${ecOk} emissionController:      ${ethers.formatUnits(ecBal, 18)} VIBE`);

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
