# seeds

> A deliberation capture CLI tool that helps ideas grow from seeds into decisions through structured lifecycle tracking.

## CRITICAL: Do Not Pollute the Design Database

The `.seeds/` directory in this project contains **real design data** used to develop and iterate on seeds. It is NOT a test database.

### Forbidden Commands (in this project)

**NEVER run these commands directly in this project:**
- `seeds create` / `seeds jot` / `seeds ask` - Creates new seeds/questions
- `seeds update` / `seeds explore` / `seeds resolve` / `seeds defer` / `seeds abandon` - Modifies seed state
- `seeds answer` - Modifies questions
- `seeds link` - Creates relationships
- `seeds init` - Initializes database

### Safe Commands (read-only)

These are safe to run:
- `seeds list` / `seeds show` / `seeds tree` - View data
- `seeds ready` / `seeds questions` / `seeds deferred` / `seeds blocked` - Query status
- `seeds --help` / `seeds --version` - Help and version
- `seeds sync --flush-only` - Export only (no import)
- `seeds prime` - Context for agents

### How to Test seeds Commands

Use the `SEEDS_DIR` environment variable to redirect to a test directory:

```bash
# Create a temp test directory and run commands there
SEEDS_DIR=/tmp/test-seeds seeds init
SEEDS_DIR=/tmp/test-seeds seeds jot "Test seed"
SEEDS_DIR=/tmp/test-seeds seeds list
```

### Running the Test Suite

The test suite uses its own isolated database and is safe to run:
```bash
uv run pytest
```

---

## Status

- **Active**
- Last meaningful work: 2026-02

## Tech Stack

- Language: Python 3.13+
- Framework: Click (CLI)
- Key dependencies: click>=8.1.0, pytest (dev)
- Package manager: uv
- Data storage: SQLite + JSONL export

## Purpose

Captures thoughts, ideas, and questions with minimal friction ("jot") and tracks them through a lifecycle: captured -> exploring -> resolved/abandoned/deferred. Supports hierarchical seeds (parent/child), attached questions, tagging, and relationships between seeds. Designed for AI-assisted workflows with a `prime` command for context injection.

## Key Entry Points

- `src/seeds/cli.py` - CLI commands via Click (entry point: `seeds`)
- `src/seeds/db.py` - SQLite database layer
- `src/seeds/models.py` - Data models (Seed, Question, enums)
- `src/seeds/export.py` - JSONL import/export
- `src/seeds/prime.py` - AI context output

## Commands

```bash
uv run seeds init                    # Initialize .seeds directory
uv run seeds jot "Quick thought"     # Minimal friction capture
uv run seeds create -t "Title"       # Full seed creation
uv run seeds list                    # List non-terminal seeds
uv run seeds show <id>               # Show seed details
uv run seeds explore <id>            # Start exploring
uv run seeds resolve <id>            # Mark resolved
uv run seeds ask "?" --seed=<id>     # Attach question
uv run seeds answer <q-id> "answer"  # Answer question
uv run seeds sync                    # Export to JSONL
uv run seeds prime                   # AI context output
uv run pytest                        # Run tests
```

## Deploy to Global CLI

After making changes, deploy to the global `seeds` command:

```bash
uv cache clean seeds && uv tool uninstall seeds && uv tool install --reinstall /home/ryan/projects/outins/seeds
```

Then restart any running `seeds serve` processes.

## Relationships

- **Depends on**: None
- **Feeds into**: None

## Domain Concepts

- **Seed**: An idea at any stage (captured/exploring/deferred/resolved/abandoned)
- **SeedType**: idea, question, decision, exploration, concern
- **Question**: First-class object attached to a seed with open/answered/deferred status
- **Hierarchical IDs**: Children use `parent-id.N` format (e.g., `seed-a1b2.1`)
- **Blocked**: A seed with unresolved children cannot be resolved
