# Skill System

> Dynamic Skill Extension Mechanism

**[English](#english-section) | [中文](#chinese-section)**

---

## English Section

## 1. Overview

The Skill System allows Agents to dynamically load and extend capabilities without modifying core code.

---

## 2. Module Structure

```
core/skills/
├── __init__.py
├── skill_system.py      # Skill system core
├── git_skill.py        # Git skill
└── npm_skill.py        # NPM skill
```

---

## 3. Usage

### 3.1 Define a Skill

```python
from usmsb_sdk.core.skills import Skill

class GitSkill(Skill):
    name = "git"
    description = "Git version control"

    async def execute(self, action: str, **kwargs):
        if action == "commit":
            return await self.git_commit(kwargs.get("message"))
        elif action == "push":
            return await self.git_push()
```

### 3.2 Register a Skill

```python
from usmsb_sdk.core.skills import SkillRegistry

registry = SkillRegistry()
registry.register(GitSkill())
```

---

## 4. Implementation Status

| Function | Status |
|----------|--------|
| Skill System Core | ✅ |
| Git Skill | ✅ |
| NPM Skill | ✅ |
| Dynamic Loading | ✅ |

---

## 5. Related Documentation

- [Meta Agent Design](./meta_agent_design.md) - Super Agent System Design

---

<details>
<summary><h2>中文翻译</h2></summary>

# 技能系统

> 动态技能扩展机制

---

## 1. 概述

技能系统（Skill System）允许 Agent 动态加载和扩展能力，无需修改核心代码。

---

## 2. 模块结构

```
core/skills/
├── __init__.py
├── skill_system.py      # 技能系统核心
├── git_skill.py        # Git 技能
└── npm_skill.py        # NPM 技能
```

---

## 3. 使用方法

### 3.1 定义技能

```python
from usmsb_sdk.core.skills import Skill

class GitSkill(Skill):
    name = "git"
    description = "Git 版本控制"

    async def execute(self, action: str, **kwargs):
        if action == "commit":
            return await self.git_commit(kwargs.get("message"))
        elif action == "push":
            return await self.git_push()
```

### 3.2 注册技能

```python
from usmsb_sdk.core.skills import SkillRegistry

registry = SkillRegistry()
registry.register(GitSkill())
```

---

## 4. 实现状态

| 功能 | 状态 |
|------|------|
| 技能系统核心 | ✅ |
| Git 技能 | ✅ |
| NPM 技能 | ✅ |
| 动态加载 | ✅ |

---

## 5. 相关文档

- [Meta Agent设计](./meta_agent_design.md) - 超级Agent系统设计

</details>
