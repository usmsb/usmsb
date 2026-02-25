const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deployer address:", deployer.address);

  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("Balance:", hre.ethers.formatEther(balance), "ETH");

  if (balance === 0n) {
    console.log("\n⚠️  Balance is 0! You need testnet ETH to deploy.");
    console.log("\nHow to get Base Sepolia ETH:");
    console.log("1. Coinbase Faucet: https://faucet.coinbase.com");
    console.log("2. Alchemy Faucet: https://www.alchemy.com/faucets/base-sepolia");
    console.log("3. QuickNode Faucet: https://faucet.quicknode.com/base/sepolia");
    console.log("4. Bridge from other networks: https://bridge.base.org");
  } else {
    console.log("\n✅ You have enough ETH to deploy!");
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
