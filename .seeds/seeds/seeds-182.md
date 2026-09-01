---
id: seeds-182
title: "seeds: emit a high-level self-summary of a repo (interesting / recent / popular) for external routers"
status: captured
type: idea
created_at: 2026-06-23T20:43:33.572245+00:00
updated_at: 2026-08-31T20:02:45.464348+00:00
tags:
  - seeds-feature
  - self-summary
  - dynamic-prime
  - routing
  - 2026-06-23
relationships:
  - target_id: seeds-181.3
    rel_type: relates-to
    created_at: 2026-06-23T20:44:23.856516+00:00
  - target_id: seeds-87
    rel_type: relates-to
    created_at: 2026-06-23T20:44:24.202651+00:00
  - target_id: seeds-130
    rel_type: relates-to
    created_at: 2026-06-23T20:44:24.314421+00:00
  - target_id: seeds-181
    rel_type: relates-to
    created_at: 2026-06-23T20:44:24.428986+00:00
  - target_id: seeds-183
    rel_type: relates-to
    created_at: 2026-06-23T20:44:24.765221+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Captured 2026-06-23 from docs/sower.txt. A seeds-the-project feature, surfaced by the sower idea but kept in this repo (sower would consume it; it should not leave when sower spins out).

A seeds repo should be able to report a terse, high-level summary of itself, so an external router (sower) does not have to read everything to know what the project is about:

> "Maybe that is a feature we build into seeds that gives like a high-level summary of what's interesting, what's you know, what the main thrust of a given seeds repo is, what's fairly recent, and/or what's been popular, and in terms of the seeds."

The ranking intuition: when @aguynamedryan mentions a project, he is usually talking about its recent or common threads —

> "generally, I would assume that when I'm talking about a project, I'm talking about recent or common threads for discussion. And then, if each seeds repo is able to report that, that would make the seed spreader job a lot easier."

So the summary should foreground recency and popularity/commonality, not just a flat dump. This is a refinement of dynamic prime (seeds-87) and the compressed project-context representation explored in project-aware gleaning (seeds-130), with a new framing: the consumer is an external cross-project tool, and recent + popular are explicit ranking signals.

## Related
seeds-87, seeds-130
