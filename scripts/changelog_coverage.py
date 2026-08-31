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

The second assertion: does CHANGELOG.md keep up?
--------------------------------------------------
All of the above gates the GENERATOR. It says nothing about the hand-polished
section that actually ships in ``CHANGELOG.md``, and that section went stale
twice during 0.6.0 — written early, then invalidated by further work, and
caught both times only by diffing the two by hand. ``--section X.Y.Z`` turns
that habit into code:

    MISSING-FROM-CHANGELOG  git-cliff put it in a gated group, and the
                            committed section neither links it nor records a
                            deliberate omission for it
    PHANTOM                 the section links a commit that is not in the
                            range at all (a stale entry after a rebase or a
                            botched merge)
    STALE-OMISSION          an omission marker names a commit outside the
                            range, so the record has rotted
    MALFORMED-OMISSION      a marker without a readable hash *and* reason

The polished section deliberately drops a lot — 14 entries in 0.6.0. Making
every one of them an explicit exception would produce an allowlist nobody
audits, and a check that fails every release gets ignored, which is worse than
no check. So only the groups a reader looks to for "what changed for me" are
gated: ``PRUNABLE_GROUPS`` (Documentation, Tooling) may be pruned freely, and
every *other* group is gated — including one nobody has added to
``cliff.toml`` yet, so a new group arrives gated rather than silently exempt.
That accounted for 13 of 0.6.0's 14 omissions. The 14th was a real ``fix:``
superseded inside the same release, and it carries a marker in the section
itself:

    <!-- changelog-omit: <short-sha> <why it is not an entry> -->

The reason is mandatory. Without it this degrades into a hash allowlist that
cannot be audited, which is the failure mode of every skip list that rots.

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

# Verdicts for the second assertion (generated notes vs the committed section).
MISSING_FROM_CHANGELOG = "MISSING-FROM-CHANGELOG"
PHANTOM = "PHANTOM"
STALE_OMISSION = "STALE-OMISSION"
MALFORMED_OMISSION = "MALFORMED-OMISSION"

# The git-cliff groups the polished section may prune without saying so.
# Everything else is gated, including a group nobody has invented yet: a new
# heading in cliff.toml should arrive guarded, not silently exempt. The two
# real misses this exists to catch were a `feat:` and a `fix:`.
PRUNABLE_GROUPS = frozenset({"Documentation", "Tooling"})

# The changelog links every entry as `.../commit/<sha>`; the generated notes
# use the full sha, the polished section may use either. Compared on the
# 7-character prefix, which is what both spell in their link text.
COMMIT_LINK_RE = re.compile(r"/commit/([0-9a-f]{7,40})")

# `<!-- changelog-omit: <sha> <reason> -->`, kept inside the section it
# describes so the record travels with the artifact rather than in a side file.
OMIT_RE = re.compile(r"<!--\s*changelog-omit:(.*?)-->", re.DOTALL)
OMIT_PAYLOAD_RE = re.compile(r"\A([0-9a-f]{7,40})\s+(\S.*)\Z", re.DOTALL)


class ConfigError(Exception):
    """``cliff.toml`` holds something this detector cannot faithfully model."""


class SectionError(Exception):
    """``CHANGELOG.md`` has no section for the version being checked."""


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
class RenderedEntry:
    """One `- ... ([sha](.../commit/sha))` line of the generated notes."""

    group: str
    sha: str
    text: str

    @property
    def short(self) -> str:
        return self.sha[:7]

    @property
    def gated(self) -> bool:
        return self.group not in PRUNABLE_GROUPS


@dataclass(frozen=True)
class SectionFinding:
    """One way the committed section and the generated notes disagree."""

    status: str
    short: str
    detail: str


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


def rendered_entries(rendered: str) -> list[RenderedEntry]:
    """Every generated entry, tagged with the ``### <group>`` it rendered under.

    The group is what decides whether the polished section is allowed to drop
    it, so it has to come from the notes themselves rather than from re-running
    the parsers — the notes are what the author actually pastes from.
    """
    entries: list[RenderedEntry] = []
    group: str | None = None
    for line in rendered.splitlines():
        if line.startswith("### "):
            group = line[4:].strip()
            continue
        if group is None or not line.startswith("- "):
            continue
        match = COMMIT_LINK_RE.search(line)
        if match is None:
            continue
        text = line[2:].split(" ([", 1)[0].strip()
        entries.append(RenderedEntry(group=group, sha=match.group(1), text=text))
    return entries


def extract_section(changelog: str, version: str) -> str:
    """The ``## [X.Y.Z]`` block of CHANGELOG.md, up to the next ``## `` heading."""
    label = version.lstrip("v")
    pattern = re.compile(
        rf"^## \[{re.escape(label)}\].*?(?=^## |\Z)", re.MULTILINE | re.DOTALL
    )
    match = pattern.search(changelog)
    if match is None:
        raise SectionError(
            f"no `## [{label}]` heading in the changelog. Write the section "
            "before running this — it is the artifact being checked."
        )
    return match.group(0)


def section_links(section: str) -> set[str]:
    """Short shas the committed section links to, i.e. what it claims to cover."""
    return {sha[:7] for sha in COMMIT_LINK_RE.findall(section)}


def parse_omissions(section: str) -> tuple[dict[str, str], list[str]]:
    """Read the ``changelog-omit`` markers: ``({short_sha: reason}, malformed)``.

    A marker with no reason is malformed on purpose. An allowlist of bare
    hashes cannot be audited by the next person, which is how every skip list
    of this shape rots.
    """
    omitted: dict[str, str] = {}
    malformed: list[str] = []
    for raw in OMIT_RE.findall(section):
        payload = " ".join(raw.split())
        match = OMIT_PAYLOAD_RE.match(payload)
        if match is None:
            malformed.append(payload or "(empty)")
            continue
        omitted[match.group(1)[:7]] = match.group(2).strip()
    return omitted, malformed


def check_section(
    rendered: str, section: str, commits: list[Commit]
) -> list[SectionFinding]:
    """Compare the generated notes against the section that actually shipped."""
    in_range = {commit.short for commit in commits}
    linked = section_links(section)
    omitted, malformed = parse_omissions(section)

    findings: list[SectionFinding] = []
    for entry in rendered_entries(rendered):
        if not entry.gated or entry.short in linked or entry.short in omitted:
            continue
        findings.append(
            SectionFinding(
                MISSING_FROM_CHANGELOG,
                entry.short,
                f"generated under '{entry.group}': {entry.text}",
            )
        )

    for short in sorted(linked - in_range):
        findings.append(
            SectionFinding(PHANTOM, short, "linked by the section, not in the range")
        )

    for short in sorted(set(omitted) - in_range):
        findings.append(
            SectionFinding(
                STALE_OMISSION,
                short,
                f"omission marker names a commit outside the range: {omitted[short]}",
            )
        )

    for payload in malformed:
        findings.append(
            SectionFinding(
                MALFORMED_OMISSION,
                "-",
                f"expected `<sha> <reason>`, got: {payload}",
            )
        )

    return findings


def report_section(
    findings: list[SectionFinding], version: str, omitted: dict[str, str]
) -> int:
    """Print the artifact verdict; return the process exit status."""
    label = version.lstrip("v")
    print(f"\nsection:  CHANGELOG.md [{label}]")
    print(f"omitted:  {len(omitted)}  (explicit markers, each with a reason)")
    if not findings:
        print(
            "\nOK: the committed section covers every generated entry in a gated "
            f"group ({', '.join(sorted(PRUNABLE_GROUPS))} may be pruned freely)."
        )
        return 0

    print(
        f"\nFAIL: CHANGELOG.md [{label}] disagrees with the generated notes "
        f"({len(findings)} finding(s)):",
        file=sys.stderr,
    )
    for finding in findings:
        print(f"  {finding.status}  {finding.short}", file=sys.stderr)
        print(f"            {finding.detail}", file=sys.stderr)
    print(
        "\nAdd the entry, drop the stale link, or record the omission next to "
        "the section as `<!-- changelog-omit: <sha> <why> -->`.",
        file=sys.stderr,
    )
    return 1


def check(
    rev_range: str,
    config_path: Path,
    cwd: Path,
    section_version: str | None = None,
    changelog_path: Path | None = None,
) -> int:
    config = load_config(config_path)
    rendered = run_cliff(rev_range, config_path, cwd)
    commits = git_log(rev_range, cwd)
    verdicts = [classify(c, rendered, config) for c in commits]
    status = report(verdicts, uncategorized_entries(rendered), rev_range)

    if section_version is None:
        return status

    assert changelog_path is not None, "a section check needs a changelog path"
    section = extract_section(changelog_path.read_text(), section_version)
    omitted, _ = parse_omissions(section)
    findings = check_section(rendered, section, commits)
    return max(status, report_section(findings, section_version, omitted))


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
    parser.add_argument(
        "--section",
        metavar="VERSION",
        help="also assert that CHANGELOG.md's `## [VERSION]` section covers "
        "every generated entry in a gated group, and links nothing outside "
        "the range",
    )
    parser.add_argument(
        "--changelog",
        type=Path,
        help="path to CHANGELOG.md (default: the --repo one)",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if shutil.which("git-cliff") is None:
        print(
            "git-cliff is not installed — see CONTRIBUTING.md 'Release Process'.",
            file=sys.stderr,
        )
        return 2

    rev_range = args.rev_range or default_range(args.repo)
    changelog = args.changelog or (args.repo / "CHANGELOG.md")
    try:
        return check(rev_range, args.config, args.repo, args.section, changelog)
    except ConfigError as exc:
        print(f"cannot read the skip rules: {exc}", file=sys.stderr)
        return 2
    except SectionError as exc:
        print(f"cannot read the changelog section: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
