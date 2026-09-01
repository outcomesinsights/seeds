---
id: seeds-131
title: "Re-ingestion: source documents should be revisitable as project context evolves"
status: captured
type: idea
created_at: 2026-03-12T20:01:55.444027+00:00
updated_at: 2026-09-01T16:59:47.818652+00:00
tags:
  - architecture
  - gleaning
  - source-materials
  - glean
  - corrected-2026-09-01
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



---
**CORRECTION 2026-09-01 (measured, titan): the "~30 days" retention figure above is wrong, at least on this host.** The note from Clancey says Claude Code deletes transcripts after ~30 days, which motivated the snapshot-to-survive-pruning argument. Measured in this project's own transcript directory today: **40 transcripts spanning 109 days** (2026-05-14 to 2026-09-01), none pruned.

This does not kill the snapshot argument — retention may be configurable, host-dependent, or version-dependent, and a durable source store is still the right shape for re-gleaning. But it does mean `glean`'s historical pass (seeds-74.2.1, `--all` / `--since`) has substantially more runway than 30 days out of the box, and building against Clancey's snapshot DB is an optimization rather than a prerequisite. Do not design a 30-day cliff into the implementation without re-measuring first.
