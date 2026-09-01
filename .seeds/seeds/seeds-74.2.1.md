---
id: seeds-74.2.1
title: "Design: seeds glean (formerly 'sweep') — hybrid verb + skill, reads the transcript not the context"
status: resolved
type: decision
parent: seeds-74.2
created_at: 2026-02-06T22:03:49.501450+00:00
updated_at: 2026-09-01T16:47:37.316423+00:00
resolved_at: 2026-09-01T16:47:37.316415+00:00
tags:
  - feature
  - sweep
  - glean
  - ratified
  - 2026-09-01
relationships:
  - target_id: seeds-142
    rel_type: relates-to
    created_at: 2026-05-18T15:58:19.859270+00:00
  - target_id: seeds-x6m0
    rel_type: relates-to
    created_at: 2026-08-27T14:08:02.282402+00:00
  - target_id: seeds-h5rq.3
    rel_type: relates-to
    created_at: 2026-09-01T16:39:27.226165+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Command:** `seeds sweep [--session=ID] [--all] [--auto]`

**Flow:**
1. Locate conversation JSONL (~/.claude/projects/<project>/<session>.jsonl)
2. Parse messages (user + assistant content)
3. Send to Claude with prompt asking to identify:
   - Questions raised (answered or not)
   - Decisions made (with rationale if present)
   - Data discoveries (specific findings with numbers)
   - User insights/clarifications worth preserving
   - Threads: question → answer → decision chains
4. Cross-reference against existing seeds (fuzzy match titles/content)
5. Present as suggestions OR auto-create with --auto flag

**Output format:**
```
Found 5 potential seeds:

1. [DECISION] WIDGETTYP only needs CPT4/HCPCS/CDT
   Evidence: 'Analyzed distribution: CPT4 13M, ICD9Proc 3 records...'
   → Create? [y/n/edit]

2. [QUESTION] Should sweep auto-create or suggest?
   Status: UNANSWERED
   → Create? [y/n/edit]
```

**Questions:**
- How to handle multi-hour conversations? Chunk or summarize?
- Should sweep use current session's model or cheaper/faster one?
- How to find 'current' session from CLI context?



## Additional Design Considerations (from discussion)

**Sweep invocation options:**
1. CLI command: `seeds sweep` - invokes Claude to analyze
2. Slash command: `/sweep` - runs within conversation context
3. Part of prime statement - AI-initiated at session end

**Re-sweep handling:**
- Track which conversations have been swept (metadata/marker)
- Avoid re-sweeping by default
- Allow intentional re-sweep with flag: `seeds sweep --force` or `seeds sweep --since=<date>`
- Use case: 'We have a new lens, let's revisit old conversations'

**Slash command vs CLI:**
- Slash command: Runs in Claude context, has conversation readily available
- CLI command: Needs to find/parse conversation files, call Claude API
- Slash command feels more natural for 'sweep current conversation'
- CLI needed for 'sweep historical conversations'



## Context vs JSONL for sweep

**Problem:** After compaction, AI context is summarized. Detail is lost.

**Compacted context has:**
- Key decisions
- Summary of what happened
- Recent exchanges in detail

**Compacted context loses:**
- Exact data from queries (13M vs 3 records)
- Step-by-step investigation process
- Specific user quotes/clarifications
- Things mentioned but not acted on

**JSONL conversation log has:**
- Full transcript - every message
- All tool calls and results
- Not compacted - raw detail

**Implication:** Slash command using current context won't work well after compaction. Need to actually read the JSONL.

**Revised approach:**
1. Slash command or 'harvest seeds' phrase triggers
2. AI identifies current session's JSONL path
3. AI reads JSONL file (it's in ~/.claude/projects/...)
4. Analyzes full conversation against seeds
5. Surfaces gaps


---

## RESOLVED 2026-09-01 (Ryan). The command is `seeds glean`.

### Naming: `sweep` -> `glean`

Adopting the Mar-2026 terminology refinement recorded in seeds-74.2.4. `glean` is
agricultural where `sweep` is janitorial, it sits consistently beside `jot`, `cutting` and
`trellis`, and its literal sense — methodically picking through material others have
already been over, gathering what was missed — is exactly what end-of-session gap-finding
does. `thresh` and `winnow` stay unused; they described stages, not commands, and turning
them into commands would be building vocabulary for its own sake.

### Shape: hybrid skill + verb (from seeds-h5rq.3, per seeds-152.5)

- **`seeds glean` (CLI verb, deterministic):** resolve the transcript, extract turns, diff
  against the existing corpus, emit a compact candidate list. Gets pytest coverage.
- **Skill (judgment):** decide which candidates are real, phrase them, present for review.

This closes the "Slash command vs CLI" open question above: it is BOTH, layered, not a
choice between them.

### Read the transcript, never the model's context

The "Context vs JSONL" section above is correct and OVERRIDES the Option A conclusion in
seeds-74.2.2, which is stale. Post-compaction context loses exact figures, verbatim user
quotes, and things mentioned-but-not-acted-on — the precise set glean exists to recover.
Gleaning from summarized context would systematically miss what it is for.

Reinforced by measurement (titan, 2026-09-01): one ordinary working session's transcript is
502KB / 256 turns. That is both too large to hand a model raw and the reason extraction
belongs in a tested verb rather than in the skill.

### Open questions, closed

- **"How to find 'current' session from CLI context?"** — `$CLAUDE_CODE_SESSION_ID` is in
  the agent's environment and resolves directly to
  `~/.claude/projects/<project-slug>/<session-id>.jsonl`. Verified on titan. No
  most-recently-modified heuristics.
- **"How to handle multi-hour conversations? Chunk or summarize?"** — dissolved rather than
  answered. The verb filters to a candidate list first, so the model never sees the raw
  transcript. Chunking inside the verb is an implementation detail, not a design fork.
- **"Should sweep use current session's model or cheaper/faster one?"** — dropped. The
  skill runs in whatever session invoked it; there is no separate model to choose.

### `--auto`: kept as an opt-in flag (Ryan's ruling)

Default remains suggest-and-review (y/n/edit per candidate). `--auto` stays available for
bulk passes over historical conversations, where reviewing every candidate one at a time is
impractical.

Guardrail this ruling implies, and which the implementation must honour: seeds written by
`--auto` need to be distinguishable after the fact — a tag at minimum — so an unattended
bulk pass can be audited or reverted without hand-sorting it out of the corpus. The risk
being managed is that `seeds ready` is only useful while it stays a curated signal, and the
corpus is already 314 files.

### Re-glean tracking (still live, carried into implementation)

The "Re-sweep handling" notes above stand: track which conversations have been gleaned,
skip them by default, and allow deliberate re-gleaning (`--force` / `--since=<date>`) for
when there is a new lens to re-read old conversations through.

### Markers as hints (Ryan's ruling, from seeds-74.2.3)

Marker phrases are NOT required and must never be, but where they do appear the gleaner
treats them as strong signals. Costs nothing; occasionally helps.
