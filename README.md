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

Requires Python 3.9+.

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

### Export

```bash
seeds sync --flush-only                  # Export to .seeds/seeds.jsonl (git-trackable)
```

### AI Context

```bash
seeds prime                              # Output context for AI agents
```

## Status

**Beta.** Seeds is under active development. The core workflow (capture, explore, resolve) is stable. The CLI interface may evolve.

## Web UI (Experimental)

Seeds includes an experimental web interface for browsing your seeds:

```bash
seeds serve                              # Starts on http://localhost:53365
```

This provides read-only views of your seeds, questions, and their relationships.

## Acknowledgments

Seeds was inspired by Steve Yegge's [beads](https://github.com/steveyegge/beads) project and its core insight: giving AI agents structured tools improves how agents work, bridges AI-human communication, and unlocks AI potential not accessible through unstructured conversation alone.

## Contributing

Issues and pull requests are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE)
