# 开放协作内核：迁移、版本与回滚

状态：2026-09-29 alpha 集成期迁移说明，不是发布公告或生产认证。以[架构与验收设计](./open-collaboration-v1.md)为边界；实际集成结果由该设计指向的交付报告记录。本文区分已有契约、本轮增量 API 和后续生产前提，不把设计要求当作已通过的结果。

## 1. 哪些使用方式需要迁移

USMSB 的九要素是共同语义，World/宿主定义认证、权限、可见性与协作规则，Agent 自行选择目标、策略、工具与执行方式。Wishbud、OPC、PEA、IAP 和 VIBE 均不构成使用共同语义的前提。`Value` 可以表达研究、公共知识、互助、服务与经济价值，不要求统一货币、排名或可交易性。

| 使用方 | 本轮迁移路径 |
|---|---|
| 已使用完整 `usmsb-sdk`、PEA、A2A 或经济模块 | 保留原导入和依赖，按消费者逐步采用新契约；本轮不自动迁移应用数据、预算、支付或身份 |
| 已使用 portable 导出、Wishbud 风格引用或旧契约 | 保留原默认行为；中立 Profile 必须显式选择，不能只换包就假定旧数据已转换 |
| 只需要共同语义、协作记录的外部 Agent/宿主 | 可评估 portable 子集；独立 `usmsb-core` wheel 经本轮构建和隔离验证后再采用，名称不代表已发布 PyPI |
| 通过 JSON 接入的异语言执行者 | 由宿主适配传输和认证；执行者无需导入 Python SDK，也无需启动 Wishbud/OPC 或连接支付/模型服务 |

参考策略、演化引擎和经济应用仍可选用。`CollaborationJournal` 记录合作状态，不替外部 Agent 决策、调用工具、运行模型或授予超出宿主配置的权限。

## 2. 包、协议、规则集和应用版本分别管理

| 版本对象 | 当前标识 / 例子 | 升级含义 |
|---|---|---|
| 完整包 | `usmsb-sdk`；`pyproject.toml` 当前为 `0.9.0-alpha`；导入 `usmsb_sdk` | Python 制品版本，继续要求 `>=3.14,<3.15`；不自动改变存量协议 |
| 独立核心包 | 本轮新增 `usmsb-core`；当前元数据 `0.9.0a1`；导入 `usmsb_core` | 从同一份规范源码生成，同样要求 Python `>=3.14,<3.15`；不复制维护第二份内核或覆盖 `usmsb_sdk` 目录 |
| 协议 schema | 旧 `usmsb.goal-contract.v1`；显式中立 Profile 使用 `usmsb.goal-contract.v2` | 消费者必须理解实际结构和必需语义；不支持的必需 schema/major 应拒绝，不能删掉版本字段继续执行 |
| Profile | `id`、`version`、复核方式、媒介和有界限制 | 参与方采用的协作规则；规则变化必须显式版本化和重新协商，不能通过包升级覆盖旧承诺 |
| 目标与承诺 | `goal_revision`、不可变目标快照、`terms_hash`、`supersedes` | 表达当时接受的意图与条款；不等于包号或协议 major |
| 应用 | Wishbud/OPC 或其他宿主自己的发布号 | 应用负责适配、权限、迁移和运维，不能从 SDK 包号推断应用就绪 |

完整包默认安装依赖仍包括模型/Web/区块链等应用依赖。本轮惰性导入目标是让轻量模型与契约的导入不加载无关模块；这与减少完整安装依赖是两件事，需分别验收。

独立 core 的目标是默认仅使用标准库，现有经验适配器通过可选 `learning` extra 使用 Pydantic。安装元数据、源码清单、许可证、来源提交、dirty 状态及文件 SHA256 都应随制品验证。含工作区修改的清单不能只用基线提交号冒充干净发布；SHA256 也不是发布者签名。

## 3. 保持兼容与显式选择规则

以下对应当前 [contracts.py](../../src/usmsb_sdk/autonomy/contracts.py)、[profiles.py](../../src/usmsb_sdk/autonomy/profiles.py) 与 [open_world.py](../../src/usmsb_sdk/autonomy/open_world.py)。新增签名属于 alpha API；升级时应固定实际制品及相应测试结果。

| 调用 | 保留的默认行为 | 显式新行为 |
|---|---|---|
| `goal_contract(criteria, verifier_ids)` | `WISHBUD_V1`，返回旧 `usmsb.goal-contract.v1` 结构 | `profile=OPEN_COLLABORATION_V1` 等中立规则集时返回 v2，记录 Profile 和复核模式 |
| `world_reference(node, ledger, kind, record_id)` | 校验旧 `wishbud:ed25519:…` 和 `storage_…` 格式 | 中立 Profile 生成带转义分段的 `usmsb-ref:`；引用不是凭据 |
| `remote_status(value)` | 保留旧文本输出约定和 accepted/running/completed/failed/unknown | 中立 Profile 可验证 `output.artifacts` 引用列表；仍不下载或执行内容 |
| `plan_steps(steps)` | 保留旧默认步骤限制及依赖检查 | Profile 可明确有硬上限的步骤限制；不执行计划 |

`entity_reference(authority, namespace, kind, record_id, *, version=None)` 表达跨宿主可归属的对象位置，不授予访问权。`artifact_reference(artifact_id, media_type, sha256, uri, size_bytes, *, profile=OPEN_COLLABORATION_V1)` 校验描述符格式；真实字节、来源、安全性和哈希匹配由宿主检查。

下面只构造契约，不产生承诺、授权或执行（适用于集成本轮 API 的完整 SDK 环境）：

```python
from usmsb_sdk.autonomy import OPEN_COLLABORATION_V1, goal_contract

contract = goal_contract(
    [{"id": "reproducible", "description": "复核者可复算结果", "evidence_kind": "artifact"}],
    ["lab-reviewer"],
    profile=OPEN_COLLABORATION_V1,
)
assert contract["schema"] == "usmsb.goal-contract.v2"
assert contract["review_mode"] == "independent"
```

独立分发验收后，对应入口为 `usmsb_core.autonomy`。源码导出时，导入前缀由导出目录名决定；导出为 `portable_usmsb` 不会自动安装 `usmsb_core`。

`OPEN_COLLABORATION_V1` 默认独立复核；`PEER_COLLABORATION_V1` 允许同伴复核。自评需显式安装 `CollaborationProfile(..., review_mode="self")`。账本对 independent 排除请求方和提供方的控制主体，对 peer 排除提供方控制主体；self 不增加这两类独立性约束，但仍需约定复核者及证据引用。构造 `goal_contract` 本身不会认证复核者，也不能证明不同字符串代表独立的人或组织。

Profile 由可信宿主代码安装，不直接采纳客户端提交的任意规则对象。同一账本当前每个 Profile ID 只安装一个版本，并把完整配置绑定到数据库；改变配置后重开原数据库会被拒绝。它不是规则热更新或通用协议协商服务。规则演进须另行迁移或并行宿主配置，让新承诺绑定新规则并获得相关同意，旧承诺继续受旧版本约束。

## 4. `CollaborationJournal` 的当前 API 边界

[journal.py](../../src/usmsb_sdk/autonomy/journal.py)提供单宿主、单 SQLite 文件的参考机制：

```python
CollaborationJournal(
    path,
    host_id=host_id,
    principals=principals,
    profiles=(OPEN_COLLABORATION_V1,),
    max_commands=100000,
)
journal.apply(actor, command_id, operation, payload)
journal.get(kind, record_id)
journal.goal_version(goal_id, revision)
journal.events(after=0, limit=100)
```

这是接口形状说明，`path`、`host_id`、`principals` 由宿主提供。`principals` 格式为 `{actor: {"controller": identity, "operations": [允许的命令]}}`。`actor` 必须由宿主认证后注入；业务 payload、自报身份、URI 和能力声明不能代替认证。`get`、`goal_version` 与 `events` 是宿主读取接口，不自带租户可见性检查，不能原样公开为无限制查询端点。

`apply` 在 SQLite `BEGIN IMMEDIATE` 事务内校验权限和前置状态、更新记录并保存事件回执；失败回滚。成功命令以 `command_id` 绑定 actor、操作与 payload 摘要。相同输入重放返回原回执，同 ID 换内容被拒绝；重启不清空回执。命令幂等只约束账本，不保证外部工具、支付或网络副作用只执行一次。

| 操作 | 关键输入与约束 |
|---|---|
| `goal.create` | `id` 与完整 `intent`：`title`、`description`、`domain`、`success_criteria`；创建者为所有者 |
| `goal.revise` | `goal_id`、`base_revision`、`changes`、`reason`、`evidence_ids`；仅所有者，基准版本须匹配，只修订意图字段 |
| `commitment.propose` | `id`、`goal_id`、`goal_revision`、`provider_id`、`description`、`terms`、`criteria`、`verifier_ids`、`profile_id`；可带 `supersedes`；所有者针对当前目标版本提议 |
| `commitment.accept` | `commitment_id`、冻结的 `terms_hash`；请求者、提供者及替换旧约定涉及的原参与方全部接受后才生效 |
| `artifact.submit` | `commitment_id`、`terms_hash`、`artifact` 描述符；仅约定提供方针对有效承诺提交；更改内容应使用新的制品 ID |
| `review.record` | `id`、`artifact_id`、`artifact_sha256`、`terms_hash`、`checks`；约定复核者覆盖全部标准，pass 必须带证据引用；同一复核者对同一制品的复核不可改写 |
| `adoption.record` | `id`、`artifact_id`、`artifact_sha256`、`terms_hash`、`evidence_ids`、`statement`；当前仅约定请求者记录采用，全部约定复核须通过 |

目标修订产生不可变快照，回执列出受影响承诺并明确 `obligations_changed=False`。回执最多包含前 32 个 `affected_commitment_ids`，同时返回 `affected_commitment_count` 和 `affected_next_after`；宿主通过 `revision_impacts(goal_id, revision, after=..., limit=32)` 获取后续 `commitment_ids` 与 `next_after`。影响快照不随后续状态变更而重写。合同修订使用新提议的 `supersedes` 引用；全部所需同意到齐前旧约定继续有效，接受后才标为 superseded。已采用的约定不能改写为未完成；新需求使用新的合作。

目标已更新时，旧成果仍可按旧约定被采用，但采用记录保留原 `goal_revision`，并以 `matches_current_goal_revision` 表示是否匹配当前目标。采用只把该承诺标为 adopted，不自动完成目标或证明因果改善。当前没有通用取消、退款、投票治理或任意第三方采用命令，不应从设计愿景推断这些端点已实现。

## 5. 渐进接入与证据门禁

1. **固定现有基线。** 记录应用版本、Python 3.14 环境、包制品/源码清单、协议与 Profile 版本、已安装授权和数据库位置。保留当前消费者的兼容性测试。
2. **备份再旁路试验。** 对原数据库做可恢复的一致性备份；为 alpha 账本使用独立文件和测试身份。不要把已有 World/经济账本当作新 journal 数据库，也不要改写旧 Wishbud 引用来伪造新身份。
3. **显式接入新契约。** 新调用指定中立 Profile；宿主验证支持的 schema、规则集和必需字段，保留可理解范围以外的附加描述但不给它行为权限。构造器不是通用反序列化或协议协商器。
4. **接通真实职责。** 宿主映射经过认证的 actor 和 controller，限制读取范围并核实制品字节；外部 Agent 自行决定是否接受并执行，再上报可核实的结果。连接中断后的 unknown 只查询、对账原操作，不创建新操作替代。
5. **按证据切换消费者。** 分别验证旧默认行为、中立规则、完整承诺流程、越权与陈旧版本反例、重启重放/并发、隔离安装和经济安全回归。单元测试通过不替代生产身份、真实证据或互操作验收。

已有的 portable 导出从规范源码生成文件和 `MANIFEST.json`。下列命令中的目录需替换为源码树外的专用目录；`--check` 检查它与当前源码是否一致，不执行数据迁移或安装发布：

```bash
python -E -B scripts/export_autonomy.py /absolute/path/to/portable_usmsb
python -E -B scripts/export_autonomy.py /absolute/path/to/portable_usmsb --check
python -E -B -m pytest tests/portable --confcutdir=tests/portable -q -p no:cacheprovider
```

Windows 使用 `.venv/Scripts/python.exe -E -B`。测试依赖与运行依赖分开：portable 测试使用 pytest、packaging，经验适配器测试使用 Pydantic 2，跨语言测试使用 Node.js，分发测试需要 build、setuptools>=77 和 wheel。新 core wheel 的构建/隔离安装结果须单独记录；源码导出可用或完整环境中的 import 成功，都不足以证明 wheel 可在干净环境独立运行。

本轮 [build_core_distribution.py](../../scripts/build_core_distribution.py) 会在临时目录生成并构建源码子集，再输出 wheel/sdist。构建依赖需事先就绪，脚本使用 `--no-isolation`，不自行安装依赖。使用专用输出目录可避免与已有制品混淆：

```bash
python -E -B scripts/build_core_distribution.py --out-dir /absolute/path/to/core-artifacts
python -E -B -m pip install --no-index --no-deps /absolute/path/to/core-artifacts/usmsb_core-0.9.0a1-py3-none-any.whl
```

安装命令应在新的 Python 3.14 验证环境中执行，并使用实际构建的文件名；可选 `learning` 需另行满足 Pydantic 依赖。`packages/usmsb-core` 只保存打包元数据，直接 `pip install packages/usmsb-core` 不会生成规范源码。具体模块导入见[独立分发说明](../../packages/usmsb-core/README.md)；顶层 `usmsb_core` 是命名空间 shim，`Goal` 应从 `usmsb_core.core.elements` 导入。

本轮外部客户端示例使用 Python 宿主与不导入 SDK 的 JavaScript 进程通过 JSON 协作。固定测试身份、本地程序产物、复核及重启重放属于协议集成验证，不是跨组织信任、跨 World 账本复制、付费模型自主性或真实客户交易的证据。

## 6. 回滚及存量义务

包回滚、应用回滚和数据回滚分别处理。旧程序能安装，不代表它能读取新 schema 或 journal；本轮没有承诺自动降级/导入工具。

1. 暂停接收新写入，保留命令 ID、冻结条款、已接受承诺和外部操作键。先确认在途操作，尤其是 unknown/uncertain，避免回滚后重复副作用。
2. 保存当前数据库及相关日志的一致性副本；SQLite 处于使用中时采用其备份机制或在停写并关闭连接后备份，不只复制可能尚未包含全部事务的主文件。
3. 恢复经过验证的旧应用和包，并指向其兼容的旧数据库/备份；保留新 journal 为只读审计资料。不要让旧程序尝试解释不支持的新 schema，也不要删除 scope 绑定记录来绕过身份/Profile 不匹配。
4. 切换前对账升级期间已接受的承诺、采用记录和外部效果。恢复旧备份不能撤销已经发生的交付、披露、支付或他人的权利义务；需要可追溯的业务处置和相关参与方同意。
5. 若不能证明数据向后兼容，保留处理旧/新版本的并行服务或先停止相关写入，完成明确的迁移方案后再恢复。已有成功回执、版本历史和证据引用不得为了“回滚成功”而丢弃。

权限收紧只能阻止后续访问，不能收回已经披露的数据副本。更换宿主身份、controller 关系、Profile 或授权配置需要明确迁移，不能通过重启覆盖原绑定。

## 7. 验证状态与后续生产前提

已有实现包括九要素/模型扩展、旧目标/复核/远程状态契约、目标修订辅助函数、portable 导出、授权、参考策略及学习/演化测试。本轮新增中立 Profile、制品引用、协作 journal、独立分发、惰性导入和异语言示例需逐项记录验证结果；本文中的 API 说明来自当前代码，不构成所有验收门禁已通过的声明。

后续生产工作包括可信身份与控制主体关系、密钥和租户隔离、内容安全与来源核实、读写可见性、备份恢复、负载与资源管理、异构宿主协议互操作及跨 World 信任选择。实际支付要另验支付轨道、争议、故障对账与凭据；不能用本地余额或占位 ZK 响应替代。既有经济安全回归应继续保证未知质量不通过、不确定结算不自动重试、占位证明不签发凭证。

公共账本保存可归属的事实声明及流程记录，不承诺全网共识、科学因果发现、通用智能、自主文明或无限规模。长期学习效果与多组织协作效果需要后续真实、有对照的验证。
