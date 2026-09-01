---
id: seeds-74.2.2
title: "Hybrid approach: explicit callouts + end-of-session sweep"
status: captured
type: decision
parent: seeds-74.2
created_at: 2026-02-06T22:14:28.430719+00:00
updated_at: 2026-02-06T22:15:09.782194+00:00
tags:
  - workflow
  - sweep
  - design
relationships:
  - target_id: seeds-82
    rel_type: questioned-by
    created_at: 2026-02-06T22:14:45.316415+00:00
  - target_id: seeds-181.4
    rel_type: relates-to
    created_at: 2026-06-23T20:44:24.088546+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Approach:** Hybrid of proactive capture + session-end sweep

**During conversation (proactive):**
- Use `seeds jot`, `seeds ask` for explicit callouts
- Capture tangents, questions, ideas that come up but aren't current focus
- Benefit: Stay on task while noting things to revisit later
- This is intentional, human-directed capture

**End of session ('land the plane' equivalent):**
- Before closing out, seeds checks: what fell through the cracks?
- Finds current conversation JSONL
- Compares what was discussed vs what got captured
- Surfaces gaps: 'These things were discussed but not captured...'
- User decides what to add

**Why hybrid:**
- Auto-capture alone can't know what's a tangent worth noting vs noise
- Pure proactive fails (as demonstrated: we talked 15min without capturing)
- Explicit callouts handle 'I want to note this but stay on task'
- End-of-session sweep catches what slipped through

**Implementation thought:**
Like beads 'land the plane' triggers sync, seeds could have similar phrase that triggers:
1. `seeds sync --flush-only`
2. Conversation sweep for gaps
3. Present any uncaptured items for review



## Technical approach options

**Option A: Slash command**
- `/seeds-sweep` slash command
- AI says 'land the plane' → invokes slash command
- Slash command prompt instructs AI to analyze current conversation
- AI has conversation context, can directly compare to seeds
- Simpler: no need to find/parse JSONL from CLI

**Option B: Hook-triggered**
- Hook listens for trigger phrase
- Calls `seeds sweep --current-session`
- CLI finds conversation JSONL, calls Claude API to analyze
- More complex: needs session discovery, API calls

**Option A seems simpler** - the AI already has the conversation in context, just needs prompting to analyze it against seeds.

## Trigger phrase
Open question: use 'land the plane' (consistency with beads) or seeds-specific phrase?
