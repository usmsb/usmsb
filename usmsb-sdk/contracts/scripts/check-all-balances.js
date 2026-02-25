const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Wallet:", deployer.address);
  console.log("=".repeat(50));

  // Check Sepolia
  console.log("\n📍 Ethereum Sepolia:");
  try {
    const provider = new hre.ethers.JsonRpcProvider("https://rpc.sepolia.org");
    const balance = await provider.getBalance(deployer.address);
    console.log("   Balance:", hre.ethers.formatEther(balance), "ETH");
  } catch (e) {
    console.log("   Error:", e.message);
  }

  // Check Base Sepolia
  console.log("\n📍 Base Sepolia:");
  try {
    const provider = new hre.ethers.JsonRpcProvider("https://sepolia.base.org");
    const balance = await provider.getBalance(deployer.address);
    console.log("   Balance:", hre.ethers.formatEther(balance), "ETH");
  } catch (e) {
    console.log("   Error:", e.message);
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
