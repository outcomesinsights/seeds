"""Tests for optional bead-ID lookup (seeds.beads).

Beads is never a dependency, and ``bd`` is the only source. The
``.beads/issues.jsonl`` export this module used to read first was retired with
JSONL on 2026-09-13 and was frozen wherever it survived, so it vouched for
beads deleted since (bead seeds-dlq). The tests that pinned its parsing are
gone; what replaces them pins that a surviving export is never read at all.
"""

import json
import subprocess
from pathlib import Path

import pytest

from seeds.beads import (
    all_bead_ids,
    beads_in_use,
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
    """Plant a stray, frozen ``issues.jsonl`` -- which nothing may read."""
    path = seeds_dir.parent / ".beads" / "issues.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _issue_line(issue_id, **extra):
    return json.dumps({"_type": "issue", "id": issue_id, **extra})


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
    references could not be checked at all, the second is beads itself saying
    no such bead. Collapsing them would either report an unchecked body as
    clean or invent a denial beads never made.
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


class TestAFrozenExportIsNeverRead:
    """The regression bead seeds-dlq exists for.

    A surviving ``issues.jsonl`` is frozen at whatever it held when JSONL was
    retired. Read as a source, it vouches for a bead deleted since, and that
    bead never reaches ``bd`` to be denied.
    """

    def test_query_trusts_bd_over_a_stale_export(self, project, tmp_path, monkeypatch):
        make_beads_workspace(project)
        _write_beads(project, _issue_line("seeds-gone") + "\n")
        install_fake_bd(tmp_path, monkeypatch, stdout="[]")
        assert query_bead_ids(project, ["seeds-gone"]) == set()

    def test_all_ids_trusts_bd_over_a_stale_export(
        self, project, tmp_path, monkeypatch
    ):
        make_beads_workspace(project)
        _write_beads(project, _issue_line("seeds-gone") + "\n")
        install_fake_bd(
            tmp_path, monkeypatch, stdout=json.dumps([{"id": "seeds-live"}])
        )
        assert all_bead_ids(project) == {"seeds-live"}


class TestAllBeadIds:
    """One ``bd list --all`` for callers that need the whole set (winnow)."""

    def test_no_beads_workspace_is_none_and_never_calls_bd(
        self, project, tmp_path, monkeypatch
    ):
        log = install_fake_bd(tmp_path, monkeypatch)
        assert all_bead_ids(project) is None
        assert call_lines(log) == []

    def test_bd_not_installed_is_none(self, project, tmp_path, monkeypatch):
        make_beads_workspace(project)
        hide_bd(monkeypatch, tmp_path)
        assert all_bead_ids(project) is None

    def test_unreadable_output_is_none_not_empty(self, project, tmp_path, monkeypatch):
        """ "Could not ask" must never read as "no beads"."""
        make_beads_workspace(project)
        install_fake_bd(tmp_path, monkeypatch, stdout="command not found\n")
        assert all_bead_ids(project) is None

    def test_an_error_object_is_none(self, project, tmp_path, monkeypatch):
        make_beads_workspace(project)
        install_fake_bd(tmp_path, monkeypatch, stdout=json.dumps({"error": "boom"}))
        assert all_bead_ids(project) is None

    def test_returns_every_id(self, project, tmp_path, monkeypatch):
        make_beads_workspace(project)
        install_fake_bd(
            tmp_path,
            monkeypatch,
            stdout=json.dumps([{"id": "seeds-a1"}, {"id": "seeds-b2"}, {"no": "id"}]),
        )
        assert all_bead_ids(project) == {"seeds-a1", "seeds-b2"}

    def test_runs_list_all_in_the_project_root(self, project, tmp_path, monkeypatch):
        make_beads_workspace(project)
        log = install_fake_bd(tmp_path, monkeypatch, stdout="[]")
        all_bead_ids(project)
        (line,) = call_lines(log)
        cwd, args = line.split("\t")
        assert cwd == project.parent.as_posix()
        assert args == "list --all --json"
