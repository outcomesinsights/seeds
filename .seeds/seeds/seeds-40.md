---
id: seeds-40
title: Add 'extra' field for flexible structured data
status: resolved
type: idea
created_at: 2026-01-28T20:27:00.144533+00:00
updated_at: 2026-02-24T17:04:31.747396+00:00
resolved_at: 2026-01-28T20:34:15.256645+00:00
tags:
  - architecture
  - model
relationships:
  - target_id: seeds-1
    rel_type: relates-to
    created_at: 2026-01-28T05:54:00.742995+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Decision:** Add a separate `extra` field (YAML/dict) to the Seed model for capturing structured data we haven't formalized yet.

**Rationale:**
- Allows capturing alternatives, rationale, answers, etc. without schema changes
- Keeps prose content separate from structured metadata
- Low cost to add now while product is nascent
- When patterns emerge, promote frequently-used keys to proper fields

**Approach:**
- Add `extra: dict` field to Seed model (nullable, defaults to empty)
- Store as JSON in SQLite
- Display in `seeds show` output
- Include in JSONL export
- CLI: add `--extra` flag or subcommand to set/update extra data


---
**Still unimplemented as of Feb 2026.** Beads v0.56 now has a full queryable metadata system validating this direction: `--metadata-field key=value` filters on `bd list`/`bd search`, reserved key prefixes (`bd:` for internal, `_` for private), and human-readable display in `bd show`. This confirms the `extra: dict` approach is the right one. The beads implementation also shows the value of making metadata *queryable* — not just a dump field, but filterable.
