---
type: experiment
node_id: experiment:toc-r2-contract-resample
title: "TOC-Bench R2 contract fix and immutable resample"
stage: completed
outcome: failed
tags: ["phase0", "toc-bench", "ledger-core", "real-video", "contract-gate"]
added: 2026-08-06T18:30:00+08:00
---

# TOC-Bench R2 contract fix and immutable resample

## 目的

检验在修复 event presupposition、visibility、identity certificate、endpoint-aware sampling 和 answer leakage 后，TOC-Bench 的全新真实视频样本能否稳定支撑 T-STEP-v0 局部 object-state → complete-event ledger-core。

这不是模型性能实验，也不检验 episode/story/intent。R2 期间 evaluator-only 答案、GPU、训练和样本替换全部锁定。

## 冻结合同

- EventPresupposition：`observed / unsupported / ambiguous / outside_clip / not_required`；非 `observed` 的事件依赖查询不得执行。
- Visibility：`fully_visible / partly_hidden / fully_hidden / out_of_frame / unknown` 按可见比例、遮挡因和画面边界证据区分。
- Identity：reappearance 必须有 pre/post anchors、同类 competitor inventory、持久对象依据和 `ambiguity=none`。
- Sampling：5-frame coarse → 24-frame endpoint-inclusive dense → question-aware targeted → manual contract review。
- R2 roster：10 个从未进入 R1 candidate-30 的视频；配额固定为 event ordering 3、cross-object order 2、reappearance identity 3、visibility/disappearance 2；禁止替换。
- Pass gate：overall ≥8/10，event/order ≥4/5，identity/visibility ≥4/5，三项必须同时通过。

## 执行审计

- 原始 roster hash：`c4d40d3e7a5cf1027ecedbc2165c680bf4af677601a64f971be874c381041fbf`。
- 上游 TOC-Bench 代码证明 ordering `events[].label/event_text` 是题面选项，`correct_order` 才是 evaluator 字段；因此以 `R2_PRESEAL_AMENDMENT_001` 只补齐三个排序题的这两个字段，样本 ID、顺序和选择均未改变。
- 有效 roster canonical hash：`e1bb008745aae4ccf30b57402764abfaf464a63a74971ce0e0e0872e8a18adfb`。
- 10/10 视频成功物化和解码；240 张 dense 帧、13 个 targeted windows、1108 张 targeted 帧。
- 首轮 render 暴露 OpenCV `CAP_PROP_POS_MSEC` 在 seek 后、decode 前返回秒值的实现错误；修复为 decode 后读取，并加入 monotonic + decoder/index drift validation，最终 sampler 为 `tstep-four-stage-sampler-v0.2.2`。
- evaluator artifact 未访问；GPU/训练未启动；R2 未换样本。

## 结果

| cohort | 通过 | 门槛 | 结果 |
|---|---:|---:|---|
| Overall | 6/10 | ≥8/10 | FAIL |
| Event/order sensitive | 3/5 | ≥4/5 | FAIL |
| Identity/visibility sensitive | 3/5 | ≥4/5 | FAIL |

| 视频 | 维度 | 判定 | 核心证据或 blocker |
|---|---|---|---|
| `charades_R5WMI` | event ordering | ACCEPT | partly hidden → fully hidden → reappears 三个边界可分 |
| `charades_Y50QF` | event ordering | ACCEPT | leaves/enters/fully hidden/reappears 四事件均观察到 |
| `perception_test_video_422` | event ordering | BLOCK | red apple 仅部分遮挡，未出现 fully hidden |
| `charades_11TTU` | cross-object order | ACCEPT | chair partial-hide 先于 bouquet full-hide，完成区间可分 |
| `charades_LV24Z` | cross-object order | BLOCK | floor toys 从片首已在画面，未观察到 required entry |
| `charades_J8KPE` | reappearance identity | ACCEPT | 固定铰链 open door 有完整 gap、post anchor、唯一几何依据 |
| `charades_OEIR9` | reappearance identity | BLOCK | black pot 始终至少部分可见，没有完整消失—回现 |
| `perception_test_video_3937` | reappearance identity | BLOCK | red book 无 post-return，且存在多个同类书竞争实例 |
| `charades_PKEZI` | disappearance | ACCEPT | flower vase 连续轨迹穿越左画面边界 |
| `perception_test_video_5280` | disappearance | ACCEPT | 手持 knife 连续轨迹穿越左画面边界 |

完整逐样本边界与证据见 [`toc_phase0_r2_manual_review.json`](../../data/phase0/toc_phase0_r2_manual_review.json)，机器校验结果见 [`toc_phase0_r2_gate_result.json`](../../data/phase0/toc_phase0_r2_gate_result.json)。

## 结论

`R2_GATE_FAILED`。

失败集中在 TOC-Bench 自动事件前提与严格 operational semantics 的错配，而不是代码无法表达这些语义：部分遮挡被写成 fully hidden/reappearance、片首已存在对象被写成 enters-frame、generic object label 无法通过 competitor-aware identity certificate。

因此：

1. 保留 v0.2 ledger-core 合同、执行器、验证器和负例测试；
2. TOC-Bench 保留为局部对象时序诊断与负例来源，不再作为严格 ledger-core 的唯一监督源；
3. 不做 R3 同源补抽，不用换样本掩盖系统性错配；
4. 继续锁定 GPU、baseline 和 corruption；
5. 下一步转向真实基础语料的 annotation-intersection 与最小人工对齐：优先核验 Ego4D family，CaptainCook4D 作为程序错误/纠错备选，TOC-Bench 只保留外部诊断角色。

## 不支持的过度结论

- 不能据此否定最终“多粒度语义自洽与跨层纠错”目标；本实验只检验局部状态—事件核心。
- 不能说 ledger-core 方法已有效；尚未获准进入模型性能实验。
- 不能把 6/10 当模型准确率；它是严格数据可标注性/合同兼容率。
