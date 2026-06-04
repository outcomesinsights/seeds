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
changelog-preview:
    @git-cliff --unreleased

# Preview a tagged release section (usage: just changelog-release v0.4.0).
changelog-release VERSION:
    @git-cliff --unreleased --tag {{VERSION}}

# Sanity check — re-render the latest tagged release from history.
changelog-latest:
    @git-cliff --latest
