---
updated: 2026-07-28
status: active
scope: TOC-Bench 真实视频 Phase 0 首轮筛选、边界复核、gate 结果与聚焦实现评审触发条件
out-of-scope: 不宣称 Phase 0 通过，不报告模型性能，不用 QA gold 反推 ledger，不启动 GPU 或训练
---

# T-STEP-v0 Phase 0 真实视频 Gate Report

## 结论

**CONDITIONAL，且首轮 8/10 gate 未通过。**

30 个分层 TOC-Bench 真实视频全部本地解码成功；答案盲粗筛、10 条 dense review、5 条补位 review 与两轮 targeted boundary replay 共形成 990 帧可复核证据。最终严格通过 7/10，低于预注册的 8/10，因此不得进入 GPU、baseline 性能比较或 corruption 实验。当前正确动作是一次聚焦实现评审，先关闭 event presupposition、visibility operator、identity anchor 和 boundary sampling 四个 blocker。

全流程中，筛选与可标注性复核者未访问 `evaluator_only` gold。

## 实验规模

| 阶段 | 数量 | 结果 |
|---|---:|---|
| 分层候选 | 30 个独立视频 | 6 个 TOC 维度均覆盖 |
| 本地解码 | 30/30 | 全部成功 |
| 5 帧答案盲粗筛 | 150 帧 | likely 15 / uncertain 12 / unsuitable 3 |
| 首批 deep-10 | 10 × 24 帧 | 初始 accept 5 / backup 4 / reject 1 |
| 同维度补位 | 5 × 24 帧 | 新增 1 个严格 accept |
| targeted replay round 1 | 324 帧 | 解决末端与交叉对象边界 |
| identity replay round 2 | 156 帧 | 证实一条重现预设失败，另一条缺 pre-gap anchor |
| 最终 gate | 10 条 | accept 7 / blocked 3；要求 accept ≥ 8 |

## 最终 10 条 roster

| 维度 | 样本 | 裁决 | 关键证据或 blocker |
|---|---|---|---|
| conditional_state | `charades_LCEM0` | accept | relevant return bracket 8.7–10.0 s |
| conditional_state | `perception_test_video_1716` | accept | relevant return bracket 12.0–12.8 s |
| relative_spatial_change | `charades_MCMTH` | accept | 全视频背景对象可稳定比较 |
| reappear_or_disappear | `charades_X95FK` | accept | 末端边界收窄至 27.09–27.39 s |
| reappear_identity | `perception_test_video_7414` | accept | 单一药瓶、连续轨迹与两处 occlusion/return |
| reappear_identity | `charades_GL7E6` | backup | 9.6–10.0 s 后红杯清晰，但缺可靠 pre-gap identity anchor |
| event_ordering | `charades_GH3D1` | backup | 两个黑锅与人物遮挡使 partial/full boundary 不稳定 |
| event_ordering | `charades_SX07Q` | backup | leaves-frame 与 disappears-for-good 合并为同一末端事件 |
| cross_object_order | `charades_6G96Q` | accept | 两对象边界可分，但必须冻结 partly-hidden 定义 |
| cross_object_order | `perception_test_video_3967` | accept | outlet 2.17–3.23 s；pen 5.40–6.50 s |

## 已确认的反例

- `charades_JFU3J`：红帽至 31.10 s 可见，31.23 s 后直到视频结束均未再出现；问题预设的 reappearance 无视觉证据。
- `charades_K7PVL`：0.0–2.0 s opening sweep 仍找不到 window-entry comparator。
- `perception_test_video_7284`：tomato 在 frame 0 已经出现，first-show boundary 不可观察。
- `perception_test_video_9057`：towel 与多个白色浴室物体混淆。
- `charades_IZTHW`：多个 framed pictures，且必需 terminal events 未发生。

这些反例说明 answer-level QA 不能直接当作 transition existence certificate。

## 四个必须关闭的 blocker

1. **Event presupposition failure**

   Query 必须显式记录 trigger/event 是否 `observed / unsupported / ambiguous / outside_clip`。未验证事件不得生成 `EventOperator`，也不得进入 TransitionF1、event ordering 或 corruption。

2. **Visibility operator overlap**

   `partly_hidden`、`fully_hidden`、`leaves_frame`、`disappears_for_good` 目前不是互斥、可执行的状态/事件定义；尤其 terminal disappearance 可能与 leaves-frame 同时发生。必须决定观测定义、边界容差和 interval overlap 的 metric applicability。

3. **Identity anchor gap**

   “单一红色物体”不等于 persistent identity。身份重现至少需要 pre-gap anchor、post-gap anchor、竞争实例记录与 identity scope；缺一项就必须 `UNKNOWN/INAPPLICABLE`。

4. **Boundary sampling policy**

   interior-only uniform sampling 会漏掉视频开头和结尾事件。脚本已改为包含 frame 0 与最后一帧；正式流程还需冻结 `5-frame coarse → 24-frame endpoint-inclusive dense → blocker-targeted replay` 的升级规则。

## 当前实现状态

- 已拆分 `StateInterval`、`TransitionBoundary`、`EventOperator`、`StateRecord`。
- 已加入 provenance、identity scope、answer blindness、orphan record、operator signature、metric applicability validator。
- query 缺失事实返回 `UNKNOWN`，不再默认为 false。
- interval 到 operator 必须经过完整 `ConversionCertificate`。
- 已加入 endpoint-inclusive uniform sampler 与 targeted-window renderer。
- 全部工作仍是 CPU/data/schema 实验；没有启动 GPU 或训练。

## 下一步裁决

聚焦实现评审只需回答：

1. 是否在 `QuerySpec` 增加 event-presupposition 状态，并使其成为 executor/metric/corruption 的统一 gate？
2. visibility 应作为连续观测量加阈值，还是离散人工标签？`leaves_frame` 与 `disappears_for_good` 能否同时间提交？
3. identity query 的最小双端 anchor 与竞争实例字段是什么？
4. 7/10 后应补抽 event-order/identity 样本重新达到 8/10，还是已足以判定 TOC 子维度不适合作为 ledger 主证据？

在以上问题裁决前，不扩标、不运行 baseline、不构造 corruption。
