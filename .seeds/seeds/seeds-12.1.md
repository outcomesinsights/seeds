---
id: seeds-12.1
title: Is beads absorbing seeds' domain?
status: captured
type: question
parent: seeds-12
created_at: 2026-02-24T17:05:11.482022+00:00
updated_at: 2026-02-26T16:37:18.175727+00:00
tags:
  - existential
  - beads
  - architecture
relationships:
  - target_id: seeds-86
    rel_type: relates-to
    created_at: 2026-02-24T17:05:11.482022+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Beads v0.50-v0.56 added wisps (ephemeral thoughts), molecules (structured templates), rich typed relationships (supersedes, duplicates, replies_to), threaded messaging, queryable metadata, and graph visualization. Every one of these was on seeds' roadmap or wish list.

**What beads now covers that seeds envisioned:**
- Quick capture → wisps
- Deliberation templates → molecules/protos
- Decision supersession → `supersedes` relationship
- Reasoning chains → `replies_to` threading
- Flexible metadata → queryable metadata fields
- Convergence mechanisms → auto-close on supersede/duplicate

**What seeds might still uniquely provide:**
- Domain-agnostic deliberation (beads is software-focused)
- "Capture the journey" philosophy (beads captures tasks, not thinking)
- Question-as-first-class-object (beads has no equivalent)
- Read-only web UI for reviewing deliberation (beads has no web UI)
- The `prime` command's deliberation-specific AI context

**The core question:** Is seeds a *tool* or a *philosophy*? If it's a philosophy (capture the journey, not just conclusions), could that philosophy be applied as a *pattern within beads* rather than a separate tool? Or does the separation of concerns matter — keeping "thinking about what to do" distinct from "tracking what to do"?


---
**Research conclusion (Feb 2026): The gap is real.**

Beads has no good mechanism for "ideas not ready for implementation":
- `bd defer` is time-based, not state-based — asks "when?" not "is this even work yet?"
- `bd ready` has no persistent exclusion filters — can't configure it to always hide ideas
- Wisps are ephemeral/GC-able — opposite of what ideas need
- P4 "Backlog" priority shows in `bd ready` alongside everything else
- Custom types help labeling but don't change lifecycle or filtering
- Multiple GitHub discussions (#266, #283, #221) show other users hitting this gap

Beads assumes everything is work to be done. Seeds assumes everything is a thought that might become work someday. These are genuinely different lifecycle models:
- Beads: open → in_progress → closed (execution lifecycle)
- Seeds: captured → exploring → resolved/abandoned/deferred (deliberation lifecycle)

**Seeds fills a real gap.** The existential threat from beads' feature expansion is less about capabilities and more about domain — beads is getting richer tooling for its domain (execution), not expanding into seeds' domain (deliberation).
