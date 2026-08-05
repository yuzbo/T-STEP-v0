---
type: paper
node_id: paper:sadhu2021_vidsitu
title: "Visual Semantic Role Labeling for Video Understanding"
authors: ["Arka Sadhu", "Tanmay Gupta", "Mark Yatskar", "Ram Nevatia", "Aniruddha Kembhavi"]
year: 2021
venue: "CVPR"
external_ids:
  arxiv: null
  doi: null
  s2: null
tags: ["event-semantics", "semantic-roles", "coreference", "video"]
added: 2026-08-03T00:00:00+08:00
---

# Visual Semantic Role Labeling for Video Understanding

## One-line thesis

VidSitu 用动词、语义角色、实体共指和事件关系描述 10 秒电影片段中的复杂事件集合。

## Problem / Gap

动作标签不足以描述参与者角色、跨事件实体延续和事件间关系。

## Method

29K 个 10 秒电影片段、145K 个以 2 秒为单元的事件结构标注。

## Key Results

支持 verb、semantic role generation 和 event relation prediction 三类 VidSRL 子任务。

## Assumptions

2 秒事件单元足以捕获显著事件；文本共指可代表跨事件实体一致性。

## Limitations / Failure Modes

视频短；无像素轨迹、对象状态 before/after、长时情节和纠错标注。

## Reusable Ingredients

事件中层 schema、participant roles、entity coreference、event relations。

## Open Questions

能否将 semantic role/event relation 与 executable state effects 可靠对齐？

## Claims

无 claim 节点；需先通过实验与 proof-checker。

## Connections

[AUTO-GENERATED from graph/edges.jsonl — do not edit manually]

## Relevance to This Project

可作为“状态层”和“情节层”之间事件语义接口的参考。
