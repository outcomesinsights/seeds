"""Tests for ``seeds check``, the violations tier (bead ``seeds-4co.3``).

This is a *detector*, not a feature, and the data-pipeline standard for
detectors applies in full: the code deciding "clean" is itself code that can be
silently wrong, and this one gates the conversion. So nothing here asks the
checker to agree with itself. Every fixture is a hand-built file whose findings
were worked out by hand from ``docs/storage-format.md`` and written down as the
assertion, and the two that carry the most weight are the negative ones:

* ``TestCleanCorpusIsClean`` — a whole valid store scores zero. A detector that
  fires on healthy input is worse than no detector, because it trains everyone
  to pass ``--no-verify``.
* ``TestNoFalsePositives`` — the specific shapes that *look* wrong and are not:
  a title that merely mentions a URL, a setext ``=======`` underline, a body
  with no text at all, a body whose bytes are not canonical. Each of those is
  either legal or another tier's business.

The empty-body case is pinned deliberately. An earlier draft of the plan called
it a violation; @aguynamedryan ruled on 2026-08-31 that it is a smell, because
``seeds jot`` produces a title-only seed by design and 31 of this repo's 314
seeds have none. ``test_empty_body_is_not_a_violation`` is what stops that
being reintroduced.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from seeds.check import (
    Finding,
    check_corpus,
    check_violations,
    format_findings,
)
from seeds.models import RelationType, SeedStatus
from seeds.seedfile import SeedEdge, SeedRecord, write_seed

NOW = datetime(2026, 8, 31, 12, 0, 0, tzinfo=UTC)
CREATED = datetime(2026, 8, 28, 14, 2, 11, 481293, tzinfo=UTC)
UPDATED = datetime(2026, 8, 30, 9, 41, 7, 220118, tzinfo=UTC)
EDGE_AT = datetime(2026, 8, 29, 10, 0, 0, tzinfo=UTC)


def record(seed_id: str = "seeds-abc", **overrides: object) -> SeedRecord:
    """A valid record, plus overrides. The baseline scores zero findings."""
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


def codes(findings: list[Finding]) -> list[str]:
    return [finding.code for finding in findings]


def write_raw(seeds_dir: Path, name: str, text: str) -> Path:
    """Write a file the writer would refuse — the whole point of a checker."""
    path = seeds_dir / "seeds" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def frontmatter(**overrides: str | None) -> str:
    """A minimal valid file's text, plus overrides. Mirrors test_seedfile's."""
    fields: dict[str, str | None] = {
        "id": "seeds-abc",
        "title": "A minimal seed",
        "status": "captured",
        "type": "idea",
        "created_at": "2026-08-28T14:02:11.481293+00:00",
        "updated_at": "2026-08-30T09:41:07.220118+00:00",
    }
    fields.update(overrides)
    body = "".join(f"{k}: {v}\n" for k, v in fields.items() if v is not None)
    return f"---\n{body}---\n\nSome deliberation.\n"


# --- The clean case ----------------------------------------------------------


class TestCleanCorpusIsClean:
    """Zero findings on healthy input, or nobody will keep the gate on."""

    def test_single_valid_seed(self, tmp_path):
        seeds_dir = store(tmp_path, record())
        assert check_violations(seeds_dir, now=NOW) == []

    def test_hierarchy_edges_tags_and_terminal_states(self, tmp_path):
        parent = record(
            "seeds-abc",
            relationships=[
                SeedEdge("seeds-xyz", RelationType.RELATES_TO, EDGE_AT),
                SeedEdge("seeds-q1", RelationType.QUESTIONS, EDGE_AT),
            ],
            tags=["storage", "format"],
        )
        child = record("seeds-abc.1", status=SeedStatus.RESOLVED, resolved_at=UPDATED)
        grandchild = record("seeds-abc.1.2")
        other = record(
            "seeds-xyz",
            relationships=[SeedEdge("seeds-abc", RelationType.RELATES_TO, EDGE_AT)],
        )
        question = record(
            "seeds-q1",
            seed_type="question",
            relationships=[SeedEdge("seeds-abc", RelationType.QUESTIONED_BY, EDGE_AT)],
        )
        seeds_dir = store(tmp_path, parent, child, grandchild, other, question)
        assert check_violations(seeds_dir, now=NOW) == []

    def test_valid_supersede_marker(self, tmp_path):
        body = (
            "## Dolt would give us cell-level merge\n"
            "> [!SUPERSEDED] 2026-08-28 — ordinary git line-merge surfaces\n"
            "> same-field collisions too.\n"
            "\n"
            "Original section text, untouched.\n"
        )
        seeds_dir = store(tmp_path, record(body=body))
        assert check_violations(seeds_dir, now=NOW) == []


# --- Strict-read refusals ----------------------------------------------------


class TestParseFailures:
    """A file the reader refuses is a violation that names the file and a fix."""

    def test_frontmatter_that_will_not_parse(self, tmp_path):
        seeds_dir = store(tmp_path, record("seeds-ok"))
        write_raw(seeds_dir, "seeds-abc.md", "id: seeds-abc\ntitle: no delimiters\n")
        findings = check_violations(seeds_dir, now=NOW)
        assert codes(findings) == ["parse-error"]
        assert "seeds-abc.md" in findings[0].message
        assert findings[0].remediation

    def test_status_outside_the_closed_set(self, tmp_path):
        seeds_dir = store(tmp_path, record("seeds-ok"))
        write_raw(seeds_dir, "seeds-abc.md", frontmatter(status="in-progress"))
        findings = check_violations(seeds_dir, now=NOW)
        assert codes(findings) == ["status-unknown"]
        assert "'in-progress'" in findings[0].message
        # The remediation names the closed set, not just "invalid status".
        assert "captured" in findings[0].remediation
        assert "abandoned" in findings[0].remediation

    def test_a_whitespace_only_title(self, tmp_path):
        seeds_dir = store(tmp_path, record("seeds-ok"))
        write_raw(seeds_dir, "seeds-abc.md", frontmatter(title='" "'))
        assert codes(check_violations(seeds_dir, now=NOW)) == ["title-empty"]

    def test_a_blank_title(self, tmp_path):
        """`title: ""` trips the earlier rule that absent and empty are one
        state (§3), so it lands as a parse error rather than title-empty. Both
        are violations that name the file; only the code differs."""
        seeds_dir = store(tmp_path, record("seeds-ok"))
        write_raw(seeds_dir, "seeds-abc.md", frontmatter(title='""'))
        findings = check_violations(seeds_dir, now=NOW)
        assert codes(findings) == ["parse-error"]
        assert "'title'" in findings[0].message

    def test_parent_disagrees_with_the_dotted_id(self, tmp_path):
        seeds_dir = store(tmp_path, record("seeds-ok"))
        write_raw(
            seeds_dir,
            "seeds-abc.1.md",
            frontmatter(id="seeds-abc.1", parent="seeds-zzz"),
        )
        findings = check_violations(seeds_dir, now=NOW)
        assert codes(findings) == ["parent-mismatch"]

    def test_parent_on_a_top_level_id(self, tmp_path):
        seeds_dir = store(tmp_path, record("seeds-ok"))
        write_raw(seeds_dir, "seeds-abc.md", frontmatter(parent="seeds-ok"))
        assert codes(check_violations(seeds_dir, now=NOW)) == ["parent-mismatch"]

    def test_filename_that_is_not_a_seed_id(self, tmp_path):
        seeds_dir = store(tmp_path, record("seeds-ok"))
        write_raw(seeds_dir, "README.md", "notes\n")
        findings = check_violations(seeds_dir, now=NOW)
        assert codes(findings) == ["bad-filename"]
        assert "README" in findings[0].message


class TestSupersedeMarkers:
    """§6.1: the marker's grammar, its mandatory reason, and its position."""

    def body_file(self, tmp_path, body: str) -> Path:
        seeds_dir = store(tmp_path, record("seeds-ok"))
        write_raw(
            seeds_dir,
            "seeds-abc.md",
            frontmatter()[: -len("Some deliberation.\n")] + body,
        )
        return seeds_dir

    def test_marker_with_no_reason_clause(self, tmp_path):
        seeds_dir = self.body_file(
            tmp_path, "## A retired position\n> [!SUPERSEDED] 2026-08-28 — \n"
        )
        findings = check_violations(seeds_dir, now=NOW)
        assert codes(findings) == ["supersede-no-reason"]
        assert "re-litigation" in findings[0].remediation

    def test_floating_marker_has_no_heading_to_retire(self, tmp_path):
        seeds_dir = self.body_file(
            tmp_path,
            "Ordinary prose.\n\n> [!SUPERSEDED] 2026-08-28 — reason enough.\n",
        )
        findings = check_violations(seeds_dir, now=NOW)
        assert codes(findings) == ["supersede-position"]

    def test_marker_not_first_line_after_its_heading(self, tmp_path):
        seeds_dir = self.body_file(
            tmp_path,
            "## A heading\n\nSome text first.\n\n"
            "> [!SUPERSEDED] 2026-08-28 — reason enough.\n",
        )
        assert codes(check_violations(seeds_dir, now=NOW)) == ["supersede-position"]

    def test_malformed_marker(self, tmp_path):
        seeds_dir = self.body_file(
            tmp_path, "## A heading\n> [!SUPERSEDED] because I said so\n"
        )
        assert codes(check_violations(seeds_dir, now=NOW)) == ["supersede-malformed"]

    def test_impossible_date(self, tmp_path):
        seeds_dir = self.body_file(
            tmp_path, "## A heading\n> [!SUPERSEDED] 2026-02-31 — reason enough.\n"
        )
        assert codes(check_violations(seeds_dir, now=NOW)) == ["supersede-malformed"]


# --- Content plausibility ----------------------------------------------------


class TestTitlePlausibility:
    """seeds-wurl: every one of the 83 clobbered titles parsed perfectly."""

    @pytest.mark.parametrize(
        "title",
        [
            "/tmp/claude-1001/scratchpad/seed-body.md",
            "./notes/draft.md",
            "../sibling/seed.md",
            "~/projects/outins/seeds/README.md",
            "src/seeds/cli.py",
            "C:/Users/agent/scratch.md",
        ],
    )
    def test_a_title_that_is_a_path(self, tmp_path, title):
        seeds_dir = store(tmp_path, record(title=title))
        findings = check_violations(seeds_dir, now=NOW)
        assert codes(findings) == ["title-is-path"]
        assert title in findings[0].message
        assert "git log -p" in findings[0].remediation

    @pytest.mark.parametrize(
        "title",
        [
            "https://github.com/outcomesinsights/seeds",
            "http://example.com",
            "file:///tmp/x",
        ],
    )
    def test_a_title_that_is_a_url(self, tmp_path, title):
        seeds_dir = store(tmp_path, record(title=title))
        assert codes(check_violations(seeds_dir, now=NOW)) == ["title-is-url"]

    def test_the_whole_corpus_is_scored_not_a_sample(self, tmp_path):
        """83 of 306 was the real ratio; a sampling checker misses most of it."""
        good = [record(f"seeds-g{n:02d}") for n in range(20)]
        bad = [
            record(f"seeds-b{n:02d}", title=f"/tmp/scratch/{n}.md") for n in range(10)
        ]
        seeds_dir = store(tmp_path, *good, *bad)
        findings = check_violations(seeds_dir, now=NOW)
        assert codes(findings) == ["title-is-path"] * 10
        assert {f.seed_id for f in findings} == {f"seeds-b{n:02d}" for n in range(10)}


class TestConflictMarkers:
    def test_markers_in_the_body(self, tmp_path):
        seeds_dir = store(tmp_path, record("seeds-ok"))
        body = (
            "Before.\n"
            "<<<<<<< HEAD\n"
            "ours\n"
            "=======\n"
            "theirs\n"
            ">>>>>>> other-branch\n"
            "After.\n"
        )
        write_raw(
            seeds_dir,
            "seeds-abc.md",
            frontmatter()[: -len("Some deliberation.\n")] + body,
        )
        findings = check_violations(seeds_dir, now=NOW)
        # Hand-counted: eight frontmatter lines (both `---` delimiters
        # included) then the blank separator, so the body starts at line 10 and
        # its three markers land on 11, 13 and 15.
        assert codes(findings) == ["conflict-markers"]
        assert "3 line(s): 11, 13, 15" in findings[0].message
        assert findings[0].line == 11

    def test_diff3_base_marker_counts(self, tmp_path):
        seeds_dir = store(tmp_path, record("seeds-ok"))
        body = "<<<<<<< ours\na\n||||||| base\nb\n=======\nc\n>>>>>>> theirs\n"
        write_raw(
            seeds_dir,
            "seeds-abc.md",
            frontmatter()[: -len("Some deliberation.\n")] + body,
        )
        assert codes(check_violations(seeds_dir, now=NOW)) == ["conflict-markers"]

    def test_a_conflicted_file_reports_the_conflict_not_the_parse_error(self, tmp_path):
        """The parse failure is a consequence; naming both doubles the noise."""
        seeds_dir = store(tmp_path, record("seeds-ok"))
        write_raw(
            seeds_dir,
            "seeds-abc.md",
            "<<<<<<< HEAD\n---\nid: seeds-abc\n=======\n---\n>>>>>>> other\n",
        )
        assert codes(check_violations(seeds_dir, now=NOW)) == ["conflict-markers"]


class TestTimestamps:
    def test_updated_before_created(self, tmp_path):
        seeds_dir = store(tmp_path, record(created_at=UPDATED, updated_at=CREATED))
        findings = check_violations(seeds_dir, now=NOW)
        assert codes(findings) == ["updated-before-created"]

    def test_created_at_in_the_future(self, tmp_path):
        ahead = NOW + timedelta(days=1)
        seeds_dir = store(tmp_path, record(created_at=ahead, updated_at=ahead))
        findings = check_violations(seeds_dir, now=NOW)
        assert codes(findings) == ["future-timestamp", "future-timestamp"]
        assert {f.message.split()[0] for f in findings} == {
            "created_at",
            "updated_at",
        }

    def test_resolved_at_in_the_future(self, tmp_path):
        ahead = NOW + timedelta(seconds=1)
        seeds_dir = store(
            tmp_path,
            record(status=SeedStatus.RESOLVED, resolved_at=ahead),
        )
        findings = check_violations(seeds_dir, now=NOW)
        assert codes(findings) == ["future-timestamp"]
        assert findings[0].message.startswith("resolved_at")

    def test_converted_at_in_the_future(self, tmp_path):
        seeds_dir = store(tmp_path, record(converted_at=NOW + timedelta(days=365)))
        findings = check_violations(seeds_dir, now=NOW)
        assert codes(findings) == ["future-timestamp"]
        assert findings[0].message.startswith("converted_at")

    def test_an_edge_stamped_in_the_future(self, tmp_path):
        ahead = NOW + timedelta(days=1)
        one = record(
            "seeds-abc",
            relationships=[SeedEdge("seeds-xyz", RelationType.RELATES_TO, ahead)],
        )
        two = record(
            "seeds-xyz",
            relationships=[SeedEdge("seeds-abc", RelationType.RELATES_TO, ahead)],
        )
        seeds_dir = store(tmp_path, one, two)
        findings = check_violations(seeds_dir, now=NOW)
        assert codes(findings) == ["future-timestamp", "future-timestamp"]

    def test_a_stamp_exactly_now_is_fine(self, tmp_path):
        seeds_dir = store(tmp_path, record(created_at=NOW, updated_at=NOW))
        assert check_violations(seeds_dir, now=NOW) == []


class TestParentIntegrity:
    def test_parent_names_a_missing_file(self, tmp_path):
        seeds_dir = store(tmp_path, record("seeds-abc.1"))
        findings = check_violations(seeds_dir, now=NOW)
        assert codes(findings) == ["parent-missing"]
        assert "seeds-abc" in findings[0].message
        assert "seeds-abc.md" in findings[0].remediation

    def test_a_grandchild_with_a_present_chain_is_clean(self, tmp_path):
        seeds_dir = store(
            tmp_path,
            record("seeds-abc"),
            record("seeds-abc.1"),
            record("seeds-abc.1.2"),
        )
        assert check_violations(seeds_dir, now=NOW) == []

    def test_a_parent_cycle(self):
        """No set of *files* can carry one -- §3 pins parent to the dotted id --
        so the walk is exercised on hand-built records instead. The rule is in
        the spec and the check has to be real, not assumed."""
        one = record("seeds-abc", parent="seeds-xyz")
        two = record("seeds-xyz", parent="seeds-abc")
        findings = check_corpus(
            [(Path("/store/seeds-abc.md"), one), (Path("/store/seeds-xyz.md"), two)],
            now=NOW,
        )
        cycles = [f for f in findings if f.code == "parent-cycle"]
        assert len(cycles) == 2
        assert "seeds-abc -> seeds-xyz -> seeds-abc" in cycles[0].message

    def test_a_seed_that_is_its_own_parent(self):
        one = record("seeds-abc", parent="seeds-abc")
        findings = check_corpus([(Path("/store/seeds-abc.md"), one)], now=NOW)
        assert "parent-cycle" in codes(findings)


class TestRelationships:
    def test_a_relationship_naming_a_missing_file(self, tmp_path):
        seeds_dir = store(
            tmp_path,
            record(
                relationships=[SeedEdge("seeds-gone", RelationType.RELATES_TO, EDGE_AT)]
            ),
        )
        findings = check_violations(seeds_dir, now=NOW)
        assert codes(findings) == ["relationship-target-missing"]
        assert "seeds-gone" in findings[0].message

    def test_a_one_sided_edge(self, tmp_path):
        one = record(
            "seeds-abc",
            relationships=[SeedEdge("seeds-xyz", RelationType.RELATES_TO, EDGE_AT)],
        )
        two = record("seeds-xyz")
        seeds_dir = store(tmp_path, one, two)
        findings = check_violations(seeds_dir, now=NOW)
        # Reported once, on the end that holds the orphaned half.
        assert codes(findings) == ["one-sided-edge"]
        assert findings[0].seed_id == "seeds-abc"
        assert "seeds-xyz.md" in findings[0].message

    def test_a_directional_edge_needs_its_named_inverse_not_a_copy(self, tmp_path):
        """§5.2: `questions` is stored as `questioned-by` at the far end."""
        asker = record(
            "seeds-abc",
            relationships=[SeedEdge("seeds-xyz", RelationType.QUESTIONS, EDGE_AT)],
        )
        asked = record(
            "seeds-xyz",
            relationships=[SeedEdge("seeds-abc", RelationType.QUESTIONS, EDGE_AT)],
        )
        seeds_dir = store(tmp_path, asker, asked)
        findings = check_violations(seeds_dir, now=NOW)
        assert codes(findings) == ["one-sided-edge", "one-sided-edge"]

    def test_the_two_ends_must_carry_the_same_created_at(self, tmp_path):
        other_stamp = EDGE_AT + timedelta(seconds=5)
        one = record(
            "seeds-abc",
            relationships=[SeedEdge("seeds-xyz", RelationType.RELATES_TO, EDGE_AT)],
        )
        two = record(
            "seeds-xyz",
            relationships=[SeedEdge("seeds-abc", RelationType.RELATES_TO, other_stamp)],
        )
        seeds_dir = store(tmp_path, one, two)
        findings = check_violations(seeds_dir, now=NOW)
        assert codes(findings) == [
            "edge-timestamp-mismatch",
            "edge-timestamp-mismatch",
        ]


# --- What must NOT fire ------------------------------------------------------


class TestNoFalsePositives:
    """The shapes that look wrong and are not. A noisy gate gets bypassed."""

    def test_empty_body_is_not_a_violation(self, tmp_path):
        """Ruled 2026-08-31: a smell (seeds-4co.4), because `seeds jot` makes
        title-only seeds by design and 31 of 314 real seeds have none."""
        seeds_dir = store(tmp_path, record(body=""))
        assert check_violations(seeds_dir, now=NOW) == []

    def test_non_canonical_bytes_are_not_a_violation(self, tmp_path):
        """282 of 314 records differ from canonical form by a trailing newline
        alone; as a violation that is the empty-body mistake again."""
        seeds_dir = store(tmp_path, record("seeds-ok"))
        write_raw(
            seeds_dir,
            "seeds-abc.md",
            frontmatter() + "\n\n\n",
        )
        assert check_violations(seeds_dir, now=NOW) == []

    @pytest.mark.parametrize(
        "title",
        [
            "Move the store to https://example.com/spec",
            "seeds/beads split",
            "Rework db.py",
            "3.11",
            "Storage: files, not SQLite",
            "Why does .seeds/seeds.jsonl still exist?",
        ],
    )
    def test_prose_titles_are_left_alone(self, tmp_path, title):
        seeds_dir = store(tmp_path, record(title=title))
        assert check_violations(seeds_dir, now=NOW) == []

    def test_a_setext_underline_is_not_a_conflict_marker(self, tmp_path):
        body = "A heading\n=======\n\nText below.\n"
        seeds_dir = store(tmp_path, record(body=body))
        assert check_violations(seeds_dir, now=NOW) == []

    def test_a_resolution_on_a_non_terminal_seed_is_not_a_violation(self, tmp_path):
        """§3 calls it a smell -- usually a seed someone reopened."""
        seeds_dir = store(tmp_path, record(resolution="Settled by seeds-sdhc."))
        assert check_violations(seeds_dir, now=NOW) == []

    def test_a_non_standard_type_is_not_a_violation(self, tmp_path):
        """§3: `type` is open, `status` is closed. The asymmetry is deliberate."""
        seeds_dir = store(tmp_path, record(seed_type="postmortem"))
        assert check_violations(seeds_dir, now=NOW) == []


# --- The store itself, and the report ----------------------------------------


class TestStoreAndReport:
    def test_a_missing_store_is_named_not_silently_clean(self, tmp_path):
        findings = check_violations(tmp_path / ".seeds", now=NOW)
        assert codes(findings) == ["store-missing"]

    def test_an_empty_store_is_clean(self, tmp_path):
        (tmp_path / ".seeds" / "seeds").mkdir(parents=True)
        assert check_violations(tmp_path / ".seeds", now=NOW) == []

    def test_every_finding_names_a_file_and_a_fix(self, tmp_path):
        seeds_dir = store(
            tmp_path,
            record("seeds-abc", title="/tmp/x.md"),
            record("seeds-xyz", created_at=UPDATED, updated_at=CREATED),
        )
        write_raw(seeds_dir, "seeds-bad.md", frontmatter(id="seeds-bad", status="huh"))
        findings = check_violations(seeds_dir, now=NOW)
        assert len(findings) == 3
        for finding in findings:
            assert finding.path.name.endswith(".md")
            assert finding.message
            assert finding.remediation

    def test_the_report_shows_the_file_the_code_and_the_fix(self, tmp_path):
        seeds_dir = store(tmp_path, record(title="/tmp/x.md"))
        report = format_findings(check_violations(seeds_dir, now=NOW))
        assert "seeds-abc.md" in report
        assert "title-is-path" in report
        assert "git log -p" in report


class TestCli:
    def test_clean_store_exits_zero(self, tmp_path, cli_runner, monkeypatch):
        store(tmp_path, record())
        monkeypatch.chdir(tmp_path)
        from seeds.cli import main

        result = cli_runner.invoke(main, ["check"])
        assert result.exit_code == 0, result.output
        assert "no violations" in result.output

    def test_a_violation_exits_non_zero(self, tmp_path, cli_runner, monkeypatch):
        store(tmp_path, record(title="/tmp/scratch/notes.md"))
        monkeypatch.chdir(tmp_path)
        from seeds.cli import main

        result = cli_runner.invoke(main, ["check"])
        assert result.exit_code == 1
        assert "title-is-path" in result.output
        assert "1 violation(s)" in result.output
