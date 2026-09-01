"""Tests for the seed-file reader/writer (bead seeds-4co.2).

The module under test is the only implementation of a format that two other
beads — ``seeds check`` and the converter — implement independently against
``docs/storage-format.md``. So nothing here lets the parser agree with itself:
every fixture is a hand-built file with the expected record, or the expected
bytes, worked out by hand from the spec and written down as the assertion.

The three that carry the most weight:

* ``test_canonical_bytes`` pins the exact file the writer must emit. It is the
  only assertion that would fail if key order, quoting, or the blank-line rule
  drifted, and the converter's byte-idempotence requirement rests on it.
* ``TestRoundTrip`` writes a record, reads it back, and compares field by
  field. A round trip that quietly loses a field is how a converter deletes
  data while reporting success.
* ``TestStrictness`` is the one that keeps the reader honest. Every case is a
  file that must RAISE; a lenient read is the silent wrongness this whole
  storage change exists to escape.
"""

from __future__ import annotations

import os
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from seeds.models import RelationType, SeedStatus
from seeds.seedfile import (
    SeedEdge,
    SeedFileError,
    SeedRecord,
    id_for_path,
    inverse_relation,
    is_valid_id,
    parse_seed_file,
    path_for_id,
    read_seed,
    read_seed_file,
    render_body,
    render_seed_file,
    seed_files_dir,
    superseded_scopes,
    write_seed,
    write_seed_file,
)

CREATED = datetime(2026, 8, 28, 14, 2, 11, 481293, tzinfo=UTC)
UPDATED = datetime(2026, 8, 31, 9, 41, 7, 220118, tzinfo=UTC)

# The file docs/storage-format.md §2 shows, written out by hand.
CANONICAL = """\
---
id: seeds-sdhc.4
title: Filenames carry identity only
status: resolved
type: decision
parent: seeds-sdhc
created_at: 2026-08-28T14:02:11.481293+00:00
updated_at: 2026-08-31T09:41:07.220118+00:00
resolved_at: 2026-08-31T09:41:07.220118+00:00
tags:
  - storage
  - format
relationships:
  - target_id: seeds-sdhc
    rel_type: relates-to
    created_at: 2026-08-28T14:02:11.481293+00:00
---

Settles seeds-sdhc's open items 3 and 4.
"""


def canonical_record() -> SeedRecord:
    """The record CANONICAL encodes — built by hand, not parsed from it."""
    return SeedRecord(
        id="seeds-sdhc.4",
        title="Filenames carry identity only",
        status=SeedStatus.RESOLVED,
        seed_type="decision",
        created_at=CREATED,
        updated_at=UPDATED,
        parent="seeds-sdhc",
        resolved_at=UPDATED,
        tags=["storage", "format"],
        relationships=[
            SeedEdge(
                target_id="seeds-sdhc",
                rel_type=RelationType.RELATES_TO,
                created_at=CREATED,
            )
        ],
        body="Settles seeds-sdhc's open items 3 and 4.\n",
    )


def minimal_record(seed_id: str = "seeds-abc") -> SeedRecord:
    """The smallest legal record: every optional field omitted."""
    return SeedRecord(
        id=seed_id,
        title="A minimal seed",
        status=SeedStatus.CAPTURED,
        seed_type="idea",
        created_at=CREATED,
        updated_at=CREATED,
    )


def write_raw(tmp_path: Path, name: str, text: str) -> Path:
    """Drop a hand-built file on disk without going through the writer."""
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


class TestPathAndId:
    """§1.1: the id is the filename stem verbatim, and this is the only mapping."""

    def test_path_is_computed_not_searched(self, tmp_path):
        expected = tmp_path / "seeds" / "seeds-sdhc.md"
        assert path_for_id(tmp_path, "seeds-sdhc") == expected

    def test_dotted_id_keeps_its_dots(self, tmp_path):
        path = path_for_id(tmp_path, "seeds-lcfa.6.1")
        assert path.name == "seeds-lcfa.6.1.md"

    def test_id_for_path_is_the_inverse(self, tmp_path):
        for seed_id in ("seeds-sdhc", "seeds-lcfa.6.1", "seeds-112", "csc-k3n7.2"):
            assert id_for_path(path_for_id(tmp_path, seed_id)) == seed_id

    def test_seed_files_dir(self, tmp_path):
        assert seed_files_dir(tmp_path) == tmp_path / "seeds"

    @pytest.mark.parametrize(
        "seed_id",
        [
            "seeds-sdhc",
            "seeds-sdhc.4",
            "seeds-lcfa.6.1",
            "seeds-112",
            "my-project-a1b2",
        ],
    )
    def test_valid_ids(self, seed_id):
        assert is_valid_id(seed_id)

    @pytest.mark.parametrize(
        "seed_id",
        [
            "Seeds-sdhc",  # uppercase: unsafe on a case-insensitive filesystem
            "seeds",  # no suffix token
            "seeds-",  # empty suffix
            "seeds-sdhc.",  # dangling dot
            "seeds-sdhc.a",  # child path is digits only
            "seeds-sdhc/4",  # a path separator is not an id
            "",
        ],
    )
    def test_invalid_ids(self, seed_id):
        assert not is_valid_id(seed_id)

    def test_path_for_invalid_id_raises(self, tmp_path):
        with pytest.raises(SeedFileError, match="not a valid seed id"):
            path_for_id(tmp_path, "Seeds-Bad")

    def test_id_for_non_seed_file_raises(self, tmp_path):
        with pytest.raises(SeedFileError, match="not a seed file"):
            id_for_path(tmp_path / "seeds-sdhc.txt")


class TestRender:
    """The writer emits exactly one representation of a given record."""

    def test_canonical_bytes(self):
        """Hand-built record, hand-written file. This is the byte contract."""
        assert render_seed_file(canonical_record()) == CANONICAL

    def test_optional_fields_are_omitted_when_empty(self):
        text = render_seed_file(minimal_record())
        assert text == (
            "---\n"
            "id: seeds-abc\n"
            "title: A minimal seed\n"
            "status: captured\n"
            "type: idea\n"
            "created_at: 2026-08-28T14:02:11.481293+00:00\n"
            "updated_at: 2026-08-28T14:02:11.481293+00:00\n"
            "---\n"
            "\n"
        )
        for absent in ("tags:", "resolution:", "relationships:", "parent:"):
            assert absent not in text

    def test_field_order_is_fixed(self):
        record = canonical_record()
        record.resolution = "settled"
        record.converted_at = UPDATED
        head = render_seed_file(record).split("\n---\n", 1)[0]
        keys = [
            line.split(":", 1)[0]
            for line in head.splitlines()[1:]
            if line and not line.startswith((" ", "-"))
        ]
        assert keys == [
            "id",
            "title",
            "status",
            "type",
            "parent",
            "created_at",
            "updated_at",
            "resolved_at",
            "resolution",
            "tags",
            "relationships",
            "converted_at",
        ]

    def test_awkward_scalars_are_quoted(self):
        """A title that would stop being a string, or would parse as syntax."""
        for title, expected in [
            ("42", '"42"'),
            ("true", '"true"'),
            ("null", '"null"'),
            ("no", '"no"'),
            ("Storage: the overhaul", '"Storage: the overhaul"'),
            ("weight # 3", '"weight # 3"'),
            ("[bracketed]", '"[bracketed]"'),
            ("- leading dash", '"- leading dash"'),
            ("trailing colon:", '"trailing colon:"'),
        ]:
            record = minimal_record()
            record.title = title
            rendered = render_seed_file(record)
            assert f"title: {expected}\n" in rendered
            # And it survives the round trip as the same string.
            back = parse_seed_file(Path("seeds-abc.md"), rendered)
            assert back.title == title

    def test_unicode_stays_readable(self):
        record = minimal_record()
        record.title = "Résumé — em dash and é"
        rendered = render_seed_file(record)
        assert "Résumé" in rendered
        assert parse_seed_file(Path("seeds-abc.md"), rendered).title == record.title

    def test_non_utc_offset_is_normalized_on_render(self):
        record = minimal_record()
        record.created_at = datetime(
            2026, 8, 28, 16, 2, 11, 481293, tzinfo=timezone(timedelta(hours=2))
        )
        assert "created_at: 2026-08-28T14:02:11.481293+00:00\n" in render_seed_file(
            record
        )


class TestRoundTrip:
    """Write, read back, compare field by field."""

    def test_every_field_survives(self, tmp_path):
        record = canonical_record()
        record.resolution = "ruled by @aguynamedryan"
        record.converted_at = UPDATED
        path = write_seed(tmp_path, record)
        back = read_seed_file(path)
        assert back == record

    def test_minimal_record_survives(self, tmp_path):
        record = minimal_record()
        write_seed(tmp_path, record)
        assert read_seed(tmp_path, record.id) == record

    def test_bytes_are_idempotent(self, tmp_path):
        """Re-writing an unchanged seed is a byte-level no-op."""
        path = write_seed(tmp_path, canonical_record())
        first = path.read_bytes()
        write_seed_file(path, read_seed_file(path))
        assert path.read_bytes() == first

    def test_parsing_the_hand_written_file_gives_the_hand_built_record(self, tmp_path):
        path = write_raw(tmp_path, "seeds-sdhc.4.md", CANONICAL)
        assert read_seed_file(path) == canonical_record()

    def test_empty_body_round_trips(self, tmp_path):
        """31 of this repo's seeds have no body; it must not become a parse error."""
        record = minimal_record()
        path = write_seed(tmp_path, record)
        assert path.read_text().endswith("---\n\n")
        assert read_seed_file(path).body == ""

    def test_body_whitespace_is_normalized(self, tmp_path):
        path = write_raw(
            tmp_path,
            "seeds-abc.md",
            "---\n"
            "id: seeds-abc\n"
            "title: A minimal seed\n"
            "status: captured\n"
            "type: idea\n"
            "created_at: 2026-08-28T14:02:11.481293+00:00\n"
            "updated_at: 2026-08-28T14:02:11.481293+00:00\n"
            "---\n"
            "\n\n\nSome prose.\n\n\n",
        )
        assert read_seed_file(path).body == "Some prose.\n"

    def test_tag_order_is_preserved_and_not_deduplicated(self, tmp_path):
        record = minimal_record()
        record.tags = ["zeta", "alpha", "zeta"]
        write_seed(tmp_path, record)
        assert read_seed(tmp_path, record.id).tags == ["zeta", "alpha", "zeta"]


class TestAtomicWrite:
    """§7: temp file in the same directory, then os.replace."""

    def test_write_goes_through_os_replace(self, tmp_path, monkeypatch):
        calls: list[tuple[Path, Path]] = []
        real_replace = os.replace

        def spy(src, dst, **kwargs):
            calls.append((Path(src), Path(dst)))
            real_replace(src, dst, **kwargs)

        monkeypatch.setattr("seeds.seedfile.os.replace", spy)
        path = write_seed(tmp_path, minimal_record())
        assert len(calls) == 1
        src, dst = calls[0]
        assert dst == path
        # Same directory means same filesystem, which is what makes it atomic.
        assert src.parent == path.parent

    def test_the_real_path_is_never_opened_for_writing(self, tmp_path):
        path = write_seed(tmp_path, minimal_record())
        before = path.stat().st_ino
        record = minimal_record()
        record.title = "Replaced wholesale"
        write_seed_file(path, record)
        assert path.stat().st_ino != before
        assert read_seed_file(path).title == "Replaced wholesale"

    def test_no_temp_file_is_left_behind(self, tmp_path):
        write_seed(tmp_path, minimal_record())
        assert [p.name for p in seed_files_dir(tmp_path).iterdir()] == ["seeds-abc.md"]

    def test_a_rejected_record_leaves_the_directory_clean(self, tmp_path):
        bad = minimal_record()
        bad.title = "   "
        with pytest.raises(SeedFileError, match="title"):
            write_seed(tmp_path, bad)
        directory = seed_files_dir(tmp_path)
        assert not directory.exists() or list(directory.iterdir()) == []

    def test_a_rejected_record_does_not_clobber_the_old_file(self, tmp_path):
        path = write_seed(tmp_path, minimal_record())
        original = path.read_bytes()
        bad = minimal_record()
        bad.status = SeedStatus.RESOLVED  # terminal with no resolved_at
        with pytest.raises(SeedFileError, match="resolved_at"):
            write_seed_file(path, bad)
        assert path.read_bytes() == original

    def test_id_must_match_the_filename(self, tmp_path):
        path = tmp_path / "seeds-other.md"
        with pytest.raises(SeedFileError, match="filename stem"):
            write_seed_file(path, minimal_record())


def frontmatter(**overrides: str) -> str:
    """Build a frontmatter block from the minimal valid one, plus overrides."""
    fields = {
        "id": "seeds-abc",
        "title": "A minimal seed",
        "status": "captured",
        "type": "idea",
        "created_at": "2026-08-28T14:02:11.481293+00:00",
        "updated_at": "2026-08-28T14:02:11.481293+00:00",
    }
    fields.update(overrides)
    body = "".join(f"{k}: {v}\n" for k, v in fields.items() if v is not None)
    return f"---\n{body}---\n\n"


class TestStrictness:
    """§7: a read that cannot fully understand a file fails loudly."""

    def parse(self, text: str, name: str = "seeds-abc.md") -> SeedRecord:
        return parse_seed_file(Path("/store") / name, text)

    def test_error_names_file_field_and_value(self):
        with pytest.raises(SeedFileError) as excinfo:
            self.parse(frontmatter(status="in-progress"))
        message = str(excinfo.value)
        assert "/store/seeds-abc.md" in message
        assert "'status'" in message
        assert "'in-progress'" in message

    def test_unknown_key_is_an_error(self):
        with pytest.raises(SeedFileError, match="unknown frontmatter key"):
            self.parse(frontmatter(priority="high"))

    def test_duplicate_key_is_an_error(self):
        text = frontmatter().replace("type: idea\n", "type: idea\ntype: concern\n")
        with pytest.raises(SeedFileError, match="duplicate key"):
            self.parse(text)

    @pytest.mark.parametrize(
        "missing", ["id", "title", "status", "type", "created_at", "updated_at"]
    )
    def test_missing_required_field_is_an_error(self, missing):
        text = frontmatter(**{missing: None})  # type: ignore[arg-type]
        with pytest.raises(SeedFileError, match="required frontmatter field"):
            self.parse(text)

    def test_flow_sequence_is_a_read_error(self):
        """§4: the flow form is never written and is a read error."""
        text = frontmatter().replace("---\n\n", "tags: [storage, format]\n---\n\n")
        with pytest.raises(SeedFileError, match="block sequence"):
            self.parse(text)

    def test_empty_block_sequence_is_a_read_error(self):
        """An empty optional field is omitted, not written out."""
        text = frontmatter().replace("---\n\n", "tags:\n---\n\n")
        with pytest.raises(SeedFileError, match="empty block sequence"):
            self.parse(text)

    def test_blank_optional_value_is_a_read_error(self):
        """§3: absent and empty are one state, with one representation."""
        with pytest.raises(SeedFileError, match="never written blank"):
            self.parse(frontmatter().replace("---\n\n", "resolution: \n---\n\n"))
        # ...and the quoted-empty spelling is equally not that representation.
        with pytest.raises(SeedFileError, match="never written blank"):
            self.parse(frontmatter(resolution='""'))

    def test_naive_timestamp_is_a_read_error(self):
        with pytest.raises(SeedFileError, match="no UTC offset"):
            self.parse(frontmatter(created_at="2026-08-28T14:02:11.481293"))

    def test_unparseable_timestamp_is_a_read_error(self):
        with pytest.raises(SeedFileError, match="ISO 8601"):
            self.parse(frontmatter(updated_at="last Tuesday"))

    def test_non_utc_offset_is_normalized_not_rejected(self):
        record = self.parse(frontmatter(created_at="2026-08-28T16:02:11.481293+02:00"))
        assert record.created_at == CREATED

    def test_status_outside_the_closed_set_is_an_error(self):
        with pytest.raises(SeedFileError, match="closed set"):
            self.parse(frontmatter(status="wontfix"))

    def test_type_is_an_open_vocabulary(self):
        """§3: any string round-trips; only 'question' carries behaviour."""
        assert self.parse(frontmatter(type="trellis")).seed_type == "trellis"

    def test_empty_title_is_an_error(self):
        with pytest.raises(SeedFileError, match="title"):
            self.parse(frontmatter(title='"   "'))

    def test_id_disagreeing_with_the_filename_is_an_error(self):
        with pytest.raises(SeedFileError, match="filename stem"):
            self.parse(frontmatter(id="seeds-xyz"))

    def test_dotted_id_requires_a_parent(self):
        text = frontmatter(id="seeds-abc.1")
        with pytest.raises(SeedFileError, match="parent must be 'seeds-abc'"):
            self.parse(text, name="seeds-abc.1.md")

    def test_parent_must_agree_with_the_dotted_id(self):
        text = frontmatter(id="seeds-abc.1", parent="seeds-zzz")
        with pytest.raises(SeedFileError, match="parent must be 'seeds-abc'"):
            self.parse(text, name="seeds-abc.1.md")

    def test_parent_is_forbidden_on_a_top_level_id(self):
        with pytest.raises(SeedFileError, match="forbidden on a top-level id"):
            self.parse(frontmatter(parent="seeds-zzz"))

    def test_grandchild_parent_is_the_full_dotted_path(self):
        text = frontmatter(id="seeds-abc.6.1", parent="seeds-abc.6")
        assert self.parse(text, name="seeds-abc.6.1.md").parent == "seeds-abc.6"

    def test_terminal_status_requires_resolved_at(self):
        for status in ("resolved", "abandoned"):
            with pytest.raises(SeedFileError, match="resolved_at is required"):
                self.parse(frontmatter(status=status))

    def test_resolved_at_is_forbidden_on_a_live_seed(self):
        text = frontmatter(resolved_at="2026-08-31T09:41:07.220118+00:00")
        with pytest.raises(SeedFileError, match="resolved_at is forbidden"):
            self.parse(text)

    def test_relationship_type_outside_the_closed_set_is_an_error(self):
        """'answers' was removed from the vocabulary; it must not parse."""
        text = CANONICAL.replace("rel_type: relates-to", "rel_type: answers")
        with pytest.raises(SeedFileError, match="rel_type is a closed set"):
            self.parse(text, name="seeds-sdhc.4.md")

    def test_relationship_missing_a_key_is_an_error(self):
        text = CANONICAL.replace(
            "    created_at: 2026-08-28T14:02:11.481293+00:00\n---", "---"
        )
        with pytest.raises(SeedFileError, match="missing created_at"):
            self.parse(text, name="seeds-sdhc.4.md")

    def test_unknown_relationship_key_is_an_error(self):
        text = CANONICAL.replace(
            "    rel_type: relates-to\n", "    rel_type: relates-to\n    weight: 3\n"
        )
        with pytest.raises(SeedFileError, match="unknown relationship key"):
            self.parse(text, name="seeds-sdhc.4.md")

    def test_relationship_target_must_be_an_id(self):
        text = CANONICAL.replace("target_id: seeds-sdhc", "target_id: Not An Id")
        with pytest.raises(SeedFileError, match="not a valid seed id"):
            self.parse(text, name="seeds-sdhc.4.md")

    def test_missing_opening_delimiter_is_an_error(self):
        with pytest.raises(SeedFileError, match="does not open with"):
            self.parse("\n" + frontmatter())

    def test_unclosed_frontmatter_is_an_error(self):
        with pytest.raises(SeedFileError, match="not closed"):
            self.parse("---\nid: seeds-abc\ntitle: x\n")

    def test_missing_blank_line_before_the_body_is_an_error(self):
        text = frontmatter()[:-1] + "Body starts immediately.\n"
        with pytest.raises(SeedFileError, match="blank line"):
            self.parse(text)

    def test_garbage_frontmatter_line_is_an_error(self):
        text = frontmatter().replace("type: idea\n", "type: idea\nnot a mapping\n")
        with pytest.raises(SeedFileError, match="unparseable frontmatter line"):
            self.parse(text)

    def test_crlf_is_a_read_error(self, tmp_path):
        path = tmp_path / "seeds-abc.md"
        path.write_bytes(frontmatter().replace("\n", "\r\n").encode())
        with pytest.raises(SeedFileError, match="CRLF"):
            read_seed_file(path)

    def test_bom_is_a_read_error(self, tmp_path):
        path = tmp_path / "seeds-abc.md"
        path.write_bytes(b"\xef\xbb\xbf" + frontmatter().encode())
        with pytest.raises(SeedFileError, match="BOM"):
            read_seed_file(path)

    def test_invalid_utf8_is_a_read_error(self, tmp_path):
        path = tmp_path / "seeds-abc.md"
        path.write_bytes(frontmatter().encode() + b"\xff\xfe")
        with pytest.raises(SeedFileError, match="not valid UTF-8"):
            read_seed_file(path)


class TestRelationInverses:
    """§5.2: only a type with a named inverse can be stored at both ends."""

    def test_relates_to_is_symmetric(self):
        assert inverse_relation(RelationType.RELATES_TO) is RelationType.RELATES_TO

    def test_questions_pairs_with_questioned_by(self):
        assert inverse_relation(RelationType.QUESTIONS) is RelationType.QUESTIONED_BY
        assert inverse_relation(RelationType.QUESTIONED_BY) is RelationType.QUESTIONS

    def test_every_type_has_an_inverse(self):
        """A directional type with no inverse cannot be stored in this format."""
        for rel_type in RelationType:
            assert inverse_relation(inverse_relation(rel_type)) is rel_type

    def test_the_inverse_round_trips_through_a_file(self, tmp_path):
        record = minimal_record()
        record.relationships = [
            SeedEdge("seeds-zzz", RelationType.QUESTIONED_BY, CREATED)
        ]
        write_seed(tmp_path, record)
        back = read_seed(tmp_path, record.id)
        assert back.relationships[0].rel_type is RelationType.QUESTIONED_BY


# --- The supersede marker (§6) ------------------------------------------------

# One body, three headings. The h2 "Dolt" section is retired; its h3 subsection
# falls INSIDE the scope (§6.2), and the following h2 closes it. The fenced
# block holds a '#' comment that a fence-blind parser would mistake for a
# heading and truncate the scope on.
MARKED_BODY = """\
## Dolt would give us cell-level merge
> [!SUPERSEDED] 2026-08-28 — ordinary git line-merge surfaces same-field
> collisions too, so the 120 MB dependency bought nothing.

Dolt stores every cell with its own history.

```sh
# not a heading
dolt sql -q 'select 1'
```

### Cost of the dependency

120 MB, and a second daemon per repo.

## What we did instead

One markdown file per seed.
"""

# Worked out by hand from MARKED_BODY: the heading and marker survive, the four
# lines they cover do not, and everything from the next h2 on is untouched.
MARKED_LIVE = """\
## Dolt would give us cell-level merge
> [!SUPERSEDED] 2026-08-28 — ordinary git line-merge surfaces same-field
> collisions too, so the 120 MB dependency bought nothing.
## What we did instead

One markdown file per seed.
"""


class TestSupersedeMarker:
    """§6: the marker grammar, and the scope rule that is the entire parse rule."""

    def test_scope_runs_to_the_next_heading_of_the_same_level(self):
        scopes = superseded_scopes(MARKED_BODY)
        assert len(scopes) == 1
        scope = scopes[0]
        lines = MARKED_BODY.split("\n")
        assert lines[scope.heading_line] == "## Dolt would give us cell-level merge"
        assert scope.level == 2
        assert scope.marker_line == 1
        assert scope.marker_end == 2  # the reason wraps onto a second '>' line
        assert lines[scope.stop] == "## What we did instead"

    def test_the_reason_clause_is_the_whole_blockquote(self):
        assert superseded_scopes(MARKED_BODY)[0].reason == (
            "ordinary git line-merge surfaces same-field collisions too, so the "
            "120 MB dependency bought nothing."
        )

    def test_the_date_is_parsed(self):
        assert superseded_scopes(MARKED_BODY)[0].retired_on == date(2026, 8, 28)

    def test_a_deeper_heading_does_not_close_the_scope(self):
        """§6.2: h3 and h4 fall inside the scope, along with their text."""
        live = render_body(MARKED_BODY)
        assert "### Cost of the dependency" not in live
        assert "120 MB, and a second daemon per repo." not in live

    def test_a_hash_inside_a_fence_is_not_a_heading(self):
        live = render_body(MARKED_BODY)
        assert "# not a heading" not in live
        assert "dolt sql" not in live

    def test_scope_runs_to_end_of_body_when_no_heading_follows(self):
        body = "# Only heading\n> [!SUPERSEDED] 2026-01-02 — wrong\n\nDead text.\n"
        assert superseded_scopes(body)[0].stop == len(body.split("\n"))
        assert render_body(body) == (
            "# Only heading\n> [!SUPERSEDED] 2026-01-02 — wrong\n"
        )

    def test_a_higher_heading_closes_a_deeper_scope(self):
        body = (
            "### Deep\n> [!SUPERSEDED] 2026-01-02 — wrong\ndead\n## Shallower\nalive\n"
        )
        assert render_body(body) == (
            "### Deep\n> [!SUPERSEDED] 2026-01-02 — wrong\n## Shallower\nalive\n"
        )

    def test_two_markers_in_one_body(self):
        body = (
            "## One\n"
            "> [!SUPERSEDED] 2026-01-02 — a\n"
            "dead one\n"
            "## Two\n"
            "> [!SUPERSEDED] 2026-03-04 — b\n"
            "dead two\n"
        )
        scopes = superseded_scopes(body)
        assert [s.reason for s in scopes] == ["a", "b"]
        assert render_body(body) == (
            "## One\n"
            "> [!SUPERSEDED] 2026-01-02 — a\n"
            "## Two\n"
            "> [!SUPERSEDED] 2026-03-04 — b\n"
        )

    def test_blank_lines_may_sit_between_heading_and_marker(self):
        body = "## H\n\n> [!SUPERSEDED] 2026-01-02 — why\ndead\n"
        assert superseded_scopes(body)[0].heading_line == 0

    def test_a_marker_inside_a_fence_is_example_text(self):
        body = (
            "## How to mark one\n"
            "```markdown\n"
            "> [!SUPERSEDED] 2026-01-02 — example\n"
            "```\n"
            "Still live.\n"
        )
        assert superseded_scopes(body) == []
        assert render_body(body) == body

    def test_a_floating_marker_raises(self):
        body = "Some prose.\n> [!SUPERSEDED] 2026-01-02 — why\n"
        with pytest.raises(SeedFileError, match="floating supersession"):
            superseded_scopes(body)

    def test_a_marker_with_no_heading_above_it_raises(self):
        with pytest.raises(SeedFileError, match="floating supersession"):
            superseded_scopes("> [!SUPERSEDED] 2026-01-02 — why\n")

    def test_a_marker_with_no_reason_clause_raises(self):
        body = "## H\n> [!SUPERSEDED] 2026-01-02 —\ndead\n"
        with pytest.raises(SeedFileError, match="no reason clause"):
            superseded_scopes(body)

    def test_a_malformed_marker_raises(self):
        for line in (
            "> [!SUPERSEDED] 2026-01-02 - hyphen not em dash",
            "> [!SUPERSEDED] 28-08-2026 — wrong date order",
            "> [!SUPERSEDED] — no date at all",
        ):
            with pytest.raises(SeedFileError, match="malformed supersede marker"):
                superseded_scopes(f"## H\n{line}\ndead\n")

    def test_an_impossible_date_raises(self):
        body = "## H\n> [!SUPERSEDED] 2026-02-31 — why\ndead\n"
        with pytest.raises(SeedFileError, match="impossible date"):
            superseded_scopes(body)

    def test_a_body_with_no_markers_is_returned_unchanged(self):
        body = "## Heading\n\nPlain prose.\n"
        assert render_body(body) == body
        assert render_body(body, full=True) == body


class TestLiveAndFullRender:
    """§7: nothing is destroyed on disk; the RENDER is what is selective."""

    def test_live_and_full_render_of_the_same_file(self, tmp_path):
        record = minimal_record()
        record.body = MARKED_BODY
        path = write_seed(tmp_path, record)

        stored = read_seed_file(path)
        # Nothing was removed on the way to disk: the file holds it all.
        assert stored.body == MARKED_BODY
        assert render_body(stored.body, full=True) == MARKED_BODY
        # The live render keeps the retired heading and its marker, and drops
        # only the text they cover.
        assert render_body(stored.body) == MARKED_LIVE

    def test_a_bad_marker_makes_the_file_unreadable(self, tmp_path):
        """The reader cannot tell what is retired, so it does not guess."""
        path = write_raw(
            tmp_path,
            "seeds-abc.md",
            frontmatter() + "Prose.\n> [!SUPERSEDED] 2026-01-02 — floating\n",
        )
        with pytest.raises(SeedFileError, match="floating supersession"):
            read_seed_file(path)

    def test_a_bad_marker_cannot_be_written(self, tmp_path):
        record = minimal_record()
        record.body = "## H\n> [!SUPERSEDED] 2026-01-02 —\ndead\n"
        with pytest.raises(SeedFileError, match="no reason clause"):
            write_seed(tmp_path, record)
