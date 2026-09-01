---
id: seeds-142.2
title: seeds recent --since=<date> — incremental-ingestion view of recent activity
status: resolved
type: idea
parent: seeds-142
created_at: 2026-05-18T15:57:48.158887+00:00
updated_at: 2026-08-31T21:34:29.191569+00:00
resolved_at: 2026-08-31T21:34:29.191562+00:00
resolution: "Shipped as 'seeds recent --since' (bead seeds-2or), a thin alias for 'list --since=<value> --sort=updated' with a 7d default, accepting ISO dates, relative windows (7d/2w/3m/1y), and today/yesterday. Efficacy: none needed. The seed left 'dedicated command vs flag on list' open and implementation answered it with both — a flag on list, aliased by a verb — which is a better answer than either option it posed."
tags:
  - feature
  - cli
  - ai-ux
  - incremental
relationships:
  - target_id: seeds-87
    rel_type: relates-to
    created_at: 2026-05-18T15:58:20.305194+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Problem:** User's 5/12 prompt: 'focus only on the dates I haven't read up to.' Claude had to derive 'what's been touched since 2026-05-08' from updated_at timestamps embedded in seed bodies. No CLI primitive answers 'what changed since X.'

**Proposed command:** `seeds recent [--since=<date>] [--limit=N] [--status=...]`

**Output:** Same one-liner format as `seeds list`, sorted by updated_at desc.

**Use cases:**
- 'Continue an incremental transcript-incorporation pass' (the seeds-142 workflow)
- 'What did the team touch since I was last in this project?'
- Feeds the 'Recently Updated' section of the proposed seeds-87 prime digest

**Implementation question:** Build as dedicated command vs add `--since` + `--sort=updated` flags to existing `seeds list`? Dedicated command is more discoverable; flags reuse existing code. Lean: add flags to `list`, and have `recent` be a thin alias with sensible defaults (e.g. last 7 days).
