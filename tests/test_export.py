"""Tests for seeds export/import functionality."""

import json
from datetime import datetime, timezone

from seeds.db import Database
from seeds.export import export_to_jsonl, import_from_jsonl, seed_to_dict
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

        # seed-test has outbound: relates-to seed-other, and inbound relates-to from other
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

        count = import_from_jsonl(db, input_path)
        assert count == 1

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

        count = import_from_jsonl(db, input_path)
        assert count == 2

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

        count = import_from_jsonl(db, input_path)
        assert count == 1

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

        count = import_from_jsonl(db, input_path)
        assert count == 1

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

        count = import_from_jsonl(db, input_path)
        assert count == 2

        rels = db.get_relationships("seed-a", rel_type=RelationType.RELATES_TO)
        assert len(rels) == 2  # Bidirectional


class TestImportGeneral:
    """Tests for import edge cases."""

    def test_import_nonexistent_file(self, db, temp_dir):
        """Verify import returns 0 for nonexistent file."""
        input_path = temp_dir / "nonexistent.jsonl"
        count = import_from_jsonl(db, input_path)
        assert count == 0

    def test_import_empty_file(self, db, temp_dir):
        """Verify import handles empty file."""
        input_path = temp_dir / "empty.jsonl"
        input_path.write_text("")

        count = import_from_jsonl(db, input_path)
        assert count == 0

    def test_import_skips_existing_seeds(self, db, temp_dir, sample_seed):
        """Verify import skips seeds that already exist."""
        db.create_seed(sample_seed)

        now = datetime.now(timezone.utc).isoformat()
        data = {
            "format_version": 2,
            "id": sample_seed.id,
            "title": "Should Not Import",
            "content": "",
            "status": "captured",
            "seed_type": "idea",
            "tags": [],
            "created_at": now,
            "updated_at": now,
            "resolved_at": None,
            "relationships": [],
        }

        input_path = temp_dir / "import.jsonl"
        input_path.write_text(json.dumps(data) + "\n")

        count = import_from_jsonl(db, input_path)
        assert count == 0

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

        count = import_from_jsonl(db, input_path)
        assert count == 1


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

            count = import_from_jsonl(db)
            assert count == 1

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

        count = import_from_jsonl(db2, export_path)
        assert count == 3  # seed-roundtrip, seed-other, seeds-qrt

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

        count = import_from_jsonl(db2, export_path)
        assert count == 1

        imported = db2.get_seed("seed-res")
        assert imported.resolution == "Shipped in PR #42"
        assert imported.status == SeedStatus.RESOLVED
        db2.close()
