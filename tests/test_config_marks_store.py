"""A store with ``.seeds/config.yaml`` but no ``.seeds/seeds/`` is empty (seeds-vpif).

git does not track an empty directory. ``seeds init`` creates an empty
``.seeds/seeds/``, so a project whose ``.seeds/`` is committed before its first
seed has no ``.seeds/seeds/`` in any worktree made from that commit. Before
this bead every store command there said "not initialized", and following that
advice ran ``seeds init`` again, which rewrote the tracked prefix to the
worktree's directory name (seeds-dn8a).

The ruling (seeds-kadx): ``config.yaml`` marks an initialized store, a missing
``seeds/`` reads as an empty store, and the first write creates it. An
unconverted pre-0.7 store still wins over ``config.yaml``: it must keep naming
``seeds convert``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from seeds.cli import main
from seeds.seedfile import write_mdformat_config
from seeds.store import Store, store_initialized
from tests.githelpers import git, git_init
from tests.test_unconverted_messaging import DATA_TOUCHING

CONFIG = "prefix: repo\n"


def _config_only(root: Path) -> Path:
    """``.seeds/`` with config.yaml and .mdformat.toml, and no ``seeds/``."""
    seeds_dir = root / ".seeds"
    seeds_dir.mkdir(parents=True)
    (seeds_dir / "config.yaml").write_text(CONFIG, encoding="utf-8")
    write_mdformat_config(seeds_dir)
    return seeds_dir


@pytest.fixture
def config_only(temp_dir, monkeypatch):
    """A tmp git repo whose ``.seeds/`` holds the config and no seed directory."""
    root = temp_dir / "repo"
    root.mkdir()
    git_init(root)
    seeds_dir = _config_only(root)
    monkeypatch.chdir(root)
    return seeds_dir


#: Read commands, each with the result an empty store gives, computed by hand:
#: (argv, exit code, a line the output must contain or None).
READS = [
    (("list",), 0, None),
    (("show", "repo-zzzz"), 1, None),
    (("ready",), 0, None),
    (("search", "anything"), 0, None),
    (("tree", "repo-zzzz"), 1, None),
    (("prime",), 0, "## Essential Commands"),
    (("export", "--json"), 0, None),
    (("check",), 0, "seeds check: 0 files, no violations."),
]


class TestTheMarker:
    def test_config_alone_marks_an_initialized_store(self, config_only):
        assert store_initialized(config_only) is True
        assert Store(config_only).is_initialized() is True

    def test_the_corpus_is_empty(self, config_only):
        store = Store(config_only)
        assert store.all() == []
        assert store.search("anything") == []

    def test_a_bare_seeds_dir_is_not_initialized(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        seeds_dir.mkdir()
        assert store_initialized(seeds_dir) is False

    def test_needs_conversion_wins_over_config(self, temp_dir):
        seeds_dir = _config_only(temp_dir)
        (seeds_dir / "seeds.jsonl").write_text("", encoding="utf-8")
        assert store_initialized(seeds_dir) is False


class TestReadsSeeAnEmptyStore:
    @pytest.mark.parametrize(("argv", "code", "expected"), READS, ids=lambda v: str(v))
    def test_it_exits_as_on_an_empty_store(
        self, argv, code, expected, config_only, cli_runner
    ):
        result = cli_runner.invoke(main, list(argv))

        assert result.exit_code == code, result.output
        assert "not initialized" not in result.output
        if expected is not None:
            assert expected in result.output, result.output
        assert not (config_only / "seeds").exists()

        # Parity: the same command on the same store with an empty seeds/
        # directory gives the same answer.
        (config_only / "seeds").mkdir()
        with_dir = cli_runner.invoke(main, list(argv))
        assert (with_dir.exit_code, with_dir.output) == (
            result.exit_code,
            result.output,
        )

    def test_export_emits_nothing(self, config_only, cli_runner):
        result = cli_runner.invoke(main, ["export", "--json"])

        assert result.exit_code == 0
        assert result.output == ""

    def test_show_of_a_missing_id_says_not_found(self, config_only, cli_runner):
        result = cli_runner.invoke(main, ["show", "repo-zzzz"])

        assert "not found" in result.output.lower(), result.output

    def test_doctor_says_no_seed_file_exists_yet(self, config_only, cli_runner):
        result = cli_runner.invoke(main, ["doctor"])

        assert "not initialized" not in result.output
        assert "no seed file exists yet" in result.output, result.output
        assert "✗" not in result.output, result.output


class TestTheFirstWriteCreatesTheDirectory:
    def test_jot_creates_the_file_under_the_configured_prefix(
        self, config_only, cli_runner
    ):
        result = cli_runner.invoke(main, ["jot", "x"])

        assert result.exit_code == 0, result.output
        files = list((config_only / "seeds").glob("*.md"))
        assert len(files) == 1
        assert re.fullmatch(r"repo-[0-9a-z]+\.md", files[0].name), files[0].name

    def test_create_creates_the_directory(self, config_only, cli_runner):
        result = cli_runner.invoke(main, ["create", "--title", "A title"])

        assert result.exit_code == 0, result.output
        assert len(list((config_only / "seeds").glob("repo-*.md"))) == 1

    def test_ask_then_lands_beside_the_first_seed(self, config_only, cli_runner):
        """ask needs a seed to attach to, so the directory exists by then."""
        cli_runner.invoke(main, ["jot", "x"])
        (seed_file,) = (config_only / "seeds").glob("*.md")

        result = cli_runner.invoke(main, ["ask", "Why?", "--seed", seed_file.stem])

        assert result.exit_code == 0, result.output
        assert len(list((config_only / "seeds").glob("repo-*.md"))) == 2


class TestInitLeavesTheConfigAlone:
    def test_init_says_already_initialized_and_keeps_the_prefix(
        self, config_only, cli_runner
    ):
        """The seeds-dn8a repro: init used to rewrite prefix to the cwd name."""
        result = cli_runner.invoke(main, ["init"])

        assert result.exit_code == 0, result.output
        assert "already initialized" in result.output
        assert (config_only / "config.yaml").read_text(encoding="utf-8") == CONFIG


class TestUnconvertedStillNamesConvert:
    @pytest.fixture(params=[True, False], ids=["with-config", "without-config"])
    def unconverted(self, request, temp_dir, monkeypatch):
        seeds_dir = temp_dir / ".seeds"
        seeds_dir.mkdir()
        if request.param:
            (seeds_dir / "config.yaml").write_text(CONFIG, encoding="utf-8")
        (seeds_dir / "seeds.jsonl").write_text(
            json.dumps({"format_version": 2, "id": "repo-a1"}) + "\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(temp_dir)
        return seeds_dir

    @pytest.mark.parametrize("argv", DATA_TOUCHING, ids=lambda a: a[0])
    def test_it_names_seeds_convert(self, argv, unconverted, cli_runner):
        result = cli_runner.invoke(main, list(argv))

        assert result.exit_code != 0, result.output
        assert "seeds convert" in result.output, result.output
        assert not (unconverted / "seeds").exists()


class TestBareSeedsDirUnchanged:
    def test_list_still_says_not_initialized(self, temp_dir, monkeypatch, cli_runner):
        (temp_dir / ".seeds").mkdir()
        monkeypatch.chdir(temp_dir)

        result = cli_runner.invoke(main, ["list"])

        assert result.exit_code == 1
        assert "seeds not initialized. Run 'seeds init' first." in result.output

    def test_check_still_reports_store_missing(self, temp_dir, monkeypatch, cli_runner):
        (temp_dir / ".seeds").mkdir()
        monkeypatch.chdir(temp_dir)

        result = cli_runner.invoke(main, ["check"])

        assert result.exit_code == 1
        assert "store-missing" in result.output


class TestAWorktreeOfACommittedEmptyStore:
    def test_list_and_jot_work_in_the_worktree(self, temp_dir, monkeypatch, cli_runner):
        root = temp_dir / "repo"
        root.mkdir()
        git_init(root)
        monkeypatch.chdir(root)
        assert cli_runner.invoke(main, ["init"]).exit_code == 0
        git(root, "add", ".seeds")
        git(root, "commit", "-q", "-m", "seeds init")
        worktree = temp_dir / "wt"
        git(root, "worktree", "add", "-q", str(worktree))
        assert not (worktree / ".seeds" / "seeds").exists()
        config_before = (worktree / ".seeds" / "config.yaml").read_text()
        monkeypatch.chdir(worktree)

        listed = cli_runner.invoke(main, ["list"])
        jotted = cli_runner.invoke(main, ["jot", "x"])

        assert listed.exit_code == 0, listed.output
        assert jotted.exit_code == 0, jotted.output
        assert (worktree / ".seeds" / "config.yaml").read_text() == config_before
        assert "prefix: repo" in config_before
        assert len(list((worktree / ".seeds" / "seeds").glob("repo-*.md"))) == 1
