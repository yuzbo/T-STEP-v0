# GO_CONTRACT_FIX_AND_RESAMPLE 结论吸收与执行记录

日期：2026-08-06
来源：用户提供的 Pro 评审 `GO_CONTRACT_FIX_AND_RESAMPLE`

## 判断

我认同评审的核心裁决与执行路线：T-STEP-v0 只保留为最终层次模型中的局部 object-state → complete-event executable core；R1 的 7/10 必须按失败记录；先修合同，再做全新、不可替换、answer-blind 的 R2；通过三重 gate 前禁止 GPU。

两条实现边界必须同时保留：

1. `CorrectionRecord` 在当前阶段只是未来跨层纠错的接口与审计结构，不把 Phase 0 膨胀为 episode/story/intent 系统。
2. evaluator artifact 与 ledger builder 物理分离；题面可以包含公开 prompt options，但任何 correct value 不得进入 builder/compiler/executor。

## 已落实的合同

- D1：EventPresupposition 五态与 query execution/metric gate。
- D2：visibility operational rubric；`leaves_frame` 是可执行边界，`disappears_for_good` 只允许 terminal predicate。
- D3：IdentityCertificate、pre/post anchors、competitor inventory、manual provenance；object swap 只改 identity binding。
- D4：5 coarse → 24 endpoint-inclusive dense → question-aware targeted → deep review，并记录 frame/PTS/version。
- D5：R2 精确配额 3/2/3/2、全新 10 视频、禁止替换、hash sealing。
- D6：immutable observation / mutable hypothesis 与最小 CorrectionRecord 接口。
- D7：修复 unverified execution、failed-precondition event 污染、answer leakage、predicted=gold、blind drop-last、无 gold 指标默认满分等问题。

## 额外发现与修复

1. 上游 TOC-Bench 代码确认 ordering `events` 是题面选项，不是答案；只恢复 `label/event_text`，并以 versioned amendment 保留前后 hash。
2. OpenCV seek 后在 decode 前读取 `CAP_PROP_POS_MSEC` 会在当前媒体上返回秒值，旧日志因此缩小约 1000 倍；已改为 decode 后读取，并加入 PTS 单调性与漂移阈值验证，sampler 升至 v0.2.2。

## R2 结果与路线裁决

- Overall：6/10，低于 8/10。
- Event/order：3/5，低于 4/5。
- Identity/visibility：3/5，低于 4/5。
- 结论：`R2_GATE_FAILED`；不启动 GPU，不换样本，不做同源 R3。

当前明确路线：保留已修复 ledger-core；TOC-Bench 降为诊断/负例资源；下一工作流转向能在同一真实视频上承载局部状态、完整事件与上层结构的基础语料交集盘点和最小人工对齐。
