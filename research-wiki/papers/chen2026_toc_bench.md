---
type: paper
node_id: paper:chen2026_toc_bench
title: "TOC-Bench: A Temporal Object Consistency Benchmark for Video Large Language Models"
authors: ["Junzhe Chen", "Siyuan Meng", "Yuxi Chen", "Man Zhao", "Xiaojie Guo"]
year: 2026
venue: "arXiv"
external_ids:
  arxiv: "2605.09904"
  doi: null
  s2: null
tags: ["video-qa", "object-consistency", "temporal-reasoning", "benchmark"]
added: 2026-08-03T00:00:00+08:00
---

# TOC-Bench: A Temporal Object Consistency Benchmark for Video Large Language Models

## One-line thesis

通过对象轨迹锚定的 QA 诊断 Video-LLM 在遮挡、重现、状态变化、事件次序和跨对象关系上的时序一致性。

## Problem / Gap

通用 VideoQA 容易高估模型对同一对象跨时间身份、状态和连续性的保持能力。

## Method

从 Charades、Perception Test、MOSE 和 OVIS 构造对象轨迹与事件时间线，经 text-only、single-frame、frame-shuffle 三类必要性过滤及专家审核生成 benchmark。

## Key Results

2,323 个 QA、1,951 个视频、10 个诊断维度；模型在计数、排序、身份敏感推理和 hallucination-aware verification 上仍弱。

## Assumptions

构建期自动 tracks/events 足以支撑候选 QA；短中视频中的对象现象可以诊断 temporal object consistency。

## Limitations / Failure Modes

公开 schema 主要是 QA、格式和 metadata；构建期 object tracks/timelines 不应被误当作已发布的 typed state/operator ground truth。视频偏短中时长，也不覆盖完整层次情节理解。

## Reusable Ingredients

对象一致性维度、时序必要性过滤、answer-blind 真实视频候选、确定性 QA 评分。

## Open Questions

能否合法取得并审计构建期 tracks/timelines？其中多少 QA 真正依赖可执行状态变化？

## Claims

无 claim 节点；需先通过实验与 proof-checker。

## Connections

[AUTO-GENERATED from graph/edges.jsonl — do not edit manually]

## Relevance to This Project

适合 T-STEP-v0 局部对象状态 ledger 的真实视频 gate；不适合作为完整多层情节纠错数据集。
