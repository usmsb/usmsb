const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();

  // Get current nonce
  const nonce = await hre.ethers.provider.getTransactionCount(deployer.address);
  console.log("Current nonce:", nonce);

  // Send a simple transaction to bump the nonce
  // Send 0 ETH to self to increment nonce
  const tx = {
    to: deployer.address,
    value: 0,
    nonce: nonce,
    gasLimit: 21000,
  };

  try {
    const sentTx = await deployer.sendTransaction(tx);
    console.log("Sent bump tx:", sentTx.hash);
    await sentTx.wait();
    console.log("Bump tx confirmed");

    // Check new nonce
    const newNonce = await hre.ethers.provider.getTransactionCount(deployer.address);
    console.log("New nonce:", newNonce);
  } catch (e) {
    console.log("Error:", e.message);
  }
}

main().then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });
