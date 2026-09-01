---
id: seeds-131
title: "Re-ingestion: source documents should be revisitable as project context evolves"
status: captured
type: idea
created_at: 2026-03-12T20:01:55.444027+00:00
updated_at: 2026-06-05T17:26:09.378211+00:00
tags:
  - architecture
  - gleaning
  - source-materials
relationships:
  - target_id: seeds-4
    rel_type: relates-to
    created_at: 2026-03-12T20:04:54.382451+00:00
  - target_id: seeds-133
    rel_type: relates-to
    created_at: 2026-03-12T20:06:55.144075+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Insight:** The same source document may yield different seeds at different points in a project's lifecycle. Early on, you might not recognize a passing comment as relevant. Later, with more context about what the project needs, that comment becomes a seed.

**Implication:** Source documents should be stored (or at minimum, remain accessible) so they can be re-gleaned. A one-pass extraction is inherently incomplete.

**Design consequence:** This argues against aggressive clipping. If you clip a transcript down to 3 relevant paragraphs on first pass, you've lost the other content that might become relevant later.

**Pragmatic resolution:** Source documents live on disk somewhere (server, local filesystem). Seeds doesn't need to be the system of record for the source document itself — it just needs to be able to find it again. For the initial implementation, the user can simply re-queue a document for re-ingestion. Automating re-ingestion across all sources is a future concern, not a launch blocker.


---
**Concrete mechanisms from Clancey (2026-06-05) — see seeds-156:**
- Idempotent re-ingestion: Clancey keys ingest on an mtime cache (path, mtime_ms) + delete-then-reinsert per session unit, so re-importing a *changed* transcript never doubles. Directly applicable to re-gleaning here and the dedup half of seeds-142.
- Snapshot-to-survive-pruning: Claude Code deletes transcripts after ~30 days; Clancey copies every transcript into its own SQLite so its memory outlives the cleanup. That snapshot store IS the "source docs remain accessible" this seed wants — seeds could read Clancey's snapshot DB as its durable gleaning corpus rather than build its own.
