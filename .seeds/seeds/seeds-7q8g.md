---
id: seeds-7q8g
title: Should seeds ship its commit-time check to the other repos that keep seed stores?
status: exploring
type: exploration
created_at: 2026-09-30T18:08:42.113398+00:00
updated_at: 2026-09-30T18:08:51.021459+00:00
---

**The question:** Should seeds offer the repos that use it a commit-time `seeds check`, the way the seeds repo itself runs one? If so, how: a documented pre-commit snippet, a `seeds` command that installs it, or `seeds doctor` running `check`?

**What exists today (verified 2026-09-30):**

- `seeds check` reads every seed file and reports damage: a title replaced by a path or URL, timestamps out of order or in the future, parent and cycle errors, links to seeds that don't exist, one-sided links, git conflict markers, duplicate bodies, and a mass-field-rewrite rule for one field changed across a large share of the store in one go. Violations exit non-zero; smells never do.
- Only the seeds repo runs it at commit: `.pre-commit-config.yaml` (the seeds-check entry) calls scripts/seeds_check_hook.py, which runs violations, `--against-git` and `--smells`. Other repos with seed stores (conceptql, code_collector, the vocabulary repos and others) have no such hook. An agent can commit a broken store there, and nothing notices until someone happens to run `seeds check`. `seeds doctor` points at `seeds check` but does not run it.
- The incident this guards against is seeds-wurl: a bulk agent edit clobbered 83 of 306 titles with a scratchpad path, and every existing check stayed green.

**Ruled nearby:** deleting a single seed is acceptable (Ryan, 2026-09-30, bead seeds-w9h closed won't-fix), because git keeps every seed file. So this question is about damage that corrupts a store, not about deletion.

**Open:** whether to ship it at all, which shape, and what it costs other repos per commit: runtime, tokens an agent pays reading its output, and whether its answer is deterministic. Measurements are appended below.

Came from bead seeds-dcn (found by the resolve-seeds-from-beads sweep of 2026-09-30, verifying seeds-sdhc), which was closed in favour of this seed because it is a product decision, not a task.
