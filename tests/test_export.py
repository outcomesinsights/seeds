"""Tests for seeds export/import functionality."""

import json
from datetime import datetime, timezone

from seeds.db import Database
from seeds.export import export_to_jsonl, import_from_jsonl, seed_to_dict
from seeds.models import (
    Question,
    QuestionStatus,
    Seed,
    SeedStatus,
    SeedType,
)


class TestSeedToDict:
    """Tests for seed_to_dict conversion."""

    def test_basic_seed_conversion(self):
        """Verify basic seed converts to dict correctly."""
        now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        seed = Seed(
            id="seed-test",
            title="Test Seed",
            content="Content here",
            status=SeedStatus.EXPLORING,
            seed_type=SeedType.IDEA,
            tags=["tag1", "tag2"],
            related_to=["seed-other"],
            created_at=now,
            updated_at=now,
        )

        result = seed_to_dict(seed, [])

        assert result["id"] == "seed-test"
        assert result["title"] == "Test Seed"
        assert result["content"] == "Content here"
        assert result["status"] == "exploring"
        assert result["seed_type"] == "idea"
        assert result["tags"] == ["tag1", "tag2"]
        assert result["related_to"] == ["seed-other"]
        assert result["created_at"] == "2025-01-15T12:00:00+00:00"
        assert result["resolved_at"] is None
        assert result["questions"] == []

    def test_seed_with_questions(self):
        """Verify questions are embedded in seed dict."""
        now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        seed = Seed(
            id="seed-test",
            title="Test Seed",
            created_at=now,
            updated_at=now,
        )
        questions = [
            Question(
                id="q-1",
                seed_id="seed-test",
                text="What is the answer?",
                status=QuestionStatus.OPEN,
                created_at=now,
            ),
            Question(
                id="q-2",
                seed_id="seed-test",
                text="Why?",
                answer="Because",
                status=QuestionStatus.ANSWERED,
                created_at=now,
                answered_at=now,
            ),
        ]

        result = seed_to_dict(seed, questions)

        assert len(result["questions"]) == 2
        assert result["questions"][0]["id"] == "q-1"
        assert result["questions"][0]["text"] == "What is the answer?"
        assert result["questions"][0]["status"] == "open"
        assert result["questions"][1]["id"] == "q-2"
        assert result["questions"][1]["answer"] == "Because"
        assert result["questions"][1]["status"] == "answered"


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

    def test_export_includes_questions(
        self, db, temp_dir, sample_seed, sample_question
    ):
        """Verify export includes questions embedded in seeds."""
        db.create_seed(sample_seed)
        db.create_question(sample_question)

        output_path = temp_dir / "output.jsonl"
        export_to_jsonl(db, output_path)

        data = json.loads(output_path.read_text().strip())
        assert len(data["questions"]) == 1
        assert data["questions"][0]["id"] == sample_question.id


class TestImportFromJsonl:
    """Tests for JSONL import."""

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

    def test_import_single_seed(self, db, temp_dir):
        """Verify single seed imports correctly."""
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

    def test_import_seed_with_questions(self, db, temp_dir):
        """Verify import creates questions."""
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "id": "seed-import",
            "title": "Seed with Questions",
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
                    "id": "q-import",
                    "text": "Imported question?",
                    "answer": None,
                    "status": "open",
                    "created_at": now,
                    "answered_at": None,
                }
            ],
        }

        input_path = temp_dir / "import.jsonl"
        input_path.write_text(json.dumps(data) + "\n")

        count = import_from_jsonl(db, input_path)
        assert count == 1

        questions = db.list_questions(seed_id="seed-import")
        assert len(questions) == 1
        assert questions[0].id == "q-import"
        assert questions[0].text == "Imported question?"

    def test_import_skips_existing_seeds(self, db, temp_dir, sample_seed):
        """Verify import skips seeds that already exist."""
        db.create_seed(sample_seed)

        now = datetime.now(timezone.utc).isoformat()
        data = {
            "id": sample_seed.id,  # Same ID as existing seed
            "title": "Should Not Import",
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
        input_path.write_text(json.dumps(data) + "\n")

        count = import_from_jsonl(db, input_path)
        assert count == 0  # Nothing imported

        seed = db.get_seed(sample_seed.id)
        assert seed.title == sample_seed.title  # Original title preserved


class TestImportDefaultPath:
    """Tests for import using default path."""

    def test_import_default_path(self, db, temp_dir):
        """Verify import uses default JSONL path when none specified."""
        import os

        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            # Create .seeds/seeds.jsonl at default location
            seeds_dir = temp_dir / ".seeds"
            seeds_dir.mkdir(exist_ok=True)
            now = datetime.now(timezone.utc).isoformat()
            data = {
                "id": "seed-default",
                "title": "Default Path Seed",
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
            jsonl_path = seeds_dir / "seeds.jsonl"
            jsonl_path.write_text(json.dumps(data) + "\n")

            count = import_from_jsonl(db)
            assert count == 1

            seed = db.get_seed("seed-default")
            assert seed is not None
            assert seed.title == "Default Path Seed"
        finally:
            os.chdir(original_cwd)

    def test_import_skips_blank_lines(self, db, temp_dir):
        """Verify import skips blank lines in JSONL file."""
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "id": "seed-blank",
            "title": "After Blank Lines",
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
        input_path = temp_dir / "blanks.jsonl"
        input_path.write_text("\n\n" + json.dumps(data) + "\n\n")

        count = import_from_jsonl(db, input_path)
        assert count == 1


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
            related_to=["seed-other"],
        )
        db1.create_seed(seed)

        question = Question(
            id="q-roundtrip",
            seed_id="seed-roundtrip",
            text="Does this work?",
            answer="Yes",
            status=QuestionStatus.ANSWERED,
        )
        db1.create_question(question)

        # Export
        export_path = temp_dir / "roundtrip.jsonl"
        export_to_jsonl(db1, export_path)
        db1.close()

        # Create second database and import
        db2_path = temp_dir / "db2" / ".seeds" / "seeds.db"
        db2 = Database(path=db2_path)
        db2.init()

        count = import_from_jsonl(db2, export_path)
        assert count == 1

        # Verify data matches
        imported_seed = db2.get_seed("seed-roundtrip")
        assert imported_seed.title == "Roundtrip Test"
        assert imported_seed.content == "Full content"
        assert imported_seed.status == SeedStatus.EXPLORING
        assert imported_seed.seed_type == SeedType.DECISION
        assert imported_seed.tags == ["test", "roundtrip"]
        assert imported_seed.related_to == ["seed-other"]

        imported_questions = db2.list_questions(seed_id="seed-roundtrip")
        assert len(imported_questions) == 1
        assert imported_questions[0].text == "Does this work?"
        assert imported_questions[0].answer == "Yes"

        db2.close()
