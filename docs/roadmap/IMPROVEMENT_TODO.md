# IMPROVEMENT_TODO.md

---

## TODO 清单

### 🔥 P0 - 让系统"活起来"

- [x] **P0-1**: 规则层行为倾向 + 指数衰减（已完成 a0cdb13）
  - ✅ ActionTendency 枚举（11种行为倾向）
  - ✅ EMOTION_TENDENCY_MAP 加权矩阵
  - ✅ EMOTION_HALF_LIVES 半衰期（10s~300s）
  - ✅ 指数衰减 effective_intensity
  - ✅ MoodState (VAD) 慢衰减背景
  - ✅ EmotionalGoalModifier → 目标难度/推理策略/协作/时间分配
  - ✅ feel() 无递归，规则层 <1ms
  - ⚠️ LLM 层待实现（触发条件：强度>0.75 || >2种情绪无主导 || 情绪目标冲突）

- [x] **P0-2**: 自主循环引擎（已完成 8bbaf5c）
  - ✅ AutonomousLoop：start/stop/pause/resume + 完整生命周期
  - ✅ CycleResult：每次循环报告
  - ✅ 目标生成：purpose_generator > 情绪池 > None
  - ✅ 动机衰减 + 情绪反馈闭环
  - ⚠️ 价值观演化（ValueSeedEngine.evolve）未接入

- [x] **P0-3**: 情绪驱动目标参数（已完成 8bbaf5c + a0cdb13）
  - ✅ EmotionalGoalSelector：注入情绪到目标生成
  - ✅ difficulty_multiplier：情绪影响目标难度
  - ✅ reasoning_strategy：情绪影响推理方式
  - ✅ collaboration_adjustment：情绪影响协作倾向
  - ✅ AutonomousLoop 中情绪→动机→目标→执行→情绪 完整闭环

### 🔶 P1 - 让智能替代代码

- [x] **P1-1**: LLM驱动目标优先级（已完成 efa6107）
  - ✅ LLMGoalPrioritizer：AgentState + GoalCandidate → PriorityResult
  - ✅ Fallback规则：难度匹配 + 协作匹配 + 情绪匹配 + 成功率加成
  - ✅ 集成到AutonomousLoop：每轮3候选 → LLM排序 → 选最优
  - ⚠️ LLM接入需真实API Key（当前用fallback）

- [x] **P1-2**: 元认知闭环v2（已完成 f34d540）
  - ✅ TaskScenario分类：10种场景 + 场景别名映射
  - ✅ LearningStrategy.scene_history：场景维度成功率
  - ✅ get_best_for_context()：综合场景历史+全局成功率选最优
  - ✅ start_reasoning()：自动根据场景推荐策略
  - ✅ finish_reasoning()：记录"场景+策略→结果"到历史

- [x] **P1-3**: Gene Capsule LLM adapter（已完成 a0ecb20）
  - ✅ PurposeGenerator 新增 gene_capsule_adapter 参数
  - ✅ generate_purpose(task_context)：同步入口，自动判断是否用 RAG
  - ✅ _generate_purpose_with_experiences()：RAG检索 → 经验注入 → LLM生成
  - ✅ AutonomousLoop 集成：传入情绪上下文用于检索

- [x] **P1-4**: Pre-match Negotiation（已完成 827fc9b）
  - ✅ AgentRecommendation 新增 pre_negotiation_session_id
  - ✅ start_pre_negotiation()：启动预协商会话
  - ✅ recommend_for_demand()：auto_pre_negotiate 为 top-3 启动预协商
  - ✅ graceful degradation：无 service 时正确降级

### 🔷 P2 - 更长期

- [ ] **P2-1**: 他心智推断升级
  - 从统计计数 → LLM 推断

- [ ] **P2-2**: 价值观动态演化
  - `ValueSeedEngine.evolve()` 真正被调用
  - 接入真实反馈信号

- [ ] **P2-3**: L5 GlobalWorkspace + AttentionBidding
  - 多个 Agent 注意力竞价

---

## 执行顺序

```
阶段1（P0）→ 阶段2（P1）→ 阶段3（P2）
```

每个阶段开始前讨论，结束后复盘。

