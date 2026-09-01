---
id: seeds-144
title: "Automate release tooling: changelog generation, release notes, version coordination"
status: resolved
type: decision
created_at: 2026-05-18T17:25:02.036395+00:00
updated_at: 2026-08-11T19:49:09.188867+00:00
resolved_at: 2026-08-11T19:49:09.188859+00:00
resolution: "Shipped. Verified present today: cliff.toml at the repo root and three git-cliff justfile recipes (changelog-preview, changelog-release, changelog-latest), plus 'just bump-version' which updates the canonical version in src/seeds/__init__.py and both Claude Code plugin manifests in one shot, with tests/test_version_sync.py failing the build if they drift.\n\nExercised end-to-end twice today cutting v0.4.0 and v0.5.0 — the tooling did its job: git-cliff produced the structure and a human wrote the prose over it, and the version bump propagated to the nix flake automatically (the flake parses __init__.py, so a release needs no flake edit).\n\nNote the bead cited by this seed (yjk) is the CI workflow, not the implementing bead — the release tooling itself landed separately. The citation is a mention, not lineage.\n\nEFFICACY: not assessed. Implemented in an earlier session. Resolved on verified end-state — and this one is verified by use rather than inspection, which is stronger."
tags:
  - release
  - automation
  - changelog
  - tooling
  - devx
relationships:
  - target_id: seeds-21
    rel_type: relates-to
    created_at: 2026-05-18T17:25:08.013454+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

**Decision (2026-05-18):** Move toward automated release tooling rather than hand-curated CHANGELOG entries + hand-written GitHub Release bodies.

**Trigger:** Shipping v0.3.0 surfaced that we'd drifted three versions on CHANGELOG.md (v0.2.0, v0.2.1, v0.3.0 all missing). Hand-writing GitHub Release notes for v0.3.0 took effort that could have been generated. The conventional-commit discipline is already there — we should harvest it.

**Direction (specifics TBD as we iterate):**
- Generate per-release notes from conventional commits (feat/fix/chore/docs/etc → grouped sections)
- Keep CHANGELOG.md in Keep-a-Changelog format
- Mirror the same notes into GitHub Releases at tag time
- Optionally: auto-update an [Unreleased] section on every commit (pre-commit hook) so the changelog is always current

**Current pick (open to revisit):** git-cliff — single Rust binary, reads conventional commits, emits both CHANGELOG.md and per-release notes from one config (cliff.toml). Lower install/maintenance cost than release-please (GitHub Action with auto-PR workflow) or python-semantic-release (heavy/opinionated). GitHub's built-in --generate-notes is simpler still but PR/label-driven rather than commit-driven.

**Hand-curated CHANGELOG entries for v0.1.0–v0.3.0 stay as-is** — they're already written and the prose is better than auto-generated. git-cliff takes over for [Unreleased] going forward.

**Related infrastructure decisions:**
- Pre-push CI gate (just wired in this session) — release tooling should hook into the same pre-commit framework rather than its own mechanism.
- seeds-yjk (CI workflow) explicitly scoped automated release tooling OUT of the v0.1.0 beta ("manual tags fine"). This decision revisits that scope now that the project has more release cadence.
