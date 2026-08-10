"""Tests for optional bead-ID loading (seeds.beads).

Beads is never a dependency: the three states that matter are the export being
absent (the normal case for a project with no beads), present and valid, and
present but unusable. Only the middle one may contribute IDs; the other two
must degrade silently to "no bead IDs known". See bead seeds-90o.
"""

import json

import pytest

from seeds.beads import beads_issues_path, load_bead_ids


@pytest.fixture
def project(tmp_path):
    """A project root with a .seeds/ directory and no .beads/ yet."""
    seeds_dir = tmp_path / ".seeds"
    seeds_dir.mkdir()
    return seeds_dir


def _write_beads(seeds_dir, text):
    path = beads_issues_path(seeds_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _issue_line(issue_id, **extra):
    return json.dumps({"_type": "issue", "id": issue_id, **extra})


class TestBeadsIssuesPath:
    """The export is located from the seeds dir's parent, not the cwd."""

    def test_path_is_sibling_of_seeds_dir(self, project):
        assert beads_issues_path(project) == project.parent / ".beads" / "issues.jsonl"

    def test_path_ignores_cwd(self, project, tmp_path, monkeypatch):
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        monkeypatch.chdir(elsewhere)
        assert beads_issues_path(project).parent.parent == project.parent


class TestLoadBeadIdsAbsent:
    """No beads at all — the normal case, and never an error."""

    def test_no_beads_dir(self, project):
        assert load_bead_ids(project) == set()

    def test_beads_dir_without_export(self, project):
        (project.parent / ".beads").mkdir()
        assert load_bead_ids(project) == set()

    def test_export_is_a_directory(self, project):
        beads_issues_path(project).mkdir(parents=True)
        assert load_bead_ids(project) == set()


class TestLoadBeadIdsValid:
    """A well-formed export contributes every issue's id."""

    def test_reads_ids(self, project):
        _write_beads(
            project,
            "\n".join(
                [
                    _issue_line("seeds-mlj", title="Hash IDs"),
                    _issue_line("seeds-230", status="open"),
                    _issue_line("seeds-90o"),
                ]
            )
            + "\n",
        )
        assert load_bead_ids(project) == {"seeds-mlj", "seeds-230", "seeds-90o"}

    def test_blank_lines_and_missing_trailing_newline(self, project):
        _write_beads(
            project,
            "\n\n" + _issue_line("seeds-abc") + "\n\n" + _issue_line("seeds-1"),
        )
        assert load_bead_ids(project) == {"seeds-abc", "seeds-1"}

    def test_empty_file(self, project):
        _write_beads(project, "")
        assert load_bead_ids(project) == set()


class TestLoadBeadIdsCorrupt:
    """Anything unusable degrades to an empty set rather than raising."""

    def test_not_json_at_all(self, project):
        _write_beads(project, "not json\n")
        assert load_bead_ids(project) == set()

    def test_json_but_not_an_object(self, project):
        _write_beads(project, '["seeds-1", "seeds-2"]\n')
        assert load_bead_ids(project) == set()

    def test_truncated_line(self, project):
        _write_beads(project, '{"_type":"issue","id":"seeds-abc"')
        assert load_bead_ids(project) == set()

    def test_records_without_usable_ids(self, project):
        _write_beads(
            project,
            '{"_type":"issue"}\n{"id":null}\n{"id":42}\n{"id":""}\n',
        )
        assert load_bead_ids(project) == set()

    def test_partial_corruption_keeps_good_lines(self, project):
        _write_beads(
            project,
            "not json\n" + _issue_line("seeds-230") + "\n{oops\n",
        )
        assert load_bead_ids(project) == {"seeds-230"}

    def test_binary_garbage(self, project):
        path = beads_issues_path(project)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\xff\xfe\x00\x80binary")
        assert load_bead_ids(project) == set()
