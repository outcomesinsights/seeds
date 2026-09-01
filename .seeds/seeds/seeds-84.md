---
id: seeds-84
title: Explore why beads doesn't use MCP
status: exploring
type: exploration
created_at: 2026-02-13T17:40:48.388550+00:00
updated_at: 2026-02-13T17:52:10.791129+00:00
tags:
  - mcp
  - beads
  - architecture
relationships:
  - target_id: seeds-83.1
    rel_type: relates-to
    created_at: 2026-02-13T17:40:35.366776+00:00
  - target_id: seeds-85
    rel_type: questioned-by
    created_at: 2026-02-13T17:52:24.522966+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Beads is our lodestone project that seeds follows. ConPort analysis surfaced MCP as the most actionable idea for seeds — but beads doesn't use MCP either. Beads uses the same pattern as seeds: CLI commands invoked via Bash by AI agents, with a prime command for context injection and hooks for auto-integration. Before seeds adopts MCP, need to understand: Is there a deliberate reason beads avoids MCP? Is it a maturity/priority thing, or a philosophical choice? What would beads gain or lose from MCP? If beads eventually adopts MCP, seeds should follow; if beads deliberately avoids it, seeds should understand why.



## Investigation Findings (2026-02-13)

### Key Discovery: Beads DOES have MCP!

Contrary to our initial assumption, beads has a full MCP server at `integrations/beads-mcp/`. It's not that beads avoids MCP — it offers BOTH approaches and explicitly recommends CLI over MCP for shell-enabled environments.

### The Token Tax

The beads docs state the trade-off clearly:
- **CLI + hooks**: ~1-2k tokens
- **MCP**: 10-50k tokens (tool schema overhead)

This is a 10-50x cost difference. Every MCP session pays this tax upfront just to describe the available tools, before any actual work happens.

### Beads' Position: CLI is Primary, MCP is Secondary

From the beads-mcp README: 'For environments with shell access...the CLI + hooks approach is recommended over MCP.'

MCP exists for environments that LACK shell access (e.g., Claude Desktop). It's not the preferred path — it's the fallback for restricted environments.

### The MCP Architecture

The beads MCP server:
- Wraps bd CLI commands via subprocess (not a separate implementation)
- Uses per-project daemon architecture (LSP-style, Unix domain sockets)
- Exposes 13 tools (create, list, ready, show, update, close, dep, blocked, stats, reopen, set_context, init, quickstart)
- Returns BriefIssue objects (6 fields) for '97% context reduction vs full issue objects'
- Supports multi-workspace routing

### Community Evidence: CLI Integration is the Pain Point

GitHub issue #225 ('Finding Claude is struggling to use bd consistently') and #486 ('Claude progressively forgets beads workflow') reveal that the real challenge is NOT the transport layer — it's getting agents to consistently USE beads at all, regardless of CLI vs MCP.

Yegge's response to #486: The solution is better hooks (SessionStart + PreCompact), not switching to MCP. The hooks re-inject `bd prime` context after compaction.

Community solutions converge on: hooks, skills, and structured end-of-session protocols — all CLI-based.

### What This Means for Seeds

1. **MCP is not the answer we thought it was.** The token tax alone makes it a worse default than CLI+hooks for Claude Code.
2. **Seeds already follows the right pattern.** CLI + prime + hooks is the proven beads approach.
3. **If seeds adds MCP, it should be secondary** — a fallback for MCP-only environments, not the primary integration.
4. **The real opportunity is improving the CLI integration**: better hooks, better prime output, maybe a skill.
