const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();

  // Get current nonce
  const nonce = await hre.ethers.provider.getTransactionCount(deployer.address);
  console.log("Current nonce:", nonce);

  // Set nonce to the expected value (191 based on error)
  try {
    await hre.network.provider.request({
      method: "hardhat_setNonce",
      params: [deployer.address, "0xbf"], // 191 in hex
    });
    console.log("Nonce reset to 191");
  } catch (e) {
    console.log("Error setting nonce:", e.message);
  }
}

main().then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });
