---
id: seeds-74.2.1
title: "Design: seeds sweep command"
status: captured
type: decision
parent: seeds-74.2
created_at: 2026-02-06T22:03:49.501450+00:00
updated_at: 2026-09-01T16:39:27.227816+00:00
tags:
  - feature
  - sweep
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
