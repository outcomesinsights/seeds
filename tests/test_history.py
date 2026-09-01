"""Tests for ``seeds history`` (bead seeds-4co.11).

The failure this command exists to prevent is a *silently short* history: 308
seed files written in one conversion commit give every seed a one-entry history
and orphan ~113 commits of real deliberation, and nothing on screen says so. A
history that came back short is indistinguishable from a seed that genuinely has
a short history, so the join across the conversion is the thing under test here,
and :class:`TestBothSidesOfTheConversion` is where it is asserted.

Everything is built from a hand-written JSONL with hand-written commit dates,
run through the real converter, so the expected field lists below are computed
by hand rather than read back off the implementation.

Two controls keep the output honest:

``test_a_commit_that_did_not_touch_this_seed_is_not_listed``
    The JSONL is one file for the whole corpus, so every seed would otherwise
    inherit the store's history under its own name.

``test_every_line_is_git_verbatim_never_prose``
    The settled rule is that this command structures and labels and NEVER
    summarises. The test decomposes each row and asserts every token in it came
    out of git or is a field name -- there is nowhere for a sentence to hide.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from click.testing import CliRunner

from seeds.cli import main
from seeds.convert import convert
from seeds.history import (
    FILE_SOURCE,
    JSONL_SOURCE,
    format_history,
    seed_history,
)
from seeds.models import SeedStatus
from seeds.store import Store, new_record
from tests.githelpers import git, git_init

CONVERTED = datetime(2026, 2, 1, 9, 0, 0, tzinfo=UTC)

CREATED = "2026-01-02T10:00:00+00:00"
RETITLED = "2026-01-04T10:00:00+00:00"

# The three JSONL commits, and the two seed-file commits after conversion.
D_CREATE = "2026-01-02"
D_UNRELATED = "2026-01-03"
D_RETITLE = "2026-01-04"
D_CONVERT = "2026-02-01"
D_EXPLORE = "2026-02-05"


def _record(
    seed_id: str,
    title: str,
    content: str,
    *,
    updated_at: str = CREATED,
) -> dict[str, object]:
    """One pre-0.7 JSONL record, with the keys that format actually carried.

    No ``parent`` and no ``converted_at``: their absence on this side is what
    the conversion boundary has to read correctly.
    """
    return {
        "format_version": 2,
        "id": seed_id,
        "title": title,
        "content": content,
        "status": "captured",
        "seed_type": "idea",
        "tags": [],
        "created_at": CREATED,
        "updated_at": updated_at,
        "resolved_at": None,
        "resolution": "",
        "relationships": [],
    }


def _write_jsonl(seeds_dir: Path, records: list[dict[str, object]]) -> None:
    seeds_dir.mkdir(parents=True, exist_ok=True)
    (seeds_dir / "seeds.jsonl").write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


def _commit(repo: Path, message: str, date: str) -> None:
    """Commit everything staged-or-not with a fixed author date.

    The date is set through ``--date`` rather than ``GIT_AUTHOR_DATE`` because
    ``tests/githelpers`` strips the six identity variables out of the
    environment on purpose; ``%ad``/``%at`` read the author date either way, so
    the rendered history is deterministic.
    """
    git(repo, "add", "-A", ".seeds")
    git(repo, "commit", "-q", "-m", message, "--date", date + "T10:00:00+00:00")


@pytest.fixture
def converted_repo(tmp_path: Path) -> Path:
    """A repo whose store was converted, with real history on both sides.

    Three JSONL commits, then the conversion, then two seed-file commits. The
    middle JSONL commit deliberately touches only ``seeds-other``.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    git_init(repo)
    seeds_dir = repo / ".seeds"

    old = _record("seeds-old", "Storage: one file per seed?", "First thoughts.")
    other = _record("seeds-other", "Unrelated", "Nothing to do with the other one.")

    _write_jsonl(seeds_dir, [old, other])
    _commit(repo, "chore(seeds): capture seeds-old and seeds-other", D_CREATE)

    other["content"] = "Still nothing to do with the other one."
    _write_jsonl(seeds_dir, [old, other])
    _commit(repo, "chore(seeds): extend seeds-other only", D_UNRELATED)

    old["title"] = "Storage: one file per seed"
    old["updated_at"] = RETITLED
    _write_jsonl(seeds_dir, [old, other])
    _commit(repo, "fix(seeds): settle the seeds-old title", D_RETITLE)

    convert(seeds_dir, now=CONVERTED)
    _commit(repo, "chore(seeds): convert the store to the seed-file tree", D_CONVERT)

    store = Store(seeds_dir)
    record = store.get("seeds-old")
    assert record is not None
    record.status = SeedStatus.EXPLORING
    store.save(record)
    store.create(
        new_record("seeds-fresh", "Born after the conversion", body="No JSONL past.")
    )
    _commit(repo, "chore(seeds): explore seeds-old and jot seeds-fresh", D_EXPLORE)
    return repo


def _history(repo: Path, seed_id: str):
    store = Store(repo / ".seeds")
    record = store.get(seed_id)
    assert record is not None
    return seed_history(store.seeds_dir, record)


class TestBothSidesOfTheConversion:
    """The acceptance criterion: one list, two stores, no orphaned history."""

    def test_a_seed_created_before_conversion_shows_revisions_from_both_sides(
        self, converted_repo
    ):
        history = _history(converted_repo, "seeds-old")
        sources = [rev.source for rev in history.revisions]

        assert JSONL_SOURCE in sources, (
            "the pre-conversion half is missing -- this seed's deliberation "
            "would look like it began on conversion day"
        )
        assert FILE_SOURCE in sources
        assert history.before_conversion == 2
        assert history.after_conversion == 2
        # Ordered: everything from the JSONL, then everything from the file.
        assert sources == [JSONL_SOURCE, JSONL_SOURCE, FILE_SOURCE, FILE_SOURCE]

    def test_the_dates_and_authors_are_the_real_ones_from_both_sides(
        self, converted_repo
    ):
        history = _history(converted_repo, "seeds-old")
        assert [rev.commit.date for rev in history.revisions] == [
            D_CREATE,
            D_RETITLE,
            D_CONVERT,
            D_EXPLORE,
        ]
        assert {rev.commit.author for rev in history.revisions} == {"Test"}

    def test_a_commit_that_did_not_touch_this_seed_is_not_listed(self, converted_repo):
        history = _history(converted_repo, "seeds-old")
        dates = [rev.commit.date for rev in history.revisions]
        assert D_UNRELATED not in dates, (
            "a commit that only changed seeds-other was reported as a "
            "revision of seeds-old"
        )
        assert D_UNRELATED in [
            rev.commit.date for rev in _history(converted_repo, "seeds-other").revisions
        ]

    def test_the_conversion_commit_reports_only_what_conversion_changed(
        self, converted_repo
    ):
        history = _history(converted_repo, "seeds-old")
        conversion = history.revisions[2]
        assert conversion.commit.date == D_CONVERT
        # converted_at has no source in the old store, so it is genuinely new
        # here. title/status/tags/created_at are NOT: the boundary diffs
        # against the last JSONL revision rather than against nothing.
        assert "converted_at" in conversion.fields
        for carried_over in ("title", "status", "tags", "created_at", "seed_type"):
            assert carried_over not in conversion.fields

    def test_a_seed_born_after_conversion_has_no_jsonl_half(self, converted_repo):
        history = _history(converted_repo, "seeds-fresh")
        assert history.converted_at is None
        assert [rev.source for rev in history.revisions] == [FILE_SOURCE]
        assert history.before_conversion == 0


class TestFieldLabelling:
    """What changed is named; what it meant is not."""

    def test_the_first_revision_lists_every_field_that_was_set(self, converted_repo):
        first = _history(converted_repo, "seeds-old").revisions[0]
        assert first.fields == (
            "content",
            "created_at",
            "id",
            "seed_type",
            "status",
            "title",
            "updated_at",
        ), "empty fields (tags, resolution, resolved_at) must not be listed"

    def test_a_title_change_names_the_title_and_nothing_else(self, converted_repo):
        retitle = _history(converted_repo, "seeds-old").revisions[1]
        assert retitle.commit.date == D_RETITLE
        assert retitle.fields == ("title", "updated_at")

    def test_a_status_change_after_conversion_names_the_status(self, converted_repo):
        explore = _history(converted_repo, "seeds-old").revisions[3]
        assert explore.commit.date == D_EXPLORE
        assert explore.fields == ("status", "updated_at")

    def test_the_same_repo_read_twice_gives_the_same_answer(self, converted_repo):
        assert format_history(_history(converted_repo, "seeds-old")) == format_history(
            _history(converted_repo, "seeds-old")
        )


class TestRendering:
    """The reader's view: a table, a boundary, and no prose."""

    def test_every_line_is_git_verbatim_never_prose(self, converted_repo):
        history = _history(converted_repo, "seeds-old")
        lines = format_history(history).splitlines()

        # Line 0 is the id and title, line 1 the count, line 2 blank.
        assert lines[0] == f"seeds-old  {history.title}"
        assert lines[1] == (
            "4 revisions: 2 in .seeds/seeds.jsonl before conversion, "
            "2 in .seeds/seeds/seeds-old.md after."
        )
        assert lines[2] == ""

        body = lines[3:]
        boundary = f"--- converted {CONVERTED.isoformat()} ---"
        assert boundary in body
        assert body.index(boundary) == 2, "the boundary sits where the source switches"

        rows = [line for line in body if line != boundary]
        assert len(rows) == len(history.revisions)
        for line, rev in zip(rows, history.revisions, strict=True):
            # Nothing may survive removing the four git-derived columns: no
            # adjective, no verdict, no summary of what the change meant.
            assert line.endswith(rev.commit.subject)
            remainder = line[: -len(rev.commit.subject)]
            for token in (rev.commit.date, rev.commit.author, ",".join(rev.fields)):
                assert token in remainder
                remainder = remainder.replace(token, "", 1)
            assert remainder.strip() == ""

    def test_a_seed_with_no_commits_says_so_rather_than_inventing_one(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        git_init(repo)
        store = Store(repo / ".seeds")
        store.files_dir.mkdir(parents=True)
        store.set_prefix("seeds")
        store.create(new_record("seeds-none", "Never committed", body="Fresh."))
        record = store.get("seeds-none")
        assert record is not None
        output = format_history(seed_history(store.seeds_dir, record))
        assert "No committed revisions." in output


class TestCli:
    def test_the_command_prints_both_halves(self, converted_repo, monkeypatch):
        monkeypatch.chdir(converted_repo)
        result = CliRunner().invoke(
            main, ["history", "seeds-old"], catch_exceptions=False
        )
        assert result.exit_code == 0, result.output
        assert D_CREATE in result.output
        assert D_EXPLORE in result.output
        assert "before conversion" in result.output

    def test_an_unknown_id_is_an_error(self, converted_repo, monkeypatch):
        monkeypatch.chdir(converted_repo)
        result = CliRunner().invoke(
            main, ["history", "seeds-nope"], catch_exceptions=False
        )
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_no_git_is_loud_rather_than_an_empty_history(self, tmp_path, monkeypatch):
        """Not in a work tree: refuse, because there is no second source."""
        store = Store(tmp_path / ".seeds")
        store.files_dir.mkdir(parents=True)
        store.set_prefix("seeds")
        store.create(new_record("seeds-lonely", "No repo here", body="Body."))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
        result = CliRunner().invoke(
            main, ["history", "seeds-lonely"], catch_exceptions=False
        )
        assert result.exit_code == 1
        assert "cannot read history" in result.output
