---
id: seeds-85
title: Should seeds build an MCP server at all, or just invest in better CLI integration (improved prime output, a skill, better hooks)?
status: resolved
type: question
created_at: 2026-02-13T17:52:24.522966+00:00
updated_at: 2026-02-13T17:52:24.522966+00:00
resolved_at: 2026-02-13T18:33:58.173900+00:00
relationships:
  - target_id: seeds-84
    rel_type: questions
    created_at: 2026-02-13T17:52:24.522966+00:00
  - target_id: seeds-169
    rel_type: relates-to
    created_at: 2026-06-15T22:02:27.789392+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Invest in better CLI integration first. The beads evidence is clear: CLI+hooks costs 1-2k tokens vs 10-50k for MCP, and beads explicitly recommends CLI for shell-enabled environments. The community pain points (#225, #486) are about agent consistency, not transport — solved by better hooks, prime output, and skills. An MCP server could come later as a secondary target for MCP-only environments like Claude Desktop, but it's not where the leverage is.
