---
type: paper
node_id: paper:islam2024_video_recap
title: "Video ReCap: Recursive Captioning of Hour-Long Videos"
authors: ["Md Mohaiminul Islam", "Ngan Ho", "Xitong Yang", "Tushar Nagarajan", "Lorenzo Torresani", "Gedas Bertasius"]
year: 2024
venue: "CVPR"
external_ids:
  arxiv: "2402.13250"
  doi: null
  s2: null
tags: ["hierarchical-captioning", "long-video", "ego4d", "multi-granularity"]
added: 2026-08-03T00:00:00+08:00
---

# Video ReCap: Recursive Captioning of Hour-Long Videos

## One-line thesis

通过 clip caption、segment description 和 video summary 的递归层次生成，处理 1 秒至 2 小时的视频。

## Problem / Gap

传统 caption 模型集中在数秒片段，无法表达长视频的层次结构。

## Method

构建 Ego4D-HCap：5.27M clip captions、17.5K segment descriptions、约 8.3K long-range video summaries；采用从局部到全局的 curriculum。

## Key Results

展示多层 caption 生成并可迁移到 EgoSchema VideoQA。

## Assumptions

文本摘要层级能够近似视频语义层级；递归聚合可利用不同层级间协同。

## Limitations / Failure Modes

中长层 caption 含 LLM 伪标扩展；没有 persistent object state、typed event effects、错误与恢复标注。

## Reusable Ingredients

三层 caption contract、长视频 base corpus、局部到全局 curriculum。

## Open Questions

三层 caption 是否在同一视频上能与 Hands & Objects、Goal-Step 和对象查询标注相交？

## Claims

无 claim 节点；需先通过实验与 proof-checker。

## Connections

[AUTO-GENERATED from graph/edges.jsonl — do not edit manually]

## Relevance to This Project

是层次语义生成的重要近邻，也是选择 Ego4D family 作为基础集合的主要原因。
