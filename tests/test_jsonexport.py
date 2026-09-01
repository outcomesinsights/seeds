"""Tests for ``seeds export --json`` (bead ``seeds-4co.12``).

This is a *replacement channel*, not a feature: on conversion day
`.seeds/seeds.jsonl` stops being written, and everything that wants a repo's
seeds as FIELDS without seeds installed — DuckDB, and anything else you would
write SQL for — has to move onto this pipe. (Full-text search does not: that is
ripgrep over ``*/.seeds/seeds/``, and it got better after conversion. The
"13 repos of cross-project query" this file used to cite was re-measured for
seeds-4co.20 and is false.) So the assertions here are about the two properties
the channel has to keep, and both of them fail *quietly* if they break:

* **Nothing is written to disk.** ``TestNothingIsWritten`` snapshots the whole
  tree before and after. A tracked file appearing again would reintroduce the
  exact defect the storage overhaul removed — a derived store that can diverge
  from the durable one — and it would do it without a single failing command.
* **The answer is complete or absent.** ``TestPartialOutputIsImpossible`` is the
  control that matters most: a stream that stops after 200 of 300 records is
  indistinguishable downstream from a repo that has 200 seeds. A short answer to
  a query looks exactly like a true one, so the export must refuse *before* the
  first byte, not part-way through.

The DuckDB case is the acceptance criterion itself rather than a unit test: it
runs the real ``duckdb`` binary over the real output, and skips when the binary
is absent rather than asserting a weaker claim.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import pytest

from seeds.jsonexport import (
    ExportError,
    export_json,
    read_corpus,
    record_to_dict,
)
from seeds.models import RelationType, SeedStatus
from seeds.seedfile import SeedEdge, SeedRecord, write_seed

CREATED = datetime(2026, 8, 28, 14, 2, 11, 481293, tzinfo=UTC)
UPDATED = datetime(2026, 8, 30, 9, 41, 7, 220118, tzinfo=UTC)
RESOLVED = datetime(2026, 8, 31, 8, 0, 0, tzinfo=UTC)
EDGE_AT = datetime(2026, 8, 29, 10, 0, 0, tzinfo=UTC)
CONVERTED = datetime(2026, 8, 31, 12, 0, 0, tzinfo=UTC)


def record(seed_id: str = "seeds-abc", **overrides: object) -> SeedRecord:
    """A valid minimal record, plus overrides."""
    fields: dict[str, object] = {
        "id": seed_id,
        "title": "A minimal seed",
        "status": SeedStatus.CAPTURED,
        "seed_type": "idea",
        "created_at": CREATED,
        "updated_at": UPDATED,
        "parent": seed_id.rsplit(".", 1)[0] if "." in seed_id else None,
        "body": "Some deliberation.\n",
    }
    fields.update(overrides)
    return SeedRecord(**fields)  # type: ignore[arg-type]


def store(tmp_path: Path, *records: SeedRecord) -> Path:
    """Write ``records`` into a fresh store and return its ``.seeds`` dir."""
    seeds_dir = tmp_path / ".seeds"
    (seeds_dir / "seeds").mkdir(parents=True, exist_ok=True)
    for item in records:
        write_seed(seeds_dir, item)
    return seeds_dir


def write_raw(seeds_dir: Path, name: str, text: str) -> Path:
    """Write a file the reader would refuse."""
    path = seeds_dir / "seeds" / name
    path.write_text(text, encoding="utf-8")
    return path


def lines(seeds_dir: Path) -> list[dict]:
    """Export ``seeds_dir`` and parse every line back."""
    buffer = StringIO()
    export_json(seeds_dir, buffer)
    text = buffer.getvalue()
    return [json.loads(line) for line in text.splitlines()]


def tree(root: Path) -> set[Path]:
    return set(root.rglob("*"))


class TestRecordShape:
    def test_every_field_of_a_full_record(self, tmp_path):
        """Hand-computed: the object a maximal seed produces, key for key."""
        full = record(
            "seeds-abc.1",
            title="A resolved child",
            status=SeedStatus.RESOLVED,
            seed_type="decision",
            resolved_at=RESOLVED,
            resolution="Ruled by @aguynamedryan.",
            tags=["storage", "0.7"],
            relationships=[SeedEdge("seeds-xyz", RelationType.RELATES_TO, EDGE_AT)],
            converted_at=CONVERTED,
            body="The deliberation.\n",
        )
        assert record_to_dict(full) == {
            "id": "seeds-abc.1",
            "title": "A resolved child",
            "content": "The deliberation.\n",
            "status": "resolved",
            "seed_type": "decision",
            "parent": "seeds-abc",
            "tags": ["storage", "0.7"],
            "created_at": "2026-08-28T14:02:11.481293+00:00",
            "updated_at": "2026-08-30T09:41:07.220118+00:00",
            "resolved_at": "2026-08-31T08:00:00+00:00",
            "resolution": "Ruled by @aguynamedryan.",
            "converted_at": "2026-08-31T12:00:00+00:00",
            "relationships": [
                {
                    "target_id": "seeds-xyz",
                    "rel_type": "relates-to",
                    "created_at": "2026-08-29T10:00:00+00:00",
                }
            ],
        }

    def test_absent_fields_are_null_not_omitted(self):
        """The file omits an empty optional; the stream must not.

        A query is written against a column, and DuckDB infers columns from the
        records it sees. Omitting a key on some records and not others makes the
        column's presence depend on which seeds happen to be in the repo.
        """
        minimal = record_to_dict(record())
        assert minimal["parent"] is None
        assert minimal["resolved_at"] is None
        assert minimal["converted_at"] is None
        assert minimal["resolution"] == ""
        assert minimal["tags"] == []
        assert minimal["relationships"] == []

    def test_no_format_version(self):
        """The frozen format has no version, so neither does its stream (§8)."""
        assert "format_version" not in record_to_dict(record())

    def test_body_is_carried_under_the_retired_name(self):
        """``content``, as the pre-0.7 JSONL called it -- queries depend on it."""
        assert record_to_dict(record(body="text\n"))["content"] == "text\n"
        assert "body" not in record_to_dict(record())


class TestStream:
    def test_one_object_per_line(self, tmp_path):
        seeds_dir = store(tmp_path, record("seeds-aaa"), record("seeds-bbb"))
        buffer = StringIO()
        count = export_json(seeds_dir, buffer)
        text = buffer.getvalue()
        assert count == 2
        assert text.endswith("\n")
        assert len(text.splitlines()) == 2
        assert [json.loads(line)["id"] for line in text.splitlines()] == [
            "seeds-aaa",
            "seeds-bbb",
        ]

    def test_records_are_sorted_by_id(self, tmp_path):
        seeds_dir = store(
            tmp_path, record("seeds-ccc"), record("seeds-aaa"), record("seeds-bbb")
        )
        assert [row["id"] for row in lines(seeds_dir)] == [
            "seeds-aaa",
            "seeds-bbb",
            "seeds-ccc",
        ]

    def test_a_body_with_newlines_stays_on_one_line(self, tmp_path):
        """JSONL's whole premise: one record is one greppable line."""
        seeds_dir = store(tmp_path, record(body="first\n\nsecond\nthird\n"))
        buffer = StringIO()
        export_json(seeds_dir, buffer)
        text = buffer.getvalue()
        assert len(text.splitlines()) == 1
        assert json.loads(text)["content"] == "first\n\nsecond\nthird\n"

    def test_non_ascii_is_not_escaped(self, tmp_path):
        """Escaping em dashes turns a greppable line into one no search hits."""
        seeds_dir = store(tmp_path, record(body="cost — not speed\n"))
        buffer = StringIO()
        export_json(seeds_dir, buffer)
        assert "cost — not speed" in buffer.getvalue()

    def test_two_runs_are_byte_identical(self, tmp_path):
        seeds_dir = store(tmp_path, record("seeds-aaa"), record("seeds-bbb"))
        first, second = StringIO(), StringIO()
        export_json(seeds_dir, first)
        export_json(seeds_dir, second)
        assert first.getvalue() == second.getvalue()

    def test_an_empty_store_is_an_empty_stream(self, tmp_path):
        seeds_dir = tmp_path / ".seeds"
        (seeds_dir / "seeds").mkdir(parents=True)
        buffer = StringIO()
        assert export_json(seeds_dir, buffer) == 0
        assert buffer.getvalue() == ""


class TestNothingIsWritten:
    def test_export_creates_no_file(self, tmp_path):
        seeds_dir = store(tmp_path, record("seeds-aaa"), record("seeds-bbb"))
        before = tree(tmp_path)
        export_json(seeds_dir, StringIO())
        assert tree(tmp_path) == before

    def test_export_does_not_touch_the_seed_files(self, tmp_path):
        seeds_dir = store(tmp_path, record())
        path = seeds_dir / "seeds" / "seeds-abc.md"
        before = path.read_bytes()
        export_json(seeds_dir, StringIO())
        assert path.read_bytes() == before


class TestPartialOutputIsImpossible:
    def test_an_unreadable_file_aborts_before_any_output(self, tmp_path):
        """The refusal is total: 2 good records do not reach the stream.

        Alphabetically 'seeds-aaa' precedes the broken 'seeds-mmm', so a
        naive streaming implementation would already have emitted it.
        """
        seeds_dir = store(tmp_path, record("seeds-aaa"), record("seeds-zzz"))
        write_raw(seeds_dir, "seeds-mmm.md", "no frontmatter here at all\n")
        buffer = StringIO()
        with pytest.raises(ExportError) as excinfo:
            export_json(seeds_dir, buffer)
        assert buffer.getvalue() == ""
        assert "seeds-mmm.md" in str(excinfo.value)
        assert "nothing was exported" in str(excinfo.value)

    def test_a_bad_filename_aborts(self, tmp_path):
        seeds_dir = store(tmp_path, record("seeds-aaa"))
        write_raw(seeds_dir, "NOTES.md", "scratch\n")
        buffer = StringIO()
        with pytest.raises(ExportError) as excinfo:
            export_json(seeds_dir, buffer)
        assert buffer.getvalue() == ""
        assert "not a valid seed id" in str(excinfo.value)

    def test_a_missing_store_is_an_error_not_an_empty_stream(self, tmp_path):
        """An unconverted repo must not read as a repo with zero seeds."""
        seeds_dir = tmp_path / ".seeds"
        seeds_dir.mkdir()
        with pytest.raises(ExportError) as excinfo:
            export_json(seeds_dir, StringIO())
        assert "no seed-file store" in str(excinfo.value)

    def test_read_corpus_returns_every_seed(self, tmp_path):
        seeds_dir = store(tmp_path, *(record(f"seeds-a{n:02d}") for n in range(30)))
        assert len(read_corpus(seeds_dir)) == 30


class TestCli:
    def _run(self, cli_runner, tmp_path, monkeypatch, args):
        monkeypatch.chdir(tmp_path)
        from seeds.cli import main

        return cli_runner.invoke(main, args)

    def test_export_json_writes_the_corpus(self, tmp_path, cli_runner, monkeypatch):
        store(tmp_path, record("seeds-aaa"), record("seeds-bbb"))
        result = self._run(cli_runner, tmp_path, monkeypatch, ["export", "--json"])
        assert result.exit_code == 0, result.output
        rows = [json.loads(line) for line in result.stdout.splitlines()]
        assert [row["id"] for row in rows] == ["seeds-aaa", "seeds-bbb"]

    def test_export_json_creates_no_file(self, tmp_path, cli_runner, monkeypatch):
        store(tmp_path, record())
        before = tree(tmp_path)
        result = self._run(cli_runner, tmp_path, monkeypatch, ["export", "--json"])
        assert result.exit_code == 0, result.output
        assert tree(tmp_path) == before

    def test_bare_export_refuses(self, tmp_path, cli_runner, monkeypatch):
        """No format, no guess -- and no seeds on stdout to be piped anywhere."""
        store(tmp_path, record())
        result = self._run(cli_runner, tmp_path, monkeypatch, ["export"])
        assert result.exit_code == 2
        assert result.stdout == ""
        assert "--json" in result.stderr

    def test_unreadable_file_exits_non_zero_with_empty_stdout(
        self, tmp_path, cli_runner, monkeypatch
    ):
        seeds_dir = store(tmp_path, record("seeds-aaa"))
        write_raw(seeds_dir, "seeds-mmm.md", "not a seed file\n")
        result = self._run(cli_runner, tmp_path, monkeypatch, ["export", "--json"])
        assert result.exit_code == 1
        assert result.stdout == ""
        assert "seeds-mmm.md" in result.stderr

    def test_uninitialized_exits_non_zero(self, tmp_path, cli_runner, monkeypatch):
        result = self._run(cli_runner, tmp_path, monkeypatch, ["export", "--json"])
        assert result.exit_code == 1
        assert "not initialized" in result.stderr

    def test_help_no_longer_claims_cross_project_query_depends_on_it(self, cli_runner):
        """Bead seeds-4co.20: the claim was re-measured and is false.

        Roughly 2-3 of 26 real calls were structured extraction; the rest were
        full-text search, which is rg's job and got *better* after conversion.
        The command stays -- a pipe to stdout costs nothing -- but it must not
        justify itself with work it does not do.
        """
        from seeds.cli import main

        result = cli_runner.invoke(main, ["export", "--help"])

        assert result.exit_code == 0
        assert "13 repos" not in result.output
        assert "cross-project query depend" not in result.output

    def test_help_says_structured_extraction_and_points_search_at_rg(self, cli_runner):
        from seeds.cli import main

        result = cli_runner.invoke(main, ["export", "--help"])

        assert "STRUCTURED EXTRACTION" in result.output
        assert "duckdb" in result.output
        assert "rg -l" in result.output
        assert "/.seeds/seeds/" in result.output


@pytest.mark.skipif(shutil.which("duckdb") is None, reason="duckdb CLI not installed")
class TestDuckDbAcceptance:
    """The acceptance criterion, run against the real binary.

    The cross-project query this replaces (``seeds-183``) is a
    ``read_json_auto`` over every repo's tracked JSONL, grouping by status. The
    same query has to work over the pipe, or conversion day breaks 13 repos.
    """

    def _query(self, payload: str, sql: str, tmp_path: Path) -> str:
        return subprocess.run(
            ["duckdb", "-noheader", "-list", "-c", sql],
            input=payload,
            capture_output=True,
            text=True,
            check=True,
            cwd=tmp_path,
        ).stdout.strip()

    def test_group_by_status_over_the_pipe(self, tmp_path):
        seeds_dir = store(
            tmp_path,
            record("seeds-aaa", status=SeedStatus.CAPTURED),
            record("seeds-bbb", status=SeedStatus.CAPTURED),
            record(
                "seeds-ccc",
                status=SeedStatus.RESOLVED,
                resolved_at=RESOLVED,
            ),
        )
        buffer = StringIO()
        export_json(seeds_dir, buffer)
        out = self._query(
            buffer.getvalue(),
            "SELECT status, count(*) FROM read_json_auto('/dev/stdin') "
            "GROUP BY 1 ORDER BY 1",
            tmp_path,
        )
        assert out.splitlines() == ["captured|2", "resolved|1"]

    def test_nested_types_survive_inference(self, tmp_path):
        """``tags varchar[]`` and the relationships struct, as before."""
        seeds_dir = store(
            tmp_path,
            record(
                "seeds-aaa",
                tags=["storage", "0.7"],
                relationships=[SeedEdge("seeds-zzz", RelationType.RELATES_TO, EDGE_AT)],
            ),
        )
        buffer = StringIO()
        export_json(seeds_dir, buffer)
        out = self._query(
            buffer.getvalue(),
            "SELECT len(tags), relationships[1].target_id "
            "FROM read_json_auto('/dev/stdin')",
            tmp_path,
        )
        assert out == "2|seeds-zzz"
