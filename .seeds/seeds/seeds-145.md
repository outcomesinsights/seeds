---
id: seeds-145
title: Convention — parent-child vs top-level+relates-to for in-scope vs deferred sub-seeds
status: captured
type: question
created_at: 2026-05-21T18:36:09.534328+00:00
updated_at: 2026-08-31T20:02:40.926986+00:00
tags:
  - convention
  - parent-child
  - relates-to
  - workflow
  - ai-ux
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Open question surfaced during code_set_catalog session 2026-05-21.

When an umbrella seed has sat in `captured` for a while and we're ready to focus on a subset of it (a "focused implementation of part of the larger idea"), what should the structure be?

Two patterns came up:

1. **Child seed** (`.N` notation). Precedent: csc-115.1 under csc-115, csc-88.1 under csc-88. Reads as "the implementation of part of the umbrella thinking."
2. **New top-level seed with `relates-to` link**. Precedent: csc-147 (relocated from csc-115.1.1) per the workaround in seed-vs-spec-tension-2026-05-19.md.

The May 19 doc proposed an interim distinction: child if the sub-seed is in-scope and will resolve when shipped; top-level + relates-to if it is a spin-off or deferred-indefinitely (because children block parent resolution, and deferred children block forever).

This convention was operationalized informally in code_set_catalog on 2026-05-21:
- csc-65 (umbrella, post-alpha thinking about extras JSON column) gets csc-65.1 as a child (alpha implementation, will resolve when shipped).
- The deferred ingest-side promotion playbook becomes a new top-level seed with relates-to csc-65, NOT csc-65.2 — because it is deferred until external publishers exist, which might be years.

Open questions for this seeds-tool conversation:
- Is "will it resolve in scope of the parent's resolution?" the right gate?
- What about umbrella seeds that themselves never resolve (e.g. csc-65 is post-alpha thinking that may always stay open)? Are children still appropriate when the parent isn't trying to resolve?
- Should this be codified in working-with-seeds.md, or fold into the May 19 doc, or both?
- Are there non-blocking child relationships that would dissolve the tension entirely?

Don't update docs yet — @aguynamedryan wants to fold this into seed-vs-spec-tension-2026-05-19.md when he is working in the seeds project directly.

Related: seed-vs-spec-tension-2026-05-19.md (the document this question follows from), seeds-118 (spec graduation lifecycle).
