"""seeds CLI entry point."""

from __future__ import annotations

import functools
import sys
from pathlib import Path
from typing import Any, Callable

import click

from seeds import __version__
from seeds.db import SEEDS_DIR, Database
from seeds.models import RelationType, Seed, SeedStatus, SeedType, generate_id


class Context:
    """CLI context object holding database connection."""

    def __init__(self) -> None:
        self.db: Database | None = None

    def get_db(self) -> Database:
        """Get database, initializing if needed."""
        if self.db is None:
            self.db = Database()
            if not self.db.is_initialized():
                click.echo(
                    "Error: seeds not initialized. Run 'seeds init' first.", err=True
                )
                sys.exit(1)
        return self.db

    def ensure_init(self) -> Database:
        """Ensure database is initialized, error if not."""
        return self.get_db()


pass_context = click.make_pass_decorator(Context, ensure=True)


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
def init() -> None:
    """Initialize seeds in the current directory."""
    seeds_dir = Path.cwd() / SEEDS_DIR
    if seeds_dir.exists():
        click.echo(f"seeds already initialized in {seeds_dir}")
        return

    db = Database()
    db.init()
    click.echo(f"Initialized seeds in {seeds_dir}")
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


def format_seed_detail(
    seed: Seed, db: Database, include_questions: bool = False
) -> str:
    """Format seed details as a string."""
    lines = []

    # Header
    lines.append(f"{seed.id}: {seed.title}")
    lines.append(f"  Status: {seed.status.value}")
    lines.append(f"  Type: {seed.seed_type.value}")

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

    Creates a question-type seed and links it via a 'questions' relationship.
    QUESTION_TEXT is the question to ask.
    """
    db = ctx.get_db()

    # Verify seed exists
    seed = db.get_seed(seed_id)
    if seed is None:
        click.echo(f"Error: Seed '{seed_id}' not found.", err=True)
        sys.exit(1)

    question_id = generate_id("seeds")
    question_seed = Seed(
        id=question_id,
        title=question_text,
        seed_type=SeedType.QUESTION,
    )

    db.create_seed(question_seed)
    db.create_relationship(question_id, seed_id, RelationType.QUESTIONS)
    click.echo(f"○ {question_id}: {question_text}")
    click.echo(f"  Attached to: {seed_id}")


@main.command()
@click.argument("question_id")
@click.argument("answer_text")
@pass_context
def answer(ctx: Context, question_id: str, answer_text: str) -> None:
    """Answer a question-seed.

    QUESTION_ID is the ID of the question-seed to answer.
    ANSWER_TEXT is the answer (stored as seed content).
    """
    db = ctx.get_db()

    from seeds.models import now_utc

    question_seed = db.get_seed(question_id)
    if question_seed is None:
        click.echo(f"Error: Question '{question_id}' not found.", err=True)
        sys.exit(1)

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
        qs = [
            q for q in db.get_questions_for_seed(seed_id) if not q.is_terminal()
        ]
    else:
        # Get all unresolved question-type seeds
        qs = db.list_seeds(seed_type=SeedType.QUESTION, include_terminal=False)

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


RELATIONSHIP_TYPES = [t.value for t in RelationType]


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
    existing = db.get_relationships(seed_id, rel_type=rel_type_enum, direction="outbound")
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


@main.command()
def prime() -> None:
    """Output AI-optimized workflow context for Claude Code hooks.

    Silently exits with code 0 if not in a seeds project.
    This enables cross-platform hook integration where both
    seeds and beads hooks can coexist.
    """
    from seeds.db import find_seeds_dir
    from seeds.prime import get_prime_output

    # Check if we're in a seeds project
    seeds_dir = find_seeds_dir()
    if seeds_dir is None:
        # Not in a seeds project - silent exit with success
        # CRITICAL: No output, exit 0 to enable hook coexistence
        return

    click.echo(get_prime_output())


@main.command()
@pass_context
def doctor(ctx: Context) -> None:
    """Check for issues with seeds installation and data."""
    from seeds.export import JSONL_FILE

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
        if db.get_seed(rel["source_id"]) is None or db.get_seed(rel["target_id"]) is None:
            orphaned_rels.append(rel)

    if not orphaned_rels:
        check_pass(f"{len(all_rels)} relationships, no orphans")
    else:
        check_warn("Relationships", f"{len(orphaned_rels)} orphaned relationships")

    # Check for open question-seeds
    open_questions = db.list_seeds(seed_type=SeedType.QUESTION, include_terminal=False)
    if open_questions:
        check_pass(f"{len(open_questions)} open questions")

    # Check JSONL sync
    click.echo()
    click.echo("Sync:")
    jsonl_path = Path.cwd() / SEEDS_DIR / JSONL_FILE
    if jsonl_path.exists():
        check_pass("JSONL file exists")

        # Check if JSONL is stale
        import os

        db_mtime = os.path.getmtime(db.path)
        jsonl_mtime = os.path.getmtime(jsonl_path)
        if jsonl_mtime >= db_mtime:
            check_pass("JSONL is up to date")
        else:
            check_warn("Sync", "JSONL may be stale, run 'seeds sync'")
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


@main.command()
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
@click.option("--port", "-p", default=53365, type=int, help="Port to bind to")
@click.option("--debug", is_flag=True, help="Enable debug mode")
def serve(host: str, port: int, debug: bool) -> None:
    """Start the web UI server for viewing seeds.

    Opens a local web interface for browsing seeds.
    """
    from seeds.db import find_seeds_dir

    # Check if we're in a seeds project
    seeds_dir = find_seeds_dir()
    if seeds_dir is None:
        click.echo("Error: seeds not initialized. Run 'seeds init' first.", err=True)
        sys.exit(1)

    from seeds.web import run_server

    click.echo(f"Starting seeds web UI at http://{host}:{port}")
    click.echo("Press Ctrl+C to stop.")
    run_server(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
