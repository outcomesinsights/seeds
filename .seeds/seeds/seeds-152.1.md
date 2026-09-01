---
id: seeds-152.1
title: "Skill: ingest a live user utterance into new/updated seeds"
status: captured
type: idea
parent: seeds-152
created_at: 2026-05-27T18:08:34.743486+00:00
updated_at: 2026-05-27T18:08:34.743493+00:00
tags:
  - skill
  - workflow
  - utterance-ingest
  - seeds-creation
relationships:
  - target_id: seeds-181.1
    rel_type: relates-to
    created_at: 2026-06-23T20:44:23.287286+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Sub-skill under seeds-152: a way for the user to say "update or create new seeds based on what I'm about to say" and have the agent file the resulting seeds without further ceremony.

## Difference from existing `transcript-seeds` skill

The `transcript-seeds` skill (Claude Code, already exists) ingests *meeting transcripts* as a batch operation. This new skill would be for *live conversational utterance* — the user speaks/types a stream of thought during an active session, and the agent files the appropriate seeds and questions in real time, with sensible defaults for type and tagging.

The rhythms are different enough (batch vs. live) that this probably wants to be a sibling skill, not an extension of `transcript-seeds`.

## Likely shape

- Accept a freeform utterance.
- Decide whether content should produce one seed or several.
- Decide type (idea/question/decision/exploration/concern) per resulting artifact.
- Decide whether to create a new seed, update an existing one, or attach a question to an existing one.
- Surface the proposed actions to the user before committing them — given [[agents-treat-user-context-as-gospel]], the agent should not blindly file what it heard.

## Risk

Same dynamic as the parent concern: if the skill files seeds aggressively without confirmation, it amplifies an already-present pattern of the agent inventing structure from messy input. Confirmation gates matter.
