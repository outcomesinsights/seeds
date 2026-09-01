---
id: seeds-190
title: "Concern (watch): two ways something could drift onto seeds' capture turf — deliberum's journey-persistence + academic post-hoc ADR extraction"
status: captured
type: concern
created_at: 2026-07-09T22:41:52.743599+00:00
updated_at: 2026-07-09T22:41:52.743604+00:00
tags:
  - competitive
  - watch
  - deliberum
  - post-hoc-extraction
  - convergence
relationships:
  - target_id: seeds-166
    rel_type: relates-to
    created_at: 2026-07-09T22:42:02.440363+00:00
  - target_id: seeds-168
    rel_type: relates-to
    created_at: 2026-07-09T22:42:02.607785+00:00
  - target_id: seeds-7
    rel_type: relates-to
    created_at: 2026-07-09T22:42:02.730193+00:00
  - target_id: seeds-189
    rel_type: relates-to
    created_at: 2026-07-09T22:42:02.862132+00:00
  - target_id: seeds-196
    rel_type: relates-to
    created_at: 2026-07-14T17:06:39.251571+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

From the deliberation-software revival sweep (docs/deliberation-software-revival-2026-06.md). Two vectors by which something could drift onto seeds' capture turf — worth watching, neither a competitor today:

1. deliberum (github.com/xuhuanstudio/deliberum; v1.0.0 dated 2026-06-15; 4 stars; "pre-production local-first") is the most philosophically-aligned entrant in the whole wave. It REJECTS the council pattern ("not a voting system, not a central-Judge workflow"; critiques majority voting for letting "weak consensus overpower strong objections"), treats humans and models as uniform participants, makes objections first-class (an "Objection Ledger"), and "compiles an outcome with unresolved boundaries instead of pretending that every disagreement disappeared." It ALREADY persists the journey (append-only event store, .deliberum/deliberum.sqlite, rotated JSONL audit) — the "watch if it adds persistence" signal already fired on day one. But it is a different UNIT (a live single-topic deliberation room/session runtime) and STACK (TypeScript + Hono daemon + React/Vite web UI) vs seeds' corpus-over-time, CLI-first, git-backed, agent-native shape. Watch whether it generalizes from single-session to corpus-over-time.

2. Academic post-hoc extraction: "Architecture Without Architects" (arXiv:2604.04990) proposes mining rationale from AI agent reasoning traces and persisting them as ADRs after the fact. That is exactly the reconstruction-from-residue seeds declined (seeds-166) and the ADR-as-output seeds rejected at founding. If shipped well it is an alternative answer to the same problem — but the field reaching for the approach seeds rejected validates the boundary by contrast.

Relates to seeds-166 (declined post-hoc extraction), seeds-168 (upstream/journey), seeds-7 (AI-as-participant).
