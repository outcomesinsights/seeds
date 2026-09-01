#!/usr/bin/env python3
"""Pass/fail gate: prove flake.nix still mirrors [project.dependencies].

Run via ``just flake-deps``; wired into the pre-push stage in
``.pre-commit-config.yaml``, immediately ahead of the nix job.

Why this exists
---------------
``flake.nix`` carries a hand-maintained copy of the runtime dependency list::

    dependencies = with python3Packages; [
      click
    ];

Its comment asks the next editor to "keep this list in step with
[project.dependencies]", and a request is not a gate. On 2026-08-31, deleting
the web UI dropped ``flask`` from ``pyproject.toml`` and left ``flake.nix``
still naming it. ruff, mypy, the full pytest suite and ``uv lock --check``
were all green with the mismatch in place; the only thing that caught it was
``nix flake check --print-build-logs``, about two minutes cold and the
slowest gate in the stack. Two artifacts derive from that one dependency list
— ``uv.lock`` and ``flake.nix`` — and until this script only the first had a
gate.

So this is the cheap detector for what the nix job otherwise finds late: two
short lists, compared by name, in milliseconds. It does not replace the nix
job, which still catches everything a name comparison cannot (a floor
nixpkgs-unstable cannot satisfy, a build that fails for any other reason).
It moves the *dependency-drift* half of that signal to the front, where it
costs nothing.

Scope: [project.dependencies], and nothing else
-----------------------------------------------
``flake.nix`` declares two other things that look like dependency mirrors and
are not:

* ``nativeCheckInputs`` (pytestCheckHook, git, ripgrep) — test-only, and
  ``[dependency-groups] dev`` names none of them, because they are binaries
  rather than Python distributions.
* the ``makeWrapper --prefix PATH`` entry for ripgrep — a real runtime
  dependency of ``seeds search``, declared in ``flake.nix`` and nowhere else.

Neither has a counterpart in ``pyproject.toml``, so there is no two-sided
mirror to compare: they are single declarations, not duplicated ones. The
only way to gate them would be to invent a source of truth (a grep for
``subprocess`` binary names, say), and a gate that measures a proxy for the
thing it claims to check is the exact defect this repo has now hit four
times. They stay out until something declares them twice.

Name normalisation
------------------
Both sides are compared under PEP 503 normalisation (lowercased, runs of
``-``, ``_`` and ``.`` collapsed to a single ``-``), which is what makes
``PyYAML`` and ``pyyaml`` the same dependency. nixpkgs attribute names
usually agree with the normalised PyPI name; where one genuinely does not,
add it to ``PYPI_TO_NIX_ATTR`` rather than loosening the comparison. That
table is the escape hatch, and it is empty on purpose — an entry in it is a
real divergence somebody had to look up, not a guess.

The parser refuses rather than guesses
--------------------------------------
If the ``dependencies = with python3Packages; [ … ];`` block is missing,
appears more than once, or holds anything other than plain attribute names,
this exits 2 with a message instead of reporting green on a shape it cannot
read. A detector that silently skips what it does not understand is a
detector that reports clean on the day it matters.

``tests/test_flake_deps_check.py`` exercises it on hand-built files with
hand-computed verdicts rather than letting it agree with the repo's own.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PYPROJECT = REPO_ROOT / "pyproject.toml"
DEFAULT_FLAKE = REPO_ROOT / "flake.nix"

# Verdicts.
MISSING_FROM_FLAKE = "MISSING-FROM-FLAKE"
NOT_IN_PYPROJECT = "NOT-IN-PYPROJECT"

# PyPI distribution name (normalised) -> nixpkgs python3Packages attribute,
# for the cases where the two genuinely differ and normalisation cannot
# bridge them. Empty on purpose: every dependency this project has ever had
# is spelled the same on both sides. Add an entry only after confirming the
# attribute really is named differently in nixpkgs — never to quiet a failure
# that is actually a missing edit.
PYPI_TO_NIX_ATTR: dict[str, str] = {}

# The leading distribution name of a PEP 508 requirement: `click>=8.1.8`,
# `uvicorn[standard]>=0.30`, `foo ; python_version < "3.12"`.
REQUIREMENT_NAME_RE = re.compile(r"\A\s*([A-Za-z0-9][A-Za-z0-9._-]*)")

# The one block in flake.nix this gate reads. Anchored on the whole
# `with python3Packages;` form rather than on `dependencies =` alone, so a
# rewrite into some other shape fails the match and is reported, instead of
# being read as an empty list.
#
# `^[ \t]*` is load-bearing: flake.nix's own comment quotes this exact form to
# tell the next editor what the gate reads, and without the anchor that prose
# counted as a second declaration and the gate refused with "flake.nix has 2
# blocks". Requiring nothing but whitespace ahead of `dependencies` excludes
# any line that has already opened a `#` comment. Caught by running the
# constructed failing case rather than by reading the regex.
FLAKE_DEPS_RE = re.compile(
    r"^[ \t]*dependencies\s*=\s*with\s+python3Packages\s*;\s*\[(?P<body>.*?)\]\s*;",
    re.DOTALL | re.MULTILINE,
)

# A nix comment: `#` to end of line. Stripped before tokenising so the
# explanatory prose inside the list is not mistaken for attribute names.
NIX_COMMENT_RE = re.compile(r"#[^\n]*")

# A bare attribute name, optionally qualified: `click`, `python3Packages.click`.
NIX_ATTR_RE = re.compile(r"\A(?:python3Packages\.)?([A-Za-z_][A-Za-z0-9_.'-]*)\Z")

PEP503_SEPARATORS_RE = re.compile(r"[-_.]+")


class ParseError(Exception):
    """A source file holds something this detector cannot faithfully read."""


@dataclass(frozen=True)
class Dependency:
    """One dependency as one of the two files spells it."""

    name: str  # PEP 503 normalised, the key both sides are compared on
    raw: str  # verbatim, for the error message to quote back


@dataclass(frozen=True)
class Mismatch:
    status: str
    name: str
    detail: str


def normalize(name: str) -> str:
    """PEP 503 normalisation: lowercase, and `-_.` runs collapsed to `-`."""
    return PEP503_SEPARATORS_RE.sub("-", name.strip()).lower()


def pyproject_dependencies(text: str) -> list[Dependency]:
    """Read ``[project] dependencies`` out of pyproject.toml.

    An absent ``[project]`` table or an absent ``dependencies`` key is a
    ParseError, not an empty list: this gate would otherwise pass by reading
    nothing at all the day somebody restructures the file.
    """
    data = tomllib.loads(text)
    project = data.get("project")
    if project is None:
        raise ParseError("pyproject.toml has no [project] table")
    if "dependencies" not in project:
        raise ParseError(
            "pyproject.toml's [project] table has no `dependencies` key. If the "
            "project genuinely has no runtime dependencies, write "
            "`dependencies = []` so this gate can tell that apart from a "
            "restructured file."
        )

    deps: list[Dependency] = []
    for requirement in project["dependencies"]:
        match = REQUIREMENT_NAME_RE.match(requirement)
        if match is None:
            raise ParseError(
                f"cannot read a distribution name out of the requirement "
                f"{requirement!r}"
            )
        deps.append(Dependency(name=normalize(match.group(1)), raw=requirement))
    return deps


def flake_dependencies(text: str) -> list[Dependency]:
    """Read the ``dependencies = with python3Packages; [ … ];`` list."""
    matches = FLAKE_DEPS_RE.findall(text)
    if not matches:
        raise ParseError(
            "flake.nix has no `dependencies = with python3Packages; [ … ];` "
            "block. If the runtime dependency list moved or changed shape, "
            "teach this script the new one — do not leave it matching nothing, "
            "which reports green on an empty list."
        )
    if len(matches) > 1:
        raise ParseError(
            f"flake.nix has {len(matches)} `dependencies = with python3Packages; "
            "[ … ];` blocks. This gate models exactly one runtime dependency "
            "list; with several it cannot say which mirrors pyproject.toml."
        )

    body = NIX_COMMENT_RE.sub("", matches[0])
    deps: list[Dependency] = []
    for token in body.split():
        attr = NIX_ATTR_RE.match(token)
        if attr is None:
            raise ParseError(
                f"flake.nix's dependency list holds {token!r}, which is not a "
                "plain package attribute. This gate compares names; it cannot "
                "evaluate nix. Keep the list to bare attributes, or teach the "
                "script about the new form."
            )
        deps.append(Dependency(name=normalize(attr.group(1)), raw=token))
    return deps


def compare(
    pyproject_deps: list[Dependency], flake_deps: list[Dependency]
) -> list[Mismatch]:
    """Every dependency one file names and the other does not."""
    expected = {PYPI_TO_NIX_ATTR.get(dep.name, dep.name): dep for dep in pyproject_deps}
    declared = {dep.name: dep for dep in flake_deps}

    mismatches: list[Mismatch] = []
    for name in sorted(set(expected) - set(declared)):
        mismatches.append(
            Mismatch(
                MISSING_FROM_FLAKE,
                name,
                f"pyproject.toml requires `{expected[name].raw}`, and flake.nix's "
                "dependency list does not name it",
            )
        )
    for name in sorted(set(declared) - set(expected)):
        mismatches.append(
            Mismatch(
                NOT_IN_PYPROJECT,
                name,
                f"flake.nix names `{declared[name].raw}`, and nothing in "
                "[project.dependencies] requires it",
            )
        )
    return mismatches


def report(
    pyproject_deps: list[Dependency],
    flake_deps: list[Dependency],
    mismatches: list[Mismatch],
) -> int:
    """Print both lists and any disagreement; return the process exit status."""

    def spell(deps: list[Dependency]) -> str:
        return ", ".join(sorted(dep.name for dep in deps)) or "(none)"

    print(f"pyproject.toml:  {len(pyproject_deps)}  {spell(pyproject_deps)}")
    print(f"flake.nix:       {len(flake_deps)}  {spell(flake_deps)}")

    if not mismatches:
        print("\nOK: flake.nix mirrors pyproject.toml's [project.dependencies].")
        return 0

    # stdout is block-buffered when piped (pre-commit always pipes it), so
    # without this the two lists above land *after* the failure below and the
    # report reads backwards.
    sys.stdout.flush()
    print(
        f"\nFAIL: flake.nix does not mirror pyproject.toml's "
        f"[project.dependencies] ({len(mismatches)} mismatch(es)):",
        file=sys.stderr,
    )
    for mismatch in mismatches:
        print(f"  {mismatch.status}  {mismatch.name}", file=sys.stderr)
        print(f"            {mismatch.detail}", file=sys.stderr)
    print(
        "\nEdit the `dependencies = with python3Packages; [ … ];` list in "
        "flake.nix to match. Left alone this surfaces two minutes into "
        "`nix flake check --print-build-logs`, or on a user's machine.",
        file=sys.stderr,
    )
    return 1


def check(pyproject_path: Path, flake_path: Path) -> int:
    pyproject_deps = pyproject_dependencies(pyproject_path.read_text())
    flake_deps = flake_dependencies(flake_path.read_text())
    return report(pyproject_deps, flake_deps, compare(pyproject_deps, flake_deps))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prove flake.nix's runtime dependency list still mirrors "
        "pyproject.toml's [project.dependencies]."
    )
    parser.add_argument(
        "--pyproject",
        type=Path,
        default=DEFAULT_PYPROJECT,
        help="path to pyproject.toml (default: this repo's own)",
    )
    parser.add_argument(
        "--flake",
        type=Path,
        default=DEFAULT_FLAKE,
        help="path to flake.nix (default: this repo's own)",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    try:
        return check(args.pyproject, args.flake)
    except ParseError as exc:
        print(f"cannot read the dependency lists: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
