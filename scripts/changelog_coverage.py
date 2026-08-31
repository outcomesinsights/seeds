#!/usr/bin/env python3
"""Pass/fail gate: prove every commit in a release range is accounted for.

Run via ``just changelog-coverage`` before ``just changelog-release``.

Why this exists
---------------
Three times a release nearly shipped with real work missing from the
changelog, and every time the existing check reported green. The check it
replaces (``just changelog-audit``) compared a *count* of commits against a
*count* of rendered entries and warned only if an ``### Uncategorized``
heading appeared. A count cannot name the commit that vanished, and the gap
between 100 commits and 39 entries looks equally plausible whether or not
``build: raise the Python floor to 3.11`` — the most user-affecting change in
0.6.0 — is one of the 61 that did not render. That is the measuring-a-proxy
failure: the number moves for the right reason and the wrong reason alike.

So this classifies every commit individually, and the only commits it lets
through unrendered are ones a rule in ``cliff.toml`` deliberately drops:

    RENDERED  its hash appears in the git-cliff output
    SKIPPED   git-cliff drops it on purpose — an unconventional subject
              (``filter_unconventional``, which is what removes merges), or
              the first matching ``commit_parsers`` entry has ``skip = true``
    MISSING   neither: git-cliff was expected to render it and did not

Exit status is 1 if anything is MISSING, or if the rendered notes contain an
``### Uncategorized`` section (a commit type no parser in ``cliff.toml`` has
been taught about — loud by design, see the catch-all's comment there).

The skip rules are READ OUT OF ``cliff.toml``
---------------------------------------------
They are never hardcoded here. A second copy of the skip list is a second
place to update, and it drifts silently — ``changelog-audit``'s hardcoded
list was already stale, which is part of how this class of omission survived
so long. ``load_parsers`` reimplements git-cliff's own resolution order
(first match wins) against the real table, and refuses to guess if it meets a
parser shape it does not understand.

The detector is itself code that can be silently wrong, so
``tests/test_changelog_coverage.py`` exercises it on hand-built commits with
hand-computed verdicts rather than letting it agree with itself.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = REPO_ROOT / "cliff.toml"

# `<type>[(scope)][!]: <description>`, matched the way git-cliff's conventional
# parser sees it: a type with no whitespace and none of `(`, `!`, `:` in it,
# then a non-empty description. "Merge branch 'x'" and "Merge origin/main: y"
# both fail this, which is exactly why merge commits never reach the parsers.
CONVENTIONAL_RE = re.compile(r"^[^\s(!:]+(\([^()]*\))?!?: \S")

RENDERED = "RENDERED"
SKIPPED = "SKIPPED"
MISSING = "MISSING"


class ConfigError(Exception):
    """``cliff.toml`` holds something this detector cannot faithfully model."""


@dataclass(frozen=True)
class Commit:
    sha: str
    subject: str
    message: str
    parents: tuple[str, ...]

    @property
    def short(self) -> str:
        return self.sha[:7]

    @property
    def is_merge(self) -> bool:
        return len(self.parents) > 1


@dataclass(frozen=True)
class Parser:
    """One entry of ``cliff.toml``'s ``commit_parsers`` table."""

    pattern: re.Pattern[str]
    skip: bool
    group: str | None

    def describe(self) -> str:
        what = "skip" if self.skip else f"group {self.group!r}"
        return f"{self.pattern.pattern} -> {what}"


@dataclass(frozen=True)
class Verdict:
    commit: Commit
    status: str
    reason: str


@dataclass(frozen=True)
class CliffConfig:
    parsers: tuple[Parser, ...]
    filter_unconventional: bool


def load_config(path: Path) -> CliffConfig:
    """Read the skip rules and unconventional-filter straight from cliff.toml.

    Raises ``ConfigError`` rather than guessing when a parser matches on a
    field this cannot evaluate from a commit (``body``, ``field``, ``sha``…).
    Guessing is how a detector goes quietly wrong; refusing is how the next
    person finds out the rules moved.
    """
    data = tomllib.loads(path.read_text())
    git = data.get("git", {})
    raw_parsers = git.get("commit_parsers")
    if not raw_parsers:
        raise ConfigError(f"{path} has no [git] commit_parsers table")

    parsers = []
    for index, entry in enumerate(raw_parsers):
        if "message" not in entry:
            raise ConfigError(
                f"{path}: commit_parsers[{index}] = {entry!r} does not match on "
                "`message`. This detector only models `message` parsers; teach "
                "it about the new field rather than letting it report green on "
                "rules it cannot evaluate."
            )
        parsers.append(
            Parser(
                pattern=re.compile(entry["message"]),
                skip=bool(entry.get("skip", False)),
                group=entry.get("group"),
            )
        )

    return CliffConfig(
        parsers=tuple(parsers),
        # git-cliff's own default is false; cliff.toml sets it true.
        filter_unconventional=bool(git.get("filter_unconventional", False)),
    )


def is_conventional(subject: str) -> bool:
    return CONVENTIONAL_RE.match(subject) is not None


def first_match(message: str, parsers: tuple[Parser, ...]) -> Parser | None:
    """git-cliff applies parsers in order and stops at the first hit.

    Matched with ``search`` against the whole commit message, because that is
    what git-cliff does: its patterns are Rust regexes run over the message
    with ``^`` anchored to the start of the text, so an anchored pattern is a
    subject match and an unanchored one can legitimately hit the body.
    """
    for parser in parsers:
        if parser.pattern.search(message):
            return parser
    return None


def classify(commit: Commit, rendered: str, config: CliffConfig) -> Verdict:
    """Decide one commit's fate. Order mirrors git-cliff's own pipeline.

    Note what is deliberately NOT here: a blanket "merges are fine" rule.
    Merges are excused only through ``filter_unconventional``, on the strength
    of their unconventional subject. A merge commit carrying a real ``feat:``
    subject that failed to render is a genuine omission, and gets reported as
    one instead of being waved through because of its parent count.
    """
    if commit.sha in rendered or commit.short in rendered:
        return Verdict(commit, RENDERED, "hash present in generated notes")

    if config.filter_unconventional and not is_conventional(commit.subject):
        detail = "merge commit" if commit.is_merge else "unconventional subject"
        return Verdict(commit, SKIPPED, f"{detail}; dropped by filter_unconventional")

    parser = first_match(commit.message, config.parsers)
    if parser is None:
        return Verdict(commit, MISSING, "no commit_parsers entry matches it")
    if parser.skip:
        return Verdict(commit, SKIPPED, f"cliff.toml rule: {parser.describe()}")
    return Verdict(
        commit,
        MISSING,
        f"cliff.toml rule: {parser.describe()}, but it did not render",
    )


def uncategorized_entries(rendered: str) -> list[str]:
    """Lines under an ``### Uncategorized`` heading, if git-cliff emitted one."""
    entries: list[str] = []
    collecting = False
    for line in rendered.splitlines():
        if line.startswith("### "):
            collecting = line.strip() == "### Uncategorized"
            continue
        if collecting and line.startswith("- "):
            entries.append(line[2:].strip())
    return entries


def parse_git_log(raw: str) -> list[Commit]:
    """Parse the ``%H%x00%P%x00%B`` records emitted by ``git_log`` below."""
    commits = []
    for record in raw.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        sha, parents, message = record.split("\x00", 2)
        commits.append(
            Commit(
                sha=sha,
                subject=message.strip().splitlines()[0] if message.strip() else "",
                message=message.strip(),
                parents=tuple(parents.split()),
            )
        )
    return commits


def _run(args: list[str], cwd: Path) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
    assert result.returncode == 0, (
        f"{' '.join(args)} failed ({result.returncode}):\n{result.stderr.strip()}"
    )
    return result.stdout


def git_log(rev_range: str, cwd: Path) -> list[Commit]:
    return parse_git_log(
        _run(["git", "log", "--format=%H%x00%P%x00%B%x1e", rev_range], cwd)
    )


def run_cliff(rev_range: str, config: Path, cwd: Path) -> str:
    return _run(["git-cliff", "--config", str(config), rev_range], cwd)


def default_range(cwd: Path) -> str:
    """``<latest tag>..HEAD`` — the same explicit range the release recipes use.

    Never ``--unreleased``: it silently under-reports once HEAD has a merge in
    it (13 entries vs 6, measured 2026-08-26; see the justfile's comment and
    seed seeds-gzf7). A gate built on a range that quietly truncates would be
    checking the wrong population.
    """
    return f"{_run(['git', 'describe', '--tags', '--abbrev=0'], cwd).strip()}..HEAD"


def report(verdicts: list[Verdict], uncategorized: list[str], rev_range: str) -> int:
    """Print the tally and the failures; return the process exit status."""
    counts = {status: 0 for status in (RENDERED, SKIPPED, MISSING)}
    for verdict in verdicts:
        counts[verdict.status] += 1

    print(f"range:    {rev_range}")
    print(f"commits:  {len(verdicts)}")
    print(f"rendered: {counts[RENDERED]}")
    print(f"skipped:  {counts[SKIPPED]}  (deliberate drops, per cliff.toml)")
    print(f"missing:  {counts[MISSING]}")

    missing = [v for v in verdicts if v.status == MISSING]
    if missing:
        print(
            f"\nFAIL: {len(missing)} commit(s) render nowhere and no cliff.toml "
            "rule drops them:",
            file=sys.stderr,
        )
        for verdict in missing:
            print(
                f"  {verdict.commit.short}  {verdict.commit.subject}", file=sys.stderr
            )
            print(f"            {verdict.reason}", file=sys.stderr)
        print(
            "\nEither give the type a group in cliff.toml or give it an explicit "
            "skip — do not leave it silently dropped.",
            file=sys.stderr,
        )

    if uncategorized:
        print(
            f"\nFAIL: an '### Uncategorized' section rendered "
            f"({len(uncategorized)} entr{'y' if len(uncategorized) == 1 else 'ies'}) "
            "— a commit type has no parser in cliff.toml:",
            file=sys.stderr,
        )
        for entry in uncategorized:
            print(f"  {entry}", file=sys.stderr)

    if missing or uncategorized:
        return 1
    print("\nOK: every commit in the range either renders or is deliberately skipped.")
    return 0


def check(rev_range: str, config_path: Path, cwd: Path) -> int:
    config = load_config(config_path)
    rendered = run_cliff(rev_range, config_path, cwd)
    verdicts = [classify(c, rendered, config) for c in git_log(rev_range, cwd)]
    return report(verdicts, uncategorized_entries(rendered), rev_range)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prove every commit in a release range renders or is "
        "deliberately skipped by cliff.toml."
    )
    parser.add_argument(
        "rev_range",
        nargs="?",
        help="git revision range (default: <latest tag>..HEAD)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="path to cliff.toml (default: the repo's own)",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=REPO_ROOT,
        help="repository to inspect (default: this one)",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if shutil.which("git-cliff") is None:
        print(
            "git-cliff is not installed — see CONTRIBUTING.md 'Release Process'.",
            file=sys.stderr,
        )
        return 2

    rev_range = args.rev_range or default_range(args.repo)
    try:
        return check(rev_range, args.config, args.repo)
    except ConfigError as exc:
        print(f"cannot read the skip rules: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
