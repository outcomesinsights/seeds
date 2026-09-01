---
id: seeds-69
title: "Web UI: Prettify markdown before rendering (fix LLM formatting issues)"
status: captured
type: idea
created_at: 2026-02-06T16:17:05.716769+00:00
updated_at: 2026-02-06T16:20:27.948599+00:00
tags:
  - ui
  - web
relationships:
  - target_id: seeds-68
    rel_type: relates-to
    created_at: 2026-02-06T16:17:05.323616+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

LLMs commonly generate malformed markdown: missing newlines between headers and lists, inconsistent spacing, etc. Prettify the markdown in the rendering pipeline (not changing stored content) to maximize rendering quality. This is a display-time transformation only.

Decision: Use a generalized markdown prettifier library rather than targeted regex fixes. Let it handle all common formatting issues comprehensively.
