---
id: seeds-29ar
title: "Measured: 0.6 and 0.7 output is byte-identical for every reading command — the storage change is invisible where it counts"
status: captured
type: exploration
created_at: 2026-09-01T15:55:59.282047+00:00
updated_at: 2026-09-01T15:56:09.110474+00:00
tags:
  - storage
  - "0.7"
  - differential
  - evidence
  - no-degradation
  - measured
  - 2026-09-01
relationships:
  - target_id: seeds-sdhc
    rel_type: relates-to
    created_at: 2026-09-01T15:56:08.537987+00:00
  - target_id: seeds-fkb8
    rel_type: relates-to
    created_at: 2026-09-01T15:56:08.686186+00:00
  - target_id: seeds-lcfa.6
    rel_type: relates-to
    created_at: 2026-09-01T15:56:08.828435+00:00
  - target_id: seeds-183
    rel_type: relates-to
    created_at: 2026-09-01T15:56:08.966177+00:00
  - target_id: seeds-dv6r
    rel_type: relates-to
    created_at: 2026-09-01T15:56:09.109878+00:00
---

The differential harness (bead seeds-4co.17) ran against real pre-0.7 stores on 2026-09-01, and the result is stronger than anyone predicted: **for most commands the 0.6 and 0.7 output is byte-identical.**

## What was measured

Four repos converted from a copy and compared command-for-command, 0.6+SQLite against 0.7+tree:

| repo | seeds | differences | unexplained |
| --- | --- | --- | --- |
| vocabulary_formats | 15 | 70 | **0** |
| epc | 34 | 157 | **0** |
| oimnibus | 52 | 235 | **0** |
| pman | 29 | 125 | **0** |

**130 seeds across 4 repos, zero unexplained differences.**

## The finding that matters

**`list`, `list --all`, `ready`, `deferred`, `recent`, `questions`, `blocked`, `tree` and `show` matched EXACTLY — byte for byte — on all four repos.** Every difference the harness reported concentrated in just three commands: `export`, `search` and `prime`.

And each of those three is a difference we chose on purpose:

- **`export`** — `format_version` dropped, `converted_at` and `parent` added. The field-set change the format ruled.
- **`search`** — ranked FTS5 is gone, so results are id-sorted rather than relevance-ordered, and Porter stemming is gone. The accepted casualty, ruled explicitly.
- **`prime`** — the static template changed; the generated digest itself is still compared in full.

So the storage change is, for the reading surface a human or an agent actually touches, **invisible**. That was the hope; it is now measured rather than hoped.

## The cross-repo result quietly indicts the OLD format

Over four repos, the retired recipe (`cat .seeds/seeds.jsonl | duckdb`) returned **128 rows** and the replacement (`seeds export --json | duckdb`) returned **130**.

The new one returned MORE. Both extra seeds had been in the 0.6 SQLite all along, and the committed JSONL had simply never carried them — the throttled-export staleness, sitting undetected in real repos. **The old cross-repo workflow was silently under-reporting**, and nobody could have known.

## What this does NOT establish, stated so the number is not overread

- **4 of 13 repos**, not all of them. Three were blocked by a converter crash on legacy `answers` rows, and six have not been run.
- **130 seeds, against the 309 in the seeds repo itself** — the largest and strangest corpus is not in this sample.
- **3 of the 12 allowlist entries never fired on real data** (`fixtures-dropped`, `jsonl-only-recovered`, `show-full-supersede`); they are covered by unit tests only, which the harness reports plainly rather than implying coverage it lacks.
- It compares **CLI output**, not lived experience. Whether deliberation *feels* the same over weeks is the half only @aguynamedryan can report.

## Why it is trustworthy

The harness refuses rather than reporting health when the corpus is empty on either side — the `seeds check` exits-0-on-an-empty-store shape, designed against this time. Three injected faults prove it can fail: dropping a seed produced 10 regressions, mutating a title 6, truncating a body 2. And a test walks the harness's own AST to fail if any finding cites an allowlist rule that carries no written justification.

Relates to seeds-sdhc, seeds-fkb8, seeds-lcfa.6, seeds-183, seeds-dv6r.
