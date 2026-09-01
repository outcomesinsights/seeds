---
id: seeds-128
title: "Concern: how much of a library should a seeds database carry?"
status: captured
type: concern
created_at: 2026-03-12T20:01:02.889220+00:00
updated_at: 2026-03-12T20:01:02.889229+00:00
tags:
  - architecture
  - storage
  - source-materials
relationships:
  - target_id: seeds-4
    rel_type: relates-to
    created_at: 2026-03-12T20:04:53.920718+00:00
  - target_id: seeds-133
    rel_type: relates-to
    created_at: 2026-03-12T20:06:55.374691+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**The question:** When seeds stores source documents, how large does the .seeds/ directory become? Is it reasonable to carry around a library of transcripts, articles, research docs alongside the seed database?

**Considerations:**
- Source documents are plain text — no images/binary for now
- Transcripts can be large (meeting transcripts: 10-50KB each; could accumulate hundreds)
- Git handles text well, but large repos get unwieldy
- The .seeds/ directory travels with the project via git
- Some documents may be relevant to multiple projects

**Possible approaches:**
1. Store everything in .seeds/sources/ — simple but potentially huge
2. Store only extracted/clipped portions — smaller but lossy
3. Store references only (paths/URLs) — minimal footprint but source may disappear
4. Hybrid: store small docs inline, reference large ones externally
5. Files in .seeds/ that aren't in the DB — just plain files alongside seeds.db and seeds.jsonl

**Current leaning:** Documents don't need to be DB entries. They can be plain files stored in .seeds/ as a convention. The DB stores seeds and references to those files. This avoids bloating the database while keeping source material co-located.
