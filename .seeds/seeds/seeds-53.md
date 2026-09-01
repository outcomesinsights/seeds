---
id: seeds-53
title: Built-in web UI for viewing seeds
status: captured
type: idea
created_at: 2026-02-05T21:23:39.989476+00:00
updated_at: 2026-02-05T21:29:36.096086+00:00
tags:
  - ui
  - future
relationships:
  - target_id: seeds-54
    rel_type: relates-to
    created_at: 2026-02-05T21:23:39.989476+00:00
  - target_id: seeds-55
    rel_type: relates-to
    created_at: 2026-02-05T21:23:39.989476+00:00
  - target_id: seeds-56
    rel_type: relates-to
    created_at: 2026-02-05T21:23:39.989476+00:00
  - target_id: seeds-57
    rel_type: relates-to
    created_at: 2026-02-05T21:23:39.989476+00:00
  - target_id: seeds-58
    rel_type: relates-to
    created_at: 2026-02-05T21:23:39.989476+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Seeds is more human-facing than Beads, so needs better human accessibility. CLI is fine for capture and AI interaction, but humans need a visual way to browse, filter, and see relationships. Beads has a third-party UI; seeds should have this built-in. Possible approaches: 1) Simple local web server (seeds serve) with read-only view 2) Static HTML export (seeds export --html) 3) TUI (terminal UI) as intermediate step. Priority: higher than typical 'nice to have' because seeds is fundamentally a human deliberation tool.
