require('dotenv').config();
const { ethers } = require('hardhat');
const fs = require('fs');

async function main() {
  const provider = new ethers.JsonRpcProvider('https://sepolia.base.org');
  const wallet = new ethers.Wallet(process.env.PRIVATE_KEY, provider);
  const d = JSON.parse(fs.readFileSync('./deployments/latest.json', 'utf8')).contracts;

  console.log('Deployer:', wallet.address);
  console.log('');

  // Deploy VIBEcosystemPool if missing
  if (!d.VIBEcosystemPool) {
    console.log('[1] Deploying VIBEcosystemPool...');
    const factory = await ethers.getContractFactory('VIBEcosystemPool');
    const txResp = await factory.connect(wallet).deploy(d.VIBEToken, wallet.address);
    const receipt = await txResp.deploymentTransaction().wait();
    if (receipt.status !== 1) throw new Error('VIBEcosystemPool deployment failed');
    d.VIBEcosystemPool = receipt.contractAddress;
    console.log('  VIBEcosystemPool:', d.VIBEcosystemPool, '✅');
  }

  // Call distributeToPools (6 params)
  // distributeToPools(teamVesting, earlySupporterVesting, communityStableFund, liquidityManager, airdropDistributor, emissionController)
  // Percentages: 8% + 4% + 6% + 12% + 7% + 63% = 100%
  // - earlySupporterVesting: not deployed → use VIBVesting as placeholder
  // - liquidityManager: zero on BaseSepolia → use VIBInfrastructurePool as placeholder
  console.log('\n[2] Calling VIBEToken.distributeToPools()...');
  const tokenAbi = ['function distributeToPools(address,address,address,address,address,address) external'];
  const token = new ethers.Contract(d.VIBEToken, tokenAbi, wallet);

  // Check if already distributed
  const tokenState = new ethers.Contract(d.VIBEToken, [
    'function tokensDistributed() external view returns (bool)',
    'function totalSupply() external view returns (uint256)'
  ], provider);

  if (await tokenState.tokensDistributed()) {
    const supply = await tokenState.totalSupply();
    console.log('  tokensDistributed already true, total supply:', ethers.formatEther(supply), 'VIBE');
  } else {
    const tx = await token.distributeToPools(
      d.VIBVesting,             // teamVestingContract 8%
      d.VIBVesting,             // earlySupporterVesting 4% (placeholder - same vesting)
      d.VIBEcosystemPool,      // communityStableFund 6%
      d.VIBInfrastructurePool,  // liquidityManager 12% (placeholder)
      d.AirdropDistributor,     // airdropDistributor 7%
      d.EmissionController      // emissionController 63%
    );
    const r = await tx.wait();
    console.log('  distributeToPools:', r.status === 1 ? '✅' : '❌', 'tx:', r.hash);
    const supply = await tokenState.totalSupply();
    console.log('  Total supply:', ethers.formatEther(supply), 'VIBE');
  }

  // Save
  fs.writeFileSync('./deployments/latest.json', JSON.stringify({
    ...JSON.parse(fs.readFileSync('./deployments/latest.json', 'utf8')),
    contracts: d
  }, null, 2));
  console.log('\nDone!');
}

main().catch(e => console.error('FAILED:', e.message));
