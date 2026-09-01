---
id: seeds-152
title: Ship an agent persona (e.g., 'Cedric') and/or skills bundled with seeds for deliberation workflows
status: captured
type: idea
created_at: 2026-05-27T18:08:01.313438+00:00
updated_at: 2026-05-27T18:08:01.313447+00:00
tags:
  - agent
  - skills
  - workflow
  - cedric
  - seeds-to-beads
  - packaging
relationships:
  - target_id: seeds-151
    rel_type: relates-to
    created_at: 2026-05-27T18:08:34.834216+00:00
  - target_id: seeds-151.1
    rel_type: relates-to
    created_at: 2026-05-27T18:22:43.263375+00:00
  - target_id: seeds-153
    rel_type: relates-to
    created_at: 2026-05-27T18:30:59.737417+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Idea: package the deliberation workflows we keep re-improvising into either a named agent persona ("Cedric") or a set of skills shipped alongside the seeds CLI — or both.

## Concrete workflows worth packaging

1. **Feedback loop with closure check.** User opens with "this is feedback on your latest statement," walks through the feedback, then ends with "do you have any questions, comments, concerns?" The expectation is that the conversation continues until the agent either resolves every item or explicitly signals "I think we've addressed everything." The closing handshake is the load-bearing part.

2. **Seeds → beads handoff.** When a deliberation reaches a point where ideas are concrete enough for implementation, the user flips the relevant seeds (or sub-tree) into a set of beads. Today this is manual: read the seed, paste into `bd create`. Packaging would automate the conversion while preserving lineage (which seed did this bead come from?).

3. **Question sweep.** Walk attached questions on a seed and prompt for answers, marking each `answered`/`deferred` as it goes.

## Agent persona vs skill — open question

- **Agent (Claude Code subagent)**: invoked with "use the cedric agent…", carries a persistent personality and tool scope. Good fit if we want Cedric to *behave differently* (more questioning, more deliberative) than the main agent.
- **Skill (slash command)**: invoked with `/seeds-to-beads` or `/closure-check`. Good fit if the value is *workflow shortcuts* without changing how the agent behaves between commands.
- These are not exclusive. Could ship a `cedric` agent that uses internal skills, plus standalone skills usable from any context.

## Does beads already do this?

Beads ships a bunch of `beads:*` skills (audit, close, dep, ready, list, workflow, show, etc.) — so there's precedent for shipping skills with a tracker. I'm not aware of beads shipping a *persona* agent. Worth verifying before duplicating.

## Risk — direct tie to [[agents-treat-user-context-as-gospel]] and [[risk-lodestones-may-over-channel-agent-reasoning]]

The "I think we've addressed all items" declaration is exactly the kind of confident agent claim that triggered the concerns in seeds-147.1 and seeds-151. If Cedric closes deliberations by announcing completeness, we're institutionalizing the very over-confidence we were just worried about. Mitigation might be: Cedric declares "here's what I think is unresolved" rather than "we're done" — leaves closure to the human.

## Risk — ritualizing the closer

If Cedric mechanically asks "any questions, comments, concerns?" at the end of every turn, the ritual becomes noise and gets ignored. The pattern is valuable *because* it's user-initiated and intentional. Better to ship it as an opt-in skill (`/closure-check`) than to bake it into every Cedric reply.

## Open shape

- Naming: Cedric fits the convention (jarod, ethel, conrad…). Worth a beat to make sure "cedric" doesn't already mean something to someone.
- Distribution: ships *with* the seeds package? installed separately to `~/.claude/agents/`? versioned with seeds releases?
- Scope creep: how do we keep Cedric focused on deliberation rather than gradually absorbing every adjacent workflow?
