test:
    uv run pytest

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
