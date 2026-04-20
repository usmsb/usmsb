const hre = require("hardhat");
const path = require("path");

async function main() {
  const emissionController = "0xaeD496480c9668dc90Dc309fCD8Fd9aE4268dF39";
  
  // Read the artifact directly
  const artifact = JSON.parse(
    require("fs").readFileSync(
      path.join(__dirname, "../artifacts/src/automation/EmissionController.sol/EmissionController.json"),
      "utf8"
    )
  );
  
  const [signer] = await hre.ethers.getSigners();
  
  // Create contract instance
  const contract = new hre.ethers.Contract(
    emissionController,
    artifact.abi,
    signer
  );
  
  // Read state
  const [totalReleased, startTime, lastEpochTime] = await Promise.all([
    contract.totalReleased(),
    contract.startTime(),
    contract.lastEpochTime()
  ]);
  
  const now = Math.floor(Date.now() / 1000);
  const epochsSinceStart = Math.floor((now - Number(startTime)) / (7 * 24 * 60 * 60));
  
  console.log("=== EmissionController State ===");
  console.log("Address:", emissionController);
  console.log("Total Released:", hre.ethers.formatUnits(totalReleased, 18), "VIBE");
  console.log("Start Time:", new Date(Number(startTime) * 1000).toISOString());
  console.log("Last Epoch Time:", new Date(Number(lastEpochTime) * 1000).toISOString());
  console.log("Now:", new Date(now * 1000).toISOString());
  console.log("Epochs since start (approx):", epochsSinceStart);
  console.log("");
  
  // Expected release per epoch
  const EMISSION_PER_EPOCH = hre.ethers.parseUnits("24246575", 18); // ~24.2M per epoch
  const expectedReleased = Number(EMISSION_PER_EPOCH) * epochsSinceStart;
  
  console.log("Expected released (approx):", hre.ethers.formatUnits(expectedReleased, 18), "VIBE");
  console.log("Actual released:", hre.ethers.formatUnits(totalReleased, 18), "VIBE");
  console.log("");
  
  if (totalReleased === 0n) {
    console.log("STATUS: No distribution has happened yet!");
    console.log("You can safely redeploy with corrected ratios.");
  } else {
    console.log("STATUS: Distribution has started!");
    console.log("Need to handle the migration of incorrectly distributed funds.");
  }
}

main().catch(console.error);
