# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.3.4] - 2026-07-16

This release adds a new output mode: turning a matured seed into a *trellis*.

`seeds trellis <id> --to <file> --as "<principle>"` distills a resolved seed's
deliberation into one crisp, bounded principle and writes it — with a two-way
provenance link — into durable, always-on project context such as `CLAUDE.md`
or `README`, then resolves the seed. A trellis is a load-bearing principle
you want every future session steered by; it lives in the context the agent
runtime injects each session, not in anything seeds surfaces internally. A
companion `seeds:trellis` skill supplies the language judgment — distilling the
one-line principle and advising the target file — and fires when you say
"promote this" or "make this a trellis". The verb's bookkeeping stays
deterministic (a provenance bullet under a `## Principles` section, a
`trellis` tag, and resolution), and README and CLAUDE.md explain when to
reach for it.

This release also **drops Python 3.9** (end-of-life; `requires-python` is now
`>=3.10`) and refreshes the dev toolchain — mypy 2.3, pytest 9.1, ruff 0.15.22,
and pre-commit 4.6.

## [0.3.3] - 2026-06-24

This release rounds out the seeds↔beads workflow and makes JSONL import a
first-class, round-trippable operation.

On the workflow side, the bundled skills now carry intent in both directions.
`seeds-to-beads` records the *why* behind each bead — locked decisions and their
rationale, verbatim stakeholder voice on subjective calls, and seed lineage —
and suggests a short efficacy note to capture when the work is done. A new
`resolve-seeds-from-beads` skill closes the loop: after an implementation
session it reconciles what actually shipped back into the originating seeds,
captures that efficacy note, and resolves them.

On the data side, `seeds import` lands with last-write-wins upsert semantics, a
fresh-clone bootstrap, and prefix recovery, so a seeds database can be rebuilt
from its JSONL export and synced round-trip without drift.

### Added

- **`seeds import [PATH|-]` with round-trip `seeds sync`.** Import seeds from a
  JSONL file or stdin; export and re-import are now lossless, enabling
  backup/restore and cross-clone sync.
- **Fresh-clone bootstrap + prefix recovery on import.** A freshly cloned repo
  with only its JSONL export can reconstruct a working database, recovering the
  project's seed-ID prefix.
- **Last-write-wins upsert for import.** Re-importing reconciles by `updated_at`
  and reports an `ImportResult` summary instead of duplicating or clobbering.
- **Executor intent in the `seeds-to-beads` skill.** Converted beads now record
  locked decisions + their rationale, verbatim stakeholder voice, and seed
  lineage — separating motivation from constraints.
- **Efficacy note suggested at seed resolution.** `seeds-to-beads` now proposes
  a short qualitative note (tweaking needed? planning-miss vs inherent unknown?)
  to capture when the originating seed is resolved.
- **New `resolve-seeds-from-beads` skill.** The symmetric bookend to
  `seeds-to-beads`: reconcile deliberation against what shipped, capture the
  efficacy note, and resolve the seeds.

### Documentation

- Added the intent-debt investigation and feedback-response notes under `docs/`.

### Tooling

- Beads now exports `issues.jsonl` on commit via a hook.
- Relocked ruff (0.15.14 → 0.15.16); raised the requirement floor to >=0.15.15.

## [0.3.2] - 2026-06-04

A correctness release for the Claude Code skills installer. `seeds skills
install` now guarantees the plugin ends up *enabled*, so the bundled `seeds:*`
skills actually load in new Claude Code sessions — previously the plugin could
install but sit disabled, silently contributing nothing. Clean package builds
are restored, and the version is now single-sourced so the CLI and the plugin
manifests can no longer drift apart.

### Fixed

- **`seeds skills install` now enables the plugin.** The command registered the
  marketplace and installed the plugin but never enabled it, so it could remain
  `disabled` in `~/.claude/settings.json` and load none of its skills. It now
  runs `claude plugin enable` on every install/update. A new `--reinstall`
  (alias `--upgrade`) flag refreshes the marketplace from source and replaces a
  stale cached copy after the seeds CLI itself is upgraded.
- **Clean wheel builds.** A redundant hatchling `force-include` re-mapped the
  bundled plugin files to wheel paths already provided by `packages`, so any
  build from a clean cache failed with a "same path" collision. Removing it
  fixes `uv build` / `uv tool install`.
- **Beads pre-commit hook.** Set `BD_GIT_HOOK=1` in the pre-commit entry to
  avoid a `.git/index.lock` race during beads' auto-export.

### Tooling

- **Single-sourced the package version.** `pyproject.toml` now derives the
  version from `src/seeds/__init__.py` (hatchling dynamic version); the two
  plugin manifests are kept in lockstep by `just bump-version`, guarded by a
  test that fails the build on drift. Previously the version lived in four
  hand-edited places and had already drifted (plugin manifests at 0.2.0 while
  the CLI was 0.3.1).

## [0.3.1] - 2026-05-27

First Claude Code skills shipped with seeds. The new `seeds skills install`
command registers a bundled local marketplace and installs the `seeds` plugin
under the `seeds:*` namespace (mirroring the `beads:*` pattern). Two
prompt-macro skills ship in this release; see `seeds-152` and its sub-seeds in
the seed database for the deliberation that produced them.

### Added

- **`seeds skills install`** — registers the bundled Claude Code plugin
  marketplace and installs (or updates) the `seeds` plugin under the user
  scope. Idempotent; safe to re-run after `uv tool upgrade seeds`.
- **`seeds:feedback` skill** — prompt-macro that frames the next user message
  as feedback on the agent's prior turn, then has the agent invite further
  questions, comments, or criticisms exactly once. Per the deliberation that
  produced it, the closer's value comes from being user-initiated; the skill
  explicitly scopes the invitation to the single reply being generated rather
  than installing it as ongoing agent behavior.
- **`seeds:seeds-to-beads` skill** — prompt-macro for converting deliberated
  seeds into a set of beads suitable for execution by a Sonnet-based agent.
  Encodes principles for separating actionable scope from context, embedding
  content templates in bead descriptions, writing mechanical acceptance
  criteria, and setting explicit dependencies.
- **Claude Code plugin tree** under `src/seeds/plugin/` — `seeds-marketplace`
  + `seeds` plugin manifests for local distribution. Bundled with the Python
  package via Hatchling's `force-include`.

### Documentation

- README section describing the Claude Code skills and the install command.

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

[Unreleased]: https://github.com/outcomesinsights/seeds/compare/v0.3.3...HEAD
[0.3.3]: https://github.com/outcomesinsights/seeds/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/outcomesinsights/seeds/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/outcomesinsights/seeds/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/outcomesinsights/seeds/compare/v0.2.0...v0.3.0
[0.2.1]: https://github.com/outcomesinsights/seeds/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/outcomesinsights/seeds/releases/tag/v0.2.0
[0.1.0]: https://github.com/outcomesinsights/seeds/releases/tag/v0.1.0
