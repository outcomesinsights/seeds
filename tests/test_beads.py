"""Tests for optional bead-ID loading (seeds.beads).

Beads is never a dependency: the three states that matter are the export being
absent (the normal case for a project with no beads), present and valid, and
present but unusable. Only the middle one may contribute IDs; the other two
must degrade silently to "no bead IDs known". See bead seeds-90o.
"""

import json
import subprocess
from pathlib import Path

import pytest

from seeds.beads import (
    beads_in_use,
    beads_issues_path,
    load_bead_ids,
    query_bead_ids,
)
from tests.beadshelpers import (
    call_lines,
    hide_bd,
    install_fake_bd,
    make_beads_workspace,
)


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


class TestBeadsInUse:
    """ "Beads is in use" means a workspace, not a stray export.

    The distinction gates every ``bd`` invocation: a project with no beads --
    the normal case -- must never spawn a subprocess, and neither must one
    holding only an ``issues.jsonl`` someone copied in.
    """

    def test_no_beads_dir(self, project):
        assert beads_in_use(project) is False

    def test_export_alone_is_not_a_workspace(self, project):
        _write_beads(project, _issue_line("seeds-230") + "\n")
        assert beads_in_use(project) is False

    def test_config_marks_a_workspace(self, project):
        make_beads_workspace(project)
        assert beads_in_use(project) is True

    def test_config_must_be_a_file(self, project):
        (project.parent / ".beads" / "config.yaml").mkdir(parents=True)
        assert beads_in_use(project) is False


class TestQueryBeadIdsNotConsulted:
    """Every route to "beads could not be asked" returns None, never a set.

    None and ``set()`` mean different things to the caller: the first says the
    answer is still coming from the throttled export, the second is beads
    itself saying no such bead. Collapsing them would either hide a stale
    export or invent a denial beads never made.
    """

    def test_no_refs(self, project, tmp_path, monkeypatch):
        make_beads_workspace(project)
        log = install_fake_bd(tmp_path, monkeypatch)
        assert query_bead_ids(project, []) is None
        assert call_lines(log) == []

    def test_no_beads_workspace(self, project, tmp_path, monkeypatch):
        log = install_fake_bd(tmp_path, monkeypatch)
        assert query_bead_ids(project, ["seeds-230"]) is None
        assert call_lines(log) == []

    def test_export_without_workspace_does_not_call_bd(
        self, project, tmp_path, monkeypatch
    ):
        _write_beads(project, _issue_line("seeds-230") + "\n")
        log = install_fake_bd(tmp_path, monkeypatch)
        assert query_bead_ids(project, ["seeds-999"]) is None
        assert call_lines(log) == []

    def test_bd_not_installed(self, project, tmp_path, monkeypatch):
        make_beads_workspace(project)
        hide_bd(monkeypatch, tmp_path)
        assert query_bead_ids(project, ["seeds-230"]) is None

    def test_bd_output_is_not_json(self, project, tmp_path, monkeypatch):
        make_beads_workspace(project)
        install_fake_bd(tmp_path, monkeypatch, stdout="command not found\n")
        assert query_bead_ids(project, ["seeds-230"]) is None

    def test_bd_error_object_of_another_kind(self, project, tmp_path, monkeypatch):
        """An unrecognised error is a failure to consult, not a denial."""
        make_beads_workspace(project)
        install_fake_bd(
            tmp_path,
            monkeypatch,
            stdout=json.dumps({"error": "database is locked"}),
            exit_code=1,
        )
        assert query_bead_ids(project, ["seeds-230"]) is None

    def test_bd_returns_a_bare_string(self, project, tmp_path, monkeypatch):
        make_beads_workspace(project)
        install_fake_bd(tmp_path, monkeypatch, stdout='"seeds-230"')
        assert query_bead_ids(project, ["seeds-230"]) is None

    def test_bd_times_out(self, project, tmp_path, monkeypatch):
        make_beads_workspace(project)
        install_fake_bd(tmp_path, monkeypatch)

        def explode(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="bd", timeout=1)

        monkeypatch.setattr(subprocess, "run", explode)
        assert query_bead_ids(project, ["seeds-230"]) is None

    def test_bd_cannot_be_executed(self, project, tmp_path, monkeypatch):
        make_beads_workspace(project)
        install_fake_bd(tmp_path, monkeypatch)

        def explode(*args, **kwargs):
            raise OSError("exec format error")

        monkeypatch.setattr(subprocess, "run", explode)
        assert query_bead_ids(project, ["seeds-230"]) is None


class TestQueryBeadIdsAnswers:
    """When bd does answer, its answer is authoritative."""

    def test_returns_the_ids_bd_knows(self, project, tmp_path, monkeypatch):
        make_beads_workspace(project)
        install_fake_bd(
            tmp_path,
            monkeypatch,
            stdout=json.dumps([{"id": "seeds-230"}, {"id": "seeds-90o"}]),
        )
        assert query_bead_ids(project, ["seeds-230", "seeds-90o", "seeds-999"]) == {
            "seeds-230",
            "seeds-90o",
        }

    def test_no_issues_found_is_an_authoritative_empty_set(
        self, project, tmp_path, monkeypatch
    ):
        make_beads_workspace(project)
        install_fake_bd(
            tmp_path,
            monkeypatch,
            stdout=json.dumps(
                {"error": "no issues found matching the provided IDs"},
            ),
            exit_code=1,
        )
        assert query_bead_ids(project, ["seeds-999"]) == set()

    def test_empty_array(self, project, tmp_path, monkeypatch):
        make_beads_workspace(project)
        install_fake_bd(tmp_path, monkeypatch, stdout="[]")
        assert query_bead_ids(project, ["seeds-999"]) == set()

    def test_unusable_records_are_skipped(self, project, tmp_path, monkeypatch):
        make_beads_workspace(project)
        install_fake_bd(
            tmp_path,
            monkeypatch,
            stdout=json.dumps(
                [
                    "seeds-1",
                    {"title": "no id"},
                    {"id": ""},
                    {"id": 7},
                    {"id": "seeds-2"},
                ]
            ),
        )
        assert query_bead_ids(project, ["seeds-2"]) == {"seeds-2"}

    def test_ids_bd_did_not_return_stay_unknown(self, project, tmp_path, monkeypatch):
        """A partial answer denies the rest -- bd saw them and did not list them."""
        make_beads_workspace(project)
        install_fake_bd(tmp_path, monkeypatch, stdout=json.dumps([{"id": "seeds-230"}]))
        assert query_bead_ids(project, ["seeds-230", "seeds-999"]) == {"seeds-230"}


class TestQueryBeadIdsInvocation:
    """How bd is called matters as much as what it says."""

    def test_runs_show_with_every_ref(self, project, tmp_path, monkeypatch):
        make_beads_workspace(project)
        log = install_fake_bd(tmp_path, monkeypatch)
        query_bead_ids(project, ["seeds-230", "seeds-90o"])
        (line,) = call_lines(log)
        _, args = line.split("\t", 1)
        assert args.split() == ["show", "seeds-230", "seeds-90o", "--json"]

    def test_runs_in_the_project_root_not_the_cwd(self, project, tmp_path, monkeypatch):
        """bd finds its database from the cwd, so it must run beside .beads/."""
        make_beads_workspace(project)
        log = install_fake_bd(tmp_path, monkeypatch)
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        monkeypatch.chdir(elsewhere)
        query_bead_ids(project, ["seeds-230"])
        (line,) = call_lines(log)
        cwd, _ = line.split("\t", 1)
        assert Path(cwd).resolve() == project.parent.resolve()

    def test_one_call_for_many_refs(self, project, tmp_path, monkeypatch):
        make_beads_workspace(project)
        log = install_fake_bd(tmp_path, monkeypatch)
        query_bead_ids(project, [f"seeds-{n}" for n in range(20)])
        assert len(call_lines(log)) == 1
