# Deep Analysis: Applying Beads Architecture to ADR Tracking

## The Core Problem: Architectural Design Amnesia

Both documents identify the same fundamental issue from different angles:

**Beads perspective** (Steve Yegge):
> "If you got competing documents, obsolete documents, conflicting documents, ambiguous documents - they get dementia."

**ADR perspective** (Michael Nygard):
> "When teams don't document decisions, future developers either blindly accept past choices or blindly change them."

For AI agents, this compounds into **architectural design amnesia**: every session, the agent forgets:
- What architectural decisions were made
- Why certain approaches were chosen over alternatives
- What constraints and tradeoffs informed those choices
- What decisions depend on or enable other decisions

---

## Why Beads Succeeds Where ADR Tools Fail

The key insight is:

| What Beads Provides | What ADR Tools Lack |
|---------------------|---------------------|
| SQLite + JSONL storage | Markdown files only |
| Discrete typed fields | Free-form sections |
| `bd dep add` relationships | Text-based "Superseded by" |
| `bd list --status=X` | Manual grep |
| `bd ready` (unblocked items) | Nothing comparable |
| Hash-based IDs | Sequential numbering (collision-prone) |
| Atomic CLI operations | "Open editor, fill template" |

The **secret sauce** is that Beads doesn't ask the AI to parse free-form text. It provides:
1. **Structured, queryable data** - Not "interpret this markdown"
2. **Programmatic operations** - Not "open vim and edit"
3. **Explicit relationships** - Not "find the text that says 'related to'"
4. **Enforced schema** - Not "hope the AI follows the template"

---

## ADR-Specific Domain Needs

While applying Beads' architecture, ADRs have distinct requirements:

### 1. Different Lifecycle Model

```
Beads Issues:           ADRs:
open                    proposed
  ↓                       ↓
in_progress             accepted ←────────────┐
  ↓                       ↓                   │
closed                  superseded/deprecated │
                             │                │
                        rejected              │
                             └────────────────┘
                        (new ADR supersedes old)
```

### 2. Immutability is Sacred

Beads issues can be updated freely. ADRs, once accepted, become **immutable historical records**. Changes require a new ADR that supersedes the old one. This is philosophically different - ADRs are a decision log, not a work tracker.

### 3. Rich Options Analysis

ADRs need to capture not just "what we decided" but "what we considered and why we rejected the alternatives":

```json
{
  "options": [
    {
      "name": "PostgreSQL",
      "description": "Relational database with ACID guarantees",
      "pros": ["Team expertise", "Mature ecosystem", "Strong consistency"],
      "cons": ["Scaling limits", "Schema rigidity"],
      "chosen": true
    },
    {
      "name": "MongoDB",
      "description": "Document database",
      "pros": ["Schema flexibility", "Horizontal scaling"],
      "cons": ["Learning curve", "Eventual consistency"],
      "chosen": false
    }
  ]
}
```

### 4. ADR-Specific Relationships

| Beads Relationship | ADR Relationship | Semantic Difference |
|-------------------|------------------|---------------------|
| `blocks` | `depends_on` | Similar - temporal ordering |
| `parent/child` | - | ADRs are typically flat |
| `relates_to` | `relates_to` | Same - loose coupling |
| - | `supersedes` | ADR-specific: replaces with immutability |
| - | `amends` | ADR-specific: modifies without replacing |
| - | `enables` | ADR-specific: "this decision opens up..." |

### 5. Different Query Patterns

Instead of "what work is ready?", ADR queries are:
- "What decisions affect the authentication system?"
- "Are there conflicting decisions about data storage?"
- "What decisions are still proposed and need review?"
- "What would break if we changed this decision?"

---

## Proposed Architecture: ADR-Beads

### Storage Layer (Identical to Beads)

```
.adrb/
├── decisions.db        # SQLite for fast queries
├── decisions.jsonl     # Git-friendly source of truth
└── config.toml         # Project configuration
```

### Data Model

```json
{
  "id": "adr-a3f8",
  "title": "Use PostgreSQL for user data",
  "status": "accepted",

  "context": "We need ACID transactions for user data. Team has SQL expertise. Expecting moderate scale initially.",
  "decision": "We will use PostgreSQL as the primary data store.",
  "rationale": "Team expertise and ACID requirements outweigh scaling concerns at current scale.",
  "consequences": [
    "positive: Familiar tooling and strong ecosystem",
    "negative: Need to plan for vertical scaling limits",
    "neutral: DBA skills required for production"
  ],

  "drivers": ["data-integrity", "team-expertise", "time-to-market"],
  "options": [...],
  "tags": ["database", "infrastructure", "backend"],

  "created_at": "2025-01-22T10:00:00Z",
  "created_by": "alice",
  "decided_at": "2025-01-22T14:00:00Z",
  "decided_by": ["alice", "bob", "carol"],

  "supersedes": null,
  "superseded_by": null,
  "depends_on": ["adr-b2c1"],
  "enables": ["adr-c4d2", "adr-e5f3"],
  "amends": null,
  "related_to": ["adr-f6g4"]
}
```

### CLI Design (Flag-Based, No Editors)

```bash
# Creating decisions
adr create --title="Use PostgreSQL" --context="..." --status=proposed
adr create --title="..." --drivers="reliability,expertise" --tags="database"

# Options analysis
adr option <id> add "PostgreSQL" --pros="ACID,familiar" --cons="scaling"
adr option <id> add "MongoDB" --pros="flexible" --cons="learning-curve"
adr option <id> choose "PostgreSQL"

# Recording the decision
adr decide <id> --rationale="..." --consequences="..."

# Status transitions
adr accept <id>
adr reject <id> --reason="..."
adr deprecate <id> --reason="Technology sunset"
adr supersede <old-id> <new-id>  # Creates link + updates status

# Relationships
adr link <id> --depends-on <other-id>
adr link <id> --enables <future-id>
adr link <id> --relates-to <related-id>

# Queries
adr list                           # All decisions
adr list --status=accepted         # Filter by status
adr list --tag=database            # Filter by tag
adr list --affects=authentication  # Semantic search
adr proposed                       # Awaiting review
adr blocked                        # Waiting on dependencies
adr show <id>                      # Full detail with relationships
adr tree <id>                      # Dependency tree

# Context injection
adr prime                          # AI-optimized context output

# Sync
adr sync                           # Full sync with git
adr sync --flush-only              # Just export to JSONL
```

### Hook Integration

```json
{
  "hooks": {
    "SessionStart": [{ "command": "adr prime" }],
    "PreCompact": [{ "command": "adr prime" }]
  }
}
```

### The `adr prime` Output

```markdown
# ADR Workflow Context

> **Context Recovery**: Run `adr prime` after compaction, clear, or new session

## Protocol

**Before making architectural choices:**
1. `adr list --tag=<area>` - Check existing decisions
2. If conflicting with accepted ADR → discuss with user, don't proceed
3. If building on existing decision → `adr link --depends-on`

**When capturing new decisions:**
1. `adr create --title="..." --context="..." --status=proposed`
2. `adr option <id> add "..." --pros="..." --cons="..."`
3. `adr decide <id> --rationale="..." --consequences="..."`

**Key Rules:**
- NEVER modify accepted ADRs - supersede them instead
- Check `adr list --status=accepted` before major design choices
- Document ALL consequences (positive, negative, neutral)
- Link related decisions

## Essential Commands
- `adr list --status=accepted` - Current decisions
- `adr proposed` - Decisions awaiting review
- `adr show <id>` - Full decision details
- `adr create --title="..." --context="..."` - New decision
```

---

## How This Solves Design Amnesia

**Without ADR-Beads:**
```
Session 1: AI designs auth system using JWT
Session 2: AI doesn't know about Session 1, proposes sessions-based auth
Session 3: AI proposes OAuth, unaware of prior discussions
→ Design churn, wasted effort, potential conflicts
```

**With ADR-Beads:**
```
Session 1: AI creates ADR for JWT auth, accepts it
Session 2: `adr prime` injects context
           AI runs `adr list --tag=auth`, sees JWT decision
           AI respects existing decision, builds on it
Session 3: If requirements change, AI creates new ADR that supersedes
           Historical record preserved
→ Coherent evolution, no amnesia
```

---

## Key Insight: ADRs as "Architectural Immune System"

The `adr prime` injection acts as an **immune system** against design amnesia:

1. **Detection** - `adr list --status=accepted` reveals what decisions exist
2. **Protection** - AI must check before making conflicting choices
3. **Memory** - Even across context compaction, the decisions persist
4. **Evolution** - Supersession allows change while preserving history

---

## Implementation Considerations

### Language Choice

Given the beads patterns (Go for CLI, SQLite for storage), a Go implementation would be natural. Python with uv could also work well.

### Schema Migration

Unlike beads (which tracks transient work), ADRs are historical records. Schema migrations must preserve old data faithfully.

### Markdown Export

While storage is JSONL, humans often want to read ADRs as markdown. An `adr export <id>` could render to traditional ADR format for documentation.

### Integration with Beads

These could coexist:
- Beads tracks "implement ADR-123" as work items
- ADR-Beads tracks the decisions themselves
- Cross-references via `external_ref` fields

---

## Conclusion

ADR-Beads would be a significant advancement for AI-assisted architectural decision-making - applying the proven patterns of beads (structured data, CLI-first, git-backed, hook-injected) to the specific domain of capturing and respecting architectural decisions.
