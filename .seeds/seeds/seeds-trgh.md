---
id: seeds-trgh
title: Seeds' core premise (ideas that mature over time) is in tension with the perishability of the measurements they rest on — should the tool surface a measurement's AGE?
status: captured
type: idea
created_at: 2026-08-27T16:45:30.008775+00:00
updated_at: 2026-08-31T20:02:50.079575+00:00
tags:
  - seeds
  - staleness
  - measurement
  - show
  - ux
  - from-consumer
  - 2026-08-27
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Raised from a consuming project (code_set_catalog, seed csc-xlkq) after five errors in one day, in
three repos, all traceable to the same thing: a factual premise inside a seed or a code comment that
was true when written and was read as true now.

## The observation about SEEDS specifically

Seeds exist to hold ideas that need time to grow. That is the tool's whole premise, and it is also
where this bites: **the longer a seed matures, the more its factual basis has moved.** The value
proposition and the failure mode are the same mechanism.

A concrete case. A bead was filed 2026-06-25 arguing "concept_ancestor is EMPTY for ICD10CM —
hierarchy lives ONLY in concept_relationship." True when written. Upstream derived the closure in the
interval. The bead sat at P3 for two months, arguing from the old reading, while the thing it was
waiting for had quietly arrived. Nobody was careless; nothing re-measured it, because nothing could.

## The part that suggests a TOOL affordance rather than only a habit

**Content inside one seed has wildly different half-lives, and the format does not distinguish
them:**

    a ruling        "@aguynamedryan chose interval-valued over per-edition"   permanent — a fact about a choice
    reasoning       "because per-edition forces a read-time         long — survives its own numbers
                     re-derivation"
    a measurement   "concept_ancestor holds 0 ICD10CM edges"        perishable, and SILENTLY
    another system  "upstream ships an icd10cm_flag table"          perishable fastest of all

One seed in that project (csc-4yq6) contains all four. Its rulings are as valid today as when
written. Its row counts were wrong within a week. A reader has no way to tell which is which except
by prose convention.

## What the convention already does, and where it stops

That project's house style writes "measured 2026-08-27 against ohdsi20260625" — and every time it was
followed, someone could tell the number was old. Every time it was not, someone acted on a stale one.
So the convention WORKS and is simply not load-bearing: nothing prompts it, nothing surfaces it, and
`seeds show` renders a two-month-old count identically to a fresh one.

## Sketch, offered as a starting point rather than a design

- A way to mark a block as a measurement with a date and an instrument — a convention `seeds` knows
  about rather than only prose.
- `seeds show` surfacing the AGE of such a block, so an old number announces itself the way a stale
  branch does in `git`.
- Possibly: `seeds ready` / `seeds list` flagging a seed whose measurements are older than some
  threshold, so maturation itself surfaces re-checking rather than hiding it.

**Deliberately not proposed: any kind of automated re-measurement.** The instrument is
project-specific — a SQL query, a `git show`, a `grep` — and a tool that tried to re-run it would
be wrong in more ways than it was right. Making the AGE visible is the whole ask. The human or agent
does the checking.

## The counter-argument, stated honestly

This may be discipline rather than tooling. The convention already exists and works when followed;
adding structure to something people can already do in prose risks ceremony for its own sake. And
seeds' minimal-friction capture (`seeds jot`) is a real virtue that a required date-and-instrument
field would erode.

The case for doing it anyway is the asymmetry: writing the date costs seconds, and not having it cost
that project two months on one bead, a cross-repo round trip on another, and a near-miss migration of
a data source they already used.
