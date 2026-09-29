# 开放协作内核整改：交付证据与已知边界

日期：2026-09-29。设计见 [open-collaboration-v1.md](./open-collaboration-v1.md)，兼容与迁移见 [open-collaboration-migration.md](./open-collaboration-migration.md)。

**本次跟进：已修复原本失败的本地集成路径，补齐 a2 的宿主接入/版本协商、显式增量迁移及有界故障实验。最新问题闭环见第 6 节。真实外部宿主、多组织、长期演化、真实证明/商户支付和生产切换仍须外部验收，不冒充完成。** 第 1–4 节保留初次 a1 交付历史，不应当作最新测试状态。

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

## 4. 初次 a1 未通过的旧集成套件（历史；本次处理见第 6 节）

运行旧 `tests/integration` 与 `tests/agent_protocol/integration`（沿用原 CI 排除旧 end-to-end、排除外部资源标记；本地最多 5 个失败后停止）：**137 passed、2 failed、3 errors**。后续用 `git archive 2a0208f` 在独立临时目录复跑对应 3 个文件，同样复现 **2 failed、3 errors**，不是用当前修改覆盖基线后作判断。

| 遗留类别 | 证据与后续处理 |
|---|---|
| `test_concurrent_reads_return_consistent_data` | 并发读取测试使用共享 SQLite 状态，出现 0/None 计数；需要独立处理旧数据库连接与测试隔离，不能归为新 journal 已通过 |
| `test_delete_demand_requires_auth` | 测试路径返回 500：`no such table: demands`；应修复应用/测试数据库绑定及认证预期，不能把 500 加进成功列表 |
| MetaAgent 集成 fixture（首 3 项） | `config.llm` 为 dict，运行时读取 `.provider` 导致 AttributeError；需修复旧 fixture/config 兼容并重新跑完整旧套件 |

旧 CI 曾用 `|| echo` 吞掉集成测试退出码。本轮改为明确标注 **advisory** 的失败步骤、摘要和 JUnit 附件，不声称修完旧集成套件；新 portable/core 构建以及既有关键契约仍为阻断门禁。CI 状态以实际 Actions 记录为准，不能仅凭汇总绿色推断旧集成测试全部成功。

## 5. 后续验收范围与权限边界

优先顺序：修复上述旧集成债务并逐项提升为阻断门禁 → 一个外部宿主的真实身份/证据适配 → 多控制主体的真实协作验收 → 协议版本协商与治理迁移 → 规模、故障与长期演化实验。支付/IAP 的真实证明、商户渠道与争议对账单独验收，不用本地账本替代。

本次已执行不依赖外部授权/参与方的工程项，进度与尚缺条件逐项列在下面，不将整条路线一并标为完成。

对 Wishbud/OPC 的生产切换需单独决定：备份、旧新契约适配、身份/可见性政策、在途承诺和不确定操作对账。此次 SDK 改善并未偷偷修改线上模型预算、PEA 或 World 数据。

## 6. 本次问题整改与 a2 交付

基线为已合入的 `main@b86dbcc`；复用干净工作区，分支 `codex/usmsb-integration-closure`，不覆盖其他工作区。core 版本更新为 **0.9.0a2**；完整 SDK 版本保持不变。新增模块仍在规范源码中维护，并纳入同源导出和独立制品。

| 原问题 | 实际完成的工程工作 | 状态与不能替代的验收 |
|---|---|---|
| 并发 SQLite 与错库 | 测试使用独立临时 DB；保留真实 `get_db` 连接/事务工厂，只绑定路径；并发读取每线程独立连接；初始化错误不再吞掉；清理跨测试查询缓存 | 本地修复验证通过，不改生产数据库 |
| demands/wallet/services 500 | 所有路由导入别名绑定同一临时 DB；严格检查创建、所有权、缓存失效、真实未认证 401、别人的交易不可见、分页边界；新增真实 API key 哈希认证及撤销测试 | 不再把 500/任意错误算成功；本地记录不等于链上资金 |
| MetaAgent fixture / 陈旧接口 | 使用真实配置类型、实际服务与数据库；只替代外部模型边界；禁止网络；发现并修复服务调用 LLMManager 时错用 `messages`/返回值类型的问题 | 离线服务集成通过，不声称调用真实模型 |
| 存储与节点遗留问题 | 修正真实存储构造/返回契约；文件键从元数据恢复并防止用户元数据覆盖 key；保留删除失败原因；节点显式地址不再触发额外网络探测，实际使用随机回环端口，关闭并等待后台任务 | 使用真实本地文件/SQLite/回环 socket，不以全 mock 或新增 skip 代替修复 |
| 集成 CI 不阻断 | 移除集成步骤 `continue-on-error`；失败直接阻断 build 与汇总，保留 JUnit；新机制 Ruff 与 portable 同为阻断项 | 历史未启用/外部条件跳过项见下文，不能说全仓库零跳过 |
| 外部身份/证据适配 | `autonomy.interop`：宿主安装认证器、过期凭据拒绝、禁止自报 actor/controller；制品字节流摘要/长度/额度核验；修订/复核/采用经可信证据回调；成功操作精确重放无需重新取证 | 工程机制完成；真实外部宿主地址、身份/证据政策和授权尚未提供，真实接入未验收 |
| 版本协商 | exact schema、必需功能、Profile ID/版本/完整内容摘要协商；command 绑定 agreement，未知 major/功能和降级规则拒绝 | 当前命令 v1；不是未来所有协议自动兼容 |
| 治理迁移 | `autonomy.migration`：全体旧 controller 对准确增量配置批准、强制一致性备份、配置 CAS、原子审计、旧配置 a2 实例围栏、完整历史保留 | 仅追加主体/不同 ID Profile/增大额度；变更旧身份/权限/规则及取消退款不支持此捷径。迁移前停止不支持围栏的 a1 二进制 |
| 规模/故障/多轮 | 可复现多进程 CAS/重放、commit 前强杀 writer、重开回滚、备份恢复与多轮目标修订/重新同意；输出原始采样与明确边界 | 短时协议实验通过；没有万级 Agent 容量、长期智能涌现或跨组织效果结论 |
| 多控制主体实测 | 接入约束、严格认证/证据边界、反例和参与方验收步骤已具备 | 待真实独立参与方；不能把本机多个角色/进程当成多个组织 |
| IAP/资金闭环 | 原有未知质量、不确定结算、占位 ZK 拒绝等经济安全回归继续保持 | 无真实生产证明器及商户渠道，未发起收付款；签名/哈希/本地余额不能代替真隐私证明和结算对账 |

### 6.1 本地验证证据

完整重跑基线得到 **17 failed、382 passed、28 skipped、28 errors**（有 fixture teardown 错误，JUnit case 数不等同最初 collection 数）；原报告只列了提前停止时先遇到的三类。本次没有只修首个错误后宣布整套通过。

| 范围 | 本次可核验结果 |
|---|---|
| portable 核心 | **309 passed，0 skipped**；含新宿主边界 32 项、增量迁移 96 项、故障实验 19 项，以及既有 162 项 |
| 旧集成范围 | 最终完整重跑 **439 passed、27 skipped，0 failed/error**，包含真实 API key 正向与撤销回归；demands/wallet 专项 **24 passed**（是子集，不再累加） |
| unit + creative economy | **1261 passed、7 skipped、1 xfailed、13 deselected**；无失败。Windows OpenHarness 的既有预期失败不算通过 |
| 制品与静态检查 | a2 sdist/wheel 构建及 `twine check` 通过；新增机制 Ruff、Python 3.14 基线、LLM provider bypass 检查通过 |
| 独立故障样本 | 8 goals、3 worker、每 goal 4 次修订；**11 阶段通过、0 失败/跳过、1 次预期强杀**；约 **5.293 秒**，不是长期实验 |

临时证据在 `dist/validation/integration-baseline.xml`、`integration-closure.xml`、`api-auth-closure.xml`、`portable-closure.xml`、`unit-closure.xml`（忽略目录，不批量提交）。独立实验原始报告位于本机 `%TEMP%/usmsb-collaboration-resilience-5hu8uwi0/report.json`；保留源码 manifest、原始调用样本、数据库/检查点/恢复副本；机器路径只用于本次本地复查，不是公开下载链接。

独立样本的初始负载 48 次调用全部成功，p95 约 191.268 ms；32 轮修订的 192 次尝试含 160 次成功（包括重放）和 32 次预期旧版本拒绝，p95 约 20.620 ms。这些指标包含 SQLite 锁等待和本机调度，不能外推为生产吞吐或几万 Agent 容量。备份前检查点 **182 条持久事件**；恢复副本明确不含检查点后的 tail，未声称零 RPO。

保留的 **27 个跳过**：14 个旧多用户隔离测试需另行整合 SessionManager/浏览器/IPFS 边界，12 个旧 staking/profile 测试按过时路由/模拟余额契约禁用，1 个 gRPC 测试以“library not available”为由默认禁用（未证明当前环境一定缺库）。它们不是本次新加 skip，也不是“通过”；旧 end-to-end 仍按原 CI 排除，外部资源标记仍不运行。不得重新启用模拟余额/虚构支付来让旧金融测试变绿。该基线不等于整个仓库所有测试均已覆盖。

### 6.2 使用与外部条件

接入 API、JSON 协商、凭据与证据回调、迁移批准和回滚步骤见 [宿主接入指南](./collaboration-host-integration.md)；有界实验运行方式、参数上限与指标定义见 [实验说明](./collaboration-experiments.md)。没有修改线上部署、PEA/World 数据、模型预算，未发布 PyPI。

要继续真实验收，需要人类提供或确认：

1. 获授权的外部宿主及身份/证据政策、凭据存放位置；不要在聊天里发送密钥。
2. 独立提供方和独立复核者（默认 independent 模式还要与请求方区分），以及真实项目的采用者/验收标准。
3. 若包含 IAP/收付款，另提供生产证明器与已存在商户轨道及对账/争议责任。暂无则此项保持阻塞，不伪造闭环。

长期演化与生产切换须先确认观察方案/风险预算/切换授权。以上外部条件未满足前，本次完成的是可复现的工程整改，不是宣称该愿景已经在真实世界全部实现。
