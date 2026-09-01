"""seeds prime command output for AI context injection.

**The unconverted repo is a first-class case here** (bead seeds-4co.18).
Conversion is on-demand -- repos are converted the first time someone uses
seeds in them -- so there is no migration guide and no batch tool, and what an
agent is handed at first contact *is* the migration experience.

Every other data-touching command refuses and names ``seeds convert``. prime
could not: the static half of this document rendered perfectly, the live-state
block was silently absent, and nothing on screen said a block was missing. An
agent has no reason to suspect it and concludes the project has no seeds. The
one measured example had 29.

@aguynamedryan ruled that prime must NOT abort: aborting would be doubly wrong,
because the agent loses the verbs *and* stays uninformed. So the fix is in the
text, in two places, and the placement is the point:

* :data:`CONVERSION_BANNER` at the very top, because a long context is read
  top-down and is sometimes truncated before the end;
* :data:`CONVERSION_NOTICE` **where the state block would have been**, so the
  absence is explained at the point of absence rather than in a footnote after
  the reader has already formed a picture.

And prime keeps **exit 0**. It produced usable output, and it is consumed as
text through hooks, so the signal belongs in the text rather than in a status a
hook would trip over.

Deliberately NOT done: reading the legacy store to report how many seeds are
waiting. That was asked for and declined. This module imports no SQLite and no
legacy reader -- :mod:`seeds.convert` stays the only caller of
:mod:`seeds.legacy`. The notice says state is unavailable, says nothing is
lost, and names the command.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from seeds.models import SeedStatus, SeedType
from seeds.store import is_terminal

if TYPE_CHECKING:
    from seeds.seedfile import SeedRecord
    from seeds.store import Store


PRIME_OUTPUT = """# seeds Workflow Context

> **Context Recovery**: Run `seeds prime` after compaction, clear, or new session

# SESSION CLOSE PROTOCOL

**CRITICAL**: Before saying "done" or "complete", you MUST run:

```
[ ] seeds check                (verify the seed files you wrote)
```

There is no export step. A seed IS its file at `.seeds/seeds/<id>.md`, written
the moment the command returns — nothing is buffered and nothing needs
flushing. Commit those files like any other source change.

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
- `seeds search '<regex>'` - ripgrep over the seed files (case-insensitive; no stemming, so search for the stem: `merg` finds both `merge` and `merging`)

### Searching Across Repos (use ripgrep directly — there is no seeds verb)

A seed is a markdown file, so searching *many* projects at once is one glob over
their stores. Use this recipe; do not invent a shell loop, and do not read
`.seeds/seeds.jsonl` — it is retired, and stale wherever it still exists.

```
rg -l "adjudicat" ~/projects/*/.seeds/seeds/          # which repos mention it
rg -i -C2 "immutable row" ~/projects/*/.seeds/seeds/  # with context lines
```

The seed id is in the file path and you get real context, which is strictly
better than the 120-character slice of one escaped line that grepping the
retired JSONL used to return. Substitute the directory that holds the projects
you mean (a habitat's root, `~/projects/<org>/`, or `..` from a sibling repo).

### Creating
- `seeds create --title="..." --type=idea --tags=foo,bar` - Full creation
- `seeds create --title="..." --parent=<id>` - Create child seed
- Bodies referencing unknown `<prefix>-...` IDs are rejected, base36 hash IDs included; existing seeds, beads and a short allowlist of prose terms all count as known; pass `--allow-unknown-refs` to override
- Bead IDs are checked against a sibling `.beads/issues.jsonl`, and anything it does not vouch for is confirmed with `bd` itself before being called unknown -- that export is throttled, so a bead created seconds ago is real and missing from it

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
- `seeds show <id>` - Detailed view; the body renders live content, with superseded text dropped and its heading + marker line kept
- `seeds show <id> --full` - Detailed view including superseded text
- `seeds tree <id>` - Hierarchy and relationships
- `seeds history <id>` - How the seed changed, one line per commit: date, author, changed fields, subject. Structures and labels; never summarises, so the reading is yours
- `seeds export --json` - The whole corpus as JSONL on stdout, for STRUCTURED extraction (pipe it into DuckDB and query it as a table). For text search across repos, use the rg recipe above instead

### Displaying Seeds to User
Claude Code CLI truncates bash output, so users can't see full seed content from `seeds show`.

**When to display**: If user asks to see a seed, or you're about to discuss a seed together, paste the seed content in your response text so the user can see it.

**When NOT to display**: If reading seeds for your own context/understanding, no need to show the user.

**How**: Run `seeds show <id>`, then paste the output in your response. The bash output comes to you fully even if truncated on user's screen.

### Relationships
- `seeds link <id> --relates-to <other-id>` - Link seeds (default: relates-to)
- `seeds link <id> --relates-to <other-id> --type=questions` - Typed relationship

### Session End
- `seeds check` - Verify the seed files; exits non-zero on a violation

### Project Prefix
Every seed ID carries a project prefix (e.g., `myproj-7`), recorded in
`.seeds/config.yaml`. `seeds init` defaults the prefix to the project
directory name; `seeds rename-prefix` changes it later.

- `seeds prefix` - Show the current project prefix
- `seeds rename-prefix <new>` - Rewrite all IDs (including children +
  relationships), rename the seed files, and rewrite ID references inside
  seed bodies to use a new prefix
- `seeds rename-prefix <new> --dry-run` - Preview the rename without
  writing; lists ID renames and snippet pairs for each body reference
- `seeds rename-prefix <new> --no-rewrite-bodies` - Skip rewriting ID
  references inside title/body/resolution
"""


CONVERSION_BANNER = """\
> **⚠ THIS PROJECT'S SEED STORE IS OUT OF DATE — run `seeds convert` first.**
> `.seeds/` still holds the pre-0.7 `seeds.jsonl` and no `.seeds/seeds/` tree.
> Every command below that reads or writes seed data will refuse until the
> conversion is run. **Existing seeds are NOT lost**, and the project-state
> section at the end of this document is missing for that reason and no other."""

CONVERSION_NOTICE = """\
## Current Seeds

**Unavailable — this project has not been converted to the seed-file store.**

`.seeds/seeds.jsonl` is present and `.seeds/seeds/` is not, so the block that
normally goes here — counts, recently updated, active exploration, open
questions, tag clusters — could not be built.

**Do not read that absence as "this project has no seeds."** Nothing has been
lost and nothing has been read: this command deliberately does not open the
pre-0.7 store, so it cannot even tell you how many seeds are waiting.

Recovery, once, in this repo:

```
seeds convert    # then re-run `seeds prime`
```"""


_STATUS_ICONS = {
    SeedStatus.CAPTURED: "○",
    SeedStatus.EXPLORING: "◐",
    SeedStatus.DEFERRED: "◌",
    SeedStatus.RESOLVED: "●",
    SeedStatus.ABANDONED: "✗",
}


def _format_line(record: SeedRecord) -> str:
    """Render a seed as a compact one-liner for the digest."""
    icon = _STATUS_ICONS.get(record.status, "?")
    tags = f" [{', '.join(record.tags)}]" if record.tags else ""
    return f"- {icon} {record.id}: {record.title}{tags}"


def build_digest(
    store: Store,
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
    all_seeds = store.list_seeds(include_terminal=True)
    if not all_seeds:
        return (
            "\n## Current Seeds\n\n"
            '_Project is empty. Start with `seeds jot "first idea"`._\n'
        )

    open_seeds = [s for s in all_seeds if not is_terminal(s)]
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
    recent_seeds = store.list_seeds(include_terminal=True, sort_by="updated")[
        :limit_recent
    ]
    if recent_seeds:
        lines.append("")
        lines.append(f"### Recently Updated (top {len(recent_seeds)})")
        for seed in recent_seeds:
            lines.append(_format_line(seed))

    # Active exploration
    exploring = store.list_seeds(status=SeedStatus.EXPLORING)
    if exploring:
        lines.append("")
        lines.append(f"### Active Exploration ({len(exploring)})")
        for seed in exploring:
            lines.append(_format_line(seed))

    # Open questions (question-type, not terminal)
    open_questions = store.list_seeds(
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
    store: Store | None = None,
    *,
    include_digest: bool = True,
    digest_limit: int = 20,
    unconverted: bool = False,
) -> str:
    """Get the prime output for AI context injection.

    If ``store`` is supplied and ``include_digest`` is true, appends a digest
    of project state (counts, recent activity, exploration, questions, tag
    clusters) after the static workflow text. ``digest_limit`` caps the
    "Recently Updated" entries.

    ``unconverted`` wraps the static text in the two-part conversion notice
    instead — see the module docstring on why it is two parts and why this
    still returns a full, usable document.
    """
    body = PRIME_OUTPUT.strip()
    if unconverted:
        return f"{CONVERSION_BANNER}\n\n{body}\n\n{CONVERSION_NOTICE}"
    if store is None or not include_digest:
        return body
    return body + "\n\n" + build_digest(store, limit_recent=digest_limit).lstrip("\n")
