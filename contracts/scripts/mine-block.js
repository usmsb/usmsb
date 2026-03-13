const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();

  // Get current nonce
  const nonce = await hre.ethers.provider.getTransactionCount(deployer.address);
  console.log("Current nonce:", nonce);

  // Try to mine a block to clear pending transactions
  try {
    await hre.network.provider.request({
      method: "evm_mine",
      params: [],
    });
    console.log("Block mined");

    // Check nonce again
    const newNonce = await hre.ethers.provider.getTransactionCount(deployer.address);
    console.log("New nonce:", newNonce);
  } catch (e) {
    console.log("Error:", e.message);
  }
}

main().then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });
