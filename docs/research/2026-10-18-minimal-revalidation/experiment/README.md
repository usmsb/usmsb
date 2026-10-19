# 可复现离线对照实验 v1

本目录只提供固定有限假设族与已知 Bernoulli 观测核下的工具检验。脚本策略不是 AI，不是新算法、HEC 完整复现或 SOTA，不提供 AGI 或现实用户价值证据。行为目标是检验目标相关再验证的观测成本、结论能力和失败边界，为主体是否使用这个局部工具提供可检查依据；不将策略写入平台语义决策主线。

实验设置在首次完整运行前固定。`scenarios.py` 是案例声明，`strategies.py` 是策略，`run_experiments.py` 通过 `importlib` 直接加载 `src/usmsb_sdk/autonomy/revalidation.py`。只依赖 Python 标准库；不导入整个 SDK，不需要 pytest、网络、外部模型或费用授权。

## 运行

从 `usmsb` 仓库目录运行，推荐现有 Python 3.14 `.venv`：

```powershell
.\.venv\Scripts\python.exe -E -B docs/research/2026-10-18-minimal-revalidation/experiment/test_experiment.py
.\.venv\Scripts\python.exe -E -B docs/research/2026-10-18-minimal-revalidation/experiment/run_experiments.py --workers 4
.\.venv\Scripts\python.exe -E -B docs/research/2026-10-18-minimal-revalidation/experiment/run_experiments.py --check --workers 2
.\.venv\Scripts\python.exe -E -B docs/research/2026-10-18-minimal-revalidation/experiment/test_experiment.py
```

首次运行写入 `experiment/results/first-run/`，已有结果绝不覆盖。`--check` 重新执行全部 4,000 个试验，比较全部文件字节（含 gzip 日志、manifest），不写结果。worker 数不进入实验条件，生成顺序固定。stdout 只输出一条摘要。`--results` 只能指向本目录的 `results/` 内，供明确标记的新版本使用；没有 CLI 调参选项。Python/zlib 版本入 manifest；跨运行时字节一致不作保证，版本或代码变化会被报告。

`-E` 忽略本机可能指向其他 Python 版本的 PYTHONHOME/PYTHONPATH；`-B` 禁止在源码目录产生字节码缓存。并行子进程继承这些解释器选项。

## 预先固定的条件

- seed = 20261018，每案例每策略 80 次，共 10 × 5 × 80 = 4,000 次。
- 每个会话 delta = 0.05，最多 800 次新观测，包含目标修订前的共同新观测前缀。delta 不是全部 4,000 次试验的联合错误预算；多个策略共享样本，不是独立实验。
- 每次均输入 16 条旧作用域观测，单价 2，旧成本 32。所有 H 对旧观测预测完全一致（p=0.9），所以旧成功不能排除当前变化。历史观测为同一重复的全部策略共享；每条只登记一次，既有成本每个方案均显示，不是重新执行历史的额外现实支出。
- 每个案例的获准新 probes、核、成本、目标、delta、历史和上限对所有策略相同。`max_cost` 为旧成本加 800 倍最贵获准新 probe 成本；另行强制 800 次新观测上限，不让不同单价改变观测上限。
- 族内真实 H 在每个案例/重复中均匀有放回抽样，并在所有策略间共享。每个 probe 有独立、确定的随机流，各策略第 n 次查询同一 probe 取得同一结果，适应性顺序不改变流。模拟器掌握真相；策略不接收真相、未来结果或实际变化位置。
- 全部 80 次（包括选错、未决、预算耗尽和模型冲突）进入分母、均值和日志。paired.csv 同时给出全部配对成本差与双方正确条件下的成本差，后者有明确分母，不能用它隐藏失败。

## 五个策略与共同证据规则

共同证据规则直接使用 SDK 会话：固定 H，似然比阈值 `log((|H|-1)/delta)`，逐步排除，保留集的所有假设有共同可接受动作才形成条件性结论。默认选共同动作中按字符串排序的第一项。空保留集为 model_conflict；没有共同动作且全部保留成员在获准新 probes 上完全同分布时，记录不可辨识冲突并拒绝行动。达到上限仍不满足相应停止条件则未决。

| 策略 | 选 probe | 停止要求 |
|---|---|---|
| uniform | 固定顺序 round robin | 共同证据规则 |
| full_identification | 对保留的全部假设对，最大化平方概率差之和 / probe 成本 | 共同证据规则，且保留集已是 singleton 或获准 probe 下不可区别类 |
| decision_greedy | 对假设对按可接受动作集合的对称差大小加权，再最大化平方概率差之和 / 成本；每第 4 次选 probe 使用独立 round-robin 覆盖游标 | 共同证据规则 |
| hinted_coverage | 每第 4 次使用给定 hint（未获准则忽略），其余使用 round robin；任意前缀中强制 hint 槽位至多 1/4 | 共同证据规则；hint 不剪 H、不改核、不改阈值 |
| blind_reuse | 不作策略新观测，直接选择给定旧动作 | 负对照，明确绕过证据背书，绝不记作 certified |

全模型探索可在已经出现动作证书后继续观察，日志记录首次证书成本；它无权使用更便宜的观测、不同错误阈值或更大上限。若预算内已有动作证书但未完成辨识，记录证书可用但全模型策略未决。各贪心并列先选自身历史采样次数最少的 probe，再按公开声明顺序。分数是可解释启发式，不声称信息论最优。动作集合相同的假设对对目标贪心贡献为零；仅仅两两相交不等于全局共同动作。

hinted_coverage 的普通覆盖可能碰巧访问同一 hinted probe；1/4 限制针对强制提示槽位，不声称该 probe 的总访问占比至多 1/4。decision_greedy 每 4 次保证一次覆盖访问，并非每个 probe 每 4 次都访问。

## 案例

| 案例 | 固定设计及主要边界 |
|---|---|
| irrelevant_nuisance | 5 bit 的 32 个 H，只有 bit 0 决定动作；4 个无关维度；相关 probe 单价 1，无关 probe 单价 1.5 |
| unknown_changed_location | 未变化或四个位置之一变化共 5 个 H；实际位置只归模拟器所有；旧动作 maintain |
| unidentifiable_conflict | 两个 H 的所有核相同，可接受动作冲突；证据不能完成决策 |
| goal_revision | 3 bit 的 8 个 H，共同新环境前缀为 new_0 的 24 次观测；动作条件由 bit 0 改成 bit 1；动作字典、H 与核都已固定且已知 |
| misleading_hint | 4 bit 的 16 个 H，目标只依赖 bit 3，hint 固定指向无关 bit 0；提示不是实际变化位置 |
| restricted_probes | 2 bit 的 4 个 H，目标依赖 bit 1，但只允许探测 bit 0 |
| outside_family | H 中新核为 0.1/0.9，实际为 0.85 且正确动作是 a0；观察倾向支持 a1。这是族外失配，保证明确不适用，可能高置信选错 |
| multiple_correct_actions | 三个 H 的动作集合为 {a,b}、{a,c}、{b,c}；两两相交但没有全局共同动作；排除一个 H 即可能够用 |
| scope_shift | 两个联合 H 都预测相同的旧成功，新核为 0.1/0.9；禁止把旧作用域观测当新观测重算 |
| weak_signal_budget | 新核 0.48/0.52；检验 800 次上限内未决与错误，保留全部结果 |

目标修订发生在所有策略开始各自选 probe 之前，所有策略承担相同的历史和前缀成本，包括盲复用。修订事件记录前后评价与未改变的似然。它检验已知形式化表示的目标修订，不检验策略自主发现目标变化或从自然语言生成新假设。

## 产物与复核

`specification.json` 保存完整公共模型和模拟器设定；`manifest.json` 保存源文件 SHA256、运行时和所有产物 SHA256。`summary.json/csv` 报告结论率、选错率（全重复和已选动作两个分母）、正确选择率、证书数、真 H 被排除数、成本与停止原因；`paired.csv` 保留配对比较；`report.md` 给出可读表格。

`trials/<case>.jsonl.gz` 每行是一次完整试验，共每案 400 行，标准库 gzip 可读取。每条新旧原始观测都含唯一来源、作用域、结果、策略选取理由、消除列表和累计成本；目标修订事件及最终似然可核对。真相单独标为 `truth_evaluator_only`，只供离线评价，未传入 Policy。

`test_experiment.py` 检查实验固定条件、策略输入面、配对随机流、提示比例、覆盖、权限范围、动作交集、字节比较无写入；结果存在后审核全部 4,000 条试验的成本与结果，并重放每案例每策略首尾两次（100 次）核对原回执、消除过程和最终评价。这些是工具/实验契约证据，SDK 的数学与单元测试另由用户维护。

首次完整运行后不根据结果调参；结果目录及失败必须保留。如发现实现错误，需要保留错误运行、明确说明，并另建版本，不能替换为表现更好的一轮。解释性复盘放在本目录 `FINDINGS.md`，不回写冻结的实验源码或结果。
