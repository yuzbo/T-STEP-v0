---
updated: 2026-07-28
status: active
scope: Phase 0 observation、boundary、operator、record 的合法转换和拒绝规则
out-of-scope: 不定义开放世界因果本体，不允许用 QA gold answer 补写 ledger，不把 metadata-only candidate 当视觉 ground truth
---

# T-STEP-v0 Phase 0 Conversion Policy

## 1. 四类对象

| 类型 | 权威含义 | 禁止承担的含义 |
|---|---|---|
| `StateInterval` | 对象在 `[start_ms,end_ms)` 上的观察状态断言 | 原因、作用者、可执行 effect |
| `TransitionBoundary` | onset/completion/change-point 的时间约束 | operator type、precondition、effect |
| `EventOperator` | 经过验证、可在 ledger 上执行的 typed transition | 未验证的时间区间或答案反推 |
| `StateRecord` | initial、observed 或 operator-derived 的 materialized state | 无 producer 的孤立状态 |

新 schema 使用 PTS 毫秒；旧 toy harness 的秒字段只保留为兼容入口。

## 2. 合法转换

### StateInterval → observed StateRecord

允许，但必须：

- entity binding、state key、typed value 明确；
- 半开时间区间合法；
- `record_kind=observed`；
- producer 指向 observation artifact，而不是伪造 EventOperator。

### Interval triplet → StateChangeCandidate

允许生成 candidate，但必须：

- 三段属于同一 entity 和同一 state key；
- before/end value 类型兼容且不同；
- transitioning interval 位于 before 与 after 之间；
- candidate 标记为 `metadata_only` 或 `unverified`。

### StateChangeCandidate → EventOperator

只有完整 `ConversionCertificate` 才允许：

- same persistent object；
- same state key；
- explicit before/after；
- explicit operator type；
- affected participant 已核验；
- effect commit boundary 已核验；
- reviewer 和 provenance 已记录。

agent、instrument、intent 等角色是可选的；缺少这些角色不得从类别文本或时间邻接中猜测。

### EventOperator + prior StateRecords → derived StateRecord

这是唯一标准 executable 路径：

1. 校验 operator signature；
2. 校验 preconditions；
3. 在 completion boundary 提交 effects；
4. 生成带 `producer=event_id` 的 derived records；
5. query 返回读取 record 与 applied event 的 proof trace。

## 3. 强制拒绝

- 直接 `StateInterval → EventOperator`；
- `StateRecord difference → named/causal EventOperator`；
- semantic subject label 通过 persistent-ID validator；
- gold/correct/GT answer 进入 ledger builder、query compiler 或 executor；
- 非法/空/倒序时间区间；
- derived record 没有存在的 producer event；
- 缺失事实默认为 `false`；必须返回 `UNKNOWN`；
- metadata-only VidOSC candidate 进入 visual grounding 指标；
- 无 proof-required event 的样本计算 TransitionF1；
- identity-independent query 使用 object-ID swap 指标。

## 4. 当前兼容边界

旧 `EventOperator(event_id,t_start,t_end,op_type,object_id,variable,before,after)` 构造仍可用于 toy smoke；构造后会显式适配成 participants、preconditions 和 effects。新 deep annotation 不得依赖该宽松入口，必须使用独立 typed objects 和 validator。
