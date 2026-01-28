# seeds MVP Specification

**Version:** 0.1.1 (Post-Interview)
**Created:** 2026-01-27
**Updated:** 2026-01-27

---

## What is seeds?

seeds is a **deliberation capture tool** that helps ideas grow from initial seeds into mature decisions (the "fruit"). Unlike traditional decision-tracking tools that capture only outcomes, seeds captures the **journey**: the questions asked, alternatives considered, mind-racing tangents, and gradual refinement that leads to a decision.

### Core Philosophy

- **Capture the journey, not just the destination** - Record how thinking evolved
- **Jot and defer** - Quick capture during mind-racing, explore later
- **AI as deliberation partner** - Designed for human-AI collaboration from day one
- **Domain agnostic** - Software, RPGs, house projects, life decisions
- **Nothing is precious** - Expect the tool itself to evolve through use

---

## MVP Scope

The MVP focuses on the **minimal set of features** needed to start using seeds to design seeds itself. We can iterate from there.

### In Scope

1. **Seed CRUD** - Create, read, update, close seeds
2. **Quick capture** - Low-friction "jot an idea" command
3. **Lifecycle states** - Track seed maturity
4. **Questions** - Attach questions to seeds, mark as answered
5. **Backlog/defer** - Shelve seeds for later
6. **Basic relationships** - Seeds can relate to other seeds
7. **CLI-first** - Flag-based commands, no editor popups
8. **SQLite storage** - Fast local queries
9. **JSONL export** - Git-friendly persistence
10. **Prime command** - AI context injection for Claude Code hooks

### Out of Scope (Future)

- Options/alternatives modeling (complex pros/cons)
- Full IBIS structure (Issues → Positions → Arguments)
- ADR generation ("fruit" export)
- Beads integration
- Multi-user collaboration
- MCP server
- Daemon for background sync

---

## Data Model

### Seed

The core entity. An idea at any stage of development.

```python
@dataclass
class Seed:
    id: str                    # Hash-based with optional hierarchy, e.g., "seed-a1b2" or "seed-a1b2.1"
    title: str                 # Brief description
    content: str               # Full description/exploration (AI updates directly)
    status: SeedStatus         # Lifecycle state
    seed_type: SeedType        # Categorization
    tags: list[str]            # Freeform; CLI suggests existing tags

    # Timestamps
    created_at: datetime
    updated_at: datetime

    # Relationships
    related_to: list[str]      # Loose coupling to other seeds
```

**Parent-child via ID convention (like Beads):**
- `seed-a1b2` - Parent seed
- `seed-a1b2.1` - First child
- `seed-a1b2.2` - Second child
- `seed-a1b2.1.1` - Nested child

**Derived "blocked" state:** A seed is considered blocked if it has unresolved children. No explicit status needed.

*Note: Evolution history tracked via git, not internal log.*

### SeedStatus (Lifecycle)

```python
class SeedStatus(Enum):
    CAPTURED = "captured"      # Just jotted down, unexplored
    EXPLORING = "exploring"    # Actively being developed
    DEFERRED = "deferred"      # Backlogged for later
    RESOLVED = "resolved"      # Reached a conclusion
    ABANDONED = "abandoned"    # Decided not to pursue
```

**Lifecycle flow:**
```
CAPTURED → EXPLORING → RESOLVED
    ↓
DEFERRED
    ↓
EXPLORING (when ready)

Any state → ABANDONED (explicit rejection)
```

*Note: "blocked" status deferred to future version. For MVP, use `deferred` with a note.*

### SeedType

```python
class SeedType(Enum):
    IDEA = "idea"              # General thought
    QUESTION = "question"      # Something needing an answer
    DECISION = "decision"      # A choice made
    EXPLORATION = "exploration" # Research/investigation notes
    CONCERN = "concern"        # Risk or worry
```

### Question (Attached to Seeds)

```python
@dataclass
class Question:
    id: str
    seed_id: str               # Parent seed
    text: str                  # The question
    answer: str | None         # Answer when resolved
    status: QuestionStatus     # open | answered | deferred
    created_at: datetime
    answered_at: datetime | None
```

---

## CLI Design

### Principles

- **Flag-based** - No interactive editors (blocks AI agents)
- **Atomic operations** - Each command does one thing
- **Queryable** - Easy to filter and find
- **Minimal output for scripting** - Quiet mode available

### Commands

#### Creating Seeds

```bash
# Full creation
seeds create --title="..." --content="..." --type=idea --tags=foo,bar

# Quick capture (minimal friction)
seeds jot "Quick thought I want to capture"

# Create a question
seeds ask "What database should we use?" --seed=seed-a1b2

# Create from stdin (for piping)
echo "My idea" | seeds create --title="Piped idea" --stdin
```

#### Viewing Seeds

```bash
# List seeds
seeds list                           # All non-resolved seeds
seeds list --status=captured         # Filter by status
seeds list --type=question           # Filter by type
seeds list --tag=database            # Filter by tag
seeds list --all                     # Include resolved/abandoned

# Show details
seeds show <id>                      # Full seed details
seeds show <id> --questions          # Include attached questions

# What needs attention?
seeds ready                          # Captured seeds ready to explore
seeds questions                      # Open questions across all seeds
seeds deferred                       # Backlogged for review
```

#### Updating Seeds

```bash
# Change status
seeds explore <id>                   # CAPTURED → EXPLORING
seeds defer <id>                     # → DEFERRED
seeds resolve <id>                   # → RESOLVED
seeds abandon <id> --reason="..."    # → ABANDONED

# Update content
seeds update <id> --title="..."
seeds update <id> --content="..."
seeds update <id> --tags=new,tags
seeds update <id> --append="Additional thoughts"  # Append to content

# Answer a question
seeds answer <question-id> "The answer is..."
```

#### Relationships

```bash
# Create child seed (ID inherits from parent)
seeds create --title="Sub-task" --parent=seed-a1b2   # Creates seed-a1b2.1

# Link seeds (loose coupling)
seeds link <id> --relates-to <other-id>

# View relationships
seeds tree <id>                      # Show hierarchy/relationships
seeds blocked                        # Seeds with unresolved children
```

#### Sync & Export

```bash
# Export to JSONL
seeds sync                           # Export to .seeds/seeds.jsonl
seeds sync --flush-only              # Same (no git ops for MVP)

# Health check
seeds doctor                         # Check for issues
```

#### Context Injection

```bash
# AI-optimized context output
seeds prime                          # Output workflow context for Claude
```

---

## Storage

### Directory Structure

```
.seeds/
├── seeds.db          # SQLite database (fast queries)
├── seeds.jsonl       # JSONL export (git-friendly)
└── config.toml       # Project configuration (future)
```

### SQLite Schema

```sql
CREATE TABLE seeds (
    id TEXT PRIMARY KEY,          -- Hierarchical: "seed-a1b2" or "seed-a1b2.1"
    title TEXT NOT NULL,
    content TEXT,
    status TEXT NOT NULL DEFAULT 'captured',
    seed_type TEXT NOT NULL DEFAULT 'idea',
    tags TEXT,  -- JSON array
    related_to TEXT,  -- JSON array of seed IDs
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    resolved_at TEXT
);

-- Parent-child derived from ID: seed-a1b2.1's parent is seed-a1b2

CREATE TABLE questions (
    id TEXT PRIMARY KEY,
    seed_id TEXT NOT NULL,
    text TEXT NOT NULL,
    answer TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    answered_at TEXT,
    FOREIGN KEY (seed_id) REFERENCES seeds(id)
);

-- Indexes for common queries
CREATE INDEX idx_seeds_status ON seeds(status);
CREATE INDEX idx_seeds_type ON seeds(seed_type);
CREATE INDEX idx_questions_seed ON questions(seed_id);
CREATE INDEX idx_questions_status ON questions(status);
```

### JSONL Format

One seed per line, questions embedded:

```json
{"id": "seed-a1b2", "title": "Database choice", "content": "...", "status": "exploring", "seed_type": "idea", "tags": ["infrastructure"], "questions": [{"id": "q-c3d4", "text": "What are our scaling requirements?", "answer": null, "status": "open"}], "created_at": "2026-01-27T10:00:00Z", "updated_at": "2026-01-27T14:00:00Z"}
```

---

## Prime Command Output

The `seeds prime` command outputs AI-optimized workflow context:

```markdown
# seeds Workflow Context

> **Context Recovery**: Run `seeds prime` after compaction, clear, or new session

## Core Rules
- Use seeds to capture ideas, questions, and deliberation
- `seeds jot "..."` for quick capture during mind-racing
- Mark seeds as `deferred` when not ready to explore
- Questions are first-class - use `seeds ask` to track them

## Essential Commands

### Quick Capture
- `seeds jot "Quick thought"` - Minimal friction capture
- `seeds ask "Question?" --seed=<id>` - Attach question to seed

### Finding Work
- `seeds ready` - Captured seeds ready to explore
- `seeds questions` - Open questions needing answers
- `seeds deferred` - Review backlog

### Updating
- `seeds explore <id>` - Start working on a seed
- `seeds resolve <id>` - Mark as resolved
- `seeds defer <id>` - Move to backlog
- `seeds answer <q-id> "..."` - Answer a question

### Session End
- `seeds sync` - Export to JSONL
```

---

## Hook Integration

For Claude Code (`~/.claude/settings.json`):

```json
{
  "hooks": {
    "SessionStart": [
      {"hooks": [{"command": "seeds prime", "type": "command"}], "matcher": ""}
    ],
    "PreCompact": [
      {"hooks": [{"command": "seeds prime", "type": "command"}], "matcher": ""}
    ]
  }
}
```

---

## Implementation Notes

### ID Generation

Hash-based IDs to prevent collisions:

```python
import hashlib
import time

def generate_id(prefix: str = "seed") -> str:
    """Generate a short hash-based ID like 'seed-a1b2'."""
    data = f"{time.time()}{os.urandom(8).hex()}"
    hash_val = hashlib.sha256(data.encode()).hexdigest()[:4]
    return f"{prefix}-{hash_val}"
```

### Python Project Structure

```
seeds/
├── pyproject.toml
├── src/
│   └── seeds/
│       ├── __init__.py
│       ├── cli.py           # Click-based CLI
│       ├── models.py        # Dataclasses
│       ├── db.py            # SQLite operations
│       ├── export.py        # JSONL export
│       └── prime.py         # Context output
└── tests/
    └── ...
```

### Dependencies

- **click** - CLI framework
- **sqlite3** - Database (stdlib)
- **dataclasses** - Models (stdlib)
- **json** - Serialization (stdlib)

---

## Success Criteria for MVP

1. Can create seeds with `seeds create` and `seeds jot`
2. Can list/filter seeds with `seeds list`, `seeds ready`
3. Can update seed status through lifecycle
4. Can attach and answer questions
5. Can defer seeds to backlog
6. Can export to JSONL with `seeds sync`
7. Can inject context with `seeds prime`
8. AI agent (Claude) can use the tool naturally

---

## Design Decisions (from Interview)

Based on user interview (2026-01-27):

1. **History tracking** → Git history only. No internal evolution log. Keeps seeds simple.
2. **Quick capture** → `jot` creates a seed with status=captured. Unified model, no separate inbox.
3. **Questions** → Separate entities with own IDs. Can be listed/queried independently.
4. **Relationships** → Parent-child via ID convention (seed-a1b2.1). "Blocked" is derived: seed with unresolved children.
5. **Tags** → Freeform, but CLI suggests existing tags for consistency.
6. **Statuses** → 5 states (dropped "blocked"): captured, exploring, deferred, resolved, abandoned.
7. **CLI name** → `seeds` (not `sd`).
8. **Mobile capture** → Later feature. MVP is CLI only.
9. **AI updates** → Update content directly. Git tracks what changed.

---

## Open Questions (Remaining)

1. **Granularity** - How fine-grained should seeds be? Many small vs. few large? (Discover through use)
2. **Manifest** - Do we need a summary/manifest for AI to quickly scan seeds? (Observe if needed)

---

## What's Next

1. User interview to refine requirements
2. Build MVP in Python with uv
3. Use seeds to plan seeds improvements
4. Iterate based on actual usage patterns
