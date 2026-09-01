# seeds

> Git-backed deliberation capture for ideas that need time to grow.

## Critical: Don't Pollute the Design Database

The `.seeds/` directory in this project contains **real design data** used to develop and iterate on seeds. It is NOT a test database.

### What "polluting" means

Running mutating seeds commands as **smoke tests, experimentation, or self-validation against this project's database** is forbidden — that's what `SEEDS_DIR=/tmp/test-seeds` is for. Any seed, question, link, or state change you create against this project's `.seeds/` should be a real, intentional part of seeds' planning and design work.

### Forbidden: smoke testing or experimenting against this database

Don't run any of these against this project's `.seeds/` to "see what happens" or to test the CLI itself:

- `seeds create` / `seeds jot` / `seeds ask` - Creating throwaway seeds/questions
- `seeds update` / `seeds explore` / `seeds resolve` / `seeds defer` / `seeds abandon` - Pretend state changes
- `seeds answer` - Throwaway answers
- `seeds link` - Junk relationships
- `seeds init` - Re-initialization (would clobber)

Use a temp directory for any of that — see "How to Test seeds Commands" below.

### Allowed: genuine planning and design work

If you and the user are actually doing planning, design, or deliberation work on the seeds project itself, mutating the database is exactly what it's for. The user (or another collaborating agent) will be driving this work intentionally — you should follow their lead and use the mutating commands normally. When in doubt about whether a given mutation is "real work" vs "experimentation," ask.

### Always-safe commands (read-only)

These are safe to run regardless of context:

- `seeds list` / `seeds show` / `seeds tree` - View data
- `seeds ready` / `seeds questions` / `seeds deferred` / `seeds blocked` - Query status
- `seeds search` / `seeds export --json` / `seeds history` - Search, dump, and read the git history of the corpus
- `seeds check` / `seeds doctor` - Verify the store
- `seeds --help` / `seeds --version` - Help and version
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

- Language: Python 3.11+
- Framework: Click (CLI)
- Key dependencies: click>=8.1.0, pytest (dev)
- Package manager: uv
- Data storage: one markdown file per seed, `.seeds/seeds/<id>.md` (see `docs/storage-format.md`)

## Purpose

Captures thoughts, ideas, and questions with minimal friction ("jot") and tracks them through a lifecycle: captured -> exploring -> resolved/abandoned/deferred. Supports hierarchical seeds (parent/child), attached questions, tagging, and relationships between seeds. Designed for AI-assisted workflows with a `prime` command for context injection.

## Key Entry Points

- `src/seeds/cli.py` - CLI commands via Click (entry point: `seeds`)
- `src/seeds/seedfile.py` - The ONE reader and writer of the seed-file format
- `src/seeds/store.py` - Set operations over the tree (list, children, blocking, links, prefix, search)
- `src/seeds/models.py` - Enums and text helpers (`Seed`/`Relationship` are legacy, conversion-path only)
- `src/seeds/check.py` - `seeds check`: the format's rules, verified after the fact
- `src/seeds/convert.py` + `src/seeds/legacy.py` - `seeds convert`, and the read-only pre-0.7 reader it needs
- `src/seeds/jsonexport.py` - `seeds export --json`
- `src/seeds/githistory.py` + `src/seeds/history.py` - git as a store: `seeds check --against-git`, and `seeds history`
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
uv run seeds trellis <id> --to <file> --as "<principle>"   # Record a matured seed as a durable trellis
uv run seeds ask "?" --seed=<id>     # Attach question
uv run seeds answer <q-id> "answer"  # Answer question
uv run seeds update <id> --type <t>  # Change a seed's type (any string)
uv run seeds update <id> --content-file <f>   # Replace a body from a file (or --content - for stdin)
uv run seeds retype --from X --to Y  # Bulk-remap one type to another
uv run seeds search "<regex>"        # ripgrep over the seed files
uv run seeds history <id>            # How a seed changed, commit by commit, across the conversion
uv run seeds check                   # Verify the files; exits non-zero on a violation
uv run seeds doctor                  # Store and installation health
uv run seeds export --json           # The whole corpus as JSONL on stdout
uv run seeds convert                 # One-time: pre-0.7 SQLite + JSONL -> .seeds/seeds/
uv run seeds prime                   # AI context output
uv run pytest                        # Run tests
```

## Deploy to Global CLI

How you refresh the global `seeds` command depends on how it got onto your PATH,
so check first:

```bash
which seeds
```

- **`~/.nix-profile/bin/seeds`** — nix installed it (this is the case on titan).
  Refresh from `~/.config/home-manager`: `nix flake update seeds`, then switch.
  The flake input carries no ref pin, so it tracks **main** — your changes must
  be pushed to `origin/main` before the update can see them. Don't bump it by
  editing `modules/packages.nix`.
- **`~/.local/bin/seeds`** — `uv tool` installed it. Refresh with
  `uv cache clean seeds && uv tool install --reinstall .`. `--reinstall` already
  implies `--refresh`, so no separate `uv tool uninstall` is needed.

The nix profile comes *before* `~/.local/bin` on PATH, so on a host with both, a
`uv tool install` is silently shadowed and `seeds --version` keeps reporting the
nix copy. home-manager's `modules/packages.nix` is authoritative on this and
documents the one-time fix: run `uv tool uninstall seeds` *after* a switch, to
drop a stale `~/.local/bin/seeds` left over from before the move to nix. That is
cleanup, not a step in a reinstall.

## Relationships

- **Depends on**: None
- **Feeds into**: None

## Domain Concepts

- **Seed**: An idea at any stage (captured/exploring/deferred/resolved/abandoned)
- **SeedType**: an arbitrary string. idea, question, decision, exploration and concern are the standard set, but the vocabulary is open — only `question` carries behavior. `seeds doctor` lists non-standard types; `seeds retype` remaps them.
- **Question**: First-class object attached to a seed with open/answered/deferred status
- **Hierarchical IDs**: Children use `parent-id.N` format (e.g., `seed-a1b2.1`)
- **Blocked**: A seed with unresolved children cannot be resolved
- **Store**: `.seeds/seeds/<id>.md`, one file per seed, tracked by git. There is no database and nothing to sync — a command writes the file before it returns. `docs/storage-format.md` is normative.
