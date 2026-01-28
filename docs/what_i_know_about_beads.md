# What I Know About Beads

A comprehensive analysis of [Beads](https://github.com/steveyegge/beads), Steve Yegge's memory system for AI coding agents. This document captures the philosophy, architecture, implementation details, and "secret sauce" that makes Beads work effectively with AI agents like Claude.

## Table of Contents

1. [The Problem Beads Solves](#the-problem-beads-solves)
2. [Philosophy and Design Principles](#philosophy-and-design-principles)
3. [Architecture](#architecture)
4. [The Claude Integration (Secret Sauce)](#the-claude-integration-secret-sauce)
5. [Data Model](#data-model)
6. [CLI Commands and Workflows](#cli-commands-and-workflows)
7. [Key Insights from the Community](#key-insights-from-the-community)
8. [What Makes Beads Work for AI](#what-makes-beads-work-for-ai)
9. [Lessons for ADR-Beads](#lessons-for-adr-beads)

---

## The Problem Beads Solves

### The "50 First Dates" Problem

AI coding agents suffer from session amnesia. Every conversation resets them. As Yegge puts it:

> "If you got competing documents, obsolete documents, conflicting documents, ambiguous documents - they get dementia."

Before Beads, developers managed AI context through scattered markdown files. This approach fails because:

- **Markdown plans are text, not structured data** - requires parsing and interpretation, placing high cognitive load on the model
- **Not queryable** - impossible to build a work queue, audit work, do forensics, or track dependencies
- **No sense of currency** - agents can't distinguish "we decided this yesterday" from "this was a brainstorm from three weeks ago"
- **Everything looks equally valid** - no way to mark decisions as obsolete or superseded

### Claude's Own Testimony

When Yegge gave Claude access to Beads for the first time, Claude said:

> "You've given me memory - I literally couldn't remember anything before, now I can."

This captures the core value proposition: **addressable, persistent, queryable work items**.

---

## Philosophy and Design Principles

### AI-Designed for AI

By and large, **Beads is a tool that AI has built for itself**. Yegge guided it, but only by telling it what he wanted the outcomes to be. He left the schema up to Claude, asking only for parent/child pointers (for epics) and blocking-issue pointers. Claude wound up putting in four kinds of dependency links.

When Yegge asked Claude to "ultrathink" about the architecture, it concluded it was better to build than buy. In about twelve minutes, Claude had created an entire SQL-based bespoke issue tracker with a rich command line interface.

### Core Design Decisions

1. **Addressable Work Items** - Every task gets an ID, a priority, dependencies, an audit trail. Not a wiki. Not scattered notes.

2. **Track Current Work Only** - Beads is designed to track *this week's work*, not future planning or past documentation. Closed issues decay via semantic compaction.

3. **Git as the Database** - Archived issues stay in history. Works offline. No external service dependency. Agents already understand git.

4. **Discrete Fields Over Free-Form Text** - Not "write whatever you want in this section" - structured, queryable fields.

5. **Zero-Conflict IDs** - Hash-based identifiers (like `bd-a1b2`) prevent collisions when multiple branches create tasks independently.

### The "Land the Plane" Protocol

At the end of every session, the user tells their agent: "Let's land the plane." This triggers a scripted cleanup:

1. File beads issues for remaining work
2. Run quality gates: `make lint` and `make test`
3. Close finished issues via `bd close`
4. Execute push sequence: `git pull --rebase` → `bd sync` → `git push`
5. Verify clean state with `git status`

**Critical**: The plane hasn't landed until `git push` succeeds. Never end the session before pushing.

The next session: copy the `bd ready` output, paste, go. The agent immediately knows what to work on.

---

## Architecture

### Dual Storage: SQLite + JSONL

Beads uses a **hybrid storage model**:

| Component | Purpose |
|-----------|---------|
| **SQLite** (`.beads/beads.db`) | Local cache for fast queries - enables database-like operations without loading entire project history |
| **JSONL** (`.beads/issues.jsonl`) | Git-friendly source of truth - one JSON object per line enables clean diffs and automatic merge resolution |

This design gives you the best of both worlds:
- Database performance for queries
- Version control for collaboration
- Git-native conflict resolution

### The Daemon

The BD daemon is a background process (LSP-style, one per workspace) that provides automatic synchronization:

**Key characteristics:**
- Communicates via Unix domain sockets (named pipes on Windows)
- Memory usage: ~30-35MB typical
- Auto-exports to JSONL after CRUD operations (500ms debounce)
- Auto-imports from JSONL when newer than database
- Triggers git commit/push if configured

**Event flow:**
1. RPC mutation → pushed to channel
2. Listener picks up event → triggers debouncer
3. After 500ms silence → export to JSONL
4. If auto-commit enabled → git commit
5. If auto-push enabled → git push

### Hierarchical IDs

Beads supports nested task structures:
- `bd-a3f8` (Epic level)
- `bd-a3f8.1` (Task level)
- `bd-a3f8.1.1` (Subtask level)

This provides collision-free namespacing while maintaining human-friendly structure.

---

## The Claude Integration (Secret Sauce)

### How Claude Code Hooks Work

The integration is remarkably simple but extremely effective. In `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreCompact": [
      {
        "hooks": [{ "command": "bd prime", "type": "command" }],
        "matcher": ""
      }
    ],
    "SessionStart": [
      {
        "hooks": [{ "command": "bd prime", "type": "command" }],
        "matcher": ""
      }
    ]
  }
}
```

This means:
- **SessionStart**: Every time Claude starts a new session, `bd prime` runs and injects workflow context
- **PreCompact**: Before Claude's context is compacted (summarized), `bd prime` runs to preserve critical workflow knowledge

### The `bd prime` Command

This is the **key to making Claude understand Beads**. It outputs AI-optimized markdown context (~80 lines in CLI mode, ~50 tokens in MCP mode):

```markdown
# Beads Workflow Context

> **Context Recovery**: Run `bd prime` after compaction, clear, or new session

# SESSION CLOSE PROTOCOL

**CRITICAL**: Before saying "done" or "complete", you MUST run this checklist:
[ ] bd sync --flush-only    (export beads to JSONL only)

## Core Rules
- Track strategic work in beads (multi-session, dependencies, discovered work)
- Use `bd create` for issues, TodoWrite for simple single-session execution
- When in doubt, prefer bd—persistence you don't need beats lost context

## Essential Commands
[command reference follows...]
```

### Why This Works

1. **Automatic injection** - Claude doesn't have to remember to check Beads; the hooks ensure it's primed at the right moments

2. **Contextual workflow** - The prime output adapts based on:
   - Whether MCP is active (brief vs. full output)
   - Whether git remote is configured (what sync commands to show)
   - Project-specific configuration

3. **Explicit protocol** - The "Session Close Protocol" and "Landing the Plane" give Claude clear, checkable steps

4. **Command-based, not editor-based** - `bd update` with flags instead of `bd edit` which would open vim/nano and block agents

### AGENTS.md Template

Beads creates an `AGENTS.md` file that serves as a minimal pointer:

```markdown
## Issue Tracking

This project uses **bd (beads)** for issue tracking.
Run `bd prime` for workflow context.

**Quick reference:**
- `bd ready` - Find unblocked work
- `bd create "Title" --type task --priority 2` - Create issue
- `bd close <id>` - Complete work
- `bd sync` - Sync with git (run at session end)
```

The key insight: **keep AGENTS.md lean** while `bd prime` provides up-to-date workflow details.

---

## Data Model

### Issue Schema

Based on examining the JSONL format:

```json
{
  "id": "adrb-4q2",
  "title": "Issue title",
  "description": "Issue description",
  "status": "open|in_progress|closed",
  "priority": 0-4,
  "issue_type": "bug|feature|task|epic|chore|merge-request|molecule|gate|agent",
  "owner": "email@example.com",
  "assignee": "username",
  "labels": ["label1", "label2"],
  "created_at": "ISO timestamp",
  "created_by": "Name",
  "updated_at": "ISO timestamp",
  "closed_at": "ISO timestamp",
  "close_reason": "Why it was closed",
  "design": "Design notes",
  "notes": "Additional notes",
  "acceptance": "Acceptance criteria",
  "due": "ISO timestamp",
  "estimate": 60,
  "external_ref": "gh-123"
}
```

### Issue Types

| Type | Purpose |
|------|---------|
| `bug` | Something broken |
| `feature` | New functionality |
| `task` | Work item (tests, docs, refactoring) |
| `epic` | Large feature with subtasks |
| `chore` | Maintenance (dependencies, tooling) |
| `molecule` | Compound/swarm coordination |
| `gate` | Async coordination point |
| `agent` | Agent state tracking |

### Priority System

| Priority | Meaning |
|----------|---------|
| 0 (P0) | Critical - security, data loss, broken builds |
| 1 (P1) | High - major features, important bugs |
| 2 (P2) | Medium - default, nice-to-have |
| 3 (P3) | Low - polish, optimization |
| 4 (P4) | Backlog - future ideas |

**Important**: NOT "high"/"medium"/"low" - numeric values only.

### Dependency Types

Beads supports four types of relationships:

| Type | Meaning |
|------|---------|
| `blocks` | Issue A must complete before Issue B can start |
| `depends_on` | Issue B depends on Issue A (inverse of blocks) |
| `relates_to` | Bidirectional loose coupling |
| `parent/child` | Hierarchical containment (epics) |

Commands:
```bash
bd dep add <issue> <depends-on>    # Add dependency
bd dep <issue> --blocks <blocked>  # Shorthand for blocking
bd dep relate <issue1> <issue2>    # Bidirectional link
bd dep tree <issue>                # Show dependency tree
```

---

## CLI Commands and Workflows

### Finding Work

```bash
bd ready                    # Show issues ready to work (no blockers)
bd list --status=open       # All open issues
bd list --status=in_progress # Currently active work
bd blocked                  # Show all blocked issues
bd show <id>               # Detailed issue view with dependencies
```

### Creating Issues

```bash
bd create --title="..." --type=task --priority=2
bd create "Quick title" -p 0           # Priority 0 task
bd create --title="Epic" --type=epic   # Create epic
bd q "Quick capture"                   # Minimal output for scripting
```

### Updating Issues

```bash
bd update <id> --status=in_progress    # Claim work
bd update <id> --title="New title"     # Update title
bd update <id> --description="..."     # Update description
bd update <id> --assignee=username     # Assign
```

**WARNING**: Do NOT use `bd edit` - it opens $EDITOR which blocks agents.

### Completing Work

```bash
bd close <id>                          # Mark complete
bd close <id> --reason="explanation"   # Close with reason
bd close <id1> <id2> ...              # Close multiple at once
```

### Sync and Collaboration

```bash
bd sync                    # Full sync: export, commit, pull, import, push
bd sync --flush-only       # Just export to JSONL (no git ops)
bd doctor                  # Check for issues
bd doctor --fix            # Auto-fix common problems
```

### Development Loop

```bash
# 1. Find work
bd ready

# 2. Claim it
bd update <id> --status=in_progress

# 3. Do the work
[actual development]

# 4. Complete
bd close <id>

# 5. Sync
bd sync
```

---

## Key Insights from the Community

### From Hacker News Discussion

- **"LLMs don't have memory—every conversation resets them. Giving them somewhere to jot down notes effectively works around this limitation."** - The core insight

- **"Agent Experience" (AX)** - Designing tools optimized for AI rather than humans, acknowledging their different capabilities and constraints

- **Issue trackers are training data** - Agents already understand issue trackers from their training on GitHub issues, Jira, etc. This makes adoption natural.

### From the Edgar Tools Analysis

> "Beads is a tool that AI has built for itself."

This reflects a pivotal moment where AI creates tools to enhance its own capabilities, suggesting an accelerating feedback loop.

### From YUV.AI

> "Being able to see the agent's thought process in Git history alongside the code changes it made is genuinely valuable."

The integration of agent memory with code versioning distinguishes Beads from external memory databases or vector stores.

---

## What Makes Beads Work for AI

### 1. Structured Data Over Natural Language

Beads doesn't ask the AI to parse free-form text. Instead:
- Discrete fields with defined types
- Enum values for status and priority
- Explicit relationships via dependency graph

### 2. Queryable State

Instead of loading an entire specification file:
```bash
bd ready                          # What can I work on?
bd blocked                        # What's stuck?
bd list --status=in_progress     # What am I doing?
```

### 3. Atomic Operations

Every command does one thing:
```bash
bd create    # Create
bd update    # Update
bd close     # Close
bd dep add   # Add dependency
```

No need to open an editor, parse a file, make changes, save, and hope nothing broke.

### 4. Automatic Context Injection

The hooks ensure Claude always has the workflow context it needs:
- `SessionStart` - fresh session gets primed
- `PreCompact` - before context compression, critical info is preserved

### 5. Clear Protocols

"Land the Plane" gives agents a clear checklist. No ambiguity about when work is "done."

### 6. Git Integration

- Changes are version controlled
- Multiple agents can collaborate
- History is preserved
- Offline capable

---

## Lessons for ADR-Beads

Based on this analysis, the key principles to apply to ADR-Beads:

### 1. Structured Fields, Not Markdown Sections

Instead of:
```markdown
## Context
[free-form text]

## Decision
[free-form text]
```

Use discrete, typed fields:
```json
{
  "context": "string",
  "decision": "string",
  "status": "proposed|accepted|rejected|deprecated|superseded",
  "drivers": ["string array"],
  "options": [{"name": "...", "pros": [], "cons": []}]
}
```

### 2. CLI-First, Flag-Based Interface

```bash
adr create --title="Use PostgreSQL" --context="..." --status=proposed
adr decide <id> PostgreSQL --rationale="..."
adr supersede <old-id> <new-id>
```

Never require interactive editors.

### 3. Git-Backed with SQLite Cache

Follow the exact same architecture:
- `decisions.jsonl` for git-friendly storage
- SQLite for fast local queries
- Background daemon for sync

### 4. Hook-Based Context Injection

Create an `adr prime` command that:
- Outputs AI-optimized workflow context
- Adapts based on MCP mode
- Can be injected via Claude Code hooks

### 5. Explicit Relationships

First-class support for:
- `supersedes` / `superseded_by`
- `depends_on`
- `enables`
- `amends`
- `relates_to`

### 6. Status Workflow

```
PROPOSED → ACCEPTED → (SUPERSEDED|DEPRECATED)
    ↓
 REJECTED
```

With immutability: once ACCEPTED, create a new ADR to change it.

### 7. Queryable Operations

```bash
adr ready            # Proposed decisions needing review
adr accepted         # Current accepted decisions
adr list --tag=database --status=accepted
adr blocked          # Decisions waiting on dependencies
```

### 8. Hash-Based IDs

Prevent collisions in multi-branch workflows:
- `adr-a1b2` instead of `adr-001`
- Supports hierarchical: `adr-a1b2.1` for related decisions

---

## Sources

### Official Beads Resources
- [GitHub Repository](https://github.com/steveyegge/beads)
- [AGENT_INSTRUCTIONS.md](https://github.com/steveyegge/beads/blob/main/AGENT_INSTRUCTIONS.md)

### Steve Yegge's Blog Posts
- [Introducing Beads: A Coding Agent Memory System](https://steve-yegge.medium.com/introducing-beads-a-coding-agent-memory-system-637d7d92514a)
- [The Beads Revolution: How I Built The TODO System That AI Agents Actually Want to Use](https://steve-yegge.medium.com/the-beads-revolution-how-i-built-the-todo-system-that-ai-agents-actually-want-to-use-228a5f9be2a9)
- [Beads Best Practices](https://steve-yegge.medium.com/beads-best-practices-2db636b9760c)
- [Beads Blows Up](https://steve-yegge.medium.com/beads-blows-up-a0a61bb889b4)

### Community Analysis
- [YUV.AI: Beads: Git-Backed Memory for AI Agents](https://yuv.ai/blog/beads-git-backed-memory-for-ai-agents-that-actually-remembers)
- [Paddo.dev: Beads: Memory for Your Coding Agents](https://paddo.dev/blog/beads-memory-for-coding-agents/)
- [Better Stack: Beads Issue Tracker Guide](https://betterstack.com/community/guides/ai/beads-issue-tracker-ai-agents/)
- [Edgar Tools: Beads and the Future of Programming](https://www.edgartools.io/beads-and-the-future-of-programming/)
- [Hacker News Discussion](https://news.ycombinator.com/item?id=46075616)

### Related Projects
- [Gas Town](https://www.dolthub.com/blog/2026-01-15-a-day-in-gas-town/) - Steve Yegge's agent orchestrator that uses Beads
