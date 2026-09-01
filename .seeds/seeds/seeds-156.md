---
id: seeds-156
title: Clancey's passive memory is orthogonal to seeds' deliberation — the capture trio
status: captured
type: idea
created_at: 2026-06-05T00:21:00.191373+00:00
updated_at: 2026-06-05T17:26:09.238749+00:00
tags:
  - clancey
  - seeds
  - beads
  - tooling
  - mental-model
  - memory
relationships:
  - target_id: seeds-112.4
    rel_type: relates-to
    created_at: 2026-06-05T17:26:20.592761+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Why I want to keep this: clancey (now 1.6.0) clicked for me as a design, and I do not want to lose the mental model of how it fits alongside seeds and beads. Capturing it here in the seeds repo because the clancey/seeds relationship is directly relevant to how seeds is positioned.

Clancey's approach (the thing I like): a *passive, retrospective* memory of my Claude Code work. 1.6.0 ingests conversations via Claude Code hooks (PostToolUse + SessionStart) into a local SQLite store (~/.clancey/clancey.db), and the agent records decisions (what was decided + why) and learnings (non-obvious facts) in the background as it works. I do nothing; it accumulates. Future sessions recall it via search / recall / grep_turns / read_turns, anchored to repo + branch + files. It captures what already happened and why.

How it is orthogonal — the capture trio:
- seeds = prospective. Unsettled ideas/questions I deliberately capture and let grow (lifecycle: explore -> defer/resolve/abandon). Serves me, the thinker.
- beads = actionable. Concrete tasks/work to do.
- clancey = retrospective. Settled facts/decisions/conversation, captured passively. Serves the future agent.

Separating axes: tense (seeds forward-looking, clancey backward-looking), capture mode (seeds deliberate by me, clancey automatic), audience (seeds for me, clancey for the agent). Different enough that they chain rather than compete: a fuzzy idea -> seeds -> explored -> resolves into a decision -> recorded in clancey (and may spawn beads tasks).

The one overlap seam to watch: a resolved seed and a recorded clancey decision can both say 'we chose X because Y'. The distinction: seeds tracked the *deliberation getting there*; clancey records only the *outcome + rationale* stamped onto the code. Seeds is the journey, clancey is the destination. Risk = recording the same conclusion in both and letting them drift. Practice: let clancey auto-capture the what-we-did, reserve seeds for thinking that is not done yet.

Room to grow (why this is a seed, not just a clancey note): explore workflows that deliberately exploit the orthogonality — when a seed resolves, do I hand the conclusion to clancey explicitly, or trust passive capture? Is a clean seeds -> clancey handoff worth building? Where exactly should the decision/rationale boundary live so the two never duplicate? And since seeds and clancey are sibling tools here, is there a product opportunity in making that handoff first-class?


---
## Architecture deep-dive (2026-06-05): feature lessons + guardrails

Went past the README into the Clancey source. Lessons for seeds, kept here because this is the Clancey seed.

**Capture mechanism — the passive/active split (the core idea):**
- *Facts* (which file/command, repo, branch, ts) captured 100% passively by a PostToolUse hook — zero agent cost, no model in the loop.
- *Reasons* (why, alternatives rejected) never inferred — captured *actively* by nudging the agent to record them.
- Two hooks only: SessionStart (standing "record as you go" instruction) + PostToolUse (matcher Edit|Write|MultiEdit|NotebookEdit|Bash). Hook never blocks; fails silent.
- Reliability trick: just-in-time, *event-triggered* nudges (detect git commit / gh pr create then "capture now"), with cooldowns; generic per-edit reminders are throttled hard. v1.5.0 rationale: event-tied lands reliably, per-tool-call causes fatigue.
- The seeds adaptation (different triggers, because deliberation isn't a shell event): seeds-112.4.

**Backfill — correction to the mental model:** clancey backfill is a plain CLI doing *deterministic* transcript parsing (imports tool events + verbatim messages + a small "framing" embedding so old sessions are searchable). It does NOT LLM-extract decisions. "Fill in the decisions it finds" = an agent behaviour (you ask Claude to read old transcripts and record them), not a pipeline. Implication: seeds' transcript-incorporation (seeds-142) is already *more* ambitious than Clancey's backfill.

**Smaller liftable mechanisms (mechanism, not policy):**
- Retrieval ladder: recall (deterministic, branch to sessions) -> search (semantic) -> grep_turns (FTS keyword) -> read_turns (full read), with an explicit low-confidence handoff (semantic score < 0.45 -> "try keywords"). UX template for discoverability — seeds-2, seeds-87.
- Semantic dedup without a vector DB: a ~30MB local MiniLM (384-dim) with brute-force cosine in-process. Makes "does this already exist?" cheap in Python — seeds-142.1.
- Idempotent re-ingestion: mtime cache + delete-then-reinsert per session unit -> re-gleaning never duplicates — seeds-131.
- Revise-or-drop discipline: update/remove re-embed, treated first-class for "wrong or duplicated" notes -> note rot, hallucinated refs (seeds-142.3).

**What NOT to bring over (orthogonality guardrail):**
- Not the passive tool-event log — seeds cares about *why*, not which files changed. Porting it makes a worse Clancey.
- Not the invisible + copious policy — seeds is deliberate, visible, human-in-the-loop.

**The handoff seam, made concrete:**
- seeds resolve IS a Clancey "decision point" — a settled rationale waiting to be recorded.
- Clancey's snapshot DB (every Claude Code transcript, pruning-proof, subagents folded in as of v1.6.0) is a ready-made durable gleaning corpus for seeds-131 / seeds-142 — seeds could consume it rather than build its own snapshotting.
- Drift boundary still holds: the destination (settled decision + rationale) -> Clancey; the journey-not-done -> seeds.
