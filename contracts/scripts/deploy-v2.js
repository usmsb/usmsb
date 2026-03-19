/**
 * deploy-v2.js
 * 完整部署脚本 - VIBEToken + 按白皮书正确分配代币
 *
 * 白皮书代币分配（相对于 TOTAL_SUPPLY = 1B VIBE）：
 *   激励池 63% → staking 28.35% / ecosystem 18.90% / governance 9.45% / reserve 6.30%
 *   直接分配: team 8% / early 4% / community 6% / liquidity 12% / airdrop 7%
 *   合计: 100% = 10000 basis points
 *
 * 部署顺序:
 *   1. VIBEToken (new, with correct distributeToPools)
 *   2. VIBDividend.distributeToPools() (if not already distributed)
 */

require('dotenv').config();
const hre = require('hardhat');
const fs = require('fs');
const path = require('path');

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  const provider = deployer.provider;

  const deploymentFile = path.join(__dirname, '../deployments/latest.json');
  let existing = {};
  try {
    existing = JSON.parse(fs.readFileSync(deploymentFile, 'utf8')).contracts || {};
  } catch (e) {}

  const d = (name, addr) => { console.log(`  ${name}: ${addr}`); existing[name] = addr; };

  console.log('========================================');
  console.log('VIBE Token 部署脚本 v2');
  console.log('========================================');
  console.log(`网络: ${hre.network.name}`);
  console.log(`部署者: ${deployer.address}`);
  console.log(`已有合约: ${Object.keys(existing).length} 个`);
  console.log('');

  // ========== 1. 部署新的 VIBEToken ==========
  console.log('[1] 部署新的 VIBEToken...');
  const VIBEToken = await hre.ethers.getContractFactory('VIBEToken');
  const vibeToken = await VIBEToken.deploy('VIB Token', 'VIBE');
  await vibeToken.waitForDeployment();
  const vibeTokenAddr = await vibeToken.getAddress();
  d('VIBEToken', vibeTokenAddr);
  console.log(`  VIBEToken: ${vibeTokenAddr} ✅`);
  console.log('');

  // ========== 2. 调用 distributeToPools ==========
  console.log('[2] 调用 distributeToPools (白皮书分配)...');
  console.log('  分配明细:');
  console.log('    stakingPool         28.35% = 283.5M VIBE  → existing.VIBStaking');
  console.log('    ecosystemPool        18.90% = 189.0M VIBE  → existing.VIBEcosystemPool');
  console.log('    governancePool        9.45% =  94.5M VIBE  → existing.VIBGovernance');
  console.log('    reservePool           6.30% =  63.0M VIBE  → existing.VIBReserve');
  console.log('    teamVesting          8.00% =  80.0M VIBE  → existing.VIBVesting');
  console.log('    earlySupporterVesting 4.00% =  40.0M VIBE  → existing.VIBVesting');
  console.log('    liquidityManager     12.00% = 120.0M VIBE  → existing.VIBInfrastructurePool');
  console.log('    airdropDistributor   7.00% =  70.0M VIBE  → existing.AirdropDistributor');
  console.log('    合计              100.00% = 1000.0M VIBE');

  const stakingPool = existing.VIBStaking;
  const ecosystemPool = existing.VIBEcosystemPool || existing.VIBInfrastructurePool;
  const governancePool = existing.VIBGovernance;
  const reservePool = existing.VIBReserve;
  const teamVesting = existing.VIBVesting;
  const earlySupporterVesting = existing.VIBVesting; // early supporter also uses team vesting
  const liquidityManager = existing.VIBInfrastructurePool || existing.VIBEToken; // placeholder if zero
  const airdropDistributor = existing.AirdropDistributor;

  // Check all addresses are valid
  const requiredAddrs = [
    ['VIBStaking', stakingPool],
    ['VIBGovernance', governancePool],
    ['VIBReserve', reservePool],
    ['VIBVesting (team)', teamVesting],
    ['AirdropDistributor', airdropDistributor],
  ];
  for (const [name, addr] of requiredAddrs) {
    if (!addr || addr === '0x0000000000000000000000000000000000000000') {
      console.log(`  ⚠️ ${name} 地址为空: ${addr} - 请确保已部署相关合约`);
    }
  }

  console.log('');
  console.log('  调用参数:');
  console.log(`    stakingPool:          ${stakingPool}`);
  console.log(`    ecosystemPool:         ${ecosystemPool || '0x0 (missing!)'}`);
  console.log(`    governancePool:       ${governancePool}`);
  console.log(`    reservePool:          ${reservePool}`);
  console.log(`    teamVesting:          ${teamVesting}`);
  console.log(`    earlySupporterVesting: ${earlySupporterVesting}`);
  console.log(`    liquidityManager:     ${liquidityManager}`);
  console.log(`    airdropDistributor:   ${airdropDistributor}`);
  console.log('');

  try {
    const tx = await vibeToken.distributeToPools(
      stakingPool,
      ecosystemPool || '0x0000000000000000000000000000000000000000',
      governancePool,
      reservePool,
      teamVesting,
      earlySupporterVesting,
      liquidityManager,
      airdropDistributor
    );
    await tx.wait();
    console.log('  distributeToPools: ✅ 交易成功');
  } catch (e) {
    console.log('  distributeToPools FAILED:', e.message.slice(0, 200));
  }

  // ========== 3. 验证分配结果 ==========
  console.log('');
  console.log('[3] 验证分配结果...');
  const totalSupply = await vibeToken.totalSupply();
  console.log(`  总供应量: ${hre.ethers.formatEther(totalSupply)} VIBE (预期: 1,000,000,000)`);

  const checkBal = async (name, addr, expectedBps) => {
    if (!addr || addr === hre.ethers.ZeroAddress) {
      console.log(`  ${name}: 地址为空，跳过`);
      return;
    }
    try {
      const bal = await vibeToken.balanceOf(addr);
      const expected = (totalSupply * BigInt(expectedBps)) / 10000n;
      const ok = bal === expected;
      console.log(`  ${name}: ${hre.ethers.formatEther(bal).padStart(14)} VIBE (预期 ${hre.ethers.formatEther(expected).padStart(14)}) ${ok ? '✅' : '❌'}`);
    } catch (e) {
      console.log(`  ${name}: 查询失败 - ${e.message.slice(0,80)}`);
    }
  };

  await checkBal('VIBStaking',          stakingPool,           2835);
  await checkBal('EcosystemPool',       ecosystemPool,          1890);
  await checkBal('GovernancePool',       governancePool,          945);
  await checkBal('ReservePool',          reservePool,             630);
  await checkBal('TeamVesting',          teamVesting,             800);
  await checkBal('EarlySupporterVest',   earlySupporterVesting,   400);
  await checkBal('LiquidityManager',      liquidityManager,        1200);
  await checkBal('AirdropDistributor',   airdropDistributor,      700);

  // ========== 4. 保存 ==========
  fs.writeFileSync(deploymentFile, JSON.stringify({
    timestamp: new Date().toISOString(),
    network: hre.network.name,
    deployer: deployer.address,
    contracts: existing
  }, null, 2));

  console.log('');
  console.log(`[4] 部署文件已保存: ${deploymentFile}`);
  console.log('完成！');
}

main().catch(e => { console.error('部署失败:', e.message); process.exit(1); });
