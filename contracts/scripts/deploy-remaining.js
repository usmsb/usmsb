require('dotenv').config();
const hre = require('hardhat');
const fs = require('fs');
const path = require('path');

async function main() {
  const provider = new hre.ethers.JsonRpcProvider('https://sepolia.base.org');
  const wallet = new hre.ethers.Wallet(process.env.PRIVATE_KEY, provider);
  
  let nonce = parseInt(await provider.send('eth_getTransactionCount', [wallet.address, 'latest']));
  console.log('Starting nonce:', nonce);
  
  const deployed = {};
  const deploymentFile = path.join(__dirname, '../deployments/latest.json');
  const existing = JSON.parse(fs.readFileSync(deploymentFile, 'utf8')).contracts || {};
  // Add newly deployed contracts (from previous session) to existing
  const newlyDeployed = {
    ZKCredential: '0xD23a416d02B9963eB69df59db1A21218e11b03CE',
    JointOrder: '0xa80A9A7bda3E9aEff55A2d4E1da1362B1E901EeD',
    VIBGovernance: '0x4624732022De6a3A53E25D10F726687Cb33Ca337',
    VIBOutputReward: '0xE949976295A2Af52a7A8017FbBf2F2b7dcD80dE6',
    AirdropDistributor: '0x8967Dff66E79BD1548bCEB34307ef8EF37eBf30c',
    VIBGovernanceDelegation: '0x8003c7e4459186F4bce9669e7b9BA7ED651C3a71',
    VIBContributionPoints: '0x2cbB07431aac73bDa29A65c755a0C9DAc25bBF1E',
    VIBVEPoints: '0x6803A33fccE80CC590904e8Bd478F152ef688e0C',
    VIBDispute: '0x3a61228c22C3360D39866e7a288f185e838b6779',
    AgentWallet: '0x27E8a52c53a2ab16e78B8FF99aaEDB59c19F9409',
  };
  for (const [k, v] of Object.entries(newlyDeployed)) existing[k] = v;
  console.log('Loaded', Object.keys(existing).length, 'existing deployments');
  console.log('Deployer:', wallet.address);
  console.log('');

  const addDeployed = (name, addr) => {
    deployed[name] = addr;
    console.log(`  ${name}: ${addr}`);
  };

  const deploy = async (name, ...args) => {
    const idx = Object.keys(existing).length + Object.keys(deployed).length + 1;
    console.log(`[${idx}] ${name}... (nonce=${nonce})`);
    const factory = await hre.ethers.getContractFactory(name);
    const contract = await factory.connect(wallet).deploy(...args, { nonce, gasLimit: 12000000 });
    const receipt = await contract.deploymentTransaction().wait();
    if (receipt.status === 0) throw new Error(`${name} deployment failed: ${receipt.hash}`);
    addDeployed(name, receipt.contractAddress);
    nonce++;
  };

  const send = async (name, populatedTx) => {
    console.log(`  Wiring: ${name}... (nonce=${nonce})`);
    populatedTx.nonce = nonce;
    populatedTx.gasLimit = 500000;
    const tx = await wallet.sendTransaction(populatedTx);
    const receipt = await tx.wait();
    nonce++;
  };

  // [24] EmissionController
  {
    console.log(`[24] EmissionController... (nonce=${nonce})`);
    const factory = await hre.ethers.getContractFactory('src/automation/EmissionController.sol:EmissionController');
    const contract = await factory.connect(wallet).deploy(
      existing.VIBEToken, existing.VIBStaking, existing.VIBInfrastructurePool,
      existing.VIBGovernance, existing.VIBReserve,
      { nonce, gasLimit: 12000000 }
    );
    const receipt = await contract.deploymentTransaction().wait();
    if (receipt.status === 0) throw new Error('EmissionController deployment failed');
    addDeployed('EmissionController', receipt.contractAddress);
    nonce++;
  }

  // Wire governance
  console.log('\n--- Wiring governance ---');

  const delegation = await hre.ethers.getContractAt('VIBGovernanceDelegation', existing.VIBGovernanceDelegation);
  await send('Delegation.setGovernanceContract',
    await delegation.setGovernanceContract.populateTransaction(existing.VIBGovernance));
  console.log('  ✅ Delegation -> Governance');

  const cp = await hre.ethers.getContractAt('VIBContributionPoints', existing.VIBContributionPoints);
  await send('ContributionPoints.setGovernanceContract',
    await cp.setGovernanceContract.populateTransaction(existing.VIBGovernance));
  console.log('  ✅ ContributionPoints -> Governance');

  const gov = await hre.ethers.getContractAt('VIBGovernance', existing.VIBGovernance);
  await send('Governance.setDelegationContract',
    await gov.setDelegationContract.populateTransaction(existing.VIBGovernanceDelegation));
  await send('Governance.setContributionPointsContract',
    await gov.setContributionPointsContract.populateTransaction(existing.VIBContributionPoints));
  console.log('  ✅ Governance wired');

  const allContracts = { ...existing, ...deployed };
  fs.writeFileSync(deploymentFile, JSON.stringify({
    timestamp: new Date().toISOString(),
    network: hre.network.name,
    contracts: allContracts
  }, null, 2));
  console.log('\nSaved', Object.keys(allContracts).length, 'contracts');
  console.log('Done!');
}

main().catch(e => { console.error('FAILED:', e.message); process.exit(1); });
