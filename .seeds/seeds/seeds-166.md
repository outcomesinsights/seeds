---
id: seeds-166
title: "Idea (declined): proactive corpus extraction — reconstruct deliberation from non-deliberation artifacts"
status: resolved
type: idea
created_at: 2026-06-15T22:00:39.891839+00:00
updated_at: 2026-08-31T20:02:42.337339+00:00
resolved_at: 2026-06-15T22:01:58.791305+00:00
resolution: "Declined as a boundary. Reconstruction-from-residue is low-value for this workflow: seeds sources live, cheap capture (AI + Zoom transcription), not inference from code/git/old artifacts. Ryan deliberately does not back-infer pre-seeds decisions on his decades-old system — that information is assumed lost to time."
tags:
  - gleaning
  - extraction
  - corpus
  - knowledge-artifact
  - declined
  - boundary
relationships:
  - target_id: seeds-60
    rel_type: relates-to
    created_at: 2026-06-15T22:01:58.373247+00:00
  - target_id: seeds-190
    rel_type: relates-to
    created_at: 2026-07-09T22:42:02.440363+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Meta's pre-compute engine sweeps a whole existing codebase/corpus with a fleet of agents answering standardized questions ("what non-obvious patterns cause failures? what tribal knowledge is buried in comments?") to reconstruct intent *nobody ever captured as deliberation*, packaged as compact "compass, not encyclopedia" context files. For seeds this would be a new mode: extend gleaning from "ingest a source that already contains deliberation" (seeds-126) to "reconstruct deliberation from raw code/configs," and attack the completeness gap (seeds-60) from the other side, giving the knowledge-artifact concept (seeds-89 / seeds-90 / seeds-91) a generation path.

@aguynamedryan's decision (2026-06-15): **declined**, recorded as a boundary. "I don't think reconstructing from residue is going to be very helpful." He has deliberately *not* asked seeds to back-infer the decisions on his decades-old system — he assumes that information is lost to time; even the artifacts that survive (GitHub issues, documents, the odd email) do not capture with anything like the rigor of a transcribed meeting. seeds is a tool for "a brave new world in which discussion capture is cheap and easy" — it sources *live* capture, not residue. Inferring intent from code or git commits has not been necessary and is not the bet.

Recorded so the boundary is explicit: setting the edges of the tool matters as much as setting its direction.



---
Update (2026-06): the deliberation-software revival sweep (docs/deliberation-software-revival-2026-06.md) found the dev-tooling research literature independently proposing exactly this post-hoc approach — "Architecture Without Architects" (arXiv:2604.04990) proposes mining rationale from AI agent reasoning traces and persisting them as ADRs after the fact. The field converging on the approach seeds declined validates this boundary by contrast: seeds bets on live capture, not reconstruction-from-residue. See the competitive-watch seed for detail.
