#!/usr/bin/env python3
"""
USMSB Testnet 初始化脚本 - 执行 distributeToPools 和 startAirdrop
使用正确的函数 selector 和参数编码
"""
import subprocess, json, time, datetime
from Crypto.Hash import keccak
from eth_account import Account
from web3 import Web3

RPC = "https://sepolia.base.org"
PRIVATE_KEY = "0x39376a7f7adcdddace9f9e84d04b56fe26c42ed95242e5719dada734c968b072"
DEPLOYER = Web3.to_checksum_address("0x382B71e8b425CFAaD1B1C6D970481F440458Abf8")

# 合约地址 (checksummed)
VT = Web3.to_checksum_address("0x93C52dF000317e12F891474B46d8B05652430bDC")
AD = Web3.to_checksum_address("0x01cdC2C7C3Deb071e6C7B42ED66884DDd3CADDf6")

# Pool 地址
POOLS = {
    "stakingPool":           Web3.to_checksum_address("0x1901Ab56eA38cBeFc7a3F0Ed188B7108d27f4c05"),
    "ecosystemPool":         Web3.to_checksum_address("0x20A25378DB87a94E19A8b51ED638F67d6e9BfE06"),
    "governancePool":        Web3.to_checksum_address("0x27475aea1eEba485005B1717a35a7D411d144a1d"),
    "reservePool":           Web3.to_checksum_address("0x56AbAf5fc5d58c92C0A51F79251BF3A3002f4263"),
    "teamVesting":           Web3.to_checksum_address("0x4d3008550fc164ccf0e1C0C4f666E77FC14dE924"),
    "earlySupporterVesting": Web3.to_checksum_address("0x4d3008550fc164ccf0e1C0C4f666E77FC14dE924"),
    "communityFund":         Web3.to_checksum_address("0x6e616E6B1d63709dA849074bb7cd5A6936350563"),
    "liquidityManager":      Web3.to_checksum_address("0x5c11b7f74bBb2dbBE232C6A456eCa64DA4722D42"),
    "airdropDistributor":    AD,
}

# 函数 selectors (keccak256 hash of function signature, first 4 bytes)
def selector(sig):
    k = keccak.new(digest_bits=256)
    k.update(sig.encode())
    return "0x" + k.hexdigest()[:8]

DISTRIBUTE_SELECTOR = selector("distributeToPools(address,address,address,address,address,address,address,address,address)")
STAIRDROP_SELECTOR = selector("startAirdrop()")

print(f"distributeToPools selector: {DISTRIBUTE_SELECTOR}")
print(f"startAirdrop selector: {STAIRDROP_SELECTOR}")

# 构建 distributeToPools 的 calldata
ordered_addrs = [
    POOLS["stakingPool"],
    POOLS["ecosystemPool"],
    POOLS["governancePool"],
    POOLS["reservePool"],
    POOLS["teamVesting"],
    POOLS["earlySupporterVesting"],
    POOLS["communityFund"],
    POOLS["liquidityManager"],
    POOLS["airdropDistributor"],
]

distribute_data = DISTRIBUTE_SELECTOR.replace("0x", "")
for addr in ordered_addrs:
    addr_hex = addr.replace("0x", "").lower().rjust(64, "0")
    distribute_data += addr_hex
DISTRIBUTE_CALDATA = "0x" + distribute_data

print(f"\ndistributeToPools calldata length: {len(DISTRIBUTE_CALDATA)} chars (should be 4 + 9*64 = 580)")
AIRDROP_CALDATA = STAIRDROP_SELECTOR  # no parameters

def rpc(method, params=None):
    payload = {"jsonrpc": "2.0", "method": method, "params": params or [], "id": 1}
    r = subprocess.run(
        ["curl", "-s", "-X", "POST", RPC,
         "-H", "Content-Type: application/json",
         "-d", json.dumps(payload), "--max-time", "30"],
        capture_output=True, text=True, timeout=35
    )
    try:
        return json.loads(r.stdout)
    except:
        return {}

def sign_and_send(to_addr, data, gas_limit, nonce, chain_id, gas_price):
    """签名并发送交易"""
    tx_dict = {
        "nonce": nonce,
        "gasPrice": gas_price,
        "gas": gas_limit,
        "to": to_addr,
        "value": 0,
        "data": data,
        "chainId": chain_id,
    }
    signed = Account.sign_transaction(tx_dict, PRIVATE_KEY)
    raw_hex = signed.raw_transaction.hex()
    if not raw_hex.startswith("0x"):
        raw_hex = "0x" + raw_hex
    result = rpc("eth_sendRawTransaction", [raw_hex])
    if "result" in result:
        return result["result"]
    else:
        print(f"    Error: {result}")
        return None

def wait_receipt(tx_hash, timeout=120):
    """等待交易确认"""
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(2)
        r = rpc("eth_getTransactionReceipt", [tx_hash])
        if "result" in r and r["result"] is not None:
            return r["result"]
        print(f"    等待确认... {int(time.time()-start)}s")
    return None

def main():
    print("=" * 60)
    print("USMSB Testnet 初始化")
    print(f"Deployer: {DEPLOYER}")
    print("=" * 60)

    # 获取链上状态
    chain_id_result = rpc("eth_chainId")
    nonce_result = rpc("eth_getTransactionCount", [DEPLOYER, "latest"])
    gas_price_result = rpc("eth_gasPrice")
    
    if "result" not in chain_id_result or "result" not in nonce_result or "result" not in gas_price_result:
        print(f"RPC error: chainId={chain_id_result}, nonce={nonce_result}, gasPrice={gas_price_result}")
        return
    
    chain_id = int(chain_id_result["result"], 16)
    nonce = int(nonce_result["result"], 16)
    gas_price = int(gas_price_result["result"], 16)
    print(f"\nChain ID: {chain_id} (Base Sepolia = 84532)")
    print(f"Gas Price: {gas_price / 1e9:.4f} Gwei")
    print(f"Current Nonce: {nonce}")

    # ========== 步骤1: 检查当前状态 ==========
    print("\n📊 检查当前状态")
    print("-" * 40)

    # 检查 tokensDistributed
    tokens_dist_result = rpc("eth_call", [{"to": VT, "data": selector("tokensDistributed()")}, "latest"])
    tokens_dist = int(tokens_dist_result.get("result", "0x0"), 16) if tokens_dist_result.get("result") else None
    if tokens_dist == 1:
        print(f"❌ VIBEToken.distributeToPools 已执行")
        pools_done = True
    else:
        print(f"✅ VIBEToken.distributeToPools 未执行，将执行")
        pools_done = False

    # 检查 Airdrop startTime
    start_time_result = rpc("eth_call", [{"to": AD, "data": selector("startTime()")}, "latest"])
    start_time = int(start_time_result.get("result", "0x0"), 16) if start_time_result.get("result") else None
    if start_time and start_time != 0:
        dt = datetime.datetime.fromtimestamp(start_time)
        print(f"❌ AirdropDistributor.startAirdrop 已启动 (startTime={dt})")
        airdrop_done = True
    else:
        print(f"✅ AirdropDistributor.startAirdrop 未启动，将执行")
        airdrop_done = False

    # 检查 totalSupply
    supply_result = rpc("eth_call", [{"to": VT, "data": selector("totalSupply()")}, "latest"])
    if supply_result.get("result") and supply_result["result"] != "0x":
        supply = int(supply_result["result"], 16)
        print(f"  current totalSupply: {supply/1e18:.0f} VIBE")
    else:
        print(f"  current totalSupply: 0 VIBE")

    # ========== 步骤2: 执行交易 ==========
    if not pools_done:
        print(f"\n📤 执行 [1/2] VIBEToken.distributeToPools()")
        print(f"   to: {VT}")
        print(f"   data: {DISTRIBUTE_CALDATA[:80]}...")
        
        tx_hash = sign_and_send(VT, DISTRIBUTE_CALDATA, 800000, nonce, chain_id, gas_price)
        if tx_hash:
            print(f"   TX: {tx_hash}")
            receipt = wait_receipt(tx_hash)
            if receipt:
                status = int(receipt["status"], 16)
                gas_used = int(receipt["gasUsed"], 16)
                if status == 1:
                    print(f"   ✅ 成功! gasUsed={gas_used}")
                else:
                    print(f"   ❌ 失败! status={status}")
                    # 打印revert reason if available
                    revert_reason = receipt.get("revertReason", "N/A")
                    print(f"   revertReason: {revert_reason}")
            nonce += 1
        time.sleep(3)
    else:
        print("\n⏭️ 跳过 distributeToPools (已执行)")

    if not airdrop_done:
        print(f"\n📤 执行 [2/2] AirdropDistributor.startAirdrop()")
        print(f"   to: {AD}")
        print(f"   data: {AIRDROP_CALDATA}")
        
        tx_hash2 = sign_and_send(AD, AIRDROP_CALDATA, 100000, nonce, chain_id, gas_price)
        if tx_hash2:
            print(f"   TX: {tx_hash2}")
            receipt2 = wait_receipt(tx_hash2)
            if receipt2:
                status2 = int(receipt2["status"], 16)
                gas_used2 = int(receipt2["gasUsed"], 16)
                if status2 == 1:
                    print(f"   ✅ 成功! gasUsed={gas_used2}")
                else:
                    print(f"   ❌ 失败! status={status2}")
    else:
        print("\n⏭️ 跳过 startAirdrop (已启动)")

    # ========== 步骤3: 验证 ==========
    time.sleep(3)
    print("\n📊 验证结果")
    print("-" * 40)

    supply_result = rpc("eth_call", [{"to": VT, "data": selector("totalSupply()")}, "latest"])
    if supply_result.get("result") and supply_result["result"] != "0x":
        supply = int(supply_result["result"], 16)
        print(f"✅ VIBEToken totalSupply: {supply/1e18:.0f} VIBE")

    # 各池余额
    for name, addr in POOLS.items():
        bal_result = rpc("eth_call", [{"to": VT, "data": f"0x70a08231000000000000000000000000{addr[2:].lower()}"}, "latest"])
        if bal_result.get("result") and bal_result["result"] != "0x":
            bal = int(bal_result["result"], 16)
            print(f"  {name}: {bal/1e18:.0f} VIBE")

    start_time_result2 = rpc("eth_call", [{"to": AD, "data": selector("startTime()")}, "latest"])
    if start_time_result2.get("result") and start_time_result2["result"] != "0x":
        ts = int(start_time_result2["result"], 16)
        if ts > 0:
            dt = datetime.datetime.fromtimestamp(ts)
            print(f"✅ Airdrop startTime: {dt}")

    print("\n" + "=" * 60)
    print("初始化完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()
