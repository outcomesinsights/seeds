---
id: seeds-83.2
title: Add full-text search (FTS5) to seeds database
status: resolved
type: idea
parent: seeds-83
created_at: 2026-02-13T17:40:38.037927+00:00
updated_at: 2026-03-12T14:29:24.595919+00:00
resolved_at: 2026-03-12T14:29:24.595910+00:00
tags:
  - search
  - database
converted_at: 2026-09-01T05:20:22.746832+00:00
---

ConPort has FTS5 search across decisions, custom data, and glossaries. Seeds currently only filters by status/type/tag — no content search. Adding FTS5 to the seeds SQLite database would be straightforward (SQLite has it built-in) and valuable for finding past deliberation context. Particularly useful when seeds accumulate — finding 'that thing we discussed about authentication' by searching content rather than scrolling through lists.
