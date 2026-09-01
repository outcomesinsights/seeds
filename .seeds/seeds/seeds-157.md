---
id: seeds-157
title: "Decision: multi-contributor attribution via git blame, not in-schema authorship"
status: captured
type: decision
created_at: 2026-06-15T20:43:59.376210+00:00
updated_at: 2026-08-31T20:02:41.634826+00:00
tags:
  - attribution
  - multi-user
  - multi-agent
  - collaboration
  - git-blame
  - decision
relationships:
  - target_id: seeds-117
    rel_type: relates-to
    created_at: 2026-06-15T20:44:17.983438+00:00
  - target_id: seeds-121
    rel_type: relates-to
    created_at: 2026-06-15T20:44:18.110631+00:00
  - target_id: seeds-126
    rel_type: relates-to
    created_at: 2026-06-15T20:44:18.228441+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Decision:** For a shared multi-contributor seeds database (e.g. @aguynamedryan + @markdanese deliberating over one DB), seeds will NOT add any in-schema authorship or per-update attribution. "Who said what" is recovered from git blame on the shared repo's JSONL. AI-agent contributions intentionally subsume under the operating human — they commit under whoever is driving the session. Provenance of bulk-imported corpora is a separate, already-designed concern (seeds-126 records which source document a seed came from), not an attribution axis.

**Context / motivating use case:** @aguynamedryan and @markdanese are doing overlapping work on defining code sets within vocabularies (SNOMED, ICD-10, mappings, embeddings, LLM-evaluated code sets). @markdanese has a mature pipeline that turns a few words ("dementia") into a swath of vocabulary codes; @aguynamedryan comes at it from published code sets and finding related ones. They want one shared seeds DB holding both bodies of investigation so a collaboration-aware agent can cross-reference, challenge, and answer across the boundary. Question raised: do we track who suggested an idea (@markdanese vs @aguynamedryan vs AI collaborator)?

**Rationale:**
- The value of a seed is its *current synthesized state*, not a forensic log of who typed what.
- Per-update attribution would force the single-markdown body into attributed chunks (a comment-thread model) — a heavier, fundamentally different data model. Not worth breaking the schema.
- git blame already gives commit-level attribution for free, at exactly the useful granularity: a "@markdanese stream" vs a "@aguynamedryan stream", each inclusive of its agent's work (the agent commits under whoever drives it). AI authorship is real, but it folds into the human stream rather than needing its own axis.
- The collaboration value @aguynamedryan described ("his work answers my questions; my work challenges his assumptions; my work operationalizes his from another angle") is better carried by typed links + questions between seeds than by author tags — but that is a separate strand (seeds-117, seeds-121), not blocked by this decision.

**Preconditions for this to work:**
- A shared git repo.
- Each contributor commits as themselves (correct git user.name/email per person/machine), or blame lumps everyone under one identity.

**On the AI-as-author question:** The AI is a genuine partner and author of investigations — not a "compiler". That is accepted. It is simply separable from, and does not justify, tracking AI authorship in-schema today.

**Scope / not permanent:** This is a "good enough for now, zero-change" scoping choice. Revisit only if blame proves insufficient or clumsy — specifically, if we repeatedly want to attribute at finer grain than a commit, *within* a single seed's body.
