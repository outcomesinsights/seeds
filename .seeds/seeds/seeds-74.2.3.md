---
id: seeds-74.2.3
title: Keyword markers in conversation → seeds extraction
status: resolved
type: idea
parent: seeds-74.2
created_at: 2026-02-06T22:16:37.549378+00:00
updated_at: 2026-09-01T16:47:37.616122+00:00
resolved_at: 2026-09-01T16:47:37.616113+00:00
tags:
  - workflow
  - capture
  - ux
  - glean
  - superseded-by-platform
relationships:
  - target_id: seeds-181.4
    rel_type: relates-to
    created_at: 2026-06-23T20:44:23.966165+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Idea:** Instead of explicit CLI calls during conversation, use natural language markers that post-analysis extracts into seeds.

**Examples of markers:**
- 'Here's a question...' → becomes a seed question
- 'I'm wondering if...' → investigation seed
- 'Decision: we'll do X because...' → decision seed
- 'Tangent:' or 'Side note:' → captured but deferred seed
- 'TODO:' → becomes a task/concern seed

**Flow:**
1. During conversation: speak naturally but use marker words
2. AI continues conversation without interruption
3. At 'harvest seeds': post-analysis finds markers, extracts structured seeds
4. User reviews/approves

**Benefit:** 
- No workflow interruption
- More natural than stopping to run CLI commands
- Markers are lightweight - just a word or phrase
- Post-analysis has full context to enrich the seed

**Open question:** 
Can this fully replace explicit `seeds jot`? Or is jot still useful for truly async capture (outside Claude conversations)?


---

## RESOLVED 2026-09-01 (Ryan): markers become hints to the gleaner, not a mechanism.

Kept, but demoted. `glean` (seeds-74.2.1) does NOT require marker phrases and must never
depend on them. Where they happen to appear in a transcript, the gleaner treats them as
strong signals. Costs nothing, occasionally helps.

**Why not the mechanism it was originally proposed as:**

- It relocates the discipline burden rather than removing it. Remembering to say "Tangent:"
  is not meaningfully cheaper than remembering to run `seeds jot` — and the seed this is a
  child of (seeds-74.2) exists because that kind of remembering demonstrably fails in
  practice.
- A competent gleaner does not need them. Decisions, open questions and walked-back claims
  are recoverable from an unmarked transcript; making extraction depend on markers would
  make it *worse* at the unmarked conversations, which is all of them.

**Superseded by the platform, not by an argument.** The open question above — "Can this
fully replace explicit `seeds jot`?" — was reaching for "speak naturally, and the right
thing fires without a CLI call". Claude Code skills now do exactly that: the harness
matches a skill's `description` against user intent. That mechanism did not exist when this
seed was written. The idea was correct about the goal and wrong about the implementation,
and the goal is now met elsewhere.

`jot` survives untouched for genuinely async capture outside a conversation, and `cutting`
(seeds-h5rq) covers the in-conversation case this seed was aiming at.
