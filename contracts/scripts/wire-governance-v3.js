// scripts/wire-governance-v3.js
// Fix VIBGovernance wiring: setDelegationContract + setContributionPointsContract
require('dotenv').config();
const { ethers } = require('hardhat');

const PRIVATE_KEY = process.env.PRIVATE_KEY;
const RPC_URL = 'https://sepolia.base.org';

const ADDR = {
  VIBEToken:    '0x93C52dF000317e12F891474B46d8B05652430bDC',
  VIBGovernance: '0x27475aea1eEba485005B1717a35a7D411d144a1d',
  VIBGovernanceDelegation:   '0x47428bAB428966B32F246a3e9456f10dc70141A5',
  VIBContributionPoints:     '0x60D9244bF262bF85Fd3057C95Ca00fEa1622f3E5',
};

async function main() {
  const provider = new ethers.JsonRpcProvider(RPC_URL);
  const wallet = new ethers.Wallet(PRIVATE_KEY, provider);
  console.log('Wallet:', wallet.address);

  // Check current owner of VIBGovernance
  const gov = await ethers.getContractFactory('VIBGovernance', wallet).then(f => f.attach(ADDR.VIBGovernance));
  const owner = await gov.owner();
  console.log('VIBGovernance owner:', owner);
  console.log('Is deployer owner?', owner.toLowerCase() === wallet.address.toLowerCase() ? 'YES ✓' : 'NO ✗');

  if (owner.toLowerCase() !== wallet.address.toLowerCase()) {
    console.error('ERROR: Not the owner! Cannot call these functions.');
    process.exit(1);
  }

  let nonce = parseInt(await provider.send('eth_getTransactionCount', [wallet.address, 'latest']), 16);

  // setDelegationContract(VIBGovernanceDelegation)
  console.log(`\nCalling setDelegationContract(${ADDR.VIBGovernanceDelegation})...`);
  try {
    const tx1 = await gov.setDelegationContract(ADDR.VIBGovernanceDelegation, { nonce });
    await tx1.wait();
    console.log(' ✓ setDelegationContract succeeded');
  } catch(e) {
    console.log(' ✗ setDelegationContract failed:', e.reason || e.message.slice(0, 100));
  }
  nonce++;
  await new Promise(r => setTimeout(r, 3000));

  // setContributionPointsContract(VIBContributionPoints)
  console.log(`\nCalling setContributionPointsContract(${ADDR.VIBContributionPoints})...`);
  try {
    const tx2 = await gov.setContributionPointsContract(ADDR.VIBContributionPoints, { nonce });
    await tx2.wait();
    console.log(' ✓ setContributionPointsContract succeeded');
  } catch(e) {
    console.log(' ✗ setContributionPointsContract failed:', e.reason || e.message.slice(0, 100));
  }

  // Verify
  console.log('\n--- Verification ---');
  try {
    const delAddr = await gov.delegationContract();
    const cpAddr = await gov.contributionPointsContract();
    console.log('delegationContract():', delAddr, delAddr === ADDR.VIBGovernanceDelegation ? '✓' : '✗');
    console.log('contributionPointsContract():', cpAddr, cpAddr === ADDR.VIBContributionPoints ? '✓' : '✗');
  } catch(e) {
    console.log('Verification read failed:', e.message.slice(0, 80));
  }

  console.log('\nDone');
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
