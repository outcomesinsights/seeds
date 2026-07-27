"""Tests for seeds CLI commands."""

import os
import re
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from seeds.cli import main
from seeds.db import SEEDS_DIR, Database
from seeds.models import (
    RelationType,
    Seed,
    SeedStatus,
    SeedType,
)


def _extract_created_id(output: str) -> str:
    """Pull the seed ID out of a 'create' command's 'Created seed: <id>' line.

    Needed since seeds-mlj: next_id() mints hash IDs, so tests can no longer
    assume a fresh 'create'/'jot' produces a predictable sequential ID.
    """
    match = re.search(r"Created seed: (\S+)", output)
    assert match, f"no 'Created seed:' line in output: {output!r}"
    return match.group(1)


def _swap_prefix(seed_id: str, new_prefix: str, old_prefix: str = "seeds") -> str:
    """Return `seed_id` with its prefix replaced: 'seeds-k3n7' -> 'demo-k3n7'.

    Lets a test name the post-rename ID of a seed whose suffix was minted by
    next_id() and is therefore unpredictable.
    """
    assert seed_id.startswith(f"{old_prefix}-"), seed_id
    return f"{new_prefix}{seed_id[len(old_prefix) :]}"


def _extract_jot_id(output: str) -> str:
    """Pull the seed ID out of a 'jot' command's leading '<id>: <thought>' line."""
    match = re.match(r"(\S+):", output)
    assert match, f"no leading '<id>:' in output: {output!r}"
    return match.group(1)


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing commands."""
    return CliRunner()


@pytest.fixture
def initialized_env():
    """Create a temp directory with initialized seeds (prefix='seeds')."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            # Initialize seeds with an explicit prefix so existing tests
            # that assert on 'seeds-N' IDs stay deterministic regardless
            # of the random tmpdir name.
            db = Database()
            db.init(prefix="seeds")
            db.close()
            yield Path(tmpdir)
        finally:
            os.chdir(original_cwd)


@pytest.fixture
def env_with_seeds(initialized_env):
    """Create env with some test seeds."""
    db = Database()

    # Create some test seeds
    seeds = [
        Seed(id="seed-test1", title="Test Seed 1", status=SeedStatus.CAPTURED),
        Seed(id="seed-test2", title="Test Seed 2", status=SeedStatus.EXPLORING),
        Seed(id="seed-test3", title="Test Seed 3", status=SeedStatus.DEFERRED),
        Seed(id="seed-test1.1", title="Child Seed", status=SeedStatus.CAPTURED),
    ]
    for seed in seeds:
        db.create_seed(seed)

    db.close()
    yield initialized_env


class TestInitCommand:
    """Tests for 'seeds init' command."""

    def test_init_creates_seeds_directory(self, cli_runner):
        """Verify init creates .seeds directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                result = cli_runner.invoke(main, ["init"])
                assert result.exit_code == 0
                assert "Initialized seeds" in result.output
                assert (Path(tmpdir) / SEEDS_DIR).exists()
            finally:
                os.chdir(original_cwd)

    def test_init_already_initialized(self, cli_runner, initialized_env):
        """Verify init handles already initialized directory."""
        result = cli_runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert "already initialized" in result.output

    def test_init_derives_prefix_from_directory(self, cli_runner):
        """Init without --prefix derives prefix from current dir name."""
        with tempfile.TemporaryDirectory() as parent:
            project = Path(parent) / "My_Cool Project"
            project.mkdir()
            original_cwd = os.getcwd()
            os.chdir(project)
            try:
                result = cli_runner.invoke(main, ["init"])
                assert result.exit_code == 0
                assert "Project prefix: my-cool-project" in result.output
                db = Database()
                assert db.get_prefix() == "my-cool-project"
                db.close()
            finally:
                os.chdir(original_cwd)

    def test_init_with_explicit_prefix(self, cli_runner):
        """Init with --prefix overrides the directory-derived default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                result = cli_runner.invoke(main, ["init", "--prefix", "myproj"])
                assert result.exit_code == 0
                assert "Project prefix: myproj" in result.output
                db = Database()
                assert db.get_prefix() == "myproj"
                db.close()
            finally:
                os.chdir(original_cwd)

    def test_init_with_invalid_prefix_errors(self, cli_runner):
        """Init rejects prefixes that can't be sanitized into validity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                result = cli_runner.invoke(main, ["init", "--prefix", "!!!"])
                assert result.exit_code != 0
                assert "invalid prefix" in result.output.lower()
            finally:
                os.chdir(original_cwd)


class TestRenamePrefixCommand:
    """Tests for 'seeds rename-prefix' command.

    Database.rename_prefix() only rewrites IDs whose suffix is purely
    numeric (its guard against renaming something like 'seeds-experiment')
    — since seeds-mlj, fresh 'jot'/'create' output is a base36 hash suffix,
    which never matches. So rename-prefix is now only meaningful for
    legacy sequential IDs; tests that need renamable IDs seed the DB
    directly with 'seeds-N' rows to simulate that legacy data instead of
    minting them via the CLI.
    """

    def test_rename_prefix_rewrites_ids(self, cli_runner, initialized_env):
        """rename-prefix rewrites all seed IDs and updates config."""
        db = Database()
        db.create_seed(Seed(id="seeds-1", title="first"))
        db.create_seed(Seed(id="seeds-2", title="second"))
        db.close()

        result = cli_runner.invoke(main, ["rename-prefix", "myproj"])
        assert result.exit_code == 0
        assert "Renamed 2 IDs" in result.output
        assert "seeds-1 → myproj-1" in result.output

        db = Database()
        assert db.get_prefix() == "myproj"
        assert db.get_seed("myproj-1") is not None
        assert db.get_seed("seeds-1") is None
        db.close()

    def test_rename_prefix_sanitizes(self, cli_runner, initialized_env):
        """rename-prefix sanitizes input before applying."""
        cli_runner.invoke(main, ["jot", "first"])

        result = cli_runner.invoke(main, ["rename-prefix", "My Project"])
        assert result.exit_code == 0
        assert "sanitized prefix to 'my-project'" in result.output

        db = Database()
        assert db.get_prefix() == "my-project"
        db.close()

    def test_rename_prefix_rejects_invalid(self, cli_runner, initialized_env):
        """rename-prefix exits non-zero on irrecoverable input."""
        result = cli_runner.invoke(main, ["rename-prefix", "!!!"])
        assert result.exit_code != 0
        assert "invalid prefix" in result.output.lower()

    def test_rename_prefix_noop_when_same(self, cli_runner, initialized_env):
        """rename-prefix to the current prefix is a no-op."""
        result = cli_runner.invoke(main, ["rename-prefix", "seeds"])
        assert result.exit_code == 0
        assert "already set" in result.output

    def test_prefix_command_shows_current(self, cli_runner, initialized_env):
        """seeds prefix prints the configured prefix."""
        result = cli_runner.invoke(main, ["prefix"])
        assert result.exit_code == 0
        assert result.output.strip() == "seeds"

    def test_rename_prefix_rewrites_children(self, cli_runner, initialized_env):
        """rename-prefix rewrites child IDs and updates parent references."""
        db = Database()
        db.create_seed(Seed(id="seeds-1", title="parent"))
        db.create_seed(Seed(id="seeds-1.1", title="child"))
        db.close()

        result = cli_runner.invoke(main, ["rename-prefix", "demo"])
        assert result.exit_code == 0
        assert "seeds-1 → demo-1" in result.output
        assert "seeds-1.1 → demo-1.1" in result.output

        # The child should still be a child of the renamed parent.
        result = cli_runner.invoke(main, ["show", "demo-1.1"])
        assert result.exit_code == 0
        assert "child" in result.output.lower()

    def test_rename_prefix_reexports_jsonl(self, cli_runner, initialized_env):
        """rename-prefix re-exports JSONL with the new IDs."""
        db = Database()
        db.create_seed(Seed(id="seeds-1", title="alpha"))
        db.create_seed(Seed(id="seeds-2", title="beta"))
        db.close()

        result = cli_runner.invoke(main, ["rename-prefix", "demo"])
        assert result.exit_code == 0

        jsonl_path = initialized_env / SEEDS_DIR / "seeds.jsonl"
        text = jsonl_path.read_text()
        assert '"id": "demo-1"' in text
        assert '"id": "demo-2"' in text
        assert '"id": "seeds-1"' not in text

    def test_rename_prefix_rewrites_body_refs(self, cli_runner, initialized_env):
        """rename-prefix rewrites ID refs inside seed content by default."""
        db = Database()
        db.create_seed(Seed(id="seeds-1", title="target"))
        db.close()
        create_result = cli_runner.invoke(
            main, ["create", "--title", "hub", "--content", "see seeds-1"]
        )
        hub_id = _extract_created_id(create_result.output)

        result = cli_runner.invoke(main, ["rename-prefix", "demo"])
        assert result.exit_code == 0
        assert "Rewrote 1 ID reference" in result.output

        # The hub's own hash ID is renamed along with everything else under
        # the old prefix, and the "seeds-1" reference inside its content is
        # rewritten too.
        new_hub_id = _swap_prefix(hub_id, "demo")
        result = cli_runner.invoke(main, ["show", new_hub_id])
        assert result.exit_code == 0
        assert "see demo-1" in result.output

    def test_rename_prefix_no_rewrite_bodies(self, cli_runner, initialized_env):
        """--no-rewrite-bodies leaves seed content alone."""
        db = Database()
        db.create_seed(Seed(id="seeds-1", title="target"))
        db.close()
        create_result = cli_runner.invoke(
            main, ["create", "--title", "hub", "--content", "see seeds-1"]
        )
        hub_id = _extract_created_id(create_result.output)

        result = cli_runner.invoke(
            main, ["rename-prefix", "demo", "--no-rewrite-bodies"]
        )
        assert result.exit_code == 0
        assert "body" not in result.output.lower()

        # The hub itself is renamed (its ID carries the prefix); only its
        # body text is left alone.
        new_hub_id = _swap_prefix(hub_id, "demo")
        result = cli_runner.invoke(main, ["show", new_hub_id])
        assert result.exit_code == 0
        # Reference is now stale — the seeds-1 in body wasn't rewritten.
        assert "see seeds-1" in result.output

    def test_rename_prefix_dry_run(self, cli_runner, initialized_env):
        """--dry-run reports what would change without writing."""
        db = Database()
        db.create_seed(Seed(id="seeds-1", title="target"))
        db.close()
        create_result = cli_runner.invoke(
            main, ["create", "--title", "hub", "--content", "see seeds-1"]
        )
        hub_id = _extract_created_id(create_result.output)

        result = cli_runner.invoke(main, ["rename-prefix", "demo", "--dry-run"])
        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        # Both the planted sequential ID and the hub's hash ID are reported.
        assert "Would rename 2 IDs" in result.output
        assert "Would rewrite 1 ID reference" in result.output
        assert "seeds-1 → demo-1" in result.output
        assert f"{hub_id} → {_swap_prefix(hub_id, 'demo')}" in result.output
        assert "see seeds-1" in result.output  # old snippet
        assert "see demo-1" in result.output  # new snippet
        assert "Run without --dry-run" in result.output

        # Nothing was actually written.
        db = Database()
        assert db.get_prefix() == "seeds"
        assert db.get_seed("seeds-1") is not None
        assert db.get_seed("demo-1") is None
        db.close()

    def test_rename_prefix_then_show_covers_both_id_shapes(
        self, cli_runner, initialized_env
    ):
        """rename-prefix + show work identically for every ID shape (seeds-skc).

        The three suffixes below are planted rather than minted so the case is
        deterministic. Before seeds-skc, rename-prefix classified IDs with
        ``int(suffix)``: 'seeds-060' (an all-digit base36 hash) was renamed
        while 'seeds-k3n7' was not, so whether the suite passed depended on
        which hash next_id() happened to emit.
        """
        db = Database()
        db.create_seed(Seed(id="seeds-112", title="grandfathered sequential"))
        db.create_seed(Seed(id="seeds-060", title="all-digit base36 hash"))
        db.create_seed(Seed(id="seeds-k3n7", title="alphanumeric base36 hash"))
        db.create_seed(Seed(id="seeds-k3n7.1", title="child of a hash ID"))
        db.close()

        result = cli_runner.invoke(main, ["rename-prefix", "demo"])
        assert result.exit_code == 0
        for old_id in ("seeds-112", "seeds-060", "seeds-k3n7", "seeds-k3n7.1"):
            assert f"{old_id} → {_swap_prefix(old_id, 'demo')}" in result.output
        assert "Renamed 4 IDs" in result.output

        # Every new ID resolves through show; no old ID survives.
        for old_id in ("seeds-112", "seeds-060", "seeds-k3n7", "seeds-k3n7.1"):
            new_id = _swap_prefix(old_id, "demo")
            found = cli_runner.invoke(main, ["show", new_id])
            assert found.exit_code == 0, f"show {new_id} failed: {found.output}"
            gone = cli_runner.invoke(main, ["show", old_id])
            assert gone.exit_code == 1
            assert "not found" in gone.output

    def test_rename_prefix_rewrites_body_refs_for_both_id_shapes(
        self, cli_runner, initialized_env
    ):
        """Body refs to hash IDs are rewritten too, so they don't go stale.

        Renaming a hash ID without rewriting references to it would strand
        every mention of it in another seed's text.
        """
        db = Database()
        db.create_seed(Seed(id="seeds-112", title="sequential target"))
        db.create_seed(Seed(id="seeds-k3n7", title="hash target"))
        db.create_seed(
            Seed(
                id="seeds-abc1",
                title="hub",
                content="see seeds-112 and seeds-k3n7 (seeds-related work)",
            )
        )
        db.close()

        result = cli_runner.invoke(main, ["rename-prefix", "demo"])
        assert result.exit_code == 0
        assert "Rewrote 2 ID reference" in result.output

        result = cli_runner.invoke(main, ["show", "demo-abc1"])
        assert result.exit_code == 0
        assert "see demo-112 and demo-k3n7" in result.output
        # 'seeds-related' is base36-shaped but isn't a seed, so it's prose.
        assert "seeds-related work" in result.output


class TestJotCommand:
    """Tests for 'seeds jot' command."""

    def test_jot_creates_seed(self, cli_runner, initialized_env):
        """Verify jot creates a captured seed."""
        result = cli_runner.invoke(main, ["jot", "My quick thought"])
        assert result.exit_code == 0
        assert "seeds-" in result.output
        assert "My quick thought" in result.output

        # Verify seed was created
        db = Database()
        seeds = db.list_seeds()
        assert len(seeds) == 1
        assert seeds[0].title == "My quick thought"
        assert seeds[0].status == SeedStatus.CAPTURED
        db.close()

    def test_jot_requires_init(self, cli_runner):
        """Verify jot fails if not initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                result = cli_runner.invoke(main, ["jot", "Test"])
                assert result.exit_code != 0
                assert "not initialized" in result.output
            finally:
                os.chdir(original_cwd)


class TestGetDbBootstrap:
    """Tests for Context.get_db's bootstrap seam (fresh-clone import path)."""

    def test_get_db_exits_when_uninitialized_by_default(self):
        """Default get_db() still exits 'run seeds init' when the DB is absent."""
        from seeds.cli import Context

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                ctx = Context()
                with pytest.raises(SystemExit):
                    ctx.get_db()
            finally:
                os.chdir(original_cwd)

    def test_get_db_bootstrap_bypasses_init_guard(self):
        """get_db(bootstrap=True) returns an (uninitialized) DB without exiting.

        This is the seam an import caller uses to bootstrap from JSONL itself;
        the actual `seeds import` command that calls it lands in a later bead.
        """
        from seeds.cli import Context

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                ctx = Context()
                db = ctx.get_db(bootstrap=True)
                assert db is not None
                assert db.is_initialized() is False  # not created yet
            finally:
                os.chdir(original_cwd)


class TestCreateCommand:
    """Tests for 'seeds create' command."""

    def test_create_with_title_only(self, cli_runner, initialized_env):
        """Verify create with just title works."""
        result = cli_runner.invoke(main, ["create", "--title", "New Idea"])
        assert result.exit_code == 0
        assert "Created seed" in result.output
        assert "New Idea" in result.output

    def test_create_with_type_and_tags(self, cli_runner, initialized_env):
        """Verify create with type and tags works."""
        result = cli_runner.invoke(
            main,
            [
                "create",
                "--title",
                "Decision",
                "--type",
                "decision",
                "--tags",
                "important,urgent",
            ],
        )
        assert result.exit_code == 0

        db = Database()
        seeds = db.list_seeds()
        assert len(seeds) == 1
        assert seeds[0].seed_type == SeedType.DECISION
        assert seeds[0].tags == ["important", "urgent"]
        db.close()

    def test_create_with_parent(self, cli_runner, env_with_seeds):
        """Verify create with parent creates child seed."""
        result = cli_runner.invoke(
            main,
            ["create", "--title", "New Child", "--parent", "seed-test1"],
        )
        assert result.exit_code == 0
        assert "seed-test1." in result.output
        assert "Parent: seed-test1" in result.output

    def test_create_with_invalid_parent(self, cli_runner, initialized_env):
        """Verify create with invalid parent fails."""
        result = cli_runner.invoke(
            main,
            ["create", "--title", "Child", "--parent", "nonexistent"],
        )
        assert result.exit_code != 0
        assert "not found" in result.output


class TestListCommand:
    """Tests for 'seeds list' command."""

    def test_list_empty(self, cli_runner, initialized_env):
        """Verify list shows no seeds message when empty."""
        result = cli_runner.invoke(main, ["list"])
        assert result.exit_code == 0
        assert "No seeds found" in result.output

    def test_list_shows_seeds(self, cli_runner, env_with_seeds):
        """Verify list shows all non-terminal seeds."""
        result = cli_runner.invoke(main, ["list"])
        assert result.exit_code == 0
        assert "seed-test1" in result.output
        assert "seed-test2" in result.output
        assert "seed-test3" in result.output

    def test_list_filter_by_status(self, cli_runner, env_with_seeds):
        """Verify list can filter by status."""
        result = cli_runner.invoke(main, ["list", "--status", "captured"])
        assert result.exit_code == 0
        assert "seed-test1" in result.output
        assert "seed-test2" not in result.output

    def test_list_since_includes_recent(self, cli_runner, env_with_seeds):
        """--since=1d should include seeds just created in the fixture."""
        result = cli_runner.invoke(main, ["list", "--since", "1d"])
        assert result.exit_code == 0
        assert "seed-test1" in result.output

    def test_list_since_excludes_old(self, cli_runner, env_with_seeds):
        """--since=2026-12-01 (far future) should exclude all fixture seeds."""
        result = cli_runner.invoke(main, ["list", "--since", "2099-01-01"])
        assert result.exit_code == 0
        assert "No seeds found" in result.output

    def test_list_since_iso_date(self, cli_runner, env_with_seeds):
        result = cli_runner.invoke(main, ["list", "--since", "2020-01-01"])
        assert result.exit_code == 0
        assert "seed-test1" in result.output

    def test_list_since_invalid_value(self, cli_runner, env_with_seeds):
        result = cli_runner.invoke(main, ["list", "--since", "not-a-date"])
        assert result.exit_code != 0
        assert "Unrecognized" in result.output

    def test_list_sort_updated(self, cli_runner, env_with_seeds):
        """--sort=updated should succeed and produce all open seeds."""
        result = cli_runner.invoke(main, ["list", "--sort", "updated"])
        assert result.exit_code == 0
        assert "seed-test1" in result.output
        assert "seed-test2" in result.output

    def test_list_sort_default_is_created(self, cli_runner, env_with_seeds):
        """Default sort behavior unchanged when no --sort given."""
        result = cli_runner.invoke(main, ["list"])
        assert result.exit_code == 0
        # All 4 fixture seeds present
        for sid in ["seed-test1", "seed-test2", "seed-test3", "seed-test1.1"]:
            assert sid in result.output


class TestSuggestCommand:
    """Tests for 'seeds suggest' command (natural-language dedup query)."""

    def test_suggest_returns_match(self, cli_runner, initialized_env):
        create_result = cli_runner.invoke(
            main,
            ["create", "-t", "Venn diagram for compare lens", "--type", "idea"],
        )
        seed_id = _extract_created_id(create_result.output)
        result = cli_runner.invoke(main, ["suggest", "venn diagram"])
        assert result.exit_code == 0
        assert seed_id in result.output
        assert "Venn diagram" in result.output

    def test_suggest_no_match_message(self, cli_runner, initialized_env):
        cli_runner.invoke(main, ["create", "-t", "Totally unrelated topic"])
        result = cli_runner.invoke(main, ["suggest", "venn diagram"])
        assert result.exit_code == 0
        assert "No seeds matched" in result.output

    def test_suggest_json_mode(self, cli_runner, initialized_env):
        create_result = cli_runner.invoke(
            main, ["create", "-t", "Venn diagram", "--tags", "venn,compare"]
        )
        seed_id = _extract_created_id(create_result.output)
        result = cli_runner.invoke(main, ["suggest", "venn diagram", "--json"])
        assert result.exit_code == 0
        import json as _json

        payload = _json.loads(result.output)
        assert isinstance(payload, list)
        assert payload[0]["id"] == seed_id
        assert payload[0]["title"] == "Venn diagram"
        assert "compare" in payload[0]["tags"]
        assert isinstance(payload[0]["score"], (int, float))

    def test_suggest_limit_caps_results(self, cli_runner, initialized_env):
        for i in range(5):
            cli_runner.invoke(main, ["create", "-t", f"Venn diagram {i}"])
        result = cli_runner.invoke(main, ["suggest", "venn diagram", "--limit", "2"])
        assert result.exit_code == 0
        # Count seed lines (lines starting with a status icon)
        ids_in_output = sum(
            1 for line in result.output.splitlines() if "seeds-" in line
        )
        assert ids_in_output == 2

    def test_suggest_includes_resolved_by_default(self, cli_runner, initialized_env):
        create_result = cli_runner.invoke(main, ["create", "-t", "Venn diagram"])
        seed_id = _extract_created_id(create_result.output)
        cli_runner.invoke(main, ["resolve", seed_id, "-r", "Done"])
        result = cli_runner.invoke(main, ["suggest", "venn diagram"])
        assert result.exit_code == 0
        assert seed_id in result.output

    def test_suggest_open_only_excludes_terminal(self, cli_runner, initialized_env):
        create_result = cli_runner.invoke(main, ["create", "-t", "Venn diagram"])
        seed_id = _extract_created_id(create_result.output)
        cli_runner.invoke(main, ["resolve", seed_id, "-r", "Done"])
        result = cli_runner.invoke(main, ["suggest", "venn diagram", "--open-only"])
        assert result.exit_code == 0
        assert "No seeds matched" in result.output


class TestRecentCommand:
    """Tests for 'seeds recent' alias."""

    def test_recent_default_window(self, cli_runner, env_with_seeds):
        """Default 7d window includes fixture seeds created moments ago."""
        result = cli_runner.invoke(main, ["recent"])
        assert result.exit_code == 0
        assert "seed-test1" in result.output

    def test_recent_explicit_since(self, cli_runner, env_with_seeds):
        result = cli_runner.invoke(main, ["recent", "--since", "today"])
        assert result.exit_code == 0
        assert "seed-test1" in result.output

    def test_recent_empty_window(self, cli_runner, env_with_seeds):
        """Far-future --since produces 'no seeds' message."""
        result = cli_runner.invoke(main, ["recent", "--since", "2099-01-01"])
        assert result.exit_code == 0
        assert "No seeds updated since" in result.output

    def test_recent_invalid_since(self, cli_runner, env_with_seeds):
        result = cli_runner.invoke(main, ["recent", "--since", "not-a-date"])
        assert result.exit_code != 0
        assert "Unrecognized" in result.output


class TestShowCommand:
    """Tests for 'seeds show' command."""

    def test_show_displays_seed(self, cli_runner, env_with_seeds):
        """Verify show displays seed details."""
        result = cli_runner.invoke(main, ["show", "seed-test1"])
        assert result.exit_code == 0
        assert "seed-test1" in result.output
        assert "Test Seed 1" in result.output
        assert "Status: captured" in result.output

    def test_show_not_found(self, cli_runner, initialized_env):
        """Verify show handles nonexistent seed."""
        result = cli_runner.invoke(main, ["show", "nonexistent"])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_show_displays_resolution(self, cli_runner, env_with_seeds):
        """Verify show displays resolution for resolved seeds."""
        # Resolve with resolution text
        cli_runner.invoke(
            main,
            ["resolve", "seed-test2", "--resolution", "Decided to use approach B"],
        )

        result = cli_runner.invoke(main, ["show", "seed-test2"])
        assert result.exit_code == 0
        assert "Resolution: Decided to use approach B" in result.output

    def test_show_with_children(self, cli_runner, env_with_seeds):
        """Verify show displays children."""
        result = cli_runner.invoke(main, ["show", "seed-test1"])
        assert result.exit_code == 0
        assert "Children:" in result.output
        assert "seed-test1.1" in result.output


class TestStatusCommands:
    """Tests for status change commands (explore, defer, resolve, abandon)."""

    def test_explore_changes_status(self, cli_runner, env_with_seeds):
        """Verify explore changes status to exploring."""
        result = cli_runner.invoke(main, ["explore", "seed-test1"])
        assert result.exit_code == 0
        assert "Now exploring" in result.output

        db = Database()
        seed = db.get_seed("seed-test1")
        assert seed.status == SeedStatus.EXPLORING
        db.close()

    def test_defer_changes_status(self, cli_runner, env_with_seeds):
        """Verify defer changes status to deferred."""
        result = cli_runner.invoke(main, ["defer", "seed-test1"])
        assert result.exit_code == 0
        assert "Deferred" in result.output

        db = Database()
        seed = db.get_seed("seed-test1")
        assert seed.status == SeedStatus.DEFERRED
        db.close()

    def test_resolve_changes_status(self, cli_runner, env_with_seeds):
        """Verify resolve changes status to resolved."""
        result = cli_runner.invoke(main, ["resolve", "seed-test2"])
        assert result.exit_code == 0
        assert "Resolved" in result.output

        db = Database()
        seed = db.get_seed("seed-test2")
        assert seed.status == SeedStatus.RESOLVED
        assert seed.resolved_at is not None
        assert seed.resolution == ""
        db.close()

    def test_resolve_with_resolution(self, cli_runner, env_with_seeds):
        """Verify resolve captures resolution text."""
        result = cli_runner.invoke(
            main,
            ["resolve", "seed-test2", "--resolution", "Shipped in PR #42"],
        )
        assert result.exit_code == 0
        assert "Resolved" in result.output
        assert "Shipped in PR #42" in result.output

        db = Database()
        seed = db.get_seed("seed-test2")
        assert seed.status == SeedStatus.RESOLVED
        assert seed.resolution == "Shipped in PR #42"
        db.close()

    def test_abandon_changes_status(self, cli_runner, env_with_seeds):
        """Verify abandon changes status to abandoned."""
        result = cli_runner.invoke(main, ["abandon", "seed-test2"])
        assert result.exit_code == 0
        assert "Abandoned" in result.output

        db = Database()
        seed = db.get_seed("seed-test2")
        assert seed.status == SeedStatus.ABANDONED
        db.close()

    def test_abandon_with_reason(self, cli_runner, env_with_seeds):
        """Verify abandon captures reason in resolution field."""
        result = cli_runner.invoke(
            main,
            ["abandon", "seed-test2", "--reason", "Not feasible"],
        )
        assert result.exit_code == 0
        assert "Not feasible" in result.output

        db = Database()
        seed = db.get_seed("seed-test2")
        assert seed.resolution == "Not feasible"
        db.close()


class TestTrellisCommand:
    """Tests for 'seeds trellis' command (trellis output mode)."""

    def test_trellis_creates_section_in_fresh_file(self, cli_runner, env_with_seeds):
        """Writing to a fresh file creates the section and the principle."""
        target = env_with_seeds / "TRELLISES.md"
        result = cli_runner.invoke(
            main,
            [
                "trellis",
                "seed-test2",
                "--to",
                str(target),
                "--as",
                "Prefer boring technology",
            ],
        )
        assert result.exit_code == 0
        assert target.exists()
        text = target.read_text(encoding="utf-8")
        assert "## Principles" in text
        assert "Prefer boring technology" in text

    def test_trellis_does_not_duplicate_existing_heading(
        self, cli_runner, env_with_seeds
    ):
        """Appending to a file that already has the section keeps one heading."""
        target = env_with_seeds / "CONTEXT.md"
        target.write_text(
            "# Project Context\n\n"
            "## Principles\n\n"
            "- Existing principle — seed-test1, 2020-01-01\n\n"
            "## Other Notes\n\n"
            "Some trailing prose.\n",
            encoding="utf-8",
        )
        result = cli_runner.invoke(
            main,
            [
                "trellis",
                "seed-test2",
                "--to",
                str(target),
                "--as",
                "New principle here",
            ],
        )
        assert result.exit_code == 0
        text = target.read_text(encoding="utf-8")
        assert text.count("## Principles") == 1
        # The new bullet lands inside the section, before the following heading.
        assert text.index("New principle here") < text.index("## Other Notes")

    def test_trellis_bullet_has_id_and_date(self, cli_runner, env_with_seeds):
        """The appended bullet cites the seed ID and an ISO (YYYY-MM-DD) date."""
        target = env_with_seeds / "TRELLISES.md"
        result = cli_runner.invoke(
            main,
            ["trellis", "seed-test2", "--to", str(target), "--as", "A principle"],
        )
        assert result.exit_code == 0
        text = target.read_text(encoding="utf-8")
        bullets = [ln for ln in text.splitlines() if ln.startswith("- ")]
        assert len(bullets) == 1
        assert "seed-test2" in bullets[0]
        assert re.search(r"\d{4}-\d{2}-\d{2}", bullets[0])

    def test_trellis_resolution_names_target_file(self, cli_runner, env_with_seeds):
        """The resolved seed's resolution names the target file path."""
        target = env_with_seeds / "TRELLISES.md"
        result = cli_runner.invoke(
            main,
            ["trellis", "seed-test2", "--to", str(target), "--as", "A principle"],
        )
        assert result.exit_code == 0
        db = Database()
        seed = db.get_seed("seed-test2")
        assert str(target) in seed.resolution
        db.close()

    def test_trellis_tag_idempotent(self, cli_runner, env_with_seeds):
        """Tags the seed 'trellis', without duplicating on repeat."""
        target = env_with_seeds / "TRELLISES.md"
        args = ["trellis", "seed-test2", "--to", str(target), "--as", "A principle"]
        assert cli_runner.invoke(main, args).exit_code == 0
        # Run it a second time — the tag must not be duplicated.
        assert cli_runner.invoke(main, args).exit_code == 0
        db = Database()
        seed = db.get_seed("seed-test2")
        assert seed.tags.count("trellis") == 1
        db.close()

    def test_trellis_resolves_by_default(self, cli_runner, env_with_seeds):
        """Making a trellis resolves the seed by default."""
        target = env_with_seeds / "TRELLISES.md"
        result = cli_runner.invoke(
            main,
            ["trellis", "seed-test2", "--to", str(target), "--as", "A principle"],
        )
        assert result.exit_code == 0
        db = Database()
        seed = db.get_seed("seed-test2")
        assert seed.status == SeedStatus.RESOLVED
        assert seed.resolved_at is not None
        db.close()

    def test_trellis_no_resolve_keeps_status(self, cli_runner, env_with_seeds):
        """With --no-resolve the status is unchanged and the seed stays queryable."""
        target = env_with_seeds / "TRELLISES.md"
        result = cli_runner.invoke(
            main,
            [
                "trellis",
                "seed-test2",
                "--to",
                str(target),
                "--as",
                "A principle",
                "--no-resolve",
            ],
        )
        assert result.exit_code == 0
        db = Database()
        seed = db.get_seed("seed-test2")
        assert seed.status == SeedStatus.EXPLORING
        db.close()
        # A non-terminal trellis seed is surfaced by the tag filter.
        listed = cli_runner.invoke(main, ["list", "--tag", "trellis"])
        assert listed.exit_code == 0
        assert "seed-test2" in listed.output

    def test_trellis_nonexistent_exits_nonzero(self, cli_runner, env_with_seeds):
        """Running trellis on an unknown seed id exits non-zero."""
        target = env_with_seeds / "TRELLISES.md"
        result = cli_runner.invoke(
            main,
            ["trellis", "does-not-exist", "--to", str(target), "--as", "X"],
        )
        assert result.exit_code != 0
        assert "not found" in result.output


class TestUpdateCommand:
    """Tests for 'seeds update' command."""

    def test_update_title(self, cli_runner, env_with_seeds):
        """Verify update can change title."""
        result = cli_runner.invoke(
            main,
            ["update", "seed-test1", "--title", "New Title"],
        )
        assert result.exit_code == 0
        assert "Updated" in result.output

        db = Database()
        seed = db.get_seed("seed-test1")
        assert seed.title == "New Title"
        db.close()

    def test_update_append_content(self, cli_runner, env_with_seeds):
        """Verify update --append adds to content."""
        result = cli_runner.invoke(
            main,
            ["update", "seed-test1", "--append", "Additional thoughts"],
        )
        assert result.exit_code == 0

        db = Database()
        seed = db.get_seed("seed-test1")
        assert "Additional thoughts" in seed.content
        db.close()

    def test_update_no_changes(self, cli_runner, env_with_seeds):
        """Verify update without changes shows message."""
        result = cli_runner.invoke(main, ["update", "seed-test1"])
        assert result.exit_code == 0
        assert "No changes specified" in result.output


class TestIdRefValidation:
    """Tests for seed-ID cross-reference validation on create/update.

    Guards against the common failure where an agent drafts a body like
    'see seeds-117' with a hallucinated ID. See bead seeds-0vs.
    """

    def test_create_rejects_unknown_ref_in_content(self, cli_runner, initialized_env):
        result = cli_runner.invoke(
            main,
            ["create", "-t", "Test", "-c", "see seeds-99999 for context"],
        )
        assert result.exit_code != 0
        assert "unknown IDs" in result.output
        assert "seeds-99999" in result.output

    def test_create_rejects_unknown_ref_in_title(self, cli_runner, initialized_env):
        result = cli_runner.invoke(main, ["create", "-t", "Follow-up to seeds-99999"])
        assert result.exit_code != 0
        assert "seeds-99999" in result.output

    def test_create_allow_unknown_refs_overrides(self, cli_runner, initialized_env):
        result = cli_runner.invoke(
            main,
            [
                "create",
                "-t",
                "Test",
                "-c",
                "see seeds-99999",
                "--allow-unknown-refs",
            ],
        )
        assert result.exit_code == 0
        assert "Created seed" in result.output

    def test_create_accepts_existing_ref(self, cli_runner, initialized_env):
        first = cli_runner.invoke(main, ["jot", "First seed"])
        assert first.exit_code == 0
        first_id = _extract_jot_id(first.output)
        result = cli_runner.invoke(
            main, ["create", "-t", "Second", "-c", f"follow-up to {first_id}"]
        )
        assert result.exit_code == 0

    def test_create_accepts_existing_child_ref(self, cli_runner, initialized_env):
        parent = cli_runner.invoke(main, ["jot", "Parent"])
        parent_id = _extract_jot_id(parent.output)
        cli_runner.invoke(main, ["create", "-t", "Child", "--parent", parent_id])
        result = cli_runner.invoke(
            main, ["create", "-t", "Third", "-c", f"see {parent_id}.1"]
        )
        assert result.exit_code == 0

    def test_create_rejects_unknown_child_ref(self, cli_runner, initialized_env):
        cli_runner.invoke(main, ["jot", "Parent"])
        result = cli_runner.invoke(
            main, ["create", "-t", "Third", "-c", "see seeds-1.99"]
        )
        assert result.exit_code != 0
        assert "seeds-1.99" in result.output

    def test_create_accepts_text_without_refs(self, cli_runner, initialized_env):
        result = cli_runner.invoke(
            main, ["create", "-t", "Plain", "-c", "no IDs here, just words"]
        )
        assert result.exit_code == 0

    def test_update_append_rejects_unknown_ref(self, cli_runner, env_with_seeds):
        result = cli_runner.invoke(
            main, ["update", "seed-test1", "--append", "see seeds-99999"]
        )
        assert result.exit_code != 0
        assert "seeds-99999" in result.output

    def test_update_append_allow_unknown_refs_overrides(
        self, cli_runner, env_with_seeds
    ):
        result = cli_runner.invoke(
            main,
            [
                "update",
                "seed-test1",
                "--append",
                "see seeds-99999",
                "--allow-unknown-refs",
            ],
        )
        assert result.exit_code == 0

    def test_update_content_rejects_unknown_ref(self, cli_runner, env_with_seeds):
        result = cli_runner.invoke(
            main,
            ["update", "seed-test1", "-c", "rewritten body referencing seeds-99999"],
        )
        assert result.exit_code != 0
        assert "seeds-99999" in result.output

    def test_update_title_rejects_unknown_ref(self, cli_runner, env_with_seeds):
        result = cli_runner.invoke(
            main, ["update", "seed-test1", "-t", "Renamed: see seeds-99999"]
        )
        assert result.exit_code != 0
        assert "seeds-99999" in result.output


class TestQuestionCommands:
    """Tests for question-related commands (question-seeds + relationships)."""

    def test_ask_creates_question_seed(self, cli_runner, env_with_seeds):
        """Verify ask creates a question-type seed with relationship."""
        result = cli_runner.invoke(
            main,
            ["ask", "What is the answer?", "--seed", "seed-test1"],
        )
        assert result.exit_code == 0
        assert "seeds-" in result.output
        assert "What is the answer?" in result.output
        assert "Attached to: seed-test1" in result.output

        db = Database()
        question_seeds = db.get_questions_for_seed("seed-test1")
        assert len(question_seeds) == 1
        assert question_seeds[0].title == "What is the answer?"
        assert question_seeds[0].seed_type == SeedType.QUESTION
        db.close()

    def test_ask_invalid_seed(self, cli_runner, initialized_env):
        """Verify ask fails with invalid seed."""
        result = cli_runner.invoke(
            main,
            ["ask", "Question?", "--seed", "nonexistent"],
        )
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_answer_resolves_question_seed(self, cli_runner, env_with_seeds):
        """Verify answer sets content and resolves question-seed."""
        # Create a question-seed via ask
        result = cli_runner.invoke(
            main,
            ["ask", "What is the answer?", "--seed", "seed-test1"],
        )
        assert result.exit_code == 0
        # Extract question-seed ID from output
        q_id = result.output.split(":")[0].split()[-1]

        result = cli_runner.invoke(main, ["answer", q_id, "42"])
        assert result.exit_code == 0
        assert "42" in result.output

        db = Database()
        q_seed = db.get_seed(q_id)
        assert q_seed.content == "42"
        assert q_seed.status == SeedStatus.RESOLVED
        db.close()

    def test_questions_lists_open(self, cli_runner, env_with_seeds):
        """Verify questions shows open question-seeds."""
        # Create a question via ask
        result = cli_runner.invoke(
            main,
            ["ask", "Open question?", "--seed", "seed-test1"],
        )
        assert result.exit_code == 0

        result = cli_runner.invoke(main, ["questions"])
        assert result.exit_code == 0
        assert "Open question?" in result.output


class TestLinkCommand:
    """Tests for 'seeds link' command."""

    def test_link_creates_bidirectional_relationship(self, cli_runner, env_with_seeds):
        """Verify link creates bidirectional relates-to relationship."""
        result = cli_runner.invoke(
            main,
            ["link", "seed-test1", "--relates-to", "seed-test2"],
        )
        assert result.exit_code == 0
        assert "Linked" in result.output

        db = Database()
        rels = db.get_relationships(
            "seed-test1", rel_type=RelationType.RELATES_TO, direction="outbound"
        )
        assert len(rels) == 1
        assert rels[0].target_id == "seed-test2"
        # Reverse direction too
        rels2 = db.get_relationships(
            "seed-test2", rel_type=RelationType.RELATES_TO, direction="outbound"
        )
        assert len(rels2) == 1
        assert rels2[0].target_id == "seed-test1"
        db.close()

    def test_link_already_linked(self, cli_runner, env_with_seeds):
        """Verify link handles already linked seeds."""
        # Link first
        cli_runner.invoke(
            main,
            ["link", "seed-test1", "--relates-to", "seed-test2"],
        )

        # Try to link again
        result = cli_runner.invoke(
            main,
            ["link", "seed-test1", "--relates-to", "seed-test2"],
        )
        assert result.exit_code == 0
        assert "Already linked" in result.output

    def test_link_with_type(self, cli_runner, env_with_seeds):
        """Verify link with --type creates typed relationship."""
        result = cli_runner.invoke(
            main,
            ["link", "seed-test1", "--relates-to", "seed-test2", "--type", "questions"],
        )
        assert result.exit_code == 0
        assert "questions" in result.output

        db = Database()
        rels = db.get_relationships(
            "seed-test1", rel_type=RelationType.QUESTIONS, direction="outbound"
        )
        assert len(rels) == 1
        db.close()


class TestReadyDeferredBlocked:
    """Tests for ready, deferred, and blocked commands."""

    def test_ready_shows_captured_seeds(self, cli_runner, env_with_seeds):
        """Verify ready shows only captured seeds."""
        result = cli_runner.invoke(main, ["ready"])
        assert result.exit_code == 0
        assert "seed-test1" in result.output
        assert "seed-test2" not in result.output  # exploring, not captured

    def test_deferred_shows_deferred_seeds(self, cli_runner, env_with_seeds):
        """Verify deferred shows only deferred seeds."""
        result = cli_runner.invoke(main, ["deferred"])
        assert result.exit_code == 0
        assert "seed-test3" in result.output
        assert "seed-test1" not in result.output

    def test_blocked_shows_blocked_seeds(self, cli_runner, env_with_seeds):
        """Verify blocked shows seeds with unresolved children."""
        result = cli_runner.invoke(main, ["blocked"])
        assert result.exit_code == 0
        # seed-test1 has child seed-test1.1 which is captured (unresolved)
        assert "seed-test1" in result.output


class TestTreeCommand:
    """Tests for 'seeds tree' command."""

    def test_tree_shows_hierarchy(self, cli_runner, env_with_seeds):
        """Verify tree shows parent-child hierarchy."""
        result = cli_runner.invoke(main, ["tree", "seed-test1"])
        assert result.exit_code == 0
        assert "Current:" in result.output
        assert "seed-test1" in result.output
        assert "Children:" in result.output
        assert "seed-test1.1" in result.output


class TestImportCommand:
    """Tests for 'seeds import' command (rehydrate from JSONL)."""

    def test_import_rehydrates_and_prints_counts(self, cli_runner, env_with_seeds):
        """import rebuilds DB-absent seeds from JSONL and prints created counts."""
        # Export the fixture's seeds, then wipe the DB to simulate a fresh clone.
        cli_runner.invoke(main, ["sync", "--flush-only"])
        db_path = env_with_seeds / SEEDS_DIR / "seeds.db"
        db_path.unlink()

        result = cli_runner.invoke(main, ["import"])
        assert result.exit_code == 0
        # Fixture has 4 seeds, all newly created on a fresh DB.
        assert "Imported: 4 created, 0 updated, 0 skipped" in result.output

        # The seeds are actually back in the DB.
        list_result = cli_runner.invoke(main, ["list", "--all"])
        assert "seed-test1" in list_result.output

    def test_import_again_skips_unchanged(self, cli_runner, env_with_seeds):
        """A second import of the same JSONL leaves fresh DB rows untouched."""
        cli_runner.invoke(main, ["sync", "--flush-only"])

        result = cli_runner.invoke(main, ["import"])
        assert result.exit_code == 0
        # DB rows are as-fresh-or-fresher than JSONL -> all skipped.
        assert "Imported: 0 created, 0 updated, 4 skipped" in result.output

    def test_import_reads_from_stdin(self, cli_runner, env_with_seeds):
        """import - reads JSONL from stdin and rehydrates a wiped DB."""
        cli_runner.invoke(main, ["sync", "--flush-only"])
        jsonl_path = env_with_seeds / SEEDS_DIR / "seeds.jsonl"
        jsonl_text = jsonl_path.read_text()

        # Wipe the DB so the stdin records are genuinely created.
        (env_with_seeds / SEEDS_DIR / "seeds.db").unlink()

        result = cli_runner.invoke(main, ["import", "-"], input=jsonl_text)
        assert result.exit_code == 0
        assert "Imported: 4 created, 0 updated, 0 skipped" in result.output

        list_result = cli_runner.invoke(main, ["list", "--all"])
        assert "seed-test1" in list_result.output

    def test_import_explicit_path(self, cli_runner, env_with_seeds):
        """import accepts an explicit PATH argument."""
        cli_runner.invoke(main, ["sync", "--flush-only"])
        jsonl_path = env_with_seeds / SEEDS_DIR / "seeds.jsonl"
        (env_with_seeds / SEEDS_DIR / "seeds.db").unlink()

        result = cli_runner.invoke(main, ["import", str(jsonl_path)])
        assert result.exit_code == 0
        assert "Imported: 4 created" in result.output


class TestSyncCommand:
    """Tests for 'seeds sync' command."""

    def test_sync_exports_jsonl(self, cli_runner, env_with_seeds):
        """Verify sync exports to JSONL."""
        result = cli_runner.invoke(main, ["sync", "--flush-only"])
        assert result.exit_code == 0
        assert "Exported" in result.output
        assert "seeds.jsonl" in result.output

        jsonl_path = env_with_seeds / SEEDS_DIR / "seeds.jsonl"
        assert jsonl_path.exists()

    def test_sync_round_trips_import_then_export(self, cli_runner, env_with_seeds):
        """Default sync prints both an import summary and an export summary."""
        # Seed the JSONL so the import half has something to report.
        cli_runner.invoke(main, ["sync", "--flush-only"])

        result = cli_runner.invoke(main, ["sync"])
        assert result.exit_code == 0
        assert "Imported:" in result.output
        assert "Exported" in result.output

    def test_sync_import_does_not_clobber_db_only_seed(
        self, cli_runner, env_with_seeds
    ):
        """sync imports JSONL records but never deletes seeds only in the DB."""
        # Snapshot the fixture seeds into JSONL.
        cli_runner.invoke(main, ["sync", "--flush-only"])

        # Add a seed that exists ONLY in the DB (absent from the JSONL).
        db = Database()
        db.create_seed(Seed(id="seed-dbonly", title="DB-only seed"))
        db.close()

        result = cli_runner.invoke(main, ["sync"])
        assert result.exit_code == 0

        # The DB-only seed survives the round-trip (import must not delete it)
        # and the subsequent export now includes it.
        list_result = cli_runner.invoke(main, ["list", "--all"])
        assert "seed-dbonly" in list_result.output

        jsonl_text = (env_with_seeds / SEEDS_DIR / "seeds.jsonl").read_text()
        assert "seed-dbonly" in jsonl_text

    def test_sync_preserves_multiple_db_only_seeds(self, cli_runner, env_with_seeds):
        """A round-trip sync preserves every DB-only seed, not just one.

        Generalizes the single-seed case: several seeds present only in the DB
        (absent from the JSONL the import half reads) all survive the import and
        all reappear in the re-exported JSONL.
        """
        cli_runner.invoke(main, ["sync", "--flush-only"])

        db = Database()
        db.create_seed(Seed(id="seed-only1", title="DB only 1"))
        db.create_seed(Seed(id="seed-only2", title="DB only 2"))
        db.create_seed(Seed(id="seed-only3", title="DB only 3"))
        db.close()

        result = cli_runner.invoke(main, ["sync"])
        assert result.exit_code == 0

        list_result = cli_runner.invoke(main, ["list", "--all"])
        for sid in ("seed-only1", "seed-only2", "seed-only3"):
            assert sid in list_result.output

        jsonl_text = (env_with_seeds / SEEDS_DIR / "seeds.jsonl").read_text()
        for sid in ("seed-only1", "seed-only2", "seed-only3"):
            assert sid in jsonl_text

    def test_sync_flush_only_is_export_only(self, cli_runner, env_with_seeds):
        """--flush-only exports without importing (no import summary line)."""
        cli_runner.invoke(main, ["sync", "--flush-only"])

        result = cli_runner.invoke(main, ["sync", "--flush-only"])
        assert result.exit_code == 0
        assert "Exported" in result.output
        assert "Imported:" not in result.output


class TestPrimeCommand:
    """Tests for 'seeds prime' command."""

    def test_prime_outputs_context_in_seeds_project(self, cli_runner, initialized_env):
        """Verify prime outputs workflow context when in a seeds project."""
        result = cli_runner.invoke(main, ["prime"])
        assert result.exit_code == 0
        assert "seeds Workflow Context" in result.output
        assert "seeds jot" in result.output

    def test_prime_documents_prefix_commands(self, cli_runner, initialized_env):
        """Verify prime mentions the new prefix-related commands."""
        result = cli_runner.invoke(main, ["prime"])
        assert result.exit_code == 0
        assert "seeds rename-prefix" in result.output
        assert "seeds prefix" in result.output
        assert "--dry-run" in result.output

    def test_prime_silent_exit_outside_seeds_project(self, cli_runner):
        """Verify prime silently exits when not in a seeds project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                result = cli_runner.invoke(main, ["prime"])
                assert result.exit_code == 0
                assert result.output == ""  # Silent exit - no output
            finally:
                os.chdir(original_cwd)

    def test_prime_includes_digest_with_seeds(self, cli_runner, env_with_seeds):
        """Prime should append a digest of project state when seeds exist."""
        result = cli_runner.invoke(main, ["prime"])
        assert result.exit_code == 0
        assert "## Current Seeds" in result.output
        assert "Counts:" in result.output
        # Fixture has captured + exploring + deferred + child
        assert "seed-test1" in result.output
        assert "seed-test2" in result.output

    def test_prime_no_digest_flag_omits_digest(self, cli_runner, env_with_seeds):
        """--no-digest should produce only the workflow text."""
        result = cli_runner.invoke(main, ["prime", "--no-digest"])
        assert result.exit_code == 0
        assert "seeds Workflow Context" in result.output
        assert "## Current Seeds" not in result.output
        assert "seed-test1" not in result.output

    def test_prime_digest_with_empty_project(self, cli_runner, initialized_env):
        """Empty project should produce a friendly empty-digest hint."""
        result = cli_runner.invoke(main, ["prime"])
        assert result.exit_code == 0
        assert "## Current Seeds" in result.output
        assert "Project is empty" in result.output

    def test_prime_digest_limit_respected(self, cli_runner, env_with_seeds):
        """--digest-limit should cap the Recently Updated section."""
        result = cli_runner.invoke(main, ["prime", "--digest-limit", "1"])
        assert result.exit_code == 0
        assert "Recently Updated (top 1)" in result.output

    def test_prime_digest_shows_active_exploration(self, cli_runner, env_with_seeds):
        """Exploring seeds should appear in their own section."""
        result = cli_runner.invoke(main, ["prime"])
        assert result.exit_code == 0
        # Fixture sets seed-test2 to EXPLORING
        assert "Active Exploration" in result.output


class TestShowOutputFile:
    """Tests for 'seeds show --output-file' flag."""

    def test_show_output_file_creates_temp_file(self, cli_runner, env_with_seeds):
        """Verify show --output-file writes to temp file and prints path."""
        result = cli_runner.invoke(main, ["show", "seed-test1", "--output-file"])
        assert result.exit_code == 0
        # Output should be a file path
        output_path = result.output.strip()
        assert "seeds-seed-test1-" in output_path

        # File should contain seed details
        content = Path(output_path).read_text()
        assert "seed-test1" in content
        assert "Test Seed 1" in content

        # Cleanup
        Path(output_path).unlink(missing_ok=True)


class TestShowDetailFormatting:
    """Tests for format_seed_detail covering various fields."""

    def test_show_with_tags(self, cli_runner, initialized_env):
        """Verify show displays tags."""
        db = Database()
        seed = Seed(id="seed-tagged", title="Tagged Seed", tags=["important", "urgent"])
        db.create_seed(seed)
        db.close()

        result = cli_runner.invoke(main, ["show", "seed-tagged"])
        assert result.exit_code == 0
        assert "Tags:" in result.output
        assert "important" in result.output

    def test_show_with_content(self, cli_runner, initialized_env):
        """Verify show displays content."""
        db = Database()
        seed = Seed(
            id="seed-content", title="Content Seed", content="Detailed content here"
        )
        db.create_seed(seed)
        db.close()

        result = cli_runner.invoke(main, ["show", "seed-content"])
        assert result.exit_code == 0
        assert "Content:" in result.output
        assert "Detailed content here" in result.output

    def test_show_with_related(self, cli_runner, initialized_env):
        """Verify show displays related seeds via relationships."""
        db = Database()
        seed1 = Seed(id="seed-r1", title="Seed 1")
        seed2 = Seed(id="seed-r2", title="Seed 2")
        db.create_seed(seed1)
        db.create_seed(seed2)
        db.create_relationship("seed-r1", "seed-r2", RelationType.RELATES_TO)
        db.close()

        result = cli_runner.invoke(main, ["show", "seed-r1"])
        assert result.exit_code == 0
        assert "Related to:" in result.output
        assert "seed-r2" in result.output

    def test_show_child_displays_parent(self, cli_runner, env_with_seeds):
        """Verify show of child displays parent ID."""
        result = cli_runner.invoke(main, ["show", "seed-test1.1"])
        assert result.exit_code == 0
        assert "Parent: seed-test1" in result.output

    def test_show_with_questions_flag(self, cli_runner, env_with_seeds):
        """Verify show --questions displays question-seeds via relationships."""
        db = Database()
        q_seed = Seed(id="seeds-qshow", title="Show this?", seed_type=SeedType.QUESTION)
        db.create_seed(q_seed)
        db.create_relationship("seeds-qshow", "seed-test1", RelationType.QUESTIONS)
        db.close()

        result = cli_runner.invoke(main, ["show", "seed-test1", "--questions"])
        assert result.exit_code == 0
        assert "Questions:" in result.output
        assert "seeds-qshow" in result.output
        assert "Show this?" in result.output

    def test_show_with_answered_question(self, cli_runner, env_with_seeds):
        """Verify show displays answered question-seeds with content."""
        db = Database()
        q_seed = Seed(
            id="seeds-qanswered",
            title="Answered?",
            content="Yes it is",
            seed_type=SeedType.QUESTION,
            status=SeedStatus.RESOLVED,
        )
        db.create_seed(q_seed)
        db.create_relationship("seeds-qanswered", "seed-test1", RelationType.QUESTIONS)
        db.close()

        result = cli_runner.invoke(main, ["show", "seed-test1", "--questions"])
        assert result.exit_code == 0
        assert "Yes it is" in result.output


class TestEmptyStateLists:
    """Tests for empty state messages in ready/deferred/blocked."""

    def test_ready_no_seeds(self, cli_runner, initialized_env):
        """Verify ready shows message when no captured seeds."""
        result = cli_runner.invoke(main, ["ready"])
        assert result.exit_code == 0
        assert "No captured seeds" in result.output

    def test_deferred_no_seeds(self, cli_runner, initialized_env):
        """Verify deferred shows message when no deferred seeds."""
        result = cli_runner.invoke(main, ["deferred"])
        assert result.exit_code == 0
        assert "No deferred seeds" in result.output

    def test_blocked_no_seeds(self, cli_runner, initialized_env):
        """Verify blocked shows message when no blocked seeds."""
        result = cli_runner.invoke(main, ["blocked"])
        assert result.exit_code == 0
        assert "No blocked seeds" in result.output


class TestExploreWarning:
    """Tests for explore warning when seed is not captured."""

    def test_explore_non_captured_shows_warning(self, cli_runner, env_with_seeds):
        """Verify explore warns when seed is not in captured state."""
        result = cli_runner.invoke(main, ["explore", "seed-test2"])
        assert result.exit_code == 0
        assert "Warning" in result.output
        assert "not captured" in result.output


class TestUpdateContentAndTags:
    """Tests for update --content and --tags flags."""

    def test_update_content(self, cli_runner, env_with_seeds):
        """Verify update --content replaces content."""
        result = cli_runner.invoke(
            main,
            ["update", "seed-test1", "--content", "New content"],
        )
        assert result.exit_code == 0

        db = Database()
        seed = db.get_seed("seed-test1")
        assert seed.content == "New content"
        db.close()

    def test_update_tags(self, cli_runner, env_with_seeds):
        """Verify update --tags replaces tags."""
        result = cli_runner.invoke(
            main,
            ["update", "seed-test1", "--tags", "new,tags"],
        )
        assert result.exit_code == 0

        db = Database()
        seed = db.get_seed("seed-test1")
        assert seed.tags == ["new", "tags"]
        db.close()

    def test_update_clear_tags(self, cli_runner, env_with_seeds):
        """Verify update --tags '' clears tags."""
        result = cli_runner.invoke(
            main,
            ["update", "seed-test1", "--tags", ""],
        )
        assert result.exit_code == 0

        db = Database()
        seed = db.get_seed("seed-test1")
        assert seed.tags == []
        db.close()


class TestAnswerNotFound:
    """Test for answering nonexistent question-seed."""

    def test_answer_nonexistent_question(self, cli_runner, initialized_env):
        """Verify answer fails for nonexistent question-seed."""
        result = cli_runner.invoke(main, ["answer", "seeds-nonexistent", "The answer"])
        assert result.exit_code != 0
        assert "not found" in result.output


class TestQuestionsFiltering:
    """Tests for questions command filtering and empty state."""

    def test_questions_no_open(self, cli_runner, initialized_env):
        """Verify questions shows message when no open questions."""
        result = cli_runner.invoke(main, ["questions"])
        assert result.exit_code == 0
        assert "No open questions" in result.output

    def test_questions_filter_by_seed(self, cli_runner, env_with_seeds):
        """Verify questions --seed filters by seed."""
        db = Database()
        q1 = Seed(id="seeds-qs1", title="Q for seed1?", seed_type=SeedType.QUESTION)
        q2 = Seed(id="seeds-qs2", title="Q for seed2?", seed_type=SeedType.QUESTION)
        db.create_seed(q1)
        db.create_seed(q2)
        db.create_relationship("seeds-qs1", "seed-test1", RelationType.QUESTIONS)
        db.create_relationship("seeds-qs2", "seed-test2", RelationType.QUESTIONS)
        db.close()

        result = cli_runner.invoke(main, ["questions", "--seed", "seed-test1"])
        assert result.exit_code == 0
        assert "seeds-qs1" in result.output
        assert "seeds-qs2" not in result.output


class TestLinkNotFound:
    """Test for linking to nonexistent seed."""

    def test_link_nonexistent_related(self, cli_runner, env_with_seeds):
        """Verify link fails when related seed doesn't exist."""
        result = cli_runner.invoke(
            main,
            ["link", "seed-test1", "--relates-to", "nonexistent"],
        )
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_link_nonexistent_source(self, cli_runner, initialized_env):
        """Verify link fails when source seed doesn't exist."""
        result = cli_runner.invoke(
            main,
            ["link", "nonexistent", "--relates-to", "also-nonexistent"],
        )
        assert result.exit_code != 0
        assert "not found" in result.output


class TestTreeAdvanced:
    """Tests for tree with parent chains, grandchildren, and related seeds."""

    def test_tree_shows_parent_chain(self, cli_runner, env_with_seeds):
        """Verify tree shows ancestor chain for child seeds."""
        result = cli_runner.invoke(main, ["tree", "seed-test1.1"])
        assert result.exit_code == 0
        assert "Ancestors:" in result.output
        assert "seed-test1" in result.output

    def test_tree_shows_grandchildren(self, cli_runner, initialized_env):
        """Verify tree shows grandchildren."""
        db = Database()
        db.create_seed(Seed(id="seed-p", title="Parent"))
        db.create_seed(Seed(id="seed-p.1", title="Child"))
        db.create_seed(Seed(id="seed-p.1.1", title="Grandchild"))
        db.close()

        result = cli_runner.invoke(main, ["tree", "seed-p"])
        assert result.exit_code == 0
        assert "Children:" in result.output
        assert "seed-p.1" in result.output
        assert "seed-p.1.1" in result.output

    def test_tree_shows_related(self, cli_runner, initialized_env):
        """Verify tree shows related seeds via relationships."""
        db = Database()
        db.create_seed(Seed(id="seed-x", title="Main"))
        db.create_seed(Seed(id="seed-y", title="Related"))
        db.create_relationship("seed-x", "seed-y", RelationType.RELATES_TO)
        db.close()

        result = cli_runner.invoke(main, ["tree", "seed-x"])
        assert result.exit_code == 0
        assert "Related:" in result.output
        assert "seed-y" in result.output

    def test_tree_shows_missing_related(self, cli_runner, initialized_env):
        """Verify tree handles missing related seeds gracefully."""
        db = Database()
        db.create_seed(Seed(id="seed-x", title="Main"))
        db.create_seed(Seed(id="seed-gone", title="Will be deleted"))
        db.create_relationship("seed-x", "seed-gone", RelationType.RELATES_TO)
        # Delete the target but leave the relationship orphaned
        conn = db._get_conn()
        conn.execute("DELETE FROM seeds WHERE id = 'seed-gone'")
        conn.commit()
        db.close()

        result = cli_runner.invoke(main, ["tree", "seed-x"])
        assert result.exit_code == 0
        assert "seed-gone" in result.output
        assert "(not found)" in result.output


class TestDoctorCommand:
    """Tests for 'seeds doctor' command."""

    def test_doctor_passes_on_healthy_install(self, cli_runner, env_with_seeds):
        """Verify doctor passes on healthy installation."""
        # First sync to create JSONL
        cli_runner.invoke(main, ["sync", "--flush-only"])

        result = cli_runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "Database exists" in result.output
        assert "passed" in result.output

    def test_doctor_warns_no_jsonl(self, cli_runner, env_with_seeds):
        """Verify doctor warns when JSONL file doesn't exist."""
        result = cli_runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "No JSONL file" in result.output or "JSONL" in result.output

    def test_doctor_shows_warnings_count(self, cli_runner, initialized_env):
        """Verify doctor shows warning count when there are issues."""
        result = cli_runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        # No open seeds = warning, no JSONL = warning
        assert "warning" in result.output

    def test_doctor_shows_open_questions(self, cli_runner, env_with_seeds):
        """Verify doctor reports open question-seeds."""
        db = Database()
        q_seed = Seed(
            id="seeds-qdoc", title="Doctor question?", seed_type=SeedType.QUESTION
        )
        db.create_seed(q_seed)
        db.create_relationship("seeds-qdoc", "seed-test1", RelationType.QUESTIONS)
        db.close()

        # Create JSONL to avoid stale warning noise
        cli_runner.invoke(main, ["sync", "--flush-only"])

        result = cli_runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "open question" in result.output

    def test_doctor_reports_configured_prefix(self, cli_runner, initialized_env):
        """Doctor surfaces the configured project prefix."""
        result = cli_runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "Project:" in result.output
        assert "Prefix configured: 'seeds'" in result.output

    def test_doctor_nudges_when_default_prefix_mismatches_dir(self, cli_runner):
        """When prefix=default but dir name differs, doctor warns with a hint."""
        with tempfile.TemporaryDirectory() as parent:
            project = Path(parent) / "shiny-project"
            project.mkdir()
            original_cwd = os.getcwd()
            os.chdir(project)
            try:
                db = Database()
                db.init(prefix="seeds")  # explicit default
                db.close()

                result = cli_runner.invoke(main, ["doctor"])
                assert result.exit_code == 0
                assert "shiny-project" in result.output
                assert "rename-prefix" in result.output
            finally:
                os.chdir(original_cwd)

    def test_doctor_warns_when_prefix_unconfigured(self, cli_runner):
        """Doctor warns when no prefix is stored in config (legacy DB)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                db = Database()
                db.init()  # no prefix
                db.close()

                result = cli_runner.invoke(main, ["doctor"])
                assert result.exit_code == 0
                assert "fallback" in result.output.lower() or (
                    "rename-prefix" in result.output
                )
            finally:
                os.chdir(original_cwd)


class TestSkillsInstall:
    """Tests for 'seeds skills install' (Claude Code plugin installer)."""

    @staticmethod
    def _completed(stdout: str = "") -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess([], 0, stdout=stdout, stderr="")

    @staticmethod
    def _argvs(mock_run):
        """The `claude ...` argv list passed to each subprocess.run call."""
        return [c.args[0] for c in mock_run.call_args_list]

    def test_fresh_install_then_enables(self, cli_runner):
        """A not-yet-installed plugin is installed and then explicitly enabled.

        Enabling is the whole point: install alone can leave the plugin disabled,
        which silently drops every seeds:* skill from new sessions.
        """
        with (
            patch("shutil.which", return_value="/usr/bin/claude"),
            patch(
                "subprocess.run", return_value=self._completed(stdout="")
            ) as mock_run,
        ):
            result = cli_runner.invoke(main, ["skills", "install"])

        assert result.exit_code == 0, result.output
        argvs = self._argvs(mock_run)
        assert [
            "claude",
            "plugin",
            "install",
            "seeds@seeds-marketplace",
            "--scope",
            "user",
        ] in argvs
        assert [
            "claude",
            "plugin",
            "enable",
            "seeds@seeds-marketplace",
            "--scope",
            "user",
        ] in argvs
        assert "enabled" in result.output

    def test_already_installed_updates_then_enables(self, cli_runner):
        """When already present, the command updates (not re-installs) and enables."""
        with (
            patch("shutil.which", return_value="/usr/bin/claude"),
            patch(
                "subprocess.run",
                return_value=self._completed(stdout="seeds@seeds-marketplace\n"),
            ) as mock_run,
        ):
            result = cli_runner.invoke(main, ["skills", "install"])

        assert result.exit_code == 0, result.output
        argvs = self._argvs(mock_run)
        assert [
            "claude",
            "plugin",
            "update",
            "seeds@seeds-marketplace",
            "--scope",
            "user",
        ] in argvs
        # Update path must NOT uninstall.
        assert not any(a[:3] == ["claude", "plugin", "uninstall"] for a in argvs)
        assert [
            "claude",
            "plugin",
            "enable",
            "seeds@seeds-marketplace",
            "--scope",
            "user",
        ] in argvs

    def test_reinstall_refreshes_marketplace_and_replaces_before_enabling(
        self, cli_runner
    ):
        """--reinstall refreshes the source and replaces the stale copy."""
        with (
            patch("shutil.which", return_value="/usr/bin/claude"),
            patch(
                "subprocess.run",
                return_value=self._completed(stdout="seeds@seeds-marketplace\n"),
            ) as mock_run,
        ):
            result = cli_runner.invoke(main, ["skills", "install", "--reinstall"])

        assert result.exit_code == 0, result.output
        argvs = self._argvs(mock_run)
        assert [
            "claude",
            "plugin",
            "marketplace",
            "update",
            "seeds-marketplace",
        ] in argvs
        # Stale copy is uninstalled, then a fresh copy installed, then enabled —
        # in that order.
        order = {
            a[2]: i
            for i, a in enumerate(argvs)
            if a[1] == "plugin" and a[2] in ("uninstall", "install", "enable")
        }
        assert order["uninstall"] < order["install"] < order["enable"]

    def test_aborts_without_claude_cli(self, cli_runner):
        """The command fails cleanly when the `claude` CLI is not installed."""
        with patch("shutil.which", return_value=None):
            result = cli_runner.invoke(main, ["skills", "install"])

        assert result.exit_code != 0
        assert "claude" in result.output.lower()

    def test_upgrade_is_an_alias_for_reinstall(self, cli_runner):
        """--upgrade behaves identically to --reinstall."""
        with (
            patch("shutil.which", return_value="/usr/bin/claude"),
            patch(
                "subprocess.run",
                return_value=self._completed(stdout="seeds@seeds-marketplace\n"),
            ) as mock_run,
        ):
            result = cli_runner.invoke(main, ["skills", "install", "--upgrade"])

        assert result.exit_code == 0, result.output
        argvs = self._argvs(mock_run)
        assert [
            "claude",
            "plugin",
            "marketplace",
            "update",
            "seeds-marketplace",
        ] in argvs
        assert any(a[:3] == ["claude", "plugin", "uninstall"] for a in argvs)
