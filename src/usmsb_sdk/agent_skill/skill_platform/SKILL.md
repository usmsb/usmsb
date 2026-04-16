# USMSB v2.0 Agent Skill Platform

## Overview

Agent Skill = 第三方 Agent 集成 L2/L3/L4 能力的方式

```
第三方 Agent
    ↓ 安装 Skill
SkillPlatform (L2Skill / L3Skill / L4Skill)
    ↓ 调用
L2/L3/L4 SDK（同一套代码）
    ↓
StrategyRouter（内部实现 vs SDK 智能切换）
```

## Architecture

```
skill_platform/
├── registry/              # Skill 注册中心
│   ├── skill_registry.py   # Skill 注册/发现
│   └── skill_store.py      # Skill 市场（发布/浏览）
├── loaders/               # Skill 加载器
│   ├── base_loader.py      # 基础加载器
│   ├── l2_skill_loader.py  # L2 Skill 加载
│   ├── l3_skill_loader.py  # L3 Skill 加载
│   └── l4_skill_loader.py  # L4 Skill 加载
├── marketplace/           # Skill 市场
│   ├── publish.py          # 发布 Skill
│   ├── search.py          # 搜索 Skill
│   └── rating.py          # Skill 评分
├── router/               # Skill 路由（集成 StrategyRouter）
│   └── skill_router.py    # Skill → SDK 路由
├── types.py               # Skill 类型定义
└── __init__.py
```

## Skill 标准格式

每个 Skill 是一个标准 Python 包：

```
skill_name/
├── SKILL.md              # Skill 描述（LLM 可读）
├── skill.yaml            # Skill 元信息
├── loader.py             # Skill 加载器
├── l2_impl.py           # L2 实现（可选）
├── l3_impl.py           # L3 实现（可选）
├── l4_impl.py           # L4 实现（可选）
└── tests/
```

## Skill 生命周期

1. **开发**: 开发者创建 Skill，定义 SKILL.md + loader.py
2. **发布**: 上传至 SkillStore，审核通过后上架
3. **安装**: Agent 调用 `SkillRegistry.install("skill_name")`
4. **调用**: Agent 通过 SkillLoader 调用 Skill
5. **路由**: SkillLoader → StrategyRouter → 内部实现 or SDK
6. **评估**: LLM 评估结果，质量记录入经验库
7. **进化**: 经验积累 → Skill 自动优化
