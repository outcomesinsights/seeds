---
id: seeds-h5rq.3
title: cutting is a pure skill with zero new CLI surface; sweep is a hybrid
status: captured
type: decision
parent: seeds-h5rq
created_at: 2026-09-01T16:39:22.768890+00:00
updated_at: 2026-09-01T16:39:27.364181+00:00
tags:
  - cutting
  - sweep
  - skill
  - cli
  - architecture
  - shape
  - 2026-09-01
relationships:
  - target_id: seeds-74.2.1
    rel_type: relates-to
    created_at: 2026-09-01T16:39:27.226165+00:00
  - target_id: seeds-152.5
    rel_type: relates-to
    created_at: 2026-09-01T16:39:27.363556+00:00
---

**Ruled 2026-09-01 (Ryan), applying the test ratified in seeds-152.5.**

## cutting — pure skill, no new CLI verb

The judgment *is* the feature. Deciding what surrounding context matters and phrasing it so
the topic can be resumed cold is exactly what a model is for, and exactly what a
deterministic verb cannot do. The mechanism it needs — write a seed with a rich body —
is `seeds create --content`, which already exists.

So `cutting` adds **zero new binary surface**. It is a SKILL.md in
`src/seeds/plugin/claude-plugin/skills/cutting/` and nothing else. This makes it the
cleanest instance of 152.5's test in the corpus, and the smallest thing on the table.

Consistent with all four shipped skills (feedback, trellis, seeds-to-beads,
resolve-seeds-from-beads): every one is a judgment-first conversational dynamic, and none
reimplements a data operation the CLI already performs.

## sweep — hybrid, and NOT yet ready to build

Agent-facing entry is a skill (Ryan, 2026-09-01), but sweep is the hybrid case 152.5
predicted, not a pure skill like cutting:

- **Skill half (judgment):** which gaps are worth capturing, what is noise, how to present
  candidates for review.
- **Verb half (deterministic):** resolve the session transcript, extract turns, diff
  against the existing corpus, emit a compact candidate list.

Two independent reasons the mechanical half must be a verb rather than the skill reading
the transcript itself:

1. **Cost.** Measured 2026-09-01 on an ordinary working session: 502KB / 256 turns. Handing
   that to the model raw to find a handful of gaps is the wrong shape.
2. **Testability.** A verb gets pytest coverage. A skill gets none.

**Also settled by measurement**, closing seeds-74.2.1's long-open question "How to find
'current' session from CLI context?": `$CLAUDE_CODE_SESSION_ID` is present in the agent's
environment and resolves directly to
`~/.claude/projects/<project-slug>/<session-id>.jsonl`. Verified on titan. No
most-recently-modified heuristics needed.

## Sequencing

`cutting` is fully specified and beadable now. `sweep` is NOT: seeds-74.2 is still
`exploring` and blocked by four unresolved children, including a design (seeds-74.2.1) with
open questions and a pivot that was already walked back (seeds-74.2.4). Beading sweep now
would be beading an unsettled design.

Drain seeds-74.2 in its own pass first, then bead sweep. This ordering is itself an
instance of the problem cutting exists to solve — the sweep cluster is a topic that fell by
the wayside.
