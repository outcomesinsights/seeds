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

# Release GATE: prove every commit in the range either renders in the notes or
# is deliberately dropped by a rule in cliff.toml. Exits non-zero and names the
# offenders otherwise. Run this before `changelog-release`.
#
# This replaced `changelog-audit` (removed 2026-08-31, bead seeds-0t1), which
# printed a commit count beside an entry count. Counts cannot name the commit
# that vanished, and 100-vs-39 looks equally reasonable whether or not `build:
# raise the Python floor to 3.11` is among the 61 that did not render — which is
# how the same omission got through three times running. Two overlapping checks
# where one is weaker only invites running the weak one, so there is now one.
#
# The skip rules are read out of cliff.toml, never hardcoded here; a second copy
# of that list is what went stale in the check this replaces.
#
# Optional argument overrides the range (default: <latest tag>..HEAD).
changelog-coverage RANGE="":
    @uv run python scripts/changelog_coverage.py {{RANGE}}

# Release GATE, second half: prove the section you just WROTE into CHANGELOG.md
# matches the notes git-cliff generates. `changelog-coverage` gates the
# generator; this gates the artifact. They are not the same check, and passing
# the first says nothing about the second — 0.6.0's section fell behind the
# generated notes twice, both times caught only by diffing the two by hand.
#
# Names anything git-cliff put under a gated group (everything except
# Documentation and Tooling) that the section neither links nor records a
# deliberate `<!-- changelog-omit: <sha> <why> -->` marker for, plus anything
# the section links that is not in the range at all.
#
# Run it AFTER pasting and polishing, and immediately before the commit and tag
# — writing the changelog last is what stops the section going stale in the
# first place; this is the belt to that suspenders.
#
# Usage: just changelog-section 0.7.0   (optional second arg overrides the range)
changelog-section VERSION RANGE="":
    @uv run python scripts/changelog_coverage.py --section {{VERSION}} {{RANGE}}

# Gate: prove flake.nix's runtime dependency list still mirrors pyproject.toml's
# [project.dependencies]. Exits non-zero and NAMES the mismatched dependency.
#
# Same shape of question as changelog-coverage above — "does the derived
# artifact still match its source?" — so it is a sibling script rather than its
# own ceremony (bead seeds-8ro). Two artifacts derive from that dependency list,
# uv.lock and flake.nix; `uv lock --check` gates the first and this gates the
# second.
#
# Also runs in the pre-push stage, immediately ahead of `nix flake check`, which
# is what used to catch this: dropping flask from pyproject.toml on 2026-08-31
# left flake.nix naming it, and ruff, mypy, the full pytest suite and `uv lock
# --check` were ALL green with the mismatch in place. The nix job found it two
# minutes in. This does the same comparison in milliseconds.
#
# Pure stdlib, so it needs no venv — but run through uv here to match the other
# recipes. The hook calls `python3` directly.
flake-deps:
    @uv run python scripts/flake_deps_check.py
