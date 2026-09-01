---
id: seeds-4
title: "Source materials: transcripts and documents as input"
status: exploring
type: idea
created_at: 2026-01-28T05:54:01.882137+00:00
updated_at: 2026-03-12T20:03:14.452323+00:00
tags:
  - architecture
  - source-materials
  - ingestion
relationships:
  - target_id: seeds-89
    rel_type: relates-to
    created_at: 2026-01-28T05:54:01.882137+00:00
  - target_id: seeds-126
    rel_type: relates-to
    created_at: 2026-03-12T20:04:53.078082+00:00
  - target_id: seeds-127
    rel_type: relates-to
    created_at: 2026-03-12T20:04:53.612862+00:00
  - target_id: seeds-128
    rel_type: relates-to
    created_at: 2026-03-12T20:04:53.920718+00:00
  - target_id: seeds-129
    rel_type: relates-to
    created_at: 2026-03-12T20:04:54.075793+00:00
  - target_id: seeds-130
    rel_type: relates-to
    created_at: 2026-03-12T20:04:54.192541+00:00
  - target_id: seeds-131
    rel_type: relates-to
    created_at: 2026-03-12T20:04:54.382451+00:00
  - target_id: seeds-132
    rel_type: relates-to
    created_at: 2026-03-12T20:04:54.632195+00:00
  - target_id: seeds-133
    rel_type: relates-to
    created_at: 2026-03-12T20:04:55.054179+00:00
  - target_id: seeds-125
    rel_type: relates-to
    created_at: 2026-03-12T20:04:55.300326+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

From spec_first_pass.md: Transcripts are NOT seeds - they are source material from which seeds are derived. Seeds reference back to specific lines in source documents.

Storage: Source materials should be stored alongside seeds as a separate entity type.

Processing workflow:
1. Store it as source material
2. Extract potential seeds from the document
3. Find existing seeds that match and merge transcript references (possibly tweaking with new info)
4. Create new seeds for unmatched extractions
5. Re-explore relationships when seeds are significantly changed or brand new

Key insight: The act of turning a transcript into seeds can be repeated multiple times. The current state of the seeds database informs what seeds to parse - it's not a one-time operation.


---
**Expanded scope (Feb 2026): source materials include generated artifacts.**

Original concept was external inputs (transcripts, documents). But source materials also include:
- Plan documents from pre-seeds conversations with Claude
- Expertise documents generated from investigation
- Any knowledge artifact that seeds were derived from or informed by

These are vulnerable — often not version controlled, can be overwritten by Claude. Seeds should at minimum provide a place to store/reference them. Provenance tracking (which seed came from which source) is deferred but acknowledged as valuable.



---
**Expanded scope (Mar 2026): source document types and the inbox model.**

Full list of source document types identified:
- Meeting notes and transcripts (boss meetings, team standups, etc.)
- Research documents and articles
- Plan files from pre-seeds conversations
- Old AI conversation logs (Claude JSONL, etc.)
- Any plain text document with deliberation content

**The inbox model:** Users place documents into a seeds inbox directory. Seeds processes them for seed extraction and records references. The user is responsible for ensuring documents are safe to include (privacy, copyright, proprietary concerns). Convention over configuration — no automated filtering.

**Key concerns raised:**
- Transcripts often span multiple projects — only a portion may be relevant
- Proprietary/personal/copyrighted content in source docs conflicts with public repos
- Verbatim preservation is desired but often infeasible
- Source documents should be re-ingestable as project context evolves
- How much of a "library" should .seeds/ carry?

Storage approach: source documents can be plain files in .seeds/, not necessarily DB entries. The DB stores seeds and references to source files. This keeps the architecture simple.
