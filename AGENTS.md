# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd dolt push          # Send beads to the Dolt remote (`bd sync` is retired)
```

## Landing the Plane (Session Completion)

**Landing the plane here means COMMITTING, not pushing.** This section shipped as
beads boilerplate demanding a push at the end of every session; that is wrong for
this repo and was corrected on 2026-09-23.

**Do not `git push` unless you were explicitly asked to.** CI on this repo runs a
Python matrix and a nix build on every push, those minutes are billed, and whether
work is ready to leave this machine is the maintainer's call and not an agent's.
Local commits are not "stranded" — they are the normal resting state here.

**When ending a work session:**

1. **File issues for remaining work** — anything that needs follow-up
2. **Run the quality gate** (if code changed) — `just ci`, which is the full local
   CI equivalent: lock check, ruff lint, mypy, formatting, flake deps, pytest
3. **Update issue status** — close finished work, update in-progress items
4. **Commit** — a clean tree is the deliverable; leave the push to the maintainer
5. **Hand off** — say plainly what is committed, what is unpushed, and what is left

If you believe a push is genuinely needed, say so and let the maintainer decide.

<!-- BEGIN BEADS INTEGRATION -->

## Issue Tracking with bd (beads)

**IMPORTANT**: This project uses **bd (beads)** for ALL issue tracking. Do NOT use markdown TODOs, task lists, or other tracking methods.

### Why bd?

- Dependency-aware: Track blockers and relationships between issues
- Git-friendly: beads travel on a git-backed Dolt remote (`refs/dolt/data`)
- Agent-optimized: JSON output, ready work detection, discovered-from links
- Prevents duplicate tracking systems and confusion

### Quick Start

**Check for ready work:**

```bash
bd ready --json
```

**Create new issues:**

```bash
bd create "Issue title" --description="Detailed context" -t bug|feature|task -p 0-4 --json
bd create "Issue title" --description="What this issue is about" -p 1 --deps discovered-from:bd-123 --json
```

**Claim and update:**

```bash
bd update bd-42 --status in_progress --json
bd update bd-42 --priority 1 --json
```

**Complete work:**

```bash
bd close bd-42 --reason "Completed" --json
```

### Issue Types

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Workflow for AI Agents

1. **Check ready work**: `bd ready` shows unblocked issues
2. **Claim your task**: `bd update <id> --status in_progress`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   - `bd create "Found bug" --description="Details about what was found" -p 1 --deps discovered-from:<parent-id>`
5. **Complete**: `bd close <id> --reason "Done"`

### Sync

Beads live in a per-repo embedded Dolt database and travel on a **git-backed Dolt
remote at `refs/dolt/data`** — a non-branch ref, so it is invisible to
`git ls-files`, to the GitHub web UI, and to a default clone. To see whether a repo
has it you must ask the remote directly:

```bash
git ls-remote origin 'refs/dolt/*'     # NOT `git for-each-ref`, which lies here
bd dolt push                           # send local beads
bd dolt pull                           # receive
```

**JSONL is not a sync channel** (ruled 2026-09-13): not sync, not a backstop, not
disaster recovery. Do not export it, do not commit it, and do not add a hook that
maintains it. A `.beads/issues.jsonl` you find in a repo is a frozen leftover —
measured here on 2026-09-23, this repo's held 175 beads against `bd`'s 183, missing
every bead created since the export stopped.

Nothing drives the push on its own. Something must run `bd dolt push` — a pre-push
gate, a `just` recipe, or you.

### Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Always use `--json` flag for programmatic use
- ✅ Link discovered work with `discovered-from` dependencies
- ✅ Check `bd ready` before asking "what should I work on?"
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT use external issue trackers
- ❌ Do NOT duplicate tracking systems

For more details, see README.md and docs/QUICKSTART.md.

<!-- END BEADS INTEGRATION -->
