---
id: seeds-88
title: Graph visualization for deliberation trees
status: captured
type: idea
created_at: 2026-02-24T17:05:52.174450+00:00
updated_at: 2026-02-24T17:05:58.458124+00:00
tags:
  - visualization
  - graph
  - beads-inspired
relationships:
  - target_id: seeds-6
    rel_type: relates-to
    created_at: 2026-01-28T05:54:02.752699+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Beads v0.50+ added `bd graph` — horizontal DAG visualization in terminal, DOT format, and HTML. For a task tracker, this shows dependency chains. For a deliberation tool, a graph would show something more interesting: how ideas branch, merge, and supersede each other.

A `seeds graph` could visualize:
- Parent-child deliberation hierarchies
- `supersedes` chains showing how decisions evolved
- `related_to` clusters showing idea neighborhoods
- Question→answer resolution paths
- Convergence patterns (many seeds resolving into one decision)

This is arguably *more* valuable for seeds than for beads — understanding the shape of deliberation is central to the tool's purpose. Beads' implementation (terminal ASCII, DOT, HTML) provides a concrete reference.

Could integrate with the existing web UI as an interactive view.
