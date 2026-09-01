---
id: seeds-74.2
title: Conversation sweep vs proactive capture for seeds
status: exploring
type: exploration
parent: seeds-74
created_at: 2026-02-06T22:02:47.824545+00:00
updated_at: 2026-02-06T22:03:02.919453+00:00
tags:
  - workflow
  - meta
  - sweep
relationships:
  - target_id: seeds-78
    rel_type: questioned-by
    created_at: 2026-02-06T22:03:18.251599+00:00
  - target_id: seeds-79
    rel_type: questioned-by
    created_at: 2026-02-06T22:03:23.823335+00:00
  - target_id: seeds-x6m0
    rel_type: relates-to
    created_at: 2026-08-27T14:08:02.392709+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Question:** Should seeds be captured during conversation (proactive) or extracted via post-conversation sweep (retrospective)?

**User's argument for sweep:**
- Holistic view of conversation reveals patterns: questions asked but not answered, decisions that led to other decisions/questions
- The conversation IS the context - sweep has full context available
- Trigger words or manual invocation ('sweep for seeds') could work
- Doesn't interrupt flow
- Proactive capture fails in practice - even with prime guidance, AI didn't stop to capture THIS conversation until told

**Key insight:** The failure mode of proactive capture was demonstrated in real-time. We discussed capture quality for 15+ minutes without making a seed about it.

**Sweep approach could identify:**
- Questions raised but not answered
- Questions answered that led to decisions
- Decisions that led to new questions
- Data discoveries with specific numbers/findings
- User clarifications/insights

**Open questions:**
- What triggers a sweep? End of session? Manual command? Keyword?
- How to present findings - auto-create seeds or suggest for user review?
- How to handle very long conversations?
- Could this work on historical conversations too?
