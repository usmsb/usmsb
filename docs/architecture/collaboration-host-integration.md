# 外部宿主接入、协商与治理迁移验收

日期：2026-09-29。对应 core `0.9.0a2`；本地工程实现，不是线上切换公告。原始待办和验收记录见 [交付报告](./open-collaboration-delivery.md)，实验工具见 [故障与规模实验](./collaboration-experiments.md)。

## 1. 职责边界

外部 Agent 决定目标、编排、接受工作、执行和复核；SDK 不启动模型或决定分工。宿主提供身份、授权、可见性、凭据与内容存储。内核只约束协议、版本、承诺、记录和回执。USMSB 的可修订目标仍是基本机制，既有承诺不能被新目标追溯覆盖。

新增 `autonomy.interop` 是可嵌入任意宿主的严格边界；没有开箱即用的公网服务器、默认管理员、公共测试凭据或通用“信任所有证明”。原 `examples/open_collaboration/host.py` 仍然只是明确标记的回环测试示例，不要拿其固定 token 部署生产。

| 边界 | 已实现 | 宿主仍需提供 |
|---|---|---|
| 身份 | `TokenAuthenticator` 核验宿主预置的 token 哈希及有效期；或替换成可信认证回调 | 高熵凭据、安全分发/撤销、TLS、真实主体登记与 controller 关系核实 |
| 协议 | exact schema/功能/Profile 内容协商；命令携带 agreement hash；未知必需语义拒绝 | 验证服务器身份，检查完整规则内容；摘要不是签名 |
| 交付 | 流式检查制品字节数与 SHA256；默认上限 16 MiB；失败不写回执 | 仅打开获授权且不可变的对象、内容/恶意代码检查、超时、路径与 SSRF 防护 |
| 证据 | 修订/复核/采用须经宿主 evidence 回调严格返回 `True` | 验证证据来源、签名/有效期/范围、实际内容与业务标准；不能直接相信客户端 `verified=true` |
| 重试 | 认证后的同 actor、command、operation、payload 精确查原回执 | unknown 时保留操作 ID 对账；不给支付或其他外部效果自动重试保证 |
| 可见性 | 接入层不暴露 journal 全量读取、事件与配置 | 自己的租户过滤、最小读取权、脱敏错误、配额和请求长度限制 |

多个 token 或 controller 字符串不能证明由不同人/组织独立控制。制品摘要匹配只证明读取字节与描述符一致，不证明事实正确、作品合法或目标已实现。签名同样不能替代内容验收。

## 2. 嵌入宿主

完整 SDK 导入 `usmsb_sdk.autonomy.interop`；独立 wheel 导入 `usmsb_core.autonomy.interop`。默认均无新增第三方运行依赖。

```python
from usmsb_core.autonomy.interop import AuthenticatedCollaborationHost, TokenAuthenticator

# journal 已用经过宿主核实的 principals/controller 和 Profile 打开。
# token_hash_entries 只来自私有配置，不接受客户端提供的身份映射。
authenticate = TokenAuthenticator(token_hash_entries)
host = AuthenticatedCollaborationHost(
    journal,
    authenticate=authenticate,
    resolve_artifact=open_authorized_immutable_object,
    verify_evidence=verify_authenticated_scoped_evidence,
    max_artifact_bytes=16 * 1024 * 1024,
)
offer = host.offer()
receipt = host.apply(credential, hello, envelope)
```

这是嵌入形状，不是含凭据的可直接部署脚本。宿主必须实现并审查两个回调：

- `resolve_artifact(actor, descriptor)` 返回二进制流的上下文管理器；它负责访问权限及 URI 到对象的可信映射，不能任意访问客户端指定 URL/文件。网关不会自己下载 URI，读出的字节也不会执行。
- `verify_evidence(actor, operation, payload)` 核实此次命令对应的真实证据，精确返回 `True` 才放行；`1`、字符串、None、错误和未知均拒绝。回调获得副本，不能通过修改已验证对象调换命令。它本身由可信宿主安装，不能配置成客户端上传的代码。

token 配置为 `{sha256(token): {actor, not_before, expires_at}}`，时间为 Unix 整数秒。使用至少 32 字节安全随机源生成 token；不要使用密码、用户名或本文示例值。该认证器只适合受控宿主的凭据验证，不是跨组织身份基础设施。与 OIDC/mTLS 等整合时用其验证后的 actor 映射替换回调，不能把未验证 JWT claims 直接传入 journal。

原始 token 只存在于传输和认证回调，journal 不记录它。传输层必须禁止日志打印请求认证头，且不能将 Python 异常原文/内部 ID 是否存在直接暴露给未授权客户端。TLS、限流、请求体上限和解析前拒绝重复 JSON key 由实际 HTTP/消息入口实现。

## 3. 版本协商与 JSON 接入

`host.offer()` 返回 `usmsb.collaboration-offer.v1`：host ID、配置摘要、可用协议、功能及完整公开 Profile；不泄露主体目录、权限矩阵或凭据。

客户端阅读规则后构造 `usmsb.collaboration-hello.v1`：

```json
{
  "schema": "usmsb.collaboration-hello.v1",
  "protocols": ["usmsb.collaboration-command.v1"],
  "profile": {
    "id": "usmsb:open-collaboration",
    "version": 1,
    "sha256": "由实际完整Profile按journal.digest规则计算的摘要"
  },
  "required_features": ["durable-idempotency", "evidence-gated", "frozen-consent", "goal-revision-cas"]
}
```

`negotiate(offer, hello)` 产生 agreement。双方须按相同规范化算法计算：JSON 只接受有界整数/字符串/布尔/数组/对象，无浮点；排序键、无多余空白、ASCII escaping（与 `journal.canonical` 相同），对 UTF-8 字节做 SHA256。异语言实现必须特别处理 Unicode escaping，不能对任意格式化 JSON 直接求 hash。配置摘要采用 scope 的既有编码，由宿主产生；客户端将它作为 offer 的不透明字段绑定，不自行重建私有配置。

命令 envelope 严格包含 `schema`、`agreement_hash`、`command_id`、`operation`、`payload`。不能携带 actor/controller 来代替认证。网关重新计算协议协商，拒绝不兼容 major、缺少的必需功能、相同 Profile ID/版本但不同内容、伪造 agreement 和未协商的规则集。当前唯一命令 schema 为 v1；这不是自动转换未知未来协议的服务。

新增 `journal.receipt(actor, command_id, operation, payload)` 供宿主做精确、鉴权后的幂等查询。成功回执优先于重复取证，避免首次已提交、证据后来过期时产生第二个操作。凭据过期/撤销仍拒绝访问；知道 command ID 并不获得他人的回执。

## 4. 显式、仅增量的治理迁移

`autonomy.migration` 提供 `configuration_hash`、`migrate_journal`、`migration_events`。所有 API 为宿主管理接口，不是公开客户端命令。

允许：追加主体（已存在主体完全不变）、追加不同 ID 的 Profile（所有旧规则完整保留）、增加持久命令预算。拒绝：更换宿主 ID、删除/改名旧主体、改变 controller 或旧权限、覆写相同 Profile ID 的内容/版本、降低预算、无变化的迁移。撤权、主体转让、同 ID 规则换版、取消/退款/争议需要单独设计，不能包装成增量迁移绕过存量义务。

```python
from usmsb_core.autonomy.migration import configuration_hash, migrate_journal

old = journal.configuration()  # 宿主专用；返回深拷贝，不公开全部目录。
audit = migrate_journal(
    journal,
    migration_id=case_id,
    expected_config_hash=configuration_hash(old),
    new_configuration=approved_additive_configuration,
    reason=reason,
    evidence_ids=approval_evidence_ids,
    verify_approval=verify_controller_approval,
    backup_path=new_private_backup_path,
)
```

每个旧 controller 都必须对准确的迁移 ID、旧/新配置 hash、reason、evidence IDs 及参与方集合批准。`verify_controller_approval(controller, request)` 接收独立副本，只接受严格 True；不带内置“自动批准”。它由宿主核验真实身份和批准证据，在写锁内执行，必须迅速结束且不重入 journal。

迁移先锁住写入，通过独立只读 SQLite 连接做一致性 backup、完整性检查和 fsync，再将配置 CAS 与审计追加一并提交。备份目标必须是全新文件，已有文件、数据库本身及 sidecar 均不能覆盖。失败可能留下备份文件用于审查，不自动删除或复用。Windows 私有 ACL 与目录完整性由宿主管理。

持有旧配置的 a2 实例会被配置检查阻止继续写入和查询回执，需用批准配置新开 journal。**迁移前必须停写并停止 a1 或其他没有围栏检查的旧二进制**；SDK 检查不是阻挡任意旧程序/raw SQL 的数据库防火墙。已接受条款、旧事件、回执、目标版本和影响快照不改写。审计读取为独立分页序号；公开审计前需脱敏备份路径和主体配置。恢复旧备份只是技术恢复点，不撤销外部已经发生的交付、支付或披露。

## 5. 真正上线前的人类输入与验收

以下目前没有可核验输入，**不标成已完成**：

1. 一个允许测试的真实外部宿主（地址、身份系统、凭据文件位置、可见性政策）；明确希望接 Wishbud/OPC 还是第三方。当前新增机制可嵌入，但未擅自改生产。
2. 至少另一位真实独立控制者参与；若使用默认 independent Profile，则请求方、提供方之外还需独立复核主体。不能由一个操作者持有全部角色凭据却宣称多组织验收。
3. 真实项目的目标、成功标准、成果使用方和证据来源。各方用自己的凭据接受冻结条款；修订、拒绝、重连、复核、采用都保存原始回执与制品摘要，并由参与方核对。
4. 真 IAP/支付：明确证明类型与生产验证器、商户/轨道、授权交易范围、退款争议和对账责任。当前没有商户配置，故不发起真实收付款，不启用占位 ZK。技术账本与测试 token 都不是资金或隐私证明。
5. 长期演化：先约定观察周期、对照、失败阈值、资源上限、真实价值指标与停止条件，再进行持久实验。短时脚本压力验证不是长期智能涌现。

生产切换另需停写/备份、在途 unknown 操作对账、回滚演练与批准。协议内核的完善不自动授权对外推广、内容披露、代签承诺或改变线上模型预算。
