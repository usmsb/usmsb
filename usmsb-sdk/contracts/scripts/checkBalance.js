const hre = require("hardhat");

async function main() {
  const balance = await hre.ethers.provider.getBalance("0x382B71e8b425CFAaD1B1C6D970481F440458Abf8");
  console.log("Balance:", hre.ethers.formatEther(balance), "ETH");
}

main();
