---
id: seeds-h9cl
title: "Seed type is write-once: no CLI route to change it, single or bulk"
status: resolved
type: decision
created_at: 2026-08-28T13:59:39.774761+00:00
updated_at: 2026-08-31T21:34:29.076980+00:00
resolved_at: 2026-08-31T21:34:29.076973+00:00
resolution: "Shipped: 'seeds update --type' for one seed (bead seeds-9cp) and 'seeds retype --from X --to Y' for bulk remap (bead seeds-scq), plus 'seeds doctor' listing non-standard types so a typo surfaces at all. Efficacy: no tweaking; built as written. The seed's own finding — that the gap was wider than the question assumed, because type was write-once with no CLI route at all — is what made the bead correct on the first pass."
tags:
  - type
  - vocabulary
  - remap
  - retype
  - update
  - cli
  - gap
  - release
  - 2026-08-28
relationships:
  - target_id: seeds-1x6b
    rel_type: relates-to
    created_at: 2026-08-28T13:59:44.681781+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

@aguynamedryan, after ruling the type vocabulary fully open in [[seeds-1x6b]]:

> "should we consider a feature where types can be bulk-remapped to other types so if ideea sneaks in, we can easily clean it up?"

Yes — and the gap is wider than the question assumes.

## The finding

`seeds update` carries --title, --content, --tags, --add-tag, --remove-tag, --append, --replace, --allow-unknown-refs. It has **no --type**. A seed's type is set once at `create` and there is no CLI route to change it afterwards, for one seed or many.

So @markdanese's "converted those 11 records to exploration" was not him declining a tedious loop of `seeds update --type` — that loop does not exist. Hand-editing `.seeds/seeds.jsonl` was the only route available. The tool pushed its first external bug reporter through the same unvalidated door that caused his incident.

This matters much more once the vocabulary opens: `seeds create --type ideea` will succeed, and today nothing in the CLI can undo it.

## Shape

Two pieces, and the first is the missing primitive rather than a convenience:
1. `seeds update <id> --type <t>` — change one seed's type.
2. A bulk remap — `seeds retype --from ideea --to idea` (name unsettled) — @markdanese's actual operation, and the repair that doctor's vocabulary warning should name.

The pairing worth building: doctor detects drift and prints the command that fixes it.

    ⚠ Vocabulary: 3 seeds use a type outside the standard set:
        ideea (3)
      Fix with: seeds retype --from ideea --to idea

Detection that hands over the repair, rather than detection that leaves the operator to find one.

## Cost is low — the pattern is already paid for

`seeds rename-prefix` is the precedent and gives the whole template: --dry-run listing every change before applying, an automatic `.db.bak` copy before mutating, an itemized report, and a re-export at the end using the sanctioned `allow_divergence=True` bypass. A type remap is far simpler than rename-prefix's 149 db-layer lines: one column, no ID rewriting, no child/relationship fixups, no scanning seed bodies for references.

## Caution

With a fully open vocabulary, `--to idae` is itself a typo nothing can catch. Dry-run plus doctor's listing afterwards is the mitigation, not validation.

## Release argument

This belongs in the same release as [[seeds-1x6b]]'s vocabulary work, not after it. That change is what makes typos possible; shipping the mess-maker and the detector without the broom is a worse story than shipping the loop closed. The bulk remap also generalizes past typos — it is the tool for deliberate vocabulary evolution (renaming `concern` to `risk` across a project), which is the more durable justification.
