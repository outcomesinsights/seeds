---
id: seeds-83.1
title: MCP server transport layer for seeds
status: resolved
type: idea
parent: seeds-83
created_at: 2026-02-13T17:40:35.366776+00:00
updated_at: 2026-02-13T18:35:00.031700+00:00
resolved_at: 2026-02-13T18:35:00.031694+00:00
tags:
  - mcp
  - architecture
relationships:
  - target_id: seeds-84
    rel_type: relates-to
    created_at: 2026-02-13T17:40:35.366776+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

The biggest actionable idea from ConPort. An MCP server for seeds would let AI agents interact with seeds natively — no Bash overhead, no prime injection needed. Agents would have direct tools like seeds_jot, seeds_show, seeds_explore. This would make seeds feel like a first-class AI capability rather than a CLI the agent happens to call. ConPort exposes 30+ MCP tools; seeds could expose its existing CLI commands as MCP tools.



## Updated After Beads MCP Investigation (2026-02-13)

Beads DOES have MCP (integrations/beads-mcp/) but explicitly recommends CLI+hooks over MCP for shell-enabled environments. The token tax is brutal: 1-2k tokens (CLI) vs 10-50k tokens (MCP schema overhead). The beads MCP server exists as a fallback for MCP-only environments like Claude Desktop, not as the preferred integration.

This significantly reframes this seed. An MCP server for seeds would be a nice-to-have for restricted environments, NOT the 'big actionable idea' initially assessed. The CLI+hooks pattern seeds already uses IS the beads-endorsed approach. Priority should be on improving the existing CLI integration (better prime, better hooks, maybe a skill) rather than building an MCP server.
