#!/usr/bin/env python3
"""
USMSB Testnet: VIBVesting 两阶段释放
Phase 1: emergencyWithdraw() 发起
Phase 2: 48小时后 confirmEmergencyWithdraw() 确认
"""
import subprocess, json, time, datetime
from Crypto.Hash import keccak
from eth_account import Account
from web3 import Web3

RPC = "https://sepolia.base.org"
PRIVATE_KEY = "0x39376a7f7adcdddace9f9e84d04b56fe26c42ed95242e5719dada734c968b072"
DEPLOYER = Web3.to_checksum_address("0x382B71e8b425CFAaD1B1C6D970481F440458Abf8")
VT = Web3.to_checksum_address("0x93C52dF000317e12F891474B46d8B05652430bDC")
TEAM_VESTING = Web3.to_checksum_address("0x4d3008550fc164ccf0e1C0C4f666E77FC14dE924")
EARLY_VESTING = Web3.to_checksum_address("0x4d3008550fc164ccf0e1C0C4f666E77FC14dE924")  # Same address in current config

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
    print("=" * 60)
    print("VIBVesting 两阶段释放")
    print("=" * 60)

    chain_id = int(rpc_raw("eth_chainId")["result"], 16)
    nonce = int(rpc_raw("eth_getTransactionCount", [DEPLOYER, "latest"])["result"], 16)
    gas_price = int(rpc_raw("eth_gasPrice")["result"], 16)
    print(f"\nChain: {chain_id}, Gas: {gas_price/1e9:.4f} Gwei, Nonce: {nonce}")

    # 检查各合约余额
    def contract_balance(addr):
        r = rpc_raw("eth_call", [{"to": VT, "data": f"0x70a08231000000000000000000000000{addr[2:].lower()}"}, "latest"])
        return int(r["result"], 16) if r.get("result") and r["result"] != "0x" else 0

    tv_bal = contract_balance(TEAM_VESTING)
    print(f"\nTeamVesting 余额: {tv_bal/1e18:.0f} VIBE")
    print(f"EarlyVesting 余额: {contract_balance(EARLY_VESTING)/1e18:.0f} VIBE")

    EW_SELECTOR = selector("emergencyWithdraw(address)")
    CONFIRM_SELECTOR = selector("confirmEmergencyWithdraw()")

    # ========== 阶段1: 发起 emergencyWithdraw ==========
    print(f"\n📤 [1/2] emergencyWithdraw(deployer)")
    print(f"    → TeamVesting")

    ew_data = EW_SELECTOR + DEPLOYER[2:].lower().rjust(64, "0")
    tx = sign_and_send(TEAM_VESTING, ew_data, 100000, nonce, chain_id, gas_price)
    if tx:
        print(f"    TX: {tx}")
        r = wait_receipt(tx)
        if r:
            status = int(r["status"], 16)
            gas_used = int(r["gasUsed"], 16)
            if status == 1:
                print(f"    ✅ 成功! gasUsed={gas_used}")
                print(f"\n⏰ 48小时后可执行 confirmEmergencyWithdraw()")
                print(f"   预计可执行时间: ~{datetime.datetime.now() + datetime.timedelta(hours=48):%Y-%m-%d %H:%M}")
                nonce += 1
            else:
                err = r.get("revertReason", "")
                print(f"    ❌ 失败: {err}")
                return
        else:
            print("    超时")
            return
    else:
        return

    # ========== 阶段2: 确认执行 ==========
    print(f"\n📤 [2/2] confirmEmergencyWithdraw()")
    print(f"    (48小时延迟后才能执行，以下代码仅作演示)")

    # 先检查是否到时间
    # 注：实际执行需要等48小时
    print(f"\n⚠️  confirmEmergencyWithdraw() 需要48小时延迟")
    print(f"   当前时间: {datetime.datetime.now():%Y-%m-%d %H:%M}")
    print(f"   提示: 48小时后再运行此脚本的第二阶段")

    # 注释掉以下代码，48小时后再取消注释执行
    # confirm_tx = sign_and_send(TEAM_VESTING, CONFIRM_SELECTOR, 100000, nonce, chain_id, gas_price)
    # if confirm_tx:
    #     print(f"    TX: {confirm_tx}")
    #     r2 = wait_receipt(confirm_tx)
    #     if r2:
    #         status2 = int(r2["status"], 16)
    #         print(f"    {'✅ 成功!' if status2 == 1 else '❌ 失败'}")

    print("\n" + "=" * 60)
    print("阶段1完成!  48小时后再执行confirm")
    print("=" * 60)

if __name__ == "__main__":
    main()
