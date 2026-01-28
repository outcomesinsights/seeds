"""SEEDS CLI entry point."""

import functools
import sys
from pathlib import Path

import click

from seeds import __version__
from seeds.db import Database, SEEDS_DIR
from seeds.models import Seed, SeedStatus, SeedType, generate_id


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


if __name__ == "__main__":
    main()
