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

Requires Python 3.11+ and [ripgrep](https://github.com/BurntSushi/ripgrep)
(`rg`) on `PATH` — `seeds search` is a ripgrep pass over the seed files. Every
other command works without it, and `seeds search` says so rather than failing
obscurely. The Nix package wraps the binary with its own ripgrep, so `nix run`
needs nothing installed.

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
seeds show <id> --full                   # ...including superseded text
seeds tree                               # Hierarchical view
seeds ready                              # Seeds ready for attention
seeds blocked                            # Seeds blocked by unresolved children
seeds search "<regex>"                   # ripgrep over the seed files
seeds history <id>                       # How this seed changed, commit by commit
```

`seeds show` renders **live** content: text inside a superseded scope is
dropped, while the retired heading and its `> [!SUPERSEDED]` marker line stay,
so you can see that a position was moved past and why. `--full` prints
everything. Nothing is removed from the file either way — the render is what is
selective.

`seeds history` reads a seed's evolution out of git: one line per commit in
which the seed actually changed, giving the date, the author, the fields that
differ from the previous revision, and the commit subject. It **structures and
labels; it never summarises** — naming which fields changed is deterministic and
every line is checkable against `git show`, while saying what a change *meant*
is a reading, and that one is yours to make.

A seed older than the conversion to the seed-file store has its history in two
places, and both are walked as one chain: its own `.seeds/seeds/<id>.md` back to
the conversion commit, and `.seeds/seeds.jsonl` before it. **That file stops
being written on conversion day, but its git history stays load-bearing forever
— never filter it out of the repository as cleanup.**

`seeds search` is a ripgrep pass over `.seeds/seeds/`, case-insensitive, with
the resolved/abandoned filter inline (`--all` includes them). The query is an
ordinary regular expression, so hyphens, quotes and punctuation are literal.
There is no stemmer, so search for the stem: `merg` finds both `merge` and
`merging`.

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
seeds retype --from x --to y --dry-run   # Preview before applying
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

### Storage

**A seed is a file.** Each one lives at `.seeds/seeds/<id>.md` — YAML
frontmatter, then a markdown body — and those files are tracked by git like any
other source. The filename stem is the id verbatim, so `seeds show` is one path
computation and one file read. The project prefix lives beside them in a tracked
`.seeds/config.yaml`. The full normative description is
[docs/storage-format.md](docs/storage-format.md).

There is nothing to sync, export, or flush. A command writes the file before it
returns; commit it like a code change.

```bash
seeds check                              # Verify the files (exits non-zero on a violation)
seeds check --smells                     # ...plus advisory findings that never gate
seeds doctor                             # Installation and store health
seeds export --json                      # The whole corpus as JSONL on stdout
```

For machine consumers, `seeds export --json` is a pipe rather than a tracked
file — one JSON object per line, so a `grep` hit is a whole record and several
repos' output concatenates into one stream:

```bash
seeds export --json | duckdb -c "SELECT status, count(*)
  FROM read_json_auto('/dev/stdin') GROUP BY 1"
```

#### Converting a pre-0.7 project

Projects created before 0.7 hold a gitignored `.seeds/seeds.db` and a tracked
`.seeds/seeds.jsonl`. Run `seeds convert` once:

```bash
seeds convert                            # SQLite + JSONL -> .seeds/seeds/*.md
```

It reads the UNION of the two stores, per id and per field, and writes the tree
alongside them without touching either — reverting the whole conversion is `rm
-rf .seeds/seeds/`. Where the two stores genuinely disagree, the seed lands with
git conflict markers for ordinary merge tooling, and the command exits non-zero
until a human resolves it.

`.seeds/seeds.jsonl` stops being written on conversion day but **must never be
deleted or filtered out of the repository**: its git history is the only source
for anything before a seed's `converted_at`.

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
