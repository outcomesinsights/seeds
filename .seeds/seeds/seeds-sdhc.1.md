---
id: seeds-sdhc.1
title: Conversion to the new format must be robust to diverged stores — union input, forks as conflict files, round-trip verified
status: captured
type: decision
parent: seeds-sdhc
created_at: 2026-08-31T20:05:23.116169+00:00
updated_at: 2026-09-01T02:33:12.092294+00:00
tags:
  - storage
  - migration
  - conversion
  - divergence
  - verification
  - idempotent
  - "0.7"
  - 2026-08-31
relationships:
  - target_id: seeds-fkb8
    rel_type: relates-to
    created_at: 2026-08-31T20:05:41.266165+00:00
  - target_id: seeds-ebg1
    rel_type: relates-to
    created_at: 2026-08-31T20:05:41.387636+00:00
  - target_id: seeds-1x6b
    rel_type: relates-to
    created_at: 2026-08-31T20:05:41.513012+00:00
  - target_id: seeds-02ur
    rel_type: relates-to
    created_at: 2026-08-31T20:05:41.629958+00:00
  - target_id: seeds-sdhc.2
    rel_type: relates-to
    created_at: 2026-08-31T20:05:42.012369+00:00
  - target_id: seeds-sdhc.5
    rel_type: relates-to
    created_at: 2026-08-31T20:09:48.826477+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

seeds-sdhc's open item #8 is one line ("the migration itself"), and its only stated requirement is that the converter be "re-runnable and non-destructive". @aguynamedryan's ruling on 2026-08-31 sets the bar higher and in plain terms: **"just fucking make sure that we get the data in correctly."** Robust conversion is a first-class deliverable of 0.7, including repos whose DB and JSONL have diverged.

## Divergence is four conditions, and only three are auto-resolvable

Per ID, classify before converting anything:

1. **DB only** — never exported. seeds-fkb8 itself was in this state on 2026-08-28.
2. **JSONL only** — the import aborted above it, or skipped it. @markdanese's 40 seeds (seeds-1x6b).
3. **Both, DB content extends disk content** — the ordinary append. `db_extends_disk`'s own docstring records 41 of 42 content edits across 67 commits were literal appends, so this is the common case and the DB wins.
4. **Both, neither prefixes the other** — a genuine fork. Today's permanent deadlock (seeds-ebg1).

Only 1-3 may be resolved by rule. **Case 4 must never be auto-resolved.** Picking a winner there is precisely the silent-collapse error seeds-sdhc caught itself making twice — once for `merge=union` plus timestamp collapse, and once already recorded about cr-sqlite in seeds-lcfa.4.

## The input is the union, not either side

Convert from `DB ∪ JSONL`, per ID and per field. Never "convert the DB, then reconcile the JSONL against it" — that reinstates the derived-store-overwrites-durable-store shape (seeds-fkb8) inside the migration itself.

## A fork converts to a file, not to an error

Emit `<id>.md` carrying both bodies with git conflict markers. This turns the deadlock into an ordinary merge conflict resolved with ordinary merge tooling. The new architecture is good at exactly one thing the old one was not: representing a conflict as text a human can read.

Today the same situation is cleared by hand-rebuilding a body and handing it back — better than it was, since ccee855 moved that off argv and onto `--content-file`, but still a manual reconstruction where a conflict file would be a normal edit.

## Git history is an input, not just provenance

The title incident (see the incident seed) proves the DB and the JSONL can agree and both be wrong. The converter should mine the ~100 commits touching `.seeds/seeds.jsonl` — for real per-seed dates and authors as seeds-sdhc already wanted, and as the **repair oracle** for corruption both live stores share.

## Verification is part of the converter, not a follow-up

Re-read the emitted markdown tree, rebuild the record set, diff it field-by-field against the union input, and fail on any difference outside an explicit normalization allowlist (whitespace, key order). The data-pipeline standard's rule applies directly: the code deciding "clean" is itself code that can be silently wrong, so it must be tested on hand-built inputs with hand-computed answers, and must score the whole corpus rather than a sample.

The repair in 1afc51c is a working dry run of this: 306 records in and out, id set unchanged, 83 titles restored, 0 path-shaped titles remaining, no other field differing on any record.

## Re-runnable should mean byte-idempotent

A second run against an unchanged store must leave `git diff` empty. Stronger than "non-destructive", and much cheaper to assert in a test.

## It is a shipped verb, not a scripts/ one-shot

13 repos on titan carry a `.seeds/`, @markdanese converts on his own schedule at a version we will not choose, and seeds-02ur (36 orphaned rows from the v2 question-seeds migration) is standing evidence that one-shot migrations here leave debris. Ship it with tests.

Relates to seeds-sdhc, seeds-fkb8, seeds-ebg1, seeds-1x6b, seeds-faxd, seeds-02ur.
