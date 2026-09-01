---
id: seeds-177
title: "seeds capability: capture code-review feedback and feed it back into the originating deliberation"
status: captured
type: idea
created_at: 2026-06-17T18:14:15.011910+00:00
updated_at: 2026-08-31T20:02:44.880230+00:00
tags:
  - feedback-loop
  - code-review
  - capability
  - provenance
  - revision
  - seeds-tool
relationships:
  - target_id: seeds-176.1
    rel_type: relates-to
    created_at: 2026-06-17T18:14:42.899390+00:00
  - target_id: seeds-176.2
    rel_type: relates-to
    created_at: 2026-06-17T18:21:04.672521+00:00
  - target_id: seeds-188
    rel_type: relates-to
    created_at: 2026-06-24T19:27:35.783739+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Flagged by @aguynamedryan while reconciling David Poll's code-review article (see sibling seed). The interest: when a code review of an implementation surfaces feedback that should change the plan, capture that feedback and feed it BACK into the originating deliberation — link review outcomes to the seed(s)/bead(s) that produced the work, so the recorded decisions and assumptions can be inspected and revised rather than lost. Turns the deliberation record into a live loop (build -> evaluate/review -> revise -> build) instead of a write-once upstream artifact. Open question: is this a seeds feature, or just an agent-on-request behavior?



---
## 2026-06-18 — @aguynamedryan's stream-of-consciousness additions

"THROWING AWAY INSIGHT, NOT JUST CODE" (verbatim-ish): "I'm not trying to be precious about code, because code has become very cheap. I don't see any reason why you wouldn't build and discard — other than if you haven't captured what you learned from building and discarding, you're throwing away more than code. You're throwing away insight." -> This is the affirmative case for the feedback loop: build-and-discard is fine, good even, IF the learning is captured. The thing worth keeping from a discarded build is the insight, not the code.

WHY RYAN DOESN'T ACTUALLY FEED BACK MUCH (a nuance that partly closes the "gap" on the seeds side): inherent in seeds is that once something is implemented and accepted, the thinking that went into it is ALREADY captured — seeds is the SOURCE of the beads that led to the implementation. seeds "understands what we specified, the conclusions and the decisions we reached." It lives beside the code and can figure out what was implemented. When a feature is left alone, seeds can mark it resolved but STILL knows about it when considering future development. So @aguynamedryan doesn't need to go back and tell seeds "by the way, we implemented this" — the upstream is already there.

THE REAL OPEN GAP (@aguynamedryan, sweeping-generalization-admitted): the field's build-and-decide-later tooling does not account for WHERE the later decisions get recorded. "Creating the code and then making the decision — well, where are we recording the decision? Where are we recording the feedback?" For seeds the upstream is captured; the open question is the DOWNSTREAM later-decisions in code-centric systems (maybe DeltaDB is an answer — see seeds-176.2). The live loop (build -> evaluate -> revise) is the cool part; the piece missing across the field is durable capture of the LATER decisions, not the initial ones.
