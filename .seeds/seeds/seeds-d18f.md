---
id: seeds-d18f
title: If seeds and beads converge on the same storage architecture, should they share one engine with two front doors?
status: captured
type: question
created_at: 2026-08-26T04:02:15.750504+00:00
updated_at: 2026-08-26T04:02:15.750504+00:00
tags:
  - architecture
  - beads
  - convergence
  - strategy
  - storage
  - positioning
  - 2026-08-25
relationships:
  - target_id: seeds-lcfa.5
    rel_type: relates-to
    created_at: 2026-08-26T04:03:23.758121+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Surfaced inside the Go-rewrite analysis (seeds-lcfa.5) and pulled out here because it is a strategic question in its own right, not a detail of that option.

THE OBSERVATION. seeds and beads have independently arrived at the same architecture: a local database that git ignores, a git-tracked JSONL export that is the real sync channel, git hooks to keep the two in step, and worktree-aware resolution to the main repo's store. Verified 2026-08-25 — `git ls-files .beads` tracks only issues.jsonl, metadata.json, config.yaml, export-state.json and hooks, exactly mirroring what `.seeds/` tracks. The differences that remain are the data model (deliberation lifecycle vs task lifecycle) and the language (Python vs Go).

WHY IT MATTERS NOW. A Go rewrite for embedded Dolt would erase the language difference too, leaving two Go programs with near-identical storage layers and different schemas on top. That is the moment the question becomes expensive to ignore: answering it BEFORE a rewrite is cheap, answering it after means reconciling two Go codebases.

But note the question does NOT depend on the rewrite happening. If the per-seed-files direction wins instead (seeds-lcfa.4 option C), the same convergence argument applies to beads — issues could just as well be files that git merges — and the shared thing would be a sync/merge convention rather than a linked library.

THE FORMS AN ANSWER COULD TAKE:
- Stay separate, accept the duplication. Cheapest, and it keeps seeds free to change its storage without negotiating with beads.
- Share a storage/sync layer as a library, two CLIs on top. Requires the same language, or a stable file-format contract instead of a linked library.
- One engine, two front doors — beads and seeds as modes of the same tool. Maximum reuse, but it couples the deliberation lifecycle to the task lifecycle, and the whole positioning argument for seeds is that deliberation is NOT task tracking (see seeds-189 on the naming and category hazard).
- Share nothing but the CONVENTION: the export format, the hook wiring, the worktree resolution rule. Written down once, implemented twice. Cheap, honest about the language split, and it captures most of the value that keeps being re-derived.

THE COUNTERWEIGHT TO SHARING, and it is real: seeds' whole thesis is that deliberation is upstream of and different in kind from task tracking (seeds-168 positions it as upstream of intent). Merging the tools risks collapsing exactly the distinction the project exists to make. Sharing plumbing is not the same as sharing identity — but the pressure to unify the data model follows the plumbing more often than anyone plans for.

Not urgent. Should be answered before any rewrite is committed to, and revisited if beads changes its own storage story.
