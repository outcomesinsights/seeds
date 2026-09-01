---
id: seeds-155
title: Add a 'seeds import' command to load exported JSONL back into the DB
status: resolved
type: idea
created_at: 2026-06-04T17:24:17.830827+00:00
updated_at: 2026-08-31T21:34:29.417225+00:00
resolved_at: 2026-08-31T21:34:29.417219+00:00
resolution: "Shipped: 'seeds import' rehydrates from JSONL with LWW upsert, and 'sync' became a true round-trip (import then export). Efficacy: minor tweaking, and it was an inherent unknown — the divergence guard (db_extends_disk) that stops a stale DB overwriting newer on-disk deliberation was only discoverable by running the round trip in anger. See the appended note."
converted_at: 2026-09-01T05:20:22.746832+00:00
---

We export to JSONL via 'seeds sync', but there is no CLI command to import that JSONL back into a seeds DB (e.g. rehydrate on a fresh clone / restore / move data between machines).

Key finding: the import LOGIC already exists but is unwired. src/seeds/export.py defines import_from_jsonl(db, input_path) plus _import_v1_record and _import_v2_record (handles both schema versions). Nothing calls it — no CLI command, and sync only ever calls export_to_jsonl. So this is mostly a wiring + UX/semantics task, not a from-scratch build.

Open design questions: should 'sync' do import-then-export for a true round-trip (like beads), or keep a separate explicit 'seeds import'? Merge vs replace semantics? Conflict handling on ID collisions?

---
RESOLVED DESIGN (2026-06-15): upsert with last-write-wins.

Semantics: UPSERT keyed on id, last-write-wins (LWW) by updated_at.
- New id -> insert.
- Existing id -> overwrite from JSONL only if the JSONL record's updated_at is newer than the DB's; otherwise skip.
- Records in DB but absent from JSONL are never touched (no deletion by absence).

Why LWW and not beads' blind 'JSONL wins': beads import is upsert (the incremental counterpart to export, INSERT ... ON DUPLICATE KEY UPDATE), but its blind overwrite is safe only because git hooks keep the JSONL fresher than the DB at import time. seeds has no such hooks (sync is manual), so a round-trip flush at end of session would clobber the session's own DB edits under blind upsert. LWW on updated_at closes that gap; update_seed reliably bumps updated_at, so the signal is trustworthy. LWW is also the simplest non-merge conflict policy, matching the decision that import is rehydration, not branch reconciliation.

Rejected: 'replace' (destructive - a truncated/corrupt JSONL could wipe the DB; and since seeds never deletes by absence, replace buys nothing). Also rejected: the current skip-on-collision behavior (silently ignores edits to existing JSONL lines - a latent round-trip bug).

Commands:
- New 'seeds import [PATH]': explicit upsert/LWW. Defaults to .seeds/seeds.jsonl; accepts a path or '-' for stdin. Prints a summary: N created, M updated, K skipped (stale).
- 'seeds sync' becomes round-trip: import (LWW) then export.
- 'seeds sync --flush-only' unchanged (export-only escape hatch).

Deletion: out of scope for the import/JSONL path. No hard-delete CLI command; db.delete_seed() exists at the DB layer (cascades relationships) and stays un-promoted. The only deletion cases - a seed added entirely by accident, or one containing PII/private info unfit for a public repo - are handled manually against the SQLite DB.

Relationships: re-asserted idempotently on import (an edge may reference a target appearing later in the file - already fine, no FK enforcement; just ensure re-import does not duplicate edges).

Implementation notes: import_from_jsonl already exists (handles v1+v2) but is unwired and currently skip-on-collision; switch it to LWW upsert and wire into the CLI. update_seed force-bumps updated_at, so import needs a write path that preserves the JSONL timestamps verbatim. next_id() is derived (max scan), so bulk import will not corrupt the ID sequence.

SHIPPED (beads seeds-94o, seeds-a8w, seeds-cv5, seeds-cyy, seeds-d19, seeds-xrx) — `seeds import` exists and rehydrates from JSONL with last-write-wins upsert. Both open design questions were answered by choosing BOTH: `sync` became a true round-trip (import LWW, then export) AND `import` ships as a separate explicit verb for the fresh-clone path. Merge semantics are LWW per record. What the seed could not have anticipated: the export half later needed a divergence guard (db_extends_disk) to stop a stale DB overwriting newer on-disk deliberation.
