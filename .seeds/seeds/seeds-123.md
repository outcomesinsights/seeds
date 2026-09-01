---
id: seeds-123
title: "ID prefix convention: project name, not entity type"
status: resolved
type: decision
created_at: 2026-03-12T15:19:08.064413+00:00
updated_at: 2026-03-20T20:43:20.143263+00:00
resolved_at: 2026-03-20T20:43:20.143256+00:00
resolution: "Confirmed: project name prefix, not entity type. Combined with sequential ID decision (seed-d023f612) — IDs will be seeds-1, seeds-2, etc."
tags:
  - model
  - architecture
relationships:
  - target_id: seeds-6
    rel_type: relates-to
    created_at: 2026-01-28T05:54:02.752699+00:00
  - target_id: seeds-49
    rel_type: relates-to
    created_at: 2026-01-28T21:00:22.070848+00:00
  - target_id: seeds-135
    rel_type: relates-to
    created_at: 2026-03-20T20:18:46.150545+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Decision: all seeds use the project name as their ID prefix (e.g., seeds- for this project). The q- prefix for questions is retired. Migrated questions get new project-prefixed IDs like all other seeds.

Rationale: IDs should identify which project a seed belongs to, not what type it is. Type is metadata, not identity.

Implementation: hardcoded default for now (no config file exists). Configurable per-project later if/when project-level configuration is added.
