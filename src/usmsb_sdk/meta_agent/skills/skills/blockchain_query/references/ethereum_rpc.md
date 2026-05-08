# Ethereum RPC 接口文档

## 常用 RPC 方法

### eth_getBalance
查询钱包余额

```json
{
  "method": "eth_getBalance",
  "params": ["0x742d35Cc6634C0532925a3b844Bc9e7595f0cB2", "latest"],
  "id": 1
}
```

### eth_getTransactionByHash
根据 Hash 查询交易

```json
{
  "method": "eth_getTransactionByHash",
  "params": ["0xabc123..."],
  "id": 1
}
```

### eth_gasPrice
获取当前 Gas 价格

```json
{
  "method": "eth_gasPrice",
  "params": [],
  "id": 1
}
```

### eth_blockNumber
获取最新区块号

```json
{
  "method": "eth_blockNumber",
  "params": [],
  "id": 1
}
```

## 网络端点

| 网络 | RPC URL |
|------|---------|
| Mainnet | https://eth.llamarpc.com |
| Sepolia (测试网) | https://rpc.sepolia.org |
