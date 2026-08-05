---
type: paper
node_id: paper:ma2026_scalelong
title: "ScaleLong: A Multi-Timescale Benchmark for Long Video Understanding"
authors: ["David Ma", "Huaqing Yuan", "Xingjian Wang", "Qianbo Zang", "Tianci Liu", "Xinyang He", "Yanbin Wei", "Jiawei Guo", "Jiahui Ni", "Zhenzhu Yang", "Meng Cao", "Shanghaoran Quan", "Yizhi Li", "Wangchunshu Zhou", "Jiaheng Liu", "Wenhao Huang", "Ge Zhang", "Shiwen Ni", "Xiaojie Jin"]
year: 2026
venue: "ICLR"
external_ids:
  arxiv: "2505.23922"
  doi: null
  s2: null
tags: ["long-video", "multi-timescale", "video-qa", "benchmark"]
added: 2026-08-03T00:00:00+08:00
---

# ScaleLong: A Multi-Timescale Benchmark for Long Video Understanding

## One-line thesis

在同一长视频内设置 Clip、Shot、Event、Story 四尺度问题，以隔离内容差异并直接比较模型的多时间尺度能力。

## Problem / Gap

以往 benchmark 常把不同尺度问题放在不同视频上，使内容难度与时间尺度混杂。

## Method

269 个平均 86 分钟的视频；每个视频 4–8 个问题，四个尺度至少各一个。

## Key Results

模型表现呈 U 型：最短与最长尺度较高，中间 Shot/Event 明显下降。

## Assumptions

问题所需证据跨度可以作为尺度定义；同视频设计能有效控制内容变量。

## Limitations / Failure Modes

尺度 QA 不提供对象状态、事件组成图、错误修复或 executable proof；层级主要是问题尺度而非共享结构化世界模型。

## Reusable Ingredients

同视频多尺度评测、四尺度操作化定义、按尺度报告能力曲线。

## Open Questions

公开标注是否包含问题所需的精确证据跨度与事件锚点？能否追加跨层一致性和纠错协议？

## Claims

无 claim 节点；需先通过实验与 proof-checker。

## Connections

[AUTO-GENERATED from graph/edges.jsonl — do not edit manually]

## Relevance to This Project

直接证明“三级不应写死”；是多尺度评测的最强近邻，但不是跨层语义纠错数据集。
