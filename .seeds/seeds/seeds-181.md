---
id: seeds-181
title: "sower: cross-project transcript-to-seed router (formerly 'spreader')"
status: captured
type: exploration
created_at: 2026-06-23T20:42:59.944977+00:00
updated_at: 2026-08-31T20:02:44.996136+00:00
tags:
  - sower
  - spreader
  - new-project
  - transcript-ingestion
  - routing
  - voice-memo
  - cross-project
  - 2026-06-23
relationships:
  - target_id: seeds-142
    rel_type: relates-to
    created_at: 2026-06-23T20:44:22.434941+00:00
  - target_id: seeds-130
    rel_type: relates-to
    created_at: 2026-06-23T20:44:22.547276+00:00
  - target_id: seeds-129
    rel_type: relates-to
    created_at: 2026-06-23T20:44:22.653821+00:00
  - target_id: seeds-87
    rel_type: relates-to
    created_at: 2026-06-23T20:44:22.761785+00:00
  - target_id: seeds-126
    rel_type: relates-to
    created_at: 2026-06-23T20:44:22.869677+00:00
  - target_id: seeds-182
    rel_type: relates-to
    created_at: 2026-06-23T20:44:24.428986+00:00
  - target_id: seeds-183
    rel_type: relates-to
    created_at: 2026-06-23T20:44:24.646580+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Captured 2026-06-23 from a solo voice memo (docs/sower.txt). Renamed from "spreader" to **sower** at @aguynamedryan's request. This seed is the umbrella for all sower thinking and is expected to be exported into its own project later, so its children are kept sower-specific.

## The idea

A standalone, more-formalized version of the transcript-ingestion tool @aguynamedryan has been prototyping in oimnibus: a tool that takes a voice-memo transcript (or any transcript), figures out which projects it touches, and routes the resulting seeds into each project's seeds database.

> "what I really need to do is break that up. Or, what I need is a tool that is something like a seed spreader... which would be kind of the transcript ingestion tool that I've been working on in OIMNIBUS, but more formalized."

> "what that program would need is to know what projects have seeds in them, what those projects are oriented towards, and then it would need to then take any given transcript, ingest that transcript and determine which projects were discussed and what seeds may or may not need to be made."

The trigger was realizing voice memos remove the friction of self-messaging:

> "having voice memo available to me at all times is kind of an eye-opening game changer... I didn't really understand that I had the ability to monologue so easily."

A single memo often spans multiple projects, so the core need is to break one transcript apart and route its pieces:

> "if I have multiple ideas across different projects and things like that in a given voice memo, what I really need to do is break that up."

## Where it lives

Probably a hub on @aguynamedryan's laptop (voice memos are Apple-oriented), reaching out to the remote servers where the projects live:

> "probably something located probably on my laptop because voice memos are Apple oriented and then that laptop has access to the various remote servers where all the projects live."

## Relationship to existing seeds

sower is essentially the productization of an existing cluster in this repo, not a greenfield idea:
- seeds-142 — transcript-incorporation workflow (the recurring dedupe-and-create use case; already grew out of oimnibus + the transcript-seeds skill)
- seeds-130 — project-aware gleaning (the routing brain: the LLM needs each project's context)
- seeds-129 — source documents may span multiple projects (the multi-project routing concern)
- seeds-87 — dynamic prime (the live project state sower would consume)
- seeds-126 — source-document ingestion / inbox model

## Children (sower-specific threads)

Broken out below: (1) the routing engine / core ingest loop; (2) the project registry + cross-server/location awareness; (3) survey-before-routing (cold-start understanding of each project); (4) meeting the tool halfway (self-labeling projects + how much @aguynamedryan should adapt his speaking style).

Two implied seeds-the-project features are captured as separate top-level seeds (kept in this repo so they don't leave with sower on export) and linked: a per-repo self-summary report, and a single-location cross-project query.

## Related
seeds-142, seeds-130, seeds-129, seeds-87, seeds-126
