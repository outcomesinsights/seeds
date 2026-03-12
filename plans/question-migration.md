# Plan: Typed Relationships + Questions-as-Seeds

## Context

Two design decisions converging: (1) relationships need types (`relates-to`, `questions`, `answers`, etc.) instead of the current untyped `related_to` JSON array, and (2) questions should just be seeds, with relationships carrying the semantics ("this seed *questions* that seed"). This resolves seed-567d and seed-80ba simultaneously.

The current model has a `questions` table (separate entity) and a `related_to` JSON array on each seed (untyped, bidirectional). The new model has a single `relationships` table with typed, directed edges, and questions become seeds of type=question linked via a `questions` relationship.

## Relationship Analysis from Production Data

Examined 114 seeds, 36 questions, and 65 seeds with `related_to` links. Here are the relationship patterns actually present:

### Pattern 1: Decision → Idea ("addresses" / "decides-for")
Decisions linked to the idea they resolve. Strongly directional.
- `seed-061a` (decision: Use Flask) → `seed-5f7b` (idea: Web UI)
- `seed-4950` (decision: Use Pico CSS) → `seed-5f7b` (idea: Web UI)
- `seed-43a0` (decision: Read-only) → `seed-5f7b` (idea: Web UI)
- `seed-91dc` (decision: Default port) → `seed-5f7b` (idea: Web UI)
- `seed-80e3` (decision: Show questions in detail) → `seed-5f7b` (idea: Web UI)

### Pattern 2: Concern → Idea/Concern ("raises-concern-about" / clustering)
Concerns linked to what they're concerned about, or clustered with related concerns.
- `seed-ed41` (concern: AI adoption) ← `seed-5c22`, `seed-aeb6` (specific friction instances)
- `seed-f537` (concern: exponential growth) ← `seed-39d3`, `seed-5c7b`, `seed-502a`, `seed-bac9` (related mitigations/observations)
- `seed-80ba` (concern: question confusion) ↔ `seed-29c0` (idea: question/exploration overlap)

### Pattern 3: Question → Seed ("questions")
The `questions` table is a clear directed relationship: question asks about a seed.
- 36 questions across 14 seeds, heavily concentrated on `seed-81a4` (18 questions about shipping beta)
- Questions have answers (25 answered, 11 open) — the answer relationship is implicit in the current model

### Pattern 4: Exploration → Topic ("explores")
Explorations linked to the thing they're investigating.
- `seed-1f89` (exploration: options modeling) ↔ `seed-eedd` (idea: where do alternatives live?)
- `seed-134e` (exploration: knowledge accumulation) ↔ `seed-dedd.2`, `seed-7e8e`, `seed-1def`, `seed-d2e765de`
- `seed-73f0` (exploration: why no MCP in beads) ↔ `seed-c989.1` (idea: MCP transport)

### Pattern 5: Mutual/symmetric ("relates-to" — genuinely undifferentiated)
Some links are genuinely symmetric with no clear directionality:
- `seed-0301` (markdown rendering) ↔ `seed-ccf0` (prettify markdown) — related ideas, neither depends on the other
- `seed-7102` (nested view) ↔ `seed-76a1` (toggle nested/flat) — complementary features
- `seed-4653` ↔ `seed-1fadaed5` — both about linking seeds to external things

### Summary of Observed Relationship Types

| Pattern | Candidate type | Direction | Count (approx) |
|---------|---------------|-----------|-----------------|
| Question asks about seed | `questions` | directed | 36 |
| Answer resolves question | `answers` | directed | 25 |
| Decision addresses idea | relates-to (TBD) | directed | ~15 |
| Concern about something | relates-to (TBD) | directed | ~12 |
| Exploration investigates | relates-to (TBD) | directed | ~8 |
| Symmetric/undifferentiated | `relates-to` | bidirectional | ~20 |

**Conclusion**: `questions` and `answers` are clearly distinct relationship types. The other patterns (decision-addresses, concern-about, explores) are real but less urgent — they can be refined from `relates-to` over time as the organic discovery process reveals which distinctions matter in practice.

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

- **Directed edges**: `relates-to` stored as two rows (A→B, B→A) for bidirectional. `questions` and `answers` are single directed edges.
- **Question → seed mapping**: `q.text` → `seed.title`, `q.answer` → `seed.content`, status: OPEN→CAPTURED, ANSWERED→RESOLVED, DEFERRED→DEFERRED. Migrated questions get new project-prefixed IDs (e.g., `seeds-a1b2c3d4`), same as all other seeds. The `q-` prefix is retired.
- **ID prefix convention**: All seeds use the project name as their ID prefix. In this project, that's `seeds-`. Hardcoded default for now — no config file exists yet, and adding one isn't necessary for this change. If/when we add project-level configuration, the prefix can become configurable then.
- **CLI stays familiar**: `seeds ask` and `seeds answer` remain as convenience commands, but create seeds + relationships under the hood.
- **Relationship types enum**: `relates-to`, `questions`, `answers`. Three types to start:
  - `questions` — directed: question-seed → seed it asks about
  - `answers` — directed: answer content lives in the question-seed itself (content field + RESOLVED status), but if a separate seed answers a question, the `answers` edge captures that
  - `relates-to` — bidirectional placeholder: indicates two seeds are related but we haven't identified the specific relationship yet. Serves as a triage signal — periodic review of `relates-to` edges should extract more specific types over time.
- **Relationship type discovery**: New types are added to the enum as patterns emerge from reviewing `relates-to` edges. The process is: (1) use `relates-to` by default, (2) periodically look for clusters of `relates-to` that share a pattern, (3) name the pattern and add it to the enum. This is evolutionary, not speculative.
- **Blocking semantics**: Seeds that have unresolved question-seeds (via `questions` relationship) or unresolved children cannot themselves be resolved. This gives seeds the same "blocked" concept beads has — some decisions can't be made until prerequisite questions/decisions are resolved first.
- **Export format**: Add `format_version: 2` to JSONL. Relationships exported as outbound edges on each seed. Import handles both v1 (embedded questions, related_to array) and v2.

## Migration

**Scope**: Migration runs on any existing seeds database (there are a few in the wild, all owned by the same user). Since adoption is minimal, we're keeping migration simple:

- Migration is idempotent (checks table/column existence before acting)
- Runs in a transaction with DB backup beforehand
- JSONL is the git-tracked source of truth — data is always recoverable
- No phased rollout needed; we can do a clean cut since all instances are under one user's control

**No separate migration phase**: Rather than a multi-phase approach where old and new code coexist, we'll do a single atomic migration. The old `questions` table and `related_to` column are migrated and removed in one pass.

**What migration does**:
1. Creates `relationships` table
2. For each seed with `related_to` entries: creates bidirectional `relates-to` relationship rows
3. For each question row: creates a new seed (type=question, title=text, content=answer, appropriate status) and a `questions` relationship from the new seed to its parent seed
4. Drops `questions` table and `related_to` column
5. Rebuilds FTS index (simplified, no `question_texts`)

## Phased Implementation

### Phase 1: Models + DB layer
Build the foundation without touching CLI or export.

**`src/seeds/models.py`**:
- Add `RelationType` enum (`relates-to`, `questions`, `answers`)
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
   - Migration from a pre-populated v1 database (questions table + related_to arrays) produces correct relationships
