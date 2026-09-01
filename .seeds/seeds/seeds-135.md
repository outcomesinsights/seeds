---
id: seeds-135
title: "ID format: should seeds use sequential IDs instead of hex hashes?"
status: resolved
type: decision
created_at: 2026-03-20T20:18:19.975197+00:00
updated_at: 2026-03-20T20:43:18.756589+00:00
resolved_at: 2026-03-20T20:43:18.756581+00:00
resolution: "Option 6: sequential IDs with project prefix (seeds-1, seeds-2). Single-user for now; concurrency concerns acknowledged but deferred. Existing hex IDs will be remapped in a one-time migration."
tags:
  - model
  - architecture
  - ids
  - ux
relationships:
  - target_id: seeds-123
    rel_type: relates-to
    created_at: 2026-03-20T20:18:46.150545+00:00
  - target_id: seeds-199
    rel_type: relates-to
    created_at: 2026-07-17T19:11:59.892332+00:00
  - target_id: seeds-32ai
    rel_type: relates-to
    created_at: 2026-08-12T13:29:18.557862+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Current state: seeds IDs use truncated SHA hex (mix of 4-char and 8-char, e.g., seed-3359, seed-086a609d). These are opaque, hard to remember, hard to type, and convey no information about order or age. Beads may have moved to sequential IDs already.

Question: what ID format best serves a deliberation tool?

## Options

### 1. Sequential integer (seed-1, seed-2, seed-47)
- **Pro**: dead simple, easy to type, easy to remember, natural ordering, instantly tells you relative age
- **Pro**: conversation-friendly — "let's look at seed 12" vs "let's look at seed-086a609d"
- **Con**: merge conflicts if multiple people create seeds concurrently (but seeds is currently single-user)
- **Con**: doesn't encode any timestamp information beyond ordering
- **Con**: IDs are short but unbounded (seed-9999 eventually)

### 2. Sequential with zero-padding (seed-001, seed-042)
- **Pro**: sorts lexicographically, looks tidy in lists
- **Con**: have to pick a width — 3 digits? 4? What happens at overflow?
- **Con**: same concurrency issues as plain sequential

### 3. Timestamp-based (seed-20260320a, seed-20260320b, or seed-2603201)
- **Pro**: encodes when the seed was created, which is meaningful for deliberation
- **Pro**: no coordination needed — timestamp is inherently unique (with suffix for same-day)
- **Con**: verbose, harder to type and remember than sequential
- **Con**: daily counter suffix adds complexity

### 4. ULID-style (sortable, timestamp-embedded, base32)
- **Pro**: globally unique, sortable by creation time, no coordination needed
- **Con**: just as opaque as hex hashes — doesn't solve the readability problem
- **Con**: over-engineered for a single-user tool

### 5. Keep hex hashes but standardize length
- **Pro**: no migration needed, already working
- **Con**: doesn't solve any of the readability/memorability problems

### 6. Short sequential with project prefix (seeds-1, seeds-2)
- **Pro**: combines the prefix convention (seed-3359) with simple sequential numbering
- **Pro**: if prefix is the project name per existing convention, seeds-42 is unambiguous across projects
- **Con**: still has concurrency limitations

## Considerations
- Seeds is currently single-user, so concurrency concerns are theoretical
- Child IDs use parent.N format (seed-81a4.1) — sequential parents make children even simpler (seed-12.1)
- Migration: existing seeds would need ID remapping or grandfathering
- The hex hash provides zero value for a deliberation tool — you never need collision resistance for your own thoughts
- Voice/conversation friendliness matters: "seed forty-two" vs "seed zero-eight-six-a"
- Related: seed-3359 decided prefix should be project name, not entity type
