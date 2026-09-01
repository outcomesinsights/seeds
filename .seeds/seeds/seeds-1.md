---
id: seeds-1
title: "Granularity question: how fine-grained should seeds be?"
status: resolved
type: question
created_at: 2026-01-28T05:54:00.742995+00:00
updated_at: 2026-01-28T20:31:32.977945+00:00
resolved_at: 2026-01-28T20:08:50.452924+00:00
tags:
  - architecture
  - ai-ux
relationships:
  - target_id: seeds-40
    rel_type: relates-to
    created_at: 2026-01-28T05:54:00.742995+00:00
  - target_id: seeds-37
    rel_type: questioned-by
    created_at: 2026-01-28T20:02:20.356727+00:00
  - target_id: seeds-38
    rel_type: questioned-by
    created_at: 2026-01-28T20:02:20.838289+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

From discussion.md: 'How fine-grained should any seed be? Is it easier to reconstruct many small seeds or is it better to have one big seed with related ideas all living under one seed?'

Considerations:
- Fine-grained (many small): More precise, easier to resolve individual pieces. Con: harder to reconstruct the whole, more relationships to manage
- Coarse-grained (fewer large): Topic stays coherent, less reconstruction. Con: harder to track state of individual sub-ideas
- Context window usage is a concern (though improving)
- AI can summarize well, so detailed is safer

Key tension: The more detailed we are, the quicker we fill context windows. But context windows are improving over time - we might be optimizing for a temporary constraint.



DECISION: Favor smaller, focused seeds (more seeds) over fewer large seeds.

Rationale:
1. 'Lost in the Middle' research shows LLMs have 20%+ accuracy drops for info buried in long contexts
2. Optimal chunk size is 500-1800 chars - smaller focused seeds align with this
3. Chunking strategy matters more than model quality
4. Smaller seeds = easier to resolve individually, clearer status tracking

Format decision: Use Markdown with conventions (not YAML or JSON) for seed content.

Rationale:
1. Seed content is primarily prose with occasional structure - markdown's sweet spot
2. YAML indentation sensitivity is dangerous for AI edits
3. Markdown is what AI naturally produces
4. More token-efficient
5. More human-readable
6. Lightweight conventions work for structured bits (e.g., **Q:** / **A:** for questions)
