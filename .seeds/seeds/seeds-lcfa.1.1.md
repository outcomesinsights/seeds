---
id: seeds-lcfa.1.1
title: "Immediate cheap win: wire seeds sync into git hooks so the DB stops needing to be refreshed by hand"
status: captured
type: idea
parent: seeds-lcfa.1
created_at: 2026-08-26T04:03:14.571300+00:00
updated_at: 2026-08-26T04:03:14.571300+00:00
tags:
  - hooks
  - sync
  - git
  - ready
  - cheap-win
  - beads-parity
  - 2026-08-25
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Problem 1 from seeds-lcfa.1, pulled out on its own because it is ready, cheap, independent of every storage decision above it, and it is the fix that removes most of the felt ricketiness.

THE GAP, verified in this repo 2026-08-25. `seeds sync` already does the right thing — import with last-write-wins, then export, with a divergence guard that refuses to overwrite JSONL records the database cannot account for. Nothing calls it. `core.hooksPath` is the default `.git/hooks`; `.pre-commit-config.yaml` has entries for ruff, pytest, `bd hooks run pre-commit` and an explicit `bd export`, and nothing at all for seeds; grepping `.git/hooks/{pre-commit,post-merge,post-checkout}` for "seeds" returns only an unrelated venv path. Meanwhile `.git/hooks/post-merge` runs `bd hooks run post-merge`, so beads' database refreshes itself after every pull and seeds' does not. That asymmetry IS the remembering.

Note the export side is manual here too: nothing flushes the DB to `.seeds/seeds.jsonl` on commit, so every seed captured in this session needed an explicit `seeds sync --flush-only` before `git add`.

THE SHAPE OF THE FIX — the same wiring beads already uses:
- post-merge and post-checkout: run the import so a pull or a branch switch leaves the DB current.
- pre-commit: flush the DB to the tracked JSONL and stage it, so a `seeds jot` cannot be stranded by a commit that happens minutes later.

TRAPS THAT ARE ALREADY DOCUMENTED AND MUST NOT BE REDISCOVERED:
- The pre-commit framework installs into `.git/hooks/` and refuses to install while `core.hooksPath` is set, which is exactly what `bd init` does. The coexistence wiring has failure modes that are all SILENT — the commit succeeds and the export just stops. The procedure lives in ~/.config/home-manager/docs/beads-git-hooks.md and should be read rather than reconstructed.
- Committing `.seeds/seeds.jsonl` and `.beads/issues.jsonl` in separate commits deadlocks the stash-then-restore against the flush and export hooks. They go in one commit when both are dirty.
- The export must be synchronous in the hook. Beads learned this the hard way: its throttled auto-export let a create survive in the DB while a quick commit shipped without it.

WHY IT COMES FIRST regardless of where the storage question lands: it costs almost nothing, it removes the daily friction immediately, and it is the only way to find out how often problem 2 actually bites. Whole-record LWW currently reports nothing about what it discarded, so there is no evidence either way — automate the sync, and the collisions start showing up as observable events instead of silent losses.

CAVEAT worth stating plainly: this makes the flow automatic, it does NOT make it correct. Auto-importing more often means LWW runs more often, and every run can still silently drop the losing edit. If this lands alone, it should land with at least a log line naming what the import overwrote.
