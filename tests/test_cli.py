"""Tests for seeds CLI commands."""

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from seeds.cli import main
from seeds.idgen import is_hash_suffix
from seeds.models import (
    RelationType,
    SeedStatus,
    SeedType,
)
from seeds.seedfile import SeedRecord
from seeds.store import SEEDS_DIR, Store, new_record
from tests.beadshelpers import (
    call_lines,
    hide_bd,
    install_fake_bd,
    make_beads_workspace,
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


def _store() -> Store:
    """The store for the project the test has chdir'd into."""
    return Store(Path.cwd() / SEEDS_DIR)


def _record(
    id: str,
    title: str,
    content: str = "",
    status: SeedStatus = SeedStatus.CAPTURED,
    seed_type: str = SeedType.IDEA.value,
    tags: list[str] | None = None,
) -> SeedRecord:
    """A seed record, built with the field names these tests were written with.

    ``content``/``id`` rather than ``body``/``seed_id`` so a test that predates
    the seed-file store still reads the way its author wrote it. The record it
    returns is the real thing -- there is no adapter under this, and
    ``store.create`` writes it as a file like any other.
    """
    record = new_record(
        id,
        title,
        body=content,
        status=status,
        seed_type=str(seed_type),
        tags=tags,
    )
    if status in (SeedStatus.RESOLVED, SeedStatus.ABANDONED):
        # resolved_at is required iff the status is terminal, and the writer
        # refuses a record that breaks that -- so a terminal fixture has to
        # carry one (docs/storage-format.md §3).
        record.resolved_at = record.updated_at
    return record


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing commands."""
    return CliRunner()


@pytest.fixture
def initialized_env():
    """Create a temp directory with an initialized seed-file store.

    The prefix is set explicitly so tests asserting on 'seeds-...' IDs stay
    deterministic regardless of the random tmpdir name.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            store = Store(Path(tmpdir) / SEEDS_DIR)
            store.files_dir.mkdir(parents=True, exist_ok=True)
            store.set_prefix("seeds")
            yield Path(tmpdir)
        finally:
            os.chdir(original_cwd)


@pytest.fixture
def env_with_seeds(initialized_env):
    """Create env with some test seeds."""
    store = Store(initialized_env / SEEDS_DIR)
    for seed_id, title, status in [
        ("seed-test1", "Test Seed 1", SeedStatus.CAPTURED),
        ("seed-test2", "Test Seed 2", SeedStatus.EXPLORING),
        ("seed-test3", "Test Seed 3", SeedStatus.DEFERRED),
        ("seed-test1.1", "Child Seed", SeedStatus.CAPTURED),
    ]:
        store.create(new_record(seed_id, title, status=status))
    yield initialized_env


class TestInitCommand:
    """Tests for 'seeds init' command."""

    def _unconverted(self, tmpdir):
        """A .seeds/ holding only the pre-0.7 JSONL: an unconverted project."""
        seeds_dir = Path(tmpdir) / SEEDS_DIR
        seeds_dir.mkdir(parents=True, exist_ok=True)
        (seeds_dir / "seeds.jsonl").write_text(
            json.dumps(
                {
                    "format_version": 2,
                    "id": "seeds-a1",
                    "title": "From the old store",
                    "content": "",
                    "status": "captured",
                    "seed_type": "idea",
                    "tags": [],
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "updated_at": "2026-01-01T00:00:00+00:00",
                    "resolved_at": None,
                    "resolution": "",
                    "relationships": [],
                }
            )
            + "\n"
        )
        return seeds_dir

    def test_init_points_at_convert_when_only_the_legacy_jsonl_is_present(
        self, cli_runner
    ):
        """The unconverted-repo state: tracked JSONL, no seed files.

        This is bead seeds-1j3's closed loop in its new shape. init used to
        report "already initialized" over a .seeds/ it could not actually use,
        while every other command sent the user to init. The recovery that
        works here is `seeds convert`, and both ends have to name it.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                self._unconverted(tmpdir)

                result = cli_runner.invoke(main, ["init"])

                assert result.exit_code == 0
                assert "already initialized" not in result.output
                assert "seeds convert" in result.output
            finally:
                os.chdir(original_cwd)

    def test_commands_point_at_convert_when_only_the_legacy_jsonl_is_present(
        self, cli_runner
    ):
        """Other commands name the recovery that actually works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                self._unconverted(tmpdir)

                result = cli_runner.invoke(main, ["list"])

                assert result.exit_code == 1
                assert "seeds convert" in result.output
                assert "seeds init" not in result.output
            finally:
                os.chdir(original_cwd)

    def test_convert_actually_recovers_that_state(self, cli_runner):
        """The advice has to work, so exercise it rather than trusting it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                self._unconverted(tmpdir)

                assert cli_runner.invoke(main, ["convert"]).exit_code == 0
                list_result = cli_runner.invoke(main, ["list"])
                assert list_result.exit_code == 0
                assert "seeds-a1" in list_result.output
            finally:
                os.chdir(original_cwd)

    def test_uninitialized_project_still_says_init(self, cli_runner):
        """No .seeds at all is the case where 'seeds init' IS the answer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                result = cli_runner.invoke(main, ["list"])
                assert result.exit_code == 1
                assert "seeds init" in result.output
            finally:
                os.chdir(original_cwd)

    def test_init_proceeds_on_empty_seeds_dir(self, cli_runner):
        """A bare .seeds with nothing to rehydrate from initializes normally."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                (Path(tmpdir) / SEEDS_DIR).mkdir()
                result = cli_runner.invoke(main, ["init"])
                assert result.exit_code == 0
                assert "Initialized seeds" in result.output
            finally:
                os.chdir(original_cwd)

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
                store = _store()
                assert store.get_prefix() == "my-cool-project"
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
                store = _store()
                assert store.get_prefix() == "myproj"
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
        store = _store()
        store.create(_record(id="seeds-1", title="first"))
        store.create(_record(id="seeds-2", title="second"))

        result = cli_runner.invoke(main, ["rename-prefix", "myproj"])
        assert result.exit_code == 0
        assert "Renamed 2 IDs" in result.output
        assert "seeds-1 → myproj-1" in result.output

        store = _store()
        assert store.get_prefix() == "myproj"
        assert store.get("myproj-1") is not None
        assert store.get("seeds-1") is None

    def test_rename_prefix_sanitizes(self, cli_runner, initialized_env):
        """rename-prefix sanitizes input before applying."""
        cli_runner.invoke(main, ["jot", "first"])

        result = cli_runner.invoke(main, ["rename-prefix", "My Project"])
        assert result.exit_code == 0
        assert "sanitized prefix to 'my-project'" in result.output

        store = _store()
        assert store.get_prefix() == "my-project"

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
        store = _store()
        store.create(_record(id="seeds-1", title="parent"))
        store.create(_record(id="seeds-1.1", title="child"))

        result = cli_runner.invoke(main, ["rename-prefix", "demo"])
        assert result.exit_code == 0
        assert "seeds-1 → demo-1" in result.output
        assert "seeds-1.1 → demo-1.1" in result.output

        # The child should still be a child of the renamed parent.
        result = cli_runner.invoke(main, ["show", "demo-1.1"])
        assert result.exit_code == 0
        assert "child" in result.output.lower()

    def test_rename_prefix_renames_the_files_themselves(
        self, cli_runner, initialized_env
    ):
        """The filename IS the id (docs/storage-format.md §1.1).

        This replaces a check that the JSONL was re-exported with the new ids.
        There is no export to re-run now, and the equivalent -- the only place
        the new id can land -- is the file's own name. A rename that rewrote
        frontmatter and left the old filenames would leave every `seeds show`
        computing a path that is not there.
        """
        store = _store()
        store.create(_record(id="seeds-1", title="alpha"))
        store.create(_record(id="seeds-2", title="beta"))

        result = cli_runner.invoke(main, ["rename-prefix", "demo"])
        assert result.exit_code == 0

        names = sorted(p.name for p in _store().files_dir.glob("*.md"))
        assert names == ["demo-1.md", "demo-2.md"]
        assert _store().get("demo-1").id == "demo-1"

    def test_rename_prefix_rewrites_body_refs(self, cli_runner, initialized_env):
        """rename-prefix rewrites ID refs inside seed content by default."""
        store = _store()
        store.create(_record(id="seeds-1", title="target"))
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
        store = _store()
        store.create(_record(id="seeds-1", title="target"))
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
        store = _store()
        store.create(_record(id="seeds-1", title="target"))
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
        store = _store()
        assert store.get_prefix() == "seeds"
        assert store.get("seeds-1") is not None
        assert store.get("demo-1") is None

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
        store = _store()
        store.create(_record(id="seeds-112", title="grandfathered sequential"))
        store.create(_record(id="seeds-060", title="all-digit base36 hash"))
        store.create(_record(id="seeds-k3n7", title="alphanumeric base36 hash"))
        store.create(_record(id="seeds-k3n7.1", title="child of a hash ID"))

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
        store = _store()
        store.create(_record(id="seeds-112", title="sequential target"))
        store.create(_record(id="seeds-k3n7", title="hash target"))
        store.create(
            _record(
                id="seeds-abc1",
                title="hub",
                content="see seeds-112 and seeds-k3n7 (seeds-related work)",
            )
        )

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
        store = _store()
        seeds = store.list_seeds()
        assert len(seeds) == 1
        assert seeds[0].title == "My quick thought"
        assert seeds[0].status == SeedStatus.CAPTURED

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

        store = _store()
        seeds = store.list_seeds()
        assert len(seeds) == 1
        assert seeds[0].seed_type == SeedType.DECISION
        assert seeds[0].tags == ["important", "urgent"]

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

        store = _store()
        seed = store.get("seed-test1")
        assert seed.status == SeedStatus.EXPLORING

    def test_defer_changes_status(self, cli_runner, env_with_seeds):
        """Verify defer changes status to deferred."""
        result = cli_runner.invoke(main, ["defer", "seed-test1"])
        assert result.exit_code == 0
        assert "Deferred" in result.output

        store = _store()
        seed = store.get("seed-test1")
        assert seed.status == SeedStatus.DEFERRED

    def test_resolve_changes_status(self, cli_runner, env_with_seeds):
        """Verify resolve changes status to resolved."""
        result = cli_runner.invoke(main, ["resolve", "seed-test2"])
        assert result.exit_code == 0
        assert "Resolved" in result.output

        store = _store()
        seed = store.get("seed-test2")
        assert seed.status == SeedStatus.RESOLVED
        assert seed.resolved_at is not None
        assert seed.resolution == ""

    def test_resolve_with_resolution(self, cli_runner, env_with_seeds):
        """Verify resolve captures resolution text."""
        result = cli_runner.invoke(
            main,
            ["resolve", "seed-test2", "--resolution", "Shipped in PR #42"],
        )
        assert result.exit_code == 0
        assert "Resolved" in result.output
        assert "Shipped in PR #42" in result.output

        store = _store()
        seed = store.get("seed-test2")
        assert seed.status == SeedStatus.RESOLVED
        assert seed.resolution == "Shipped in PR #42"

    def test_abandon_changes_status(self, cli_runner, env_with_seeds):
        """Verify abandon changes status to abandoned."""
        result = cli_runner.invoke(main, ["abandon", "seed-test2"])
        assert result.exit_code == 0
        assert "Abandoned" in result.output

        store = _store()
        seed = store.get("seed-test2")
        assert seed.status == SeedStatus.ABANDONED

    def test_abandon_with_reason(self, cli_runner, env_with_seeds):
        """Verify abandon captures reason in resolution field."""
        result = cli_runner.invoke(
            main,
            ["abandon", "seed-test2", "--reason", "Not feasible"],
        )
        assert result.exit_code == 0
        assert "Not feasible" in result.output

        store = _store()
        seed = store.get("seed-test2")
        assert seed.resolution == "Not feasible"


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
        store = _store()
        seed = store.get("seed-test2")
        assert str(target) in seed.resolution

    def test_trellis_tag_idempotent(self, cli_runner, env_with_seeds):
        """Tags the seed 'trellis', without duplicating on repeat."""
        target = env_with_seeds / "TRELLISES.md"
        args = ["trellis", "seed-test2", "--to", str(target), "--as", "A principle"]
        assert cli_runner.invoke(main, args).exit_code == 0
        # Run it a second time — the tag must not be duplicated.
        assert cli_runner.invoke(main, args).exit_code == 0
        store = _store()
        seed = store.get("seed-test2")
        assert seed.tags.count("trellis") == 1

    def test_trellis_resolves_by_default(self, cli_runner, env_with_seeds):
        """Making a trellis resolves the seed by default."""
        target = env_with_seeds / "TRELLISES.md"
        result = cli_runner.invoke(
            main,
            ["trellis", "seed-test2", "--to", str(target), "--as", "A principle"],
        )
        assert result.exit_code == 0
        store = _store()
        seed = store.get("seed-test2")
        assert seed.status == SeedStatus.RESOLVED
        assert seed.resolved_at is not None

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
        store = _store()
        seed = store.get("seed-test2")
        assert seed.status == SeedStatus.EXPLORING
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


class TestRetypeCommand:
    """Tests for 'seeds retype' (bulk type remap, bead seeds-scq)."""

    def _seed(self, store, seed_id, seed_type):
        store.create(_record(id=seed_id, title=f"Seed {seed_id}", seed_type=seed_type))

    def test_retype_changes_every_matching_seed(self, cli_runner, env_with_seeds):
        store = _store()
        self._seed(store, "seed-a", "ideea")
        self._seed(store, "seed-b", "ideea")
        self._seed(store, "seed-c", "idea")

        result = cli_runner.invoke(main, ["retype", "--from", "ideea", "--to", "idea"])
        assert result.exit_code == 0
        assert "seed-a" in result.output and "seed-b" in result.output

        store = _store()
        assert store.get("seed-a").seed_type == "idea"
        assert store.get("seed-b").seed_type == "idea"

    def test_dry_run_writes_nothing(self, cli_runner, env_with_seeds):
        store = _store()
        self._seed(store, "seed-a", "ideea")

        result = cli_runner.invoke(
            main, ["retype", "--from", "ideea", "--to", "idea", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "DRY RUN" in result.output

        store = _store()
        assert store.get("seed-a").seed_type == "ideea"

    def test_no_sidecar_backup_is_written(self, cli_runner, env_with_seeds):
        """The backup step went with the database it copied.

        `retype` used to `cp` the gitignored .db beside itself before a bulk
        edit. The seed files are tracked, so `git diff` shows what changed and
        `git checkout` undoes it -- a strictly better backup than a sidecar
        nobody would have found. Nothing untracked is left behind.
        """
        store = _store()
        self._seed(store, "seed-a", "ideea")

        result = cli_runner.invoke(main, ["retype", "--from", "ideea", "--to", "idea"])

        assert result.exit_code == 0
        assert "Backed up" not in result.output
        assert list((env_with_seeds / SEEDS_DIR).glob("*.bak")) == []

    def test_no_match_touches_nothing(self, cli_runner, env_with_seeds):
        result = cli_runner.invoke(
            main, ["retype", "--from", "nonexistent", "--to", "idea"]
        )
        assert result.exit_code == 0
        assert "nothing to do" in result.output

    def test_same_from_and_to_is_refused_as_a_noop(self, cli_runner, env_with_seeds):
        result = cli_runner.invoke(main, ["retype", "--from", "idea", "--to", "idea"])
        assert result.exit_code == 0
        assert "nothing to do" in result.output

    def test_arbitrary_types_accepted_both_sides(self, cli_runner, env_with_seeds):
        """The vocabulary is open, so neither --from nor --to is constrained."""
        store = _store()
        self._seed(store, "seed-a", "context")

        result = cli_runner.invoke(
            main, ["retype", "--from", "context", "--to", "background"]
        )
        assert result.exit_code == 0

        store = _store()
        assert store.get("seed-a").seed_type == "background"


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

        store = _store()
        seed = store.get("seed-test1")
        assert seed.title == "New Title"

    def test_update_type(self, cli_runner, env_with_seeds):
        """Verify update can change a seed's type.

        Regression: type was write-once. `seeds update` had no --type at all,
        so the only way to fix a wrong one was hand-editing the JSONL -- the
        same door the malformed records in seed seeds-1x6b came through.
        """
        result = cli_runner.invoke(
            main,
            ["update", "seed-test1", "--type", "decision"],
        )
        assert result.exit_code == 0

        store = _store()
        assert store.get("seed-test1").seed_type == "decision"

    def test_update_type_accepts_arbitrary_value(self, cli_runner, env_with_seeds):
        """The vocabulary is open here too, matching `seeds create`."""
        result = cli_runner.invoke(
            main,
            ["update", "seed-test1", "--type", "context"],
        )
        assert result.exit_code == 0

        store = _store()
        assert store.get("seed-test1").seed_type == "context"

    def test_update_type_composes_with_other_fields(self, cli_runner, env_with_seeds):
        """--type is an ordinary field edit, usable alongside the rest."""
        result = cli_runner.invoke(
            main,
            ["update", "seed-test1", "--type", "concern", "--title", "Renamed"],
        )
        assert result.exit_code == 0

        store = _store()
        seed = store.get("seed-test1")
        assert seed.seed_type == "concern"
        assert seed.title == "Renamed"

    def test_update_append_content(self, cli_runner, env_with_seeds):
        """Verify update --append adds to content."""
        result = cli_runner.invoke(
            main,
            ["update", "seed-test1", "--append", "Additional thoughts"],
        )
        assert result.exit_code == 0

        store = _store()
        seed = store.get("seed-test1")
        assert "Additional thoughts" in seed.body

    def test_update_no_changes(self, cli_runner, env_with_seeds):
        """Verify update without changes shows message."""
        result = cli_runner.invoke(main, ["update", "seed-test1"])
        assert result.exit_code == 0
        assert "No changes specified" in result.output


class TestUpdateContentGuard:
    """Tests for the --content guard against discarding deliberation.

    The gate is whether the seed has been edited since creation, never how
    much content it holds -- see the module docstring on ``update``.
    """

    def _create(self, cli_runner, content="Original capture"):
        """Create a seed via the CLI and return its minted ID."""
        result = cli_runner.invoke(
            main, ["create", "--title", "Guarded seed", "--content", content]
        )
        assert result.exit_code == 0, result.output
        return _extract_created_id(result.output)

    def _content_of(self, seed_id):
        """The seed's body, minus the file's own terminating newline.

        A seed file ends with exactly one newline and the reader hands the body
        back verbatim, so ``body`` always carries it. That newline is the
        file's, not the deliberation's, and no assertion below is about it.
        """
        return _store().get(seed_id).body.rstrip("\n")

    def test_virgin_seed_content_replaced_silently(self, cli_runner, initialized_env):
        """A seed never edited since creation accepts -c with no complaint."""
        seed_id = self._create(cli_runner)

        result = cli_runner.invoke(main, ["update", seed_id, "-c", "replaced"])
        assert result.exit_code == 0, result.output
        assert result.stderr == ""
        assert self._content_of(seed_id) == "replaced"

        shown = cli_runner.invoke(main, ["show", seed_id])
        assert "replaced" in shown.output

    def test_edited_seed_content_refused(self, cli_runner, initialized_env):
        """Once appended to, -c exits non-zero and changes nothing."""
        seed_id = self._create(cli_runner)
        assert cli_runner.invoke(main, ["update", seed_id, "-a", "more"]).exit_code == 0
        before = self._content_of(seed_id)

        result = cli_runner.invoke(main, ["update", seed_id, "-c", "wiped"])
        assert result.exit_code != 0
        assert self._content_of(seed_id) == before

        shown = cli_runner.invoke(main, ["show", seed_id])
        assert "wiped" not in shown.output
        assert "Original capture" in shown.output

    def test_refusal_names_append_and_replace(self, cli_runner, initialized_env):
        """The refusal points at both the safe verb and the override."""
        seed_id = self._create(cli_runner)
        cli_runner.invoke(main, ["update", seed_id, "-a", "more"])

        result = cli_runner.invoke(main, ["update", seed_id, "-c", "wiped"])
        assert "--append" in result.stderr
        assert "--replace" in result.stderr

    def test_refusal_reports_character_count_and_first_line(
        self, cli_runner, initialized_env
    ):
        """The refusal quantifies the loss and shows what it would discard."""
        seed_id = self._create(cli_runner, content="First line here\nSecond line")
        cli_runner.invoke(main, ["update", seed_id, "-a", "more"])

        result = cli_runner.invoke(main, ["update", seed_id, "-c", "x"])
        assert re.search(r"[0-9]+ char", result.stderr), result.stderr
        assert "First line here" in result.stderr
        assert "Second line" not in result.stderr

    def test_refusal_warns_that_replace_leaves_git_history(
        self, cli_runner, initialized_env
    ):
        """--replace stops the bleeding; it does not scrub git history."""
        seed_id = self._create(cli_runner)
        cli_runner.invoke(main, ["update", seed_id, "-a", "more"])

        result = cli_runner.invoke(main, ["update", seed_id, "-c", "wiped"])
        assert "git history" in result.stderr

    def test_replace_flag_overrides_the_guard(self, cli_runner, initialized_env):
        """--replace performs the discard the bare -c refused."""
        seed_id = self._create(cli_runner)
        cli_runner.invoke(main, ["update", seed_id, "-a", "more"])

        result = cli_runner.invoke(
            main, ["update", seed_id, "-c", "wiped", "--replace"]
        )
        assert result.exit_code == 0, result.output
        assert self._content_of(seed_id) == "wiped"

    def test_guard_fires_for_any_edit_not_just_append(
        self, cli_runner, initialized_env
    ):
        """The gate is updated_at, so a status change arms it too."""
        seed_id = self._create(cli_runner)
        assert cli_runner.invoke(main, ["explore", seed_id]).exit_code == 0

        result = cli_runner.invoke(main, ["update", seed_id, "-c", "wiped"])
        assert result.exit_code != 0
        assert self._content_of(seed_id) == "Original capture"

    def test_empty_content_seed_can_be_filled_after_an_edit(
        self, cli_runner, initialized_env
    ):
        """Nothing accumulated means nothing to protect: -c just works."""
        jotted = cli_runner.invoke(main, ["jot", "A bodyless thought"])
        seed_id = _extract_jot_id(jotted.output)
        assert cli_runner.invoke(main, ["explore", seed_id]).exit_code == 0

        result = cli_runner.invoke(main, ["update", seed_id, "-c", "the body"])
        assert result.exit_code == 0, result.output
        assert self._content_of(seed_id) == "the body"

    def test_append_unaffected_on_edited_seed(self, cli_runner, initialized_env):
        """--append keeps working after the seed has deliberation in it."""
        seed_id = self._create(cli_runner)
        first = cli_runner.invoke(main, ["update", seed_id, "-a", "first"])
        assert first.exit_code == 0, first.output

        result = cli_runner.invoke(main, ["update", seed_id, "-a", "second"])
        assert result.exit_code == 0, result.output
        content = self._content_of(seed_id)
        assert content == "Original capture\n\nfirst\n\nsecond"

    def test_title_has_no_guard(self, cli_runner, initialized_env):
        """--title stays freely replaceable on an edited seed."""
        seed_id = self._create(cli_runner)
        cli_runner.invoke(main, ["update", seed_id, "-a", "more"])

        result = cli_runner.invoke(main, ["update", seed_id, "--title", "Renamed"])
        assert result.exit_code == 0, result.output

        store = _store()
        assert store.get(seed_id).title == "Renamed"

    def test_tags_have_no_guard(self, cli_runner, initialized_env):
        """--tags replacement stays unguarded: tags are working state."""
        seed_id = self._create(cli_runner)
        cli_runner.invoke(main, ["update", seed_id, "-a", "more"])

        result = cli_runner.invoke(main, ["update", seed_id, "--tags", "a,b"])
        assert result.exit_code == 0, result.output

        store = _store()
        assert store.get(seed_id).tags == ["a", "b"]


class TestUpdateContentInput:
    """Tests for 'update --content-file' / '--content -' (see bead seeds-lf5).

    These are three spellings of one replacement, so what is asserted is that
    they land the same body, clear the same guard the same way, and refuse to
    be combined instead of picking a winner.
    """

    def _create(self, cli_runner, content="Original capture"):
        result = cli_runner.invoke(
            main, ["create", "--title", "Filed seed", "--content", content]
        )
        assert result.exit_code == 0, result.output
        return _extract_created_id(result.output)

    def _content_of(self, seed_id):
        """The seed's body, minus the file's own terminating newline.

        A seed file ends with exactly one newline and the reader hands the body
        back verbatim, so ``body`` always carries it. That newline is the
        file's, not the deliberation's, and no assertion below is about it.
        """
        return _store().get(seed_id).body.rstrip("\n")

    def test_content_file_replaces_the_body(self, cli_runner, initialized_env):
        seed_id = self._create(cli_runner)
        body = initialized_env / "body.md"
        body.write_text("line one\n\nline two\n")

        result = cli_runner.invoke(
            main, ["update", seed_id, "--content-file", str(body)]
        )
        assert result.exit_code == 0, result.output
        assert self._content_of(seed_id) == "line one\n\nline two"

    def test_content_file_keeps_quotes_and_newlines_intact(
        self, cli_runner, initialized_env
    ):
        """The whole point: text argv would mangle survives the file route."""
        seed_id = self._create(cli_runner)
        awkward = 'it\'s "quoted" $HOME `backticks`\nand a second line'
        body = initialized_env / "body.md"
        body.write_text(awkward)

        result = cli_runner.invoke(
            main, ["update", seed_id, "--content-file", str(body)]
        )
        assert result.exit_code == 0, result.output
        assert self._content_of(seed_id) == awkward

    def test_content_dash_reads_stdin(self, cli_runner, initialized_env):
        seed_id = self._create(cli_runner)

        result = cli_runner.invoke(
            main, ["update", seed_id, "-c", "-"], input="piped body\n"
        )
        assert result.exit_code == 0, result.output
        assert self._content_of(seed_id) == "piped body"

    def test_missing_content_file_is_refused(self, cli_runner, initialized_env):
        seed_id = self._create(cli_runner)

        result = cli_runner.invoke(
            main, ["update", seed_id, "--content-file", "no-such-file.md"]
        )
        assert result.exit_code != 0
        assert "--content-file" in result.stderr
        assert self._content_of(seed_id) == "Original capture"

    def test_content_file_dash_points_at_the_one_stdin_spelling(
        self, cli_runner, initialized_env
    ):
        """Stdin has exactly one spelling; the other is redirected, not aliased."""
        seed_id = self._create(cli_runner)

        result = cli_runner.invoke(
            main, ["update", seed_id, "--content-file", "-"], input="piped body\n"
        )
        assert result.exit_code != 0
        assert "--content -" in result.stderr
        assert self._content_of(seed_id) == "Original capture"

    def test_content_and_content_file_together_are_refused(
        self, cli_runner, initialized_env
    ):
        """Refused, not resolved by precedence -- a silent winner is the bug."""
        seed_id = self._create(cli_runner)
        body = initialized_env / "body.md"
        body.write_text("from the file")

        result = cli_runner.invoke(
            main,
            ["update", seed_id, "-c", "from argv", "--content-file", str(body)],
        )
        assert result.exit_code != 0
        assert "ambiguous" in result.stderr
        assert self._content_of(seed_id) == "Original capture"

    def test_content_file_respects_the_edited_seed_guard(
        self, cli_runner, initialized_env
    ):
        seed_id = self._create(cli_runner)
        assert cli_runner.invoke(main, ["update", seed_id, "-a", "more"]).exit_code == 0
        body = initialized_env / "body.md"
        body.write_text("wiped")

        result = cli_runner.invoke(
            main, ["update", seed_id, "--content-file", str(body)]
        )
        assert result.exit_code != 0
        assert "--replace" in result.stderr
        assert "wiped" not in self._content_of(seed_id)

    def test_stdin_respects_the_edited_seed_guard(self, cli_runner, initialized_env):
        seed_id = self._create(cli_runner)
        assert cli_runner.invoke(main, ["update", seed_id, "-a", "more"]).exit_code == 0

        result = cli_runner.invoke(
            main, ["update", seed_id, "-c", "-"], input="wiped\n"
        )
        assert result.exit_code != 0
        assert "--replace" in result.stderr
        assert "wiped" not in self._content_of(seed_id)

    def test_replace_overrides_the_guard_for_the_file_route(
        self, cli_runner, initialized_env
    ):
        seed_id = self._create(cli_runner)
        cli_runner.invoke(main, ["update", seed_id, "-a", "more"])
        body = initialized_env / "body.md"
        body.write_text("deliberately rebuilt")

        result = cli_runner.invoke(
            main, ["update", seed_id, "--content-file", str(body), "--replace"]
        )
        assert result.exit_code == 0, result.output
        assert self._content_of(seed_id) == "deliberately rebuilt"

    def test_replace_overrides_the_guard_for_the_stdin_route(
        self, cli_runner, initialized_env
    ):
        seed_id = self._create(cli_runner)
        cli_runner.invoke(main, ["update", seed_id, "-a", "more"])

        result = cli_runner.invoke(
            main,
            ["update", seed_id, "-c", "-", "--replace"],
            input="deliberately rebuilt\n",
        )
        assert result.exit_code == 0, result.output
        assert self._content_of(seed_id) == "deliberately rebuilt"

    def test_both_routes_are_documented_in_help(self, cli_runner):
        result = cli_runner.invoke(main, ["update", "--help"])
        assert result.exit_code == 0
        assert "--content-file" in result.output


class TestUpdateTagEdits:
    """Tests for 'update --add-tag/--remove-tag' (see bead seeds-3ps).

    The point of these flags is that changing one tag stops being a
    read-modify-write whose write nobody checks -- so most of what is asserted
    here is that the tags nobody named came through untouched and in order.
    """

    def _create(self, cli_runner, tags="alpha,beta,gamma"):
        """Create a tagged seed via the CLI and return its minted ID."""
        result = cli_runner.invoke(
            main, ["create", "--title", "Tagged seed", "--tags", tags]
        )
        assert result.exit_code == 0, result.output
        return _extract_created_id(result.output)

    def _tags_of(self, seed_id):
        store = _store()
        return store.get(seed_id).tags

    def test_add_tag_keeps_every_existing_tag(self, cli_runner, initialized_env):
        """--add-tag appends without disturbing what was already there."""
        seed_id = self._create(cli_runner)

        result = cli_runner.invoke(main, ["update", seed_id, "--add-tag", "delta"])
        assert result.exit_code == 0, result.output
        assert self._tags_of(seed_id) == ["alpha", "beta", "gamma", "delta"]

        shown = cli_runner.invoke(main, ["show", seed_id])
        assert "Tags: alpha, beta, gamma, delta" in shown.output

    def test_add_tag_is_repeatable(self, cli_runner, initialized_env):
        """Two --add-tag flags in one call add both, in the order given."""
        seed_id = self._create(cli_runner)

        result = cli_runner.invoke(
            main, ["update", seed_id, "--add-tag", "delta", "--add-tag", "epsilon"]
        )
        assert result.exit_code == 0, result.output
        assert self._tags_of(seed_id) == [
            "alpha",
            "beta",
            "gamma",
            "delta",
            "epsilon",
        ]

    def test_add_tag_already_present_does_not_duplicate(
        self, cli_runner, initialized_env
    ):
        """Adding a tag the seed carries is a no-op, not a second copy."""
        seed_id = self._create(cli_runner)

        result = cli_runner.invoke(main, ["update", seed_id, "--add-tag", "beta"])
        assert result.exit_code == 0, result.output
        assert self._tags_of(seed_id) == ["alpha", "beta", "gamma"]
        assert "0 added" in result.output

    def test_remove_tag_removes_only_that_tag(self, cli_runner, initialized_env):
        """--remove-tag takes out one tag and leaves the others in place."""
        seed_id = self._create(cli_runner)

        result = cli_runner.invoke(main, ["update", seed_id, "--remove-tag", "beta"])
        assert result.exit_code == 0, result.output
        assert self._tags_of(seed_id) == ["alpha", "gamma"]

    def test_remove_tag_is_repeatable(self, cli_runner, initialized_env):
        """Two --remove-tag flags in one call remove both."""
        seed_id = self._create(cli_runner)

        result = cli_runner.invoke(
            main, ["update", seed_id, "--remove-tag", "alpha", "--remove-tag", "gamma"]
        )
        assert result.exit_code == 0, result.output
        assert self._tags_of(seed_id) == ["beta"]

    def test_remove_absent_tag_is_a_silent_no_op(self, cli_runner, initialized_env):
        """A typo'd tag exits 0, changes nothing, and reports 0 removed.

        Locked decision: erroring would abort an agent's batch mid-loop, so the
        count is the signal instead.
        """
        seed_id = self._create(cli_runner)

        result = cli_runner.invoke(main, ["update", seed_id, "--remove-tag", "nope"])
        assert result.exit_code == 0, result.output
        assert result.stderr == ""
        assert "0 removed" in result.output
        assert self._tags_of(seed_id) == ["alpha", "beta", "gamma"]

    def test_no_op_removal_does_not_touch_updated_at(self, cli_runner, initialized_env):
        """A request that matched nothing must not count as an edit.

        Otherwise a typo would silently arm the --content guard on a seed
        nobody actually changed.
        """
        seed_id = self._create(cli_runner)
        store = _store()
        before = store.get(seed_id).updated_at

        assert (
            cli_runner.invoke(
                main, ["update", seed_id, "--remove-tag", "nope"]
            ).exit_code
            == 0
        )

        store = _store()
        assert store.get(seed_id).updated_at == before

    def test_add_and_remove_compose_in_one_invocation(
        self, cli_runner, initialized_env
    ):
        """The two flags work together: swap one tag for another in one call."""
        seed_id = self._create(cli_runner)

        result = cli_runner.invoke(
            main,
            ["update", seed_id, "--remove-tag", "beta", "--add-tag", "delta"],
        )
        assert result.exit_code == 0, result.output
        assert self._tags_of(seed_id) == ["alpha", "gamma", "delta"]
        assert "1 added, 1 removed" in result.output

    def test_untouched_tags_keep_their_authored_order(
        self, cli_runner, initialized_env
    ):
        """Surviving tags are not re-sorted -- that would churn the JSONL diff."""
        seed_id = self._create(cli_runner, tags="zebra,apple,mango")

        result = cli_runner.invoke(
            main,
            ["update", seed_id, "--remove-tag", "apple", "--add-tag", "banana"],
        )
        assert result.exit_code == 0, result.output
        assert self._tags_of(seed_id) == ["zebra", "mango", "banana"]

    def test_tag_edits_work_on_an_edited_seed(self, cli_runner, initialized_env):
        """Tag edits are not content replacement, so the -c guard stays out.

        Landed alongside the guard from bead seeds-884; this is the case that
        matters, since every seed worth re-tagging has been edited.
        """
        seed_id = self._create(cli_runner)
        assert cli_runner.invoke(main, ["update", seed_id, "-a", "more"]).exit_code == 0

        result = cli_runner.invoke(
            main,
            ["update", seed_id, "--add-tag", "delta", "--remove-tag", "alpha"],
        )
        assert result.exit_code == 0, result.output
        assert result.stderr == ""
        assert self._tags_of(seed_id) == ["beta", "gamma", "delta"]

    def test_tags_with_add_tag_is_refused(self, cli_runner, initialized_env):
        """Mixing wholesale replacement with an edit is ambiguous: reject it."""
        seed_id = self._create(cli_runner)

        result = cli_runner.invoke(
            main, ["update", seed_id, "--tags", "x,y", "--add-tag", "delta"]
        )
        assert result.exit_code != 0
        assert "--add-tag" in result.stderr
        assert self._tags_of(seed_id) == ["alpha", "beta", "gamma"]

    def test_tags_with_remove_tag_is_refused(self, cli_runner, initialized_env):
        """Same rejection for the removal side of the pair."""
        seed_id = self._create(cli_runner)

        result = cli_runner.invoke(
            main, ["update", seed_id, "--tags", "x,y", "--remove-tag", "alpha"]
        )
        assert result.exit_code != 0
        assert "--remove-tag" in result.stderr
        assert self._tags_of(seed_id) == ["alpha", "beta", "gamma"]

    def test_same_tag_added_and_removed_is_refused(self, cli_runner, initialized_env):
        """No precedence rule for add-vs-remove of one tag: name the conflict."""
        seed_id = self._create(cli_runner)

        result = cli_runner.invoke(
            main, ["update", seed_id, "--add-tag", "beta", "--remove-tag", "beta"]
        )
        assert result.exit_code != 0
        assert "beta" in result.stderr
        assert self._tags_of(seed_id) == ["alpha", "beta", "gamma"]

    def test_help_documents_the_tags_combination_rule(self, cli_runner):
        """The chosen behavior is discoverable from --help, not just the code."""
        result = cli_runner.invoke(main, ["update", "--help"])
        assert result.exit_code == 0
        # Collapse click's line wrapping so the assertion is about the wording,
        # not about where the terminal width happened to break it.
        unwrapped = " ".join(result.output.split())
        assert "--add-tag" in unwrapped
        assert "--remove-tag" in unwrapped
        assert "cannot be combined with --tags" in unwrapped
        assert "cannot be mixed in one command" in unwrapped

    def test_wholesale_tags_still_replaces(self, cli_runner, initialized_env):
        """--tags is untouched by this bead: it still resets the whole set."""
        seed_id = self._create(cli_runner)

        result = cli_runner.invoke(main, ["update", seed_id, "--tags", "only,these"])
        assert result.exit_code == 0, result.output
        assert self._tags_of(seed_id) == ["only", "these"]

    def test_tags_are_stripped_and_blanks_ignored(self, cli_runner, initialized_env):
        """Whitespace is trimmed like --tags does; an empty tag adds nothing."""
        seed_id = self._create(cli_runner)

        result = cli_runner.invoke(
            main, ["update", seed_id, "--add-tag", "  delta  ", "--add-tag", "   "]
        )
        assert result.exit_code == 0, result.output
        assert self._tags_of(seed_id) == ["alpha", "beta", "gamma", "delta"]
        assert "1 added" in result.output


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


def _write_beads_export(project_root: Path, text: str) -> Path:
    """Write a .beads/issues.jsonl beside the project's .seeds directory."""
    path = project_root / ".beads" / "issues.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class TestBeadRefValidation:
    """Bead IDs count as known references. See bead seeds-90o.

    seeds and beads share a project prefix, so citing a real bead in a seed
    body used to read as a hallucinated seed ID and hard-fail creation.
    """

    def test_create_accepts_bead_ref(self, cli_runner, initialized_env):
        _write_beads_export(
            initialized_env,
            '{"_type":"issue","id":"seeds-230","title":"A real bead"}\n',
        )
        result = cli_runner.invoke(
            main, ["create", "-t", "Test", "-c", "promoted from seeds-230"]
        )
        assert result.exit_code == 0, result.output
        assert "Created seed" in result.output

    def test_update_accepts_bead_ref(self, cli_runner, env_with_seeds):
        _write_beads_export(env_with_seeds, '{"_type":"issue","id":"seeds-230"}\n')
        result = cli_runner.invoke(
            main, ["update", "seed-test1", "--append", "tracked as seeds-230"]
        )
        assert result.exit_code == 0, result.output

    def test_create_still_rejects_id_in_neither(self, cli_runner, initialized_env):
        """The check is narrowed, not disabled."""
        _write_beads_export(initialized_env, '{"_type":"issue","id":"seeds-230"}\n')
        result = cli_runner.invoke(
            main, ["create", "-t", "Test", "-c", "see seeds-99999"]
        )
        assert result.exit_code != 0
        assert "seeds-99999" in result.output

    def test_create_works_with_no_beads_dir(self, cli_runner, initialized_env):
        """Beads is optional: a project with no .beads/ is the normal case."""
        assert not (initialized_env / ".beads").exists()
        result = cli_runner.invoke(main, ["create", "-t", "Test", "-c", "plain body"])
        assert result.exit_code == 0, result.output
        assert "Error" not in result.output
        assert "Warning" not in result.output

    def test_update_works_with_no_beads_dir(self, cli_runner, env_with_seeds):
        assert not (env_with_seeds / ".beads").exists()
        result = cli_runner.invoke(
            main, ["update", "seed-test1", "--append", "see seed-test2"]
        )
        assert result.exit_code == 0, result.output
        assert "Error" not in result.output
        assert "Warning" not in result.output

    def test_create_survives_corrupt_beads_export(self, cli_runner, initialized_env):
        """A broken export degrades to 'no bead IDs known', it does not crash."""
        _write_beads_export(initialized_env, "not json\n")
        result = cli_runner.invoke(main, ["create", "-t", "Test", "-c", "plain body"])
        assert result.exit_code == 0, result.output
        assert "Created seed" in result.output

    def test_corrupt_beads_export_does_not_whitelist_refs(
        self, cli_runner, initialized_env
    ):
        _write_beads_export(initialized_env, "not json\n")
        result = cli_runner.invoke(
            main, ["create", "-t", "Test", "-c", "see seeds-99999"]
        )
        assert result.exit_code != 0
        assert "seeds-99999" in result.output

    def test_beads_export_resolved_from_seeds_dir_not_cwd(self, cli_runner, tmp_path):
        """With SEEDS_DIR pointing elsewhere, the export follows the seeds dir.

        cwd holds a decoy .beads/ that must be ignored; the one beside the
        real seeds directory is what counts.
        """
        project = tmp_path / "project"
        (project / ".seeds").mkdir(parents=True)
        _write_beads_export(project, '{"_type":"issue","id":"seeds-230"}\n')

        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        _write_beads_export(elsewhere, '{"_type":"issue","id":"seeds-99999"}\n')

        original_cwd = os.getcwd()
        os.chdir(elsewhere)
        try:
            with patch("seeds.store.SEEDS_DIR", str(project / ".seeds")):
                store = Store(project / ".seeds")
                store.files_dir.mkdir(parents=True, exist_ok=True)
                store.set_prefix("seeds")
                good = cli_runner.invoke(
                    main, ["create", "-t", "Test", "-c", "see seeds-230"]
                )
                decoy = cli_runner.invoke(
                    main, ["create", "-t", "Test", "-c", "see seeds-99999"]
                )
        finally:
            os.chdir(original_cwd)

        assert good.exit_code == 0, good.output
        assert decoy.exit_code != 0
        assert "seeds-99999" in decoy.output


class TestLiveBeadRefValidation:
    """A bead the throttled export has not caught up with is still real.

    Bead seeds-4co.23: ``bd create`` writes to Dolt and the JSONL export runs
    on an interval, so referencing a bead minted seconds ago was rejected as a
    hallucinated seed ID -- and the only way through was
    ``--allow-unknown-refs``, which switches the whole check off. seeds now
    asks ``bd`` about anything the export did not vouch for.
    """

    def _bd_knows(self, *ids):
        return json.dumps([{"id": bead_id, "title": "A real bead"} for bead_id in ids])

    def _bd_knows_nothing(self):
        return json.dumps({"error": "no issues found matching the provided IDs"})

    def test_create_accepts_bead_missing_from_the_export(
        self, cli_runner, initialized_env, tmp_path, monkeypatch
    ):
        """The regression: no export at all, and the bead was made seconds ago."""
        make_beads_workspace(initialized_env / SEEDS_DIR)
        assert not (initialized_env / ".beads" / "issues.jsonl").exists()
        install_fake_bd(tmp_path, monkeypatch, stdout=self._bd_knows("seeds-230"))
        result = cli_runner.invoke(
            main, ["create", "-t", "Test", "-c", "promoted from seeds-230"]
        )
        assert result.exit_code == 0, result.output
        assert "Created seed" in result.output

    def test_update_accepts_bead_missing_from_the_export(
        self, cli_runner, env_with_seeds, tmp_path, monkeypatch
    ):
        make_beads_workspace(env_with_seeds / SEEDS_DIR)
        _write_beads_export(env_with_seeds, '{"_type":"issue","id":"seeds-1"}\n')
        install_fake_bd(tmp_path, monkeypatch, stdout=self._bd_knows("seeds-230"))
        result = cli_runner.invoke(
            main, ["update", "seed-test1", "--append", "tracked as seeds-230"]
        )
        assert result.exit_code == 0, result.output

    def test_hallucinated_id_is_still_rejected(
        self, cli_runner, initialized_env, tmp_path, monkeypatch
    ):
        """The hole this check exists to plug stays plugged."""
        make_beads_workspace(initialized_env / SEEDS_DIR)
        install_fake_bd(
            tmp_path, monkeypatch, stdout=self._bd_knows_nothing(), exit_code=1
        )
        result = cli_runner.invoke(
            main, ["create", "-t", "Test", "-c", "see seeds-99999"]
        )
        assert result.exit_code != 0
        assert "seeds-99999" in result.output
        assert "may be stale" not in result.output

    def test_only_the_unknown_ids_reach_bd(
        self, cli_runner, initialized_env, tmp_path, monkeypatch
    ):
        """The subprocess is off the happy path: refs the export vouches for
        are never asked about, and a body with no unknown refs never calls bd.
        """
        make_beads_workspace(initialized_env / SEEDS_DIR)
        _write_beads_export(initialized_env, '{"_type":"issue","id":"seeds-230"}\n')
        log = install_fake_bd(tmp_path, monkeypatch, stdout=self._bd_knows("seeds-777"))
        result = cli_runner.invoke(
            main, ["create", "-t", "Test", "-c", "seeds-230 and seeds-777"]
        )
        assert result.exit_code == 0, result.output
        (line,) = call_lines(log)
        _, args = line.split("\t", 1)
        assert args.split() == ["show", "seeds-777", "--json"]

    def test_no_bd_call_when_every_ref_is_known(
        self, cli_runner, initialized_env, tmp_path, monkeypatch
    ):
        make_beads_workspace(initialized_env / SEEDS_DIR)
        _write_beads_export(initialized_env, '{"_type":"issue","id":"seeds-230"}\n')
        log = install_fake_bd(tmp_path, monkeypatch)
        result = cli_runner.invoke(
            main, ["create", "-t", "Test", "-c", "promoted from seeds-230"]
        )
        assert result.exit_code == 0, result.output
        assert call_lines(log) == []

    def test_no_bd_call_without_a_beads_workspace(
        self, cli_runner, initialized_env, tmp_path, monkeypatch
    ):
        """No beads in the project means no subprocess, ever."""
        log = install_fake_bd(tmp_path, monkeypatch, stdout=self._bd_knows("seeds-999"))
        result = cli_runner.invoke(
            main, ["create", "-t", "Test", "-c", "see seeds-99999"]
        )
        assert result.exit_code != 0
        assert call_lines(log) == []
        assert "may be stale" not in result.output

    def test_reports_a_possibly_stale_bead_list_when_bd_is_missing(
        self, cli_runner, initialized_env, tmp_path, monkeypatch
    ):
        """Beads in use but unreachable: say the list may be stale, do not
        pretend the export was the last word.
        """
        make_beads_workspace(initialized_env / SEEDS_DIR)
        hide_bd(monkeypatch, tmp_path)
        result = cli_runner.invoke(
            main, ["create", "-t", "Test", "-c", "see seeds-99999"]
        )
        assert result.exit_code != 0
        assert "seeds-99999" in result.output
        assert "may be stale" in result.output
        assert "issues.jsonl" in result.output

    def test_allow_unknown_refs_still_skips_bd_entirely(
        self, cli_runner, initialized_env, tmp_path, monkeypatch
    ):
        make_beads_workspace(initialized_env / SEEDS_DIR)
        log = install_fake_bd(tmp_path, monkeypatch)
        result = cli_runner.invoke(
            main,
            ["create", "-t", "Test", "-c", "see seeds-99999", "--allow-unknown-refs"],
        )
        assert result.exit_code == 0, result.output
        assert call_lines(log) == []


class TestBase36RefValidation:
    """Hash-shaped references are checked too. See bead seeds-819.

    Before this, ``find_id_refs`` discarded every non-numeric token before it
    was looked up, so a body citing a base36 ID that never existed sailed
    through — the exact failure the check was built to catch, against the
    scheme every new ID now uses.
    """

    ALLOWLISTED_BODY = (
        "the seeds-marketplace plugin, seeds-cli on PyPI, a seeds-native "
        "workflow, the seeds-tool itself, seeds-generated output, "
        "seeds-level concerns, seeds-like tools, and the seeds-side of it"
    )

    # A fixed hash-shaped ID for the reference under test. The letters in the
    # suffix are load-bearing: they put the ref on the base36 path rather than
    # the numeric one, and pinning them here (instead of minting an ID and
    # hoping) is what keeps that deterministic. See bead seeds-oaw.
    HASH_ID = "seeds-k3n7"

    def test_create_rejects_hallucinated_hash_ref(self, cli_runner, initialized_env):
        result = cli_runner.invoke(
            main, ["create", "-t", "Test", "-c", "see seeds-zq4x"]
        )
        assert result.exit_code != 0, result.output
        assert "unknown IDs" in result.output
        assert "seeds-zq4x" in result.output

    def test_create_rejects_hallucinated_hash_ref_in_title(
        self, cli_runner, initialized_env
    ):
        result = cli_runner.invoke(main, ["create", "-t", "Follow-up to seeds-zq4x"])
        assert result.exit_code != 0, result.output
        assert "seeds-zq4x" in result.output

    def test_update_rejects_hallucinated_hash_ref(self, cli_runner, env_with_seeds):
        result = cli_runner.invoke(
            main, ["update", "seed-test1", "--append", "see seeds-zq4x"]
        )
        assert result.exit_code != 0, result.output
        assert "seeds-zq4x" in result.output

    def test_allow_unknown_refs_still_overrides(self, cli_runner, initialized_env):
        result = cli_runner.invoke(
            main,
            ["create", "-t", "Test", "-c", "see seeds-zq4x", "--allow-unknown-refs"],
        )
        assert result.exit_code == 0, result.output
        assert "Created seed" in result.output

    def test_allowlisted_prose_terms_accepted(self, cli_runner, initialized_env):
        """All eight measured domain terms pass without an override."""
        result = cli_runner.invoke(
            main, ["create", "-t", "Test", "-c", self.ALLOWLISTED_BODY]
        )
        assert result.exit_code == 0, result.output
        assert "Created seed" in result.output

    def test_real_hash_seed_ref_accepted(self, cli_runner, initialized_env):
        """A base36 ID that does exist is a reference, not a hallucination.

        The referenced seed is inserted with a known ID rather than minted by
        ``jot``. next_id() draws a random base36 suffix and base36 includes
        0-9, so ~3% of minted IDs are all digits — which used to fail the
        guard assertion here about one run in 33 (seeds-oaw), the same fact
        behind seeds-skc. The subject of the test must not be random.
        """
        suffix = self.HASH_ID.split("-", 1)[1]
        assert is_hash_suffix(suffix), self.HASH_ID
        assert not suffix.isdigit(), self.HASH_ID

        store = _store()
        store.create(_record(id=self.HASH_ID, title="First seed"))

        result = cli_runner.invoke(
            main, ["create", "-t", "Second", "-c", f"follow-up to {self.HASH_ID}"]
        )
        assert result.exit_code == 0, result.output

    def test_real_bead_ref_accepted(self, cli_runner, initialized_env):
        """Bead lookup (seeds-90o) still short-circuits the stricter check."""
        _write_beads_export(initialized_env, '{"_type":"issue","id":"seeds-230"}\n')
        result = cli_runner.invoke(
            main, ["create", "-t", "Test", "-c", "promoted from seeds-230"]
        )
        assert result.exit_code == 0, result.output

    def test_hash_shaped_bead_ref_accepted(self, cli_runner, initialized_env):
        """Beads mint base36 IDs too; those were invisible before seeds-819."""
        _write_beads_export(initialized_env, '{"_type":"issue","id":"seeds-90o"}\n')
        result = cli_runner.invoke(
            main, ["create", "-t", "Test", "-c", "tracked as seeds-90o"]
        )
        assert result.exit_code == 0, result.output

    def test_error_names_the_allowlist(self, cli_runner, initialized_env):
        """The failure has to say exactly what to add. See bead seeds-819."""
        result = cli_runner.invoke(
            main, ["create", "-t", "Test", "-c", "a seeds-idiosyncratic phrase"]
        )
        assert result.exit_code != 0, result.output
        assert "PROSE_REF_ALLOWLIST" in result.output


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

        store = _store()
        question_seeds = store.questions_for("seed-test1")
        assert len(question_seeds) == 1
        assert question_seeds[0].title == "What is the answer?"
        assert question_seeds[0].seed_type == SeedType.QUESTION

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

        store = _store()
        q_seed = store.get(q_id)
        assert q_seed.body.rstrip("\n") == "42"
        assert q_seed.status == SeedStatus.RESOLVED

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


class TestGuardCopyIsPerCaller:
    """Every command's guard must print remediation that works for THAT command.

    seeds-ijk: `_guard_content_replacement` hardcoded `update`'s prose, so once
    `answer` reused it a guarded re-answer was told to pass a `--content` flag
    that `answer` does not have. That is the same defect class as seeds-pfe,
    where the divergence refusal advised an append its own prefix check could
    never accept -- guidance describing a command other than the one it belongs
    to. These tests pin the property both bugs lacked.
    """

    def _edited_seed(self, cli_runner):
        """A seed that has been appended to, so the guard will fire on it."""
        result = cli_runner.invoke(
            main, ["create", "--title", "Guarded seed", "--content", "Original"]
        )
        assert result.exit_code == 0, result.output
        seed_id = _extract_created_id(result.output)
        assert cli_runner.invoke(main, ["update", seed_id, "-a", "more"]).exit_code == 0
        return seed_id

    def _answered_question(self, cli_runner, seed_id="seed-test1"):
        """A question-seed that already carries an answer."""
        asked = cli_runner.invoke(main, ["ask", "What is it?", "--seed", seed_id])
        assert asked.exit_code == 0, asked.output
        q_id = asked.output.split(":")[0].split()[-1]
        assert cli_runner.invoke(main, ["answer", q_id, "first"]).exit_code == 0
        return q_id

    def test_update_guard_advises_update(self, cli_runner, initialized_env):
        """`update`'s refusal names update, and its own --content/--append flags."""
        seed_id = self._edited_seed(cli_runner)

        result = cli_runner.invoke(main, ["update", seed_id, "-c", "wiped"])
        assert result.exit_code != 0
        assert f"seeds update {seed_id} --append" in result.stderr
        assert f"seeds update {seed_id} --content" in result.stderr
        assert "--replace" in result.stderr

    def test_answer_guard_advises_answer_and_never_mentions_content(
        self, cli_runner, env_with_seeds
    ):
        """`answer`'s refusal names answer -- and never a flag answer lacks.

        The negative assertion is the regression this test exists for: the
        shipped bug was the word `--content` appearing in advice to a command
        that has no such flag.
        """
        q_id = self._answered_question(cli_runner)

        result = cli_runner.invoke(main, ["answer", q_id, "second"])
        assert result.exit_code != 0
        assert f"seeds answer {q_id} " in result.stderr
        assert "--append" in result.stderr
        assert "--replace" in result.stderr
        assert "--content" not in result.stderr
        assert "seeds update" not in result.stderr

    def test_answer_guard_reason_reads_as_an_answer_not_an_edit(
        self, cli_runner, env_with_seeds
    ):
        """The refusal's opening clause describes answering, not editing."""
        q_id = self._answered_question(cli_runner)

        result = cli_runner.invoke(main, ["answer", q_id, "second"])
        assert result.exit_code != 0
        assert "has already been answered" in result.stderr
        assert "answering again would discard" in result.stderr


class TestAnswerContentGuard:
    """Tests for the guard against silently destroying a prior answer.

    seeds-btr: `answer` assigned the body unconditionally, so re-answering an
    already-answered question destroyed the previous answer with no warning.
    Mirrors TestUpdateContentGuard: reuses `_guard_content_replacement`, so a
    question that has never been answered (empty content, untouched
    updated_at) is unaffected -- only a re-answer is guarded.
    """

    def _ask(self, cli_runner, seed_id="seed-test1"):
        """Create a question-seed via `ask` and return its minted ID."""
        result = cli_runner.invoke(
            main, ["ask", "What is the answer?", "--seed", seed_id]
        )
        assert result.exit_code == 0, result.output
        return result.output.split(":")[0].split()[-1]

    def _content_of(self, seed_id):
        """The seed's body, minus the file's own terminating newline.

        A seed file ends with exactly one newline and the reader hands the body
        back verbatim, so ``body`` always carries it. That newline is the
        file's, not the deliberation's, and no assertion below is about it.
        """
        return _store().get(seed_id).body.rstrip("\n")

    def test_first_answer_to_open_question_succeeds_unchanged(
        self, cli_runner, env_with_seeds
    ):
        """The new guard must not touch the ordinary, unanswered-question case."""
        q_id = self._ask(cli_runner)

        result = cli_runner.invoke(main, ["answer", q_id, "42"])
        assert result.exit_code == 0, result.output
        assert result.stderr == ""
        assert self._content_of(q_id) == "42"

        store = _store()
        q_seed = store.get(q_id)
        assert q_seed.status == SeedStatus.RESOLVED
        assert q_seed.resolved_at is not None

    def test_bare_re_answer_is_refused_and_leaves_content_untouched(
        self, cli_runner, env_with_seeds
    ):
        """The defect itself: a second bare `answer` must not destroy the first."""
        q_id = self._ask(cli_runner)
        first = cli_runner.invoke(main, ["answer", q_id, "the original answer"])
        assert first.exit_code == 0, first.output

        result = cli_runner.invoke(main, ["answer", q_id, "an overwriting answer"])
        assert result.exit_code != 0
        assert self._content_of(q_id) == "the original answer"

    def test_replace_flag_overwrites_the_prior_answer(self, cli_runner, env_with_seeds):
        """--replace performs the discard the bare re-answer refused."""
        q_id = self._ask(cli_runner)
        cli_runner.invoke(main, ["answer", q_id, "the original answer"])

        result = cli_runner.invoke(
            main, ["answer", q_id, "the corrected answer", "--replace"]
        )
        assert result.exit_code == 0, result.output
        assert self._content_of(q_id) == "the corrected answer"

    def test_append_flag_records_a_revision_alongside_the_original(
        self, cli_runner, env_with_seeds
    ):
        """--append is the verb for a reversal: keep the original, add the revision."""
        q_id = self._ask(cli_runner)
        cli_runner.invoke(main, ["answer", q_id, "the original answer"])

        result = cli_runner.invoke(
            main, ["answer", q_id, "actually, it reversed", "--append"]
        )
        assert result.exit_code == 0, result.output
        content = self._content_of(q_id)
        assert "the original answer" in content
        assert "actually, it reversed" in content

    def test_append_and_replace_together_are_refused(self, cli_runner, env_with_seeds):
        """The two flags are contradictory; neither should silently win."""
        q_id = self._ask(cli_runner)
        cli_runner.invoke(main, ["answer", q_id, "the original answer"])

        result = cli_runner.invoke(
            main, ["answer", q_id, "which one wins?", "--append", "--replace"]
        )
        assert result.exit_code != 0
        assert self._content_of(q_id) == "the original answer"

    def test_append_re_stamps_resolved_at(self, cli_runner, env_with_seeds):
        """Design pick: every successful answer re-stamps resolved_at to now."""
        q_id = self._ask(cli_runner)
        cli_runner.invoke(main, ["answer", q_id, "the original answer"])
        store = _store()
        first_resolved_at = store.get(q_id).resolved_at

        result = cli_runner.invoke(
            main, ["answer", q_id, "a later revision", "--append"]
        )
        assert result.exit_code == 0, result.output

        store = _store()
        second_resolved_at = store.get(q_id).resolved_at
        assert second_resolved_at > first_resolved_at

    def test_answer_help_documents_both_flags(self, cli_runner):
        result = cli_runner.invoke(main, ["answer", "--help"])
        assert result.exit_code == 0
        assert "--append" in result.output
        assert "--replace" in result.output


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

        # relates-to is symmetric, so it is stored as itself in BOTH files
        # (docs/storage-format.md §5.1/§5.2) -- there is no second table to
        # ask, and a one-sided edge is a `seeds check` violation.
        store = _store()
        near = store.get("seed-test1").relationships
        far = store.get("seed-test2").relationships
        assert [(e.target_id, e.rel_type) for e in near] == [
            ("seed-test2", RelationType.RELATES_TO)
        ]
        assert [(e.target_id, e.rel_type) for e in far] == [
            ("seed-test1", RelationType.RELATES_TO)
        ]
        assert near[0].created_at == far[0].created_at

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

        # `questions` is directional, so the far end stores its named inverse.
        store = _store()
        assert [
            (e.target_id, e.rel_type) for e in store.get("seed-test1").relationships
        ] == [("seed-test2", RelationType.QUESTIONS)]
        assert [
            (e.target_id, e.rel_type) for e in store.get("seed-test2").relationships
        ] == [("seed-test1", RelationType.QUESTIONED_BY)]


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

    def test_prime_teaches_the_cross_repo_rg_recipe(self, cli_runner, initialized_env):
        """Bead seeds-4co.20: the gap prime exists to close.

        All 35 transcript invocations of cross-repo seed search were hand-rolled
        shell loops, reinvented each time, because nothing told the agent how.
        The recipe has to be in the document an agent is handed, not left to
        instinct -- and it has to name the glob rather than a loop.
        """
        result = cli_runner.invoke(main, ["prime"])

        assert result.exit_code == 0
        assert "rg -l" in result.output
        assert "/.seeds/seeds/" in result.output
        assert "-C2" in result.output, "context lines are half of why rg wins"
        assert "do not invent a shell loop" in result.output

    def test_prime_does_not_send_agents_back_to_the_retired_jsonl(
        self, cli_runner, initialized_env
    ):
        result = cli_runner.invoke(main, ["prime"])

        _, _, recipe = result.output.partition("Searching Across Repos")
        assert "retired" in recipe
        assert "stale" in recipe

    def test_prime_frames_export_as_structured_extraction_not_search(
        self, cli_runner, initialized_env
    ):
        result = cli_runner.invoke(main, ["prime"])

        assert "STRUCTURED extraction" in result.output
        assert "DuckDB" in result.output

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
        store = _store()
        seed = _record(
            id="seed-tagged", title="Tagged Seed", tags=["important", "urgent"]
        )
        store.create(seed)

        result = cli_runner.invoke(main, ["show", "seed-tagged"])
        assert result.exit_code == 0
        assert "Tags:" in result.output
        assert "important" in result.output

    def test_show_with_content(self, cli_runner, initialized_env):
        """Verify show displays content."""
        store = _store()
        seed = _record(
            id="seed-content", title="Content Seed", content="Detailed content here"
        )
        store.create(seed)

        result = cli_runner.invoke(main, ["show", "seed-content"])
        assert result.exit_code == 0
        assert "Content:" in result.output
        assert "Detailed content here" in result.output

    def test_show_with_related(self, cli_runner, initialized_env):
        """Verify show displays related seeds via relationships."""
        store = _store()
        seed1 = _record(id="seed-r1", title="Seed 1")
        seed2 = _record(id="seed-r2", title="Seed 2")
        store.create(seed1)
        store.create(seed2)
        store.link("seed-r1", "seed-r2", RelationType.RELATES_TO)

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
        store = _store()
        q_seed = _record(
            id="seeds-qshow", title="Show this?", seed_type=SeedType.QUESTION
        )
        store.create(q_seed)
        store.link("seeds-qshow", "seed-test1", RelationType.QUESTIONS)

        result = cli_runner.invoke(main, ["show", "seed-test1", "--questions"])
        assert result.exit_code == 0
        assert "Questions:" in result.output
        assert "seeds-qshow" in result.output
        assert "Show this?" in result.output

    def test_show_with_answered_question(self, cli_runner, env_with_seeds):
        """Verify show displays answered question-seeds with content."""
        store = _store()
        q_seed = _record(
            id="seeds-qanswered",
            title="Answered?",
            content="Yes it is",
            seed_type=SeedType.QUESTION,
            status=SeedStatus.RESOLVED,
        )
        store.create(q_seed)
        store.link("seeds-qanswered", "seed-test1", RelationType.QUESTIONS)

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

        store = _store()
        seed = store.get("seed-test1")
        assert seed.body.rstrip("\n") == "New content"

    def test_update_tags(self, cli_runner, env_with_seeds):
        """Verify update --tags replaces tags."""
        result = cli_runner.invoke(
            main,
            ["update", "seed-test1", "--tags", "new,tags"],
        )
        assert result.exit_code == 0

        store = _store()
        seed = store.get("seed-test1")
        assert seed.tags == ["new", "tags"]

    def test_update_clear_tags(self, cli_runner, env_with_seeds):
        """Verify update --tags '' clears tags."""
        result = cli_runner.invoke(
            main,
            ["update", "seed-test1", "--tags", ""],
        )
        assert result.exit_code == 0

        store = _store()
        seed = store.get("seed-test1")
        assert seed.tags == []


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
        store = _store()
        q1 = _record(id="seeds-qs1", title="Q for seed1?", seed_type=SeedType.QUESTION)
        q2 = _record(id="seeds-qs2", title="Q for seed2?", seed_type=SeedType.QUESTION)
        store.create(q1)
        store.create(q2)
        store.link("seeds-qs1", "seed-test1", RelationType.QUESTIONS)
        store.link("seeds-qs2", "seed-test2", RelationType.QUESTIONS)

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
        store = _store()
        store.create(_record(id="seed-p", title="Parent"))
        store.create(_record(id="seed-p.1", title="Child"))
        store.create(_record(id="seed-p.1.1", title="Grandchild"))

        result = cli_runner.invoke(main, ["tree", "seed-p"])
        assert result.exit_code == 0
        assert "Children:" in result.output
        assert "seed-p.1" in result.output
        assert "seed-p.1.1" in result.output

    def test_tree_shows_related(self, cli_runner, initialized_env):
        """Verify tree shows related seeds via relationships."""
        store = _store()
        store.create(_record(id="seed-x", title="Main"))
        store.create(_record(id="seed-y", title="Related"))
        store.link("seed-x", "seed-y", RelationType.RELATES_TO)

        result = cli_runner.invoke(main, ["tree", "seed-x"])
        assert result.exit_code == 0
        assert "Related:" in result.output
        assert "seed-y" in result.output

    def test_tree_shows_missing_related(self, cli_runner, initialized_env):
        """Verify tree handles missing related seeds gracefully."""
        store = _store()
        store.create(_record(id="seed-x", title="Main"))
        store.create(_record(id="seed-gone", title="Will be deleted"))
        store.link("seed-x", "seed-gone", RelationType.RELATES_TO)
        # Delete the target's file but leave the edge in seed-x naming it. The
        # foreign key SQLite used to enforce is a file-existence test now, so
        # this is exactly the state `seeds check` reports and `tree` must
        # survive.
        store.path_for("seed-gone").unlink()

        result = cli_runner.invoke(main, ["tree", "seed-x"])
        assert result.exit_code == 0
        assert "seed-gone" in result.output
        assert "(not found)" in result.output


class TestDoctorCommand:
    """Tests for 'seeds doctor' command.

    Every JSONL/DB comparison this class used to hold is gone with the second
    store that made it possible: whether the two agreed, whether an import
    would refuse a record, whether the file held a body the database had never
    seen. There is one store now, so those checks could only ever pass, and a
    check that cannot fail is the "green while broken" shape they were written
    to prevent. What doctor still answers is below; the files themselves are
    `seeds check`'s job, and doctor says so.
    """

    def test_doctor_passes_on_healthy_install(self, cli_runner, env_with_seeds):
        """Verify doctor passes on a healthy installation."""
        result = cli_runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "Seed files at" in result.output
        assert "passed" in result.output

    def test_doctor_reports_no_sync_state(self, cli_runner, env_with_seeds):
        """The two-store section is gone, not silently passing.

        Its replacement points at the command that actually verifies the
        files, rather than reporting a comparison that no longer has two
        things to compare.
        """
        result = cli_runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "JSONL" not in result.output
        assert "seeds check" in result.output

    def test_doctor_fails_on_an_edge_naming_a_missing_seed(
        self, cli_runner, env_with_seeds
    ):
        """The foreign key SQLite enforced is a file-existence test now.

        Deleting a linked seed's file leaves the other end's edge pointing at
        nothing. Nothing structural catches that any more, so doctor has to
        ask -- and it must fail, not warn: an edge to a seed that is not there
        cannot be rendered and cannot be right.
        """
        store = _store()
        store.link("seed-test1", "seed-test2", RelationType.RELATES_TO)
        store.path_for("seed-test2").unlink()

        result = cli_runner.invoke(main, ["doctor"])

        assert result.exit_code == 1
        assert "seed-test1 -> seed-test2" in result.output

    def test_doctor_fails_and_names_the_file_when_a_seed_will_not_read(
        self, cli_runner, env_with_seeds
    ):
        """A strict read refuses the corpus on one bad file, so doctor must
        say WHICH file rather than dying with a traceback."""
        store = _store()
        store.path_for("seed-test2").write_text("not a seed file\n")

        result = cli_runner.invoke(main, ["doctor"])

        assert result.exit_code == 1
        assert "seed-test2.md" in result.output
        assert "seeds check" in result.output

    def test_doctor_warns_on_nonstandard_types_without_failing(
        self, cli_runner, env_with_seeds
    ):
        """A non-standard type is legal, so it warns and does not fail.

        With the vocabulary open (bead seeds-0lb) this is the only thing that
        surfaces a typo, so it is load-bearing rather than cosmetic.
        """
        store = _store()
        store.create(_record(id="seed-typo", title="Typo", seed_type="ideea"))

        result = cli_runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "ideea (1)" in result.output
        assert "seeds retype" in result.output

    def test_doctor_shows_warnings_count(self, cli_runner, initialized_env):
        """Verify doctor shows warning count when there are issues."""
        result = cli_runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        # No open seeds = warning
        assert "warning" in result.output

    def test_doctor_shows_open_questions(self, cli_runner, env_with_seeds):
        """Verify doctor reports open question-seeds."""
        store = _store()
        store.create(
            _record(
                id="seeds-qdoc",
                title="Doctor question?",
                seed_type=SeedType.QUESTION,
            )
        )
        store.link("seeds-qdoc", "seed-test1", RelationType.QUESTIONS)

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
                store = _store()
                store.files_dir.mkdir(parents=True, exist_ok=True)
                store.set_prefix("seeds")  # explicit default

                result = cli_runner.invoke(main, ["doctor"])
                assert result.exit_code == 0
                assert "shiny-project" in result.output
                assert "rename-prefix" in result.output
            finally:
                os.chdir(original_cwd)

    def test_doctor_warns_when_prefix_unconfigured(self, cli_runner):
        """Doctor warns when config.yaml records no prefix.

        A store can reach this state -- a converted repo whose legacy database
        never had one, or a hand-made .seeds/seeds/ -- and the fallback is
        silent, so doctor is what surfaces it.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                _store().files_dir.mkdir(parents=True, exist_ok=True)

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
