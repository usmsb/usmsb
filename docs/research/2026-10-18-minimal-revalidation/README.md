# 目标演化下的协作经验迁移与最小再验证

日期：2026-10-18。交付：研究、可选 SDK 工具、Wishbud/Morrow 与 OPC 本地接入、模拟及真实 AI 行为证据。**不是 AGI、市场优越性或原创突破声明。**

## 研究问题

当目标、伙伴或环境发生变化时，智能主体怎样判断哪些旧经验仍可用，怎样花较少代价补充真正影响当前决策的证据？

这承接[上一阶段研究](../2026-10-18-collaboration-evidence/README.md)，不把 USMSB 缩成一个统计算法。主体理解和修订目标、形成假设、选择伙伴、决定试验和解释价值；软件提供授权边界、可追溯上下文与计算工具。人的持续点击不是本研究预设的发动机。

## 阅读顺序

1. [研究协议](01-protocol.md)：执行前写下的范围、对照、预算和失败口径。
2. [独立查新与批判](02-independent-prior-art-review.md)：DRD、纯探索和顺序检验是直接前驱，不能把已有理论改名当原创。
3. [数学推导与不可能性边界](03-mathematics.md)：条件正确性、识别条件、成本下界、目标修订和族外失配。
4. [模拟方法与复现](experiment/README.md)、[结果解释](experiment/FINDINGS.md)、[完整报告](experiment/results/first-run/report.md)：4,000 次合成试验，全部负结果保留。
5. [真实 AI 与产品接入](04-real-ai-and-integration.md)：三类真实推理行为、一次失败及修复、完整回执、默认和可选路径。
6. [交付、验收与未完成的科学问题](05-delivery-and-open-problems.md)：工程完成不等于愿景完成。

## 本轮最重要的发现

- 在固定、覆盖真实机制的有限模型中，AI 可以任意选择获准探针，标准序贯检验仍能给出条件错误界；目标重评不必重复计算同一份证据。
- “只查与目标有关的信息”有时省成本，但不是普遍优于其他方法。未知变化位置会产生定位成本，不能只按变化数量宣称低复杂度。
- 目标相关贪心在无关因素场景的新观测成本为 3.85，对照完整识别为 26.0125；计入共同历史成本32后，总成本为35.85对58.0125。它不是与最强已有算法的比较。
- 族外失配场景中，四个证据策略各有79/80次错误。系统未发现冲突，并不证明世界模型正确。
- 真实 Codex 在三个合成环境中自主选择了两次相关读取、舍弃一次不相关读取，修订旧建议或保留未知。伙伴案例的工具实际经过本地 OPC A2A runtime，再交给 Morrow；不是现实客户/收益试验。

## 工程入口

可选计算器：[revalidation.py](../../../src/usmsb_sdk/autonomy/revalidation.py)，测试：[test_revalidation.py](../../../tests/autonomy/test_revalidation.py)。通过 `scripts/export_autonomy.py` 纳入 `usmsb-core`，没有加入全局 planner，也没有强制 Morrow 使用统计计算器。

完整SDK用下面的`usmsb_sdk`导入；独立core发行包使用`usmsb_core.autonomy.revalidation`，无需安装完整SDK或LLM依赖。

```python
from usmsb_sdk.autonomy.revalidation import (
    FiniteModel, Hypothesis, Observation, Probe, RevalidationSession,
)

# 仅用于演示；这些概率不由 LLM 自信得分充当。
model = FiniteModel('calibrated-demo-v1', (Probe('check', 1.0, 'current'),), (
    Hypothesis('unchanged', (0.9,)), Hypothesis('changed', (0.1,)),
))
session = RevalidationSession(model, allowed_probes={'check'}, max_cost=20, delta=.05)
session.observe(Observation('receipt-1', 'check', 'current', 1, 'fixture://receipt-1'))
result = session.evaluate('goal-2', {'unchanged': {'reuse'}, 'changed': {'revise'}})
assert result['status'] == 'inconclusive'  # 一条证据不必产生结论。
```

实际使用前，宿主须验证测量来源、完整登记流、模型覆盖与概率校准，并在执行工具前落实授权。此计算器本身不执行网络、模型、支付或业务行动。

`source_ref`应标识一个可核对的原子观测，而不只是整批报告；同一原子观测不得换别名重计。一份批次回执若含多个测量，宿主仍须核对它们的独立/条件核，不能把相关数据当独立样本相乘。

## 证据等级

本轮完成的是可检验的研究工程阶段：53项SDK/打包回归、9项实验检查、Wishbud/Morrow相关回归（完整数量见[验收记录](05-delivery-and-open-problems.md)）、138项OPC相关回归，以及4次真实根模型调用（1次失败保留、修复后3类场景完成）。不是全仓所有测试，也不是三次市场验证。

尚未证明原创最优算法、自然语言自动形成可靠模型、跨任务泛化、长期净收益或“市场上其他产品无法达到”。没有部署生产、没有独立参与者、没有声称实现万能 AGI。下一步最重要的证据缺口是**开放条件下的模型失配发现和重建**，不是增加更多业务模块。
