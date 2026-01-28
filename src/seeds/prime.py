"""seeds prime command output for AI context injection."""

PRIME_OUTPUT = """# seeds Workflow Context

> **Context Recovery**: Run `seeds prime` after compaction, clear, or new session

# SESSION CLOSE PROTOCOL

**CRITICAL**: Before saying "done" or "complete", you MUST run:

```
[ ] seeds sync --flush-only    (export seeds to JSONL)
```

## Core Rules
- Use seeds to capture ideas, questions, and deliberation
- `seeds jot "..."` for quick capture during mind-racing
- Mark seeds as `deferred` when not ready to explore
- Questions are first-class - use `seeds ask` to track them
- A seed is "blocked" if it has unresolved children

## Essential Commands

### Quick Capture
- `seeds jot "Quick thought"` - Minimal friction capture
- `seeds ask "Question?" --seed=<id>` - Attach question to seed

### Finding Work
- `seeds ready` - Captured seeds ready to explore
- `seeds questions` - Open questions needing answers
- `seeds deferred` - Review backlog
- `seeds blocked` - Seeds with unresolved children

### Creating
- `seeds create --title="..." --type=idea --tags=foo,bar` - Full creation
- `seeds create --title="..." --parent=<id>` - Create child seed

### Updating
- `seeds explore <id>` - Start working on a seed
- `seeds resolve <id>` - Mark as resolved
- `seeds defer <id>` - Move to backlog
- `seeds abandon <id> --reason="..."` - Abandon with reason
- `seeds update <id> --append="..."` - Add to content
- `seeds answer <q-id> "..."` - Answer a question

### Viewing
- `seeds list` - All non-terminal seeds
- `seeds show <id>` - Detailed view
- `seeds tree <id>` - Hierarchy and relationships

### Displaying Seeds to User
Claude Code CLI truncates bash output, so users can't see full seed content from `seeds show`.

**When to display**: If user asks to see a seed, or you're about to discuss a seed together, paste the seed content in your response text so the user can see it.

**When NOT to display**: If reading seeds for your own context/understanding, no need to show the user.

**How**: Run `seeds show <id>`, then paste the output in your response. The bash output comes to you fully even if truncated on user's screen.

### Relationships
- `seeds link <id> --relates-to <other-id>` - Link seeds

### Session End
- `seeds sync --flush-only` - Export to JSONL
"""


def get_prime_output() -> str:
    """Get the prime output for AI context injection."""
    return PRIME_OUTPUT.strip()
