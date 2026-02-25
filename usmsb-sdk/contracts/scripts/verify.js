const hre = require("hardhat");
const fs = require("fs");

async function main() {
  const network = hre.network.name;
  console.log(`Verifying contracts on ${network}...\n`);

  // Read deployment info
  const deploymentFile = `deployments/${network}.json`;
  if (!fs.existsSync(deploymentFile)) {
    console.error(`Deployment file not found: ${deploymentFile}`);
    console.error("Please deploy the contracts first using 'npm run deploy'");
    process.exit(1);
  }

  const deploymentInfo = JSON.parse(fs.readFileSync(deploymentFile, "utf8"));
  const contracts = deploymentInfo.contracts;

  // Verify VIBEToken
  console.log("1. Verifying VIBEToken...");
  try {
    await hre.run("verify:verify", {
      address: contracts.VIBEToken,
      constructorArguments: ["VIBE Token", "VIBE", deploymentInfo.deployer],
    });
    console.log("   VIBEToken verified successfully!");
  } catch (error) {
    console.log("   VIBEToken verification failed:", error.message);
  }

  // Verify VIBStaking
  console.log("\n2. Verifying VIBStaking...");
  try {
    await hre.run("verify:verify", {
      address: contracts.VIBStaking,
      constructorArguments: [contracts.VIBEToken],
    });
    console.log("   VIBStaking verified successfully!");
  } catch (error) {
    console.log("   VIBStaking verification failed:", error.message);
  }

  // Verify VIBVesting
  console.log("\n3. Verifying VIBVesting...");
  try {
    await hre.run("verify:verify", {
      address: contracts.VIBVesting,
      constructorArguments: [contracts.VIBEToken],
    });
    console.log("   VIBVesting verified successfully!");
  } catch (error) {
    console.log("   VIBVesting verification failed:", error.message);
  }

  // Verify VIBIdentity
  console.log("\n4. Verifying VIBIdentity...");
  try {
    await hre.run("verify:verify", {
      address: contracts.VIBIdentity,
      constructorArguments: ["VIBE Identity SBT", "VIBID", contracts.VIBEToken],
    });
    console.log("   VIBIdentity verified successfully!");
  } catch (error) {
    console.log("   VIBIdentity verification failed:", error.message);
  }

  console.log("\n========== Verification Complete ==========");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
