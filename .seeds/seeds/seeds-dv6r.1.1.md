---
id: seeds-dv6r.1.1
title: Fence anything in a seed body that must stay verbatim
status: captured
type: decision
parent: seeds-dv6r.1
created_at: 2026-09-08T22:06:56.132333+00:00
updated_at: 2026-09-08T22:06:56.132333+00:00
tags:
  - storage
  - format
  - authoring
  - formatter
  - 2026-09-08
---

Ruled by @aguynamedryan, 2026-09-08, while settling the write-time formatter in
seeds-dv6r.1.

**Anything in a seed body that must survive as literal text gets a fence.** Logs,
command output, tracebacks, SQL, file listings, hand-aligned columns, YAML
samples — if the characters matter, they go in a fenced block.

This stops being style advice the moment the writer formats bodies. Measured
against mdformat, a fenced block is preserved byte for byte; an unfenced one is
not, and the damage is silent:

- a pasted traceback loses its indentation and gains escapes (`*args` -> `\*args`)
- a 2-space-indented SQL block is flattened to column 0, and under prettier its
  literal `count(*)` became `count(_)` (seeds-183, corpus-wide measurement)
- an unfenced YAML sample whose `---` lines CommonMark reads as setext headings
  collapses into a heading (an oimnibus seed)
- hand-aligned two-column blocks collapse to single spaces — 84 files corpus-wide

Every one of those is the author's choice of layout markdown does not have. A
fence is the construct that does have it, and it survives *any* formatter, which
is why this is the rule rather than "exclude the store from formatters".

The audience is agents, since agents write nearly every seed body. So the delivery
mechanism matters more than the rule: `seeds prime` is what actually reaches an
agent in any repo, which makes it the place this belongs — not one repo's
CLAUDE.md.
