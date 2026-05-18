# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.3.0] - 2026-05-18

Discovery and dedup primitives aimed at the recurring transcript-incorporation
workflow (see `seeds-142` in the seed database for the use-case write-up).

### Added

- **`seeds prime` digest** — appends counts, recently-updated seeds, active
  exploration, open questions, and top tag clusters after the static workflow
  text. Bodies are intentionally omitted; agents `seeds show <id>` for detail.
  Flags: `--no-digest`, `--digest-limit=N`.
- **`seeds suggest "<text>"`** — natural-language dedup query. Ranks existing
  seeds by FTS5 BM25 over title/content/tags/resolution, with multiplicative
  tag-overlap and recency boosts and a dynamic noise floor (drops hits below
  half the top score). Includes resolved/abandoned by default — the question
  is "does this idea exist in our deliberation history?", not "what can I edit
  right now". Flags: `--limit=N`, `--open-only`, `--json`.
- **`seeds list --since=<date>` / `--sort=updated|created`** — surfaces "what
  changed since X" as a first-class CLI primitive instead of forcing agents to
  derive it from `updated_at` timestamps inside seed bodies. Accepts ISO dates
  (`2026-05-08`), relative shorthand (`7d`, `2w`, `3m`, `1y`), and
  `today`/`yesterday`.
- **`seeds recent`** — thin alias for `seeds list --since=7d --sort=updated`.
- **Cross-reference validation on `seeds create` / `seeds update`** —
  rejects bodies that reference unknown `<prefix>-N` IDs (catches the
  hallucinated-cross-reference failure mode). Pass `--allow-unknown-refs` to
  override.

### Changed

- `seeds prime` command help reorganised: `suggest`, `search`, `recent` now
  sit alongside `ready`/`questions`/`deferred`/`blocked` in "Finding Work".

### Tooling

- Pre-push hook wired via pre-commit framework: runs mypy, ruff check, ruff
  format --check, pytest, plus beads pre-push. Matches the GitHub Actions
  lint+test jobs so CI on remote becomes the last line of defense rather
  than the first.
- ruff-pre-commit pin bumped v0.4.0 → v0.15.13 to match the local `uv` ruff
  version (the older pin disagreed with current isort defaults).
- Dev deps migrated from the deprecated `[tool.uv] dev-dependencies` field
  to PEP 735 `[dependency-groups] dev`.
- 359 tests (was 300).

## [0.2.1] - 2026-05-14

Configurable project prefix for seed IDs and supporting `rename-prefix`
improvements. This version was bumped in code but not tagged as a GitHub
release; its features shipped to users as part of v0.3.0.

### Added

- **Configurable project prefix** (`seeds-5at`) — `seeds init --prefix` and
  `seeds rename-prefix <new>` to change the prefix used on seed IDs after
  the fact. `seeds prefix` prints the current value.
- **`seeds rename-prefix --dry-run`** (`seeds-d7o`) — preview ID renames
  and body-reference rewrites without writing.
- **Body-reference rewriting** during `rename-prefix` — IDs mentioned inside
  seed titles/content/resolution are updated alongside the structural rename.
  Use `--no-rewrite-bodies` to skip.

### Documentation

- Added `docs/working-with-seeds.md` — primer + blog workflow.
- Clarified the design-database protection rule in `CLAUDE.md`.

## [0.2.0] - 2026-04-28

### Added

- **Typed relationships** between seeds (Phases 1 + 2): infrastructure +
  CLI/export/web wiring.
- **Sequential IDs** replacing random hashes, with migration of existing
  seeds.
- **Resolution field** to capture what happened when a seed is resolved.
- **Full-text search (FTS5)** across seeds and questions.

### Removed

- Deprecated `Question` / `QuestionStatus` and legacy DB columns.

### Tooling

- ruff lint cleanup, pre-commit hook wiring, beads hook shims to v0.61.0.

### Dependencies

- `click>=8.1.8`
- `flask>=3.1.3`

## [0.1.0] - 2026-02-27

Initial public beta release.

### Added

- **Seed lifecycle**: captured → exploring → resolved/abandoned/deferred
- **Quick capture**: `seeds jot` for minimal-friction idea capture
- **Hierarchical seeds**: parent/child organization with dotted IDs (e.g., `seed-a1b2.1`)
- **Blocking semantics**: seeds with unresolved children cannot be resolved
- **Attached questions**: first-class question objects with open/answered/deferred lifecycle
- **Tagging**: comma-separated tags with filtering support
- **Relationships**: bidirectional `seeds link` for loose coupling between seeds
- **JSONL export**: git-trackable export via `seeds sync --flush-only`
- **AI context**: `seeds prime` command for agent workflow injection
- **Navigation commands**: `seeds ready`, `seeds blocked`, `seeds deferred`, `seeds questions`
- **Experimental web UI**: `seeds serve` for read-only browsing of seeds and questions
- **Doctor command**: `seeds doctor` for installation health checks

[Unreleased]: https://github.com/outcomesinsights/seeds/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/outcomesinsights/seeds/compare/v0.2.0...v0.3.0
[0.2.1]: https://github.com/outcomesinsights/seeds/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/outcomesinsights/seeds/releases/tag/v0.2.0
[0.1.0]: https://github.com/outcomesinsights/seeds/releases/tag/v0.1.0
