"""Tests for ``seeds check --gate``, the commit-path check (bead seeds-l80).

``--gate`` replaced ``scripts/seeds_check_hook.py`` (bead seeds-4co.13), and
these cases are that script's suite carried over to the flag, plus what the
flag adds: the ``--smells`` refusal, the seeds-owned escape, and reading a
``seeds rename-prefix`` commit as a rename rather than a mass deletion.

A gate nobody has watched refuse a commit is not a gate. This project has hit
that defect class four times (doctor's mtime proxy, the changelog's commit
count, the missing ``uv lock --check``, and a converter that would have passed
on an empty store), so every case here is a hand-built store with a
hand-computed expected exit status, and both directions are asserted: the gate
refusing what it must refuse, and -- carrying more weight -- letting through
everything else. A gate that blocks ordinary commits gets bypassed, and the
bypass is permanent.

Every git call goes through ``tests.githelpers``; ``tests/test_git_single_door``
fails this file at the AST level otherwise.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from seeds import cli as seeds_cli
from seeds.cli import GATE_CONFIRM_ENV, main
from seeds.models import SeedStatus
from seeds.seedfile import SeedRecord, write_seed
from seeds.store import Store
from tests.githelpers import git, git_init

CREATED = datetime(2026, 8, 28, 14, 2, 11, 481293, tzinfo=UTC)
UPDATED = datetime(2026, 8, 30, 9, 41, 7, 220118, tzinfo=UTC)


def record(seed_id: str, **overrides: object) -> SeedRecord:
    """A valid record, plus overrides. The baseline scores zero findings."""
    fields: dict[str, object] = {
        "id": seed_id,
        "title": "A minimal seed",
        "status": SeedStatus.CAPTURED,
        "seed_type": "idea",
        "created_at": CREATED,
        "updated_at": UPDATED,
        "parent": None,
        "body": "One line of thinking.\n",
    }
    fields.update(overrides)
    return SeedRecord(**fields)  # type: ignore[arg-type]


def make_store(root: Path, *records: SeedRecord) -> Path:
    """Write ``records`` into a store under ``root`` and return its .seeds dir."""
    seeds_dir = root / ".seeds"
    (seeds_dir / "seeds").mkdir(parents=True, exist_ok=True)
    for item in records:
        write_seed(seeds_dir, item)
    return seeds_dir


def corpus(count: int) -> list[SeedRecord]:
    """``count`` distinct, healthy seeds. Bodies differ so no duplicate-body smell."""
    return [
        record(
            f"seeds-a{index:02d}",
            title=f"Seed number {index}",
            body=f"Body {index}.\n",
        )
        for index in range(count)
    ]


def committed_repo(root: Path, *records: SeedRecord) -> Path:
    """A git repo at ``root`` whose HEAD holds ``records``. Returns the .seeds dir."""
    git_init(root)
    seeds_dir = make_store(root, *records)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "the store as HEAD holds it")
    return seeds_dir


@pytest.fixture(autouse=True)
def _no_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    """A confirmation leaking in from the caller's shell would pass everything."""
    monkeypatch.delenv(GATE_CONFIRM_ENV, raising=False)


def gate(monkeypatch: pytest.MonkeyPatch, root: Path, *extra: str) -> Result:
    """Run ``seeds check --gate`` from ``root``, as a recipe or hook would."""
    monkeypatch.chdir(root)
    return CliRunner().invoke(main, ["check", "--gate", *extra])


# --- The skip paths: a missing store must never block a commit ---------------


class TestMissingStoreDoesNotBlock:
    def test_no_seeds_directory_at_all_passes_silently(self, tmp_path, monkeypatch):
        """The one-line recipe runs in every repo, most of which have no seeds."""
        (tmp_path / "somewhere").mkdir()
        result = gate(monkeypatch, tmp_path / "somewhere")
        assert result.exit_code == 0, result.output
        assert result.output == ""

    def test_pre_conversion_store_passes_with_one_line(self, tmp_path, monkeypatch):
        """.seeds/ exists but .seeds/seeds/ does not: a repo not yet converted.

        Plain `seeds check` refuses here, correctly for a checker and wrongly
        for a gate that would then refuse every commit in the repo.
        """
        (tmp_path / ".seeds").mkdir()
        (tmp_path / ".seeds" / "seeds.jsonl").write_text("")
        result = gate(monkeypatch, tmp_path)
        assert result.exit_code == 0, result.output
        assert result.output.strip().count("\n") == 0
        assert "nothing to gate" in result.output

    def test_store_missing_cue_is_not_a_blanket_pass(self, tmp_path, monkeypatch):
        """One finding is the cue only when its code is store-missing.

        Guards the cheap wrong version -- `len(findings) == 1` without
        inspecting the code -- which would wave through every store holding
        exactly one violation.
        """
        seeds_dir = committed_repo(tmp_path, record("seeds-a01"))
        (seeds_dir / "seeds" / "seeds-a02.md").write_text("not a seed file at all\n")
        assert gate(monkeypatch, tmp_path).exit_code == 1


# --- What runs: violations plus --against-git, never --smells ----------------


class TestWhatTheGateRuns:
    def test_healthy_store_passes_and_runs_both_gating_tiers(
        self, tmp_path, monkeypatch
    ):
        committed_repo(tmp_path, *corpus(20))
        result = gate(monkeypatch, tmp_path)
        assert result.exit_code == 0, result.output
        assert "20 files, no violations" in result.output
        assert "seeds check --against-git: 20 seed(s) at HEAD~1" not in result.output
        assert "seeds check --against-git: 20 seed(s)" in result.output

    def test_the_smells_tier_is_never_run(self, tmp_path, monkeypatch):
        """--smells never gates, and it was ~94% of the hook's time (seeds-7q8g).

        Pinned by making the smells tier explode if called, so the slow,
        non-gating tier cannot drift back into every commit.
        """

        def explode(*_args: object, **_kwargs: object) -> None:
            raise AssertionError("--gate ran the smells tier")

        monkeypatch.setattr(seeds_cli, "check_smells", explode)
        committed_repo(
            tmp_path, *[record(f"seeds-a{index:02d}", body="") for index in range(20)]
        )
        result = gate(monkeypatch, tmp_path)
        assert result.exit_code == 0, result.output
        assert "smell" not in result.output

    def test_gate_with_smells_is_a_usage_error(self, tmp_path, monkeypatch):
        """The ruling is "never smells"; asking for both is a contradiction."""
        committed_repo(tmp_path, *corpus(20))
        result = gate(monkeypatch, tmp_path, "--smells")
        assert result.exit_code == 2
        assert "--gate never runs --smells" in result.output

    def test_gate_with_against_git_is_accepted(self, tmp_path, monkeypatch):
        """Redundant, since --gate implies it, and harmless."""
        committed_repo(tmp_path, *corpus(20))
        result = gate(monkeypatch, tmp_path, "--against-git")
        assert result.exit_code == 0, result.output
        assert "seeds check --against-git:" in result.output

    def test_smells_everywhere_do_not_block(self, tmp_path, monkeypatch):
        """20 empty bodies -- a candidate for attention, never an error."""
        committed_repo(
            tmp_path, *[record(f"seeds-a{index:02d}", body="") for index in range(20)]
        )
        assert gate(monkeypatch, tmp_path).exit_code == 0


# --- The violations tier gates -----------------------------------------------


class TestViolationsBlock:
    def test_unparseable_file_blocks_and_names_the_escape(self, tmp_path, monkeypatch):
        """A blocked commit that does not name its escape invites --no-verify."""
        seeds_dir = committed_repo(tmp_path, *corpus(20))
        (seeds_dir / "seeds" / "seeds-a03.md").write_text("### not front matter\n")
        result = gate(monkeypatch, tmp_path)
        assert result.exit_code == 1
        assert f"{GATE_CONFIRM_ENV}=1 git commit" in result.output


# --- The --against-git tier gates the mass-rewrite shape ---------------------


def sweep_titles(seeds_dir: Path, count: int) -> None:
    """The seeds-wurl shape, scaled down: titles replaced by a scratchpad path."""
    for index in range(count):
        write_seed(
            seeds_dir,
            record(f"seeds-a{index:02d}", title="scratchpad", body=f"Body {index}.\n"),
        )


class TestMassRewriteBlocks:
    def test_mass_title_rewrite_blocks_and_names_the_escape(
        self, tmp_path, monkeypatch
    ):
        """10 of 20 titles is 50% -- over 20%, and at the 10-seed floor."""
        seeds_dir = committed_repo(tmp_path, *corpus(20))
        sweep_titles(seeds_dir, 10)
        result = gate(monkeypatch, tmp_path)
        assert result.exit_code == 1
        assert "mass-field-rewrite" in result.output
        assert f"{GATE_CONFIRM_ENV}=1 git commit" in result.output
        # SKIP is prek's and pre-commit's, and a justfile recipe has no such
        # thing. --no-verify is named only to warn against it.
        assert "SKIP=" not in result.output

    def test_mass_deletion_blocks(self, tmp_path, monkeypatch):
        """There is no delete verb, so `rm` is the de facto one -- gate it."""
        seeds_dir = committed_repo(tmp_path, *corpus(20))
        for index in range(10):
            (seeds_dir / "seeds" / f"seeds-a{index:02d}.md").unlink()
        assert gate(monkeypatch, tmp_path).exit_code == 1

    def test_ordinary_edit_does_not_block(self, tmp_path, monkeypatch):
        """2 of 20 is 10% and 2 seeds -- under both halves of the threshold."""
        seeds_dir = committed_repo(tmp_path, *corpus(20))
        for index in range(2):
            write_seed(
                seeds_dir,
                record(
                    f"seeds-a{index:02d}",
                    title=f"A genuinely revised title {index}",
                    body=f"Body {index}.\n",
                ),
            )
        assert gate(monkeypatch, tmp_path).exit_code == 0

    def test_adding_seeds_to_an_empty_history_does_not_block(
        self, tmp_path, monkeypatch
    ):
        """The very first commit of a store compares against nothing."""
        git_init(tmp_path)
        make_store(tmp_path, *corpus(20))
        assert gate(monkeypatch, tmp_path).exit_code == 0


# --- The escape --------------------------------------------------------------


class TestTheEscape:
    """SEEDS_GATE_CONFIRM=1 is seeds' own, so it works from a plain justfile
    recipe as well as under prek -- where SKIP=<hook id> would not."""

    def test_confirmation_lets_an_intended_mass_rewrite_through(
        self, tmp_path, monkeypatch
    ):
        seeds_dir = committed_repo(tmp_path, *corpus(20))
        sweep_titles(seeds_dir, 10)
        monkeypatch.setenv(GATE_CONFIRM_ENV, "1")
        result = gate(monkeypatch, tmp_path)
        assert result.exit_code == 0, result.output
        # Confirmed, not hidden: the findings are still printed.
        assert "mass-field-rewrite" in result.output
        assert "confirmed rather than refused" in result.output

    @pytest.mark.parametrize("value", ["", "0", "yes", "true"])
    def test_only_exactly_1_confirms(self, tmp_path, monkeypatch, value):
        """One spelling, so a stray `SEEDS_GATE_CONFIRM=0` left in an
        environment cannot read as consent."""
        seeds_dir = committed_repo(tmp_path, *corpus(20))
        sweep_titles(seeds_dir, 10)
        monkeypatch.setenv(GATE_CONFIRM_ENV, value)
        assert gate(monkeypatch, tmp_path).exit_code == 1


# --- A real `seeds rename-prefix` is a rename, not a mass deletion -----------


def renamed_repo(
    root: Path, monkeypatch: pytest.MonkeyPatch, *rename_args: str
) -> Path:
    """A committed 20-seed store that references itself, then a REAL rename.

    Driven through the CLI verb, not ``Store.rename_prefix``, so the test
    tracks what an operator actually runs. Keyed by id, every one of the 20
    seeds reads as deleted: without the rename reading, that is a 100% change
    on every field -- the marketscan_mdcd 596555b false alarm (seeds-7q8g).
    """
    git_init(root)
    records = [
        record(
            f"seeds-{n:04d}",
            title=f"Seed {n}, after seeds-{(n + 1) % 20:04d}",
            body=f"Follows from seeds-{(n + 1) % 20:04d}.\n",
        )
        for n in range(20)
    ]
    records[3] = record(
        "seeds-0003.1",
        parent="seeds-0003",
        title="A child",
        body="Child of seeds-0003.\n",
    )
    records.append(record("seeds-0003", title="The parent", body="Parent.\n"))
    seeds_dir = make_store(root, *records)
    Store(seeds_dir).set_prefix("seeds")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "a store that references itself")

    monkeypatch.chdir(root)
    result = CliRunner().invoke(main, ["rename-prefix", "sprout", *rename_args])
    assert result.exit_code == 0, result.output
    # The precondition, asserted rather than assumed: the rename really moved
    # every id (and, by default, rewrote the references inside the text).
    assert not list((seeds_dir / "seeds").glob("seeds-*.md"))
    rewritten = "sprout-0001" in (seeds_dir / "seeds" / "sprout-0000.md").read_text()
    assert rewritten == ("--no-rewrite-bodies" not in rename_args)
    return seeds_dir


class TestRenamePrefix:
    """PICKED (seeds-l80): recognise the rename, apply it to the before-state,
    and judge only what it does not explain -- so a pure rename passes with a
    report line, and a sweep riding along with one is still refused."""

    def test_an_uncommitted_rename_passes_and_is_reported(self, tmp_path, monkeypatch):
        renamed_repo(tmp_path, monkeypatch)
        result = gate(monkeypatch, tmp_path)
        assert result.exit_code == 0, result.output
        assert "read as `seeds rename-prefix` (seeds → sprout, 21 id(s) moved)" in (
            result.output
        )

    def test_a_rename_that_left_the_text_alone_passes(self, tmp_path, monkeypatch):
        """`--no-rewrite-bodies` moves the ids and leaves every reference in
        the text as it was. That is a rename too."""
        renamed_repo(tmp_path, monkeypatch, "--no-rewrite-bodies")
        result = gate(monkeypatch, tmp_path)
        assert result.exit_code == 0, result.output
        assert "read as `seeds rename-prefix`" in result.output

    def test_a_committed_rename_passes_on_the_next_commit(self, tmp_path, monkeypatch):
        """marketscan_mdcd's exact state: the rename is HEAD, nothing staged,
        so --against-git audits HEAD~1 against HEAD."""
        renamed_repo(tmp_path, monkeypatch)
        git(tmp_path, "add", "-A")
        git(tmp_path, "commit", "-q", "-m", "rename the prefix")
        result = gate(monkeypatch, tmp_path)
        assert result.exit_code == 0, result.output
        assert "at HEAD~1, compared with HEAD" in result.output
        assert "read as `seeds rename-prefix`" in result.output

    def test_a_title_sweep_riding_along_with_a_rename_is_refused(
        self, tmp_path, monkeypatch
    ):
        seeds_dir = renamed_repo(tmp_path, monkeypatch)
        for n in (0, 1, 2, 4, 5, 6, 7, 8, 9, 10):
            path = seeds_dir / "seeds" / f"sprout-{n:04d}.md"
            text = path.read_text(encoding="utf-8")
            path.write_text(
                text.replace(f"title: Seed {n},", "title: scratchpad,", 1),
                encoding="utf-8",
            )
        result = gate(monkeypatch, tmp_path)
        assert result.exit_code == 1, result.output
        assert "title differs on 10 of 21 seeds" in result.output
