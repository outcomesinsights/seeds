test:
    uv run pytest

# Bump the version in every place it must appear: src/seeds/__init__.py
# (canonical; pyproject derives it) plus the two Claude Code plugin manifests.
# Usage: just bump-version 0.3.2
bump-version VERSION:
    @uv run python scripts/bump_version.py {{VERSION}}

# git-cliff drives [Unreleased] and future versions in CHANGELOG.md;
# v0.1.0–v0.3.0 sections are intentionally hand-written. See cliff.toml.

# Preview the [Unreleased] section from commits since the latest tag.
#
# These use an EXPLICIT range, NOT `--unreleased`. Do not "simplify" them back;
# `--unreleased` silently under-reports once HEAD has a merge in it.
#
# Measured 2026-08-26, preparing v0.6.0, right after merging origin/main:
#   git-cliff --unreleased                 ->  6 entries
#   git-cliff $(latest-tag)..HEAD          -> 13 entries
# The seven it dropped included 54057b1, one of the three headline fixes of the
# release. Every dropped commit was confirmed a genuine descendant of v0.5.0 and
# ancestor of HEAD, so they were unambiguously unreleased. Nothing in the output
# says it truncated anything — it just looks complete and is not, which is what
# makes it dangerous in a release recipe. Full evidence: seed seeds-gzf7.
changelog-preview:
    @git-cliff "$(git describe --tags --abbrev=0)..HEAD"

# Preview a tagged release section (usage: just changelog-release v0.6.0).
# Same explicit range, same reason — this is the recipe that generates the notes
# that actually ship, so it is the one that must not silently drop commits.
changelog-release VERSION:
    @git-cliff "$(git describe --tags --abbrev=0)..HEAD" --tag {{VERSION}}

# Sanity check — re-render the latest tagged release from history.
# `--latest` renders a closed tag..tag range rather than walking back from an
# open HEAD, so it does not share the defect above. It has not been re-verified
# against a release whose range spans a merge; if one ever looks short, suspect
# the same cause.
changelog-latest:
    @git-cliff --latest

# Release guard: how many commits the range holds vs how many entries render.
# The gap is expected (cliff.toml skips chore(beads)/chore(seeds)/style/test and
# unconventional subjects), so this is an eyeball check, not a pass/fail gate —
# read it before cutting a release and confirm the entry count matches the real
# user-facing work. Exists because the failure it guards against reports green.
changelog-audit:
    @echo "range:   $(git describe --tags --abbrev=0)..HEAD"
    @echo "commits: $(git log --oneline $(git describe --tags --abbrev=0)..HEAD | wc -l | tr -d ' ')"
    @echo "entries: $(git-cliff "$(git describe --tags --abbrev=0)..HEAD" 2>/dev/null | grep -c '^- ' | tr -d ' ')"
    @echo "skipped by cliff.toml (expected): chore(beads), chore(seeds*), style, test, merge commits"
