---
id: seeds-not2
title: "The 'answers' relation type is a fossil: seeds answer stores content and never made an edge, so an edge-based answering model was superseded before anyone used it"
status: captured
type: decision
created_at: 2026-09-01T00:49:40.060776+00:00
updated_at: 2026-09-01T00:49:49.298758+00:00
tags:
  - relationships
  - vestigial
  - answers
  - questions
  - schema
  - storage
  - "0.7"
  - 2026-08-31
relationships:
  - target_id: seeds-02ur
    rel_type: relates-to
    created_at: 2026-09-01T00:49:49.413635+00:00
  - target_id: seeds-sdhc.4
    rel_type: relates-to
    created_at: 2026-09-01T00:49:49.521323+00:00
  - target_id: seeds-tz66
    rel_type: relates-to
    created_at: 2026-09-01T00:49:49.630737+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

@aguynamedryan, 2026-08-31, on being told the `answers` relation type has zero edges: *"I'm surprised answers isn't ever used -- we have lots of questions and assigning answers to those questions was supposed to be the correct way to answer a question, yes?"*

The intent was right and the mechanism was never wired to it.

## What was actually traced

- **`seeds answer <q-id> "text"`** (cli.py:1269) stores the answer as the **question-seed's own `content`** and re-stamps `resolved_at`. It creates no relationship. This is the working, used path — the intent is intact.
- **`RelationType.ANSWERS`** (models.py:56) appears in exactly three places: the enum member, a docstring in `db.create_relationship` (db.py:610), and the choice list on `seeds link --type [relates-to|questions|answers]`. **No workflow creates one.** The only route is a hand-run `seeds link A --relates-to B --type answers`.
- **Corpus, 2026-08-31:** 534 `relates-to`, 57 `questions`, **0 `answers`** — across 214 days.
- By contrast `questions` is genuinely live: created by `seeds ask` (cli.py:1242) and by the v2 question-seeds migration (export.py:650), pointing question-seed → the seed it asks about.

## The reading

An **edge-based answering model was designed, then superseded by the content-field approach before anyone used it**, and the enum member was left behind. The zero count is not neglect of a working feature; it is a fossil of a design that lost.

That distinction is what decided it. A type that is merely idle might earn its place on uniformity grounds — every directional type having a named inverse is a rule with no exceptions to remember. A type that **no workflow can produce** is dead weight the format would have carried forever.

## Ruling

`answers` and its proposed inverse `answered-by` are **dropped**. The closed set is three strings: `relates-to` ↔ `relates-to`, `questions` ↔ `questioned-by`. Bead seeds-4co.2 removes `RelationType.ANSWERS` and the `answers` choice on `seeds link --type`. `seeds answer` is untouched, because it never depended on the edge.

## The process note worth keeping

This ruling reversed one made minutes earlier. The first was taken on the framing *"`answers` has zero edges"*, which sounds like an unused-but-real relation; the second on *"the answering workflow does not use edges at all"*, which is the same fact stated at the depth that actually decides. **The reversal was caused by the description, not by new evidence** — everything needed was already in the code both times.

The lesson for how these get put to @aguynamedryan: a count is not a finding. Trace what produces a thing before reporting that nothing has.

Relates to seeds-02ur, seeds-sdhc.4, seeds-tz66.
