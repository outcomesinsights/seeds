---
id: seeds-96
title: What CI/CD workflows do we need for a public beta?
status: resolved
type: question
created_at: 2026-02-27T15:07:00.529920+00:00
updated_at: 2026-02-27T15:07:00.529920+00:00
resolved_at: 2026-02-27T15:15:11.149269+00:00
relationships:
  - target_id: seeds-93
    rel_type: questions
    created_at: 2026-02-27T15:07:00.529920+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Comprehensive CI: pytest with coverage, linting (ruff), type checking (question of merit raised), auto-formatting (ruff format). GitHub Actions CI matrix testing across all non-EOL Python versions.
