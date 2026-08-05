---
type: idea
node_id: idea:tstep-hierarchical-semantic-correction
title: "同一视频上的层次语义理解与跨层纠错"
stage: active
outcome: pending
tags: ["video-understanding", "semantic-hierarchy", "cross-level-correction", "state-transition", "dataset-design"]
added: 2026-08-03T00:00:00+08:00
---

# 同一视频上的层次语义理解与跨层纠错

## One-line thesis

视频模型应在可变语义粒度上形成互相约束的表示，使局部状态证据能够纠正错误的事件/情节解释，也使全局情境能够消解局部身份、边界和事件歧义。

## Problem / Gap

现有视频数据集通常分别监督对象轨迹、状态变化、动作分段、事件关系、全局 QA 或错误检测。即使把这些数据混合训练，也不能证明模型在同一视频内部建立了跨层对应，更不能证明它执行了跨层纠错。

## Target data contract

每个核心样本必须来自同一连续真实视频，并尽量包含：

1. 持久对象及跨时间 identity anchors；
2. 可观察 StateInterval 与 TransitionBoundary；
3. 有参与者、边界、precondition/effect 和 provenance 的 EventOperator；
4. 事件到步骤/情节/全局情境的显式组成链接；
5. 局部与全局查询及其最小证据/proof；
6. 合法错误、受影响层级、正确恢复目标及修复后的一致性判定。

“意图”默认是有置信度和证据来源的高层假设，不与可观察事实混写。

## Dataset landscape

符号：✓ 明确提供；△ 部分、间接或仅构建期提供；— 未提供。这里的“纠错”要求存在错误及正确恢复目标，仅错误检测记为 △。

| 数据集 | 视频内容 | 身份 | 状态变化 | 事件/步骤 | 情节/全局 | 同视频跨层 | 纠错 | 结论 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| [TOC-Bench](https://arxiv.org/abs/2605.09904) | Charades 室内活动、Perception Test 脚本场景、MOSE/OVIS 遮挡视频；均值约 28.8 秒 | △ | △ | △ | — | — | △ | 很适合对象时序一致性诊断；公开 QA schema 不等于完整 track/state/operator 标注 |
| [ScaleLong](https://arxiv.org/abs/2505.23922) | 269 个平均 86 分钟的长视频 | — | — | △ | ✓ | ✓ | — | 当前最强“同视频多尺度 QA”候选，但没有跨层结构或修复监督 |
| [Ego4D-HCap / Video ReCap](https://arxiv.org/abs/2402.13250) | 第一视角日常活动，1 秒至 2 小时 | — | — | △ | ✓ | ✓ | — | clip/segment/video 三层 caption；层级生成强，状态与纠错弱 |
| [FineGym](https://openaccess.thecvf.com/content_CVPR_2020/html/Shao_FineGym_A_Hierarchical_Video_Dataset_for_Fine-Grained_Action_Understanding_CVPR_2020_paper.html) | 体操视频 | — | — | ✓ | △ | ✓ | — | action/sub-action 与三层语义 taxonomy 清晰，但域窄且无对象状态 |
| [VidSitu](https://vidsitu.org/) | 29K 个 10 秒电影片段，2 秒事件单元 | ✓ | — | ✓ | △ | ✓ | — | 事件角色、实体共指、事件关系很强；视频太短且无状态 effect |
| [VidOR](https://xdshang.github.io/docs/vidor.html) | 10K 个用户视频，均值约 35.7 秒 | ✓ | △ | ✓ | — | △ | — | trajectory ID 与关系时间段强；没有事件—情节 hierarchy |
| [MovieGraphs](https://moviegraphs.cs.toronto.edu/) | 电影片段与连续场景 | ✓ | △ | ✓ | ✓ | △ | — | 人物、关系、互动、reason 与时间 grounding 强；动机带主观性，非状态执行图 |
| [Ego4D Hands & Objects](https://ego4d-data.org/docs/benchmarks/hands-and-objects/) | 编织、木工、烘焙等第一视角手物交互 | △ | ✓ | △ | — | — | — | pre/PNR/post、对象框和状态变化类型强；仅局部事件 |
| [HowToChange / VidOSC](https://github.com/facebookresearch/VidOSC) | HowTo100M 教学视频片段 | — | ✓ | △ | — | — | — | initial/transitioning/end 时间区间强；无 persistent ID 和情节层 |
| [VOST](https://www.vostdataset.org/) | 破碎、撕裂、塑形等复杂对象变换 | ✓ | △ | — | — | — | — | 像素级持续对象身份强；缺 typed state 和事件语义 |
| [NExT-GQA](https://arxiv.org/abs/2309.01327) | 日常视频的因果/时序 QA | — | — | △ | △ | △ | — | QA 与 10.5K 时间证据区间绑定；不是跨层 proof |
| [VideoCon](https://research.google/pubs/videocon-robust-video-language-alignment-evaluation-via-contrast-captions/) | 多来源 video-caption | — | △ | △ | — | — | △ | contrast caption + 差异解释可测一致性，但不要求修复 |
| [VideoHallucer](https://github.com/patrick-tssn/VideoHallucer) | 多类真实视频与对抗式真假问题 | — | △ | △ | — | — | △ | 有错误类别和解释；主要是 hallucination detection，不是 correction |
| [CaptainCook4D](https://captaincook4d.github.io/captain-cook/) | 94.5 小时真实厨房程序，正常与诱导错误执行 | — | △ | ✓ | ✓ | ✓ | △ | 步骤、细粒动作和错误类别强；缺 persistent typed states 与系统性 recovery target |
| [PIE-V](https://arxiv.org/abs/2604.15134) | Ego-Exo4D 程序经受控错误与视频片段编辑 | — | △ | ✓ | ✓ | ✓ | ✓ | 最接近错误—恢复—全程一致性；仅 50 scenarios，含生成视频且缺 typed object ledger |
| [OmniCapBench](https://huggingface.co/datasets/OmniCapBench/OmniCapBench) | 786 个短/中视频，shot/event/scene/entity 结构 caption | △ | — | ✓ | ✓ | ✓ | — | 结构丰富但尚无正式论文，部分标注模型辅助，应先审计可靠性 |

## Evidence-weighted conclusion

没有发现单一现有数据集完整满足目标。最接近的能力被拆散在四组资源中：

- 同视频多尺度：ScaleLong、Ego4D-HCap；
- 局部对象状态：Ego4D Hands & Objects、VidOSC、VOST、TOC-Bench；
- 事件/实体结构：VidSitu、VidOR、MovieGraphs；
- 错误与恢复：CaptainCook4D、PIE-V、VideoCon、VideoHallucer。

因此，现有数据可用于预训练、模块验证和外部 benchmark，但不能通过简单拼接形成目标数据集。核心实验仍需要在一个基础视频集合上追加对齐标注。

## Candidate base-corpus decision

当前候选优先级：

1. **Ego4D family（首选待核验）**：长真实视频生态最完整，已有 narration、Hands & Objects、Goal-Step、HCap summary 和对象查询资源；最大未知是这些标注是否在足够多同一视频上相交。
2. **CaptainCook4D（强纠错备选）**：真实步骤和错误最强，适合可执行程序纠错；缺点是烹饪域窄、对象状态需补标。
3. **ScaleLong（评测锚）**：同视频四尺度最干净，但只适合多尺度 QA 评测，不能直接训练状态 ledger 或纠错。
4. **TOC-Bench（局部诊断锚）**：适合对象一致性和短中时序 gate，不适合作为完整情节层主数据。

Ego4D 的“规模过大”只对整库视频下载成立，不构成 annotation-intersection 审计 blocker。官方当前给出的近似下载量为：Full Primary Dataset 约 7.1 TB、Entire Dataset 30+ TB、annotations 约 2 GB、visualization data 约 500 MB、narrations only 约 350 MB。CLI 支持按 benchmark 和 `video_uid` 过滤。因此 Phase 0 先下载 annotations + metadata/manifest，计算 Narrations、FHO、Goal-Step 的 `video_uid` 交集，再只拉交集样本的视频或低分辨率 clips；禁止先下载全库。

当前未发现官方发布 Narrations × FHO × Goal-Step 的交集统计。HCap 是基于 Ego4D 的外部派生工作，不应在未核对其 UID 映射前当作 Ego4D 官方 benchmark 组件或假定可直接相交。

CaptainCook4D 是第一人称而非第三人称：HoloLens2 与 GoPro Hero 11 都安装在参与者头部。它提供双设备、多模态同步流，但不是独立第三人称/外部多视角。因此它适合程序错误与步骤结构，却不能单独覆盖第三人称场景关系；视角与烹饪域偏置是明确 blocker。

## Supervision decision

“局部纠正全局、全局纠正局部”是跨层信息交互与一致性机制，不天然等于无监督或弱监督。当前推荐：

1. self-supervised 预训练学习视觉/时间表示；
2. narration、summary、task graph 等粗粒度标签提供弱监督扩规模；
3. 少量同视频人工强标注提供局部状态—事件—episode 对齐、合法错误、正确修复目标和 proof；
4. 独立人工强标注测试集验证 correction gain，而不是只验证一致性。

纯无监督或只有跨层 consistency loss 不能支持“语义纠正”主张，因为两个层级可能一致地犯错，错误全局也可能反向污染局部。首版方法应称为混合监督（弱/自监督扩规模 + 小规模强监督纠错锚点），而不是纯无监督。

## Route consequences

- 不应把三级当作数据先验。ScaleLong 的四尺度和 Ego4D-HCap 的三层说明，层数取决于语义职责与标注可分性。
- 推荐模型定义“状态—事件—episode”三种核心职责，并允许 shot/step/story 等中间或上层节点动态展开。
- 数据 gate 应先检查同视频 annotation intersection；若交集不足，再决定补标 Ego4D、转 CaptainCook4D，或构建小规模 aligned benchmark。
- 2026-08-06 R2 证明：即使 TOC-Bench 题面面向对象时序，自动事件标签也不足以直接满足 strict `fully_hidden / reappearance / enters_frame` 与 competitor-aware identity 合同；它保留为诊断锚，但不再承担局部 ledger-core 唯一监督源。
- ledger-core 合同修复本身保留；R2 失败不授权膨胀模型，也不授权换样本追数。下一步必须先改变数据证据来源/人工标注合同。

## Open questions

- 哪个基础集合能以最低成本获得同视频六类核心标注？
- 纠错目标是恢复结构化 ledger、修复文本解释，还是两者都要？
- 评价跨层自洽时，哪些关系必须硬约束，哪些允许概率性假设？
- Ego4D 的 Hands & Objects、Goal-Step、narration 是否在足够多同一 `video_uid` 上相交；外部 HCap 能否可靠映射回这些 UID？
- 最终论文是否要求第三人称泛化；若要求，哪个第三人称基础集合承担主训练或外部验证？

## Connections

[AUTO-GENERATED from graph/edges.jsonl — do not edit manually]
