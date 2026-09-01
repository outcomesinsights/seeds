---
id: seeds-176.2
title: DeltaDB (Zed) — Poll's 'code is the centerpiece' productized; downstream of where seeds sits
status: captured
type: exploration
parent: seeds-176
created_at: 2026-06-17T18:20:31.660501+00:00
updated_at: 2026-08-31T20:02:44.047647+00:00
tags:
  - blog
  - landscape
  - deltadb
  - zed
  - poll
  - downstream
  - lifecycle
  - distillation
  - version-control
relationships:
  - target_id: seeds-176.1
    rel_type: relates-to
    created_at: 2026-06-17T18:21:04.561641+00:00
  - target_id: seeds-177
    rel_type: relates-to
    created_at: 2026-06-17T18:21:04.672521+00:00
  - target_id: seeds-168
    rel_type: relates-to
    created_at: 2026-06-17T18:21:04.787250+00:00
  - target_id: seeds-176.5
    rel_type: relates-to
    created_at: 2026-06-18T22:32:21.579555+00:00
  - target_id: seeds-178
    rel_type: questioned-by
    created_at: 2026-06-18T22:32:22.692283+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Source: Zed / Nathan Sobo, 'Introducing DeltaDB' (zed.dev, 2026-06; PRE-LAUNCH — waitlist, beta in weeks, so a design bet not shipping behavior). What it is: a new version control system meant to REPLACE Git's commit model for agent-driven dev — records fine-grained DELTAS (every operation between commits; CRDT worktrees) and pairs each agent MESSAGE with the EDIT it produced. Taglines: 'software is made between commits'; 'software now takes shape in the conversation, not the commit.' Bidirectional: from any line jump to the conversation that produced it, and back. Kills the PR ('put them in the same place, and the ceremony disappears'). Does NOT distill/summarize — keeps everything, navigable via references anchored to deltas. RYAN'S READ (confirmed accurate): yes, it ties the agent conversation to the code the agent writes, fine-grained, mid-build. Two nuances to add: (a) it is a Git REPLACEMENT / new VCS, not merely a capture or monitoring tool; (b) KEY DISTINCTION — DeltaDB is DOWNSTREAM (the implementation conversation, at/around the code), seeds is UPSTREAM (pre-implementation deliberation, distilled into beads' ## Why). Different lifecycle stages, so complementary not competing; DeltaDB still presupposes the upstream what/how-to-build, same as Poll. POLL CONNECTION (@aguynamedryan's instinct, correct): DeltaDB is Poll's 'code is the centerpiece' thesis productized — same kill-the-PR move, same Zed-adjacent worldview. WORKFLOW FIT: @aguynamedryan front-loads deliberation into seeds and implements in big chunks ('one fell swoop'), so the inline build-conversation DeltaDB optimizes is exactly the part he deliberately keeps THIN. Hence little personal use — a defensible lifecycle choice, not a misunderstanding. The current mainstream agentic pattern (spec-then-let-it-run, Claude Code CLI) is closer to @aguynamedryan's workflow than DeltaDB's converse-and-edit bet. DISTILLATION: DeltaDB = maximal capture + navigation (no distillation); seeds = distillation (the ## Why). Clean contrast for the landscape.



---
## 2026-06-18 — @aguynamedryan's questions + DeltaDB investigation

FIDELITY CORRECTION (supersedes the "Git REPLACEMENT / kills the PR" language above): per the Zed post, DeltaDB's stated aim is "NOT to replace Git or CI." Git and CI "stay for what they're good at: running checks and connecting you to the rest of the world." DeltaDB replaces the commit-centric model / PR ceremony for the INNER agent loop (the between-commits work Git never modeled), not Git wholesale. Keep this scoping in the post; "Git replacement" overstates Zed's claim and was our interpretation.

WHAT IT ACTUALLY CAPTURES (confirmed via the post): message+edit pairs, recorded RAW as fine-grained deltas ("a message and the edit it produced are recorded side by side"). No pre-implementation planning as a distinct artifact — the focus is the conversation that "generates the code," recorded alongside the changes. No distillation/summarization. Intent is only IMPLICIT (an agent can ask a prior agent "why is this written this way" and reconstruct from the recorded conversation) — not a first-class decision/rationale record, and no representation of paths considered-and-rejected before any code existed. Ongoing feedback exists via "annotate as you go" + bidirectional nav (from any line, find every conversation that has touched it since).

RYAN'S THREE QUESTIONS, answered:
Q1 — Does DeltaDB do what seeds does? NO, not as-is. It captures the conversation AROUND code edits — downstream and raw. seeds captures the PRE-CODE deliberation (what/why, what's the real problem, what we considered and rejected), which happens before there is any edit to attach something to.
Q2 — Could you bolt a distillation layer on and have that suffice? A distillation layer over DeltaDB's message+edit stream would give you something like intent.build's Capture (decisions-from-the-build) — but still DOWNSTREAM. You cannot distill what was never captured: the pre-code journey leaves NO edits to anchor to, so no amount of summarizing the edit stream recovers it.
Q3 — Could build-and-correct via AI capture the journey without planning? ("just talk to an AI, have it build, say 'no, I need this other thing,' and the journey is captured as you go") PARTLY yes — in a converse-and-edit workflow, real deliberation IS expressed as you react to what was built (cf. Ball, "building is learning"). For react-first thinkers, DeltaDB genuinely captures THAT journey. BUT (a) it's a DIFFERENT journey than @aguynamedryan's plan-first one; @aguynamedryan front-loads (often ~1-2 hrs thinking, then ~1-2 hrs of AI implementing), so his "no, not like that" reactions are thin — DeltaDB would catch the thin part and miss the thick part; (b) it stays raw/downstream; the rejected-before-you-build branches still have no delta to attach to. HONEST CONCESSION: as implementation time falls (@aguynamedryan expects it to keep falling), the journey's center of gravity may migrate INTO the edit stream, strengthening DeltaDB/intent.build-style tools — but implementation isn't free YET, and @aguynamedryan's plan-first style isn't served by it.

RYAN'S STRONG POINT — "where are the LATER decisions recorded?": even if code is the centerpiece and it's a build-and-decide-later system, where do the later decisions/feedback get recorded durably? DeltaDB's partial answer = annotate-as-you-go + bidirectional nav (a record anchored to code, but raw and not linked to any upstream rationale). seeds' answer = feed feedback back into the originating deliberation (seeds-177). Same gap, two philosophies: raw-at-the-code (DeltaDB) vs distilled-and-linked-to-the-journey (seeds).

CODE-AS-SPEC LENS (see seeds-176.6): DeltaDB sits AT the concrete contract (the conversation writing/editing the code); seeds sits a level up (what should the contract contain, and why). Cleanest one-line relationship.
