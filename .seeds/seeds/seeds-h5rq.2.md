---
id: seeds-h5rq.2
title: Claude Code has four conversation-splitting primitives; none of them close the loop
status: captured
type: exploration
parent: seeds-h5rq
created_at: 2026-09-01T16:29:42.501797+00:00
updated_at: 2026-09-01T16:29:42.501797+00:00
tags:
  - claude-code
  - harness
  - reference
  - fork
  - branch
  - subtask
  - inbox
  - 2026-09-01
---

Context gathered 2026-09-01 by string-dumping the Claude Code binary (v2.1.252, titan).
These are the verbatim registered command descriptions, not recollection.

| Command | Registered description | Shape |
|---|---|---|
| `/branch [name]` | "Create a branch of the current conversation at this point" | **You move into the branch**; the original stays behind |
| `/fork [prompt]` | "Copy this conversation into a new background session and keep working here" | The topic leaves, you stay |
| `/subtask <directive>` | "Send a subagent off with your full context; its result comes back here" | Answer returns inline |
| `/btw` | "Ask a quick side question without interrupting the main conversation" | Smallest case |

Supporting: `claude agents` / `/tasks` (list background sessions), `claude attach <id>`,
`claude --resume --fork-session`, and `/rewind` (which also forks at the restore point).

Both `/fork` variants sit behind an unresolved `isEnabled` gate; availability per account
was not confirmed.

## Why `/branch` felt clunky

It is a *divergence* tool, not a *deferral* tool — built for "retry this same topic a
different way," so it drags you onto the new thread. That is inverted from what a parked
topic needs: the interruption should leave and you should stay. Reaching for `/branch` to
defer a topic pushes you onto the very branch you meant to set aside.

## Why none of them solve the problem

`/fork` preserves context but not **attention**. A forked background session is visible
only if you run `claude agents` or `/tasks`. It is host-local, does not survive
indefinitely, and nothing ever surfaces it unprompted.

That is a queue with no inbox — which is the original failure (topics falling by the
wayside) relocated rather than fixed.

Seeds is the inbox: `seeds ready` is the pick-up-next list, and it is git-backed, so it
crosses hosts and survives compaction. This is the argument for seeds-h5rq existing at all
rather than telling people to use `/fork`.

## Adjacent idea, not yet its own seed

A `Stop` hook that prints `seeds ready` at session end would mechanically close the
"falls by the wayside" loop — the harness-level complement to the sweep proposed in
seeds-74.2.2.
