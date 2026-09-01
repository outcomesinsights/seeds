---
id: seeds-181.3
title: "sower: survey each project before routing (cold-start understanding)"
status: captured
type: idea
parent: seeds-181
created_at: 2026-06-23T20:43:33.256768+00:00
updated_at: 2026-06-23T20:43:33.256775+00:00
tags:
  - sower
  - survey
  - cold-start
  - project-context
  - 2026-06-23
relationships:
  - target_id: seeds-130
    rel_type: relates-to
    created_at: 2026-06-23T20:44:23.638124+00:00
  - target_id: seeds-87
    rel_type: relates-to
    created_at: 2026-06-23T20:44:23.754150+00:00
  - target_id: seeds-182
    rel_type: relates-to
    created_at: 2026-06-23T20:44:23.856516+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Captured 2026-06-23 from docs/sower.txt. Part of the sower umbrella.

Before routing anything, sower must understand each project. On each run it would pull a summary of the seeds already in each project:

> "I imagine when each time it gets fired up, what it would want to do is grab a summary of the seeds that are already in each project."

> "I think it needs to first understand each project before it starts routing, which means it would need to survey each project before routing."

Open scale question — how much state must it hold?

> "I don't know how big of a how big of a database it needs to keep track of for seeds."

This is the consumer side. The producer side — a seeds repo emitting a high-level self-summary (what's interesting / recent / popular) — is captured as a separate seeds-the-project feature so it stays in this repo when sower spins out. Builds on project-aware gleaning (seeds-130) and dynamic prime (seeds-87).

## Related
seeds-130, seeds-87
