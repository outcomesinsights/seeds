# When a Seed Stops Being a Seed: Tensions Surfaced in a Design Session

**Date**: 2026-05-19
**Source**: A Claude Code session in the `code_set_catalog` project, designing the export feature.
**Anchor seeds**: csc-115 (Mark's Friday-ready bar), csc-115.1 (export feature design), csc-115.1.1 (now resolved; relocated to csc-147), csc-145 (PDF spin-off), csc-146 (compare-page spin-off), csc-147 (OHDSI/ATLAS interop spin-off).

This document captures observations and open questions about the seeds tool that emerged organically during a real design session. It's intended as input for a separate seeds-tool conversation — not a proposal.

## What happened, briefly

The session started with Ryan dumping a half-formed export-feature design ("CSV, JSON, maybe Excel; here's roughly what columns; what do you think?") and asking for critique. The assistant pushed back on five points, Ryan responded, several rounds of dig-list iteration followed, and we arrived at a fully-specified design ready for implementation.

Along the way we created one child seed (csc-115.1.1 for OHDSI/ATLAS interop) and noted two other deferred items inline (PDF report-style export, compare-page export). At the end, when reviewing the seed for "is this ready to spawn beads?", three structural problems surfaced. They are the subject of this document.

## The three tensions

### 1. Seeds with embedded OPEN/CONFIRM markers smell like missing child seeds

The export-design seed (csc-115.1) was built across the conversation as a chronological transcript. Each round added a new "## Round N" section appended to the bottom. Earlier sections carried markers like:

- `CONTESTED below`
- `(awaiting Ryan)`
- `OPEN: split or fold?`
- `Working proposed schema (subject to Ryan's reaction)`

By the time round 3 finished, every one of those markers had been resolved further down — but the markers were still there, in the body. The seed read as if it were full of open questions when it wasn't. A fresh reader had to mentally subtract the early "tentative" claims against the later "locked" resolutions.

The right thing to have done at the time was: every "I'll ask Ryan and update this" thought becomes a child question-seed; when Ryan answers, the question-seed resolves. The parent stays clean and reflects only locked decisions.

Doing this in-flight requires a different rhythm than the conversational "I'll just append it to the parent" instinct most natural to a streaming dialogue. The tool doesn't push you toward the question-seed pattern; the path of least resistance is to write into the body and add a marker.

**Observation**: A seed that accumulates OPEN/CONFIRM markers in its body is probably a parent that should have had children carrying those open questions. The marker is a structural smell.

**Open question for the seeds tool**: Could the tool detect (or warn about) markers like `OPEN`, `CONFIRM`, `TODO`, `(awaiting …)` in seed bodies and nudge the author toward extracting them as child question-seeds? Or is that too prescriptive for what is intentionally a low-friction capture tool?

### 2. Child seeds that are spin-offs block parent resolution forever

We created csc-115.1.1 as a child of csc-115.1 to hold the OHDSI/ATLAS interop question. csc-115.1.1 is a backlog idea — it won't be resolved until OHDSI ecosystem use cases materialize in our user base, which might be never, or might be years.

But because csc-115.1.1 was a CHILD of csc-115.1, csc-115.1 itself couldn't be resolved. The status panel showed `[BLOCKED by unresolved children]`. The export-feature seed — which describes work we want to ship NOW — was structurally tied to a piece of work we're explicitly deferring indefinitely.

This is the wrong relationship type. csc-115.1.1 isn't a sub-task of csc-115.1; it's a *spin-off discussion that emerged during the same conversation*. The two should be related but independent.

The seeds CLI's typed links (`seeds link --type`) currently support only three relationship types:
- `relates-to`
- `questions`
- `answers`

There's no `spin-off-of`, `superseded-by`, `deferred-from`, `derivative-of`, or similar. The choice is binary: child (blocks parent) or unrelated (loses thread).

We worked around this in the cleanup by:
1. Resolving csc-115.1.1 with a "relocated to csc-147" note.
2. Creating csc-147 as a new top-level seed with the same content.
3. Adding a `relates-to` link from csc-147 back to csc-115.1.

This works but feels like a structural patch on a missing affordance. The relation that actually exists — "csc-147 came out of csc-115.1's discussion but is not part of csc-115.1's scope" — has no direct expression in the tool.

**Open questions for the seeds tool**:
- Should there be a `spin-off-of` (or similar) typed link?
- Should the "blocking" semantics of the parent-child relationship be reconsidered? (e.g., a `--non-blocking` flag for child relationships)
- Or is the right answer that *children* should always be in-scope-of-parent, and the right pattern for spin-offs is exactly what we did — top-level seeds with `relates-to` links?

### 3. Seeds drift from "deliberation" to "specification" — and the tool doesn't notice

csc-115.1 started as an idea (Ryan's design dump) and a deliberation (critique, pushback, exploration). By round 3 it had become a *specification* — a row-by-row schema, a route block, MIME type table, JSON example, error-mode rules.

There's a discontinuity in what the seed IS at each of these points:

| Phase | What it is | Right tool? |
|-------|-----------|-------------|
| Initial dump | A half-formed proposal | Seed (idea type) |
| Critique cycles | A live conversation | Seed (exploration type) |
| Locked decisions | A specification | ?? |
| Implementation | A task | Beads |

There's a missing layer between "seed" and "bead". The seed captured the deliberation faithfully; the beads will capture the work. But the *specification* — the thing an implementer reads to know what to build — doesn't have a natural home. In this session it ended up as a "Final Design (Locked)" section prepended to the seed body, with the deliberation history preserved below.

That works but it's a stretch. The seeds tool is designed for low-friction deliberation capture; asking it to also be a spec authoring environment changes the rhythm. A user opening a seed expecting deliberation finds a 200-line spec instead. A user opening a seed expecting a spec has to scroll past the deliberation history to find the locked design.

**Ryan's framing** (paraphrased): "Maybe seeds is just idea and deliberation capture, and actual specification is a separate tool that sits between seeds and beads."

That feels right. The cost: a new tool to invent, build, and maintain. The benefit: each tool stays focused on what it's good at; the spec layer becomes a first-class artifact (versioned, reviewable, link-target-able) instead of a section in a seed body.

**Open questions**:
- What would a between-seeds-and-beads spec layer look like? A new tool? A formalized seed type (`type: specification`)? A separate file living alongside the seed?
- How does deliberation flow into spec, and spec flow into beads? Manual lift? Tool-mediated?
- Where do test fixtures, API contracts, schema diagrams live in this layered model? In the spec layer or the bead layer?
- What's the lifecycle of a spec? It probably becomes immutable once beads start consuming it, with subsequent changes requiring a new spec version. Seeds, by contrast, can be appended to indefinitely.

## Cross-cutting observation: the conversation had three concurrent topics

Toward the end of the session, Ryan named three distinct conversations happening simultaneously:

1. **Primary**: design the export feature, get it ready to spawn beads.
2. **Secondary**: clean up the seeds related to the feature so they're well-structured.
3. **Tertiary**: capture the philosophical observations about seeds tool itself (this document).

Conflating these three is a real risk in a long session. The seeds tool today doesn't help separate them — they all want to write into seeds, and the writer has to consciously decide which seed each thought belongs to. A spec layer might inadvertently help here by giving (1) its own surface, leaving seeds for (2) and (3).

## Suggested next moves for the seeds-tool conversation

In rough order of "cheap to address":

1. **Document the spin-off pattern** as established practice: when a tangent emerges during a seed discussion that won't be in scope, create it as a top-level seed with `relates-to` rather than as a child. (Cheap; documentation only.)
2. **Consider adding more typed link relationships**: `spin-off-of`, `superseded-by`, `deferred-from`, `derives-from`. (Moderate; new CLI options + storage.)
3. **Consider a lint check** for OPEN/CONFIRM/TODO markers in seed bodies that warns "these probably should be child question-seeds." (Moderate; needs a heuristic.)
4. **Consider a non-blocking child relationship**: a child seed that's part of the parent's conversation but doesn't block parent resolution. (Bigger; rethinks the parent-child semantics.)
5. **Consider a spec layer** between seeds and beads. (Big; new tool or major feature.)

## What this session did to mitigate the problems

For the export-feature design specifically, the in-flight workaround was:

- Resolved csc-115.1.1 with a "relocated to csc-147" note.
- Created csc-147 as a new top-level seed with `relates-to csc-115.1`.
- Created csc-145 (PDF) and csc-146 (compare-page) as top-level seeds with `relates-to csc-115.1` from the start.
- Rewrote csc-115.1 to prepend a "Final Design (Locked)" section above the preserved deliberation history.
- Stripped the in-body OPEN/CONFIRM markers (the resolutions they referenced are now in the locked spec section).

This is acceptable for one feature but doesn't scale as a manual practice. Hence this document.

## Pointers

- Beads work for the actual export-feature implementation will be filed in `code_set_catalog`'s beads tracker as csc-NNN entries, gated on csc-115.1's Final Design section.
- This document lives independently of those beads; it's input for a future seeds-tool conversation, not a deliverable on the export feature.
