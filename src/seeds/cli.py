"""seeds CLI entry point."""

from __future__ import annotations

import functools
import shlex
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, NamedTuple

import click

from seeds import __version__
from seeds.beads import load_bead_ids
from seeds.check import (
    GitUnavailable,
    check_against_git,
    check_smells,
    check_violations,
    format_findings,
)
from seeds.convert import ConversionError, convert, format_report
from seeds.history import format_history, seed_history
from seeds.jsonexport import ExportError, export_json
from seeds.legacy import JSONL_FILE
from seeds.models import (
    DEFAULT_PREFIX,
    RelationType,
    SeedStatus,
    SeedType,
    find_id_ref_candidates,
    is_allowlisted_prose,
    now_utc,
    parse_since,
    sanitize_prefix,
)
from seeds.seedfile import SeedFileError, SeedRecord, render_body, seed_files_dir
from seeds.store import (
    CONFIG_FILE,
    SEEDS_DIR,
    Store,
    StoreError,
    find_seeds_dir,
    has_been_edited,
    is_terminal,
    needs_conversion,
    new_record,
    questions_asked_about,
    relates_to,
)


def _uninitialized_error(seeds_dir: Path) -> str:
    """The right recovery to name when there is no store.

    Three states hide behind "no seed files", and sending all of them to
    `seeds init` is wrong for the one that matters most. A repo that has not
    converted yet still carries the pre-0.7 `.seeds/seeds.jsonl`, and `seeds
    init` refuses there, reporting the directory as already initialized -- the
    same closed loop bead seeds-1j3 broke for the database, in its new shape.
    That repo needs `seeds convert`, not `seeds init`.
    """
    if not seeds_dir.exists():
        return "Error: seeds not initialized. Run 'seeds init' first."

    if needs_conversion(seeds_dir):
        return (
            f"Error: no seed files in {seed_files_dir(seeds_dir)}, but "
            f"{seeds_dir / JSONL_FILE} is present.\n"
            "This project has not been converted to the seed-file store yet. "
            "Run 'seeds convert'."
        )
    return "Error: seeds not initialized. Run 'seeds init' first."


def _resolve_seeds_dir() -> Path:
    """The ``.seeds`` this invocation is about, whether or not it is usable."""
    return find_seeds_dir() or Path.cwd() / SEEDS_DIR


class Context:
    """CLI context object holding the seed-file store."""

    def __init__(self) -> None:
        self.store: Store | None = None

    def get_store(self) -> Store:
        """The store for the nearest ``.seeds`` directory.

        Exits with an error naming the right recovery when there is no store
        to read -- see :func:`_uninitialized_error`.
        """
        if self.store is None:
            seeds_dir = _resolve_seeds_dir()
            store = Store(seeds_dir)
            if not store.is_initialized():
                click.echo(_uninitialized_error(seeds_dir), err=True)
                sys.exit(1)
            self.store = store
        return self.store

    def ensure_init(self) -> Store:
        """Ensure the store exists, error if not."""
        return self.get_store()


pass_context = click.make_pass_decorator(Context, ensure=True)


def _validate_id_refs(
    store: Store, texts: list[str | None], allow_unknown: bool
) -> None:
    """Verify every project-prefixed token in ``texts`` names something real.

    Catches the common failure where an agent drafts a body like
    ``see seeds-117`` — or, now that IDs are base36, ``see seeds-zq4x`` — with
    an ID that never existed. Each ``<prefix>-…`` token is a candidate, checked
    in turn against:

    1. **seed IDs** — the store;
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
    prefix = store.get_prefix()
    candidates: set[str] = set()
    for text in texts:
        if not text:
            continue
        candidates.update(find_id_ref_candidates(text, prefix))
    if not candidates:
        return
    bead_ids = load_bead_ids(store.seeds_dir)
    unknown = sorted(
        ref
        for ref in candidates
        if not store.exists(ref)
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


def _guard_content_replacement(record: SeedRecord, copy: GuardCopy) -> None:
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
    if not record.body.strip() or not has_been_edited(record):
        return

    first_line = record.body.strip().splitlines()[0]
    if len(first_line) > 72:
        first_line = first_line[:69] + "..."

    click.echo(
        f"Error: {record.id} {copy.reason} -- {copy.subject} "
        f"would discard {len(record.body)} characters of deliberation.",
        err=True,
    )
    click.echo(f"  Would discard: {first_line}", err=True)
    click.echo(f"  Add to it instead:      {copy.append_cmd}", err=True)
    click.echo(f"  Discard it on purpose:  {copy.replace_cmd}", err=True)
    click.echo(
        "  --replace does not erase anything: the old body survives in the "
        "seed file's git history and needs separate scrubbing.",
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


def _apply_tag_edits(
    record: SeedRecord, add: Sequence[str], remove: Sequence[str]
) -> str:
    """Add/remove individual tags in place; return a report of what happened.

    Removals run first and additions append to the tail, so tags the command
    did not name keep their authored positions -- re-sorting would churn the
    diff of every touched seed file for no reason.

    Naming a tag the seed does not carry (or one it already has) is a silent
    no-op, per the locked decision on this command: with an agent driving a
    batch, erroring mid-loop is worse than finishing. The counts are what
    actually happened, so a typo lands as "0 removed" rather than vanishing.
    """
    to_add = _clean_tags(add)
    to_remove = _clean_tags(remove)

    removed = sum(1 for t in to_remove if t in record.tags)
    if to_remove:
        drop = set(to_remove)
        record.tags = [t for t in record.tags if t not in drop]

    added = 0
    for tag in to_add:
        if tag not in record.tags:
            record.tags.append(tag)
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
    store = Store(seeds_dir)
    if seeds_dir.exists():
        # The directory existing is not the same as the project being usable.
        # The seed-file store settles that.
        if store.is_initialized():
            click.echo(f"seeds already initialized in {seeds_dir}")
            return
        jsonl_path = seeds_dir / JSONL_FILE
        if jsonl_path.exists():
            click.echo(
                f"{seeds_dir} exists but holds no seed files, and "
                f"{jsonl_path.name} is present."
            )
            click.echo(
                "This project has not been converted to the seed-file store "
                "yet. Run 'seeds convert'."
            )
            return
        # An empty .seeds/ with nothing to convert: carry on and initialize,
        # rather than refusing over a bare directory.

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

    store.files_dir.mkdir(parents=True, exist_ok=True)
    store.set_prefix(prefix)
    click.echo(f"Initialized seeds in {seeds_dir}")
    click.echo(f"  Project prefix: {prefix}")
    click.echo(f"  Seed files live in {store.files_dir}/ and are tracked by git")
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
    store = ctx.get_store()

    # Generate ID (child ID if parent specified)
    if parent_id:
        # Verify parent exists
        if not store.exists(parent_id):
            click.echo(f"Error: Parent seed '{parent_id}' not found.", err=True)
            sys.exit(1)
        seed_id = store.next_child_id(parent_id)
    else:
        seed_id = store.next_id(seed_text=title)

    _validate_id_refs(store, [title, content], allow_unknown_refs)

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    store.create(
        new_record(
            seed_id,
            title,
            body=content,
            seed_type=seed_type,
            tags=tag_list,
        )
    )
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

    Refusing on an unconverted store is right; losing the thought with it is
    not. jot is the minimum-friction verb whose whole job is catching an idea
    before it escapes, and first contact with an unconverted repo happens
    mid-thought, so the refusal prints the text back and the exact command to
    re-run (seeds-4co.18).
    """
    seeds_dir = _resolve_seeds_dir()
    if not Store(seeds_dir).is_initialized():
        click.echo(_uninitialized_error(seeds_dir), err=True)
        click.echo("", err=True)
        click.echo("Nothing was written. Your thought, so it survives:", err=True)
        click.echo("", err=True)
        click.echo(f"  {thought}", err=True)
        click.echo("", err=True)
        click.echo("Re-run it once the store is usable:", err=True)
        click.echo(f"  seeds jot {shlex.quote(thought)}", err=True)
        sys.exit(1)

    store = ctx.get_store()

    seed_id = store.next_id(seed_text=thought)
    store.create(new_record(seed_id, thought))
    click.echo(f"{seed_id}: {thought}")


# Valid statuses for CLI
SEED_STATUSES = [s.value for s in SeedStatus]


STATUS_ICONS = {
    SeedStatus.CAPTURED: "○",
    SeedStatus.EXPLORING: "◐",
    SeedStatus.DEFERRED: "◌",
    SeedStatus.RESOLVED: "●",
    SeedStatus.ABANDONED: "✗",
}


def format_seed_line(record: SeedRecord, store: Store) -> str:
    """Format a seed for list output."""
    status_icon = STATUS_ICONS.get(record.status, "?")
    blocked = " [BLOCKED]" if store.is_blocked(record.id) else ""
    tags = f" [{', '.join(record.tags)}]" if record.tags else ""

    return f"{status_icon} {record.id}: {record.title}{blocked}{tags}"


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
    store = ctx.get_store()

    status_enum = SeedStatus(status) if status else None

    since_dt = None
    if since_value:
        try:
            since_dt = parse_since(since_value)
        except ValueError as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

    records = store.list_seeds(
        status=status_enum,
        seed_type=seed_type,
        tag=tag,
        include_terminal=include_all,
        since=since_dt,
        sort_by=sort_by,
    )

    if not records:
        click.echo("No seeds found.")
        return

    for record in records:
        click.echo(format_seed_line(record, store))


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
    store = ctx.get_store()

    try:
        since_dt = parse_since(since_value)
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    records = store.list_seeds(
        since=since_dt,
        sort_by="updated",
        include_terminal=include_all,
    )

    if not records:
        click.echo(f"No seeds updated since {since_value}.")
        return

    for record in records:
        click.echo(format_seed_line(record, store))


def format_seed_detail(
    record: SeedRecord,
    store: Store,
    include_questions: bool = False,
    full: bool = False,
) -> str:
    """Format seed details as a string.

    The body is rendered *selectively* by default: text inside a superseded
    scope is dropped, while the retired heading and its marker line stay, so a
    reader sees that something was retired and why. ``full=True`` prints
    everything. Nothing is ever removed from the file to achieve this — the
    render is what is selective (docs/storage-format.md §7).
    """
    lines = []

    # Header
    lines.append(f"{record.id}: {record.title}")
    lines.append(f"  Status: {record.status.value}")
    lines.append(f"  Type: {record.seed_type}")

    if record.resolution:
        lines.append(f"  Resolution: {record.resolution}")

    if record.tags:
        lines.append(f"  Tags: {', '.join(record.tags)}")

    if record.parent:
        lines.append(f"  Parent: {record.parent}")

    # Check if blocked
    if store.is_blocked(record.id):
        lines.append("  [BLOCKED by unresolved children]")

    # Show children
    children = store.get_children(record.id)
    if children:
        lines.append(f"  Children: {len(children)}")
        for child in children:
            status_mark = "●" if is_terminal(child) else "○"
            lines.append(f"    {status_mark} {child.id}: {child.title}")

    # Show related (both ends of every relates-to edge are in this file)
    related_ids = relates_to(record)
    if related_ids:
        lines.append(f"  Related to: {', '.join(related_ids)}")

    # Content
    body = render_body(record.body, full=full).rstrip("\n")
    if body:
        lines.append("")
        lines.append("Content:")
        lines.append(body)

    # Questions (question-seeds linked via 'questions' relationship)
    if include_questions:
        question_seeds = store.questions_for(record.id)
        if question_seeds:
            lines.append("")
            lines.append("Questions:")
            for qs in question_seeds:
                status_mark = "●" if is_terminal(qs) else "○"
                lines.append(f"  {status_mark} {qs.id}: {qs.title}")
                if qs.body.strip():
                    body = render_body(qs.body, full=full).rstrip("\n")
                    lines.append(f"    → {body}")

    return "\n".join(lines)


@main.command()
@click.argument("query")
@click.option("--all", "include_all", is_flag=True, help="Include resolved/abandoned")
@pass_context
def search(ctx: Context, query: str, include_all: bool) -> None:
    """Search seed files with ripgrep.

    QUERY is a ripgrep regular expression, matched case-insensitively over the
    whole seed file -- body, title and the rest of the frontmatter. Resolved
    and abandoned seeds are excluded unless --all is passed, and that filter is
    part of the ripgrep pass rather than a scan afterwards.

      - Simple words:  seeds search deliberation
      - Phrases:       seeds search 'agent reasoning'
      - Alternation:   seeds search 'agent|sweep'
      - Anchors, classes, and the rest of the regex vocabulary all work.

    This replaced an FTS5 index, and the difference worth knowing is that there
    is no stemmer: 'merging' no longer finds 'merge'. What FTS uniquely
    provided was ranking, not recall -- measured on a real query, grep returned
    72 hits to FTS's 77 and found one FTS missed.
    """
    store = ctx.get_store()

    try:
        results = store.search(query, include_terminal=include_all)
    except StoreError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if not results:
        click.echo(f"No seeds matching '{query}'.")
        return

    click.echo(f"Found {len(results)} seed(s):")
    for record in results:
        click.echo(format_seed_line(record, store))


@main.command()
@click.argument("seed_id")
@click.option("--questions", "-q", is_flag=True, help="Include attached questions")
@click.option(
    "--full",
    is_flag=True,
    help=(
        "Print superseded text too. By default a superseded scope's text is "
        "dropped and only its heading and marker line are shown."
    ),
)
@click.option(
    "--output-file",
    "-o",
    is_flag=True,
    help="Write to temp file, print path (for Claude Code)",
)
@pass_context
def show(
    ctx: Context, seed_id: str, questions: bool, full: bool, output_file: bool
) -> None:
    """Show detailed information about a seed.

    The body renders LIVE content: text inside a superseded scope is dropped,
    while the retired heading and its marker line stay, so the reader can see
    that a position was moved past and why. --full prints everything. Nothing
    is removed from the file either way (docs/storage-format.md §7).

    Use --output-file to write output to a temp file and print the path.
    This works around Claude Code CLI terminal truncation issues.
    """
    store = ctx.get_store()

    record = store.get(seed_id)
    if record is None:
        click.echo(f"Error: Seed '{seed_id}' not found.", err=True)
        sys.exit(1)

    output = format_seed_detail(record, store, include_questions=questions, full=full)

    if output_file:
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, prefix=f"seeds-{seed_id}-"
        ) as f:
            f.write(output)
            click.echo(f.name)
    else:
        click.echo(output)


@main.command("history")
@click.argument("seed_id")
@pass_context
def history_cmd(ctx: Context, seed_id: str) -> None:
    """Show how a seed changed, commit by commit, across the conversion.

    Each line is one commit in which this seed actually changed: the date, the
    author, the fields that differ from the previous revision, and the commit
    subject. Commits that touched the store without touching this seed are not
    listed.

    It structures and labels; it NEVER summarises. Naming which fields changed
    is deterministic and every line is checkable against `git show`. Saying what
    a change *meant* is judgment, and a rolling summary of a deliberation is the
    decision log seeds exists not to be -- so that reading is yours to make.

    A seed that predates conversion has its history in two places, and both are
    walked as one chain: its own .seeds/seeds/<id>.md back to the conversion
    commit, and .seeds/seeds.jsonl before it. That file stops being written on
    conversion day, but its git history stays load-bearing forever -- never
    filter it out of the repository as cleanup.
    """
    store = ctx.get_store()

    record = store.get(seed_id)
    if record is None:
        click.echo(f"Error: Seed '{seed_id}' not found.", err=True)
        sys.exit(1)

    try:
        history = seed_history(store.seeds_dir, record)
    except (GitUnavailable, ValueError) as exc:
        click.echo(
            f"Error: cannot read history -- {exc}\n"
            "A seed's evolution lives in git and nowhere else, so there is "
            "nothing to fall back to.",
            err=True,
        )
        sys.exit(1)

    click.echo(format_history(history))


@main.command()
@pass_context
def ready(ctx: Context) -> None:
    """Show captured seeds ready to explore."""
    store = ctx.get_store()

    records = store.list_seeds(status=SeedStatus.CAPTURED)

    if not records:
        click.echo("No captured seeds ready to explore.")
        return

    click.echo("Ready to explore:")
    for record in records:
        click.echo(format_seed_line(record, store))


@main.command()
@pass_context
def deferred(ctx: Context) -> None:
    """Show deferred seeds (backlog)."""
    store = ctx.get_store()

    records = store.list_seeds(status=SeedStatus.DEFERRED)

    if not records:
        click.echo("No deferred seeds.")
        return

    click.echo("Deferred (backlog):")
    for record in records:
        click.echo(format_seed_line(record, store))


@main.command()
@pass_context
def blocked(ctx: Context) -> None:
    """Show seeds blocked by unresolved children or questions."""
    store = ctx.get_store()

    records = store.blocked()

    if not records:
        click.echo("No blocked seeds.")
        return

    click.echo("Blocked seeds:")
    for record in records:
        click.echo(f"  {record.id}: {record.title}")
        # Show unresolved children
        for child in store.get_children(record.id):
            if not is_terminal(child):
                click.echo(f"    ○ {child.id}: {child.title}")
        # Show unresolved question-seeds
        for qs in store.questions_for(record.id):
            if not is_terminal(qs):
                click.echo(f"    ? {qs.id}: {qs.title}")


# --- Status change commands ---


def get_seed_or_exit(store: Store, seed_id: str) -> SeedRecord:
    """Get a seed by ID or exit with error."""
    record = store.get(seed_id)
    if record is None:
        click.echo(f"Error: Seed '{seed_id}' not found.", err=True)
        sys.exit(1)
    return record


@main.command()
@click.argument("seed_id")
@pass_context
def explore(ctx: Context, seed_id: str) -> None:
    """Start exploring a seed (captured → exploring)."""
    store = ctx.get_store()
    record = get_seed_or_exit(store, seed_id)

    if record.status != SeedStatus.CAPTURED:
        click.echo(f"Warning: Seed is {record.status.value}, not captured.")

    record.status = SeedStatus.EXPLORING
    # Leaving a terminal state clears the stamp: resolved_at is forbidden
    # unless the status is terminal (docs/storage-format.md §3).
    record.resolved_at = None
    store.save(record)
    click.echo(f"◐ {seed_id}: Now exploring")


@main.command()
@click.argument("seed_id")
@pass_context
def defer(ctx: Context, seed_id: str) -> None:
    """Defer a seed to the backlog."""
    store = ctx.get_store()
    record = get_seed_or_exit(store, seed_id)

    record.status = SeedStatus.DEFERRED
    record.resolved_at = None
    store.save(record)
    click.echo(f"◌ {seed_id}: Deferred to backlog")


@main.command()
@click.argument("seed_id")
@click.option("--resolution", "-r", help="What was decided or what happened")
@pass_context
def resolve(ctx: Context, seed_id: str, resolution: str | None) -> None:
    """Mark a seed as resolved."""
    store = ctx.get_store()
    record = get_seed_or_exit(store, seed_id)

    record.status = SeedStatus.RESOLVED
    record.resolved_at = now_utc()
    if resolution:
        record.resolution = resolution
    store.save(record)
    click.echo(f"● {seed_id}: Resolved")
    if resolution:
        click.echo(f"  Resolution: {resolution}")


@main.command()
@click.argument("seed_id")
@click.option("--reason", "-r", help="Reason for abandoning")
@pass_context
def abandon(ctx: Context, seed_id: str, reason: str | None) -> None:
    """Abandon a seed (decided not to pursue)."""
    store = ctx.get_store()
    record = get_seed_or_exit(store, seed_id)

    record.status = SeedStatus.ABANDONED
    record.resolved_at = now_utc()
    if reason:
        record.resolution = reason
    store.save(record)
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
    from seeds.trellis import append_to_managed_section

    store = ctx.get_store()
    record = get_seed_or_exit(store, seed_id)

    date_str = now_utc().strftime("%Y-%m-%d")
    bullet = f"- {principle} — {record.id}, {date_str}"

    # Forward-provenance: file -> seed (the bullet cites the seed id).
    path = Path(target_file)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        append_to_managed_section(existing, section, bullet), encoding="utf-8"
    )

    # Back-provenance: seed -> file (the resolution names the file + date).
    record.resolution = (
        f"Recorded as a trellis in `{target_file}` on {date_str}: {principle}"
    )
    if "trellis" not in record.tags:
        record.tags.append("trellis")

    if not no_resolve:
        record.status = SeedStatus.RESOLVED
        record.resolved_at = now_utc()

    store.save(record)

    # Echo both ends of the link: the appended bullet and the new resolution.
    click.echo(f"● {record.id}: trellis → {target_file}")
    click.echo(f"  {bullet}")
    click.echo(f"  Resolution: {record.resolution}")
    click.echo(f"  Status: {record.status.value}")


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
    the store -- which is how the malformed records in seed seeds-1x6b got in.
    """
    store = ctx.get_store()
    record = get_seed_or_exit(store, seed_id)

    content = _resolve_content(content, content_file)

    _validate_id_refs(store, [title, content, append_text], allow_unknown_refs)
    _reject_ambiguous_tag_flags(tags, add_tags, remove_tags)

    if content is not None and not replace:
        _guard_content_replacement(
            record,
            GuardCopy(
                reason="has been edited since it was created",
                subject="--content",
                append_cmd=f'seeds update {record.id} --append "..."',
                replace_cmd=f'seeds update {record.id} --content "..." --replace',
            ),
        )

    changed = False

    if title:
        record.title = title
        changed = True

    if content is not None:
        record.body = content
        changed = True

    if append_text:
        # rstrip first: a body read off disk ends with the file's trailing
        # newline, and concatenating onto it would separate the append with
        # three newlines instead of the one blank line an append means.
        record.body = f"{record.body.rstrip()}\n\n{append_text}".strip()
        changed = True

    if tags is not None:
        record.tags = [t.strip() for t in tags.split(",")] if tags else []
        changed = True

    if seed_type:
        record.seed_type = seed_type
        changed = True

    tag_report = None
    if add_tags or remove_tags:
        before = list(record.tags)
        tag_report = _apply_tag_edits(record, add_tags, remove_tags)
        # A request that matched nothing leaves updated_at alone, so it cannot
        # arm the --content guard on a seed nobody actually edited.
        changed = changed or record.tags != before

    if not changed:
        click.echo(tag_report or "No changes specified.")
        return

    store.save(record)
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
    store = ctx.get_store()

    # Verify seed exists
    if not store.exists(seed_id):
        click.echo(f"Error: Seed '{seed_id}' not found.", err=True)
        sys.exit(1)

    question_id = store.next_id(seed_text=question_text)
    store.create(
        new_record(
            question_id,
            question_text,
            seed_type=SeedType.QUESTION.value,
        )
    )
    store.link(question_id, seed_id, RelationType.QUESTIONS)
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
        "deliberate correction only -- the old answer stays in the seed "
        "file's git history and needs separate scrubbing."
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

    store = ctx.get_store()

    question_seed = store.get(question_id)
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
        question_seed.body = f"{question_seed.body.rstrip()}\n\n{answer_text}".strip()
    else:
        question_seed.body = answer_text
    question_seed.status = SeedStatus.RESOLVED
    question_seed.resolved_at = now_utc()
    store.save(question_seed)
    click.echo(f"● {question_id}: {question_seed.title}")
    click.echo(f"  → {answer_text}")


@main.command()
@click.option("--seed", "seed_id", help="Filter by seed ID")
@pass_context
def questions(ctx: Context, seed_id: str | None) -> None:
    """List open questions (question-type seeds that are unresolved)."""
    store = ctx.get_store()

    if seed_id:
        # Get question-seeds for a specific seed
        qs = [q for q in store.questions_for(seed_id) if not is_terminal(q)]
    else:
        # Get all unresolved question-type seeds
        qs = store.list_seeds(seed_type=SeedType.QUESTION.value, include_terminal=False)

    if not qs:
        click.echo("No open questions.")
        return

    click.echo("Open questions:")
    for q in qs:
        # Find which seed this question is about
        asked_about = questions_asked_about(q)
        if asked_about:
            target = store.get(asked_about[0])
            target_title = target.title if target else "?"
            click.echo(f"  ○ {q.id}: {q.title}")
            click.echo(f"    └─ {asked_about[0]}: {target_title}")
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
    store = ctx.get_store()

    record = get_seed_or_exit(store, seed_id)
    if not store.exists(related_id):
        click.echo(f"Error: Seed '{related_id}' not found.", err=True)
        sys.exit(1)

    rel_type_enum = RelationType(rel_type)

    # Check if already linked
    if any(
        edge.target_id == related_id and edge.rel_type is rel_type_enum
        for edge in record.relationships
    ):
        click.echo(f"Already linked: {seed_id} ↔ {related_id}")
        return

    try:
        store.link(seed_id, related_id, rel_type_enum)
    except StoreError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if rel_type_enum == RelationType.RELATES_TO:
        click.echo(f"Linked: {seed_id} ↔ {related_id}")
    else:
        click.echo(f"Linked: {seed_id} —[{rel_type}]→ {related_id}")


@main.command()
@click.argument("seed_id")
@pass_context
def tree(ctx: Context, seed_id: str) -> None:
    """Show hierarchy and relationships for a seed."""
    store = ctx.get_store()

    record = get_seed_or_exit(store, seed_id)

    def print_seed(s: SeedRecord, indent: int = 0) -> None:
        prefix = "  " * indent
        status_icon = STATUS_ICONS.get(s.status, "?")
        click.echo(f"{prefix}{status_icon} {s.id}: {s.title}")

    # Show parent chain
    parent_chain: list[SeedRecord] = []
    current_id = record.parent
    while current_id:
        parent = store.get(current_id)
        if parent:
            parent_chain.insert(0, parent)
            current_id = parent.parent
        else:
            break

    if parent_chain:
        click.echo("Ancestors:")
        for i, p in enumerate(parent_chain):
            print_seed(p, i)

    # Show current seed
    click.echo()
    click.echo("Current:")
    print_seed(record, 0)

    # Show children
    children = store.get_children(seed_id)
    if children:
        click.echo()
        click.echo("Children:")
        for child in children:
            print_seed(child, 1)
            # Show grandchildren
            for gc in store.get_children(child.id):
                print_seed(gc, 2)

    # Show related (both ends of every edge live in this seed's own file)
    related_ids = relates_to(record)
    if related_ids:
        click.echo()
        click.echo("Related:")
        for related_id in related_ids:
            related = store.get(related_id)
            if related:
                click.echo(f"  ↔ {related.id}: {related.title}")
            else:
                click.echo(f"  ↔ {related_id}: (not found)")


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

    On an UNCONVERTED project it still emits the full document and still exits
    0 -- but the document carries the conversion notice twice, once at the top
    and once where the project-state block would have been. Returning
    normal-looking context there was the defect (seeds-4co.18): the static half
    rendered, the state block vanished silently, and an agent reading it
    concluded the project had no seeds.
    """
    from seeds.prime import get_prime_output

    # Check if we're in a seeds project
    seeds_dir = find_seeds_dir()
    if seeds_dir is None:
        # Not in a seeds project - silent exit with success
        # CRITICAL: No output, exit 0 to enable hook coexistence
        return

    store = Store(seeds_dir)
    if not store.is_initialized():
        # A .seeds/ that holds no seed files yet -- an unconverted project, or
        # one mid-init. The static workflow text is still the right answer;
        # only the digest needs a store. Which of the two it is decides whether
        # the reader is told a block is missing.
        click.echo(
            get_prime_output(
                include_digest=False,
                unconverted=needs_conversion(seeds_dir),
            )
        )
        return

    click.echo(
        get_prime_output(
            store=store,
            include_digest=not no_digest,
            digest_limit=digest_limit,
        )
    )


@main.command()
@pass_context
def doctor(ctx: Context) -> None:
    """Check for issues with the seeds installation and store.

    Reports what is true of this project: the store is there, the prefix is
    recorded, the seeds read, no edge names a missing seed, the type
    vocabulary has not drifted. It does NOT verify the files themselves --
    that is `seeds check`, which reads the same tree and gates on it.
    """
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

    # Check the store
    click.echo("Store:")
    store = ctx.get_store()
    check_pass(f"Seed files at {store.files_dir}")

    # Report project prefix and nudge the user when the default doesn't
    # match the project directory name.
    click.echo()
    click.echo("Project:")
    current_prefix = store.get_prefix()
    if store.has_prefix_configured():
        check_pass(f"Prefix configured: {current_prefix!r}")
    else:
        check_warn(
            "Prefix",
            f"Using fallback {current_prefix!r}; run 'seeds rename-prefix "
            f"<name>' to record one in {store.seeds_dir / CONFIG_FILE}",
        )
    derived = sanitize_prefix(store.seeds_dir.parent.name)
    if current_prefix == DEFAULT_PREFIX and derived and derived != DEFAULT_PREFIX:
        check_warn(
            "Prefix",
            f"Default prefix {DEFAULT_PREFIX!r} doesn't match project dir; "
            f"run 'seeds rename-prefix {derived}' to customize",
        )

    # Check seeds. A strict read refuses the whole corpus on one bad file, so
    # this is also where an unreadable seed surfaces -- and it names the file,
    # which is the only thing doctor could usefully say about it.
    click.echo()
    click.echo("Seeds:")
    try:
        all_seeds = store.all()
    except (SeedFileError, StoreError) as exc:
        check_fail("Seeds", str(exc))
        click.echo("      Run 'seeds check' to see every bad file at once.")
        click.echo()
        click.echo("─" * 40)
        click.echo(f"✓ {passed} passed  ✗ {failed} failed")
        sys.exit(1)

    check_pass(f"{len(all_seeds)} seeds total")

    open_seeds = store.list_seeds(include_terminal=False)
    if open_seeds:
        check_pass(f"{len(open_seeds)} open seeds")
    else:
        check_warn("Seeds", "No open seeds")

    # Edges whose far end names a file that is not there. The foreign key
    # SQLite used to enforce is a file-existence test now, so it has to be
    # asked rather than assumed.
    click.echo()
    click.echo("Relationships:")
    edges = 0
    dangling: list[str] = []
    for record in all_seeds:
        for edge in record.relationships:
            edges += 1
            if not store.exists(edge.target_id):
                dangling.append(f"{record.id} -> {edge.target_id}")
    if not dangling:
        check_pass(f"{edges} edges, none dangling")
    else:
        check_fail("Relationships", f"{len(dangling)} edge(s) name a missing seed")
        for pair in dangling[:10]:
            click.echo(f"      {pair}")
        if len(dangling) > 10:
            click.echo(f"      ... and {len(dangling) - 10} more")
        click.echo("      Run 'seeds check' for the full picture.")

    # Check for open question-seeds
    open_questions = store.list_seeds(
        seed_type=SeedType.QUESTION.value, include_terminal=False
    )
    if open_questions:
        check_pass(f"{len(open_questions)} open questions")

    # Vocabulary drift. With seed_type an open string (seeds-0lb), this is the
    # only thing that surfaces a typo, so it is load-bearing rather than
    # cosmetic. A non-standard type is legal, hence a warning and not a failure.
    nonstandard: dict[str, int] = {}
    for record in all_seeds:
        if record.seed_type not in SEED_TYPES:
            nonstandard[record.seed_type] = nonstandard.get(record.seed_type, 0) + 1
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

    # There is no second store to disagree with, so there is nothing here to
    # check. `seeds doctor` used to end with a JSONL/DB comparison, and every
    # question it answered -- do the two agree, will an import refuse a record
    # -- stopped existing with the store that made them possible. Leaving those
    # checks in place, passing, would be the exact "green while broken" shape
    # they were written to prevent: a check that cannot fail is not a check.
    # File-level plausibility now lives in `seeds check`, which reads the same
    # files this does and gates on them.
    click.echo()
    click.echo("Verification:")
    click.echo("  → Run 'seeds check' to verify the files themselves.")

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
@click.option(
    "--smells",
    is_flag=True,
    help=(
        "Also report smells: an empty body, a long body with many commits and "
        "no supersede marker, a body byte-identical to another seed's, a "
        "resolution on a non-terminal seed, a file whose bytes are not the "
        "canonical form, and a repo-wide tool configured without excluding "
        ".seeds/. Never affects the exit code."
    ),
)
@click.option(
    "--against-git",
    "against_git",
    is_flag=True,
    help=(
        "Also compare every field with its value at the previous commit and "
        "fail on one field rewritten across a large fraction of the corpus."
    ),
)
def check_cmd(smells: bool, against_git: bool) -> None:
    """Verify the seed files are plausible, not merely parseable.

    The violations tier runs always: every finding there is either a file the
    reader would refuse or a value that parses perfectly and is not credible --
    a title that is a filesystem path, an edge written at one end only, a stamp
    ahead of the clock. It exits non-zero, so it can gate a commit or a
    conversion.

    Content plausibility is the job because format validity had nothing to say
    when a bulk sweep replaced 83 titles with a scratchpad path (seeds-wurl):
    every record parsed, both stores agreed, and every divergence check was
    correctly green for three days.

    --against-git is the tier that catches that particular sweep, and it gates
    too: a commit rewriting most of the corpus in one field has no cheap human
    review, so it needs a decision rather than a glance.

    --smells is the tier that does not gate. Nothing it prints is an error, and
    nothing it prints reaches the exit code -- it reports the things worth
    noticing that cannot carry being a gate.
    """
    seeds_dir = find_seeds_dir()
    if seeds_dir is None:
        click.echo("Error: seeds not initialized. Run 'seeds init' first.", err=True)
        sys.exit(1)
    if needs_conversion(seeds_dir):
        # Otherwise this reports store-missing as a bare path, which is a true
        # statement of a symptom and no help at all on an unconverted repo.
        click.echo(_uninitialized_error(seeds_dir), err=True)
        sys.exit(1)

    findings = check_violations(seeds_dir)
    if findings:
        click.echo(format_findings(findings), nl=False)
        click.echo()
        click.echo(f"seeds check: {len(findings)} violation(s).")
    else:
        count = len(list(seed_files_dir(seeds_dir).glob("*.md")))
        click.echo(f"seeds check: {count} files, no violations.")
    failed = bool(findings)

    if against_git:
        # A comparison the operator explicitly asked for that could not run is
        # the exact "green while broken" shape this tier exists to prevent, so
        # no git means a loud failure rather than a quiet skip. An unborn HEAD
        # is not that case: it is a real, empty before-state.
        try:
            comparison = check_against_git(seeds_dir)
        except GitUnavailable as exc:
            click.echo(f"Error: seeds check --against-git: {exc}", err=True)
            sys.exit(1)
        click.echo()
        click.echo(
            f"seeds check --against-git: {comparison.corpus} seed(s) at "
            f"{comparison.before}, compared with {comparison.after}."
        )
        if comparison.findings:
            click.echo(format_findings(comparison.findings), nl=False)
            click.echo(f"seeds check: {len(comparison.findings)} mass rewrite(s).")
            failed = True

    if smells:
        smell_findings = check_smells(seeds_dir)
        click.echo()
        if smell_findings:
            click.echo(format_findings(smell_findings, marker="⚠"), nl=False)
        click.echo(
            f"seeds check --smells: {len(smell_findings)} smell(s) — reporting "
            f"only, never a failure."
        )

    if failed:
        sys.exit(1)


@main.command("convert")
@click.option(
    "--keep-fixtures",
    is_flag=True,
    help=("Convert the six ruled test-fixture seeds too, instead of dropping them."),
)
def convert_cmd(keep_fixtures: bool) -> None:
    """Convert the SQLite + JSONL store into the .seeds/seeds/ markdown tree.

    Reads the UNION of the two stores, per id and per field. Never "the
    database, reconciled against the file" -- that would rebuild the
    derived-store-overwrites-durable-store shape inside the migration itself.

    Every id is classified before anything is written: db-only, jsonl-only,
    db-extends-disk, or fork. Only the first three are resolved by rule. A fork
    -- two bodies where neither is a prefix of the other -- lands as a file
    carrying both, with git conflict markers, for ordinary merge tooling.

    The tree is written alongside the pre-0.7 seeds.db and seeds.jsonl, and
    neither is rewritten. Re-running against an unchanged store rewrites
    nothing.

    seeds.jsonl is then RETIRED: where git can restore it -- inside a work
    tree, tracked, and with no uncommitted changes -- its deletion is staged,
    so the removal lands in the same commit as the seed files. Failing any one
    of those three, the file is left alone and this says which one failed. The
    FILE is disposable; its git HISTORY must never be rewritten or filtered
    out of the repository, because `seeds history` reads it for everything
    before a seed's converted_at. seeds.db is never deleted, for the opposite
    reason: .seeds/.gitignore excludes *.db, so git holds no copy of it.

    Every run prints the exact command that reverts the state it created.

    Exits non-zero while a fork is unresolved or `seeds check` reports a
    violation on the output: the data landed, but the store is not finished.
    """
    seeds_dir = find_seeds_dir()
    if seeds_dir is None:
        click.echo("Error: seeds not initialized. Run 'seeds init' first.", err=True)
        sys.exit(1)

    try:
        report = convert(seeds_dir, keep_fixtures=keep_fixtures)
    except ConversionError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(format_report(report))
    if report.check_findings:
        click.echo()
        click.echo(format_findings(report.check_findings), nl=False)
    if not report.clean:
        sys.exit(1)


@main.command("export")
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Emit the corpus as JSON (one object per line) on stdout.",
)
def export_cmd(as_json: bool) -> None:
    """Write the whole corpus to stdout as JSON. Creates no file.

    This serves STRUCTURED EXTRACTION: a consumer that wants fields, not
    matches -- counts by status, a join against beads, anything you would write
    SQL for. Pipe it into DuckDB on demand:

    \b
        seeds export --json | duckdb -c "SELECT status, count(*)
          FROM read_json_auto('/dev/stdin') GROUP BY 1"

    FULL-TEXT SEARCH ACROSS REPOS IS RIPGREP'S JOB, not this command's. A seed
    is a markdown file, so it is one glob over the stores:

    \b
        rg -l "adjudicat" ~/projects/*/.seeds/seeds/
        rg -i -C2 "immutable row" ~/projects/*/.seeds/seeds/

    which is better than what it replaces -- the seed id is in the path and you
    get real context lines, where grepping the retired `.seeds/seeds.jsonl`
    returned a 120-character slice of one escaped line.

    So this command exists because a pipe to stdout costs nothing -- no second
    store, nothing to diverge, nothing to sync -- and NOT because searching
    across repos needs it. One JSON object per line, so a grep hit is still a
    whole record and several repos' output concatenates into one stream.

    Either the whole corpus is written or nothing is: a file the reader refuses
    aborts before the first byte, because a stream that stops halfway looks
    exactly like a repo with fewer seeds.
    """
    if not as_json:
        # JSON is the only format, but a bare `seeds export` must not guess.
        # The retired command of this name wrote a tracked file; anyone typing
        # it from muscle memory should be told the shape changed, not handed a
        # megabyte of stdout.
        click.echo(
            "Error: 'seeds export' needs a format. Pass --json to write the "
            "corpus to stdout as JSON; it is the only format.",
            err=True,
        )
        sys.exit(2)

    seeds_dir = find_seeds_dir()
    if seeds_dir is None:
        click.echo("Error: seeds not initialized. Run 'seeds init' first.", err=True)
        sys.exit(1)
    if needs_conversion(seeds_dir):
        # Ahead of export_json, which would otherwise report the missing tree
        # as a bare path and leave the reader to work out the recovery.
        click.echo(_uninitialized_error(seeds_dir), err=True)
        sys.exit(1)

    try:
        export_json(seeds_dir, sys.stdout)
    except ExportError as exc:
        click.echo(f"Error: {exc}", err=True)
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

    There is no backup step. The seed files are tracked, so `git diff` shows
    exactly what changed and `git checkout` undoes it -- which is a better
    backup than the sidecar copy this used to take of a gitignored database.
    """
    store = ctx.get_store()

    if from_type == to_type:
        click.echo(f"--from and --to are both {from_type!r}; nothing to do.")
        return

    ids = store.retype(from_type, to_type, dry_run=dry_run)

    if not ids:
        click.echo(f"No seeds have type {from_type!r}; nothing to do.")
        return

    if dry_run:
        click.echo("DRY RUN — no changes will be written.")

    verb = "Would retype" if dry_run else "Retyped"
    click.echo(f"{verb} {len(ids)} seed(s) from {from_type!r} to {to_type!r}:")
    for seed_id in ids:
        click.echo(f"  {seed_id}")

    if dry_run:
        click.echo("\nRun without --dry-run to apply.")


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
    letters, digits, and hyphens. The current prefix is read from
    ``.seeds/config.yaml``; all top-level IDs (and their children, and every
    edge at both ends) using the old prefix are rewritten, and the seed files
    are renamed to match. ID references inside seed bodies (``title``,
    ``body``, ``resolution``) are also rewritten unless
    ``--no-rewrite-bodies`` is passed.
    """
    store = ctx.get_store()

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

    old_prefix = store.get_prefix()
    if old_prefix == sanitized:
        click.echo(f"Prefix already set to {sanitized!r}; nothing to do.")
        return

    try:
        id_map, body_changes = store.rename_prefix(
            sanitized,
            old_prefix=old_prefix,
            rewrite_bodies=rewrite_bodies,
            dry_run=dry_run,
        )
    except StoreError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if dry_run:
        click.echo("DRY RUN — no changes will be written.")

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

    if id_map:
        click.echo(
            f"\nRenamed {len(id_map)} file(s) under {store.files_dir}. "
            "`git status` shows the renames; `seeds check` verifies them."
        )


@main.command("prefix")
@pass_context
def show_prefix(ctx: Context) -> None:
    """Show the current project prefix."""
    store = ctx.get_store()
    click.echo(store.get_prefix())


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
