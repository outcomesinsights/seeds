"""Guard that README's skills list still names every shipped skill (bead seeds-xiy).

Skills are discovered by *directory*: ``seeds skills install`` copies
``src/seeds/plugin/claude-plugin/skills/`` wholesale, and ``plugin.json``
enumerates nothing. So the only declaration of what ships is the directory
listing — and README carries a second, hand-maintained copy of it under
``### Available skills``.

That is the same two-artifact drift shape as ``flake.nix`` mirroring
``pyproject.toml``'s dependencies, which this repo gated in
``scripts/flake_deps_check.py`` after it silently desynced. Here it had already
happened: on 2026-09-02 seven skills shipped and README named three. ``cutting``,
``glean``, ``resolve-seeds-from-beads`` and ``winnow`` were invisible to anyone
reading the docs, and nothing anywhere failed. Two sub-agents noticed by eye,
which is not a gate.

The check reads the repo source tree rather than an installed package, so it
validates exactly what gets committed.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "src" / "seeds" / "plugin" / "claude-plugin" / "skills"
README = REPO_ROOT / "README.md"

SECTION_HEADING = "### Available skills"

# One bullet of the list: `- **\`seeds:winnow\`** — …`, where the separator is the
# em dash (\u2014) the whole list uses. The `seeds:` namespace prefix is
# required, because that is how the skills are actually invoked.
SKILL_BULLET_RE = re.compile(
    r"^- \*\*`seeds:(?P<name>[a-z0-9][a-z0-9-]*)`\*\*"
    r"\s*\u2014\s*(?P<description>\S.*)$",
    re.MULTILINE,
)


def shipped_skills() -> set[str]:
    """Every skill directory that ships, i.e. every one holding a SKILL.md."""
    assert SKILLS_DIR.is_dir(), f"no skills directory at {SKILLS_DIR}"
    names = {
        path.name for path in SKILLS_DIR.iterdir() if (path / "SKILL.md").is_file()
    }
    # A directory listing that came back empty would let every assertion below
    # pass vacuously — exactly how a mirror check reports green on the day it
    # matters.
    assert names, f"{SKILLS_DIR} holds no skill directories; refusing to compare"
    return names


def readme_skills_section() -> str:
    """The body of README's `### Available skills` section.

    Missing or duplicated headings are a failure, not an empty section: this
    guard would otherwise pass by reading nothing at all the day somebody
    restructures README.
    """
    text = README.read_text()
    parts = text.split(SECTION_HEADING)
    assert len(parts) == 2, (
        f"README.md has {len(parts) - 1} `{SECTION_HEADING}` headings; "
        "this guard models exactly one skills list."
    )
    # Up to the next heading of any level.
    return re.split(r"^#", parts[1], maxsplit=1, flags=re.MULTILINE)[0]


def listed_skills() -> dict[str, str]:
    """Skill name -> description, as README's bullets spell them."""
    section = readme_skills_section()
    listed = {
        match.group("name"): match.group("description")
        for match in SKILL_BULLET_RE.finditer(section)
    }
    assert listed, (
        f"README.md's `{SECTION_HEADING}` section has no "
        "`- **`seeds:<name>`** — <description>` bullets. Keep the list in that "
        "shape, or teach this guard the new one — do not leave it matching "
        "nothing, which reports green on an empty list."
    )
    return listed


def test_readme_lists_every_shipped_skill():
    shipped = shipped_skills()
    listed = set(listed_skills())

    missing = sorted(shipped - listed)
    assert not missing, (
        f"{len(missing)} skill(s) ship under {SKILLS_DIR.relative_to(REPO_ROOT)} "
        f"and README.md's `{SECTION_HEADING}` list does not name them: "
        f"{', '.join(missing)}. Add a bullet for each, taking its wording from "
        "the skill's own SKILL.md `description` frontmatter."
    )


def test_readme_lists_no_skill_that_does_not_ship():
    shipped = shipped_skills()
    listed = set(listed_skills())

    phantom = sorted(listed - shipped)
    assert not phantom, (
        f"README.md's `{SECTION_HEADING}` list names {', '.join(phantom)}, and "
        f"no such skill directory exists under "
        f"{SKILLS_DIR.relative_to(REPO_ROOT)}. Installing the plugin will not "
        "produce it."
    )


def test_every_listed_skill_has_a_description():
    for name, description in listed_skills().items():
        assert len(description.split()) >= 5, (
            f"README.md's bullet for `seeds:{name}` has no real description "
            f"({description!r}); write one line from the skill's SKILL.md "
            "`description` frontmatter."
        )
