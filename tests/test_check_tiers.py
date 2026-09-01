"""Tests for ``seeds check --smells`` and ``seeds check --against-git``.

Beads ``seeds-4co.4`` and ``seeds-4co.5``. Both tiers are *detectors*, and the
data-pipeline standard applies in full: the code deciding "clean" is itself
code that can be silently wrong, so nothing here asks a checker to agree with
itself. Every fixture is hand-built and every expectation is hand-computed —
83 of 306 is 27.1%, 20 of 100 is 20%, 19 of 100 is 19% — and written down as
the assertion.

The false-positive suites carry the most weight, and for opposite reasons.

* A **smell** that fires on healthy records is worse than no smell, because the
  tier's whole claim is that it is safe to read every day. ``--smells`` already
  stands at 32 entries on this repo's real corpus (25 title-only seeds, 7
  bodies duplicated by the old "Abandoned: consolidated into …" stubs); if
  ordinary seeds joined them nobody would read the list again.
* An **--against-git** false positive is worse still, because that tier *gates*
  a commit. A reordered tag block or an ordinary one-seed edit that demanded a
  human decision would train everyone to pass ``--no-verify``, which is exactly
  how the seeds-wurl sweep would go through unread a second time.

Every git call goes through ``tests.githelpers``; ``tests/test_git_single_door``
fails this file at the AST level otherwise.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from seeds.check import (
    Finding,
    GitUnavailable,
    check_against_git,
    check_smells,
    check_violations,
    format_findings,
)
from seeds.models import SeedStatus
from seeds.seedfile import SeedRecord, read_seed_file, write_seed
from tests.githelpers import git, git_init

NOW = datetime(2026, 8, 31, 12, 0, 0, tzinfo=UTC)
CREATED = datetime(2026, 8, 28, 14, 2, 11, 481293, tzinfo=UTC)
UPDATED = datetime(2026, 8, 30, 9, 41, 7, 220118, tzinfo=UTC)

# 100 paragraphs of 24 bytes each = 2400 bytes, comfortably over the 2000-byte
# LONG_BODY_BYTES threshold and computed here rather than guessed at.
LONG_BODY = "Deliberation paragraph.\n" * 100
SHORT_BODY = "One line of thinking.\n"


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
        "body": SHORT_BODY,
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


def ids_for(findings: list[Finding], code: str) -> list[str]:
    return sorted(f.seed_id or "" for f in findings if f.code == code)


# --- The smells tier ---------------------------------------------------------


class TestEmptyBodySmell:
    """Moved here from violations by ruling (@aguynamedryan, 2026-08-31)."""

    def test_a_title_only_seed_is_a_smell(self, tmp_path):
        seeds_dir = store(tmp_path, record(body=""))
        assert codes(check_smells(seeds_dir)) == ["empty-body"]

    def test_it_is_not_also_a_violation(self, tmp_path):
        """The whole point of the ruling: `seeds jot` makes these by design."""
        seeds_dir = store(tmp_path, record(body=""))
        assert check_violations(seeds_dir, now=NOW) == []

    def test_a_whitespace_only_body_counts_as_empty(self, tmp_path):
        seeds_dir = store(tmp_path, record(body="   \n\n\t\n"))
        assert codes(check_smells(seeds_dir)) == ["empty-body"]

    def test_a_seed_with_a_body_is_not_flagged(self, tmp_path):
        seeds_dir = store(tmp_path, record(body="Real deliberation.\n"))
        assert check_smells(seeds_dir) == []

    def test_every_empty_seed_is_named_individually(self, tmp_path):
        seeds_dir = store(
            tmp_path,
            record("seeds-aaa", body=""),
            record("seeds-bbb", body=""),
            record("seeds-ccc", body="Has a body.\n"),
        )
        findings = check_smells(seeds_dir)
        assert ids_for(findings, "empty-body") == ["seeds-aaa", "seeds-bbb"]


class TestDuplicateBodySmell:
    def test_two_byte_identical_bodies_are_both_reported(self, tmp_path):
        body = "Abandoned: consolidated into seeds-91f2.\n"
        seeds_dir = store(
            tmp_path, record("seeds-aaa", body=body), record("seeds-bbb", body=body)
        )
        findings = check_smells(seeds_dir)
        assert codes(findings) == ["duplicate-body", "duplicate-body"]
        assert ids_for(findings, "duplicate-body") == ["seeds-aaa", "seeds-bbb"]

    def test_each_finding_names_the_others(self, tmp_path):
        body = "The same deliberation, twice.\n"
        seeds_dir = store(
            tmp_path,
            record("seeds-aaa", body=body),
            record("seeds-bbb", body=body),
            record("seeds-ccc", body=body),
        )
        findings = check_smells(seeds_dir)
        assert len(findings) == 3
        for finding in findings:
            assert "2 other seed(s)" in finding.message
            others = {"seeds-aaa", "seeds-bbb", "seeds-ccc"} - {finding.seed_id}
            for other in others:
                assert other in finding.message

    def test_a_one_byte_difference_is_not_a_duplicate(self, tmp_path):
        seeds_dir = store(
            tmp_path,
            record("seeds-aaa", body="Same thought.\n"),
            record("seeds-bbb", body="Same thought!\n"),
        )
        assert check_smells(seeds_dir) == []

    def test_empty_bodies_are_not_reported_as_duplicates_of_each_other(self, tmp_path):
        """25 of this repo's seeds have none; pairing them would be 300 findings."""
        seeds_dir = store(
            tmp_path,
            record("seeds-aaa", body=""),
            record("seeds-bbb", body=""),
            record("seeds-ccc", body=""),
        )
        assert codes(check_smells(seeds_dir)) == ["empty-body"] * 3


class TestUnsupersededLongBodySmell:
    """Long AND much-edited AND unmarked. Any one of the three alone is fine."""

    def build(self, tmp_path: Path, body: str, *, commits: int) -> Path:
        """A repo whose one seed has been touched by ``commits`` commits."""
        git_init(tmp_path)
        seeds_dir = store(tmp_path, record("seeds-aaa", body=body))
        for n in range(commits):
            path = seeds_dir / "seeds" / "seeds-aaa.md"
            path.write_text(
                path.read_text(encoding="utf-8") + f"\nEdit {n}.\n", encoding="utf-8"
            )
            git(tmp_path, "add", "-A")
            git(tmp_path, "commit", "-q", "-m", f"edit {n}")
        return seeds_dir

    def test_long_and_much_edited_and_unmarked_is_a_smell(self, tmp_path):
        seeds_dir = self.build(tmp_path, LONG_BODY, commits=5)
        findings = check_smells(seeds_dir)
        assert codes(findings) == ["unsuperseded-long-body"]
        assert "5 commits" in findings[0].message

    def test_a_long_body_with_few_commits_is_not_flagged(self, tmp_path):
        """Four commits is under the threshold; the smell is about history."""
        seeds_dir = self.build(tmp_path, LONG_BODY, commits=4)
        assert check_smells(seeds_dir) == []

    def test_a_short_body_with_many_commits_is_not_flagged(self, tmp_path):
        seeds_dir = self.build(tmp_path, SHORT_BODY, commits=8)
        assert check_smells(seeds_dir) == []

    def test_a_supersede_marker_anywhere_in_the_body_clears_it(self, tmp_path):
        body = (
            "## Dolt would give us cell-level merge\n"
            "> [!SUPERSEDED] 2026-08-28 — ordinary git line-merge surfaces the "
            "same collisions.\n\n" + LONG_BODY
        )
        seeds_dir = self.build(tmp_path, body, commits=8)
        assert check_smells(seeds_dir) == []

    def test_outside_a_git_repo_the_smell_is_silent_not_guessed(self, tmp_path):
        """Without history there is no second half of the AND to test."""
        seeds_dir = store(tmp_path, record("seeds-aaa", body=LONG_BODY))
        assert check_smells(seeds_dir) == []

    def test_an_uncommitted_seed_has_no_history_and_is_not_flagged(self, tmp_path):
        git_init(tmp_path)
        seeds_dir = store(tmp_path, record("seeds-aaa", body=LONG_BODY))
        git(tmp_path, "add", "-A")
        git(tmp_path, "commit", "-q", "-m", "first")
        write_seed(seeds_dir, record("seeds-bbb", body=LONG_BODY + "Distinct.\n"))
        assert check_smells(seeds_dir) == []


class TestSmellFalsePositives:
    """Healthy records that a careless tier would report."""

    def test_a_clean_store_has_no_smells(self, tmp_path):
        seeds_dir = store(
            tmp_path,
            record("seeds-aaa", body="One thought.\n"),
            record("seeds-bbb", body="A different thought.\n"),
            record("seeds-ccc", body=LONG_BODY),
        )
        assert check_smells(seeds_dir) == []

    def test_a_missing_store_is_not_a_smell(self, tmp_path):
        """`store-missing` is the violations tier's finding, not this one's."""
        assert check_smells(tmp_path / ".seeds") == []

    def test_an_unparseable_file_is_not_reported_twice(self, tmp_path):
        """It is a violation; repeating it here would double-count the corpus."""
        seeds_dir = store(tmp_path, record("seeds-aaa", body="Fine.\n"))
        (seeds_dir / "seeds" / "seeds-bad.md").write_text(
            "not frontmatter at all\n", encoding="utf-8"
        )
        assert check_smells(seeds_dir) == []
        assert check_violations(seeds_dir, now=NOW) != []


class TestSmellsNeverFail:
    def test_smells_alone_exit_zero(self, tmp_path, cli_runner, monkeypatch):
        body = "Duplicated deliberation.\n"
        store(
            tmp_path,
            record("seeds-aaa", body=""),
            record("seeds-bbb", body=body),
            record("seeds-ccc", body=body),
        )
        monkeypatch.chdir(tmp_path)
        from seeds.cli import main

        result = cli_runner.invoke(main, ["check", "--smells"])
        assert result.exit_code == 0, result.output
        assert "3 smell(s)" in result.output
        assert "never a failure" in result.output
        assert "empty-body" in result.output
        assert "duplicate-body" in result.output

    def test_the_exit_code_still_comes_from_the_violations(
        self, tmp_path, cli_runner, monkeypatch
    ):
        store(tmp_path, record("seeds-aaa", title="/tmp/scratch/notes.md", body=""))
        monkeypatch.chdir(tmp_path)
        from seeds.cli import main

        result = cli_runner.invoke(main, ["check", "--smells"])
        assert result.exit_code == 1
        assert "1 violation(s)" in result.output
        assert "1 smell(s)" in result.output

    def test_no_smells_still_says_so(self, tmp_path, cli_runner, monkeypatch):
        store(tmp_path, record(body="A body.\n"))
        monkeypatch.chdir(tmp_path)
        from seeds.cli import main

        result = cli_runner.invoke(main, ["check", "--smells"])
        assert result.exit_code == 0, result.output
        assert "0 smell(s)" in result.output

    def test_the_report_marks_smells_differently_from_violations(self, tmp_path):
        seeds_dir = store(tmp_path, record(body=""))
        report = format_findings(check_smells(seeds_dir), marker="⚠")
        assert "⚠ empty-body" in report
        assert "✗" not in report


class TestThereIsNoTendVerb:
    """@aguynamedryan, 2026-08-31: 'let's remove suggest/tend for now'.

    It was never built, and this tier is what survives of it. A future agent
    reading seeds-sdhc.2 could easily file the verb as a gap; this is the line
    that says it is not one.
    """

    def test_the_cli_has_no_tend_command(self, cli_runner):
        from seeds.cli import main

        result = cli_runner.invoke(main, ["--help"])
        assert "tend" not in result.output
        assert "tend" not in main.commands

    def test_the_smells_tier_is_where_its_function_went(self, cli_runner):
        """`seeds check --smells` is the surviving half: noticing, not editing.

        `suggest` is a different, pre-existing command -- similarity search
        over seeds -- and retiring it was not part of either bead, so it is
        deliberately left alone here.
        """
        from seeds.cli import main

        result = cli_runner.invoke(main, ["check", "--help"])
        assert "--smells" in result.output


class TestResolutionOnNonTerminalSmell:
    """§3: "carrying one on a non-terminal seed is a smell rather than a violation".

    Stated in the spec since the format was frozen and enforced by nothing
    until ``seeds-4co.16``. The interesting half is the false-positive half:
    the reopened seed §3 describes is *correct*, and every terminal seed with a
    resolution — which is most of the resolved corpus — has to stay silent.
    """

    RESOLUTION = "Settled: files-as-truth, one file per seed."

    def test_a_captured_seed_carrying_a_resolution_is_a_smell(self, tmp_path):
        seeds_dir = store(
            tmp_path,
            record(status=SeedStatus.CAPTURED, resolution=self.RESOLUTION),
        )
        findings = check_smells(seeds_dir)
        assert codes(findings) == ["resolution-on-non-terminal"]
        assert "status is captured" in findings[0].message
        assert "files-as-truth" in findings[0].message

    @pytest.mark.parametrize(
        "status", [SeedStatus.CAPTURED, SeedStatus.EXPLORING, SeedStatus.DEFERRED]
    )
    def test_every_non_terminal_status_is_reported(self, tmp_path, status):
        seeds_dir = store(tmp_path, record(status=status, resolution=self.RESOLUTION))
        assert codes(check_smells(seeds_dir)) == ["resolution-on-non-terminal"]

    @pytest.mark.parametrize("status", [SeedStatus.RESOLVED, SeedStatus.ABANDONED])
    def test_a_terminal_seed_with_a_resolution_is_silent(self, tmp_path, status):
        """The ordinary shape of every resolved seed. Firing here ends the tier."""
        seeds_dir = store(
            tmp_path,
            record(status=status, resolved_at=UPDATED, resolution=self.RESOLUTION),
        )
        assert check_smells(seeds_dir) == []

    def test_a_non_terminal_seed_with_no_resolution_is_silent(self, tmp_path):
        seeds_dir = store(tmp_path, record(status=SeedStatus.EXPLORING))
        assert check_smells(seeds_dir) == []

    def test_an_empty_resolution_string_is_not_a_resolution(self, tmp_path):
        """§3: absent and empty are the same state, and the writer omits it."""
        seeds_dir = store(tmp_path, record(status=SeedStatus.EXPLORING, resolution=""))
        assert check_smells(seeds_dir) == []

    def test_it_is_not_also_a_violation(self, tmp_path):
        seeds_dir = store(
            tmp_path,
            record(status=SeedStatus.CAPTURED, resolution=self.RESOLUTION),
        )
        assert check_violations(seeds_dir, now=NOW) == []


class TestNonCanonicalBytesSmell:
    """The positive assertion that no tool has rewritten a seed (seeds-dv6r).

    ruff 0.16 formats Python code blocks inside markdown; the night this repo's
    store was converted its file count went 65 -> 385 and it offered to
    reformat ``seeds-154.md``. Excluding ruff is one layer; this is the layer
    that notices whatever the next tool turns out to be.
    """

    def path_of(self, seeds_dir: Path, seed_id: str = "seeds-abc") -> Path:
        return seeds_dir / "seeds" / f"{seed_id}.md"

    def test_a_file_written_by_the_writer_is_canonical(self, tmp_path):
        seeds_dir = store(tmp_path, record(body="Real deliberation.\n"))
        assert check_smells(seeds_dir) == []

    def test_a_second_trailing_newline_is_a_smell(self, tmp_path):
        """§2: the file ends with exactly one newline."""
        seeds_dir = store(tmp_path, record(body="Real deliberation.\n"))
        path = self.path_of(seeds_dir)
        path.write_bytes(path.read_bytes() + b"\n")
        findings = check_smells(seeds_dir)
        assert codes(findings) == ["non-canonical-bytes"]
        assert "1 trailing line(s)" in findings[0].message

    def test_crlf_stays_a_violation_and_is_not_reported_here(self, tmp_path):
        """§2 says LF, and the reader refuses CRLF outright — so it never
        reaches this tier.

        Worth pinning rather than assuming: the two rules overlap, and a file
        counted once as a violation and again as a smell would make the corpus
        look worse than it is.
        """
        seeds_dir = store(tmp_path, record(body="Real deliberation.\n"))
        path = self.path_of(seeds_dir)
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        assert check_smells(seeds_dir) == []
        assert codes(check_violations(seeds_dir, now=NOW)) == ["parse-error"]

    def test_reordered_frontmatter_keys_are_a_smell(self, tmp_path):
        """§3: order is not semantic for a reader, but a writer must produce it.

        The file still parses and every value is right — which is exactly why
        this belongs to smells and why nothing else in the module notices it.
        """
        seeds_dir = store(tmp_path, record(body="Real deliberation.\n"))
        path = self.path_of(seeds_dir)
        text = path.read_text(encoding="utf-8")
        lines = text.split("\n")
        # Hand-computed: line 0 is '---', 1 is id, 2 is title, 3 is status.
        assert lines[2].startswith("title:") and lines[3].startswith("status:")
        lines[2], lines[3] = lines[3], lines[2]
        path.write_text("\n".join(lines), encoding="utf-8")
        findings = check_smells(seeds_dir)
        assert codes(findings) == ["non-canonical-bytes"]
        assert "line 3" in findings[0].message

    def test_an_extra_blank_line_under_the_frontmatter_is_a_smell(self, tmp_path):
        """§2: exactly one blank line separates the closing --- from the body.

        The reader normalizes leading blank lines away, so the file still reads
        back correctly and nothing else in the module notices — which is both
        why this rule exists and why it cannot gate.
        """
        seeds_dir = store(tmp_path, record(body="Real deliberation.\n"))
        path = self.path_of(seeds_dir)
        path.write_text(
            path.read_text(encoding="utf-8").replace("---\n\n", "---\n\n\n", 1),
            encoding="utf-8",
        )
        findings = check_smells(seeds_dir)
        assert codes(findings) == ["non-canonical-bytes"]
        assert "seeds-dv6r" in findings[0].remediation

    def test_a_body_rewritten_within_canonical_layout_is_NOT_caught(self, tmp_path):
        """The measured limit of this rule, pinned so nobody over-trusts it.

        The comparison is the file against the canonical render *of what the
        file now says*, so a tool that rewrites body content while leaving the
        layout canonical — ruff 0.16 reformatting a Python block inside a
        markdown body is exactly that shape, and so is trimming trailing
        whitespace off a body line — leaves nothing here to see. That case
        belongs to ``--against-git``, which compares the body field itself.
        This rule catches the serialization half: trailing newlines, the blank
        lines around the body, frontmatter key order and scalar encoding.
        """
        body = "Consider:\n\n```python\nx = {'a':1}\n```\n"
        seeds_dir = store(tmp_path, record(body=body))
        path = self.path_of(seeds_dir)
        path.write_text(
            path.read_text(encoding="utf-8").replace("x = {'a':1}", 'x = {"a": 1}'),
            encoding="utf-8",
        )
        assert check_smells(seeds_dir) == []

    def test_it_is_not_a_violation(self, tmp_path):
        seeds_dir = store(tmp_path, record(body="Real deliberation.\n"))
        path = self.path_of(seeds_dir)
        path.write_bytes(path.read_bytes() + b"\n")
        assert check_violations(seeds_dir, now=NOW) == []

    def test_blank_lines_the_reader_normalizes_are_still_reported(self, tmp_path):
        """The reason this cannot gate: the file reads back fine either way.

        282 of the 314 pre-conversion records differed from canonical form by a
        trailing newline alone, so as a violation this would have failed on
        90% of a healthy corpus.
        """
        seeds_dir = store(tmp_path, record(body="Real deliberation.\n"))
        path = self.path_of(seeds_dir)
        path.write_bytes(path.read_bytes() + b"\n\n\n")
        assert read_seed_file(path).body.strip() == "Real deliberation."
        assert codes(check_smells(seeds_dir)) == ["non-canonical-bytes"]

    def test_an_unwritable_record_is_skipped_not_reported(self, tmp_path):
        """A parent that disagrees with the id: a violation, with no canonical form.

        ``render_seed_file`` validates before it renders, so there is nothing to
        compare against; reporting it here would double-count the one file.
        """
        seeds_dir = store(tmp_path, record("seeds-aaa", body="Fine.\n"))
        path = seeds_dir / "seeds" / "seeds-aaa.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "status:", "parent: seeds-zzz\nstatus:"
            ),
            encoding="utf-8",
        )
        assert check_smells(seeds_dir) == []
        assert "parent-mismatch" in codes(check_violations(seeds_dir, now=NOW))


class TestToolConfigSmell:
    """@aguynamedryan, 2026-09-01: assert the repo's tools skip the store.

    The store looks like 309 markdown files to every formatter and linter in
    the repo. ruff found it within minutes of conversion; the point of this
    rule is to have said so before the next tool does.
    """

    def build(self, tmp_path: Path, **files: str) -> Path:
        seeds_dir = store(tmp_path, record(body="A body.\n"))
        for name, text in files.items():
            (tmp_path / name.replace("__", ".")).write_text(text, encoding="utf-8")
        return seeds_dir

    RUFF_BARE = "[tool.ruff]\nline-length = 88\n"
    RUFF_EXCLUDING = '[tool.ruff]\nline-length = 88\nextend-exclude = [".seeds/"]\n'

    def test_ruff_configured_without_an_exclusion_is_a_smell(self, tmp_path):
        seeds_dir = self.build(tmp_path, pyproject__toml=self.RUFF_BARE)
        findings = check_smells(seeds_dir)
        assert codes(findings) == ["tool-config-includes-store"]
        assert "ruff" in findings[0].message
        assert findings[0].path == tmp_path / "pyproject.toml"

    def test_ruff_excluding_the_store_is_silent(self, tmp_path):
        """This repo's own state since the night of the conversion."""
        seeds_dir = self.build(tmp_path, pyproject__toml=self.RUFF_EXCLUDING)
        assert check_smells(seeds_dir) == []

    def test_a_ruff_toml_carries_the_exclusion_too(self, tmp_path):
        seeds_dir = self.build(tmp_path, ruff__toml='extend-exclude = [".seeds/"]\n')
        assert check_smells(seeds_dir) == []

    def test_a_bare_ruff_toml_is_a_smell(self, tmp_path):
        seeds_dir = self.build(tmp_path, ruff__toml="line-length = 88\n")
        findings = check_smells(seeds_dir)
        assert codes(findings) == ["tool-config-includes-store"]
        assert findings[0].path == tmp_path / "ruff.toml"

    def test_prettier_with_no_ignore_file_is_a_smell(self, tmp_path):
        """prettier's config carries no exclusion at all — the ignore file does."""
        seeds_dir = self.build(tmp_path, __prettierrc='{"semi": false}\n')
        findings = check_smells(seeds_dir)
        assert codes(findings) == ["tool-config-includes-store"]
        assert "prettier" in findings[0].message

    def test_prettier_with_the_store_in_its_ignore_file_is_silent(self, tmp_path):
        seeds_dir = self.build(
            tmp_path,
            __prettierrc='{"semi": false}\n',
            __prettierignore="node_modules/\n.seeds/\n",
        )
        assert check_smells(seeds_dir) == []

    def test_markdownlint_and_editorconfig_are_both_covered(self, tmp_path):
        """Two configs, two findings — the report names each tool separately."""
        seeds_dir = self.build(
            tmp_path,
            __markdownlint__json='{"MD013": false}\n',
            __editorconfig="[*]\ntrim_trailing_whitespace = true\n",
        )
        findings = check_smells(seeds_dir)
        assert codes(findings) == ["tool-config-includes-store"] * 2
        reported = " ".join(finding.message for finding in findings)
        assert "markdownlint" in reported
        assert "EditorConfig" in reported

    def test_a_repo_with_no_such_config_is_silent(self, tmp_path):
        seeds_dir = self.build(tmp_path)
        assert check_smells(seeds_dir) == []

    def test_tools_that_never_see_the_store_are_not_reported(self, tmp_path):
        """mypy and pytest are configured in this repo's pyproject too.

        They are pointed at a path list and never walk .seeds/, so a finding
        about them would name no fix — and a tier that reports unfixable things
        stops being read.
        """
        seeds_dir = self.build(
            tmp_path,
            pyproject__toml=(
                "[tool.mypy]\nstrict = true\n\n"
                '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n\n'
                '[tool.hatch.version]\npath = "src/seeds/__init__.py"\n'
            ),
        )
        assert check_smells(seeds_dir) == []

    def test_an_unparseable_pyproject_is_not_this_check_s_business(self, tmp_path):
        seeds_dir = self.build(tmp_path, pyproject__toml="[tool.ruff\nbroken = \n")
        assert check_smells(seeds_dir) == []

    def test_it_is_not_a_violation(self, tmp_path):
        seeds_dir = self.build(tmp_path, pyproject__toml=self.RUFF_BARE)
        assert check_violations(seeds_dir, now=NOW) == []

    def test_the_remediation_names_the_knob_to_set(self, tmp_path):
        seeds_dir = self.build(tmp_path, pyproject__toml=self.RUFF_BARE)
        remediation = check_smells(seeds_dir)[0].remediation
        assert "extend-exclude" in remediation
        assert "seeds-dv6r" in remediation


# --- The against-git tier ----------------------------------------------------


def corpus(tmp_path: Path, count: int, **overrides: object) -> Path:
    """A committed store of ``count`` seeds, ids ``seeds-0000``…, in a repo."""
    git_init(tmp_path)
    records = [record(f"seeds-{n:04d}", **overrides) for n in range(count)]
    seeds_dir = store(tmp_path, *records)
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "seed the corpus")
    return seeds_dir


def rewrite_titles(seeds_dir: Path, count: int, title: str) -> None:
    """Replace the title of the first ``count`` seeds, in file order."""
    for path in sorted((seeds_dir / "seeds").glob("*.md"))[:count]:
        lines = path.read_text(encoding="utf-8").split("\n")
        for n, line in enumerate(lines):
            if line.startswith("title:"):
                lines[n] = f"title: {title}"
                break
        path.write_text("\n".join(lines), encoding="utf-8")


class TestTheWurlShape:
    """The incident, reproduced at its real size: 83 titles of 306, one commit."""

    def test_a_mass_title_rewrite_in_one_commit_is_flagged(self, tmp_path):
        seeds_dir = corpus(tmp_path, 306)
        rewrite_titles(seeds_dir, 83, "/tmp/claude-scratch/notes.md")
        git(tmp_path, "add", "-A")
        git(tmp_path, "commit", "-q", "-m", "the sweep")

        comparison = check_against_git(seeds_dir)

        assert comparison.corpus == 306
        assert comparison.before == "HEAD~1"
        assert comparison.after == "HEAD"
        assert codes(comparison.findings) == ["mass-field-rewrite"]
        # 83 / 306 = 27.1%, hand-computed from the incident's own numbers.
        assert "title differs on 83 of 306 seeds (27% of the corpus" in (
            comparison.findings[0].message
        )
        assert "83 rewritten" in comparison.findings[0].message

    def test_only_the_field_that_moved_is_named(self, tmp_path):
        """A per-field score, not "83 files changed" -- that is the whole idea."""
        seeds_dir = corpus(tmp_path, 306)
        rewrite_titles(seeds_dir, 83, "/tmp/claude-scratch/notes.md")
        git(tmp_path, "add", "-A")
        git(tmp_path, "commit", "-q", "-m", "the sweep")

        findings = check_against_git(seeds_dir).findings
        assert len(findings) == 1
        for other in ("status", "body", "created_at", "type"):
            assert f"{other} differs" not in findings[0].message

    def test_the_finding_says_how_to_get_the_titles_back(self, tmp_path):
        seeds_dir = corpus(tmp_path, 306)
        rewrite_titles(seeds_dir, 83, "/tmp/claude-scratch/notes.md")
        git(tmp_path, "add", "-A")
        git(tmp_path, "commit", "-q", "-m", "the sweep")

        finding = check_against_git(seeds_dir).findings[0]
        assert "git diff HEAD~1 -- .seeds/seeds" in finding.remediation
        assert "git checkout HEAD~1 -- .seeds/seeds" in finding.remediation

    def test_the_same_sweep_uncommitted_is_caught_before_it_lands(self, tmp_path):
        """The hook case: HEAD is the previous commit, the sweep is on disk."""
        seeds_dir = corpus(tmp_path, 306)
        rewrite_titles(seeds_dir, 83, "/tmp/claude-scratch/notes.md")

        comparison = check_against_git(seeds_dir)
        assert comparison.before == "HEAD"
        assert comparison.after == "the working tree"
        assert codes(comparison.findings) == ["mass-field-rewrite"]


class TestAgainstGitFalsePositives:
    """A gate that fires on ordinary work is a gate everybody bypasses."""

    def test_an_ordinary_single_seed_edit_is_not_flagged(self, tmp_path):
        seeds_dir = corpus(tmp_path, 306)
        rewrite_titles(seeds_dir, 1, "A title someone actually rewrote")

        comparison = check_against_git(seeds_dir)
        assert comparison.corpus == 306
        assert comparison.findings == []

    def test_an_unchanged_store_is_clean(self, tmp_path):
        seeds_dir = corpus(tmp_path, 40)
        assert check_against_git(seeds_dir).findings == []

    def test_a_dozen_edits_in_a_306_seed_store_is_not_a_mass_rewrite(self, tmp_path):
        """12 / 306 = 3.9%, well under the 20% the rule asks for."""
        seeds_dir = corpus(tmp_path, 306)
        rewrite_titles(seeds_dir, 12, "A retitled seed")
        assert check_against_git(seeds_dir).findings == []

    def test_a_reordered_tag_block_is_not_a_change(self, tmp_path):
        """Same tags, different order. A no-op must never gate a commit."""
        seeds_dir = corpus(tmp_path, 100, tags=["storage", "format"])
        for path in sorted((seeds_dir / "seeds").glob("*.md")):
            text = path.read_text(encoding="utf-8")
            path.write_text(
                text.replace("  - storage\n  - format\n", "  - format\n  - storage\n"),
                encoding="utf-8",
            )
        comparison = check_against_git(seeds_dir)
        assert comparison.findings == []

    def test_adding_seeds_is_not_a_change_to_the_corpus(self, tmp_path):
        """`seeds jot` in bulk is ordinary; only what existed can be rewritten."""
        seeds_dir = corpus(tmp_path, 100)
        for n in range(100, 200):
            write_seed(seeds_dir, record(f"seeds-{n:04d}"))
        assert check_against_git(seeds_dir).findings == []

    def test_a_single_deleted_seed_is_not_a_mass_change(self, tmp_path):
        seeds_dir = corpus(tmp_path, 100)
        (seeds_dir / "seeds" / "seeds-0000.md").unlink()
        assert check_against_git(seeds_dir).findings == []


class TestTheThresholds:
    """Both halves of the rule, exercised on either side of the line."""

    def test_twenty_of_a_hundred_trips_the_fraction(self, tmp_path):
        seeds_dir = corpus(tmp_path, 100)
        rewrite_titles(seeds_dir, 20, "Rewritten")
        findings = check_against_git(seeds_dir).findings
        assert codes(findings) == ["mass-field-rewrite"]
        assert "20 of 100 seeds (20% of the corpus" in findings[0].message

    def test_nineteen_of_a_hundred_does_not(self, tmp_path):
        seeds_dir = corpus(tmp_path, 100)
        rewrite_titles(seeds_dir, 19, "Rewritten")
        assert check_against_git(seeds_dir).findings == []

    def test_the_absolute_minimum_holds_a_tiny_store_back(self, tmp_path):
        """5 of 20 is 25% -- over the fraction, under the 10-seed floor."""
        seeds_dir = corpus(tmp_path, 20)
        rewrite_titles(seeds_dir, 5, "Rewritten")
        assert check_against_git(seeds_dir).findings == []

    def test_ten_of_twenty_clears_both_halves(self, tmp_path):
        seeds_dir = corpus(tmp_path, 20)
        rewrite_titles(seeds_dir, 10, "Rewritten")
        assert codes(check_against_git(seeds_dir).findings) == ["mass-field-rewrite"]


class TestDeletionsAreSubsumed:
    """There is no delete verb, so `rm` at scale must trip the same rule."""

    def test_a_mass_deletion_counts_against_every_field(self, tmp_path):
        seeds_dir = corpus(tmp_path, 100)
        for path in sorted((seeds_dir / "seeds").glob("*.md"))[:40]:
            path.unlink()

        findings = check_against_git(seeds_dir).findings
        # Every compared field lost 40 of 100 values, so every one is named.
        assert codes(findings) == ["mass-field-rewrite"] * 12
        assert all("40 deleted" in f.message for f in findings)
        assert any("title differs on 40 of 100" in f.message for f in findings)

    def test_the_whole_store_removed_is_flagged_not_read_as_clean(self, tmp_path):
        seeds_dir = corpus(tmp_path, 40)
        for path in (seeds_dir / "seeds").glob("*.md"):
            path.unlink()
        findings = check_against_git(seeds_dir).findings
        assert codes(findings) == ["mass-field-rewrite"] * 12
        assert all("100% of the corpus" in f.message for f in findings)


class TestWhatItCompared:
    """ "No findings" only reassures once you know what was actually compared."""

    def test_a_dirty_store_is_compared_against_head(self, tmp_path):
        seeds_dir = corpus(tmp_path, 20)
        rewrite_titles(seeds_dir, 1, "Edited but not committed")
        comparison = check_against_git(seeds_dir)
        assert (comparison.before, comparison.after) == ("HEAD", "the working tree")

    def test_a_clean_store_falls_back_to_the_commit_that_just_landed(self, tmp_path):
        seeds_dir = corpus(tmp_path, 20)
        rewrite_titles(seeds_dir, 1, "Edited and committed")
        git(tmp_path, "add", "-A")
        git(tmp_path, "commit", "-q", "-m", "second")
        comparison = check_against_git(seeds_dir)
        assert (comparison.before, comparison.after) == ("HEAD~1", "HEAD")

    def test_a_single_commit_repo_has_nothing_earlier_to_fall_back_to(self, tmp_path):
        seeds_dir = corpus(tmp_path, 20)
        comparison = check_against_git(seeds_dir)
        assert (comparison.before, comparison.after) == ("HEAD", "the working tree")
        assert comparison.corpus == 20

    def test_an_unborn_head_is_an_empty_before_state_not_an_error(self, tmp_path):
        git_init(tmp_path)
        seeds_dir = store(tmp_path, record("seeds-aaa"), record("seeds-bbb"))
        comparison = check_against_git(seeds_dir)
        assert comparison.before == "the empty tree"
        assert comparison.corpus == 0
        assert comparison.findings == []

    def test_outside_a_git_repo_it_refuses_rather_than_reporting_clean(self, tmp_path):
        """A comparison that silently could not run is the green-while-broken
        shape this tier exists to prevent."""
        seeds_dir = store(tmp_path, record())
        with pytest.raises(GitUnavailable):
            check_against_git(seeds_dir)


class TestAgainstGitCli:
    def test_the_mass_rewrite_shape_exits_non_zero(
        self, tmp_path, cli_runner, monkeypatch
    ):
        seeds_dir = corpus(tmp_path, 100)
        rewrite_titles(seeds_dir, 40, "Rewritten by a sweep")
        monkeypatch.chdir(tmp_path)
        from seeds.cli import main

        result = cli_runner.invoke(main, ["check", "--against-git"])
        assert result.exit_code == 1, result.output
        assert "mass-field-rewrite" in result.output
        assert "1 mass rewrite(s)" in result.output

    def test_an_ordinary_edit_exits_zero_and_says_what_it_compared(
        self, tmp_path, cli_runner, monkeypatch
    ):
        seeds_dir = corpus(tmp_path, 100)
        rewrite_titles(seeds_dir, 1, "An ordinary retitle")
        monkeypatch.chdir(tmp_path)
        from seeds.cli import main

        result = cli_runner.invoke(main, ["check", "--against-git"])
        assert result.exit_code == 0, result.output
        assert "100 seed(s) at HEAD, compared with the working tree" in result.output

    def test_no_git_is_an_error_not_a_clean_run(
        self, tmp_path, cli_runner, monkeypatch
    ):
        store(tmp_path, record())
        monkeypatch.chdir(tmp_path)
        from seeds.cli import main

        result = cli_runner.invoke(main, ["check", "--against-git"])
        assert result.exit_code == 1
        assert "not inside a git work tree" in result.output

    def test_both_tiers_run_together(self, tmp_path, cli_runner, monkeypatch):
        seeds_dir = corpus(tmp_path, 100, body="")
        rewrite_titles(seeds_dir, 40, "Rewritten by a sweep")
        monkeypatch.chdir(tmp_path)
        from seeds.cli import main

        result = cli_runner.invoke(main, ["check", "--against-git", "--smells"])
        assert result.exit_code == 1, result.output
        assert "mass-field-rewrite" in result.output
        assert "100 smell(s)" in result.output
        assert "never a failure" in result.output

    def test_plain_check_does_neither(self, tmp_path, cli_runner, monkeypatch):
        seeds_dir = corpus(tmp_path, 100, body="")
        rewrite_titles(seeds_dir, 40, "Rewritten by a sweep")
        monkeypatch.chdir(tmp_path)
        from seeds.cli import main

        result = cli_runner.invoke(main, ["check"])
        assert result.exit_code == 0, result.output
        assert "no violations" in result.output
        assert "smell" not in result.output
        assert "against-git" not in result.output
