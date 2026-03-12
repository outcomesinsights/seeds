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
- **Question → seed mapping**: `q.text` → `seed.title`, `q.answer` → `seed.content`, status: OPEN→CAPTURED, ANSWERED→RESOLVED, DEFERRED→DEFERRED. Keep `q-` ID prefix.
- **CLI stays familiar**: `seeds ask` and `seeds answer` remain as convenience commands, but create seeds + relationships under the hood.
- **Relationship types enum**: `relates-to`, `questions`, `answers`, `supersedes`, `duplicates`. Only first two used initially.
- **Export format**: Add `format_version: 2` to JSONL. Relationships exported as outbound edges on each seed. Import handles both v1 (embedded questions, related_to array) and v2.

## Phased Implementation

### Phase 1: Add relationships table + migration (non-breaking)
All existing code continues to work. New table created alongside old structures.

**`src/seeds/models.py`**:
- Add `RelationType` enum
- Add `Relationship` dataclass (source_id, target_id, rel_type, created_at)

**`src/seeds/db.py`**:
- Add `relationships` table to schema
- Add `ensure_relationships()` migration: creates table, populates from `related_to` JSON arrays
- Add CRUD: `create_relationship()`, `get_relationships(seed_id, rel_type=None, direction='both')`, `delete_relationship()`
- Indexes on source_id, target_id, rel_type

**Tests**: New `TestRelationships` class in `test_db.py`

### Phase 2: Migrate questions to seeds
The big change. Questions become seeds with typed relationships.

**`src/seeds/db.py`**:
- Add `_migrate_questions_to_seeds()`: for each question row, INSERT a seed (type=question) + INSERT a `questions` relationship. Runs in transaction. Backs up DB first.
- Remove all Question CRUD methods
- Add `get_questions_for_seed(seed_id)` → returns Seed objects via relationship query
- Update `delete_seed()` to cascade-delete relationships
- Update `is_blocked()`: blocked if unresolved children OR unresolved question-seeds

**`src/seeds/models.py`**:
- Remove `Question` dataclass and `QuestionStatus` enum

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

### Phase 3: Remove `related_to` column + cleanup
- Drop `related_to` from seeds table (SQLite table rebuild)
- Remove `related_to` from Seed dataclass
- Simplify FTS: remove `question_texts` column, drop question triggers, rebuild index
- Update all tests

## Files Modified (in order)
1. `src/seeds/models.py` — add RelationType, Relationship; remove Question, QuestionStatus, related_to
2. `src/seeds/db.py` — relationships table, migrations, new queries, remove question methods
3. `src/seeds/cli.py` — rewrite ask/answer/questions/link/show/tree/doctor
4. `src/seeds/export.py` — v2 format with backward-compatible import
5. `src/seeds/prime.py` — update command descriptions
6. `src/seeds/web.py` — use relationships for display
7. `tests/conftest.py` — update fixtures
8. `tests/test_db.py` — rewrite question tests as relationship tests
9. `tests/test_cli.py` — update command tests
10. `tests/test_export.py` — add v1→v2 import test, update roundtrip

## Migration Safety
- Back up `seeds.db` → `seeds.db.bak` before migration
- JSONL is git-tracked source of truth — data recoverable even if SQLite migration fails
- Migrations are idempotent (check table/column existence)
- All migration steps in transactions
- `seeds sync --flush-only` after migration to update JSONL

## Verification
1. `uv run pytest` — all tests pass
2. `uv run seeds list` — shows all seeds (including former questions as question-type seeds)
3. `uv run seeds questions` — shows open questions (via relationship query)
4. `uv run seeds show <id> -q` — shows question-seeds attached via relationship
5. `uv run seeds search "polymorphic"` — FTS still works
6. `uv run seeds link <a> --relates-to <b>` — creates typed relationship
7. `uv run seeds sync --flush-only` — exports v2 JSONL
8. Reimport from v1 JSONL into fresh DB — backward compat verified
9. `uv run seeds doctor` — clean health check

## Open Questions

(To be populated with feedback)
