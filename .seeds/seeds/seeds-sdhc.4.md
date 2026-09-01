---
id: seeds-sdhc.4
title: "Filenames carry identity only: relationships live at both ends and hierarchy in a parent field, with check enforcing both"
status: captured
type: decision
parent: seeds-sdhc
created_at: 2026-08-31T20:09:39.044459+00:00
updated_at: 2026-08-31T20:09:47.899537+00:00
tags:
  - storage
  - relationships
  - hierarchy
  - frontmatter
  - check
  - symmetry
  - "0.7"
  - 2026-08-31
relationships:
  - target_id: seeds-sdhc.2
    rel_type: relates-to
    created_at: 2026-08-31T20:09:48.362602+00:00
  - target_id: seeds-ebg1
    rel_type: relates-to
    created_at: 2026-08-31T20:09:48.474691+00:00
  - target_id: seeds-32ai
    rel_type: relates-to
    created_at: 2026-08-31T20:09:48.584312+00:00
  - target_id: seeds-not2
    rel_type: relates-to
    created_at: 2026-09-01T00:49:49.521323+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Settles seeds-sdhc's open items #3 (where relationships live) and #4 (child IDs as filenames). Both are the same question: when structure could be derived from a name or stored explicitly, which wins.

**The rule that decides both: the filename carries identity and nothing else. Every other structural fact is stored in frontmatter and cross-checked by `seeds check`.**

Deriving structure from a path is what already sank directory-as-state in seeds-sdhc, and it fails the same way here.

## Relationships: both ends, with symmetry as a check violation

549 rows today, roughly 275 logical edges.

Rejected: storing each edge once and deriving the inverse. `seeds show <id>` is the most common read, "what relates to this" is part of its answer, and deriving it means a corpus scan on every invocation. That forfeits the one-file-read property the whole format was chosen for. The 35 ms frontmatter scan measured in seeds-sdhc is fine for `list`; paying it on every `show` for a fact that could simply be stored is not.

The objection (seeds-ebg1) is real: two writes with no transaction can leave a half-edge that renders from A and not from B. But that is **mechanically verifiable**, which is the trade this architecture already makes everywhere else — SQLite mitigated it with a transaction, files mitigate it with detection. `seeds link` writes both ends and immediately re-reads both files to confirm symmetry before returning, so the window is one process, and `check` catches anything that escapes.

One constraint that falls out: **only symmetric edge types may be stored at both ends.** `relates-to` is symmetric. A directional type needs a named inverse stored at the far end, or symmetry checking is ambiguous about which side is wrong.

## Hierarchy: filename is `<id>.md` verbatim; `parent:` is stored too

75 of 304 IDs are dotted (`seeds-lcfa.6.1`). Dots in filenames are fine on every filesystem in play.

- **`seeds show <id>` must compute its path from the id** — that is the one-file-read property, and it means the file is `<id>.md`, dots included.
- **But `get_children` must not be a glob.** `seeds-lcfa.*.md` also matches grandchildren, and excluding them means counting dots, which is parsing structure back out of a name.
- **So `parent: seeds-lcfa.6` is an explicit frontmatter field**, and `check` verifies three things: the `parent` value agrees with the dotted id, the parent file exists, and no cycle exists.

The redundancy is deliberate and it is cheap because it is checked. It also decouples the two for the future — seeds-32ai asks whether ids should be topic slugs rather than base36 hashes, and under this layout hierarchy survives that change untouched.

Relates to seeds-sdhc, seeds-sdhc.2, seeds-ebg1, seeds-32ai.
