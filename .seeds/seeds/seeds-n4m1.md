---
id: seeds-n4m1
title: "seeds setup claude: an honest name for installing seeds' Claude Code integration, with skills install kept as an alias"
status: captured
type: decision
created_at: 2026-09-30T20:10:38.030701+00:00
updated_at: 2026-09-30T20:10:38.030701+00:00
---

**The question:** The command that installs seeds' Claude Code integration is `seeds skills install`. Once bead seeds-oiy lands, it also installs SessionStart and PreCompact hooks that inject `seeds prime`. The name then undersells what it does: an agent or user looking for "set seeds up with Claude Code" won't find it under "skills". beads names the same job `bd setup claude`.

**Why it came up:** Option (c) on seed seeds-i9y6.1 (2026-09-30), while settling that seeds must install its own session hooks without relying on home-manager.

**RULED (Ryan, 2026-09-30):** add `seeds setup claude` as the honest name for installing seeds' Claude Code integration (plugin, skills and session hooks), mirroring `bd setup claude`. Keep `seeds skills install` working as an alias, so existing docs, scripts and muscle memory don't break. `--reinstall` / `--upgrade` behave the same under both names. Implementation: see the bead sourced from this seed.

**Left open for the implementer:** whether `seeds setup` gets a `--check` (as `bd setup claude --check` has; it overlaps the doctor bead's plugin check, so share one detector); whether other agents (codex, cursor and others, as `bd setup` has recipes for) are in scope. Default: claude only.
