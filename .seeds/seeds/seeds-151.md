---
id: seeds-151
title: "Observation: agents treat user-provided context as gospel rather than checking assumptions"
status: captured
type: idea
created_at: 2026-05-22T17:13:08.291458+00:00
updated_at: 2026-05-22T17:13:08.291467+00:00
tags:
  - meta
  - agent-behavior
  - observation
  - context-shaping
relationships:
  - target_id: seeds-147.1
    rel_type: relates-to
    created_at: 2026-05-22T17:13:11.266896+00:00
  - target_id: seeds-147
    rel_type: relates-to
    created_at: 2026-05-22T17:13:11.356792+00:00
  - target_id: seeds-152
    rel_type: relates-to
    created_at: 2026-05-27T18:08:34.834216+00:00
  - target_id: seeds-192
    rel_type: relates-to
    created_at: 2026-07-10T17:17:20.144954+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

General pattern observed across multiple agent interactions: when a user brings an assumption or premise to an agent, the agent treats it as authoritative and proceeds without verifying.

## Example (ConceptQL)

I once asked an agent to add some columns to a particular ConceptQL operator. I did not realize the columns had already been added; the feature already existed in the code. The agent did not check whether the columns already existed. It simply added them a second time. The premise "we need to add X" was accepted; the question "does X already exist?" was never asked.

## Why this matters for seeds

Seeds is, in part, a context-shaping mechanism for agents. Every artifact we capture and re-surface (via `seeds prime`, `seeds show`, etc.) becomes additional gospel for the agent to accept.

This dynamic has two implications:

1. **The status quo is already shaping behavior.** We are not choosing whether seeds influence agents — only how much.
2. **Amplifying features compound the risk.** Anything that elevates certain seeds (lodestones — see [[lodestone-north-star-marker]] and [[risk-lodestones-may-over-channel-agent-reasoning]]) makes this compounding worse. Stronger signal → less questioning.

## Possible design responses

- Encourage seeds to be framed as *open* (hypothesis, observation, concern) rather than *closed* (rule, principle, decision) whenever possible.
- When seeds re-surface in context, accompany them with an explicit verification prompt: "this was true at time T — has it changed?"
- Resist features whose primary effect is to make agents *more* compliant with stored context. Prefer features that make agents *more questioning* of it.

## Caveat

This is one user's anecdotal pattern, not measured behavior. May vary by model, by task, by phrasing. Worth verifying before designing around it heavily — which is itself an instance of the very pattern this seed describes.
