"""Tests for seeds export/import functionality."""

import json
from datetime import datetime, timedelta, timezone

from seeds.db import Database
from seeds.export import (
    ImportResult,
    export_to_jsonl,
    import_from_jsonl,
    import_lines,
    seed_to_dict,
)
from seeds.models import (
    RelationType,
    Seed,
    SeedStatus,
    SeedType,
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
        """ImportResult.total sums created/updated/skipped."""
        assert ImportResult(created=2, updated=1, skipped=3).total == 6
        assert ImportResult().total == 0


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

    def test_bootstrap_next_id_continues_sequence(self, temp_dir):
        """After a bootstrap import, next_id continues the JSONL's sequence."""
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

        # A subsequent jot continues the sequence: max(155, 156) + 1 = 157,
        # and uses the recovered prefix.
        assert db.next_id() == "seeds-157"
        db.create_seed(Seed(id=db.next_id(), title="Third"))
        assert db.next_id() == "seeds-158"
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
        assert db.next_id() == "myproj-43"
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
        assert db.next_id() == "seeds-9"
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
        """A legacy hex-hash first ID can't yield a prefix; DB still bootstraps."""
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat()
        jsonl_path = temp_dir / ".seeds" / "seeds.jsonl"
        self._write_jsonl(
            jsonl_path,
            [_v2_record("seed-a1b2", title="Hex", updated_at=ts)],
        )

        db = Database(path=temp_dir / ".seeds" / "seeds.db")
        result = import_from_jsonl(db, jsonl_path, bootstrap=True)

        assert result.created == 1
        assert db.is_initialized()
        assert db.has_prefix_configured() is False
        assert db.get_seed("seed-a1b2").title == "Hex"
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
