# Research Wiki Query Pack

最后更新：2026-08-06

## Project direction

目标：同一真实视频上，多语义粒度理解保持自洽，并允许局部证据纠正全局理解、全局情境消解局部歧义。层级按语义边界定义，深度可变。T-STEP-v0 ledger-core 是局部状态—事件层的候选执行核心，不是完整目标。监督路线不是纯无监督，而是弱/自监督扩规模 + 小规模强监督纠错锚点。

## Top gaps

1. G1：缺少状态→事件→情节的同视频显式跨层组成关系。
2. G2：现有 benchmark 多为错误检测或对比判断，缺少可验证修复目标与 proof。
3. G3：对象轨迹、事件语义和长时情节通常分散在不同数据集。
4. G4：状态标签通常不可直接执行为 typed operator/ledger rollout。
5. G5：真实长视频、密集结构、可靠人工标注与许可难同时满足。

## Paper clusters

- 多时间尺度：ScaleLong（同视频四尺度 QA）、Video ReCap/Ego4D-HCap（三层 caption）、FineGym（action/sub-action hierarchy）。
- 对象与状态：TOC-Bench、Ego4D Hands & Objects、VidOSC/HowToChange、VOST、VidOR。
- 事件与情节：VidSitu、MovieGraphs、NExT-GQA、长视频 QA benchmarks。
- 错误与纠正：VideoCon、VideoHallucer、CaptainCook4D、PIE-V。

## Failed ideas / banlist

- 不把固定三种秒级窗口当作语义层次。
- 不把 TOC-Bench 的构建期 object tracks/timelines 误写成公开的 typed ledger ground truth。
- 不把三个互不对齐的数据集任务拼接称为“跨层纠错”。
- 不把 contrast/hallucination detection 自动等价为 correction。
- 不从状态差直接臆造 operator、因果或意图。

## Top papers

- TOC-Bench：对象时序一致性真实视频诊断；适合 Phase 0，公开字段不足以直接监督完整 ledger。
- ScaleLong：同一长视频上的 Clip/Shot/Event/Story 四尺度 QA；最接近多尺度评测，但缺跨层结构与纠错。
- Video ReCap / Ego4D-HCap：clip/segment/video 三层 caption；适合层次生成，缺对象状态与错误修复。
- VidSitu：事件、语义角色、实体共指、事件关系；适合事件中层。
- CaptainCook4D：步骤、细粒动作、真实/诱导程序错误；适合错误与程序结构。
- PIE-V：错误注入、recovery correction、procedure/state-change coherence；最接近纠错协议，但规模小且包含生成式视频编辑。

## Active chain

现有 T-STEP-v0 ledger 可执行性 → R1 真实视频 gate 7/10 失败 → Pro 冻结 presupposition、visibility、identity、sampling 合同并完成 v0.2 修复 → 全新不可替换 R2 为 6/10，两个子组均 3/5，三重 gate 失败 → 禁止 GPU/性能实验/同源 R3；保留 ledger-core，转 Ego4D annotation-intersection + 最小人工对齐，TOC-Bench 仅作诊断与负例来源 → 获得合格局部核心后再对齐 event/episode hierarchy 与跨层修复。

## Open unknowns

- Ego4D 的 Hands & Objects、Goal-Step、narration 是否在足够多同一 `video_uid` 上相交；HCap 外部派生标注能否映射回这些 UID？整库约 7.1 TB，但交集审计只需先取约 2 GB annotations + metadata。
- CaptainCook4D 是否能低成本补出 persistent object-state 与恢复后状态？它是双头戴设备的第一人称数据，不提供独立第三人称视角。
- ScaleLong 是否发布问题所需证据跨度/局部事件锚点，还是仅尺度标签？
- 首版层数应由标注可分性决定为三层、四层，还是可变深度？
- 若论文目标包含通用第三人称视频，哪一数据集承担主训练或外部泛化验证？
- Ego4D intersection 若不足，CaptainCook4D 与第三人称外部验证集如何组成最小双域 pilot？
