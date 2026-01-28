"""SEEDS CLI entry point."""

import sys
from pathlib import Path

import click

from seeds import __version__
from seeds.db import Database, SEEDS_DIR


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


if __name__ == "__main__":
    main()
