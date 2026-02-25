const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();

  const vibeToken = await hre.ethers.getContractAt(
    "VIBEToken",
    "0x895BeA0E70F61C093E7Ef05b45Fe744ef45c2600"
  );

  console.log("VIBEToken Configuration Check");
  console.log("-".repeat(40));

  const taxEnabled = await vibeToken.transactionTaxEnabled();
  const isExempt = await vibeToken.taxExemptedAddresses(deployer.address);
  const stakingContract = await vibeToken.stakingContract();
  const treasuryMinted = await vibeToken.treasuryMinted();

  console.log("Transaction tax enabled:", taxEnabled);
  console.log("Deployer is tax exempt:", isExempt);
  console.log("Treasury minted:", treasuryMinted);
  console.log("Staking contract:", stakingContract);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
