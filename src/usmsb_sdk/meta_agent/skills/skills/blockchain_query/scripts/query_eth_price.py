#!/usr/bin/env python3
"""
获取 ETH 当前价格

输出: ETH/USD 价格
"""

import json
import urllib.request


def get_eth_price() -> dict:
    """获取 ETH 价格（使用 CoinGecko API）"""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            price = data.get("ethereum", {}).get("usd", 0)
            return {
                "price": price,
                "currency": "USD",
                "source": "CoinGecko",
            }
    except Exception as e:
        return {
            "error": str(e),
            "price": None,
        }


if __name__ == "__main__":
    result = get_eth_price()
    print(json.dumps(result, ensure_ascii=False, indent=2))
