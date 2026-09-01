---
id: seeds-lcfa.2
title: Dolt would not fix worktrees — that is a resolution problem with a ruled decision already sitting in seeds-191
status: captured
type: concern
parent: seeds-lcfa
created_at: 2026-08-26T03:40:53.579804+00:00
updated_at: 2026-08-31T20:02:49.208507+00:00
tags:
  - worktree
  - db-resolution
  - dolt
  - branching
  - beads-inspired
  - 2026-08-25
relationships:
  - target_id: seeds-191
    rel_type: relates-to
    created_at: 2026-08-26T03:40:53.696841+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Asked whether Dolt would make worktrees more reliable. It would not, and conflating the two risks parking a fix that is already decided.

WHY WORKTREES BREAK TODAY, precisely: `seeds.db` is gitignored (`.seeds/.gitignore` ignores `*.db`) while `seeds.jsonl` is tracked. So `git worktree add` produces a `.seeds/` holding a branch-snapshot JSONL and NO live DB, and `find_seeds_dir()` (src/seeds/db.py:110) just walks up the directory tree with no git awareness at all — so seeds bootstraps an empty or stale store in the worktree. That is a PATH RESOLUTION bug. The storage engine is not involved in it anywhere.

The engine swap does not touch it. Beads' `.beads/embeddeddolt/` is gitignored exactly like `seeds.db`, so a fresh worktree gets no Dolt data either. Beads fixed worktrees with resolution logic (FindBeadsDir + GetMainRepoRoot), not with Dolt. Adopting Dolt and changing nothing else leaves the identical hole.

The fix is already ruled on. seeds-191 carries @aguynamedryan's decision of 2026-07-10: from ANY git worktree, resolve to the MAIN repo's `.seeds/` for both reads and writes; main-repo root is dirname of `git rev-parse --git-common-dir`; SEEDS_DIR stays the only escape hatch; any git failure degrades to today's walk-up. Separate-DB-per-worktree was explicitly dropped. Scope is one function plus a git helper plus two integration tests. That seed is still `captured` — the decision has simply not been built.

The one genuinely Dolt-shaped version of the idea, for the record: worktree as Dolt BRANCH — each parallel agent's seeds land on their own branch and merge at integration with cell-level merge. That is a real design and it is the only place Dolt improves on the status quo here. But it is the isolated-per-worktree model that seeds-191 deliberately rejected in favour of "everyone points at main," so proposing it means reopening that decision, not implementing it. It also multiplies the concurrency question rather than removing it: several agents against one embedded engine directory is a heavier proposition than several processes against one SQLite file.

Practical consequence: seeds-191 should not wait on any Dolt question. It is cheap, decided, and independent of the engine — and the parallel-worktree bead workflows are hitting it now.
