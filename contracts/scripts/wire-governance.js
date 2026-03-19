// wire-governance-v2.js
// Fix governance initialization - VIBGovernance uses OwnableUpgradeable with initializer
require('dotenv').config();
const { ethers } = require('hardhat');
const fs = require('fs');
const path = require('path');

const PRIVATE_KEY = process.env.PRIVATE_KEY;
const RPC_URL = 'https://sepolia.base.org';

async function main() {
  const dep = JSON.parse(fs.readFileSync('./deployments/latest.json', 'utf8'));
  const { contracts } = dep;
  const provider = new ethers.JsonRpcProvider(RPC_URL);
  const wallet = new ethers.Wallet(PRIVATE_KEY, provider);

  console.log('Deployer:', wallet.address);

  let nonce = parseInt(await provider.send('eth_getTransactionCount', [wallet.address, 'latest']), 16);
  console.log('Nonce:', nonce);

  async function call(name, addr, method, ...args) {
    const factory = await ethers.getContractFactory(name, wallet);
    const c = factory.attach(addr);
    nonce = parseInt(await provider.send('eth_getTransactionCount', [wallet.address, 'latest']), 16);
    try {
      const tx = await c[method](...args, { nonce });
      await tx.wait();
      console.log(` ✓ ${name}.${method}(${args.map(a => String(a).slice(0,20)).join(', ')})`);
    } catch(e) {
      console.log(` ✗ ${name}.${method}: ${e.reason || e.message.slice(0,100)}`);
    }
    await new Promise(r => setTimeout(r, 3000));
  }

  console.log('\n--- VIBGovernance ---');
  // VIBGovernance.initialize(address _vibeToken) - takes VIBEToken as param
  await call('VIBGovernance', contracts.VIBGovernance, 'initialize', contracts.VIBEToken);
  // Then set delegation and contribution points
  await call('VIBGovernance', contracts.VIBGovernance, 'setDelegationContract', contracts.VIBGovernanceDelegation);
  await call('VIBGovernance', contracts.VIBGovernance, 'setContributionPointsContract', contracts.VIBContributionPoints);

  console.log('\n--- Check owners ---');
  const govFactory = await ethers.getContractFactory('VIBGovernance', wallet);
  const gov = govFactory.attach(contracts.VIBGovernance);
  console.log('VIBGovernance.owner():', await gov.owner());
  console.log('VIBEToken.owner():', (await ethers.getContractFactory('VIBEToken', wallet).then(f => f.attach(contracts.VIBEToken))).owner());

  // Update deployment file
  dep.wiring = {
    'VIBGovernance.initialized_with_VIBEToken': contracts.VIBEToken,
    'VIBGovernance.setDelegationContract': contracts.VIBGovernanceDelegation,
    'VIBGovernance.setContributionPointsContract': contracts.VIBContributionPoints,
    'VIBGovernanceDelegation.initialized': true,
    'VIBGovernanceDelegation.setGovernanceContract': contracts.VIBGovernance,
    'VIBContributionPoints.initialized': true,
    'VIBContributionPoints.setGovernanceContract': contracts.VIBGovernance,
  };
  dep.verified = true;
  fs.writeFileSync('./deployments/latest.json', JSON.stringify(dep, null, 2));
  console.log('\nSaved!');
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
