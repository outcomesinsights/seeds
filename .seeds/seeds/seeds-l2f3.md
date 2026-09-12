---
id: seeds-l2f3
title: A rename that repoints an edge onto an existing but wrong seed is invisible to check
status: captured
type: concern
created_at: 2026-09-12T03:54:34.806761+00:00
updated_at: 2026-09-12T03:59:19.102511+00:00
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

## SIGNAL CHOSEN (2026-09-11), and it is none of the three above

home-manager-main replaced its own same-`created_at` proposal after I objected
to it, and the replacement has what the others lacked: no false-positive story
at all, because **it never examines a relationship**.

**Look at the rename, not the edge.** A reference rewritten from `A-N` to
`B-N` by an id pass is suspect if and only if `A-N` and `B-N` were DIFFERENT
seeds immediately before that pass.

- benign collision: the two were the same seed (a duplicate), so the rewrite
  preserved meaning — 50 of 51 here;
- corrupting collision: the two were different seeds, so the rewrite silently
  repointed the reference at an unrelated record — 1 of 51, and it is the
  `hm-7 -> hm-6` case found by hand.

A legitimate inverse pair cannot trip it, because it asks nothing about edges.
A store that never had a colliding prefix pass yields an empty candidate set —
a genuine zero rather than a check with nothing to say.

**Measured on home-manager, and reproduced independently here:**

```
files at c27ba89^                       240
suffixes carrying BOTH seeds-N and hm-N  51
  identical titles (benign)              50
  DIFFERENT titles (corrupting)           1
    seeds-6  Make FluidVoice reliably capture from the AB13X handset mic…
    hm-6     jsaw.io is an internal-only TLD (nothing public on it)
```

Titles were sufficient and unambiguous on this corpus; a content hash is
stricter if it is ever wanted.

**The caveat, which is theirs and matters more than the signal.** This needs
the pre-pass commit to be identifiable. Here it is `c27ba89`, known from the
thread. Where nobody recorded which commit did the rename, the rule holds but
its INPUT does not exist, and `--against-git` would have to find the pass by
scanning for commits that delete many files sharing one prefix. So the
acceptance criterion "zero findings across 21 stores" must not be read as "the
check ran everywhere" — on most stores it will correctly have nothing to look
at, and those two outcomes have to be distinguishable in the output or this
detector acquires the exact disease it exists to cure.

## And a sharper statement of the pattern

Mine was "somebody reported an empty result rather than assuming they had
misread it". Theirs is better: all three detectors answered a **narrower
question than their name**, and in each case the narrowing was invisible from a
clean run. What caught them was someone with a *specific suspected instance*
checking whether the detector saw THAT instance — not reading the aggregate.

**A check that cannot be pointed at a known-bad case is a check nobody can
falsify.**
