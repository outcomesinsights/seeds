test:
    uv run pytest

# Bump the version in every place it must appear: src/seeds/__init__.py
# (canonical; pyproject derives it) plus the two Claude Code plugin manifests.
# Usage: just bump-version 0.3.2
bump-version VERSION:
    @uv run python scripts/bump_version.py {{ VERSION }}

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
    @git-cliff "$(git describe --tags --abbrev=0)..HEAD" --tag {{ VERSION }}

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
    @uv run python scripts/changelog_coverage.py {{ RANGE }}

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
    @uv run python scripts/changelog_coverage.py --section {{ VERSION }} {{ RANGE }}

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

# Differential harness: prove the 0.7 storage change costs nothing behaviourally
# (bead seeds-4co.17). Names one or more repo roots; each store is COPIED, never
# converted in place, so this is safe to point at a repo the operator has not
# converted yet.
#
# It builds a real seeds 0.6 from the v0.6.0 tag with `git archive` (a worktree
# would write into the shared .git of a repo this is only allowed to read),
# drives both versions over the same command set, and reports every difference
# that is not on the declared allowlist. Run `just differential-allowlist` for
# the entries and the argument behind each one.
#
# The cross-repo half runs the retired `cat .seeds/seeds.jsonl` recipe and the
# documented `seeds export --json | duckdb` one over the same repo set and diffs
# the two answers -- that is what proves the replacement is equivalent for the
# one workflow that spans repos. Give it two or more repos for that to mean
# anything.
#
# Exit 0 clean, 1 with unexplained differences, 2 when it refuses to guess. A
# refusal is named -- the summary groups the refused repos by cause and prints
# the argument for each, because "seeds 0.6 cannot read this store either" and
# "seeds 0.7's converter crashed" call for opposite responses.
# Every run tees a timestamped log into claude_stuff/ and prints the path.
#
# Usage: just differential ~/projects/outins/vocabulary_formats ~/projects/outins/epc
differential *REPOS:
    @uv run python scripts/differential_harness.py {{ REPOS }}

# The allowlist and the written justification for each entry.
differential-allowlist:
    @uv run python scripts/differential_harness.py --show-allowlist

# Self-test the harness: inject a deliberate behavioural difference into the
# converted copy and REQUIRE it to be reported. Each of these exits 0 only if
# the difference was caught, so a harness that has gone blind fails here rather
# than reporting a clean bill of health on a broken conversion.
#
# This is the control for the failure mode the bead names: an allowlist written
# broadly enough to swallow a real regression. Point it at a small repo.
#
# Usage: just differential-selftest ~/projects/outins/vocabulary_formats
differential-selftest REPO:
    @uv run python scripts/differential_harness.py {{ REPO }} --inject drop-seed --no-cross-repo
    @uv run python scripts/differential_harness.py {{ REPO }} --inject mutate-title --no-cross-repo
    @uv run python scripts/differential_harness.py {{ REPO }} --inject truncate-body --no-cross-repo

# Rewrite files to canonical format. Run deliberately; never from a hook.
fmt:
    uv run ruff format .
    git ls-files "*.nix" | xargs -r nixfmt
    just --fmt --unstable
    git ls-files "*.md" | xargs -r mdformat

# Report format drift without changing anything. This is what the hooks run —
# a formatter that rewrites files mid-commit changes what you already reviewed.
fmt-check:
    uv run ruff format --check .
    git ls-files "*.nix" | xargs -r nixfmt --check
    just --fmt --check --unstable
    git ls-files "*.md" | xargs -r mdformat --check

# Full local CI equivalent — run this before pushing.
# The recipe IS the contract: if CI runs a check and this does not, the gate is
# decorative (see ~/.config/home-manager/docs/ci-gates.md).
ci: fmt-check test

# What actually runs before a push. Defaults to the complete `ci`; point it at
# something smaller ONLY where running complete CI locally is impractical.
pre-push: ci

# Runs on every commit, so it must stay FAST — a sub-minute budget. Tests belong
# here when they fit; lint alone when they do not. fmt-check never rewrites.
pre-commit: fmt-check

# Arm THIS clone's git hooks. A gate in .git/hooks is per-clone and untracked, so a
# fresh clone silently has none; this recipe is the tracked declaration that one is
# expected, plus the installer. `habituate repo-doctor` reports an unarmed clone.
# Chains the beads hook first and preserves any hook it did not write.
hooks:
    #!/usr/bin/env bash
    set -euo pipefail
    root="$(git rev-parse --show-toplevel)"
    # Resolve from the GIT DIR, not `--git-path hooks`. beads points core.hooksPath at
    # .beads/hooks and `--git-path` HONOURS it, so the obvious call aims this recipe at
    # beads' own tracked shim -- the very file the generated hook then chains to. The
    # hook ends up calling itself and every commit recurses until the shell gives up.
    # Measured 2026-09-13: `git commit` hung with no output whatsoever, reporting only
    # "shell level (1000) too high", until it was killed at two minutes. The guard
    # below is the half that matters: it turns a silent self-call into a loud refusal.
    hooks="$(git rev-parse --absolute-git-dir)/hooks"
    case "$hooks" in
        */.beads/hooks)
            echo "refusing to write hooks inside .beads: $hooks" >&2
            echo "core.hooksPath still points at beads; unset it first" >&2
            exit 1
            ;;
    esac
    mkdir -p "$hooks"
    for h in pre-commit pre-push; do
        just --summary 2>/dev/null | tr ' ' '\n' | grep -qx "$h" || continue
        live="$hooks/$h"
        # Never clobber a hook this recipe did not write; chain it instead.
        keep=""
        if [ -f "$live" ] && ! grep -qs 'just hooks' "$live"; then
            mkdir -p "$hooks/preserved"
            keep="$hooks/preserved/$h"
            [ -e "$keep" ] || { mv "$live" "$keep"; chmod +x "$keep"; }
        fi
        {
            echo '#!/usr/bin/env sh'
            echo '# Written by `just hooks`. Re-run to regenerate.'
            echo 'set -e'
            echo 'root="$(git rev-parse --show-toplevel)"'
            echo 'hooks="$(git rev-parse --absolute-git-dir)/hooks"'
            [ -n "$keep" ] && echo "p=\"\$hooks/preserved/$h\"; [ -x \"\$p\" ] && { \"\$p\" \"\$@\" || exit \$?; }"
            echo "b=\"\$root/.beads/hooks/$h\"; [ -x \"\$b\" ] && { \"\$b\" \"\$@\" || exit \$?; }"
            echo "cd \"\$root\" && exec just $h"
        } > "$live"
        chmod +x "$live"
        echo "armed: $h"
    done
