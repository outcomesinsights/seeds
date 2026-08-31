"""Tests for scripts/changelog_coverage.py (bead seeds-0t1).

The thing under test is a release gate, and a gate that returns 0 on a
changelog with a commit missing from it is worse than no gate — it reads as
"checked and clean", which is exactly how the same omission survived three
releases. So nothing here lets the detector agree with itself: every case is a
hand-built commit list plus a hand-built block of git-cliff output, with the
verdict worked out by hand and written down as the assertion.

The two controls that matter are ``test_missing_commit_is_reported`` (a commit
with a real group that rendered nowhere) and
``test_uncategorized_section_fails`` (a type no parser handles, surfacing
loudly). ``test_skip_rules_come_from_the_config`` is the one that keeps the
skip list honest: the *same* commit is SKIPPED or MISSING depending only on
what the passed-in cliff.toml says, so a hardcoded list would fail it.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.githelpers import git, git_env, git_init

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "changelog_coverage.py"
REPO_ROOT = SCRIPT.parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("changelog_coverage", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves annotations through sys.modules[cls.__module__], so
    # a module loaded straight off a path has to be registered before exec.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


cc = _load()


# A miniature cliff.toml: one deliberate skip, two real groups, and the loud
# catch-all. Written out in full rather than derived from the real file so the
# expected verdicts below can be computed by hand.
CONFIG = """\
[changelog]
header = ""
body = '''
{% for group, commits in commits | group_by(attribute="group") %}
### {{ group }}
{% for commit in commits -%}
- {{ commit.message | split(pat="\\n") | first | trim }} ({{ commit.id }})
{% endfor %}
{%- endfor %}
'''
footer = ""
trim = true

[git]
conventional_commits = true
filter_unconventional = true
filter_commits = true
commit_parsers = [
    { message = "^chore\\\\(beads\\\\)", skip = true },
    { message = "^feat", group = "Added" },
    { message = "^fix", group = "Fixed" },
    { message = ".*", group = "Uncategorized" },
]
"""

# Same table with the chore(beads) skip removed, so the identical commit that
# CONFIG deliberately drops now falls through to the catch-all instead.
CONFIG_WITHOUT_SKIP = CONFIG.replace(
    '    { message = "^chore\\\\(beads\\\\)", skip = true },\n', ""
)


def _write_config(tmp_path: Path, body: str = CONFIG) -> Path:
    path = tmp_path / "cliff.toml"
    path.write_text(body)
    return path


def _commit(sha: str, subject: str, parents: int = 1) -> cc.Commit:
    return cc.Commit(
        sha=sha,
        subject=subject,
        message=subject,
        parents=tuple(f"{i:040x}" for i in range(parents)),
    )


# Hand-built git-cliff output. Only aaaaaaa… and bbbbbbb… are in it.
RENDERED_NOTES = """\
## [Unreleased]

### Added
- Add a thing ([aaaaaaa](https://example.invalid/commit/aaaaaaa0000000000000000000000000000000a))

### Fixed
- Fix a thing ([bbbbbbb](https://example.invalid/commit/bbbbbbb0000000000000000000000000000000b))
"""

SHA_RENDERED_FEAT = "aaaaaaa0000000000000000000000000000000a"
SHA_RENDERED_FIX = "bbbbbbb0000000000000000000000000000000b"
SHA_ABSENT = "ccccccc0000000000000000000000000000000c"


def test_rendered_commit_is_rendered(tmp_path: Path) -> None:
    config = cc.load_config(_write_config(tmp_path))
    verdict = cc.classify(
        _commit(SHA_RENDERED_FEAT, "feat: add a thing"), RENDERED_NOTES, config
    )
    assert verdict.status == cc.RENDERED


def test_missing_commit_is_reported(tmp_path: Path) -> None:
    """The control that matters: a real `fix:` that rendered nowhere.

    Hand-computed: the first parser to match `fix: ...` is `^fix -> Fixed`, a
    group and not a skip, so git-cliff was supposed to render it. Its hash is
    absent from RENDERED_NOTES. Therefore MISSING, and the run must fail.
    """
    config = cc.load_config(_write_config(tmp_path))
    verdict = cc.classify(
        _commit(SHA_ABSENT, "fix: a fix that vanished"), RENDERED_NOTES, config
    )
    assert verdict.status == cc.MISSING
    assert "did not render" in verdict.reason

    status = cc.report([verdict], [], "v0.1.0..HEAD")
    assert status == 1


def test_missing_commit_is_named_not_just_counted(tmp_path: Path, capsys) -> None:
    """Naming the offender is the entire reason this replaced changelog-audit."""
    config = cc.load_config(_write_config(tmp_path))
    verdicts = [
        cc.classify(
            _commit(SHA_RENDERED_FEAT, "feat: add a thing"), RENDERED_NOTES, config
        ),
        cc.classify(
            _commit(SHA_ABSENT, "fix: a fix that vanished"), RENDERED_NOTES, config
        ),
    ]
    assert cc.report(verdicts, [], "v0.1.0..HEAD") == 1
    err = capsys.readouterr().err
    assert "ccccccc" in err
    assert "a fix that vanished" in err


def test_uncategorized_section_fails(tmp_path: Path) -> None:
    """The other control: a type no parser handles surfaces loudly.

    Every commit here renders, so the MISSING count is 0 — a count-based check
    would call this clean. The `### Uncategorized` heading is the only signal,
    and it must be enough on its own to fail the run.
    """
    notes = RENDERED_NOTES + (
        "\n### Uncategorized\n"
        "- Build: raise the Python floor to 3.11 ([ddddddd](https://example.invalid/c/d))\n"
    )
    entries = cc.uncategorized_entries(notes)
    assert len(entries) == 1
    assert "raise the Python floor" in entries[0]

    config = cc.load_config(_write_config(tmp_path))
    verdicts = [
        cc.classify(_commit(SHA_RENDERED_FEAT, "feat: add a thing"), notes, config)
    ]
    assert all(v.status == cc.RENDERED for v in verdicts)
    assert cc.report(verdicts, entries, "v0.1.0..HEAD") == 1


def test_uncategorized_entries_ignores_other_sections() -> None:
    """Entries under Added/Fixed must not be misread as uncategorized."""
    assert cc.uncategorized_entries(RENDERED_NOTES) == []


def test_skip_rules_come_from_the_config(tmp_path: Path) -> None:
    """One commit, two configs, two verdicts — so the list cannot be hardcoded.

    `chore(beads): …` is absent from the notes either way. With the skip rule
    present it is a deliberate drop; with the rule deleted the only parser left
    that matches is the `.*` catch-all, which assigns a group, so the same
    commit becomes a genuine omission.
    """
    commit = _commit(SHA_ABSENT, "chore(beads): regenerate JSONL")

    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    with_skip = cc.load_config(_write_config(tmp_path / "a", CONFIG))
    without_skip = cc.load_config(_write_config(tmp_path / "b", CONFIG_WITHOUT_SKIP))

    assert cc.classify(commit, RENDERED_NOTES, with_skip).status == cc.SKIPPED
    assert cc.classify(commit, RENDERED_NOTES, without_skip).status == cc.MISSING


def test_first_matching_parser_wins(tmp_path: Path) -> None:
    """Parser order is load-bearing: the specific skip precedes the catch-all."""
    config = cc.load_config(_write_config(tmp_path))
    verdict = cc.classify(
        _commit(SHA_ABSENT, "chore(beads): regenerate JSONL"), RENDERED_NOTES, config
    )
    assert verdict.status == cc.SKIPPED
    assert "chore" in verdict.reason


def test_unconventional_subject_is_skipped(tmp_path: Path) -> None:
    config = cc.load_config(_write_config(tmp_path))
    verdict = cc.classify(_commit(SHA_ABSENT, "wip"), RENDERED_NOTES, config)
    assert verdict.status == cc.SKIPPED
    assert "filter_unconventional" in verdict.reason


def test_merge_commit_is_skipped_on_its_subject_not_its_parents(tmp_path: Path) -> None:
    """A merge is excused for looking unconventional, never for being a merge.

    So an ordinary `Merge branch 'x'` is SKIPPED, but a merge someone gave a
    real `feat:` subject and that rendered nowhere is a genuine omission and
    must not be waved through on parent count.
    """
    config = cc.load_config(_write_config(tmp_path))

    ordinary = cc.classify(
        _commit(SHA_ABSENT, "Merge branch 'topic'", parents=2), RENDERED_NOTES, config
    )
    assert ordinary.status == cc.SKIPPED
    assert "merge commit" in ordinary.reason

    disguised = cc.classify(
        _commit(SHA_ABSENT, "feat: land the thing", parents=2), RENDERED_NOTES, config
    )
    assert disguised.status == cc.MISSING


@pytest.mark.parametrize(
    ("subject", "expected"),
    [
        ("feat: add a thing", True),
        ("fix(db): correct a query", True),
        ("feat!: break a thing", True),
        ("chore(seeds-a1b2): capture", True),
        ("Merge branch 'topic'", False),
        ("Merge origin/main: dependabot bumps", False),
        ("wip", False),
        ("feat:", False),
        ("feat:no space", False),
    ],
)
def test_is_conventional(subject: str, expected: bool) -> None:
    assert cc.is_conventional(subject) is expected


def test_parser_without_message_field_is_refused(tmp_path: Path) -> None:
    """Refusing to model an unknown parser beats reporting green on it."""
    path = tmp_path / "cliff.toml"
    path.write_text(
        '[git]\ncommit_parsers = [\n    { body = "^BREAKING", group = "Changed" },\n]\n'
    )
    with pytest.raises(cc.ConfigError, match="does not match on `message`"):
        cc.load_config(path)


def test_missing_commit_parsers_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "cliff.toml"
    path.write_text("[git]\nconventional_commits = true\n")
    with pytest.raises(cc.ConfigError, match="no \\[git\\] commit_parsers"):
        cc.load_config(path)


def test_real_cliff_toml_loads() -> None:
    """This repo's own config must stay inside what the detector can model."""
    config = cc.load_config(REPO_ROOT / "cliff.toml")
    assert config.filter_unconventional is True
    assert any(p.skip for p in config.parsers)
    assert config.parsers[-1].group == "Uncategorized"
    assert not config.parsers[-1].skip, (
        "the catch-all must stay a loud group, not a silent skip — a "
        "`.* -> skip` catch-all would make every unhandled type look deliberate"
    )


def test_parse_git_log_round_trip() -> None:
    raw = (
        "aaa\x00p1 p2\x00feat: a thing\n\nwith a body\n\x1e"
        "bbb\x00p1\x00fix: another\n\x1e"
    )
    commits = cc.parse_git_log(raw)
    assert [c.sha for c in commits] == ["aaa", "bbb"]
    assert commits[0].subject == "feat: a thing"
    assert "with a body" in commits[0].message
    assert commits[0].is_merge is True
    assert commits[1].is_merge is False


@pytest.mark.skipif(
    shutil.which("git-cliff") is None, reason="git-cliff not installed on this host"
)
def test_end_to_end_on_a_throwaway_repo(tmp_path: Path) -> None:
    """Drive the real git + git-cliff path over a repo built commit by commit.

    Deliberately a throwaway repo via tests/githelpers, never this one: the
    suite must not go red because of the state of the range being released.
    That check is `just changelog-coverage`, run at release time.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    git_init(repo)
    config = _write_config(tmp_path)

    def commit(subject: str) -> None:
        (repo / "f.txt").write_text(subject)
        git(repo, "add", "f.txt")
        git(repo, "commit", "-q", "-m", subject)

    commit("feat: the first thing")
    git(repo, "tag", "v0.0.1")
    commit("feat: a rendered feature")
    commit("chore(beads): regenerate JSONL")

    def run() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "v0.0.1..HEAD",
                "--config",
                str(config),
                "--repo",
                str(repo),
            ],
            capture_output=True,
            text=True,
            check=False,
            env=git_env(repo),
        )

    clean = run()
    assert clean.returncode == 0, clean.stdout + clean.stderr
    assert "rendered: 1" in clean.stdout
    assert "skipped:  1" in clean.stdout

    # Now teach cliff.toml nothing about `build:` and remove the catch-all —
    # the pre-fix shape of this repo's own config — and add such a commit.
    commit("build: raise the Python floor")
    config.write_text(
        CONFIG.replace('    { message = ".*", group = "Uncategorized" },\n', "")
    )
    broken = run()
    assert broken.returncode == 1, broken.stdout + broken.stderr
    assert "raise the Python floor" in broken.stderr
