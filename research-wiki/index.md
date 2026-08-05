# Research Wiki

最后更新：2026-08-06

## 当前研究方向

本项目当前目标是构建一个在多个语义时间粒度上保持自洽、并能进行跨粒度语义纠错的层次视频理解模型。

当前已确认：

- 层级由语义边界决定，而不是固定秒数；
- 核心样本单位是同一视频中的跨层对应与纠错，不是多个独立任务的拼接；
- “三级”只是候选首版配置，不是理论限制；
- 现有 T-STEP-v0 executable object-state transition ledger-core 保留为局部状态—事件层的候选可执行核心，但不能代表完整最终目标；
- 在数据证据不足前，不把“情节”和“意图”强行合并，也不把主观意图当作事实标签。

## 当前路线状态

1. 真实资产入口：继续保留 TOC-Bench Phase 0 的真实视频与 answer-blind ledger 审计结果。
2. 数据集路线：优先寻找同一真实长视频上可对齐的对象状态、事件、步骤/情节和纠错标注。
3. 模型路线：层级接口允许可变深度；首版是否采用三级，待数据可标注性和任务必要性决定。
4. 实验硬约束：跨层纠错必须通过受控错误、恢复目标和可验证证据评测，不能只用最终 QA 准确率代替。
5. 当前 gate：Pro 合同修复已完成；全新不可替换 R2 严格通过 6/10，event/order 3/5、identity/visibility 3/5，三项均失败。TOC-Bench 自动事件标签不再作为严格 ledger-core 唯一监督源；GPU、performance baseline 和 corruption 继续锁定。
6. 下一路线：保留 ledger-core v0.2；停止同源 R3 补抽，转向 Ego4D family annotation-intersection 与最小人工对齐，CaptainCook4D 作为程序错误/纠错备选。

## 关键节点

- [主研究路线](ideas/tstep-hierarchical-semantic-correction.md)
- [Gap map](gap_map.md)
- [压缩查询包](query_pack.md)
- [更新日志](log.md)
- [TOC-Bench R2 合同复验](experiments/toc-r2-contract-resample.md)

## 核心论文/数据集节点

- [TOC-Bench](papers/chen2026_toc_bench.md)
- [ScaleLong](papers/ma2026_scalelong.md)
- [Video ReCap / Ego4D-HCap](papers/islam2024_video_recap.md)
- [VidSitu](papers/sadhu2021_vidsitu.md)
- [VidOSC / HowToChange](papers/xue2024_vidosc.md)
- [CaptainCook4D](papers/peddi2024_captaincook4d.md)
- [PIE-V](papers/loginova2026_pie_v.md)
