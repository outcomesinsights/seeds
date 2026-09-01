---
id: seeds-152.3
title: "Decision: install seeds skills as a Claude Code plugin (option 2) if feasible, else as a packaged copy command (option 1)"
status: resolved
type: decision
parent: seeds-152
created_at: 2026-05-27T18:30:32.050102+00:00
updated_at: 2026-08-31T21:34:46.618522+00:00
resolved_at: 2026-08-31T21:34:46.618516+00:00
resolution: "Shipped, and option 2 was reached rather than the option 1 fallback: skills install as a Claude Code plugin under the seeds:* namespace matching beads:*, with 'seeds skills' as the management verb (beads seeds-4dw, seeds-9q6, seeds-dn7, seeds-wa0). Efficacy: none — the decision's own condition ('option 2 if the install is as smooth as option 1, else option 1 first') was the right shape, and the feasibility question it hedged against did not materialize. Proof it works: this resolution was produced by invoking seeds:resolve-seeds-from-beads."
tags:
  - install
  - distribution
  - plugin
  - skills
  - decision
  - namespace
relationships:
  - target_id: seeds-154
    rel_type: questioned-by
    created_at: 2026-05-27T18:30:37.499182+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

## The decision

Skills shipped with seeds should be distributed as a **Claude Code plugin** (option 2), provided we can make the install experience as smooth as a hypothetical `seeds skills install` command (option 1). If we can't — for example, if plugin install requires the user to run separate Claude Code commands or accept multiple prompts — we ship option 1 first and migrate to option 2 once tooling allows.

The strong preference for option 2 is driven by:
- The `seeds:*` namespace (matching `beads:*`) is what we want long-term anyway.
- Native Claude Code discovery, listing, versioning.
- Avoids inventing our own out-of-band install/update mechanism that we'd later replace.

## Scope rules

- **User-scoped, not project-scoped.** Skills go to `~/.claude/...` (or whatever the plugin equivalent is), available everywhere. This leaves room for users to add their own *project-level* customizations via `<project>/.claude/skills/` without conflicting with seeds defaults.
- **Update on CLI upgrade.** After `uv tool upgrade seeds`, running the install command (or its plugin equivalent) should re-install / refresh the bundled skills cleanly. The CLI version and skill versions stay in lockstep.
- **`--diff` flag worth shipping** even though it'll be rarely used. Someone reviewing what changed before re-installing will appreciate it.

## Open dependency

The hinge for option 2 viability: can the seeds CLI programmatically drive a Claude Code plugin install? See attached question.

## Reversibility

If plugin churn turns out to be brutal (mechanism changes, breakage), fall back to option 1. The skill content is portable between mechanisms — only the install path changes.
