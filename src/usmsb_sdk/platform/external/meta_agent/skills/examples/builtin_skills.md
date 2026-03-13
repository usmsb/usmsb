# Skill: platform_health_check

## Description
检查平台整体健康状态，包括节点、Agent、网络等

## Parameters
- target: 检查目标 (system/node/agent/all)

## Returns
返回健康状态报告

## Example
```json
{
  "target": "all"
}
```

## LLM Usage
当用户说"检查平台健康"、"系统状态怎么样"时使用此技能

---

# Skill: agent_recommendation

## Description
根据用户需求推荐合适的 Agent

## Parameters
- requirements: 用户需求描述
- category: 需求类别
- budget: 预算范围

## Example
```json
{
  "requirements": "需要Python开发服务",
  "category": "development",
  "budget": "1000-5000"
}
```

## LLM Usage
当用户说"推荐一个Agent"、"谁能帮我做XXX"时使用此技能

---

# Skill: blockchain_operation

## Description
执行区块链操作，如质押、投票等

## Parameters
- operation: 操作类型 (stake/unstake/vote)
- amount: 数量
- chain: 区块链网络

## Example
```json
{
  "operation": "stake",
  "amount": 1000,
  "chain": "ethereum"
}
```

## LLM Usage
当用户说"我要质押"、"帮我投票"时使用此技能
