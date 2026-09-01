---
id: seeds-74.2.2
title: "Hybrid approach: explicit callouts + end-of-session sweep"
status: resolved
type: decision
parent: seeds-74.2
created_at: 2026-02-06T22:14:28.430719+00:00
updated_at: 2026-09-01T16:47:37.459190+00:00
resolved_at: 2026-09-01T16:47:37.459182+00:00
tags:
  - workflow
  - sweep
  - design
  - glean
  - cutting
  - resolved-2026-09-01
relationships:
  - target_id: seeds-82
    rel_type: questioned-by
    created_at: 2026-02-06T22:14:45.316415+00:00
  - target_id: seeds-181.4
    rel_type: relates-to
    created_at: 2026-06-23T20:44:24.088546+00:00
  - target_id: seeds-h5rq
    rel_type: relates-to
    created_at: 2026-09-01T16:29:53.018536+00:00
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


---

## RESOLVED 2026-09-01. The hybrid stands; both halves now have names.

The hybrid ruling above was right and is unchanged. What it lacked was a concrete proactive
half — it named `jot` and `ask`, which are too thin for the job. Both halves now exist:

- **Explicit callout half -> `cutting`** (seeds-h5rq). A jot captures a topic's statement;
  a cutting captures it with enough surrounding deliberation to resume cold. That richness
  is what "stay on task while noting things to revisit later" actually requires — the cost
  of a cold restart is why parked topics stayed parked.
- **End-of-session half -> `glean`** (seeds-74.2.1, renamed from `sweep`).

## CORRECTION: "Option A seems simpler" is superseded

The Technical-approach section above concludes Option A (slash command analysing the
conversation already in the model's context) over Option B (read the transcript). **That
conclusion is wrong and is overridden by seeds-74.2.1**, whose own later "Context vs JSONL"
section argues the opposite case correctly:

Post-compaction context is summarized. It loses exact figures, verbatim user quotes, and
things mentioned-but-not-acted-on — exactly the set glean exists to recover. Gleaning from
context would systematically miss what it is for, and would appear to work in short
sessions while failing silently in the long ones that need it most.

The two seeds contradicted each other for roughly six months without either being resolved.
That is itself an argument for draining clusters rather than letting them accumulate.

The final shape is neither A nor B as written: a **skill** (judgment) over a **CLI verb**
(transcript resolution, extraction, corpus diff), per seeds-152.5.

## Trigger phrase

The open question "'land the plane' or a seeds-specific phrase?" is dissolved. Skills are
matched by description against user intent, so the trigger is the skill's `description`
field rather than a magic phrase anyone has to memorize. Write it to match how the user
actually asks ("what did we miss?", "glean this session", "anything not captured?").
