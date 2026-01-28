"""SEEDS CLI entry point."""

import functools
import sys
from pathlib import Path

import click

from seeds import __version__
from seeds.db import Database, SEEDS_DIR
from seeds.models import Seed, SeedStatus, SeedType, QuestionStatus, generate_id


class Context:
    """CLI context object holding database connection."""

    def __init__(self) -> None:
        self.db: Database | None = None

    def get_db(self) -> Database:
        """Get database, initializing if needed."""
        if self.db is None:
            self.db = Database()
            if not self.db.is_initialized():
                click.echo("Error: SEEDS not initialized. Run 'seeds init' first.", err=True)
                sys.exit(1)
        return self.db

    def ensure_init(self) -> Database:
        """Ensure database is initialized, error if not."""
        return self.get_db()


pass_context = click.make_pass_decorator(Context, ensure=True)


def require_init(f):
    """Decorator to require SEEDS to be initialized."""
    @functools.wraps(f)
    @click.pass_context
    def wrapper(click_ctx, *args, **kwargs):
        ctx = click_ctx.ensure_object(Context)
        ctx.ensure_init()
        return click_ctx.invoke(f, *args, **kwargs)
    return wrapper


@click.group()
@click.version_option(version=__version__, prog_name="seeds")
@click.pass_context
def main(ctx: click.Context) -> None:
    """SEEDS: A deliberation capture tool that helps ideas grow into decisions."""
    ctx.ensure_object(Context)


@main.command()
def init() -> None:
    """Initialize SEEDS in the current directory."""
    seeds_dir = Path.cwd() / SEEDS_DIR
    if seeds_dir.exists():
        click.echo(f"SEEDS already initialized in {seeds_dir}")
        return

    db = Database()
    db.init()
    click.echo(f"Initialized SEEDS in {seeds_dir}")
    click.echo("Run 'seeds jot \"Your first idea\"' to capture a thought.")


# Valid seed types for CLI
SEED_TYPES = [t.value for t in SeedType]


@main.command()
@click.option("--title", "-t", required=True, help="Title of the seed")
@click.option("--content", "-c", default="", help="Full content/description")
@click.option(
    "--type",
    "seed_type",
    type=click.Choice(SEED_TYPES),
    default="idea",
    help="Type of seed",
)
@click.option("--tags", help="Comma-separated tags")
@click.option("--parent", "parent_id", help="Parent seed ID for hierarchical grouping")
@pass_context
def create(
    ctx: Context,
    title: str,
    content: str,
    seed_type: str,
    tags: str | None,
    parent_id: str | None,
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
        seed_id = generate_id()

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    seed = Seed(
        id=seed_id,
        title=title,
        content=content,
        seed_type=SeedType(seed_type),
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

    seed_id = generate_id()
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
    type=click.Choice(SEED_TYPES),
    help="Filter by type",
)
@click.option("--tag", help="Filter by tag")
@click.option("--all", "include_all", is_flag=True, help="Include resolved/abandoned")
@pass_context
def list_seeds(
    ctx: Context,
    status: str | None,
    seed_type: str | None,
    tag: str | None,
    include_all: bool,
) -> None:
    """List seeds with optional filters."""
    db = ctx.get_db()

    status_enum = SeedStatus(status) if status else None
    type_enum = SeedType(seed_type) if seed_type else None

    seeds = db.list_seeds(
        status=status_enum,
        seed_type=type_enum,
        tag=tag,
        include_terminal=include_all,
    )

    if not seeds:
        click.echo("No seeds found.")
        return

    for seed in seeds:
        click.echo(format_seed_line(seed, db))


@main.command()
@click.argument("seed_id")
@click.option("--questions", "-q", is_flag=True, help="Include attached questions")
@pass_context
def show(ctx: Context, seed_id: str, questions: bool) -> None:
    """Show detailed information about a seed."""
    db = ctx.get_db()

    seed = db.get_seed(seed_id)
    if seed is None:
        click.echo(f"Error: Seed '{seed_id}' not found.", err=True)
        sys.exit(1)

    # Header
    click.echo(f"{seed.id}: {seed.title}")
    click.echo(f"  Status: {seed.status.value}")
    click.echo(f"  Type: {seed.seed_type.value}")

    if seed.tags:
        click.echo(f"  Tags: {', '.join(seed.tags)}")

    if seed.parent_id:
        click.echo(f"  Parent: {seed.parent_id}")

    # Check if blocked
    if db.is_blocked(seed.id):
        click.echo("  [BLOCKED by unresolved children]")

    # Show children
    children = db.get_children(seed.id)
    if children:
        click.echo(f"  Children: {len(children)}")
        for child in children:
            status_mark = "●" if child.is_terminal() else "○"
            click.echo(f"    {status_mark} {child.id}: {child.title}")

    # Show related
    if seed.related_to:
        click.echo(f"  Related to: {', '.join(seed.related_to)}")

    # Content
    if seed.content:
        click.echo()
        click.echo("Content:")
        click.echo(seed.content)

    # Questions
    if questions:
        qs = db.list_questions(seed_id=seed.id)
        if qs:
            click.echo()
            click.echo("Questions:")
            for q in qs:
                status_mark = "●" if q.status == QuestionStatus.ANSWERED else "○"
                click.echo(f"  {status_mark} {q.id}: {q.text}")
                if q.answer:
                    click.echo(f"    → {q.answer}")


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
    """Show seeds blocked by unresolved children."""
    db = ctx.get_db()

    seeds = db.get_blocked_seeds()

    if not seeds:
        click.echo("No blocked seeds.")
        return

    click.echo("Blocked by unresolved children:")
    for seed in seeds:
        children = db.get_children(seed.id)
        unresolved = [c for c in children if not c.is_terminal()]
        click.echo(f"  {seed.id}: {seed.title}")
        for child in unresolved:
            click.echo(f"    ○ {child.id}: {child.title}")


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
@pass_context
def resolve(ctx: Context, seed_id: str) -> None:
    """Mark a seed as resolved."""
    db = ctx.get_db()
    seed = get_seed_or_exit(db, seed_id)

    from seeds.models import now_utc

    seed.status = SeedStatus.RESOLVED
    seed.resolved_at = now_utc()
    db.update_seed(seed)
    click.echo(f"● {seed_id}: Resolved")


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
        seed.content = f"{seed.content}\n\nAbandoned: {reason}".strip()
    db.update_seed(seed)
    click.echo(f"✗ {seed_id}: Abandoned")
    if reason:
        click.echo(f"  Reason: {reason}")


@main.command()
@click.argument("seed_id")
@click.option("--title", "-t", help="New title")
@click.option("--content", "-c", help="New content (replaces existing)")
@click.option("--tags", help="New tags (comma-separated, replaces existing)")
@click.option("--append", "-a", "append_text", help="Append to content")
@pass_context
def update(
    ctx: Context,
    seed_id: str,
    title: str | None,
    content: str | None,
    tags: str | None,
    append_text: str | None,
) -> None:
    """Update a seed's fields."""
    db = ctx.get_db()
    seed = get_seed_or_exit(db, seed_id)

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

    if not changed:
        click.echo("No changes specified.")
        return

    db.update_seed(seed)
    click.echo(f"Updated {seed_id}")


# --- Question commands ---


@main.command()
@click.argument("question_text")
@click.option("--seed", "seed_id", required=True, help="Seed ID to attach question to")
@pass_context
def ask(ctx: Context, question_text: str, seed_id: str) -> None:
    """Ask a question and attach it to a seed.

    QUESTION_TEXT is the question to ask.
    """
    db = ctx.get_db()

    # Verify seed exists
    seed = db.get_seed(seed_id)
    if seed is None:
        click.echo(f"Error: Seed '{seed_id}' not found.", err=True)
        sys.exit(1)

    from seeds.models import Question

    question_id = generate_id("q")
    question = Question(id=question_id, seed_id=seed_id, text=question_text)

    db.create_question(question)
    click.echo(f"○ {question_id}: {question_text}")
    click.echo(f"  Attached to: {seed_id}")


@main.command()
@click.argument("question_id")
@click.argument("answer_text")
@pass_context
def answer(ctx: Context, question_id: str, answer_text: str) -> None:
    """Answer a question.

    QUESTION_ID is the ID of the question to answer.
    ANSWER_TEXT is the answer.
    """
    db = ctx.get_db()

    question = db.get_question(question_id)
    if question is None:
        click.echo(f"Error: Question '{question_id}' not found.", err=True)
        sys.exit(1)

    from seeds.models import now_utc

    question.answer = answer_text
    question.status = QuestionStatus.ANSWERED
    question.answered_at = now_utc()

    db.update_question(question)
    click.echo(f"● {question_id}: {question.text}")
    click.echo(f"  → {answer_text}")


@main.command()
@click.option("--seed", "seed_id", help="Filter by seed ID")
@pass_context
def questions(ctx: Context, seed_id: str | None) -> None:
    """List open questions."""
    db = ctx.get_db()

    if seed_id:
        qs = db.list_questions(seed_id=seed_id, status=QuestionStatus.OPEN)
    else:
        qs = db.get_open_questions()

    if not qs:
        click.echo("No open questions.")
        return

    click.echo("Open questions:")
    for q in qs:
        seed = db.get_seed(q.seed_id)
        seed_title = seed.title if seed else "?"
        click.echo(f"  ○ {q.id}: {q.text}")
        click.echo(f"    └─ {q.seed_id}: {seed_title}")


# --- Relationship commands ---


@main.command()
@click.argument("seed_id")
@click.option("--relates-to", "related_id", required=True, help="ID of related seed")
@pass_context
def link(ctx: Context, seed_id: str, related_id: str) -> None:
    """Link a seed to another seed (loose coupling)."""
    db = ctx.get_db()

    seed = get_seed_or_exit(db, seed_id)
    related = db.get_seed(related_id)
    if related is None:
        click.echo(f"Error: Seed '{related_id}' not found.", err=True)
        sys.exit(1)

    if related_id in seed.related_to:
        click.echo(f"Already linked: {seed_id} ↔ {related_id}")
        return

    # Add bidirectional link
    seed.related_to.append(related_id)
    db.update_seed(seed)

    if seed_id not in related.related_to:
        related.related_to.append(seed_id)
        db.update_seed(related)

    click.echo(f"Linked: {seed_id} ↔ {related_id}")


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
    parent_chain = []
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

    # Show related
    if seed.related_to:
        click.echo()
        click.echo("Related:")
        for related_id in seed.related_to:
            related = db.get_seed(related_id)
            if related:
                click.echo(f"  ↔ {related.id}: {related.title}")
            else:
                click.echo(f"  ↔ {related_id}: (not found)")


# --- Sync and export commands ---


@main.command()
@click.option("--flush-only", is_flag=True, help="Only export to JSONL (no git ops)")
@pass_context
def sync(ctx: Context, flush_only: bool) -> None:
    """Export seeds to JSONL for git-friendly storage."""
    db = ctx.get_db()

    from seeds.export import export_to_jsonl

    output_path = export_to_jsonl(db)

    # Count seeds
    seeds = db.list_seeds(include_terminal=True)
    click.echo(f"Exported {len(seeds)} seeds to {output_path}")


if __name__ == "__main__":
    main()
