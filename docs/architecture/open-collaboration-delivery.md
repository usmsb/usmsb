# 开放协作内核整改：交付证据与已知边界

日期：2026-09-29。设计见 [open-collaboration-v1.md](./open-collaboration-v1.md)，兼容与迁移见 [open-collaboration-migration.md](./open-collaboration-migration.md)。

## 1. 交付结论

本轮把 USMSB 从依赖完整应用环境的入口，推进到**可独立分发、可由外部执行者驱动、有可执行协作约束的 alpha 内核**。共同语义不依赖 Wishbud/OPC/VIBE；原有高级模块保留为可选应用路径，没有删除九要素、旧策略或经济安全修复。

不是“硅基文明已经实现”、生产认证、全网共识或真实商业闭环。未发布 PyPI、未部署生产、未启动付费模型协作或真实收付款。

| 交付项 | 已实现与核验 | 边界 |
|---|---|---|
| 独立分发 | `usmsb-core 0.9.0a1`；同源导出，独立命名空间；sdist/wheel 带清单与许可证；隔离环境能导入并运行持久回执 | alpha、本地构建；默认无第三方运行依赖，learning extra 才需要 Pydantic |
| 显式规则集 | 保留旧默认，新增 neutral/peer/self 选项、开放引用与非文本制品 | Profile 是宿主安装的规则，不是自动治理或全网身份 |
| 协作账本 | 目标快照、版本 CAS、冻结条款、必要参与方同意、合同替换、制品、复核、采用、持久幂等与原子回滚 | SQLite 单宿主参考机制；不执行工作、不托管资金、不保证外部恰好执行一次 |
| 可修订目标 | 不追溯改写旧承诺；修订影响保存为不可变分页快照；大量提议不会因回执过大而锁死目标 | 规则/权限配置迁移、取消/争议/退款仍需显式扩展与授权 |
| 旧 SDK 兼容 | root/core 公共导出惰性加载，保留旧别名与真实类型；消除订单适配器导入顺序循环 | 完整包安装依赖暂不骤减；使用旧高级类仍需原依赖 |
| 异语言接入 | 独立 Python 宿主 + 无 SDK 的 Node 客户端，真实本地计算产物；重启重放通过 | 三个测试角色由同一测试操作者控制，不能证明多组织信任或 LLM 自主性 |
| Windows 制品兼容 | 原生 file URI、单次解码、摘要/根目录/符号链接/目录联接检查；旧读回与恢复通过 | Windows ACL 由宿主配置；不把 chmod 当作 Windows 私有权限保证 |
| 文档与门禁 | 中英文入口、详细设计、迁移回滚、示例/API 文档；新增核心阻断门禁 | 旧集成测试仍有债务，结果不掩盖为全库通过 |

## 2. 分支与未提交工作区

最初 `git fetch origin` 后，`origin/main@2a0208f` 已包含所有当时的本地/远端功能分支提交，包括 Health（PR #11）、目标修订（#12）、IAP 经济安全（#13）及 Growth 各工作线；开放 PR 为 0。未为祖先分支重复制造功能合并。

用户追加要求提交工作区改动后：

- 主工作区 `usmsb`：`5a049d4`，保存 `requirements-runtime.txt` 与已跟踪打包元数据的实质差异。
- `usmsb-wt-open-growth-quality`：`97e74d3`，保存 SQLAlchemy asyncio 依赖及源码清单等打包元数据。
- 集成分支：`2b5c97d` 合入上述工作，随后进行本轮整改；最终代码提交与主干状态以 Git/PR 记录为准。
- Health 与 World 公共模型工作区当时没有未提交源码。工作区/旧分支均保留，不删除、不重置。
- 两个旧 `build/` 目录是历史构建副本，保留在本机；纳入忽略规则（旧工作区同时使用本仓库本地 exclude），不提交为第二套源码。忽略不是删除，也不是宣称这些副本经过升级。

交付前再次 fetch，远端 main 仍为 `2a0208f`，集成分支没有落后提交。后续合入不得 force push 或绕过失败的核心验收。

## 3. 本地验证记录

环境：Windows、Python 3.14.7、Node.js；Python 命令使用 `-E -B` 隔离错误的机器级 Python 覆盖。测试并不自动代表生产可用。

| 检查 | 结果 |
|---|---|
| `tests/portable` | **162 passed**；包括原有契约、授权/演化/学习、新规则集、78 项协作反例、12 项独立制品与导入检查、异语言宿主重启 |
| `tests/unit` + `tests/creative_economy/test_services.py`，排除 slow/requires_llm/requires_network | **1261 passed，7 skipped，13 deselected，1 xfailed**；跳过/预期失败不计入通过 |
| 原有经济安全专项（7 个文件） | **72 passed**，已包含于上面更大范围回归；不是额外独立通过总数 |
| `check_python314_baseline.py` | 通过 |
| `check_llm_provider_bypasses.py` | 通过 |
| 新核心文件 Ruff、工作流 YAML/阻断依赖检查、`git diff --check` | 通过 |
| core sdist/wheel `twine check`、无 site-packages 导入与持久重放 | 通过；不能等同于 PyPI 发布 |

本地 JUnit 证据生成到忽略目录 `dist/validation/portable.xml`、`unit.xml`；不将临时测试数据库、缓存、构建目录和测试日志批量提交。

回归中发现并修复：

1. `supersedes` 空白别名可能导致替换错记录：先规范化引用。
2. 调用方在哈希/验证后修改对象：命令与远程回执验证使用同一份快照。
3. 远程状态入口接受未知制品 schema：新增拒绝，并拒绝重复制品 ID。
4. 合法提议数量让修订回执超限：影响快照持久化并分页，不降低目标可修订性。
5. SDK 惰性导入暴露旧订单模块循环依赖：窄化订单适配器的延迟导出，新增多种导入顺序的独立进程回归。
6. Windows file URI 和 POSIX 权限假设：保留安全校验，修复原生路径转换，区分 Windows ACL 与 POSIX 模式。

## 4. 未通过的旧集成套件：明确保留

运行旧 `tests/integration` 与 `tests/agent_protocol/integration`（沿用原 CI 排除旧 end-to-end、排除外部资源标记；本地最多 5 个失败后停止）：**137 passed、2 failed、3 errors**。后续用 `git archive 2a0208f` 在独立临时目录复跑对应 3 个文件，同样复现 **2 failed、3 errors**，不是用当前修改覆盖基线后作判断。

| 遗留类别 | 证据与后续处理 |
|---|---|
| `test_concurrent_reads_return_consistent_data` | 并发读取测试使用共享 SQLite 状态，出现 0/None 计数；需要独立处理旧数据库连接与测试隔离，不能归为新 journal 已通过 |
| `test_delete_demand_requires_auth` | 测试路径返回 500：`no such table: demands`；应修复应用/测试数据库绑定及认证预期，不能把 500 加进成功列表 |
| MetaAgent 集成 fixture（首 3 项） | `config.llm` 为 dict，运行时读取 `.provider` 导致 AttributeError；需修复旧 fixture/config 兼容并重新跑完整旧套件 |

旧 CI 曾用 `|| echo` 吞掉集成测试退出码。本轮改为明确标注 **advisory** 的失败步骤、摘要和 JUnit 附件，不声称修完旧集成套件；新 portable/core 构建以及既有关键契约仍为阻断门禁。CI 状态以实际 Actions 记录为准，不能仅凭汇总绿色推断旧集成测试全部成功。

## 5. 下一阶段验收，不混入本轮完成声明

优先顺序：修复上述旧集成债务并逐项提升为阻断门禁 → 一个外部宿主的真实身份/证据适配 → 多控制主体的真实协作验收 → 协议版本协商与治理迁移 → 规模、故障与长期演化实验。支付/IAP 的真实证明、商户渠道与争议对账单独验收，不用本地账本替代。

对 Wishbud/OPC 的生产切换需单独决定：备份、旧新契约适配、身份/可见性政策、在途承诺和不确定操作对账。此次 SDK 改善并未偷偷修改线上模型预算、PEA 或 World 数据。
