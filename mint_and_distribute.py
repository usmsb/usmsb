#!/usr/bin/env python3
"""
USMSB Testnet: 初始化 + Mint & 分发 VIBE 完整脚本
"""
import subprocess, json, time
from Crypto.Hash import keccak
from eth_account import Account
from web3 import Web3

RPC = "https://sepolia.base.org"
PRIVATE_KEY = "0x39376a7f7adcdddace9f9e84d04b56fe26c42ed95242e5719dada734c968b072"
DEPLOYER = Web3.to_checksum_address("0x382B71e8b425CFAaD1B1C6D970481F440458Abf8")
VT = Web3.to_checksum_address("0x93C52dF000317e12F891474B46d8B05652430bDC")
VS = Web3.to_checksum_address("0x1901Ab56eA38cBeFc7a3F0Ed188B7108d27f4c05")

def selector(sig):
    k = keccak.new(digest_bits=256)
    k.update(sig.encode())
    return "0x" + k.hexdigest()[:8]

def rpc_raw(method, params=None):
    payload = {"jsonrpc": "2.0", "method": method, "params": params or [], "id": 1}
    r = subprocess.run(
        ["curl", "-s", "-X", "POST", RPC,
         "-H", "Content-Type: application/json",
         "-d", json.dumps(payload), "--max-time", "15"],
        capture_output=True, text=True, timeout=20
    )
    try:
        return json.loads(r.stdout)
    except:
        return {}

def wait_receipt(tx_hash, timeout=120):
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(2)
        r = rpc_raw("eth_getTransactionReceipt", [tx_hash])
        if "result" in r and r["result"] is not None:
            return r["result"]
        print(f"    等待确认... {int(time.time()-start)}s")
    return None

def sign_and_send(to_addr, data, gas_limit, nonce, chain_id, gas_price):
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
    result = rpc_raw("eth_sendRawTransaction", [raw_hex])
    if "result" in result:
        return result["result"]
    print(f"    Error: {result}")
    return None

def main():
    # 测试用户: (名字, 地址, 金额VIBE)
    TEST_USERS = [
        ("古军 (你)",     DEPLOYER,                        1_000_000),
        ("测试用户A",     Web3.to_checksum_address("0xAb5801a7D398351b8bE11C439e05C5B3259aeC9b"), 500_000),
        ("测试用户B",     Web3.to_checksum_address("0x28C6c06298d514Db089934071355E5743bf21d60"), 500_000),
        ("水龙头备用",    Web3.to_checksum_address("0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199"), 2_000_000),
    ]

    print("=" * 60)
    print("USMSB Testnet: Mint & 分发 VIBE")
    print("=" * 60)

    chain_id = int(rpc_raw("eth_chainId")["result"], 16)
    nonce = int(rpc_raw("eth_getTransactionCount", [DEPLOYER, "latest"])["result"], 16)
    gas_price = int(rpc_raw("eth_gasPrice")["result"], 16)
    print(f"\nChain: {chain_id}, Gas: {gas_price/1e9:.4f} Gwei, Nonce: {nonce}")

    # ========== 步骤1: setVibeToken(VIBEToken) on VIBStaking ==========
    print("\n📤 [1/6] VIBStaking.setVibeToken(VIBEToken)")
    data = selector("setVibeToken(address)") + VT[2:].lower().rjust(64, "0")
    tx = sign_and_send(VS, data, 100000, nonce, chain_id, gas_price)
    if tx:
        print(f"    TX: {tx}")
        r = wait_receipt(tx)
        if r:
            status = int(r["status"], 16)
            print(f"    {'✅ 成功' if status == 1 else '❌ 失败'} (gas={int(r['gasUsed'],16)})")
            if status == 1:
                nonce += 1
            else:
                print(f"    revertReason: {r.get('revertReason', 'N/A')}")
                return
        else:
            print("    超时")
            return
    else:
        return
    time.sleep(2)

    # ========== 步骤2: setStakingContract(VIBStaking) on VIBEToken ==========
    print("\n📤 [2/6] VIBEToken.setStakingContract(VIBStaking)")
    data2 = selector("setStakingContract(address)") + VS[2:].lower().rjust(64, "0")
    tx2 = sign_and_send(VT, data2, 100000, nonce, chain_id, gas_price)
    if tx2:
        print(f"    TX: {tx2}")
        r2 = wait_receipt(tx2)
        if r2:
            status2 = int(r2["status"], 16)
            print(f"    {'✅ 成功' if status2 == 1 else '❌ 失败'} (gas={int(r2['gasUsed'],16)})")
            if status2 == 1:
                nonce += 1
            else:
                print(f"    revertReason: {r2.get('revertReason', 'N/A')}")
                return
        else:
            print("    超时")
            return
    else:
        return
    time.sleep(2)

    # ========== 步骤3: mintReward(deployer, 500万 VIBE) ==========
    print("\n📤 [3/6] VIBEToken.mintReward(deployer, 5,000,000 VIBE)")
    TOTAL_MINT = 5_000_000 * 1e18
    mint_data = selector("mintReward(address,uint256)")
    mint_data += DEPLOYER[2:].lower().rjust(64, "0")
    mint_data += hex(int(TOTAL_MINT))[2:].rjust(64, "0")
    tx3 = sign_and_send(VT, mint_data, 200000, nonce, chain_id, gas_price)
    if tx3:
        print(f"    TX: {tx3}")
        r3 = wait_receipt(tx3)
        if r3:
            status3 = int(r3["status"], 16)
            print(f"    {'✅ 成功' if status3 == 1 else '❌ 失败'} (gas={int(r3['gasUsed'],16)})")
            if status3 == 1:
                nonce += 1
            else:
                print(f"    revertReason: {r3.get('revertReason', 'N/A')}")
                return
        else:
            print("    超时")
            return
    else:
        return
    time.sleep(2)

    # ========== 步骤4-7: 分发给各测试用户 ==========
    print("\n📤 [4-7/6] 分发 VIBE 给测试用户")
    transfer_sel = selector("transfer(address,uint256)")

    for name, addr, amount in TEST_USERS:
        xfer_data = transfer_sel + addr[2:].lower().rjust(64, "0")
        xfer_data += hex(int(amount * 1e18))[2:].rjust(64, "0")
        print(f"\n    → {name}: {amount:,} VIBE")
        tx4 = sign_and_send(VT, xfer_data, 100000, nonce, chain_id, gas_price)
        if tx4:
            print(f"      TX: {tx4}")
            r4 = wait_receipt(tx4)
            if r4:
                status4 = int(r4["status"], 16)
                print(f"      {'✅ 成功' if status4 == 1 else '❌ 失败'} (gas={int(r4['gasUsed'],16)})")
                if status4 == 1:
                    nonce += 1
                    time.sleep(1)
                else:
                    print(f"      revertReason: {r4.get('revertReason', 'N/A')}")
        else:
            print(f"      发送失败")

    time.sleep(3)

    # ========== 验证 ==========
    print("\n📊 验证结果")
    print("-" * 40)

    def balance(addr):
        r = rpc_raw("eth_call", [{"to": VT, "data": f"0x70a08231000000000000000000000000{addr[2:].lower()}"}, "latest"])
        return int(r["result"], 16) if r.get("result") and r["result"] != "0x" else 0

    total_supply = rpc_raw("eth_call", [{"to": VT, "data": selector("totalSupply()")}, "latest"])
    if total_supply.get("result"):
        print(f"✅ totalSupply: {int(total_supply['result'], 16)/1e18:.0f} VIBE")

    for name, addr, amount in TEST_USERS:
        bal = balance(addr)
        status = "✅" if bal >= amount * 0.99 else "⚠️"
        print(f"  {status} {name:20s}: {bal/1e18:>10,.0f} VIBE")

    print("\n" + "=" * 60)
    print("✅ 全部完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()
