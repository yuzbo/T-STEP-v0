# Research Wiki Log

本文件只追加，不回写历史记录。

## 2026-08-03

- Wiki initialized.
- 项目内未发现 `tools/research_wiki.py`、`.aris` helper 清单或技能目录中的 fallback helper；因此按 research-wiki 规范手工初始化目录与页面，并保留相同 node ID、frontmatter、graph 和日志约束。
- 记录用户确认的目标：同一视频上的多粒度语义自洽与跨层纠错；语义边界优先，三级不写死。
- 完成首轮数据集一手来源调研，覆盖对象状态、对象持续身份、事件结构、层次时间理解、长视频情节、错误检测与恢复。
- 形成当前结论：未发现单一现有数据集同时提供持久对象身份、显式状态变化、事件/情节跨层链接、受控错误、正确恢复目标和可验证 proof；ScaleLong、Ego4D-HCap、Ego4D Hands & Objects、VidSitu、CaptainCook4D、PIE-V 分别覆盖互补子集。
- 记录 TOC-Bench 关键限制：构建过程使用对象轨迹和事件时间线，但公开 benchmark schema 主要发布 QA、格式、events（排序题）及 metadata，不等于发布了可直接监督 typed ledger 的完整逐帧轨迹/状态/operator 标注。
- 同步更新 `RTK.md` 与 `idea-stage/CURRENT_GOAL_AND_ROUTE.md`，使后续任务优先读取 research wiki，并明确 ledger-core 是局部执行核心而非完整最终目标。
- 核验监督范式：跨层双向纠正是信息交互机制，不天然属于无监督；首版采用弱/自监督扩规模 + 小规模强监督纠错锚点，纯 consistency 不能证明语义修复。
- 核验 CaptainCook4D 视角：HoloLens2 与 GoPro Hero 11 均头戴，属于第一人称双设备多模态采集，不是第三人称/独立外部多视角；将视角与烹饪域偏置列为 blocker。
- 核验 Ego4D 规模与下载路线：整库 Full Primary 约 7.1 TB、Entire Dataset 30+ TB，但 annotations 约 2 GB，CLI 支持按 benchmark/`video_uid` 过滤；Phase 0 只做 annotations + metadata UID 交集盘点，不下载全库。
- 未发现 Ego4D 官方提供 Narrations × FHO × Goal-Step 的现成交集统计；HCap 视为外部派生工作，需单独核对 UID 映射。

## 2026-08-05

- 恢复并核验真实实验进度：TOC-Bench Phase 0 已完成 30 个真实视频解码、990 帧 answer-blind 证据复核与 deep-10 gate；严格通过 7/10，低于预注册 8/10，GPU、性能 baseline 和 corruption 仍被禁止。
- 确认当前正处于此前约定的“首批真实样本与明确 blocker 后的聚焦实现评审”节点，而不是继续资产调研或直接训练节点。
- 四个必须由评审冻结的 blocker：event presupposition、visibility operator overlap、persistent identity anchors、endpoint-aware sampling/replay escalation。
- 核验公开代码已提交到 `https://github.com/yuzbo/T-STEP-v0/pull/1`，分支 `codex/phase0-real-video-gate`，commit `878c7b1`；本地与远端一致，30 tests passed。
- 生成 2026-08-05 Pro Prompt，将更新后的“同视频多粒度语义自洽与跨层纠错”上位目标纳入评审，同时把 ledger-core 严格限定为状态—事件局部执行核心。

## 2026-08-06

- 完整吸收 Pro 裁决 `GO_CONTRACT_FIX_AND_RESAMPLE`，认同保留局部 ledger-core、先修合同、全新 R2、三重 gate 前禁 GPU 的路线；同时限定 `CorrectionRecord` 仅作未来接口，evaluator artifact 不得进入 builder/compiler/executor。
- 实现 D1–D7：EventPresupposition、visibility rubric、IdentityCertificate、ConversionCertificate、verified-only execution、answer-free build input、typed corruption、status-aware metrics 与四阶段 sampler。
- 预封存全新 R2 10-video roster，配额 3/2/3/2、无 R1 candidate-30 重叠、禁止替换；10/10 真实资产物化与解码成功。
- 核验 TOC-Bench 上游代码：ordering `events[].label/event_text` 是题面选项，`correct_order` 是独立 evaluator 字段；以 `R2_PRESEAL_AMENDMENT_001` 只补题面字段，ID/顺序/选择不变。
- 采样中发现并修复 OpenCV seek 后 decode 前 `CAP_PROP_POS_MSEC` 单位异常；最终 sampler `v0.2.2` 增加 decode-after-read、PTS monotonicity 与 drift validation。
- 完成 240 dense frames、13 targeted windows、1108 targeted frames 的 blind review；R2 overall 6/10、event/order 3/5、identity/visibility 3/5，三项 gate 全部失败。
- 冻结 `R2_GATE_FAILED`：不换样本、不做同源 R3、不启动 GPU/baseline/corruption。保留 ledger-core v0.2；TOC-Bench 降为诊断/负例来源；下一步转 Ego4D annotation-intersection 与最小人工对齐，CaptainCook4D 为纠错备选。
- 最终验证：68 tests passed；两个 Draft 2020-12 schemas 合法，deep annotation template 验证通过，R2 四个公开 JSON 记录可解析，`git diff --check` 通过。
