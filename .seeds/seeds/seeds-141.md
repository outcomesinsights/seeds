---
id: seeds-141
title: AskUserQuestion answers should be capturable in seeds
status: captured
type: idea
created_at: 2026-05-15T16:16:06.441733+00:00
updated_at: 2026-05-15T16:16:06.441739+00:00
tags:
  - ai-ux
  - workflow
  - capture-gap
  - deliberation
relationships:
  - target_id: seeds-112.4
    rel_type: relates-to
    created_at: 2026-06-05T17:26:20.343026+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Observation while using Claude's AskUserQuestion interface during a seeds dev session: the user enjoys answering questions through the structured Q&A UI, but there's no slot to attach rationale or follow-up commentary to a selection. The chosen option is recorded; the *why* is not.

In this session alone, AskUserQuestion was used several times for non-trivial design decisions (auto-derive yes/no, body-rewrite default-on/opt-in, dry-run verbosity). Those answers shaped the codebase, but the only record is in the chat log — and one of those decisions was reversed mid-session, with the reversal also captured nowhere durable.

# What the user wonders
- Should seeds be *aware* of AskUserQuestion-style interactions? (Right now seeds has no concept of this UI.)
- When the user answers one of those questions, should the Q+A get persisted as a seed (or attached to an existing seed under deliberation)?
- Should the system optionally follow up with a 'why did you pick that?' prompt that the user can either answer or skip?

# Why this matters
Seeds' whole pitch is capturing the *journey* of deliberation, not just conclusions. AskUserQuestion is currently a journey-loss hole: a decision is rendered, picked, gone. If the decision was material (and many are), the rationale is exactly the kind of thing seeds was built to keep.

# Open shape
- Could be a manual flow: agent runs `seeds answer` after an AskUserQuestion exchange, optionally with --rationale
- Could be a hook/integration: AskUserQuestion responses fed into seeds automatically with rationale prompt
- Could just be a documented pattern in prime.py guidance rather than a new feature

Just a note for now.
