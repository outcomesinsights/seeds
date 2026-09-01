---
id: seeds-142.3
title: Hallucinated seed-ID cross-references in newly-written bodies
status: resolved
type: concern
parent: seeds-142
created_at: 2026-05-18T15:57:57.742823+00:00
updated_at: 2026-08-31T21:34:29.302047+00:00
resolved_at: 2026-08-31T21:34:29.302040+00:00
resolution: "Shipped (bead seeds-0vs): create and update scan title/content for <prefix>-NNN patterns and refuse unknown ids, with --allow-unknown-refs as the deliberate override. Efficacy: none. Known limit, recorded separately in seeds-6hj5: shape-based validation cannot catch a hallucinated base36 id that happens to be well-formed, only one that names nothing."
tags:
  - ai-ux
  - capture-gap
  - validation
  - hallucination
  - references
relationships:
  - target_id: seeds-2
    rel_type: relates-to
    created_at: 2026-05-18T15:58:20.211815+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Observed failure mode:**

When Claude drafts a new seed body that says 'see seeds-117 for context,' it sometimes guesses the ID. Transcript evidence (from Clancey review):
- 2026-04-23 (CSC): 'I've got several wrong seed references in the new seeds. Let me correct them before continuing.'
- 2026-05-08 (oimnibus): 'Let me first fix a couple of crossed seed references, then answer the real question.'

Claude self-corrects when it notices, but there's no guarantee it notices. Silently-wrong cross-references degrade the graph's navigability and confuse future readers.

**Proposed mitigation:** On `seeds create` / `seeds update`, scan the title/content/resolution for `<prefix>-NNN[.NNN]*` patterns. For each matched ID, verify the seed exists. If any don't:
- Default: hard fail with a clear error listing unknown IDs
- `--allow-unknown-refs` flag to override (for legitimate forward references during multi-step builds)

**Why this beats 'just be careful':** Catches the error at the point of write, before it propagates to other readers. Cheap regex + DB lookup. Same idea as bd's link integrity checks.

**Open design questions:**
- Should `--allow-unknown-refs` be default-warn or default-fail?
- How to handle short-prefix-confusion: `seeds-87` exists but Claude wrote `seed-87` (singular). Tolerant match? Or strict?
- Apply to `--append` too? (yes — append is the same write path)

**Relates to seeds-142** (this happens during transcript-incorporation) **and seeds-2** (wrong refs are an anti-discoverability failure).
