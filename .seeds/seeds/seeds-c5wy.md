---
id: seeds-c5wy
title: 'Focus set / board: a sprint-like set of seeds to work next, dropped in and out, shown Kanban-style'
status: resolved
type: idea
created_at: 2026-10-07T17:54:45.300356+00:00
updated_at: 2026-10-07T18:50:21.498023+00:00
resolved_at: 2026-10-07T18:50:13.423301+00:00
resolution: 'Tags only: the focus tag is the working set; convention shipped in seeds prime. --sort status deferred to seeds-1cho.'
tags:
  - focus-set
  - board
  - kanban
  - workflow
  - ux
relationships:
  - target_id: seeds-kfoa
    rel_type: questioned-by
    created_at: 2026-10-07T17:54:51.099027+00:00
  - target_id: seeds-1cho
    rel_type: relates-to
    created_at: 2026-10-07T18:50:21.398174+00:00
---

## What Ryan said

Dictated 2026-10-07 (relayed by a session in another repo; the transcription errors are left in):

```
I wonder if seeds need some sort of notion of like a sprint or something like that. So we can put together a set of seeds that we want to focus on next. And we can drop seeds out, put seeds in, things like that. I think that would be helpful to have a localized situation like that. I hear people talk about Kanban boards all the time and things like that. Is there perhaps an existing agile system that seeds could supplement or hook into or vice versa? We could hook into seeds to present this kind of approach.
```

## What already exists (verified 2026-10-07 on 0.7.0a9)

- The statuses (captured / exploring / deferred / resolved / abandoned) already work as Kanban columns.
- `seeds update --add-tag X` / `--remove-tag X` moves a seed into or out of a set without touching its other tags. That is the "drop in, drop out" behaviour.
- `seeds list --tag X` (optionally with `--status`) filters to one set.
- Missing: a single view of a set grouped by status, e.g. `seeds board --tag focus`.
- Prior art in the corpus: none. A search for sprint, kanban, board, focus set, milestone and iteration finds only incidental hits.

## Two directions (NOT RULED)

(a) **Native, tag-scoped focus set plus a board view.** It needs no new storage: a focus set is just a tag, and the board is a grouped read. The open questions are a reserved tag name versus any tag, and whether several focus sets can coexist.

(b) **Hook into an external agile tool** (GitHub Projects, Linear cycles, Jira sprints), in either direction. The cost: those tools work on their own issue objects, so seeds would have to mirror a second copy and keep it in sync. They also assume tasks, not open deliberation.

The relaying session leaned towards (a). Ryan has not ruled.

RULED 2026-10-07 (Ryan, relayed from another session): "c5wy - let's do this -- ask ponytail if we should just use tags for this somehow?" Approved to go ahead. Direction (a), native, per the seeds-kfoa answer. The shape stays open until Ryan rules on the review below.

## Ponytail review of the idea (2026-10-07, against 0.7.0a9). PROPOSED, NOT RULED

Verdict: tags alone cover it. No new concept, no new command, no new storage.

- **Put in / drop out** already works: `seeds update <id> --add-tag focus` / `--remove-tag focus`. Each call takes one ID, so a batch is a shell loop. That is fine and not worth a multi-ID change.
- **See the set** already works: `seeds list --tag focus` prints only the set, and every line already carries its status icon. `--all` adds the done column (resolved/abandoned). Named or parallel sets are just more tags (`focus-0.8`), so there is nothing to model.
- **The one gap:** `list` sorts only by created or updated, so the columns are interleaved. The smallest fix is `--sort status` on `list`, which orders lines by the `SeedStatus` enum. It is about 3 lines in `store.list_seeds` plus the Click choice, and it works for every filter, not just focus sets. If headers per column are wanted, a `--group-by status` printing `## exploring (n)` blocks is about 10 lines. Pick one, not both.
- **Ship the convention in the package, not in a CLAUDE.md** (seeds-gi9k): one recipe line in `prime --full`: "focus set = a tag; `seeds list --tag focus --sort status`".

Cut from the proposal: a `seeds board` command (it would be a second `list`); a reserved or special `focus` tag; sprint objects with dates or cadence; WIP limits; any new field in the seed file format.

RULED 2026-10-07 (Ryan, relayed from another session): "let's not worry about sort right now and just use tags." Tags only. The convention, a `focus` tag added and removed with `--add-tag`/`--remove-tag` and viewed with `seeds list --tag focus`, is now one line in both short and full `seeds prime`. `--sort status` is DEFERRED, not rejected, and split out to seeds-1cho.
