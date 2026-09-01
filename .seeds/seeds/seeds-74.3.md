---
id: seeds-74.3
title: "Investigate: intent.build vs seeds"
status: captured
type: exploration
parent: seeds-74
created_at: 2026-02-06T22:08:34.701725+00:00
updated_at: 2026-02-09T14:35:19.800172+00:00
tags:
  - research
  - competitive
  - intent-build
relationships:
  - target_id: seeds-80
    rel_type: questioned-by
    created_at: 2026-02-06T22:09:44.245298+00:00
  - target_id: seeds-81
    rel_type: questioned-by
    created_at: 2026-02-06T22:09:50.002290+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Question:** How does seeds compare to intent.build? Is seeds reinventing something that already exists?

**Context:** While designing a 'sweep' feature for extracting seeds from conversations, realized this sounds similar to what intent.build might do.

**To investigate:**
- What is intent.build's core value prop?
- Does it extract insights from conversations?
- How does it track deliberation/decisions?
- What's their approach to AI-assisted capture?

**Key differentiators to look for:**
- CLI-first vs web-first?
- Integrated into dev workflow vs standalone?
- How it handles the capture problem (proactive vs sweep)

**User note:** 'Figure out whether seeds is all that different, and if so, what those differences are.'



## Research: intent.build

**Tagline:** 'The system of record for human decisions in software'

**Problem they solve:** As AI agents generate code faster, the reasoning behind decisions gets lost. Context scattered in chat logs, meetings, docs, heads.

**Three surfaces:**
1. **Capture** - Auto-records decisions from agent prompts/IDE sessions, structures them (not just logs)
2. **Arena** - Real-time team collaboration, 'intent emerges as you discuss, not after'
3. **Repo** - Versions decisions in `intent/` directory alongside code, searchable, diffable

**Key features:**
- AI grounding: Prevents agents from repeating suggestions or hallucinating past decisions
- Knowledge preservation: Ephemeral → persistent, queryable
- Integrates with: Cursor, GitHub Copilot, Claude Code, Codex, Gemini

**Overlap with seeds:**
- Both address 'reasoning gets lost' problem
- Both capture decisions from AI conversations
- Both make decisions accessible to future AI

**Potential differences (to explore):**
- Intent: Team-focused (Arena for collaboration). Seeds: Single-dev CLI.
- Intent: Versions in repo (`intent/` dir). Seeds: SQLite + JSONL export.
- Intent: Broader IDE integration. Seeds: Claude Code specific.
- Seeds: Hierarchical seeds, questions as first-class, deliberation lifecycle.
- Seeds: `jot` for quick capture vs Intent's auto-capture?



## Potential differentiator: Structured relationships

**User observation:** Does intent.build track relationships? Having decisions and design as part of a *database* with structure might give us something a flat structure wouldn't.

**Seeds structure:**
- Hierarchical: parent/child seeds (seed-123.1.2)
- Questions attached to seeds
- Relationships: seed-X relates-to seed-Y
- Lifecycle: captured → exploring → resolved/abandoned/deferred
- Types: idea, question, decision, exploration, concern

**If intent.build is flat:**
- Seeds' structure could be the differentiator
- Enables: blocked seeds (unresolved children), dependency tracking
- Enables: tracing decision chains (question → investigation → decision)
- Enables: querying by lifecycle state (what's still open?)

**Need to investigate:** Is intent.build actually flat, or does it have structure too?



## Reframe: Seeds as general deliberation extractor

User insight: Harvesting from Claude logs is same as harvesting from any deliberation source (meetings, email, Slack, etc.)

**If seeds is source-agnostic:**
- Competes less directly with intent.build (which is IDE-focused)
- Broader value prop: 'Extract structure from any deliberation'
- CLI-first makes it composable: pipe anything into harvest
- Could become the 'grep for decisions' across all your communication

**Potential positioning:**
- Intent.build: 'System of record for decisions in software' (IDE-integrated, team-focused)
- Seeds: 'Extract and track deliberation from anywhere' (CLI-first, source-agnostic, structured lifecycle)



## CORRECTED positioning

**Intent.build:** System of record for decisions (the outputs)
**Seeds:** Structured database for the deliberation *process* (the journey)

**Seeds' secret sauce is the structure:**
- Hierarchical: drill down from big idea → sub-questions → specific findings
- Questions attached to seeds: track what was asked, answered or not
- Lifecycle states: see what's still being explored vs resolved
- Blocking: can't resolve parent until children are resolved
- Relationships: how ideas connect and inform each other

**Seeds answers questions intent.build might not:**
- 'What did we explore before deciding X?'
- 'What questions led to this decision?'
- 'What's still open/unresolved?'
- 'What was considered but deferred?'
- 'Show me the investigation that informed decision Y'

The harvest feature isn't about 'capture from anywhere' - it's about enriching the structured deliberation database from conversation sources.
