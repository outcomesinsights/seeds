"""Tests for scripts/flake_deps_check.py (bead seeds-8ro).

The thing under test is a gate, and a gate that returns 0 while flake.nix
names a dependency pyproject.toml dropped is worse than no gate — it reads as
"checked and clean", which is how ``flask`` survived the web-UI deletion until
a two-minute ``nix flake check`` found it. So nothing here lets the detector
agree with the repo's own files: every case is a hand-written pair of
pyproject.toml and flake.nix fragments with the verdict worked out by hand.

The three controls that matter are the ones the bead's acceptance criteria
name: a dependency added to pyproject.toml only, a dependency removed from
flake.nix only, and both files in step. ``test_real_repo_files_agree`` is the
one live case, and it asserts the invariant the pre-push hook exists to hold.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "flake_deps_check.py"
REPO_ROOT = SCRIPT.parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("flake_deps_check", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves annotations through sys.modules[cls.__module__], so
    # a module loaded straight off a path has to be registered before exec.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


fdc = _load()


def pyproject(*requirements: str) -> str:
    """A miniature pyproject.toml with just the table the gate reads."""
    body = "".join(f'    "{req}",\n' for req in requirements)
    return f'[project]\nname = "seeds"\ndependencies = [\n{body}]\n'


def flake(*attrs: str, body: str | None = None) -> str:
    """A miniature flake.nix carrying the one block the gate reads."""
    inner = body if body is not None else "".join(f"    {attr}\n" for attr in attrs)
    return (
        "{\n"
        "  buildPythonApplication {\n"
        "    dependencies = with python3Packages; [\n"
        f"{inner}"
        "    ];\n"
        "  };\n"
        "}\n"
    )


def write_pair(tmp_path: Path, pyproject_text: str, flake_text: str) -> list[str]:
    """Write both files and return the argv that points the gate at them."""
    (tmp_path / "pyproject.toml").write_text(pyproject_text)
    (tmp_path / "flake.nix").write_text(flake_text)
    return [
        "--pyproject",
        str(tmp_path / "pyproject.toml"),
        "--flake",
        str(tmp_path / "flake.nix"),
    ]


# --- the three acceptance cases ------------------------------------------


def test_dependency_added_to_pyproject_only_fails(tmp_path, capsys):
    """`requests` required but never mirrored: fails, and names it."""
    argv = write_pair(
        tmp_path, pyproject("click>=8.1.8", "requests>=2.32"), flake("click")
    )

    assert fdc.main(argv) == 1

    err = capsys.readouterr().err
    assert "MISSING-FROM-FLAKE" in err
    assert "requests" in err
    # The name of the dependency that is fine must NOT be reported.
    assert "MISSING-FROM-FLAKE  click" not in err


def test_dependency_removed_from_pyproject_only_fails(tmp_path, capsys):
    """The flask case verbatim: dropped from pyproject, left in flake.nix."""
    argv = write_pair(tmp_path, pyproject("click>=8.1.8"), flake("click", "flask"))

    assert fdc.main(argv) == 1

    err = capsys.readouterr().err
    assert "NOT-IN-PYPROJECT" in err
    assert "flask" in err


def test_both_files_in_step_passes(tmp_path, capsys):
    """Adding a dependency to both sides is clean — the gate is not noise."""
    argv = write_pair(
        tmp_path,
        pyproject("click>=8.1.8", "requests>=2.32"),
        flake("click", "requests"),
    )

    assert fdc.main(argv) == 0
    assert "OK: flake.nix mirrors" in capsys.readouterr().out


def test_removing_a_dependency_from_both_sides_passes(tmp_path, capsys):
    """The other half of "in step": a removal mirrored on both sides."""
    argv = write_pair(tmp_path, pyproject("click>=8.1.8"), flake("click"))

    assert fdc.main(argv) == 0
    assert "OK: flake.nix mirrors" in capsys.readouterr().out


def test_both_directions_reported_at_once(tmp_path, capsys):
    """One swapped dependency is two findings, not one."""
    argv = write_pair(tmp_path, pyproject("requests>=2.32"), flake("flask"))

    assert fdc.main(argv) == 1

    err = capsys.readouterr().err
    assert "MISSING-FROM-FLAKE  requests" in err
    assert "NOT-IN-PYPROJECT  flask" in err


# --- parsing --------------------------------------------------------------


def test_requirement_decorations_are_stripped():
    """Extras, markers and floors are not part of the name being compared."""
    deps = fdc.pyproject_dependencies(
        pyproject(
            "click>=8.1.8",
            "uvicorn[standard]>=0.30",
            "tomli ; python_version < '3.11'",
        )
    )
    assert [dep.name for dep in deps] == ["click", "uvicorn", "tomli"]


def test_names_compare_under_pep503_normalisation(tmp_path, capsys):
    """`PyYAML` and `pyyaml` are the same dependency; `.`/`_` fold to `-`."""
    argv = write_pair(
        tmp_path,
        pyproject("PyYAML>=6", "typing_extensions>=4"),
        flake("pyyaml", "typing-extensions"),
    )

    assert fdc.main(argv) == 0
    assert "OK: flake.nix mirrors" in capsys.readouterr().out


def test_comments_inside_the_list_are_not_dependencies():
    """flake.nix's list carries prose; none of its words are attributes."""
    deps = fdc.flake_dependencies(
        flake(body="    # Sole runtime dependency per pyproject.toml.\n    click\n")
    )
    assert [dep.name for dep in deps] == ["click"]


def test_a_comment_quoting_the_block_is_not_a_second_block(tmp_path, capsys):
    """flake.nix's own prose quotes the block shape; that is not a declaration.

    This is a regression test for a bug the gate shipped with for about ten
    minutes: the comment added to flake.nix to explain what the gate reads
    quoted `dependencies = with python3Packages; [ … ];` verbatim, the pattern
    matched it, and the gate refused with "flake.nix has 2 blocks" on a
    perfectly good file. Found by running the constructed failing case.
    """
    text = flake("click").replace(
        "  buildPythonApplication {\n",
        "  buildPythonApplication {\n"
        "    # The gate reads this exact `dependencies = with python3Packages;\n"
        "    # [ … ];` form. Reshape it and the check refuses.\n",
    )
    argv = write_pair(tmp_path, pyproject("click>=8.1.8"), text)

    assert fdc.main(argv) == 0
    assert "OK: flake.nix mirrors" in capsys.readouterr().out


def test_qualified_attribute_is_read():
    """`python3Packages.click` names the same package as a bare `click`."""
    deps = fdc.flake_dependencies(flake("python3Packages.click"))
    assert [dep.name for dep in deps] == ["click"]


def test_empty_dependency_lists_agree(tmp_path, capsys):
    """No runtime dependencies on either side is a clean pass, not a crash."""
    argv = write_pair(tmp_path, pyproject(), flake())

    assert fdc.main(argv) == 0
    out = capsys.readouterr().out
    assert "pyproject.toml:  0  (none)" in out


# --- the parser refuses rather than guesses -------------------------------


def test_missing_flake_block_is_refused(tmp_path, capsys):
    """A restructured flake.nix must not read as "no dependencies, clean"."""
    argv = write_pair(
        tmp_path,
        pyproject("click>=8.1.8"),
        "{ buildPythonApplication { deps = [ click ]; }; }\n",
    )

    assert fdc.main(argv) == 2
    assert "no `dependencies = with python3Packages;" in capsys.readouterr().err


def test_two_flake_blocks_are_refused(tmp_path, capsys):
    """With two lists the gate cannot say which one mirrors pyproject.toml."""
    argv = write_pair(
        tmp_path, pyproject("click>=8.1.8"), flake("click") + flake("click")
    )

    assert fdc.main(argv) == 2
    assert "2 `dependencies = with python3Packages;" in capsys.readouterr().err


def test_non_attribute_token_is_refused(tmp_path, capsys):
    """This compares names; it cannot evaluate nix, and says so."""
    argv = write_pair(
        tmp_path,
        pyproject("click>=8.1.8"),
        flake(body="    click\n    (lib.optional stdenv.isLinux foo)\n"),
    )

    assert fdc.main(argv) == 2
    assert "not a plain package attribute" in capsys.readouterr().err


def test_absent_dependencies_key_is_refused(tmp_path, capsys):
    """An absent key is a restructured file, not an empty dependency list."""
    argv = write_pair(tmp_path, '[project]\nname = "seeds"\n', flake())

    assert fdc.main(argv) == 2
    assert "no `dependencies` key" in capsys.readouterr().err


def test_absent_project_table_is_refused(tmp_path, capsys):
    argv = write_pair(tmp_path, "[tool.ruff]\nline-length = 88\n", flake())

    assert fdc.main(argv) == 2
    assert "no [project] table" in capsys.readouterr().err


def test_unreadable_requirement_is_refused():
    with pytest.raises(fdc.ParseError):
        fdc.pyproject_dependencies(pyproject("!!!"))


# --- the live invariant ---------------------------------------------------


def test_real_repo_files_agree(capsys):
    """This repo's own flake.nix and pyproject.toml are in step right now.

    The pre-push hook asserts the same thing; this makes a mismatch visible in
    `just test` too, which is where a dependency edit is most likely to be
    sitting when it happens.
    """
    assert fdc.main([]) == 0
    assert "OK: flake.nix mirrors" in capsys.readouterr().out
