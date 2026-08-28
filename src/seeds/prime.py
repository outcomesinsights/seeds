"""seeds prime command output for AI context injection."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from seeds.models import SeedStatus, SeedType

if TYPE_CHECKING:
    from seeds.db import Database
    from seeds.models import Seed


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
- Questions are seeds — `seeds ask` creates a question-type seed with a relationship
- A seed is "blocked" if it has unresolved children or unanswered question-seeds

## What to Capture (IMPORTANT)

Seeds should capture the **journey**, not just conclusions. When investigating:

**Capture DURING investigation, not just after:**
- Before running a query: jot what you're checking and why
- After findings: record what you found, with data/counts
- When user clarifies something: capture their insight verbatim

**Types of things worth capturing:**
- Data discoveries: "Checked X table, found Y has 3 records vs Z has 10M"
- Eliminated options: "Don't need feature X because data shows..."
- User insights: Direct quotes of user clarifications/decisions
- Queries/commands that revealed something important
- Assumptions that were validated or invalidated

**Bad capture:** "Decided to use CPT4/HCPCS/CDT only"
**Good capture:** "Analyzed WIDGETTYP distribution: CPT4 (13M), HCPCS (11M), CDT (121K), ICD9Proc (3 total). Found when WIDGETTYP is NULL, PROC1 is also NULL—no default needed. User clarified: 'WIDGETTYP governs generator choice, not a mapped value.'"

**Rule of thumb:** If you ran a query or the user said something insightful, capture it before moving on.

## Essential Commands

### Quick Capture
- `seeds jot "Quick thought"` - Minimal friction capture
- `seeds ask "Question?" --seed=<id>` - Attach question to seed

### Finding Work
- `seeds ready` - Captured seeds ready to explore
- `seeds questions` - Open questions needing answers
- `seeds deferred` - Review backlog
- `seeds blocked` - Seeds with unresolved children
- `seeds recent [--since=7d]` - Recently touched (any status)
- `seeds suggest "<text>"` - Rank existing seeds by relevance to a candidate item
- `seeds search '<fts5-query>'` - FTS5 keyword search

### Creating
- `seeds create --title="..." --type=idea --tags=foo,bar` - Full creation
- `seeds create --title="..." --parent=<id>` - Create child seed
- Bodies referencing unknown `<prefix>-...` IDs are rejected, base36 hash IDs included; existing seeds, beads (from a sibling `.beads/issues.jsonl`) and a short allowlist of prose terms all count as known; pass `--allow-unknown-refs` to override

### Updating
- `seeds explore <id>` - Start working on a seed
- `seeds resolve <id> --resolution="what happened"` - Mark as resolved with outcome
- `seeds defer <id>` - Move to backlog
- `seeds abandon <id> --reason="..."` - Abandon with reason
- `seeds update <id> --append="..."` - Add to content
- `seeds update <id> --content="..."` - REPLACES the whole body; refused once a seed has been edited (use `--append`, or `--replace` to discard deliberately)
- `seeds update <id> --add-tag=foo --remove-tag=bar` - Edit tags one at a time, leaving every other tag in place (both repeatable; removing a tag the seed lacks is a no-op reported as "0 removed")
- `seeds update <id> --tags=foo,bar` - REPLACES the whole tag set; cannot be combined with `--add-tag`/`--remove-tag`
- `seeds answer <seed-id> "..."` - Answer a question-seed

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
- `seeds link <id> --relates-to <other-id>` - Link seeds (default: relates-to)
- `seeds link <id> --relates-to <other-id> --type=questions` - Typed relationship

### Session End
- `seeds sync --flush-only` - Export to JSONL

### Project Prefix
Every seed ID carries a project prefix (e.g., `myproj-7`). `seeds init`
defaults the prefix to the project directory name; `seeds rename-prefix`
changes it later.

- `seeds prefix` - Show the current project prefix
- `seeds rename-prefix <new>` - Rewrite all IDs (including children +
  relationships) and ID references inside seed bodies to use a new prefix
- `seeds rename-prefix <new> --dry-run` - Preview the rename without
  writing; lists ID renames and snippet pairs for each body reference
- `seeds rename-prefix <new> --no-rewrite-bodies` - Skip rewriting ID
  references inside title/content/resolution
"""


_STATUS_ICONS = {
    SeedStatus.CAPTURED: "○",
    SeedStatus.EXPLORING: "◐",
    SeedStatus.DEFERRED: "◌",
    SeedStatus.RESOLVED: "●",
    SeedStatus.ABANDONED: "✗",
}


def _format_line(seed: Seed) -> str:
    """Render a seed as a compact one-liner for the digest."""
    icon = _STATUS_ICONS.get(seed.status, "?")
    tags = f" [{', '.join(seed.tags)}]" if seed.tags else ""
    return f"- {icon} {seed.id}: {seed.title}{tags}"


def build_digest(
    db: Database,
    *,
    limit_recent: int = 20,
    limit_tag_clusters: int = 15,
) -> str:
    """Build the project-state digest section appended to the prime output.

    Surfaces what the agent would otherwise need 3-6 discovery commands to
    rebuild: counts, recently-updated seeds, active exploration, open
    questions, and the tag-cluster shape of the project. Body content is
    intentionally omitted — agents can ``seeds show <id>`` for detail.
    """
    all_seeds = db.list_seeds(include_terminal=True)
    if not all_seeds:
        return (
            "\n## Current Seeds\n\n"
            '_Project is empty. Start with `seeds jot "first idea"`._\n'
        )

    open_seeds = [s for s in all_seeds if not s.is_terminal()]
    status_counts = Counter(s.status for s in open_seeds)

    lines: list[str] = []
    lines.append("")
    lines.append("## Current Seeds")
    lines.append("")
    lines.append(
        f"**Counts:** {len(all_seeds)} total · {len(open_seeds)} open "
        f"({status_counts[SeedStatus.CAPTURED]} captured, "
        f"{status_counts[SeedStatus.EXPLORING]} exploring, "
        f"{status_counts[SeedStatus.DEFERRED]} deferred)"
    )

    # Recently updated (any status) — only show meaningful section if there's data
    recent_seeds = db.list_seeds(include_terminal=True, sort_by="updated")[
        :limit_recent
    ]
    if recent_seeds:
        lines.append("")
        lines.append(f"### Recently Updated (top {len(recent_seeds)})")
        for seed in recent_seeds:
            lines.append(_format_line(seed))

    # Active exploration
    exploring = db.list_seeds(status=SeedStatus.EXPLORING)
    if exploring:
        lines.append("")
        lines.append(f"### Active Exploration ({len(exploring)})")
        for seed in exploring:
            lines.append(_format_line(seed))

    # Open questions (question-type, not terminal)
    open_questions = db.list_seeds(
        seed_type=SeedType.QUESTION.value, include_terminal=False
    )
    if open_questions:
        lines.append("")
        lines.append(f"### Open Questions ({len(open_questions)})")
        for seed in open_questions:
            lines.append(_format_line(seed))

    # Tag cluster summary
    tag_counts: Counter[str] = Counter()
    for seed in open_seeds:
        for tag in seed.tags:
            tag_counts[tag] += 1
    if tag_counts:
        lines.append("")
        top_tags = tag_counts.most_common(limit_tag_clusters)
        rendered = ", ".join(f"{tag} ({count})" for tag, count in top_tags)
        lines.append(f"### Top Tag Clusters\n{rendered}")

    lines.append("")
    return "\n".join(lines)


def get_prime_output(
    db: Database | None = None,
    *,
    include_digest: bool = True,
    digest_limit: int = 20,
) -> str:
    """Get the prime output for AI context injection.

    If ``db`` is supplied and ``include_digest`` is true, appends a digest
    of project state (counts, recent activity, exploration, questions, tag
    clusters) after the static workflow text. ``digest_limit`` caps the
    "Recently Updated" entries.
    """
    body = PRIME_OUTPUT.strip()
    if db is None or not include_digest:
        return body
    return body + "\n\n" + build_digest(db, limit_recent=digest_limit).lstrip("\n")
