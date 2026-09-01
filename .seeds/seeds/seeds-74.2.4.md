---
id: seeds-74.2.4
title: Harvest seeds is source-agnostic deliberation extraction
status: resolved
type: idea
parent: seeds-74.2
created_at: 2026-02-09T14:31:38.746545+00:00
updated_at: 2026-09-01T16:47:37.752028+00:00
resolved_at: 2026-09-01T16:47:37.752020+00:00
tags:
  - architecture
  - harvest
  - integration
  - glean
  - naming
  - ratified
relationships:
  - target_id: seeds-125
    rel_type: relates-to
    created_at: 2026-03-12T20:06:55.221328+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Key insight:** Harvesting seeds from Claude conversations is the same process as harvesting from ANY deliberation source.

**Potential sources:**
- Claude conversation logs
- Meeting transcripts (Zoom, Teams, etc.)
- Email threads
- Slack/Discord channels
- PR discussions / code review comments
- Document comments (Google Docs, Notion)
- Voice memos / audio transcripts

**Common pattern:**
All are unstructured/semi-structured text containing:
- Decisions made (and rationale)
- Questions raised (answered or not)
- Investigations and findings
- User/participant insights

**Architecture implication:**
- Harvest logic should be source-agnostic
- 'Sweep' = point extractor at a text source
- Different sources may have different markers, but core extraction is same
- `seeds harvest <source>` where source could be:
  - `--conversation` (Claude JSONL)
  - `--transcript <file>` (meeting)
  - `--email <mbox/thread>`
  - `--slack <export>`
  - `--stdin` (pipe anything)

**This makes seeds a general deliberation→structure tool, not just Claude-specific.**



## CORRECTION: User pushback

Too hard a pivot. Overlaps with intent.build's positioning.

**Seeds' actual secret sauce:**
Not 'capture from anywhere' but the **structured database** around deliberation:
- Hierarchical seeds (parent/child for drilling down)
- Questions as first-class objects attached to seeds
- Lifecycle: captured → exploring → resolved/deferred/abandoned
- Blocked/dependency relationships
- Records the *discovery and exploration process*, not just decisions

**The difference:**
- Intent.build: System of record for *decisions* (the outputs)
- Seeds: Structured tracking of the *deliberation process* (the journey)

Seeds answers: 'How did we get here? What did we explore? What questions led to this decision? What's still open?'



---
**Terminology refinement (Mar 2026):**

The user identified that 'harvest' and 'gather' are overloaded — seeds is both the tool and the thing being extracted. Agriculture vocabulary offers more precision:

- **Glean**: pick through existing material to find valuable seeds (best fit for document extraction)
- **Thresh**: separate seeds from chaff (filtering noise from signal)
- **Winnow**: separate wanted from unwanted (project-scoping step)

'Glean' is the strongest candidate for the primary extraction command: `seeds glean <source>`. It implies methodical examination of existing material, not generation of new material. It also carries the connotation of 'picking up what others missed' — fitting for re-ingestion where later passes find seeds the first pass didn't.


---

## RESOLVED 2026-09-01. The pivot stays rejected; the vocabulary is what survived.

Two separate things sit in this seed and they ended differently.

**The source-agnostic pivot: rejected, and it stays rejected.** The user pushback recorded
above ("Too hard a pivot. Overlaps with intent.build's positioning.") stands unchanged.
Seeds is the structured database around the *deliberation process*, not a general
extract-from-anything tool. `glean` reads Claude Code transcripts. It does not grow
`--email`, `--slack` or `--stdin` sources on the strength of this seed.

Note the one adjacent thing that DID ship on the transcript side: the `transcript-seeds`
skill handles curated meeting-transcript extraction. That is a narrow, deliberate case with
a human curation step in front of it — not the open-ended source-agnostic architecture
proposed here.

**The terminology refinement: adopted, and it is now the command name.** The Mar-2026
observation that "harvest" and "gather" are overloaded — seeds being both the tool and the
thing extracted — was correct, and `glean` beat the alternatives for the reasons given
above: methodical examination of existing material rather than generation of new material,
plus the connotation of picking up what earlier passes missed, which is precisely
re-gleaning.

Ratified 2026-09-01 (Ryan): the command is `seeds glean`, replacing `sweep` throughout.
See seeds-74.2.1 for the design.

`thresh` and `winnow` are deliberately NOT adopted. They name stages of a process, not
operations a user invokes; promoting them to commands would be vocabulary for its own sake.
They remain available as internal language if the implementation ever needs to distinguish
the filtering step from the scoping one.
