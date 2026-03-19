require('dotenv').config();
const { ethers } = require('hardhat');

async function main() {
  const provider = new ethers.JsonRpcProvider('https://sepolia.base.org');
  const wallet = new ethers.Wallet(process.env.PRIVATE_KEY, provider);
  
  let nonce = parseInt(await provider.send('eth_getTransactionCount', [wallet.address, 'latest']));
  console.log('Starting nonce:', nonce);

  const abi = [
    'function initialize() external',
    'function setGovernanceContract(address) external'
  ];

  const govAddr = '0x4624732022De6a3A53E25D10F726687Cb33Ca337';

  // VIBGovernanceDelegation
  {
    const addr = '0x8003c7e4459186F4bce9669e7b9BA7ED651C3a71';
    const c = new ethers.Contract(addr, abi, wallet);
    try {
      const tx = await c.initialize({ nonce, gasLimit: 100000 });
      await (await tx).wait();
      console.log('  Delegation initialize: ✅');
      nonce++;
    } catch(e) {
      console.log('  Delegation initialize:', e.message.slice(0,100));
    }
    try {
      const tx = await c.setGovernanceContract(govAddr, { nonce, gasLimit: 100000 });
      await (await tx).wait();
      console.log('  Delegation setGovernanceContract: ✅');
      nonce++;
    } catch(e) {
      console.log('  Delegation setGovernanceContract:', e.message.slice(0,100));
    }
  }

  // VIBContributionPoints
  {
    const addr = '0x2cbB07431aac73bDa29A65c755a0C9DAc25bBF1E';
    const c = new ethers.Contract(addr, abi, wallet);
    try {
      const tx = await c.initialize({ nonce, gasLimit: 100000 });
      await (await tx).wait();
      console.log('  ContributionPoints initialize: ✅');
      nonce++;
    } catch(e) {
      console.log('  ContributionPoints initialize:', e.message.slice(0,100));
    }
    try {
      const tx = await c.setGovernanceContract(govAddr, { nonce, gasLimit: 100000 });
      await (await tx).wait();
      console.log('  ContributionPoints setGovernanceContract: ✅');
      nonce++;
    } catch(e) {
      console.log('  ContributionPoints setGovernanceContract:', e.message.slice(0,100));
    }
  }

  // Governance -> Delegation
  {
    const govABI = [
      'function setDelegationContract(address) external',
      'function setContributionPointsContract(address) external'
    ];
    const gov = new ethers.Contract(govAddr, govABI, wallet);
    try {
      const tx = await gov.setDelegationContract('0x8003c7e4459186F4bce9669e7b9BA7ED651C3a71', { nonce, gasLimit: 100000 });
      await (await tx).wait();
      console.log('  Governance setDelegationContract: ✅');
      nonce++;
    } catch(e) {
      console.log('  Governance setDelegationContract:', e.message.slice(0,100));
    }
    try {
      const tx = await gov.setContributionPointsContract('0x2cbB07431aac73bDa29A65c755a0C9DAc25bBF1E', { nonce, gasLimit: 100000 });
      await (await tx).wait();
      console.log('  Governance setContributionPointsContract: ✅');
      nonce++;
    } catch(e) {
      console.log('  Governance setContributionPointsContract:', e.message.slice(0,100));
    }
  }

  console.log('\nDone!');
}

main().catch(e => { console.error(e.message); process.exit(1); });
