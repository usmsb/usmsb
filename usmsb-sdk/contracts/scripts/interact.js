const hre = require("hardhat");
const fs = require("fs");

async function main() {
  const network = hre.network.name;
  console.log(`Interacting with contracts on ${network}\n`);

  // Read deployment info
  const deploymentFile = `deployments/${network}.json`;
  if (!fs.existsSync(deploymentFile)) {
    console.error(`Deployment file not found: ${deploymentFile}`);
    console.error("Please deploy the contracts first");
    process.exit(1);
  }

  const deploymentInfo = JSON.parse(fs.readFileSync(deploymentFile, "utf8"));
  const contracts = deploymentInfo.contracts;

  // Get signers
  const [owner, addr1] = await hre.ethers.getSigners();
  console.log("Using account:", owner.address);

  // Get contract instances
  const VIBEToken = await hre.ethers.getContractFactory("VIBEToken");
  const vibeToken = VIBEToken.attach(contracts.VIBEToken);

  const VIBStaking = await hre.ethers.getContractFactory("VIBStaking");
  const vibStaking = VIBStaking.attach(contracts.VIBStaking);

  const VIBVesting = await hre.ethers.getContractFactory("VIBVesting");
  const vibVesting = VIBVesting.attach(contracts.VIBVesting);

  const VIBIdentity = await hre.ethers.getContractFactory("VIBIdentity");
  const vibIdentity = VIBIdentity.attach(contracts.VIBIdentity);

  // Example interactions
  console.log("\n========== Contract Information ==========");

  console.log("\n--- VIBEToken ---");
  console.log("Name:", await vibeToken.name());
  console.log("Symbol:", await vibeToken.symbol());
  console.log("Total Supply:", hre.ethers.formatEther(await vibeToken.totalSupply()), "VIBE");
  console.log("Your Balance:", hre.ethers.formatEther(await vibeToken.balanceOf(owner.address)), "VIBE");
  console.log("Treasury:", await vibeToken.treasury());
  console.log("Owner:", await vibeToken.owner());

  console.log("\n--- VIBStaking ---");
  console.log("Current APY:", await vibStaking.currentAPY(), "%");
  console.log("Total Staked:", hre.ethers.formatEther(await vibStaking.totalStaked()), "VIBE");
  console.log("Staker Count:", await vibStaking.getStakerCount());

  console.log("\n--- VIBVesting ---");
  console.log("Beneficiary Count:", await vibStaking.getBeneficiaryCount());
  console.log("Total Released:", hre.ethers.formatEther(await vibStaking.totalReleased()), "VIBE");

  console.log("\n--- VIBIdentity ---");
  console.log("Identity Count:", await vibIdentity.identityCount());
  console.log("Your Registered:", await vibIdentity.isRegistered(owner.address));

  console.log("\n========== Interaction Complete ==========");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
