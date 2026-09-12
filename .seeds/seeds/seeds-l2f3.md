---
id: seeds-l2f3
title: A rename that repoints an edge onto an existing but wrong seed is invisible to check
status: captured
type: concern
created_at: 2026-09-12T03:54:34.806761+00:00
updated_at: 2026-09-12T03:54:34.806761+00:00
tags:
  - check
  - relationships
  - rename
  - detector-gap
  - 2026-09-11
---

Found 2026-09-11 by home-manager-main, repairing what a `seeds-N` -> `hm-N`
prefix rename had left behind. The dangling half was caught by `seeds check`.
The other half was not, and it is the more valuable finding.

## What the rename did

```
before   seeds-6  <->  seeds-7      a resolved question on the handset exploration

after    seeds-6  questioned-by -> seeds-7   DANGLING, caught by check
         hm-7     questions     -> hm-6      RESOLVES, and is the wrong seed
         hm-6     questioned-by -> hm-7      symmetric, and equally wrong
```

`hm-7` is `seeds-7`'s correct twin; nothing was lost. But the rewrite also
moved the *other* end onto `hm-6`, which is an unrelated leaf decision titled
"jsaw.io is an internal-only TLD". The tell was an identical `created_at` on
both edges.

## Why check cannot see it

`relationship-target-missing` fires when the target has **no file**. Here the
target resolves — it is simply the wrong seed. And the pair is *symmetric*, so
a one-sided-edge check does not fire either: `hm-7` and `hm-6` point at each
other consistently. The store gets a clean bill of health while carrying a
relationship between two seeds that have nothing to do with one another.

**Anywhere a rename rewrites a reference onto an id that already exists as a
different seed, the corruption is silent.** That is the general shape, and it
is not specific to prefix renames — it is what any id-rewriting operation risks.

## Candidate signals, none yet chosen

- **Same `created_at`, different targets** (home-manager-main's suggestion).
  Cheap. But a legitimate inverse pair also shares `created_at` by construction,
  and so do two edges written by one operation, so this needs a sharper
  statement than "same timestamp" to avoid firing on healthy stores.
- **Compare against git.** `check --against-git` already reads history; an edge
  whose target changed in the same commit that renamed ids is recoverable from
  it. Expensive, and only works while the history is present.
- **Semantic implausibility.** A `questions` edge between seeds whose bodies
  share no vocabulary. Cheap to describe, impossible to gate on.

The `--against-git` route is the only one that can distinguish "this edge was
rewritten by a rename" from "somebody meant this", because it is the only one
with access to what the edge said before.

## The shape worth remembering

This is the third detector on this project measured to be blind to the case it
was assumed to cover -- after `non-canonical-bytes` (which cannot see a body
kept verbatim, because such a file renders to exactly its own bytes) and
`body-kept-verbatim` itself (which fired on merely stale files until narrowed).
Each was found by somebody running the check and reporting an empty result
rather than assuming they had misread it.

A check that answers a NARROWER question than its name suggests is worse than
no check, because the clean result is taken as evidence. Worth asking of each
existing rule: what is the nearest case it does NOT cover, and is that gap
written down next to it?
