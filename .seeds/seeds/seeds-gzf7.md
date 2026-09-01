---
id: seeds-gzf7
title: git-cliff --unreleased silently drops commits after a merge — the release recipe would have shipped an incomplete changelog
status: resolved
type: concern
created_at: 2026-08-26T19:59:30.352755+00:00
updated_at: 2026-08-31T21:35:01.705778+00:00
resolved_at: 2026-08-31T21:35:01.705772+00:00
resolution: "Fixed: the changelog recipes use an explicit $(git describe --tags --abbrev=0)..HEAD range instead of --unreleased, with this seed's measurement preserved as a justfile comment so it is not simplified back, and 'just changelog-coverage' now verifies per-commit that nothing was silently dropped (bead seeds-0t1 promoted the detector into the repo; bead seeds-3sh fixed the cliff.toml rule that ate build: commits). Efficacy: no tweaking. Residual gap, deliberately left as open bead seeds-3ti rather than holding this seed: coverage gates the generator, not the committed CHANGELOG.md artifact."
tags:
  - release
  - changelog
  - git-cliff
  - tooling
  - silent-failure
  - verified
  - 2026-08-26
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Found 2026-08-26 while preparing the v0.6.0 release. This is a silent-failure class defect in the release tooling itself, which is the worst place for one.

WHAT WAS OBSERVED, verified rather than inferred. After merging origin/main (three dependabot commits) into local main:

  just changelog-preview     (= git-cliff --unreleased)  ->  5 entries
  git-cliff v0.5.0..HEAD     (explicit range)            -> 12 entries

`git log v0.5.0..HEAD --oneline | wc -l` reports 34 commits, and all three of the dropped code commits were confirmed as genuine ancestors of HEAD and descendants of the v0.5.0 tag via `git merge-base --is-ancestor`. So the commits are unambiguously unreleased and git-cliff's `--unreleased` mode is not seeing them.

WHAT WOULD HAVE SHIPPED. The dropped entries include:
- `54057b1` fix(export): make the divergence guard's guidance able to satisfy itself -- one of the THREE headline fixes of the release
- `194cd3e` fix(lint): set ruff target-version to py310 to match requires-python
- `ca568b0` ci: make pre-push actually match CI (Python matrix + nix job)
- four dependabot dependency bumps

A release cut with `just changelog-release v0.6.0` -- which is `git-cliff --unreleased --tag`, the same broken mode -- would have published release notes missing a third of the actual fixes, with no warning. The generated output looks complete; nothing about it says "I truncated this."

LIKELY CAUSE, stated as a hypothesis rather than a finding: the merge gives HEAD two parents, and `--unreleased` appears to stop walking when it reaches the v0.5.0 tag on one path, truncating whatever sits on the other. Note `cliff.toml` sets `topo_order = false` and `sort_commits = "newest"`, which may interact. The oddest detail, and the one that would confirm or kill the hypothesis: `89e6db0` was KEPT while its own parent `54057b1` was dropped, so it is not a simple "everything before commit X" cutoff. Worth reproducing on a scratch repo before believing any particular explanation.

THE FIX IS CHEAP, whatever the cause. Change the justfile recipes to use an explicit range against the latest tag rather than `--unreleased`:

  changelog-preview:  git-cliff $(git describe --tags --abbrev=0)..HEAD
  changelog-release VERSION:  git-cliff $(git describe --tags --abbrev=0)..HEAD --tag {{VERSION}}

THE BROADER POINT, and the reason this is a concern rather than a chore: this repo's own data-pipeline standard says a stale-check that reports green while the artifact is broken is the failure mode to design against, and that the detector itself is code that can be silently wrong. The release changelog is exactly such an artifact, and its generator just demonstrated the failure. A guard worth adding: at release time, assert that the number of non-skipped commits in the generated section matches what the explicit range produces, and fail loudly on a mismatch.

Related: the same run surfaced that `cliff.toml` has no breaking-change handling at all (`grep -c breaking cliff.toml` returns 0), so a `BREAKING CHANGE:` footer or a `type!:` subject renders under "Fixed" like anything else. The v0.5.0 Breaking section was hand-written. These are two independent gaps in the same tool.


--- FIXED (2026-08-26, commit 7cad77f) ---

`changelog-preview` and `changelog-release` now take an explicit `$(git describe --tags --abbrev=0)..HEAD` range instead of `--unreleased`. Verified immediately after: preview went from 6 entries to 13, and `just changelog-release v0.6.0` renders all four Fixed entries including 54057b1, the one that was being dropped.

Added a third recipe, `changelog-audit`, printing the range, the commit count (37) and the rendered entry count (13) side by side. Deliberately NOT a pass/fail gate: cliff.toml legitimately skips chore(beads), chore(seeds*), style, test and unconventional subjects, so a gap is expected and a hard assertion would either be wrong or would have to duplicate the skip rules and drift from them. It is a read-before-release check, which is the honest shape for something whose whole job is to make a silent truncation visible.

`changelog-latest` was left on `--latest`. It renders a closed tag..tag range rather than walking back from an open HEAD, so it does not share the defect — noted in the justfile that it has not been re-verified against a release whose range spans a merge.

The justfile comment carries the measured numbers and a "do not simplify this back" warning, because reverting to `--unreleased` is the obvious tidy-up and would silently reintroduce the bug.

STILL OPEN from this seed, and it is the other half: cliff.toml has no breaking-change handling at all. A `BREAKING CHANGE:` footer or a `type!:` subject still renders under "Fixed". v0.6.0 carries THREE breaking changes, so its Breaking section has to be hand-written the way v0.5.0's was. Worth a separate seed if the hand-writing turns out to be a recurring cost rather than a one-off.

## SECOND INSTANCE (2026-08-31), different mechanism, same failure

Found while pre-flighting the 0.6.0 release. The first instance was the *range* (`--unreleased` walking past a merge), fixed by pinning an explicit tag range in the recipe (7cad77f). The range is now correct — and the changelog was still incomplete, for an unrelated reason.

**`cliff.toml`'s `commit_parsers` has no entry for the conventional-commit type `build:`.** The table ends with a catch-all `{ message = ".*", skip = true }`, and `filter_commits` is on, so an unmatched type is dropped **silently** — no warning names it.

The commit it swallowed: `6a70429 build: raise the Python floor to 3.11`, which **removes Python 3.10 support** — the most user-affecting change in 0.6.0. Verified by grepping the generated output for "3.11" and "python floor": zero hits. It would have shipped with no mention in the release notes.

Filed as a bead (the cliff.toml parser gap, P1).

**Not to be confused with the warning the preview prints.** `WARN: 7 commit(s) were skipped due to parse error(s)` is exactly the 7 merge commits in the range. Those are not conventional commits and are correctly ignored — that warning is working as intended and is a red herring here. The `build:` drop produced no warning at all, which is precisely what makes it the same defect as the first instance.

## What the two instances share, and the lesson worth keeping

Both are **the changelog omitting work while reporting success.** The mechanisms are unrelated — one a range bug, one a parser gap — which is the point: fixing the first did nothing to prevent the second, because neither fix addressed the shape they share.

The root cause is the catch-all's `skip = true`. A generator that silently discards anything it does not recognise will keep finding new ways to discard things. **A changelog that omits real work is worse than one carrying an untidy line**, so the safer default is to surface an unmatched commit rather than drop it — noisy output gets edited during the polish step that already exists in the release procedure, whereas an omission is invisible by construction.

Also worth noting how it was caught, since it was not caught by either fix: a deliberate pre-release audit that *diffed the generated output against the actual commit list*, rather than reading the generated output and finding it plausible. That check — "does every user-facing commit in the range appear somewhere in the notes?" — is the thing that finds this class, and it belongs in the release procedure.

## Incidental friction found while filing this

`seeds update` refused this very append with "seed body references unknown IDs: seeds-3sh". That is a **bead** ID, not a seed ID — but beads and seeds in this repo share the `seeds-` prefix, so the cross-reference validator cannot tell one tracker's IDs from the other's and treats every bead reference as a dangling seed reference. `--allow-unknown-refs` is the workaround. Worth deciding whether that validator should know about the sibling tracker, since seeds and beads are designed to be used together and citing a bead from a seed is the normal case, not an exception.

FIXED — the justfile's changelog recipes now use an explicit $(git describe --tags --abbrev=0)..HEAD range, never `--unreleased`, with a comment block carrying this seed's measurement so nobody "simplifies" it back. `just changelog-coverage` (scripts/changelog_coverage.py, bead seeds-0t1) then verifies every commit in the range either renders or matches a deliberate cliff.toml skip rule. RESIDUAL, tracked separately as open bead seeds-3ti: coverage gates the GENERATOR, not the artifact — a hand-polished CHANGELOG.md section that fell behind the generated notes still passes, which bit twice during 0.6.0.
