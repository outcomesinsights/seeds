"""Tests for the converter (beads seeds-4co.6 and seeds-4co.7).

The thing under test is a migration, so the failure that matters is not a
crash — it is a run that reports success while a body, a tag or an edge quietly
did not make it. Everything here is therefore built the way the data-pipeline
standard asks a detector to be built: hand-made stores with hand-computed
answers, plus two adversarial suites that hand :func:`verify` output it must
refuse.

Two fixtures are load-bearing and are named in the bead:

``synthetic_store``
    A repo exhibiting **all four divergence cases at once**, so the classifier
    is exercised rather than assumed. Every one of its four seeds has a
    hand-written expected outcome below.

``real_corpus``
    This repository's own ``.seeds/seeds.jsonl`` — 314 records, 549
    relationship halves — copied into a temp directory. Nothing here writes to
    the real store; the copy is the point.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from seeds.check import check_violations
from seeds.cli import main
from seeds.convert import (
    FIXTURE_IDS,
    SPLIT_AT_BLANK_LINE,
    SPLIT_AT_FIRST_LINE,
    SPLIT_AT_SENTENCE_END,
    Classification,
    ConversionError,
    classify,
    convert,
    fork_body,
    format_report,
    split_legacy_title,
    verify,
)
from seeds.legacy import LegacyDatabase, LegacyRelationTypeError
from seeds.models import RelationType, Seed, SeedStatus
from seeds.seedfile import read_seed_file, seed_files_dir
from tests.githelpers import git, git_init
from tests.legacyhelpers import LegacyWriter, build_legacy_db

REPO_JSONL = Path(__file__).resolve().parent.parent / ".seeds" / "seeds.jsonl"

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def _iso(offset_days: int = 0) -> str:
    return (T0 + timedelta(days=offset_days)).isoformat()


def _stamp(offset_days: int = 0) -> datetime:
    return T0 + timedelta(days=offset_days)


def _seed_from_jsonl(data: dict) -> Seed:
    """One frozen-JSONL record as a legacy ``Seed``, for the fixture above."""

    def when(value):
        if value is None:
            return None
        stamp = datetime.fromisoformat(value)
        return stamp if stamp.tzinfo else stamp.replace(tzinfo=UTC)

    return Seed(
        id=data["id"],
        title=data["title"],
        content=data.get("content", "") or "",
        status=SeedStatus(data["status"]),
        seed_type=data.get("seed_type", "idea"),
        tags=list(data.get("tags") or []),
        created_at=when(data["created_at"]),
        updated_at=when(data["updated_at"]),
        resolved_at=when(data.get("resolved_at")),
        resolution=data.get("resolution", "") or "",
    )


# --- Store builders ----------------------------------------------------------


def write_jsonl(seeds_dir: Path, records: list[dict[str, object]]) -> Path:
    """Write a v2 JSONL store. Records are given verbatim, defects included."""
    seeds_dir.mkdir(parents=True, exist_ok=True)
    path = seeds_dir / "seeds.jsonl"
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8"
    )
    return path


def record(
    seed_id: str,
    *,
    title: str = "A title",
    content: str = "",
    status: str = "captured",
    seed_type: str = "idea",
    tags: list[str] | None = None,
    created: int = 0,
    updated: int = 0,
    resolved: int | None = None,
    resolution: str = "",
    relationships: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    """One v2 JSONL record, with everything the exporter emits."""
    return {
        "format_version": 2,
        "id": seed_id,
        "title": title,
        "content": content,
        "status": status,
        "seed_type": seed_type,
        "tags": tags or [],
        "created_at": _iso(created),
        "updated_at": _iso(updated),
        "resolved_at": _iso(resolved) if resolved is not None else None,
        "resolution": resolution,
        "relationships": relationships or [],
    }


def build_db(seeds_dir: Path, seeds: list[Seed]) -> LegacyWriter:
    """A legacy SQLite store holding exactly ``seeds``, open for the caller.

    The write path lives in tests/legacyhelpers.py because ``seeds.legacy`` is
    read-only: nothing shipped writes the retired store any more, so only a
    fixture is allowed to.
    """
    seeds_dir.mkdir(parents=True, exist_ok=True)
    return build_legacy_db(seeds_dir, seeds)


def seed(
    seed_id: str,
    *,
    title: str = "A title",
    content: str = "",
    status: SeedStatus = SeedStatus.CAPTURED,
    seed_type: str = "idea",
    tags: list[str] | None = None,
    created: int = 0,
    updated: int = 0,
    resolved: int | None = None,
    resolution: str = "",
) -> Seed:
    return Seed(
        id=seed_id,
        title=title,
        content=content,
        status=status,
        seed_type=seed_type,
        tags=tags or [],
        created_at=_stamp(created),
        updated_at=_stamp(updated),
        resolved_at=_stamp(resolved) if resolved is not None else None,
        resolution=resolution,
    )


# --- Classification ----------------------------------------------------------


class TestClassify:
    """The four conditions, hand-built, with the verdict written down."""

    def test_db_only(self):
        assert classify("body\n", None) is Classification.DB_ONLY

    def test_jsonl_only(self):
        assert classify(None, "body\n") is Classification.JSONL_ONLY

    def test_identical_bodies_are_not_a_fork(self):
        assert classify("same\n", "same\n") is Classification.DB_EXTENDS_DISK

    def test_db_appended(self):
        assert classify("one\ntwo\n", "one\n") is Classification.DB_EXTENDS_DISK

    def test_disk_ahead_of_a_database_that_never_imported_it(self):
        # The mirror of the ordinary append: one body is still a prefix of the
        # other, so the longer one is the shorter plus text and taking it loses
        # nothing. Not a fork -- a fork is "NEITHER prefixes the other".
        assert classify("one\n", "one\ntwo\n") is Classification.DB_EXTENDS_DISK

    def test_genuine_fork(self):
        assert classify("one\nleft\n", "one\nright\n") is Classification.FORK

    def test_empty_against_content_is_an_append(self):
        assert classify("grew\n", "") is Classification.DB_EXTENDS_DISK

    def test_neither_store_is_a_programming_error(self):
        with pytest.raises(ConversionError):
            classify(None, None)


class TestForkBody:
    def test_carries_both_bodies_between_git_markers(self):
        body = fork_body("left\n", "right\n")
        assert body == (
            "<<<<<<< database (.seeds/seeds.db)\n"
            "left\n"
            "=======\n"
            "right\n"
            ">>>>>>> on disk (.seeds/seeds.jsonl)\n"
        )

    def test_an_empty_side_still_renders_three_markers(self):
        body = fork_body("", "right\n")
        assert body.splitlines()[0].startswith("<<<<<<< ")
        assert "=======" in body
        assert body.splitlines()[-1].startswith(">>>>>>> ")


# --- The synthetic four-case repo --------------------------------------------

# Hand-built so every expected outcome below is computed by hand, not by
# running the converter and writing down what it said.
#
#   seeds-a1   DB only         body "db only\n"
#   seeds-b2   JSONL only      body "disk only\n"
#   seeds-c3   both, DB = disk + one appended line   -> DB body wins
#   seeds-d4   both, neither a prefix of the other   -> conflict file
DB_ONLY_ID = "seeds-a1"
JSONL_ONLY_ID = "seeds-b2"
APPEND_ID = "seeds-c3"
FORK_ID = "seeds-d4"


@pytest.fixture
def synthetic_store(temp_dir):
    """A store exhibiting all four divergence cases at once."""
    seeds_dir = temp_dir / ".seeds"
    db = build_db(
        seeds_dir,
        [
            seed(DB_ONLY_ID, title="Only in the database", content="db only\n"),
            seed(APPEND_ID, title="Appended", content="shared\nappended\n"),
            seed(FORK_ID, title="Forked", content="shared\nfrom the database\n"),
        ],
    )
    db.close()
    write_jsonl(
        seeds_dir,
        [
            record(JSONL_ONLY_ID, title="Only on disk", content="disk only\n"),
            record(APPEND_ID, title="Appended", content="shared\n"),
            record(FORK_ID, title="Forked", content="shared\nfrom the file\n"),
        ],
    )
    return seeds_dir


class TestFourDivergenceCases:
    def test_every_case_is_classified_and_counted(self, synthetic_store):
        report = convert(synthetic_store)
        assert report.counts == {
            Classification.DB_ONLY: 1,
            Classification.JSONL_ONLY: 1,
            Classification.DB_EXTENDS_DISK: 1,
            Classification.FORK: 1,
        }
        assert report.total == 4

    def test_db_only_seed_lands_with_its_body(self, synthetic_store):
        convert(synthetic_store)
        got = read_seed_file(seed_files_dir(synthetic_store) / f"{DB_ONLY_ID}.md")
        assert got.title == "Only in the database"
        assert got.body == "db only\n"

    def test_jsonl_only_seed_lands_with_its_body(self, synthetic_store):
        convert(synthetic_store)
        got = read_seed_file(seed_files_dir(synthetic_store) / f"{JSONL_ONLY_ID}.md")
        assert got.title == "Only on disk"
        assert got.body == "disk only\n"

    def test_the_append_takes_the_longer_body(self, synthetic_store):
        convert(synthetic_store)
        got = read_seed_file(seed_files_dir(synthetic_store) / f"{APPEND_ID}.md")
        assert got.body == "shared\nappended\n"

    def test_the_fork_becomes_a_conflict_file_holding_both_bodies(
        self, synthetic_store
    ):
        report = convert(synthetic_store)
        assert report.forks == [FORK_ID]
        got = read_seed_file(seed_files_dir(synthetic_store) / f"{FORK_ID}.md")
        assert "<<<<<<< " in got.body
        assert "=======" in got.body
        assert ">>>>>>> " in got.body
        assert "shared\nfrom the database" in got.body
        assert "shared\nfrom the file" in got.body

    def test_the_fork_is_the_only_thing_check_complains_about(self, synthetic_store):
        convert(synthetic_store)
        findings = check_violations(synthetic_store)
        assert [f.code for f in findings] == ["conflict-markers"]
        assert findings[0].path.name == f"{FORK_ID}.md"

    def test_an_unresolved_fork_keeps_the_report_unclean(self, synthetic_store):
        report = convert(synthetic_store)
        # The expected conflict markers are filtered out of the gate -- saying
        # the same thing twice would bury any finding that is NOT expected.
        assert report.check_findings == []
        assert not report.clean

    def test_a_fork_resolved_by_hand_survives_a_second_run(self, synthetic_store):
        convert(synthetic_store)
        path = seed_files_dir(synthetic_store) / f"{FORK_ID}.md"
        resolved = read_seed_file(path)
        text = path.read_text(encoding="utf-8")
        merged = "shared\nfrom the database\nfrom the file\n"
        head, _, _ = text.partition("\n\n")
        path.write_text(f"{head}\n\n{merged}", encoding="utf-8")

        report = convert(synthetic_store)

        assert report.forks_already_resolved == [FORK_ID]
        assert report.forks == []
        assert report.clean
        assert read_seed_file(path).body == merged
        assert read_seed_file(path).id == resolved.id


# --- Per-field union ---------------------------------------------------------


class TestUnionPerField:
    def test_disagreeing_titles_keep_the_database_and_report_the_other(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        build_db(seeds_dir, [seed("seeds-a1", title="Live title")]).close()
        write_jsonl(seeds_dir, [record("seeds-a1", title="Stale title")])

        report = convert(seeds_dir)

        assert read_seed_file(seed_files_dir(seeds_dir) / "seeds-a1.md").title == (
            "Live title"
        )
        [divergence] = report.field_divergences
        assert divergence.field_name == "title"
        assert divergence.in_db == "Live title"
        assert divergence.on_disk == "Stale title"

    def test_tags_are_a_real_union_of_both_stores(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        build_db(seeds_dir, [seed("seeds-a1", tags=["storage", "format"])]).close()
        write_jsonl(seeds_dir, [record("seeds-a1", tags=["format", "migration"])])

        convert(seeds_dir)

        got = read_seed_file(seed_files_dir(seeds_dir) / "seeds-a1.md")
        assert got.tags == ["storage", "format", "migration"]

    def test_created_at_takes_the_earlier_and_updated_at_the_later(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        build_db(seeds_dir, [seed("seeds-a1", created=5, updated=5)]).close()
        write_jsonl(seeds_dir, [record("seeds-a1", created=1, updated=3)])

        convert(seeds_dir)

        got = read_seed_file(seed_files_dir(seeds_dir) / "seeds-a1.md")
        assert got.created_at == _stamp(1)
        assert got.updated_at == _stamp(5)

    def test_resolved_at_on_a_non_terminal_seed_is_dropped_and_reported(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(seeds_dir, [record("seeds-a1", status="exploring", resolved=2)])

        report = convert(seeds_dir)

        got = read_seed_file(seed_files_dir(seeds_dir) / "seeds-a1.md")
        assert got.resolved_at is None
        assert [d.field_name for d in report.field_divergences] == ["resolved_at"]

    def test_a_terminal_seed_missing_resolved_at_falls_back_to_updated_at(
        self, temp_dir
    ):
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(seeds_dir, [record("seeds-a1", status="resolved", updated=4)])

        convert(seeds_dir)

        got = read_seed_file(seed_files_dir(seeds_dir) / "seeds-a1.md")
        assert got.resolved_at == _stamp(4)

    def test_a_dotted_id_carries_its_parent(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(seeds_dir, [record("seeds-a1"), record("seeds-a1.2")])

        convert(seeds_dir)

        assert read_seed_file(seed_files_dir(seeds_dir) / "seeds-a1.md").parent is None
        child = read_seed_file(seed_files_dir(seeds_dir) / "seeds-a1.2.md")
        assert child.parent == "seeds-a1"


# --- Relationships -----------------------------------------------------------


class TestRelationships:
    def test_the_questioned_by_inverse_is_materialized(self, temp_dir):
        """The carry-over finding: 57 one-sided `questions` edges on the real
        corpus, because `questioned-by` did not exist before the format froze.
        Output that does not write both ends fails its own check step."""
        seeds_dir = temp_dir / ".seeds"
        db = build_db(seeds_dir, [seed("seeds-a1"), seed("seeds-b2")])
        db.create_relationship(
            "seeds-a1", "seeds-b2", RelationType.QUESTIONS, _stamp(1)
        )
        db.close()

        convert(seeds_dir)

        asker = read_seed_file(seed_files_dir(seeds_dir) / "seeds-a1.md")
        asked = read_seed_file(seed_files_dir(seeds_dir) / "seeds-b2.md")
        assert [(e.target_id, e.rel_type) for e in asker.relationships] == [
            ("seeds-b2", RelationType.QUESTIONS)
        ]
        assert [(e.target_id, e.rel_type) for e in asked.relationships] == [
            ("seeds-a1", RelationType.QUESTIONED_BY)
        ]
        assert asker.relationships[0].created_at == asked.relationships[0].created_at
        assert check_violations(seeds_dir) == []

    def test_relates_to_is_written_at_both_ends(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        db = build_db(seeds_dir, [seed("seeds-a1"), seed("seeds-b2")])
        db.create_relationship(
            "seeds-a1", "seeds-b2", RelationType.RELATES_TO, _stamp(1)
        )
        db.close()

        convert(seeds_dir)

        for near, far in (("seeds-a1", "seeds-b2"), ("seeds-b2", "seeds-a1")):
            got = read_seed_file(seed_files_dir(seeds_dir) / f"{near}.md")
            assert [(e.target_id, e.rel_type) for e in got.relationships] == [
                (far, RelationType.RELATES_TO)
            ]

    def test_two_halves_stamped_differently_collapse_to_the_earlier(self, temp_dir):
        """One edge recorded twice, not two edges. Leaving the stamps
        disagreeing fails check's edge-timestamp-mismatch rule on the
        converter's own output."""
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(
            seeds_dir,
            [
                record(
                    "seeds-a1",
                    relationships=[
                        {
                            "target_id": "seeds-b2",
                            "rel_type": "relates-to",
                            "created_at": _iso(5),
                        }
                    ],
                ),
                record(
                    "seeds-b2",
                    relationships=[
                        {
                            "target_id": "seeds-a1",
                            "rel_type": "relates-to",
                            "created_at": _iso(1),
                        }
                    ],
                ),
            ],
        )

        convert(seeds_dir)

        near = read_seed_file(seed_files_dir(seeds_dir) / "seeds-a1.md")
        far = read_seed_file(seed_files_dir(seeds_dir) / "seeds-b2.md")
        assert near.relationships[0].created_at == _stamp(1)
        assert far.relationships[0].created_at == _stamp(1)
        assert check_violations(seeds_dir) == []

    def test_an_edge_naming_no_seed_is_dropped_and_named(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(
            seeds_dir,
            [
                record(
                    "seeds-a1",
                    relationships=[
                        {
                            "target_id": "seeds-gone",
                            "rel_type": "relates-to",
                            "created_at": _iso(1),
                        }
                    ],
                )
            ],
        )

        report = convert(seeds_dir)

        assert report.dropped_edges == ["seeds-a1 -relates-to-> seeds-gone"]
        got = read_seed_file(seed_files_dir(seeds_dir) / "seeds-a1.md")
        assert got.relationships == []
        assert check_violations(seeds_dir) == []


# --- What is dropped rather than translated ----------------------------------


class TestDrops:
    def test_the_six_ruled_fixtures_are_dropped(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(
            seeds_dir,
            [record("seeds-a1"), *(record(i) for i in sorted(FIXTURE_IDS))],
        )

        report = convert(seeds_dir)

        assert report.dropped_fixtures == sorted(FIXTURE_IDS)
        assert report.total == 1
        assert sorted(p.name for p in seed_files_dir(seeds_dir).glob("*.md")) == [
            "seeds-a1.md"
        ]

    def test_a_fixture_id_holding_real_content_is_kept_and_reported(self, temp_dir):
        """An id is repo-local. Another repo's `seeds-71` is not this repo's
        test fixture, and dropping it on the strength of a name would be the
        silent data loss this whole converter exists to avoid."""
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(seeds_dir, [record("seeds-71", content="real deliberation\n")])

        report = convert(seeds_dir)

        assert report.kept_fixtures == ["seeds-71"]
        assert report.dropped_fixtures == []
        assert (seed_files_dir(seeds_dir) / "seeds-71.md").exists()

    def test_keep_fixtures_converts_them_all(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(seeds_dir, [record(i) for i in sorted(FIXTURE_IDS)])

        report = convert(seeds_dir, keep_fixtures=True)

        assert report.dropped_fixtures == []
        assert report.total == len(FIXTURE_IDS)

    def test_the_legacy_questions_table_is_counted_and_never_translated(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        build_db(seeds_dir, [seed("seeds-a1")]).close()
        conn = sqlite3.connect(seeds_dir / "seeds.db")
        conn.execute("CREATE TABLE questions (id TEXT PRIMARY KEY, text TEXT)")
        conn.executemany(
            "INSERT INTO questions VALUES (?, ?)",
            [("q1", "orphaned"), ("q2", "also orphaned")],
        )
        conn.commit()
        conn.close()

        report = convert(seeds_dir)

        assert report.dropped_legacy_rows == {"questions": 2}
        assert report.total == 1
        tree = "".join(
            p.read_text(encoding="utf-8")
            for p in seed_files_dir(seeds_dir).glob("*.md")
        )
        assert "orphaned" not in tree

    def test_a_store_with_no_legacy_table_reports_nothing(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        build_db(seeds_dir, [seed("seeds-a1")]).close()
        assert convert(seeds_dir).dropped_legacy_rows == {}


class TestVestigialAnswersEdges:
    """The retired ``answers`` rows three real repos still hold.

    ``RelationType.ANSWERS`` was removed as a fossil, which was right — but
    pre-0.7 SQLite stores kept the rows, and the reader built the enum member
    eagerly, so ``seeds convert`` died with a bare ``ValueError`` on three of
    the thirteen unconverted repos. Ruled 2026-09-01: drop them and report the
    count, exactly as the legacy ``questions`` table is handled.

    Both readers drop them, because the legacy JSONL is an export *of* the
    legacy SQLite and carries the same rows — fixing only the SQLite path left
    the same three repos unconvertible for the same reason, one message later.
    """

    def _store_with_answers(self, seeds_dir: Path, count: int = 1) -> None:
        writer = build_db(
            seeds_dir,
            [seed("seeds-a1"), seed("seeds-b2"), seed("seeds-c3")],
        )
        writer.create_relationship(
            "seeds-a1", "seeds-b2", RelationType.RELATES_TO, _stamp(1)
        )
        pairs = [("seeds-b2", "seeds-a1"), ("seeds-c3", "seeds-a1"), ("a", "b")]
        for source, target in pairs[:count]:
            writer.create_raw_relationship(source, target, "answers", _stamp(2))
        writer.close()

    def test_conversion_completes_and_reports_the_dropped_count(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        self._store_with_answers(seeds_dir, count=3)

        report = convert(seeds_dir)

        assert report.dropped_legacy_edges == {"answers": 3}
        assert report.total == 3
        assert "dropped 3 legacy 'answers' edge(s), untranslated" in format_report(
            report
        )

    def test_the_dropped_edges_are_absent_from_the_tree(self, temp_dir):
        """The one `relates-to` survives at both ends; no `answers` reaches disk."""
        seeds_dir = temp_dir / ".seeds"
        self._store_with_answers(seeds_dir, count=2)

        convert(seeds_dir)

        out = seed_files_dir(seeds_dir)
        assert "answers" not in "".join(
            p.read_text(encoding="utf-8") for p in out.glob("*.md")
        )
        a1 = read_seed_file(out / "seeds-a1.md")
        b2 = read_seed_file(out / "seeds-b2.md")
        assert [(e.target_id, e.rel_type.value) for e in a1.relationships] == [
            ("seeds-b2", "relates-to")
        ]
        assert [(e.target_id, e.rel_type.value) for e in b2.relationships] == [
            ("seeds-a1", "relates-to")
        ]

    def test_a_dropped_edge_naming_a_missing_seed_is_still_counted(self, temp_dir):
        """Counted table-wide, not while reading.

        `get_relationships` only visits rows naming a seed that exists, so an
        `answers` row pointing at a deleted seed would go uncounted if the
        count were accumulated there — and an under-reported drop is the whole
        failure this count exists to prevent.
        """
        seeds_dir = temp_dir / ".seeds"
        writer = build_db(seeds_dir, [seed("seeds-a1")])
        writer.create_raw_relationship("seeds-gone", "seeds-x9", "answers", _stamp(1))
        writer.close()

        assert convert(seeds_dir).dropped_legacy_edges == {"answers": 1}

    def test_a_store_with_no_answers_rows_reports_nothing(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        build_db(seeds_dir, [seed("seeds-a1")]).close()

        report = convert(seeds_dir)

        assert report.dropped_legacy_edges == {}
        assert "untranslated" not in format_report(report)

    def test_an_unrecognised_rel_type_names_itself_instead_of_crashing(self, temp_dir):
        """The asymmetry this bead exists to close.

        The JSONL path already explained an unreadable `rel_type`; the SQLite
        path raised a bare `ValueError`, so *which store held the row* decided
        whether the operator got a diagnostic or a stack trace. A future
        unknown must not vanish into the `answers` bucket either.
        """
        seeds_dir = temp_dir / ".seeds"
        writer = build_db(seeds_dir, [seed("seeds-a1"), seed("seeds-b2")])
        writer.create_raw_relationship("seeds-a1", "seeds-b2", "supersedes", _stamp(1))
        writer.close()

        with pytest.raises(ConversionError) as excinfo:
            convert(seeds_dir)

        message = str(excinfo.value)
        assert str(seeds_dir / "seeds.db") in message
        assert "seeds-a1 -> seeds-b2" in message
        assert "'supersedes'" in message
        assert "closed set (relates-to, questions, questioned-by)" in message
        assert "§5.2" in message

    def test_the_jsonl_path_says_the_same_thing(self, temp_dir):
        """Both stores report the rule in one wording, which is the fix."""
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(
            seeds_dir,
            [
                record(
                    "seeds-a1",
                    relationships=[{"target_id": "seeds-b2", "rel_type": "supersedes"}],
                )
            ],
        )

        with pytest.raises(ConversionError) as excinfo:
            convert(seeds_dir)

        assert "closed set (relates-to, questions, questioned-by)" in str(excinfo.value)
        assert "§5.2" in str(excinfo.value)

    def test_the_jsonl_alone_drops_and_counts_them_too(self, temp_dir):
        """A fresh clone has no `seeds.db` — only the JSONL export of it."""
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(
            seeds_dir,
            [
                record(
                    "seeds-a1",
                    relationships=[
                        {"target_id": "seeds-b2", "rel_type": "answers"},
                        {"target_id": "seeds-b2", "rel_type": "relates-to"},
                    ],
                ),
                record("seeds-b2"),
            ],
        )

        report = convert(seeds_dir)

        assert report.dropped_legacy_edges == {"answers": 1}
        assert report.total == 2
        out = seed_files_dir(seeds_dir)
        assert [
            (e.target_id, e.rel_type.value)
            for e in read_seed_file(out / "seeds-a1.md").relationships
        ] == [("seeds-b2", "relates-to")]

    def test_one_edge_in_both_stores_is_counted_once(self, temp_dir):
        """The JSONL is an export of the SQLite, so one edge is normally two
        rows. Reporting "2" for one dropped edge would read as data the
        converter never had."""
        seeds_dir = temp_dir / ".seeds"
        self._store_with_answers(seeds_dir, count=1)
        write_jsonl(
            seeds_dir,
            [
                record("seeds-a1"),
                record(
                    "seeds-b2",
                    relationships=[{"target_id": "seeds-a1", "rel_type": "answers"}],
                ),
                record("seeds-c3"),
            ],
        )

        assert convert(seeds_dir).dropped_legacy_edges == {"answers": 1}

    def test_the_reader_skips_answers_and_raises_on_anything_else(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        writer = build_db(seeds_dir, [seed("seeds-a1"), seed("seeds-b2")])
        writer.create_raw_relationship("seeds-a1", "seeds-b2", "answers", _stamp(1))
        writer.close()

        db = LegacyDatabase(seeds_dir / "seeds.db")
        try:
            assert db.get_relationships("seeds-a1") == []
            assert db.vestigial_relationship_keys() == [
                ("seeds-a1", "seeds-b2", "answers")
            ]
        finally:
            db.close()

        writer = LegacyWriter(seeds_dir / "seeds.db")
        writer.create_raw_relationship("seeds-a1", "seeds-b2", "nonsense", _stamp(1))
        writer.close()

        db = LegacyDatabase(seeds_dir / "seeds.db")
        try:
            with pytest.raises(LegacyRelationTypeError) as excinfo:
                db.get_relationships("seeds-a1")
        finally:
            db.close()
        assert excinfo.value.rel_type == "nonsense"
        assert excinfo.value.source_id == "seeds-a1"
        assert excinfo.value.target_id == "seeds-b2"


# --- Multi-line legacy titles ------------------------------------------------


class TestSplitLegacyTitle:
    """The rule itself, on hand-built titles with hand-written verdicts.

    Ruled 2026-09-01, in precedence order: a blank line, else the first
    sentence end, else the first line. Two of the three have never fired on
    real data, which is exactly why they are pinned here rather than left to
    agree with whatever the function currently does.
    """

    def test_a_one_line_title_is_left_alone(self):
        assert split_legacy_title("A title", "body") == ("A title", "body", "", "")

    def test_the_two_real_shapes_split_at_the_blank_line(self):
        title, body, moved, rule = split_legacy_title(
            "Is X or Y?\n\nTwo readings:\n(a) one\n(b) two", "Resolved: (a)."
        )
        assert title == "Is X or Y?"
        assert rule == SPLIT_AT_BLANK_LINE
        assert moved == "Two readings:\n(a) one\n(b) two"
        assert body == "Two readings:\n(a) one\n(b) two\n\nResolved: (a)."

    def test_no_blank_line_splits_at_the_first_sentence_end(self):
        title, body, moved, rule = split_legacy_title(
            "The question. And then the elaboration\nover two lines", ""
        )
        assert (title, rule) == ("The question.", SPLIT_AT_SENTENCE_END)
        assert body == "And then the elaboration\nover two lines"
        assert moved == body

    def test_an_abbreviation_is_not_a_sentence_end(self):
        """`e.g.` mid-sentence must not silently truncate somebody's title.

        The corpus this rule exists for is dense with 'e.g.', 'vs.', 'Fig.'
        and version strings; cutting at one would look like a working split
        and be a truncation.
        """
        title, body, moved, rule = split_legacy_title(
            "Use e.g. Foo as the example. Then the rest\nsecond line", ""
        )
        assert title == "Use e.g. Foo as the example."
        assert rule == SPLIT_AT_SENTENCE_END
        assert body == "Then the rest\nsecond line"
        assert moved == body

    @pytest.mark.parametrize(
        "first_line",
        [
            "Label the version v2023.1 in the dropdown",  # a version number
            "Compare A vs. B before deciding",  # an abbreviation
            "no sentence punctuation here at all",
            "Ends the line with a stop.",  # a stop AT the end is the line rule
            "A question mark then lowercase? no capital follows",
        ],
    )
    def test_nothing_that_is_not_a_sentence_end_cuts_the_first_line(self, first_line):
        title, body, moved, rule = split_legacy_title(f"{first_line}\nsecond line", "")
        assert title == first_line
        assert rule == SPLIT_AT_FIRST_LINE
        assert (body, moved) == ("second line", "second line")

    def test_a_blank_line_below_line_two_cuts_by_the_rule_that_actually_fired(self):
        """Rule 1 fires only where it yields a one-line title.

        A first blank line further down would leave a title still spanning
        lines, so the cut is made by rule 2 and reported as rule 2. The moved
        text is the same either way; what must be true is that the operator is
        told which rule touched their title.
        """
        title, body, moved, rule = split_legacy_title(
            "First. Second\nthird\n\nfourth", ""
        )
        assert (title, rule) == ("First.", SPLIT_AT_SENTENCE_END)
        assert body == "Second\nthird\n\nfourth"
        assert moved == body

    def test_leading_blank_lines_do_not_empty_the_title(self):
        title, body, moved, rule = split_legacy_title("\n \nReal title\nmore", "")
        assert (title, rule) == ("Real title", SPLIT_AT_FIRST_LINE)
        assert (body, moved) == ("more", "more")

    def test_a_title_that_is_only_blank_lines_stays_empty(self):
        """Inventing a title is not this function's call.

        `write_seed_file` refuses an empty one loudly a moment later, which is
        the right place for that to be settled.
        """
        assert split_legacy_title("\n\n", "body") == ("", "body", "", "")

    def test_trailing_blank_lines_alone_are_not_a_split(self):
        assert split_legacy_title("A title\n\n", "body") == ("A title", "body", "", "")

    def test_an_empty_body_takes_the_moved_text_alone(self):
        title, body, moved, _ = split_legacy_title("Head\n\nTail", "")
        assert (title, body, moved) == ("Head", "Tail", "Tail")


class TestMultiLineLegacyTitleConversion:
    """The last store `seeds convert` could not finish.

    Two of `code_set_catalog`'s 435 seeds carried a whole multi-paragraph
    thought in the title column, and §3 allows one non-empty line -- so the
    writer refused and 435 seeds stayed unconverted over 2 records. Ruled
    2026-09-01: split it, and NAME every seed split, because a content move
    nobody is told about is the silent collapse this module refuses.
    """

    LONG = "The real question?\n\nElaboration line one.\nElaboration line two."

    def test_a_multi_line_title_converts_and_loses_nothing(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        build_db(
            seeds_dir, [seed("seeds-a1", title=self.LONG, content="Resolved: yes.")]
        ).close()

        report = convert(seeds_dir)

        written = read_seed_file(seed_files_dir(seeds_dir) / "seeds-a1.md")
        assert written.title == "The real question?"
        assert written.body == (
            "Elaboration line one.\nElaboration line two.\n\nResolved: yes.\n"
        )
        assert report.split_titles == {"seeds-a1": SPLIT_AT_BLANK_LINE}

    def test_the_report_names_every_split_seed_and_the_rule_that_cut_it(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        build_db(
            seeds_dir,
            [
                seed("seeds-a1", title=self.LONG),
                seed("seeds-b2", title="One line only"),
                seed("seeds-c3", title="No blank line here\nsecond line"),
            ],
        ).close()

        text = format_report(convert(seeds_dir))

        assert "split 2 multi-line legacy title(s)" in text
        assert "seeds-a1  (at blank line)" in text
        assert "seeds-c3  (at first line)" in text
        assert "seeds-b2" not in text

    def test_the_jsonl_alone_splits_it_too(self, temp_dir):
        """A fresh clone has no `seeds.db` -- only the JSONL export of it.

        The legacy JSONL is an export *of* the legacy SQLite, so it carries the
        same over-long title. Handling it at one reader only turns the crash
        into a refusal one message later, which is the mistake the vestigial
        `answers` drop already made once.
        """
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(
            seeds_dir, [record("seeds-a1", title=self.LONG, content="Resolved: yes.")]
        )

        report = convert(seeds_dir)

        assert report.split_titles == {"seeds-a1": SPLIT_AT_BLANK_LINE}
        written = read_seed_file(seed_files_dir(seeds_dir) / "seeds-a1.md")
        assert written.title == "The real question?"
        assert "Elaboration line two.\n\nResolved: yes." in written.body

    def test_one_title_in_both_stores_is_reported_once(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        build_db(
            seeds_dir, [seed("seeds-a1", title=self.LONG, content="Resolved: yes.")]
        ).close()
        write_jsonl(
            seeds_dir, [record("seeds-a1", title=self.LONG, content="Resolved: yes.")]
        )

        report = convert(seeds_dir)

        assert report.split_titles == {"seeds-a1": SPLIT_AT_BLANK_LINE}
        assert report.counts == {Classification.DB_EXTENDS_DISK: 1}
        assert "split 1 multi-line legacy title(s)" in format_report(report)

    def test_a_store_with_no_multi_line_title_says_nothing(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        build_db(seeds_dir, [seed("seeds-a1")]).close()

        report = convert(seeds_dir)

        assert report.split_titles == {}
        assert "multi-line legacy title" not in format_report(report)

    def test_the_converted_tree_passes_its_own_check(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        build_db(
            seeds_dir, [seed("seeds-a1", title=self.LONG, content="Resolved: yes.")]
        ).close()

        report = convert(seeds_dir)

        assert report.check_findings == []
        assert report.verified == 1
        assert check_violations(seeds_dir) == []


# --- Non-destructive, and idempotent -----------------------------------------


class TestNonDestructive:
    def test_neither_source_store_is_touched(self, synthetic_store):
        before = {
            name: (synthetic_store / name).read_bytes()
            for name in ("seeds.db", "seeds.jsonl")
        }

        convert(synthetic_store)

        for name, content in before.items():
            assert (synthetic_store / name).read_bytes() == content

    def test_reverting_is_removing_the_tree(self, synthetic_store):
        convert(synthetic_store)
        assert seed_files_dir(synthetic_store).is_dir()
        assert (synthetic_store / "seeds.jsonl").exists()

    def test_a_stale_file_is_reported_and_left_alone(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(seeds_dir, [record("seeds-a1")])
        convert(seeds_dir)
        stale = seed_files_dir(seeds_dir) / "seeds-zz.md"
        stale.write_text("not a seed file", encoding="utf-8")

        report = convert(seeds_dir)

        assert report.stale_files == ["seeds-zz.md"]
        assert stale.read_text(encoding="utf-8") == "not a seed file"

    def test_the_second_run_rewrites_nothing(self, synthetic_store):
        first = convert(synthetic_store)
        second = convert(synthetic_store)
        assert len(first.written) == 4
        assert second.written == []
        assert len(second.unchanged) == 4

    def test_a_second_run_leaves_git_diff_empty(self, temp_dir):
        """Byte-idempotence of the tree, asserted the way the bead states it.

        Scoped to ``.seeds/seeds/`` because the second run is the first one in
        which the JSONL is tracked and clean, so it is also the run that stages
        the JSONL's deletion (seeds-4co.19). That removal is a real, intended
        change to the index; what must not move is the tree.
        """
        repo = temp_dir / "repo"
        seeds_dir = repo / ".seeds"
        seeds_dir.mkdir(parents=True)
        write_jsonl(
            seeds_dir,
            [record("seeds-a1", content="one\n"), record("seeds-b2", tags=["x"])],
        )
        git_init(repo)
        convert(seeds_dir)
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "converted")

        convert(seeds_dir)

        assert git(repo, "diff", "--", ".seeds/seeds").stdout == ""
        assert git(repo, "status", "--porcelain", "--", ".seeds/seeds").stdout == ""

    def test_converted_at_is_stamped_once_and_never_re_read_from_the_clock(
        self, temp_dir
    ):
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(seeds_dir, [record("seeds-a1")])
        convert(seeds_dir, now=_stamp(10))
        first = read_seed_file(seed_files_dir(seeds_dir) / "seeds-a1.md")

        convert(seeds_dir, now=_stamp(99))

        second = read_seed_file(seed_files_dir(seeds_dir) / "seeds-a1.md")
        assert first.converted_at == _stamp(10)
        assert second.converted_at == _stamp(10)


# --- Verification refuses output it cannot vouch for -------------------------


class TestVerificationCatchesLies:
    """The gate is itself code that can be silently wrong, so it is handed
    output that is wrong in a specific way and must refuse each one."""

    def _unions(self, seeds_dir: Path):
        from seeds.convert import _load_db, _load_jsonl, _resolve_edges, union_records

        db_sides, db_halves, _, _ = _load_db(seeds_dir / "seeds.db")
        jsonl_sides, jsonl_halves, _ = _load_jsonl(seeds_dir / "seeds.jsonl")
        known = frozenset(set(db_sides) | set(jsonl_sides))
        edges, _ = _resolve_edges([*db_halves, *jsonl_halves], known)
        unions, _ = union_records(db_sides, jsonl_sides, edges)
        return unions, db_sides, jsonl_sides

    def test_a_body_edited_after_the_write_is_caught(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(seeds_dir, [record("seeds-a1", content="original\n")])
        convert(seeds_dir)
        unions, db_sides, jsonl_sides = self._unions(seeds_dir)
        for union in unions:
            union.record.converted_at = read_seed_file(
                seed_files_dir(seeds_dir) / "seeds-a1.md"
            ).converted_at
        path = seed_files_dir(seeds_dir) / "seeds-a1.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace("original", "tampered"),
            encoding="utf-8",
        )

        with pytest.raises(ConversionError, match="part ways at character"):
            verify(seed_files_dir(seeds_dir), unions, db_sides, jsonl_sides)

    def test_a_title_no_store_holds_is_caught(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(seeds_dir, [record("seeds-a1", title="Real title")])
        convert(seeds_dir)
        unions, db_sides, jsonl_sides = self._unions(seeds_dir)
        # Both the tree and the union carry the invented title, so only the
        # comparison against the RAW STORES can see it. A converter verified
        # against its own intermediate would agree with itself here.
        path = seed_files_dir(seeds_dir) / "seeds-a1.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace("Real title", "Invented"),
            encoding="utf-8",
        )
        for union in unions:
            union.record.title = "Invented"
            union.record.converted_at = read_seed_file(path).converted_at

        with pytest.raises(ConversionError, match="no source store holds that value"):
            verify(seed_files_dir(seeds_dir), unions, db_sides, jsonl_sides)

    def test_a_missing_file_is_caught(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(seeds_dir, [record("seeds-a1")])
        convert(seeds_dir)
        unions, db_sides, jsonl_sides = self._unions(seeds_dir)
        (seed_files_dir(seeds_dir) / "seeds-a1.md").unlink()

        with pytest.raises(ConversionError):
            verify(seed_files_dir(seeds_dir), unions, db_sides, jsonl_sides)

    def test_a_dropped_tag_is_caught(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(seeds_dir, [record("seeds-a1", tags=["kept", "lost"])])
        convert(seeds_dir)
        unions, db_sides, jsonl_sides = self._unions(seeds_dir)
        path = seed_files_dir(seeds_dir) / "seeds-a1.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace("  - lost\n", ""),
            encoding="utf-8",
        )
        for union in unions:
            union.record.tags = ["kept"]
            union.record.converted_at = read_seed_file(path).converted_at

        with pytest.raises(ConversionError, match="are in a source store"):
            verify(seed_files_dir(seeds_dir), unions, db_sides, jsonl_sides)


class TestCompletenessOutranksCheck:
    """`seeds check` exits 0 on an empty store, so it cannot be the whole gate.

    Measured on the merged checker: an empty `.seeds/seeds/` reports "0 files,
    no violations" and exits 0, while the same corpus rendered in full reports
    57 violations and exits 1. A converter that emitted nothing, or silently
    skipped most ids, therefore passes its own check step cleanly. Every test
    here asserts BOTH halves -- that check is green on the broken tree, and
    that verification refuses it anyway -- because the first half is what makes
    the second one necessary.
    """

    def _unions(self, seeds_dir: Path):
        from seeds.convert import _load_db, _load_jsonl, _resolve_edges, union_records

        db_sides, db_halves, _, _ = _load_db(seeds_dir / "seeds.db")
        jsonl_sides, jsonl_halves, _ = _load_jsonl(seeds_dir / "seeds.jsonl")
        known = frozenset(set(db_sides) | set(jsonl_sides))
        edges, _ = _resolve_edges([*db_halves, *jsonl_halves], known)
        unions, _ = union_records(db_sides, jsonl_sides, edges)
        return unions, db_sides, jsonl_sides

    def test_check_really_is_green_on_an_empty_store(self, temp_dir):
        """The premise, asserted rather than assumed."""
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(seeds_dir, [record("seeds-a1")])
        convert(seeds_dir)
        for path in seed_files_dir(seeds_dir).glob("*.md"):
            path.unlink()

        assert check_violations(seeds_dir) == []

    def test_a_zero_file_conversion_is_a_hard_error(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(
            seeds_dir, [record("seeds-a1"), record("seeds-b2"), record("seeds-c3")]
        )
        convert(seeds_dir)
        unions, db_sides, jsonl_sides = self._unions(seeds_dir)
        for path in seed_files_dir(seeds_dir).glob("*.md"):
            path.unlink()

        assert check_violations(seeds_dir) == []
        with pytest.raises(ConversionError, match="holds none of them"):
            verify(seed_files_dir(seeds_dir), unions, db_sides, jsonl_sides)

    def test_a_short_conversion_names_the_missing_ids(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(
            seeds_dir, [record("seeds-a1"), record("seeds-b2"), record("seeds-c3")]
        )
        convert(seeds_dir)
        unions, db_sides, jsonl_sides = self._unions(seeds_dir)
        (seed_files_dir(seeds_dir) / "seeds-b2.md").unlink()

        assert check_violations(seeds_dir) == []
        with pytest.raises(ConversionError) as caught:
            verify(seed_files_dir(seeds_dir), unions, db_sides, jsonl_sides)
        assert "seeds-b2" in str(caught.value)
        assert "seeds-a1" not in str(caught.value)

    def test_a_union_that_skipped_an_id_is_caught_before_any_file_is_read(
        self, temp_dir
    ):
        """Equal counts can still hide a swap, so the comparison is on SETS."""
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(seeds_dir, [record("seeds-a1"), record("seeds-b2")])
        convert(seeds_dir)
        unions, db_sides, jsonl_sides = self._unions(seeds_dir)
        short = [u for u in unions if u.record.id != "seeds-b2"]

        with pytest.raises(ConversionError, match="does not cover the source stores"):
            verify(seed_files_dir(seeds_dir), short, db_sides, jsonl_sides)

    def test_an_absence_the_converter_never_declared_is_a_failure(self, temp_dir):
        """The six fixtures are absences the converter DECLARED. Passing an
        empty drop list makes the same absence unexplained, and it must fail."""
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(seeds_dir, [record("seeds-a1"), record("seeds-71")])
        report = convert(seeds_dir)
        assert report.dropped_fixtures == ["seeds-71"]

        from seeds.convert import _load_jsonl

        jsonl_sides, _, _ = _load_jsonl(seeds_dir / "seeds.jsonl")
        unions, db_sides, _ = self._unions(seeds_dir)
        kept = [u for u in unions if u.record.id != "seeds-71"]
        for union in kept:
            union.record.converted_at = read_seed_file(
                seed_files_dir(seeds_dir) / f"{union.record.id}.md"
            ).converted_at

        # Declared: passes. Undeclared: the identical tree is refused.
        assert (
            verify(
                seed_files_dir(seeds_dir),
                kept,
                db_sides,
                jsonl_sides,
                drop_ids=frozenset({"seeds-71"}),
            )
            == 1
        )
        with pytest.raises(ConversionError, match="does not cover the source stores"):
            verify(seed_files_dir(seeds_dir), kept, db_sides, jsonl_sides)

    def test_the_report_prints_the_arithmetic(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(
            seeds_dir,
            [record("seeds-a1"), *(record(i) for i in sorted(FIXTURE_IDS))],
        )

        report = convert(seeds_dir)

        assert report.source_ids == 1 + len(FIXTURE_IDS)
        assert report.total == 1
        assert format_report(report).splitlines()[1] == (
            "  7 seed(s) in the source stores -> 1 converted: 1 written, "
            "0 already current"
        )


# --- Strict reading of the source stores -------------------------------------


class TestStrictSources:
    def test_a_line_that_is_not_json_stops_the_conversion(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        seeds_dir.mkdir(parents=True)
        (seeds_dir / "seeds.jsonl").write_text(
            json.dumps(record("seeds-a1")) + "\n<<<<<<< HEAD\n", encoding="utf-8"
        )

        with pytest.raises(ConversionError, match="not valid JSON"):
            convert(seeds_dir)

    def test_a_v1_record_is_refused_by_name(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        stale = record("seeds-a1")
        stale["format_version"] = 1
        write_jsonl(seeds_dir, [stale])

        with pytest.raises(ConversionError, match="format_version"):
            convert(seeds_dir)

    def test_two_lines_for_one_id_are_refused_rather_than_guessed_at(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(
            seeds_dir,
            [
                record("seeds-a1", content="left\n"),
                record("seeds-a1", content="right\n"),
            ],
        )

        with pytest.raises(ConversionError, match="more than one line"):
            convert(seeds_dir)

    def test_two_identical_lines_for_one_id_are_the_same_record(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(seeds_dir, [record("seeds-a1"), record("seeds-a1")])
        assert convert(seeds_dir).total == 1

    def test_a_status_outside_the_closed_set_is_refused(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(seeds_dir, [record("seeds-a1", status="percolating")])

        with pytest.raises(ConversionError, match="outside the closed set"):
            convert(seeds_dir)

    def test_an_open_type_vocabulary_round_trips(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(seeds_dir, [record("seeds-a1", seed_type="incident")])
        convert(seeds_dir)
        got = read_seed_file(seed_files_dir(seeds_dir) / "seeds-a1.md")
        assert got.seed_type == "incident"

    def test_no_store_at_all_is_an_error(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        seeds_dir.mkdir(parents=True)
        with pytest.raises(ConversionError, match=r"no pre-0\.7 store"):
            convert(seeds_dir)

    def test_a_naive_timestamp_is_normalized_to_utc_once(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        naive = record("seeds-a1")
        naive["created_at"] = "2026-01-01T12:00:00"
        naive["updated_at"] = "2026-01-01T12:00:00"
        write_jsonl(seeds_dir, [naive])

        convert(seeds_dir)

        got = read_seed_file(seed_files_dir(seeds_dir) / "seeds-a1.md")
        assert got.created_at == datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


# --- Repo-level configuration ------------------------------------------------


class TestConfig:
    def test_the_prefix_is_carried_out_of_sqlite_into_config_yaml(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        build_db(seeds_dir, [seed("seeds-a1")]).close()

        report = convert(seeds_dir)

        assert report.prefix_written == "seeds"
        assert (seeds_dir / "config.yaml").read_text() == "prefix: seeds\n"

    def test_an_existing_config_is_never_overwritten(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        seeds_dir.mkdir(parents=True)
        (seeds_dir / "config.yaml").write_text("prefix: mine\n")
        write_jsonl(seeds_dir, [record("seeds-a1")])

        report = convert(seeds_dir)

        assert report.prefix_written is None
        assert (seeds_dir / "config.yaml").read_text() == "prefix: mine\n"

    def test_with_no_database_the_prefix_comes_from_the_ids(self, temp_dir):
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(seeds_dir, [record("seeds-a1")])
        assert convert(seeds_dir).prefix_written == "seeds"


# --- This repository's real corpus -------------------------------------------


@pytest.fixture
def real_corpus(temp_dir):
    """A copy of this repo's own JSONL. Nothing here writes to the real store."""
    if not REPO_JSONL.exists():
        pytest.skip("no .seeds/seeds.jsonl here (a source tarball, not a checkout)")
    seeds_dir = temp_dir / ".seeds"
    seeds_dir.mkdir(parents=True)
    (seeds_dir / "seeds.jsonl").write_bytes(REPO_JSONL.read_bytes())
    return seeds_dir


class TestRealCorpus:
    def test_every_record_converts_and_the_six_fixtures_go(self, real_corpus):
        source_ids = {
            json.loads(line)["id"]
            for line in (real_corpus / "seeds.jsonl").read_text().splitlines()
            if line.strip()
        }

        report = convert(real_corpus)

        assert report.total == len(source_ids) - len(FIXTURE_IDS)
        assert report.verified == report.total
        written = {p.name[:-3] for p in seed_files_dir(real_corpus).glob("*.md")}
        assert written == source_ids - FIXTURE_IDS

    def test_the_output_passes_seeds_check(self, real_corpus):
        """The carry-over finding in reverse: check reports 57 one-sided
        `questions` edges on a corpus rendered without the inverses, and zero
        once the converter materializes them."""
        convert(real_corpus)
        assert check_violations(real_corpus) == []

    def test_no_fork_and_nothing_unexplained(self, real_corpus):
        report = convert(real_corpus)
        assert report.forks == []
        assert report.dropped_edges == []
        assert report.field_divergences == []
        assert report.clean

    def test_it_is_byte_idempotent_on_the_real_corpus(self, real_corpus):
        convert(real_corpus)
        digests = {
            p.name: p.read_bytes()
            for p in sorted(seed_files_dir(real_corpus).glob("*.md"))
        }

        convert(real_corpus)

        assert {
            p.name: p.read_bytes()
            for p in sorted(seed_files_dir(real_corpus).glob("*.md"))
        } == digests

    def test_converting_through_the_database_gives_the_same_bodies(self, real_corpus):
        """DB + JSONL, where the database holds exactly that file's records,
        must land exactly what the file alone lands. It is the cheapest
        available check that the union step does not favour a store."""
        convert(real_corpus)
        file_only = {
            p.name: read_seed_file(p).body
            for p in seed_files_dir(real_corpus).glob("*.md")
        }
        writer = LegacyWriter(real_corpus / "seeds.db")
        writer.set_prefix("seeds")
        with open(real_corpus / "seeds.jsonl", encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    writer.create_seed(_seed_from_jsonl(json.loads(line)))
        writer.close()

        report = convert(real_corpus)

        assert report.counts == {Classification.DB_EXTENDS_DISK: report.total}
        assert {
            p.name: read_seed_file(p).body
            for p in seed_files_dir(real_corpus).glob("*.md")
        } == file_only


# --- The CLI -----------------------------------------------------------------


class TestConvertCommand:
    def test_it_reports_and_exits_clean(self, temp_dir, cli_runner, monkeypatch):
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(seeds_dir, [record("seeds-a1", title="Landed")])
        monkeypatch.chdir(temp_dir)

        result = cli_runner.invoke(main, ["convert"])

        assert result.exit_code == 0, result.output
        assert "1 seed(s) in the source stores -> 1 converted" in result.output
        assert "round-trip verified 1 record(s)" in result.output

    def test_an_unresolved_fork_exits_non_zero_and_names_the_file(
        self, synthetic_store, cli_runner, monkeypatch
    ):
        monkeypatch.chdir(synthetic_store.parent)

        result = cli_runner.invoke(main, ["convert"])

        assert result.exit_code == 1
        assert "1 fork(s) need a human" in result.output
        assert f"{FORK_ID}.md" in result.output

    def test_a_refused_source_record_exits_non_zero(
        self, temp_dir, cli_runner, monkeypatch
    ):
        seeds_dir = temp_dir / ".seeds"
        write_jsonl(seeds_dir, [record("seeds-a1", status="percolating")])
        monkeypatch.chdir(temp_dir)

        result = cli_runner.invoke(main, ["convert"])

        assert result.exit_code == 1
        assert "outside the closed set" in result.output
