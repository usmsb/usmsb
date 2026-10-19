# 查新记录与原创性审计

检索日期：2026-10-18。优先论文原文、作者发布页和正式论文集。以下是定向查新，不是穷尽性系统综述、专利检索或创新性鉴定。

## 1. 查新改变了什么

最初很容易把“多主体协作 + 真实反馈 + 持续学习”当成新技术。但工作流搜索、反思优化、反事实信用分配、跨奖励迁移、缺失结果处理和安全策略改进均有直接前驱。

尤其是 **OPSE 已经对未到达结果作 0/1 悲观／乐观补全**。本轮命题 C 的缺失处理不构成新发明。把这些方法组合并用于 Wishbud，可能产生工程价值，但不能仅凭组合声称科学突破。

## 2. 最接近的数学前驱

| 来源 | 已有内容及本轮核对范围 | 对本研究的约束 |
| --- | --- | --- |
| [Manski, Partial identification with missing data: concepts and findings, 2005](https://doi.org/10.1016/j.ijar.2004.10.006) | 出版页摘要：缺失数据下，资料与额外假设共同决定识别集合 | 无假设不强行点估计不是原创；本轮未完整审读全文 |
| [Lancewicki et al., Stochastic Multi-Armed Bandits with Unrestricted Delay Distributions, ICML 2021](https://proceedings.mlr.press/v139/lancewicki21a.html) | 核对 PDF §4、Algorithm 6：OPSE 将全部派发计入分母，并对缺失结果取上下极值；论文还有遗憾分析 | **直接前驱**。本轮不是完整 OPSE 复现，也没有比它更好的遗憾界 |
| [Tang et al., Stochastic Multi-Armed Bandits with Strongly Reward-Dependent Delays, AISTATS 2024](https://proceedings.mlr.press/v238/tang24c.html) | 正式摘要：结果与延迟紧密相关时的 censored-UCB 与界 | “延迟依赖结果”本身已是研究对象 |
| [Howard et al., Time-uniform, nonparametric, nonasymptotic confidence sequences, Annals of Statistics 2021; arXiv v9 2022](https://arxiv.org/abs/1810.08240v9) | 核对置信序列定义、条件均值与有界序列部分；先读早期 HTML，再核验最终版本元数据 | 任意停止有效的置信界不是原创；本文简单并界通常更宽 |
| [Karampatziakis et al., Off-Policy Confidence Sequences, ICML 2021](https://proceedings.mlr.press/v139/karampatziakis21a.html) | 正式摘要：离策略评价的时间一致置信界 | 有 propensity 的观察数据需专门处理；不能把本文直接均值法冒充离策略估计 |
| [Barreto et al., Successor Features for Transfer in Reinforcement Learning, 2017](https://arxiv.org/abs/1606.05312) | 原论文摘要：分离奖励与动力学，支持奖励变化时迁移 | 保存结果特征、重估新奖励不是原创；本文也没有其策略改进能力 |
| [Jin et al., Reward-Free Exploration for Reinforcement Learning, ICML 2020](https://proceedings.mlr.press/v119/jin20d.html) | 正式摘要：先探索环境，再支持多个奖励下的规划及样本复杂度 | 多目标复用旧数据不是新领域；我们的被动均值比较远弱于通用规划 |
| [Kirschner, Lattimore & Krause, Linear Partial Monitoring, 2023 v2](https://arxiv.org/abs/2302.03683v2) | 原论文摘要：反馈与收益分离、信息导向采样和可观察结构 | 命题 A 属于线性可识别性范畴，不能冠以新的基础定理名称 |
| [Kazerouni et al., Conservative Contextual Linear Bandits, NeurIPS 2017](https://papers.nips.cc/paper_files/paper/2017/hash/bdc4626aa1d1df8e14d80d345b2a442d-Abstract.html) | 正式摘要：相对基线的累计保守约束与遗憾界 | 本文仅签发局部期望增益证据，不提供累计安全保证 |
| [Laroche et al., Safe Policy Improvement with Baseline Bootstrapping, ICML 2019](https://proceedings.mlr.press/v97/laroche19a.html) | 正式摘要：有限离线数据下的基线安全策略改进 | “不确定时回到基线”不是新发明；安全概念须精确定义 |
| [Bianchi et al., Scalable Safe Policy Improvement for Factored Multi-Agent MDPs, ICML 2024](https://proceedings.mlr.press/v235/bianchi24b.html) | 正式摘要：利用分解结构扩大多主体安全策略改进规模 | “安全改进 + 多主体”也已有前驱 |
| [Tucker et al., Bandits with costly reward observations, UAI 2023](https://proceedings.mlr.press/v216/tucker23a.html) | 作者 PDF 初次访问超时，正式论文集摘要可访问：观测成本改变学习代价，并有下界与算法 | “花钱取得反馈”不是新问题；下一步必须与这类方法比较 |
| [Reymond et al., Interactively Learning the User's Utility for Best-Arm Identification in Multi-Objective Multi-Armed Bandits, AAMAS 2024](https://ifaamas.csc.liv.ac.uk/Proceedings/aamas2024/pdfs/p1611.pdf) | 核对摘要及模型：有限试验预算与效用询问预算共同分配 | 不要把目标理解与实验时机的联合选择说成无人研究；也不应把频繁问人变成我们的自治发动机 |

## 3. 与 Agent / LLM 研究的关系

| 来源 | 已有内容 | 本文不应冒领的部分 |
| --- | --- | --- |
| [AFlow, arXiv 2410.10762v4, 2025-04-15](https://arxiv.org/abs/2410.10762v4) | 用执行反馈搜索 Agent 工作流；核对版本与摘要 | 自动生成／优化协作方法 |
| [GEPA, arXiv 2507.19457v2, 2026-02-14](https://arxiv.org/abs/2507.19457v2) | 利用轨迹和语言反思进行提示优化；核对版本与摘要 | 以文字反馈促进迭代学习 |
| [Darwin Gödel Machine, arXiv 2505.22954](https://arxiv.org/abs/2505.22954) | 以实验评估推动 Agent 自修改；核对摘要 | 开放式自改进这一大方向 |
| [The Trace Is the State: Exact Credit Assignment for LLM Agent Teams, arXiv 2603.06859v4, 2026-10-07](https://arxiv.org/abs/2603.06859v4) | 完整共享上下文条件下运行反事实延续；核对摘要与条件描述 | 反事实信用分配。真实世界外部状态未必能从 trace 重放 |
| [Towards a Science of Scaling Agent Systems, arXiv 2512.08296v3](https://arxiv.org/abs/2512.08296v3) | 对多种架构与任务的受控比较；核对摘要 | 不能用“Agent 越多越强”代替实测，亦不能把其结果直接当作我们系统的证据 |

这些工作的实验并未在本轮完整重跑；这里比较研究对象和边界，不作排行榜性能判断。

## 4. 检索覆盖与遗漏

本轮检索关键词包括：

```text
multi objective bandits changing preferences vector rewards delayed feedback
partial identification missing outcomes bounded outcomes
conservative bandits baseline guarantee
time uniform nonparametric confidence sequences bounded observations
reward dependent delays optimistic pessimistic successive elimination
successor features transfer reward free exploration
linear partial monitoring observability row span
multi objective best arm identification costly feedback
bandits costly reward observations missing outcomes
```

也找到需后续全文审读的近期线索：

- [Multi-armed Bandits with Missing Outcome, arXiv 2411.05661](https://arxiv.org/abs/2411.05661)：不同缺失机制下的学习问题。
- [Efficient Multi-objective Prompt Optimization via Pure-exploration Bandits, arXiv 2605.14553](https://arxiv.org/abs/2605.14553)：提示优化与多目标识别的直接交叉。
- [Few-for-Many Best-Arm Identification in Multi-Objective Bandits, arXiv 2610.16840v1, 2026-10-12](https://arxiv.org/abs/2610.16840v1)：以少量选项满足多个目标、共享观测降低试验代价。本轮仅核验摘要，不视为已完成算法比较。

本轮未完成全部引文追踪、专利检索、开放世界干扰因果推断、机制设计及大规模非平稳学习综述。尤其不能从“本轮没找到完全相同的组合”推导出“从未有人做过”。2026 年新预印本的评审状态不一，摘要不能替代完整比较。

## 5. 原创性账本

| 项目 | 当前判定 |
| --- | --- |
| 九要素能否作为统一科学定律 | 尚未建立；概念完整性与科学预测是两回事 |
| 命题 A：目标重评的行空间条件 | 标准线性代数／可识别性应用 |
| 命题 B：缺失结果上下补全 | 部分识别已有思想，OPSE 有直接算法前驱 |
| 命题 C：向量 + 任意时刻 + 缺失 + 明示漂移包络 | 本轮给出自包含组合推导；尚不足以证明非平凡原创 |
| 目标改变时复用结果向量 | 后继特征、多目标学习等已有前驱 |
| AI 主动选择什么反馈值得取得 | 有潜在应用研究空间，但已有昂贵反馈与主动学习前驱 |
| 开放、不可信、目标变化的合作中更低成本的可靠学习 | **待攻克研究命题**；新算法、界与实证优势均未建立 |

## 6. 为什么仍值得做

查新否定的是轻率的“原创”宣称，不是否定问题价值。真实系统常把旧分数、选择性回传和模型反思混为可靠经验。把这些问题显式暴露，是进行真正研究的起点。

科学上要形成壁垒，必须在一个明确条件族中给出超过现有方法的可识别性、样本效率、迁移或决策保证。技术上必须让 AI 能在真实开放任务中使用它，且总成本更低。商业上必须有客户愿意为持续净收益付费。这三项不能相互替代。
