# 通用方案不是执行回执：SDK 局部整改

日期：2026-10-19。范围仅为 SDK 通用执行返回及两个直接调用方；不修改 Wishbud/Morrow，不新增行业分类器、执行权限或业务流程。

## 行为目标与起点

让主体与调用方能够继续利用候选方案，同时不把模型对拟议行动的描述记成已执行成功或已实现目标。行动与方法仍由主体决定，代码只区分返回证据的性质。

开始时 usmsb 工作区干净，分支 `codex/usmsb-collaboration-evidence-research-20261018`，HEAD `347dd93d1d0b5eb8852b9210420c61fa93bfe2a6`。本轮未提交、推送、部署或运行真实模型。

原 generic 分支只调用 `generate_text`，却要求模型返回 `steps_executed`、`status: success/failure`，并在生成文本后无条件返回 `ActionResultStatus.SUCCESS`。这不是执行工具的结果。另一个直接调用方 `GoalActionOutcomeLoop` 把所有正常返回均包装成 `success=True`；仅更改 generic 的返回状态不足以修正该调用链。

## 返回契约及兼容范围

`LLMExecutionService.execute` 的 `code`、`tool_call` 显式分派保持原行为。其他类型（包括缺省、未知类型）只生成候选方案，不按名称推断行业，不寻找同名工具自动执行，也不执行方案中的代码。

generic 有非空文本返回时：

| 字段 | 含义 |
| --- | --- |
| `status = PENDING` | 请求的行动未执行；不是排队任务，也没有自动续执行 |
| `data.execution_plan` | 保留原始模型文本，兼容已有方案读取方；其中的自报成功不是执行证据 |
| `data.execution_result = None` | 本次没有行动执行结果 |
| `data.steps_executed = []` | 本分支没有执行任何拟议步骤 |
| `metadata.result_kind = "plan"` | 返回的是候选方案 |
| `metadata.execution_status = "not_executed"` | 确定性的执行边界，不由模型生成字段覆盖 |

提示中的字段改为 `proposed_steps`、`expected_result`、`requirements`。不依赖提示服从来保证返回状态：即使原文仍自称执行成功，外层仍为未执行。空白或非文本返回、生成异常均返回 FAILURE；服务不自动重试。`execution_time` 仍是服务调用耗时，不是现实行动用时。

需要只读取方案的旧调用方应读取 `execution_plan` 并检查其性质，不能继续要求 generic 返回 SUCCESS。实际执行必须由已获授权的调用方另行选择现有执行通路；PENDING 不要求人逐次批准，也不自动授予主体权限。

## 直接调用方

- `GoalActionOutcomeLoop` 保留 `success`、`outcome` 字段，新增执行 `status`。SDK `ActionResult` 的状态被保留；旧字典结果支持明确的 `status` 或布尔 `success`，没有状态的任意返回值记为 unknown，不再推定成功。原始 outcome 不改写。执行器的显式成功仍只是其声明，不自动成为独立验证或现实目标达成证明。
- 对本次 `evaluate_action_outcome` 的达成断言，未成功的执行不能仅凭评估器的一句 `goal_achieved=True` 自动完成目标；原评估声明保留在 `reported_goal_achieved`，并记录阻止完成的原因。pending、partial、unknown 不再混入 failed 计数。
- pending 时循环返回 PAUSED，不在同一 run 内重复生成方案。调用方/主体决定后续行动；本次未增加后台轮询、自动重放或人工审批要求。
- `InformationDecisionControlEngine` 保留 `executed`、`outcome`，补充状态、错误和元数据。`execution_results` 收录全部服务返回，`actions_executed` 只收录明确成功项。旧调用方若需查看所有返回，应迁移到 `execution_results`；不能把该列表长度当作现实效果数。

上述阻断只约束本次行动评估返回的达成断言，不是 USMSB 对目标成因的限制。环境变化或其他主体的行动同样可以使目标达成，不应要求本主体重做一次行动才能承认这些效果。当前接口没有独立表达这类证据来源与归因的契约；若旧适配器把外部状态判定混入同一个 `goal_achieved` 布尔值，在本次执行未成功时也会被阻断，这是兼容限制，而不是外部效果不存在的证明。调用方需区分独立目标状态证据与本次执行归因；本切片未新增外部证据处理通路、权限或引擎，也不声称已验证这类目标状态更新。

检索 SDK `src`、`tests`、`examples` 的类名、工厂与 `execution_service.execute` 引用，发现上述两个直接执行消费者；其他同名 ExecutionService/ExecutionResult 属于不同模块，不在本切片内修改。`core.ActionResult` 与 `universal_actions.ActionResult` 原有不同导出身份保持不变。

## 工程验证与未达项

新增 `tests/unit/test_execution_evidence.py`，全部使用确定性适配器/工具替身，不调用真实模型、网络或生产执行器。覆盖缺省及未知类型、模型自报成功、原文保留、空响应/异常、显式 code/tool 分派、同步/异步测试工具、两个调用方的状态与计数、评估误称完成、pending 不重复生成，以及旧字典结果兼容。

测试首次启动时，本机 Python 3.14 环境缺少 pytest-asyncio，异步用例主体未运行；随后使用已安装的 AnyIO asyncio 后端，不安装依赖、不改全局测试配置。既有 asyncio 配置警告与 `asyncio.iscoroutinefunction` 弃用警告保留，不借此扩展整改范围。

实际运行：仓库 `.venv/Scripts/python.exe -E -B -m pytest`（Python 3.14.7），禁用 pytest 缓存，以下合计 **84 passed**：

- `tests/unit/test_execution_evidence.py`：53 项。
- `tests/unit/test_elements.py`：26 项。
- `tests/portable/test_core_distribution.py` 中 `test_sdk_elements_and_contracts_import_without_dependencies`、`test_sdk_core_preserves_aliases_interfaces_action_result_and_star_import`、`test_sdk_optional_exports_load_original_modules_only_on_access`、`test_lazy_import_errors_are_not_hidden_and_unknown_attributes_remain_absent`：参数化后共 5 项。

这不是全仓回归或包发布验证。现有环境没有 Ruff，未安装或声称完成 Ruff 检查。

未证明：模型会正确规划、现实行动成功、业务效果或独立生态协作。已有显式代码分支仍是本机子进程而非安全沙箱；授权必须由宿主控制，本次未调用或扩权。工具返回正常不等于其业务结果成功，本次未设计通用业务验收器。旧的决策/评估服务接口差异与其他模拟服务未在本切片中统一；不能据此宣布整个 SDK 已完成端到端兼容或证据治理。

本轮修复的是方案与执行证据混淆及其直接传播，没有替主体选择行业方法，也没有给原本不存在的能力签发执行成功。
