---
id: seeds-126
title: "Source document ingestion: the inbox model"
status: captured
type: exploration
created_at: 2026-03-12T19:00:28.382547+00:00
updated_at: 2026-03-12T19:00:28.382555+00:00
tags:
  - architecture
  - ingestion
  - source-materials
  - privacy
relationships:
  - target_id: seeds-4
    rel_type: relates-to
    created_at: 2026-03-12T20:04:53.078082+00:00
  - target_id: seeds-89
    rel_type: relates-to
    created_at: 2026-03-12T20:06:55.293714+00:00
  - target_id: seeds-157
    rel_type: relates-to
    created_at: 2026-06-15T20:44:18.228441+00:00
  - target_id: seeds-181
    rel_type: relates-to
    created_at: 2026-06-23T20:44:22.869677+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Core concept:** Users place documents into a seeds inbox (a directory within .seeds/). Whatever is placed there is the user's responsibility to ensure it's cleared for inclusion. Seeds processes it for seed extraction, records references, but does NOT worry about copyright/privacy/sensitivity filtering — that's the user's job before placement.

**Why this approach:**
- No configuration needed (convention over configuration)
- Avoids premature complexity around privacy/copyright detection
- The user knows their documents and their risk tolerance
- Seeds stays focused on deliberation capture, not content moderation

**What seeds does with inbox documents:**
1. Stores the document in .seeds/sources/ (or similar)
2. Extracts/gleans candidate seeds using current project context
3. Creates new seeds or updates existing ones with references to the source
4. Records provenance: which seed came from which source document

**Document types to support:**
- Meeting notes/transcripts
- Research documents (articles, reports)
- Plan files (pre-seeds conversations)
- Old AI conversations (Claude JSONL, etc.)
- Any plain text document

**Key tension identified:** User wants to hold onto source data (data hoarder instinct, nuance in original words matters) but acknowledges verbatim capture is often infeasible for privacy/legal/copyright reasons. The inbox model resolves this by making the user the gatekeeper.
