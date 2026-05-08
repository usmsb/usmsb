# Blockchain Query

## Metadata
- **Name**: blockchain_query
- **Description**: 查询区块链数据，包括钱包余额、交易记录、Gas 价格、网络状态等。当用户询问区块链相关问题或需要链上数据时使用。
- **Version**: 1.0.0
- **Author**: usmsb
- **Category**: blockchain

## Triggers
When should this skill be activated?
- 用户询问钱包余额
- 用户查询交易状态
- 用户需要当前的 Gas 价格
- 用户询问区块链网络状态
- 用户请求验证某个地址或交易

## Instructions

### 查询类型

1. **余额查询**: 查询指定钱包地址的 ETH 和代币余额
2. **交易查询**: 查询交易详情、状态、Hash
3. **Gas 价格**: 获取当前网络的建议 Gas 价格
4. **区块信息**: 查询区块高度、区块详情
5. **代币信息**: 查询 ERC-20 代币详情

### 执行流程

1. 确定查询类型（method）
2. 构建查询参数（params）
3. 调用区块链查询工具
4. 解析返回结果
5. 以用户友好的方式展示

## Parameters
- `method`: string - 查询方法
  - `get_balance`: 获取余额
  - `get_transaction`: 获取交易详情
  - `get_gas_price`: 获取 Gas 价格
  - `get_block_number`: 获取最新区块号
  - `get_token_balance`: 获取代币余额
- `params`: object - 查询参数（根据 method 不同而不同）

## Scripts
Available scripts in `scripts/`:
- `query_eth_price.py` - 获取 ETH 价格
- `estimate_gas.py` - 估算 Gas

## References
- `references/ethereum_rpc.md` - Ethereum RPC 接口文档
- `references/supported_networks.md` - 支持的网络列表
