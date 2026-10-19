# 合成实验结果（自动生成）

生成器：experiment/run_experiments.py。不是 AI 行为、商业收益或原创性证明。

固定种子 20261018；每场景 400 次重复；每臂 4096 次登记；delta=0.05；检查点 [32, 128, 512, 2048, 4096]。

每种方法使用同一批模拟样本。表中的期望增益由模拟真值评分，未扣除学习样本与观测成本；不能据此计算实际 ROI。错误包括选择零增益候选；严格负增益另列。

| 场景 | 方法 | 正增益切换 | 严格负增益切换 | 非正增益切换 | 留在基线 | 平均最终期望增益 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| stable_gain | baseline_only | 0 | 0 | 0 | 400 | 0.0000 |
| stable_gain | completed_only | 400 | 0 | 0 | 0 | 0.3125 |
| stable_gain | frozen_goal | 400 | 0 | 0 | 0 | 0.3125 |
| stable_gain | vector_certificate | 400 | 0 | 0 | 0 | 0.3125 |
| selective_missing | baseline_only | 0 | 0 | 0 | 400 | 0.0000 |
| selective_missing | completed_only | 0 | 400 | 400 | 0 | -0.2500 |
| selective_missing | frozen_goal | 0 | 400 | 400 | 0 | -0.2500 |
| selective_missing | vector_certificate | 0 | 0 | 0 | 400 | 0.0000 |
| revised_goal | baseline_only | 0 | 0 | 0 | 400 | 0.0000 |
| revised_goal | completed_only | 400 | 0 | 0 | 0 | 0.4000 |
| revised_goal | frozen_goal | 0 | 400 | 400 | 0 | -0.4000 |
| revised_goal | vector_certificate | 400 | 0 | 0 | 0 | 0.4000 |
| stale_environment | baseline_only | 0 | 0 | 0 | 400 | 0.0000 |
| stale_environment | completed_only | 0 | 400 | 400 | 0 | -0.2500 |
| stale_environment | frozen_goal | 0 | 400 | 400 | 0 | -0.2500 |
| stale_environment | vector_certificate | 0 | 400 | 400 | 0 | -0.2500 |
| stale_environment | drift_envelope | 0 | 0 | 0 | 400 | 0.0000 |
| small_gain | baseline_only | 0 | 0 | 0 | 400 | 0.0000 |
| small_gain | completed_only | 400 | 0 | 0 | 0 | 0.0400 |
| small_gain | frozen_goal | 400 | 0 | 0 | 0 | 0.0400 |
| small_gain | vector_certificate | 0 | 0 | 0 | 400 | 0.0000 |
| adaptive_null | baseline_only | 0 | 0 | 0 | 400 | 0.0000 |
| adaptive_null | completed_only | 0 | 0 | 355 | 45 | 0.0000 |
| adaptive_null | frozen_goal | 0 | 0 | 265 | 135 | 0.0000 |
| adaptive_null | vector_certificate | 0 | 0 | 0 | 400 | 0.0000 |

## 覆盖与多次查看

| 场景 | 证据方法 | 任一检查点覆盖失败次数 / 400 |
| --- | --- | ---: |
| stable_gain | vector_certificate | 0 |
| selective_missing | vector_certificate | 0 |
| revised_goal | vector_certificate | 0 |
| stale_environment | vector_certificate | 400 |
| stale_environment | drift_envelope | 0 |
| small_gain | vector_certificate | 0 |
| adaptive_null | vector_certificate | 0 |

0/400 不是错误概率为零：Wilson 95% 区间上端约 0.9512%。具体频率区间与首次切换统计见 summary.json。每次重复的 0.05 预算不能冒充全部模拟重复的联合保证。

stale_environment 中 vector_certificate 故意使用错误 D=0；drift_envelope 使用已知的 0.60 包络，它不是自动检测器。

## 查明已有试验的待回传结果

| 查明比例 | 新观测数 | 未知补全宽度 | 增益下界 | 增益上界 | 有正增益证据 |
| --- | ---: | ---: | ---: | ---: | --- |
| 0% | 0 | 0.7998 | -0.5507 | 0.4011 | False |
| 25% | 819 | 0.5999 | -0.4014 | 0.4011 | False |
| 50% | 1638 | 0.3999 | -0.2014 | 0.4011 | False |
| 100% | 3276 | 0.0000 | 0.1985 | 0.4011 | True |

这里所有补充观测均成功且不收费，是确定性构造。区间缩小不是经济收益，不能推断现实应无限等待或无限核验。

## 从未测量的新目标

同一可见记录兼容增益 -0.4 与 +0.4 两个系统，新目标的证据区间为 [-1, 1]。这是不可识别构造，不是模型跑分。

所有逐重复选择、观察数量与检查点保存在 trials.jsonl；基础代码 SHA-256 与全部汇总保存在 summary.json。
