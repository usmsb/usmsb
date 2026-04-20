#!/usr/bin/env python3
"""
USMSB Testnet: 使用 AirdropDistributor.ownerClaim() 分发 VIBE
ownerClaim(address to, uint256 amount) - 无 Merkle Proof，owner 直接领取
"""
import subprocess, json, time
from Crypto.Hash import keccak
from eth_account import Account
from web3 import Web3

RPC = "https://sepolia.base.org"
PRIVATE_KEY = "0x39376a7f7adcdddace9f9e84d04b56fe26c42ed95242e5719dada734c968b072"
DEPLOYER = Web3.to_checksum_address("0x382B71e8b425CFAaD1B1C6D970481F440458Abf8")
AD = Web3.to_checksum_address("0x01cdC2C7C3Deb071e6C7B42ED66884DDd3CADDf6")
VT = Web3.to_checksum_address("0x93C52dF000317e12F891474B46d8B05652430bDC")

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
    # 测试用户列表 (名字, 地址, 金额VIBE)
    TEST_USERS = [
        ("古军 (你)",           DEPLOYER,                        1_000_000),
        ("测试用户A",           Web3.to_checksum_address("0xAb5801a7D398351b8bE11C439e05C5B3259aeC9b"), 500_000),
        ("测试用户B",           Web3.to_checksum_address("0x28C6c06298d514Db089934071355E5743bf21d60"), 500_000),
        ("水龙头备用",           Web3.to_checksum_address("0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199"), 2_000_000),
        ("测试矿工1",           Web3.to_checksum_address("0x22d491Bde2303f2f43325b2108D26f1eAbA1e32b"), 1_000_000),
        ("测试矿工2",           Web3.to_checksum_address("0xE11BA2b5354aA8bCD9be7c2340C2EF9B60CAb6C2"), 1_000_000),
    ]

    OWNER_CLAIM_SELECTOR = selector("ownerClaim(address,uint256)")

    print("=" * 60)
    print("AirdropDistributor.ownerClaim() 分发 VIBE")
    print("=" * 60)

    # 检查 AD 余额
    bal = rpc_raw("eth_call", [{"to": VT, "data": f"0x70a08231000000000000000000000000{AD[2:].lower()}"}, "latest"])
    ad_balance = int(bal["result"], 16) if bal.get("result") and bal["result"] != "0x" else 0
    print(f"\nAirdropDistributor VIBE 余额: {ad_balance/1e18:.0f} VIBE")
    print(f"计划分发总量: {sum(u[2] for u in TEST_USERS)/1e18:.0f} VIBE")

    chain_id = int(rpc_raw("eth_chainId")["result"], 16)
    nonce = int(rpc_raw("eth_getTransactionCount", [DEPLOYER, "latest"])["result"], 16)
    gas_price = int(rpc_raw("eth_gasPrice")["result"], 16)
    print(f"\nChain: {chain_id}, Gas: {gas_price/1e9:.4f} Gwei, Nonce: {nonce}")

    # 先测试一笔小额的
    print(f"\n🧪 先测试一笔小的 (1 VIBE)...")
    test_data = OWNER_CLAIM_SELECTOR + DEPLOYER[2:].lower().rjust(64, "0")
    test_data += hex(int(1e18))[2:].rjust(64, "0")  # 1 VIBE
    test_tx = sign_and_send(AD, test_data, 150000, nonce, chain_id, gas_price)
    if test_tx:
        print(f"    Test TX: {test_tx}")
        r = wait_receipt(test_tx)
        if r:
            status = int(r["status"], 16)
            print(f"    {'✅ 测试成功!' if status == 1 else '❌ 测试失败: ' + str(r.get('revertReason', 'N/A'))}")
            if status == 1:
                nonce += 1
                time.sleep(3)
                # 验证余额变化
                new_bal = rpc_raw("eth_call", [{"to": VT, "data": f"0x70a08231000000000000000000000000{DEPLOYER[2:].lower()}"}, "latest"])
                print(f"    Deployer 余额: {int(new_bal['result'],16)/1e18:.6f} VIBE")
            else:
                print(f"    revertReason: {r.get('revertReason', 'N/A')}")
                return
        else:
            print("    超时")
            return

    time.sleep(2)

    # 分发正式金额
    print(f"\n📤 开始分发...")
    for name, addr, amount in TEST_USERS:
        xfer_data = OWNER_CLAIM_SELECTOR + addr[2:].lower().rjust(64, "0")
        xfer_data += hex(int(amount * 1e18))[2:].rjust(64, "0")
        print(f"\n    → {name}: {amount:,} VIBE")
        tx = sign_and_send(AD, xfer_data, 150000, nonce, chain_id, gas_price)
        if tx:
            print(f"      TX: {tx}")
            r = wait_receipt(tx)
            if r:
                status = int(r["status"], 16)
                print(f"      {'✅ 成功' if status == 1 else '❌ 失败'}")
                if status == 1:
                    nonce += 1
                    time.sleep(1)
                else:
                    err = r.get("revertReason", r.get("error", ""))
                    print(f"      错误: {err}")
        else:
            print(f"      发送失败")

    # 最终验证
    time.sleep(3)
    print("\n📊 最终验证")
    print("-" * 40)
    def balance(addr):
        r = rpc_raw("eth_call", [{"to": VT, "data": f"0x70a08231000000000000000000000000{addr[2:].lower()}"}, "latest"])
        return int(r["result"], 16) if r.get("result") and r["result"] != "0x" else 0

    for name, addr, amount in TEST_USERS:
        bal = balance(addr)
        status = "✅" if bal >= amount * 0.99 else "⚠️"
        print(f"  {status} {name:20s}: {bal/1e18:>10,.0f} VIBE")

    print("\n" + "=" * 60)
    print("✅ 全部完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()
