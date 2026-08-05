# Gap Map

最后更新：2026-08-03

## G1 — 同一视频上的显式跨层对应

- 状态：未解决；部分数据集覆盖。
- 需要：局部状态变化 → 完整事件 → 步骤/情节/全局情境之间的显式组成关系与时间支撑。
- 已有部分证据：ScaleLong 在同一视频设置 Clip/Shot/Event/Story QA；Ego4D-HCap 提供 clip/segment/video 三层 caption；FineGym 提供 action/sub-action 时间层次。
- 缺口：上述数据通常没有对象状态 ledger、可执行事件 effect 或纠错目标。

## G2 — 从错误检测升级为可验证纠错

- 状态：未解决；新近工作接近。
- 需要：错误类型、受控扰动、错误影响范围、正确修复目标、修复后的跨层一致性和证据/proof。
- 已有部分证据：VideoCon 提供 contrast caption 与差异解释；VideoHallucer 提供对抗式错误陈述；CaptainCook4D 提供真实/诱导程序错误；PIE-V 生成错误与 recovery correction，并评估 procedure/state-change coherence。
- 缺口：没有一个数据集同时给出视觉 grounded 的跨层 state/event proof 与可执行修复。

## G3 — 持久对象身份与高层事件/情节共存

- 状态：未解决。
- 需要：同一对象跨遮挡、跨事件、跨场景的 identity anchors，并链接到 state、event role 和 episode-level reference。
- 已有部分证据：VidOR/VidVRD 有 trajectory ID；VidSitu 有事件语义角色与 entity coreference；MovieGraphs 有角色/互动图及时间 grounding；TOC-Bench 构建时以 object track 为锚。
- 缺口：这些身份标注很少同时与状态 effect、长时情节层和纠错链共存。

## G4 — 可执行状态语义，而非仅 caption/QA

- 状态：未解决；T-STEP-v0 正在验证。
- 需要：typed before/after state、transition boundary、operator、precondition/effect、provenance、UNKNOWN 和 query proof。
- 已有部分证据：Ego4D Hands & Objects 提供 pre/PNR/post 与框；VidOSC/HowToChange 提供 initial/transitioning/end intervals；TOC-Bench 提供对象一致性 QA。
- 缺口：现有公开标注通常不能直接生成可执行 operator，也不能证明答案确实来自 state rollout。

## G5 — 可扩展的真实视频与可靠标注交集

- 状态：未解决。
- 需要：真实连续视频、足够长的情节、多事件与对象复现、可重复标注、合法许可和可控成本。
- 风险：最完整的结构常来自短片、单一体育/烹饪域、模型辅助 caption 或合成视频编辑；跨数据集拼接不能替代同一视频上的对齐标注。
