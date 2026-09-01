---
id: seeds-127
title: "Concern: privacy, copyright, and proprietary data in source documents"
status: captured
type: concern
created_at: 2026-03-12T19:00:43.469674+00:00
updated_at: 2026-03-12T19:00:43.469681+00:00
tags:
  - privacy
  - legal
  - copyright
  - source-materials
relationships:
  - target_id: seeds-4
    rel_type: relates-to
    created_at: 2026-03-12T20:04:53.612862+00:00
  - target_id: seeds-133
    rel_type: relates-to
    created_at: 2026-03-12T20:06:54.656547+00:00
  - target_id: seeds-132
    rel_type: relates-to
    created_at: 2026-03-12T20:06:54.751838+00:00
  - target_id: seeds-114
    rel_type: relates-to
    created_at: 2026-03-12T20:06:54.827479+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**The problem:** Seeds is developed in public. Source documents (transcripts, articles, research) may contain:
- Proprietary/confidential business information
- Personal information (names, employers, internal projects)
- Copyrighted material (articles, papers)
- Extraneous information unrelated to the project

Including full source documents in the .seeds/ directory means they get committed to a public repo.

**Tensions identified:**
1. Data hoarder vs public project: Want to preserve original nuance and words, but can't safely publish everything
2. AI summarization/rewording: Could strip sensitive content, but raises its own copyright questions (is AI-reworded copyrighted text still infringement?) and may miss sensitive data
3. Clipping/excerpting: Captures only relevant portions, but future re-ingestion may need parts that were clipped away
4. References (URLs, file paths): Even metadata can reveal sensitive info (file paths with usernames, internal URLs)

**Open questions:**
- Is AI summarization of copyrighted material legally defensible for inclusion in a public database?
- Can redaction ever be thorough enough for meeting transcripts with proprietary discussions?
- Should there be a .seeds/sources-private/ that's .gitignored by default?
- Is the right answer simply that source documents live outside seeds and seeds only stores references + extracted seeds?

**Current resolution:** The inbox model (user responsibility) handles this for now, but this concern will intensify as seeds gets more users and more ambitious ingestion features.
