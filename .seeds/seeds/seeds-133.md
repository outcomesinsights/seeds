---
id: seeds-133
title: "Concern: verbatim source preservation vs feasibility"
status: captured
type: concern
created_at: 2026-03-12T20:02:21.150836+00:00
updated_at: 2026-03-12T20:02:21.150844+00:00
tags:
  - philosophy
  - source-materials
  - privacy
relationships:
  - target_id: seeds-4
    rel_type: relates-to
    created_at: 2026-03-12T20:04:55.054179+00:00
  - target_id: seeds-127
    rel_type: relates-to
    created_at: 2026-03-12T20:06:54.656547+00:00
  - target_id: seeds-131
    rel_type: relates-to
    created_at: 2026-03-12T20:06:55.144075+00:00
  - target_id: seeds-128
    rel_type: relates-to
    created_at: 2026-03-12T20:06:55.374691+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**The tension:** User has a strong instinct to preserve original source material verbatim — the nuance in people's actual words matters, and AI extraction may misinterpret or put its own twist on things. Being able to go back to the source is valuable.

At the same time, verbatim preservation is often infeasible:
- Privacy: meeting transcripts contain proprietary/personal information
- Copyright: articles and research papers can't be freely reproduced
- Scale: accumulating full transcripts gets unwieldy
- Public repo: .seeds/ is committed and potentially public

**The frustration is real:** There's a genuine loss when you can't keep the original words. AI-generated summaries flatten nuance. Extracted seeds are interpretations, not primary sources.

**Possible middle grounds:**
- Keep originals on a private server, seeds stores references
- .gitignored source directory for local-only storage
- AI-assisted clipping that preserves relevant verbatim sections
- Summarize with explicit quotes for key passages
- Accept the loss and trust that seeds capture the important bits

**This is a philosophical tension at the heart of the source materials feature, not a problem to solve once.**
