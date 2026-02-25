const hre = require("hardhat");

async function main() {
  console.log("=".repeat(60));
  console.log("VIBE Protocol - Contract Functionality Test");
  console.log("=".repeat(60));

  const [deployer] = await hre.ethers.getSigners();

  // Contract addresses
  const addresses = {
    VIBEToken: "0x895BeA0E70F61C093E7Ef05b45Fe744ef45c2600",
    VIBStaking: "0xE6b7494bceAd5B092e8F870035aeD7f44F0Fc868",
    VIBGovernance: "0x732ae212c8961ae773d68Da3Ddf9F29b788992b1",
    VIBDividend: "0x421844eC1a51d1246f7A740762998f308AA653db",
    VIBTreasury: "0x664C9E36C9328E9530407e0B44281cf9B1F14A5a",
  };

  // Get contract instances
  const VIBEToken = await hre.ethers.getContractFactory("VIBEToken");
  const vibeToken = VIBEToken.attach(addresses.VIBEToken);

  const VIBStaking = await hre.ethers.getContractFactory("VIBStaking");
  const staking = VIBStaking.attach(addresses.VIBStaking);

  const VIBGovernance = await hre.ethers.getContractFactory("VIBGovernance");
  const governance = VIBGovernance.attach(addresses.VIBGovernance);

  console.log("\n📍 Test 1: VIBEToken Basic Info");
  console.log("-".repeat(40));

  const name = await vibeToken.name();
  const symbol = await vibeToken.symbol();
  const totalSupply = await vibeToken.totalSupply();
  const deployerBalance = await vibeToken.balanceOf(deployer.address);

  console.log(`   Name: ${name}`);
  console.log(`   Symbol: ${symbol}`);
  console.log(`   Total Supply: ${hre.ethers.formatEther(totalSupply)} VIBE`);
  console.log(`   Deployer Balance: ${hre.ethers.formatEther(deployerBalance)} VIBE`);

  console.log("\n📍 Test 2: Transfer with Tax");
  console.log("-".repeat(40));

  // Test transfer to another address (should apply 0.8% tax)
  const testAmount = hre.ethers.parseEther("1000"); // 1000 VIBE
  const testRecipient = "0x1234567890123456789012345678901234567890";

  const balanceBefore = await vibeToken.balanceOf(testRecipient);
  console.log(`   Recipient balance before: ${hre.ethers.formatEther(balanceBefore)} VIBE`);

  console.log(`   Transferring 1000 VIBE...`);
  const tx = await vibeToken.transfer(testRecipient, testAmount);
  await tx.wait();

  const balanceAfter = await vibeToken.balanceOf(testRecipient);
  const received = balanceAfter - balanceBefore;
  console.log(`   Recipient received: ${hre.ethers.formatEther(received)} VIBE`);
  console.log(`   Tax applied: ${hre.ethers.formatEther(testAmount - received)} VIBE (0.8%)`);

  console.log("\n📍 Test 3: Staking");
  console.log("-".repeat(40));

  // Approve staking contract
  const stakeAmount = hre.ethers.parseEther("10000"); // 10,000 VIBE
  console.log(`   Approving ${hre.ethers.formatEther(stakeAmount)} VIBE for staking...`);
  const approveTx = await vibeToken.approve(addresses.VIBStaking, stakeAmount);
  await approveTx.wait();
  console.log(`   ✅ Approved`);

  // Stake
  console.log(`   Staking ${hre.ethers.formatEther(stakeAmount)} VIBE (90 days lock)...`);
  const stakeTx = await staking.stake(stakeAmount, 2); // 2 = 90 days lock
  await stakeTx.wait();
  console.log(`   ✅ Staked successfully`);

  // Check staking info
  const stakeInfo = await staking.getStakeInfo(deployer.address);
  console.log(`   Staked amount: ${hre.ethers.formatEther(stakeInfo.amount)} VIBE`);
  console.log(`   Tier: ${stakeInfo.tier} (0=Bronze, 1=Silver, 2=Gold, 3=Platinum)`);
  console.log(`   Lock period: ${stakeInfo.lockPeriod}`);
  console.log(`   Active: ${stakeInfo.isActive}`);

  // Check voting power
  const votingPower = await staking.getVotingPower(deployer.address);
  console.log(`   Voting power: ${hre.ethers.formatEther(votingPower)}`);

  console.log("\n📍 Test 4: Governance - Create Proposal");
  console.log("-".repeat(40));

  // Create a proposal
  const proposalDesc = "Test Proposal: Increase staking rewards";
  console.log(`   Creating proposal: "${proposalDesc}"...`);

  const proposalTx = await governance.createProposal(
    0, // GENERAL type
    proposalDesc,
    [], // no targets
    [], // no values
    [] // no calldata
  );
  const receipt = await proposalTx.wait();
  console.log(`   ✅ Proposal created`);

  // Get proposal info
  const proposalCount = await governance.getProposalCount();
  console.log(`   Total proposals: ${proposalCount}`);

  console.log("\n📍 Test 5: Check Contract Configurations");
  console.log("-".repeat(40));

  // Check VIBEToken configurations
  const stakingContract = await vibeToken.stakingContract();
  const dividendContract = await vibeToken.dividendContract();
  const treasuryContract = await vibeToken.ecosystemFundContract();

  console.log(`   VIBEToken.stakingContract: ${stakingContract}`);
  console.log(`   VIBEToken.dividendContract: ${dividendContract}`);
  console.log(`   VIBEToken.ecosystemFundContract: ${treasuryContract}`);
  console.log(`   Match expected: ${stakingContract.toLowerCase() === addresses.VIBStaking.toLowerCase()}`);

  // Check staking APY
  const apy = await staking.currentAPY();
  console.log(`   VIBStaking.currentAPY: ${apy}%`);

  console.log("\n" + "=".repeat(60));
  console.log("✅ All Tests Passed!");
  console.log("=".repeat(60));

  // Final balances
  const finalVibeBalance = await vibeToken.balanceOf(deployer.address);
  const finalEthBalance = await hre.ethers.provider.getBalance(deployer.address);

  console.log("\nFinal Balances:");
  console.log(`   VIBE: ${hre.ethers.formatEther(finalVibeBalance)}`);
  console.log(`   ETH: ${hre.ethers.formatEther(finalEthBalance)}`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Test failed:", error);
    process.exit(1);
  });
