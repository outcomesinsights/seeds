---
id: seeds-199
title: Adopt beads-style adaptive base36 hash IDs (sequential IDs collide across hosts)
status: resolved
type: decision
created_at: 2026-07-17T19:11:53.679373+00:00
updated_at: 2026-07-17T22:21:33.349214+00:00
resolved_at: 2026-07-17T22:21:33.349207+00:00
resolution: "Shipped whole-cloth as beads seeds-tek (idgen.py) + seeds-mlj (next_id -> adaptive base36 hash IDs with DB-check + nonce retry; config knobs; grandfathered seeds-1..198, no migration). Merged to main; full suite 429 green; live CLI mints hash IDs (fresh store -> seeds-8su, 3 chars; this repo 4). Efficacy: MINOR tweaking, mostly a planning-miss -- the next_id contract change (sequential->hash) rippled into ~12 pre-existing tests hardcoding seeds-1/seeds-2; a better seeds-mlj would have said \"adapt tests asserting sequential output, and note rename-prefix then covers legacy numeric IDs only.\" The rename_prefix/hash-ID interaction (see appended as-built note) was an inherent unknown, surfaced only by building. Global-CLI redeploy left to Ryan."
tags:
  - ids
  - architecture
  - migration
  - concurrency
relationships:
  - target_id: seeds-135
    rel_type: relates-to
    created_at: 2026-07-17T19:11:59.892332+00:00
  - target_id: seeds-140
    rel_type: relates-to
    created_at: 2026-07-17T19:12:00.022208+00:00
  - target_id: seeds-32ai
    rel_type: relates-to
    created_at: 2026-08-12T13:29:18.446956+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

## Problem

seeds' `next_id()` (db.py) is a stateless *derived* counter — it scans existing IDs and returns `max(seq)+1`. Because seeds is git-backed and the same repo can be worked from multiple hosts, each host's checkout runs that scan against its own local state and independently mints the same next number; the collision only surfaces when the git-tracked JSONL is merged (where the last-write-wins import can then silently drop one side). There is no shared counter to coordinate them.

(The incident that surfaced this was a collision in a *different* repo, since resolved by hand. This change is preventative — it removes the whole class of collision going forward.)

## How we got here — and what actually changed

seeds-135 (2026-03-20) chose Option 6, "sequential IDs with project prefix" (seeds-1, seeds-2), resolving: *"Single-user for now; concurrency concerns acknowledged but deferred."* Reasonable given the understanding at the time; the motivation was readability / conversation-friendliness ("seed 12" vs "seed-086a609d"), plus the belief that "the hex hash provides zero value for a deliberation tool — you never need collision resistance for your own thoughts." (Related: seeds-123 fixed prefix = project-name; seeds-140 made the prefix configurable and built the rename/migration machinery.)

What changed is **our understanding of the problem, not the user count.** seeds is still single-user. The flaw in the old framing was locating the coordination boundary at the *user*. The boundary is really the *repo checkout / host*: one git-backed repo living on multiple machines was never a single coordination point. A single user across multiple hosts is enough to collide — both a real situation and a far likelier one than genuine multi-user concurrency.

## Decision — adopt beads' ID scheme whole cloth (Option A: grandfather)

Switch **new** id minting to beads' adaptive base36 hash scheme; leave existing sequential IDs (`seeds-1`..`seeds-198`) untouched. This keeps the readability that motivated seeds-135 (a 3–4 char id like `seeds-k3n` is as typeable as `seeds-42`) while gaining coordination-freedom.

Rejected: Option B (full renumber of all existing seeds) — "aggressive and unnecessary at this time." Because no existing IDs change, the cross-database hazard (beads `Source: seeds-N` provenance refs, seeds-171) is moot.

### Settled design (confirmed 2026-07-17)

- **Format**: base36 (0-9a-z) suffix, `<prefix>-<hash>`.
- **Generation**: SHA-256 over seed content + a nanosecond timestamp + a nonce, encoded to base36. Insert path: generate candidate → check DB for that id → on collision bump the nonce and retry. (Fits seeds' stateless model better than the counter did — nothing to coordinate.)
- **Adaptive length**: birthday-paradox threshold (`P ≈ 1 − e^(−n²/2N)`), defaults max 25% / min 3 / max 8 chars, **counting all top-level seeds**. Consequence (by design, no special-casing): this repo (~198 existing seeds) starts new IDs at **4 chars**; fresh/small repos start at **3**.
- **Children**: keep `parent.N` (per-parent sequential). Small residual risk on concurrent same-parent children across hosts, accepted (matches beads).
- **Config**: store `max_collision_prob` / `min_hash_length` / `max_hash_length` in the existing seeds `config` table (added in seeds-140), defaults baked into code so it's zero-config by default and overridable.

## Conversion path

Under Option A there is **no data migration** — existing IDs stay put. The work is: port the generator (from beads `internal/idgen/hash.go` + `internal/storage/dolt/adaptive_length.go`), swap `next_id()`'s call site in `create`/`jot` to the new generator (top-level only; children keep `get_next_child_id`'s `.N`), add the config plumbing, and cover it with tests. The existing `migrate_to_sequential_ids` / `rename_prefix` machinery stays in place (still useful; simply not invoked here).

## What beads actually does (reference — confirmed by reading ~/projects/outins/beads)

- base36 (0-9a-z), denser than hex. (`internal/idgen/hash.go`)
- `GenerateHashID` = SHA-256 of `title|description|creator|timestamp_ns|nonce` → first N bytes → base36 at the target length; nonce breaks exact hash collisions.
- Adaptive length 3→8 by top-level count: 3 → ~160 items, 4 → ~980, 5 → ~5.9K, 6 → ~35K, 7 → ~212K, 8 → ~1M+. (`internal/storage/dolt/adaptive_length.go`)
- On insert: generate candidate → DB collision check → bump nonce → retry. Config read from DB config table, else defaults.
- (beads also has a sequential-counter mode via an `issue_counter` table, but its default — and the thing adopted here — is the hash scheme above.)



---

## As-built reconciliation (2026-07-17, via resolve-seeds-from-beads)

Shipped to spec as beads seeds-tek (`idgen.py`: base36 encode + adaptive length) and seeds-mlj (`next_id()` rewired — top-level count → adaptive length → generate → DB-check → nonce retry; config knobs in the config table; `create`/`jot` pass `seed_text`). No design calls changed mid-build. Full suite green (429); a fresh store mints 3-char ids, this repo 4-char, as predicted.

Emergent finding worth recording (refines the earlier "rename_prefix stays but isn't invoked here"): `rename_prefix()` **structurally can't rewrite hash IDs** — its pre-existing numeric-suffix guard (added to avoid renaming `seeds-experiment`-style IDs) also excludes base36 hash suffixes. So as a store fills with hash IDs, rename-prefix's reach narrows to the grandfathered `seeds-1..198` sequential IDs (it still rewrites in-body numeric references). Fine under "keep for legacy use"; flag only if renaming a prefix across hash IDs ever becomes desirable.
