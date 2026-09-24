---
id: seeds-1a0j
title: 'Changing the seed-ID separator is parked: the cost is fleet coordination, not code'
status: captured
type: decision
created_at: 2026-09-24T03:21:28.915513+00:00
updated_at: 2026-09-24T03:21:28.915513+00:00
tags:
  - ids
  - separator
  - parked
  - adversarial-review
---

**Ruled 2026-09-23 (@aguynamedryan):** "the idea of changing the identifier separator has become a nightmare." The tilde separator (bead seeds-4co.22) is parked, not abandoned, on branch `seeds-4co.22/tilde-separator-parked` (83d05a9). It was never pushed, and no repo but this one was ever migrated.

## Why it became a nightmare

The code worked. Two adversarial reviews found the migration verb itself sound in a single quiet checkout. What did not work was everything a separator change touches outside one checkout:

- **Every host at once.** The installed binary cannot read a store that holds a tilde file, so the new build has to reach every host before any repo migrates. Pushing the branch also publishes an already-migrated store.
- **Bead text on every host.** The bead pass rewrites seed citations inside beads. A same-field edit on another host before it pulls wedges that host's Dolt sync. The review demonstrated this with two copies of a bead database.
- **Every branch, worktree and checkout.** A pre-migration branch merged afterwards, or an unmigrated worktree sharing the bead database, brings the old spelling back silently.
- **Every citation outside the store.** Docs, other repos and bead comments. csc alone has 1,512 hyphen citations in 340 tracked files, and 600+ citations cross stores.
- **Shared prefixes.** The same prefix in several repos (seeds/oimnibus, hm, seed, q) makes "is this ours?" undecidable by lookup.

After round 2, 12 more fixes were open (seeds-4co.22.10–.21), plus a procedure (freeze bead edits, pull everywhere, canary on two hosts).

## If it is revisited

The problem it solved is still real: a seed ID and a bead ID share a prefix and cannot be told apart by shape. Any fix that changes the spelling of existing IDs inherits the whole list above. Two options avoid that:

- a **new mint only** (old IDs keep their spelling forever);
- a **different prefix** for seeds rather than a different separator.

Rounds 1 and 2 of the adversarial review are in `claude_stuff/` of this repo, local only.
