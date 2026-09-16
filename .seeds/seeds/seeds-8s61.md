---
id: seeds-8s61
title: Session depth, not wall-clock, may be the predictor of a degraded decision — and glean already reads the transcript that holds it
status: captured
type: idea
created_at: 2026-09-16T16:07:25.820170+00:00
updated_at: 2026-09-16T16:08:39.086749+00:00
tags:
  - context-rot
  - self-conditioning
  - glean
  - targeting
  - prior-art
  - degradation
relationships:
  - target_id: seeds-cpkr
    rel_type: relates-to
    created_at: 2026-09-16T16:08:38.856246+00:00
---

"Claude gets dumber in stretches" is framed temporally — the failure is a window of
wall-clock time. The best-documented mechanism says the unit is not the calendar but
**how deep into a session the reasoning happened**.

- Chroma's *Context Rot* (Hong, Troynikov, Huber, July 2025) held task difficulty constant
  while varying input length across 18 frontier models. Every one degraded, including on
  trivial retrieve-and-copy tasks.
- *The Illusion of Diminishing Returns: Measuring Long Horizon Execution in LLMs*
  (arXiv 2509.09677) adds **self-conditioning**: models degrade by conditioning on their
  own earlier mistakes, and accuracy recovers sharply when handed a fully-correct history.
- *Drift No More? Context Equilibria in Multi-Turn LLM Interactions* (arXiv 2510.07777)
  models multi-turn drift directly.

Two consequences if this is the mechanism.

**Any in-session self-check is checking with the same degraded instrument**, and the
degradation is self-reinforcing rather than random — which is an independent argument for
cold, cross-session review over an added step inside the session.

**The predictor is recoverable here and nearly free.** `seeds glean` already resolves and
reads the session transcript. The turn index at which a decision first appears is data the
transcript holds and the corpus throws away. A reviewer could be handed that index and
told to read the late-session decisions first.

That converts an unmeasurable premise into a targeting heuristic with published evidence
behind it, using an instrument already composed by \[[seeds-cpkr]\]. It also interacts
with \[[seeds-r85y]\]: if the efficacy sweep finds misses, their session depth is the
first thing to check.

Identified by the outside-in reviewer, 2026-09-16, as the clearest case where a blind
frame saw something the deliberation's own frame structurally could not.
