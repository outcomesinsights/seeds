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
    git ls-files "*.md" | xargs -r uv run mdformat

# Report format drift without changing anything. This is what the hooks run —
# a formatter that rewrites files mid-commit changes what you already reviewed.
fmt-check:
    uv run ruff format --check .
    git ls-files "*.nix" | xargs -r nixfmt --check
    just --fmt --check --unstable
    git ls-files "*.md" | xargs -r uv run mdformat --check

# Gate: the lock must match pyproject. MUST run before anything invokes
# `uv run`, which re-locks by default and leaves this passing unconditionally —
# the same ordering trap ci.yml documents above its own copy (bead seeds-3p1).
# That is why it is a prerequisite of `ci` and listed first, not a line in a
# later recipe.
lock-check:
    uv lock --check

# The LINTER, which is not the formatter. `ruff format --check` says nothing
# about unused imports, shadowed names, or anything else in ruff's lint rules,
# and mypy says nothing that either of them does.
#
# Absent from `ci` until 2026-09-23 (bead seeds-6zi). The cost was not
# hypothetical: 0.7.0a7 shipped two ruff findings and a mypy error, and CI could
# not have caught them either, because ci.yml only triggered on `main` and this
# work happens on the 0.7.0 branch. Both gates missed for 213 commits.
lint:
    uv run ruff check .
    uv run mypy src/

# The fast, serial checks every gate starts with. `lock-check` is first because
# it has to precede anything that runs `uv run`. Shared by `ci` and `pre-push`
# so the two cannot drift apart.
checks: lock-check lint fmt-check flake-deps

# Local CI equivalent for the lint and test jobs, on the local interpreter.
# The recipe IS the contract: if CI runs a check and this does not, the gate is
# decorative (see ~/.config/home-manager/docs/ci-gates.md). `pre-push` below
# adds the rest of ci.yml: the other Python versions and the nix job.
ci: checks test

# ci.yml's test job runs 3.11, 3.12 and 3.13; `test` covers only the local
# interpreter (3.13). Each version gets its OWN environment. The hook this
# replaced ran `uv run --python 3.11 --no-sync pytest`, and --no-sync makes uv
# fall back to the existing 3.13 .venv ("Using incompatible environment"), so
# it re-ran 3.13 twice and never exercised 3.11 or 3.12 (seeds-29i, measured
# 2026-09-28).
test-matrix:
    for v in {{ matrix }}; do echo "--- python $v ---"; "{{ just_executable() }}" test-python "$v" || exit 1; done

# The non-local interpreters `test-matrix` and `pre-push` cover.
matrix := "3.11 3.12"

# One interpreter of the matrix, in its own environment (usage: just test-python 3.11).
test-python VERSION:
    UV_PROJECT_ENVIRONMENT=".venv-py{{ VERSION }}" uv run --python "{{ VERSION }}" pytest -q

# Mirrors ci.yml's nix job verbatim; its comments explain the two-run split.
# Skips when nix is absent, since this repo is public and a contributor without
# nix must still be able to push. ~7s warm; much slower after a flake.lock
# change.
nix-check:
    #!/usr/bin/env bash
    set -euo pipefail
    command -v nix >/dev/null 2>&1 || { echo "nix not on PATH — skipping (CI still runs this job)"; exit 0; }
    nix flake check --all-systems --no-build
    nix flake check --print-build-logs
    nix run . -- --version

# What runs before a push: every job in ci.yml, so a green push means a green CI
# (seeds-29i, ruled 2026-09-28). The serial `checks` go first, because
# `lock-check` has to precede anything that runs `uv run`. Then the four test
# runs -- `test` on the local interpreter, `test-python` for each version in
# `matrix`, and `nix-check` -- run CONCURRENTLY (seeds-0o5): they were 94% of a
# 524s serial gate, and each already has its own environment.
#
# Why concurrency is safe here, checked rather than assumed (seeds-0o5):
# - uv.lock: `lock-check` has just proved it current, and UV_LOCKED=1 turns any
#   re-lock a job would attempt into a loud failure instead of a racing write.
# - The uv cache is documented as safe for concurrent readers and writers.
# - pytest's /tmp/pytest-of-$USER/pytest-N dirs are made with an atomic mkdir
#   and each carries a lock file that stops another session's cleanup deleting
#   it while in use. The nix job's pytest runs in the build sandbox anyway.
#
# Each job logs to claude_stuff/pre-push-<stamp>-<job>.log. Every PID is waited
# on and its status checked individually; a failure names the job and its log
# and prints the log's tail, and the recipe exits non-zero.
pre-push: checks
    #!/usr/bin/env bash
    set -euo pipefail
    export UV_LOCKED=1
    mkdir -p claude_stuff
    prefix="claude_stuff/pre-push-$(date +%Y%m%d-%H%M%S)"
    # Parallel indexed arrays, not `declare -A`: macOS's /bin/bash is 3.2.
    names=()
    pids=()
    launch() { # launch <job name> <command...>
        local name=$1
        shift
        (
            start=$SECONDS
            if "$@"; then rc=0; else rc=$?; fi
            echo "[$name] exit $rc after $((SECONDS - start))s"
            exit "$rc"
        ) >"$prefix-$name.log" 2>&1 &
        pids+=("$!")
        names+=("$name")
        echo "started $name (pid $!) -> $prefix-$name.log"
    }
    trap 'kill "${pids[@]}" 2>/dev/null || true' INT TERM
    launch test "{{ just_executable() }}" test
    for v in {{ matrix }}; do launch "test-py$v" "{{ just_executable() }}" test-python "$v"; done
    launch nix-check "{{ just_executable() }}" nix-check
    failed=""
    for i in "${!names[@]}"; do
        name=${names[$i]}
        if wait "${pids[$i]}"; then
            echo "ok     $name  ($(tail -n 1 "$prefix-$name.log"))"
        else
            echo "FAILED $name (exit $?) -- log: $prefix-$name.log"
            failed="$failed $name"
        fi
    done
    [ -z "$failed" ] && { echo "pre-push passed; logs: $prefix-*.log"; exit 0; }
    for name in $failed; do
        echo
        echo "===== $name: last 40 lines of $prefix-$name.log ====="
        tail -n 40 "$prefix-$name.log"
    done
    echo
    echo "pre-push FAILED:$failed"
    exit 1

# Runs on every commit, so it must stay FAST — a sub-minute budget. Tests belong
# here when they fit; lint alone when they do not. fmt-check never rewrites.
pre-commit: fmt-check
