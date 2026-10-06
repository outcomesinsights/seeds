"""Commands 0.7 removed answer with what replaced them (seeds-nera).

`seeds sync` used to fail with Click's bare "No such command 'sync'.", which
names no recovery -- and pre-0.7 instructions tell agents to run it at session
start. Each removed name is a hidden tombstone instead.
"""

import pytest

from seeds.cli import main

# name -> a phrase the message must contain: the thing that replaced it.
TOMBSTONES = {
    "sync": "commit them",
    "import": "commit them",
    "serve": "seeds show",
    "suggest": "seeds search",
}


@pytest.fixture
def runner(cli_runner, temp_dir, monkeypatch):
    """Run from an empty directory, so no store is found or touched."""
    monkeypatch.chdir(temp_dir)
    monkeypatch.delenv("SEEDS_DIR", raising=False)
    return cli_runner


@pytest.mark.parametrize(("name", "replacement"), sorted(TOMBSTONES.items()))
def test_tombstone_exits_nonzero_and_names_the_replacement(runner, name, replacement):
    result = runner.invoke(main, [name])

    assert result.exit_code != 0
    assert "No such command" not in result.output
    assert f"'seeds {name}' was removed in 0.7" in result.output
    assert replacement in result.output


@pytest.mark.parametrize("name", sorted(TOMBSTONES))
def test_tombstone_ignores_any_arguments(runner, name):
    bare = runner.invoke(main, [name])
    with_args = runner.invoke(main, [name, "--whatever", "x", "-q", "--help"])

    assert with_args.exit_code == bare.exit_code
    assert with_args.output == bare.output


@pytest.mark.parametrize("name", sorted(TOMBSTONES))
def test_tombstone_is_not_listed_in_help(runner, name):
    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    listed = {
        line.split()[0]
        for line in result.output.splitlines()
        if line.startswith("  ") and line.strip()
    }
    assert "search" in listed  # the parse finds real commands
    assert name not in listed


def test_sync_and_import_point_an_unconverted_project_at_convert(runner):
    for name in ("sync", "import"):
        assert "seeds convert" in runner.invoke(main, [name]).output
