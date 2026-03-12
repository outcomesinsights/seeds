# Plan: Typed Relationships + Questions-as-Seeds

## Context

Two design decisions converging: (1) relationships need types (`relates-to`, `questions`, `answers`, etc.) instead of the current untyped `related_to` JSON array, and (2) questions should just be seeds, with relationships carrying the semantics ("this seed *questions* that seed"). This resolves seed-567d and seed-80ba simultaneously.

The current model has a `questions` table (separate entity) and a `related_to` JSON array on each seed (untyped, bidirectional). The new model has a single `relationships` table with typed, directed edges, and questions become seeds of type=question linked via a `questions` relationship.

## Schema Changes

### New table: `relationships`
```sql
CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    rel_type TEXT NOT NULL DEFAULT 'relates-to',
    created_at TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES seeds(id),
    FOREIGN KEY (target_id) REFERENCES seeds(id),
    UNIQUE(source_id, target_id, rel_type)
);
```

### Removed: `questions` table and `related_to` column on seeds

### FTS5 simplified
Remove `question_texts` column — questions are now seeds with their own FTS entries.

## Key Design Decisions

- **Directed edges**: `relates-to` stored as two rows (A→B, B→A) for bidirectional. `questions` is one directed edge (question-seed → parent-seed).
- **Question → seed mapping**: `q.text` → `seed.title`, `q.answer` → `seed.content`, status: OPEN→CAPTURED, ANSWERED→RESOLVED, DEFERRED→DEFERRED. Migrated questions get new project-prefixed IDs (e.g., `seeds-a1b2c3d4`), same as all other seeds. The `q-` prefix is retired.
- **ID prefix convention**: All seeds use the project name as their ID prefix. In this project, that's `seeds-`. Other projects using the seeds tool would use their own prefix (e.g., `myproject-`). This applies uniformly — questions-turned-seeds are no exception.
- **CLI stays familiar**: `seeds ask` and `seeds answer` remain as convenience commands, but create seeds + relationships under the hood.
- **Relationship types enum**: Start minimal with `relates-to` and `questions`. `relates-to` serves as a placeholder indicating "we haven't identified the specific relationship type yet" — it's a signal that the edge needs refinement, not a permanent category. Additional types (e.g., `blocks`, `answers`, `supersedes`, `duplicates`) will be discovered organically as usage patterns emerge rather than defined speculatively upfront.
- **`blocks` relationship**: Inspired by beads' blocking concept — some decisions can't be made until other decisions are resolved. This is a strong candidate for an early addition once the base infrastructure is in place.
- **Export format**: Add `format_version: 2` to JSONL. Relationships exported as outbound edges on each seed. Import handles both v1 (embedded questions, related_to array) and v2.

## Migration

**Scope**: Migration runs on any existing seeds database (there are a few in the wild, all owned by the same user). Since adoption is minimal, we're keeping migration simple:

- Migration is idempotent (checks table/column existence before acting)
- Runs in a transaction with DB backup beforehand
- JSONL is the git-tracked source of truth — data is always recoverable
- No phased rollout needed; we can do a clean cut since all instances are under one user's control

**No separate migration phase**: Rather than a multi-phase approach where old and new code coexist, we'll do a single atomic migration. The old `questions` table and `related_to` column are migrated and removed in one pass.

## Phased Implementation

### Phase 1: Models + DB layer
Build the foundation without touching CLI or export.

**`src/seeds/models.py`**:
- Add `RelationType` enum (initially: `relates-to`, `questions`)
- Add `Relationship` dataclass (source_id, target_id, rel_type, created_at)
- Remove `Question` dataclass and `QuestionStatus` enum
- Remove `related_to` from `Seed` dataclass

**`src/seeds/db.py`**:
- Add `relationships` table to schema, remove `questions` table and `related_to` column
- Add migration: create relationships table, populate from `related_to` JSON arrays and `questions` table, then drop old structures
- Add CRUD: `create_relationship()`, `get_relationships(seed_id, rel_type=None, direction='both')`, `delete_relationship()`
- Add `get_questions_for_seed(seed_id)` → returns Seed objects via relationship query
- Update `delete_seed()` to cascade-delete relationships
- Update `is_blocked()`: blocked if unresolved children OR unresolved question-seeds
- Remove all Question CRUD methods
- Simplify FTS: remove `question_texts` column, drop question triggers, rebuild index
- Indexes on source_id, target_id, rel_type

**Tests**: New `TestRelationships` class in `test_db.py`, rewrite question tests

### Phase 2: CLI + export + web
Wire up the new DB layer to user-facing code.

**`src/seeds/cli.py`**:
- `ask`: creates seed (type=question) + `questions` relationship
- `answer`: sets seed.content = answer, status = RESOLVED
- `questions`: queries via relationship type
- `show -q`: displays question-seeds via relationships
- `link`: writes to relationships table, add `--type` option (default `relates-to`)
- `tree`: reads relationships from table
- `doctor`: update orphan check to use relationships

**`src/seeds/export.py`**:
- Export: `format_version: 2`, relationships as outbound edges per seed, no embedded questions
- Import: detect format version, handle v1 (reconstruct relationships from old format) and v2

**`src/seeds/prime.py`**:
- Update command descriptions (minor text changes)

**`src/seeds/web.py`** + templates:
- Read relationships from DB instead of `seed.related_to`
- Questions page queries question-type seeds

## Files Modified (in order)
1. `src/seeds/models.py` — add RelationType, Relationship; remove Question, QuestionStatus, related_to
2. `src/seeds/db.py` — relationships table, migration, new queries, remove question methods, simplify FTS
3. `src/seeds/cli.py` — rewrite ask/answer/questions/link/show/tree/doctor
4. `src/seeds/export.py` — v2 format with backward-compatible import
5. `src/seeds/prime.py` — update command descriptions
6. `src/seeds/web.py` — use relationships for display
7. `tests/conftest.py` — update fixtures
8. `tests/test_db.py` — rewrite question tests as relationship tests
9. `tests/test_cli.py` — update command tests
10. `tests/test_export.py` — add v1→v2 import test, update roundtrip

## Verification

All verification is done through the test suite — no manual smoke tests against the production database.

1. **`uv run pytest`** — the single source of truth for correctness
2. Tests use `SEEDS_DIR` pointed at `tmp_path` fixtures (pytest's built-in temp directories)
3. Test fixtures include:
   - A v1 JSONL file with embedded questions and `related_to` arrays (for migration/import testing)
   - A v2 JSONL file with relationships as outbound edges (for roundtrip testing)
4. Specific test coverage:
   - Relationship CRUD (create, query by type/direction, delete, cascade on seed delete)
   - Question-as-seed lifecycle (`ask` creates seed + relationship, `answer` resolves it)
   - `is_blocked()` considers both unresolved children and unresolved question-seeds
   - v1 → v2 import (old format JSONL reconstructed correctly)
   - v2 export roundtrip
   - FTS indexes question-seeds by their title/content (no separate `question_texts` column)
   - `link` command creates typed relationships
   - `doctor` detects orphaned relationships

## Open Questions

1. **Relationship type discovery**: How do we handle adding new relationship types over time? Options: (a) just add to the enum and bump a version, (b) allow freeform strings in the DB but validate in the CLI, (c) registry pattern. Leaning toward (a) for simplicity.
2. **`blocks` relationship**: Strong candidate for early addition. Should `blocks` be directional (A blocks B) and integrate with the existing `is_blocked()` / `blocked` command? This would give seeds the same blocking semantics beads has for issues.
3. **ID prefix configuration**: The plan assumes `seeds-` as the prefix for this project. Should the prefix be configurable per-project (stored in `.seeds/config` or similar), or is it always derived from the project name?
