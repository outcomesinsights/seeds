---
id: seeds-7q8g
title: Should seeds ship its commit-time check to the other repos that keep seed stores?
status: exploring
type: exploration
created_at: 2026-09-30T18:08:42.113398+00:00
updated_at: 2026-09-30T18:14:56.068033+00:00
---

**The question:** Should seeds offer the repos that use it a commit-time `seeds check`, the way the seeds repo itself runs one? If so, how: a documented pre-commit snippet, a `seeds` command that installs it, or `seeds doctor` running `check`?

**What exists today (verified 2026-09-30):**

- `seeds check` reads every seed file and reports damage: a title replaced by a path or URL, timestamps out of order or in the future, parent and cycle errors, links to seeds that don't exist, one-sided links, git conflict markers, duplicate bodies, and a mass-field-rewrite rule for one field changed across a large share of the store in one go. Violations exit non-zero; smells never do.
- Only the seeds repo runs it at commit: `.pre-commit-config.yaml` (the seeds-check entry) calls scripts/seeds_check_hook.py, which runs violations, `--against-git` and `--smells`. Other repos with seed stores (conceptql, code_collector, the vocabulary repos and others) have no such hook. An agent can commit a broken store there, and nothing notices until someone happens to run `seeds check`. `seeds doctor` points at `seeds check` but does not run it.
- The incident this guards against is seeds-wurl: a bulk agent edit clobbered 83 of 306 titles with a scratchpad path, and every existing check stayed green.

**Ruled nearby:** deleting a single seed is acceptable (Ryan, 2026-09-30, bead seeds-w9h closed won't-fix), because git keeps every seed file. So this question is about damage that corrupts a store, not about deletion.

**Open:** whether to ship it at all, which shape, and what it costs other repos per commit: runtime, tokens an agent pays reading its output, and whether its answer is deterministic. Measurements are appended below.

Came from bead seeds-dcn (found by the resolve-seeds-from-beads sweep of 2026-09-30, verifying seeds-sdhc), which was closed in favour of this seed because it is a product decision, not a task.

## Measured 2026-09-30 (titan): cost and determinism of `seeds check` across all 26 seed stores

Method: the working-tree seeds binary (0.7.0 at f607eb5 plus later commits), read-only, run from each repo root. Each store was run twice with plain `seeds check` and twice with the hook's full command (`seeds check --against-git --smells`). Tokens are estimated as characters / 4, so treat them as approximate. Raw data: claude_stuff/check-measure/check-20260930-110917.tsv in the seeds checkout (gitignored, titan only).

**Time**

- Plain `seeds check` (violations only): 0.2-0.6 s on every store, from 1 seed to 568.
- The full command: 0.5-32 s. The largest are code_set_catalog (568 seeds) 31-32 s, code_collector (242) 11 s, icd10cm (114) 8 s, seeds (343) 7 s, home-manager (196) 5-6 s.
- Split by flag on the two largest stores:
  - code_set_catalog: plain 0.5 s, `--against-git` 1.5 s, `--smells` 31.5 s.
  - seeds: plain 0.4 s, `--against-git` 1.1 s, `--smells` 7.0 s.
    `--smells` is nearly all the cost. Its per-seed history smells (for example unsuperseded-long-body, which counts commits) scale with store size and history.

**Tokens an agent pays**

- Plain `seeds check`: about 9 tokens, one line ("N files, no violations").
- The full command: about 44-5,500 tokens. code_set_catalog is the largest (220 lines), then seeds (~3,500) and jigsaw-diagram-editor (~1,800). Nearly all of it is smells, which never gate.
- As a commit hook under prek, a PASSING hook's output is hidden (one "Passed" line). Only a failing hook prints everything, including all the smells.

**Determinism**

- 52 of 52 run pairs were byte-identical. For a given repo state the answer is deterministic.
- Inputs that can legitimately change the answer: the seed files; git HEAD and HEAD~1 (`--against-git` compares them, falling back to HEAD~1 vs HEAD when nothing is staged); the clock (the future-timestamp violation); and the repo's other tool configs (the tool-config-includes-store smell).

**What it found in stores that have no commit-time check (3 of 26 fail the full command)**

- gator: 1 seed body rewritten in place (the body changed while updated_at did not), today, which is a formatter's signature. Plus 5 smells.
- mani: 5 seed bodies rewritten in place, stamps from 2026-02-26. Unnoticed for seven months.
- marketscan_mdcd: a FALSE ALARM for this purpose. Its latest commit is a legitimate `seeds rename-prefix` (seed- to mdcd-, 596555b), and `--against-git` reports it as a 95% mass change ("158 deleted"). This is the documented case that needs `SKIP=seeds-check` on the rename commit. As a standing check, it keeps failing until the next commit moves HEAD.
- Plain `seeds check` passes on all 26.

**What this suggests (not ruled)**

- A shipped commit-time check could run violations plus `--against-git` (about 2 s, small output, deterministic, and it catches the in-place rewrites found above) and leave `--smells` out of the commit path. `--smells` costs about 94% of the time and most of the output, and it never gates.
- A rename-prefix commit needs to be recognized, or the escape hatch named in the refusal. Today it reads as mass deletion.
