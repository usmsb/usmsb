# 协作账本：规模、故障与受控多轮实验

本工具落实 [开放协作交付记录](./open-collaboration-delivery.md) 所列下一阶段实验的**可复现工程入口**，不改变原交付结论。它验证单宿主 SQLite 协议在并发、进程终止、恢复和脚本化目标修订下的不变量；不证明长期涌现、智能、自主学习、多组织信任或生产可用性。

实现为 `scripts/check_collaboration_resilience.py`，测试为 `tests/portable/test_collaboration_resilience.py`。不需要模型、网络、服务账户、收费 API 或应用服务器。使用现有 `export_autonomy.py` 将实际源码导出到本次实验专用临时目录；未改生产模块、导出清单、CI 或原交付报告。

## 运行与资源边界

在仓库根目录的 PowerShell 中运行：

```powershell
# 默认：4 个负载 goal、2 个并发 worker、每 goal 3 轮修订，45 秒全局预算。
.venv/Scripts/python.exe -E -B scripts/check_collaboration_resilience.py

# 一个稍大的、有界样本；不是长期验收。
.venv/Scripts/python.exe -E -B scripts/check_collaboration_resilience.py --goals 8 --workers 3 --rounds 4 --seconds 45

# 仅本工具的测试；禁用 pytest 缓存写入。
.venv/Scripts/python.exe -E -B -m pytest -q -p no:cacheprovider tests/portable/test_collaboration_resilience.py
```

| 配置 | 默认 | 硬边界 |
|---|---:|---|
| `--goals` | 4 | 1–64；指负载 goal，不含固定故障/恢复探针 |
| `--workers` | 2 | 2–4 个实际 Python 工作进程；Windows 可能另有解释器启动器 |
| `--rounds` | 3 | 1–32 轮/goal，且 `goals × rounds ≤ 256` |
| `--seconds` | 45 | 5–120 秒，全阶段共用；清理最多另加 5 秒及操作系统调度时间 |

所有 SQLite 操作都在被监督的子进程内执行，SQLite 内部等待也受全局预算约束。子进程使用同一 Python 的 `-E -B -S` 模式；并发阶段按 worker 分配 goal。每 goal 初始建立一个双方接受的活动合同和两个待接受提议，每轮产生四条新提交事件。账本命令预算固定为 10000，参数上限下实际提交远低于此值。超限参数在分配目录和启动进程前被拒绝。

每次创建系统临时目录下的 `usmsb-collaboration-resilience-*` 独立目录，保留以下证据：

- `report.json`：完整报告；同一 JSON 也写 stdout。
- `journal.sqlite`、`checkpoint.sqlite`、`restored.sqlite`：本地合成账本、检查点和恢复副本。
- `resilience_core/`：本次固定源码快照及 `MANIFEST.json`。
- 每个 worker 的 job、PID、ready、result、逐调用 `samples.jsonl` 和 stderr 文件。

脚本不接受生产数据库路径，不读取应用配置或凭据，不调用网络、不执行模型、不上传报告。证据目录会保留，系统临时文件清理可能删除它；需长期保存时另行归档已核验的报告和源码快照。临时目录应位于本机磁盘；工具拒绝 UNC 路径，映射盘或网络挂载仍需由运行者确认。未设置 Windows ACL 的特殊保证。

成功退出码为 `0`，实验不变量失败/异常/超时为 `1`，参数错误为 `2`。实验失败会保留报告、错误和已完成的样本，其余阶段标为 `skipped`；不能把跳过项计入通过。受控杀死 writer 是预期故障事件，另计 `expected_killed_writers`。

## 各阶段实际验证什么

| 阶段 | 操作与验收证据 |
|---|---|
| 源码与初始化 | 导出实际 journal/store；记录 Git 基准、脏源码状态、逐文件 SHA-256、Python/SQLite/OS、SQLite journal mode、synchronous 和 page size |
| `replay` | 多个独立进程各自打开真实 SQLite 连接，在连接打开后设置屏障；所有同 command 调用进入后统一放行，要求回执完全相同，只提交一条事件 |
| `cas` | 同一 goal、同一 `base_revision=1`、不同 command 和候选内容同时竞争；要求恰好一个成功，其余明确拒绝 `Stale goal revision`，最终状态等于获胜回执 |
| `fault_baseline` | 建立活动合同并保存整库逻辑摘要，包含版本、命令、影响表、scope 绑定及 `sqlite_sequence` |
| `kill_writer` | 使用真实 `goal.revise` 写入新版本、影响行和持久回执；在 store 的 commit 前暂停并确认非空 rollback journal；父进程强杀真正持有 SQLite 的 Python PID |
| `rollback_restart` | 新进程重新打开账本，要求整库逻辑摘要与故障前完全一致，`integrity_check=ok`；重试被杀 command 后只提交一次，再次重放返回原回执 |
| `load` | 在同一 SQLite 文件上并发建立 N 个 goal 及合同，采集每次真实 `apply()` 的耗时和结果 |
| `revision_rounds` | 每 goal 重复“修订 → 重放 → 拒绝旧 CAS → 替换合同提议 → 双方同意”；检查旧版本、冻结条款、待接受提议不被追溯修改，以及影响快照跨两页的稳定性 |
| `restart` | 独立新进程遍历所有历史版本、分页影响及合同链，核对事件数量、连续序号、command 唯一性和最初回执的幂等重放 |
| `backup_restore` | 使用 SQLite backup API 创建无并发写入的检查点；源账本追加一个已提交 tail，再恢复至另一个新文件；核对检查点全部内容和回执、tail 不存在、恢复后可写且不修改源账本/检查点 |

生产 `SQLiteEvolutionStore` 每个事务都会建立独立连接并执行 `BEGIN IMMEDIATE`。工具没有替换 SQLite 事务实现：仅在 replay/CAS 子进程内为第一次真实连接加入屏障，并为故障 writer 包裹该实例的事务上下文以停在 commit 前。故障注入将该连接的 page cache 调小并允许 spill，让未提交写入实际产生 rollback journal。其他阶段沿用 store 的默认设置。

Windows venv 的启动器 PID 可能不同于实际解释器 PID，因此报告分别保存 `launcher_pid`、`killed_pid` 与故障点 PID，验证终止目标是实际 writer。`SIGKILL`（POSIX）/`TerminateProcess`（Windows）使 Python 的正常 rollback/finally 无法运行；回滚由下一次 SQLite 打开完成。这覆盖进程崩溃，不模拟机器断电、磁盘损坏、网络分区或硬件缓存失效。

恢复点是显式检查点。`checkpoint_sequence` 之后的 `backup:tail` 不在恢复副本中，报告列出被排除的 command；不声称零 RPO、自动灾备或并发写入期间的备份保证。恢复后探针只写恢复副本。

## 如何读 JSON 指标

`config`、`hard_limits`、`started_at_utc`、`finished_at_utc`、`wall_seconds`、`environment`、`harness_sha256` 和 `source_manifest` 共同描述本次样本。共享工作区可能有未提交源码，manifest 会明确记录；复现应保留该次导出的确切内容，不能只引用 HEAD。CAS 获胜者、进程号和时间测量本来就会变化；可复现的是配置、输入生成规则和不变量，不是逐字相同的报告。

每个 phase 和全局都有 `metrics`：

- `completed_apply_attempts` 是已经观测到完成的调用；分为 `success`、`expected_rejection` 和 `unexpected_failure`。启动/核验失败另见阶段 `error`，不是数据库调用失败样本。
- `success` 包括幂等重放；`unique_successful_command_ids` 去掉重复 command，但全局含源账本及恢复副本的探针，不能直接当作单一账本提交数。实际提交数在 restart 的 `event_count` 及 backup 的 checkpoint/tail 序号中验证。
- `latency_ms` 给出 count、min、p50、p95、p99、max，使用 nearest-rank；包括所有完成结果的 `apply()` 执行、锁等待和回执处理，不包含 worker 初始导入及其 journal 初始化。
- replay/CAS 的延迟还包含显式连接屏障等待，属于故障/竞争证据。正常负载延迟应看 `load` 和 `revision_rounds`；其调用前屏障在计时之外。
- `sample_window_seconds` 从首个已观测调用开始至最后一次完成，窗口中的检查、调度、JSONL 写入和跨阶段空档都算在内；吞吐分别是成功调用数、全部完成调用数除以该窗口。它不是纯 SQLite 极限吞吐，也不是远程工作吞吐。
- 被杀/超时的未完成调用没有虚构延迟，也不计成功。worker 每完成一个调用就追加 JSONL；失败报告尽量恢复这些样本，并标记 `incomplete_workers`。若恰在提交到遥测落盘之间被杀，样本可能缺失，失败报告不能推定未观测命令均未提交。

完整成功运行在备份前的事件数为 `6 + N × (6 + 4 × rounds)`。例如 N=3、workers=3、rounds=2 时应有 48 条事件、61 次成功调用（含重放）、8 次预期拒绝；备份源 tail 和恢复副本探针分别使用序号 49。此算式是核对样本完整性的约束，不是性能承诺。

## 受控多轮与后续长期实验

目标变化由脚本固定生成，`evidence_ids` 是明确标记的合成引用，所有身份均由同一测试操作者控制。不使用学习模型、真实观察或业务成效指标。报告固定包含：

```json
{
  "protocol_stress_only": true,
  "long_term_emergence_completed": false,
  "autonomous_intelligence_demonstrated": false,
  "external_services_used": false
}
```

当前工具适合作为长期研究之前的协议回归基线，或按人工选定的配置重复短实验并归档比较。硬上限不因“长期”选项被绕过；没有后台自动循环、调度器或跨运行自动恢复。报告的实际样本时长必须随结果一起引用，不能将快速多轮冒充长时间运行。

进一步长期验收仍需单独设计多控制主体、真实证据来源、观察周期、对照组、治理/版本迁移、失败判据及数据保留策略。实验通过只说明此次边界内的协议压力验证通过。发现真实 journal 缺陷时，应保留失败 JSON、源码摘要和配置，单独报告并修复生产代码后重新运行；本工具不吞异常、不改生产实现来绕过失败。
