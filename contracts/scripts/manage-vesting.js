const hre = require("hardhat");
const fs = require("fs");

// ========== 配置 ==========
const VESTING_ADDRESS = "0x3d476714B8B78488CEF6B795eF6A2C5167625BEf";
const TOKEN_ADDRESS = "0x91d8C3084b4fd21A04fA3584BFE357F378938dbc";

// ========== 工具函数 ==========
function formatAmount(amount) {
  return hre.ethers.formatEther(amount);
}

function printHeader(title) {
  console.log("\n" + "=".repeat(60));
  console.log(`  ${title}`);
  console.log("=".repeat(60));
}

// ========== 主函数 ==========
async function main() {
  const args = process.argv.slice(2);
  const command = args[0] || "status";

  // 配额
  const TEAM_QUOTA = hre.ethers.parseEther("80000000"); // 8000万
  const SUPPORTER_QUOTA = hre.ethers.parseEther("40000000"); // 4000万
  const TOTAL_QUOTA = TEAM_QUOTA + SUPPORTER_QUOTA;

  printHeader("VIBVesting 受益人管理工具");

  console.log(`\n合约地址: ${VESTING_ADDRESS}`);
  console.log(`网络: ${hre.network.name}`);

  // 连接合约
  const vesting = await hre.ethers.getContractAt("VIBVesting", VESTING_ADDRESS);
  const token = await hre.ethers.getContractAt("VIBEToken", TOKEN_ADDRESS);

  // 查询当前状态
  const contractBalance = await token.balanceOf(VESTING_ADDRESS);
  const beneficiaryCount = await vesting.beneficiaryCount();

  console.log(`合约余额: ${formatAmount(contractBalance)} VIBE`);
  console.log(`受益人数量: ${beneficiaryCount}`);

  if (command === "status") {
    await showStatus(vesting, TEAM_QUOTA, SUPPORTER_QUOTA, TOTAL_QUOTA);
  } else if (command === "list") {
    await listBeneficiaries(vesting);
  } else if (command === "export") {
    await exportData(vesting, token);
  } else if (command === "add" && args[1]) {
    console.log("\n用法: npx hardhat run manage-vesting.js add <address1,amount1,address2,amount2,...> --network baseSepolia");
    console.log("示例: npx hardhat run manage-vesting.js add 0x1234... 1000000 0x5678... 500000 --network baseSepolia");
    return;
  } else {
    console.log("\n用法:");
    console.log("  npx hardhat run manage-vesting.js status --network baseSepolia");
    console.log("  npx hardhat run manage-vesting.js list --network baseSepolia");
    console.log("  npx hardhat run manage-vesting.js export --network baseSepolia");
  }
}

// ========== 功能函数 ==========

async function showStatus(vesting, TEAM_QUOTA, SUPPORTER_QUOTA, TOTAL_QUOTA) {
  printHeader("分配状态");

  const beneficiaryCount = await vesting.beneficiaryCount();
  const token = await hre.ethers.getContractAt("VIBEToken", await vesting.vibeToken());
  const contractBalance = await token.balanceOf(VESTING_ADDRESS);

  // 统计各类型分配
  let teamAllocated = 0n;
  let supporterAllocated = 0n;

  for (let i = 0; i < Number(beneficiaryCount); i++) {
    const beneficiary = await vesting.beneficiaryList(i);
    const info = await vesting.beneficiaries(beneficiary);
    if (info.vestingType === 0) {
      supporterAllocated += info.totalAmount;
    } else {
      teamAllocated += info.totalAmount;
    }
  }

  const teamRemaining = TEAM_QUOTA - teamAllocated;
  const supporterRemaining = SUPPORTER_QUOTA - supporterAllocated;

  console.log("\n┌─────────────────┬─────────────┬─────────────┬───────────┐");
  console.log("│ 类型           │ 配额        │ 已分配      │ 剩余      │");
  console.log("├─────────────────┼─────────────┼─────────────┼───────────┤");
  console.log(`│ 团队 (TEAM)     │ ${formatAmount(TEAM_QUOTA).padEnd(12)} │ ${formatAmount(teamAllocated).padEnd(12)} │ ${formatAmount(teamRemaining).padEnd(9)} │`);
  console.log(`│ 早期支持者      │ ${formatAmount(SUPPORTER_QUOTA).padEnd(12)} │ ${formatAmount(supporterAllocated).padEnd(12)} │ ${formatAmount(supporterRemaining).padEnd(9)} │`);
  console.log("├─────────────────┼─────────────┼─────────────┼───────────┤");
  console.log(`│ 总计            │ ${formatAmount(TOTAL_QUOTA).padEnd(12)} │ ${formatAmount(teamAllocated + supporterAllocated).padEnd(12)} │ ${formatAmount(teamRemaining + supporterRemaining).padEnd(9)} │`);
  console.log("└─────────────────┴─────────────┴─────────────┴───────────┘");

  console.log("\n合约余额 vs 已分配:");
  console.log(`  合约余额: ${formatAmount(contractBalance)} VIBE`);
  console.log(`  已分配量: ${formatAmount(teamAllocated + supporterAllocated)} VIBE`);
  console.log(`  未分配量: ${formatAmount(contractBalance - teamAllocated - supporterAllocated)} VIBE`);

  // 检查配额使用情况
  if (teamAllocated > TEAM_QUOTA) {
    console.log("\n⚠️ 警告: 团队分配已超过配额!");
  }
  if (supporterAllocated > SUPPORTER_QUOTA) {
    console.log("\n⚠️ 警告: 早期支持者分配已超过配额!");
  }

  console.log("\n锁仓参数说明:");
  console.log("  团队 (TEAM): 4年锁仓, 1年悬崖期");
  console.log("  早期支持者 (EARLY_SUPPORTER): 2年锁仓, 6个月悬崖期");
}

async function listBeneficiaries(vesting) {
  printHeader("受益人列表");

  const beneficiaryCount = await vesting.beneficiaryCount();
  const tokenAddr = await vesting.vibeToken();
  const token = await hre.ethers.getContractAt("VIBEToken", tokenAddr);
  const contractBalance = await token.balanceOf(VESTING_ADDRESS);

  let teamCount = 0;
  let supporterCount = 0;
  let teamTotal = 0n;
  let supporterTotal = 0n;

  for (let i = 0; i < Number(beneficiaryCount); i++) {
    const beneficiary = await vesting.beneficiaryList(i);
    const info = await vesting.beneficiaries(beneficiary);

    if (info.vestingType === 0) {
      supporterCount++;
      supporterTotal += info.totalAmount;
    } else {
      teamCount++;
      teamTotal += info.totalAmount;
    }
  }

  console.log(`\n团队 (TEAM): ${teamCount} 人, 总计 ${formatAmount(teamTotal)} VIBE`);
  console.log(`早期支持者: ${supporterCount} 人, 总计 ${formatAmount(supporterTotal)} VIBE`);
  console.log(`\n受益人总数: ${teamCount + supporterCount}`);

  if (Number(beneficiaryCount) === 0) {
    console.log("\n暂无受益人");
    return;
  }

  console.log("\n详细列表:");
  console.log("┌──────┬────────────────────────────────────────────────┬──────────────┬────────────┬─────────┐");
  console.log("│ 序号 │ 地址                                       │ 总分配       │ 已释放    │ 状态    │");
  console.log("├──────┬────────────────────────────────────────────────┬──────────────┬────────────┬─────────┤");

  for (let i = 0; i < Number(beneficiaryCount); i++) {
    const beneficiary = await vesting.beneficiaryList(i);
    const info = await vesting.beneficiaries(beneficiary);
    const typeStr = info.vestingType === 0 ? "支持者" : "团队";

    console.log(`│ ${(i + 1).toString().padEnd(4)} │ ${beneficiary} │ ${formatAmount(info.totalAmount).padEnd(12)} │ ${formatAmount(info.releasedAmount).padEnd(10)} │ ${info.isActive ? "活跃" : "已移除"} │`);
  }

  console.log("└──────┴────────────────────────────────────────────────┴──────────────┴────────────┴─────────┘");
}

async function exportData(vesting, token) {
  printHeader("导出数据");

  const beneficiaryCount = await vesting.beneficiaryCount();
  const contractBalance = await token.balanceOf(VESTING_ADDRESS);

  const data = {
    exportTime: new Date().toISOString(),
    contract: {
      address: VESTING_ADDRESS,
      balance: contractBalance.toString(),
      beneficiaryCount: Number(beneficiaryCount)
    },
    beneficiaries: {
      team: [],
      supporter: []
    }
  };

  for (let i = 0; i < Number(beneficiaryCount); i++) {
    const beneficiary = await vesting.beneficiaryList(i);
    const info = await vesting.beneficiaries(beneficiary);

    const beneficiaryData = {
      address: beneficiary,
      totalAmount: info.totalAmount.toString(),
      releasedAmount: info.releasedAmount.toString(),
      vestingStart: info.vestingStart.toString(),
      vestingDuration: info.vestingDuration.toString(),
      cliffPeriod: info.cliffPeriod.toString(),
      isActive: info.isActive
    };

    if (info.vestingType === 0) {
      data.beneficiaries.supporter.push(beneficiaryData);
    } else {
      data.beneficiaries.team.push(beneficiaryData);
    }
  }

  const filename = `vesting-report-${Date.now()}.json`;
  fs.writeFileSync(filename, JSON.stringify(data, null, 2));
  console.log(`\n✅ 数据已导出到: ${filename}`);
  console.log(`  受益人总数: ${Number(beneficiaryCount)}`);
  console.log(`  团队成员: ${data.beneficiaries.team.length}`);
  console.log(`  早期支持者: ${data.beneficiaries.supporter.length}`);
}

main().then(() => process.exit(0)).catch(e => {
  console.error(e);
  process.exit(1);
});
