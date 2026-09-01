"""``seeds convert`` retires ``.seeds/seeds.jsonl`` (bead seeds-4co.19).

This is a fix, not tidiness. Measured on this repo six hours after its own
conversion: the leftover ``seeds.jsonl`` held 314 records while the tree held
309, and a seed created after conversion was in the tree and absent from the
file. It does not merely stop being written — it starts lying immediately while
still looking authoritative, and the shell loops that grep it keep working,
keep returning pre-conversion data, and report nothing.

Deleting it is safe only because **git** holds it, so the three conditions
below are the whole design, and each one is tested by making it fail:

1. the repo is a git work tree;
2. ``.seeds/seeds.jsonl`` is tracked;
3. it has no uncommitted changes.

The counterintuitive half is asserted too: ``seeds.db`` is the dangerous one,
because ``.seeds/.gitignore`` excludes ``*.db`` and git holds nothing.

:class:`TestHistorySurvivesTheDeletion` is the load-bearing test. The reason the
file can go at all is that ``seeds history`` reads ``git log``/``git show``, not
the working file — so it is asserted against a repo where the removal has
actually been committed, rather than argued.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from seeds.convert import convert, format_report
from seeds.gitstage import plan_tracked_deletion
from seeds.history import JSONL_SOURCE, seed_history
from seeds.legacy import JSONL_FILE
from seeds.models import Seed, SeedStatus
from seeds.seedfile import seed_files_dir
from seeds.store import Store
from tests.githelpers import git, git_init
from tests.legacyhelpers import build_legacy_db

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
CONVERTED = datetime(2026, 2, 1, 9, 0, 0, tzinfo=UTC)


def _record(
    seed_id: str,
    *,
    title: str = "A title",
    content: str = "",
) -> dict[str, object]:
    """One pre-0.7 JSONL record, with the keys that format carried."""
    return {
        "format_version": 2,
        "id": seed_id,
        "title": title,
        "content": content,
        "status": "captured",
        "seed_type": "idea",
        "tags": [],
        "created_at": T0.isoformat(),
        "updated_at": T0.isoformat(),
        "resolved_at": None,
        "resolution": "",
        "relationships": [],
    }


def _write_jsonl(seeds_dir: Path, records: list[dict[str, object]]) -> Path:
    seeds_dir.mkdir(parents=True, exist_ok=True)
    path = seeds_dir / JSONL_FILE
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8"
    )
    return path


def _commit(repo: Path, message: str, *, days: int = 0) -> None:
    """Commit whatever is staged plus everything under ``.seeds``.

    A fixed author date, set through ``--date`` because ``tests/githelpers``
    strips the identity variables out of the environment on purpose.
    """
    git(repo, "add", "-A", ".seeds")
    when = (T0 + timedelta(days=days)).isoformat()
    git(repo, "commit", "-q", "-m", message, "--date", when)


@pytest.fixture
def tracked_store(temp_dir):
    """A git repo whose pre-0.7 JSONL is tracked and clean: all three hold."""
    repo = temp_dir / "repo"
    repo.mkdir()
    git_init(repo)
    seeds_dir = repo / ".seeds"
    _write_jsonl(seeds_dir, [_record("seeds-a1", content="one\n")])
    _commit(repo, "chore(seeds): the pre-0.7 store")
    return seeds_dir


class TestAllThreeConditionsHold:
    def test_the_removal_is_staged_and_the_file_is_gone(self, tracked_store):
        repo = tracked_store.parent

        report = convert(tracked_store)

        assert report.jsonl_deletion_staged is True
        assert report.jsonl_deletion_blocked is None
        assert not (tracked_store / JSONL_FILE).exists()
        status = git(repo, "status", "--porcelain").stdout
        assert "D  .seeds/seeds.jsonl" in status, status

    def test_the_removal_lands_in_the_same_commit_as_the_seed_files(
        self, tracked_store
    ):
        repo = tracked_store.parent
        convert(tracked_store)

        git(repo, "add", ".seeds/seeds")
        git(repo, "commit", "-q", "-m", "chore(seeds): convert")

        names = git(repo, "show", "--name-status", "--format=", "HEAD").stdout
        assert "D\t.seeds/seeds.jsonl" in names, names
        assert "A\t.seeds/seeds/seeds-a1.md" in names, names

    def test_the_revert_command_is_for_the_state_this_run_created(self, tracked_store):
        report = convert(tracked_store)

        assert report.revert_command == (
            "git checkout HEAD -- .seeds/seeds.jsonl && rm -rf .seeds/seeds "
            "&& rm -f .seeds/config.yaml"
        )

    def test_that_revert_command_actually_reverts(self, tracked_store):
        repo = tracked_store.parent
        before = git(repo, "rev-parse", "HEAD").stdout.strip()
        convert(tracked_store)

        git(repo, "checkout", "HEAD", "--", ".seeds/seeds.jsonl")
        shutil.rmtree(seed_files_dir(tracked_store))
        (tracked_store / "config.yaml").unlink()

        assert (tracked_store / JSONL_FILE).read_text(encoding="utf-8").strip()
        assert git(repo, "status", "--porcelain").stdout == ""
        assert git(repo, "rev-parse", "HEAD").stdout.strip() == before

    def test_the_report_says_the_history_is_what_is_kept(self, tracked_store):
        report = convert(tracked_store)

        text = format_report(report)
        assert "staged the deletion of seeds.jsonl" in text
        assert "git history" in text
        assert "seeds history" in text


class TestEachConditionFailingLeavesTheFileAlone:
    """Fail one, and the file must survive with the condition named."""

    def test_not_a_git_work_tree(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        _write_jsonl(seeds_dir, [_record("seeds-a1")])

        report = convert(seeds_dir)

        assert report.jsonl_deletion_staged is False
        assert (seeds_dir / JSONL_FILE).exists()
        assert "not inside a git work tree" in (report.jsonl_deletion_blocked or "")
        assert report.revert_command == (
            "rm -rf .seeds/seeds && rm -f .seeds/config.yaml"
        )

    def test_the_jsonl_is_untracked(self, temp_dir):
        repo = temp_dir / "repo"
        repo.mkdir()
        git_init(repo)
        seeds_dir = repo / ".seeds"
        _write_jsonl(seeds_dir, [_record("seeds-a1")])
        # Never committed: git holds nothing to check out afterwards.

        report = convert(seeds_dir)

        assert report.jsonl_deletion_staged is False
        assert (seeds_dir / JSONL_FILE).exists()
        assert "not tracked by git" in (report.jsonl_deletion_blocked or "")

    def test_the_jsonl_has_uncommitted_changes(self, tracked_store):
        _write_jsonl(
            tracked_store,
            [_record("seeds-a1", content="one\n"), _record("seeds-b2")],
        )

        report = convert(tracked_store)

        assert report.jsonl_deletion_staged is False
        assert (tracked_store / JSONL_FILE).exists()
        assert "uncommitted changes" in (report.jsonl_deletion_blocked or "")

    def test_a_staged_but_uncommitted_jsonl_also_counts_as_dirty(self, temp_dir):
        """An unborn HEAD's ``git add`` is the sharpest form of this case."""
        repo = temp_dir / "repo"
        repo.mkdir()
        git_init(repo)
        seeds_dir = repo / ".seeds"
        _write_jsonl(seeds_dir, [_record("seeds-a1")])
        git(repo, "add", ".seeds/seeds.jsonl")

        report = convert(seeds_dir)

        assert report.jsonl_deletion_staged is False
        assert (seeds_dir / JSONL_FILE).exists()
        assert "uncommitted changes" in (report.jsonl_deletion_blocked or "")

    def test_a_blocked_leftover_is_reported_as_stale_and_unreadable(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        _write_jsonl(seeds_dir, [_record("seeds-a1")])

        text = format_report(convert(seeds_dir))

        assert "left seeds.jsonl in place" in text
        assert "STALE" in text
        assert "do not read it" in text
        assert ".seeds/seeds/" in text


class TestThePlanItself:
    """The detector, on hand-built inputs with hand-computed answers."""

    def test_it_reports_the_repo_relative_path_when_all_three_hold(self, tracked_store):
        plan = plan_tracked_deletion(tracked_store / JSONL_FILE)

        assert plan.deletable is True
        assert plan.relpath == ".seeds/seeds.jsonl"
        assert plan.root == tracked_store.parent.resolve()

    def test_a_missing_file_in_a_repo_is_untracked_not_deletable(self, temp_dir):
        repo = temp_dir / "repo"
        (repo / ".seeds").mkdir(parents=True)
        git_init(repo)

        plan = plan_tracked_deletion(repo / ".seeds" / JSONL_FILE)

        assert plan.deletable is False
        assert "not tracked" in (plan.blocker or "")

    def test_a_tracked_file_deleted_from_the_worktree_is_dirty(self, tracked_store):
        (tracked_store / JSONL_FILE).unlink()

        plan = plan_tracked_deletion(tracked_store / JSONL_FILE)

        assert plan.deletable is False
        assert "uncommitted changes" in (plan.blocker or "")


class TestTheDatabaseIsNeverDeleted:
    def test_seeds_db_survives_a_conversion_that_deletes_the_jsonl(self, tracked_store):
        db = build_legacy_db(
            tracked_store,
            [
                Seed(
                    id="seeds-a1",
                    title="A title",
                    content="one\n",
                    status=SeedStatus.CAPTURED,
                    seed_type="idea",
                    tags=[],
                    created_at=T0,
                    updated_at=T0,
                )
            ],
        )
        db.close()

        report = convert(tracked_store)

        assert report.jsonl_deletion_staged is True
        assert (tracked_store / "seeds.db").exists()
        text = format_report(report)
        assert "seeds.db is never deleted" in text
        assert "*.db" in text


class TestAnUnresolvedForkKeepsTheSecondSource:
    """A fork is finished by re-running the converter, which reads both stores."""

    def test_the_jsonl_stays_until_the_fork_is_resolved(self, temp_dir):
        repo = temp_dir / "repo"
        repo.mkdir()
        git_init(repo)
        seeds_dir = repo / ".seeds"
        db = build_legacy_db(
            seeds_dir,
            [
                Seed(
                    id="seeds-f1",
                    title="Forked",
                    content="shared\nfrom the database\n",
                    status=SeedStatus.CAPTURED,
                    seed_type="idea",
                    tags=[],
                    created_at=T0,
                    updated_at=T0,
                )
            ],
        )
        db.close()
        _write_jsonl(
            seeds_dir,
            [_record("seeds-f1", title="Forked", content="shared\nfrom the file\n")],
        )
        _commit(repo, "chore(seeds): the pre-0.7 store")

        report = convert(seeds_dir)

        assert report.forks == ["seeds-f1"]
        assert report.jsonl_deletion_staged is False
        assert (seeds_dir / JSONL_FILE).exists()
        assert "fork(s) are unresolved" in (report.jsonl_deletion_blocked or "")


class TestHistorySurvivesTheDeletion:
    """The claim the whole change rests on, asserted against a real repo."""

    def test_pre_conversion_revisions_are_still_readable_after_the_removal(
        self, temp_dir
    ):
        repo = temp_dir / "repo"
        repo.mkdir()
        git_init(repo)
        seeds_dir = repo / ".seeds"

        _write_jsonl(seeds_dir, [_record("seeds-old", content="First thoughts.")])
        _commit(repo, "chore(seeds): capture seeds-old", days=0)
        _write_jsonl(
            seeds_dir,
            [_record("seeds-old", title="Settled", content="First thoughts.")],
        )
        _commit(repo, "fix(seeds): settle the title", days=1)

        report = convert(seeds_dir, now=CONVERTED)
        assert report.jsonl_deletion_staged is True
        _commit(repo, "chore(seeds): convert the store", days=40)

        assert not (seeds_dir / JSONL_FILE).exists()
        store = Store(seeds_dir)
        record = store.get("seeds-old")
        assert record is not None
        history = seed_history(seeds_dir, record)

        assert history.before_conversion == 2, (
            "the pre-conversion half was lost with the working file -- "
            "'seeds history' must read git, not the file on disk"
        )
        assert [rev.commit.subject for rev in history.revisions][:2] == [
            "chore(seeds): capture seeds-old",
            "fix(seeds): settle the title",
        ]
        assert {rev.source for rev in history.revisions} >= {JSONL_SOURCE}
