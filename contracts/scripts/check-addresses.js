const hre = require("hardhat");

async function main() {
  // Try different known factory addresses
  const addresses = [
    "0x0000000000000000000000000000000000000000",  // ZeroAddress
    "0x5C69bEe701ef814a2B6fF3A05B3c5cDBf4D3D",   // Uniswap V2 on Ethereum mainnet
    "0x8BCacC969b0D1EA58F5a4C4Bd8CC1eDbE0D5a99e", // Another testnet factory
  ];

  for (const addr of addresses) {
    try {
      const checksum = hre.ethers.getAddress(addr);
      console.log(`Valid: ${checksum}`);
    } catch (e) {
      console.log(`Invalid: ${addr}`);
    }
  }
}

main().then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });
