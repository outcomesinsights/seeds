---
id: seeds-sdhc.2
title: Detection under files-as-truth is content plausibility — and the two-store doctor vanishes, so it must be replaced not extended
status: captured
type: decision
parent: seeds-sdhc
created_at: 2026-08-31T20:05:23.254050+00:00
updated_at: 2026-08-31T20:05:32.248583+00:00
tags:
  - storage
  - detection
  - check
  - doctor
  - plausibility
  - parse-policy
  - hook
  - "0.7"
  - 2026-08-31
relationships:
  - target_id: seeds-wurl
    rel_type: relates-to
    created_at: 2026-08-31T20:05:41.136836+00:00
  - target_id: seeds-ebg1
    rel_type: relates-to
    created_at: 2026-08-31T20:05:41.767259+00:00
  - target_id: seeds-dgyw
    rel_type: relates-to
    created_at: 2026-08-31T20:05:41.893176+00:00
  - target_id: seeds-sdhc.1
    rel_type: relates-to
    created_at: 2026-08-31T20:05:42.012369+00:00
  - target_id: seeds-sdhc.3
    rel_type: relates-to
    created_at: 2026-08-31T20:09:48.139750+00:00
  - target_id: seeds-sdhc.4
    rel_type: relates-to
    created_at: 2026-08-31T20:09:48.362602+00:00
  - target_id: seeds-tz66
    rel_type: relates-to
    created_at: 2026-08-31T22:21:03.188995+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

@aguynamedryan ruled on 2026-08-31: detection stays the enforcement strategy (seeds-sdhc), and its content is **plausibility checking**.

## The regression nobody had named

Nearly all of today's `doctor` checks the *relationship between two stores* — JSONL readable, JSONL and DB agree, `find_divergence` clean. Under files-as-truth **there is no second store, so those checks become vacuous and simply disappear.** If `check` is scoped only to "did an agent violate the file format", 0.7 ships with strictly less detection than 0.6 has. That is the thing to design against.

## What replaces it is a different job

Format validity is not the gap. The 83 clobbered titles parsed perfectly — a path is valid free text. The checks that matter ask whether a value is *plausible*:

- a title that is a filesystem path, or a URL, or empty
- a body that is empty, or byte-identical to another seed's
- git conflict markers left in a file
- `updated_at` before `created_at`; a future timestamp
- a dotted ID (`seeds-lcfa.6.1`) with no parent file — 75 of 304 IDs are dotted
- a relationship naming a file that does not exist
- frontmatter that will not parse; a `status` outside the closed set

**On relationships specifically:** the orphan check already exists and passes (549 relationships, no orphans, verified 2026-08-31). What changes under files is only its mechanism — a foreign key becomes a file-existence test, and edges written at both ends with no transaction (seeds-ebg1) make a *symmetry* check newly necessary alongside it.

## `check --against-git`

Diff every field against its value at the previous commit and flag mass single-field changes. This is the detector that catches 83 titles turning into paths, in under a second. It is also the right hook gate: a commit rewriting 87 files has no cheap human review, and demanding confirmation for that shape subsumes gating `D` and `R` in `git diff --name-status`.

## Strict reads, and `check` is what makes strictness survivable

This answers seeds-sdhc's open item #1 (parse policy for invalid values on read), and it collapses that question into this one rather than leaving them separate. Files-as-truth makes every command a parser, so lenient reads reintroduce exactly the silent wrongness the rewrite exists to escape. Reads go strict. `check` exists so that a strict read failing on the first bad file is not the only feedback channel — it names every bad file in one pass, with a remediation per finding.

## Two tiers

- **Violations** — fail, exit non-zero, block the commit.
- **Smells** — report only. Supersession discipline can only ever live here: a long body with many commits of history and no `## Superseded` fold is a tending candidate, never an error. Naming the tier keeps discipline-shaped checks from being promoted into gates they cannot support.

## Three entry points, one implementation

`seeds check` by hand, the git pre-commit hook, and — the one seeds-sdhc did not list — **inside the converter, run against its own output before the source store is left alone.**

Relates to seeds-sdhc, seeds-ebg1, seeds-fkb8, seeds-dgyw.
