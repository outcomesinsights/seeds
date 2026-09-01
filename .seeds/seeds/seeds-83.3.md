---
id: seeds-83.3
title: Typed relationship links between seeds
status: captured
type: idea
parent: seeds-83
created_at: 2026-02-13T17:40:39.806019+00:00
updated_at: 2026-02-24T17:04:24.597610+00:00
tags:
  - data-model
  - relationships
converted_at: 2026-09-01T05:20:22.746832+00:00
---

ConPort links have relationship types and descriptions (e.g., 'implements', 'contradicts'). Seeds links are currently untyped (relates-to only). Upgrading to typed links like 'supersedes', 'contradicts', 'refines', 'implements' would enrich the knowledge graph and give more semantic meaning to connections between seeds.


---
**Beads v0.50-v0.56 confirms this direction.** Beads now has exactly this in production: `supersedes`, `duplicates`, `replies_to`, `relates_to` plus blocking variants. The typed link model is proven at scale. Seeds should adopt at minimum `supersedes` and `duplicates` as they directly serve the deliberation domain (decisions replace each other, ideas turn out to be the same thing).
