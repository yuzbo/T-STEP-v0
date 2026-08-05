---
updated: 2026-08-06
status: active
scope: 当前项目目标锚点；固化多粒度语义自洽与跨层纠错最终目标，并保留 T-STEP-v0 ledger-core 作为局部执行核心和真实视频 feasibility workstream
out-of-scope: 本文不记录实验数字，不替代正式 proposal、paper plan、citation audit 或最终实验报告
---

# 当前目标与路线锚点

## 0. 2026-08-03 用户确认的上位目标更新

本节优先于本文后续 2026-07-06 的 ledger-core 收缩记录。后续章节继续作为局部执行核心、Phase 0 证据和 kill gates 使用，不再代表完整最终目标。

最新最终目标：

> 构建一个在多个语义时间粒度上保持自洽、并具有可验证跨粒度语义纠错能力的层次视频理解模型。

已确认的设计边界：

1. 层级由语义边界决定，而不是固定时长；
2. 状态变化、完整事件、步骤/情节/全局情境是候选语义职责，层数可变；
3. 三级只是首版候选，不写成理论限制；
4. 数据核心单位是同一视频上的跨层对应与纠错，不能用三个互不对齐的数据集任务拼接代替；
5. T-STEP-v0 executable object-state transition ledger-core 保留为状态—事件层的候选可执行机制；
6. 意图默认是证据支持的高层假设，不与可观察事实混写；
7. 实现前先完成真实资产与 annotation-intersection 盘点。

持续知识入口：

```text
research-wiki/index.md
research-wiki/ideas/tstep-hierarchical-semantic-correction.md
research-wiki/query_pack.md
```

首轮数据集核验结论：目前没有发现单一现有数据集同时提供持久对象身份、typed 状态变化、事件/情节跨层链接、受控错误、正确恢复目标和可验证 proof。ScaleLong、Ego4D-HCap、Ego4D Hands & Objects、VidSitu、CaptainCook4D 和 PIE-V 分别覆盖互补子集，详细证据见 research wiki。

### 0.1 2026-08-06 当前实验 gate（覆盖后文旧 Phase 0 下一步）

- Pro `GO_CONTRACT_FIX_AND_RESAMPLE` 合同已完成代码化。
- R1 deep-10 7/10 失败保持不变；全新不可替换 R2 为 overall 6/10、event/order 3/5、identity/visibility 3/5，三重 gate 全失败。
- 失败对象是 TOC-Bench 自动事件前提作为 strict ledger supervision 的兼容性，不是最终多粒度目标，也不是 ledger schema 的表达能力。
- GPU、performance baseline、corruption 继续禁止；不做同源 R3 或换样本追数。
- 保留 T-STEP-v0 ledger-core v0.2；TOC-Bench 只作局部诊断/负例；当前下一步改为 Ego4D family annotation-intersection + 最小人工 aligned ledger 标注，CaptainCook4D 为程序纠错备选。
- 逐样本证据与机器 gate：`data/phase0/toc_phase0_r2_manual_review.json`、`data/phase0/toc_phase0_r2_gate_result.json`。

> 最新更新时间：2026-08-03 +08:00
> 目的：避免后续 session 遗忘当前任务目的、最终目标和创新边界。
> 2026-07-06 历史子路线裁决：从大而全 **T-STEP / Event-Complete Object-State Transition Program** 收缩为 **T-STEP-v0 / executable object-state transition ledger-core**；自 2026-08-03 起，该路线作为上位层次模型的局部执行核心继续保留。

## 1. Ledger-core 子工作流产出

最终产出是一个论文级研究包，但不再是大而全系统。当前最小主线是：

1. **主方法系统**：T-STEP-v0: Event-complete object-state transition ledger for faithful video reasoning。
2. **核心中间表示**：typed object-state transition ledger。
3. **核心执行机制**：state ledger update + ledger query executor。
4. **必要前端**：ECTok v0 / Event-Complete Tokenization，用于保留 transition-critical events。
5. **必要支撑**：off-the-shelf tracker / oracle track ablation，而不是自训 tracker。
6. **诊断模块**：从 IBD-STGR 保留 sufficiency、necessity、CLCC、risk-coverage、selective abstention。
7. **验证协议**：event completeness、object persistence、transition correctness、ledger query faithfulness、corruption diagnostics。
8. **Fallback**：若 ledger-core gate 失败，转 OST-Bench / Event-Drop Robustness Curve benchmark paper。

## 2. Ledger-core 子目标

当前最终目标是：

> 构建一个能把视频转成事件完整、对象持久、可执行更新、可查询的 typed object-state transition ledger，并要求答案由 ledger query / rollout 得到的视频推理系统。

不要再把目标写成：

> 构建一个同时包含 tokenizer、tracker、transition decoder、ledger、executor、IBD、pretraining、causal twin 的大系统。

更准确的目标是：

> 证明现有视频模型即使能回答问题、定位 evidence 或生成 CoT，也常没有维护可执行的对象状态转移程序；T-STEP-v0 通过 typed transition ledger 和 query executor 改善这种失败，并通过 ledger corruption / shuffle / object-ID swap 证明答案确实依赖 ledger。

## 3. 一句话论文主张

英文：

> Faithful video reasoning requires executable object-state transition ledgers, not only evidence grounding or answer-first chain-of-thought.

中文：

> 可信视频推理不应只寻找证据或生成解释，而应维护可执行的对象状态转移账本，并从账本查询或回放得到答案。

## 4. 论文面对的问题

| 问题 | 为什么现有路线不够 |
|---|---|
| evidence grounding 不等于状态理解 | timestamp / bbox 只能说明看哪里，不能说明事件如何改变对象状态 |
| active search 不等于事件完整 | query relevance 可能找相关片段，但漏掉短暂关键状态转移 |
| graph memory 不等于可执行转移 | entity graph / event graph 往往是检索索引或解释图，不是 state update program |
| final QA 不等于中间状态正确 | 模型可能答对但 object state timeline 错 |
| CoT 不等于执行 | 文本推理链可能合理，但没有被状态 ledger 约束 |
| counterfactual QA 不等于可干预世界模型 | 反事实答案若不基于 state transition rollout，容易变成语言假想 |

## 5. 当前核心解决方案

T-STEP-v0 只保留五个当前必要组件：

1. **ECTok v0 / Event-Complete Tokenizer**
   选择 state-change、relation-change、possession-change、visibility-change、causal-trigger、momentary-event clips / objects。必须通过 EventRecall@Budget 证明，不做花哨 tokenizer。

2. **Object Persistence Adapter**
   使用 off-the-shelf tracker 或 dataset tracks 维护 object identity、visibility、location、attributes、relations、confidence。必须做 oracle track 上界。

3. **Typed Transition Operator Decoder**
   只做有限 closed schema：location、visibility、possession、relation、attribute、state_change。避免 open-ended full state ontology。

4. **State Ledger Update Engine**
   持续更新 typed object-state ledger，支持 uncertainty、conflict resolution、missing transition detection。必须可执行、可回放、可查询。

5. **Ledger Query Executor**
   把问题转成 ledger query：final state、intermediate state、event order、count、causal dependency、counterfactual。答案必须由 ledger query / rollout 得到。

保留但非主线：

6. **IBD Diagnostic Module**
   sufficiency、necessity、irrelevance stability、CLCC、risk-coverage、selective abstention，用于 verifier / calibration / reward / ablation。

当前不做：

- Local Causal Video Twin；
- 大规模 DeltaLedger pretraining；
- 大型端到端 RL agent；
- open-ended state ontology；
- 把 IBD-STGR 重新拉回主线。

## 6. 与现有工作的创新边界

| 近邻方向 | 已有能力 | T-STEP-v0 的安全差异 |
|---|---|---|
| Open-o3 / EG-VQA / VideoZeroBench | 证据定位与 evidence verification | T-STEP-v0 解释 evidence 如何改变对象状态，并要求答案从 ledger 查询得到 |
| VideoTree / OASIS / AVP / TimeSearch-R | 自适应看哪里、层次检索、长视频 memory | T-STEP-v0 的 acquisition target 是 transition completeness，不只是 query relevance |
| HARG / MOMA / EGAgent / EgoGraph / GraphThinker | activity hierarchy、entity graph、event graph | T-STEP-v0 不是静态图，而是 typed executable state-transition ledger |
| VSTAT / Video-MME-Logical / Moment-Video | 诊断状态追踪与短暂事件失败 | T-STEP-v0 是针对这些失败的模型路线 |
| CaST / CausalVQA / CounterVQA | causal / counterfactual video QA | T-STEP-v0 的反事实来自 ledger state rollout，而不是只生成文本答案 |
| UMPIRE / confidence / self-consistency | answer-level uncertainty | T-STEP-v0 的 sufficiency 绑定 ledger completeness 和 transition uncertainty |

## 7. 必须证明什么

### 7.1 问题存在性

- 现有模型 final QA 与 intermediate state / transition correctness 脱钩。
- 关键短事件在 sampling / compression 阶段丢失。
- graph / evidence / active-search baselines 不恢复可执行 state transition。
- oracle event tokens / oracle tracks / oracle states 能显著提升 state / transition / QA。

### 7.2 方法有效性

| 组件 | 必须证明 |
|---|---|
| ECTok v0 | EventRecall@Budget、Transition boundary F1、state QA 优于 uniform / CLIP / VideoTree-style selection |
| Object Persistence | Object-ID consistency、occlusion/reappearance、state persistence 优于 caption memory |
| Transition Operator | Transition-F1、precondition/effect accuracy 优于 caption parser / event graph baseline |
| Ledger Update | StateAcc@t、state timeline edit distance、Ledger Query Accuracy 提升 |
| Query Executor | 答案来自 ledger 的版本优于 free-text CoT / caption+LLM |
| Corruption Diagnostics | shuffled / corrupted / dropped transition 会显著破坏答案 |
| IBD verifier | 改善 selective risk、CLCC、irrelevance stability，但不作为主创新 |

## 8. Phase 0 / Phase 1 gates

### Phase 0：1 周数据审计

必须产出：

- `dataset_audit.jsonl`
- `unified_sample_schema.json`
- `annotation_coverage.csv`
- `phase0_baseline.jsonl`
- `manual_audit_50.md`
- `metrics_smoke_test.py`
- `GO / NO_GO`

Phase 0 kill gate：

> 如果 50 个样本里超过 40% 无法定义稳定 object-state variable，停止 T-STEP 主线，转 Event-Drop / OST-Bench diagnostic。

### Phase 1：2-week pilot

必须跑：

- dense-frame MLLM；
- uniform sparse；
- CLIP relevance；
- caption+LLM；
- tracker+caption+LLM；
- ECTok v0；
- T-STEP-v0；
- oracle event tokens；
- oracle tracks；
- oracle states；
- ECTok without ledger；
- ledger without ECTok；
- no object persistence；
- no transition operator；
- answer-first CoT；
- shuffled / corrupted ledger。

Phase 1 核心判定：

> **Proceed only if Phase 1 证明 ledger 不是装饰；否则 Reframe to benchmark。**

## 9. 核心指标

- EventRecall@Budget
- Transition Boundary F1
- Object-ID Consistency
- StateAcc@t
- Transition-F1
- RelationChange-F1
- State Timeline Edit Distance
- Ledger Query Accuracy
- Final QA Accuracy
- Counterfactual State Accuracy
- CLCC / Causal Ledger Consistency under Corruption
- Risk-Coverage AUC
- Token / Frame Budget
- Ledger-Faithfulness Score

## 10. 数据集优先级

主实验优先：

1. VSTAT
2. TOC-Bench
3. Moment-Video
4. HowToChange / VidOSC
5. Video-MME-Logical
6. CaST-Bench

补充与 baseline：

7. EG-VQA
8. VideoZeroBench
9. NExT-GQA
10. AGQA / STAR / CLEVRER
11. MOMA / MOMA-LRG
12. Something-Something-V2

注意：以上 2025/2026 数据集链接与论文状态需后续 citation-audit / repo availability check，不得直接当作已核验事实。

## 11. 实现基线和仓库路线

最终选择：

- **Main implementation base**：自建轻量仓库，PyTorch + HF + OpenCV + tracker + MLLM harness。
- **Baseline reproduction base**：VideoTree + OASIS + Open-o3 Video + AVP / TimeSearch-R 可复现部分。
- **Evaluation harness base**：自建统一 JSONL / CSV，借鉴 EG-VQA、CaST-Bench、VideoZeroBench 的 evidence metrics。
- **旧 IBD 可迁移模块**：CLCC、sufficiency / necessity、irrelevance stability、risk-coverage、selective abstention、reward / calibration。

第一批应创建的代码模块：

- `ledger_schema.py`
- `ectok.py`
- `transition_decoder.py`
- `ledger_update.py`
- `query_executor.py`
- `metrics.py`
- `datasets.py`
- `train.py`
- `eval.py`

## 12. Kill Gates

若以下条件出现，应停止或重构 T-STEP-v0：

1. oracle event tokens 不提升：QA 或 EventRecall 相比 uniform 提升 <3 pp。
2. oracle tracks 不提升：TOC / object-sensitive QA 提升 <3 pp。
3. oracle states 不提升：Ledger Query Acc / QA 提升 <5 pp。
4. ledger metrics 与 final QA 无关：Pearson/Spearman <0.2。
5. ECTok+T-STEP-v0 不超过 caption+LLM：主指标 < caption+LLM +3-5 pp。
6. active search / graph memory baseline 同预算追平或更强。
7. 只在 synthetic 有效，real-world 数据无提升。
8. 实现主要靠 prompt engineering。
9. 人工审计 >40% 样本状态变量不稳定。
10. 每 100 clips 标注 >1 人日且一致性低。
11. 只在一个数据集提升，无法跨数据集迁移。
12. causal corruption 后 QA 下降 <10 pp。
13. shuffled ledger 后 order/state QA 下降 <10 pp。
14. full 与 no transition 差 <2 pp。

## 13. 当前路线组合

当前主线：

> **T-STEP-v0 / executable object-state transition ledger-core**

必要前端：

> **ECTok v0 / Event-Complete Tokenization**

诊断 / 校准模块：

> **IBD-STGR 的 sufficiency / necessity / CLCC / risk-coverage / selective abstention**

Fallback paper：

> **OST-Bench / Event-Drop Robustness Curve**

暂缓：

> **DeltaLedger Pretraining**

暂不主攻：

> **Local Causal Video Twin**

放弃或禁止膨胀：

> broad HBV-R、泛泛 hierarchical belief graph、泛泛 grounded self-correction、Open-o3 + verifier 式 IBD-STGR 主线、无 state-transition 约束的 graph reasoning、大而全 T-STEP 系统叙事。

## 14. 下一步

> 本节原始列表是 2026-07-06 的历史计划；当前执行顺序以 §0.1 为准。

1. 做 citation-audit / repo availability check，核验附件中的 2025/2026 论文、代码、数据集是否真实可用。
2. 做 Phase 0 dataset audit。
3. 定义 `unified_sample_schema.json` 与 `ledger_schema.py`。
4. 实现 uniform / CLIP relevance / caption+LLM 三个最低 baseline。
5. 实现 metric smoke tests。
6. 人工审 50 个样本，判定 object-state variable 是否稳定。
7. 若 Phase 0 通过，再进入 2-week pilot。
