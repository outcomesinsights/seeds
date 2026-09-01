---
id: seeds-153
title: "Concern: agent memory customization may distort the author's view of out-of-the-box seeds experience"
status: captured
type: concern
created_at: 2026-05-27T18:30:18.337184+00:00
updated_at: 2026-05-27T18:30:18.337192+00:00
tags:
  - meta
  - customization
  - drift
  - adoption
  - claude-memory
  - defaults
relationships:
  - target_id: seeds-152
    rel_type: relates-to
    created_at: 2026-05-27T18:30:59.737417+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Claude is increasingly eager to generate memory files at user and project level, accumulating customizations that shape how the agent works with each individual user. For most people this is good — the tool adapts to their working style.

For *tool authors*, it creates a specific epistemological problem: customizations specific to the author's usage progressively drift the author's experience away from what a new adopter would feel. As the seeds author, I can no longer cleanly assess "is seeds nice to use out-of-the-box, or have I quietly taught Claude to make seeds nice for *me*?"

## Why this matters for seeds

Two goals are in tension:

- We want flexibility — users should be able to customize how they use seeds.
- We want assurance that the out-of-the-box experience is solid — anyone who adopts seeds without setup should get something that works well.

Invisible customization works against the second goal. It also obscures whether our design is good or whether we're papering over deficiencies with accumulated memories.

This is part of *why* shipping skills/agents with seeds matters (see [[ship-an-agent-persona-cedric-and-or-skills]] and [[decision-skills-are-prompt-macro-scale]]) — good defaults should be baked into the tool, not just emergent in the author's environment.

## Possible responses

- **Periodic fresh-environment testing.** Spin up a Claude Code session with no user memory, no project CLAUDE.md, no accumulated customizations. Use seeds. Feel what a new adopter feels. Frequency: maybe at every major release.
- **Bake good defaults into shipped artifacts.** Skills, recommended prompts, the `seeds prime` output. Anything currently "in my head" or "in my CLAUDE.md" that genuinely helps should live somewhere portable.
- **Document recommended Claude Code setup alongside seeds.** Not as a prerequisite, but as a curated baseline so adopters can opt into a known-good configuration.
- **Author memory audit.** Some workflow for the author to inspect what has leaked into local memory and decide what should be promoted into seeds itself vs left as personal preference.

## Open

How would we even tell if a customization is "personal preference" vs "missing default"? The line is fuzzy. Probably the test is: would another seeds user benefit from this? If yes, promote it. If no, leave it personal.
