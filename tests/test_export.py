"""Tests for seeds export/import functionality."""

import json
import re
from datetime import datetime, timedelta, timezone

import pytest

from seeds.db import Database
from seeds.export import (
    FUTURE_TIMESTAMP_TOLERANCE,
    DivergentExportError,
    ImportResult,
    RefusedRecord,
    db_extends_disk,
    export_to_jsonl,
    export_would_change,
    find_divergence,
    import_from_jsonl,
    import_lines,
    seed_to_dict,
)
from seeds.models import (
    RelationType,
    Seed,
    SeedStatus,
    SeedType,
    now_utc,
)


class TestSeedToDict:
    """Tests for seed_to_dict conversion (v2 format)."""

    def test_basic_seed_conversion(self, db):
        """Verify basic seed converts to dict correctly."""
        now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        seed = Seed(
            id="seed-test",
            title="Test Seed",
            content="Content here",
            status=SeedStatus.EXPLORING,
            seed_type=SeedType.IDEA,
            tags=["tag1", "tag2"],
            created_at=now,
            updated_at=now,
        )
        db.create_seed(seed)

        result = seed_to_dict(seed, db)

        assert result["format_version"] == 2
        assert result["id"] == "seed-test"
        assert result["title"] == "Test Seed"
        assert result["content"] == "Content here"
        assert result["status"] == "exploring"
        assert result["seed_type"] == "idea"
        assert result["tags"] == ["tag1", "tag2"]
        assert result["created_at"] == "2025-01-15T12:00:00+00:00"
        assert result["resolved_at"] is None
        assert result["resolution"] == ""
        assert result["relationships"] == []

    def test_seed_with_resolution(self, db):
        """Verify resolved seed with resolution exports correctly."""
        now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        seed = Seed(
            id="seed-resolved",
            title="Resolved Seed",
            status=SeedStatus.RESOLVED,
            resolved_at=now,
            resolution="Shipped in PR #42",
            created_at=now,
            updated_at=now,
        )
        db.create_seed(seed)

        result = seed_to_dict(seed, db)
        assert result["resolution"] == "Shipped in PR #42"
        assert result["status"] == "resolved"

    def test_seed_with_relationships(self, db):
        """Verify relationships are included as outbound edges."""
        now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        seed = Seed(id="seed-test", title="Test Seed", created_at=now, updated_at=now)
        other = Seed(id="seed-other", title="Other", created_at=now, updated_at=now)
        q_seed = Seed(
            id="seeds-q1",
            title="A question?",
            seed_type=SeedType.QUESTION,
            created_at=now,
            updated_at=now,
        )
        db.create_seed(seed)
        db.create_seed(other)
        db.create_seed(q_seed)
        db.create_relationship("seed-test", "seed-other", RelationType.RELATES_TO)
        db.create_relationship("seeds-q1", "seed-test", RelationType.QUESTIONS)

        result = seed_to_dict(seed, db)

        # seed-test has outbound: relates-to seed-other, and inbound from other
        # Only outbound edges are exported per seed
        rels = result["relationships"]
        assert len(rels) == 1
        assert rels[0]["target_id"] == "seed-other"
        assert rels[0]["rel_type"] == "relates-to"

        # Question-seed has outbound 'questions' edge
        q_result = seed_to_dict(q_seed, db)
        q_rels = q_result["relationships"]
        assert len(q_rels) == 1
        assert q_rels[0]["target_id"] == "seed-test"
        assert q_rels[0]["rel_type"] == "questions"


class TestExportToJsonl:
    """Tests for JSONL export."""

    def test_export_empty_database(self, db, temp_dir):
        """Verify export creates empty file for empty database."""
        output_path = temp_dir / "output.jsonl"
        result = export_to_jsonl(db, output_path)

        assert result == output_path
        assert output_path.exists()
        assert output_path.read_text() == ""

    def test_export_single_seed(self, db, temp_dir, sample_seed):
        """Verify single seed exports correctly."""
        db.create_seed(sample_seed)
        output_path = temp_dir / "output.jsonl"

        export_to_jsonl(db, output_path)

        lines = output_path.read_text().strip().split("\n")
        assert len(lines) == 1

        data = json.loads(lines[0])
        assert data["format_version"] == 2
        assert data["id"] == sample_seed.id
        assert data["title"] == sample_seed.title

    def test_export_multiple_seeds_sorted(self, db, temp_dir):
        """Verify multiple seeds are exported sorted by ID."""
        seeds = [
            Seed(id="seed-c", title="C"),
            Seed(id="seed-a", title="A"),
            Seed(id="seed-b", title="B"),
        ]
        for seed in seeds:
            db.create_seed(seed)

        output_path = temp_dir / "output.jsonl"
        export_to_jsonl(db, output_path)

        lines = output_path.read_text().strip().split("\n")
        ids = [json.loads(line)["id"] for line in lines]
        assert ids == ["seed-a", "seed-b", "seed-c"]

    def test_export_includes_terminal_seeds(self, db, temp_dir):
        """Verify export includes resolved/abandoned seeds."""
        seeds = [
            Seed(id="seed-1", title="Active", status=SeedStatus.EXPLORING),
            Seed(id="seed-2", title="Resolved", status=SeedStatus.RESOLVED),
            Seed(id="seed-3", title="Abandoned", status=SeedStatus.ABANDONED),
        ]
        for seed in seeds:
            db.create_seed(seed)

        output_path = temp_dir / "output.jsonl"
        export_to_jsonl(db, output_path)

        lines = output_path.read_text().strip().split("\n")
        assert len(lines) == 3

    def test_export_includes_relationships(self, db, temp_dir):
        """Verify export includes relationships as outbound edges."""
        db.create_seed(Seed(id="seed-a", title="A"))
        db.create_seed(Seed(id="seed-b", title="B"))
        db.create_relationship("seed-a", "seed-b", RelationType.RELATES_TO)

        output_path = temp_dir / "output.jsonl"
        export_to_jsonl(db, output_path)

        lines = output_path.read_text().strip().split("\n")
        data_a = json.loads(lines[0])  # seed-a (sorted first)
        assert len(data_a["relationships"]) == 1
        assert data_a["relationships"][0]["target_id"] == "seed-b"


class TestExportWouldChange:
    """Tests for export_would_change (seeds-ww8's no-op detector)."""

    def test_missing_file_counts_as_a_change_even_for_an_empty_db(self, db, temp_dir):
        """Nothing on disk to be a no-op against, even with zero seeds."""
        output_path = temp_dir / "output.jsonl"
        assert not output_path.exists()

        assert export_would_change(db, output_path) is True

    def test_missing_file_with_seeds_is_a_change(self, db, temp_dir, sample_seed):
        db.create_seed(sample_seed)
        output_path = temp_dir / "output.jsonl"

        assert export_would_change(db, output_path) is True

    def test_freshly_exported_file_is_not_a_change(self, db, temp_dir, sample_seed):
        """The everyday no-op: export, then ask again with nothing new."""
        db.create_seed(sample_seed)
        output_path = temp_dir / "output.jsonl"
        export_to_jsonl(db, output_path)

        assert export_would_change(db, output_path) is False

    def test_freshly_exported_file_with_relationships_is_not_a_change(
        self, db, temp_dir
    ):
        """Round-trips relationships too, not just scalar fields."""
        db.create_seed(Seed(id="seed-a", title="A"))
        db.create_seed(Seed(id="seed-b", title="B"))
        db.create_relationship("seed-a", "seed-b", RelationType.RELATES_TO)
        output_path = temp_dir / "output.jsonl"
        export_to_jsonl(db, output_path)

        assert export_would_change(db, output_path) is False

    def test_unflushed_db_delta_is_a_change(self, db, temp_dir, sample_seed):
        """A seed created after the last export makes the next flush real."""
        db.create_seed(sample_seed)
        output_path = temp_dir / "output.jsonl"
        export_to_jsonl(db, output_path)

        db.create_seed(Seed(id="seed-new", title="Not yet flushed"))

        assert export_would_change(db, output_path) is True

    def test_content_divergent_from_disk_is_a_change(self, db, temp_dir, sample_seed):
        """Blind to the divergence guard's safety question -- the bytes just differ.

        export_would_change only answers "would the bytes differ"; whether
        overwriting them is SAFE is find_divergence's job. A file the export
        would refuse to overwrite still, correctly, reads as "would change".
        """
        db.create_seed(sample_seed)
        output_path = temp_dir / "output.jsonl"
        export_to_jsonl(db, output_path)

        records = [json.loads(line) for line in output_path.read_text().splitlines()]
        records[0]["content"] = "hand-edited, never seen by the db"
        output_path.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
        )

        assert export_would_change(db, output_path) is True

    def test_defaults_to_the_project_seeds_jsonl_path(self, db, temp_dir, monkeypatch):
        """No explicit output_path falls back to .seeds/seeds.jsonl under cwd."""
        monkeypatch.chdir(temp_dir)
        (temp_dir / ".seeds").mkdir(exist_ok=True)

        assert export_would_change(db) is True

        export_to_jsonl(db)

        assert export_would_change(db) is False


def _write_records(path, records):
    """Write JSONL records to `path`, returning the path."""
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
    return path


def _record(seed_id, content, updated_at=None, **overrides):
    """A minimal v2 JSONL record, ready to be mutated by a test."""
    stamp = (updated_at or now_utc()).isoformat()
    data = {
        "format_version": 2,
        "id": seed_id,
        "title": f"Title for {seed_id}",
        "content": content,
        "status": "captured",
        "seed_type": "idea",
        "tags": [],
        "created_at": stamp,
        "updated_at": stamp,
        "resolved_at": None,
        "resolution": "",
        "relationships": [],
    }
    data.update(overrides)
    return data


class TestDbExtendsDisk:
    """The append-prefix heuristic that separates 'DB is ahead' from 'diverged'."""

    def test_identical_content_extends(self):
        assert db_extends_disk("same body", "same body")

    def test_appended_content_extends(self):
        """The normal editing verb: `seeds update -a` appends to the body."""
        assert db_extends_disk("original\n\nappended later", "original")

    def test_empty_on_disk_is_covered(self):
        """A seed jotted with no body, then filled in, must not trip the check."""
        assert db_extends_disk("body added after the first sync", "")

    def test_divergent_content_is_not_covered(self):
        assert not db_extends_disk("DESKTOP edit", "LAPTOP edit")

    def test_truncated_db_content_is_not_covered(self):
        """The disk holding MORE than the DB is the loss case, not an append."""
        assert not db_extends_disk("original", "original\n\nappended on a peer")

    def test_prepended_content_is_not_covered(self):
        """An in-place rewrite that keeps the old body but not at the front."""
        assert not db_extends_disk("Header:\noriginal", "original")

    def test_replaced_content_is_not_covered(self):
        """`seeds update -c --replace` breaks the prefix property, deliberately.

        A replace is exactly when the operator should be sure, so a
        replace-derived divergence refuses like any other; the escape hatch
        covers the case where the discard was intended.
        """
        assert not db_extends_disk("brand new body", "the body it replaced")

    def test_leading_whitespace_does_not_trip_the_check(self):
        """`seeds update -a` strips the COMBINED body (cli.py).

        So appending to a body with leading whitespace yields a result that is
        not a literal prefix of it, even though no text was lost.
        """
        assert db_extends_disk("original\n\nappended", "  original")

    def test_stripped_fallback_still_catches_real_loss(self):
        """The whitespace tolerance must not become a hole for missing text."""
        assert not db_extends_disk("  original  ", "original and then some")


class TestFindDivergence:
    """What `export_to_jsonl` would destroy if it rewrote the file."""

    def test_missing_file_has_no_divergence(self, db, temp_dir):
        assert find_divergence(db, temp_dir / "absent.jsonl") == []

    def test_empty_file_has_no_divergence(self, db, temp_dir):
        path = temp_dir / "out.jsonl"
        path.write_text("")
        assert find_divergence(db, path) == []

    def test_matching_file_has_no_divergence(self, db, temp_dir):
        db.create_seed(Seed(id="seed-a", title="A", content="body"))
        path = export_to_jsonl(db, temp_dir / "out.jsonl")
        assert find_divergence(db, path) == []

    def test_db_ahead_by_an_append_has_no_divergence(self, db, temp_dir):
        seed = Seed(id="seed-a", title="A", content="body")
        db.create_seed(seed)
        path = export_to_jsonl(db, temp_dir / "out.jsonl")

        seed.content = "body\n\nmore deliberation"
        db.update_seed(seed)
        assert find_divergence(db, path) == []

    def test_db_only_seeds_are_not_divergence(self, db, temp_dir):
        """Records the export ADDS are not loss; only what it removes is."""
        db.create_seed(Seed(id="seed-a", title="A", content="body"))
        path = export_to_jsonl(db, temp_dir / "out.jsonl")
        db.create_seed(Seed(id="seed-b", title="B", content="new"))
        assert find_divergence(db, path) == []

    def test_divergent_content_is_reported(self, db, temp_dir):
        db.create_seed(Seed(id="seed-a", title="A", content="DESKTOP body"))
        path = _write_records(
            temp_dir / "out.jsonl", [_record("seed-a", "LAPTOP body")]
        )

        divergences = find_divergence(db, path)
        assert len(divergences) == 1
        assert divergences[0].seed_id == "seed-a"
        assert divergences[0].kind == "content"
        assert "LAPTOP body" in divergences[0].on_disk
        assert "DESKTOP body" in divergences[0].in_db

    def test_record_absent_from_db_is_reported(self, db, temp_dir):
        """A peer's new seed arriving via git pull, before any import ran."""
        db.create_seed(Seed(id="seed-a", title="A", content="mine"))
        path = _write_records(
            temp_dir / "out.jsonl",
            [_record("seed-a", "mine"), _record("seed-peer", "theirs")],
        )

        divergences = find_divergence(db, path)
        assert [d.seed_id for d in divergences] == ["seed-peer"]
        assert divergences[0].kind == "missing"

    def test_unparseable_line_is_reported_not_raised(self, db, temp_dir):
        """Conflict markers must refuse the overwrite, not crash the export."""
        path = temp_dir / "out.jsonl"
        path.write_text("<<<<<<< HEAD\n")

        divergences = find_divergence(db, path)
        assert len(divergences) == 1
        assert divergences[0].kind == "unreadable"
        assert "line 1" in divergences[0].detail

    def test_record_without_id_is_reported(self, db, temp_dir):
        path = temp_dir / "out.jsonl"
        path.write_text('{"title": "no id here"}\n')

        divergences = find_divergence(db, path)
        assert len(divergences) == 1
        assert divergences[0].kind == "unreadable"

    def test_duplicate_ids_are_judged_line_by_line(self, db, temp_dir):
        """A botched merge can leave two lines for one seed; check both."""
        db.create_seed(Seed(id="seed-a", title="A", content="kept"))
        path = _write_records(
            temp_dir / "out.jsonl",
            [_record("seed-a", "kept"), _record("seed-a", "the other side")],
        )

        divergences = find_divergence(db, path)
        assert len(divergences) == 1
        assert divergences[0].kind == "content"

    def test_blank_lines_are_ignored(self, db, temp_dir):
        db.create_seed(Seed(id="seed-a", title="A", content="body"))
        path = export_to_jsonl(db, temp_dir / "out.jsonl")
        path.write_text(path.read_text() + "\n\n")
        assert find_divergence(db, path) == []

    def test_detection_ignores_updated_at_when_file_is_older(self, db, temp_dir):
        """Divergence is a CONTENT question; the file's timestamp is irrelevant."""
        db.create_seed(Seed(id="seed-a", title="A", content="DESKTOP body"))
        old = now_utc() - timedelta(days=365)
        path = _write_records(
            temp_dir / "out.jsonl", [_record("seed-a", "LAPTOP body", updated_at=old)]
        )
        assert [d.kind for d in find_divergence(db, path)] == ["content"]

    def test_detection_ignores_updated_at_when_file_is_newer(self, db, temp_dir):
        """Same divergence, opposite timestamp ordering, same refusal."""
        db.create_seed(Seed(id="seed-a", title="A", content="DESKTOP body"))
        newer = now_utc() + timedelta(minutes=1)
        path = _write_records(
            temp_dir / "out.jsonl",
            [_record("seed-a", "LAPTOP body", updated_at=newer)],
        )
        assert [d.kind for d in find_divergence(db, path)] == ["content"]

    def test_title_and_tag_changes_are_not_divergence(self, db, temp_dir):
        """Replacement is the normal verb for working state; only body is guarded."""
        db.create_seed(Seed(id="seed-a", title="A", content="body", tags=["x"]))
        path = _write_records(
            temp_dir / "out.jsonl",
            [_record("seed-a", "body", title="a different title", tags=["y", "z"])],
        )
        assert find_divergence(db, path) == []


class TestExportRefusesDivergence:
    """`export_to_jsonl` must not destroy what the database never accounted for."""

    def test_export_refuses_and_leaves_file_byte_identical(self, db, temp_dir):
        db.create_seed(Seed(id="seed-a", title="A", content="DESKTOP body"))
        path = _write_records(
            temp_dir / "out.jsonl", [_record("seed-a", "LAPTOP body")]
        )
        before = path.read_bytes()

        with pytest.raises(DivergentExportError) as excinfo:
            export_to_jsonl(db, path)

        assert path.read_bytes() == before
        assert [d.seed_id for d in excinfo.value.divergences] == ["seed-a"]
        assert excinfo.value.output_path == path

    def test_export_refuses_to_delete_a_record_absent_from_the_db(self, db, temp_dir):
        db.create_seed(Seed(id="seed-a", title="A", content="mine"))
        path = _write_records(
            temp_dir / "out.jsonl",
            [_record("seed-a", "mine"), _record("seed-peer", "theirs")],
        )
        before = path.read_bytes()

        with pytest.raises(DivergentExportError):
            export_to_jsonl(db, path)
        assert path.read_bytes() == before

    def test_allow_divergence_permits_the_overwrite(self, db, temp_dir):
        db.create_seed(Seed(id="seed-a", title="A", content="DESKTOP body"))
        path = _write_records(
            temp_dir / "out.jsonl", [_record("seed-a", "LAPTOP body")]
        )

        export_to_jsonl(db, path, allow_divergence=True)

        records = [json.loads(line) for line in path.read_text().splitlines()]
        assert [r["content"] for r in records] == ["DESKTOP body"]

    def test_normal_flush_after_append_still_succeeds(self, db, temp_dir):
        """The everyday case: export, append, export again. No refusal."""
        seed = Seed(id="seed-a", title="A", content="original")
        db.create_seed(seed)
        path = export_to_jsonl(db, temp_dir / "out.jsonl")

        seed.content = "original\n\nappended"
        db.update_seed(seed)
        export_to_jsonl(db, path)

        records = [json.loads(line) for line in path.read_text().splitlines()]
        assert records[0]["content"] == "original\n\nappended"

    def test_full_roundtrip_on_multi_seed_db_is_a_noop(self, db, temp_dir):
        """export -> import -> export over an untouched file must not trip."""
        for i in range(5):
            db.create_seed(Seed(id=f"seed-{i}", title=f"T{i}", content=f"body {i}"))
        db.create_relationship("seed-0", "seed-1", RelationType.RELATES_TO)
        path = export_to_jsonl(db, temp_dir / "out.jsonl")
        first = path.read_bytes()

        result = import_from_jsonl(db, path)
        assert result.updated == 0
        assert result.refused == []

        export_to_jsonl(db, path)
        assert path.read_bytes() == first

    def test_refused_import_record_is_not_then_erased_by_the_export(self, db, temp_dir):
        """The seam with seeds-agk.1: a refused record stays refused, and stays.

        `import_records` declines a future-dated record outright, so nothing
        about it reaches the DB. Without the divergence guard the very next
        export would delete it from the file, quietly undoing the refusal.
        """
        db.create_seed(Seed(id="seed-a", title="A", content="mine"))
        far_future = now_utc() + FUTURE_TIMESTAMP_TOLERANCE + timedelta(hours=1)
        path = _write_records(
            temp_dir / "out.jsonl",
            [
                _record("seed-a", "mine"),
                _record("seed-poison", "theirs", updated_at=far_future),
            ],
        )

        result = import_from_jsonl(db, path)
        assert [r.seed_id for r in result.refused] == ["seed-poison"]

        with pytest.raises(DivergentExportError) as excinfo:
            export_to_jsonl(db, path)
        assert [d.seed_id for d in excinfo.value.divergences] == ["seed-poison"]
        assert "seed-poison" in path.read_text()


class TestImportV1:
    """Tests for importing v1 format JSONL (legacy with embedded questions)."""

    def test_import_v1_basic(self, db, temp_dir):
        """Verify v1 seed imports correctly."""
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "id": "seed-import",
            "title": "Imported Seed",
            "content": "Imported content",
            "status": "captured",
            "seed_type": "idea",
            "tags": ["imported"],
            "related_to": [],
            "created_at": now,
            "updated_at": now,
            "resolved_at": None,
            "questions": [],
        }

        input_path = temp_dir / "import.jsonl"
        input_path.write_text(json.dumps(data) + "\n")

        result = import_from_jsonl(db, input_path)
        assert result.created == 1
        assert result.updated == 0
        assert result.skipped == 0

        seed = db.get_seed("seed-import")
        assert seed is not None
        assert seed.title == "Imported Seed"
        assert seed.tags == ["imported"]

    def test_import_v1_with_related_to(self, db, temp_dir):
        """Verify v1 related_to arrays create relationships."""
        now = datetime.now(timezone.utc).isoformat()
        data_a = {
            "id": "seed-a",
            "title": "A",
            "content": "",
            "status": "captured",
            "seed_type": "idea",
            "tags": [],
            "related_to": ["seed-b"],
            "created_at": now,
            "updated_at": now,
            "resolved_at": None,
            "questions": [],
        }
        data_b = {
            "id": "seed-b",
            "title": "B",
            "content": "",
            "status": "captured",
            "seed_type": "idea",
            "tags": [],
            "related_to": [],
            "created_at": now,
            "updated_at": now,
            "resolved_at": None,
            "questions": [],
        }

        input_path = temp_dir / "import.jsonl"
        input_path.write_text(json.dumps(data_a) + "\n" + json.dumps(data_b) + "\n")

        result = import_from_jsonl(db, input_path)
        assert result.created == 2

        # Check relationship was created
        rels = db.get_relationships("seed-a", rel_type=RelationType.RELATES_TO)
        assert len(rels) == 2  # Bidirectional

    def test_import_v1_with_questions(self, db, temp_dir):
        """Verify v1 embedded questions become question-seeds with relationships."""
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "id": "seed-parent",
            "title": "Parent",
            "content": "",
            "status": "exploring",
            "seed_type": "idea",
            "tags": [],
            "related_to": [],
            "created_at": now,
            "updated_at": now,
            "resolved_at": None,
            "questions": [
                {
                    "id": "q-1",
                    "text": "Open question?",
                    "answer": None,
                    "status": "open",
                    "created_at": now,
                    "answered_at": None,
                },
                {
                    "id": "q-2",
                    "text": "Answered?",
                    "answer": "Yes",
                    "status": "answered",
                    "created_at": now,
                    "answered_at": now,
                },
            ],
        }

        input_path = temp_dir / "import.jsonl"
        input_path.write_text(json.dumps(data) + "\n")

        result = import_from_jsonl(db, input_path)
        assert result.created == 1

        # Question-seeds should have been created
        q_seeds = db.get_questions_for_seed("seed-parent")
        assert len(q_seeds) == 2

        statuses = {qs.title: qs.status for qs in q_seeds}
        assert statuses["Open question?"] == SeedStatus.CAPTURED
        assert statuses["Answered?"] == SeedStatus.RESOLVED


class TestImportV2:
    """Tests for importing v2 format JSONL (relationships as outbound edges)."""

    def test_import_v2_basic(self, db, temp_dir):
        """Verify v2 seed imports correctly."""
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "format_version": 2,
            "id": "seed-v2",
            "title": "V2 Seed",
            "content": "Content",
            "status": "captured",
            "seed_type": "idea",
            "tags": ["v2"],
            "created_at": now,
            "updated_at": now,
            "resolved_at": None,
            "relationships": [],
        }

        input_path = temp_dir / "import.jsonl"
        input_path.write_text(json.dumps(data) + "\n")

        result = import_from_jsonl(db, input_path)
        assert result.created == 1

        seed = db.get_seed("seed-v2")
        assert seed is not None
        assert seed.title == "V2 Seed"

    def test_import_v2_with_relationships(self, db, temp_dir):
        """Verify v2 relationships are created correctly."""
        now = datetime.now(timezone.utc).isoformat()
        data_a = {
            "format_version": 2,
            "id": "seed-a",
            "title": "A",
            "content": "",
            "status": "captured",
            "seed_type": "idea",
            "tags": [],
            "created_at": now,
            "updated_at": now,
            "resolved_at": None,
            "relationships": [
                {"target_id": "seed-b", "rel_type": "relates-to", "created_at": now},
            ],
        }
        data_b = {
            "format_version": 2,
            "id": "seed-b",
            "title": "B",
            "content": "",
            "status": "captured",
            "seed_type": "idea",
            "tags": [],
            "created_at": now,
            "updated_at": now,
            "resolved_at": None,
            "relationships": [
                {"target_id": "seed-a", "rel_type": "relates-to", "created_at": now},
            ],
        }

        input_path = temp_dir / "import.jsonl"
        input_path.write_text(json.dumps(data_a) + "\n" + json.dumps(data_b) + "\n")

        result = import_from_jsonl(db, input_path)
        assert result.created == 2

        rels = db.get_relationships("seed-a", rel_type=RelationType.RELATES_TO)
        assert len(rels) == 2  # Bidirectional


class TestImportGeneral:
    """Tests for import edge cases."""

    def test_import_nonexistent_file(self, db, temp_dir):
        """Verify import returns an empty result for a nonexistent file."""
        input_path = temp_dir / "nonexistent.jsonl"
        result = import_from_jsonl(db, input_path)
        assert result.total == 0

    def test_import_empty_file(self, db, temp_dir):
        """Verify import handles empty file."""
        input_path = temp_dir / "empty.jsonl"
        input_path.write_text("")

        result = import_from_jsonl(db, input_path)
        assert result.total == 0

    def test_import_skips_stale_existing_seeds(self, db, temp_dir, sample_seed):
        """A record whose updated_at is not newer than the DB's is skipped.

        ``sample_seed`` has no explicit timestamps, so create_seed stamps it at
        import-of-the-fixture time; the JSONL record's older updated_at must NOT
        clobber it (last-write-wins).
        """
        db.create_seed(sample_seed)
        db_seed = db.get_seed(sample_seed.id)

        stale = (db_seed.updated_at - timedelta(hours=1)).isoformat()
        data = {
            "format_version": 2,
            "id": sample_seed.id,
            "title": "Should Not Import",
            "content": "",
            "status": "captured",
            "seed_type": "idea",
            "tags": [],
            "created_at": stale,
            "updated_at": stale,
            "resolved_at": None,
            "relationships": [],
        }

        input_path = temp_dir / "import.jsonl"
        input_path.write_text(json.dumps(data) + "\n")

        result = import_from_jsonl(db, input_path)
        assert result.created == 0
        assert result.updated == 0
        assert result.skipped == 1

        seed = db.get_seed(sample_seed.id)
        assert seed.title == sample_seed.title  # Original preserved

    def test_import_skips_blank_lines(self, db, temp_dir):
        """Verify import skips blank lines in JSONL file."""
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "format_version": 2,
            "id": "seed-blank",
            "title": "After Blank Lines",
            "content": "",
            "status": "captured",
            "seed_type": "idea",
            "tags": [],
            "created_at": now,
            "updated_at": now,
            "resolved_at": None,
            "relationships": [],
        }
        input_path = temp_dir / "blanks.jsonl"
        input_path.write_text("\n\n" + json.dumps(data) + "\n\n")

        result = import_from_jsonl(db, input_path)
        assert result.created == 1

    def test_import_mixed_v1_and_v2_in_one_file(self, db, temp_dir):
        """A single file may interleave legacy v1 and v2 records.

        Format is detected per record (``format_version: 2`` -> v2, anything
        else -> legacy v1), so a v1 record (``related_to``/``questions``) and a
        v2 record (``relationships``) in the same file each import via their own
        code path.
        """
        now = datetime.now(timezone.utc).isoformat()
        v1 = {
            "id": "seed-v1",
            "title": "Legacy",
            "content": "",
            "status": "captured",
            "seed_type": "idea",
            "tags": [],
            "related_to": [],
            "created_at": now,
            "updated_at": now,
            "resolved_at": None,
            "questions": [],
        }
        v2 = {
            "format_version": 2,
            "id": "seed-v2",
            "title": "Modern",
            "content": "",
            "status": "captured",
            "seed_type": "idea",
            "tags": [],
            "created_at": now,
            "updated_at": now,
            "resolved_at": None,
            "relationships": [],
        }

        input_path = temp_dir / "mixed.jsonl"
        input_path.write_text(json.dumps(v1) + "\n" + json.dumps(v2) + "\n")

        result = import_from_jsonl(db, input_path)
        assert result.created == 2

        assert db.get_seed("seed-v1").title == "Legacy"
        assert db.get_seed("seed-v2").title == "Modern"


class TestImportDefaultPath:
    """Tests for import using default path."""

    def test_import_default_path(self, db, temp_dir):
        """Verify import uses default JSONL path when none specified."""
        import os

        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            seeds_dir = temp_dir / ".seeds"
            seeds_dir.mkdir(exist_ok=True)
            now = datetime.now(timezone.utc).isoformat()
            data = {
                "format_version": 2,
                "id": "seed-default",
                "title": "Default Path Seed",
                "content": "",
                "status": "captured",
                "seed_type": "idea",
                "tags": [],
                "created_at": now,
                "updated_at": now,
                "resolved_at": None,
                "relationships": [],
            }
            jsonl_path = seeds_dir / "seeds.jsonl"
            jsonl_path.write_text(json.dumps(data) + "\n")

            result = import_from_jsonl(db)
            assert result.created == 1

            seed = db.get_seed("seed-default")
            assert seed is not None
            assert seed.title == "Default Path Seed"
        finally:
            os.chdir(original_cwd)


class TestArbitrarySeedType:
    """A seed_type outside the standard five must survive sync (bead seeds-0lb)."""

    def test_unrecognized_type_imports_and_does_not_block_later_records(
        self, db, tmp_path
    ):
        """Mark Danese's exact case (seed seeds-1x6b).

        An agent wrote a 'context' seed_type into the JSONL. Every import
        raised on it, so not only was that record lost -- every record after
        it in the file never imported either, silently, for five weeks.
        """
        jsonl = tmp_path / "seeds.jsonl"
        records = [
            {
                "format_version": 2,
                "id": "seed-1",
                "title": "Ordinary seed",
                "content": "",
                "status": "captured",
                "seed_type": "idea",
                "tags": [],
                "created_at": "2026-08-01T00:00:00+00:00",
                "updated_at": "2026-08-01T00:00:00+00:00",
                "relationships": [],
            },
            {
                "format_version": 2,
                "id": "seed-2",
                "title": "Type an agent invented",
                "content": "",
                "status": "captured",
                "seed_type": "context",
                "tags": [],
                "created_at": "2026-08-01T00:00:00+00:00",
                "updated_at": "2026-08-01T00:00:00+00:00",
                "relationships": [],
            },
            {
                "format_version": 2,
                "id": "seed-3",
                "title": "Filed AFTER the bad record",
                "content": "",
                "status": "captured",
                "seed_type": "idea",
                "tags": [],
                "created_at": "2026-08-02T00:00:00+00:00",
                "updated_at": "2026-08-02T00:00:00+00:00",
                "relationships": [],
            },
        ]
        jsonl.write_text("\n".join(json.dumps(r) for r in records) + "\n")

        result = import_from_jsonl(db, jsonl)

        assert result.created == 3
        assert db.get_seed("seed-2").seed_type == "context"
        # The point of the regression: the record after the bad one landed.
        assert db.get_seed("seed-3") is not None

    def test_arbitrary_type_survives_export_import(self, db, tmp_path):
        """Full round trip, since the export side writes the type too."""
        db.create_seed(Seed(id="seed-1", title="Context", seed_type="context"))
        out = export_to_jsonl(db, tmp_path / "seeds.jsonl")

        db2 = Database(path=tmp_path / "other.db")
        import_from_jsonl(db2, out, bootstrap=True)
        assert db2.get_seed("seed-1").seed_type == "context"
        db2.close()


class TestRoundTrip:
    """Tests for export -> import round trip."""

    def test_roundtrip_preserves_data(self, temp_dir):
        """Verify export -> import preserves all data."""
        # Create first database and populate
        db1_path = temp_dir / "db1" / ".seeds" / "seeds.db"
        db1 = Database(path=db1_path)
        db1.init()

        seed = Seed(
            id="seed-roundtrip",
            title="Roundtrip Test",
            content="Full content",
            status=SeedStatus.EXPLORING,
            seed_type=SeedType.DECISION,
            tags=["test", "roundtrip"],
        )
        db1.create_seed(seed)

        other = Seed(id="seed-other", title="Other seed")
        db1.create_seed(other)
        db1.create_relationship("seed-roundtrip", "seed-other", RelationType.RELATES_TO)

        # Create a question-seed with relationship
        q_seed = Seed(
            id="seeds-qrt",
            title="Does this work?",
            content="Yes",
            seed_type=SeedType.QUESTION,
            status=SeedStatus.RESOLVED,
        )
        db1.create_seed(q_seed)
        db1.create_relationship("seeds-qrt", "seed-roundtrip", RelationType.QUESTIONS)

        # Export
        export_path = temp_dir / "roundtrip.jsonl"
        export_to_jsonl(db1, export_path)
        db1.close()

        # Create second database and import
        db2_path = temp_dir / "db2" / ".seeds" / "seeds.db"
        db2 = Database(path=db2_path)
        db2.init()

        result = import_from_jsonl(db2, export_path)
        assert result.created == 3  # seed-roundtrip, seed-other, seeds-qrt

        # Verify seed data
        imported_seed = db2.get_seed("seed-roundtrip")
        assert imported_seed.title == "Roundtrip Test"
        assert imported_seed.content == "Full content"
        assert imported_seed.status == SeedStatus.EXPLORING
        assert imported_seed.seed_type == SeedType.DECISION
        assert imported_seed.tags == ["test", "roundtrip"]

        # Verify relationships roundtripped
        rels = db2.get_relationships(
            "seed-roundtrip", rel_type=RelationType.RELATES_TO, direction="outbound"
        )
        assert len(rels) == 1
        assert rels[0].target_id == "seed-other"

        # Verify question-seed roundtripped
        q_seeds = db2.get_questions_for_seed("seed-roundtrip")
        assert len(q_seeds) == 1
        assert q_seeds[0].title == "Does this work?"
        assert q_seeds[0].content == "Yes"

        db2.close()

    def test_roundtrip_preserves_resolution(self, temp_dir):
        """Verify export -> import preserves resolution field."""
        db1_path = temp_dir / "db1" / ".seeds" / "seeds.db"
        db1 = Database(path=db1_path)
        db1.init()

        seed = Seed(
            id="seed-res",
            title="Resolved Seed",
            status=SeedStatus.RESOLVED,
            resolution="Shipped in PR #42",
        )
        db1.create_seed(seed)

        export_path = temp_dir / "roundtrip-res.jsonl"
        export_to_jsonl(db1, export_path)
        db1.close()

        db2_path = temp_dir / "db2" / ".seeds" / "seeds.db"
        db2 = Database(path=db2_path)
        db2.init()

        result = import_from_jsonl(db2, export_path)
        assert result.created == 1

        imported = db2.get_seed("seed-res")
        assert imported.resolution == "Shipped in PR #42"
        assert imported.status == SeedStatus.RESOLVED
        db2.close()


def _v2_record(seed_id, *, title, updated_at, relationships=None, **extra):
    """Build a minimal v2 JSONL record dict for import tests."""
    ts = updated_at if isinstance(updated_at, str) else updated_at.isoformat()
    record = {
        "format_version": 2,
        "id": seed_id,
        "title": title,
        "content": "",
        "status": "captured",
        "seed_type": "idea",
        "tags": [],
        "created_at": ts,
        "updated_at": ts,
        "resolved_at": None,
        "relationships": relationships or [],
    }
    record.update(extra)
    return record


class TestImportLastWriteWins:
    """Acceptance criteria for the v2 upsert / last-write-wins import path."""

    def test_reimport_is_full_noop(self, temp_dir):
        """Re-importing the same JSONL skips every record (no creates/updates)."""
        db1 = Database(path=temp_dir / "db1" / ".seeds" / "seeds.db")
        db1.init()
        db1.create_seed(Seed(id="seed-a", title="A"))
        db1.create_seed(Seed(id="seed-b", title="B"))
        db1.create_relationship("seed-a", "seed-b", RelationType.RELATES_TO)
        export_path = temp_dir / "rt.jsonl"
        export_to_jsonl(db1, export_path)
        db1.close()

        db2 = Database(path=temp_dir / "db2" / ".seeds" / "seeds.db")
        db2.init()

        first = import_from_jsonl(db2, export_path)
        assert first.created == 2
        assert first.updated == 0
        assert first.skipped == 0

        # Second import of the identical file: equal updated_at -> all skipped.
        second = import_from_jsonl(db2, export_path)
        assert second.created == 0
        assert second.updated == 0
        assert second.skipped == 2
        db2.close()

    def test_newer_updated_at_overwrites(self, db, temp_dir):
        """A record with a newer updated_at overwrites the existing seed."""
        base = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        db.create_seed(
            Seed(id="seed-x", title="Old title", created_at=base, updated_at=base)
        )

        newer = (base + timedelta(days=1)).isoformat()
        record = _v2_record(
            "seed-x", title="New title", updated_at=newer, content="updated body"
        )
        input_path = temp_dir / "newer.jsonl"
        input_path.write_text(json.dumps(record) + "\n")

        result = import_from_jsonl(db, input_path)
        assert result.created == 0
        assert result.updated == 1
        assert result.skipped == 0

        seed = db.get_seed("seed-x")
        assert seed.title == "New title"
        assert seed.content == "updated body"
        # updated_at is written verbatim from the JSONL (touch=False), not bumped.
        assert seed.updated_at == datetime.fromisoformat(newer)

    def test_stale_updated_at_does_not_clobber(self, db, temp_dir):
        """A record older than the DB row leaves the DB row untouched."""
        fresh = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        db.create_seed(
            Seed(id="seed-y", title="Fresh title", created_at=fresh, updated_at=fresh)
        )

        stale = (fresh - timedelta(days=10)).isoformat()
        record = _v2_record("seed-y", title="Stale title", updated_at=stale)
        input_path = temp_dir / "stale.jsonl"
        input_path.write_text(json.dumps(record) + "\n")

        result = import_from_jsonl(db, input_path)
        assert result.skipped == 1
        assert result.updated == 0

        seed = db.get_seed("seed-y")
        assert seed.title == "Fresh title"
        assert seed.updated_at == fresh

    def test_equal_updated_at_is_skipped(self, db, temp_dir):
        """Equal updated_at is not 'newer' — the record is skipped, not updated."""
        ts = datetime(2025, 3, 3, 9, 0, 0, tzinfo=timezone.utc)
        db.create_seed(
            Seed(id="seed-z", title="Original", created_at=ts, updated_at=ts)
        )

        record = _v2_record("seed-z", title="Changed", updated_at=ts.isoformat())
        input_path = temp_dir / "equal.jsonl"
        input_path.write_text(json.dumps(record) + "\n")

        result = import_from_jsonl(db, input_path)
        assert result.skipped == 1
        assert db.get_seed("seed-z").title == "Original"

    def test_relationships_not_duplicated_on_reimport(self, db, temp_dir):
        """Re-importing does not duplicate relationship edges."""
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat()
        rec_a = _v2_record(
            "seed-a",
            title="A",
            updated_at=ts,
            relationships=[
                {"target_id": "seed-b", "rel_type": "relates-to", "created_at": ts}
            ],
        )
        rec_b = _v2_record(
            "seed-b",
            title="B",
            updated_at=ts,
            relationships=[
                {"target_id": "seed-a", "rel_type": "relates-to", "created_at": ts}
            ],
        )
        input_path = temp_dir / "rels.jsonl"
        input_path.write_text(json.dumps(rec_a) + "\n" + json.dumps(rec_b) + "\n")

        import_from_jsonl(db, input_path)
        import_from_jsonl(db, input_path)  # re-import

        rels = db.get_relationships(
            "seed-a", rel_type=RelationType.RELATES_TO, direction="outbound"
        )
        assert len(rels) == 1  # not duplicated despite two imports

    def test_skipped_stale_seed_still_backfills_missing_edge(self, db, temp_dir):
        """A record skipped as stale still asserts its (missing) relationships.

        ``_import_v2_record`` re-asserts edges in every branch, so even when the
        seed itself is left untouched (DB row as-fresh-or-fresher), an edge the
        DB is missing gets backfilled. Here the DB seed is fresh (so the record
        is skipped) but carries no relationship; the stale record names one,
        which must still be created.
        """
        fresh = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        # seed-a is fresh in the DB and has NO outbound edge yet.
        db.create_seed(Seed(id="seed-a", title="A", created_at=fresh, updated_at=fresh))
        # seed-b exists so the edge has a target (no FK, but keep it realistic).
        db.create_seed(Seed(id="seed-b", title="B"))

        assert db.get_relationships("seed-a", direction="outbound") == []

        stale = (fresh - timedelta(days=5)).isoformat()
        record = _v2_record(
            "seed-a",
            title="Stale A",
            updated_at=stale,
            relationships=[
                {"target_id": "seed-b", "rel_type": "relates-to", "created_at": stale}
            ],
        )
        input_path = temp_dir / "backfill.jsonl"
        input_path.write_text(json.dumps(record) + "\n")

        result = import_from_jsonl(db, input_path)

        # The seed row is stale -> skipped (title untouched)...
        assert result.skipped == 1
        assert result.updated == 0
        assert db.get_seed("seed-a").title == "A"

        # ...yet the missing edge was backfilled.
        rels = db.get_relationships(
            "seed-a", rel_type=RelationType.RELATES_TO, direction="outbound"
        )
        assert len(rels) == 1
        assert rels[0].target_id == "seed-b"

    def test_import_lines_accepts_iterable(self, db):
        """import_lines consumes an arbitrary iterable of JSONL lines (stdin seam)."""
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat()
        lines = [
            "",  # blank lines ignored
            json.dumps(_v2_record("seed-1", title="One", updated_at=ts)),
            json.dumps(_v2_record("seed-2", title="Two", updated_at=ts)),
        ]
        result = import_lines(db, iter(lines))
        assert result.created == 2
        assert db.get_seed("seed-1").title == "One"
        assert db.get_seed("seed-2").title == "Two"

    def test_import_result_total(self):
        """ImportResult.total sums created/updated/skipped/refused."""
        assert ImportResult(created=2, updated=1, skipped=3).total == 6
        assert ImportResult().total == 0
        assert (
            ImportResult(
                created=1,
                refused=[RefusedRecord("seed-x", "2030-01-01T00:00:00+00:00", "why")],
            ).total
            == 2
        )


class TestImportUntrustworthyTimestamps:
    """Import must not trust a record's ``updated_at`` blindly.

    Two defects covered here (bead seeds-agk.1):
    a future-dated record poisons a seed permanently, and a timezone-naive
    ``updated_at`` used to abort the import mid-file with a TypeError.
    """

    def test_future_dated_record_is_refused(self, db, temp_dir):
        """A record dated far in the future is refused; the DB row is unchanged."""
        base = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        db.create_seed(
            Seed(
                id="seed-f",
                title="Real title",
                content="real body",
                created_at=base,
                updated_at=base,
            )
        )

        forged = "2030-01-01T00:00:00+00:00"
        record = _v2_record(
            "seed-f", title="Forged title", updated_at=forged, content="POISON"
        )
        input_path = temp_dir / "future.jsonl"
        input_path.write_text(json.dumps(record) + "\n")

        result = import_from_jsonl(db, input_path)

        assert result.created == 0
        assert result.updated == 0
        assert result.skipped == 0
        assert len(result.refused) == 1
        # The refusal names the seed and quotes the timestamp the file claimed.
        assert result.refused[0].seed_id == "seed-f"
        assert result.refused[0].claimed_updated_at == forged

        seed = db.get_seed("seed-f")
        assert seed.title == "Real title"
        assert seed.content == "real body"
        assert seed.updated_at == base

    def test_future_dated_record_is_not_created(self, db, temp_dir):
        """A refused record with an unseen ID is not inserted either.

        Creating it would plant the poisoned timestamp rather than reject it.
        """
        record = _v2_record(
            "seed-new", title="From the future", updated_at="2030-01-01T00:00:00+00:00"
        )
        input_path = temp_dir / "future-new.jsonl"
        input_path.write_text(json.dumps(record) + "\n")

        result = import_from_jsonl(db, input_path)

        assert result.created == 0
        assert len(result.refused) == 1
        assert db.get_seed("seed-new") is None

    def test_refused_record_applies_nothing_not_even_edges(self, db, temp_dir):
        """A refused record's relationships are not asserted.

        Skipped records still backfill edges, but a refused record is untrusted
        wholesale — none of it reaches the DB.
        """
        db.create_seed(Seed(id="seed-a", title="A"))
        db.create_seed(Seed(id="seed-b", title="B"))

        record = _v2_record(
            "seed-a",
            title="A from the future",
            updated_at="2030-06-01T00:00:00+00:00",
            relationships=[
                {
                    "target_id": "seed-b",
                    "rel_type": "relates-to",
                    "created_at": "2030-06-01T00:00:00+00:00",
                }
            ],
        )
        input_path = temp_dir / "future-rel.jsonl"
        input_path.write_text(json.dumps(record) + "\n")

        result = import_from_jsonl(db, input_path)

        assert len(result.refused) == 1
        assert db.get_relationships("seed-a", direction="outbound") == []

    def test_future_dated_v1_record_is_refused(self, db, temp_dir):
        """The refusal is format-agnostic — legacy v1 records are checked too."""
        record = {
            "id": "seed-v1",
            "title": "Legacy from the future",
            "content": "",
            "status": "captured",
            "seed_type": "idea",
            "created_at": "2030-01-01T00:00:00+00:00",
            "updated_at": "2030-01-01T00:00:00+00:00",
            "related_to": [],
            "questions": [],
        }
        input_path = temp_dir / "v1-future.jsonl"
        input_path.write_text(json.dumps(record) + "\n")

        result = import_from_jsonl(db, input_path)

        assert result.created == 0
        assert len(result.refused) == 1
        assert db.get_seed("seed-v1") is None

    def test_poisoning_sequence_preserves_local_work(self, db, temp_dir):
        """The full reproduction: a local edit is no longer destroyed on re-import.

        Before the fix this sequence lost "MY REAL WORK": the forged 2030
        record won the comparison, and every later legitimate edit stamped
        ``now_utc()`` — earlier than 2030 — so the same unchanged file kept
        winning forever.
        """
        base = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        db.create_seed(
            Seed(
                id="seed-p",
                title="Seed P",
                content="original body",
                created_at=base,
                updated_at=base,
            )
        )

        forged = _v2_record(
            "seed-p",
            title="Seed P",
            updated_at="2030-01-01T00:00:00+00:00",
            content="POISONED BODY FROM THE FILE",
        )
        input_path = temp_dir / "poison.jsonl"
        input_path.write_text(json.dumps(forged) + "\n")

        # 1. The forged record is refused, so the body is never poisoned.
        first = import_from_jsonl(db, input_path)
        assert len(first.refused) == 1
        assert db.get_seed("seed-p").content == "original body"

        # 2. A legitimate local append lands in the DB.
        seed = db.get_seed("seed-p")
        seed.content = seed.content + "\n\nMY REAL WORK"
        db.update_seed(seed)
        assert "MY REAL WORK" in db.get_seed("seed-p").content

        # 3. Re-importing the SAME unchanged file leaves the append intact.
        second = import_from_jsonl(db, input_path)
        assert len(second.refused) == 1
        assert second.updated == 0
        assert "MY REAL WORK" in db.get_seed("seed-p").content
        assert "POISONED" not in db.get_seed("seed-p").content

    def test_tolerance_is_not_zero(self):
        """Clock skew is real; a zero tolerance would reject honest records."""
        assert FUTURE_TIMESTAMP_TOLERANCE.total_seconds() > 0

    def test_record_within_skew_tolerance_still_imports(self, db, temp_dir):
        """A slightly-ahead record (ordinary clock skew) imports normally."""
        db.create_seed(Seed(id="seed-s", title="Old", updated_at=now_utc()))

        slightly_ahead = now_utc() + FUTURE_TIMESTAMP_TOLERANCE / 2
        record = _v2_record(
            "seed-s", title="Slightly ahead", updated_at=slightly_ahead.isoformat()
        )
        input_path = temp_dir / "skew.jsonl"
        input_path.write_text(json.dumps(record) + "\n")

        result = import_from_jsonl(db, input_path)

        assert result.refused == []
        assert result.updated == 1
        assert db.get_seed("seed-s").title == "Slightly ahead"

    def test_naive_updated_at_does_not_abort_the_import(self, db, temp_dir):
        """A timezone-naive updated_at neither raises nor stops later records.

        Before the fix this raised
        ``TypeError: can't compare offset-naive and offset-aware datetimes``
        and left the import partially applied, with no summary.
        """
        base = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        for sid in ("seed-1", "seed-2", "seed-3"):
            db.create_seed(
                Seed(id=sid, title=f"old {sid}", created_at=base, updated_at=base)
            )

        newer = base + timedelta(days=1)
        records = [
            _v2_record("seed-1", title="new 1", updated_at=newer.isoformat()),
            # Middle record has no timezone offset at all.
            _v2_record(
                "seed-2",
                title="new 2",
                updated_at=newer.replace(tzinfo=None).isoformat(),
            ),
            _v2_record("seed-3", title="new 3", updated_at=newer.isoformat()),
        ]
        input_path = temp_dir / "naive.jsonl"
        input_path.write_text("".join(json.dumps(r) + "\n" for r in records))

        result = import_from_jsonl(db, input_path)

        # All three processed — including the one AFTER the naive record.
        assert result.total == 3
        assert result.updated == 3
        assert result.refused == []
        assert db.get_seed("seed-1").title == "new 1"
        assert db.get_seed("seed-2").title == "new 2"
        assert db.get_seed("seed-3").title == "new 3"

    def test_naive_updated_at_is_read_as_utc(self, db, temp_dir):
        """Naive input is interpreted as UTC, matching ``parse_since``.

        The naive value here equals the DB's UTC timestamp, so reading it as
        UTC makes it not-newer and the record is skipped — the same outcome an
        explicit ``+00:00`` would produce.
        """
        ts = datetime(2025, 3, 3, 9, 0, 0, tzinfo=timezone.utc)
        db.create_seed(
            Seed(id="seed-n", title="Original", created_at=ts, updated_at=ts)
        )

        record = _v2_record(
            "seed-n", title="Changed", updated_at=ts.replace(tzinfo=None).isoformat()
        )
        input_path = temp_dir / "naive-equal.jsonl"
        input_path.write_text(json.dumps(record) + "\n")

        result = import_from_jsonl(db, input_path)

        assert result.skipped == 1
        assert result.updated == 0
        assert db.get_seed("seed-n").title == "Original"

    def test_naive_stored_timestamp_is_normalized_to_utc(self, db, temp_dir):
        """A naive record that wins is stored timezone-aware, not naive."""
        base = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        db.create_seed(Seed(id="seed-w", title="Old", created_at=base, updated_at=base))

        newer = base + timedelta(days=2)
        record = _v2_record(
            "seed-w", title="New", updated_at=newer.replace(tzinfo=None).isoformat()
        )
        input_path = temp_dir / "naive-newer.jsonl"
        input_path.write_text(json.dumps(record) + "\n")

        result = import_from_jsonl(db, input_path)

        assert result.updated == 1
        stored = db.get_seed("seed-w")
        assert stored.title == "New"
        assert stored.updated_at == newer
        assert stored.updated_at.tzinfo is not None

    def test_normal_import_reports_no_refusals(self, db, temp_dir):
        """Well-formed records are unaffected: nothing refused, counts unchanged."""
        db2 = Database(path=temp_dir / "src" / ".seeds" / "seeds.db")
        db2.init()
        db2.create_seed(Seed(id="seed-a", title="A"))
        db2.create_seed(Seed(id="seed-b", title="B"))
        db2.create_relationship("seed-a", "seed-b", RelationType.RELATES_TO)
        export_path = temp_dir / "clean.jsonl"
        export_to_jsonl(db2, export_path)

        result = import_from_jsonl(db, export_path)

        assert result.refused == []
        assert result.created == 2
        assert result.total == 2


class TestImportBootstrap:
    """Fresh-clone bootstrap: import into a directory with only seeds.jsonl."""

    def _write_jsonl(self, path, records):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(r) + "\n" for r in records))

    def test_bootstrap_creates_db_and_recovers_prefix(self, temp_dir):
        """Import into a dir with only seeds.jsonl builds a populated DB.

        The DB file is absent (gitignored on a fresh clone) and the prefix
        lives only in the gitignored DB config. bootstrap=True must create the
        schema and recover the prefix ('seeds') from the first record's ID.
        """
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat()
        seeds_dir = temp_dir / ".seeds"
        jsonl_path = seeds_dir / "seeds.jsonl"
        self._write_jsonl(
            jsonl_path,
            [
                _v2_record("seeds-155", title="First", updated_at=ts),
                _v2_record("seeds-156", title="Second", updated_at=ts),
            ],
        )

        db_path = seeds_dir / "seeds.db"
        assert not db_path.exists()

        db = Database(path=db_path)
        result = import_from_jsonl(db, jsonl_path, bootstrap=True)

        assert result.created == 2
        assert db_path.exists()
        assert db.is_initialized()
        assert db.get_prefix() == "seeds"
        assert db.has_prefix_configured() is True
        assert db.get_seed("seeds-155").title == "First"
        assert db.get_seed("seeds-156").title == "Second"
        db.close()

    def test_bootstrap_next_id_avoids_imported_ids(self, temp_dir):
        """After a bootstrap import, next_id mints hash IDs (seeds-mlj) that
        don't collide with the imported ones, using the recovered prefix."""
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat()
        jsonl_path = temp_dir / ".seeds" / "seeds.jsonl"
        self._write_jsonl(
            jsonl_path,
            [
                _v2_record("seeds-155", title="First", updated_at=ts),
                _v2_record("seeds-156", title="Second", updated_at=ts),
            ],
        )

        db = Database(path=temp_dir / ".seeds" / "seeds.db")
        import_from_jsonl(db, jsonl_path, bootstrap=True)

        # A subsequent jot avoids the imported IDs and uses the recovered
        # prefix; it does not reissue or renumber them.
        id1 = db.next_id()
        assert re.match(r"^seeds-[0-9a-z]{3,8}$", id1)
        assert id1 not in {"seeds-155", "seeds-156"}
        db.create_seed(Seed(id=id1, title="Third"))
        id2 = db.next_id()
        assert re.match(r"^seeds-[0-9a-z]{3,8}$", id2)
        assert id2 != id1
        db.close()

    def test_bootstrap_recovers_custom_prefix(self, temp_dir):
        """The recovered prefix is the JSONL's, not a directory-derived one."""
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat()
        jsonl_path = temp_dir / ".seeds" / "seeds.jsonl"
        self._write_jsonl(
            jsonl_path,
            [_v2_record("myproj-42", title="Only", updated_at=ts)],
        )

        db = Database(path=temp_dir / ".seeds" / "seeds.db")
        import_from_jsonl(db, jsonl_path, bootstrap=True)

        assert db.get_prefix() == "myproj"
        new_id = db.next_id()
        assert re.match(r"^myproj-[0-9a-z]{3,8}$", new_id)
        assert new_id != "myproj-42"
        db.close()

    def test_bootstrap_recovers_prefix_from_hash_ids(self, temp_dir):
        """Fresh-clone bootstrap recovers the prefix from a base36 hash-ID
        export (seeds-199), not just legacy sequential IDs. Regression guard:
        without this, hash-ID stores fall back to a wrong directory-derived
        prefix on fresh clone."""
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat()
        jsonl_path = temp_dir / ".seeds" / "seeds.jsonl"
        self._write_jsonl(
            jsonl_path,
            [_v2_record("myproj-k3n", title="Only", updated_at=ts)],
        )

        db = Database(path=temp_dir / ".seeds" / "seeds.db")
        import_from_jsonl(db, jsonl_path, bootstrap=True)

        assert db.get_prefix() == "myproj"
        new_id = db.next_id()
        assert re.match(r"^myproj-[0-9a-z]{3,8}$", new_id)
        db.close()

    def test_bootstrap_on_initialized_db_does_not_clobber_prefix(self, temp_dir):
        """An already-initialized DB keeps its prefix; bootstrap is a no-op there."""
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat()
        db_path = temp_dir / ".seeds" / "seeds.db"
        db = Database(path=db_path)
        db.init(prefix="existing")

        jsonl_path = temp_dir / ".seeds" / "seeds.jsonl"
        self._write_jsonl(
            jsonl_path,
            [_v2_record("seeds-155", title="First", updated_at=ts)],
        )

        result = import_from_jsonl(db, jsonl_path, bootstrap=True)

        assert result.created == 1
        # Prefix recovered from the JSONL must NOT overwrite the configured one.
        assert db.get_prefix() == "existing"
        assert db.get_seed("seeds-155").title == "First"
        db.close()

    def test_bootstrap_lines_seam(self, temp_dir):
        """import_lines also bootstraps when fed an iterable (stdin seam)."""
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat()
        lines = [
            json.dumps(_v2_record("seeds-7", title="One", updated_at=ts)),
            json.dumps(_v2_record("seeds-8", title="Two", updated_at=ts)),
        ]

        db = Database(path=temp_dir / ".seeds" / "seeds.db")
        result = import_lines(db, iter(lines), bootstrap=True)

        assert result.created == 2
        assert db.get_prefix() == "seeds"
        new_id = db.next_id()
        assert re.match(r"^seeds-[0-9a-z]{3,8}$", new_id)
        assert new_id not in {"seeds-7", "seeds-8"}
        db.close()

    def test_bootstrap_empty_jsonl_creates_db_without_prefix(self, temp_dir):
        """Bootstrap with no records still creates a usable DB (prefix unset)."""
        jsonl_path = temp_dir / ".seeds" / "seeds.jsonl"
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        jsonl_path.write_text("")

        db = Database(path=temp_dir / ".seeds" / "seeds.db")
        result = import_from_jsonl(db, jsonl_path, bootstrap=True)

        assert result.total == 0
        assert db.is_initialized()
        # No records to recover from -> prefix left unset (DEFAULT fallback).
        assert db.has_prefix_configured() is False
        db.close()

    def test_bootstrap_unrecoverable_first_id_leaves_prefix_unset(self, temp_dir):
        """A malformed first ID with no '<prefix>-<suffix>' shape can't yield a
        prefix; the DB still bootstraps with the prefix left unset."""
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat()
        jsonl_path = temp_dir / ".seeds" / "seeds.jsonl"
        self._write_jsonl(
            jsonl_path,
            [_v2_record("nohyphen", title="Malformed", updated_at=ts)],
        )

        db = Database(path=temp_dir / ".seeds" / "seeds.db")
        result = import_from_jsonl(db, jsonl_path, bootstrap=True)

        assert result.created == 1
        assert db.is_initialized()
        assert db.has_prefix_configured() is False
        assert db.get_seed("nohyphen").title == "Malformed"
        db.close()

    def test_no_bootstrap_skips_missing_file_without_creating_db(self, temp_dir):
        """Default bootstrap=False against a missing file does not create a DB.

        Confirms the default leaves existing behavior intact: a nonexistent
        JSONL yields an empty result and never touches the DB file.
        """
        db_path = temp_dir / ".seeds" / "seeds.db"
        db = Database(path=db_path)
        result = import_from_jsonl(db, temp_dir / ".seeds" / "missing.jsonl")
        assert result.total == 0
        assert not db_path.exists()
        db.close()
