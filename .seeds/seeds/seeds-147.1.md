---
id: seeds-147.1
title: "Risk: lodestones may over-channel agent reasoning and suppress fruitful exploration"
status: captured
type: concern
parent: seeds-147
created_at: 2026-05-22T17:12:53.974799+00:00
updated_at: 2026-08-31T20:02:41.172151+00:00
tags:
  - meta
  - agent-behavior
  - risk
  - unintended-consequences
relationships:
  - target_id: seeds-151
    rel_type: relates-to
    created_at: 2026-05-22T17:13:11.266896+00:00
  - target_id: seeds-192
    rel_type: relates-to
    created_at: 2026-07-10T17:17:20.425069+00:00
  - target_id: seeds-197
    rel_type: relates-to
    created_at: 2026-07-15T21:52:07.471922+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Worry: even when lodestones are framed as "weighted" rather than "binding," they may behave as heavy guardrails in practice, because agents tend to over-weight stated principles.

## Concrete cautionary example (Jigsaw)

In November I recorded a principle along the lines of "if Ember code or related dependencies are deprecated, respect the deprecation and move forward." Later, during a routine minor upgrade of an Ember add-on, the agent picked up "deprecated vibes" from the changelog — even though the add-on was being *maintained*, just *discouraged from further use* (a subtle distinction). It took the principle as license to strip 33 instances of functions across the codebase. A tremendous amount of refactoring, not urgent, not needed. The principle had become a trigger.

If a casual statement-of-intent can produce that, a deliberately-elevated lodestone might do worse.

## Related phenomenon — agents over-weight provided context

See [[agents-treat-user-context-as-gospel]] for the broader pattern. The shorthand version: when a user brings an assumption to an agent, the agent typically accepts it without checking. Example: I once asked an agent to add a column to a ConceptQL operator — a column that already existed in the codebase. The agent added it a second time without ever verifying. The agent doesn't reach for "is this premise true?"; it reaches for "how do I satisfy this premise?"

Lodestones would be another lever for this same dynamic. Worse, lodestones are *retained* across conversations, so the over-weighting compounds.

## Tension we're already inside

We are already shaping conversation by recording seeds at all. Every `seeds prime` invocation channels the agent toward prior thinking. The question isn't *whether* to influence — that ship has sailed — but whether amplifying selected ideas via lodestone status is net-positive or net-negative.

Arguments for amplification:
- Lodestones could *attract* agents toward important considerations they would otherwise miss.
- A few well-chosen pillars beat 200 indistinguishable seeds for orienting an agent.

Arguments against:
- Channeling effect: lodestones might suppress entire avenues of fruitful exploration.
- Promotion errors are sticky: a wrongly-elevated principle would distort every adjacent decision.
- The Jigsaw failure mode shows we can't predict how agents will interpret a principle.

## Possible mitigations (not decisions)

- Require explicit justification at promotion time ("this is load-bearing because…").
- Make demotion cheap — lodestones should be reversible if the project pivots.
- Surface lodestones to agents with hedging framing: "current principle; consider alternatives before applying" rather than as a constraint.
- Maybe lodestones should encourage *questioning*, not adherence — i.e., "before acting in this neighborhood, surface relevant lodestones and explicitly check whether they still hold."

## Meta

Hard to predict. We are designing for an intelligence that behaves unexpectedly. Whatever we build here should be testable and reversible, not bet-the-farm.

**Status after the 2026-08-27 cluster review (@aguynamedryan ruled: still live).** The rest of the seeds-147 cluster is resolved — the feature shipped as `seeds trellis` and seeds-148 / seeds-149 / seeds-150 / seeds-147.2 / seeds-147.3 / seeds-147.4 are all closed. This concern is the deliberate exception.

**Why it stays open.** The mitigation for it is phrasing discipline — the `seeds:trellis` skill and the README both demand a bounded, scoped line and cite the Jigsaw 33-refactor by name as the shape to avoid. But that mitigation has never been exercised: **no seed in this repo has ever been trellised** (`seeds list --tag trellis` is empty; the `lodestone` tags on the sibling seeds were applied by hand during the deliberation). The risk is untested, not retired, and closing it would record a confidence nobody has earned.

**What it costs.** Only `resolved` and `abandoned` are terminal (`db.py:574`, `models.py:457`), so keeping this open keeps the parent **seeds-147 blocked** indefinitely. That is accepted as an honest signal rather than worked around — deferring would not unblock it either.

**What would close it.** First real use: trellis something, then watch whether the promoted line channels an agent the way the Jigsaw principle did. Until a trellis line exists and has been lived with, there is nothing to evaluate.
