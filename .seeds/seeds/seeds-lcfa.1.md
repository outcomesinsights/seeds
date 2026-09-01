---
id: seeds-lcfa.1
title: "The rickety multi-host sync splits into two problems: nothing runs the import, and the import that does run is whole-record LWW"
status: captured
type: exploration
parent: seeds-lcfa
created_at: 2026-08-26T03:39:41.214351+00:00
updated_at: 2026-08-26T03:39:41.214351+00:00
tags:
  - sync
  - hooks
  - merge
  - lww
  - multi-host
  - beads-inspired
  - dolt
  - 2026-08-25
relationships:
  - target_id: seeds-sdhc
    rel_type: relates-to
    created_at: 2026-08-28T17:36:41.309903+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Answering seeds-44ht: the felt pain is cross-host sync. Edits happen on separate hosts, a hook dumps the DB to JSONL, and then someone has to remember to pull the JSONL back into the local DB. Digging into what is actually wired up (this repo, 2026-08-25) shows two independent problems hiding behind one feeling. They have different fixes and only one of them is an argument for Dolt.

PROBLEM 1 — the import is not wired to anything.
- `seeds sync` already does the right thing: import (LWW) then export, with a divergence guard that refuses to overwrite JSONL records the DB cannot account for. The machinery exists.
- But nothing calls it. In this repo `core.hooksPath` is the default `.git/hooks`; `.pre-commit-config.yaml` has entries for ruff, pytest, `bd hooks run pre-commit`, and an explicit `bd export`, and NOTHING for seeds. `grep -rn seeds .git/hooks/{pre-commit,post-merge,post-checkout}` returns only an unrelated venv path.
- Meanwhile `.git/hooks/post-merge` exists and runs `bd hooks run post-merge`. So beads' DB refreshes itself after every pull and seeds' does not — that asymmetry is the "remember to" step, and it is the whole of the felt ricketiness.
- Note this also means the export side is manual here: nothing flushed the DB to `.seeds/seeds.jsonl` on commit either.
- Fix: a post-merge + post-checkout hook running `seeds sync`, and a pre-commit flush. Same mechanism beads already uses, no engine change. This is the cheap fix and it is probably 90% of the relief.

PROBLEM 2 — the merge is whole-record last-write-wins.
- `src/seeds/export.py` upserts by comparing `updated_at` per seed: JSONL strictly newer replaces the DB row, otherwise the DB row is left alone.
- So if host A edits a seed's content and host B edits the same seed's tags, the newer one wins WHOLESALE and the other host's edit is silently discarded. No conflict, no warning.
- Git's own merge of the JSONL has the same granularity for a different reason: one seed per line, so a two-host edit to the same seed is a line conflict, while edits to different seeds merge cleanly.
- This is the real Dolt argument, and it is narrower than "the DB should live in git": Dolt merges per CELL, so two hosts touching different fields of the same seed would merge cleanly, and a genuine same-field collision would surface as a conflict instead of vanishing.
- Cheaper alternatives worth pricing first: per-field timestamps, a conflict flag instead of silent LWW, or splitting a seed across multiple JSONL records so the line-merge granularity matches the edit granularity.

The order matters. Fixing 1 without 2 leaves a silent data-loss path but makes the day-to-day flow automatic. Fixing 2 without 1 leaves the remembering. Doing 1 first is also how you find out how often 2 actually bites — right now there is no signal at all, because LWW never reports what it dropped.
