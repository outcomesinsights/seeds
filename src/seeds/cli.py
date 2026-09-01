"""seeds CLI entry point."""

from __future__ import annotations

import functools
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, NamedTuple

import click

from seeds import __version__
from seeds.beads import load_bead_ids
from seeds.check import check_violations, format_findings
from seeds.db import SEEDS_DIR, Database, find_seeds_dir
from seeds.export import (
    JSONL_FILE,
    DivergentExportError,
    ImportResult,
    RefusedRecord,
)
from seeds.models import (
    DEFAULT_PREFIX,
    RelationType,
    Seed,
    SeedStatus,
    SeedType,
    find_id_ref_candidates,
    is_allowlisted_prose,
    parse_since,
    sanitize_prefix,
)
from seeds.seedfile import seed_files_dir


def _uninitialized_error(db_path: Path) -> str:
    """The right recovery to name when there is no database.

    Three states hide behind "no seeds.db", and sending all of them to `seeds
    init` is wrong for the most common one. `.seeds/seeds.db` is gitignored
    while `seeds.jsonl` is tracked, so a fresh clone has the file and not the
    database -- and `seeds init` refuses there, reporting the directory as
    already initialized. That closed loop is what this exists to break
    (bead seeds-1j3).
    """
    seeds_dir = db_path.parent
    if not seeds_dir.exists():
        return "Error: seeds not initialized. Run 'seeds init' first."

    jsonl_path = seeds_dir / JSONL_FILE
    if jsonl_path.exists():
        return (
            f"Error: no database, but {jsonl_path} is present.\n"
            "Run 'seeds import' to rehydrate it (the fresh-clone path -- the "
            "database is gitignored, the JSONL is tracked)."
        )
    return "Error: seeds not initialized. Run 'seeds init' first."


class Context:
    """CLI context object holding database connection."""

    def __init__(self) -> None:
        self.db: Database | None = None

    def get_db(self, bootstrap: bool = False) -> Database:
        """Get database, initializing if needed.

        By default, exits with an error when the DB file is absent (seeds not
        initialized). Pass ``bootstrap=True`` to bypass that guard and return
        the (uninitialized) ``Database`` so an import caller can create the
        schema and recover the prefix from JSONL itself — the fresh-clone
        rehydration path, where ``.seeds/seeds.jsonl`` exists but the gitignored
        DB does not. The caller is responsible for actually bootstrapping
        (e.g. ``import_from_jsonl(db, bootstrap=True)``).
        """
        if self.db is None:
            self.db = Database()
            if not bootstrap and not self.db.is_initialized():
                click.echo(_uninitialized_error(self.db.path), err=True)
                sys.exit(1)
        return self.db

    def ensure_init(self) -> Database:
        """Ensure database is initialized, error if not."""
        return self.get_db()


pass_context = click.make_pass_decorator(Context, ensure=True)


def _validate_id_refs(
    db: Database, texts: list[str | None], allow_unknown: bool
) -> None:
    """Verify every project-prefixed token in ``texts`` names something real.

    Catches the common failure where an agent drafts a body like
    ``see seeds-117`` — or, now that IDs are base36, ``see seeds-zq4x`` — with
    an ID that never existed. Each ``<prefix>-…`` token is a candidate, checked
    in turn against:

    1. **seed IDs** — the database;
    2. **bead IDs** — the sibling ``.beads/`` export, since beads share the
       project prefix and recording bead lineage in a seed is a supported
       workflow, not a hallucination (projects without beads are unaffected;
       see :mod:`seeds.beads`);
    3. **prose** — :data:`~seeds.models.PROSE_REF_ALLOWLIST`, because
       ``<prefix>-<word>`` is ordinary English ("a seeds-native workflow") and
       no rule of shape separates it from a base36 hash.

    Anything still unmatched is a hallucination: exit with an error listing it,
    unless ``allow_unknown`` is true.
    """
    if allow_unknown:
        return
    prefix = db.get_prefix()
    candidates: set[str] = set()
    for text in texts:
        if not text:
            continue
        candidates.update(find_id_ref_candidates(text, prefix))
    if not candidates:
        return
    bead_ids = load_bead_ids(db.path.parent)
    unknown = sorted(
        ref
        for ref in candidates
        if db.get_seed(ref) is None
        and ref not in bead_ids
        and not is_allowlisted_prose(ref, prefix)
    )
    if unknown:
        click.echo(
            "Error: seed body references unknown IDs: " + ", ".join(unknown),
            err=True,
        )
        click.echo(
            "  Fix the references, or pass --allow-unknown-refs to override.",
            err=True,
        )
        click.echo(
            "  If one is prose rather than an ID, add its suffix to"
            " PROSE_REF_ALLOWLIST in seeds/models.py.",
            err=True,
        )
        sys.exit(1)


class GuardCopy(NamedTuple):
    """The caller-specific half of :func:`_guard_content_replacement`'s refusal.

    Every field is required and there is deliberately **no default**. The
    defect this type exists to prevent was a second caller silently inheriting
    the first caller's prose: ``answer`` reused the guard and was handed
    ``update``'s remediation, which told the user to pass a ``--content`` flag
    that ``answer`` does not have. A default set to either caller's wording
    would reintroduce exactly that, and the next caller would ship the same bug
    again -- so adding a caller has to mean stating its own remediation.

    The rule the two shipped instances of this bug share: **the remediation a
    command prints must be a command that works for THAT command.** Assert it.
    """

    reason: str
    """Why the seed is protected, as a predicate: "has already been answered"."""

    subject: str
    """What would do the discarding: ``--content``, or "answering again"."""

    append_cmd: str
    """A ready-to-paste command that adds to the body instead of replacing it."""

    replace_cmd: str
    """A ready-to-paste command that discards the body on purpose."""


def _guard_content_replacement(seed: Seed, copy: GuardCopy) -> None:
    """Refuse a wholesale body replacement that would discard accumulated thinking.

    ``-c`` sits one keystroke from ``-a`` and replaces the whole body without
    warning, which for a deliberation store is a sharp edge pointed at the
    thing being kept. The gate is whether deliberation *exists*, never how much
    of it there is: a short seed refined over a week deserves more protection
    than a long one mispasted ten seconds ago.

    A seed still carrying its creation timestamp has never been added to, so
    the replacement proceeds silently -- that is the botched-capture and
    encoding-repair case. So does a seed with an empty body, where there is
    nothing to lose. Anything else exits non-zero; ``--replace`` is the
    deliberate override.

    The *decision* above is shared by every caller; the *prose* is not, and
    arrives in ``copy``. See :class:`GuardCopy` for why that is mandatory
    rather than defaulted.
    """
    if not seed.content.strip() or not seed.has_been_edited():
        return

    first_line = seed.content.strip().splitlines()[0]
    if len(first_line) > 72:
        first_line = first_line[:69] + "..."

    click.echo(
        f"Error: {seed.id} {copy.reason} -- {copy.subject} "
        f"would discard {len(seed.content)} characters of deliberation.",
        err=True,
    )
    click.echo(f"  Would discard: {first_line}", err=True)
    click.echo(f"  Add to it instead:      {copy.append_cmd}", err=True)
    click.echo(f"  Discard it on purpose:  {copy.replace_cmd}", err=True)
    click.echo(
        "  --replace does not erase anything: the old body survives in git "
        "history (.seeds/seeds.jsonl) and needs separate scrubbing.",
        err=True,
    )
    sys.exit(1)


def _clean_tags(raw: Sequence[str]) -> list[str]:
    """Strip and de-duplicate requested tags, preserving the order given.

    Blanks are dropped rather than rejected: ``--add-tag ''`` then shows up as
    "0 added" like any other request that changed nothing.
    """
    return list(dict.fromkeys(t.strip() for t in raw if t.strip()))


def _reject_ambiguous_tag_flags(
    tags: str | None, add: Sequence[str], remove: Sequence[str]
) -> None:
    """Refuse tag flag combinations whose intent cannot be read off the command.

    Two shapes are ambiguous and both exit non-zero before anything is written:
    ``--tags`` (which replaces the whole set) alongside either additive flag,
    and the same tag passed to both ``--add-tag`` and ``--remove-tag``. Picking
    a precedence order for either would just make the surprise silent, which is
    the failure this pair of flags exists to remove.
    """
    if tags is not None and (add or remove):
        click.echo(
            "Error: --tags replaces the whole tag set, so combining it with "
            "--add-tag/--remove-tag is ambiguous.",
            err=True,
        )
        click.echo("  Reset the set, or edit it -- run them as two commands.", err=True)
        sys.exit(1)

    both = [t for t in _clean_tags(add) if t in set(_clean_tags(remove))]
    if both:
        click.echo(
            "Error: tag(s) passed to both --add-tag and --remove-tag: "
            + ", ".join(both),
            err=True,
        )
        sys.exit(1)


STDIN_SENTINEL = "-"
"""``--content -``: read the new body from stdin rather than from argv."""


def _resolve_content(content: str | None, content_file: str | None) -> str | None:
    """Collapse ``--content``/``--content-file`` into the single body to store.

    A body worth protecting is a body nobody wants in argv. Folding a
    divergence means reproducing the whole existing text verbatim as one shell
    word -- for an agent, reading it into context and re-emitting it, roughly
    twice the body in tokens, where a truncation or a mangled quote corrupts
    deliberation without saying so. So the same text can arrive from a file, or
    on stdin.

    Stdin is the sentinel ``-`` on the EXISTING ``--content`` option rather
    than a third flag: where the body came from is not a different kind of
    update. ``--content-file -`` is refused for the same reason -- one spelling
    for stdin, not two.

    Combining the two options is refused rather than resolved by a precedence
    rule, matching :func:`_reject_ambiguous_tag_flags`: a silent winner is the
    surprise, not the error.

    A trailing newline is dropped, because every editor and ``>`` redirect adds
    one and ``-c TEXT`` never carries one -- keeping it would make the same
    body differ by its delivery route. Returns ``None`` when neither option was
    passed (body untouched); an empty file or empty stdin returns ``""``, a
    deliberate blanking that still has to clear the guard.
    """
    if content is not None and content_file is not None:
        click.echo(
            "Error: --content and --content-file both supply the new body, so "
            "passing both is ambiguous.",
            err=True,
        )
        click.echo(
            "  Pick one: -c TEXT, --content-file PATH, or --content - for stdin.",
            err=True,
        )
        sys.exit(1)

    if content_file == STDIN_SENTINEL:
        click.echo(
            "Error: --content-file takes a path; read stdin with --content -.",
            err=True,
        )
        sys.exit(1)

    if content_file is not None:
        path = Path(content_file)
        if not path.is_file():
            click.echo(
                f"Error: --content-file: not a readable file: {content_file}",
                err=True,
            )
            sys.exit(1)
        return path.read_text(encoding="utf-8").rstrip("\n")

    if content == STDIN_SENTINEL:
        return sys.stdin.read().rstrip("\n")

    return content


def _apply_tag_edits(seed: Seed, add: Sequence[str], remove: Sequence[str]) -> str:
    """Add/remove individual tags in place; return a report of what happened.

    Removals run first and additions append to the tail, so tags the command
    did not name keep their authored positions -- re-sorting would churn the
    ``.seeds/seeds.jsonl`` diff of every touched seed for no reason.

    Naming a tag the seed does not carry (or one it already has) is a silent
    no-op, per the locked decision on this command: with an agent driving a
    batch, erroring mid-loop is worse than finishing. The counts are what
    actually happened, so a typo lands as "0 removed" rather than vanishing.
    """
    to_add = _clean_tags(add)
    to_remove = _clean_tags(remove)

    removed = sum(1 for t in to_remove if t in seed.tags)
    if to_remove:
        drop = set(to_remove)
        seed.tags = [t for t in seed.tags if t not in drop]

    added = 0
    for tag in to_add:
        if tag not in seed.tags:
            seed.tags.append(tag)
            added += 1

    return f"Tags: {added} added, {removed} removed"


def require_init(f: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to require seeds to be initialized."""

    @functools.wraps(f)
    @click.pass_context
    def wrapper(click_ctx: click.Context, *args: Any, **kwargs: Any) -> Any:
        ctx = click_ctx.ensure_object(Context)
        ctx.ensure_init()
        return click_ctx.invoke(f, *args, **kwargs)

    return wrapper


@click.group()
@click.version_option(version=__version__, prog_name="seeds")
@click.pass_context
def main(ctx: click.Context) -> None:
    """seeds: Git-backed deliberation capture for ideas that need time to grow."""
    ctx.ensure_object(Context)


@main.command()
@click.option(
    "--prefix",
    "prefix",
    default=None,
    help=(
        "Project prefix for seed IDs (e.g., 'myproj' → myproj-1). "
        "Defaults to the current directory name, lowercased and hyphenated."
    ),
)
def init(prefix: str | None) -> None:
    """Initialize seeds in the current directory."""
    seeds_dir = Path.cwd() / SEEDS_DIR
    if seeds_dir.exists():
        # The directory existing is not the same as the project being usable.
        # Only the database settles that, and it is the gitignored half.
        if Database().is_initialized():
            click.echo(f"seeds already initialized in {seeds_dir}")
            return
        jsonl_path = seeds_dir / JSONL_FILE
        if jsonl_path.exists():
            click.echo(
                f"{seeds_dir} exists but holds no database, and "
                f"{jsonl_path.name} is present."
            )
            click.echo("Run 'seeds import' to rehydrate it.")
            return
        # An empty .seeds/ with nothing to rehydrate from: carry on and
        # initialize, rather than refusing over a bare directory.

    if prefix is None:
        derived = sanitize_prefix(Path.cwd().name)
        if not derived:
            click.echo(
                f"Warning: could not derive a valid prefix from "
                f"directory name {Path.cwd().name!r}; using {DEFAULT_PREFIX!r}. "
                f"Use --prefix to set explicitly.",
                err=True,
            )
            derived = DEFAULT_PREFIX
        prefix = derived
    else:
        sanitized = sanitize_prefix(prefix)
        if not sanitized:
            click.echo(
                f"Error: invalid prefix {prefix!r}. Must start with a "
                "lowercase letter and contain only lowercase letters, digits, "
                "and hyphens.",
                err=True,
            )
            sys.exit(1)
        prefix = sanitized

    db = Database()
    db.init(prefix=prefix)
    click.echo(f"Initialized seeds in {seeds_dir}")
    click.echo(f"  Project prefix: {prefix}")
    click.echo("  .seeds/.gitignore created (SQLite ignored, JSONL tracked)")
    click.echo("Run 'seeds jot \"Your first idea\"' to capture a thought.")


# Valid seed types for CLI
SEED_TYPES = [t.value for t in SeedType]


@main.command()
@click.option("--title", "-t", required=True, help="Title of the seed")
@click.option("--content", "-c", default="", help="Full content/description")
@click.option(
    "--type",
    "seed_type",
    default="idea",
    help=f"Type of seed (any value; standard: {', '.join(SEED_TYPES)})",
)
@click.option("--tags", help="Comma-separated tags")
@click.option("--parent", "parent_id", help="Parent seed ID for hierarchical grouping")
@click.option(
    "--allow-unknown-refs",
    is_flag=True,
    help="Skip validation of seed-ID cross-references in title/content",
)
@pass_context
def create(
    ctx: Context,
    title: str,
    content: str,
    seed_type: str,
    tags: str | None,
    parent_id: str | None,
    allow_unknown_refs: bool,
) -> None:
    """Create a new seed."""
    db = ctx.get_db()

    # Generate ID (child ID if parent specified)
    if parent_id:
        # Verify parent exists
        parent = db.get_seed(parent_id)
        if parent is None:
            click.echo(f"Error: Parent seed '{parent_id}' not found.", err=True)
            sys.exit(1)
        seed_id = db.get_next_child_id(parent_id)
    else:
        seed_id = db.next_id(seed_text=title)

    _validate_id_refs(db, [title, content], allow_unknown_refs)

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    seed = Seed(
        id=seed_id,
        title=title,
        content=content,
        seed_type=seed_type,
        tags=tag_list,
    )

    db.create_seed(seed)
    click.echo(f"Created seed: {seed_id}")
    click.echo(f"  Title: {title}")
    if parent_id:
        click.echo(f"  Parent: {parent_id}")


@main.command()
@click.argument("thought")
@pass_context
def jot(ctx: Context, thought: str) -> None:
    """Quickly capture a thought with minimal friction.

    THOUGHT is the idea to capture (becomes the title).
    """
    db = ctx.get_db()

    seed_id = db.next_id(seed_text=thought)
    seed = Seed(id=seed_id, title=thought)

    db.create_seed(seed)
    click.echo(f"{seed_id}: {thought}")


# Valid statuses for CLI
SEED_STATUSES = [s.value for s in SeedStatus]


def format_seed_line(seed: Seed, db: Database) -> str:
    """Format a seed for list output."""
    status_icon = {
        SeedStatus.CAPTURED: "○",
        SeedStatus.EXPLORING: "◐",
        SeedStatus.DEFERRED: "◌",
        SeedStatus.RESOLVED: "●",
        SeedStatus.ABANDONED: "✗",
    }.get(seed.status, "?")

    blocked = " [BLOCKED]" if db.is_blocked(seed.id) else ""
    tags = f" [{', '.join(seed.tags)}]" if seed.tags else ""

    return f"{status_icon} {seed.id}: {seed.title}{blocked}{tags}"


@main.command("list")
@click.option(
    "--status",
    type=click.Choice(SEED_STATUSES),
    help="Filter by status",
)
@click.option(
    "--type",
    "seed_type",
    help=f"Filter by type (any value; standard: {', '.join(SEED_TYPES)})",
)
@click.option("--tag", help="Filter by tag")
@click.option("--all", "include_all", is_flag=True, help="Include resolved/abandoned")
@click.option(
    "--since",
    "since_value",
    help=(
        "Only show seeds updated on or after this point. Accepts ISO date "
        "(2026-05-08), relative (7d, 2w, 3m, 1y), or 'today'/'yesterday'."
    ),
)
@click.option(
    "--sort",
    "sort_by",
    type=click.Choice(["created", "updated"]),
    default="created",
    help="Sort order (descending). Defaults to 'created'.",
)
@pass_context
def list_seeds(
    ctx: Context,
    status: str | None,
    seed_type: str | None,
    tag: str | None,
    include_all: bool,
    since_value: str | None,
    sort_by: str,
) -> None:
    """List seeds with optional filters."""
    db = ctx.get_db()

    status_enum = SeedStatus(status) if status else None

    since_dt = None
    if since_value:
        try:
            since_dt = parse_since(since_value)
        except ValueError as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

    seeds = db.list_seeds(
        status=status_enum,
        seed_type=seed_type,
        tag=tag,
        include_terminal=include_all,
        since=since_dt,
        sort_by=sort_by,
    )

    if not seeds:
        click.echo("No seeds found.")
        return

    for seed in seeds:
        click.echo(format_seed_line(seed, db))


@main.command()
@click.option(
    "--since",
    "since_value",
    default="7d",
    show_default=True,
    help=(
        "Recency window. Accepts ISO date (2026-05-08), relative "
        "(7d, 2w, 3m, 1y), or 'today'/'yesterday'."
    ),
)
@click.option("--all", "include_all", is_flag=True, help="Include resolved/abandoned")
@pass_context
def recent(ctx: Context, since_value: str, include_all: bool) -> None:
    """Show seeds updated recently, sorted by updated_at descending.

    Thin alias for ``seeds list --since=<value> --sort=updated`` with a
    default window of 7 days.
    """
    db = ctx.get_db()

    try:
        since_dt = parse_since(since_value)
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    seeds = db.list_seeds(
        since=since_dt,
        sort_by="updated",
        include_terminal=include_all,
    )

    if not seeds:
        click.echo(f"No seeds updated since {since_value}.")
        return

    for seed in seeds:
        click.echo(format_seed_line(seed, db))


def format_seed_detail(
    seed: Seed, db: Database, include_questions: bool = False
) -> str:
    """Format seed details as a string."""
    lines = []

    # Header
    lines.append(f"{seed.id}: {seed.title}")
    lines.append(f"  Status: {seed.status.value}")
    lines.append(f"  Type: {seed.seed_type}")

    if seed.resolution:
        lines.append(f"  Resolution: {seed.resolution}")

    if seed.tags:
        lines.append(f"  Tags: {', '.join(seed.tags)}")

    if seed.parent_id:
        lines.append(f"  Parent: {seed.parent_id}")

    # Check if blocked
    if db.is_blocked(seed.id):
        lines.append("  [BLOCKED by unresolved children]")

    # Show children
    children = db.get_children(seed.id)
    if children:
        lines.append(f"  Children: {len(children)}")
        for child in children:
            status_mark = "●" if child.is_terminal() else "○"
            lines.append(f"    {status_mark} {child.id}: {child.title}")

    # Show related (via relationships table)
    relates_to = db.get_relationships(
        seed.id, rel_type=RelationType.RELATES_TO, direction="outbound"
    )
    if relates_to:
        related_ids = [r.target_id for r in relates_to]
        lines.append(f"  Related to: {', '.join(related_ids)}")

    # Content
    if seed.content:
        lines.append("")
        lines.append("Content:")
        lines.append(seed.content)

    # Questions (question-seeds linked via 'questions' relationship)
    if include_questions:
        question_seeds = db.get_questions_for_seed(seed.id)
        if question_seeds:
            lines.append("")
            lines.append("Questions:")
            for qs in question_seeds:
                status_mark = "●" if qs.is_terminal() else "○"
                lines.append(f"  {status_mark} {qs.id}: {qs.title}")
                if qs.content:
                    lines.append(f"    → {qs.content}")

    return "\n".join(lines)


@main.command()
@click.argument("text")
@click.option("--limit", type=int, default=5, show_default=True, help="Max results")
@click.option(
    "--open-only",
    is_flag=True,
    help="Restrict to non-terminal seeds (default includes resolved/abandoned)",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Emit compact JSON for agent piping (pipe through jq to read it)",
)
@pass_context
def suggest(
    ctx: Context, text: str, limit: int, open_only: bool, as_json: bool
) -> None:
    """Find existing seeds related to natural-language TEXT.

    Purpose-built dedup query for the transcript-incorporation workflow:
    given a candidate item, answer 'does a seed about this already exist?'
    Includes resolved/abandoned seeds by default — the question is about
    deliberation history, not just actionable seeds.
    """
    db = ctx.get_db()
    results = db.suggest(text, limit=limit, open_only=open_only)

    if as_json:
        import json as _json

        payload = [
            {
                "id": r.seed.id,
                "title": r.seed.title,
                "status": r.seed.status.value,
                "tags": r.seed.tags,
                "snippet": r.snippet,
                "score": round(r.score, 4),
            }
            for r in results
        ]
        # Compact, not pretty: this output exists to be piped into an agent,
        # and indentation is tokens the model pays for. `separators` matters
        # too — dropping `indent` alone still leaves ", " and ": " padding.
        # Humans: pipe through `jq`. (seeds-d773)
        click.echo(_json.dumps(payload, separators=(",", ":")))
        return

    if not results:
        click.echo(f"No seeds matched '{text}'.")
        return

    status_icon = {
        SeedStatus.CAPTURED: "○",
        SeedStatus.EXPLORING: "◐",
        SeedStatus.DEFERRED: "◌",
        SeedStatus.RESOLVED: "●",
        SeedStatus.ABANDONED: "✗",
    }
    for r in results:
        icon = status_icon.get(r.seed.status, "?")
        tags = f" [{', '.join(r.seed.tags)}]" if r.seed.tags else ""
        click.echo(f"{icon} {r.seed.id}: {r.seed.title}{tags}")
        if r.snippet:
            click.echo(f"    …{r.snippet}…")


@main.command()
@click.argument("query")
@click.option("--all", "include_all", is_flag=True, help="Include resolved/abandoned")
@pass_context
def search(ctx: Context, query: str, include_all: bool) -> None:
    """Full-text search across seeds and questions.

    QUERY is an FTS5 search string. Supports:
      - Simple words: seeds search deliberation
      - Phrases: seeds search '"agent reasoning"'
      - Prefix: seeds search 'delib*'
      - Boolean: seeds search 'agent OR sweep'
    """
    db = ctx.get_db()

    results = db.search(query, include_terminal=include_all)

    if not results:
        click.echo(f"No seeds matching '{query}'.")
        return

    click.echo(f"Found {len(results)} seed(s):")
    for seed in results:
        click.echo(format_seed_line(seed, db))


@main.command()
@click.argument("seed_id")
@click.option("--questions", "-q", is_flag=True, help="Include attached questions")
@click.option(
    "--output-file",
    "-o",
    is_flag=True,
    help="Write to temp file, print path (for Claude Code)",
)
@pass_context
def show(ctx: Context, seed_id: str, questions: bool, output_file: bool) -> None:
    """Show detailed information about a seed.

    Use --output-file to write output to a temp file and print the path.
    This works around Claude Code CLI terminal truncation issues.
    """
    db = ctx.get_db()

    seed = db.get_seed(seed_id)
    if seed is None:
        click.echo(f"Error: Seed '{seed_id}' not found.", err=True)
        sys.exit(1)

    output = format_seed_detail(seed, db, include_questions=questions)

    if output_file:
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, prefix=f"seeds-{seed_id}-"
        ) as f:
            f.write(output)
            click.echo(f.name)
    else:
        click.echo(output)


@main.command()
@pass_context
def ready(ctx: Context) -> None:
    """Show captured seeds ready to explore."""
    db = ctx.get_db()

    seeds = db.list_seeds(status=SeedStatus.CAPTURED)

    if not seeds:
        click.echo("No captured seeds ready to explore.")
        return

    click.echo("Ready to explore:")
    for seed in seeds:
        click.echo(format_seed_line(seed, db))


@main.command()
@pass_context
def deferred(ctx: Context) -> None:
    """Show deferred seeds (backlog)."""
    db = ctx.get_db()

    seeds = db.list_seeds(status=SeedStatus.DEFERRED)

    if not seeds:
        click.echo("No deferred seeds.")
        return

    click.echo("Deferred (backlog):")
    for seed in seeds:
        click.echo(format_seed_line(seed, db))


@main.command()
@pass_context
def blocked(ctx: Context) -> None:
    """Show seeds blocked by unresolved children or questions."""
    db = ctx.get_db()

    seeds = db.get_blocked_seeds()

    if not seeds:
        click.echo("No blocked seeds.")
        return

    click.echo("Blocked seeds:")
    for seed in seeds:
        click.echo(f"  {seed.id}: {seed.title}")
        # Show unresolved children
        children = db.get_children(seed.id)
        for child in children:
            if not child.is_terminal():
                click.echo(f"    ○ {child.id}: {child.title}")
        # Show unresolved question-seeds
        question_seeds = db.get_questions_for_seed(seed.id)
        for qs in question_seeds:
            if not qs.is_terminal():
                click.echo(f"    ? {qs.id}: {qs.title}")


# --- Status change commands ---


def get_seed_or_exit(db: Database, seed_id: str) -> Seed:
    """Get a seed by ID or exit with error."""
    seed = db.get_seed(seed_id)
    if seed is None:
        click.echo(f"Error: Seed '{seed_id}' not found.", err=True)
        sys.exit(1)
    return seed


@main.command()
@click.argument("seed_id")
@pass_context
def explore(ctx: Context, seed_id: str) -> None:
    """Start exploring a seed (captured → exploring)."""
    db = ctx.get_db()
    seed = get_seed_or_exit(db, seed_id)

    if seed.status != SeedStatus.CAPTURED:
        click.echo(f"Warning: Seed is {seed.status.value}, not captured.")

    seed.status = SeedStatus.EXPLORING
    db.update_seed(seed)
    click.echo(f"◐ {seed_id}: Now exploring")


@main.command()
@click.argument("seed_id")
@pass_context
def defer(ctx: Context, seed_id: str) -> None:
    """Defer a seed to the backlog."""
    db = ctx.get_db()
    seed = get_seed_or_exit(db, seed_id)

    seed.status = SeedStatus.DEFERRED
    db.update_seed(seed)
    click.echo(f"◌ {seed_id}: Deferred to backlog")


@main.command()
@click.argument("seed_id")
@click.option("--resolution", "-r", help="What was decided or what happened")
@pass_context
def resolve(ctx: Context, seed_id: str, resolution: str | None) -> None:
    """Mark a seed as resolved."""
    db = ctx.get_db()
    seed = get_seed_or_exit(db, seed_id)

    from seeds.models import now_utc

    seed.status = SeedStatus.RESOLVED
    seed.resolved_at = now_utc()
    if resolution:
        seed.resolution = resolution
    db.update_seed(seed)
    click.echo(f"● {seed_id}: Resolved")
    if resolution:
        click.echo(f"  Resolution: {resolution}")


@main.command()
@click.argument("seed_id")
@click.option("--reason", "-r", help="Reason for abandoning")
@pass_context
def abandon(ctx: Context, seed_id: str, reason: str | None) -> None:
    """Abandon a seed (decided not to pursue)."""
    db = ctx.get_db()
    seed = get_seed_or_exit(db, seed_id)

    from seeds.models import now_utc

    seed.status = SeedStatus.ABANDONED
    seed.resolved_at = now_utc()
    if reason:
        seed.resolution = reason
    db.update_seed(seed)
    click.echo(f"✗ {seed_id}: Abandoned")
    if reason:
        click.echo(f"  Reason: {reason}")


@main.command()
@click.argument("seed_id")
@click.option(
    "--to",
    "target_file",
    required=True,
    help="Durable context file to write the trellis into (e.g. CLAUDE.md).",
)
@click.option(
    "--as",
    "principle",
    required=True,
    help="The one-line principle to record as a trellis.",
)
@click.option(
    "--no-resolve",
    is_flag=True,
    help="Record the trellis without resolving the seed (resolves by default).",
)
@click.option(
    "--section",
    default="## Principles",
    show_default=True,
    help="Managed section heading to find-or-create in the target file.",
)
@pass_context
def trellis(
    ctx: Context,
    seed_id: str,
    target_file: str,
    principle: str,
    no_resolve: bool,
    section: str,
) -> None:
    """Record a matured seed as a trellis in durable context.

    Writes the one-line PRINCIPLE (given with --as) into a managed section of
    the file named by --to, records two-way provenance (a bullet citing the
    seed in the file; a resolution naming the file on the seed), tags the seed
    'trellis', and resolves it (unless --no-resolve is passed).
    """
    from seeds.models import now_utc
    from seeds.trellis import append_to_managed_section

    db = ctx.get_db()
    seed = get_seed_or_exit(db, seed_id)

    date_str = now_utc().strftime("%Y-%m-%d")
    bullet = f"- {principle} — {seed.id}, {date_str}"

    # Forward-provenance: file -> seed (the bullet cites the seed id).
    path = Path(target_file)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        append_to_managed_section(existing, section, bullet), encoding="utf-8"
    )

    # Back-provenance: seed -> file (the resolution names the file + date).
    seed.resolution = (
        f"Recorded as a trellis in `{target_file}` on {date_str}: {principle}"
    )
    if "trellis" not in seed.tags:
        seed.tags.append("trellis")

    if not no_resolve:
        seed.status = SeedStatus.RESOLVED
        seed.resolved_at = now_utc()

    db.update_seed(seed)

    # Echo both ends of the link: the appended bullet and the new resolution.
    click.echo(f"● {seed.id}: trellis → {target_file}")
    click.echo(f"  {bullet}")
    click.echo(f"  Resolution: {seed.resolution}")
    click.echo(f"  Status: {seed.status.value}")


@main.command()
@click.argument("seed_id")
@click.option("--title", "-t", help="New title")
@click.option(
    "--content",
    "-c",
    metavar="TEXT",
    help=(
        "New content (replaces existing; refused once a seed has been edited). "
        "Pass - to read the body from stdin."
    ),
)
@click.option(
    "--content-file",
    metavar="PATH",
    help=(
        "Read the new content from a file instead of argv (same replacement "
        "and same guard as --content; cannot be combined with it)"
    ),
)
@click.option("--tags", help="New tags (comma-separated, replaces existing)")
@click.option(
    "--type",
    "seed_type",
    help=f"New type (any value; standard: {', '.join(SEED_TYPES)})",
)
@click.option(
    "--add-tag",
    "add_tags",
    multiple=True,
    help=(
        "Add one tag, keeping the rest (repeatable; no-op if already present; "
        "cannot be combined with --tags)"
    ),
)
@click.option(
    "--remove-tag",
    "remove_tags",
    multiple=True,
    help=(
        "Remove one tag, keeping the rest (repeatable; silent no-op if the "
        "seed does not carry it; cannot be combined with --tags)"
    ),
)
@click.option("--append", "-a", "append_text", help="Append to content")
@click.option(
    "--replace",
    is_flag=True,
    help=(
        "Let a --content/--content-file replacement discard content "
        "accumulated since the seed was created. "
        "For redactions only -- and it does not finish the job: the old body "
        "stays in git history and needs separate scrubbing."
    ),
)
@click.option(
    "--allow-unknown-refs",
    is_flag=True,
    help="Skip validation of seed-ID cross-references in title/content/append",
)
@pass_context
def update(
    ctx: Context,
    seed_id: str,
    title: str | None,
    content: str | None,
    content_file: str | None,
    tags: str | None,
    seed_type: str | None,
    add_tags: tuple[str, ...],
    remove_tags: tuple[str, ...],
    append_text: str | None,
    replace: bool,
    allow_unknown_refs: bool,
) -> None:
    """Update a seed's fields.

    --content replaces the body wholesale, so it is refused on a seed that has
    been edited since it was created; use --append to add to the deliberation,
    or --replace to discard it deliberately. --title and --tags carry no such
    guard: tags are working state whose normal verb is replacement.

    The replacement body does not have to travel through argv: --content-file
    PATH reads it from a file and --content - reads it from stdin. Both are the
    same replacement as -c TEXT and clear the same guard the same way; passing
    more than one of the three is refused rather than ranked.

    Tags can be set wholesale with --tags or edited one at a time with
    --add-tag/--remove-tag, which compose with each other and leave every other
    tag untouched and in place. The two styles cannot be mixed in one command,
    and neither can adding and removing the same tag: both are refused rather
    than resolved by a precedence rule. Removing a tag the seed does not carry
    is a silent no-op reported as "0 removed".

    --type accepts any string, matching `seeds create`. Before this existed a
    seed's type was write-once and the only way to change it was hand-editing
    the JSONL -- which is how the malformed records in seed seeds-1x6b got in.
    """
    db = ctx.get_db()
    seed = get_seed_or_exit(db, seed_id)

    content = _resolve_content(content, content_file)

    _validate_id_refs(db, [title, content, append_text], allow_unknown_refs)
    _reject_ambiguous_tag_flags(tags, add_tags, remove_tags)

    if content is not None and not replace:
        _guard_content_replacement(
            seed,
            GuardCopy(
                reason="has been edited since it was created",
                subject="--content",
                append_cmd=f'seeds update {seed.id} --append "..."',
                replace_cmd=f'seeds update {seed.id} --content "..." --replace',
            ),
        )

    changed = False

    if title:
        seed.title = title
        changed = True

    if content is not None:
        seed.content = content
        changed = True

    if append_text:
        seed.content = f"{seed.content}\n\n{append_text}".strip()
        changed = True

    if tags is not None:
        seed.tags = [t.strip() for t in tags.split(",")] if tags else []
        changed = True

    if seed_type:
        seed.seed_type = seed_type
        changed = True

    tag_report = None
    if add_tags or remove_tags:
        before = list(seed.tags)
        tag_report = _apply_tag_edits(seed, add_tags, remove_tags)
        # A request that matched nothing leaves updated_at alone, so it cannot
        # arm the --content guard on a seed nobody actually edited.
        changed = changed or seed.tags != before

    if not changed:
        click.echo(tag_report or "No changes specified.")
        return

    db.update_seed(seed)
    click.echo(f"Updated {seed_id}")
    if tag_report:
        click.echo(f"  {tag_report}")


# --- Question commands ---


@main.command()
@click.argument("question_text")
@click.option("--seed", "seed_id", required=True, help="Seed ID to attach question to")
@pass_context
def ask(ctx: Context, question_text: str, seed_id: str) -> None:
    """Ask a question and attach it to a seed.

    Creates a question-type seed and links it via a 'questions' relationship.
    QUESTION_TEXT is the question to ask.
    """
    db = ctx.get_db()

    # Verify seed exists
    seed = db.get_seed(seed_id)
    if seed is None:
        click.echo(f"Error: Seed '{seed_id}' not found.", err=True)
        sys.exit(1)

    question_id = db.next_id()
    question_seed = Seed(
        id=question_id,
        title=question_text,
        seed_type=SeedType.QUESTION.value,
    )

    db.create_seed(question_seed)
    db.create_relationship(question_id, seed_id, RelationType.QUESTIONS)
    click.echo(f"○ {question_id}: {question_text}")
    click.echo(f"  Attached to: {seed_id}")


@main.command()
@click.argument("question_id")
@click.argument("answer_text")
@click.option(
    "--append",
    "-a",
    is_flag=True,
    help=(
        "Append to the existing answer instead of replacing it -- use to "
        "record a revision or reversal without discarding the prior answer."
    ),
)
@click.option(
    "--replace",
    is_flag=True,
    help=(
        "Let a re-answer discard the previous answer wholesale. For a "
        "deliberate correction only -- the old answer stays in git history "
        "(.seeds/seeds.jsonl) and needs separate scrubbing."
    ),
)
@pass_context
def answer(
    ctx: Context, question_id: str, answer_text: str, append: bool, replace: bool
) -> None:
    """Answer a question-seed.

    QUESTION_ID is the ID of the question-seed to answer.
    ANSWER_TEXT is the answer (stored as seed content).

    An answer is a recorded conclusion, so re-answering an already-answered
    question is refused by default -- same guard as `update --content`, and
    for the same reason: silently destroying a prior answer is worse than
    refusing. Use --append to record a revision (e.g. a reversed decision)
    alongside the original, or --replace to discard the old answer on
    purpose. Neither flag is needed to answer an open question for the first
    time. Every successful answer -- first, appended, or replaced --
    re-stamps resolved_at to now, marking the moment of the latest
    resolution.
    """
    if append and replace:
        click.echo(
            "Error: --append and --replace are contradictory -- pick one.",
            err=True,
        )
        sys.exit(1)

    db = ctx.get_db()

    from seeds.models import now_utc

    question_seed = db.get_seed(question_id)
    if question_seed is None:
        click.echo(f"Error: Question '{question_id}' not found.", err=True)
        sys.exit(1)

    if not append and not replace:
        _guard_content_replacement(
            question_seed,
            GuardCopy(
                reason="has already been answered",
                subject="answering again",
                append_cmd=f'seeds answer {question_seed.id} "..." --append',
                replace_cmd=f'seeds answer {question_seed.id} "..." --replace',
            ),
        )

    if append:
        question_seed.content = f"{question_seed.content}\n\n{answer_text}".strip()
    else:
        question_seed.content = answer_text
    question_seed.status = SeedStatus.RESOLVED
    question_seed.resolved_at = now_utc()
    db.update_seed(question_seed)
    click.echo(f"● {question_id}: {question_seed.title}")
    click.echo(f"  → {answer_text}")


@main.command()
@click.option("--seed", "seed_id", help="Filter by seed ID")
@pass_context
def questions(ctx: Context, seed_id: str | None) -> None:
    """List open questions (question-type seeds that are unresolved)."""
    db = ctx.get_db()

    if seed_id:
        # Get question-seeds for a specific seed
        qs = [q for q in db.get_questions_for_seed(seed_id) if not q.is_terminal()]
    else:
        # Get all unresolved question-type seeds
        qs = db.list_seeds(seed_type=SeedType.QUESTION.value, include_terminal=False)

    if not qs:
        click.echo("No open questions.")
        return

    click.echo("Open questions:")
    for q in qs:
        # Find which seed this question is about
        rels = db.get_relationships(
            q.id, rel_type=RelationType.QUESTIONS, direction="outbound"
        )
        if rels:
            target_seed = db.get_seed(rels[0].target_id)
            target_title = target_seed.title if target_seed else "?"
            click.echo(f"  ○ {q.id}: {q.title}")
            click.echo(f"    └─ {rels[0].target_id}: {target_title}")
        else:
            click.echo(f"  ○ {q.id}: {q.title}")


# --- Relationship commands ---


# The types a user may pick. Not every ``RelationType`` member: ``questioned-by``
# is the storage-side inverse of ``questions`` (docs/storage-format.md §5.2),
# laid down at the far end by the writer, so offering it here would only let
# someone create a reversed edge with no forward counterpart.
RELATIONSHIP_TYPES = [RelationType.RELATES_TO.value, RelationType.QUESTIONS.value]


@main.command()
@click.argument("seed_id")
@click.option("--relates-to", "related_id", required=True, help="ID of related seed")
@click.option(
    "--type",
    "rel_type",
    type=click.Choice(RELATIONSHIP_TYPES),
    default="relates-to",
    help="Relationship type",
)
@pass_context
def link(ctx: Context, seed_id: str, related_id: str, rel_type: str) -> None:
    """Link a seed to another seed via typed relationship."""
    db = ctx.get_db()

    get_seed_or_exit(db, seed_id)
    related = db.get_seed(related_id)
    if related is None:
        click.echo(f"Error: Seed '{related_id}' not found.", err=True)
        sys.exit(1)

    rel_type_enum = RelationType(rel_type)

    # Check if already linked
    existing = db.get_relationships(
        seed_id, rel_type=rel_type_enum, direction="outbound"
    )
    if any(r.target_id == related_id for r in existing):
        click.echo(f"Already linked: {seed_id} ↔ {related_id}")
        return

    db.create_relationship(seed_id, related_id, rel_type_enum)

    if rel_type_enum == RelationType.RELATES_TO:
        click.echo(f"Linked: {seed_id} ↔ {related_id}")
    else:
        click.echo(f"Linked: {seed_id} —[{rel_type}]→ {related_id}")


@main.command()
@click.argument("seed_id")
@pass_context
def tree(ctx: Context, seed_id: str) -> None:
    """Show hierarchy and relationships for a seed."""
    db = ctx.get_db()

    seed = get_seed_or_exit(db, seed_id)

    def print_seed(s: Seed, indent: int = 0) -> None:
        prefix = "  " * indent
        status_icon = {
            SeedStatus.CAPTURED: "○",
            SeedStatus.EXPLORING: "◐",
            SeedStatus.DEFERRED: "◌",
            SeedStatus.RESOLVED: "●",
            SeedStatus.ABANDONED: "✗",
        }.get(s.status, "?")
        click.echo(f"{prefix}{status_icon} {s.id}: {s.title}")

    # Show parent chain
    parent_chain: list[Seed] = []
    current_id = seed.parent_id
    while current_id:
        parent = db.get_seed(current_id)
        if parent:
            parent_chain.insert(0, parent)
            current_id = parent.parent_id
        else:
            break

    if parent_chain:
        click.echo("Ancestors:")
        for i, p in enumerate(parent_chain):
            print_seed(p, i)

    # Show current seed
    click.echo()
    click.echo("Current:")
    print_seed(seed, 0)

    # Show children
    children = db.get_children(seed_id)
    if children:
        click.echo()
        click.echo("Children:")
        for child in children:
            print_seed(child, 1)
            # Show grandchildren
            grandchildren = db.get_children(child.id)
            for gc in grandchildren:
                print_seed(gc, 2)

    # Show related (via relationships)
    relates_to = db.get_relationships(
        seed_id, rel_type=RelationType.RELATES_TO, direction="outbound"
    )
    if relates_to:
        click.echo()
        click.echo("Related:")
        for rel in relates_to:
            related = db.get_seed(rel.target_id)
            if related:
                click.echo(f"  ↔ {related.id}: {related.title}")
            else:
                click.echo(f"  ↔ {rel.target_id}: (not found)")


# --- Sync and export commands ---


def _format_refusal(rec: RefusedRecord) -> str:
    """One refusal line: where the record is, which one it is, what is wrong."""
    where = f"record {rec.record_number}"
    if rec.seed_id:
        where += f" ({rec.seed_id})"
    return f"  {where}: {rec.field} — {rec.reason}"


def _format_import_summary(result: ImportResult) -> str:
    """Created/updated/skipped summary shared by import and sync.

    Stays a single unchanged line when nothing was refused. Refusals are the
    exception, and each one names the record's position in the file, its ID,
    the field that failed and why — everything needed to go fix it without a
    second command.

    The import is best-effort (seed seeds-hao9): everything else in the file
    landed, so this report is the ONLY trace a refused record leaves. Both
    callers exit non-zero when it is non-empty, because a refusal that scrolls
    past unnoticed is the defect being fixed, not a cosmetic one.
    """
    summary = (
        f"Imported: {result.created} created, "
        f"{result.updated} updated, {result.skipped} skipped"
    )
    if not result.refused:
        return summary

    lines = [f"{summary}, {len(result.refused)} refused"]
    lines.append(
        "Refused (DB left unchanged by these records; everything else landed):"
    )
    lines.extend(_format_refusal(rec) for rec in result.refused)
    return "\n".join(lines)


@main.command("import")
@click.argument("path", required=False)
@pass_context
def import_(ctx: Context, path: str | None) -> None:
    """Rehydrate seeds from JSONL (last-write-wins upsert).

    PATH defaults to .seeds/seeds.jsonl. Pass '-' to read JSONL from stdin.
    Uses the bootstrap seam so it works on a fresh clone with no DB: the
    schema is created and the project prefix recovered from the JSONL itself.
    DB rows fresher than their JSONL record are never clobbered, and DB-only
    seeds (absent from the JSONL) are never deleted.

    Best-effort: a record seeds cannot read is refused and named, and every
    other record in the file still imports. Exits non-zero when anything was
    refused, so a script notices.
    """
    from seeds.export import import_from_jsonl, import_lines

    db = ctx.get_db(bootstrap=True)

    reported_path = (
        Path(path) if path not in (None, "-") else db.path.parent / JSONL_FILE
    )
    if path == "-":
        result = import_lines(db, sys.stdin, bootstrap=True)
    else:
        input_path = Path(path) if path is not None else None
        result = import_from_jsonl(db, input_path, bootstrap=True)

    click.echo(_format_import_summary(result))
    if result.refused:
        click.echo(
            f"Fix the records named above in "
            f"{Path('<stdin>') if path == '-' else reported_path} and re-run.",
            err=True,
        )
        sys.exit(1)


def _format_divergence_error(exc: DivergentExportError) -> str:
    """Render a refused export so the operator can act on it without guessing.

    Names every affected seed, shows what each side holds, and states the two
    ways forward. seeds did not write the on-disk content, so it cannot say
    where it came from — it can only say that overwriting would destroy it.

    A content divergence still has to be resolved by a person: only they can
    say what the merged body should read. What this must NOT do is make them
    pay for that twice — the remediation used to print a ``-c '<on-disk
    text><newer text>'`` template, which asked for the entire rebuilt body as
    one shell word. For the agent that actually runs this, that is the whole
    seed read into context and re-emitted verbatim, where a truncation or a
    mangled quote corrupts deliberation silently, and the seeds most likely to
    diverge are the long ones. So the rebuild is still theirs; the delivery
    points at ``--content-file``/``--content -`` (seeds-lf5) instead.
    """
    path = exc.output_path
    lines = [
        f"Error: refusing to overwrite {path} — it holds content the database "
        "has never seen.",
        "",
    ]
    for div in exc.divergences:
        lines.append(f"  {div.seed_id}: {div.detail}")
        if div.on_disk:
            lines.append(f"      on disk: {div.on_disk}")
        if div.in_db:
            lines.append(f"      in db:   {div.in_db}")
    lines.extend(
        [
            "",
            "Nothing was written; the file is byte-for-byte unchanged.",
            "",
            "seeds did not write that content, so it cannot tell you where it "
            "came from —",
            "a resolved git conflict, a hand edit, or a peer's export are the "
            "usual sources.",
            "",
            "To keep it, fold it into the database, then re-run the sync:",
            "  # see what arrived",
            f"  git diff -- {path}",
        ]
    )
    kinds = {div.kind for div in exc.divergences}
    if "missing" in kinds:
        lines.append("  # absorb the records the database is missing")
        lines.append(f"  seeds import {path}")
    if "content" in kinds:
        lines.append("  # compare, then rebuild the body: the on-disk text FIRST,")
        lines.append("  # then whatever the database added after it")
        lines.append("  seeds show <id>")
        lines.append("  # hand the rebuilt body over as a file -- not through argv")
        lines.append("  seeds update <id> --replace --content-file <file>")
        lines.append("  # or on stdin: ... | seeds update <id> --replace --content -")
    if "unreadable" in kinds:
        lines.append("  # unreadable lines have to be repaired in the file by hand")
    lines.extend(
        [
            "",
            "Only if that content is genuinely disposable — this destroys it:",
            "  seeds sync --allow-divergence",
        ]
    )
    return "\n".join(lines)


def _detect_mixed_stage(db: Database) -> list[str] | None:
    """Staged paths outside .seeds/ that a flush would fold into their commit.

    Returns ``None`` when the guard should NOT fire: no git commit context
    (see :func:`seeds.gitstage.staged_paths_outside`), nothing staged outside
    .seeds/, or the flush would not change seeds.jsonl at all — a clean sync
    has nothing pending to bake into anything. A non-empty list names the
    staged paths and means the guard fires.

    Order matters for cost, not correctness: the git query runs first only
    because it's the cheaper way to rule the common case out (no commit in
    progress at all).
    """
    from seeds.export import export_would_change
    from seeds.gitstage import staged_paths_outside

    staged = staged_paths_outside(SEEDS_DIR)
    if not staged:
        return None
    if not export_would_change(db):
        return None
    return staged


def _format_mixed_stage_error(staged_paths: list[str]) -> str:
    """Render the mixed-stage refusal (seeds-ww8) with the approved wording.

    The first two lines are the exact text Ryan approved verbatim. Everything
    after names the staged paths that triggered the refusal and restates
    --allow-mixed-stage, so the escape hatch is discoverable at the moment
    it's needed — the bead's own point is that noisy pre-commit output makes a
    bare warning easy to miss, which is exactly why this exits non-zero
    instead of just printing a line.
    """
    lines = [
        "seeds: refusing to flush -- the export would modify .seeds/seeds.jsonl "
        "but staged code is unrelated.",
        "Resolve with EITHER `git commit` the code first then re-run, OR `git "
        "stash --keep-index` and create a dedicated `chore(seeds): ...` commit.",
        "",
        "Staged outside .seeds/:",
    ]
    lines.extend(f"  {path}" for path in staged_paths)
    lines.extend(
        [
            "",
            "Only for an intentional combined seed+code commit:",
            "  seeds sync --allow-mixed-stage",
        ]
    )
    return "\n".join(lines)


@main.command()
@click.option("--flush-only", is_flag=True, help="Only export to JSONL (no git ops)")
@click.option(
    "--allow-divergence",
    is_flag=True,
    help=(
        "Overwrite .seeds/seeds.jsonl even when it holds records the database "
        "cannot account for. Destroys that content. Off by default; use only "
        "after reading what the refusal names."
    ),
)
@click.option(
    "--allow-mixed-stage",
    is_flag=True,
    help=(
        "Flush even when other, unrelated files are staged for commit. Off by "
        "default: a flush that changes .seeds/seeds.jsonl while code is staged "
        "would otherwise bake pending seed-database changes into whatever "
        "commit fires next. Use only for an intentional combined seed+code "
        "commit."
    ),
)
@pass_context
def sync(
    ctx: Context, flush_only: bool, allow_divergence: bool, allow_mixed_stage: bool
) -> None:
    """Round-trip seeds with JSONL: import (LWW) then export.

    The import half rehydrates any seeds present in .seeds/seeds.jsonl but
    missing or staler in the DB, without clobbering fresher DB rows or
    deleting DB-only seeds. Pass --flush-only to skip the import and export
    only (the original behaviour).

    The export half rewrites the file wholesale, so it first checks that the
    database accounts for everything already on disk and refuses rather than
    destroying a record it has never seen — a resolved merge conflict, a hand
    edit, or a peer's seed that no import absorbed. --flush-only gets the same
    check: skipping the import does not make the overwrite any less
    destructive. Pass --allow-divergence to overwrite anyway.

    Before writing, also refuses when the flush would change .seeds/seeds.jsonl
    while other files are staged for commit outside .seeds/ — that combination
    means a `git commit` right now would fold pending seed-database changes
    into whatever commit fires next, regardless of topic (seeds-ww8). This
    only fires inside a git working tree with something staged, and only when
    the flush would actually change the file; a seed-only commit or a no-op
    sync is never blocked. Pass --allow-mixed-stage to flush anyway.

    The import half is best-effort: a record it cannot read is refused and
    named, and every other record still imports. Sync then finishes normally
    and exits non-zero at the END, rather than stopping at the refusal — a bad
    record must not also block the flush, or one unreadable line silently
    freezes the whole round-trip, which is the failure this policy replaced
    (seed seeds-hao9).
    """
    db = ctx.get_db()

    from seeds.export import export_to_jsonl, import_from_jsonl

    refused: list[RefusedRecord] = []
    if not flush_only:
        import_result = import_from_jsonl(db)
        refused = import_result.refused
        click.echo(_format_import_summary(import_result))

    if not allow_mixed_stage:
        contaminating_paths = _detect_mixed_stage(db)
        if contaminating_paths is not None:
            click.echo(_format_mixed_stage_error(contaminating_paths), err=True)
            sys.exit(1)

    try:
        output_path = export_to_jsonl(db, allow_divergence=allow_divergence)
    except DivergentExportError as exc:
        click.echo(_format_divergence_error(exc), err=True)
        sys.exit(1)

    # Count seeds
    seeds = db.list_seeds(include_terminal=True)
    click.echo(f"Exported {len(seeds)} seeds to {output_path}")

    # Deferred to the very end so the flush still happens, but still non-zero
    # so a script or hook driving `seeds sync` cannot mistake a lossy round
    # trip for a clean one.
    if refused:
        click.echo(
            f"{len(refused)} record(s) were refused on import (listed above) and "
            "are not in the database.",
            err=True,
        )
        sys.exit(1)


@main.command()
@click.option(
    "--no-digest",
    is_flag=True,
    help="Omit the project-state digest (counts, recent, exploration, questions, tags)",
)
@click.option(
    "--digest-limit",
    type=int,
    default=20,
    show_default=True,
    help="Max entries in the 'Recently Updated' section",
)
def prime(no_digest: bool, digest_limit: int) -> None:
    """Output AI-optimized workflow context for Claude Code hooks.

    Silently exits with code 0 if not in a seeds project.
    This enables cross-platform hook integration where both
    seeds and beads hooks can coexist.
    """
    from seeds.prime import get_prime_output

    # Check if we're in a seeds project
    seeds_dir = find_seeds_dir()
    if seeds_dir is None:
        # Not in a seeds project - silent exit with success
        # CRITICAL: No output, exit 0 to enable hook coexistence
        return

    db = Database()
    click.echo(
        get_prime_output(
            db=db,
            include_digest=not no_digest,
            digest_limit=digest_limit,
        )
    )


@main.command()
@pass_context
def doctor(ctx: Context) -> None:
    """Check for issues with seeds installation and data."""
    passed = 0
    warnings = 0
    failed = 0

    def check_pass(name: str) -> None:
        nonlocal passed
        click.echo(f"  ✓ {name}")
        passed += 1

    def check_warn(name: str, msg: str) -> None:
        nonlocal warnings
        click.echo(f"  ⚠ {name}: {msg}")
        warnings += 1

    def check_fail(name: str, msg: str) -> None:
        nonlocal failed
        click.echo(f"  ✗ {name}: {msg}")
        failed += 1

    click.echo("seeds Doctor")
    click.echo()

    # Check database
    click.echo("Database:")
    db = ctx.get_db()
    if db.is_initialized():
        check_pass("Database exists")
    else:
        check_fail("Database", "Not initialized")
        return

    # Report project prefix and nudge the user when the default doesn't
    # match the project directory name.
    click.echo()
    click.echo("Project:")
    current_prefix = db.get_prefix()
    if db.has_prefix_configured():
        check_pass(f"Prefix configured: {current_prefix!r}")
    else:
        check_warn(
            "Prefix",
            f"Using fallback {current_prefix!r}; run 'seeds rename-prefix "
            "<name>' to set one explicitly",
        )
    derived = sanitize_prefix(db.path.parent.parent.name)
    if current_prefix == DEFAULT_PREFIX and derived and derived != DEFAULT_PREFIX:
        check_warn(
            "Prefix",
            f"Default prefix {DEFAULT_PREFIX!r} doesn't match project dir; "
            f"run 'seeds rename-prefix {derived}' to customize",
        )

    # Check seeds
    click.echo()
    click.echo("Seeds:")
    all_seeds = db.list_seeds(include_terminal=True)
    check_pass(f"{len(all_seeds)} seeds total")

    open_seeds = db.list_seeds(include_terminal=False)
    if open_seeds:
        check_pass(f"{len(open_seeds)} open seeds")
    else:
        check_warn("Seeds", "No open seeds")

    # Check for orphaned relationships
    click.echo()
    click.echo("Relationships:")
    conn = db._get_conn()
    all_rels = conn.execute("SELECT * FROM relationships").fetchall()
    orphaned_rels = []
    for rel in all_rels:
        if (
            db.get_seed(rel["source_id"]) is None
            or db.get_seed(rel["target_id"]) is None
        ):
            orphaned_rels.append(rel)

    if not orphaned_rels:
        check_pass(f"{len(all_rels)} relationships, no orphans")
    else:
        check_warn("Relationships", f"{len(orphaned_rels)} orphaned relationships")

    # Check for open question-seeds
    open_questions = db.list_seeds(
        seed_type=SeedType.QUESTION.value, include_terminal=False
    )
    if open_questions:
        check_pass(f"{len(open_questions)} open questions")

    # Vocabulary drift. With seed_type an open string (seeds-0lb), this is the
    # only thing that surfaces a typo, so it is load-bearing rather than
    # cosmetic. A non-standard type is legal, hence a warning and not a failure.
    nonstandard: dict[str, int] = {}
    for seed in db.list_seeds(include_terminal=True):
        if seed.seed_type not in SEED_TYPES:
            nonstandard[seed.seed_type] = nonstandard.get(seed.seed_type, 0) + 1
    if nonstandard:
        click.echo()
        click.echo("Vocabulary:")
        total = sum(nonstandard.values())
        check_warn(
            "Non-standard types",
            f"{total} seeds use a type outside the standard set",
        )
        for type_name, count in sorted(nonstandard.items()):
            click.echo(f"      {type_name} ({count})")
        # Deliberately does not suggest a target. A non-standard type is legal
        # -- it may be this project's own vocabulary -- so naming one as the
        # "right" type would presume a typo doctor cannot actually detect.
        click.echo("      Remap one with: seeds retype --from <type> --to <type>")

    # Check JSONL sync
    click.echo()
    click.echo("Sync:")
    jsonl_path = Path.cwd() / SEEDS_DIR / JSONL_FILE
    if jsonl_path.exists():
        check_pass("JSONL file exists")

        # Compare CONTENT, not mtimes. The mtime check this replaces was not
        # merely a weak proxy -- it was anti-correlated with the failure it
        # should have caught. A failed import leaves the JSONL holding records
        # the database lacks, i.e. JSONL newer than DB, which is exactly what
        # it certified as "up to date". That is how Mark Danese's sync stayed
        # broken for five weeks with doctor reporting all clear (seeds-1x6b).
        #
        # The ID comparison alone was ALSO a proxy, and blind to the other half
        # of the same failure: an edit to a record's body in the file leaves
        # every ID matching, so doctor passed while `seeds sync` refused on
        # every run, permanently. find_divergence is the check the export
        # itself refuses on, so asking it here makes doctor agree with sync by
        # construction rather than by a second, weaker approximation.
        from seeds.export import find_divergence, find_refused_records, read_record_ids

        # Records the import will not apply. Since the import became
        # best-effort (seed seeds-hao9) these no longer stop a sync, so nothing
        # else makes noise about them: `seeds sync` reports them once and the
        # line scrolls away, and every one of doctor's other checks can be
        # perfectly green while the file quietly loses records on every round
        # trip. This is the check that keeps that from reading as clean.
        refused_records = find_refused_records(jsonl_path)
        if refused_records:
            check_fail(
                "Records", f"{len(refused_records)} record(s) the import will refuse"
            )
            for rec in refused_records[:10]:
                click.echo(f"    {_format_refusal(rec)}")
            if len(refused_records) > 10:
                click.echo(f"      ... and {len(refused_records) - 10} more")
        else:
            check_pass("All records readable")

        disk_ids = read_record_ids(jsonl_path)
        db_ids = {seed.id for seed in db.list_seeds(include_terminal=True)}
        missing_from_db = sorted(disk_ids - db_ids)
        missing_from_disk = sorted(db_ids - disk_ids)
        divergences = find_divergence(db, jsonl_path)
        # 'missing' divergences are the same records as missing_from_db; report
        # each fact once, under the heading that explains what to do about it.
        content_divergences = [d for d in divergences if d.kind != "missing"]

        if not missing_from_db and not missing_from_disk and not content_divergences:
            check_pass("JSONL and DB agree")
        else:
            check_fail("Sync", "JSONL and DB disagree")
            if missing_from_db:
                click.echo(f"      {len(missing_from_db)} records in JSONL not in DB")
                click.echo(f"        {', '.join(missing_from_db[:10])}")
            if missing_from_disk:
                click.echo(f"      {len(missing_from_disk)} seeds in DB not in JSONL")
                click.echo(f"        {', '.join(missing_from_disk[:10])}")
            if content_divergences:
                click.echo(
                    f"      {len(content_divergences)} records whose on-disk body "
                    "the database has not seen"
                )
                click.echo(
                    f"        {', '.join(d.seed_id for d in content_divergences[:10])}"
                )
            click.echo("      Run 'seeds sync'; if it fails, fix the records it names.")
    else:
        check_warn("Sync", "No JSONL file, run 'seeds sync'")

    # Summary
    click.echo()
    click.echo("─" * 40)
    status_parts = []
    if passed:
        status_parts.append(f"✓ {passed} passed")
    if warnings:
        status_parts.append(f"⚠ {warnings} warnings")
    if failed:
        status_parts.append(f"✗ {failed} failed")
    click.echo("  ".join(status_parts))

    # Exit non-zero on a real failure so doctor can gate a pre-commit or CI
    # hook. Warnings stay exit 0 -- they are advisory by design.
    if failed:
        sys.exit(1)


@main.command("check")
def check_cmd() -> None:
    """Verify the seed files are plausible, not merely parseable.

    The violations tier: every finding here is either a file the reader would
    refuse or a value that parses perfectly and is not credible -- a title that
    is a filesystem path, an edge written at one end only, a stamp ahead of the
    clock. It exits non-zero, so it can gate a commit or a conversion.

    Content plausibility is the job because format validity had nothing to say
    when a bulk sweep replaced 83 titles with a scratchpad path (seeds-wurl):
    every record parsed, both stores agreed, and every divergence check was
    correctly green for three days.
    """
    seeds_dir = find_seeds_dir()
    if seeds_dir is None:
        click.echo("Error: seeds not initialized. Run 'seeds init' first.", err=True)
        sys.exit(1)

    findings = check_violations(seeds_dir)
    if not findings:
        count = len(list(seed_files_dir(seeds_dir).glob("*.md")))
        click.echo(f"seeds check: {count} files, no violations.")
        return

    click.echo(format_findings(findings), nl=False)
    click.echo()
    click.echo(f"seeds check: {len(findings)} violation(s).")
    sys.exit(1)


@main.command("retype")
@click.option("--from", "from_type", required=True, help="The type to change")
@click.option("--to", "to_type", required=True, help="The type to change it to")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would change without writing to the database.",
)
@pass_context
def retype(ctx: Context, from_type: str, to_type: str, dry_run: bool) -> None:
    """Change every seed of one type to another.

    Both types are arbitrary strings, matching `seeds create --type`. That
    makes this the cleanup for a typo that slipped in (`--from ideea --to
    idea`) and equally the tool for deliberate vocabulary evolution
    (`--from concern --to risk`) across a whole project.

    Note the same openness applies to --to: a typo there is not catchable
    either. Use --dry-run first, and `seeds doctor` lists non-standard types
    afterwards.
    """
    db = ctx.get_db()

    if from_type == to_type:
        click.echo(f"--from and --to are both {from_type!r}; nothing to do.")
        return

    ids = db.retype_seeds(from_type, to_type, dry_run=dry_run)

    if not ids:
        click.echo(f"No seeds have type {from_type!r}; nothing to do.")
        return

    if dry_run:
        click.echo("DRY RUN — no changes will be written.")
    else:
        import shutil

        backup_path = db.path.with_suffix(".db.bak")
        shutil.copy2(db.path, backup_path)
        click.echo(f"Backed up database to {backup_path}")

    verb = "Would retype" if dry_run else "Retyped"
    click.echo(f"{verb} {len(ids)} seed(s) from {from_type!r} to {to_type!r}:")
    for seed_id in ids:
        click.echo(f"  {seed_id}")

    if dry_run:
        click.echo("\nRun without --dry-run to apply.")
        return

    from seeds.export import export_to_jsonl

    output_path = export_to_jsonl(db)
    click.echo(f"\nRe-exported to {output_path}")


@main.command("rename-prefix")
@click.argument("new_prefix")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would change without writing to the database.",
)
@click.option(
    "--rewrite-bodies/--no-rewrite-bodies",
    "rewrite_bodies",
    default=True,
    help=(
        "Whether to rewrite ID references inside seed title/content/"
        "resolution. Defaults to enabled; pass --no-rewrite-bodies to skip."
    ),
)
@pass_context
def rename_prefix(
    ctx: Context, new_prefix: str, dry_run: bool, rewrite_bodies: bool
) -> None:
    """Rename the project prefix and rewrite all seed IDs to use it.

    NEW_PREFIX must start with a lowercase letter and contain only lowercase
    letters, digits, and hyphens. The current prefix is read from the database
    config; all top-level IDs (and their children/relationships) using the old
    prefix are rewritten in place. ID references inside seed bodies
    (``title``, ``content``, ``resolution``) are also rewritten unless
    ``--no-rewrite-bodies`` is passed.
    """
    db = ctx.get_db()

    sanitized = sanitize_prefix(new_prefix)
    if not sanitized:
        click.echo(
            f"Error: invalid prefix {new_prefix!r}. Must start with a "
            "lowercase letter and contain only lowercase letters, digits, "
            "and hyphens.",
            err=True,
        )
        sys.exit(1)
    if sanitized != new_prefix:
        click.echo(f"Note: sanitized prefix to {sanitized!r}")

    old_prefix = db.get_prefix()
    if old_prefix == sanitized:
        click.echo(f"Prefix already set to {sanitized!r}; nothing to do.")
        return

    try:
        id_map, body_changes = db.rename_prefix(
            sanitized,
            old_prefix=old_prefix,
            rewrite_bodies=rewrite_bodies,
            dry_run=dry_run,
        )
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if dry_run:
        click.echo("DRY RUN — no changes will be written.")
    elif id_map or body_changes:
        import shutil

        backup_path = db.path.with_suffix(".db.bak")
        shutil.copy2(db.path, backup_path)
        click.echo(f"Backed up database to {backup_path}")

    if id_map:
        verb = "Would rename" if dry_run else "Renamed"
        click.echo(
            f"{verb} {len(id_map)} IDs from prefix {old_prefix!r} to {sanitized!r}:"
        )
        for old_id, new_id in sorted(id_map.items(), key=lambda x: x[1]):
            click.echo(f"  {old_id} → {new_id}")
    elif not body_changes:
        click.echo(f"Updated prefix to {sanitized!r} (no IDs matched {old_prefix!r}).")

    if body_changes:
        verb = "Would rewrite" if dry_run else "Rewrote"
        click.echo(f"\n{verb} {len(body_changes)} ID reference(s) inside seed bodies:")
        for change in body_changes:
            click.echo(f"  {change.seed_id} ({change.field}):")
            click.echo(f"    - {change.old_snippet}")
            click.echo(f"    + {change.new_snippet}")

    if dry_run:
        click.echo("\nRun without --dry-run to apply.")
        return

    from seeds.export import export_to_jsonl

    # The only sanctioned bypass of the divergence guard. A prefix rename
    # renumbers every ID at once, so every record on disk is "absent from the
    # database" by construction — the guard would fire on all of them and say
    # nothing the operator has not just been shown above, ID by ID. The
    # divergence here is self-inflicted, already reported, and the database was
    # backed up before the rename.
    output_path = export_to_jsonl(db, allow_divergence=True)
    click.echo(f"\nRe-exported to {output_path}")


@main.command("prefix")
@pass_context
def show_prefix(ctx: Context) -> None:
    """Show the current project prefix."""
    db = ctx.get_db()
    click.echo(db.get_prefix())


@main.group()
def skills() -> None:
    """Manage Claude Code skills shipped with seeds."""


@skills.command()
@click.option(
    "--reinstall",
    "--upgrade",
    "reinstall",
    is_flag=True,
    help="Force a clean refresh: re-read the marketplace from source and replace "
    "the installed plugin. Use after upgrading the seeds CLI so Claude Code picks "
    "up updated skill content.",
)
def install(reinstall: bool) -> None:
    """Install (and enable) the seeds Claude Code plugin (provides seeds:* skills).

    Idempotent and safe to re-run. Always ensures the plugin ends up *enabled* —
    install/update alone can leave it disabled, which silently drops every
    seeds:* skill from new Claude Code sessions. Pass --reinstall (alias
    --upgrade) after upgrading the seeds CLI to replace a stale cached copy.
    """
    import importlib.resources
    import shutil
    import subprocess

    plugin = "seeds@seeds-marketplace"
    marketplace = "seeds-marketplace"

    if not shutil.which("claude"):
        click.echo("`claude` CLI not found. Install Claude Code first.", err=True)
        raise click.Abort()

    def claude(*args: str, fatal: bool = False) -> subprocess.CompletedProcess[str]:
        """Run a `claude` subcommand; abort the install only when fatal."""
        proc = subprocess.run(
            ["claude", *args],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0 and fatal:
            click.echo(
                f"`claude {' '.join(args)}` failed: {proc.stderr.strip()}", err=True
            )
            raise click.Abort()
        return proc

    plugin_path = str(importlib.resources.files("seeds") / "plugin")

    # Register the local marketplace (idempotent — re-adding is a no-op/warning).
    claude("plugin", "marketplace", "add", plugin_path)
    if reinstall:
        # Re-read marketplace.json + plugin files from the on-disk source so an
        # upgraded seeds CLI's newer skill content is picked up.
        claude("plugin", "marketplace", "update", marketplace)

    installed = plugin in claude("plugin", "list").stdout

    if reinstall and installed:
        # Drop the cached copy so we re-copy fresh content. The plugin manifest
        # version is not always bumped, so `plugin update` can no-op on changed
        # content — a clean uninstall/install is reliable.
        claude("plugin", "uninstall", plugin, "--scope", "user", "-y")
        installed = False

    if installed:
        claude("plugin", "update", plugin, "--scope", "user", fatal=True)
        action = "updated"
    else:
        claude("plugin", "install", plugin, "--scope", "user", fatal=True)
        action = "installed"

    # Always enable — a freshly installed/updated plugin can land disabled, which
    # is exactly the failure mode where seeds:* skills never appear in sessions.
    claude("plugin", "enable", plugin, "--scope", "user")

    click.echo(f"seeds plugin {action} and enabled.")
    click.echo("Start a new Claude Code session to load the seeds:* skills.")


if __name__ == "__main__":
    main()
