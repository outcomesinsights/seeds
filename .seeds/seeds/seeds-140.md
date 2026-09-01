---
id: seeds-140
title: Configurable project prefix for seed IDs
status: resolved
type: decision
created_at: 2026-05-14T18:24:18.371108+00:00
updated_at: 2026-05-14T18:37:22.548471+00:00
resolved_at: 2026-05-14T18:37:22.548462+00:00
resolution: Implemented as bead seeds-5at; commit 0f762d6. Config table in SQLite stores prefix; init --prefix overrides default (sanitized cwd name); rename-prefix command renames all IDs + relationships in place; auto-derive on first command after upgrade for legacy DBs.
tags:
  - cli
  - db
  - migration
relationships:
  - target_id: seeds-199
    rel_type: relates-to
    created_at: 2026-07-17T19:12:00.022208+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Long-standing bug: every seeds database hardcodes 'seeds' as the ID prefix (e.g., seeds-1, seeds-7.1). Across multiple projects, every database's IDs look identical, defeating the readability benefit of sequential IDs.

# Design

## Storage
Add a `config` table to the SQLite schema (key TEXT PRIMARY KEY, value TEXT) for project-level metadata. First entry: `prefix`.

## Default derivation
On `seeds init` with no `--prefix` flag, derive the prefix from the project directory name:
- Take `seeds_dir.parent.name` (typically `Path.cwd().name`)
- Sanitize: lowercase, replace runs of non-[a-z0-9] with single hyphen, strip leading/trailing hyphens
- Must start with a letter; if it doesn't (e.g., starts with a digit), prepend 'p-' or fall back to DEFAULT_PREFIX
- Empty sanitized result → fall back to DEFAULT_PREFIX ('seeds')

Examples:
- `My Project` → `my-project`
- `foo_bar.v2` → `foo-bar-v2`
- `seeds` → `seeds`

## Init flag
`seeds init --prefix=<name>` overrides the default. The supplied value is still sanitized (or rejected if it can't be coerced).

## Auto-derive on first run (after upgrade)
For existing DBs lacking a config entry, on first command after upgrade:
1. Derive prefix from project dir name
2. Set config
3. Rewrite all IDs (top-level seeds + children + relationships) replacing the old 'seeds' prefix with the new prefix
4. Print one-line summary (`seeds: configured prefix 'newprefix' (renamed N seeds)`)
5. Skip if derived prefix equals 'seeds' (no rewrite needed, just set config)

## Rename command
`seeds rename-prefix <new>`:
- Validates and sanitizes the new prefix
- Reads current prefix from config (fallback: 'seeds')
- If unchanged, no-op
- Uses two-phase temp-suffix rewrite (like `migrate_to_sequential_ids`) to avoid PK collisions on the seeds table
- Updates seeds.id, relationships.source_id, relationships.target_id
- Rebuilds FTS index
- Updates config
- Backs up DB to .db.bak before writing
- Re-exports JSONL after

## Plumbing changes
- `Database.get_prefix() -> str` reads from config, falls back to DEFAULT_PREFIX
- `Database.set_prefix(value)` sets the config entry
- `Database.next_id()` calls `get_prefix()` (no prefix arg required for callers)
- `migrate_to_sequential_ids()` continues to accept a prefix override (one-time hex→sequential migration)
- Sanitization helper `sanitize_prefix(raw: str) -> str` in models.py

## Bead
Tracked as bead seeds-5at.
