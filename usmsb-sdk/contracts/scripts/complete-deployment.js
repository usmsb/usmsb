const hre = require("hardhat");
const fs = require("fs");

async function main() {
  console.log("Completing deployment configuration...\n");

  const [deployer] = await hre.ethers.getSigners();
  console.log("Deployer:", deployer.address);

  // Already deployed contract addresses
  const deployedContracts = {
    VIBEToken: "0x895BeA0E70F61C093E7Ef05b45Fe744ef45c2600",
    VIBInflationControl: "0x82aA3F07B153DfFeCfb6464d0726c53dc2626464",
    VIBStaking: "0xE6b7494bceAd5B092e8F870035aeD7f44F0Fc868",
    VIBVesting: "0x4B898eBEA09b771e4EfD1Ea0986E2bF1f7734ACE",
    VIBIdentity: "0xFe1c819d193796B731A13da51a1D55E43C6521e3",
    VIBGovernance: "0x732ae212c8961ae773d68Da3Ddf9F29b788992b1",
    VIBTimelock: "0x8a9dc76bE021b6e36A43acB0088fcBe428FAdE3d",
    VIBDividend: "0x421844eC1a51d1246f7A740762998f308AA653db",
    VIBTreasury: "0x664C9E36C9328E9530407e0B44281cf9B1F14A5a",
    AgentRegistry: "0x2fc57E56e06A5cCC8c17fdE84eA768b76B51c644",
    AgentWallet: "0x99AF837f7A154b244e3E92BaC962a0064AA1F053",
    ZKCredential: "0x84cCAF1C87a88eB90f360112B2E87b49Ab216012",
    AssetVault: "0x0D7a7e8353984330cB566E8Bc8951ed1728c236A",
    JointOrder: "0x578Ad702F3df5F5863CD7172FEa65cca4D0E44cD"
  };

  // Get VIBEToken contract instance
  const VIBEToken = await hre.ethers.getContractFactory("VIBEToken");
  const vibeToken = VIBEToken.attach(deployedContracts.VIBEToken);

  // Check if treasury tokens are already minted
  const treasuryMinted = await vibeToken.treasuryMinted();
  console.log("Treasury minted:", treasuryMinted);

  if (!treasuryMinted) {
    console.log("\nMinting treasury tokens (92% of supply)...");
    const tx = await vibeToken.mintTreasury();
    await tx.wait();
    console.log("✅ Treasury tokens minted successfully!");
  } else {
    console.log("✅ Treasury tokens already minted");
  }

  // Get token info
  const totalSupply = await vibeToken.totalSupply();
  const deployerBalance = await vibeToken.balanceOf(deployer.address);

  console.log("\n" + "=".repeat(60));
  console.log("Deployment Complete!");
  console.log("=".repeat(60));

  console.log("\nNetwork:", hre.network.name);
  console.log("Chain ID:", (await hre.ethers.provider.getNetwork()).chainId.toString());

  console.log("\nDeployed Contracts:");
  for (const [name, address] of Object.entries(deployedContracts)) {
    console.log(`  ${name.padEnd(22)}: ${address}`);
  }

  console.log("\nToken Information:");
  console.log(`  Total Supply: ${hre.ethers.formatEther(totalSupply)} VIBE`);
  console.log(`  Deployer Balance: ${hre.ethers.formatEther(deployerBalance)} VIBE`);

  // Save deployment info
  const dir = "./deployments";
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }

  const deploymentInfo = {
    network: hre.network.name,
    chainId: (await hre.ethers.provider.getNetwork()).chainId.toString(),
    deployer: deployer.address,
    timestamp: new Date().toISOString(),
    contracts: deployedContracts,
    tokenInfo: {
      totalSupply: hre.ethers.formatEther(totalSupply),
      deployerBalance: hre.ethers.formatEther(deployerBalance)
    }
  };

  const deploymentPath = `${dir}/${hre.network.name}.json`;
  fs.writeFileSync(deploymentPath, JSON.stringify(deploymentInfo, null, 2));
  console.log(`\nDeployment info saved to: ${deploymentPath}`);

  console.log("\n" + "=".repeat(60));
  console.log("View on Block Explorer:");
  console.log("=".repeat(60));
  console.log(`https://sepolia.basescan.org/address/${deployedContracts.VIBEToken}#code`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
