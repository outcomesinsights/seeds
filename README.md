# seeds

> Git-backed deliberation capture for ideas that need time to grow.

Seeds is a CLI tool for capturing thoughts, ideas, and questions with minimal friction, then tracking them through a deliberation lifecycle. Designed for developers and AI-assisted workflows where ideas need time to mature before becoming decisions.

## Quick Demo

```
$ seeds jot "What if we used event sourcing instead of CRUD?"
Created seed-a1b2: What if we used event sourcing instead of CRUD?

$ seeds ask "How would this affect our current migration strategy?" --seed seed-a1b2
Created question q-c3d4 on seed-a1b2

$ seeds explore seed-a1b2
seed-a1b2 → exploring

$ seeds create -t "Try event sourcing for the audit log first" --parent seed-a1b2 --type exploration
Created seed-a1b2.1: Try event sourcing for the audit log first

$ seeds resolve seed-a1b2.1
seed-a1b2.1 → resolved

$ seeds answer q-c3d4 "Migration can proceed independently — event sourcing only affects new writes"
Answered q-c3d4

$ seeds resolve seed-a1b2
seed-a1b2 → resolved
```

## Installation

```bash
# From GitHub
pip install git+https://github.com/outcomesinsights/seeds.git

# Or clone and install locally
git clone https://github.com/outcomesinsights/seeds.git
cd seeds
pip install .
```

Requires Python 3.11+.

## Usage

### Initialize

```bash
seeds init                              # Creates .seeds/ directory
```

### Capture

```bash
seeds jot "Quick thought"               # Minimal friction capture
seeds create -t "Title" --type idea      # Full seed creation with metadata
seeds create -t "Sub-idea" --parent <id> # Create a child seed
```

### Track

```bash
seeds list                               # List active seeds
seeds show <id>                          # Show seed details with questions
seeds tree                               # Hierarchical view
seeds ready                              # Seeds ready for attention
seeds blocked                            # Seeds blocked by unresolved children
```

### Evolve

```bash
seeds explore <id>                       # Start actively exploring
seeds defer <id>                         # Set aside for later
seeds resolve <id>                       # Mark as resolved
seeds abandon <id>                       # Decided against
seeds update <id> --type <type>          # Change a seed's type
seeds update <id> --content-file <path>  # Replace the body from a file
cmd | seeds update <id> --content -      # Replace the body from stdin
```

A body can get long, and passing one through `-c TEXT` means quoting a
multi-paragraph string on the command line — easy to truncate or mangle, and
expensive for an agent, which has to re-emit the whole body verbatim as a shell
argument. `--content-file` and `--content -` take the same body without argv.
All three are mutually exclusive, and all three respect the guard that refuses
to replace a body that has been edited since it was created (`--replace`
overrides it).

### Types

A seed's type is an arbitrary string. Seeds ships five — `idea`, `question`,
`decision`, `exploration`, `concern` — but they are a suggestion, not a
constraint: use your project's own vocabulary if it fits better. Only
`question` carries behavior (`seeds ask` / `seeds questions`).

The trade-off is that a typo becomes a new type rather than an error, so
`seeds doctor` lists any type outside the standard five, and `seeds retype`
sweeps them up:

```bash
seeds retype --from ideea --to idea      # Clean up a typo
seeds retype --from concern --to risk    # Or evolve the vocabulary
seeds retype --from x --to y --dry-run   # Preview; backs up the DB when applied
```

### Trellis

```bash
seeds trellis <id> --to <file> --as "<principle>"   # Distill a resolved seed into a durable trellis
```

### Ask Questions

```bash
seeds ask "Question?" --seed <id>        # Attach a question to a seed
seeds answer <q-id> "The answer"         # Answer a question
seeds questions                          # List open questions
```

### Connect

```bash
seeds link <id1> <id2>                   # Create bidirectional relationship
```

### Sync

`.seeds/seeds.db` is gitignored; `.seeds/seeds.jsonl` is tracked. The JSONL is
what travels between machines and through code review.

```bash
seeds sync                               # Round trip: import the JSONL, then export
seeds sync --flush-only                  # Export only, no import
seeds import                             # Rehydrate the database from the JSONL
seeds import -                           # Read JSONL from stdin
seeds doctor                             # Check DB and JSONL agree (exits non-zero if not)
```

**On a fresh clone you have the JSONL and no database** — that is the normal
state, not a broken one. Run `seeds import` to rebuild the database from it;
the schema and the project prefix are both recovered from the file.

`seeds sync` refuses rather than overwrite a record on disk the database has
never seen — a merge resolution, a hand edit, or a peer's seed. Read what it
names and fold the content in; `--allow-divergence` skips the check and
destroys that content.

A record the import cannot read no longer stops the file. Each bad record is
refused **individually** and named — its record number, id, failing field and
reason — while every other record imports, and the command exits non-zero so a
script notices. This matters because the old behaviour aborted where it stood:
records above a bad line landed, records below it silently did not, and nothing
said so. `seeds doctor` reports refusable records too, so the state is
discoverable before an import is ever run.

### AI Context

```bash
seeds prime                              # Output context for AI agents
```

## Trellises

A **trellis** is a durable principle that future work is *trained along* — a load-bearing but gentle guide (one crisp, bounded line) that stays in front of every future session. `seeds trellis` distills a matured or resolved seed into such a principle and writes it, with a two-way provenance link, into always-on project context (`CLAUDE.md`, `AGENTS.md`, or the README), then resolves the seed. The point is *placement*: a trellis lands in the context your agent runtime injects every session, so it shapes what grows next without anyone re-explaining it.

```bash
seeds trellis <id> --to CLAUDE.md --as "a code set has exactly one vocabulary ID"
```

Under the hood this appends a provenance-stamped bullet under a managed `## Principles` section of the target file, tags the seed `trellis`, records the back-link in the seed's resolution, and resolves it (pass `--no-resolve` to keep deliberating). Reach for this **sparingly** — only when a deliberation has settled into a genuinely load-bearing, *bounded* principle, not for everyday seeds. Keep the line scoped ("a code set has exactly one vocabulary ID"), never an open-ended imperative ("respect deprecations and move forward"), because a trellis line is read as a hard rule every session. In [Claude Code](https://claude.com/claude-code), saying **"trellis this"** or **"make this a trellis"** fires the bundled `seeds:trellis` skill, which walks the deliberation, helps you distill the one line, and runs `seeds trellis` for you.

## Status

**Beta.** Seeds is under active development. The core workflow (capture, explore, resolve) is stable. The CLI interface may evolve.

## Claude Code Skills

Seeds ships a small set of skills for use with [Claude Code](https://claude.com/claude-code), distributed as a local plugin. After installing the seeds CLI, run:

```bash
seeds skills install
```

This registers the bundled marketplace and installs the `seeds` plugin under the `seeds:*` namespace.

### Available skills

- **`seeds:feedback`** — frames the next user message as feedback on the agent's prior turn and invites the agent to follow up with its own questions, comments, or criticisms. Useful during deliberation when you want the agent to push back rather than just execute.
- **`seeds:seeds-to-beads`** — frames the user's request as "convert these seeds into beads" and applies the agreed seeds-to-beads conversion principles (separating action from context, mechanically checkable acceptance criteria, etc.) for that one reply. By default it stops and asks you about decisions the deliberation left open before writing the bead that depends on them; pass `--autonomous` to convert in one pass, with each such call recorded in the bead as an explicit assumption.
- **`seeds:trellis`** — fires when you say "trellis this" or "make this a trellis"; distills the seed's deliberation into one bounded principle and writes it into durable context via `seeds trellis`.

Re-run `seeds skills install` after upgrading the seeds CLI to pick up updated skill content.

## Acknowledgments

Seeds was inspired by Steve Yegge's [beads](https://github.com/steveyegge/beads) project and its core insight: giving AI agents structured tools improves how agents work, bridges AI-human communication, and unlocks AI potential not accessible through unstructured conversation alone.

## Contributing

Issues and pull requests are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE)
