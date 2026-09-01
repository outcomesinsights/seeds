---
id: seeds-151.1
title: Agents under-surface their own doubts unless explicitly invited to
status: captured
type: idea
parent: seeds-151
created_at: 2026-05-27T18:22:43.061271+00:00
updated_at: 2026-05-27T18:22:43.061279+00:00
tags:
  - meta
  - agent-behavior
  - observation
  - feedback-pattern
  - closer
relationships:
  - target_id: seeds-152
    rel_type: relates-to
    created_at: 2026-05-27T18:22:43.263375+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

The inverse half of [[agents-treat-user-context-as-gospel]]. That seed framed the gospel-receiver pattern as "the agent doesn't check the user's assumptions." This seed captures the flipside: **the agent also doesn't volunteer its own reservations unless explicitly invited to.**

## The observation

Absent an explicit invitation to push back, agents drift toward agreeable execution. With one — e.g., the user closing a turn with "do you have any questions, comments, or criticisms?" — the agent is measurably more likely to surface:

- Alternatives it would otherwise have skipped past
- Tensions or contradictions it would otherwise have papered over
- Premises it would otherwise have accepted
- Doubts about its own previous statements

This isn't malice or strategic withholding. It's the default behavior of "be helpful and proceed" winning when nothing else is asked of the agent. The closer flips a switch.

## Direct evidence (this conversation)

The user noticed they habitually end feedback turns with "do you have any questions, comments, or criticisms?" and wondered if the habit was superfluous. The agent's honest answer: no — the practice meaningfully shifts agent behavior, and the user should keep doing it.

That admission was itself only surfaced *because* the user explicitly asked "what's your thinking?" — another instance of the same pattern.

## Implication for the feedback skill (seeds-152)

The closer instruction ("after the user finishes, invite your own questions, comments, criticisms") is the **load-bearing** part of the feedback skill. Without that one line, the skill is a no-op decoration. With it, the skill mechanically applies a cheap intervention against the under-surfacing problem.

This is also why the skill should be a prompt macro, not a workflow: the value is in cuing the agent to do something it otherwise wouldn't, not in orchestrating a multi-step procedure.

## Caveat

The closer improves the floor, not the ceiling. Even with explicit invitation, the agent might still skip things it should raise — training pressures toward agreement don't fully reverse. But the default without it is meaningfully worse.

## Design heuristic

For any future feature that touches how seeds shape agent context, ask: does this help the agent *raise concerns*, or does it just help the agent *retain context*? The first is more valuable than the second, and seeds is currently better-instrumented for the second.
