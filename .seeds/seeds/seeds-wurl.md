---
id: seeds-wurl
title: An agent's bulk sweep clobbered 83 of 306 titles with a scratchpad path, and every divergence check stayed green
status: captured
type: concern
created_at: 2026-08-31T20:05:22.988769+00:00
updated_at: 2026-08-31T20:05:32.007353+00:00
tags:
  - incident
  - data-loss
  - detection
  - plausibility
  - bulk-rewrite
  - git-as-oracle
  - storage
  - 2026-08-31
relationships:
  - target_id: seeds-1x6b
    rel_type: relates-to
    created_at: 2026-08-31T20:05:40.576442+00:00
  - target_id: seeds-fkb8
    rel_type: relates-to
    created_at: 2026-08-31T20:05:40.699629+00:00
  - target_id: seeds-ebg1
    rel_type: relates-to
    created_at: 2026-08-31T20:05:40.886339+00:00
  - target_id: seeds-sdhc
    rel_type: relates-to
    created_at: 2026-08-31T20:05:41.011821+00:00
  - target_id: seeds-sdhc.2
    rel_type: relates-to
    created_at: 2026-08-31T20:05:41.136836+00:00
  - target_id: seeds-sdhc.5
    rel_type: relates-to
    created_at: 2026-08-31T20:09:48.956658+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

On 2026-08-31, commit 4144e8f ("chore(seeds): attribute Ryan as @aguynamedryan across the seed corpus") replaced the **title of 83 of 306 seeds** with the scratchpad path the sweeping agent was using as its working file: `/tmp/claude-1001/.../ry-seeds-<id>.md`.

Found by accident, minutes into an unrelated storage review, three days and three commits after it landed. Repaired in 1afc51c from 63a47ca, the commit immediately preceding the sweep.

## Not a CLI bug

`seeds update --content-file` never touches the title (`_resolve_content`, cli.py:261; the title branch is independent at cli.py:1176). The sweep's own commit message says it was "applied through `seeds update --replace --content-file`" — the loop passed the same path to `-t` as well. An agent bug, and the CLI had no reason to refuse it: a title is free text, and a path is valid free text.

## Why this reframes the storage deliberation

**The two stores agreed, and both were wrong.** Every divergence mechanism seeds has — `find_divergence`, `db_extends_disk`, the export refusal, `doctor`'s sync check — compares the DB against the JSONL. All of them were green throughout, correctly, because both sides were written from the same bad edit. Divergence was never the failure mode here.

This matters for two conclusions the storage work had reached:

- **seeds-ebg1's "the observed pain here is validation, not merging" is right and did not go far enough.** Validation was scoped to *parse* failures — a `seed_type` or `status` value that no enum accepts. This record parsed perfectly. What failed is *plausibility*: no check asks whether a title looks like a title.
- **Git history is the third source, and the only one that can repair.** seeds-sdhc lists mining the ~100 commits of `seeds.jsonl` history as open item #8, framed as a nice-to-have for reconstructing per-seed history with real dates and authors. This incident promotes it: when both live stores carry the same corruption, git is the only oracle. The repair was possible solely because the JSONL is tracked and the last-good value was one commit back.

## The general shape

A bulk agent rewrite touching 87 records in one commit is exactly the operation with no cheap review — the diff is 174 lines of JSONL and nobody reads it. That shape (mass single-field change across most of the corpus) is trivially detectable and was not detected. See seeds-sdhc.2.

Relates to seeds-1x6b, seeds-fkb8, seeds-ebg1, seeds-sdhc.
