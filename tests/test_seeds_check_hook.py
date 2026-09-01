"""Tests for scripts/seeds_check_hook.py — the pre-commit gate (bead seeds-4co.13).

A gate nobody has watched refuse a commit is not a gate. This project has now
hit that defect class four times (doctor's mtime proxy, the changelog's commit
count, the missing ``uv lock --check``, and a converter that would have passed
on an empty store), so every case here is a hand-built store with a
hand-computed expected exit status, and both directions are asserted: the gate
refusing what it must refuse, and — carrying more weight — letting through
everything else.

The false-negative cases (a mass title rewrite, a mass deletion) are the reason
the hook exists. The false-positive cases are the reason anyone will still have
it installed next month: a gate that blocks ordinary commits gets bypassed, and
the bypass is permanent.

Two skip paths are load-bearing rather than incidental. This repository has not
converted yet, so ``.seeds/seeds/`` does not exist here; a hook that failed on
that would refuse every commit in the repo today. Both the no-``.seeds``-at-all
and the no-store-yet cases are therefore asserted to exit 0.

Every git call goes through ``tests.githelpers``; ``tests/test_git_single_door``
fails this file at the AST level otherwise.
"""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

import pytest

from seeds.models import SeedStatus
from seeds.seedfile import SeedRecord, write_seed
from tests.githelpers import git, git_init

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "seeds_check_hook.py"

CREATED = datetime(2026, 8, 28, 14, 2, 11, 481293, tzinfo=UTC)
UPDATED = datetime(2026, 8, 30, 9, 41, 7, 220118, tzinfo=UTC)


def _load():
    spec = importlib.util.spec_from_file_location("seeds_check_hook", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hook = _load()


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


def run_in(monkeypatch: pytest.MonkeyPatch, root: Path) -> int:
    monkeypatch.chdir(root)
    return hook.main()


# --- The skip paths: a missing store must never block a commit ---------------


class TestMissingStoreDoesNotBlock:
    def test_no_seeds_directory_at_all_passes(self, tmp_path, monkeypatch, capsys):
        """A repo that has never run `seeds init` is not this hook's business."""
        (tmp_path / "somewhere").mkdir()
        assert run_in(monkeypatch, tmp_path / "somewhere") == 0
        assert "nothing to gate" in capsys.readouterr().out

    def test_pre_conversion_store_passes(self, tmp_path, monkeypatch, capsys):
        """.seeds/ exists but .seeds/seeds/ does not — this repo, today.

        `seeds check` reports store-missing and exits 1 here, which is correct
        for the checker and would refuse every commit if the hook took it at
        face value. Exactly one finding, coded store-missing, is the cue.
        """
        (tmp_path / ".seeds").mkdir()
        (tmp_path / ".seeds" / "seeds.jsonl").write_text("")
        assert run_in(monkeypatch, tmp_path) == 0
        assert "no seed-file store yet" in capsys.readouterr().out

    def test_store_missing_cue_is_not_a_blanket_pass(self, tmp_path, monkeypatch):
        """One finding is the cue only when its code is store-missing.

        Guards the cheap wrong version of the check above — `len(findings) == 1`
        without inspecting the code — which would wave through every store
        holding exactly one violation.
        """
        seeds_dir = make_store(tmp_path, record("seeds-a01"))
        (seeds_dir / "seeds" / "seeds-a02.md").write_text("not a seed file at all\n")
        assert run_in(monkeypatch, tmp_path) == 1


# --- The violations tier gates -----------------------------------------------


class TestViolationsBlock:
    def test_healthy_store_passes(self, tmp_path, monkeypatch):
        committed_repo(tmp_path, *corpus(20))
        assert run_in(monkeypatch, tmp_path) == 0

    def test_unparseable_file_blocks(self, tmp_path, monkeypatch):
        seeds_dir = committed_repo(tmp_path, *corpus(20))
        (seeds_dir / "seeds" / "seeds-a03.md").write_text("### not front matter\n")
        assert run_in(monkeypatch, tmp_path) == 1

    def test_confirmation_hint_is_printed_on_a_block(
        self, tmp_path, monkeypatch, capsys
    ):
        """A blocked commit that does not name its escape hatch invites --no-verify."""
        seeds_dir = committed_repo(tmp_path, *corpus(20))
        (seeds_dir / "seeds" / "seeds-a03.md").write_text("### not front matter\n")
        assert run_in(monkeypatch, tmp_path) == 1
        assert "SKIP=seeds-check" in capsys.readouterr().err


# --- The --against-git tier gates the mass-rewrite shape ---------------------


class TestMassRewriteBlocks:
    def test_mass_title_rewrite_blocks(self, tmp_path, monkeypatch):
        """10 of 20 titles is 50% — over 20%, and at the 10-seed floor.

        This is the seeds-wurl shape, scaled down: a bulk sweep that replaces a
        title with a scratchpad path. Every record still parses, so the
        violations tier alone is green.
        """
        seeds_dir = committed_repo(tmp_path, *corpus(20))
        for index in range(10):
            write_seed(
                seeds_dir,
                record(
                    f"seeds-a{index:02d}",
                    title="scratchpad",
                    body=f"Body {index}.\n",
                ),
            )
        assert run_in(monkeypatch, tmp_path) == 1

    def test_mass_deletion_blocks(self, tmp_path, monkeypatch):
        """There is no delete verb, so `rm` is the de facto one — gate it.

        A deleted seed lost every field, so 10 deletions out of 20 trip the same
        threshold a 50% title rewrite does. The surviving files are all
        perfectly well formed, so nothing else here has anything to say.
        """
        seeds_dir = committed_repo(tmp_path, *corpus(20))
        for index in range(10):
            (seeds_dir / "seeds" / f"seeds-a{index:02d}.md").unlink()
        assert run_in(monkeypatch, tmp_path) == 1

    def test_ordinary_edit_does_not_block(self, tmp_path, monkeypatch):
        """2 of 20 is 10% and 2 seeds — under both halves of the threshold.

        The false positive that matters most: if a two-seed edit demanded a
        decision, everyone would learn to pass the gate by reflex.
        """
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
        assert run_in(monkeypatch, tmp_path) == 0

    def test_adding_seeds_to_an_empty_history_does_not_block(
        self, tmp_path, monkeypatch
    ):
        """The very first commit of a store compares against nothing."""
        git_init(tmp_path)
        make_store(tmp_path, *corpus(20))
        assert run_in(monkeypatch, tmp_path) == 0


# --- The smells tier reports and never gates ---------------------------------


class TestSmellsDoNotBlock:
    def test_empty_bodies_across_the_corpus_pass(self, tmp_path, monkeypatch):
        """20 empty bodies and 20 duplicate bodies — every smell there is, at scale.

        An empty body is a candidate for attention, never an error; if this
        blocked, this repo's real corpus (25 title-only seeds today) could not
        be committed at all.
        """
        committed_repo(
            tmp_path,
            *[record(f"seeds-a{index:02d}", body="") for index in range(20)],
        )
        assert run_in(monkeypatch, tmp_path) == 0
