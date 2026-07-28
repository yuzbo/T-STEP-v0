---
updated: 2026-07-28
status: ready_for_review
scope: GPT-5 Pro 对 T-STEP-v0 Phase 0 首轮真实视频 gate failure 的聚焦实现裁决
---

# Prompt

你是一名严格的视频理解研究实现评审者。请对 T-STEP-v0 Phase 0 的首轮真实视频结果做一次 **focused implementation decision review**。不要重新 brainstorming 大系统，不要讨论论文包装，不要建议直接启动训练。

代码仓库：`https://github.com/yuzbo/T-STEP-v0`

评审分支：`codex/phase0-real-video-gate`

请优先检查：

- `tstep_v0/ledger_schema.py`
- `tstep_v0/validators.py`
- `tstep_v0/conversion.py`
- `tstep_v0/ledger_update.py`
- `tstep_v0/query_executor.py`
- `scripts/tstep_phase0_prepare_deep10.py`
- `scripts/tstep_phase0_render_targeted_windows.py`
- `schemas/tstep_v0/deep_annotation_schema.json`
- `data/phase0/toc_phase0_gate_report.json`
- `idea-stage/T_STEP_PHASE0_REAL_VIDEO_GATE_REPORT_20260728.md`
- `tests/tstep_v0/`

## 固定路线与不可放宽条件

目标仍是 executable typed object-state transition ledger-core。Phase 1 只有在 ledger 被证明不是 decorative 时才继续；否则转为 OST-Bench / Event-Drop。当前不得扩成 tokenizer + tracker + decoder + causal twin + pretraining 的大系统。

筛选、dense review 与 targeted replay 全程 answer-blind，未访问 evaluator-only gold；请不要建议用 QA 正确答案反推事件、状态或身份。

## 首轮真实结果

1. 从 TOC-Bench 六个维度分层选取 30 个独立真实视频，30/30 本地解码成功。
2. 5-frame 粗筛：ledger-critical likely 15、uncertain 12、unsuitable 3；deep-annotation yes 14、unclear 13、no 3。
3. 对首批 10 条做 24-frame dense review；对 blocker 做 324 帧 targeted replay；另审 5 条同维度补位，并对身份样本做 156 帧 0.1 s replay。总计 990 帧证据。
4. 最终严格 accept 7/10，低于预注册 gate 8/10，因此本轮 gate 失败，没有启动 GPU、baseline 或 corruption。
5. 已确认的 presupposition failure：
   - `charades_JFU3J`：红帽 31.23 s 后直到视频结束未重现；
   - `charades_K7PVL`：包括 0–2 s opening sweep 在内，window-entry comparator 未发生；
   - `perception_test_video_7284`：tomato 在 frame 0 已存在，first-show boundary 不可观察。
6. 已确认的语义 blocker：
   - `leaves_frame` 与 `disappears_for_good` 可能在同一 terminal event 上重合；
   - `partly_hidden` 与 `fully_hidden` 在多人/多实例遮挡下缺少可复现阈值；
   - 单一外观或 subject label 不足以建立 pre-gap / post-gap persistent identity。
7. 工程侧已修复 interior-only sampling：uniform dense sampling 现在包含 frame 0 与最后一帧，并支持 blocker-targeted temporal windows。

## 你必须做出的裁决

### D1. Event presupposition contract

是否应在 `QuerySpec` 增加：

```text
event_presupposition_status =
  observed | unsupported | ambiguous | outside_clip | not_required
```

并规定只有 `observed` 才能：

- 生成 query-required `EventOperator`；
- 计算 TransitionF1 / event-order accuracy；
- 构造 transition-drop corruption；
- 进入 oracle executor？

请明确选择，并指出 validator、executor、metric applicability 与 annotation schema 的最小修改。

### D2. Visibility semantics

请明确裁决以下哪种实现进入 Phase 0：

1. 人工离散标签 + 明确 operational rubric；
2. visible-fraction 连续量 + 冻结阈值；
3. 两者并存，但连续量只作证据、离散标签作 executor state。

同时裁决：

- `leaves_frame` 是 boundary event 还是 state value；
- `disappears_for_good` 是可在线判定的 event，还是只能在 clip end 后回溯确认的 terminal predicate；
- 两个 event interval 重叠时，event-order query 应返回 `UNKNOWN`、`INAPPLICABLE`，还是允许 tie。

### D3. Persistent identity minimum

请给出 identity query 的最小 required fields，至少裁决：

- pre-gap anchor；
- post-gap anchor；
- competing-instance inventory；
- identity scope；
- ambiguity label；
- evidence span / provenance。

请明确 subject-label-only、unique appearance、continuous track、manual/oracle ID 各自能通过哪些 gate，以及 object-ID swap corruption 何时不适用。

### D4. Sampling and review escalation

是否接受以下固定流程：

```text
5-frame coarse screen
→ 24-frame endpoint-inclusive dense review
→ question-aware targeted replay
→ only then deep annotation
```

请给出触发 targeted replay 的最小条件，并判断 0.1–0.5 s 时间窗是否足以做 feasibility gate，还是必须逐帧。

### D5. Route decision after 7/10

必须二选一：

- `RESAMPLE_WITH_CONTRACT_FIX`：先实现 D1–D4，再从 TOC event-order/identity 池补抽候选，重新运行 8/10 gate；
- `DEFER_TOC_SUBDIMENSIONS`：保留已通过的 conditional/spatial/cross-object 子集，但把 event-order/identity 主证据转向 OST-Bench/Event-Drop 或另一个原生 transition dataset。

不得把 7/10 四舍五入为通过。

## 输出格式

请严格按以下顺序输出：

1. `VERDICT`：`RESAMPLE_WITH_CONTRACT_FIX` 或 `DEFER_TOC_SUBDIMENSIONS`，最多 5 句。
2. `DECISION TABLE`：D1–D5 的单一明确裁决、理由、风险。
3. `SCHEMA PATCH`：逐字段列出 required / optional / forbidden inference。
4. `CODE PATCH PLAN`：精确到仓库文件与函数/类；只列最小必要修改。
5. `VALIDATION TESTS`：至少包含 presupposition failure、overlapping events、missing identity anchor、endpoint event、illegal corruption 五类负测。
6. `REVISED GATES`：哪些 gate 保留、修改或新增；不得事后降低 8/10。
7. `NEXT 48 HOURS`：严格排序的可执行步骤；明确何时仍禁止 GPU。

如果仓库实现与上述事实不一致，请指出具体文件、符号和不一致，不要给泛泛建议。
