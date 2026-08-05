---
type: paper
node_id: paper:xue2024_vidosc
title: "Learning Object State Changes in Videos: An Open-World Perspective"
authors: ["Zihui Xue", "Kumar Ashutosh", "Kristen Grauman"]
year: 2024
venue: "CVPR"
external_ids:
  arxiv: null
  doi: null
  s2: null
tags: ["object-state-change", "temporal-localization", "open-world", "instructional-video"]
added: 2026-08-03T00:00:00+08:00
---

# Learning Object State Changes in Videos: An Open-World Perspective

## One-line thesis

HowToChange 用 initial、transitioning、end 时间区间监督开放世界对象状态变化定位。

## Problem / Gap

对象状态变化在开放对象与状态组合上难以识别和时间定位。

## Method

5,423 个 HowTo100M evaluation clips，409 个 object-state changes、20 种 transition、134 种对象；另有 36,075 个伪标训练片段。

## Key Results

公开时间区间、OSC 类别、seen/novel 设置和 1 fps evaluation。

## Assumptions

initial/transitioning/end 区间足以监督局部状态变化定位。

## Limitations / Failure Modes

没有 persistent object ID、participant roles、precondition/effect、跨事件情节或纠错目标；区间不能自动升级为 EventOperator。

## Reusable Ingredients

状态区间 schema、开放世界 split、局部 transition localization。

## Open Questions

哪些样本能补出稳定对象身份与可执行 operator certificate？

## Claims

无 claim 节点；需先通过实验与 proof-checker。

## Connections

[AUTO-GENERATED from graph/edges.jsonl — do not edit manually]

## Relevance to This Project

适合状态层和 boundary 模块预训练/评测，不足以承担跨层主数据。
