---
id: seeds-64
title: "Web UI: Column filtering for all columns"
status: captured
type: idea
created_at: 2026-02-06T16:17:02.536442+00:00
updated_at: 2026-02-06T16:20:26.012338+00:00
tags:
  - ui
  - web
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Decision: When filtering in nested view, matching children whose parents don't match get bumped to top-level visually. Try this approach and see how it feels.

Implementation: Client-side JavaScript filtering (dataset size is small-to-medium, keeps things simple with Pico CSS approach).
