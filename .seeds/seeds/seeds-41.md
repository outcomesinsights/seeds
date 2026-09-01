---
id: seeds-41
title: Types could be inferred from relationships rather than declared (SNOMED insight)
status: captured
type: idea
created_at: 2026-01-28T20:52:39.298905+00:00
updated_at: 2026-01-28T20:53:02.731295+00:00
tags:
  - model
  - architecture
relationships:
  - target_id: seeds-16
    rel_type: relates-to
    created_at: 2026-01-28T05:55:39.401266+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

From SNOMED vocabulary: concepts are defined by the relationships they have, not explicit type declarations.

Applied to seeds: if a seed has an 'answers' relationship pointing to it, that implies the target is a question. Type emerges from relationship structure rather than being declared upfront.

Relates to the polymorphic model question - maybe we don't need explicit types at all.
