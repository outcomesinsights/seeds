"""SEEDS CLI entry point."""

import click

from seeds import __version__


@click.group()
@click.version_option(version=__version__, prog_name="seeds")
def main() -> None:
    """SEEDS: A deliberation capture tool that helps ideas grow into decisions."""
    pass


if __name__ == "__main__":
    main()
