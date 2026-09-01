---
id: seeds-h5rq.1
title: "Ruled: a cutting carries a conversation excerpt, not a pointer to a forked session"
status: captured
type: decision
parent: seeds-h5rq
created_at: 2026-09-01T16:29:26.119544+00:00
updated_at: 2026-09-01T16:29:26.119544+00:00
tags:
  - cutting
  - decision
  - context
  - portability
  - session-id
  - 2026-09-01
---

**Ruled 2026-09-01 (Ryan): seed-only, richly captured. Option B.**

The fork behind seeds-h5rq: when a mid-conversation topic is set aside, does the artifact
carry its *context* or only its *statement*?

## Option A — fork the session, seed is an index (REJECTED)

Use Claude Code's `/fork` to copy the conversation into a background session, then write a
seed that points at that session id. Full conversational context is preserved for free.

Rejected because the pointer rots:
- Session ids are host-local. A cutting taken on titan is meaningless on boost.
- Background sessions do not survive indefinitely; the seed outlives the thing it names.
- It makes seeds depend on a harness-specific, undocumented identifier.

Seeds' whole value is being git-backed and portable. An artifact that only resolves on one
machine, for a while, is the opposite of that.

## Option B — seed-only, richly captured (CHOSEN)

The agent writes a proper body: what was being discussed, why the topic matters, what the
open question is. Not a one-liner. Deliberately more expensive to write than `jot`.

Costs: you restart cold-ish; the capture is a summary, so fidelity depends on the agent
doing it well at the moment of capture.

Buys: portable, survives compaction, reboots, and host switches. Reviewable in git. No
dependency on harness internals.

## Design consequence

The interesting version is a cutting that captures the topic **plus a conversation
excerpt** into the body — most of a fork's context recovery, none of the rotting pointer.
That excerpt is what makes it a cutting rather than a verbose jot.

Open: where the excerpt comes from. The agent can write it from its own context, or it can
be pulled from the session JSONL the way seeds-74.2.2's sweep proposes. The latter shares
machinery with the sweep branch and is probably the better path — see seeds-74.2.2.
