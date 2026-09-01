---
id: seeds-74.2.3
title: Keyword markers in conversation → seeds extraction
status: captured
type: idea
parent: seeds-74.2
created_at: 2026-02-06T22:16:37.549378+00:00
updated_at: 2026-02-06T22:16:37.549386+00:00
tags:
  - workflow
  - capture
  - ux
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
