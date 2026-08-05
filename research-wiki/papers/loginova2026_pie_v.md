---
type: paper
node_id: paper:loginova2026_pie_v
title: "How to Correctly Make Mistakes: A Framework for Constructing and Benchmarking Mistake Aware Egocentric Procedural Videos"
authors: ["Olga Loginova", "Frank Keller"]
year: 2026
venue: "arXiv preprint"
external_ids:
  arxiv: "2604.15134"
  doi: null
  s2: null
tags: ["procedural-error", "correction", "state-coherence", "video-editing"]
added: 2026-08-03T00:00:00+08:00
---

# How to Correctly Make Mistakes: A Framework for Constructing and Benchmarking Mistake Aware Egocentric Procedural Videos

## One-line thesis

PIE-V 在程序视频中注入人类可解释的错误并生成 recovery corrections，同时评估 procedure logic、sequence consistency、state-change coherence 和 text-video grounding。

## Problem / Gap

任意 corruption 容易破坏 precondition、对象状态和长程程序逻辑，无法代表真实错误或合法恢复。

## Method

在 17 个任务、50 个 Ego-Exo4D scenarios 上注入 102 个错误并生成 27 个 recovery corrections；使用错误规划、修复规划、文本重写/验证和视频片段生成/拼接。

## Key Results

提出五类通用错误、恢复行为和九维人工 rubric，并审计多种程序错误数据集。

## Assumptions

结构化规划和生成式视频编辑可以形成足够可信的 mistake-aware variants。

## Limitations / Failure Modes

规模小；视频片段含生成/编辑，可能引入视觉伪影；state-change coherence 是 rubric，不是 typed ledger proof；属于新近预印本。

## Reusable Ingredients

合法错误 taxonomy、correction simulator、procedure-level coherence、错误—恢复成对协议。

## Open Questions

能否把错误和恢复改写为可回放的 typed state/operator diff，并在纯真实视频上验证？

## Claims

无 claim 节点；需先通过实验与 proof-checker。

## Connections

[AUTO-GENERATED from graph/edges.jsonl — do not edit manually]

## Relevance to This Project

是跨层纠错协议最接近的当前近邻，必须纳入 novelty 与实验设计比较。
