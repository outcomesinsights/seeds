---
id: seeds-112.3
title: No structural trigger reminds agents to persist open questions
status: captured
type: exploration
parent: seeds-112
created_at: 2026-02-27T16:00:09.214196+00:00
updated_at: 2026-02-27T16:00:09.214204+00:00
tags:
  - hooks
  - capture-gap
  - ai-ux
  - triggers
relationships:
  - target_id: seeds-112.4
    rel_type: relates-to
    created_at: 2026-06-05T17:26:20.206670+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Beads has session hooks that remind agents to check for work (the session-start hook in prime). Seeds has no equivalent mechanism that detects 'you just discussed an open question and didn't record it.' This could be a periodic nudge in the prime output, a session hook that checks for uncaptured deliberation, or even a convention where agents are expected to do a 'question sweep' at natural breakpoints in conversation.
