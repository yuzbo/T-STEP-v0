---
type: paper
node_id: paper:peddi2024_captaincook4d
title: "CaptainCook4D: A Dataset for Understanding Errors in Procedural Activities"
authors: ["Rohith Peddi", "Shivvrat Arya", "Bharath Challa", "Likhitha Pallapothula", "Akshay Vyas", "Bhavya Gouripeddi", "Qifan Zhang", "Jikai Wang", "Vasundhara Komaragiri", "Eric Ragan", "Nicholas Ruozzi", "Yu Xiang", "Vibhav Gogate"]
year: 2024
venue: "NeurIPS Datasets and Benchmarks Track"
external_ids:
  arxiv: "2312.14556"
  doi: null
  s2: null
tags: ["procedural-video", "error-recognition", "step-localization", "egocentric"]
added: 2026-08-03T00:00:00+08:00
---

# CaptainCook4D: A Dataset for Understanding Errors in Procedural Activities

## One-line thesis

用真实厨房中的正常与诱导错误执行，评测程序错误识别、多步骤定位和 procedure learning。

## Problem / Gap

长程序活动容易出现顺序、测量、技术、温度、遗漏等错误，但常规动作数据缺少错误执行。

## Method

384 个记录、94.5 小时、5.3K step annotations、10K fine-grained action annotations，并提供 recipe task graphs。采集使用安装在参与者头部的 HoloLens2 与 GoPro Hero 11；包含 RGB、depth、audio、head/hand tracking、pose 与 IMU 等同步模态。

## Key Results

支持 supervised/zero-shot error recognition、multi-step localization 和 procedure learning。

## Assumptions

诱导错误能代表可学习的程序偏差；recipe/task graph 是高层正确性参考。

## Limitations / Failure Modes

烹饪域窄；缺少显式 persistent object states、typed transition effects 和统一 recovery target。两台成像设备均为头戴式第一人称，不是独立第三人称/外部多视角，因此不能单独验证第三人称场景关系与跨视角泛化。

## Reusable Ingredients

真实错误视频、步骤层级、错误 taxonomy、正常/错误对照、task graph。

## Open Questions

能否补标错误前后 object-state ledger，并从错误定位扩展到可执行恢复？

## Claims

无 claim 节点；需先通过实验与 proof-checker。

## Connections

[AUTO-GENERATED from graph/edges.jsonl — do not edit manually]

## Relevance to This Project

是构建跨层纠错任务的强现实基础集合，但需要补足对象状态与恢复监督。定位为第一人称程序纠错候选或 fallback，而不是默认的通用第三人称主数据集。
