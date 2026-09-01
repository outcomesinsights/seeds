---
id: seeds-181.1
title: "sower: the routing engine — ingest a transcript, identify projects, create/update seeds, route"
status: captured
type: exploration
parent: seeds-181
created_at: 2026-06-23T20:43:33.016177+00:00
updated_at: 2026-08-31T20:02:45.108396+00:00
tags:
  - sower
  - routing
  - ingestion
  - agent
  - 2026-06-23
relationships:
  - target_id: seeds-142
    rel_type: relates-to
    created_at: 2026-06-23T20:44:23.068605+00:00
  - target_id: seeds-130
    rel_type: relates-to
    created_at: 2026-06-23T20:44:23.185079+00:00
  - target_id: seeds-152.1
    rel_type: relates-to
    created_at: 2026-06-23T20:44:23.287286+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Captured 2026-06-23 from docs/sower.txt. The core loop of sower (part of the sower umbrella).

## The loop

For any transcript @aguynamedryan feeds it, sower must:
1. Ingest the transcript.
2. Determine which projects were discussed.
3. For each, decide which seeds need to be created or updated.
4. Route those seeds into the right project's seeds database.

> "it would need to then take any given transcript, ingest that transcript and determine which projects were discussed and what seeds may or may not need to be made."

> "then it would be able to route various ideas or various seeds to various projects."

## Shape (open)

Possibly just an agent wired together with scripts that pulls transcripts and walks them:

> "I don't know if this is like an agent that I would just put together with some coherent scripts that would, you know, run through and grab transcriptions of every voice memo or whatever it is I feed it."

This is the productized form of the transcript-incorporation workflow already captured as seeds-142 (and its dedupe-and-create discipline), driven by the project context described in seeds-130. The update-vs-create judgment, hallucinated-ID risk (seeds-142.3), and "only look at what I haven't processed" (seeds-142.2) all apply here, per-project.

## Related
seeds-142, seeds-130, seeds-152.1



## Input source & quality

The input is voice memos, which @aguynamedryan finds far lower-friction than self-messaging:

> "In the past, I've been trying to send myself messages, and that's frustrating at times with there being pauses, and the dictation wants to stop at some point after it's run for a while. But a voice memo is a full recording of what it is I've said."

A voice memo carries both the audio and Apple's auto-transcript — but @aguynamedryan trusts that transcript less than his preferred dictation tool:

> "plus Apple's best attempt at a transcript, which I don't necessarily trust to be as good as the transcripts that get generated from my preferred dictation tool right now, Fluid voice."

Open question for sower: which transcript does it consume — Apple's built-in one, or a (better) re-transcription via Fluid Voice or another engine — and does input quality affect routing accuracy?
